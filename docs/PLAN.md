# GTA SA Xbox — "PS2 Atmosphere" mod: evidence-based engineering plan

Legend: **[C]** Confirmed (read from bytes/source), **[S]** Strongly inferred, **[H]** Hypothesis requiring testing.

> **Status 2026-10-12 (v1.1):** P7 bakes the PS2 `stream.ini` settings into the XBE, so the whole mod is `default.xbe` (`dist/SA-PS2Atmosphere-v1.1.zip`, one xdelta that works in any GUI). Boot-tested in xemu with the stock `stream.ini`. The installer's ISO output is byte-identical to that test ISO. Real hardware ✅ (user, Cerbios + XBMC4Gamers).
>
> **Status 2026-10-12 (Phase 7):** **release v1.0** (the v0.5 build) built and tested: `dist/SA-PS2Atmosphere-v1.0.zip` (xdelta + `apply_patch.py` + README). The test ISO is `work/xbox/gtasa_v05_release.xiso`, which replaces the lost `gtasa_p2p3p4p5p6b.xiso` (same XBE and ini SHA1s). User sign-off ✅ (2026-10-12, Grove St in game). **Phase 7 closed**; real hardware ✅ 2026-10-12 (Cerbios + XBMC4Gamers, game folder on the HDD; findings "Real hardware").
- **Post-release — USA Rev 0.** ✅ 2026-10-16: v1.1 (P2–P7) ported to Rev 0 (`default.xbe` sha1 1ceae5be…) by proven address translation; `dist/default_rev0_v1.1.xbe` sha1 6883102c…, booted in xemu, user visual sign-off ✅, real hardware ✅ (Cerbios + XBMC4Gamers); installer + Rev 0 xdeltas built and decoded against the real Redump Rev 0 ISO (findings "USA Rev 0 port"). Released as **v1.2** (`dist/SA-PS2Atmosphere-v1.2.zip`, per-revision folders; findings "Release v1.2").
- **Post-release — Europe Rev 1 / Rev 0.** 2026-10-20: v1.1 (P2–P7) ported to Europe Rev 1 (`default.xbe` sha1 f0ed7d69…) and Rev 0 (7a424b08…) with the same proven map; plus **P8** (`patches/p8_eu_regionfree.py`, Europe only: NOPs the game's own `XGetGameRegion() == 4` check, which quits on non-Europe EEPROMs) → `dist/default_eu1_v1.3.xbe` sha1 d4b4a593…, `dist/default_eu0_v1.3.xbe` sha1 acd8ea4a…; installer + xdeltas built and decoded against the real Europe Redump ISOs. Boot ✅ in xemu (NA EEPROM) and on real hardware (NTSC console, Cerbios + XBMC4Gamers), user sign-off ✅. Release v1.3 (`dist/SA-PS2Atmosphere-v1.3.zip`; findings "Europe Rev 1 / Rev 0 port").
>
> **Earlier status 2026-09-25 (Phase 6):** Phases 0–6 are done. **v0.5 candidate = `gtasa_p2p3p4p5p6b.xiso`** (v0.4 + P6b building-pipe dual pass, PS2 alpha-test semantics; boot-tested and signed off). Phase 6 also closed display filters (no patch), grass (P6c rejected by the user) and heat haze (present; the gap was a harness artefact). Next: Phase 7 (distribution).
>
> **Earlier status 2026-09-25:** Phases 0–5 are done. v0.2 = `gtasa_p2p5.xiso` (P2 blur), v0.3 = `gtasa_p2p3p5.xiso` (P3 radiosity), **v0.4 candidate = `gtasa_p2p3p4p5.xiso`** (P4 v2 building lighting G 0.91 / N 0.80 / KA 1.80, boot-tested and signed off 2026-09-25). The night-ground gap that remains is the Xbox asphalt texture, accepted as asset content (user, option a). Next: Phase 6 (optional polish) or Phase 7 (distribution). Corrections from live measurement are marked **(2026-09-24)** below; the evidence is in `docs/findings.md`.
Xbox addresses are VAs in `default.xbe` USA Rev 1 (SHA1 `10EFB868F13D6944AA6684A52CAC5156393F14C5`). File offset = VA − 0x10000 (.text), VA − 0xFB60 (.data), VA − 0x10280 (.rdata). Any .data VA ≥ 0x3D2C04 is BSS (zero at boot).

Routing evidence:
- `zoom-out`: the system map is §1–§5 below. It covers PS2 data/ELF+overlays, the Xbox XBE (RW 3.6 + XDK 5849), SkyGfx `src/`+`shaders/`, and gta-reversed `PostEffects/Streaming/TimeCycle`.
- `diagnose` Phases 1–3: the feedback loop is §16 (the "differential loop"). The ranked falsifiable hypotheses are §7. Phases 4–6 are the experiments in §13.
- `tdd`: runs after approval. Each patch gets one runnable check: the `xbe_patch.py` original-byte guards and `predict_filter.py` self-check.
- Delegation: **OFF** (`~/.claude/delegation-off` present), so I execute directly after approval.

---

## Context

The goal is the Xbox version of GTA SA, rendered with the PS2 atmosphere, while keeping Xbox advantages: DXT textures, longer LOD distances, 480p, and the Xbox car shader. The research shows the difference is **almost entirely in engine code, not in data**:

- `timecyc.dat` is byte-identical between the two versions. The sscanf format is the same (52 fields).
- The assets (vertex colours, textures) are calibrated identically.

Four code differences create the look:
- a different colour-filter formula;
- radiosity that is off and broken on Xbox;
- a missing colour-filter blur;
- a smaller building-lighting difference.

The minimum viable mod is therefore **a `default.xbe` binary patch plus a 3-line `stream.ini` edit**. No shader files are involved, because Xbox SA has no custom pixel shaders.

---

## 1. Game structure findings

| | PS2 (SLUS_209.46 v3.00) | Xbox (default.xbe Rev 1) |
|---|---|---|
| Code | MIPS ELF, stripped. Init code lives in **overlay `INIT.NM`** (VA 0x88E400); the stream.ini + timecyc parsers are there [C] | x86 XBE, 14 sections, RW 3.6 (`RW36Active` paths), XDK 5849, D3D8LTCG, XGRAPHCL [C] |
| RW pipes | VU1 microcode, PS2 native geometry 0x510 + ExtraVertColour 0x253F2F9 [C] | 16 custom vertex-shader microcode blobs in .data 0x3C9B18–0x3CAF08; **no custom pixel shaders**; fixed-function stages → NV2A combiners [C]/[S] |
| Night prelight | ExtraVertColour plugin + high byte of the VIF colour stream [C] | Packed 11:11:10 inside the 28-byte vertex (R,G ×4, B ×2) [C] |
| timecyc | `DATA\TIMECYC.DAT` (timecycp.dat is never referenced) [C] | Identical file and format; the loader **doubles both PostFX alphas** [C] |

## 2. Relevant PS2 files

- `STREAM.INI`: `pe_lightchangerate 0.0008`, `pe_lightingbasecap 0.35`, `pe_lightingbasemult 0.4`, `pe_leftx/topy/rightx/bottomy 8`, `pe_bRadiosity 1`, `def_brightness_ntsc 256` [C].
- `INIT.NM` (0x14958 `TIMECYC.DAT`, 0x14A98 `stream.ini` key table): this is the parser to diff against Xbox when a value's meaning is uncertain.
- `SLUS_209.46` main segment: holds the PS2 `CPostEffects::ColourFilter`/`Radiosity`. It is only needed if a SkyGfx claim must be re-verified (the factor-of-2 radiosity intensity question in §17).
- `DATA\TIMECYC.DAT`: the behavioural reference values (PostFX1/2 ARGB, IntensityLimit column 49).
- Not relevant [C]: `plants.dat` (mesh id only), `object.dat` (physics), `fonts.dat`, `effects.fxp` (prt_wake bounds only), all textures and vertex colours.

## 3. Relevant Xbox files

- `default.xbe`: every change except the ini.
- `stream.ini`: data knobs; the parser already knows all the PS2 keys [C].
- `data\timecyc.dat`: leave untouched (identical to PS2).

## 4. Relevant SkyGfx source (aap/skygfx @926616a3)

| File / function | PS2 behaviour reproduced | Xbox status |
|---|---|---|
| `src/postfx.cpp` `ColourFilter_PS2`, `ColourFilter_switch`; `main.cpp` hook 0x704D1E; Nop 0x5BBF6F/0x5BBF83 (alpha ×2) | `out = fb·2rgb1 + fb′·2rgb2·2a2` (MODULATE2X, pass 1 replaces, pass 2 SRCALPHA/ONE, fb′ = UV-offset, linear filtered) | **Present, but uses the PC formula** `fb + fb·c1·a1 + fb·c2·a2` [C] |
| `postfx.cpp` `Radiosity`/`Radiosity_shader`; hooks 0x704D5D/0x704FB3 | downsample ×filterPasses → `2D − limit` → add `tmp·intensity` × renderPasses | **Present but dead**: off by default, and it draws degenerate PS2-sprite strips [C]/[S] |
| blur via `m_colour*Offset` (pe_leftx…) | half-pixel shift + bilinear = soft image | **Absent**: the ini values are parsed but have no readers [C] |
| `buildingPipe.cpp` `ps2BuildingVS` + `simplePS`, `CustomPipeRenderCB_Xbox` | `(day·(1−b)+night·b)·matCol/scale + ambient`, then `tex·col·255/128`, so ambient is ≈×2 and results above 1 are allowed | Xbox pipe = `(prelight·surfDiff + amb·surfAmb)·matCol`, no 2× [S] (SkyGfx's reimplementation of the Xbox pipe) |
| `D3D9RenderDual` | PS2 alpha test (fail pixels still write colour) → fuller foliage | Unknown [H] |
| `vehiclePipe.cpp` `CustomPipeRenderCB_Xbox`/`xboxCarVS` | — (Xbox-specific: sun-only, Blinn pow16 spec, diff+spec averaged) | **Keep Xbox** (an Xbox hardware advantage) |
| grass `grassPS`, `grassAddAmbient` | `tex·matCol·255/128 + ambient` | Unknown [H] |
| `disableGamma`, gta-reversed brightness 0x561468 | brightness scales ambient only | Xbox has the same code at 0x10FC6D; gamma ramp unknown [H] |

## 5. PS2 vs Xbox rendering differences (differential map)

| System | PS2 | Xbox | SkyGfx | Modification |
|---|---|---|---|---|
| Timecycle data | reference | identical file/format [C] | uses the console file | none |
| Timecycle alpha | 0..127, 128=1.0 | ×2 at load (`fadd st0,st0` at 0x1572A4 / 0x1572B4) [C] | Nop'd for the PS2 path | keep (compensate in the filter) |
| **Colour filter** | `fb·2c1 + fb′·2c2·(2a2/255)` | `fb + fb·c1·A1 + fb·c2·A2` [C], **then diluted by the Xbox blur pass (next row)** (2026-09-24) | `ColourFilter_PS2` | **P1 done:** rewrite of `0x24F007` (MODULATE2X) |
| **Xbox blur pass** (2026-09-24) | absent | `0x24ECAA`, after the filter: 2× lerp of the *pre-filter* copy at α 60 → `out = 0.585·F + 0.415·raw` [C] (enable byte `0x3CE7AD`, count `0x3CE7B4`, alpha `0x3CE7B8`, UV scale `0x3CE7B0`) | — | **P1:** `0x3CE7AD` 1 → 0 |
| **Radiosity** | on (`pe_bRadiosity 1`; flag 0x66CEC8 [C]) | flag 0x5F4B1C = 0; function 0x24DF8E is broken [C] (E2) | PS2 (fixed-function path) | **P3 built** (rewrite of 0x24DF8E) + ini `pe_bRadiosity 1` |
| **Filter blur** | offsets 8 → ½ px, linear (PS2 globals 0x668D28 [C]) | offsets unused; NEAREST [C] | `m_bBlurColourFilter` | **P2 built** (UV offsets + LINEAR) + ini 8 |
| Dark-area boost | basemult 0.4, rate 0.0008 | 0.5 / 0.0005 (exe default 1.0) [C] | same code | **ini only** |
| Building ambient/2× | ambient ≈×2 relative to prelight [C, sweep]; prelight ~0.87× day / ~0.75× night vs Xbox [S] | `(prelight·surfDiff + ambient·surfAmb)·matCol` [C, VS decoded] | `ps2ModulateBuilding` | **P4 v2 done** (G 0.91 / N 0.80 / KA 1.80, building pipes only) |
| Foliage alpha | GS TEST AFAIL FB_ONLY, AREF 64/128 [C] | GREATER 100/140, fail discarded [C] | `dualPass` | **P6b** dual pass (building pipes) |
| Grass alpha (2026-09-25) | `plants.dat` A read as /128 (GS) [S] | same byte read as /255 → half as opaque [C] | `grassPS` ×255/128 | none (P6c built, rejected by the user; opt-in) |
| Fog / sky | timecyc | same code path [S] | engine default | none |
| Vehicles | PS2 env/spec | Xbox spec pipe | selectable | **keep Xbox** |
| Draw distance | shorter LODs | 1,830 LODs longer [C] | — | keep Xbox |
| Gamma / display | GS output | brightness → ambient [C]; brightness also builds a gamma ramp via pow() (table 0x5F20F0, SetGammaRamp call 0x2746EE; e.g. exponent 0.843) [C] (2026-09-24) | disableGamma | none; captures must be linearized with the active ramp |

## 6. What creates the PS2 look (ranked by visual weight)

1. **Colour-filter formula [C].** This is the "orange filter". The PS2 has no identity term, so blue can drop below 1× while red goes up to ~1.8×. LA 12:00 (c1 66,66,48; c2 166,129,60; a2 127):
   - PS2 gain R/G/B = **1.81 / 1.53 / 0.85**.
   - Xbox formula alone = 1.91 / 1.76 / 1.42, but the real stock output is diluted by the blur pass: `1 + 0.585·(c1·a1 + c2·a2)`. Measured at the same scene with c1 70,121,120,a240, c2 160,88,21,a254: **1.52 / 1.46 / 1.30** (xemu and Cxbx agree) (2026-09-24).
   - R/B ratio: PS2 2.14 vs Xbox 1.34 (formula only).
   - At 20:00: PS2 1.15 / 0.88 / 0.31 vs Xbox 1.57 / 1.44 / 1.16.
   - Xbox is neutral and washed out (41.5% of the unfiltered frame is blended back); PS2 is warm, darker in blue, and more contrasty.
2. **Radiosity [C].** It runs after the filter, so it blooms the already-orange highlights (`limit` comes from the timecyc, 60–220). This is the PS2 "glow/haze".
3. **Filter blur [C].** The soft PS2 image; it also softens the radiosity.
4. **Building ambient ×2 / modulation [S].** Brighter shadowed and night buildings; affects luminance, not hue.
5. **SCREEN_EXTRA_MULT params [C].** Small filter-strength boost in dark areas.
6. Foliage alpha, grass ambient [H]: texture and fullness, not colour.

Not factors [C]: timecyc values, vertex colours, textures, plants/effects data, fog/sky data.

## 7. Ranked falsifiable hypotheses (diagnose Phase 3)

- **H1 — Confirmed (E3, P1 boot).** The filter formula explains most of the colour gap. *Prediction:* applying the PS2 formula offline to a Xbox postfx-off frame brings its mean R/B ratio and hue histogram to within noise of the PS2 capture of the same scene. Applying the Xbox formula leaves a large gap.
- **H2 — Confirmed (E2, 2026-09-24).** The flag only adds an edge shift/blur, no bloom. Original text: Xbox radiosity is non-functional. *Prediction:* `pe_bRadiosity 1` produces no visible change, or thin-line artifacts only.
- **H3 — Refuted as stated / resolved (2026-09-24).** The fb copy is X8R8G8B8, so its alpha reads 1.0 and `ALPHAOP=MODULATE` is fine. The measured 0.585 factor came from the Xbox blur pass, not from alpha. Original text: Pass 2's framebuffer alpha reads as 1.0 on Xbox. *Prediction:* the PS2 formula with `ALPHAOP=MODULATE` matches `predict_filter.py` within ±2 levels. If not, the backbuffer is A8R8G8B8 with geometry alpha, and `SELECTARG2` (diffuse) must be used.
- **H4 — Confirmed /255 (E6, 2026-09-24): the PS2's own radiosity on/off at Grove St noon is fitted by SkyGfx's operator at the timecyc limit 180, intensity 35, /255 (bias ≈ 0; /128 clearly worse).** PS2 radiosity intensity is `intensity/128` (aap's text), not SkyGfx's `/255`. *Prediction:* the bloom energy in PS2 captures matches `/128` better.
- **H5 — mechanism Confirmed, prediction Refuted (2026-09-24, ambient sweep on both consoles):** relative to prelight, the PS2 adds building ambient at ~2× (texture-free ratio 0.47–0.54 vs 0.502). Its prelight term is also weaker (~0.87× day, ~0.75× night [S]), so ambient ×2 alone overshoots (natural night: stock ≈ PS2, P4 +45 %). Original text follows.
- **H5 — leading candidate for the night-asphalt residual [S] (2026-09-24: PS2 − P1 ≈ +2/+8/+7 teal at matched luminance; gamma, E1 and radiosity ruled out).** The remaining brightness gap in shadow/night is building ambient ×2. *Prediction:* doubling the uploaded ambient VS constant closes the dark-region luminance gap without shifting hue. **Counter-evidence (2026-09-24, CJ's house at 12:00):** the Xbox interior is *brighter* in the darks than the PS2 before radiosity (median luminance 18 vs 8), so P4 must handle both directions (findings "P3 interior check").

## 8. Data-only modifications worth testing

Edit `stream.ini` (the parser already reads these keys [C]):
```
pe_lightchangerate	0.0008
pe_lightingbasemult	0.4
pe_leftx 8 / pe_topy 8 / pe_rightx 8 / pe_bottomy 8   (inert until blur patch)
pe_bRadiosity	1                                      (only after radiosity rewrite)
def_brightness_ntsc	256                                (Xbox default already 256 [S])
```
No timecyc change is needed. Do **not** port PS2 textures or models.

## 9. Binary modifications required (XBE)

**P1 — ColourFilter PS2 formula. DONE (2026-09-24):** `patches/p1_colourfilter.py` → `.json`, `dist/default_p1.xbe`, E4 87% of pixels within ±2, boots with a correct HUD. As built:
- 266 of 300 B. Pass 1 `ONE/ZERO` with A = FF; pass 2 `SRCALPHA/ONE` with A = a2. Vertex colour = c as-is.
- Stage0 `COLOROP=MODULATE2X` is written **only** to the D3D state `0x36BBF8` (+ dirty `0x800`) while the RW cache `0x75D5A0` stays 4, so RW's 2D setup `0x2AB710` does not overwrite it. It is restored to 4 before returning.
- Data patch `0x3CE7AD` 1 → 0 turns off the Xbox blur pass (see §5).
- The builder falls back to MODULATE4X + colour scale 1/(2k) if a dilution k < 1 ever has to be compensated.

Original design (kept for reference): in-place rewrite of `0x24F007–0x24F132` (300 B; call site 0x24CAF5; args c1, c2 as RGBA bytes on the stack, R at byte 0).
- Pass 1: vertex alpha off / `ONE`,`ZERO`; stage0 `COLOROP=MODULATE2X`; vertex colour = c1 → `fb·2c1`.
- Pass 2: `SRCALPHA`,`ONE`; `COLOROP=MODULATE2X`, `ALPHAOP=MODULATE` (the loader's ×2 alpha already equals PS2's `2a2`); vertex colour = c2 → adds `fb′·2c2·(2a2/255)`.
- Stage state goes through the Xbox D3D deferred texture-state array and the dirty flag, exactly as RW's 2D setup does at `0x2AB710`:
  - `0x36BBF8` = stage0 COLOROP;
  - `0x36BC08` = ALPHAOP [C] (`D3D__TextureState` base 0x36BBC8, 0x80 per stage, XDK 5849 order: COLOROP 12, COLORARG1/2 14/15, ALPHAOP 16, ALPHAARG1/2 18/19);
  - dirty flags `0x36E280 |= 0x800`;
  - RW cache `0x75D5A0`.
  - ~~Write both the RW cache and the D3D state~~ → write the D3D state only (see "As built" above); restore it to 4 after the draws, otherwise HUD/2D rendering inherits 2×.
- Fallback if stage patching misbehaves: 4 draws at MODULATE (`ONE/ZERO` c1, `ONE/ONE` c1, `SRCALPHA/ONE` c2 ×2). This is mathematically identical, and it works because every draw samples the fb copy `0x5F4B28`, not the running result.

**P5 — Neutral display gamma. BUILT (2026-09-24):** `patches/p5_display_gamma.py`. SetBrightness 0x274662 gives the default brightness 256 a brightening ramp (exp 0.85); PS2 matches the Xbox framebuffer with no ramp. P5 repoints the `addss` operand at 0x27468E from the pooled 0.2 (0x390A24, ~335 uses, must not be edited) to the read-only 0.35 at 0x390C44, so 256 becomes the identity. Fidelity: noon frame ΔE 5.7 → 1.0, night 3.8 → 2.1 (findings).

**P2 — Filter blur. BUILT (2026-09-24):** `patches/p2_filterblur.py` → `.json`; live RAM test 97.1 % within ±2 of `predict(raw, shift=0.5)`; E5 Laplacian gap to PS2 +79 % (P1) → −12 %. As built:
- P1 + blur is 439 B, so the body moves to the dead Xbox blur pass 0x24ECAA (504 B; only caller 0x24CC89, NOP'd), and 0x24F007 becomes `jmp 0x24ECAA`. **P2 supersedes P1**: apply P2 + P5 (the patcher refuses P1 + P2).
- Pass 2 draws a stack copy of the quad with UVs += pe/(16·raster w|h), so the persistent quad is never touched. There is no SkyGfx W/640 or H/448 scale: pe/16 is in framebuffer pixels on both consoles.
- Ship `pe_leftx/topy/rightx/bottomy 8` (Xbox ini 16 = a sharp 1-texel shift).

Original design (kept for reference):
- Pass 2 uses texture filter `LINEAR` (RS 9 = 2).
- Pass 2 shifts the UVs of the Im2D verts at `0x5C7318` (stride 28, UV at +0x14/+0x18) by `off = pe_x·(W/640)/16/rasterW`, reading the now-live globals `0x3CE808/80C/810/814`.
- The vertex ordering must be mapped to SkyGfx's (left/top on v0,v1 / v0,v3; right/bottom on v2,v3 / v1,v2). **Verified live 2026-09-24: 0x5C7318 is v0 TL, v1 BL, v2 BR, v3 TR, so the SkyGfx mapping applies as is.**
- Xbox ini offsets are 16 (a full texel on the 1024×512 copy, no blur); the PS2 uses 8 (half texel + LINEAR = the soft blur). Restore the UVs after pass 2 (the quad persists across frames). Code cave candidate: the dead Xbox blur pass 0x24ECAA (0x1F8 B). See findings "Phase 3 prep".

**P3 — Radiosity. BUILT (2026-09-24):** `patches/p3_radiosity.py` → `.json`, 978 of 1413 B in place (the stock function ends at 0x24E512; 0x24E513+ are other functions). SkyGfx's fixed-function PS2 radiosity on the two Xbox surfaces: `0x24BB7B` copies F to C; downsample hops ping-pong C → backbuffer corner → C strip x ≥ 640 (postfx camera `0x5F4B30`, SkyGfx geometry with UC/VC 2); highlight `2D − limit` = stage-0 ADDSIGNED2X with vertex grey 128 − L·128/255; restore the backbuffer 1:1, add the stretched highlight with SRCALPHA/ONE, A = intensity (/255) × renderPasses; copy again (UpdateFrontBuffer). No new raster and no Initialise patch. E6 live: 100 % within ±2 of `model()` at noon, midnight and on the darkness-filter path. Ship `pe_bRadiosity 1` (on the ISO it replaces the equivalent `devkit_memory` line, same size).

Original design (kept for reference): replace the body of `0x24DF8E` (≈2.4 KB up to 0x24E90C, used as the code cave). Keep its ABI: stack = limit, filterPasses, intensity; EAX = renderPasses. It is also called by the darkness filter with (45, 0, 255, 2).
1. Re-copy the filtered backbuffer (call `0x24BB7B`).
2. Downsample ×filterPasses, halving each time with LINEAR filtering and UV correction `(corr+0.5)/w` (globals 0x3CE7C4..D8), ping-ponging between the backbuffer corner and a small raster.
3. Highlight pass with fixed-function stages: stage0 `SUBTRACT(TEXTURE, TFACTOR=limit/2)`, stage1 `ADD(CURRENT, CURRENT)` → `2D − limit`.
4. Restore the full frame from the fb copy (`ONE/ZERO`), then add the stretched bloom with `SRCALPHA/ONE`, alpha = intensity, ×renderPasses.

- Decision point: first reverse how `0x24BB7B`, heat haze `0x24D7E2` and underwater `0x24F309` get framebuffer rasters and copies, and **reuse those primitives**. Use a D3D `SetRenderTarget` to a linear texture only if copy-based ping-pong is not available.
- Raster creation: patch `CPostEffects::Initialise` (locate it via writers of `0x5F4B28`) to allocate one ½-res raster.
- Enable via the ini `pe_bRadiosity 1` (flag 0x5F4B1C, reader 0x24CD43).

**P4 v2 — Building lighting. DONE (2026-09-25):** G 0.91 / N 0.80 / KA 1.80 on the building pipes only (c23 + c15), boot-tested in `gtasa_p2p3p4p5.xiso` and signed off; see §18 and findings "P4 v2 step 3–4", "Ground investigation". History follows.

**P4 v1 — Building ambient. BUILT, not shippable as is (2026-09-24):** `patches/p4_building_ambient.py`. Three 86-byte c15 clamp blocks are rewritten in place (0x166D91 and 0x167700 always; 0x16A30A only for the building VS `[0x5F2934]`/`[0x5F2940]`, because that setup is shared with the vehicle/unlit pipes): c15 = 2·min(pAmbient, 1), w kept. E7 live: ambient response exactly 2.00×, vehicles untouched. A VS-operand edit is impossible because the ILU pairing uses operand C. Natural scenes get *worse*: the PS2 prelight is ~0.87× (day) / ~0.75× (night) of the Xbox's [S], and the common ~0.87 could be textures [H]. Options: (a) 2-parameter P4 (ambient ×~1.75, prelight ×~0.87, night set ×~0.86 via c20/c23 on building pipes only), after a texture check; (b) drop P4. **Chosen: (a)** (user, 2026-09-24). Details: findings "Phase 5". Original text follows.

**P4 — Building ambient (phase 4).** Find the `SetVertexShaderConstant` upload of ambient in pipe `0x53F20096` (VS 0x3C9DA8/0x3C9E90, creator ~0x167B7A; also 0x9E/0xA0/0xA2 via check 0x1688ED). Scale ×2 [H5]. Only if hue-neutral dark-area captures still differ: move the ambient add after matCol and use VS `×0.5` + stage `MODULATE2X`, which is a microcode edit.

Key Xbox anchors [C]:
- PostFX Render `0x24C537` (caller 0xF362C; disable-all byte 0x5F4B1F).
- Current PostFX floats `0x6C88B8–D4`; timecyc limit `0x6C88DC`.
- Lighting mult `0x24C6B6–0x24C75F`.
- stream.ini parser `0x157EFD`; timecyc loader `0x156F55`.
- **P7 — ini defaults. BUILT (2026-10-12):** `patches/p7_ini_defaults.py`. The pe handlers' stores at 0x158063/84/A2/C0 → NOP (the .data pe defaults are already 8); `pe_bRadiosity` handler `setne` → `sete` (0x1580E1) and the only reader, the guard at 0x24CD4A, `je` → `jne`. So the byte 0x5F4B1C now means "radiosity off": on with no line or with `1`, off with `0`. The stock `stream.ini` gives the PS2 settings, so the release is `default.xbe` only (v1.1, sha1 84e14eef…). `requires` P2 + P3.
- `RwRenderStateSet` = `[0x75DE80]`; `Im2DRenderIndexedPrimitive` = `[0x75DE94]`; index buffer `0x3CE82C`.
- RW state ids: 1 raster, 6 ztest, 8 zwrite, 9 filter, 10 src, 11 dst, 12 vtxalpha, 14 fog.

## 10. Shader modifications

- None for P1–P3: fixed-function stages suffice. (2026-09-24: the RW Xbox driver does create ≥8 pixel shaders at 0x2B3069…, but PS = 0 during PostFX. Im2D goes through pass-through vertex shaders created at 0x2AB5A2: `oD0 = v1`, `oT0 = v2`.)
- P4 may need a vertex-shader microcode edit (in-place in .data; the instruction count must not grow unless the blob is relocated).
- No external shader files can be loaded; everything lives in the XBE [C].

## 11. Exact reverse-engineering targets (remaining)

Resolved 2026-09-24 (details in `docs/findings.md`):
- **5.** The building lighting is `oD0 = (v1·b + v2·(1−b))·c20 + c15·c21` in all 8 building VS blobs. Constants come from `SetVertexShaderConstant1/4` in the setups 0x166C70/0x1675DF/0x16A1E5, not from inline push-buffer writes (see findings "Phase 5").
- **1.** `0x24BB7B` is a render pass into the postfx camera (not CopyRects). The copy is 1024×512 X8R8G8B8 swizzled; the backbuffer is LIN_X8R8G8B8 640×480.
- **2.** Texture-stage layout (see §9).
- **6.** Clock / weather / player on both platforms, plus CTimer timeScale (Xbox 0x56B9AC, PS2 0x66C1A8).
- **7.** SetGammaRamp: see §5. Flicker / soft display filter (2026-09-25): the game never calls them; D3D init sets the XDK defaults (flicker 5 at 0x3637FF, soft display off at 0x363828). SDTV encoder only, no patch (findings "Phase 6A").

Other anchors found:
- D3D device `[0x36E278]`: PS `+0x784`, VS `+0x794`, gamma ramps `+0x1C28+0x1DC`.
- XDK symbols come from the Cxbx-Reloaded symbol cache.

Original list:

1. `0x24BB7B`: the fb-copy method (CopyRects vs RW raster render) and the raster size/format of `0x5F4B28`. Also the backbuffer format (tests H3).
2. The Xbox D3D deferred texture-state layout: the Xbox `D3DTSS_*` index order, to confirm the ALPHAOP, TFACTOR (RS), COLORARG1/2 slots and stage-1 offsets near `0x36BBF8`. Cross-check against RW's 2D setup `0x2AB710–0x2AB820` and the XDK 5849 `D3D__TextureState` layout.
3. `CPostEffects::Initialise` (writers of 0x5F4B28) and the Im2D vertex layout at `0x5C7318` (verify order vs screen corners). **3a (vertex layout) resolved 2026-09-24; 3b (Initialise) still open, needed for P3.**
4. Heat haze `0x24D7E2` / underwater `0x24F309`: existing Xbox fb-effect techniques to reuse for P3.
5. The ambient constant upload for pipe 0x53F20096. Decode VS microcode with an NV2A vertex-program decoder (port the decoder from xemu `hw/xbox/nv2a/vsh.c`).
6. `CClock` hours/minutes and `CWeather` Old/New/Forced type on **both** platforms, plus the player position/heading. Anchor from the timecyc interpolation code and the weather-cheat handlers; these are needed by the validation harness.
7. [H] `SetGammaRamp` / `SetFlickerFilter` / `SetSoftDisplayFilter` calls in the XBE (display softness).

## 12. Tools / scripts

Installed: python + capstone/pefile/PIL/numpy/keystone, java 21, PCSX2 (`E:\Emuladores\PCSX2`, PINE on), xemu 0.8.136 (`E:\Emuladores\xemu`, launch `xemu-gdb.bat`), Cxbx-Reloaded (`E:\Emuladores\Cxbx-Reloaded`), Ghidra 12.1.4 (`F:\Tools\ghidra`), xdelta (`F:\Tools\xdelta`), ffmpeg, gh, git. Harness tools: `tools/xemu_gdb.py` (also `--cxbx`), `tools/pcsx2_pine.py`, `tools/ps2_cheats.pnach`.

Optional: the ghidra-emotionengine plugin if PS2 code must be re-verified; clang/lld for C-authored patch blobs.

Project scripts (under `tools/`; usage in CLAUDE.md):
- `xbe_patch.py`: applies `patches/*.json` (VA, original bytes, new bytes). It **refuses if the original bytes mismatch** and verifies the input SHA1. Emits `default.xbe` + an xdelta/BPS diff.
- `predict_filter.py`: given a postfx-off frame + the c1/c2 read from memory, it computes the expected PS2/Xbox output (assert-based self-check with the LA 12:00 gains above).
- `compare.py`: per-scene metrics (see §16).
- `ps2_cheats.pnach` / `xemu_gdb.py`: set time, weather, position; freeze the clock.

## 13. Experiments (cheapest → most invasive)

| # | Experiment | Expected evidence |
|---|---|---|
| E0 | Build the capture harness: xemu + PCSX2, fixed scenes, time/weather pokes | Paired 640×480 PNGs per scene |
| E1 | ini only: basemult 0.4, rate 0.0008 | Small change in dark areas only (confirms low rank) |
| E2 | ini `pe_bRadiosity 1` on the stock XBE | Nothing or line artifacts → confirms H2 |
| E3 | **Offline filter transplant**: xemu poke 0x5F4B1F=1 (postfx off), capture, apply the PS2 formula in Python, compare to the PS2 capture | Quantifies H1 before any XBE edit |
| E4 | P1 ColourFilter patch | Patched frame == `predict_filter.py` within ±2 levels (H3) |
| E5 | P2 blur | Edge-sharpness metric matches PS2 |
| E6 | P3 radiosity (+ini flag) | Highlight bloom energy matches PS2; test the /128 vs /255 knob (H4) |
| E7 | P4 building ambient ×2 | Dark-region luminance gap closes, hue unchanged (H5). **2026-09-24:** mechanism ✅ (exactly 2×); natural scenes overshoot, so the 2-parameter P4 is next |
| E8 | Optional: foliage dual-pass, grass ambient | Visual only |

## 14. Evidence per experiment

Each run writes `captures/<scene>/<variant>.png` plus `metrics.json`. Each patch has a JSON with original-bytes guards. A per-phase note in `docs/findings.md` gives: hypothesis, prediction, result, Confirmed/Refuted.

## 15. Final mod architecture

```
SA-PS2Atmosphere/
  README.md                  install + credits (SkyGfx/aap research)
  default.xbe.xdelta         (or .bps) vs Rev 1 SHA1 10EFB868…; no Rockstar bytes shipped beyond the diff
  apply_patch.py / .bat      verifies the hash, applies xdelta, edits stream.ini lines in place
  stream.ini.patch.txt       the 5 lines to set (not the whole Rockstar file)
```
- Toggles stay data-driven through the existing ini keys: `pe_bRadiosity` and `pe_*` offsets for blur.
- Radiosity passes and intensity keep their exe defaults. A new ini key is only worth adding if it's cheap in the parser cave.
- XBE signature: retail signing cannot be preserved; the target is softmodded/modchipped consoles and xemu, neither of which checks it [S].
- **ISO patches (v1.1, 2026-10-12):** `tools/iso_xdelta.py` writes `xiso.xdelta` (game partition, 7,419,363,328 B) and `redump-iso.xdelta` (Redump, 7,825,162,240 B), about 29 KB each. Every 8 MiB window is a same-offset COPY plus ADDs of the changed bytes, with an adler32 per window. The Redump video-partition windows are unchecksummed: we don't have those bytes, and the copy reproduces them. A wrong image fails with "checksum mismatch".
- **v1.1 (2026-10-12):** P7 makes `stream.ini` edits unnecessary, so `apply_patch.py` patches only `default.xbe` and refuses a v1.0 XBE with a "restore the original" hint. The build below uses `dist/default_v1.1.xbe` (P2 + P3 + P4 + P5 + P6b + P7) and `SA-PS2Atmosphere-v1.1.zip`.
- **As built (release v1.0 = the v0.5 build, 2026-10-12):** sources in `release/` (`README.md`, `apply_patch.py`). `stream.ini.patch.txt` was folded into the README, and there is no `.bat`, because the manual route (xdelta GUI + Notepad) covers users without Python. `apply_patch.py` takes a game folder or an image (patched in place via `xdvdfs_extract.image_files`). Either way it first saves the original as `*.bak`, the image as a full copy; the copy goes through `.bak.part` so an interrupted copy never counts as a backup, and an existing `.bak` is never replaced. It verifies the stock SHA1 of both files before any write and the v0.5 SHA1 after, and makes the ini edits as same-length swaps (`devkit_memory\t38000` → `pe_bRadiosity\t\t\t\t\t1`, `16` → `\t8`). The xdelta has no secondary compression (older decoders lack lzma) and its app header names `default.xbe`. Build:
  ```
  xdelta3 -e -9 -S none -A=default.xbe//default.xbe/ -f -s work/xbox/default.xbe dist/default_v1.1.xbe dist/SA-PS2Atmosphere/default.xbe.xdelta
  N="Grand Theft Auto - San Andreas (USA) (En,Es) (Rev 1) (PS2 Atmosphere v1.1)"
  py tools/iso_xdelta.py work/xbox/gtasa_stock.xiso work/xbox/gtasa_v1.1.xiso dist/SA-PS2Atmosphere/xiso.xdelta --name "$N.xiso"
  py tools/iso_xdelta.py work/xbox/gtasa_stock.xiso work/xbox/gtasa_v1.1.xiso dist/SA-PS2Atmosphere/redump-iso.xdelta --redump --name "$N.iso"
  cp release/README.md release/apply_patch.py xdvdfs_extract.py dist/SA-PS2Atmosphere/
  py -m zipfile -c dist/SA-PS2Atmosphere-v1.1.zip dist/SA-PS2Atmosphere
  ```

## 16. Testing / validation procedure (the feedback loop)

- **Deterministic correctness loop (primary, fast):** freeze the world (timeScale = 0); read the real call-site args with `xemu_gdb.py filterargs`; capture the raw frame by NOP-ing only `call 0x24F007` at 0x24CAF5 (the postfx disable byte also changes other passes, so it is not a raw frame); **linearize captures with the active gamma ramp**. Original text: pause xemu; read c1/c2 at `0x6C88B8`; capture the frame with postfx off and on. Assert `patched == predict_filter(raw, c1, c2)` within ±2 levels. This checks each patch against its formula without any need to align scenes across consoles.
- **Fidelity loop (PS2 reference):** scenes = LS Grove St sunset 19:00–20:00, LS noon, LS midnight, SF fog, LS rain, Red County countryside, Las Venturas desert noon, one interior.
  - Force weather and hour and freeze the clock on both platforms (pnach on PS2, GDB pokes on xemu).
  - Teleport the player to the same coordinates and heading, and reset the camera behind the player.
  - PCSX2: **software renderer or Blending Accuracy = Maximum**, native 1×. The PS2 radiosity's `dst·2−src` blend is otherwise emulated wrong.
  - xemu: 1× surface scale.
- **Metrics (`compare.py`):**
  - mean RGB and R/B ratio;
  - luminance mean + p5/p50/p95;
  - HSV saturation mean;
  - per-channel histogram EMD;
  - CIEDE2000 on hand-picked matched patches (sky, road, wall, foliage);
  - bloom energy (% of pixels > 0.9 luminance);
  - Laplacian variance (blur).
  - Plus a side-by-side / diff image. Global stats tolerate small camera misalignment.
- Acceptance: PS2-vs-patched-Xbox deltas should be at least 3× smaller than PS2-vs-stock-Xbox on R/B and saturation, and visual sign-off beats the metrics.

## 17. Risks and unknowns

- ~~H3: backbuffer alpha content for pass 2~~ resolved (X8 copy; the dilution was the Xbox blur pass).
- The Xbox blur pass also gives a slight softness; with it off, P2 must supply the PS2 softness.
- ~~Real hardware: the formulas are verified in LLE xemu + HLE Cxbx only~~ resolved 2026-10-12: v1.0 runs on a real Xbox (Cerbios + XBMC4Gamers), first mission played.
- The Xbox D3D deferred-state index layout; getting it wrong corrupts the HUD. Mitigation: the restore step + the 4-draw fallback.
- ~~The radiosity code cave may be too small~~ resolved: P3 fits in 978 of the 1413 B.
- Radiosity performance at 480p on NV2A (low risk; PS2 did it at ½ res).
- ~~H4 intensity scale~~ resolved: /255.
- PCSX2 blending inaccuracy contaminating the reference.
- ~~The Xbox building pipe formula is inferred from SkyGfx's reimplementation, not yet from Xbox microcode~~ resolved: decoded from the Xbox VS blobs (§11, item 5).
- ~~Only USA Rev 1 is supported~~ USA Rev 0 ported 2026-10-16 (`tools/rev0_map.py`, findings "USA Rev 0 port"). Other regions still need re-anchoring (the patcher refuses by hash).

## 18. Implementation phases / prioritized roadmap

- **Phase 0 — Workspace & harness (E0).** ✅ done 2026-09-24.
  - Create `work/` with **copies** of `default.xbe`/`stream.ini`; never touch the extracted game folders or the ISOs.
  - Write `tools/xbe_patch.py`, `predict_filter.py` (with self-check) and `compare.py`.
  - Install xemu, Ghidra, numpy, keystone.
  - Do RE target 6 (clock/weather/position on both platforms).
  - Suggest `git init` of the project (user decision).
- **Phase 1 — Cheap proofs (E1–E3).** E3 ✅ (H1 confirmed); E2 ✅ (H2 confirmed, 2026-09-24); E1 measured in code + live (the lighting mult scales the filter colours by ≤1+basemult; ~1% at Grove St at night, so low rank confirmed; ini not changed). ini edits, the radiosity-flag test, the offline filter transplant. Gate: H1 confirmed (otherwise re-rank before patching).
- **Phase 2 — P1 ColourFilter (E4).** ✅ E4 passed, v0.1 candidate booted (`work/xbox/gtasa_p1.xiso`); in-game interior check ✅ (2026-09-24, CJ house, 100% within ±2 outside animated pixels, HUD intact); night check ✅ (Grove St 00:00, 98.6% within ±2 on filtered pixels); P5 built and boot-tested (`gtasa_p1p5.xiso`); pause-menu check ✅ (ColourFilter not called in menus; identical to stock). **Phase 2 closed 2026-09-24.** RE targets 1–3, then patch, then the deterministic loop. **This alone delivers the core orange atmosphere.** Ship-able milestone v0.1.
- **Phase 3 — P2 blur (E5)** + ini offsets 8 → v0.2. **In progress:** RE target 3a done; P2 built, live RAM test ✅, E5 ✅ [S] (2026-09-24). Boot test ✅ (`gtasa_p2p5.xiso`, 99.0 % within ±2, HUD intact); visual sign-off ✅. **Phase 3 closed 2026-09-24.**
- **Phase 4 — P3 radiosity (E6).** RE target 4, then Initialise raster + rewrite + ini `pe_bRadiosity 1`, then calibrate against PS2 (H4) → v0.3. **In progress (2026-09-24):** P3 built without a new raster (camera switch into the copy's off-screen strip); PS2 calibration ✅ (H4 = /255); live RAM test ✅ (100 % within ±2 on all three paths). Boot test ✅ (100 % within ±2); pause-menu check ✅ (not called in menus); visual sign-off ✅. **Phase 4 closed 2026-09-24.**
- **Phase 5 — P4 building ambient (E7)** → v0.4, only if dark-scene metrics still diverge. **In progress (2026-09-24):** RE target 5 ✅; H5 mechanism ✅ (PS2 ambient ~2× relative to prelight); P4 built + E7 live ✅ (exactly 2×, vehicles untouched). Natural-scene check ❌: ambient ×2 alone overshoots (night stock ≈ PS2). **Decision (2026-09-24): 2-parameter P4** (ambient + prelight scale), texture check first. Texture/data checks ✅ (equal); PS2 display chain identified (16-bit + merge, reference only); P4 v2 (G/N/KA) built + live ✅, facade matched; night ground +10–20 % open. Harness: `idlecam off` on both consoles. Ground investigated (2026-09-25): DN pipe, the residual is the texture (accepted); boot test ✅ (`gtasa_p2p3p4p5.xiso`); visual sign-off ✅. **Phase 5 closed 2026-09-25.**
- **Phase 6 — Optional polish.** Foliage dual pass, grass ambient, the gamma/display filter investigation (RE target 7). **In progress (2026-09-25):** plan = diagnose first, patch only on a confirmed difference (6A display → 6C grass → 6B foliage). 6A ✅ RE target 7 resolved, no patch (findings "Phase 6A"). 6C ✅ mechanism [S]: the PS2 GS reads the grass alpha (`plants.dat` column A) with 128 = 1.0, the Xbox with 255, so the Xbox grass is half as opaque; RGB ×2 (SkyGfx) refuted. **P6c** (data-only `plants.dat` A → min(2A, 255)) built and boot-tested, **rejected on visual sign-off** (user prefers the v0.4 grass); generator removed (the transform is in findings "Phase 6C"). Release candidate stays v0.4. 6D ✅ heat haze: present and matching on the Xbox (user visual check); the "missing" haze was the frozen clock holding the ramp `0x74AEE0` at 0 (findings "Heat haze"). 6B: H6a ✅ [C] (PS2 GS TEST AFAIL FB_ONLY, AREF 64/128; Xbox GREATER 100/140, discard); **P6b** building-pipe dual pass (`patches/p6b_dualpass.py`, cave 0x24F00C in P2's dead ColourFilter body, `requires` P2), visual sign-off ✅ live; boot test ✅ (opaque geometry, P4 facades and HUD unchanged; pause menu 0 px). **Phase 6 closed 2026-09-25.** v0.5 candidate `work/xbox/gtasa_p2p3p4p5p6b.xiso` (XBE sha1 2d1829b5…). Grass anchors [C]: `CPlantMgr::Initialise` 0x16D239, per-plant draw loop 0x16B8A8 (colour `>>8` at 0x16B9E5, atomic render `call [edi+0x48]` at 0x16BA28).
- **Phase 7 — Distribution.** xdelta + patcher + README; test on a clean Rev 1 copy in xemu (and real hardware if available). **Built and tested 2026-10-12:** release v1.0, `dist/SA-PS2Atmosphere-v1.0.zip` (§15 "As built"). The installer was tested on a clean folder and a clean ISO copy (0 bytes changed outside the two files), and `gtasa_v05_release.xiso` boots in xemu with all 12 blocks live and radiosity 1 (findings "Phase 7"). User sign-off ✅ (2026-10-12, Grove St in game). **Phase 7 closed**; real hardware ✅ 2026-10-12 (Cerbios + XBMC4Gamers, game folder on the HDD; findings "Real hardware").
- **Post-release — USA Rev 0.** ✅ 2026-10-16: v1.1 (P2–P7) ported to Rev 0 (`default.xbe` sha1 1ceae5be…) by proven address translation; `dist/default_rev0_v1.1.xbe` sha1 6883102c…, booted in xemu, user visual sign-off ✅, real hardware ✅ (Cerbios + XBMC4Gamers); installer + Rev 0 xdeltas built and decoded against the real Redump Rev 0 ISO (findings "USA Rev 0 port"). Released as **v1.2** (`dist/SA-PS2Atmosphere-v1.2.zip`, per-revision folders; findings "Release v1.2").
- **Post-release — Europe Rev 1 / Rev 0.** 2026-10-20: v1.1 (P2–P7) ported to Europe Rev 1 (`default.xbe` sha1 f0ed7d69…) and Rev 0 (7a424b08…) with the same proven map; plus **P8** (`patches/p8_eu_regionfree.py`, Europe only: NOPs the game's own `XGetGameRegion() == 4` check, which quits on non-Europe EEPROMs) → `dist/default_eu1_v1.3.xbe` sha1 d4b4a593…, `dist/default_eu0_v1.3.xbe` sha1 acd8ea4a…; installer + xdeltas built and decoded against the real Europe Redump ISOs. Boot ✅ in xemu (NA EEPROM) and on real hardware (NTSC console, Cerbios + XBMC4Gamers), user sign-off ✅. Release v1.3 (`dist/SA-PS2Atmosphere-v1.3.zip`; findings "Europe Rev 1 / Rev 0 port").

### Current state and next session (2026-09-24 – 2026-09-25)

- **Builds:** `dist/default_p1p5.xbe` (P1 + P5; sha1 9c4db1ab…) → `work/xbox/gtasa_p1p5.xiso`, boot-tested. `dist/default_p1.xbe` / `gtasa_p1.xiso` are kept. `dist/default_p2p5.xbe` (P2 + P5; sha1 ed5c41e3…) → `work/xbox/gtasa_p2p5.xiso` (embedded stream.ini pe 8), boot-tested ✅.
- **Disk cleanup (2026-09-25):** only `gtasa_stock.xiso` and `gtasa_p2p3p4p5.xiso` (v0.4) are kept. The v0.2/v0.3 ISOs and the Cxbx copy `work/xbox/game/` are deleted. To rebuild one, copy `gtasa_stock.xiso`, write `dist/default_*.xbe` at sector 348678 and the matching `work/xbox/stream_*.ini` at sector 1998977 (same sizes). For Cxbx, re-copy the extracted Xbox folder to `work/xbox/game/`.
- **Test saves:**
  - xemu HDD: slots 1–3. Slot 2 = EU "Ryder", converted and verified in-game. Slot 1 (2026-09-24) = the same save re-saved by the user with brightness 256 (the genuine v2 "Big Smoke" save that was there is gone from the HDD; the original is still in `xbox_hdd.qcow2.bak_20260924`). It stores brightness 384; set 256 in Options → Display, or with `work/session_tools/xbright.py 256`. Original HDD backed up as `E:\Emuladores\xemu\xbox_hdd.qcow2.bak_20260924`.
  - PCSX2 `Mcd001.ps2` slot 1: "Tagging up Turf", native v3.00 (backup `Mcd001.ps2.bak_20260924`; `mymcplus` is installed via pip).
- **Reference scene:** Grove St (2488.2, −1665.5, 13.3), heading 1.4309, weather 0, at 12:00 and 00:00. Paired captures: `work/session_tools/scene.py`. Existing sets: `captures/grove_{noon,night}_gammafix/`.
- **Capture rule update:** with P5 and brightness 256 the Xbox ramp is the identity, so captures need no linearization. Otherwise read the ramp first (CLAUDE.md "Gamma").
- **P2 boot-tested** (findings "P2 filter blur"). Visual sign-off ✅ with pe 8.
- **P3 built + live-tested** (findings "Phase 4"): `dist/default_p2p3p5.xbe` (sha1 d7e1d28c…) → `work/xbox/gtasa_p2p3p5.xiso` (ini pe 8 + `pe_bRadiosity 1`). Boot-tested ✅, menu ✅, signed off ✅ (v0.3 candidate). Next: Phase 5 (P4 building ambient). Remaining noon gap after P3 is the Xbox ground being brighter than the PS2's before radiosity (upstream: P4/H5 or framing).
- **Phase 5 (2026-09-24):** see §9 P4 and findings "Phase 5". The "inline push buffer" note was a tracer bug: the constants go through SetVertexShaderConstant1/4. Before any capture run `idlecam off` on both consoles. A/B build: `dist/default_p2p3p4p5.xbe` (sha1 b38df22e…), not boot-tested. Decision: **2-parameter P4** (option a).
- **Next session plan (P4 v2):**
  1. ✅ **Texture check (2026-09-24):** textures equal (0.985), vertex prelights equal, and the PS2 display chain is a 16-bit truncation + 2-line merge (−3.5 levels; `work/session_tools/ps2disp.py`). The refit must compare against `disp(Xbox)`. Findings "P4 v2 step 1". Original text: **Texture check.** Decode one Grove St facade texture from the PS2 and Xbox `gta3.img` TXDs, or find it by RwTexture name in both RAMs (`ps2dump.py`, `xdump`), and compare mean colour. If PS2 ≈ 0.87× Xbox, the common factor is texture: fold it into the building lighting only if the user wants buildings matched regardless. If the textures match, the factor is lighting.
  2. **Fit the model.** Model the PS2 as `t·(g·(Pday·(1−b) + n·Pnight·b) + ka·A)`, with the current estimates g ≈ 0.87, n ≈ 0.86, ka ≈ 1.75 (findings "Phase 5"). Apply `ps2disp.disp()` to the Xbox frames first (frame-level after the correction: g ≈ 0.90, n ≈ 0.77, ka ≈ 1.7). Refit from the sweep sets `captures/p4_amb_{night,noon}` (registered facade, `ratio.py` method) plus the interior set.
  3. **Implement on the building pipes only.**
     - ka: the constant in P4's c15 blocks (`addps` → `mulps` by a pooled/stack constant).
     - g: scale c20 (matCol·surfDiff). The per-material upload 0x166EE3 / 0x16AFAD is shared with vehicles, so gate it on RW's current VS `[0x3D4750]` as P4 does.
     - n: scale c23.x (the night weight) in the DN setups 0x166C70/0x1675DF.
  4. **Live tests.** Run `p4live.py` + `p4fid.py` at 00:00 and 12:00 plus the interior; then the boot test and ISO.
- **P4 v2 status (2026-09-24):** steps 1–2 ✅; P4 v2 built (G 0.91, N 0.80, KA 1.80; c23 + c15) and live-tested ✅. Facade matches at 00:00 and 12:00 (±4 %); the night ground overshoots 10–20 % (findings "P4 v2 step 3–4"). Open: the ground at night, then the boot test.
- **Decision (user, 2026-09-24):** no parameter compromise. The next session investigates the ground first.
- **Next session plan (ground):**
  1. **Which pipe/VS draws the ground.** Log RW's current VS `[0x3D4750]` and the pipe for `lae2_roads89`, `lae2_landhub05` and the decal `hub_grnd_alpha` (breakpoint at the DN setups 0x166C70/0x1675DF vs 0x16A1E5, while looking only at the ground). A non-DN blob gets G/N nowhere (prelight ×1) and KA 1.8.
  2. **Alpha decal layers.** `hub_grnd_alpha`/`hubst4alpha` are blended over the ground. Compare the ground with the decal models hidden, or check whether the PS2 draws them differently.
  3. **Night lamp pools.** At 00:00, exclude the areas lit by street lamps (pointlight/shadow textures) and refit n/ka on the unlit ground only.
  4. **Refit** with `p4fit.py` (env `BOX=y0,y1,x0,x1`) on `captures/p4v2_{night,noon}` and `captures/p4v2_fid_*`. Then set per-pipe parameters if the ground is a separate pipe, or else fold the finding into the model. Then live re-check, boot test and ISO.
  - **Ground status (2026-09-25):** steps 1–4 done (findings "Ground investigation").
    - The ground is drawn by DN blobs (89 %), so it gets G/N/KA.
    - The residual is the Xbox asphalt texture (`plaintarmac1` 0.92 PS2/Xbox), accepted as asset content (user, option a).
    - About 7 % remains, at night only: a dark-end loss in the PS2 colour path [H], not specific to the ground.
    - Lamp pools, radiosity and registration are refuted.
    - P4 v2 keeps G 0.91 / N 0.80 / KA 1.80.
    - Boot test ✅ (2026-09-25): `work/xbox/gtasa_p2p3p4p5.xiso` (sha1 2d98911b…) matches the live poke. Facade PS2/disp(Xbox) is 1.06/1.05/1.03 at 00:00 and 1.01/1.04/1.05 at 12:00.
    - Visual sign-off ✅ (user, 2026-09-25). Phase 5 closed; v0.4 candidate = `gtasa_p2p3p4p5.xiso`.
  - Tools (in `work/`, not committed): `session_tools/ps2disp.py` (PS2 display model, selftest), `p4fit.py`, `vsc.py`, `ps2entry.py`, `imgtool.py`; `work/tex/txdmean.py`, `prelight.py`, `pmatch.py`.
- **Session start checklist:** run `idlecam off` on both consoles; check the xemu pad is connected (a black "reconnect controller" frame means it isn't); check P4 with `p4live.py state` (on the v0.3 ISO it stays off; the v0.4 ISO `gtasa_p2p3p4p5.xiso` boots with it on).

## Execution context (for any executor)

- Local reverse-engineering workstation only: no database, no web app, no VLD/HML/PRD target.
- Game originals (read-only):
  - `F:\Projects\GTA_SA_PS2ToXboxExperience\Microsoft - Xbox\Grand Theft Auto - San Andreas (USA) (En,Es) (Rev 1)\`
  - `…\Sony - PlayStation 2\Grand Theft Auto - San Andreas (USA) (v3.00) (Rev 1)\`
- Deliverables: `F:\Projects\GTA_SA_PS2ToXboxExperience\{tools,patches,work,captures,docs,dist}\`.
- Emulators: PCSX2 `E:\Emuladores\PCSX2` (PINE port 28011); xemu 0.8.136 `E:\Emuladores\xemu` (launch `xemu-gdb.bat`, GDB stub port 1234).
- The ISOs and extracted folders must never be modified.
