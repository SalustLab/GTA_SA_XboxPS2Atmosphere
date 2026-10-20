"""P4 v2 - PS2 building lighting (PLAN §9 P4, H5; findings 2026-09-24 "Phase 5", "P4 v2 step 1/2").

Xbox building vertex shaders (decoded, blobs 0x3C9B18..0x3CA270):
  DN blobs 0x3C9B18/0x3C9C00/0x3C9DA8/0x3C9E90:  oD0.rgb = (night*c23.x + day*c23.y)*c20 + c15*c21
  other 4 building blobs:                         oD0.rgb = prelight*c20 + c15*c21        (no c23)
  c20 = matCol*surfDiff, c21 = matCol*surfAmb, c15 = ambient light (<= 1), c23 = (b, 1-b) with b = DN balance.
PS2 fit (Grove St sweeps, PS2 display chain removed with ps2disp.disp):
  PS2 ~ G*day*(1-b) + N*night*b + KA*ambient   (KA/G ~ 2: SkyGfx's x255/128 ambient times a common ~0.9)

P4 v2 edits, all in place:
  c15 (ambient) - the three 86-byte clamp blocks: c15 = min(pAmbient, 1) * (KA, KA, KA, 1)   (w kept: vehicles read c15.w)
    0x166D91  setup 0x166C70 (building DN pipe, VS [0x5F291C])                   -> always; also holds the constants
    0x167700  setup 0x1675DF (building DN pipe 0x53F20096, VS [0x5F2928])        -> always
    0x16A30A  setup 0x16A1E5, shared with the vehicle/unlit pipes (VS [0x5F2960], [0x5F2984])
              -> only when RW's current VS [0x3D4750] is a building one ([0x5F2934] / [0x5F2940])
  c23 (DN weights) - 0x166E4C / 0x1677BB (41 B each): c23 = (b, 1-b, 0, 0) * (N, G, 0, 0). Only the DN blobs read c23.
A VS operand edit is not possible: each blob's `mov r, c[15]` shares its operand C with a paired ILU `mov oT0, ...`.
Not reproduced: PS2 overbright (the VS output still clamps at 1); G on the 4 non-DN building blobs (needs c20,
whose per-material upload 0x166EE3 is shared with vehicles).
# ponytail: non-DN buildings keep prelight x1; gate c20 on [0x3D4750] if a scene shows the residual.

Usage: py patches/p4_building_ambient.py [--selftest]      -> writes patches/p4_building_ambient.json
"""
import hashlib
import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from keystone import KS_ARCH_X86, KS_MODE_32, Ks

G, N, KA = 0.91, 0.80, 1.80                     # findings "P4 v2 step 2"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import XBE, A, write_json  # noqa: E402  (--rev0|--eu1|--eu0: Rev 1 VAs below are mapped)
P_AMBIENT, RW_CUR_VS = A(0x5F4BFC), A(0x3D4750)
BUILDING_VS_SHARED = (A(0x5F2934), A(0x5F2940))      # handles that reach the shared setup 0x16A1E5 from building pipes
BLOCKS = ((A(0x166D91), A(0x166DE7), "ebp + 0x54", False),   # (start, end, c15 stack slot, shared -> check the VS)
          (A(0x167700), A(0x167756), "ebp + 0x54", False),
          (A(0x16A30A), A(0x16A360), "ebp - 0x20", True))
C23 = ((A(0x166E4C), A(0x3C9B10)), (A(0x1677BB), A(0x3C9DA4)))    # (site, DN balance global); 41 B, ends at the upload call
C23_LEN = 41
K_C23 = BLOCKS[0][1] - 32                        # constants live in the tail of block 0x166D91, after its jmp
K_AMB = K_C23 + 16


def text(xbe, va, n):
    return xbe[va - 0x10000:va - 0x10000 + n]


