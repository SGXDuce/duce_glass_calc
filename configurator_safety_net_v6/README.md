# Configurator safety net (v6 exports)

This folder holds five real Configurator exports (schemaVersion 6), captured
on 1 October 2026 from master at commit fb8eb69. They are a safety net for
the Configurator variant work: steps 4b to 5c must not change the numbers
these files produce. Step 5d deliberately changes the OX file's numbers,
after which new schemaVersion 7 exports will be saved separately.

## How each was captured

Opened `/configurator` standalone in a normal (not Incognito) browser window
after a hard reload (Ctrl+Shift+R), built the system, clicked Export JSON,
then renamed the downloaded file.
(Corrected 1 October 2026: an earlier version said Incognito; Sahil reports it was not.)

## What each file is

| File | What was built | Verified daylight (W x H) | Lowest sightline | Span |
|---|---|---|---|---|
| `safety_net_v6_01_caseA_slider_door.json` | Case A slider door (pane F) | 1640 x 1940 | 80 | 1640 |
| `safety_net_v6_02_ox_door_860_920.json` | OX door, panes .R and .S | .R 860 x 1980 / .S 840 x 1940 | .R 60 / .S 80 | .R 860 / .S 840 |
| `safety_net_v6_03_casement_C_1680x1980.json` | Casement C (pane F) | 1600 x 1900 | 100 | 1600 |
| `safety_net_v6_04_caseB_horizontal_silicone_990.json` | Case B, horizontal silicone joint at 990 (.T, .B) | both 1680 x 990 | .T 1050 / .B 60 | both 1680 |
| `safety_net_v6_05_caseC_vertical_silicone_840.json` | Case C, vertical silicone joint at 840 (.L, .R) | both 840 x 1980 | both 60 | both 1980 (framing "partly") |

## Facts seen in the files

- A casement exports as type `"hinged"` with `productClass` `"window"`.
- Fixed panes store sash 40 on their edges inside `rawState`, but export
  `sashEdgesMM` as all 0.
- The export holds no tuck-in or made-size field.

## Comparison rule (DECIDED BY SAHIL, 1 October 2026; first proposed by Claude)

Later re-exports should be compared on the `"system"` block exactly.
`"rawState"` is allowed to differ, because it holds drawing and selection
state, and step 5a may add tuck-in data there.
DECIDED BY SAHIL on 1 October 2026 (was PROPOSED BY CLAUDE); after step 5a, print exactly what differs in rawState.

## Data note

These files contain only window dimensions and no confidential data.

## Re-checking after a Configurator change

- Run from the repo root: `python tools/compare.py <saved file> <new file>`
- `<saved file>` is one of the committed exports in this folder. `<new file>` is a fresh export of the same system, rebuilt by hand in the Configurator.
- The script compares parsed JSON, not file hashes. Git changes line endings on checkout, so hashes of the repo copies differ from the originals.
- Rule decided by Sahil: the `"system"` block and `"schemaVersion"` must be identical. `"rawState"` may differ (screen-pixel values under `lastGeom`, and `"selected"`). After step 5a, every `rawState` difference must be listed and explained.
- Known result on 1 October 2026 for the five committed files against fresh rebuilds: 01 = 10 differences, 02 = 10, 03 = 11 (ten `lastGeom` plus `"selected"`), 04 = 10, 05 = 10.
## Extra exports added 6 October 2026

| File | What it is | Key numbers (read from the file) |
|---|---|---|
| safety_net_v6_06_framed_double_hung_1680x1980.json | Framed double-hung window, 1800 x 2100 overall | Both sashes 1720 x 1040, sash edges all 40; .S at x 40, y 1000; .R at x 40, y 60 |
| safety_net_v6_07_framed_OX_window_860_920.json | Framed OX window (fixed pane plus sliding sash) | .R fixed 860 x 1980 at x 40, y 60, sash edges 0; .S horizontal slider 920 x 2020 at x 840, y 40, sash edges 40 |
| safety_net_v6_08_sashless_OX_840_900.json | Sashless OX (fixed pane beside a sashless slider) | .R fixed 840 x 1980 at x 60, y 60, right edge "next-to-sashless"; .S 900 x 1980 at x 840, y 60, sash top 15 bottom 15 left 0 right 0, visible glazed area 1.755 m2 |
| safety_net_v6_09_sashless_double_hung_1020.json | Sashless double-hung | Both sashes 1680 x 1020 at x 60; sash top 0 bottom 0 left 15 right 15; .S at y 1020, .R at y 60 |
| safety_net_v6_10_slider_beside_mullion_980.json | Fixed pane, mullion, then a sliding sash | .L fixed 900 x 1980 at x 60, y 60, sash edges 0; .R slider 780 x 2020 at x 980, y 40, sash edges 40; mullion position 920, thickness 40 |
| safety_net_v6_11_no_frame_slider_1680x1980.json | Single slider, no outer frame | Pane F 1680 x 1980 at x 0, y 0, sash edges 40; visible glazed area 3.04 m2; overall 1680 x 1980 |
| safety_net_v6_12_no_frame_double_hung_1680x1980.json | Double-hung, no outer frame | Both sashes 1680 x 1020 at x 0, sash edges 40; .S at y 960, .R at y 0; overlap 60; visible glazed area 1.504 m2 each; overall 1680 x 1980 |

Real Configurator exports, schemaVersion 6, supplied by Sahil on 6 October 2026 (REPORTED BY SAHIL). No hand values were written before these exports were made. The key numbers above were read from the files and checked by Claude's arithmetic against the tool, not hand-calculated by Sahil. Files 11 and 12 have no outer frame. The older fixture tests/fixtures/sashless_double_hung.json appears to use a 1680-high opening, while file 09 uses a 1980-high opening (INFERRED BY CLAUDE from the fixture's heights in the summary; not checked in the fixture itself).
