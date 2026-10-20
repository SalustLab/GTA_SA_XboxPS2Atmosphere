"""Poke/read GTA SA (Xbox USA Rev 1; add --rev0 for USA Rev 0, --eu1 / --eu0 for Europe Rev 1 / Rev 0) state in xemu through its GDB stub (start xemu with -s, port 1234).

Usage:
  py tools/xemu_gdb.py clock <hour> <minute>        set + freeze the clock
  py tools/xemu_gdb.py weather <id>                 Old=New=Forced=id (gta-reversed eWeatherType)
  py tools/xemu_gdb.py postfx on|off                PostFX disable-all byte 0x5F4B1F
  py tools/xemu_gdb.py filter                       print c1/c2 at 0x6C88B8 (predict_filter.py args)
  py tools/xemu_gdb.py teleport <x> <y> <z> [heading_rad]
  py tools/xemu_gdb.py timescale <f>                CTimer::ms_fTimeScale; 0 freezes the world, rendering continues
  py tools/xemu_gdb.py idlecam off|on               CIdleCam kick-in time 1e30 / stock 90000 ms (idle pan + HUD hide)
  py tools/xemu_gdb.py capture <out.png>            PrintWindow of the xemu window (works when covered), 2x box-reduced
  py tools/xemu_gdb.py --cxbx <command ...>         same commands on Cxbx-Reloaded via process memory (no filterargs)
  py tools/xemu_gdb.py --rev0 <command ...>         same commands for the USA Rev 0 default.xbe
  py tools/xemu_gdb.py --eu1|--eu0 <command ...>    same commands for the Europe Rev 1 / Rev 0 default.xbe
  py tools/xemu_gdb.py --selftest

QEMU halts the guest while GDB is attached; every command detaches at the end, which resumes it.
Addresses: docs/findings.md "RE target 6".
"""
import socket
import struct
import sys

CLOCK_SECONDS, CLOCK_MINUTES, CLOCK_HOURS = 0x55F3DC, 0x55F3DE, 0x55F3DF
MS_PER_GAME_MINUTE = 0x55F3E8          # signed compare in CClock::Update; 0x7FFFFFFF never ticks
WEATHER_FORCED, WEATHER_NEW, WEATHER_OLD = 0x5E62F4, 0x5E62F8, 0x5E62FC
POSTFX_DISABLE = 0x5F4B1F
POSTFX_COLOURS = 0x6C88B8              # 8 floats: c1 rgba, c2 rgba (alpha already x2)
PLAYERS = 0x6C8F18                     # CWorld::Players[0].m_pPed
COLOURFILTER_CALL = 0x24CAF5           # call CPostEffects::ColourFilter(c1, c2); args = packed RGBA bytes
TIME_SCALE = 0x56B9AC                 # CTimer::ms_fTimeScale [S] (savegame field order), freeze tested live
IDLECAM_KICKIN = 0x6C5270             # gIdleCam 0x6C5248 +0x28: ms without input before the idle cam [C] (Init 0xD271F)
if "--rev0" in sys.argv:               # USA Rev 0: same build, data at -0x240 (proven by tools/rev0_map.py)
    sys.argv.remove("--rev0")
    CLOCK_SECONDS, CLOCK_MINUTES, CLOCK_HOURS = 0x55F19C, 0x55F19E, 0x55F19F
    MS_PER_GAME_MINUTE = 0x55F1A8
    WEATHER_FORCED, WEATHER_NEW, WEATHER_OLD = 0x5E60B4, 0x5E60B8, 0x5E60BC
    POSTFX_DISABLE = 0x5F48DF
    POSTFX_COLOURS = 0x6C8678
    PLAYERS = 0x6C8CD8
    COLOURFILTER_CALL = 0x24C826
    TIME_SCALE = 0x56B76C
    IDLECAM_KICKIN = 0x6C5030             # gIdleCam 0x6C5008 +0x28
