# Vendored Configurator — Variant Changes

This directory holds the AS 1288 variant of the Configurator. From this
point it is a deliberate fork, not a plain vendored copy: `configurator.html`
is edited directly here.

Each edit is one small commit and one ledger entry below. Every entry is
tagged either "AS1288-only, do not carry back" or "carry back". The main
Configurator project keeps its own Duce-only content as-is; "carry back"
entries are applied there at the end of this project.

## Change log

- **Baseline:** SGXDuce/Configurator commit `6cc789e` (batch 55/56, export
  schemaVersion 5), unmodified.
- **Re-vendored:** SGXDuce/Configurator commit `dad98aa` (batch 57–61,
  through the sliding-sash tuck-in export fix for non-preset-built leaves),
  unmodified. Picks up sliding-window/door head/sill tuck-in correction
  (batch 57), the O-panel head/sill tuck-in exclusion fix (batch 58),
  double-hung jamb tuck-in correction (batch 59), and the lone
  non-preset sliding leaf tuck-in fix (batch 61).
- **Fork begins.** Baseline UNPINNED: the vendored file contains Batch 63
  comments, which are newer than `dad98aa`. The exact upstream commit is not
  yet identified (to be filled in by Sahil). Tag: not applicable.
- **Deleted** `ASSEMBLY_PRESET_CATALOG_SIZES`, `findClosestCatalogSize` and
  the "Closest standard size" info line. Tag: AS1288-only, do not carry
  back. Commit `d7aecdb`.
  REPORTED BY CLAUDE CODE: effect on the export: none expected, the catalog
  never reached the export.
- **Deleted** the door panel style feature: `DOOR_PANEL_CATALOG`, its seven
  helper functions, `computeDoorPanelLayout`, the icon/picker functions, the
  render-loop drawing branch, the toolbar entry point, and
  `canHaveDoorPanelStyle`. Tag: AS1288-only, do not carry back. Commits
  `b347831` (entry points and drawing) and `10b53e3` (catalogue and
  helpers).
  REPORTED BY CLAUDE CODE: the catalogue had 33 keys, including D5L and
  D64H; D21 does not exist. The earlier "31" figure in the read-only survey
  was wrong: its grep only matched digit-only names. Full key list: D1, D6,
  D22, D2, D3, D4, D5L, D5, D7, D8, D9, D10, D11, D12, D13, D14, D15, D16,
  D17, D18, D19, D20, D23, D24, D25, D32, D63V, D64H, '65H', '65V', '66V',
  '66H', '67H'.
  REPORTED BY CLAUDE CODE: effect on the export: none expected, these
  fields are not exported.
  INFERRED BY CLAUDE (not tested): a saved system that contains these
  fields will load and ignore them, because restoreFromRawState assigns
  state without checking fields.
- **Deleted** `PRESET_SASH_EDGES` (the NGR-sourced casement and awning sash
  shape) so casement and awning presets now use `DEFAULT_SASH_MM` (40) on
  every stile and rail. Tag: AS1288-only, do not carry back.
  REPORTED BY CLAUDE CODE: effect on the export: casement and awning leaves
  now export sashEdgesMM 40/40/40/40 instead of 60/60/60/86 for newly built
  presets.