def stock_ok(xbe, start, end, slot):
    """The stock block: mov ecx,[pAmbient]; 4x (movss xmm0,[ecx+0x18+4k]; comiss xmm4,xmm0; movss [slot+4k],xmm0; ja; movss [slot+4k],xmm4)."""
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(text(xbe, start, end - start), start))
    assert sum(i.size for i in ins) == end - start and len(ins) == 21, hex(start)
    assert (ins[0].mnemonic, ins[0].op_str) == ("mov", f"ecx, dword ptr [{P_AMBIENT:#x}]"), ins[0].op_str
    base = int(slot.split()[-1], 16) * (-1 if "-" in slot else 1)
    for k in range(4):
        ld, cmp, st, ja, st1 = ins[1 + 5 * k:6 + 5 * k]
        disp = lambda d: f"ebp {'+' if d >= 0 else '-'} {abs(d):#x}"
        assert ld.op_str == f"xmm0, dword ptr [ecx + {0x18 + 4 * k:#x}]" and cmp.op_str == "xmm4, xmm0", hex(ld.address)
        assert st.op_str == f"dword ptr [{disp(base + 4 * k)}], xmm0" and ja.mnemonic == "ja", hex(st.address)
        assert st1.op_str == f"dword ptr [{disp(base + 4 * k)}], xmm4", hex(st1.address)
    nxt = next(Cs(CS_ARCH_X86, CS_MODE_32).disasm(text(xbe, end, 3), end))
    assert (nxt.mnemonic, nxt.op_str) == ("mov", "eax, dword ptr [eax + 4]"), nxt.op_str   # eax = pDirect, kept


def c23_stock_ok(xbe, site, bal):
    """movss xmm0,[bal]; push 0x77; movaps xmm1,xmm4; subss xmm1,xmm0; lea edx,[ebp+0x28]; pop ecx;
    movss [ebp+0x28..0x34], xmm0/xmm1/xmm7/xmm7; then call 0x35D0A0 (SetVertexShaderConstant c23). xmm7 = 0, xmm4 = (1,0,0,0)."""
    ops = [(i.mnemonic, i.op_str) for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(text(xbe, site, C23_LEN + 5), site)]
    assert ops == [("movss", f"xmm0, dword ptr [{bal:#x}]"), ("push", "0x77"), ("movaps", "xmm1, xmm4"),
                   ("subss", "xmm1, xmm0"), ("lea", "edx, [ebp + 0x28]"), ("pop", "ecx"),
                   ("movss", "dword ptr [ebp + 0x28], xmm0"), ("movss", "dword ptr [ebp + 0x2c], xmm1"),
                   ("movss", "dword ptr [ebp + 0x30], xmm7"), ("movss", "dword ptr [ebp + 0x34], xmm7"),
                   ("call", f"{A(0x35D0A0):#x}")], (hex(site), ops)


def asm(src, va):
    return bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(src, va)[0])


def build(start, end, slot, shared):
    check = "".join(f"cmp edx, dword ptr [{h:#x}]; je scale; " for h in BUILDING_VS_SHARED)
    src = (f"mov ecx, dword ptr [{P_AMBIENT:#x}]; movups xmm0, [ecx + 0x18];"
           f"movaps xmm2, xmm4; shufps xmm2, xmm2, 0; minps xmm0, xmm2; movups [{slot}], xmm0;"   # xmm4 = (1,0,0,0)
           + (f"mov edx, dword ptr [{RW_CUR_VS:#x}]; {check}jmp done;" if shared else "")
           + f"scale: movups xmm2, [{K_AMB:#x}]; mulps xmm0, xmm2; movups [{slot}], xmm0; done: jmp {end:#x}")
    code = asm(src, start)
    room = (K_C23 if start == BLOCKS[0][0] else end) - start
    assert len(code) <= room, (hex(start), len(code), room)
    code += b"\xcc" * (room - len(code))
    if start == BLOCKS[0][0]:
        code += struct.pack("<8f", N, G, 0, 0, KA, KA, KA, 1)
    return code


def build_c23(site, bal):
    src = (f"movss xmm0, dword ptr [{bal:#x}]; movaps xmm1, xmm4; subss xmm1, xmm0; unpcklps xmm0, xmm1;"  # (b, 1-b, 0, 0)
           f"movups xmm1, [{K_C23:#x}]; mulps xmm0, xmm1; movups [ebp + 0x28], xmm0;"                       # * (N, G, 0, 0)
           f"push 0x77; pop ecx; lea edx, [ebp + 0x28]")
    code = asm(src, site)
    assert len(code) <= C23_LEN, (hex(site), len(code))
    return code + b"\x90" * (C23_LEN - len(code))                  # falls through into the upload call


