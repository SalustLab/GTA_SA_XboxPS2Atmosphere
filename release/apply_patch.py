"""PS2 Atmosphere installer for GTA San Andreas (Xbox, USA or Europe, Rev 1 or Rev 0).

Patches default.xbe with "GTA SA (<region>) Rev <n>/default.xbe.xdelta" (USA or Europe, Rev 1 or Rev 0), picked by its SHA1.
That is the whole mod: since v1.1 the PS2 stream.ini settings are built into default.xbe, so stream.ini stays
untouched.

Usage:
    py apply_patch.py <game folder | image.iso>  [--xdelta path\\to\\xdelta3.exe]
    py apply_patch.py --selftest

A game folder must hold default.xbe; an .iso / .xiso is patched in place.
Either way the original is kept as *.bak first (an existing .bak is never replaced).
Any input other than the USA or Europe Rev 1 or Rev 0 default.xbe is refused and nothing is written.
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))  # repo layout: xdvdfs_extract.py sits one level up
from xdvdfs_extract import SECTOR, image_files  # noqa: E402

XBE = {  # stock default.xbe SHA1 -> (patched SHA1, xdelta file)
    "10efb868f13d6944aa6684a52cac5156393f14c5": ("84e14eef41e0e83d7191a66973c99959815d7553", "GTA SA (USA) Rev 1/default.xbe.xdelta"),  # USA Rev 1
    "1ceae5be753b3675ce8c5c79d7f496dfc0ad597d": ("6883102c897eaa58e8e01fb41a51b9c4b44b481d", "GTA SA (USA) Rev 0/default.xbe.xdelta"),  # USA Rev 0
    "f0ed7d693c5b9b579ffef38cf40ae0efae6a71d3": ("d4b4a593033690afcf298073e2a2eafac07eb15d", "GTA SA (Europe) Rev 1/default.xbe.xdelta"),  # Europe Rev 1
    "7a424b08e79a4feba39ec8acf2168c6c94bc0b5a": ("acd8ea4a872186adf7e67e6f9e1aec5340bbf346", "GTA SA (Europe) Rev 0/default.xbe.xdelta"),  # Europe Rev 0
}
OLDER = {"2d1829b5647f05930290d6e56425a4b656b8937b": "PS2 Atmosphere v1.0"}


def sha1(data):
    return hashlib.sha1(data).hexdigest()


def find_xdelta(arg):
    found = [arg] if arg else glob.glob(os.path.join(HERE, "xdelta3*")) + [shutil.which("xdelta3")]
    exe = next((p for p in found if p and os.path.isfile(p)), None)
    if not exe:
        raise SystemExit("xdelta3 not found: put xdelta3.exe next to this script or pass --xdelta <path>")
    return exe


def pick(have, table=XBE):
    """((stock, mod), xdelta file) for a stock or already-patched SHA1, else None."""
    for stock, (mod, patch) in table.items():
        if have in (stock, mod):
            return (stock, mod), patch
    return None


def xdelta_decode(exe, xbe, patch):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "in.xbe"), os.path.join(tmp, "out.xbe")
        with open(src, "wb") as f:
            f.write(xbe)
        subprocess.run([exe, "-d", "-f", "-s", src, os.path.join(HERE, patch), out], check=True)
        with open(out, "rb") as f:
            return f.read()


def backup(path):
    """Copy path to path.bak once; the copy goes through .part so a failed copy never looks like a backup."""
    if not os.path.exists(path + ".bak"):
        shutil.copyfile(path, path + ".bak.part")
        os.replace(path + ".bak.part", path + ".bak")


def patched(name, data, hashes, fn):
    """New bytes for one file, None if it is already patched; exits on any mismatch."""
    stock, mod = hashes
    have = sha1(data)
    if have == mod:
        print(f"{name}: already patched")
        return None
    if have in OLDER:
        raise SystemExit(f"{name} is {OLDER[have]}: put the original back (default.xbe.bak) and run again; nothing written")
    if have != stock:
        raise SystemExit(f"{name}: SHA1 {have} is not GTA SA USA / Europe Rev 1 or Rev 0 ({', '.join(XBE)}); nothing written")
    new = fn(data)
    if sha1(new) != mod or len(new) != len(data):
        raise SystemExit(f"{name}: patch result has SHA1 {sha1(new)}, expected {mod}; nothing written")
    return new


def run(target, exe):
    name = "default.xbe"

    def patch_xbe(data):
        hashes, patch = pick(sha1(data)) or (("", ""), None)   # unknown input: patched() refuses it
        return patched(name, data, hashes, lambda d: xdelta_decode(exe, d, patch))

    if os.path.isdir(target):
        path = os.path.join(target, name)
        with open(path, "rb") as f:
            new = patch_xbe(f.read())
        if new is not None:
            backup(path)
            with open(path, "wb") as f:
                f.write(new)
            print(f"patched {path}")
        return
    with open(target, "rb") as f:
        base, files = image_files(f)
        where = {path.lower(): (base + start * SECTOR, size) for path, start, size in files}
        if name not in where:
            raise SystemExit(f"{name} not found at the image root; nothing written")
        off, size = where[name]
        f.seek(off)
        old = f.read(size)
    new = patch_xbe(old)  # same length as old, so it fits in place
    if new is None:
        return
    print(f"backing up {target} -> {target}.bak (needs as much free space as the image)")
    backup(target)
    with open(target, "r+b") as f:
        f.seek(off)
        f.write(new)
    print(f"patched {name} inside {target}")


def selftest():
    h = (sha1(b"stock"), sha1(b"mod!!"))
    assert patched("t", b"stock", h, lambda d: b"mod!!") == b"mod!!"
    assert patched("t", b"mod!!", h, lambda d: 1 / 0) is None            # already patched: fn not called
    OLDER[sha1(b"old!!")] = "test v0"
    for data, fn in ((b"other", lambda d: b"mod!!"),                      # wrong input
                     (b"old!!", lambda d: b"mod!!"),                      # an older release
                     (b"stock", lambda d: b"bad!!")):                     # wrong result
        try:
            patched("t", data, h, fn)
            raise AssertionError("not refused")
        except SystemExit:
            pass
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "game.iso")
        for content in (b"stock", b"mod!!"):
            with open(p, "wb") as f:
                f.write(content)
            backup(p)
        with open(p + ".bak", "rb") as f:
            assert f.read() == b"stock"                                   # an existing backup is never replaced
        assert os.listdir(tmp) == ["game.iso", "game.iso.bak"]            # no .part left behind
    assert pick(sha1(b"x"), {sha1(b"x"): ("m", "a.xdelta")}) == ((sha1(b"x"), "m"), "a.xdelta")
    assert pick("m", {sha1(b"x"): ("m", "a.xdelta")})[1] == "a.xdelta"               # an already-patched file
    assert pick("zz", {sha1(b"x"): ("m", "a.xdelta")}) is None                       # unknown: patched() refuses
    assert {pick(s)[1] for s in XBE} == {f"GTA SA ({r}) Rev {n}/default.xbe.xdelta" for r in ("USA", "Europe") for n in (1, 0)}
    print("apply_patch selftest OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args in ([], ["--selftest"]):
        selftest()
    else:
        exe = args[args.index("--xdelta") + 1] if "--xdelta" in args else None
        run(args[0], find_xdelta(exe))