- **Replaced** the single "Sash frame width (mm)" toolbar box with four
  per-edge boxes (Top, Bottom, Left, Right), and the Assigned panes table's
  "Sash frame (mm)" column (top value only) with "Sash T / B / L / R (mm)"
  (all four values). Tag: carry back (tag proposed by Claude, not confirmed
  by Sahil). Branch `step-4b-sash-boxes`.
  REPORTED BY CLAUDE CODE: this is a screen change only — no exported number
  changes. `getSashEdges`, `DEFAULT_SASH_MM`, the `isFixed` override in
  `buildExportElevation`, `buildExportDataOrBlockedError`,
  `serializeRawState`, the drawing code, the glazed-area code, the preset
  code, the unframed-joint locking code and `schemaVersion` were not
  touched.
  Rules implemented, exactly as decided by Sahil:
  1. A silicone-joint edge (its `sash*Locked` flag set) shows 0 and its box
     is disabled (greyed out); it cannot be edited.
  2. A sashless leaf (`node.sashless === true`) shows no sash boxes at all.
  3. A plain Fixed pane (`node.type === 'fixed'`, windows and doors) shows
     no sash boxes. "Fixed (sash)" (`node.type === 'fixed-framed'`) keeps
     its four boxes. Every other filled leaf type shows four boxes, as the
     old single box did.
  4. The Assigned panes table shows all four sash values per leaf. Plain
     Fixed keeps its dash; a sashless leaf shows its real four stored
     values, not a dash. For example, a sashless horizontal-slider leaf
     (`SASHLESS_HSLIDER_CAPPING_MM`, 15mm, on top/bottom, 0 on left/right)
     reads top / bottom / left / right = 15 / 15 / 0 / 0 (an earlier
     version of this entry gave 15 / 15 / 0 / 0 without naming the leaf
     type; that is correct for the sashless horizontal slider). A
     sashless double-hung leaf is the other way round
     (`SASHLESS_DH_CAPPING_MM`, 15mm, on left/right, 0 on top/bottom): it
     reads 0 / 0 / 15 / 15.
  5. Each box is validated on change: rejects a blank value, a non-finite
     value, a negative value, or a value that would make left+right >= the
     leaf's width or top+bottom >= the leaf's height (same `l.w`/`l.h` the
     glazed-area code uses, read here via `ev.lastLeafRects` keyed by the
     selected leaf's path). On rejection the box is restored to its
     previous value and a plain-language message is shown in a
     `.field-error` div under the boxes (the same CSS class already used
     for the angled-join angle input's error). Zero is allowed; no
     decimal-places rule was added.
  6. Typing in one box changes only that edge (`withSashEdgeMM`, respecting
     the lock flag) — the old "set all four at once" behaviour
     (`withUniformSashMM`) is gone.
  `withUniformSashMM` was deleted after confirming by grep that its only
  caller was the old toolbar box's own `change` handler (the only other
  hits were historical batch-log comments, left alone).
  REPORTED BY CLAUDE CODE: Tab/Enter between the four boxes is preserved by
  giving each box a stable id (`sashEdgeInput-<edge>`) and, after the
  `render()` that a valid `change` triggers rebuilds the whole toolbar,
  looking that same id back up and calling `.focus()`/`.select()` on it.
  This was not tested in a browser (JavaScript is not covered by the
  Python test suite); only visual/manual inspection and Python's `pytest`
  were run.
- **Follow-up:** fixed Tab focus order in the four sash boxes — Sahil found
  in the browser that the earlier fix above (refocusing the same edge after
  every `render()`) also caught Tab, so pressing Tab from Top landed back
  in Top instead of Bottom. Each box's own `keydown` now records which edge
  Tab/Shift+Tab is trying to reach (skipping locked edges) before `change`
  fires and `render()` rebuilds the row, then refocuses that edge once the
  rebuild is done; Enter still just keeps the cursor on the same edge. A
  click away from the row never runs that `keydown` handler, so it can
  never pull focus back into a sash box. Tag: carry back (tag proposed by
  Claude, not confirmed by Sahil). Not tested in a browser by Claude Code.
- **Second follow-up:** fixed Tab/Shift+Tab on an unedited sash box — the
  `keydown` handler always intercepted Tab and blurred the box, but an
  unedited box never fires `change`, so nothing restored focus and the
  cursor was lost; the same gap let Enter leave a stale "restore focus
  here" intent behind. Tab/Shift+Tab is now only intercepted when the
  box's text differs from the value it was built with, so an unedited box
  uses the browser's own native Tab with no rebuild; Enter only records
  its intent when a `change` will actually follow to consume it; and a
  rejected entry refocuses the intended box directly (or the box itself
  if there is no such target) instead of relying on a `render()` that no
  longer happens. Tag: carry back (tag proposed by Claude, not confirmed
  by Sahil). Not tested in a browser by Claude Code.
- **Step 5a:** added `isRealMullionNode` and `classifyLeafEdges`;
  `computeLoneSlidingLeafCorrections` now asks `classifyLeafEdges` whether
  each leaf edge sits against the frame, a real mullion or nothing, instead
  of doing those tests inline (the old local `isRealMullion` is gone). No
  behaviour change intended; `schemaVersion` stays 6. The other three
  correction functions and `getDoubleHungOverlapMM` are untouched. Top and
  bottom edges are still tested for the frame only, never for a mullion or
  transom; this is kept on purpose in step 5a. Tag: carry back (tag proposed
  by Claude, not confirmed by Sahil). Node is not installed on
  Claude Code's machine, so no syntax check or equivalence run was done
  (REPORTED BY CLAUDE CODE). REPORTED BY SAHIL: no red errors in the
  Console; five rebuilt exports (files 01, 02, 10, 11, 13) compared with
  compare_full.py show an identical system block in all five.

- **Step 5b:** added two display-only columns to the Configurator's pane
  table, "Made size (mm)" and "Daylight size (mm)" (width x height). New
  functions: `getActiveExportPaneMap`, `formatSizeMM`, `madeSizeCellText`,
  `daylightSizeCellText`; `renderTable` and the table heading/footer changed. Both
  columns read the active elevation's `buildExportElevation` result (a pure
  read): made size is the pane's `widthMM` x `heightMM`, daylight is those
  less the same `sashEdgesMM` values the export carries. The export, every
  correction function, every tuck-in constant and `schemaVersion` (stays 6)
  are untouched.
  - Daylight for fixed panes is KNOWN WRONG until step 5d: the export gives
    fixed panes sash edges of 0, so their daylight equals their made size.
    DECIDED BY SAHIL: left as is for now.
  - Sashless panes keep their stored capping edges, and their daylight
    deducts them like every other pane: 15 mm per capped edge. This matches
    the existing "Visible glazed area" column (checked by Claude's arithmetic
    against that column for files 08 and 09; not hand-verified by Sahil). No asterisk and no note
    under the table.
  - The table's older "Area" and "Visible glazed area" columns use the drawn
    leaf size and are display only: nothing outside `renderTable` reads them
    (REPORTED BY CLAUDE CODE).
  - The export computes its own `areaM2` from the made size and its
    `visibleGlazedAreaM2` from the made size less the sash edges, the same
    basis as the Daylight column (`buildExportElevation`, about lines
    6213-6214; REPORTED BY CLAUDE CODE). Example: file 13 .L table glazed
    1.56 m2 vs export and Daylight 860 x 1940 = 1.67 m2.
  - OPEN ITEM: not traced whether the compliance calc or System check reads
    the export's `areaM2` (made size, not daylight) or its
    `visibleGlazedAreaM2`. This matters for the 30 September 2026 decision
    that daylight is the basis for span, aspect ratio and area (DECIDED BY
    SAHIL).
  - Failure fallback is a PLACEHOLDER (Sahil will revisit): if the export
    cannot be built for the current system (cross-elevation mismatch or a
    throw), both new columns show "—", every other column still works and no
    new error message is added.
  - Tag: carry back (tag proposed by Claude, not confirmed by Sahil). Node is
    not installed on Claude Code's machine, so no syntax check was done. The
    page was run in a browser test with tools/ui_regression.py (headless
    Chromium, REPORTED BY CLAUDE CODE).

