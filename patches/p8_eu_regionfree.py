"""P8 - Europe builds only: drop the game's own EEPROM region check, so the Europe disc runs on any console region
(findings 2026-10-20, "Europe Rev 1 / Rev 0 port").

The RW skeleton main (Rev 1 0x273xxx) does `call XGetGameRegion; cmp eax, <own region>; jne exit` right after the
camera is created, and quits to the dashboard silently on a mismatch. XGetGameRegion (Rev 1 0x27872D) is
XQueryValue(0x104 = XC_FACTORY_GAME_REGION), i.e. the EEPROM, not the XBE certificate. USA compares with esi = 1
(`3B C6`), Europe with `83 F8 04`; P8 NOPs the Europe 6-byte `jne`. Tested in xemu with an NA EEPROM and on real
hardware (NTSC console, Cerbios + XBMC4Gamers). USA builds are left alone.

Usage: py patches/p8_eu_regionfree.py --eu1|--eu0      -> writes patches/p8_eu_regionfree.eu1.json / .eu0.json
"""
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rev0_map import REV, XBE, A, write_json  # noqa: E402  (--eu1|--eu0: Rev 1 VAs below are mapped)

if REV not in ("eu1", "eu0"):
    raise SystemExit("P8 is for the Europe builds only: run with --eu1 or --eu0")
CALL, GET_REGION = A(0x273CCF), A(0x27872D)      # call XGetGameRegion in main; the function itself
JNE = CALL + 8                                   # after `cmp eax, 4` (3 B); Rev 1's `cmp eax, esi` is 2 B

xbe = XBE.read_bytes()
site = xbe[CALL - 0x10000:JNE - 0x10000 + 6]      # .text file offset = VA - 0x10000
rel = struct.unpack_from("<i", site, 1)[0]
assert site[0] == 0xE8 and CALL + 5 + rel == GET_REGION, site.hex()
assert site[5:10] == bytes.fromhex("83f8040f85"), site.hex()          # cmp eax, 4 (Europe); jne rel32
assert xbe[GET_REGION - 0x10000:GET_REGION - 0x10000 + 22].endswith(bytes.fromhex("6804010000")), "not XQueryValue(0x104)"
orig = site[8:]
out = {"name": "P8 Europe region-free (the game's XGetGameRegion() == 4 check after camera init is dropped)",
       "patches": [{"va": hex(JNE), "orig_sha1": hashlib.sha1(orig).hexdigest(), "len": 6, "new": "90" * 6,
                    "note": "main: call XGetGameRegion; cmp eax, 4; jne exit -> NOP the jne (Rev 1 site 0x273CD6)"}]}
print(f"wrote {write_json(__file__, out).name} (jne at {JNE:#x})")
