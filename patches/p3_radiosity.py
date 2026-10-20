"""P3 - CPostEffects::Radiosity, PS2 behaviour (PLAN §9 P3; SkyGfx postfx.cpp CPostEffects::Radiosity, fixed-function PS2 path).

  out = F + renderPasses x clip(up(H) * intensity/255),   H = clip(2*down(F) - limit)

down = filterPasses bilinear 2:1 halvings with SkyGfx's PS2 geometry (src [UC+0.5, dw+0.5] -> dst [0, dw/2+1],
UC/VC = 0x3CE7D4/D8 = 2), up = bilinear stretch of the (dw+1)-texel highlight region back to the full screen.
The stock body 0x24DF8E-0x24E512 (1413 B) draws PS2 sprite strips that degenerate on Xbox (E2: no bloom); it is
replaced in place, same ABI: [esp+4] limit, [esp+8] filterPasses, [esp+0xC] intensity, eax = renderPasses
(callers 0x24CD7D: timecyc limit, 2, 35, 1; 0x24CB32 darkness filter: 45, 0, 255, 2).

Xbox has two surfaces to ping-pong: the backbuffer BB (screen raster 0x5F4B2C, linear, texel-unit UVs) and the
copy C (0x5F4B28, 1024x512 swizzled, normalised UVs) whose strip x >= 640 is never on screen. 0x24BB7B first
copies F into C; downsample hops then alternate C -> BB corner (scene camera) and BB corner -> C strip (postfx
camera 0x5F4B30, the 0x24BB7B pattern). The highlight 2T - L is one stage-0 op, ADDSIGNED2X = 2T + 2d - 1 with
vertex colour d = 128 - L*128/255 (SkyGfx's SUBTRACT/ADD pair), merged into the last hop when that hop lands in C
(the clip commutes with nothing in between), else a separate 1:1 hop, as in SkyGfx. BB is then restored 1:1
from C, the highlight is added with SRCALPHA/ONE, and C is refreshed once more (SkyGfx UpdateFrontBuffer).
filterPasses = 0 (darkness filter) merges the highlight into the 1:1 composite instead.

Usage: py patches/p3_radiosity.py [--selftest]      -> writes patches/p3_radiosity.json
"""
import hashlib
import sys
from pathlib import Path

from keystone import KS_ARCH_X86, KS_MODE_32, Ks

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import XBE, A, write_json  # noqa: E402  (--rev0|--eu1|--eu0: Rev 1 VAs below are mapped)

START, END = A(0x24DF8E), A(0x24E513)  # stock Radiosity, ret at 0x24E512 [C]; 0x24E513 is another function

RWSTATE, IM2D_INDEXED = A(0x75DE80), A(0x75DE94)  # [RwRenderStateSet], [RwIm2DRenderIndexedPrimitive]
CAM_END, CAM_BEGIN = A(0x2977F0), A(0x297800)  # RwCameraEndUpdate / RwCameraBeginUpdate (cdecl, camera)
SCENE_CAM, POSTFX_CAM = A(0x5B8528), A(0x5F4B30)  # postfx camera raster = the copy C
COPY, SCREEN = A(0x5F4B28), A(0x5F4B2C)  # RwRaster*: fb copy (width +0xC, height +0x10), backbuffer
FB_COPY = A(0x24BB7B)  # BB -> C full-screen copy (leaves NEAREST, fog/vtxalpha off, clamp)
SCREEN_W, SCREEN_H = A(0x5B8530), A(0x5B8534)
UCORR, VCORR = A(0x3CE7D4), A(0x3CE7D8)  # m_RadiosityFilterU/VCorrection (2, 2)
QUAD, INDICES = A(0x5C7318), A(0x3CE82C)  # ColourFilter quad (template for z/rhw), indices 0,1,2, 0,2,3
COLOROP, DIRTY = A(0x36BBF8), A(0x36E280)# D3D stage-0 COLOROP (deferred) + dirty 0x800, as in P1
MODULATE, ADDSIGNED2X = 4, 9

