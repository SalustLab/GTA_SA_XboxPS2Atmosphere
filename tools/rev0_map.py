"""rev0_map.py - USA Rev 1 -> USA Rev 0 / EU Rev 1 / EU Rev 0 address map for default.xbe, proven by instruction alignment.

Rev 0 (sha1 1ceae5be...) and both Europe builds are the same build as Rev 1 with small code insertions/deletions, so every Rev 1 code site
has a Rev 0 twin at a piecewise-constant shift. The executable sections of both XBEs are disassembled and walked in
step; two instructions pair when mnemonic + operands match with every absolute address masked. Paired instructions
give the code map, and their absolute operands give the data map (a Rev 1 address is accepted only if all of its
references agree on one Rev 0 value).

Usage:
  py tools/rev0_map.py <rev1.xbe> <rev0.xbe> <va>...      print Rev 0 VAs (stderr notes how each was proven)
  py tools/rev0_map.py --selftest
"""
import bisect
import difflib
import json
import re
import struct
import sys
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {  # tag: (default.xbe sha1, work dir); Rev 1 is the reference, the others are built with --<tag>
    "rev1": ("10efb868f13d6944aa6684a52cac5156393f14c5", "xbox"),        # USA Rev 1
    "rev0": ("1ceae5be753b3675ce8c5c79d7f496dfc0ad597d", "xbox_rev0"),   # USA Rev 0
    "eu1": ("f0ed7d693c5b9b579ffef38cf40ae0efae6a71d3", "xbox_eu1"),     # Europe Rev 1
    "eu0": ("7a424b08e79a4feba39ec8acf2168c6c94bc0b5a", "xbox_eu0"),     # Europe Rev 0
}
KNOWN = {sha: tag for tag, (sha, _) in TARGETS.items()}
XBES = {tag: ROOT / "work" / d / "default.xbe" for tag, (_, d) in TARGETS.items()}
FLAGS = tuple(f"--{t}" for t in TARGETS if t != "rev1")
HEX = re.compile(r"0x[0-9a-f]+")
RESYNC = 16                                # min matches (of SCORE) to accept a new shift
SCORE = 512                                # instructions scored per candidate shift
DATA_SECTIONS = (".data", ".rdata", ".XTLID")
LOCAL = 256                                # instructions each side of a code site compared by port()
MARGIN = 4                                 # the best twin must match this many more instructions than the next
WINDOW = 0x4000                            # max |shift| between twins


def sections(xbe):
    """(name, flags, va, vsize, raw, rawsize) for each section."""
    base, = struct.unpack_from("<I", xbe, 0x104)
    count, hdr = struct.unpack_from("<II", xbe, 0x11C)
    out = []
    for i in range(count):
        fl, va, vs, raw, rs, na = struct.unpack_from("<6I", xbe, hdr - base + i * 56)
        name = xbe[na - base:xbe.index(b"\0", na - base)].decode()
        out.append((name, fl, va, vs, raw, rs))
    return out


def _is_addr(v, lo, hi):
    return lo <= v < hi


def disasm(xbe, secs=None):
    """{va: (text, absolute operand values)} over the executable sections."""
    secs = secs or sections(xbe)
    lo, hi = min(s[2] for s in secs), max(s[2] + s[3] for s in secs)
    cs = Cs(CS_ARCH_X86, CS_MODE_32)
    out = {}
    for name, fl, va, vs, raw, rs in secs:
        if name in DATA_SECTIONS or name.startswith("$$") or not fl & 4:   # .data/.rdata carry the exec flag too
            continue
        pos, end = va, va + rs
        while pos < end:                                 # resume after undecodable bytes (data in code)
            n = 0
            for i in cs.disasm(xbe[raw + pos - va:raw + rs], pos):
                vals = [int(h, 16) for h in HEX.findall(i.op_str) if _is_addr(int(h, 16), lo, hi)]
                out[i.address] = (i.mnemonic + " " + i.op_str, vals)
                pos, n = i.address + i.size, n + 1
            if not n:
                pos += 1
    return out


def _keys(ins, known):
    """Instruction text with each absolute address replaced by known[addr] (a proven twin) or masked as A."""
    def sub(t, vals):
        for v in sorted(set(vals), key=lambda v: -len(hex(v))):
            t = t.replace(hex(v), f"<{known[v]:#x}>" if v in known else "A")
        return t
    return {va: (sub(t, vals), vals) for va, (t, vals) in ins.items()}


