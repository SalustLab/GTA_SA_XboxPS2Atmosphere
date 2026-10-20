"""P6b - PS2 alpha-test semantics for the building pipes: SkyGfx-style dual pass (findings 2026-09-25, "Phase 6B").

PS2 GS TEST_1 for 3D = ATE 1, GEQUAL, AREF 64/128, AFAIL FB_ONLY: a pixel that fails the alpha test is still
blended into the colour buffer and only skips the Z write. The Xbox (D3D) discards it (GREATER 100/140), which
thins the foliage and hard-cuts its edges. D3D has no FB_ONLY, so each alpha-tested, blended mesh is drawn twice:
  pass 1: ALPHATESTFUNCTION GREATEREQUAL, ref 128, Z write as set   (the solid part, depth-correct)
  pass 2: ALPHATESTFUNCTION LESS,         ref 128, Z write off      (the soft fringe, colour only)
then the three RW states are restored. Meshes without alpha test or without blending keep the single draw.

Hook: the one draw of the building mesh helper 0x16AD9A (5 building-pipe callers) is `call 0x2A0F00` at 0x16AFA3
(RW: flush deferred states 0x2A0230, then D3DDevice_DrawIndexedVertices(prim, count, indices), cdecl).
It becomes `call CAVE`. States go through RwRenderStateSet/Get ([0x75DE80]/[0x75DE84]) so RW's cache stays right:
8 = ZWRITEENABLE, 29 = ALPHATESTFUNCTION (2 LESS, 7 GREATEREQUAL), 30 = ALPHATESTFUNCTIONREF.
D3D current state after the flush: ALPHA_TEST_ENABLE [0x36E378], BLEND_ENABLE [0x36E374] (D3D_g_RenderState).

Cave: 0x24F00C-0x24F132, the stock ColourFilter body after P2's jmp; the JSON "requires" p2_filterblur.
Usage: py patches/p6b_dualpass.py [--selftest]      -> writes patches/p6b_dualpass.json
"""
import struct
import sys
from pathlib import Path

from keystone import Ks, KS_ARCH_X86, KS_MODE_32

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import SHA1, XBE, A, write_json  # noqa: E402  (--rev0|--eu1|--eu0: Rev 1 VAs below are mapped)

SITE, DRAW, FLUSH = A(0x16AFA3), A(0x2A0F00), A(0x2A0230)
RS_SET, RS_GET = A(0x75DE80), A(0x75DE84)
D3D_ATEST, D3D_BLEND = A(0x36E378), A(0x36E374)
ZWRITE, AFUNC, AREF = 8, 29, 30
LESS, GEQUAL, REF = 2, 7, 128
CAVE, CAVE_END = A(0x24F00C), A(0x24F133)   # dead stock ColourFilter body: P2 turns 0x24F007 into jmp 0x24ECAA
                                     # (no external jump or pointer into 0x24F00C-0x24F132), so P6b requires P2


def site(cave):
    return b"\xE8" + struct.pack("<i", cave - (SITE + 5))


def asm(cave):
    set_ = lambda st, v: f"push {v}\npush {st}\ncall dword ptr [{RS_SET:#x}]\nadd esp, 8\n"
    get = lambda st, slot: f"lea eax, [ebp-{slot}]\npush eax\npush {st}\ncall dword ptr [{RS_GET:#x}]\nadd esp, 8\n"
    draw = "push dword ptr [ebp+16]\npush dword ptr [ebp+12]\npush dword ptr [ebp+8]\n" \
           f"call {DRAW:#x}\nadd esp, 12\n"
    return (
        f"call {FLUSH:#x}\n"                                   # D3D state now = what this mesh draws with
        f"cmp dword ptr [{D3D_ATEST:#x}], 0\nje single\n"
        f"cmp dword ptr [{D3D_BLEND:#x}], 0\nje single\n"
        "push ebp\nmov ebp, esp\nsub esp, 12\n"
        + get(ZWRITE, 4) + get(AFUNC, 8) + get(AREF, 12)
        + set_(AFUNC, GEQUAL) + set_(AREF, REF) + draw          # pass 1
        + set_(AFUNC, LESS) + set_(ZWRITE, 0) + draw            # pass 2
        + f"push dword ptr [ebp-4]\npush 8\ncall dword ptr [{RS_SET:#x}]\nadd esp, 8\n"
        + f"push dword ptr [ebp-8]\npush 29\ncall dword ptr [{RS_SET:#x}]\nadd esp, 8\n"
        + f"push dword ptr [ebp-12]\npush 30\ncall dword ptr [{RS_SET:#x}]\nadd esp, 8\n"
        + "leave\nret\n"
        + f"single:\njmp {DRAW:#x}\n")


def build(cave):
    return bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(asm(cave), cave)[0])


def selftest():
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    code = build(CAVE)
    ins = list(md.disasm(code, CAVE))
    assert sum(i.size for i in ins) == len(code), "disassembly must cover every byte"
    assert CAVE + len(code) <= CAVE_END, len(code)
    calls = [i.op_str for i in ins if i.mnemonic == "call"]
    assert calls.count(hex(DRAW)) == 2 and calls[0] == hex(FLUSH)
    assert calls.count(f"dword ptr [{RS_SET:#x}]") == 7 and calls.count(f"dword ptr [{RS_GET:#x}]") == 3
    assert ins[-1].mnemonic == "jmp" and ins[-1].op_str == hex(DRAW)
    # every push balanced by an add esp (the cave returns to 0x16AFA8 with the caller's args untouched)
    assert site(CAVE)[0] == 0xE8 and len(site(CAVE)) == 5
    print(f"p6b_dualpass selftest OK ({len(code)} B)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    import hashlib
    import xbe_patch as xp
    xbe = XBE.read_bytes()
    assert hashlib.sha1(xbe).hexdigest() == SHA1
    secs = xp.sections(xbe)
    stock_site = b"\xE8" + struct.pack("<i", DRAW - (SITE + 5))
    o = xp.va_to_offset(secs, SITE, 5)
    assert xbe[o:o + 5] == stock_site, xbe[o:o + 5].hex()
    code = build(CAVE)
    oc = xp.va_to_offset(secs, CAVE, len(code))
    out = {"name": "P6b building-pipe dual pass (PS2 alpha test: fail = colour only, no Z)",
           "requires": ["p2_filterblur"],
           "patches": [
               {"va": hex(SITE), "orig_sha1": hashlib.sha1(stock_site).hexdigest(), "new": site(CAVE).hex(),
                "note": "mesh helper 0x16AD9A: call 0x2A0F00 (flush + DrawIndexedVertices) -> call dual-pass cave"},
               {"va": hex(CAVE), "orig_sha1": hashlib.sha1(xbe[oc:oc + len(code)]).hexdigest(), "new": code.hex(),
                "note": "dual pass: GEQUAL 128 with Z, then LESS 128 without Z write, if alpha test and blend are on"}]}
    print(f"wrote {write_json(__file__, out).name} ({len(code)} B cave)")