- **Step 5c-1:** per-edge tuck-in boxes for LONE and MANUALLY SPLIT sliders
  only (horizontal and vertical sliders outside any assembly-preset marker,
  not sashless). Tuck-in is how far the sash slides behind the frame or
  mullion, so the made size is larger than the drawn size by that amount.
  - New optional leaf fields: `tuckTopMM`, `tuckBottomMM`, `tuckLeftMM`,
    `tuckRightMM`. null or missing = automatic; a number (0 or more) = typed.
  - Automatic rule is exactly today's: half of the full allowance per edge,
    only where the edge sits against the outer frame (left/right also against
    a real mullion; top/bottom never against a transom), zero when there is
    no outer frame, sashless uses its own figures. A typed value replaces the
    automatic one; it is still forced to 0 when there is no outer frame, the
    pane is sashless, or the edge is a silicone joint. New helpers:
    `autoTuckInMM`, `effectiveTuckInMM`, `typedTuckInMM`, `validateTuckInMM`,
    `appendTuckInRow`; `computeLoneSlidingLeafCorrections` now calls
    `effectiveTuckInMM`.
  - UI: a "Tuck-in (mm)" row under the sash boxes, each box tagged "(auto)"
    or "(typed)", disabled and shown as 0 for a silicone-joint edge, a 0 sash
    edge, or no outer frame, plus one "Reset tuck-ins to automatic" button
    per leaf. No boxes for casement, awning, hinged door, louvre, fixed,
    sashless or preset panes (later steps).
  - Blocking, with the value snapping back and a one-line reason shown: a
    typed tuck-in cannot exceed that edge's sash width; at a mullion edge it
    is also capped at half the mullion thickness (read from the adjacent
    split, no new plumbing). A sash edge cannot be narrowed below the tuck-in
    on that edge, typed or automatic ("lower the tuck-in first"); see the
    follow-up entry below, which replaced the first version of this rule.
  - The type-change handler copies the four fields. They only take effect on
    sliders, so they are harmless on another type and come back if the pane
    is switched back to a slider. `cloneForSplit` does NOT copy them: a split
    pane's new halves start automatic.
  - A sash edge set to 0 on a frame edge: the box shows 0 (disabled); the
    export now agrees (see the follow-up entry below).
  - No export or schema change: no new export field, `schemaVersion` stays 6,
    `RAW_STATE_SCHEMA_VERSION` not bumped. A reset leaves four null fields in
    the saved rawState (system block unchanged).
  - Existing-data check: in the 13 safety-net files every lone slider has
    40 mm sashes, so no automatic tuck-in (20 mm) exceeds a sash.
  - Tag: carry back (tag proposed by Claude, not confirmed by Sahil). Node is
    not installed on Claude Code's machine, so no syntax check was done. Run
    with tools/ui_regression.py (headless Chromium, REPORTED BY CLAUDE CODE):
    the five existing files unchanged and a new typed/refused/reset scenario
    on file 13 .L pass. Save/reload of a typed value is not covered by that
    harness.