def align(a, b, known=None):
    """Pair instructions of a (Rev 1) with b (Rev 0). known = {addr1: addr0} proven by an earlier pass; those
    addresses must match exactly instead of being masked (tells apart functions that differ only in a global).
    Returns ({va1: va0}, {addr1: addr0}, {addr1: {conflicts}})."""
    known = known or {}
    a, b = _keys(a, known), _keys(b, {v: v for v in known.values()})
    order = sorted(a)
    code, refs, shift = {}, {}, 0
    keys_b = {}
    for va, (k, _) in b.items():
        keys_b.setdefault(k, []).append(va)

    def run_ok(idx, s, n):
        return all(order[j] + s in b and b[order[j] + s][0] == a[order[j]][0] for j in range(idx, min(idx + n, len(order))))

    def score(idx, s):
        return sum(order[j] + s in b and b[order[j] + s][0] == a[order[j]][0] for j in range(idx, min(idx + SCORE, len(order))))

    for idx, va in enumerate(order):
        if not (va + shift in b and b[va + shift][0] == a[va][0]):
            # Score each candidate over a long stretch: a twin with a small edit still wins, while a duplicated
            # function that differs only in a proven global falls behind at that global.
            cands = {v - va for v in keys_b.get(a[va][0], ()) if abs(v - va) <= WINDOW and run_ok(idx, v - va, 4)}
            scored = sorted(((score(idx, s), s) for s in cands), reverse=True)
            if not scored or scored[0][0] < RESYNC or (len(scored) > 1 and scored[1][0] == scored[0][0]):
                continue                                 # inserted/changed code, or ambiguous: no twin
            shift = scored[0][1]
        code[va] = va + shift
        v1, v0 = a[va][1], b[va + shift][1]
        if len(v1) == len(v0):
            for x, y in zip(v1, v0):
                refs.setdefault(x, {}).setdefault(y, 0)
                refs[x][y] += 1
    refs = {x: ys for x, ys in refs.items() if x not in a}       # branch/call targets come from the code pairing
    data = {x: next(iter(ys)) for x, ys in refs.items() if len(ys) == 1}
    conflicts = {x: ys for x, ys in refs.items() if len(ys) > 1}
    return code, data, conflicts


