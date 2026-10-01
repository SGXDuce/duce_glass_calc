# Configurator safety net (v6 exports)

This folder holds five real Configurator exports (schemaVersion 6), captured
on 1 October 2026 from master at commit fb8eb69. They are a safety net for
the Configurator variant work: steps 4b to 5c must not change the numbers
these files produce. Step 5d deliberately changes the OX file's numbers,
after which new schemaVersion 7 exports will be saved separately.

## How each was captured

Opened `/configurator` standalone in an Incognito browser window, built the
system, clicked Export JSON, then renamed the downloaded file.

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

## Comparison rule (PROPOSED BY CLAUDE, not decided by Sahil)

Later re-exports should be compared on the `"system"` block exactly.
`"rawState"` is allowed to differ, because it holds drawing and selection
state, and step 5a may add tuck-in data there.

## Data note

These files contain only window dimensions and no confidential data.