### Step 5c-1 follow-up: the tuck-in can never exceed its sash edge

- The rule: on a slider edge the tuck-in can never be more than that edge's
  sash width, automatic or typed. The tuck-in is the part of the sash that
  slides behind the frame or mullion, so it has to fit inside the sash.
- Fix 1: `effectiveTuckInMM` now returns min(tuck-in, sash width on that
  edge). The old logic moved to `uncappedTuckInMM`. Silicone-joint, no-frame
  and sashless rules are unchanged. The table, the export and the Tuck-in box
  now agree, including a sash set to 0 (tuck-in 0).
- Fix 2: `validateSashEdgeMM` refuses a sash value below the current tuck-in
  on that edge, automatic or typed, for sliders only ("lower the tuck-in
  first"). New helper `selectedEdgeTuckInMM` supplies the uncapped number; it
  returns 0 for a non-slider, a sashless pane, a pane under an assembly-preset
  marker, or an edge with no tuck-in, so none of those are checked.
- Numbers that can change: only a lone slider whose sash is narrower than its
  automatic tuck-in (for example an old saved design with a 10 mm sash). The
  made size there now uses the smaller tuck-in. None of the 13 safety-net
  files is affected (every non-sashless slider has 40 mm sashes; the sashless
  ones have a 0 tuck-in).
- No export field or schema change; `schemaVersion` stays 6.
- Tag: carry back (tag proposed by Claude, not confirmed by Sahil). Node is
  not installed, so no syntax check; verified with tools/ui_regression.py.

### Rename: "Made size (mm)" column heading is now "Sash/Leaf size (mm)"

- Display only. The Assigned panes table heading changed from "Made size (mm)"
  to "Sash/Leaf size (mm)" (label decided by Sahil). The cells, the numbers
  and the column position are unchanged.
- Unchanged: the function names (`madeSizeCellText` and the others), the
  export fields `widthMM` / `heightMM`, every calculation, and
  `schemaVersion` (stays 6).
- The word "made" in earlier entries of this log is kept as history.
- Tag: carry back (tag proposed by Claude, not confirmed by Sahil). Node is
  not installed, so no syntax check; verified with tools/ui_regression.py.

### Step 5c-2: no-frame sliders tuck into a mullion

- The rule: a sash slides behind a mullion whether or not the elevation has
  an outer frame. So a slider with no outer frame now gets an automatic
  tuck-in of 20 mm (half of `FRAME_TUCKIN_MM`) at a real mullion edge, left
  and right only. A typed value follows the same gate: allowed (and the box
  enabled) at a mullion edge with no frame, still forced to 0 at an opening
  edge with no frame.
- What stays 0: an opening edge with no frame (nothing to slide behind), top
  and bottom with no frame (a transom is still never tested), sashless
  sliders (their own constant is 0), and a silicone-joint edge. Framed
  systems do not change at all.
- Code: new `noFrameBlocksTuckIn`; `autoTuckInMM` and `uncappedTuckInMM` use
  it instead of testing `hasFrame` on its own, and so does the disabled test
  in `appendTuckInRow` (its title now says "an opening edge with no outer
  frame"). The existing blocking rules still apply: cap by the sash width,
  mullion edge capped at half the mullion thickness, sash cannot be narrowed
  below the tuck-in.
- New safety-net files (exports made by tools/ui_regression.py, layout:
  1800 x 2100, no outer frame, mullion at 980 thickness 40, both panes
  horizontal sliders): `safety_net_v6_14_no_frame_two_sliders_mullion_BEFORE_5c2.json`
  (today's rule: .L 960 x 2100, .R 800 x 2100) and
  `safety_net_v6_14_no_frame_two_sliders_mullion_AFTER_5c2.json` (.L 980 x
  2100, .R 820 x 2100). The expected numbers are Claude's arithmetic, not
  hand values.
- Numbers that change: only a no-frame lone slider beside a real mullion.
  None of the 13 earlier safety-net files has one. Between the BEFORE and
  AFTER files the system differences are the two sliders' `widthMM`,
  `areaM2` and `visibleGlazedAreaM2`, the right slider's `xMM` (1000 to
  980, it now starts 20 mm further left), and `frameLengthMM` /
  `totalFrameLengthMM` (14020 to 14100, the two sliders are 40 mm wider in
  total, counted on top and bottom).
- No export field or schema change; `schemaVersion` stays 6.
- Tag: carry back (tag proposed by Claude, not confirmed by Sahil). Node is
  not installed, so no syntax check; verified with tools/ui_regression.py.

## Planned changes (not yet made)

1. ~~Replace the single "Sash frame width" box with four per-edge boxes
   (top, bottom, left, right).~~ Done above (step 4b).
2. Make the frame tuck-in editable per frame side (head, sill, left jamb,
   right jamb). The starting value rule is to be settled before this is
   built — see "Open before change 2" below. Status: PROPOSED, not built.
   Tag: carry back.
3. Add an editable side table of user inputs, values only, inside the
   Configurator. Status: PROPOSED, not built. Tag: carry back.
4. Strip Duce/NGR wording from comments in configurator.html. Status:
   PROPOSED, not built. Tag: AS1288-only, do not carry back.

## Decisions

- DECIDED BY SAHIL: frame widths start at 60mm on all four sides, and are
  editable by the user.
- DECIDED BY SAHIL: every sash stile and rail starts at 40mm
  (`DEFAULT_SASH_MM`), and each is editable by the user individually.
- DECIDED BY SAHIL: the 60mm sliding overlap is kept as is; making it
  editable is an open item.

## Open before change 2

Open, not decided:

- (a) Whether the starting tuck-in is a fixed 20mm capped at the sash width,
  or the smaller of 20mm and half the sash width.
- (b) How the separate sliding-height, double-hung jamb, meeting-rail, and
  sashless tuck-in constants fit a per-frame-side design.
- (c) The unconfirmed `hasFrame` gating of the tuck-in.
- (d) Whether a typed tuck-in is locked against later sash width changes.
- (e) Because each leaf in a preset assembly can have a different width on
  each stile and rail, the tuck-in must belong to each leaf edge that
  touches the frame, not to each frame side. The flat 40mm per row (20 at
  each end) would need to become a separate left and right value. Raised by
  Sahil, 30 September 2026; the design impact is INFERRED BY CLAUDE, not
  yet checked in code.
- (f) REPORTED BY CLAUDE CODE (survey, master b9253f1): none of the nine
  tuck-in uses reads a leaf's sash width; today's tuck-in is a fixed amount
  per edge. The preset form solves and checks widths before any leaf
  exists.
- (g) INFERRED BY CLAUDE (6 October 2026 survey, not run): the mullion
  tuck-in is a fixed 20mm per leaf whatever the bar width; in safety-net
  file 13 the two sashes meet at the bar centre line with a 40mm bar.
  Relevant to the blocking rule in 5c.
- (h) INFERRED BY CLAUDE (6 October 2026 survey): getDoubleHungOverlapMM
  also uses FRAME_TUCKIN_MM, so the double-hung head/sill tuck-in sits in
  the overlap and not in the correction functions. The line numbers are
  in summary v1.48 item G.

## Preset slide-direction lock

- What changed: inside a sliding-window or sliding-door assembly preset (the
  OX family: OX, OXX, OXXO, XOX, OXXX, OXXXX, OXXXXX, window and door ids),
  the "Slide direction" dropdown on a horizontal slider is shown disabled,
  still displaying the current value, with the tooltip "Slide direction is
  set by the preset pattern. Choose a different preset to change it."
- The rule behind it (DECIDED BY SAHIL): where two X sashes meet, sliding
  the same way = overlap, sliding apart = butt, sliding towards each other
  = overlap (see the decision below).
- The decision to lock (DECIDED BY SAHIL): the preset code sets each join
  type from the pattern when the preset is built and never reads the
  dropdown, so changing a direction afterwards would leave the export
  silently wrong. Inside a sliding preset the directions stay as built; to
  get a different arrangement the user picks a different preset.
- Not locked: lone sliders, manually built sliders, and double-hung
  vertical sliders. Finding for double-hung (REPORTED BY CLAUDE CODE, tested
  in the harness on the file 09 layout, not committed): flipping a
  double-hung direction changes only that pane's slideDirection field (one
  system difference, plus the matching rawState fields and the arrow in the
  drawing). No size, overlap or other number changes.
- DECIDED BY SAHIL (8 October 2026): sashes sliding towards each other
  overlap. The full rule is now: same direction = overlap, sliding apart =
  butt, sliding towards each other = overlap. The preset lock means no
  preset can reach the towards-each-other case today; it only matters if
  the dropdown is ever made to rebuild the joins.
- No numbers change. No stored data is rewritten, old saved designs are
  untouched, schemaVersion stays 6.
- Tag: carry back (tag proposed by Claude, not confirmed by Sahil).

## Drawing order: sliders paint above fixed panes

- The problem (REPORTED BY SAHIL from screenshots): in the OXXO and XOX
  sliding-window presets, an X sash with an O immediately to its right did
  not show its right-hand stile until the pane was clicked. OX was fine.
- The cause (checked in the drawing code and in the browser by Claude
  Code): panes are painted left to right and an unselected pane had no
  stacking level, so a later O was painted over the earlier X's overlapped
  edge (8.9 px on screen: a 3 px inset plus the 5.9 px stile). A selected
  pane has a higher level, which is why the stile appeared on click.
- The fix: one CSS rule. Every non-fixed pane (class "filled" without
  "no-frame-band") that is not selected gets z-index 1, so sliders paint
  above fixed panes. Their order among themselves is unchanged. A selected
  pane keeps z-index 2. Bars are added after all panes, so they still sit
  on top at the same level and a mullion stays clickable.
- NOT changed: the double-hung meeting rail (the bottom sash still paints
  over the top sash's bottom rail; the test records this), the X-over-X
  order in OXX and similar, any number, any export field, any stored data.
- Display only. schemaVersion stays 6.
- Tag: carry back (tag proposed by Claude, not confirmed by Sahil).
