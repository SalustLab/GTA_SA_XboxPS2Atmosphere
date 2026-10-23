<p align="center">
  <img src="docs/media/banner.jpg" alt="PS2 Atmosphere: the same Grove Street frame, original Xbox on the left, patched on the right" width="100%">
</p>

<h3 align="center">The orange haze is back.</h3>

<p align="center">
  A binary patch that gives the original-Xbox <i>GTA: San Andreas</i> the look of the PS2 version<br>
  and keeps everything the Xbox does better.
</p>

<p align="center">
  <a href="https://github.com/SalustLab/GTA_SA_XboxPS2Atmosphere/releases/latest"><img src="https://img.shields.io/github/v/release/SalustLab/GTA_SA_XboxPS2Atmosphere?label=release&color=FFC440" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/platform-original%20Xbox-107C10?logo=xbox&logoColor=white" alt="Platform: original Xbox">
  <img src="https://img.shields.io/badge/game-GTA%20SA%20%C2%B7%20USA%20%2F%20Europe%20Rev%200%20%2F%20Rev%201-F28C28" alt="Game: GTA San Andreas USA / Europe Rev 0 / Rev 1">
  <img src="https://img.shields.io/badge/runs%20on-xemu%20%7C%20softmod-4c8dff" alt="Runs on xemu or a softmodded console">
  <img src="https://img.shields.io/badge/patch-1.4%20KB%20xdelta-9b59b6" alt="Patch: 1.4 KB xdelta">
  <img src="https://img.shields.io/badge/game%20files-none%20included-2ea44f" alt="No game files included">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/SalustLab/GTA_SA_XboxPS2Atmosphere?color=blue" alt="MIT license"></a>
  <a href="https://ko-fi.com/salustlab"><img src="https://img.shields.io/badge/Ko--fi-support-ff5e5b?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a>
</p>

<p align="center">
  <b><a href="https://github.com/SalustLab/GTA_SA_XboxPS2Atmosphere/releases/latest">Download</a></b> ·
  <a href="#see-it">See it</a> ·
  <a href="#install">Install</a> ·
  <a href="#compatibility">Compatibility</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#for-tinkerers">For tinkerers</a> ·
  <a href="#credits">Credits</a> ·
  <a href="#support">Support</a>
</p>

---

## Why this exists

If you played San Andreas on a PS2, you remember the air. The orange haze over Los Santos at sunset, the soft glow on every bright wall, that slightly dreamy blur over everything.

The Xbox port is the sharper version: better textures, longer draw distance, 480p. But it lost the mood. Daylight goes grey and sunsets go flat.

I wanted both, so I took the game apart.

The first surprise: `timecyc.dat`, the file that holds the colours for every hour and every weather, is **byte-identical on both consoles**, and so are the other assets. The difference is all in the engine code. Here is what the Xbox build does differently:

- it blends the colour filter with a different formula;
- it runs an extra blur pass that washes the filter out;
- it ships with radiosity off;
- it lights buildings differently;
- it treats foliage transparency its own way.

**PS2 Atmosphere** is a set of small, surgical x86 patches to `default.xbe` that put the PS2 behaviour back. Each one was checked against PS2 captures of the same frozen scene.

## See it

<p align="center">
  <img src="docs/media/compare_grove.jpg" alt="Grove Street at 12:00, 19:00 and 00:00: PS2, original Xbox, Xbox with the patch" width="100%">
  <br><sub>Grove Street, same spot, same weather, clock frozen. Left to right: <b>PS2</b> · <b>Xbox original</b> · <b>Xbox + PS2 Atmosphere</b>.</sub>
</p>

Each loop below flips between the original Xbox and the patched game on the exact same frame:

| Noon | Golden hour |
|:---:|:---:|
| <img src="docs/media/flip_grove_1200.webp" alt="Grove Street 12:00, original vs patched" width="400"> | <img src="docs/media/flip_grove_1900.webp" alt="Grove Street 19:00, original vs patched" width="400"> |
| **Midnight** | **Palm canopies (zoomed)** |
| <img src="docs/media/flip_grove_0000.webp" alt="Grove Street 00:00, original vs patched" width="400"> | <img src="docs/media/flip_palms.webp" alt="Glen Park palm fronds, original vs patched" width="400"> |

