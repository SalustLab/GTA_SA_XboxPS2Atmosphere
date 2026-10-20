"""P1 - CPostEffects::ColourFilter with the PS2 formula (PLAN §9, findings 2026-09-24).

  PS2: out = clip(fb*2c1) + clip(fb*2c2) * a2      (a2 = in-memory alpha, already x2 by the loader)

The stock "k ~= 0.585" dilution is not a draw property: it is the Xbox-only blur pass 0x24ECAA, which lerps the
pre-filter copy over the result twice at alpha 60 ((1 - 60/255)^2 = 0.585). P1 switches it off (data byte
0x3CE7AD 1 -> 0), so k defaults to 1. Both passes run stage-0 COLOROP = MODULATE2X with vertex colour c * S, S = 2/(mult*k) = 1 for k = 1,

  pass 1  ONE/ZERO      -> clip(4k*fb*c1*S) = clip(fb*2c1)
  pass 2  SRCALPHA/ONE  -> + clip(fb*2c2) * a2
The colour op is written only to the D3D deferred state (0x36BBF8 + dirty 0x800); RW's 2D setup 0x2AB710 leaves
it alone while its cache 0x75D5A0 stays 4. It is restored to MODULATE before returning (HUD).

Usage: py patches/p1_colourfilter.py [k]      -> writes patches/p1_colourfilter.json
"""
import hashlib
import sys
from pathlib import Path

from keystone import KS_ARCH_X86, KS_MODE_32, Ks

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import FLAGS, XBE, A, offset, write_json  # noqa: E402  (--rev0|--eu1|--eu0: Rev 1 VAs below are mapped)

START, END = A(0x24F007), A(0x24F133)      # original function, 300 bytes (ret at 0x24F132)


BLUR_ENABLE = A(0x3CE7AD)                    # .data byte, 1 in the stock XBE; gates the blur pass 0x24ECAA


PE_OFFSETS = A(0x3CE808)                     # int left, top, right, bottom (stream.ini pe_leftx..; PS2 8, Xbox 16)
QUAD = A(0x5C7318)                           # 4 Im2D verts, stride 28, UV at +0x14/+0x18: v0 TL, v1 BL, v2 BR, v3 TR


def _pass2(blur):
    """Pass 2 draw. blur (P2): LINEAR + a stack copy of the quad with UVs shifted by pe/16 texels (PS2 fb')."""
    if not blur:
        return """
        add esp, 0x10
        lea esi, [ebp + 0xc]
        mov dl, byte ptr [ebp + 0xf]
        call pack_draw                      # pass 2: c2*S, A=a2"""
    shifts = ""                             # SkyGfx corners: left v0,v1; top v0,v3; right v2,v3; bottom v1,v2
    for i, (a, v, uv) in enumerate([(0, (0, 1), 0x14), (1, (0, 3), 0x18), (2, (2, 3), 0x14), (3, (1, 2), 0x18)]):
        p, q = (8 + n * 28 + uv for n in v)
        shifts += f"""
        fild dword ptr [{PE_OFFSETS + 4 * a:#x}]
        fidiv dword ptr [esp + {4 * (i & 1)}]   # / (16 * raster w|h)
        fld dword ptr [esp + {p}]
        fadd st(0), st(1)
        fstp dword ptr [esp + {p}]
        fadd dword ptr [esp + {q}]
        fstp dword ptr [esp + {q}]"""
    return f"""
        push 2
        push 9
        call edi           # filter LINEAR (pass 2 only)
        add esp, 0x18
        lea esi, [ebp + 0xc]
        mov dl, byte ptr [ebp + 0xf]
        call pack                           # c2*S, A=a2 into the quad
        sub esp, 0x70
        push edi
        mov esi, {QUAD:#x}
        lea edi, [esp + 4]
        push 0x1c
        pop ecx
        rep movsd dword ptr es:[edi], dword ptr [esi]   # quad -> stack; the original stays unshifted for next frame
        pop edi
        mov eax, dword ptr [{A(0x5f4b28):#x}]  # copy raster: RwRaster width +0xC, height +0x10
        mov ecx, dword ptr [eax + 0xc]
        shl ecx, 4
        mov edx, dword ptr [eax + 0x10]
        shl edx, 4
        push edx
        push ecx                            # [esp] 16w, [esp+4] 16h, quad copy at esp+8{shifts}
        lea eax, [esp + 8]
        call draw
        add esp, 0x78"""