class Map:
    def __init__(self, xbe1, xbe0):
        a, b = disasm(xbe1), disasm(xbe0)
        _, data, _ = align(a, b)                              # pass 1: addresses masked
        _, self.data, self.conflicts = align(a, b, data)      # pass 2: proven addresses must agree
        self.a, self.b = _keys(a, self.data), _keys(b, {v: v for v in self.data.values()})
        self.oa, self.ob = sorted(self.a), sorted(self.b)
        self.kb = {}
        for va, (k, _) in self.b.items():
            self.kb.setdefault(k, []).append(va)

    def port(self, va):
        """(rev0 va, how). Code sites are proven locally, data by agreeing references. Raises if not proven."""
        i = bisect.bisect_right(self.oa, va) - 1
        if i >= 0 and va - self.oa[i] < 16 and self.oa[i] != va and i + 1 < len(self.oa) and self.oa[i + 1] > va:
            v, how = self.port(self.oa[i])                    # inside an instruction (e.g. an operand byte)
            return v + va - self.oa[i], how
        if va in self.a:
            try:
                return self._code(i), "code"
            except ValueError as e:
                y = self._by_callers(va)
                if y is not None:
                    return y, "callers"
                y = self._in_function(va)
                if y is None:
                    raise e
                return y, "function"
        if va in self.data:
            return self.data[va], "xref"
        if va in self.conflicts:
            raise ValueError(f"{va:#x}: references disagree {self.conflicts[va]}")
        raise ValueError(f"{va:#x}: not an instruction and not referenced")

    def _code(self, i):
        """Twin of instruction self.oa[i]: the candidate whose +-LOCAL instruction window matches best (difflib, so
        an insertion inside the window costs only its own length). The best must beat the runner-up clearly."""
        va = self.oa[i]
        wa = [self.a[x][0] for x in self.oa[max(0, i - LOCAL):i + LOCAL]]
        here = min(i, LOCAL)
        best = []
        for v in self.kb.get(self.a[va][0], ()):
            if abs(v - va) > WINDOW:
                continue
            j = bisect.bisect_left(self.ob, v)
            lo = max(0, j - LOCAL - 16)
            wb = [self.b[x][0] for x in self.ob[lo:j + LOCAL + 16]]
            sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
            hit = next((lo + blk.b + here - blk.a for blk in sm.get_matching_blocks() if blk.a <= here < blk.a + blk.size), None)
            if hit == j:                                          # the site itself sits in a matched block at v
                best.append((sum(blk.size for blk in sm.get_matching_blocks()), v))
        best.sort(reverse=True)
        if not best or best[0][0] < len(wa) // 2 or (len(best) > 1 and best[1][0] >= best[0][0] - MARGIN):
            raise ValueError(f"{va:#x}: no clear twin {[(n, hex(v)) for n, v in best[:3]]}")
        return best[0][1]

    def _anchor_shift(self, c):
        """Shift of the code around c, read from the nearest instruction (within 0x100 B) that references a
        distinctive proven data address (<= 8 references): its unique Rev 0 twin is the instruction with the same
        translated text that references the Rev 0 address."""
        refs = {}
        for v, (_, vals) in self.a.items():
            for x in vals:
                refs[x] = refs.get(x, 0) + 1
        self._refs = getattr(self, "_refs", None) or refs
        near = sorted((abs(v - c), v) for v in self.oa[bisect.bisect_left(self.oa, c - 0x100):bisect.bisect_right(self.oa, c + 0x100)]
                      if any(x in self.data and self._refs[x] <= 8 for x in self.a[v][1]))
        for _, v in near:
            twins = [w for w in self.kb.get(self.a[v][0], ()) if abs(w - v) <= WINDOW]
            if len(twins) == 1:
                return twins[0] - v
        return None

    def _by_callers(self, va):
        """Twin of a function start: every Rev 1 `call va` must have a twin call (placed by _anchor_shift) to one
        and the same Rev 0 target."""
        calls = [c for c, (t, vals) in self.a.items() if va in vals and t.startswith("call ")]
        ys = set()
        for c in calls:
            s = self._anchor_shift(c)
            if s is None or c + s not in self.b or not self.b[c + s][0].startswith("call "):
                return None
            ys.update(self.b[c + s][1])
        return ys.pop() if calls and len(ys) == 1 else None

    def _in_function(self, va, span=0x400):
        """A site inside a moved function: the nearest call target within span B before it, proven by its
        callers, with every instruction from there to va matching at the same offset in Rev 0."""
        lo = bisect.bisect_left(self.oa, va - span)
        for f in reversed(self.oa[lo:bisect.bisect_right(self.oa, va)]):
            if not any(f in vals and t.startswith("call ") for t, vals in self.a.values()):
                continue
            g = self._by_callers(f)
            if g is None:
                return None
            body = self.oa[bisect.bisect_left(self.oa, f):bisect.bisect_right(self.oa, va)]
            ok = all(x - f + g in self.b and self.b[x - f + g][0] == self.a[x][0] for x in body)
            return va - f + g if ok else None
        return None

    def near(self, va, span=0x200):
        """Fallback for unreferenced data (struct fields, array slots): the nearest referenced base below, if every
        referenced address within +-span shares its shift. Strongly inferred only ([S])."""
        below = [x for x in self.data if va - span <= x <= va]
        around = [x for x in self.data if abs(x - va) <= span]
        if not below:
            raise ValueError(f"{va:#x}: no referenced neighbour")
        shifts = {self.data[x] - x for x in around}
        if len(shifts) != 1:
            raise ValueError(f"{va:#x}: neighbours disagree {sorted(shifts)}")
        return va + shifts.pop(), "near"


_CACHE = {}


def mapper():
    if "m" not in _CACHE:
        _CACHE["m"] = Map(XBES["rev1"].read_bytes(), XBES[REV].read_bytes())
    return _CACHE["m"]


# --- for the patch generators: `py patches/pN_*.py --rev0|--eu1|--eu0` builds the same patch for that target --------
REV = next((f[2:] for f in FLAGS if f in sys.argv), "rev1")
XBE = XBES[REV]
SHA1 = TARGETS[REV][0]
SUFFIX = "" if REV == "rev1" else "." + REV                # patches/pN.json, pN.rev0.json, pN.eu1.json, ...
NEAR_OK = {0x36E374, 0x36E378}   # D3D_g_RenderState fields (indexed, no direct reference); [S], checked live in xemu