<p align="center">
  <img src="docs/media/compare_palms.jpg" alt="Glen Park foliage: PS2, original Xbox, Xbox with the patch, with a zoom on the palm fronds" width="100%">
  <br><sub>Glen Park. The Xbox cuts palm fronds into hard, broken shapes; the PS2 alpha test keeps them full and soft. The patch draws them the PS2 way.</sub>
</p>

## What changes, what stays

<table>
<tr>
<td width="50%" valign="top">

**What you get from the PS2**
- The colour filter: the warm orange (or green, or grey) grade from `timecyc.dat`, at full strength
- The soft blur on that filter
- The radiosity glow on bright surfaces
- PS2 building lighting: stronger ambient light, softer baked light
- Full, continuous foliage, palm fronds and power lines
- A neutral display gamma at the default brightness

</td>
<td width="50%" valign="top">

**What you keep from the Xbox**
- DXT textures
- Longer draw distance (LODs)
- 480p output
- The Xbox car reflection shader
- Your saves: the patch doesn't touch them

</td>
</tr>
</table>

## Install

You need **your own** copy of GTA San Andreas, **USA** or **Europe**, either revision:

| Version | Original `default.xbe` SHA1 |
|---|---|
| USA Rev 1 (Platinum Hits / *The Trilogy*) | `10EFB868F13D6944AA6684A52CAC5156393F14C5` |
| USA Rev 0 (original release) | `1CEAE5BE753B3675CE8C5C79D7F496DFC0AD597D` |
| Europe Rev 1 | `F0ED7D693C5B9B579FFEF38CF40AE0EFAE6A71D3` |
| Europe Rev 0 (original release) | `7A424B08E79A4FEBA39EC8ACF2168C6C94BC0B5A` |

 The whole mod is one file: only `default.xbe` changes, and `stream.ini` and everything else stay untouched.

**With any xdelta GUI (easiest):**