# frame (ebp): args +8 limit, +0xC passes, +0x10 intensity; locals below; P = draw block at ebp-0x4C (= esp)
RP, W, H, OX, DCOL = -0x10, -0x14, -0x18, -0x1C, -0x20
# P: +0 x0 +4 y0 +8 x1 +0xC y1 (dst px) | +0x10 u0 +0x14 v0 +0x18 u1 +0x1C v1 (src texels, +0.5 added) |
#    +0x20 src-is-BB flag (then the draw targets C) | +0x24 ARGB | +0x28 stage-0 COLOROP


def _vertices():
    """Fill the stack quad (v0 TL, v1 BL, v2 BR, v3 TR; stride 28: x y z rhw colour u v) from P (ebx)."""
    out = ""
    for n, (c, r) in enumerate([(0, 0), (0, 1), (1, 1), (1, 0)]):
        o = n * 28
        out += f"""
        cvtsi2ss xmm0, dword ptr [ebx + {8 * c}]
        movss dword ptr [esp + {o}], xmm0
        cvtsi2ss xmm0, dword ptr [ebx + {4 + 8 * r}]
        movss dword ptr [esp + {o + 4}], xmm0
        mov dword ptr [esp + {o + 0x10}], edx
        cvtsi2ss xmm0, dword ptr [ebx + {0x10 + 8 * c}]
        addss xmm0, xmm5
        divss xmm0, xmm6
        movss dword ptr [esp + {o + 0x14}], xmm0
        cvtsi2ss xmm0, dword ptr [ebx + {0x14 + 8 * r}]
        addss xmm0, xmm5
        divss xmm0, xmm7
        movss dword ptr [esp + {o + 0x18}], xmm0"""
    return out