elif "--eu1" in sys.argv:              # Europe Rev 1: data at +0x60 (proven by tools/rev0_map.py, xref; idle cam via its base)
    sys.argv.remove("--eu1")
    CLOCK_SECONDS, CLOCK_MINUTES, CLOCK_HOURS = 0x55F43C, 0x55F43E, 0x55F43F
    MS_PER_GAME_MINUTE = 0x55F448
    WEATHER_FORCED, WEATHER_NEW, WEATHER_OLD = 0x5E6354, 0x5E6358, 0x5E635C
    POSTFX_DISABLE = 0x5F4B7F
    POSTFX_COLOURS = 0x6C8918
    PLAYERS = 0x6C8F78
    COLOURFILTER_CALL = 0x24CA12
    TIME_SCALE = 0x56BA0C
    IDLECAM_KICKIN = 0x6C52D0             # gIdleCam 0x6C52A8 +0x28
elif "--eu0" in sys.argv:              # Europe Rev 0: data at -0x1E0 (proven by tools/rev0_map.py, xref; idle cam via its base)
    sys.argv.remove("--eu0")
    CLOCK_SECONDS, CLOCK_MINUTES, CLOCK_HOURS = 0x55F1FC, 0x55F1FE, 0x55F1FF
    MS_PER_GAME_MINUTE = 0x55F208
    WEATHER_FORCED, WEATHER_NEW, WEATHER_OLD = 0x5E6114, 0x5E6118, 0x5E611C
    POSTFX_DISABLE = 0x5F493F
    POSTFX_COLOURS = 0x6C86D8
    PLAYERS = 0x6C8D38
    COLOURFILTER_CALL = 0x24C84C
    TIME_SCALE = 0x56B7CC
    IDLECAM_KICKIN = 0x6C5090             # gIdleCam 0x6C5068 +0x28


def capture(path, title_prefix="xemu |"):
    """Grab an emulator window's client area; at an integer scale of 640 wide, box-reduce back to 640."""
    import ctypes
    from ctypes import wintypes
    from PIL import Image
    u, gd = ctypes.windll.user32, ctypes.windll.gdi32
    ctypes.windll.shcore.SetProcessDpiAwareness(2)

    class BIH(ctypes.Structure):
        _fields_ = [(n, t) for n, t in (("size", wintypes.DWORD), ("w", wintypes.LONG), ("h", wintypes.LONG),
                    ("planes", wintypes.WORD), ("bits", wintypes.WORD), ("comp", wintypes.DWORD),
                    ("img", wintypes.DWORD), ("xp", wintypes.LONG), ("yp", wintypes.LONG),
                    ("used", wintypes.DWORD), ("imp", wintypes.DWORD))]

    hwnd = u.FindWindowW(None, None)
    title = ctypes.create_unicode_buffer(256)
    while hwnd:
        u.GetWindowTextW(hwnd, title, 256)
        if title_prefix in title.value and u.IsWindowVisible(hwnd):
            break
        hwnd = u.GetWindow(hwnd, 2)                               # GW_HWNDNEXT
    if not hwnd:
        raise SystemExit(f"window '{title_prefix}…' not found")
    if u.IsIconic(hwnd):                                          # minimized windows render nothing
        u.ShowWindow(hwnd, 4)                                     # SW_SHOWNOACTIVATE: restore without taking focus
        import time
        time.sleep(1)

    def grab(win, flags):
        r = wintypes.RECT()
        u.GetClientRect(win, ctypes.byref(r))
        w, h = r.right, r.bottom
        hdc = u.GetDC(win)
        mdc, bmp = gd.CreateCompatibleDC(hdc), gd.CreateCompatibleBitmap(hdc, w, h)
        gd.SelectObject(mdc, bmp)
        u.PrintWindow(win, mdc, flags)
        buf = ctypes.create_string_buffer(w * h * 4)
        gd.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(BIH(ctypes.sizeof(BIH), w, -h, 1, 32)), 0)
        gd.DeleteObject(bmp), gd.DeleteDC(mdc), u.ReleaseDC(win, hdc)
        return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)

    img = grab(hwnd, 3)                                           # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    child = u.FindWindowExW(hwnd, None, None, None)
    if img.convert("L").getextrema()[1] == 0 and child:           # Cxbx: D3D9 child window, needs flag 2
        img = grab(child, 2)
    if img.width * 3 != img.height * 4:                          # letterboxed (PCSX2): drop black borders
        img = img.crop(img.convert("L").point(lambda v: 255 if v > 2 else 0).getbbox())
    w = img.width
    if w % 640 == 0 and w > 640:
        img = img.reduce(w // 640)                                # ponytail: assumes xemu integer scale + 4:3 fit
    img.save(path)
    return f"{path} {img.size[0]}x{img.size[1]}"


class Gdb:
    def __init__(self, host="127.0.0.1", port=1234):
        self.s = socket.create_connection((host, port), timeout=5)
        self.buf = b""

    def _recv_packet(self):
        while True:
            while b"#" not in self.buf or len(self.buf) - self.buf.index(b"#") < 3:
                self.buf += self.s.recv(4096)
            start = self.buf.index(b"$")
            end = self.buf.index(b"#", start)
            data, self.buf = self.buf[start + 1:end], self.buf[end + 3:]
            self.s.sendall(b"+")
            return data.decode()

    def cmd(self, data):
        self.s.sendall(f"${data}#{sum(data.encode()) % 256:02x}".encode())
        return self._recv_packet()

    def read(self, addr, n):
        reply = self.cmd(f"m{addr:x},{n:x}")
        if reply.startswith("E") or len(reply) != 2 * n:
            raise IOError(f"read {addr:#x}: {reply}")
        return bytes.fromhex(reply)

    def write(self, addr, data):
        reply = self.cmd(f"M{addr:x},{len(data):x}:{data.hex()}")
        if reply != "OK":
            raise IOError(f"write {addr:#x}: {reply}")

    def u32(self, addr):
        return struct.unpack("<I", self.read(addr, 4))[0]

    def detach(self):
        self.s.sendall(b"$D#44")
        self.s.close()


class CxbxMem:
    """Same read/write/u32 interface over Cxbx-Reloaded: HLE maps the XBE at its own VAs inside cxbxr-ldr.exe."""

    def __init__(self):
        import ctypes
        import subprocess
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq cxbxr-ldr.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True).stdout
        if "cxbxr-ldr" not in out:
            raise SystemExit("cxbxr-ldr.exe not running")
        pid = int(out.split(",")[1].strip('"'))
        self.k = ctypes.windll.kernel32
        self.h = self.k.OpenProcess(0x0438, False, pid)          # VM_READ | VM_WRITE | VM_OPERATION | QUERY_INFO
        self.ct = ctypes

    def read(self, addr, n):
        buf, got = self.ct.create_string_buffer(n), self.ct.c_size_t()
        if not self.k.ReadProcessMemory(self.h, self.ct.c_void_p(addr), buf, n, self.ct.byref(got)):
            raise IOError(f"read {addr:#x} failed")
        return buf.raw

    def write(self, addr, data):
        old = self.ct.c_ulong()
        self.k.VirtualProtectEx(self.h, self.ct.c_void_p(addr), len(data), 0x40, self.ct.byref(old))   # code pages
        if not self.k.WriteProcessMemory(self.h, self.ct.c_void_p(addr), data, len(data), None):
            raise IOError(f"write {addr:#x} failed")

    def u32(self, addr):
        return struct.unpack("<I", self.read(addr, 4))[0]

    def detach(self):
        self.k.CloseHandle(self.h)