def _helpers(blur, s):
    pack = f"""
    pack:                                   # esi -> R,G,B bytes, dl = alpha
        movzx edx, dl
        mov ecx, 3
    chan:
        shl edx, 8
        movzx eax, byte ptr [esi]
        imul eax, eax, {s}
        add eax, 0x80                       # round, don't truncate
        shr eax, 8
        or edx, eax
        inc esi
        loop chan
        mov dword ptr [{A(0x5c7328):#x}], edx
        mov dword ptr [{A(0x5c7344):#x}], edx
        mov dword ptr [{A(0x5c7360):#x}], edx
        mov dword ptr [{A(0x5c737c):#x}], edx"""
    draw = f"""
        push 6
        push {A(0x3ce82c):#x}
        push 4
        push {{verts}}
        push 3
        call dword ptr [{A(0x75de94):#x}]   # Im2DRenderIndexedPrimitive
        add esp, 0x14
        ret"""
    if not blur:                            # P1 layout, byte-identical to the v0.1 build
        return pack.replace("pack:", "pack_draw:") + draw.replace("{verts}", f"{QUAD:#x}")
    return f"""
    pack_draw:
        call pack
        mov eax, {QUAD:#x}
    draw:                                   # eax -> 4 Im2D verts{draw.replace("{verts}", "eax")}{pack}
        ret"""


def build(k=1.0, blur=False, start=START, end=END):
    mult, op = (2, 5) if k >= 1 else (4, 6)   # MODULATE2X is exact for k = 1; 4X only to compensate k < 1
    s = round(256 * 2 / (mult * k))         # colour scale, fixed point /256 (256 = colour as-is)
    asm = f"""
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        xor ebx, ebx
        inc ebx
        xor esi, esi
        mov edi, dword ptr [{A(0x75de80):#x}]  # RwRenderStateSet, callee-saved register
        push ebx
        push 9
        call edi           # filter NEAREST
        push esi
        push 0xe
        call edi           # fog off
        push esi
        push 6
        call edi           # ztest off
        push esi
        push 8
        call edi           # zwrite off
        push dword ptr [{A(0x5f4b28):#x}]
        push ebx
        call edi           # raster = fb copy
        push ebx
        push 0xc
        call edi           # vertex alpha on
        push 2
        push 0xa
        call edi           # src ONE
        push 1
        push 0xb
        call edi           # dst ZERO
        add esp, 0x40
        mov dword ptr [{A(0x36bbf8):#x}], {op}  # stage0 COLOROP = MODULATE2X/4X (D3D only)
        or dword ptr [{A(0x36e280):#x}], 0x800
        lea esi, [ebp + 8]
        mov dl, 0xff
        call pack_draw                      # pass 1: c1*S, A=FF
        push 5
        push 0xa
        call edi           # src SRCALPHA
        push 2
        push 0xb
        call edi           # dst ONE
{_pass2(blur)}
        mov dword ptr [{A(0x36bbf8):#x}], 4  # restore MODULATE
        or dword ptr [{A(0x36e280):#x}], 0x800
        push 2
        push 9
        call edi           # original restore tail
        push ebx
        push 6
        call edi
        push ebx
        push 8
        call edi
        push 0
        push ebx
        call edi
        push 5
        push 0xa
        call edi
        push 6
        push 0xb
        call edi
        add esp, 0x30
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
{_helpers(blur, s)}
    """
    code, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm(asm, start)
    code = bytes(code)
    assert len(code) <= end - start, f"{len(code)} bytes > {end - start}"
    return code + b"\xcc" * (end - start - len(code)), s


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in FLAGS]
    k = float(args[0]) if args else 1.0
    new, s = build(k)
    xbe = XBE.read_bytes()
    orig = xbe[START - 0x10000:END - 0x10000]
    blur = xbe[offset(xbe, BLUR_ENABLE):offset(xbe, BLUR_ENABLE) + 1]
    out = {"name": f"P1 ColourFilter PS2 formula (k={k}, S={s}/256) + Xbox blur pass off",
           "patches": [{"va": hex(START), "orig_sha1": hashlib.sha1(orig).hexdigest(), "len": len(orig),
                        "new": new.hex(), "note": "full rewrite of CPostEffects::ColourFilter 0x24F007-0x24F132"},
                       {"va": hex(BLUR_ENABLE), "orig_sha1": hashlib.sha1(blur).hexdigest(), "len": 1,
                        "new": "00", "note": "disable the Xbox blur pass 0x24ECAA (re-adds the pre-filter frame)"}]}
    path = write_json(__file__, out)
    print(f"{len(new.rstrip(bytes([0xcc])))} code bytes / {len(new)}; S={s}; wrote {path.name}")
