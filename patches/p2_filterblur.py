"""P2 - PS2 colour-filter blur (PLAN §9 P2): P1's PS2 formula with pass 2 sampling fb' through LINEAR at +pe/16 texels.

  out = clip(fb*2c1) + clip(fb'*2c2) * a2,   fb' = fb bilinear-sampled at +pe/16 texels (pe_leftx..bottomy: PS2 8)

P1 + blur is 439 B and does not fit P1's 300 B slot, so P2 is self-contained and replaces P1 (apply p2 + p5, never
p1 + p2; xbe_patch refuses the overlap at 0x24F007):
  - 0x24ECAA  the Xbox blur pass (504 B, only caller 0x24CC89) becomes the new ColourFilter body;
  - 0x24CC89  that call -> NOP (same as P1's blur byte = 0: the pass then returns with no side effect);
  - 0x24F007  jmp 0x24ECAA (every ColourFilter caller lands in the new body, stack/ABI unchanged).
The pass-2 UVs are shifted on a stack copy of the quad 0x5C7318, so the persistent quad is never modified.
With the Xbox ini value 16 the shift is a full texel (sharp, 1 px); ship pe_* 8 for the PS2 blur.

Usage: py patches/p2_filterblur.py [--selftest]      -> writes patches/p2_filterblur.json
"""
import hashlib
import json
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from keystone import KS_ARCH_X86, KS_MODE_32, Ks

sys.path.insert(0, str(Path(__file__).parent))
from p1_colourfilter import START as FILTER, XBE, build  # noqa: E402
from rev0_map import SUFFIX, A, write_json  # noqa: E402  (p1 put tools/ on sys.path)

CAVE, CAVE_END = A(0x24ECAA), A(0x24EEA2)        # Xbox blur pass, ret at 0x24EEA1
BLUR_CALL = A(0x24CC89)                       # call 0x24ECAA, the only reference to the cave [C]


def patches(xbe):
    def at(va, n):
        return xbe[va - 0x10000:va - 0x10000 + n]

    assert at(BLUR_CALL, 5) == b"\xe8" + (CAVE - BLUR_CALL - 5).to_bytes(4, "little"), "blur call site moved"
    body, _ = build(blur=True, start=CAVE, end=CAVE_END)
    jmp = bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(f"jmp {CAVE:#x}", FILTER)[0])
    out = []
    for va, new, note in ((FILTER, jmp, "CPostEffects::ColourFilter -> new body in the cave"),
                          (BLUR_CALL, b"\x90" * 5, "Xbox blur pass call -> NOP (cave reused)"),
                          (CAVE, body, "ColourFilter PS2 formula + LINEAR pass 2 at +pe/16 texels (P1 + P2)")):
        orig = at(va, len(new))
        out.append({"va": hex(va), "orig_sha1": hashlib.sha1(orig).hexdigest(), "len": len(orig),
                    "new": new.hex(), "note": note})
    return out, body


def selftest():
    body, _ = build(blur=True, start=CAVE, end=CAVE_END)
    code = body.rstrip(b"\xcc")
    assert len(code) <= CAVE_END - CAVE
    # the 8 UV writes must hit the SkyGfx corners on the stack copy (quad at esp+8, stride 28, u +0x14, v +0x18)
    uv = lambda n, c: 8 + n * 28 + c
    want = [uv(0, 0x14), uv(1, 0x14), uv(0, 0x18), uv(3, 0x18), uv(2, 0x14), uv(3, 0x14), uv(1, 0x18), uv(2, 0x18)]
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, CAVE))
    got = [int(i.op_str.split("+ ")[1].rstrip("]"), 16) for i in ins if i.mnemonic == "fstp"]
    assert got == want, (got, want)
    offs = [i.op_str for i in ins if i.mnemonic == "fild"]
    assert offs == [f"dword ptr [{A(0x3CE808) + 4 * a:#x}]" for a in range(4)], offs
    p1 = json.loads(Path(__file__).with_name(f"p1_colourfilter{SUFFIX}.json").read_text())["patches"][0]["new"]
    assert build()[0].hex() == p1, "blur=False must keep the v0.1 P1 bytes"
    print("p2_filterblur selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    entries, body = patches(XBE.read_bytes())
    out = {"name": "P2 ColourFilter PS2 formula + blur (supersedes P1; apply with P5, not with P1)", "patches": entries}
    path = write_json(__file__, out)
    print(f"{len(body.rstrip(bytes([0xcc])))} code bytes / {len(body)}; wrote {path.name}")