def build(start=START, end=END):
    asm = f"""
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        sub esp, 0x40
        mov ebx, esp                        # P
        mov dword ptr [ebp {RP}], eax       # renderPasses
        call {FB_COPY:#x}                   # C = F (the frame as filtered so far)
        mov edi, dword ptr [{RWSTATE:#x}]
        xor esi, esi
        push 2
        push 9
        call edi                            # filter LINEAR
        push esi
        push 6
        call edi                            # ztest off
        push esi
        push 8
        call edi                            # zwrite off
        push 2
        push 0xa
        call edi                            # src ONE
        push 1
        push 0xb
        call edi                            # dst ZERO
        add esp, 0x28
        mov dword ptr [ebx + 4], esi        # y0 = 0 throughout
        mov dword ptr [ebx + 0x20], esi     # source = C
        mov dword ptr [ebp {OX}], esi
        mov eax, dword ptr [{SCREEN_W:#x}]
        mov dword ptr [ebp {W}], eax
        mov eax, dword ptr [{SCREEN_H:#x}]
        mov dword ptr [ebp {H}], eax
        mov eax, dword ptr [ebp + 8]        # d = 128 - limit*128/255, as grey ARGB, A = FF
        shl eax, 7
        xor edx, edx
        mov ecx, 0xff
        div ecx
        neg eax
        add eax, 0x80
        imul eax, eax, 0x10101
        or eax, 0xff000000
        mov dword ptr [ebp {DCOL}], eax

    hop:                                    # downsample: src [ox+UC, ox+w] x [VC, h] -> dst [dx, dx+w/2+1] x [0, h/2+1]
        cmp esi, dword ptr [ebp + 0xc]
        jge hops_done
        inc esi
        mov eax, dword ptr [ebp {OX}]
        mov ecx, eax
        add ecx, dword ptr [{UCORR:#x}]
        mov dword ptr [ebx + 0x10], ecx
        add eax, dword ptr [ebp {W}]
        mov dword ptr [ebx + 0x18], eax
        mov eax, dword ptr [{VCORR:#x}]
        mov dword ptr [ebx + 0x14], eax
        mov eax, dword ptr [ebp {H}]
        mov dword ptr [ebx + 0x1c], eax
        sar dword ptr [ebp {W}], 1
        sar dword ptr [ebp {H}], 1
        xor eax, eax                        # dst: BB corner (x 0) from C, C strip (x = screen w) from BB
        cmp dword ptr [ebx + 0x20], eax
        je dst_x
        mov eax, dword ptr [{SCREEN_W:#x}]
    dst_x:
        mov dword ptr [ebx], eax
        mov dword ptr [ebp {OX}], eax
        mov ecx, dword ptr [ebp {W}]
        lea eax, [eax + ecx + 1]
        mov dword ptr [ebx + 8], eax
        mov eax, dword ptr [ebp {H}]
        inc eax
        mov dword ptr [ebx + 0xc], eax
        or dword ptr [ebx + 0x24], 0xffffffff
        mov dword ptr [ebx + 0x28], {MODULATE}
        cmp esi, dword ptr [ebp + 0xc]
        jne do_hop
        cmp dword ptr [ebx + 0x20], 0
        je do_hop                           # last hop lands in BB: highlight gets its own 1:1 hop below
        mov eax, dword ptr [ebp {DCOL}]
        mov dword ptr [ebx + 0x24], eax
        mov dword ptr [ebx + 0x28], {ADDSIGNED2X}
    do_hop:
        call draw
        xor dword ptr [ebx + 0x20], 1
        jmp hop

    hops_done:
        cmp dword ptr [ebx + 0x20], 0
        je highlit
        xor eax, eax                        # 1:1 highlight hop BB corner -> C strip, (w+1) x (h+1)
        mov dword ptr [ebx + 0x10], eax
        mov dword ptr [ebx + 0x14], eax
        mov eax, dword ptr [ebp {W}]
        inc eax
        mov dword ptr [ebx + 0x18], eax
        mov ecx, dword ptr [{SCREEN_W:#x}]
        mov dword ptr [ebx], ecx
        mov dword ptr [ebp {OX}], ecx
        add eax, ecx
        mov dword ptr [ebx + 8], eax
        mov eax, dword ptr [ebp {H}]
        inc eax
        mov dword ptr [ebx + 0x1c], eax
        mov dword ptr [ebx + 0xc], eax
        mov eax, dword ptr [ebp {DCOL}]
        mov dword ptr [ebx + 0x24], eax
        mov dword ptr [ebx + 0x28], {ADDSIGNED2X}
        call draw
        mov dword ptr [ebx + 0x20], 0
    highlit:
        xor eax, eax                        # full-screen 1:1 quad from C (restore, then composite)
        mov dword ptr [ebx], eax
        mov dword ptr [ebx + 0x14], eax
        mov eax, dword ptr [{SCREEN_W:#x}]
        mov dword ptr [ebx + 8], eax
        mov eax, dword ptr [{SCREEN_H:#x}]
        mov dword ptr [ebx + 0xc], eax
        cmp dword ptr [ebp + 0xc], 0
        jle composite                       # no hop touched BB
        mov dword ptr [ebx + 0x10], 0
        mov eax, dword ptr [{SCREEN_W:#x}]
        mov dword ptr [ebx + 0x18], eax
        mov eax, dword ptr [{SCREEN_H:#x}]
        mov dword ptr [ebx + 0x1c], eax
        or dword ptr [ebx + 0x24], 0xffffffff
        mov dword ptr [ebx + 0x28], {MODULATE}
        call draw                           # BB = F again

    composite:                              # src [ox, ox+w] x [0, h] stretched over the screen, SRCALPHA/ONE
        mov eax, dword ptr [ebp {OX}]
        mov dword ptr [ebx + 0x10], eax
        add eax, dword ptr [ebp {W}]
        mov dword ptr [ebx + 0x18], eax
        mov eax, dword ptr [ebp {H}]
        mov dword ptr [ebx + 0x1c], eax
        mov eax, dword ptr [ebp {DCOL}]
        mov dword ptr [ebx + 0x28], {ADDSIGNED2X}
        cmp dword ptr [ebp + 0xc], 0
        jle comp_colour                     # filterPasses 0: highlight in this 1:1 draw
        or eax, 0xffffffff
        mov dword ptr [ebx + 0x28], {MODULATE}
    comp_colour:
        and eax, 0xffffff
        movzx ecx, byte ptr [ebp + 0x10]
        shl ecx, 0x18
        or eax, ecx
        mov dword ptr [ebx + 0x24], eax     # A = intensity -> /255
        push 1
        push 0xc
        call edi                            # vertex alpha on
        push 5
        push 0xa
        call edi                            # src SRCALPHA
        push 2
        push 0xb
        call edi                            # dst ONE
        add esp, 0x18
        mov esi, dword ptr [ebp {RP}]
    comp_pass:
        test esi, esi
        jle comp_done
        call draw
        dec esi
        jmp comp_pass
    comp_done:
        mov dword ptr [{COLOROP:#x}], {MODULATE}
        or dword ptr [{DIRTY:#x}], 0x800
        call {FB_COPY:#x}                   # C = final frame (SkyGfx UpdateFrontBuffer); leaves the stock tail's
        push 5                              # fog/vertex alpha off, ztest/zwrite on, raster none
        push 0xa
        call edi                            # src SRCALPHA
        push 6
        push 0xb
        call edi                            # dst INVSRCALPHA
        add esp, 0x10
        add esp, 0x40
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret

    draw:                                   # ebx -> P; preserves ebx/esi/edi
        push esi
        push edi
        mov eax, dword ptr [{COPY:#x}]
        push dword ptr [eax + 0x10]         # UV denominators: C height, width
        push dword ptr [eax + 0xc]
        cmp dword ptr [ebx + 0x20], 0
        je set_raster
        mov dword ptr [esp], 1              # BB is linear: texel-unit UVs
        mov dword ptr [esp + 4], 1
        push dword ptr [{SCENE_CAM:#x}]
        call {CAM_END:#x}
        push dword ptr [{POSTFX_CAM:#x}]
        call {CAM_BEGIN:#x}                 # render into C
        add esp, 8
        mov eax, dword ptr [{SCREEN:#x}]
    set_raster:
        push eax
        push 1
        call dword ptr [{RWSTATE:#x}]
        add esp, 8
        sub esp, 0x70
        mov esi, {QUAD:#x}
        mov edi, esp
        push 0x1c
        pop ecx
        rep movsd dword ptr es:[edi], dword ptr [esi]
        cvtsi2ss xmm6, dword ptr [esp + 0x70]
        cvtsi2ss xmm7, dword ptr [esp + 0x74]
        push 0x3f000000
        movss xmm5, dword ptr [esp]         # 0.5 (texel centre)
        pop eax
        mov edx, dword ptr [ebx + 0x24]{_vertices()}
        mov eax, dword ptr [ebx + 0x28]
        mov dword ptr [{COLOROP:#x}], eax   # D3D only; RW's cache 0x75D5A0 stays 4 (P1)
        or dword ptr [{DIRTY:#x}], 0x800
        mov eax, esp
        push 6
        push {INDICES:#x}
        push 4
        push eax
        push 3
        call dword ptr [{IM2D_INDEXED:#x}]
        add esp, 0x14 + 0x78
        cmp dword ptr [ebx + 0x20], 0
        je drawn
        push dword ptr [{POSTFX_CAM:#x}]
        call {CAM_END:#x}
        push dword ptr [{SCENE_CAM:#x}]
        call {CAM_BEGIN:#x}                 # back to BB
        add esp, 8
    drawn:
        pop edi
        pop esi
        ret
    """
    code, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm(asm, start)
    code = bytes(code)
    assert len(code) <= end - start, f"{len(code)} bytes > {end - start}"
    return code + b"\xcc" * (end - start - len(code))