def run(g, args):
    op = args[0]
    if op == "clock":
        h, m = int(args[1]), int(args[2])
        g.write(MS_PER_GAME_MINUTE, struct.pack("<i", 0x7FFFFFFF))
        g.write(CLOCK_SECONDS, struct.pack("<HBB", 0, m, h))      # seconds, minutes, hours are contiguous
    elif op == "weather":
        w = struct.pack("<h", int(args[1]))
        for a in (WEATHER_FORCED, WEATHER_NEW, WEATHER_OLD):
            g.write(a, w)
    elif op == "postfx":
        g.write(POSTFX_DISABLE, bytes([args[1] == "off"]))
    elif op == "filter":
        c = struct.unpack("<8f", g.read(POSTFX_COLOURS, 32))
        return " ".join(f"{v:g}" for v in c)
    elif op == "teleport":
        ped = g.u32(PLAYERS)
        ent = ped
        if g.read(ped + 0x46D, 1)[0] & 1 and g.u32(ped + 0x58C):
            ent = g.u32(ped + 0x58C)                              # in a vehicle: move the vehicle
        mat = g.u32(ent + 0x14)
        g.write((mat + 0x30) if mat else (ent + 4), struct.pack("<3f", *map(float, args[1:4])))
        if len(args) > 4 and ent == ped:                          # heading offsets are [S]
            g.write(ped + 0x558, struct.pack("<2f", float(args[4]), float(args[4])))
    elif op == "filterargs":                                      # the bytes ColourFilter really gets
        if g.cmd(f"Z0,{COLOURFILTER_CALL:x},1") != "OK":
            raise IOError("breakpoint refused")
        try:
            g.s.sendall(b"$c#63")
            g.s.settimeout(10)
            g._recv_packet()                                      # stop reply (T05...) when the call is reached
            esp = struct.unpack("<I", bytes.fromhex(g.cmd("g")[32:40]))[0]
            c1, c2 = g.read(esp, 4), g.read(esp + 4, 4)           # push [ebp-8]; push [ebp-4] -> c1 on top
        finally:
            g.cmd(f"z0,{COLOURFILTER_CALL:x},1")
        return " ".join(str(v) for v in c1 + c2)
    elif op == "timescale":
        g.write(TIME_SCALE, struct.pack("<f", float(args[1])))
    elif op == "idlecam":
        g.write(IDLECAM_KICKIN, struct.pack("<f", 90000.0 if args[1] == "on" else 1e30))
    else:
        raise SystemExit(__doc__)
    return "ok"