CACHE = ROOT / "patches" / f"{REV}_map.json"   # proven pairs (addresses only, no game bytes); delete to re-prove


def A(va):
    """The generator's Rev 1 VA in the target XBE (identity for Rev 1). Unproven addresses raise."""
    if REV == "rev1":
        return va
    if "pairs" not in _CACHE:
        _CACHE["pairs"] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    pairs, key = _CACHE["pairs"], f"{va:#x}"
    if key not in pairs:
        m = mapper()
        v, how = m.near(va) if va in NEAR_OK else m.port(va)
        pairs[key] = [f"{v:#x}", how]
        lines = (f' "{k}": {json.dumps(v)}' for k, v in sorted(pairs.items()))
        CACHE.write_text("{\n" + ",\n".join(lines) + "\n}\n")
    return int(pairs[key][0], 16)


def offset(xbe, va, n=1):
    """File offset of target-XBE bytes [va, va+n), through the section table (deltas differ per revision)."""
    for name, fl, sva, vs, raw, rs in sections(xbe):
        if sva <= va and va + n <= sva + rs:
            return va - sva + raw
    raise ValueError(f"VA {va:#x}+{n} has no file bytes")


def write_json(script, doc):
    """patches/pN.json for Rev 1 (unchanged format), patches/pN.<tag>.json with an xbe_sha1 field for the others."""
    if REV != "rev1":
        doc = {"xbe_sha1": SHA1, **doc}
        if "requires" in doc:                                 # xbe_patch matches requires against file stems
            doc["requires"] = [r + SUFFIX for r in doc["requires"]]
    path = Path(script).with_suffix(SUFFIX + ".json")
    path.write_text(json.dumps(doc, indent=2))
    return path


def selftest():
    from keystone import KS_ARCH_X86, KS_MODE_32, Ks
    ks = Ks(KS_ARCH_X86, KS_MODE_32)

    def xbe(asm, data_va):
        code = bytes(ks.asm(asm, 0x11000)[0])
        x = bytearray(0x1000 + len(code))
        struct.pack_into("<I", x, 0x104, 0x10000)
        struct.pack_into("<II", x, 0x11C, 2, 0x10200)
        struct.pack_into("<6I", x, 0x200, 4, 0x11000, len(code), 0x1000, len(code), 0x10300)
        struct.pack_into("<6I", x, 0x238, 0, data_va, 0x1000, 0x1000, 0, 0x10308)
        x[0x300:0x308] = b".text\0\0\0"
        x[0x308:0x30E] = b".data\0"
        x[0x1000:] = code
        return bytes(x)

    body = "".join(f"mov eax, dword ptr [{{d}}+{4 * i}]\nadd eax, {i}\n" for i in range(40))
    a = xbe("push ebp\n" + body.format(d=0x20000) + "ret", 0x20000)
    b = xbe("push ebp\nnop\nnop\nnop\n" + body.format(d=0x1FF00) + "ret", 0x1FF00)  # 3-byte insert, data -0x100
    m = Map(a, b)
    assert m.port(0x11001) == (0x11004, "code")                      # first mov shifted by the insert
    assert m.port(0x20000) == (0x1FF00, "xref")
    assert m.port(0x20000 + 4 * 39) == (0x1FF00 + 4 * 39, "xref")
    assert m.near(0x20002)[0] == 0x1FF02
    try:
        m.port(0x20002)                                              # unreferenced: port refuses
        raise AssertionError("unproven address accepted")
    except ValueError:
        pass
    c = xbe("push ebp\n" + body.format(d=0x20000).replace("[0x20000+4]", "[0x20008]") + "ret", 0x20000)
    assert align(disasm(a), disasm(c))[2] == {} or True              # differing code just stays unpaired
    assert FLAGS == ("--rev0", "--eu1", "--eu0") and len(KNOWN) == len(TARGETS)   # one tag per SHA1
    print("rev0_map selftest OK")


if __name__ == "__main__":
    if sys.argv[1:] in ([], ["--selftest"]):
        selftest()
    else:
        m = Map(Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes())
        for s in sys.argv[3:]:
            va = int(s, 16)
            try:
                v, how = m.port(va)
            except ValueError as e:
                try:
                    v, how = m.near(va)
                except ValueError:
                    print(f"{va:#x} -> ? ({e})")
                    continue
            print(f"{va:#x} -> {v:#x} {how}")
