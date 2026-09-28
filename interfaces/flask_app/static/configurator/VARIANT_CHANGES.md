# Vendored Configurator — Variant Changes

This directory holds a vendored copy of the configurator, a separate project
with its own repository and chat history. `configurator.html` is served
as-is by the AS 1288 tool and must never be hand-edited directly — any
change needed on our side goes through the configurator project first, then
gets re-vendored here.

Every future change to our copy (re-vendoring a newer commit, or any
local patch applied here as a stopgap) must be logged below, oldest first.

## Change log

- **Baseline:** SGXDuce/Configurator commit `6cc789e` (batch 55/56, export
  schemaVersion 5), unmodified.
- **Re-vendored:** SGXDuce/Configurator commit `dad98aa` (batch 57–61,
  through the sliding-sash tuck-in export fix for non-preset-built leaves),
  unmodified. Picks up sliding-window/door head/sill tuck-in correction
  (batch 57), the O-panel head/sill tuck-in exclusion fix (batch 58),
  double-hung jamb tuck-in correction (batch 59), and the lone
  non-preset sliding leaf tuck-in fix (batch 61).
