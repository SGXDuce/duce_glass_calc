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
     values (e.g. 15 / 15 / 0 / 0), not a dash.
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
