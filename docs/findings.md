# Findings log

One entry per experiment / RE target: hypothesis, prediction, result, Confirmed/Refuted. Evidence legend as in PLAN.md.

## 2026-09-23 — Phase 0: workspace and tools

- `work/xbox/default.xbe` and `work/xbox/stream.ini` are copies of the originals; SHA1 match (`10efb868…` / `67732726…`) [C].
- XBE section table [C]: `.text` VA 0x11000 raw 0x1000 (Δ0x10000); `.rdata` Δ0x10280; `.data` Δ0xFB60, raw ends at VA 0x3D2C04 (BSS above); `D3D` VA 0x35AD80 Δ0xDD80 (raw 0x10B44 < vsize 0x14418, so the deferred-state area near 0x36BBF8 is partly BSS). `xbe_patch.py` maps VAs through this table.
- `0x24F007` begins `55 8B EC 53 56 33 DB 57 43 53 6A 09 FF 15 80 DE 75 00` = prologue + `RwRenderStateSet(9 filter, 1 nearest)` — consistent with PLAN §9 ColourFilter [C].
- Installed: xemu 0.8.136 (`E:\Emuladores\xemu`), Ghidra 12.1.4 (`F:\Tools\ghidra`, JDK 21), numpy, keystone-engine, capstone (was missing on py 3.13). xdelta already at `F:\Tools\xdelta`.
- Tools: `tools/xbe_patch.py`, `tools/predict_filter.py`, `tools/compare.py`, `tools/xemu_gdb.py`, each with an assert self-check (`--selftest`, all pass; `xemu_gdb` against a fake RSP stub, not yet a live xemu). `predict_filter` reproduces the PLAN §6 LA 12:00 gains for both formulas using in-memory alpha 254 (timecyc 127 ×2) [C].

## 2026-09-23 — RE target 6: clock / weather / player (static)

### Xbox (`default.xbe` Rev 1)

| Item | Address | Evidence |
|---|---|---|
| CClock::Initialise(eax = ms/minute) | 0xEBBA6 (sets 12:00, day 1, month 1, weekday 4) | [C] |
| CClock::SetGameClock(h, m, day) | 0xEBBE4 | [C] |
| CClock::Update | 0xEBD11 | [C] |
| ms_nGameClockHours (byte) | 0x55F3DF | [C] |
| ms_nGameClockMinutes (byte) | 0x55F3DE | [C] |
| ms_nGameClockSeconds (word) | 0x55F3DC | [C] |
| day / month / weekday (bytes) | 0x55F3E0 / 0x55F3E1 / 0x55F3DA | [C] |
| ms_nLastClockTick / ms_nMillisecondsPerGameMinute | 0x55F3E4 / 0x55F3E8 (signed compare; also written at 0x163D4C) | [C] |
| CTimer::m_snTimeInMilliseconds | 0x56B9CC | [C] |
| CCheat active flags read by Update | 0x45660B (faster clock), 0x456637, 0x456638 (clock-stop cheats) | [S] names |
| CWeather::Update | 0x26025D | [C] |
| OldWeatherType / NewWeatherType / ForcedWeatherType (short) | 0x5E62FC / 0x5E62F8 / 0x5E62F4 | [C] (Update: Old=New; New = Forced≥0 ? Forced : list[(idx+1)%64]) |
| WeatherTypeInList / InterpolationValue | 0x5E62EC / 0x5E62E8 | [C] |
| Weather cheat handlers (Old=New=Forced=k) | 0x39D9D… | [C] |
| CWorld::Players (stride 0x190) / PlayerInFocus (byte) | 0x6C8F18 / 0x56BC54 | [C] (FindPlayerPed 0x102F07) |
| FindPlayerEntity / FindPlayerCoors | 0x102EA0 / 0x102F37 | [C] |
| CPed: bInVehicle bit / m_pVehicle / heading | +0x46D bit0 / +0x58C / +0x558, +0x55C (current, aiming) | [C] (heading live: −1.71 / 4.57 = same angle mod 2π) |
| Entity position | `[ent+0x14]` matrix → +0x30 (x,y,z floats); else `ent+4` | [C] |
| TheCamera placement / m_matrix | 0x6C44D4 / 0x6C44E4 | [S] |

### PS2 (`SLUS_209.46` v3.00; `$gp` = 0x66B870, set in crt0 at 0x100198)

| Item | Address | Evidence |
|---|---|---|
| CClock::SetGameClock | 0x22CD60 | [C] |
| CClock::Update | 0x22CF30 | [C] |
| hours / minutes (bytes), seconds (short) | 0x66BF2C / 0x66BF30 / 0x66BF34 | [C] |
| day / month / weekday | 0x66BF28 / 0x66BF24 / 0x66BF38 | [C] |
| LastClockTick / ms per minute | 0x66BF20 / 0x66BF1C | [C] |
| CTimer::m_snTimeInMilliseconds | 0x66C194 | [C] |
| CCheat flags read by Update | 0x88E28B, 0x88E2B7, 0x88E2B8 (same 0x2C spacing as Xbox) | [S] names |
| CWeather::ForceWeather / ForceWeatherNow / ReleaseWeather | 0x2BDF50 / 0x2BDF60 / 0x2BDFC0 | [C] |
| Old / New / Forced weather (short) | 0x66C4A4 / 0x66C4A8 / 0x66C4AC | [C] (Update shift at 0x2BC6CC) |
| WeatherTypeInList / InterpolationValue | 0x66C4B4 / 0x66C4B8 | [C] / [S] |
| CWorld::Players (stride 0x1BC) / PlayerInFocus | 0x70A160 / 0x66C1F4 | [C] |
| CPed: bInVehicle bit / m_pVehicle | +0x4A5 bit0 / +0x5CC | [C] |
| CPed heading | unknown — PS2 CPed offsets are not a constant shift of Xbox (0x38 vs 0x40) | [H] |
| Entity position | `[ent+0x14]` matrix → +0x30, same as Xbox | [C] |
| TheCamera placement / m_matrix | 0x6FF094 / 0x6FF0A4 | [S] |

### Consequences for the harness (E0)

