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
  back.
  REPORTED BY CLAUDE CODE: effect on the export: none expected, the catalog
  never reached the export.

## Planned changes (not yet made)

1. Delete `DOOR_PANEL_CATALOG`, its helper functions, the picker, the render
   branch, and the toolbar entry. The commit that makes this change must
   paste the full list of catalog keys read from the code. Status: PROPOSED,
   not built. Tag: AS1288-only, do not carry back.
2. Delete `PRESET_SASH_EDGES` (the NGR-sourced casement and awning sash
   shape) so casement and awning presets start at `DEFAULT_SASH_MM` (40) on
   every stile and rail. Status: PROPOSED, not built. Tag: AS1288-only, do
   not carry back.
3. Make the frame tuck-in editable per frame side (head, sill, left jamb,
   right jamb). The starting value rule is to be settled before this is
   built — see "Open before change 3" below. Status: PROPOSED, not built.
   Tag: carry back.
4. Add an editable side table of user inputs, values only, inside the
   Configurator. Status: PROPOSED, not built. Tag: carry back.
5. Strip Duce/NGR wording from comments in configurator.html. Status:
   PROPOSED, not built. Tag: AS1288-only, do not carry back.

## Decisions

- DECIDED BY SAHIL: frame widths start at 60mm on all four sides, and are
  editable by the user.
- DECIDED BY SAHIL: every sash stile and rail starts at 40mm
  (`DEFAULT_SASH_MM`), and each is editable by the user individually.
- DECIDED BY SAHIL: the 60mm sliding overlap is kept as is; making it
  editable is an open item.

## Open before change 3

Open, not decided:

- (a) Whether the starting tuck-in is a fixed 20mm capped at the sash width,
  or the smaller of 20mm and half the sash width.
- (b) How the separate sliding-height, double-hung jamb, meeting-rail, and
  sashless tuck-in constants fit a per-frame-side design.
- (c) The unconfirmed `hasFrame` gating of the tuck-in.
- (d) Whether a typed tuck-in is locked against later sash width changes.
