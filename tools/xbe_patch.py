"""Apply patches/*.json to a copy of GTA SA Xbox default.xbe (USA Rev 1; USA Rev 0 / Europe Rev 1 / Europe Rev 0
with the *.rev0.json / *.eu1.json / *.eu0.json builds).

Usage:
  py tools/xbe_patch.py <in.xbe> <out.xbe> <patch.json> [patch.json ...]
  py tools/xbe_patch.py --selftest

Patch JSON:
  {"name": "P1 ColourFilter", "patches": [
     {"va": "0x24F007", "orig": "55 8B EC", "new": "90 90 90", "note": "..."}]}
  "orig_sha1" (SHA1 of the original bytes, same length as "new") may replace "orig", so
  committed patch files carry no Rockstar bytes. An optional top-level "requires": ["p2_filterblur"]
  names patch files (by stem) that must be applied in the same run (e.g. code placed in bytes another
  patch makes dead). "xbe_sha1" names the input the file was built for (absent = Rev 1); all files in
  one run must agree, and the input must have that SHA1.

VAs are mapped to file offsets through the XBE section headers. The tool refuses:
wrong input SHA1, a VA outside a section's raw data (BSS), overlapping entries,
orig/new length mismatch, any original-byte mismatch, and writing over the input
or into the original game folders. Every orig is checked against the pristine
input, so the result does not depend on patch order.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

REV1_SHA1 = "10efb868f13d6944aa6684a52cac5156393f14c5"
REV0_SHA1 = "1ceae5be753b3675ce8c5c79d7f496dfc0ad597d"
EU1_SHA1 = "f0ed7d693c5b9b579ffef38cf40ae0efae6a71d3"
EU0_SHA1 = "7a424b08e79a4feba39ec8acf2168c6c94bc0b5a"
TARGETS = {REV1_SHA1: "USA Rev 1", REV0_SHA1: "USA Rev 0", EU1_SHA1: "Europe Rev 1", EU0_SHA1: "Europe Rev 0"}
ORIGINAL_DIRS = ("Microsoft - Xbox", "Sony - PlayStation 2")


def sections(xbe):
    base, = struct.unpack_from("<I", xbe, 0x104)
    count, hdr = struct.unpack_from("<II", xbe, 0x11C)
    out = []
    for i in range(count):
        _, va, _, raw, raw_size, _ = struct.unpack_from("<6I", xbe, hdr - base + i * 56)
        out.append((va, raw, raw_size))
    return out


def va_to_offset(secs, va, length):
    for sva, raw, raw_size in secs:
        if sva <= va and va + length <= sva + raw_size:
            return va - sva + raw
    raise ValueError(f"VA {va:#x}+{length} is not inside any section's file data (BSS or unmapped)")


def check_requires(docs):
    """docs = [(file stem, parsed JSON)]. A patch may list the stems of patches it depends on in "requires"."""
    stems = {s for s, _ in docs}
    for s, j in docs:
        missing = [r for r in j.get("requires", []) if r not in stems]
        if missing:
            raise ValueError(f"{s} requires {', '.join(missing)} in the same run")


def target_sha1(docs):
    """The one input SHA1 all patch files were built for: "xbe_sha1" (non-Rev 1 builds), absent = Rev 1."""
    want = {j.get("xbe_sha1", REV1_SHA1).lower() for _, j in docs}
    if len(want) != 1 or not want <= TARGETS.keys():
        raise ValueError(f"patch files target {sorted(want)}: all must be built for one known default.xbe")
    return want.pop()


def load_entries(paths):
    entries = []
    docs = [(Path(p).stem, json.loads(Path(p).read_text())) for p in paths]
    check_requires(docs)
    sha1 = target_sha1(docs)
    for p, (_, j) in zip(paths, docs):
        for e in j["patches"]:
            new = bytes.fromhex(e["new"])
            orig = e["orig_sha1"].lower() if "orig_sha1" in e else bytes.fromhex(e["orig"])
            if not new or (isinstance(orig, bytes) and len(orig) != len(new)):
                raise ValueError(f"{p}: {e['va']}: orig/new must be non-empty and equal length")
            entries.append((int(e["va"], 16), orig, new, str(p)))
    return entries, sha1


def apply(xbe, entries, expected_sha1=REV1_SHA1):
    got = hashlib.sha1(xbe).hexdigest()
    if got != expected_sha1:
        raise ValueError(f"input SHA1 {got} is not default.xbe {TARGETS.get(expected_sha1, '?')} ({expected_sha1})")
    secs = sections(xbe)
    out = bytearray(xbe)
    ranges = []
    for va, orig, new, src in entries:
        off = va_to_offset(secs, va, len(new))
        for a, b, other in ranges:
            if off < b and a < off + len(new):
                raise ValueError(f"{src}: VA {va:#x} overlaps a patch from {other}")
        ranges.append((off, off + len(new), src))
        have = xbe[off:off + len(new)]
        if (hashlib.sha1(have).hexdigest() if isinstance(orig, str) else have) != orig:
            raise ValueError(f"{src}: VA {va:#x} original bytes mismatch (have sha1 {hashlib.sha1(have).hexdigest()})")
        out[off:off + len(new)] = new
    return bytes(out)


def main(argv):
    src, dst, *patch_files = argv
    src, dst = Path(src).resolve(), Path(dst).resolve()
    if dst == src or any(d in dst.parts for d in ORIGINAL_DIRS):
        raise SystemExit(f"refusing to write {dst}: never overwrite the input or the originals")
    out = apply(src.read_bytes(), *load_entries(patch_files))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(out)
    print(f"wrote {dst} sha1={hashlib.sha1(out).hexdigest()}")


def selftest():
    # Synthetic XBE: base 0x10000, one section va 0x11000 -> raw 0x1000, 0x10 raw bytes, larger vsize (BSS tail).
    x = bytearray(0x1010)
    struct.pack_into("<I", x, 0x104, 0x10000)
    struct.pack_into("<II", x, 0x11C, 1, 0x10200)
    struct.pack_into("<6I", x, 0x200, 0, 0x11000, 0x100, 0x1000, 0x10, 0)
    x[0x1000:0x1010] = bytes(range(0x10))
    x = bytes(x)
    sha = hashlib.sha1(x).hexdigest()

    def refused(entries, sha1=sha):
        try:
            apply(x, entries, sha1)
        except ValueError:
            return True
        return False

    out = apply(x, [(0x11002, b"\x02\x03", b"\x90\x90", "t")], sha)
    assert out[0x1002:0x1004] == b"\x90\x90" and out[:0x1002] == x[:0x1002] and out[0x1004:] == x[0x1004:]
    assert refused([(0x11002, b"\x02\x03", b"\x90\x90", "t")], REV1_SHA1)      # wrong hash
    assert refused([(0x11002, b"\xFF\x03", b"\x90\x90", "t")])                 # orig mismatch
    assert refused([(0x1100F, b"\x0F\x00", b"\x90\x90", "t")])                 # runs into BSS
    assert apply(x, [(0x11002, hashlib.sha1(b"\x02\x03").hexdigest(), b"\x90\x90", "t")], sha)[0x1002:0x1004] == b"\x90\x90"
    assert refused([(0x11002, hashlib.sha1(b"\xFF\x03").hexdigest(), b"\x90\x90", "t")])   # orig_sha1 mismatch
    assert refused([(0x11002, b"\x02\x03", b"\x90\x90", "a"),
                    (0x11003, b"\x03", b"\x90", "b")])                        # overlap
    check_requires([("p2", {}), ("p6b", {"requires": ["p2"]})])
    try:
        check_requires([("p6b", {"requires": ["p2"]})])                       # dependency missing
        raise AssertionError("missing requirement accepted")
    except ValueError:
        pass
    assert target_sha1([("p1", {}), ("p2", {})]) == REV1_SHA1                  # no field = Rev 1 (old JSONs)
    assert target_sha1([("p1.rev0", {"xbe_sha1": REV0_SHA1})]) == REV0_SHA1
    assert target_sha1([("p1.eu1", {"xbe_sha1": EU1_SHA1}), ("p2.eu1", {"xbe_sha1": EU1_SHA1})]) == EU1_SHA1
    for bad in ([("p1", {}), ("p2.rev0", {"xbe_sha1": REV0_SHA1})],              # Rev 1 and Rev 0 patches mixed
                [("p1", {}), ("p2.eu1", {"xbe_sha1": EU1_SHA1})],                # USA and Europe mixed
                [("p1.eu1", {"xbe_sha1": EU1_SHA1}), ("p2.eu0", {"xbe_sha1": EU0_SHA1})],
                [("x", {"xbe_sha1": "00" * 20})]):                               # unknown target
        try:
            target_sha1(bad)
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass
    print("xbe_patch selftest OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"] or not sys.argv[1:]:
        selftest()
    elif len(sys.argv) < 4:
        raise SystemExit(__doc__)
    else:
        main(sys.argv[1:])