- Clock freeze: continuously write hours/minutes/seconds (pnach place 1), or set ms-per-minute to 0x7FFFFFFF (signed compare → never ticks). On Xbox re-poke 0x55F3E8, since 0x163D4C also writes it.
- Weather freeze: write the same id to Old/New/Forced; with Forced ≥ 0 Update keeps New = Forced.
- `tools/ps2_cheats.pnach` implements clock + weather groups for the §16 scenes; installed as `PCSX2\cheats\SLUS-20946_2C6BE434.pnach`. CRC = XOR of all ELF words [C] (method reproduces PCSX2's logged `2F56CBC9` for Klonoa 2 SLUS_201.51).
- xemu: portable `E:\Emuladores\xemu\xemu.toml` points at the BIOS files, the official copyright-free `xbox_hdd.qcow2` (xemu-project/xemu-hdd-image) and the original Xbox ISO (read-only DVD). Teleport (pointer chase to the ped matrix) and PS2 heading are still open.
- Weather ids are taken from gta-reversed `eWeatherType` [S]; the code's special-cases (0x10, 0x13, and the 0/0xB/0x11/0x12 group) are consistent with it.

## 2026-09-24 — E0: xemu live validation

- The Redump ISO (video partition first) shows "insert an Xbox disc" in xemu. Fix: `work/xbox/gtasa_stock.xiso` = original ISO bytes from 0x18300000 to the end (game partition). The embedded `default.xbe` (sector 348678, 4018176 B) hashes to Rev 1 [C]. Patched builds = copy of this XISO with the XBE bytes replaced in place.
- xemu 0.8.136 `-s` boots it; `tools/xemu_gdb.py` works live [C]:
  - clock 0x55F3DF/0x55F3DE ticks (8:00 → 8:02); `clock 12 0` holds 12:00:00 after 10 s (ms-per-minute 0x7FFFFFFF freeze works);
  - `weather 1` holds Old/New/Forced = 1 (was 14/14/14 at boot);
  - Players[0].m_pPed = 0xEB71A0, matrix pos (2489.3, −1667.0, 13.3) = Grove Street;
  - PostFX floats at 0x6C88B8 have alpha 254 = timecyc 127 ×2 (loader doubling confirmed live); radiosity flag 0x5F4B1C = 0, postfx disable 0x5F4B1F = 0.

## 2026-09-24 — E0/E4 prep: deterministic check of the stock Xbox ColourFilter (Grove St, 12:00, SUNNY_LA)

- **Hypothesis (PLAN §5/§9):** stock Xbox output = `fb·(1 + c1·a1 + c2·a2)`, with a = vertex alpha and framebuffer-copy alpha = 1.0 (H3).
- **Setup:** world frozen via `CTimer::ms_fTimeScale` 0x56B9AC = 0 (4.0% → 0.86% changing px). Real ColourFilter args read by breakpoint at 0x24CAF5: c1 = (70,121,120, a240), c2 = (160,88,21, a254) = the 0x6C88B8 floats (lighting mult ≈ 1 at noon) [C]. Live RAM-only code patches (XBE on disk untouched): NOP `call ColourFilter` (raw frame); alpha of pass 1 or pass 2 forced to 0 (`movzx eax,[ebp+0xb|0xf]` → `xor eax,eax`).
- **Code [C]:** ColourFilter sets filter NEAREST, fog/ztest/zwrite off, raster = fb copy 0x5F4B28, vtxalpha on, SRC = SRCALPHA, DST = ONE, then draws two Im2D quads with vertex colour c1, then c2 (ARGB packed from the arg bytes, R at byte 0).
- **Result:** gain vs raw is spatially constant (road/wall/ground agree; IQR ≤ 0.03 on R/G). Per pass:
  - pass 2 alone: α2 = 0.585 / 0.587 / 0.592 (R/G/B), vertex a2 = 0.996;
  - pass 1 alone: α1 = 0.552 / 0.552 / 0.531, vertex a1 = 0.941;
  - both: gain 1.517 / 1.462 / 1.296 (PLAN's formula predicted 1.883 / 1.790 / 1.525).
  - The model `fb·(1 + Σ c·α)` holds (α is consistent across channels), but **α ≈ 0.58–0.59 × vertex alpha**, i.e. the effective framebuffer-copy alpha is a constant ≈ 0.585 (≈149/255), not 1.0.
- **Verdict:** H3 **Refuted** as stated (fb alpha ≠ 1). Stock Xbox formula corrected to `fb + fb·c1·(a1·k) + fb·c2·(a2·k)`, k ≈ 0.585 [C for this scene]. The origin of k (backbuffer alpha content vs. xemu NV2A behaviour) is open [H]; it matters for P1, since `ALPHAOP=MODULATE` would inherit it.
- **Also:** the PostFX disable-all byte 0x5F4B1F changes 19% of pixels vs NOP-ing only the ColourFilter call, so it is **not** a clean "raw" frame. E3/E4 must use the call-NOP raw frame.

## 2026-09-24 — E3: offline filter transplant (LS street by the tracks, (2277.4, −1254.4, 24.0), 12:00, SUNNY_LA)

- **Hypothesis H1:** the colour-filter formula explains most of the PS2/Xbox colour gap. *Prediction:* the PS2 formula applied to a raw Xbox frame lands near the PS2 capture; stock Xbox stays far.
- **Setup:** both emulators frozen (timeScale 0; PS2 timeScale = 0x66C1A8 = 0x938($gp) [C, live]). Same clock/weather/position via `xemu_gdb.py` / `pcsx2_pine.py` (PS2 heading +0x598/+0x59C written; PS2 CJ drifted 3.6 m before capture). PCSX2 software renderer 1× (per-game ini). Xbox raw = ColourFilter call NOP'd in RAM. PS2 formula applied with the real call-site args c1 (70,121,120,a240), c2 (160,88,21,a254) → `xbox_raw_ps2formula.png`. Files in `captures/ls_2277_noon/`.
- **Result (matched regions, CIE76 ΔE vs PS2):**

| Region | PS2 RGB | Xbox stock | Xbox raw + PS2 formula | ΔE stock | ΔE PS2-formula |
|---|---|---|---|---|---|
| ground left of CJ | 141 118 61 | 121 108 74 | 143 121 63 | 14.5 | **1.1** |
| railway | 108 92 45 | 103 96 73 | 122 107 62 | 14.9 | **6.4** |
| sky (hue-classified) | 64 229 238 | 67 190 229 | 80 218 233 | — | G gap 39 → 11 |

  Global stats are skewed by framing (a parked car on PS2, xemu menubar in the top 12 rows, no Xbox HUD): saturation PS2 0.615 / stock 0.460 / PS2-formula 0.549; R/B 0.82 / 0.75 / 0.97.
- **Verdict:** H1 **Confirmed** (visually and on the matched ground/rail patches). Residual: the PS2-formula frame is a little too red in the sky (R 80 vs 64) and the PS2 has darker shadows (lum p5 0.087 vs 0.154). Candidates: radiosity (not modelled), the per-pass clamp points, or c1 on PS2 differing from the Xbox call-site value [H].
- **Harness notes:** set `display.ui.show_menubar = false` in xemu.toml (the menubar appears in captures on mouse-over); give the PS2 camera time to settle before freezing.

## 2026-09-24 — RE targets 1–2 + diagnosis of the k ≈ 0.585 filter factor

**RE target 1 — fb copy `0x24BB7B` [C]:** not CopyRects. It ends the scene camera `[0x5B8528]`, begins the postfx camera `[0x5F4B30]` (its raster is the copy `[0x5F4B28]`), draws the Im2D quad at 0x5C72A8 (0..640 × 0..480, vertex colour FFFFFFFF, texel-space UVs 0.5..640.5 = linear texture) textured with the screen raster `[0x5F4B2C]` (vtxalpha 0, ztest/zwrite/fog off, address CLAMP, cull none), then restores the scene camera.
- Copy raster: RwRaster 1024×512×32; D3D texture at plugin +0x34 → `D3DPixelContainer` {Common 0x000C0001, Data phys, Format 0x09A10729 = fmt 0x07 **X8R8G8B8 swizzled**}. Screen raster: 640×480×32, surface 0x36D7F4 in the D3D section, fmt 0x1E LIN_X8R8G8B8, pitch 2560. Guest VA = 0x80000000 | Data.
- ColourFilter quad at 0x5C7318: 0..1024 × 0..512, UV 0..1 plus a half texel, rhw 1.111 → samples the 1024×512 copy 1:1.

**RE target 2 — Xbox D3D texture-stage state [C]:** `D3D__TextureState` base **0x36BBC8**, 0x80 bytes per stage, XDK 5849 order (ADDRESSU 0, ADDRESSV 1, MAGFILTER 3, MINFILTER 4, MIPFILTER 5, COLOROP 12, COLORARG0/1/2 13/14/15, ALPHAOP 16, ALPHAARG0/1/2 17/18/19, RESULTARG 20, TEXCOORDINDEX 28). Values: D3DTOP DISABLE 1, SELECTARG1 2, SELECTARG2 3, MODULATE 4, MODULATE2X 5; D3DTA DIFFUSE 0, CURRENT 1, TEXTURE 2. During ColourFilter: stage0 COLOROP = ALPHAOP = MODULATE(DIFFUSE, TEXTURE), CLAMP, POINT; stage1 DISABLE. Dirty flags 0x36E280 = 0x20 at that point.

**Diagnosis of k (live pass-2 probes, pass 1 alpha = 0, c2 forced via `push imm8; pop reg` RAM patches):**
- gain − 1 = k·c·a with k = 0.585 ± 0.005, constant over channel, colour value (64/127) and vertex alpha (64/128/255) [C].
- rhw 1.111 / 20 / 1.0 → same k; c2 = 0 → gain exactly 1 (no additive term) → **fog/depth refuted**.
- Blend ONE/ONE with a = 128 → gain − 1 = 0.585·c (alpha unused) → **k is in the colour path** (combiner output = 0.585·texel·diffuse), not in the blend factor.
- Copy texels in guest RAM equal the backbuffer exactly (Morton-swizzle check at 7 points) → the data in RAM is not darkened. (xemu keeps render targets on the GPU, so RAM may not be what gets sampled.)
- RW alpha test kills a = 0 source pixels (a0 + ONE/ONE adds nothing).
- By the book (MODULATE, X8 texture, SRCALPHA/ONE) real hardware gives k = 1. The HUD (also Im2D + MODULATE) does not look darkened, so k is specific to sampling this render-target texture.

**Status:** H-a (fb alpha) refuted, H-b refuted, fog refuted. Leading hypothesis **H-c: xemu artefact when sampling a render-target texture** [H] — needs a hardware or second-emulator reference. Consequences:
- The E3 transplant stays valid (the raw frame has no filter).
- On real hardware the stock Xbox gain should be the PLAN's 1.88/1.79/1.53 (brighter, more washed out than xemu's 1.52/1.46/1.30).
- P1 must be designed to hardware semantics; xemu validation then needs k in the prediction, until k is explained.

## 2026-09-24 — k cross-check on Cxbx-Reloaded (HLE)

- Cxbx-Reloaded CI-585c49a runs `work/xbox/game/default.xbe` (a copy of the extracted folder). CJ is invisible, but the scene renders. The XBE lives at its own VAs inside `cxbxr-ldr.exe`, so `xemu_gdb.py --cxbx` pokes memory via Read/WriteProcessMemory (the same addresses work: clock, ped, code). Capture needs PrintWindow flag 2 on the D3D9 child window (automatic fallback in `capture`).
- Same scene/state, same RAM patches: pass 2 alone k = 0.581 / 0.583 / 0.577 (a255); ONE/ONE a128 identical to SRCALPHA a255 → colour path; stock full-filter gain **1.519 / 1.462 / 1.304** (xemu 1.517 / 1.462 / 1.296).
- **Verdict:** H-c (xemu artefact) **Refuted**. Two independent GPU implementations (LLE NV2A vs HLE D3D8→D3D9) agree, so k ≈ 0.58 comes from the game's D3D state/data. The PLAN's "Xbox gain 1.91 / 1.76 / 1.42" (k = 1) is wrong for the real game. Stock Xbox = `fb·(1 + 0.585·(c1·a1 + c2·a2))` [C for this scene; both emulators].
- Remaining candidates (matter for P1, because stage-state MODULATE2X only works if the fixed-function stages are what is really active) [H]:
  1. a pixel shader still bound during PostFX (stage states ignored; the PS computes tex·diffuse·const);
  2. the copy pass `0x24BB7B` stores fb·0.585 on the GPU (guest RAM compare in xemu could be stale);
  3. RW's Xbox Im2D draws through a vertex shader that scales diffuse;
  4. a D3D state not yet read (e.g., a stage-0 texture-transform or colour-sign side effect).

## 2026-09-24 — Where k lives (continued)

Symbols come from the Cxbx-Reloaded symbol cache (`E:\Emuladores\Cxbx-Reloaded\SymbolCache\GTA San Andreas-80a6f8dd6db3ccc6.ini`, 354 XDK 5849 functions and D3DRS addresses, e.g. SetPixelShader 0x368270, SetVertexShader 0x35CF30, DrawIndexedVertices 0x360610, D3DRS_FogEnable 0x36E3F8).

- Device global `[0x36E278]`; current pixel shader `[dev+0x784]`; current vertex shader `[dev+0x794]` [C].
- During ColourFilter: **pixel shader = 0** (fixed function) [C]. RW `Im2DRenderIndexedPrimitive` 0x2ABA40 copies the vertices verbatim (movntq), calls the 2D setup 0x2AB710 (SetPixelShader(0); with a texture: COLOROP = ALPHAOP = MODULATE, ARG1 DIFFUSE, ARG2 TEXTURE; VS 0x3D4D18), then DrawIndexedVertices [C].
- Im2D vertex shaders (created at 0x2AB5A2; decl/func in .rdata): 0x3D4D18 = {oPos = v0·c96 + c97, oPos.w = 1/v0.w, **oD0 = v1**, oT0 = v2}; 0x3D4D1C = no texcoord; 0x3D4D20 = no colour. No oFog write, no colour scaling [C]. RW uploads only c96/c97 (viewport).
- Render state at the draw: FOGENABLE 0, ZFUNC ALWAYS, ALPHATEST on (GREATER, ref 2), SRCBLEND SRCALPHA, DESTBLEND ONE, BLENDOP ADD, BLENDCOLOR 0, COLORWRITE all, DITHER 1 [C].
- **Texture-less probe** (raster push → 0, ONE/ONE, c2 = (64,32,16,a255)): the result is an addition of +37/+19/+10 = 0.58·c → k is on the **diffuse** side, not in the texture/copy [C].
- The HUD (Im2D) is not visibly scaled (clock digits 225,225,225) → k is draw-specific; cause still unknown [H]. A float 0.585 at 0x36A4D4 (D3D section) is part of a log2 table {0, 0.585, 1, 1.322, 1.585} with no code reference, so it's a coincidence.
- **Decision for P1:** treat k as an empirical property of this draw (present in LLE xemu and HLE Cxbx). The P1 colour constants get a single tunable k (default 0.585), so the patched output matches the PS2 formula in the emulators. Hardware validation remains open (if k = 1 on hardware, re-tune one constant).

## 2026-09-24 — k solved: the Xbox blur pass; P1 built and E4 (live, RAM-only)

**k = the Xbox-only blur pass `0x24ECAA` [C].** It runs after ColourFilter (called at 0x24CC89 with count `[0x3CE7B4]` = 2, alpha `[0x3CE7B8]` = 60, UV-offset scale `[0x3CE7B0]` = 1, enable byte `[0x3CE7AD]` = 1; static .data defaults, no direct writers). Each iteration draws the **pre-filter copy** `[0x5F4B28]` full-screen (colour 255,255,255, a = 60, default SRCALPHA/INVSRCALPHA) with slightly larger UV offsets. Two lerps at 60/255 → `out = 0.585·F + 0.415·raw`, and **(1 − 60/255)² = 0.5854** = the measured k.
- Evidence: in replace mode the output is `0.415·raw + 0.585·F` (pass-1-only probes with MODULATE/2X/4X fit this); with `0x3CE7AD` = 0 the additive-probe k goes from 0.489 to 0.83 (ratio 0.589).
- H-a (fb alpha), H-b, H-c (xemu), fog, VS scaling and pixel shader are all refuted. The HUD is unaffected because it is drawn later.
- This pass is part of the Xbox "washed-out" look: it re-adds 41.5% of the unfiltered frame (plus a slight blur).

**Residual k2 ≈ 0.80–0.83 [H].** It appeared only after the controller was disconnected/reconnected (before that, total k was exactly 0.585). It sits in the colour path (ONE/ONE and SRCALPHA give the same result; alpha is exact) and fits a further ~17% raw mix. Not the 0x24E90C/0x24B93E SpeedFX block, heat haze, underwater, 0x24E55E, 0x24E513, 0x110594, or 0x24EF1A (night vision only). Not a fade (black level normal). The trace of `0x263B40` callers after the filter: blur ×2 (0x24C42F), 0x24FA3A (render-to-texture, shadows), 0x250410 ×4, 0x25CCA8, 0x25BBAC ×9. Next check: a fresh boot, to see whether it disappears.

**P1 (`patches/p1_colourfilter.py` → `.json`) [built]:** a full rewrite of 0x24F007–0x24F132 (261 of 300 B): NEAREST, fog/z off, raster = copy, vtxalpha on; D3D-only stage0 COLOROP = MODULATE4X (RW cache 0x75D5A0 stays 4, so 0x2AB710 does not overwrite it), vertex colour = c·S (S = 128/256 for k = 1); pass 1 ONE/ZERO A = FF, pass 2 SRCALPHA/ONE A = a2; restores MODULATE and the original tail. Plus a data patch `0x3CE7AD` 01 → 00 (blur off). The JSON uses `orig_sha1` (no Rockstar bytes); `xbe_patch.py` now supports it. `dist/default_p1.xbe` sha1 96956a41…, 292 bytes changed.

**E4 (live RAM patch, blur off, frozen scene):**
- pass 1 alone: gain/c1 = 2.20 / 2.00 / 2.02 → `clip(fb·2c1)` reproduced [C] (R slightly high at a low c value).
- pass 2 alone: (gain − 1)/c2 = 1.59 / 1.63 / 1.56 vs 2·a2 = 1.99 → the residual k2 ≈ 0.8.
- Verdict: the P1 mechanism is **Confirmed** (MODULATE4X survives RW's 2D setup; the pass-1 term is exact). The ±2 E4 criterion is **not met yet** while the k2 residual is present; to be re-run after a fresh boot.
- Bug fixed on the way: `capture` letterbox auto-crop cut into dark 4:3 frames; it now crops only non-4:3 windows (PCSX2).

## 2026-09-24 — Residual k2 = display gamma; E4 passes

- **Residual k2 ≈ 0.83 = display gamma [C].** `D3DDevice_SetGammaRamp` (0x35E4E0) keeps a double-buffered ramp in the device at `dev + 0x1C28 + 0x1DC + idx·0x300` (R, G, B × 256; current idx `[dev+0x240C]`). The game builds it from the brightness setting with pow() into 0x5F20F0 and calls it from 0x2746EE. Active ramp after loading the save: R = G = B, `[0,32,64,128,192,255] → [2,44,79,142,200,255]`, fitted exponent **0.843**; the other buffer is the identity (the first session, a new game → k was exactly 0.585). xemu applies the ramp at display, so the captures are `fb^0.843`. This explains every "k2" probe, e.g. pass-1 R 0.549 → 0.608 (measured 0.604), 0.275 → 0.343 (0.338), 0.137 → 0.192 (0.191). A fresh boot + the same save keeps it; it is not a render pass (a trace of 1,372 RwRenderStateSet calls after the filter found no rebind of the copy raster).
- **Rule for all future captures:** read the active ramp and linearize with its inverse before any per-pixel comparison (the E3 captures were taken while the ramp was still the identity).
- **P1 final form:** MODULATE2X with the colours as-is (S = 256, exact for k = 1; the builder falls back to 4X + scale only if k < 1), rounding in the scale, plus blur off. 266 of 300 B. `dist/default_p1.xbe` regenerated via `xbe_patch.py`.
- **E4 (live RAM patch, frozen scene, framebuffer space):** P1 vs `predict_filter` PS2 formula on the raw frame: MAE 2.49 / 2.29 / 0.97, **86.9% of pixels within ±2**, 93% within ±4, mean bias ≈ −1 level. Residual spread is consistent with gamma-inversion quantization of 8-bit captures + dithering. **Verdict: E4 Confirmed** (P1 implements the PS2 colour-filter formula on the Xbox). (MODULATE4X variants: truncated S = 1/2 → 83.8% within ±2; rounded → 77.5%.)

## 2026-09-24 — P1 boot test (v0.1 candidate)

- `work/xbox/gtasa_p1.xiso` = a copy of `gtasa_stock.xiso` with the embedded default.xbe (sector 348678) replaced by `dist/default_p1.xbe` (sha1 c54604a8…; same size; the XDVDFS listing is still valid). Booted in xemu via Machine → Load Disc + Reset; the save loads.
- Live check [C]: RAM at 0x24F007 = P1 code, blur byte 0x3CE7AD = 0. The gamma ramp is the identity in this session (captures are linear).
- HUD, radar, clock and money render normally at dawn (06:51) and noon, so the MODULATE restore works. The dawn sky is strongly orange (PS2-like).
- Fidelity vs PS2 (same spot/time/weather; camera framing differs a little; `captures/ls_2277_noon/_p1_vs_ps2.png`):

| Metric | PS2 | Xbox stock | Xbox + P1 |
|---|---|---|---|
| ground patch RGB / ΔE vs PS2 | 141 118 61 | 121 108 74 / 14.5 | 131 113 66 / **6.3** |
| rail patch ΔE (framing-sensitive) | — | 14.9 | 10.5 |
| sky RGB (hue-classified) | 64 229 238 | 67 190 229 | **80 221 236** |
| HSV saturation mean | 0.615 | 0.460 | 0.533 |
| luminance p5 | 0.087 | 0.136 | 0.102 |

- **Verdict:** P1 closes most of the colour gap (Phase 2 goal). Remaining gap (saturation, deep shadows, glow) is expected from P2 blur / P3 radiosity / P4 building ambient, which are not applied yet.
- Note: `display.ui.show_menubar = false` in xemu.toml did not hide the menubar (it still appears in the top ~12 rows of captures); the analysis masks rows < 14.

## 2026-09-24 — Test saves past the first missions (interiors)

- The xemu HDD had no GTA SA save, only `UDATA/545400a3/{TitleMeta,TitleImage,SaveImage}.xbx`. Title ID `545400A3` = Second Edition (v2). First-edition saves use `54540082` (NTSC) and `54540086` (PAL).
- Xbox save format [C]: `GTA_SA.xsv` = a 20-byte signature + the standard 0x31800-byte SA save (checksum = byte sum, as on PC). Signature = HMAC-SHA1(key, data[20:]), key = HMAC-SHA1(XboxCERTKey `5C0733AE…1FE0`, XBE cert SignatureKey at cert+0xC0)[:16] = `2914C3D3C61115BF5CD42C09655FED02`. The computed signature matches a genuine v2 save (roamable, not tied to the console).
- v1 → v2 conversion [C]:
  - Version ID: v1 = `4CDC1D64`, v2 = `F68D14FD` (block 0 +0).
  - MAIN is 196293 B in v1 and 196272 B in v2, and the 21-byte edit comes before every saved IP. Every relative thread IP and return-stack slot is shifted −21. All 28 threads then land after a `wait`, and the return slot lands after a `gosub`. A genuine v2 save has main at `0xEB36` = v1's `0xEB4B` − 21.
  - The scm-size field is set to 196272, then the checksum is recomputed and the save re-signed. Block sizes match v1/v2 exactly.
- Installed in `E:\Emuladores\xemu\xbox_hdd.qcow2` (original backed up as `xbox_hdd.qcow2.bak_20260924`):
  - slot 1 "Big Smoke": a genuine v2 save, unmodified (GameFAQs 9370), $999,999,999;
  - slot 2 "Ryder": EU v1, converted, clean (GameFAQs 12695);
  - slot 3 "Ryder": NA v1, converted, $999M, has-cheated flag set (GameFAQs 8099).
- Tools (read-only qcow2+FATX reader, installer that rewrites a fresh qcow2 and verifies every cluster, converter) and the downloads are in `work/saves/` (gitignored).
- Status: slot 1 is the zero-risk save. Slots 2–3 depend on the conversion **[S]**; untested in-game.

## 2026-09-24 — P1 in-game interior check (CJ's house)

- Setup: `gtasa_p1.xiso` with save slot 2 (the converted Ryder save, which loads fine → the v1→v2 conversion is **[C]**). CJ is inside interior 3 at (2495.6, −1700.9, 1014.7), clock about 06:30, `timescale 0`.
- Live checks [C]: RAM at 0x24F007 = P1 code, and `0x3CE7AD` = 0.
- Gamma ramp idx 0 is **not** the identity (`[0,32,64,128,192,255] → [6,63,101,160,210,255]`). Saved as `captures/cj_house_int/_gamma_ramp.bin`; captures are linearized through its inverse.
- ColourFilter args (`filterargs`) [C]: c1 = (64,64,64, a128), c2 = (64,64,64, a254). This is a neutral interior filter.
  - PS2 formula: gain ≈ 1.00.
  - Stock Xbox formula: 1.376 (before the blur mix).
- Hypothesis: P1 in an interior matches `predict_filter` (PS2) within ±2 and leaves the HUD untouched. Prediction: ≥ 90% of pixels within ±2, and HUD P1 == raw (raw = ColourFilter call NOP at 0x24CAF5).
- Result:
  - Whole frame (rows < 14 masked): 95.6% within ±2. The misses all fall in one box (x 268–396, y 173–428) where CJ's idle animation and the bobbing entry marker keep moving at `timescale 0`; two P1 captures differ from each other in the same box.
  - Outside that box: **100% within ±2**, MAE 0.51 / 0.51 / 0.48.
  - HUD (clock, money, health, weapon, radar): P1 vs raw max 2, MAE 0.30, so the MODULATE restore holds in interiors.
- **Verdict: Confirmed.** Caveat: the interior filter is close to the identity under the PS2 formula, so this scene tests state safety (HUD, restore, no artefacts) more than the colour transform. The night check is the stronger remaining test.

## 2026-09-24 — P1 in-game night check (Grove St, 00:00, SUNNY_LA)

- Setup: slot 2 save on `gtasa_p1.xiso`, player at (2488.2, −1665.5, 13.3). Clock frozen at 00:00, weather 0, then `timescale 0`. Gamma ramp idx 0 is the same non-identity ramp as in the interior check; captures are linearized.
- ColourFilter args [C]: c1 = (93,93,93, a254), c2 = (64,129,130, a254).
  - PS2 gain ≈ 1.23 / 1.74 / 1.75.
  - Stock Xbox gain ≈ 1.61 / 1.87 / 1.87 (formula only).
- Hypothesis: P1 at night matches the PS2 formula within ±2 on filtered pixels. Prediction: ≥ 95% within ±2 and near-zero bias; P1 vs the Xbox formula far off.
- Result (rows < 14 masked; pixels that move between two P1 captures masked, 6.1%):
  - All static pixels: 94.8% within ±2. Every outlier is a pixel where P1 == raw: the HUD, radar, help text and streetlight coronas. These are drawn after PostFX, so the prediction wrongly filters them.
  - Excluding pixels drawn after the filter (P1 == raw within ±2): **98.6% within ±2, 99.5% within ±4**, MAE 0.47 / 0.68 / 0.80, bias +0.2 / −0.0 / +0.1.
  - P1 vs the stock-Xbox formula: 5.3% within ±2 (bias −11.5 / −5.8 / −4.5).
  - HUD and coronas are unfiltered and intact (`_raw_vs_p1_bad.png`).
- **Verdict: Confirmed.** P1 applies the PS2 colour-filter formula at night, and the stage-state restore holds. PS2 fidelity at this spot/time (a PCSX2 reference) is not measured yet.

## 2026-09-24 — PS2 test save (PCSX2 memory card)

- Our PS2 disc is v3.00 (Greatest Hits): MAIN is 196586 B, globals 43792 [C], and the save version ID is `F68D14FD` (the same as Xbox v2). v3.00 MAIN differs from Xbox v2 MAIN (+314 B), so an Xbox→PS2 conversion would need an IP remap. Most PS2 saves online are v1 (`4CDC1D64`, globals 43768), which is incompatible.
- Used a native v2 save instead: GTASnP `Kn1lF4` "Tagging up Turf" (the mission after Ryder), downloaded with all site edits off. It has no cheats, $50,723, and was saved in CJ's house.
  - Checks [C]: ID `F68D14FD`, globals 43792, scm size 196586 = our MAIN, checksum OK, and all 28 thread IPs land after a `wait` in our v3.00 `MAIN.SCM`.
- Folder `BASLUS-20946GTA50000` (one folder holds every slot's `N  Mission.b`):
  - `icon.sys` and icons come from a PCSX2 `.psu` (GameFAQs 34735). Its `icon.sys` is identical to that of a v3.00 save.
  - The 1 KB `BASLUS-20946GTA50000` header comes from a genuine v3.00 save (GameFAQs 25084).
- Imported into `E:\Emuladores\PCSX2\memcards\Mcd001.ps2` with `mymcplus` (pip). Original backed up as `Mcd001.ps2.bak_20260924`. `mymcplus check`: no errors; the save read back from the card is byte-identical. Card free space is now 108 KB, so extra in-game save slots will not fit on this card. Untested in-game.

## 2026-09-24 — Interior fidelity vs PS2 (CJ's house)

- PS2 reference: `Tagging up Turf` save (it loads in PCSX2 → PS2 save **[C]**), software renderer 1×, clock 06:30, weather 0. CJ teleported to the Xbox capture spot (2495.6, −1700.9, 1014.7), then `timescale 0`.
  - Framing differs: the PS2 camera is lower and closer, so only global stats and hand-matched patches are used.
  - Variants are in `captures/cj_house_int/vs_ps2/`, rows < 14 cropped. The Xbox frames are linearized (= default brightness), because this Xbox save has a raised brightness ramp.
  - "Stock" is an **estimate**: raw × (1 + 0.585·(c1·a1 + c2·a2)) = 1.22×. It is not a capture.
- Global metrics (linear): see the table.

| Metric | PS2 | Xbox stock (est.) | Xbox + P1 |
|---|---|---|---|
| luminance mean | 0.140 | 0.199 | **0.165** |
| luminance p5 | 0.003 | 0.046 | 0.036 |
| HSV saturation mean | 0.472 | 0.322 | 0.329 |
| R/B | 1.342 | 1.275 | 1.280 |

- Patches (ΔE76 vs PS2, stock → P1): blue wall 20.7 → 13.4; wooden floor 7.5 → 4.6; door 17.3 → 8.9; ceiling 1.3 → 4.2.
- As displayed with this save's brightness ramp, Xbox luminance is 0.28 vs PS2 0.14, so the brightness option alone dominates. Fidelity captures need the Xbox brightness at its default (identity ramp).
- **Reading:**
  - The interior filter is neutral, so P1 only removes Xbox's 1.22× brightening. That closes about 57% of the luminance-mean gap and most of the wall/door ΔE.
  - What remains is **not** ColourFilter: the PS2 has much deeper shadows (p5 0.003 vs 0.036) and far more saturation (0.47 vs 0.33), for example the PS2 floor at 26/12/2. These are candidates for lighting/ambient (H5/P4), radiosity (P3) or the PS2 brightness setting (unknown for this save) [H].

## 2026-09-24 — Xbox brightness default + night fidelity vs PS2 (Grove St, 00:00, SUNNY_LA)

**Xbox brightness [C]:**
- `SetBrightness(float b)` is at 0x274662. `b` = menu int `[0x6E79AC]` (FrontEndMenuManager+0x3C) × 1/512.
- Exponent = 1 − 0.7·b + 0.2 (constants 0x390AAC / 0x39087C / 0x390A24). The ramp is `pow(i/256, exp)·255` → `SetGammaRamp(1, 0x5F20F0)`.
- Callers: menu slider 0x11C9E9, "restore defaults" 0x11DDCB (writes 256 and calls with 0.5), and settings load 0x11BFC7/0x11C11B/0x163FCE.
- **The default 256 is not the identity**: exponent 0.85 (`128→141`), which brightens. The identity seen in the first session was an untouched buffer. The Ryder save had 384 (exponent 0.675).
- Set live to 256 by injecting `SetBrightness(0.5)` through GDB (hijacked at the PostFX Render entry 0x24C537, registers restored). Resulting ramp idx 1 = `[2,44,79,142,200,255]`, the known 0.843 ramp.

**Night captures:**
- Both consoles were at (2488.2, −1665.5, 13.3), heading 1.43, 00:00, weather 0, `timescale 0`. Xbox stock was captured live by restoring the original 0x24F007 bytes + blur byte 1, then P1 was put back and verified.
- The PS2 frame has no HUD/CJ and a slightly different camera, so the stats are regional with CJ/HUD/menubar masked. Files: `captures/grove_night/{ps2,xbox_stock_display,xbox_p1_display}.png`, `_ps2_stock_p1.png`.

| Region | Metric | PS2 | Xbox stock | Xbox P1 |
|---|---|---|---|---|
| frame | R/B | 0.73 | 1.07 | **0.95** |
| road | R/B | 1.19 | 1.92 | **1.56** |
| road | saturation | 0.306 | 0.476 | **0.366** |
| frame | lum (displayed, ramp 256) | 0.133 | 0.175 | 0.192 |
| frame | lum (ramp removed) | 0.133 | 0.130 | 0.144 |

**Reading:**
- P1 moves the night hue toward PS2 (teal instead of brown).
- The displayed image is brighter than PS2 because of the **Xbox display gamma at default brightness (exp 0.85)**. With the ramp removed, luminance matches PS2 within ~0.01. So PS2 ≈ Xbox framebuffer without a display ramp **[S]** (the PS2 save's own brightness setting was not read).
- Candidate data patch [H]: `0x390A24` 0.2 → 0.35 makes brightness 256 give exponent 1.0 (identity), leaving the slider working. Test it against the PS2 in another scene before adopting it.

## 2026-09-24 — Gamma fix test: `0x390A24` 0.2 → 0.35 (brightness 256 = identity ramp)

- Hypothesis: the remaining displayed-brightness gap to PS2 is the Xbox default display gamma (exp 0.85). Prediction: with brightness 256 mapped to the identity ramp, P1's luminance and mean-colour ΔE vs PS2 drop in both a day and a night scene.
- Method:
  - Live RAM poke `0x390A24` = 0.35, then `SetBrightness(0.5)` injected. The ramp becomes **exactly the identity** on all 768 entries [C].
  - Grove St (2488.2, −1665.5, 13.3), heading 1.43, weather 0, at 12:00 and 00:00. Both consoles frozen. Captures:
    - PS2;
    - Xbox P1 and stock (live), both captured with the fix;
    - "default gamma" variants: the default ramp applied to those same frames, exact because the fixed display = framebuffer.
  - Masks: HUD, radar, CJ, menubar. Files: `captures/grove_{noon,night}_gammafix/`, `_grid.png`.
- Result (PS2 vs Xbox; ΔE76 of the region's mean colour; dlum = Xbox − PS2):

| Scene / region | stock, default gamma | P1, default gamma | **P1 + fix** |
|---|---|---|---|
| noon frame | ΔE 21.6, dlum +0.034 | ΔE 5.7, dlum +0.055 | **ΔE 1.0, dlum +0.002** |
| noon sky | 35.4 | 7.6 | 7.5 |
| noon road | 25.2 | 11.3 | **6.9** |
| night frame | ΔE 3.8, dlum +0.017 | ΔE 3.8, dlum +0.031 | **ΔE 2.1, dlum −0.015** |
| night sky | 6.8 | 9.3 | **3.2** |
| night road | 7.9 | 3.5 | 4.9 |

- **Verdict: Confirmed.** The fix improves whole-frame fidelity in both scenes. With it, PS2 ≈ the Xbox framebuffer with no display ramp [S→C for these two scenes].
  - Side effect: the brightness slider still works (exp = 1.35 − 0.7·b, so it brightens only above 256).
  - Remaining gaps: noon saturation (−0.10), noon sky (PS2 more teal), night road slightly darker (−0.03). These are candidates for P2/P3.
- Live state left in the xemu session: `0x390A24` = 0.35, brightness 256.

## 2026-09-24 — Diagnosis of the two residuals after P1 + gamma fix (noon sky, night asphalt)

- **Region boxes were framing-confounded.** The PS2 camera sits lower and closer and is pitched differently, so the same box samples a different height of the sky gradient. Re-measured by content (sky/asphalt pixel classes) at matched luminance. **Both residuals are real:**
  - Noon sky at equal luminance: PS2 81/187/178 vs P1+fix 104/178/173 (PS2 less red); the PS2 sky reaches higher luminance.
  - Night asphalt at equal luminance: PS2 40/47/31 vs 42/44/27 (PS2 greener/bluer); median lum 42 vs 36.
- **E2 (live `0x5F4B1C` = 1, noon) → H2 Confirmed.** The Xbox radiosity is called after ColourFilter at 0x24CD7D with args limit `[0x6C88DC]` (int; 180 at noon, 90 at midnight), filterPasses 2, renderPasses 1, intensity 35 (`0x3CE7C4..D0`). With it on, only edges change (a slight shift/blur) and bright pixels get marginally darker (−0.3). There is **no bloom**.
- **Offline PS2-radiosity model** (PLAN §9 P3: downsample ×4, `2D − limit`, add ×intensity/k):
  - Noon: the sky gets closer (ΔE 6.3 → **3.3** with /255; /128 overshoots, 10.2, so H4 favours **/255**), but the whole frame gets worse (ΔE 1.1 → 3.3) because the ground passes the limit too.
  - The PS2 sky's lower R cannot come from an additive bloom, so part of the sky gap is already in the pre-filter sky [H].
  - Night: the model does not touch asphalt (below limit 90) and the frame ΔE goes 2.2 → 2.0.
- **E1 (lighting mult) ruled out here [C].** 0x24C6B6–0x24C75F: `L` (smoothed light level at the player, `[0x75865C]`, rate `pe_lightchangerate`, cap `pe_lightingbasecap`) gives `mult = 1 + (1 − L/cap)·pe_lightingbasemult`, which scales the ColourFilter colour bytes. Live at Grove St, midnight: L = 0.30 of cap 0.35 → mult 1.071 (Xbox 0.5) vs 1.057 (PS2 0.4). That is about 1%, negligible.
- **Night asphalt → H5 (building ambient) is the remaining candidate [S].** The PS2 − P1 difference at matched luminance is ≈ +2/+8/+7, i.e. a teal additive term that looks like extra night ambient. Not gamma, not E1, not radiosity.
  - For P4: the building-pipe constant-upload functions around 0x166E26 (c6D–c70, c77, c80/81, c74–76) do not fire in this scene.
  - A 400-hit log of `SetVertexShaderConstant*` saw only RW Im2D's c96 (0x2AB925). So the 3D pipes write their constants **inline into the push buffer**; RE target 5 has to find those writers.

## 2026-09-24 — P5 built: neutral display gamma (operand repoint, not a constant edit)

- **Correction to "Gamma fix test".** `0x390A24` is the compiler's pooled float 0.2, with ~335 references game-wide (raw operand search). Editing it changes unrelated systems, and the live test did that while its captures were taken. Reverted in RAM.
  - The ramp and fidelity results stand: those frames were frozen, and the ramp depends only on SetBrightness.
  - "Candidate data patch `0x390A24` 0.2 → 0.35" is **withdrawn**.
- **P5 as built [C]:**
  - `addss xmm0, [0x390A24]` at 0x27468E (`F3 0F 58 05` imm32) now reads `[0x390C44]`, an existing float 0.35 in the same constant pool.
  - `.rdata` flags 0x6: not writable.
  - Only the 4-byte operand at 0x274692 changes (`240A3900` → `440C3900`, 2 bytes differ).
  - Live: operand poked, pooled 0.2 untouched, `SetBrightness(0.5)` → exact identity ramp on all channels.
- `patches/p5_display_gamma.py`: guards the instruction bytes and the 0.35 value. Its `--selftest` models the game's ramp loop and reproduces all three live ramps: stock 256, Ryder-save 384, and fixed = identity.
- `dist/default_p1p5.xbe` sha1 9c4db1ab…; `work/xbox/gtasa_p1p5.xiso` (embedded XBE replaced at sector 348678 after verifying the stock bytes). Boot test pending.
- **P5 boot test (2026-09-24) [C]:** `gtasa_p1p5.xiso` boots and slot 2 loads. Live: P1 code, blur byte 0, P5 operand `440C3900`, pooled 0.2 intact. The save restores its own brightness (384 → exp 0.825 under P5, ramp `128→144`; stock at 384 gives `128→160`), so brightness is per-save state. Setting 256 (slider or "restore defaults") gives the exact identity ramp.

## 2026-09-24 — P1 pause-menu check (Phase 2 closed)

- `gtasa_p1p5.xiso`, pause menu (Map tab). A breakpoint at 0x24F007 never hits within 3 s → **ColourFilter is not called while the menu is up [C]**.
- Capture with P1+P5 vs live stock ColourFilter + blur on: **0 pixels differ** (max diff 0). Repeat P1 capture also identical. The menu renders normally, with no leaked stage state (`captures/pause_menu/_p1p5_vs_stock.png`).
- **Verdict: Confirmed.** Phase 2 in-game checks (interior, night, menu) are all passed.

## 2026-09-24 — Phase 3 prep: RE target 3a (ColourFilter quad) + P2 design notes

- **ColourFilter quad at 0x5C7318 (live) [C]:**
  - Vertices (stride 28):
    - v0 = (0, 0) top-left, UV (0.00049, 0.00098);
    - v1 = (0, 512) bottom-left;
    - v2 = (1024, 512) bottom-right;
    - v3 = (1024, 0) top-right.
  - Index buffer 0x3CE82C = (0,1,2, 0,2,3). This **matches SkyGfx's corner mapping** directly: left → v0,v1; top → v0,v3; right → v2,v3; bottom → v1,v2.
  - UV at +0x14/+0x18; the half-texel bias is already present.
- **Blur offsets `0x3CE808/80C/810/814` (left/top/right/bottom) read 16/16/16/16 live**: Xbox `stream.ini` value; the PS2 ships 8.
  - SkyGfx: off_u = pe·(W/640)/16/rasW, off_v = pe·(H/448)/16/rasH, with the copy raster 1024×512.
  - pe 8 → +0.5 texel (u and v), which with LINEAR gives the PS2's soft 2×2 blur of the pass-2 term. pe 16 → a full-texel shift, with no blur.
  - [S] The PS2 value 8 is needed; for the RAM test poke the four globals. The shipped mod gives the ini lines (PLAN §15).
- **Code cave candidate:** the Xbox blur pass 0x24ECAA–0x24EEA1 (0x1F8 B; dead since P1 sets 0x3CE7AD = 0).
  - It starts `push ebp; mov ebp,esp; sub esp,0x28; cmp byte [0x3CE7AD],0; …; je 0x24EE9F`, and its only known call is at 0x24CC89. Not checked yet: whether other callers exist.
  - Alternative: 34 free bytes left in P1's 300-byte ColourFilter slot. That is too small for UV shift + restore.
- **P2 requirements:** pass 2 only, texture filter LINEAR (RwRenderStateSet 9 = 2), then back to NEAREST. The UVs must be restored after the draw (0x5C7318 persists across frames, so shifts would accumulate).

## 2026-09-24 — P2 filter blur: built, live RAM test and E5 (Grove St 12:00, SUNNY_LA)

- **Hypothesis:** the PS2 softness is pass 2 of the colour filter sampling fb′ with LINEAR filtering at +pe/16 texels (pe = 8 → +0.5 texel, a 2×2 box). **Prediction:** the patched frame matches `predict_filter.predict(raw, c1, c2, shift=(0.5, 0.5))` within ±2 levels, and its Laplacian variance moves from P1's value to the PS2's.
- **Cave [C]:** the Xbox blur pass 0x24ECAA–0x24EEA1 (504 B) has exactly one reference, `call` at 0x24CC89 (rel32 scan of every section; no absolute pointers). The caller pops the two args itself, so NOP-ing the call is equivalent to P1's blur byte = 0.
- **P2 as built (`patches/p2_filterblur.py` → `.json`):** P1 plus blur is 439 B, which does not fit P1's 300 B slot. P2 is therefore self-contained and **supersedes P1**. `xbe_patch.py` refuses P1 + P2 because both patch 0x24F007.
  - `0x24F007`: `jmp 0x24ECAA`. Every caller lands in the new body, with the stack and ABI unchanged.
  - `0x24CC89`: the blur-pass call becomes 5 × NOP.
  - `0x24ECAA`: P1's code (`p1_colourfilter.build(blur=True)`, which emits the same bytes as v0.1 when `blur=False`; the selftest asserts this) plus, for pass 2: filter LINEAR, a stack copy of the quad 0x5C7318, and UVs += `pe/(16·rasW|rasH)`. The raster size is read from the copy raster, where RwRaster width/height sit at +0xC/+0x10 = 1024/512 [C]. The persistent quad is never modified.
  - Unlike SkyGfx, no `W/640`, `H/448` scale is applied: the Xbox renders 640×480 natively, and the PS2 meaning of the value is pe/16 of a framebuffer pixel.
- **PS2 pe globals [C]:** `0x668D28..0x668D34` (`$gp` − 0x2B48): 8, 8, 8, 8, followed by 1.0, 1.0, 0.0008 (`pe_lightchangerate`) and 0.35 (`pe_lightingbasecap`). Found by a batched PINE scan of $gp ± 32 KB. Poking them to 0 visibly sharpens the PS2 image, so they are read every frame.
- **Live RAM test (xemu, P1+P5 session, brightness 256 = identity ramp, timescale 0):** c1 66,66,48,a254, c2 166,129,60,a254. The mask drops rows < 14, the last 2 rows/columns, moving pixels and the HUD (91.9 % of the frame kept). Files: `captures/grove_noon_p2/`.

| Capture vs model | MAE R/G/B | within ±2 | within ±4 |
|---|---|---|---|
| P1 vs predict (no shift) | 0.68 / 0.76 / 0.34 | 98.2 % | 99.5 % |
| **P2 pe 8 vs predict (+0.5)** | 0.83 / 0.86 / 0.45 | **97.1 %** | 98.3 % |
| P2 pe 8 vs predict (no shift) | 2.91 / 2.76 / 1.79 | 59.9 % | 78.6 % |
| P2 pe 16 vs predict (+1.0) | 1.12 / 1.19 / 0.60 | 97.1 % | 98.1 % |

- **E5 (sharpness):**
  - The PS2 blur toggle (pe 8 ↔ 0, three alternating pairs): Laplacian-variance ratio **0.626**, repeatable to 5 digits.
  - Xbox P2/P1: 0.497 as captured. Through a simulated PS2 display resample (448 → 480 bilinear, the PCSX2 present path) it is 0.557.
  - Absolute Laplacian variance: PS2 0.0064, P1 0.0115 (+79 %), **P2 0.0056 (−12 %)**, P2 with pe 16 0.0067.
  - Mean colour, R/B ratio, saturation and luminance percentiles are unchanged from P1, since the blur does not shift colour.
- **Verdict:** P2 mechanism **Confirmed** (97.1 % within ±2, and the unshifted model is clearly rejected). E5 **Confirmed [S]**: the sharpness gap to PS2 drops from +79 % to −12 %. The rest is inside the confounds (the PCSX2 present-path resample, different framing and content, and an offline sweep that is not reliable because the model also blurs the HUD). If visual sign-off wants less blur, the knob is data-only: ini pe 6 = +0.375 texel.
- **Harness note:** the PS2 camera keeps swinging for about 20 s after a teleport even at timescale 0. Wait until frame-to-frame diffs settle (mean |d| ≈ 1) before paired toggles.
- **Build:** `dist/default_p2p5.xbe` (P2 + P5) has sha1 ed5c41e3…. `work/xbox/gtasa_p2p5.xiso` = a stock copy with the embedded XBE replaced after checking the stock bytes, and with the embedded `stream.ini` (sector 1998977, 197 B, same size) set to pe 8 (`\t16` → `\t\t8`; a copy is at `work/xbox/stream_pe8.ini`). Boot test pending.
- **P2 boot test (2026-09-24) [C]:** `gtasa_p2p5.xiso` boots, and slot 2 loads. Live: all P2 and P5 bytes equal the JSONs; pe offsets are 8 ×4, read from the ISO's edited `stream.ini`; blur byte 0x3CE7AD = 1, as expected (P2 NOPs the call instead). Grove St 12:00, c1 66,66,48,a254, c2 166,129,60,a254: P2 vs `predict(raw, shift=0.5)` = **99.0 % within ±2** (MAE 0.63/0.62/0.35) with the overlays and animated characters masked (help box, Stats panel, HUD, CJ, one pedestrian; 69.7 % of the frame kept). The unshifted model gets 58.1 %. The unmasked frame gives 93.2 %, and all of the excess is the translucent HUD boxes (drawn after the filter) and CJ's idle animation. The HUD renders crisp and complete. Files: `captures/grove_noon_p2boot/`.
  - Brightness after "set 256" in the menu read **284** (`[0x6E79AC]`, ramp max +4, not the identity). The captures were linearized with the captured ramp. For exact-identity captures use `work/session_tools/xbright.py 256`.
- **Visual sign-off (2026-09-24):** the user accepted P2 with pe 8 against the PS2. Phase 3 is closed.

## 2026-09-24 — Phase 4: P3 radiosity (RE targets 3b/4, build, E6 live)

**RE [C]:**
- Stock `CPostEffects::Radiosity` is **0x24DF8E–0x24E512 (1413 B)**, not ~2.4 KB: 0x24E513 (darkness quad), 0x24E55E and 0x24E665 are separate functions with their own callers. References: only `call` at 0x24CD7D (main: limit = `[0x5F4B1E]` ? `[0x3CE7CC]` 220 : timecyc `[0x6C88DC]`; filterPasses `[0x3CE7C4]` 2, intensity `[0x3CE7D0]` 35, eax = renderPasses `[0x3CE7C8]` 1; skipped while the darkness filter `[0x5F4B14]` is on) and 0x24CB32 (darkness filter: `[0x3CE7A4]` 45, 0, 255, eax 2). UV corrections `[0x3CE7D4/D8]` = 2/2. The same defaults as PC `CPostEffects::m_Radiosity*`.
- Render order: 0x24BB7B (copy) → ColourFilter → darkness filter + radiosity → … → radiosity 0x24CD7D. No copy between the filter and the radiosity: the stock function samples the **pre-filter** copy. It builds a 2-vertex-per-rect sprite list at 0x5DB7C0 and draws it as a tristrip through 0x263B40, which degenerates on Xbox (the E2 result).
- `0x24BB7B` = RwCameraEndUpdate (0x2977F0, jmp [cam+0x1C]) on the scene camera `[0x5B8528]`, RwCameraBeginUpdate (0x297800, jmp [cam+0x18]) on the postfx camera `[0x5F4B30]` (raster = the copy 0x5F4B28, 1024×512, confirmed live), 0x263368 (2D default states), then the full-screen quad 0x5C72A8 textured with the screen raster, then back. So "render into C" is just a camera switch; no new raster or Initialise patch is needed (RE target 3b is not needed for P3).
- Screen W/H `[0x5B8530]/[0x5B8534]` = 640/480.
- `pe_bRadiosity` → `atoi != 0` → byte `0x5F4B1C` (handler 0x1580C7; tokens split on `" ,\t"`). `devkit_memory` sets the same memory global as `memory` (0x39F334 = v<<10) plus a "devkit" flag that makes later `memory` lines ignored; in the Xbox ini both are 38000.
- **PS2 `m_bRadiosity` = `$gp+0x1658` = 0x66CEC8** (INIT.NM stream.ini handler `sb $v0, 0x1658($gp)` at 0x895C20, next to `pe_bottomy` at `$gp−0x2B3C`). Live: 1, read every frame.

**P3 as built (`patches/p3_radiosity.py` → `.json`, 978 of 1413 B):** SkyGfx's fixed-function PS2 radiosity (`postfx.cpp CPostEffects::Radiosity` @926616a3), on the two Xbox surfaces:
1. `0x24BB7B`: C = F (the filtered frame).
2. Downsample ×filterPasses, SkyGfx geometry (src [UC+0.5, dw+0.5] → dst [0, dw/2+1], LINEAR), ping-pong C → backbuffer corner (scene camera) → C strip x ≥ 640 (postfx camera; that strip is never on screen).
3. Highlight `2D − L` = stage-0 `ADDSIGNED2X` (9) with vertex grey d = 128 − L·128/255, merged into the last hop when it lands in C, else a 1:1 hop (odd filterPasses; no stock caller).
4. Restore the backbuffer 1:1 from C, then add the (dw+1)-texel highlight stretched to full screen: LINEAR, SRCALPHA/ONE, A = intensity (/255), ×renderPasses. filterPasses 0 (darkness filter): highlight inside the 1:1 composite.
5. COLOROP back to 4, `0x24BB7B` again (C = final frame, SkyGfx UpdateFrontBuffer), stock tail states.
- Self-check (`--selftest`): code fits, disassembles fully, calls only 0x24BB7B / camera begin/end / its own draw helper, one Im2D draw site; `model()` = the same operator in numpy (analytic flat-frame and single-dot cases).

**PS2 reference (Grove St 12:00, weather 0, software renderer 1×, `m_bRadiosity` toggled live):**
- Hypothesis: SkyGfx's PS2 path with the timecyc limit and /255 reproduces the PS2 bloom (H4: /255 vs /128). Prediction: `model(ps2_off, L, 2, I)` ≈ `ps2_on` with best fit at the Xbox's live limit (180) and 35.
- Result: PS2 on − off mean +4.8/+5.5/+4.5 (repeatable, on/on MAE 0.8). Grid fit over L ∈ {140…220}, I ∈ {25, 35, 50, 70}: **best L = 180, I = 35: MAE 1.02, bias −0.02/0.00/−0.01** (no radiosity: MAE 6.01). /128 (I 70) is clearly worse. UC/VC 2 beats 0 and 1 (MAE 1.02 vs 1.58/1.27). The residual is unstructured scanline noise (PS2 448 → 480 display resample; modelling it gives 0.94).
- Night (00:00, limit 90): the PS2 bloom is tiny (+0.14/+0.32/+0.07); model(90, 35) bias ≈ 0, MAE 0.167 vs 0.222 with no radiosity (consistent, weak signal).
- **Verdict: H4 Confirmed = /255 [C for these scenes].** The PS2 radiosity operator is SkyGfx's, with the timecyc limit and the stock 35.
- Harness: the **idle camera** (CIdleCam) starts panning after CJ is left idle, on both consoles, even at timescale 0 (it made the first PS2 night set unusable). Nudge the player, then capture quickly.

**E6, Xbox live RAM test (`work/session_tools/p3live.py`; `gtasa_p2p5.xiso` session, brightness 256 = identity ramp, timescale 0):** P3 poked into 0x24DF8E, `0x5F4B1C` toggled. Deterministic check: capture vs `model(flag-off frame, …)`. The HUD boxes and moving pixels (dilated 16 px) are masked, because the HUD is drawn after PostFX and the model would bloom it.

| Path | Scene / args | kept | P3 − off mean | vs model MAE | within ±2 |
|---|---|---|---|---|---|
| filterPasses 2 (highlight merged) | noon, 180/2/35/1 | 75.6 % | +8.4/+7.4/+4.5 | 0.08/0.20/0.02 | **100 %** |
| (same, model without UC/VC) | | | | 1.28/1.47/0.72 | 79.4 % |
| filterPasses 2 | midnight, 90/2/35/1 | 72.7 % | +0.3/+0.4/+0.2 | 0.02/0.03/0.01 | **100 %** |
| filterPasses 0 (darkness filter forced via `0x5F4B14` = 1, darkness alpha 170) | 45/0/255/2 | 89.8 % | +0.5/+0.8/+0.3 | 0.04/0.06/0.02 | **100 %** |

- The HUD is intact, with no edge or strip artefacts; the game keeps running (GDB responsive, frames repeatable to MAE 0.15). `ADDSIGNED2X` = 9 and drawing at x ≥ 640 in the postfx camera are confirmed by the 100 % match.
- **Verdict: E6 Confirmed**: P3 draws exactly the PS2 (SkyGfx) radiosity on the Xbox.
- Fidelity vs PS2 at noon (content classes; framing differs): **sky ΔE 6.8 → 3.9** (the "noon sky" residual after P1 + gamma is mostly radiosity). Ground ΔE 8.1 → 10.6 and frame 3.8 → 6.6 get worse, because the Xbox ground is already brighter than the PS2's *before* radiosity (142/106/56 vs PS2 no-radiosity 121/86/42) and the bloom grows with it. Since the operator matches, that gap is upstream (building/ground lighting, H5/P4, or framing) [H].
- **Build:** `dist/default_p2p3p5.xbe` (P2 + P3 + P5; sha1 d7e1d28c…) → `work/xbox/gtasa_p2p3p5.xiso` (a copy of `gtasa_p2p5.xiso`, both regions verified before the write). The embedded `stream.ini` is pe 8 + `devkit_memory\t38000\r\n` → `pe_bRadiosity\t\t\t\t\t1\r\n` (same 21 B, file stays 197 B; a copy is at `work/xbox/stream_pe8_rad.ini`). Boot test pending.
- **P3 boot test (2026-09-24) [C]:** `gtasa_p2p3p5.xiso` boots and the save loads (slot 1, now a copy of slot 2 re-saved with brightness 256). Live (`work/session_tools/p3boot.py`):
  - All P2, P3 and P5 bytes equal the JSONs.
  - pe 8 ×4; `0x5F4B1C` = 1 read from the ISO's `stream.ini`; memory 38000 (the `devkit_memory` swap is harmless); brightness 256 → identity ramp.
  - Grove St 12:00, limit 180, c1 66,66,48,a254, c2 166,129,60,a254: P3 vs `model(flag-off frame, 180)` = **100 % within ±2** (MAE 0.08/0.22/0.02; 66.2 % kept after masking the HUD, radar and phone help box, dilated 16 px, plus CJ's phone animation, his shadow and a pedestrian). The first pass (95.9 %) left the help box and the later animation unmasked.
  - Overlays drawn after PostFX are unchanged. Side-by-side for sign-off: `captures/grove_noon_p3boot/_signoff_grid.png`.
- **P3 pause-menu check (2026-09-24) [C]:** with the pause menu up, breakpoints at 0x24DF8E (radiosity) and 0x24C537 (PostFX Render) never hit within 3 s. Captures with `0x5F4B1C` = 1 / 0 / 1: **0 pixels differ** (`captures/pause_menu_p3/`).
- **Visual sign-off (2026-09-24):** the user accepted P3 against the PS2 (`_signoff_grid.png`). **Phase 4 is closed**; v0.3 candidate = `gtasa_p2p3p5.xiso`.

## 2026-09-24 — P3 interior check (CJ's house, both consoles, 12:00)

- Setup: `gtasa_p2p3p5.xiso` (slot 1), the user walked CJ into his house on both consoles (Xbox (2495.5, −1702.3, 1014.7) area 3; PS2 (2495.8, −1701.6, 1014.7)), clocks 12:00, then `timescale 0`. ColourFilter args c1 64,64,64,a128, c2 64,64,64,a254 (neutral). Files: `captures/cj_house_p3/`.
- **Interior radiosity limit `[0x6C88DC]` = 0 [C]**: every pixel passes, so H = clip(2D) and the bloom is a relative gain (≈ +27 % of 2D·35/255).
- PS2 radiosity on/off (55 % static px): on − off +5.3/+4.4/+3.9. Grid fit: **best L = 0, I = 35** (MAE 1.43, bias −0.6), next L = 10. So the PS2 uses the same interior limit 0 [C].
- Xbox P3 vs `model(off, 0)`: **100 % within ±2** (MAE 0.11; 71 % kept); P3 − off = +10.8/+9.5/+8.5.
- Same relative bloom on both consoles: blue wall 108 → 133 (PS2, ×1.23) vs 122 → 155 (Xbox, ×1.27); window +33 on both.
- **The absolute gap is upstream of P3 [C for this frame]:** before radiosity, the Xbox interior is already brighter in the shadows (median luminance 18 vs 8; floor 18/11/7 vs 6/1/0; mean 33.4 vs 27.7), matching the earlier "PS2 has much deeper shadows" interior result. At L = 0 radiosity scales that gap by ~1.3× (mean 35.0 PS2 vs 42.6 Xbox P3).
- **Consequence for Phase 5 [H]:** in this interior the Xbox is brighter in the darks than the PS2. That is the *opposite* of H5 (PS2 building ambient ×2 → brighter PS2 shadows, from the night-asphalt residual). P4 must be tested in both directions: interiors may use a different pipe/prelight path (the 11:11:10 night/day prelight packing, or a missing PS2 darkening), rather than a plain ambient ×2.

## 2026-09-24 — Harness: idle camera disabled on both consoles

- After 90 s with no pad input, `CIdleCam` hides the HUD and radar and pans to nearby peds. It does this even at `timescale 0`. It spoiled several capture sets, including the HUD-less Xbox noon frames and PS2 frames aimed at a pedestrian.
- Xbox [C]: `CIdleCam::Init` 0xD271F is called once, from the static initializer 0x2D55F3, with `gIdleCam` = **0x6C5248**. Init writes the kick-in time 90000.0 ms to +0x28, so the float is at **0x6C5270** (live 90000.0).
- PS2 [C]: the same layout sits at **0x6FFE20**, found by searching the savestate RAM for 2000.0 at +0x14, 1.0 at +0x24, 90000.0 at +0x28 and 5000.0 at +0x38. The kick-in float is at **0x6FFE48**.
- Live test on both consoles: kick-in 3000 → idle mode starts within 7 s (the HUD vanishes, then the camera pans). 1e30 → it exits and does not come back.
- New harness command on both consoles: `xemu_gdb.py idlecam off|on` and `pcsx2_pine.py idlecam off|on`. `off` writes 1e30 and lasts until the emulator reboots. It is in the CLAUDE.md capture rules and in the session capture scripts.
- Other harness additions this session:
  - `work/session_tools/ps2dump.py`: full PS2 RAM through a PINE savestate (slot 9) plus `eeMemory.bin` extraction. The .p2s is a zip with zstd entries, decoded with the zstd bundled with Poppler.
  - `trace.py`-style breakpoint loggers must remove the breakpoint, single-step and re-insert it on every hit. A plain `c` from a software breakpoint re-reports the same hit forever (RF set, no progress). That explains the earlier "building constant uploads 0x166E26 do not fire" note, which is wrong: they fire every frame.

## 2026-09-24 — Phase 5: RE target 5 (building lighting) + H5 test + P4 (E7)

**RE target 5 — the Xbox building lighting path [C]:**
- The building pipes upload their constants with plain `SetVertexShaderConstant1/4` calls, not inline push-buffer writes; the earlier 400-hit log only ever saw Im2D because of the tracer bug above. The per-frame setup functions are 0x166C70 (VS `[0x5F291C]`), 0x1675DF (DN pipe 0x53F20096, VS `[0x5F2928]`/`[0x5F292C]`) and 0x16A1E5. 0x16A1E5 is shared by the building VS `[0x5F2934]`/`[0x5F2940]` and by the vehicle VS `[0x5F2960]` and the unlit VS `[0x5F2984]`.
  - They upload: c0–c3 the transform; c13 the directional light and c15 the **ambient light**, each `min(RpLight colour, 1)` from pDirect `[0x5F4C00]` and pAmbient `[0x5F4BFC]`; c23 = (DN balance `[0x3C9DA4]` or `[0x3C9B10]`, 1−b); c32 = (0, 1, 0.5, 2).
  - Per material, 0x166EE3 uploads c20/c21/c22 from the D3DMATERIAL at 0x3D26C0, filled by 0x16AFAD: c20 = matCol·surfDiff, c21 = matCol·surfAmb.
- NV2A decoder (xemu vsh.c layout). All 8 building VS blobs (0x3C9B18, 0x3C9C00, 0x3C9DA8, 0x3C9E90, 0x3C9FB8, 0x3CA060, 0x3CA1C8, 0x3CA270) share one lighting core: **`oD0.rgb = (v1·c23.x + v2·c23.y)·c20 + c15·c21`**, clamped to [0, 1]. This is SkyGfx's `xboxBuildingVS`, exactly.
  - Declaration 0x3D25E0: v1 = NORMPACKED3 night colours (weight b), v2 = D3DCOLOR day colours (weight 1−b).
  - The blobs from 0x3CA480 on also light with c13/c16 (directional) and c14/c22 (specular). They are vehicle/ped shaders.
- The DN balance is a pure function of the clock (0x168918 via 0x11028D; setter 0x168824 clamps to [0, 1]). It is 0 at 12:00 and 1 at 00:00.
- pAmbient for buildings is `SetAmbientColours` 0x26409A → `AmbientLightColourForFrame` 0x5ECCC8 = timecyc ambient / 255 (A/255 exactly, live). The timecyc current colour set is at 0x6C8840. The ambient tables, laid out [hour][weather] u8, are at Xbox **0x56B8B8 / 0x56B800 / 0x56B748** (R/G/B) and PS2 **0x7073F0 / 0x7074B0 / 0x707570**.
- Interior (CJ's house, 12:00): c15 = 0, c13 = 0, DN = 0, so the Xbox interior is exactly `tex·day prelight·matCol`. Forcing D3D fog off (0x361872 `je`→`jmp`) changes 2.7 % of pixels by +0.02, so **fog is refuted** as the source of the interior dark gap. Forcing DN to 0.5 or 1 moves the Xbox away from the PS2 (the night set has brighter darks), so **the DN hypothesis is refuted**.

**H5 test (ambient sweep on both consoles, radiosity off, Grove St, weather 0; `work/session_tools/p4amb.py`):** timecyc ambient forced to A on every hour slot, then ΔOut = Out(A) − Out(0) per console.
- Frame means: PS2/Xbox ΔOut = **1.74–1.84** at 00:00 (A 64/128) and **1.73** at 12:00 (A 32).
- Registered facade, per pixel, 00:00: ambient term PS2/Xbox **1.78** (IQR 1.63–1.93); night-prelight term (A0) **0.75** for R and G. B is not usable: tiny values, and the PS2 darks are quantized in steps of 4.
- Texture-free ratio (P/g)PS2 / (P/g)Xbox, where the texture cancels per pixel: **0.47–0.54 at noon**, against 0.502 predicted by SkyGfx (prelight ×1, ambient ×255/128). At night it is 0.41.
- **Verdict: H5's mechanism is confirmed.** Relative to prelight, the PS2 adds the building ambient at ~2× the Xbox. **H5's prediction** ("doubling the ambient closes the dark gap") **is refuted**: the PS2 prelight term is also *weaker*, about 0.87× (day set) and 0.75× (night set) in absolute frame terms [S]. Whether that shared ~0.87 comes from lighting or textures is open [H]. The interior "PS2 darker in the darks" fits the same ~0.85–0.9 prelight factor (Xbox 96–200 → PS2 ×0.85–0.9; darks lower still).

**P4 (`patches/p4_building_ambient.py` → `.json`) [built]:** c15 × 2 on the building pipes only.
- A VS-operand edit (`mov r, c15` → `add r, c15, c15`) is **not possible**. In every blob that `mov` is paired with an ILU `mov oT0/oD0.w, …` that reads operand C. The first try broke the texture coordinates live: darker facade, lit windows.
- As built, the three 86-byte clamp blocks are rewritten in place (65 B each):
  - `c15 = minps(pAmbient, 1)`, then xyz doubled and w kept (the vehicle VS reads c15.w);
  - 0x166D91 and 0x167700 (building-only setups) are always doubled;
  - 0x16A30A (shared) is doubled only if RW's current VS `[0x3D4750]` is `[0x5F2934]` or `[0x5F2940]`.
- The selftest checks the stock block pattern, fit, full disassembly, that eax (pDirect) and xmm4 (1.0) are preserved, and that only the shared block carries the check.
- **E7 live (RAM, 00:00, A 0/64):** A0 frame P4 vs stock mean|d| **0.014**. Ambient response **2.00×** per pixel (IQR 1.98–2.03). PS2/Xbox ambient ratio 1.74–1.81 (stock) → **0.87–0.91** (P4).
- c15 log with P4 on:
  - building DN 0.1725 = 2 × 0.0863;
  - unlit `[0x5F2984]` 0.0863 and vehicle `[0x5F2960]` (0.189, 0.182, 0.112): not doubled [C];
  - building `[0x5F2940]` gets 0 on stock as well.
- **E7 verdict: the mechanism is confirmed**. P4 does exactly what it should to the ambient term.
- **Natural-scene fidelity (`p4fid.py`, radiosity as shipped, idle cam off) — P4 makes things worse:**

| Grove St, frame mean (median lum) | PS2 | Xbox stock | Xbox + P4 |
|---|---|---|---|
| 00:00 | 37/47/30 (37.3) | 36/44/29 (35.0) | 50/63/44 (53.7) |
| 12:00 | 111/84/47 (89.3) | 120/102/63 (104.0) | 131/102/63 (108.0) |

  - At night the stock total already matches the PS2. The sweep model predicts the PS2 night R mean at 0.75·25.5 (prelight) + 1.78·10.8 (ambient) = 38.3, against 37.4 measured, and P4 alone at 47 (49.6 measured).
  - **Conclusion:** P4 as planned (ambient ×2) must not ship alone. A faithful P4 needs ambient ×~1.75 **and** prelight ×~0.87 (day) / ×~0.75 (night), which is a 2-parameter model. Or skip P4, since the PS2/stock totals already agree at night.
  - Build for A/B only: `dist/default_p2p3p4p5.xbe` (sha1 b38df22e…). Not boot-tested; no ISO made.
- **Decision (user, 2026-09-24): option (a), the 2-parameter P4.** Next session starts with the texture check (PS2 vs Xbox TXD for a Grove St facade texture), then the refit and the building-pipe-only implementation. The step list is in PLAN §18 "Next session plan (P4 v2)".

## 2026-09-24 — P4 v2 step 1: texture check, prelight data check, PS2 display chain

**Texture check (offline, `work/tex/txdmean.py`; IMG reader `work/session_tools/imgtool.py`):**
- Hypothesis: the shared PS2 ≈ 0.87× factor is in the textures. Prediction: PS2/Xbox per-texture mean ≈ 0.87.
- Method: every TXD whose name contains `lae` in both `gta3.img`, decoded natively. PS2: PAL4/PAL8 (CSM1 bit 3/4 swap for PAL8), alpha ×255/128. Xbox: DXT via PIL `bcn`, 8888, PAL8. Only order-free stats are used: swizzling is a texel permutation, so no unswizzle is needed. The Xbox often has 2× the resolution (same texture set, same names).
- Result: **1483 textures, PS2/Xbox mean-luminance ratio 0.985 (IQR 0.982–0.987)**, per channel 0.981/0.987/0.981. `ganton01_lae2` (Grove facades): 0.982. **Refuted [C]:** the textures are equal; the 1.5 % is PS2 palette quantization.

**Prelight data check (`work/tex/prelight.py`, `pmatch.py`):**
- Hypothesis: the PS2 DFF vertex colours are darker than the Xbox ones.
- Formats [C]:
  - Xbox native geometry 0x510: the vertex buffer is the last numVerts × 28 B of the chunk: pos f32×3, night NORMPACKED3 (11:11:10 signed, /1023 /1023 /511), day D3DCOLOR (BGRA), uv f32×2.
  - PS2 native 0x510: per mesh {size, noPointers, data}. DMA REF tags alternate with empty CNT tags. Unpacks: V4_16 signed = position (/128), V2_16 = uv (/4096, padded to an even count), **V4_16 unsigned = colour: low byte day, high byte night**. ExtraVertColour 0x253F2F9 carries the same night colours.
- Result: vertices matched by position + uv in `compfukhouse3`, `carlshou1_lae2`, `ganghous01_lax`, `lae2_roads89` (97–99 % matched). **PS2 = Xbox within 1–3 %** for both day and night; for example `ganghous01_lax` day ratio 0.996/0.998/1.002, night 0.98. Materials: colour ffffffff and surfProps 1/0/1 on both (`compfukhouse3`). **Refuted [C]:** the vertex data are equal.

**PS2 display chain [C] (HUD check + GS state; `captures/hud_check/`, `work/session_tools/ps2entry.py`, `ps2disp.py`):**
- The Xbox HUD reads the exact CHudColours constants (money 54/104/44, clock 225, health 180/25/29), so with P5 and brightness 256 the Xbox display is the identity.
- The PS2 HUD reads 44–48/96/36–40, 216–220 and 176/20–24: always multiples of 4, and 5-bit levels or the mean of two.
- GS state from a PINE savestate: the render `FRAME` is **PSMCT32** (0xa0046, 640×448) with `DTHE = 0` (DIMX holds the standard matrix). The display `DISPFB2 = 0x51400` is **PSMCT16S** (FBW 10). `PMODE = 0x8067`: both circuits on, ALP 0x80, so a **50/50 merge of two circuits one line apart** (anti-flicker; circuit 1 has DH 446). The register slot mapping inside PCSX2's internal structures is inferred from the values [S].
- Model (`ps2disp.disp`): truncate to 5 bits (`<<3`, no dither), then average rows y and y+1. It reproduces the PS2 HUD (225 → textured 223 → 216; 180 → 176; 54/104/44 → 48/96/40). Mean effect −3.5 levels, which is large in dark scenes. It also explains the earlier note "the PS2 darks are quantized in steps of 4". PCSX2 is the software renderer at 1×, and ReShade is not loaded (its log is from 2024-10). This is the game's own register setup, so it is expected on real hardware too [S].
- Consequence: every PS2-vs-Xbox absolute comparison must apply `disp()` to the Xbox frame, or +3.5 to the PS2. Differences (on − off, ΔA sweeps) are unaffected.
- Sweep frame means, re-read with `disp()`:

| Set | raw PS2/Xbox | PS2/disp(Xbox) |
|---|---|---|
| night A0 (prelight only) | 0.66/0.70/0.59 | **0.75/0.79/0.76** |
| noon A0 | 0.86/0.88/0.85 | **0.88/0.91/0.91** |
| ambient slope (night Δ64 / noon Δ32) | 1.73 / 1.69 | unchanged |

- **Verdict:** the ~0.87 day / ~0.75 night factor is neither texture nor data. About 3.5 levels of it is the PS2 16-bit display truncation. The rest (frame level: day ≈ 0.90, night ≈ 0.77, ambient ≈ 1.7×) is in the PS2 render path [S]; its exact mechanism (VU1 building microcode) is still [H]. The sky is also a little darker on the PS2 (noon ≈ 0.92–0.97 after the correction, framing-limited), so the building-only scope of the residual is [S], not [C].
- **Decision (user, 2026-09-24): reference only.** The PS2 display chain is not emulated (the Xbox keeps 32-bit colour, no banding). `disp()` is used only to correct PS2 comparisons; P4 is fitted against the pre-display PS2 image.

## 2026-09-24 — P4 v2 step 2: refit with the display model (Grove St, fresh sweeps)

- Setup: `p4amb.py` on both consoles, radiosity off, weather 0, `idlecam off`. 12:00 A ∈ {0, 32, 64} → `captures/p4v2_noon/`; 00:00 A ∈ {0, 64, 128} → `captures/p4v2_night/`.
- Analysis (`work/session_tools/p4fit.py <dir> <A> [--show] [--curve]`):
  - The PS2 frame is registered onto the Xbox with a similarity search on gradients. Noon: scale 1.06, shift (−16, −36), corr 0.46. Night: 1.05, (−12, −28), corr 0.70.
  - Region: the main house box (Xbox x 200–465, y 70–245), sky excluded, pixels unclamped, the 30 % worst local gradient mismatch dropped.
  - g = mean(PS2_A0)/mean(disp(Xbox_A0)); ka = ΔPS2/ΔXbox.

| Set | region | g or n (disp) | g raw | ka |
|---|---|---|---|---|
| noon A32 | house | 0.914/0.919/0.881 | 0.877/0.875/0.802 | 1.80/1.81/1.82 |
| noon A64 | house | 0.891/0.899/0.857 | | 1.81/1.82/1.83 |
| night A64 | house | 0.825/0.830/(0.54) | 0.747/0.743/0.376 | 1.82/1.83/1.79 |
| night A128 | house | 0.777/0.792/(0.57) | | 1.75/1.72/1.71 |

- By storey the corrected ratio still rises with brightness: noon upper 0.94 vs ground 0.88; night upper 0.87–0.89 vs ground 0.56–0.72. So a small extra dark-end loss remains [H] (integer floors in the PS2 colour path, or registration). Blue at night is too dark to fit.
- **Model [S]:** PS2 building ≈ `t·(0.91·Pday·(1−b) + 0.80·Pnight·b + 1.80·A)`, then the PS2 display chain. ka/g ≈ 1.97, i.e. SkyGfx's ×2 ambient times the common ≈ 0.9 factor. Check on the natural night frame (p4fid table): 0.80·25.5 + 1.80·10.8 − 3.5 = 36.3 vs PS2 37 ✓.
- Scalar (channel-uniform) parameters for P4 v2: **g 0.91, n 0.80, ka 1.80**.

## 2026-09-24 — P4 v2 step 3–4: built, live RAM test, natural-scene fidelity

**Constant readers [C] (`work/session_tools/vsc.py`, xemu vsh.c fields: FLD_CONST dword1 bit 13, −96; A/B/C MUX = 3):**
- c23 is read **only by the 4 DN building blobs** 0x3C9B18/0x3C9C00/0x3C9DA8/0x3C9E90.
- The other 4 building blobs (0x3C9FB8/0x3CA060/0x3CA1C8/0x3CA270) light as `prelight·c20 + c15·c21`, without c23. The earlier "all 8 share the DN core" note is corrected here.
- No vehicle or ped blob reads c23. c15 is read by all 15 lit blobs.

**c23 sites [C]:** 0x166E4C (b = `[0x3C9B10]`) and 0x1677BB (b = `[0x3C9DA4]`), 41 B each: `movss b; movaps xmm1, xmm4(=1,0,0,0); subss; stores b, 1−b, xmm7(=0, xorps), xmm7`, then `call 0x35D0A0` with ecx 0x77 (c23). The shared setup 0x16A1E5 does not upload c23.

**P4 v2 (`patches/p4_building_ambient.py` → `.json`, 5 blocks):**
- c15 blocks: `min(pAmbient, 1) · (KA, KA, KA, 1)`; the shared block keeps the building-VS gate.
- c23 sites: `(b, 1−b, 0, 0) · (N, G, 0, 0)` via `unpcklps` + `mulps`.
- The constants (N, G, 0, 0) and (KA, KA, KA, 1) sit in the tail of block 0x166D91 (0x166DC7), after its `jmp`.
- G 0.91, N 0.80, KA 1.80. The selftest checks the stock patterns, full disassembly, the preserved registers (eax, xmm4, xmm7), the constant bytes and a scalar `model()`.
- A/B build: `dist/default_p2p3p4p5.xbe` (sha1 2d98911b…), not boot-tested.

**Live (RAM, `p4live.py on`, 00:00) [C]:** c23 = (0.800, 0, 0, 0) = N·b with b = 1; c15 = 0.1553 = 22/255 × 1.8 on the DN setup and the shared setup (building VS).
- `vslog.py` now steps off each breakpoint (the tracer bug in "Harness"); before this it logged the same Im2D hit 400 times.

**Natural-scene fidelity (`p4fid.py`, radiosity as shipped; `captures/p4v2_fid_{night,noon}/`), PS2 / disp(Xbox), 1.0 = match:**

| Region | 00:00 stock | 00:00 P4 v2 | 12:00 stock | 12:00 P4 v2 |
|---|---|---|---|---|
| house facade (registered) | 1.14/1.24/1.49 | **1.04/1.02/0.97** | 1.03/0.95/0.93 | **1.02/1.03/1.00** |
| ground y ≥ 255 | 1.07/1.18/1.32 | 0.90/0.88/0.81 | 0.90/0.86/0.84 | **0.93/0.96/0.93** |
| frame median lum (PS2 39.8 / 99.7) | 34.9 | 44.4 | 112.9 | 104.9 |

- **Verdict:** the facade is matched at both hours and the noon ground improves. At night the ground overshoots about 10–20 % (the Xbox is now too bright). Candidates [H]:
  - (1) the ground models are non-DN or use a different pipe (prelight ×1, ambient ×1.8);
  - (2) the street lamps' light pools at 00:00 differ between the consoles;
  - (3) weak registration on the near ground (parallax).
- **Decision (user, 2026-09-24):** no parameter compromise. The next session investigates the ground first (pipe/VS, alpha decals, lamp pools). The step list is in PLAN §18 "Next session plan (ground)". P4 v2 stays off in RAM, and the committed JSON holds the facade values.

## 2026-09-25 — Ground investigation (P4 v2 night-ground overshoot)

**Step 1, which pipe draws the ground (xemu live, `work/session_tools/p4mask.py`; `captures/p4v2_ground_mask/`):**
- Hypothesis (1): the ground is a non-DN building blob or another pipe, so it gets KA 1.8 but not G/N. Prediction: ground pixels respond to KA = 0 but not to c23 = 0.
- Method: P4 v2 on in RAM, Grove St 00:00, `timescale 0`. Zero the pooled constants one at a time: c23 (N, G) at 0x166DC7 → only DN-blob pixels change; KA at 0x166DD7 → only building-blob pixels change. Noise = P4 vs P4 again (0.2 %). The camera kept the user's angle (facing the overpass, not the house), but the asphalt in view is the same street.
- Result [C]: ground y ≥ 255 = **89.4 % DN blobs**, 0.5 % non-DN building, 10.1 % unaffected (CJ, radar). The whole frame is 67 % DN. **Refuted:** the ground gets exactly the facade's G/N/KA.

**Ground-only refit (offline, `p4fit.py` with `BOX=255,480,0,640` on the step 2 sweeps):**

| Set | facade (step 2) n or g / ka | ground n or g / ka |
|---|---|---|
| night A64 | 0.825/0.830 · 1.82/1.83 | 0.728/0.764 · 1.65/1.67 |
| night A128 | 0.777/0.792 · 1.75/1.72 | 0.736/0.775 · 1.67/1.68 |
| noon A32 | 0.914/0.919 · 1.80/1.81 | 0.856/0.879 · 1.64/1.66 |

- Every term on the ground is ≈ 0.93× the facade value, at both hours. So the gap is one multiplicative factor per surface, not a lighting term.

**Materials and textures (offline, `work/tex/means_lae.json` from step 1):**
- Materials of `lae2_roads89` / `lae2_landhub05`: colour ffffffff, surfProps 1/0/1 on both consoles [C] (same as the facade).
- The ground textures are outliers in the step 1 texture check, which only looked at the median [C]:
  - `plaintarmac1` (the asphalt): PS2/Xbox **0.918/0.935/0.921**, bottom 1.2 % of 1483 textures;
  - `dt_road_stoplinea` 0.946; `grasspatch_64hv` 0.91; the `sidewgrass*` textures 0.97–0.98;
  - the facade texture `comptwall4` is 0.982 (median 0.983).
  - The PS2 textures are 128², the Xbox ones 256² (a different mip or a re-quantized source).
- Asphalt relative to facade: 0.925/0.982 = **0.94**, matching the refit's ground/facade ratio of ≈ 0.93–0.94.
- **Verdict [S]:** most of the night-ground overshoot is texture content. The Xbox asphalt texture is ≈ 6 % brighter relative to the facades than the PS2 one. The lighting model (G/N/KA) holds on the ground too. What's left: P4 v2 at night measured 0.90/0.88 (R/G) against an expected ≈ 1.03 × 0.94 ≈ 0.97. That leaves ≈ 5–7 % open [H]: lamp pools (step 3) or the dark-end loss seen on the facade's ground storey. Blue at night is too dark to fit.
- **Decision (user, 2026-09-25): option (a).** The ground texture gap is asset content and is accepted: the Xbox keeps its own textures (PLAN §8), and P4 keeps the facade-fitted G/N/KA. Next: step 3 (lamp pools) on the remaining ≈ 5–7 %.

**Step 3, what's left at night (offline on `captures/p4v2_fid_*` + one Xbox live toggle):**
- Lamp pools (2) — **refuted.** A per-tile map of PS2/disp(Xbox P4) over the night ground is flat at 0.83–0.90. The only exceptions are the bottom row (edge effect of the `disp` line merge) and CJ's shadow edge. No lamp pool falls on the ground in this framing.
- Radiosity — **refuted.** Toggling the Xbox radiosity flag 0x5F4B1C with P4 on (00:00) changes the ground by only +0.4/+2.6/0 %. It is additive, so it cannot darken the PS2 ground.
- Registration (3) — **refuted.** Re-measured on registered pixels (`p4fit.py`, X0 = Xbox P4, P0 = PS2):

| | facade | ground | ground/facade |
|---|---|---|---|
| 12:00 | 1.01/1.03/1.00 | 0.93/0.96/0.93 | 0.92–0.94 (texture predicts 0.94 ✓) |
| 00:00 | 1.03/1.01/0.95 | 0.90/0.88/0.81 | 0.87 (texture 0.94 → ≈ 7 % extra) |

- **Verdict [S]:** the noon ground is fully explained by the asphalt texture. At night ≈ 7 % (≈ 3 levels at ground level ≈ 50) is left over. It shows only on dark pixels, and the facade's ground storey had the same dark-end loss in step 2. So it is a low-level nonlinearity in the PS2 colour path, not specific to the ground [H]. Candidates: integer floors in the VU1 colour output or in the GS `(tex·col)>>7` modulate. The ground-specific question is closed.

## 2026-09-25 — P4 v2 boot test (`gtasa_p2p3p4p5.xiso`)

- **Build:** `patches/p4_building_ambient.json` regenerated byte-identical (selftest OK). `xbe_patch.py` P2 + P3 + P4 + P5 → sha1 2d98911b…, equal to `dist/default_p2p3p4p5.xbe`. `work/xbox/gtasa_p2p3p4p5.xiso` = a copy of `gtasa_p2p3p5.xiso` (its embedded XBE was checked to be `default_p2p3p5.xbe` first) with the XBE at sector 348678 replaced; the embedded sha1 is 2d98911b…. The ISO's `stream.ini` is unchanged (pe 8 + `pe_bRadiosity 1`).
- **Boot [C]:** it boots, slot 1 loads, and all blocks are live in RAM (P2 3/3, P3 1/1, P4 5/5, P5 1/1). The radiosity flag is 1. The HUD is intact at 00:00 and 12:00 (`captures/p4v2_boot_{night,noon}/_grid.png`).
- **Boot = live poke [C]:** P4/stock on the ground at 00:00 is 1.198/1.346/1.581 (boot) vs 1.213/1.360/1.601 (live poke on the v0.3 ISO, `captures/p4v2_ground_mask/`), with nearly the same framing. At 12:00 it is 0.97/0.89/0.91. Stock vs stock-again: 0.01 % of pixels |d| > 2.
- Not done: a registered PS2 comparison on this set. The Xbox camera kept a manual angle (facing the overpass) while the PS2 faced the house, and Xbox CJ had a weapon drawn. `xemu_gdb.py` has no camera reset.
- **Fidelity on the boot build [C] (`captures/p4v2_boot2_{night,noon}/`, the user turned the Xbox camera to face the house, framing matched):** registered PS2/disp(Xbox), 1.0 = match (`p4fit.py`, X0 = Xbox variant, P0 = PS2):

| Region | 00:00 stock | 00:00 P4 v2 | 12:00 stock | 12:00 P4 v2 |
|---|---|---|---|---|
| house facade | 1.18/1.30/1.56 | **1.06/1.05/1.03** | 1.00/0.94/0.96 | **1.01/1.04/1.05** |
| ground y ≥ 255 | 1.03/1.16/1.34 | 0.88/0.88/0.83 | 0.89/0.85/0.83 | **0.92/0.96/0.92** |

  - This matches the live-poke set (facade 00:00 1.04/1.02/0.97, ground 0.90/0.88/0.81). The ground residual is the texture + dark-end loss described above (accepted).
  - Mean |1 − ratio|: facade night 0.35 → 0.05, noon 0.03 → 0.03; ground night 0.18 → 0.14, noon 0.14 → 0.07.
- Harness note: `p4fid.py` leaves `timescale 0`, which also freezes the camera. Set `timescale 1` before asking the user to reframe.
- **Visual sign-off (user, 2026-09-25) ✅** on `captures/p4v2_boot2_{night,noon}/_grid.png` and live. **Phase 5 is closed**; v0.4 candidate = `gtasa_p2p3p4p5.xiso`.

## 2026-09-25 — Phase 6A: RE target 7 (display filters)

- **Question:** does the Xbox game set a flicker or soft-display filter that could stand in for the PS2's 2-line display merge (Phase 5, `ps2disp.py`)?
- **Result [C] (static, `default.xbe`):**
  - `D3DDevice_SetFlickerFilter` (Cxbx symbol cache 0x35F820) = `AvSendTVEncoderOption(dev+0x1C28, 0xB, esi, 0)`, cached in 0x36F134/0x36F13C. Its only caller is D3D device init: `mov esi, 5; call 0x35F820` at 0x3637FF (the XDK default, 5).
  - `SetSoftDisplayFilter` is inlined in the same init: `AvSendTVEncoderOption(dev+0x1C28, 0xE, 0, 0)` at 0x363828–0x36382F, i.e. **off**.
  - Every other `call [0x375408]` (AvSendTVEncoderOption) is D3D-internal: option 6 (0x35FC19, 0x35FCE5, 0x36617C), 9 (0x363A6E, 0x36504C) and 0x10 (0x369525). No game code calls either filter API.
- **Reading:** the game ships the XDK defaults (flicker 5, soft display off). Both options act on the SDTV video encoder only, so they have no effect at 480p and are not emulated by xemu or Cxbx.
- **Verdict:** RE target 7 resolved. **No patch**: turning the soft display filter on (`push 0` → `push 1` at 0x363829) would be SDTV-hardware-only and unverifiable here, and the PS2 display chain is reference only (user decision, 2026-09-24). Listed as an optional hardware-only note for the Phase 7 README.

## 2026-09-25 — Phase 6C: grass, static RE and asset check

- **Xbox `CPlantMgr` [C]:**
  - `CPlantMgr::Initialise` 0x16D239 (caller 0x154321) loads `models\grass\plant1.txd` (string 0x38B270) into TXD slot `grass_pc` (0x38B118).
  - Textures: `txgrass0_0…0_3` go to 0x5F29B4…0x5F29C0 (set 0, pointer 0x5F29F4/0x5F29FC) and `txgrass1_0…1_3` to 0x5F29C4…0x5F29D0 (set 1, pointer 0x5F29F8/0x5F2A00); 0x38B204 goes to 0x5F2A54.
  - Model sets: `grass0_1…0_4` → 0x5F2A04 and `grass1_1…1_4` → 0x5F2A14. They are loaded by 0x16D168.
- The model loader clears the geometry flags PRELIT, NORMALS and LIGHT (`and ~0x38`) and sets MODULATEMATERIALCOLOR (`or 0x40`) at 0x16D1D9. So **Xbox grass is unlit**: out = tex · matCol, with no ambient and no directional term [C]. This is the same as PC SA.
- **Per-plant draw loop** 0x16B8A8 (stride 0x5C, caller 0x16BABA):
  - material colour = plant colour `+0x40..0x42` × intensity `+0x44`, `>> 8` (0x16B9E5–0x16BA0F);
  - set on all materials through 0x16B889 → callback 0x16B865;
  - then `call [edi+0x48]` (the RpAtomic render callback) at 0x16BA28.
  - The distance fade reads `[0x3CAF9C]`.
- **PS2 `CPlantMgr` (INIT.NM strings near 0x151D0) [C]:** textures `txgrassbig0`/`txgrassbig1` from TXD `particle`, and **four** model sets `grass0_1…grass3_4`, plus `PLANTS.DAT`. The Xbox uses the PC grass assets instead: the `grass_pc` TXD with 8 textures of 64×64, and two model sets. The PS2 assets are **already on the Xbox disc**: `models/grass/grass2_*.dff` and `grass3_*.dff`, and `txgrassbig0/1` inside `models/particle.txd`, whose texels have the same opaque-pixel means as the PS2's (the channel order differs only because of the decoder). The grass DFFs are byte-size-identical on both consoles.
- Texture means (opaque pixels): PS2 `txgrassbig0` 87/91/51 and `txgrassbig1` 120/121/106; Xbox `txgrass0_0…0_3` 82–92 / 83–99 / 34–65 and `txgrass1_0…1_3` 105–138 / 103–140 / 80–138. Comparable brightness, different art.
- **SkyGfx @926616a3 (`src/main.cpp`, `shaders/ps/grassPS.hlsl`):**
  - PS2 grass is `tex · matCol · 255/128` (`ps2ModulateGrass`, default = `ps2ModulateGlobal`);
  - `dualPassGrass` (default = `dualPassGlobal`) draws Z-write alpha ≥ ref first, then alpha < ref with Z-write off;
  - `grassAddAmbient` is an **optional, default-off** hack (it adds the timecyc ambient to the colour before the intensity `>>8`);
  - grass backface culling is on by default; there is also a far-distance tweak to 78.0 and an unused `ps2grassFiles` option.
- **Re-ranked hypotheses:**
  - **H7b** (PS2 ×2 modulate) first. Prediction: PS2/disp(Xbox) on grass pixels ≈ 2 in unclamped areas.
  - **H7a** (ambient) second.
  - **H7d (new)**: the grass look also differs in assets (PS2 texture/model set). That is PLAN §8 territory ("do not port PS2 textures or models"), although here it would only be a pointer/string patch to files already on the Xbox disc.
- **Decision (user, 2026-09-25): shading only.** The Xbox keeps its grass assets (consistent with PLAN §8 and the asphalt decision). Phase 6C tests and patches only the engine difference: ×2 modulate (H7b), then ambient (H7a).

## 2026-09-25 — Phase 6C: grass live tests (E8b, Glen Park)

- **Scene:** both consoles at (1970, −1180, ~23.5) Glen Park LS, weather 0, `timescale 0`, `idlecam off`; Xbox = v0.4 ISO (P4 on, identity ramp). Framing matches closely (the PS2 camera sits a little higher).
- **Grass masks (both consoles) [C]:**
  - Xbox: `work/session_tools/grass.py off` makes the per-plant draw loop 0x16B8A8 return at once.
  - PS2: `ps2grass.py off` puts `jr $ra` at the PS2 `CPlantMgr` render **0x489870** (SLUS_209.46). That function was found via `CPlantMgr::Initialise` 0x89CBB0 in INIT.NM (called at 0x88F170), which stores `txgrassbig0/1` at 0x846970/0x846974 and the atomic tables at 0x846980/0x846F80 (4 sets → 2 tables). It sets states zwrite/ztest/vtxalpha, SRCALPHA/INVSRCALPHA and filter LINEAR, and builds the geometry on VU0 (no RpAtomic).
  - PCSX2 picks up the code poke immediately.
  - Captures: 3× alternating on/off per console. Mask = |median on − median off| > 12 and > 4× the frame spread. Tools: `grasscap.py`, `grassfit.py` (Xbox through `disp()`), `grassvar.py`.
- **Xbox grass lighting [C]:** `CPlantMgr::Render`, loop 0x16BE9C. Per triangle, `CColLighting` byte +0x47 (day low nibble, night high nibble) gives `L = (day·(1−b) + night·b) · (1/30) · 255` (pool 0x390DB0 = 1/30, 0x3909E8 = 255; b = `[0x3C9DA4]`, the same DN balance as the buildings). Then plant colour × L `>> 8` (0x16BF61); the entry is added through 0x16B822; the draw loop applies × intensity `>> 8`. So L ≤ 127 = the PS2 GS 1.0 range.
- **Draw colours read live at 00:00 (breakpoint 0x16BA12):** RGB 3–22 (the lawn triangles mostly have night nibble 0, so L = 0 and the blades are near black on both consoles), **alpha 0x28 = 40** (faded plants 7–31).
- **H7b (SkyGfx ×255/128 on RGB) — refuted as the main effect.** Noon, stock: grass PS2/disp(Xbox) = 0.94/1.04/1.01 (equal).
- **Night gap [C]:** grass/ground luminance PS2 0.34 vs Xbox 0.56 (the PS2 grass covers the lawn more darkly). The night-weight test (N_g 0.45–1.0 through an operand repoint at 0x16BF4C) changes nothing, because the night nibble is 0. **H7e (night lighting) refuted.**
- **Mechanism [S]:** the plant alpha byte 40 means 40/255 = 0.16 in D3D but 40/128 = 0.31 on the PS2 GS (128 = 1.0). The Xbox port doubles the PostFX timecyc alphas for this reason (PLAN §1), but not the grass alpha.
- **Live variants** (`grassmod.py`; a cave in P3's 0xCC padding 0x24E360+ doubles bytes of the draw colour with a 255 clamp, site 0x16BA12 `call cave; nop×4`). Grass/ground luminance ratio (1 = invisible grass):

| Variant | 00:00 (PS2 0.338) | 12:00 (PS2 0.699) |
|---|---|---|
| stock | 0.559 | 0.756 |
| **A: alpha ×2** | **0.426** | **0.670** |
| C: RGB ×2 | 0.578 | 0.829 |
| AC: both | 0.452 | 0.780 |

- **Reading:** A is closest at both hours (it closes ≈ 60 % of the night gap and overshoots the noon gap slightly: 0.670 vs 0.699). RGB ×2 moves noon away from the PS2, so the PS2 grass RGB is not effectively doubled [S]. The residual is consistent with the different grass assets (PS2 `txgrassbig` 64×256 vs Xbox `txgrass` 64×64; different density and placement: Xbox mask 3.7 % vs PS2 1.0 % at noon), which are kept by decision. Absolute grass colour PS2/disp(Xbox) favours stock/AC at noon, but it is confounded by the lawn itself differing (ground PS2/disp(Xbox) 0.99/1.12/1.30).
- **Verdict: H7 (PS2 grass alpha = 2× Xbox) supported [S]; RGB ×2 refuted.** Visual grid: `captures/grass_glen_noon2/_grid.png`.
- **Decision (user, 2026-09-25): build P6c = alpha ×2.**
- **Source of the alpha [C]:** it is the `plants.dat` colour column **A** (Xbox == PS2 file except 2 ModelID fields; values 16–200, mostly 40/50). It is parsed into definitions at 0x5F2EB0–0x5F428C (RGBA dword, stride 0x28). Live, `work/session_tools/plantsa.py x2` sets A = min(2A, 255) in those RAM definitions and gives **the same frame as the draw-time cave** (0.15 % of pixels > 4 vs 5.57 % against stock; grass/ground 0.670 = cave A). The fade path already clamps to 255 (0x16B985); the near path uses A as-is, and the file's A > 127 rows must clamp (310 would wrap as a byte).
- No free code cave exists outside the committed patch JSONs (no ≥ 24-byte 0xCC run in `.text`; the P3 padding belongs to P3's JSON entry, and `xbe_patch.py` refuses overlaps). So **P6c is data-only** and the XBE is untouched.
- **P6c as built (`patches/p6c_grass_alpha.py`):** `work/xbox/plants.dat` (stock sha1 5576de10…) → `work/xbox/plants_p6c.dat` (sha1 7588d60b…, same 9887 B: a field that gains a digit takes one tab from the separator before it). The selftest checks the line transform, the clamp, comment lines, and, on the local stock copy, that only column A changes.
- **v0.5 candidate:** `work/xbox/gtasa_v05.xiso` = a copy of `gtasa_p2p3p4p5.xiso` (stock `plants.dat` verified at sector 1999020 first) with `plants_p6c.dat` written in place. The embedded XBE is unchanged (2d98911b…). Boot test pending.
- **Heat haze (user question) [C]:** `CPostEffects::HeatHaze` 0x24D7E2 is present on the Xbox, with one call in PostFX Render at 0x24CE9F. It is gated by the weather heat-haze intensity `[0x5E62B4]` against `[0x5F4BCC]` (or a force flag). It is never active in the LS weather-0 test scenes. PS2 parity untested [H]: candidate 6D.

## 2026-09-25 — Heat haze "missing on Xbox" = harness artefact (frozen clock)

- **Report (user):** at Glen Park 12:00, weather 0, the PS2 shows heat haze and the Xbox does not.
- **Xbox gate (PostFX Render 0x24CE3E–0x24CEA5) [C]:**
  - force byte `[0x5F4B09]` → HeatHaze(1.0);
  - otherwise, if `HeatHazeFXControl` `[0x5E62B8]` > 0 (or flag `[0x608AF8]`), it calls `CPostEffects::HeatHaze` 0x24D7E2 with intensity `CWeather::HeatHaze` `[0x5E62B4]`.
  - Live: control 1.0, but **intensity 0.0**.
- **Where the intensity comes from [C]:** `CWeather::Update` 0x260908–0x260A5D. The control is 1 for weather 0/0xB/0x11/0x12 (old or new). The intensity is a ramp `[0x74AEE0]` (0..1) × the control.
  - The ramp moves **only when the game minute changes** (0x260972: minute `[0x55F3DE]` vs last `[0x3D2B40]`): +0.05 `[0x3CE788]` per minute inside hours [10, 19) (`[0x3CE780]`/`[0x3CE784]`), and −0.5 `[0x3CE78C]` per minute outside them or in interiors.
- **Cause:** `xemu_gdb.py clock` / `pcsx2_pine.py clock` freeze the minute (ms-per-minute 0x7FFFFFFF), so each console keeps whatever ramp it had when frozen. The Xbox had come from 06:00 → ramp 0. The PS2 still had its daytime ramp.
- **Check:** ramp poked to 1.0 → HeatHaze 1.0, and the Xbox draws an animated edge distortion (5.7 % of pixels vs off; 6.4 % between two "on" frames 1 s apart, even at `timescale 0`). `captures/heathaze/`.
- **Verdict:** the Xbox heat haze works; there is no missing effect. **Harness rule:** captures in 10:00–19:00 with weather 0/0xB/0x11/0x12 must set the ramp equally on both consoles (Xbox `0x74AEE0`; the PS2 address is still to be found), or let the clock run ≥ 20 game minutes before freezing. Earlier noon sets (Grove St, Glen Park) may carry a PS2-only haze. It is an animated edge shift, so it adds noise but no colour bias. PS2/Xbox haze parity (strength, shape) is untested [H] → 6D.
- **Visual check (user, 2026-09-25) ✅:** with the Xbox ramp at 1.0, the Xbox heat haze looks the same as the PS2's live (Glen Park, 12:00, weather 0). **6D closed**: no patch.

## 2026-09-25 — P6c boot test (`gtasa_v05.xiso`)

- **Boot [C]:** v0.5 boots and slot 1 loads. The XBE blocks are live (P2 3/3, P3 1/1, P4 5/5, P5 1/1; unchanged from v0.4). All 61 parsed plant definitions carry the P6c alpha (0 stock-only values). Brightness 256, radiosity flag 1.
- **Boot = live poke [C]** (Glen Park, the user reframed to the earlier view; Xbox heat-haze ramp 0 as in the live sets; A/B in the same session by writing the stock or P6c alpha into the RAM definitions with `work/session_tools/plantsab.py`). Grass/ground luminance:

| | 12:00 | 00:00 |
|---|---|---|
| v0.5 P6c | **0.668** (repeat 0.668) | **0.432** |
| stock alpha (v0.4) | 0.756 | 0.565 |
| live cave A / stock (earlier) | 0.670 / 0.756 | 0.426 / 0.559 |
| PS2 | 0.699 | 0.338 |

- Harness note: with the Xbox haze ramp at 1 the noon ratio reads 0.608. The animated distortion enters the spread filter and biases the mask, so grass metrics need the same haze state on both consoles, or haze off on the Xbox, with the PS2 frames judged by eye.
- Sign-off grid: `captures/grass_glen_noon_v05ab_p6c/_signoff_grid.png`.
- **Decision (user, 2026-09-25): P6c rejected on visual sign-off.** The user prefers the v0.4 grass (stock alpha, middle column of the grid) to the more PS2-like P6c. **v0.4 stays the release candidate**; P6c is not shipped. `patches/p6c_grass_alpha.py` is kept as a documented, opt-in data patch (the mechanism finding stands [S]). `work/xbox/gtasa_v05.xiso` is not a candidate.

## 2026-09-25 — Phase 6B: foliage alpha test (E8a), state RE on both consoles

- **Hypotheses:**
  - H6a: the PS2 GS AFAIL = FB_ONLY (failed pixels still write colour, but not Z) while the Xbox discards them;
  - H6b: a different reference;
  - H6c: no difference.
- **PS2 [C]** (`work/ps2_ee_foliage.bin`, EE RAM from a PINE savestate, Glen Park 09:38; GIF A+D qwords with register 0x47/0x48 counted in the resident display lists):
  - TEST_1 = **0x5140B** ×1107 and 0x3140B ×128: **ATE 1, ATST GEQUAL, AREF 64 (of 128 = 0.5), AFAIL FB_ONLY**, ZTE 1 (ZTST GEQUAL/GREATER);
  - the ATE 0 variants carry the same fields;
  - a few special draws use GREATER with AREF 8–51 (still FB_ONLY), and 6 use RGB_ONLY.
  - So on the PS2 **no alpha-tested pixel is discarded**. Pixels below 0.5 are still blended into the colour buffer and only skip the Z write. This is exactly what SkyGfx's `dualPass` emulates.
- **Xbox [C]** (`work/session_tools/alphalog.py`: breakpoints on the building setups 0x1675DF / 0x166C70 / 0x16A1E5; D3D simple render states at D3D_g_RenderState 0x36E288, indices 0x39–0x40 → NV2A DEPTH_FUNC, ALPHA_FUNC 0x36E370, BLEND_ENABLE 0x36E374, ALPHA_TEST_ENABLE 0x36E378, ALPHA_REF 0x36E37C, SFACTOR, DFACTOR, DEPTH_MASK 0x36E388; mapping from the method table 0x381BD0):
  - building draws run with ALPHA_FUNC **GREATER**, ref **140 or 100** (plus 0–2), and z-write on;
  - a failed pixel is discarded.
  - The refs come from the game: `push 0x8C` (imm32) at 0x10507B (render-list pass, skipped when `[0x5F273C]` ≠ 0) and `push 0x64` at 0x266848 (per-entity, unless entity flag +0x12 & 8), both `RwRenderStateSet(30 = ALPHATESTFUNCTIONREF, …)`.
  - (0x360610 DrawIndexedVertices only saw one 2D batch caller, 0x2A0F19. The 3D pipes do not go through the three symbol-cache draw entries, so the state is read at the setups.)
- **Verdict: H6a confirmed [C]** (both consoles read from bytes and state). The Xbox cuts foliage at alpha 100/140 of 255 (0.39/0.55); the PS2 keeps every pixel, blended, and cuts only the Z write at 0.5.
- **Live approximation** (`work/session_tools/aref.py 2`: both refs → 2; faint pixels are drawn and blended, but still write Z, so it is not the PS2 dual pass): 3.7 % of pixels change at Glen Park 09:38, mostly palm fronds and bush edges, which get softer and fuller. Crops: `captures/foliage_glen/_ref_zoom.png`. The faithful fix is a dual pass (pass 1: ref 128 with Z write; pass 2: alpha < 128 with Z write off). No free code cave is outside the committed JSONs (see "Phase 6C"), so a dual pass would have to live inside an existing patch's reserved bytes (P3's padding).
- **Visual grid (user camera, Glen Park 09:38 on both, Xbox haze 0):** `captures/foliage_user/_signoff_grid.png` (PS2 | Xbox v0.4 | Xbox refs 2), plus the noon grid `captures/foliage_glen_noon/_signoff_grid.png`. The central palm crown is the same tree in all three: the PS2 fronds are thicker and softer; Xbox stock is thinner, with cut-out gaps; refs 2 are in between.
- **Decision (user, 2026-09-25): dual pass** (technically the most correct: depth-correct solid part plus soft blended fringe, as the PS2 GS does in one pass with FB_ONLY).
- **Draw path [C]:**
  - building render CB (DN pipe) 0x167852 (registered by pointer at 0x167C04);
  - per mesh: 0x166B49 (material → 0x16AFAD), 0x166EE3 (c20/c21), then the mesh helper 0x16AD9A (textures, then **the one draw**: `call 0x2A0F00` at 0x16AFA3);
  - 0x2A0F00 = RW flush of deferred states 0x2A0230 + `D3DDevice_DrawIndexedVertices` 0x360610, return 0x2A0F19;
  - 0x16AD9A has 5 building-pipe callers (0x167317, 0x167A55, 0x1680D2, 0x16864C, 0x16965A).
  - `RwRenderStateGet` = `[0x75DE84]`; RW 3.6 states 8 ZWRITEENABLE, 29 ALPHATESTFUNCTION (2 LESS, 7 GREATEREQUAL; e.g. `push 7; push 0x1D` at 0x2166C2), 30 ALPHATESTFUNCTIONREF.
- **P6b prototype (`patches/p6b_dualpass.py`, selftest OK, 220 B; live `work/session_tools/dualpass.py on`, cave in P3's padding 0x24E360):**
  - site 0x16AFA3 → `call cave`;
  - the cave flushes, and if D3D ALPHA_TEST_ENABLE and BLEND_ENABLE are both on: pass 1 GEQUAL 128 (Z write as set), pass 2 LESS 128 with Z write off, then restores the three RW states; otherwise it tail-jumps to the single draw.
- **Live [C]:** the game runs; 10.9 % of pixels change at the palm scene (Glen Park 09:38, user camera). The changes are on the palm fronds (fuller and softer, visibly closer to the PS2 crown) and on a distant glass tower that now draws its below-ref pixels translucent instead of cut (PS2 FB_ONLY does the same); the smoke plume is animated noise. Grid: `captures/foliage_user/_dualpass_grid.png`; change mask `_dual_mask.png`.
- **Visual sign-off (user, 2026-09-25) ✅ of the live dual pass** ("the dual-pass result is much better"; A/B toggled live).
- **P6b as built:**
  - `patches/p6b_dualpass.py` → `.json` (selftest OK). Cave = **0x24F00C–0x24F132**, the stock ColourFilter body that is dead under P2 (P2 writes only the 5-byte `jmp` at 0x24F007). A scan of every section finds no external rel32 jump/call and no absolute pointer into that range. 220 B are used.
  - The JSON carries `"requires": ["p2_filterblur"]`; `tools/xbe_patch.py` gained `requires` (selftest OK) and refuses P6b without P2 (checked).
  - The live prototype moved to the JSON bytes (`work/session_tools/dualpass.py`): same effect (8.0 % of pixels vs stock at a palm/bush view; 0.5 % dual vs dual).
- **Build:** the P2 + P3 + P4 + P5 rebuild still gives sha1 2d98911b… (v0.4 unchanged by the patcher edit). `dist/default_p2p3p4p5p6b.xbe` sha1 **2d1829b5…** → `work/xbox/gtasa_p2p3p4p5p6b.xiso` (a copy of the v0.4 ISO with the XBE at sector 348678 replaced after checking it; stock `plants.dat`; `stream.ini` as v0.4). Boot test pending.

## 2026-09-25 — Cleanup after Phase 6 (user: "delete all the trash")

- Removed:
  - the rejected P6c artefacts: `patches/p6c_grass_alpha.py`, `work/xbox/plants_p6c.dat` and `work/xbox/gtasa_v05.xiso`. The mechanism and the exact transform (A → min(2A, 255), keep the file size by trimming a tab) stay documented above;
  - the scratch captures `captures/grass_scout`, `grass_glen_night_n0.*`, `grass_glen_noon_v05` and `foliage_json`;
  - the session tools of rejected paths (`grassn.py`, `grassmod.py`, `grassvar.py`, `plantsa.py`, `plantsab.py`, `aref.py`).
- Kept:
  - every capture set cited above;
  - `work/ps2_ee_foliage.bin`, the evidence for the PS2 TEST histogram;
  - the harness tools `grass.py`, `ps2grass.py`, `grasscap.py`, `grassfit.py`, `alphalog.py`, `bphits.py` and `dualpass.py`.

## 2026-09-25 — P6b boot test (`gtasa_p2p3p4p5p6b.xiso`)

- **Boot [C]:** v0.5 boots and slot 1 loads. Live blocks: P2 3/3, P3 1/1, P4 5/5, P5 1/1, **P6b 2/2**. Brightness 256, radiosity flag 1, pe 8 ×4.
- **A/B on the boot build** (`dualpass.py off/on` restores the stock bytes and re-applies the JSON bytes; heat-haze ramp 0; `timescale 0`):

| Scene | dual vs stock (px > 8) | dual vs dual | what changes |
|---|---|---|---|
| Glen Park 09:38 | 1.67 % | 0.21 % | tree canopies, bushes, CJ idle outline |
| Grove St 12:00 | 3.87 % | 0.23 % | palms/trees, power lines (thin alpha textures now continuous), CJ outline |
| Grove St 00:00 | 2.04 % | 1.39 % | same, weaker |

- Opaque geometry (road, house walls, the overpass, the P4-lit facades) is unchanged, and the HUD is intact. Files: `captures/p6b_boot_{glen,grove}/`.
- Not done yet: the pause-menu check.
- **Pause-menu check [C]** (Map tab): breakpoints at the P6b cave 0x24F00C and the site 0x16AFA3 never hit within 3 s each. The menu captured with dual pass on vs off: **0 pixels differ**; on vs on: 589 px, the blinking player marker. `captures/pause_menu_p6b/`.
- **Phase 6 closed (2026-09-25).** v0.5 candidate = `work/xbox/gtasa_p2p3p4p5p6b.xiso` (P2 + P3 + P4 v2 + P5 + P6b; XBE sha1 2d1829b5…; stock `plants.dat`; `stream.ini` pe 8 + `pe_bRadiosity 1`).

## 2026-09-25 — Harness: live code swaps only at a safe point

- **Incident:** a live `modswap.py stock` (stock bytes over all 12 mod blocks) hung the Xbox. EIP stayed at kernel 0x800151EF with a fixed ESP, and the frame no longer changed.
- **Cause:** the guest had been stopped at an arbitrary point, here inside the P6b cave's draw call. When that call returned, it ran into the restored stock ColourFilter bytes. The earlier Grove St swaps were lucky.
- **Rule:** write patch bytes only with the main thread stopped at the PostFX Render entry **0x24C537**. It runs once per frame after all 3D pipes, and no patched function is on the stack there. Now in `work/session_tools/safepoint.py` (`write_safely`), used by `modswap.py` and `dualpass.py`. Earlier one-block tools (p3live, p4live, grass…) wrote at arbitrary stops too. They worked because their code is rarely on the stack; prefer `write_safely` for any new live poke.

## 2026-09-25 — Showcase grids (for posting)

- Paired captures with the user's framing on both consoles: weather 0, clock frozen, Xbox heat haze 0. The Xbox "original" column is taken live: `modswap.py stock` restores all 12 blocks, the radiosity flag 0 and pe 16, and applies brightness 256 through SetBrightness, giving the stock ramp exponent 0.85. The mod is swapped back afterwards, and every swap is done at the safe point.
- Scenes: Grove St 12:00 / 19:00 / 00:00, and Glen Park 09:38 (palm canopies zoomed).
- Output: `captures/showcase/_tweet_grove_{1200,1900,0000,all}.png`, `_tweet_glen_palms.png` (`work/session_tools/tweetgrid.py`).

## 2026-10-12 — Phase 7: release package v0.5 (xdelta + installer), clean tests

- **Lost ISOs (noted 2026-10-12):** `work/xbox/` held only `gtasa_stock.xiso`. Both the v0.4 and v0.5 ISOs were gone, deleted after 2026-09-25 with no log entry. `dist/default_p2p3p4p5p6b.xbe` (sha1 2d1829b5…) and `work/xbox/stream_pe8_rad.ini` (sha1 dda7e888…) were intact, so the release is built from them.
- **Package:** `dist/SA-PS2Atmosphere-v0.5.zip` holds `README.md`, `apply_patch.py`, `xdvdfs_extract.py` and `default.xbe.xdelta` (1439 B). The xdelta3 3.1.0 encode uses `-9 -S none -A=default.xbe//default.xbe/`. The first encode had lzma secondary compression, which older decoders lack, and named the internal file `default_p2p3p4p5p6b.xbe` in its app header; both were removed. Round-trip decode → sha1 2d1829b5… [C].
- **Installer [C]** (run from the unzipped package, `py -B`):
  - Folder (copies of the extracted Rev 1 `default.xbe` + `stream.ini`): patched to 2d1829b5… / dda7e888…, with `.bak` files equal to stock. A re-run prints `already patched` for both files. Without xdelta3 it exits with the help message.
  - Wrong input (1 byte flipped in `default.xbe`): refused, exit 1. `stream.ini` is untouched and no `.bak` is written, because both files are checked before any write.
  - Image: `work/xbox/gtasa_v05_release.xiso` is a copy of `gtasa_stock.xiso`. Files are located through `xdvdfs_extract.image_files` (default.xbe sector 348678, stream.ini sector 1998977) and patched in place. Full compare against stock: 2436 bytes differ, **0 outside the two files**, and the embedded sha1s are 2d1829b5… / dda7e888…. A re-run prints `already patched`.
- **Boot (xemu, `dvd_path` → `gtasa_v05_release.xiso`) [C]:** `modswap.py state` polled every 15 s shows **12/12 mod blocks** from the first poll. The radiosity flag `0x5F4B1C` goes 0 → **1 at ~135 s**, when the game reads `stream.ini`. pe reads 8 ×4 throughout, but the stock XBE's .data default is already 8 (only the ini's `16` changes it), so pe = 8 is consistent, not proof [S]. In game at CJ's house, 06:00: HUD intact. `captures/release_v05/boot.png`.
- Not done: real hardware (none available here); a GUI xdelta decoder (Delta Patcher / xdelta UI) on the `.xdelta`.
- **Visual sign-off (user, 2026-10-12) ✅** on `gtasa_v05_release.xiso`, in game at Grove St: "all is fine". **Phase 7 closed.**

## 2026-10-12 — Release renamed v1.0; installer backs up images too

- The user named this release **v1.0**. It is the v0.5 build with the same XBE and ini SHA1s. The package is now `dist/SA-PS2Atmosphere-v1.0.zip`, and the v0.5 zip was deleted.
- `apply_patch.py` now saves `<image>.bak` (a full copy) before patching an image in place, as folder mode already did for its files (user request). The copy goes through `.bak.part` and is renamed when complete, so an interrupted copy is never taken for a backup on the next run; an existing `.bak` is never replaced. The backup happens only after both files pass the SHA1 checks and the xdelta decode, and never on an already-patched image. Selftest covers it.
- **Retest from the unzipped v1.0 [C]:** folder mode unchanged (2d1829b5… / dda7e888…, `.bak` = stock). Image: a fresh `gtasa_stock.xiso` copy → `.bak` byte-identical to stock (`cmp`), patched image 2436 bytes differ and 0 outside the two files, and a re-run prints `already patched` without a second copy. Test images deleted afterwards.

## 2026-10-12 — Real hardware: v1.0 on a Cerbios Xbox

- **Setup:** the user's original Xbox with the Cerbios BIOS and the XBMC4Gamers dashboard. The game was copied to the HDD as an extracted folder, `work/hdd/GTA San Andreas/`, made with `xdvdfs_extract.py` from the patched ISO (now `work/xbox/gtasa_v1.0.xiso.xiso`). 368 files; `diff -rq` against the original extracted Rev 1 folder differs only in `default.xbe` (2d1829b5…) and `stream.ini` (dda7e888…).
- **Result (user report) [C]:** boots from XBMC4Gamers, and the first mission was played with no problems. The user's TV photo at Grove St shows the PS2-style orange sunset filter with the HUD intact. So the unsigned patched XBE runs under Cerbios.
- **CCI route, dropped:** Repackinator 2.0.4 (`F:\Tools\Repackinator`) built `.cci` (2.76 GB, no split) + Cerbios attacher `default.xbe` (title ID 0x545400A3, same as the game) + `default.tbn`. The CCI was checked by extracting it again: the patched files were inside. The user preferred the plain folder and the CCI set was deleted, without being tested on the console.

## 2026-10-12 — P7: PS2 stream.ini settings as XBE defaults (v1.1, one-file xdelta)

- **Why:** the user wants the xdelta to be plug and play in any GUI. v1.0 also needed five `stream.ini` lines, so the mod has to live in `default.xbe` alone.
- **RE [C]:** the stream.ini key handlers live in the parser at 0x157EFD:
  - `pe_leftx` 0x15805D, `pe_rightx` 0x15807E, `pe_topy` 0x15809C and `pe_bottomy` 0x1580BA each do `push edi; call atoi; mov [0x3CE808/0C/10/14], eax`. These are the only writers, and the stock .data values are already 8 ×4.
  - `pe_bRadiosity` 0x1580D8 does `atoi; test; setne al; mov [0x5F4B1C], al`. That BSS byte has exactly two references: this writer and the reader `cmp byte [0x5F4B1C], 0; je 0x24CD85` at 0x24CD43, which skips the radiosity call at 0x24CD7D.
- **P7 as built:** `patches/p7_ini_defaults.py` → `.json` (selftest OK), with 6 edits:
  - the four pe stores → NOP ×5;
  - 0x1580E1 `95` → `94` (`sete`);
  - 0x24CD4A `74` → `75` (`jne`).

  The byte now means "radiosity off". With no line or with `pe_bRadiosity 1` (the v1.0 ini) radiosity is on, and `pe_bRadiosity 0` turns it off. `requires` P2 + P3. P2 + P3 + P4 + P5 + P6b + P7 → `dist/default_v1.1.xbe` sha1 **84e14eef…**. The diff against v1.0 is exactly the 22 bytes above.
- **Boot test:** `work/xbox/_p7test.xiso` = `gtasa_stock.xiso` with only the v1.1 XBE written (stock `stream.ini`, sha1 67732726…).
  - The user loaded it in xemu (a session the user started, without the GDB stub) and played in Grove St at 06:00. The warm filter and blur are present (`captures/release_v05/p7_grove.png`).
  - Boot with the untouched ini [C]. pe 8 and radiosity on are [S], from the visual only: that instance had no GDB to read 0x3CE808 / 0x5F4B1C.
- **Harness incident:** the xemu install is shared with the BFBB DELUXE project. `xemu.toml`'s `dvd_path` was switched to the BFBB disc while this test ran, so one GDB attach landed on BFBB, and a software breakpoint at 0x158063 was planted into the wrong game. Rules from now on:
  - never edit `xemu.toml` for tests; launch with `-dvd_path <iso> -s`;
  - check that no other xemu is running;
  - verify the expected code bytes in RAM before any `Z0`.
- **Release v1.1 [C]:** `dist/SA-PS2Atmosphere-v1.1.zip` (xdelta 1475 B, `-S none`, app header `default.xbe`). `apply_patch.py` now patches only `default.xbe` and refuses the v1.0 XBE with a hint. From the unzipped package:
  - `xdelta3 -d` on the original `default.xbe` (what every GUI runs) → 84e14eef…;
  - folder mode: XBE patched, `stream.ini` untouched (67732726…), `.bak` = stock; a re-run prints `already patched`; the v1.0 XBE is refused (exit 1, nothing written);
  - image mode on a fresh `gtasa_stock.xiso` copy: `.bak` == stock, and the patched image is **byte-identical to `_p7test.xiso`**, the ISO played in xemu.

## 2026-10-12 — Real hardware: v1.1

- **Result (user report) [C]:** the v1.1 `default.xbe` (sha1 84e14eef…, P2–P7) runs on the user's original Xbox with Cerbios + XBMC4Gamers. P7's parser and guard edits behave on hardware as in xemu.
- The local `work/hdd/GTA San Andreas/` is still the v1.0 folder (XBE 2d1829b5…, ini dda7e888…). The console copy was patched separately.

## 2026-10-12 — Whole-ISO xdelta patches (XISO + Redump)

- **Why:** the user wants ISO patches, as is usual for xdelta releases. An ISO xdelta only applies to the exact image it was made for, and image layouts differ by tool. Found on this box: a 3.06 GB rebuilt xiso with `default.xbe` at sector 265, sha1 1ceae5be… (not Rev 1, probably Rev 0; not supported). The user chose two targets: the Redump image and our game-partition XISO.
- **Tool:** `tools/iso_xdelta.py` (selftest decodes with the real xdelta3 and rejects a wrong source). It diffs stock vs v1.1 XISO into 51 runs, all inside `default.xbe`, and writes 8 MiB VCDIFF windows. Each window is a same-offset COPY (code table 19, mode 0) plus ADD (1) of the changed bytes, with `VCD_ADLER32`, laid out as xdelta3 writes it (checked on its own output). With `--redump` everything shifts by 0x18300000. The video-partition windows get no checksum: the Redump ISO isn't on this box, and a same-offset copy reproduces whatever is there.
- **Validation [C]** (xdelta3 3.1.0):
  - `xiso.xdelta` (28,595 B) on `gtasa_stock.xiso` gives a byte-identical `gtasa_v1.1.xiso`. On that rebuilt image it fails with "target window checksum mismatch", exit 1.
  - `redump-iso.xdelta` (29,818 B) on a synthetic Redump (random 0x18300000-byte video partition + `gtasa_stock.xiso`, 7,825,162,240 B): the video partition is untouched and the game partition equals `gtasa_v1.1.xiso`. Synthetic files deleted.
  - Not tested: a real Redump Rev 1 dump (none on this box).

## 2026-10-16 — USA Rev 0 port

- **Target [C]:** the Redump image `Grand Theft Auto - San Andreas (USA) (En,Es).iso` (7,825,162,240 B, the same layout as Rev 1: game partition at 0x18300000). Its `default.xbe` sits at partition sector 348552, 4018176 B, sha1 **1ceae5be…**. That is the XBE of the rebuilt xiso noted on 2026-10-12, so that image was Rev 0. Cert title ID 0x54540082 (Rev 1: 0x545400A3). Working copies: `work/xbox_rev0/gtasa_stock.xiso` (ISO[0x18300000:]) and `default.xbe`.
- **Layout [C]:** the same build with small code changes. `.text` is 0x200 B shorter, every later section starts 0x200 lower except `.data` (−0x240, same vsize). Inside `.text` the shift is piecewise: −0x2CF around PostFX (ColourFilter, Radiosity, blur pass, guard), −0xB9 at the stream.ini parser, −0x200 at RW. The building-pipe area 0x166C70–0x16AFA8 is reordered. Rev 1 has a 0x26 B stub at 0x166C4A that Rev 0 lacks, and the shared setup 0x16A1E5 moved to 0x167C14.
- **Method:** `tools/rev0_map.py` disassembles the code sections of both XBEs and aligns them, masking absolute operands, in two passes. Pass 1 builds a data map from paired instructions. Pass 2 repeats with those proven addresses translated rather than masked, which separates functions that differ only in a global, such as the four building pipes with different VS handles. A Rev 1 address is accepted only if:
  - code: its ±256-instruction window matches one Rev 0 candidate clearly best (difflib), or every caller of the function calls one Rev 0 target ("callers"), or it sits inside such a function at an equal offset with all instructions between equal ("function");
  - data: every reference to it pairs with one Rev 0 value ("xref").

  Generators run with `--rev0`. Each address goes through `A()`, which raises if the address is unproven. Proven pairs: `patches/rev0_map.json` (64 entries).
- **[S] exceptions:** `D3D_g_RenderState` ALPHA_TEST/BLEND 0x36E378/0x36E374 (P6b) have no direct reference (indexed). The D3D library section is identical modulo relocations: 1339 differing bytes, 1113 explained as dwords shifted −0x200/−0x228/−0x240, the rest rel32 calls. So they map at −0x200 (0x36E178/0x36E174).
- **Notable proofs [C]:** the DN setups 0x166C70 → 0x166BEC and 0x1675DF → 0x16755C (each Rev 0 copy reads the mapped VS handle and DN balance). The shared setup 0x16A1E5 → 0x167C14: its four Rev 1 callers (pipes with VS 0x5F2934/40/60/84) map to the four Rev 0 calls at the shifts their own VS references give (+0x19C ×3, −0xF0). P4's `stock_ok` / `c23_stock_ok`, P2's call-site check, P5's 0.35 check, P6b's site check and P7's handler bytes all pass on Rev 0.
- **Build:** all Rev 1 JSONs regenerate byte-identical, and Rev 1 v1.1 is still 84e14eef…. Rev 0 P2 + P3 + P4 + P5 + P6b + P7 (`*.rev0.json`, `xbe_sha1` = Rev 0) → `dist/default_rev0_v1.1.xbe` sha1 **6883102c…**, 2434 bytes changed (Rev 1: 2434). `xbe_patch.py` refuses Rev 1 JSONs on Rev 0 and the reverse.
- **Boot test [C]:** `work/xbox_rev0/gtasa_rev0_v1.1.xiso` (XBE at sector 348552) boots in xemu and plays. P2's jmp is live in RAM. Live reads through `xemu_gdb.py --rev0` (data −0x240): clock, position, idle cam 90000, pe offsets 8 with the stock `stream.ini` (P7), radiosity flag 0. Grove St 12:00, weather 0: Rev 0 mod ground/sky medians (156,100,52)/(121,204,200) vs Rev 1 mod (153,98,51)/(116,204,198); Rev 1 stock ground (133,114,96). The camera angles differ, so these are regional medians, not a per-pixel diff. **User visual sign-off ✅** ("the mod is identical and working").
- **Release:** `default_rev0.xbe.xdelta` (1472 B), `rev0-xiso.xdelta` (28,587 B) and `rev0-redump-iso.xdelta` (29,810 B, 51 runs). Decoded with xdelta3 3.1.0 [C]:
  - the XBE patch gives 6883102c…;
  - the XISO patch gives a byte-identical `gtasa_rev0_v1.1.xiso`;
  - the Redump patch, applied to the **real** Rev 0 Redump ISO, leaves the video partition untouched and makes the game partition equal to the boot-tested XISO;
  - each patch fails with "target window checksum mismatch" on the Rev 1 source.

  `apply_patch.py` picks the patch by SHA1 (table stock → (mod, xdelta)). On a Rev 0 folder and a Rev 0 XISO copy it gives 6883102c… with a stock `.bak`, and a re-run prints "already patched". A Rev 1 folder still gives 84e14eef….
- **GUI patcher [C]:** xdeltaUI with `default_rev0.xbe.xdelta` on the stock Rev 0 XBE gives 6883102c….
- **Real hardware [C] (user report, 2026-10-16):** that `default.xbe` in an extracted Rev 0 game folder runs fine on the user's Xbox (Cerbios + XBMC4Gamers).
- **Not tested:** a per-pixel A/B with the same save and camera, and the Rev 0 ISO patches in a GUI patcher (they were decoded with xdelta3 only).

## 2026-10-16 — Release v1.2 (Rev 0 support)

- **Package:** `dist/SA-PS2Atmosphere-v1.2.zip` (47 KB):
  - `install_instructions.txt` (quick guide: xdelta GUIs, web, CLI, Python);
  - `README.md`;
  - `GTA SA (USA) Rev 1/` and `GTA SA (USA) Rev 0/`, each with `default.xbe.xdelta`, `iso.xdelta` (full Redump-layout ISO, formerly `redump-iso.xdelta`) and `xiso.xdelta`;
  - `apply_patch.py` (the patch table now points into the two folders) and `xdvdfs_extract.py`.

  The Rev 1 patched bytes are unchanged from v1.1 (84e14eef…); only the ISO patches' internal output names say v1.2. The user-facing docs name the ISO by its game title and say the ISO patches target the Redump dumps.
- **Validation [C]:**
  - every packaged xdelta decodes with xdelta3 3.1.0: XBE patches → 84e14eef… / 6883102c…; XISO patches → byte-identical modded XISOs;
  - `GTA SA (USA) Rev 0/iso.xdelta` on the real Rev 0 Redump ISO changes exactly 2434 bytes, and the embedded XBE is 6883102c…;
  - the packaged `apply_patch.py` patches a Rev 0 and a Rev 1 folder correctly.
- **Editions [C] (2026-10-16):** per xemu-project/xdb `titles/TT/130/info.json`, title ID 54540082 = USA Original (our Rev 0) and 545400A3 = USA Platinum Hits / *The Trilogy* (our Rev 1). Both IDs match the XBE certificates read earlier. The docs keep the Rev 0 / Rev 1 names and add the editions.

## 2026-10-20 — Europe Rev 1 / Rev 0 port (release v1.3)

- **Targets [C]** (Redump images in `Microsoft - Xbox/`, same layout as USA: 7,825,162,240 B, game partition at 0x18300000):

  | Build | `default.xbe` sha1 | Title ID / region / version | XBE partition sector |
  |---|---|---|---|
  | Europe Rev 1 `(Europe) (En,Fr,De,Es,It) (Rev 1)` | f0ed7d69… | 545400A4 / 4 / 1 | 347516 |
  | Europe Rev 0 `(Europe) (En,Fr,De,Es,It)` | 7a424b08… | 54540086 / 4 / 3 | 347390 |

  Both are 4018176 B, the same section list as USA. `.text` vsize: EU1 0x2C9ED4, EU0 0x2C9CD4 (USA Rev 0 0x2C9C74). `.data` VA: EU1 0x392BC0, EU0 0x392980. Work copies: `work/xbox_eu1/`, `work/xbox_eu0/` (`gtasa_stock.xiso` = ISO[0x18300000:], `default.xbe`).
- **Map [C]:** `tools/rev0_map.Map` (unchanged) ports all 64 addresses the generators use from USA Rev 1 to both builds: 58 code, 2 function, 64 xref, 4 near ([S], the two `D3D_g_RenderState` fields, as on Rev 0), with no failures. Shifts: EU1 code −0x183…+0x80, data +0x48/+0x60/+0x70; EU0 code −0x2A9…−0x124 (function −0x1EB4: the building shared setup), data −0x1E0/−0x1C8/−0x1A0. `rev0_map.py` now holds a target table (`--rev0`, `--eu1`, `--eu0`; caches `patches/eu1_map.json`, `eu0_map.json`; output `pN.eu1.json` / `pN.eu0.json` with `xbe_sha1`).
- **Generators [C]:** P1–P7 build for both with all built-in byte checks passing (P2 call site, P4 `stock_ok` / `c23_stock_ok`, P5 0.35, P6b site, P7 handler bytes). The USA Rev 1 and Rev 0 JSONs regenerate byte-identical.
- **Build [C]:** P2–P7 → `dist/default_eu1_v1.1.xbe` sha1 **fc50bdfd…** and `dist/default_eu0_v1.1.xbe` sha1 **f6f9e051…**, each 2434 bytes changed in the same 23 runs (lengths and order) as USA Rev 1 and Rev 0. `xbe_patch.py` refuses EU JSONs on USA XBEs, the reverse, and EU1/EU0 mixed. Boot candidates: `work/xbox_eu1/gtasa_eu1_v1.1.xiso`, `work/xbox_eu0/gtasa_eu0_v1.1.xiso`.
- **xemu_gdb [C]:** `--eu1` (data +0x60) and `--eu0` (data −0x1E0) live addresses, each proven by xref (idle cam via its base 0x6C5248). The same method reproduces the hand-written `--rev0` block exactly. Not used live yet.
- **Release v1.3:** `GTA SA (Europe) Rev 1/` and `GTA SA (Europe) Rev 0/` with `default.xbe.xdelta` (1473 / 1472 B), `xiso.xdelta` (28,555 / 28,562 B), `iso.xdelta` (29,831 / 29,823 B, 51 runs); the USA folders are copied from v1.2 unchanged. Decoded with xdelta3 3.1.0 [C]: XBE patches → fc50bdfd… / f6f9e051…; XISO patches → byte-identical patched XISOs; `iso.xdelta` on each **real** Europe Redump ISO leaves the video partition untouched and gives a game partition equal to the patched XISO. `apply_patch.py` on folders of all four versions gives the patched SHA1 with a stock `.bak`, and a re-run prints "already patched".
- **Boot in xemu with the NA EEPROM [C] (2026-10-20):** every Europe image, **stock included**, returns to the dashboard ("Please insert an Xbox disc...", title FFFF0002) before the first frame; USA v1.1 boots in the same setup. Not the patch, not the BIOS (BIOS images are region-neutral). Traced with hardware breakpoints:
  - `HalReturnToFirmware(2)` is reached from the CRT exit after the game's `main` (EU0 0x27391c) **returns**;
  - `main` passes init events 0x18 / 0x15 and the camera, then `call 0x27859b; cmp eax, 4; jne exit` (EU0 0x273B14, EU1 0x273D0A). 0x27859b is `XGetGameRegion` (`XQueryValue(0x104 = XC_FACTORY_GAME_REGION)`), so the game itself requires the **EEPROM** game region = 4 (Europe) and quits silently otherwise. USA builds do the same with `cmp eax, esi` (= 1), at Rev 1 0x273CCF and Rev 0 0x273ADC;
  - forcing the XBE certificate region to 7 changes nothing (that check passes; this one doesn't read the certificate).
- **Test-only builds** (not shipped): `work/xbox_eu{0,1}/_test_noregion_{stock,v1.1}.xiso` NOP the `jne` (6 bytes at call + 8). EU0 stock and v1.1 reach the Rockstar logo and intro credits in xemu with the NA EEPROM. For a real check: a Europe-region EEPROM (PAL console, or an EEPROM copy set to Europe), or these test builds in xemu.
- **User sign-off ✅ (2026-10-20):** the user booted both `_test_noregion_v1.1.xiso` builds (EU Rev 0 and Rev 1) in xemu and played: "funcionou sem problemas". The test images were then deleted (the shipped builds keep the region check; they differ from the tested ones only by those 6 bytes).
- **Real hardware ✅ (2026-10-20, user report):** both test XBEs (`dist/_test_noregion_eu{0,1}_v1.1.xbe`) in extracted game folders on the user's NTSC Xbox (Cerbios + XBMC4Gamers): "testei as duas no meu console, funcionou". The user chose to ship the Europe patch region-free.
- **P8 [C]:** `patches/p8_eu_regionfree.py` (`--eu1` / `--eu0` only; refuses USA). The sites come through `A()`: Rev 1 call 0x273CCF → EU1 0x273D0A / EU0 0x273B14, and XGetGameRegion 0x27872D → 0x278791 / 0x27859B (both "code"). It asserts `call XGetGameRegion; 83 F8 04; 0F 85` and that the callee is `XQueryValue(0x104)`, then NOPs the 6-byte `jne` (EU1 0x273D12, EU0 0x273B1C). P2–P8 → `dist/default_eu1_v1.3.xbe` sha1 **d4b4a593…** and `dist/default_eu0_v1.3.xbe` sha1 **acd8ea4a…**, byte-identical to the hardware-tested XBEs. The v1.1-only EU builds (fc50bdfd… / f6f9e051…) are superseded and not shipped.
- **Release v1.3, final:** the Europe xdeltas were rebuilt from the P2–P8 XBEs (`xiso.xdelta` 28,569 / 28,576 B, `iso.xdelta` 29,846 / 29,838 B, 52 runs; `work/xbox_eu{1,0}/gtasa_eu{1,0}_v1.3.xiso`). The installer table maps Europe to the new SHA1s. `apply_patch.py` on folders of all four versions gives 84e14eef… / 6883102c… / d4b4a593… / acd8ea4a… with a stock `.bak`.
- **Not tested:** a live RAM read on EU, and a non-HDTV (composite) TV on EU.
