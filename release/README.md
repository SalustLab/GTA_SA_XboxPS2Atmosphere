# GTA San Andreas (Xbox) — PS2 Atmosphere v1.3

New in v1.3: support for the **Europe** release, both revisions, **region-free**. The USA patch is unchanged from v1.1; USA users who already have v1.1 or v1.2 don't need to do anything.

A patch for the original-Xbox *GTA: San Andreas* that brings back the look of the PS2 version. The Xbox advantages stay: DXT textures, longer draw distance, 480p and the Xbox car shader.

What changes:

- The PS2 colour filter: the warm orange or green grade from `timecyc.dat`, which the Xbox washes out.
- The soft PS2 blur on that filter.
- The PS2 radiosity glow on bright areas.
- PS2-style building lighting: stronger ambient light, softer baked light.
- PS2 alpha test on foliage, so palms, trees and power lines look full and continuous.
- A neutral display gamma at the default brightness.
- Europe version only: region-free. The stock Europe disc quits on a console that isn't set to the Europe region; the patched one runs on any console.

**One file changes: `default.xbe`.** Everything else, `stream.ini` included, stays as it is. No game files are included.

## Requirements

- Your own copy of **GTA San Andreas, USA or Europe**, either revision:

  | Version | Title ID | Original `default.xbe` SHA1 |
  |---|---|---|
  | USA Rev 1 (Platinum Hits / *The Trilogy*) | `545400A3` | `10EFB868F13D6944AA6684A52CAC5156393F14C5` |
  | USA Rev 0 (original release) | `54540082` | `1CEAE5BE753B3675CE8C5C79D7F496DFC0AD597D` |
  | Europe Rev 1 | `545400A4` | `F0ED7D693C5B9B579FFEF38CF40AE0EFAE6A71D3` |
  | Europe Rev 0 (original release) | `54540086` | `7A424B08E79A4FEBA39EC8ACF2168C6C94BC0B5A` |

  Other regions or an already-modded file won't patch.

  The original Europe disc only runs on a console set to the Europe region. The patched Europe version drops that check, so it runs on any console (tested on an NTSC console and in xemu with a North American EEPROM).
- A softmodded or modchipped Xbox, or the [xemu](https://xemu.app) emulator. The patched XBE is no longer retail-signed, so an unmodified console won't run it.

## Install with any xdelta GUI (easiest)

The patches are in four folders, one per version, with the same three files in each: `GTA SA (USA) Rev 1`, `GTA SA (USA) Rev 0`, `GTA SA (Europe) Rev 1` and `GTA SA (Europe) Rev 0`. Pick the folder for your version, then the patch for the file you have:

| Your file | Patch |
|---|---|
| `default.xbe` from a game folder (for example on the Xbox hard drive) | `default.xbe.xdelta` |
| Full game ISO, 7,825,162,240 bytes (Redump names: `Grand Theft Auto - San Andreas (USA) (En,Es) (Rev 1).iso`, `… (USA) (En,Es).iso`, `… (Europe) (En,Fr,De,Es,It) (Rev 1).iso`, `… (Europe) (En,Fr,De,Es,It).iso`) | `iso.xdelta` |
| XISO of the game partition (the full ISO minus its video partition), 7,419,363,328 bytes | `xiso.xdelta` |

The ISO patches are made for the Redump dumps of the game. The USA Rev 0 and both Europe ones were checked against their Redump images; the USA Rev 1 one against an image with the same layout.

A patch for another version is rejected with *"checksum mismatch"*, so trying the wrong folder does no harm.

1. Open your xdelta patcher (Delta Patcher, xdelta UI, or any other). For `default.xbe` a web patcher such as [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) also works; the ISOs are too big for a browser.
2. **Original file:** your file. **Patch file:** the matching `.xdelta`.
3. Apply. Keep the original somewhere safe.

If you patched `default.xbe`, put the patched file back in the game folder. The patched XBE has SHA1 `84E14EEF41E0E83D7191A66973C99959815D7553` (USA Rev 1), `6883102C897EAA58E8E01FB41A51B9C4B44B481D` (USA Rev 0), `D4B4A593033690AFCF298073E2A2EAFAC07EB15D` (Europe Rev 1) or `ACD8EA4A872186ADF7E67E6F9E1AEC5340BBF346` (Europe Rev 0).

A patched full ISO keeps its format. Convert it the way you usually do (Repackinator, extract-xiso, ...); xemu doesn't boot the full ISO directly, but it boots the patched XISO as is.

The wrong file is rejected with *"checksum mismatch"*. An ISO that was rebuilt or trimmed (for example by extract-xiso or Repackinator) has a different layout, so the ISO patches won't fit it. For those, use the script below, or extract the ISO and patch `default.xbe`.

Command line equivalent:

```
xdelta3 -d -s default.xbe "GTA SA (USA) Rev 1/default.xbe.xdelta" default_patched.xbe    # or the folder of your version
```

## Install with the script (folders and ISO images)

Needs Python 3 and [`xdelta3.exe`](https://github.com/jmacd/xdelta-gpl/releases) in this folder (or pass `--xdelta <path>`).

```
py apply_patch.py "D:\Games\GTA San Andreas"
py apply_patch.py "D:\xemu\GTA San Andreas.iso"
```

- **A folder:** `default.xbe` is patched and the original is kept as `default.xbe.bak`.
- **An `.iso` / `.xiso`:** a full copy is saved as `<name>.iso.bak` first, so you need as much free space as the image takes. Then `default.xbe` is patched inside the image.

The script tells the four versions apart by the SHA1 of `default.xbe` and uses the matching patch. It checks the file before it writes anything and checks the result afterwards. An existing `.bak` is never overwritten. Running it again only reports `already patched`.

## Coming from v1.0, v1.1 or v1.2

v1.1 / v1.2 → v1.3: nothing to do on USA, the patched file is the same.

From v1.0: patch the **original** `default.xbe` again: restore it from `default.xbe.bak`, or from your original image. The `stream.ini` lines that v1.0 added can stay; they do no harm.

## Options

- **Turn the radiosity glow off:** add the line `pe_bRadiosity 0` to `stream.ini`.
- The blur is fixed at the PS2 value. The `pe_*` lines in `stream.ini` are ignored.

## Recommended setting

Keep **Brightness** at its default. Saves store their own brightness, so reset it with the Display menu's restore-defaults option. The patch's neutral gamma is calibrated for the default; higher values only brighten the image.

## Uninstall

Put the original `default.xbe` back: rename `default.xbe.bak` → `default.xbe`, or `<name>.iso.bak` → `<name>.iso`.

## Credits

The PS2 rendering behaviour follows aap's [SkyGfx](https://github.com/aap/skygfx) research and the [gta-reversed](https://github.com/gta-reversed/gta-reversed) project. The Xbox patches are original x86 code.
