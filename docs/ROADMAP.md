# Roadmap (after v1.1)

Ideas and open items collected after release, mostly from user feedback. Nothing here is committed to. Each item gets its own entry in `findings.md` once work starts. `PLAN.md` still covers the shipped atmosphere work.

## Next: other USA versions

- ~~**USA Rev 0.**~~ Done 2026-10-16: `default.xbe` sha1 1ceae5be… is the Redump Rev 0 image; v1.1 is ported, released as `default_rev0.xbe.xdelta` / `rev0-xiso.xdelta` / `rev0-redump-iso.xdelta` (findings "USA Rev 0 port").
- ~~**Europe Rev 1 and Rev 0.**~~ Done 2026-10-20: ported with the same map (`--eu1` / `--eu0`), release v1.3 (findings "Europe Rev 1 / Rev 0 port"). Region-free (P8). Tested in xemu and on real hardware, user sign-off ✅.
- **Any other USA revisions.** Check the Redump list. A new close build can reuse `tools/rev0_map.py` (it maps Rev 1 VAs to another build by code alignment).

## Investigate

- **Every Xbox difference vs PS2 and PC.** Build a full list of what the Xbox port does differently from the other versions: rendering, HUD, assets, gameplay bugs and the like. Rank each one by how visible it is and how hard it would be to patch. This list feeds the fixes below.

## Candidate fixes

- **Map/radar blips.** On the Xbox, compression damages the blip icons. Find out whether the cause is the texture data or the way the game draws them.
- **Parachute placement.** The parachute sits in the wrong place on CJ's back on the Xbox.

## Testing gaps

- **Xbox 360 (Aurora / backward compatibility).** Not tested. It's unknown whether a modified XBE boots there, and whether the blur and radiosity look right.
- **Real Redump Rev 1 image.** `redump-iso.xdelta` has only been tested on a synthetic image.
- **GUI xdelta tools.** Delta Patcher and xdelta UI haven't been tested on the release patch.