1. Grab **`SA-PS2Atmosphere-v1.3.zip`** from [Releases](https://github.com/SalustLab/GTA_SA_XboxPS2Atmosphere/releases/latest) and unzip it.
2. Open your xdelta patcher (Delta Patcher, xdelta UI, any of them) and pick the patch that matches your file:

   | Your file | Patch (in your version's folder: `GTA SA (USA) Rev 1`, `GTA SA (USA) Rev 0`, `GTA SA (Europe) Rev 1` or `GTA SA (Europe) Rev 0`) |
   |---|---|
   | `default.xbe` from a game folder | `default.xbe.xdelta` |
   | Full game ISO (7,825,162,240 bytes) | `iso.xdelta` |
   | XISO of the game partition (7,419,363,328 bytes, boots in xemu) | `xiso.xdelta` |

   The ISO patches are made for the Redump dumps. Not sure which version you have? The Redump names are `Grand Theft Auto - San Andreas (USA) (En,Es) (Rev 1)`, `… (USA) (En,Es)` (Rev 0), `… (Europe) (En,Fr,De,Es,It) (Rev 1)` and `… (Europe) (En,Fr,De,Es,It)` (Rev 0). Or use the script below, which picks the right patch by itself.

3. Apply. Keep the original somewhere safe. The wrong file is rejected with *"checksum mismatch"*.

**With the script (it also patches ISO images in place):** drop [`xdelta3.exe`](https://github.com/jmacd/xdelta-gpl/releases) next to `apply_patch.py` and point the script at your game folder or `.iso` / `.xiso`:

```
py apply_patch.py "D:\Games\GTA San Andreas"
py apply_patch.py "D:\xemu\GTA San Andreas.iso"
```

Before it writes a single byte, the script checks `default.xbe` and keeps the original as `.bak` (a full copy for an ISO). Afterwards it verifies the result.

Already on v1.1 or v1.2 (USA)? Nothing to do: v1.3 only adds Europe (region-free). Coming from v1.0? Patch the original `default.xbe` again. The `stream.ini` lines that v1.0 added can stay. Full guide: [`release/README.md`](release/README.md).

> [!TIP]
> Keep **Brightness** at its default. Saves remember their own brightness, so hit *restore defaults* in the Display menu once. The neutral gamma is calibrated for that setting.

## Compatibility

| Setup | Status |
|---|---|
| GTA San Andreas, USA, Rev 1 (Platinum Hits / The Trilogy, title ID 545400A3) | Supported |
| GTA San Andreas, USA, Rev 0 (original release, title ID 54540082) | Supported since 2026-10-16: same patches, ported address by address; tested in xemu and on real hardware |
| GTA San Andreas, Europe, Rev 1 (title ID 545400A4) and Rev 0 (original release, title ID 54540086) | Supported since 2026-10-20: same patches, ported address by address, plus P8 (region-free); tested in xemu and on real hardware (NTSC console) |
| [xemu](https://xemu.app) | Tested: boots, loads saves, all patches live |
| Real Xbox, Cerbios + XBMC4Gamers (game folder on the HDD) | Tested with v1.0, v1.1 and v1.2 (Rev 1 and Rev 0): boots and plays |
| Other softmodded / modchipped Xbox | Expected to work: the patched XBE loses its retail signature, which modded consoles don't check |
| Other regions or editions | Not supported: different binaries; the installer refuses them |
| Stock, unmodded console | Not supported: won't boot an unsigned XBE |

<p align="center">
  <img src="docs/media/real_hardware.jpg" alt="PS2 Atmosphere v1.0 running on a real original Xbox: Grove Street under an orange evening sky on the TV, the console below" width="420">
  <br><sub>v1.0 on real hardware: an original Xbox with Cerbios + XBMC4Gamers, Grove Street in the evening.</sub>
</p>

## How it works

Everything happens inside one frame of the game's renderer. Each patch replaces Xbox code in place, usually inside the original function's own bytes, so the file size never changes.

```mermaid
flowchart LR
    A["3D world"] --> B["Building pipe<br/>P4 · PS2 lighting<br/>P6b · PS2 alpha test"]
    B --> C["PostFX<br/>P2 · colour filter + soft blur"]
    C --> D["P3 · radiosity glow"]
    D --> E["HUD"]
    E --> F["Display<br/>P5 · neutral gamma"]
```

| Patch | What it does | How I checked it |
|---|---|---|
| **P2** | PS2 colour-filter formula and its soft blur; also turns off the Xbox blur pass that washed it out (this supersedes the first version, P1) | 99 % of pixels within ±2 of the predicted PS2 result, in the booted game |
| **P3** | PS2 radiosity (the fixed-function path documented by SkyGfx), intensity calibrated against the PS2 | 100 % of pixels within ±2 of the model, in the booted game |
| **P4** | PS2 building lighting on the building pipes only: baked light ×0.91 (the night set a further ×0.80), ambient ×1.8 | Fitted to paired PS2/Xbox captures, day and night |
| **P5** | Default brightness becomes an identity gamma ramp, as on the PS2 | Noon frame colour error vs PS2: ΔE 5.7 → 1.0 |
| **P6b** | Foliage drawn with PS2 alpha-test semantics (a dual pass) | Only alpha-tested textures change (1.7–3.9 % of pixels); opaque geometry is identical |
| **P7** | Makes the PS2 `stream.ini` settings (blur offsets 8, radiosity on) the built-in defaults, so the stock `stream.ini` needs no edit. `pe_bRadiosity 0` still turns the glow off | Boots with the untouched `stream.ini`. The installer's ISO is byte-identical to the one played in xemu |
| **P8** | Europe only: drops the game's own EEPROM region check (`XGetGameRegion() == Europe`), so the Europe disc runs on any console | The patched XBE is byte-identical to the one played on an NTSC console and in xemu with a North American EEPROM |

The full research is public in this repo: [`docs/PLAN.md`](docs/PLAN.md) has the plan, hypotheses and roadmap, and [`docs/findings.md`](docs/findings.md) is the dated lab log of every address, experiment and verdict.

## Known limits & what's next

- **Night streets** come out a touch brighter than on the PS2. I traced most of it to the Xbox asphalt texture itself, which is about 6 % brighter than the PS2's. That's game data, not code, and this project keeps the Xbox textures, so I left it alone.
- **Grass**: I built a PS2-accurate grass tweak, put it side by side with the stock grass, and liked the Xbox grass better. The mechanism is documented in the lab log, but it isn't shipped.
- **Real hardware**: tested on one console so far (Cerbios + XBMC4Gamers). Reports from other setups (softmods, other BIOSes, dashboards) are very welcome.
- **Other versions**: USA and Europe, Rev 1 and Rev 0. Another build would need its own address map (`tools/rev0_map.py` shows how Rev 0 and Europe were ported).

## For tinkerers

<details>
<summary><b>Build it yourself, poke at it, break it</b></summary>

### Requirements

- Your own dump of `default.xbe`, one of the four versions above (SHA1s above). Every tool refuses any other input. USA Rev 1 goes in `work/xbox/`, USA Rev 0 in `work/xbox_rev0/`, Europe Rev 1 / Rev 0 in `work/xbox_eu1/` / `work/xbox_eu0/`.
- Python 3.13 with `capstone`, `pefile`, `pillow`, `numpy` and `keystone-engine`.
- For live testing: xemu with its GDB stub, and PCSX2 with PINE for the PS2 reference.

No game data lives in this repo. Patch JSONs guard the original bytes with a SHA1 (`orig_sha1`) instead of storing them.

### Patch pipeline

```sh
py patches/p2_filterblur.py          # each generator assembles its patch (keystone) and writes the JSON
py tools/xbe_patch.py work/xbox/default.xbe dist/default_v1.1.xbe \
   patches/p2_filterblur.json patches/p3_radiosity.json patches/p4_building_ambient.json \
   patches/p5_display_gamma.json patches/p6b_dualpass.json patches/p7_ini_defaults.json
```

For the other versions, run each generator with `--rev0` (USA Rev 0), `--eu1` or `--eu0` (Europe Rev 1 / Rev 0): it writes `patches/pN_*.rev0.json` / `.eu1.json` / `.eu0.json`, with every USA Rev 1 address mapped through `tools/rev0_map.py` (proven pairs cached in `patches/rev0_map.json` / `eu1_map.json` / `eu0_map.json`). Apply those to that version's `default.xbe` the same way.

`xbe_patch.py` refuses a wrong input hash (a non-Rev 1 JSON names its input in `xbe_sha1`), targets in BSS, overlapping patches, any mismatch in the original bytes, and patches whose `requires` are missing (P6b needs P2; P7 needs P2 and P3). Europe also applies `p8_eu_regionfree` (built with `--eu1` / `--eu0` only). Every script has a self-check: `py <script> --selftest`.

### Building the release

```sh
R=dist/SA-PS2Atmosphere-v1.3; mkdir -p "$R/GTA SA (USA) Rev 1" "$R/GTA SA (USA) Rev 0" "$R/GTA SA (Europe) Rev 1" "$R/GTA SA (Europe) Rev 0"
# Rev 1
xdelta3 -e -9 -S none -A=default.xbe//default.xbe/ -f -s work/xbox/default.xbe dist/default_v1.1.xbe "$R/GTA SA (USA) Rev 1/default.xbe.xdelta"
N="Grand Theft Auto - San Andreas (USA) (En,Es) (Rev 1) (PS2 Atmosphere v1.2)"
py tools/iso_xdelta.py work/xbox/gtasa_stock.xiso work/xbox/gtasa_v1.1.xiso "$R/GTA SA (USA) Rev 1/xiso.xdelta" --name "$N.xiso"
py tools/iso_xdelta.py work/xbox/gtasa_stock.xiso work/xbox/gtasa_v1.1.xiso "$R/GTA SA (USA) Rev 1/iso.xdelta" --redump --name "$N.iso"
# Rev 0
xdelta3 -e -9 -S none -A=default.xbe//default.xbe/ -f -s work/xbox_rev0/default.xbe dist/default_rev0_v1.1.xbe "$R/GTA SA (USA) Rev 0/default.xbe.xdelta"
N="Grand Theft Auto - San Andreas (USA) (En,Es) (PS2 Atmosphere v1.2)"
py tools/iso_xdelta.py work/xbox_rev0/gtasa_stock.xiso work/xbox_rev0/gtasa_rev0_v1.1.xiso "$R/GTA SA (USA) Rev 0/xiso.xdelta" --name "$N.xiso"
py tools/iso_xdelta.py work/xbox_rev0/gtasa_stock.xiso work/xbox_rev0/gtasa_rev0_v1.1.xiso "$R/GTA SA (USA) Rev 0/iso.xdelta" --redump --name "$N.iso"
# Europe Rev 1; for Europe Rev 0 use t=eu0, the "Rev 0" folder and N without "(Rev 1)"
t=eu1; F="$R/GTA SA (Europe) Rev 1"; N="Grand Theft Auto - San Andreas (Europe) (En,Fr,De,Es,It) (Rev 1) (PS2 Atmosphere v1.3)"
xdelta3 -e -9 -S none -A=default.xbe//default.xbe/ -f -s work/xbox_$t/default.xbe dist/default_${t}_v1.3.xbe "$F/default.xbe.xdelta"   # P2-P8
py tools/iso_xdelta.py work/xbox_$t/gtasa_stock.xiso work/xbox_$t/gtasa_${t}_v1.3.xiso "$F/xiso.xdelta" --name "$N.xiso"
py tools/iso_xdelta.py work/xbox_$t/gtasa_stock.xiso work/xbox_$t/gtasa_${t}_v1.3.xiso "$F/iso.xdelta" --redump --name "$N.iso"
cp release/README.md release/install_instructions.txt release/apply_patch.py xdvdfs_extract.py "$R/"
(cd dist && py -m zipfile -c SA-PS2Atmosphere-v1.3.zip SA-PS2Atmosphere-v1.3)
```

### Tools

| Script | Purpose |
|---|---|
| `tools/xbe_patch.py` | Applies patch JSONs to `default.xbe`, with every safety check above |
| `tools/xemu_gdb.py` | Live pokes and captures through the xemu GDB stub: clock, weather, teleport, timescale, idle cam, capture |
| `tools/pcsx2_pine.py` | The same for the PS2 through PCSX2 PINE |
| `tools/compare.py` | Capture metrics against the PS2 reference, with diff images |
| `tools/predict_filter.py` | Expected PS2 / Xbox colour-filter output for a frame |
| `tools/ps2_cheats.pnach` | Alternative PS2 clock and weather freeze |
| `xdvdfs_extract.py` | Extracts or lists an Xbox XDVDFS image (7-Zip misreads the format) |
| `tools/iso_xdelta.py` | Builds the whole-ISO xdelta patches (XISO and full ISO) for an in-place mod |
| `tools/rev0_map.py` | Maps USA Rev 1 addresses to USA Rev 0 and Europe Rev 1 / Rev 0 by aligning the builds' code; each address is proven by matching code or by references that all agree |
| `release/apply_patch.py` | The player-facing installer |

### Layout

- `patches/`: one generator script per patch, plus its JSON.
- `tools/`: patcher, metrics and the live-memory helpers for both emulators.
- `release/`: installer and player README.
- `docs/`: plan, lab log, and the media on this page.

</details>

## Credits

- **aap**, for [SkyGfx](https://github.com/aap/skygfx): that research into how the PS2 renders San Andreas is the reference this whole project is measured against.
- The [gta-reversed](https://github.com/gta-reversed/gta-reversed) project, for mapping the engine.
- [xemu](https://xemu.app) and [PCSX2](https://pcsx2.net), the two emulators every test in this project ran on.
- [xdelta](https://github.com/jmacd/xdelta), for the patch format.

## Legal

This is a fan project. It is not affiliated with or endorsed by Rockstar Games or Take-Two Interactive. *Grand Theft Auto* and *San Andreas* are their trademarks.

The repository and releases contain **no game code or assets**: the patch is a diff that only applies to your own legally dumped copy, and every tool refuses anything else. Screenshots are shown for comparison. The code in this repository is released under the [MIT License](LICENSE).

## Support

If this patch brought the PS2 look back for you, you can [buy me a coffee on Ko-fi](https://ko-fi.com/salustlab).

<a href="https://ko-fi.com/salustlab"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi"></a>

<p align="center"><sub>Made solo by <b>SalustLab</b>, one patch at a time.</sub></p>