def selftest():
    import threading
    mem = bytearray(0x800000)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def stub():
        c, _ = srv.accept()
        buf = b""
        while True:
            chunk = c.recv(4096)
            if not chunk:
                return
            buf += chunk
            while b"#" in buf and len(buf) - buf.index(b"#") >= 3:
                s, e = buf.index(b"$"), buf.index(b"#")
                pkt, buf = buf[s + 1:e].decode(), buf[e + 3:]
                c.sendall(b"+")
                if pkt == "D":
                    c.close()
                    return
                if pkt[0] == "m":
                    a, n = (int(x, 16) for x in pkt[1:].split(","))
                    rep = mem[a:a + n].hex()
                else:
                    head, hx = pkt[1:].split(":")
                    a = int(head.split(",")[0], 16)
                    mem[a:a + len(hx) // 2] = bytes.fromhex(hx)
                    rep = "OK"
                c.sendall(f"${rep}#{sum(rep.encode()) % 256:02x}".encode())

    threading.Thread(target=stub, daemon=True).start()
    ped, mat = 0x700000, 0x710000
    struct.pack_into("<I", mem, PLAYERS, ped)
    struct.pack_into("<I", mem, ped + 0x14, mat)
    struct.pack_into("<8f", mem, POSTFX_COLOURS, 66, 66, 48, 254, 166, 129, 60, 254)
    g = Gdb(port=srv.getsockname()[1])
    run(g, ["clock", "19", "30"])
    assert mem[CLOCK_HOURS] == 19 and mem[CLOCK_MINUTES] == 30
    assert struct.unpack_from("<i", mem, MS_PER_GAME_MINUTE)[0] == 0x7FFFFFFF
    run(g, ["weather", "9"])
    assert all(struct.unpack_from("<h", mem, a)[0] == 9 for a in (WEATHER_OLD, WEATHER_NEW, WEATHER_FORCED))
    run(g, ["postfx", "off"])
    assert mem[POSTFX_DISABLE] == 1
    assert run(g, ["filter"]) == "66 66 48 254 166 129 60 254"
    run(g, ["teleport", "2495.5", "-1687", "13.5", "1.5"])
    assert struct.unpack_from("<3f", mem, mat + 0x30) == (2495.5, -1687.0, 13.5)
    assert struct.unpack_from("<f", mem, ped + 0x558)[0] == 1.5
    run(g, ["timescale", "0"])
    assert struct.unpack_from("<f", mem, TIME_SCALE)[0] == 0.0
    run(g, ["idlecam", "off"])
    assert struct.unpack_from("<f", mem, IDLECAM_KICKIN)[0] > 1e29
    g.detach()
    print("xemu_gdb selftest OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args in ([], ["--selftest"]):
        selftest()
    elif args[0] == "--cxbx":                                     # same commands against Cxbx-Reloaded (no filterargs)
        if args[1] == "capture":
            print(capture(args[2], "(GTA San Andreas)"))
        else:
            g = CxbxMem()
            try:
                print(run(g, args[1:]))
            finally:
                g.detach()
    elif args[0] == "capture" and len(args) == 2:
        print(capture(args[1]))                                   # no GDB: grabbing never halts the guest
    else:
        g = Gdb()
        try:
            print(run(g, args))
        finally:
            g.detach()