def model(frame, limit, passes=2, intensity=35, render=1, ucorr=2, vcorr=2):
    """What the patch draws, in numpy (float, 0..255, HxWx3): SkyGfx's PS2 geometry with real bilinear sampling."""
    import numpy as np

    def sample(img, x0, x1, y0, y1, u0, u1, v0, v1, nw, nh):
        """Rasterise a quad dst [x0,x1)x[y0,y1) (pixel centres at integers) sampling img bilinearly, texel centres +0.5."""
        xs, ys = np.arange(x0, min(x1, nw)), np.arange(y0, min(y1, nh))
        u = u0 + (xs - x0) * (u1 - u0) / (x1 - x0) - 0.5
        v = v0 + (ys - y0) * (v1 - v0) / (y1 - y0) - 0.5
        iu, iv = np.floor(u).astype(int), np.floor(v).astype(int)
        fu, fv = (u - iu)[None, :, None], (v - iv)[:, None, None]
        cu = lambda a: np.clip(a, 0, img.shape[1] - 1)
        cv = lambda a: np.clip(a, 0, img.shape[0] - 1)
        g = lambda dv, du: img[cv(iv + dv)][:, cu(iu + du)]
        out = np.zeros((nh, nw, 3))
        out[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1] = ((1 - fv) * ((1 - fu) * g(0, 0) + fu * g(0, 1)) +
                                                   fv * ((1 - fu) * g(1, 0) + fu * g(1, 1)))
        return out

    q = lambda a: np.round(np.clip(a, 0, 255))                        # 8-bit render targets
    hi = lambda a: q(2 * a - 2 * (limit * 128 // 255))                # SkyGfx 2*(D - limit*128/255)
    h, w = frame.shape[:2]
    cur, dw, dh = frame, w, h
    for _ in range(passes):
        nw, nh = dw // 2, dh // 2
        cur = q(sample(cur, 0, nw + 1, 0, nh + 1, ucorr + 0.5, dw + 0.5, vcorr + 0.5, dh + 0.5, nw + 1, nh + 1))
        dw, dh = nw, nh
    cur = hi(cur)
    out = frame.astype(float)
    add = sample(cur, 0, w, 0, h, 0.5, dw + 0.5, 0.5, dh + 0.5, w, h) if passes else cur[:h, :w]
    for _ in range(render):
        out = q(out + q(add * intensity / 255))
    return out


def selftest():
    import numpy as np
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs

    code = build().rstrip(b"\xcc")
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, START))
    assert sum(i.size for i in ins) == len(code), "disassembly must cover every byte"
    assert ins[-1].mnemonic == "ret" and ins[0].mnemonic == "push" and ins[0].op_str == "ebp"
    # every external call is to a known RW/game entry; every draw goes through Im2DRenderIndexedPrimitive
    draw = next(i.address for i in ins if i.mnemonic == "ret") + 1
    calls = {int(i.op_str, 16) for i in ins if i.mnemonic == "call" and i.op_str.startswith("0x")}
    assert calls == {FB_COPY, CAM_END, CAM_BEGIN, draw}, [hex(c) for c in calls]
    assert sum(f"[{IM2D_INDEXED:#x}]" in i.op_str for i in ins) == 1
    # stack balance: pushes before each call are popped (checked live); here: the frame is torn down symmetrically
    assert [i.op_str for i in ins if i.mnemonic == "sub" and "esp" in i.op_str] == ["esp, 0x40", "esp, 0x70"]
    # d = 128 - limit*128/255 for the stock limits (noon 180, midnight 90, darkness 45, override 220)
    for lim, d in ((180, 38), (90, 83), (45, 106), (220, 18)):
        assert 128 - lim * 128 // 255 == d
        assert abs((255 - 2 * d) - 2 * (lim * 128 // 255)) <= 1          # ADDSIGNED2X threshold vs SkyGfx +-1
    # model: a flat frame below the limit gets no bloom; one above it gets the analytic amount
    flat = np.full((480, 640, 3), 80.0)
    assert np.array_equal(model(flat, 180), flat)
    bright = np.full((480, 640, 3), 200.0)
    add = np.round(np.round(2 * 200 - 180) * 35 / 255)                  # 220 * 35/255 = 30.2
    assert np.all(model(bright, 180) == 200 + add), np.unique(model(bright, 180))
    # a single bright pixel blooms into a soft blob around it, energy spread over ~4x4 px x (4x4 upscale)
    dot = flat.copy()
    dot[200:208, 300:308] = 255
    m = model(dot, 180)
    assert m[204, 304, 0] > 80 and m[100, 100, 0] == 80 and (m > 80).any(axis=2).sum() > 64
    # darkness filter path (passes 0, render 2): 1:1, no spatial spread
    dk = model(dot, 45, passes=0, intensity=255, render=2)
    assert np.array_equal(dk[199, 300], dk[100, 100]) and dk[200, 300, 0] == 255   # no spread next to the dot
    print(f"p3_radiosity selftest OK ({len(code)} of {END - START} bytes)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    new = build()
    orig = XBE.read_bytes()[START - 0x10000:END - 0x10000]
    out = {"name": "P3 Radiosity, PS2 behaviour (SkyGfx geometry; needs stream.ini pe_bRadiosity 1)",
           "patches": [{"va": hex(START), "orig_sha1": hashlib.sha1(orig).hexdigest(), "len": len(orig),
                        "new": new.hex(), "note": "full rewrite of CPostEffects::Radiosity 0x24DF8E-0x24E512"}]}
    path = write_json(__file__, out)
    print(f"{len(new.rstrip(bytes([0xcc])))} code bytes / {len(new)}; wrote {path.name}")
