"""P5 - neutral display gamma at the default brightness (findings 2026-09-24, "Gamma fix test").

SetBrightness(b) 0x274662, b = menu int [0x6E79AC] / 512, builds the display ramp
  exp = 1.0 - 0.7*b + C,   ramp[i] = trunc(pow((i+1)/256, exp) * 255)
C is read by `addss xmm0, [0x390A24]` at 0x27468E. 0x390A24 is the compiler's pooled float 0.2 (~335 references
game-wide), so it must NOT be edited. P5 repoints that one operand to an existing read-only .rdata float 0.35
(0x390C44): C = 0.35 makes the default 256 the identity ramp (stock 0.2 gives exp 0.85, which brightens; PS2
matches the Xbox framebuffer with no ramp). The slider still works (exp = 1.35 - 0.7*b).

Usage: py patches/p5_display_gamma.py [--selftest]      -> writes patches/p5_display_gamma.json
"""
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import XBE, A, offset, write_json  # noqa: E402  (--rev0|--eu1|--eu0: Rev 1 VAs below are mapped)

INSN, OLD, NEW = A(0x27468E), A(0x390A24), A(0x390C44)   # addss xmm0, dword ptr [OLD]  (F3 0F 58 05 imm32)
STOCK, FIXED = 0.2, 0.35


def f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def ramp(c, brightness=256):
    """The game's loop at 0x2746AA with float32 constants (x87 math is close enough for a trunc check)."""
    e = f32(1.0) - f32(f32(0.7) * f32(brightness * f32(1 / 512))) + f32(c)
    return [int(((i + 1) * f32(0.00390625)) ** e * 255) for i in range(256)]


def selftest():
    pts = (0, 32, 64, 128, 192, 255)
    assert [ramp(STOCK)[i] for i in pts] == [2, 44, 79, 142, 200, 255]        # live ramp at 256, stock
    assert [ramp(STOCK, 384)[i] for i in pts] == [6, 63, 101, 160, 210, 255]   # live ramp of the Ryder save
    assert ramp(FIXED) == list(range(256))                                     # live: exact identity
    print("p5_display_gamma selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit()
    xbe = XBE.read_bytes()
    op = INSN + 4
    insn = xbe[INSN - 0x10000:INSN - 0x10000 + 8]
    assert insn == bytes.fromhex("f30f5805") + struct.pack("<I", OLD), insn.hex()
    assert xbe[offset(xbe, NEW, 4):offset(xbe, NEW, 4) + 4] == struct.pack("<f", FIXED)
    orig = insn[4:]
    out = {"name": "P5 neutral display gamma at default brightness (SetBrightness reads 0.35, not pooled 0.2)",
           "patches": [{"va": hex(op), "orig_sha1": hashlib.sha1(orig).hexdigest(), "len": 4,
                        "new": struct.pack("<I", NEW).hex(),
                        "note": "addss operand at 0x27468E: [0x390A24] 0.2 -> [0x390C44] 0.35 (read-only .rdata)"}]}
    print(f"wrote {write_json(__file__, out).name}")