def patches(xbe):
    out = []
    for start, end, slot, shared in BLOCKS:
        stock_ok(xbe, start, end, slot)
        out.append({"va": hex(start), "orig_sha1": hashlib.sha1(text(xbe, start, end - start)).hexdigest(),
                    "len": end - start, "new": build(start, end, slot, shared).hex(),
                    "note": f"c15 = min(pAmbient,1)*({KA},{KA},{KA},1){' if RW VS is a building one' if shared else ''}"
                            + (f"; constants (N,G,0,0),(KA,KA,KA,1) at {K_C23:#x}" if start == BLOCKS[0][0] else "")})
    for site, bal in C23:
        c23_stock_ok(xbe, site, bal)
        out.append({"va": hex(site), "orig_sha1": hashlib.sha1(text(xbe, site, C23_LEN)).hexdigest(),
                    "len": C23_LEN, "new": build_c23(site, bal).hex(), "note": f"c23 = (b,1-b,0,0)*({N},{G},0,0)"})
    return out


def model(b, day, night, amb):
    """What the patched DN building VS computes (before the [0,1] clamp): numpy-free scalar reference."""
    c23 = (b * N, (1 - b) * G)
    return night * c23[0] + day * c23[1] + min(amb, 1) * KA


def selftest():
    xbe = XBE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    es = patches(xbe)
    for (start, end, slot, shared), e in zip(BLOCKS, es):
        new = bytes.fromhex(e["new"])
        code = new[:K_C23 - start] if start == BLOCKS[0][0] else new
        ins = list(md.disasm(code.rstrip(b"\xcc"), start))
        assert sum(i.size for i in ins) == len(code.rstrip(b"\xcc")), hex(start)
        ops = [(i.mnemonic, i.op_str) for i in ins]
        assert ops[-1] == ("jmp", f"{end:#x}")
        assert ("minps", "xmm0, xmm2") in ops and ("mulps", "xmm0, xmm2") in ops
        assert ("movups", f"xmm2, xmmword ptr [{K_AMB:#x}]") in ops
        assert not any("eax" in o or "xmm4" in o.split(", ")[0] for _, o in ops), "eax (pDirect) and xmm4 (1.0) must survive"
        assert (("mov", f"edx, dword ptr [{RW_CUR_VS:#x}]") in ops) == shared
    k = bytes.fromhex(es[0]["new"])[K_C23 - BLOCKS[0][0]:]
    assert struct.unpack("<8f", k) == struct.unpack("<8f", struct.pack("<8f", N, G, 0, 0, KA, KA, KA, 1))
    assert BLOCKS[0][0] < K_C23 and K_AMB + 16 == BLOCKS[0][1]
    for (site, bal), e in zip(C23, es[3:]):
        new = bytes.fromhex(e["new"])
        ops = [(i.mnemonic, i.op_str) for i in md.disasm(new, site)]
        assert sum(1 for _ in md.disasm(new, site)) == len(ops) and ops[-1] == ("nop", ""), hex(site)
        assert ("movups", f"xmm1, xmmword ptr [{K_C23:#x}]") in ops and ("mulps", "xmm0, xmm1") in ops
        assert ("push", "0x77") in ops and ("lea", "edx, [ebp + 0x28]") in ops and ("pop", "ecx") in ops
        assert not any(o.split(", ")[0] in ("xmm4", "xmm7") for _, o in ops), "xmm4/xmm7 must survive"
        assert next(md.disasm(text(xbe, site + C23_LEN, 5), site + C23_LEN)).op_str == f"{A(0x35D0A0):#x}"
    # model: noon (b 0) day-only, night (b 1) night-only, ambient clamp
    assert abs(model(0, 0.5, 0.3, 0) - 0.5 * G) < 1e-9 and abs(model(1, 0.5, 0.3, 0) - 0.3 * N) < 1e-9
    assert abs(model(0, 0, 0, 2.0) - KA) < 1e-9
    print("p4_building_ambient selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    out = {"name": f"P4 v2 PS2 building lighting (c23 x (N {N}, G {G}), c15 x KA {KA})", "patches": patches(XBE.read_bytes())}
    path = write_json(__file__, out)
    print(f"{len(out['patches'])} blocks; wrote {path.name}")
