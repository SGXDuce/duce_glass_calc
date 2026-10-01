# Window Schedule feature — progress handover

**Project:** AS 1288 Tool (Duce Glass Calc)
**Date:** 28 September 2026
**Read first:** `AS1288_Full_Project_Summary.md` (authoritative on architecture and current state), then `Configurator_Project_Summary.md` and `configurator_export_schema.md` from the Configurator project.

This doc covers one thread only: the **window schedule input feature** and the **configurator → AS 1288 integration** behind it. It does not restate the wind load engine, the existing pathways, or anything else already in the main summary.

---

## 0. Resolved — human impact engine recovery

The human impact engine (Phase 1 rules engine + Phase 2 questionnaire UI, per `human-impact-engine-notes.md`) was at one point missing from this repo entirely — not on `master`, not on any branch, not in history — because `master` stopped at V1.32 (4 September), before this work was reportedly built and tested. Recorded here rather than deleted so future readers know this almost got lost and why the recovery mattered.

The engine, routes, page, data tables and tests were recovered from uncommitted local work (11 September session), merged via PR #3 (commit `1225c20`) into `master`. Post-merge regression on the merged `master`: **91 passed, 0 failed**, across `test_human_impact.py`, `test_human_impact_routes.py`, the full 8-suite regression, and `test_schedule_routes.py`.

---

## 1. What the feature is

A schedule list in the AS 1288 tool. Each row is one window/door **system** as laid out on the plans — which may be a multi-panel combination (awning + fixed, hinged door with sidelights and a highlight above, etc.).

Per row, the user:
- enters **height of the lowest part of the system above FFL**, **room type**, and **building type** directly on the row
- builds the system's geometry in the **configurator**, launched from the row
- the returned pane data then drives the **human impact engine** and the **wind load engine** to produce glass thickness and allowed glass types

The configurator is a separate project with its own chat. This doc reflects the state of that integration as of today.

---

## 2. Architecture decided

- **Derivation lives on the AS 1288 side.** The configurator exports geometry facts only; all clause routing, span derivation, and pathway selection happens here. This follows the configurator project's own §6.1 boundary.
- **Embedding, not file exchange.** The AS 1288 Flask app serves the configurator HTML itself, and opens it in a same-origin modal iframe from each schedule row. File export/upload was rejected — a real schedule has 20+ rows and every plan revision would mean manual download/upload cycles.
- **postMessage protocol (built, configurator side):**
  - Origin check: accept only if `event.origin === window.location.origin` **and** `event.source === window.parent`. Send with `window.location.origin`, never `"*"`. This works for both the EXE (localhost) and the hosted domain without configuration — no hardcoded URL.
  - Handshake order: configurator sends `ready` (with `schemaVersion`) first, parent replies with `load` (saved raw state, or `null` for a new system), configurator sends `done` (the export) when finished.
  - **Cancel belongs to the parent.** The modal close button is ours. The configurator sends no cancel message and has no close button when embedded.
  - No row ID in the protocol — the parent tracks which row opened the modal.
  - AS 1288 side to send a `frame-ancestors 'self'` header on the configurator page as a second layer.
- **Round-trip editing is required** (plans get revised), so the export carries an opaque **raw state block** the AS 1288 side stores without reading and passes back unchanged on `load`. The derived flat pane list alone cannot rebuild the configurator's tree.
- **Manual-entry escape hatch (AS 1288 side, not yet built):** a schedule row option for anything the configurator can't represent (Pathway 4, raked heads), opening the existing standalone pathway forms instead. Prevents the schedule becoming a dead end.

---

## 3. Configurator export — current state (schema v4)

Built and verified on the configurator side:

- `system.angledJoinAngleDeg` (90–180) and `system.angledJoinType` (`butt`/`mitred`), `null` on single-elevation systems.
- `linkedPaneId` per pane — the cross-elevation link. Computed fresh from geometry on export, never stored.
- **Pane matching by edge position.** An earlier version matched by count and sorted order alone, which would falsely pair panes whose edges didn't line up (e.g. left elevation 1000 over 1400, right elevation 1400 over 1000 — same count, transoms at different heights). Now matched on actual start and end height along the meeting jamb, tolerance `PANE_EDGE_MATCH_TOL_MM = 1`. Mismatch **blocks the whole export** (configurator-side decision) with a visible error next to the Done button.
- `sashless: boolean` per pane — explicit field, direct read of the internal flag, never inferred from sash values.
- `unframedEdges: {top, bottom, left, right}` booleans — added because `unframedEdgeCount` alone can't say *which* edges are unframed, and Table 5.3 applies to unframed **vertical** edges specifically.
- `unframedEdgeCount` is unchanged and **we ignore it entirely** on the AS 1288 side. It can legitimately diverge from `unframedEdges`; that divergence is documented and is not a bug.

**Superseded by schema v5:** the plain `unframedEdges` booleans above have been replaced by `unframedEdgeReasons` (batch 46), which gives the *reason* an edge is unframed rather than just a flag. See §8 for the full routing table this now drives.

---

## 4. Resolved decisions (do not reopen)

| Item | Outcome |
|---|---|
| Structural vs weatherseal silicone joint | **Not a configurator field.** Derived here from angle: 90–160° structural (Pathway 3), over 160° weatherseal (Pathway 2). A flat same-elevation joint is 180°, so always weatherseal. |
| Depth / z-axis for angled joins | **Not needed.** Pathway 3's inputs are height, the two pane widths, angle, corner/general, and joint type. Corner/general is a building-location input and stays on the schedule row. |
| Sashless orientation | **Superseded by Configurator batch 63 / schema v6 — see §15.** Originally: sashless always means the glass **horizontal** edges have no sash rail, with thin stiles left/right; span = distance between stiles = pane width, constant, no export field needed. This was wrong for a double-hung (vertical-slider), where the free edges are left/right, not top/bottom. Orientation is now per-pane, read from `unframedEdgeReasons`'s `sashless-free-edge` value, not assumed from a constant. |
| Coplanar multi-part systems | A door with sidelights and a highlight above is **one elevation** built with ordinary tree splits. The 2-elevation angled-join mechanism is only for a genuine change in surface direction (corner/return). Most schedule items won't touch it. |
| Head/sill meeting edges | Parked. Data model supports it, no UI path. Revisit only if a real product needs an angled join at the head. |
| Pathway 4 (full-perimeter structural silicone to frame) | Out of schedule scope. No configurator representation, feature-flagged off here anyway. |
| Sashless supported-edge-pair field | Dropped — never built, doc-only removal. Orientation is constant (see above). |

---

## 5. OPEN — blocking, and they are product questions not code questions

5.2 needs checking against a real Duce sashless unit (or asking Scott/Michael). No code should change on it until answered.

### 5.1 Does the fixed `O` light in a sashless slider route to Clause 5.15? — **RESOLVED**

The configurator stamps `sashless: true` on **every** leaf of a sashless preset, including the fixed `O` panes. On our end `sashless: true` selects Clause 5.15, which forces Grade A safety glass, applies a span-derived minimum thickness, and excludes annealed and heat-strengthened outright.

Batch 45 zeroed the `O` pane's sash material (a bare fixed pane has no sash), but **left the `sashless` flag on it**. So the routing question was still unanswered — it was resolved on code-consistency grounds, not against a real product.

- If the `O` is genuinely bare glass running in head and sill channels → flag is correct, just record it as verified.
- If it's a normally framed fixed light → the flag belongs only on the sliding `X` leaves, and we are currently over-restricting every fixed panel in a sashless system.

**Resolution (configurator batch 46):** the sashless flag now lives only on the `X` leaf, never the `O`. A sashless `O` is a normal partly-framed window (3-edge, one edge — the one facing the `X` — unframed). This does **not** route to Clause 5.15; it routes as an ordinary partly-framed window. Consequence: a sashless `O` at low level in a residential building hits the still-open AGWA question about partly-framed windows under Clause 5.5 (see `human-impact-engine-notes.md`, Open AGWA questions).

### 5.2 "Unframed" vs "unsupported" — the definition isn't pinned

We asked for `unframedEdges` without defining it, and the configurator has implemented it as *no sash material present*. We need it to mean **structurally unsupported**, because we use it to pick a clause.

- Zero sash ≠ zero support. A fixed light glazed straight into the frame has no sash but is fully supported by head, sill and jamb.
- **Case 4** (batch 45) flags a sashless `O`'s edge at an **overlap join** as unframed. But an overlap join isn't a joint — the panes sit in different planes and never meet. No silicone, no butt joint, no load transfer. Routing that into Table 5.3 (which is for unframed vertical edges forming butt joints) would apply the wrong clause.
- Question put to the configurator side: what physically supports that edge of the `O`? If nothing, Case 4 stands. If it's retained in a channel or rebate, Case 4 should be removed.
- The same test applies to the sashless top/bottom exception, which assumes those edges are genuinely unsupported.

---

## 6. OPEN — AS 1288 side, not yet started

1. **Schedule row fields.** Room type vocabulary is undefined. It must map onto the human impact location categories already implemented (ordinary, bathroom/ensuite/spa, school/early-childhood, aged-care, none-of-these). Building type and FFL entry also need defining. **SUPERSEDED in part:** see "System check mode", which uses the two-level classification (building type, room type) plus a separate high-risk yes/no. The single-vocabulary wording above conflated the two levels.
2. **Per-pane height above FFL.** The row gives the system's lowest point above FFL; each pane's own Y offset comes from the configurator export. Per-pane height = system base + pane offset. **Each pane can trigger a different clause** — do not apply one verdict to the whole system based on the lowest pane.
3. **Exposed edges (Clause 5.3.1(b)) — DECIDED.** `unframedEdgeReasons` (configurator schema v5) gives four reasons an edge can be unframed: `angled-joint`, `silicone-flat`, `frame-off`, `next-to-sashless`. Decision: only `frame-off` asks the schedule-row/pane user whether the edge is exposed. The other three reasons are joined to another pane (sealed or overlapping), so they default to not exposed.
4. **Multi-panel uniform glass thickness — DECIDED, see "System check mode (design, 29 September 2026)" below.** No longer blocked on Michael (Michael is no longer involved in this project; Sahil is sole engineering authority — see that section). Required outputs are a single thickness/type that works for the whole system AND the minimum for each pane, checking every candidate thickness against every pane directly rather than assuming monotonic safety.
5. **Glass size vs sash size — DECIDED.** Use sight size, not true glass size, for the wind load span. Sight size is the physically correct span (the sight line is where the glass is actually restrained; the rebate overlap past it is embedment, not span). Derivation from the export: `sight_width_mm = widthMM - sashEdgesMM.left - sashEdgesMM.right`; `sight_height_mm = heightMM - sashEdgesMM.top - sashEdgesMM.bottom`. For a fixed (`O`) pane, `sashEdgesMM` is always zero, so sight size equals `widthMM`/`heightMM` directly.
6. **Schedule storage/persistence.** Tied to the account/database decision already open in `overview.md`, pending Adam's sign-off and the move external.
7. **Mismatch error surfacing.** No parent-side work needed — the configurator's block error appears next to its own Done button inside the visible modal.
8. **`__pycache__` tracked in git (separate small task).** `.pyc` files are currently tracked and show as modified after every test run. Add `__pycache__` to `.gitignore` and untrack the files already committed.

---

## 8. unframedEdgeReasons → AS1288 routing table

| Reason | Wind | Human impact |
|---|---|---|
| `null` | edge held | — |
| `angled-joint`, 90–160° | held IF bite check passes | 90° exactly → Table 5.1; over 90° → Table 5.3 |
| `angled-joint`, over 160° | not held (weatherseal) | Table 5.3 |
| `silicone-flat` | not held (weatherseal, 180° butt joint) | Table 5.3, counts as a butt joint |
| `frame-off` | ask the user | ask the user |
| `next-to-sashless` | not held | Table 5.3 |
| `sashless-free-edge` | not held (this is the sashless pane's own free edge — see §15) | counts as an unframed edge; drives sashless span per §15 |
| `sashless: true` (per pane) | 2-edge, span = the sight dimension between the two held edges, read from `unframedEdgeReasons` per pane (see §15) | Clause 5.15 |

`angled-joint` routing needs both `angledJoinAngleDeg` **and** `angledJoinType` (butt/mitred) — Pathway 3 already takes joint type as an input, so this maps onto existing Pathway 3 fields, run once per linked pane pair (via `linkedPaneId`).

---

## 9. Sashless wind span — confirmed supported; Section 14.5 rule 7 corrected

`calculate_span()` in `engine/wind_load/formulas.py` supports 2-edge with `span_dimension='width'` today (Pathway 2 already exposes it). So a sashless `X` pane's wind check is **not a gap**.

Section 14.5 rule 7 ("horizontal span out of scope") is documentation-only — not enforced anywhere in code — and is too broad. Restated: **horizontal-span glazing is out of scope for HUMAN IMPACT unless sashless (Clause 5.15); wind is supported.**

**Separate, unrelated gap flagged here (not part of this work):** nothing currently stops a Pathway 2 user selecting a horizontal span together with Table 5.3, which the table doesn't actually cover.

---

## 10. Edge support rule — opposite vs adjacent missing edges

- Two edges missing on **OPPOSITE** sides (e.g. left+right, or top+bottom) is a real 2-edge case, in scope.
- Two edges missing on **ADJACENT** sides (e.g. top+right) is **NOT** 2-edge — it's corner-supported, no AS 1288 chart exists for it, and the translation layer must reject this case rather than treat it as 2-edge.
- 3 or more edges missing (other than the sashless top+bottom case) is also out of scope.

---

## 11. Sliding panel height and double-hung jamb corrections — RESOLVED, verified against real code

Configurator batches 57–59 (commit `89d802c` on github.com/SGXDuce/Configurator) fixed:
- sliding-window/door `heightMM` now includes the head/sill tuck-in (40mm total, person-confirmed, sashless = flush/0)
- a real bug in batch 57 (`O` wrongly getting the height correction) was found and fixed in batch 58
- double-hung `widthMM` now includes a per-UNIT jamb tuck-in (40mm total per unit, including a boxed-in DDD middle unit)

All verified directly against the diff, not just the batch report. `widthMM`/`heightMM` are now trustworthy for both axes, both families, framed and sashless, **for preset-built assemblies**.

**Batch 60 (dad98aa + 24f1e45) extends this to a lone or manually split slider** — a slider pane (horizontal or vertical, both types treated the same) typed directly via the per-pane dropdown or manually split, with no D/DD/DDD or OX-style preset. Each edge is now corrected per edge, upstream, matching the preset-built correction. Top/bottom edges are corrected only where they touch the frame — NOT at a horizontal bar between two panes, since a bar isn't the outer frame. A fixed pane sitting next to a slider is uncorrected; the correction applies only to the sliding leaf's own edges. There is no batch 61; batch 60 is the current upstream state. See the Configurator's own docs (`configurator_export_schema.md`, section "Lone and manually split slider tuck-in (batch 60)", and `Configurator_Project_Summary.md`) for the exported figures and worked examples — not reproduced here.

**Rejected: a `tuckInCorrected` field.** No correction-tracking field was added, because no value in such a field can legitimately mean "the correct tuck-in is 0" — a slider edge with zero tuck-in and an edge that was never corrected would be indistinguishable, so the field would be actively misleading rather than merely incomplete.

**This repo's vendored copy is still `dad98aa` (no per-edge fix)** until re-vendored to pick up batch 60 in full (`dad98aa` + `24f1e45`). Do not treat a non-preset slider pane's `yMM`/`heightMM` as corrected in this repo until that re-vendor happens.

**Open product questions (28 September 2026):**
- Vertical slider head/sill tuck-in amount: confirmed present, but the figure used is the horizontal slider's 20mm-per-end reused — unconfirmed as correct for a vertical slider specifically.
- Top/bottom tuck-in at a real horizontal bar (not a frame edge): not built upstream at all — unconfirmed.

The translation layer's BAR and VERTICAL warnings (§15) are the stopgap for both open questions until they're resolved upstream.

---

## 12. Step A (schedule page + configurator embed) — built and verified

Live on branch `claude/determined-allen-duepf4` of github.com/SGXDuce/duce_glass_calc. Vendored configurator is at commit `dad98aa` (picks up batches 57–59; does NOT include the batch 60 per-edge slider tuck-in fix, which needs `dad98aa` + `24f1e45` — see §11). Re-vendoring to pick up batch 60 in full is still outstanding.

Full click-through test passed via Claude in Chrome: add row, edit geometry, build a sashless OX, Done, pane table populated correctly (sashless + `unframedEdgeReasons` both matched), reopen round-trips the same layout, close-without-Done leaves data unchanged. All 8 existing test suites still pass, no engine code touched.

---

## 13. Working notes

- Nothing from AGWA's codebase is referenced or reused.
- No AS 1288 table, figure or clause text reproduced in code, comments or docs — clause/table numbers only. Data in CSVs, logic in code.
- Engineering logic gets validated by hand, against Michael, or against the standard **before** code is written.
- The configurator project has no visibility into this project, so every handoff must be self-contained.
- **Verification status note:** `side_panel_rule_tester.html`, referenced in the configurator's own project summary as "built and verified," could not be found in either project's repo or files. Treat the side-panel rule (§6.3-referenced in the configurator's own docs) as documented but **unverified** on both sides until it turns up or is rebuilt.

---

## 14. Step C — ctx field mapping (human impact engine inputs)

Traced directly against the real recovered engine code (`engine/human_impact/__init__.py`, `location_rules.py`) on `master`, not against the original design notes — field names and required-vs-optional status confirmed from `match_location()`'s actual body.

### Fields derivable directly from the configurator export, no new question needed

| ctx field | Source |
|---|---|
| `opening_type` | pane's `productClass` — `'door'` or `'window'` map directly; `'side-panel'` also maps to `'window'`, with `is_side_panel` set separately |
| `is_side_panel` | `productClass === 'side-panel'`, via the configurator's own section 6.3 derivation rule |
| `is_louvre` | pane type === `'louvre'` |
| `blade_width_mm` / `blade_length_mm` | pane's `bladeWidthMM` / `bladeLengthMM`, already exported for louvre panes |
| `sight_width_mm` / `sight_height_mm` | `widthMM`/`heightMM` minus `sashEdgesMM` per side (see §6 item 5) |
| `panel_area_m2` / `panel_width_mm` | derived from the sight-size values above |
| `framing` (`'fully'`/`'partly'`/`'unframed'`) | derived from `unframedEdgeReasons`, using the opposite-vs-adjacent-edges rule (§10) and the four-reason routing table (§8) |

### Fields from the schedule row, already decided

| ctx field | Source |
|---|---|
| `building_use` | schedule row's building type |
| `is_bathroom` | schedule row's room type (kitchens included, NCC 8.4.6) |
| `high_risk` | schedule row's separate yes/no question |

### `sightline_mm` — RESOLVED

**Meaning (confirmed by Sahil):** height of the bottom edge of the visible glass above finished floor level (FFL).

**Formula:**
```
sightline_mm = row's height of lowest part of system above FFL + pane.yMM + pane.sashEdgesMM.bottom
```

**`yMM` convention**, per the Configurator export: measured from the elevation's main origin (bottom-left corner of the outer frame, or of the opening if there is no frame), Y increasing upward, and it is the pane's own bottom-left corner. The Configurator's internal drawing coordinates are top-down; the export code converts them. The AS 1288 tool only ever consumes the exported (bottom-up) version.

For fixed panes `sashEdgesMM` is zero, so the sash rail term is zero.

**Verified worked example:** 1800 x 2100 opening, 60mm frame all round, single plain horizontal-slider door pane, 40mm sash all edges, FFL height 0. Fresh export after re-vendoring to pick up the per-edge fix (`dad98aa` + `24f1e45`, batch 60) gave `yMM` 40, `heightMM` 2020, `sashEdgesMM.bottom` 40, so `sightline_mm = 0 + 40 + 40 = 80mm`. This matches the hand calculation (60mm sill, 20mm of the 40mm rail tucked in, 20mm visible, 60 + 20 = 80).

Before that fix (`6cc789e`) the same case exported `yMM` 60 and `heightMM` 1980, giving 100mm — the wrong result, now fixed upstream in batch 60. This repo's own vendored copy is still `dad98aa` alone (pre-batch-60 per-edge fix) — see §11/§12.

**Open questions carried forward (28 September 2026):** the vertical slider's own head/sill tuck-in amount (currently the horizontal slider's 20mm/end figure reused, unconfirmed), and top/bottom tuck-in at a real horizontal bar (not built upstream). See §11 and §15 for the translation layer's BAR/VERTICAL warnings that stand in for both until resolved.

### Fields that still need a real question asked somewhere, not derivable from geometry

| ctx field | Where it has to be asked |
|---|---|
| `opaque_or_patterned` | Per pane, a glass-order property the configurator has no reason to know |
| `rail_present`, `rail_upper_edge_mm`, `rail_lower_edge_mm`, `level_difference_mm` | The mistaken-for-doorway sub-questions (Clause 5.4) — per pane, asked only when relevant |
| framing for the `frame-off` edge case | Still needs the hybrid confirm-or-mark-edges question (§6 item 3) before framing can be computed for that case |

**Status:** the translation layer (pure geometry → ctx) is now fully specified for every geometry-derived field, including `sightline_mm` above. The remaining open items are all question-driven fields (`opaque_or_patterned`, the rail-height/`level_difference_mm` sub-questions) still using hand-supplied stub values pending UI design — they do not block building or testing the translation layer itself.

### End-of-section-14 status

**Built and merged to master, not yet wired.** The translation layer described above is now implemented: `engine/schedule/translation.py` (`translate_pane()`, `translate_system()`), tested in `tests/test_schedule_translation.py` (38 passed, via `python -m pytest tests/test_schedule_translation.py -q`). Full regression at merge: **131 passed**. It is NOT yet wired to the engine, the schedule page, or any route — it is a standalone, tested module only.

This section's ctx table above was missing one field: **`exposed_edges`**, which the human impact engine requires for a partly framed or unframed side panel. The translation layer supplies it (see §8's `frame-off` row and §15).

The layer produces **three output methods** — `fixed`, `louvre`, `sashless` — one per pane depending on its geometry, not a single method for the whole layer.

**Bug found and fixed during review, before merge:** the side-panel gap function originally measured the gap between a pane and a door leaf incorrectly when the pane sat to the LEFT of the door — it always returned 0 regardless of actual distance, only computing correctly for a pane to the door's right. Fixed, with boundary tests added for both directions at gap 100, 300, 301, and 1000mm (300 is the pass/fail threshold — see §15).

---

## 15. Translation layer decisions

Decided during the build of `engine/schedule/translation.py` (§14). Recorded here as **locked in — do not reopen** unless new information overturns the underlying assumption.

- **Door/side-panel classification is geometric, same elevation only.** The gap is measured sideways, between the two panes' VISIBLE-GLASS edges (sight edges, not outer frame edges), and must be `<= 300`mm inclusive. The candidate pane must overlap the door in height. The pane's own sightline must be `<= 1200`mm inclusive — that 1200 figure comes from project notes, not yet checked against the standard (open item below). Each pane is judged independently against every door pane in its elevation. A pane the Configurator itself labels `productClass: 'side-panel'` always counts as a side panel, regardless of what the geometry test says, with a warning raised if the geometry disagrees. There is no measurement across an angled join — the test only runs within one elevation.
- **A fixed, no-sash pane beside a sliding door leaf counts as a door** (Duce interpretation, not literal clause text) — covers a fixed light built into a sliding-door assembly that the Configurator doesn't itself tag as a door. No chaining (a fixed pane next to that fixed pane doesn't also become a door). Sliding windows (not doors) never trigger this. A fixed sidelight beside a hinged door is a side panel, not a door — the door-adjacency rule above is specific to sliding-door assemblies.
- **Human impact areas and widths, including the annealed exception caps, use sight size** (glass exposed to view, per §6 item 5's `sight_width_mm`/`sight_height_mm`), not true glass size. This is less conservative than true glass size for a sashed pane, since true glass size is always sight size plus the rebate overlap under the sash. **Open question for Michael** — flagged, not resolved.
- **Sashless span (Configurator batch 63 / schema v6) = the sight dimension measured between the two HELD edges**, read from `unframedEdgeReasons` per pane, not assumed from the pane type or a constant orientation. A pane must have exactly two edges marked `sashless-free-edge`, and they must be opposite each other (left+right, or top+bottom) — the other two edges are the held edges and must both carry reason `null`. Free edges left+right (held top/bottom, e.g. a horizontal slider) → span = `sight_height_mm`. Free edges top+bottom (held left/right, e.g. a double-hung/vertical slider, including its meeting-rail edge) → span = `sight_width_mm`. This replaces both the original "span = pane width" (§4) and the interim "span = `widthMM` minus both stile widths" — the latter assumed the pre-batch-63 orientation and was itself wrong for a double-hung.
- **Fail closed on unknown edge reasons.** Every pane's four `unframedEdgeReasons` values are checked against the known set (`null`, `angled-joint`, `silicone-flat`, `frame-off`, `next-to-sashless`, `sashless-free-edge`) before any framing or span logic runs, for every pane, sashless or not. Missing, non-string, empty, wrong-case, or otherwise unrecognised values return `not_assessable` — never treated as held. `sashless-free-edge` appearing on a pane whose `sashless` flag is false is also `not_assessable` (an inconsistent export).
- **Sashless edge-pattern rule.** Anything other than exactly two opposite `sashless-free-edge` edges (0, 1, 3, 4 free edges, or two adjacent free edges) is `not_assessable`. If a held edge (one of the remaining two) carries any reason other than `null`, that is also `not_assessable`, not treated as held.
- **Framing comes from `unframedEdgeReasons`** per §8 and §10's opposite-vs-adjacent rule. `'unframed'` (all four edges unsupported) is never produced by the translation layer. Three or more unframed edges are not assessed. An angled-joint edge at exactly 90° counts as held; over 90° counts as not held; a missing angle value makes that edge not assessable.
- **Stub answers default to no exemption** — a question-driven field without a real answer yet (§14's "still need a real question" table) defaults to the position that assumes the exemption does NOT apply, never the more permissive assumption. Sightline is never passed to the human impact engine as `None` (see `human-impact-engine-notes.md` on fail-open behaviour); a pane missing its FFL height is marked not assessable rather than guessed.
- **Slider handling: no refusal.** The translation layer does not block or reject a slider pane pending the open tuck-in questions (§11) — it proceeds and attaches two warnings instead, as built: a BAR warning (top/bottom tuck-in at a real horizontal bar is unconfirmed upstream) and a VERTICAL warning (a vertical slider's own head/sill tuck-in reuses the horizontal slider's unconfirmed 20mm/end figure).
- **Test fixtures.** Two real, hand-verified Configurator exports (schema v6, batch 63) now exist under `tests/fixtures/`: a sashless OX window (`sashless_ox_window.json`, horizontal-slider, span 1050mm measured top-to-bottom) and a sashless double-hung (`sashless_double_hung.json`, vertical-slider pair, span 1050mm measured left-to-right). The old hand-built 20mm-stile sashless test fixture is gone — it assumed the pre-batch-63 orientation. The lone-slider case (sightline 80mm, §14's worked example) and the slider-warning harness values remain real Configurator output; the rest of `tests/test_schedule_translation.py`'s fixtures are still hand-built, not exported.

### Open items (28 September 2026)

- The sight-size-for-human-impact-caps question above, for Michael.
- The 1200mm side-panel sightline figure needs checking against the standard.
- Check that Clause 5.15 still applies to a horizontal slider whose top and bottom edges are held — Sahil to check against the standard.
- **MUST DO at wiring time:** the wiring step must read the export's top-level `schemaVersion` and treat any sashless pane from a schema below 6 as not assessable, because a pre-v6 sashless export carries the old (wrong) edge orientation and would give a wrong span silently. `translate_pane()`/`translate_system()` cannot see `schemaVersion` (they only receive `export['system']`), so this check belongs where the full export is available.

---

## System check mode (design, 29 September 2026)

**Decided by Sahil**, sole engineering authority on this project as of this entry — Michael is no longer involved, so any earlier item recorded as "for Michael" or "blocked on Michael" (e.g. §6 item 4, superseded above) is now Sahil's call to make, not a block. Items below not explicitly resolved remain genuinely open and are listed at the end of this section.

- **A new top-level mode, "System check", sits above Pathways 1–3.** The landing page offers a choice: **"Check a single glass"** (the existing pathways, unchanged) or **"Build a system"**. This is a new mode alongside the pathways, not a fourth pathway.
- **One system per session, no persistence.** Output is the existing downloadable-results-snapshot style (see `downloadSnapshotAsImage`, verified in `AS1288_Full_Project_Summary.md` v1.36). The separate, not-yet-built Window Schedule feature (this document, §1 onward) is what will hold whole-job schedules of multiple systems — System check mode does not attempt that.
- **Flat structure, no building or room tree.** Each system carries THREE separate inputs matching the translator's row fields and the two-level classification in `engineering-decisions-notes.md`: (a) building type (aged care / school or early childhood / residential / other) feeding `building_use`; (b) room type (bathroom, with kitchens counted as bathrooms, or other) feeding `is_bathroom`; (c) high risk of breakage, a yes/no feeding `high_risk`. Building type and room type are required with NO defaults. This corrects an earlier single "room type" dropdown wording in this section, which wrongly folded building type into room type and treated it as a default only. Exact accepted `building_use` values must be confirmed against `engine/human_impact/location_rules.py` at build time (**UNVERIFIED**). **PROVISIONAL: Sahil cannot judge the layout until he sees it working.** No free-text label for now. Confirmed by Sahil.
- **HIGH RISK (Clause 5.24), DECIDED by Sahil as a Duce interpretation, not a literal reading of the clause:** Clause 5.24 states no height, but glass whose lowest sightline is more than 2000mm above FFL is not subject to human impact, so high risk is applied only to panes whose own lowest sightline is 2000mm or less (exactly 2000 counts as applying, following the existing inclusive convention; Sahil to confirm the boundary). The existing engine applies Clause 5.24 to every pane at any height (`location_rules.py` lines 298-304, seen by Sahil), so System check applies the cutoff in its own wiring by passing `high_risk` False for panes above 2000mm; the engine is unchanged. The cutoff uses each glass panel's own height (the outside glass panel is measured from the surface a person would stand on outside). Height must be measured from the surface people actually stand on, which for gymnasiums, halls and viewing galleries may not be the building FFL; show this as help text. Sahil's examples of high-risk areas for help text beside the question: gymnasiums, swimming pools and spa pools and enclosures, parts of schools, halls, public viewing galleries in stadiums and the like. **QUESTION RULE, PROPOSED by Claude, NOT yet confirmed by Sahil:** ask the high-risk yes/no once per system, and hide it only when every pane is either above 2000mm or already covered by a school, aged care, bathroom or kitchen rule at that pane's height; when hidden pass `high_risk` False. Sidelights and low-level glass at or below 2000mm that are not already covered must still be asked, because a Claude Code read-only run (`tests/test_human_impact.py` test_5 fully framed side panel and test_9 fully framed low-level window, reported by Claude Code and not re-run by Sahil) showed flipping `high_risk` alone blocked the annealed route entirely in both cases. Sahil's earlier view that the question could be skipped for low level and sidelight is contradicted by that run.
- **Both faceted angled joints and framed-and-sashless systems are in scope for the mode**, with framed and sashless to be built first internally, angled joints after. Build order (framed and sashless first, angled joints after) confirmed by Sahil as acceptable.
- **Wind input is ULS and SLS design pressures in kPa. Default: one pressure applied to every elevation. Option: the user may set a different pressure per elevation. Decided by Sahil.** The wind engine takes kPa directly on each call and `translate_system` tags each pane with its elevation, so a pane can use its own elevation's pressure (**UNVERIFIED, to be confirmed at build time**).
- **Required outputs: a single glass thickness/type that works for the whole system, AND the minimum for each pane.** Every candidate thickness must be checked against every pane directly — thicker must not be assumed safer for every clause, so the search cannot shortcut by assuming monotonicity.
- **Two operating modes inside System check.** (a) Find the minimum, per pane and for the whole system: both glass panels of an insulating glass unit are assumed EQUAL thickness (and the same glass type), which is what the existing Mode 1 minimum-thickness search supports. (b) Check a given spec: independent glass type and thickness per glass panel, matching the existing Mode 2 compliance check, reporting pass or fail. Decided by Sahil. Consequence: find-the-minimum cannot produce a mixed build-up (for example toughened inside, annealed outside); a mixed build-up can only be assessed in check mode.
- **TXT report: wanted for System check, in addition to the snapshot image. Decided by Sahil.** No download button in the UI for now; build the report builder and route only.
- **Terminology fixed for this mode, to avoid the ambiguity in earlier notes:** a **pane** is one glazed region in the Configurator's own model. A **glass panel** is one sheet of glass within an insulating glass unit (an IGU has an inside glass panel and an outside glass panel). A **leaf** refers only to a door leaf, never a glass panel.
- **Insulating glass unit (IGU) rules:**
  - **Fully framed IGUs only are in scope.** A partly framed or unframed IGU is out of scope for this mode — the tool shows a stop message and produces no result, rather than attempting an unsupported calculation.
  - **Human impact is run once per glass panel**, not once per pane — each glass panel (inside and outside) carries its own room/location category.
  - **The outside glass panel has its own height-above-surface input** (measured from the surface a person would actually stand on outside, which need not match the inside FFL) **and its own location category input**, independent of the inside glass panel's. For the outside glass panel the room type is never bathroom (Sahil's ground-floor example). Whether the outside glass panel needs its own building type and high-risk answer is **OPEN**.
  - **A mandatory access question with no default:** inside only, outside only, or both sides subject to human impact. This must be answered explicitly; the tool must not assume a default.
  - **The 1.5 area factor applies to the Table 5.1 maximum area only, and only when both sides are subject to impact.** It is never applied when access is one-sided.
  - **Annealed exception area caps are never multiplied by the 1.5 factor**, even when both sides apply — this is a deliberate Duce conservative interpretation, not asserted to be a literal reading of the clause text.
  - **Wind and human impact are assessed separately per glass panel, and the stricter of the two governs** that glass panel's result.
  - **Any 1.5 multiplier on the Table 5.1 maximum-area lookup (`get_safety_glass_max_area`, `engine/wind_load/formulas.py`) must default to 1.0 or be applied by the caller, so every existing caller (pathway3, pathway4, and the wind checks) is unchanged.** This is separate from the wind load-sharing factor (`calculate_kpane`), which is a different calculation and is not being changed.
- **Snapshot layout for this mode must warn if a glass panel was not assessed for human impact** (e.g. because the access question left that side out of scope), so the output can't be mistaken for a fully-checked result.
- **Build implications from the survey (UNVERIFIED):** the whole inputs step is new build — `schedule.html` has no input fields today. The three inputs (building type, room type, high-risk yes/no) must map onto `building_use`, `is_bathroom` and `high_risk` respectively. An IGU may be handled by calling `translate_pane` twice with different row values (inside and outside) — to be confirmed at build time. The snapshot layout and TXT report builder are both single-result shaped, so this mode needs its own snapshot layout. **Second read-only survey, UNVERIFIED:** `translate_pane` only guards `ffl_height_mm` (missing means `not_assessable`) and `frame_off_exposed` (missing means `needs_answer`). `building_use`, `is_bathroom`, `high_risk` and the five Clause 5.4 answers (`opaque_or_patterned`, `rail_present`, `rail_upper_edge_mm`, `rail_lower_edge_mm`, `level_difference_mm`) default silently and are never listed as missing, so a missing answer silently skips the school, aged care, bathroom or high-risk rules. The input step must therefore refuse to run until building type, room type, floor height and (where the high-risk question rule requires it) the high-risk answer are given. `building_use` is matched against exact string literals in `location_rules.py`, so option values must match exactly and a test must prove each triggers its rule. The five Clause 5.4 answers apply to any ordinary window pane that is not a side panel, regardless of framing (only `frame_off_exposed` is tied to framing); this is not IGU-specific, and an earlier note in this design that an IGU pane would need fewer questions was wrong. If `translate_pane` is called twice for an IGU (inside and outside), those five answers are per pane, not per glass panel, and must be supplied identically both times.

### Open items (29 September 2026)

- **Sahil to verify against the standard that the wind load-sharing method (`calculate_kpane`, `engine/wind_load/formulas.py:99` — verified to already take all panel thicknesses, see `AS1288_Full_Project_Summary.md` v1.36) matches AS 1288's intended method** for a fully framed IGU.
- **The 1.5 factor is decided as: Table 5.1 maximum area only, both-sides case only, annealed caps never multiplied.** Sahil may still re-read the clause wording to confirm this against the standard directly.
- **For an angled-joint pane pair where the two elevations have different wind pressures, which pressure governs the silicone bite calculation?** Suggested by Claude, NOT decided: the higher of the two (conservative). Sahil to decide and check against the standard.
- **Check mode input shape is undecided:** one given spec per pane, or one per system with a per-pane override?
- **In find-the-minimum mode, the outside glass panel gets the same glass type as the inside even if human impact applies to one side only (conservative).** Confirm this is acceptable.
- **(d) How to collect the five Clause 5.4 answers for windows: one answer per pane, or one per system with a per-pane override?** The existing human impact page already asks these questions and should be reused. Undecided.
- **(e) Landing screen: the mode choice screen resets on every visit, no stored choice** (simplest; Sahil may change).
- **(f) Sahil to confirm or change the proposed high-risk question rule.**
- **(g) The existing single-glass human impact page still applies Clause 5.24 at any height; whether to align it with the 2000mm cutoff is undecided.**
- **(h) Sahil to confirm the 2000mm boundary is inclusive (exactly 2000mm applies).**
- **(i) The daylight size for a fixed pane with no sash has not been checked** (added 30 September 2026, see below).
- **(j) The 20mm tuck-in of glass into a sash edge remains unconfirmed for some cases** — see section 11 above (added 30 September 2026).
- **(k) DECIDED BY SAHIL, 30 September 2026: wind AREA (and span, and aspect ratio) uses daylight size, not true glass size — see "Span built for every pane" below.** No longer open.

---

## System check mode — page shell built (30 September 2026)

**Built on branch `system-check-shell`; merged as PR #19, merge commit `a98260b`** (correction, 30 September 2026 — this paragraph previously said "not yet merged"; not silently edited, see this document's v1.41 section below). Two commits: `f69bb1a` (page shell — Configurator embed, `CONFIGURATOR_SCHEMA_VERSION` constant, `/system-check/translate` route, geometry-only pane table, fixed "no glass check has been run" banner) and `65f7f2a` (three follow-up fixes — a required floor-height field gating the server call, an exact rather than "at least" schema-version match, and a "Span (mm)" column fed from the translator's own `span_mm` instead of a hand-rolled recompute). Full detail, including what was VERIFIED BY SAHIL vs REPORTED BY CLAUDE CODE, is in `AS1288_Full_Project_Summary.md`'s v1.39 changelog entry — not repeated here in full. `SYSTEM_CHECK_ENABLED` remains `False` by default; `schedule.html`, `engine/`, and every CSV are untouched.

**DECIDED BY SAHIL (30 September 2026): span redefined as "Daylight size", and required for every pane.** Span for System check is measured on daylight size, between the supported edges: four edges supported → span is the shorter daylight dimension; two or three edges supported → span is the daylight length measured between the supported edges. "Daylight size" is the fixed UI term for this (internal field names are unchanged). Span must appear for every pane, not sashless panes only. **NOT YET BUILT** — the shell's pane table today only populates the Span column for a sashless pane. Worked case (the 1800 x 2100 slider door): daylight size 1640 x 1940 is the tool's own output, CONFIRMED BY SAHIL on screen, not calculated by hand. Span 1640 follows from the decided rule; it was derived by Claude and is NOT yet shown by the tool (span is only populated for sashless panes today).

**Two lists recorded, not built — see the v1.39 changelog entry in `AS1288_Full_Project_Summary.md` for the full numbered list.** COSMETIC (action after this round of testing): mode tile wording; a back button on the System check page (a "Back to start" link was lost when the placeholder page was replaced); stale "Wind Loads Only — Internal Use" header text; Configurator intro text implying nothing is wired to the engine; the height-field prompt's error styling; "fully framed" wording and framing-value mapping; renaming the "Method" column and adding a "Type" column; renaming "Sight size" to "Daylight size" in the UI; debouncing the height field so it doesn't call the server on every keystroke. PRE-RELEASE (public-launch requirement): removing the Duce-only door panel style options from the Configurator as used in this tool, which needs a Configurator-project change plus re-vendoring, and a read-only check first of whether door panel style affects the export at all (proposed by Claude, not yet done).

**NOT YET VERIFIED.** The red schema-mismatch banner has not been seen in a browser. A sashless system (span 1050) has not been built in a browser. The daylight size of a plain fixed pane with no sash has not been checked. It is not confirmed that the vendored Configurator copy is the latest re-vendor — the 80mm result is consistent with the per-edge fix in section 14 above, but the commit itself was not checked. `run_tests.sh` is untested. No EXE build has been tried on Python 3.14.

---

## System check mode — span built for every pane, not sashless only (30 September 2026)

**Built, on branch `system-check-span`, commits `ca19cd5` and `2204227`.** The Span column is no longer populated for sashless panes only — every ready pane (fixed, louvre, sashless) now gets a `span_mm` and a plain-sentence `span_basis`, both computed at the top level of `translate_pane()`'s result, never inside the `ctx` dict the human-impact engine reads (that dict is unchanged, proved by a test against master's own pre-change output). `_framing()` in `engine/schedule/translation.py` now also returns the set of unsupported edges it already worked out internally, without changing what it classifies. Commit `2204227` fixes a defect the schema-mismatch guard had (found in chat review by Claude, reproduced by Claude Code before the fix): a sashless pane the guard demoted to `not_assessable` for a non-matching schema version still carried its old `span_mm`/`span_basis` from before the demotion — both are now cleared by the guard, and `_pane_table_row()` also gates both fields on `status == 'ready'` as a second, independent check. Full detail, including what was VERIFIED BY SAHIL vs REPORTED BY CLAUDE CODE and the three browser test cases, is in `AS1288_Full_Project_Summary.md`'s v1.40 changelog entry — not repeated here in full. Only `engine/schedule/translation.py` was touched under `engine/`; `schedule.html` and every CSV remain untouched; `SYSTEM_CHECK_ENABLED` remains `False` by default.

**DECIDED BY SAHIL (30 September 2026): the span rule, confirmed against three browser cases, and daylight size confirmed as the basis for span, aspect ratio and area — settles open item (k) above.** Four edges supported → span is the shorter daylight dimension. Three supported edges → span is the daylight length between the one opposite pair of supported edges. Two opposite supported edges → span is the daylight length between them. Two adjacent unsupported edges, or three or more unsupported edges, stay `not_assessable`. Browser-verified against independent hand values written before viewing the tool's output: the Case A slider door (span 1640, all four edges supported); Case C, a vertical silicone joint splitting the opening into two 840 x 1980 panes (span 1980, `partly` framed — Sahil's hand value was taken from the Configurator's own Assigned panes table, so it is independent of the tool but not of the Configurator); Case B, a horizontal silicone joint splitting the opening into two 1680 x 990 panes (span 1680, `partly` framed, and suggesting — INFERRED by Claude from the sightlines, not measured — that the Configurator's silicone joint has no gap width, since the two panes' sightlines are contiguous). The Pathway 1 tooltip wording said "measured between framing members"; Sahil states "framing" there meant the sash, so Pathway 1 was already on daylight size (STATED BY SAHIL). The Pathway 2 and Pathway 3 tooltips say nothing about the basis, so whether those pathways take daylight size is NOT YET CONFIRMED by Sahil (open question).

**Findings.** A hand-built pane in `tests/test_schedule_translation.py`/`tests/test_system_check_shell.py` (the 1680-wide slider door object) computes a daylight width of 1600mm, but the real Configurator export (Case A above) gave 1640mm — that hand-built object is not a real export for width; only its sightline and height match. Test comments were corrected; assertions were not changed. A plain fixed pane with no sash (the silicone-joint panes in Cases B and C) showed daylight size equal to the Configurator's own glass size for those two panes specifically — not yet confirmed as the general no-sash case. This partly supersedes the older "NOT YET VERIFIED" paragraph above that says the daylight size of a plain fixed pane with no sash has not been checked; it now has been for two panes only.

**NOT YET VERIFIED (this entry).** Span for a pane whose unsupported edge comes from an angled joint or a `frame-off` reason — only silicone-joint unsupported edges were tried in a browser. Span is not yet fed into any wind calculation; System check still runs no wind or human-impact check at all.

---

## PR #20/#21 merged; full human impact confirmed in scope; Configurator variant policy decided (30 September 2026)

**Merged.** PR #20 (span built for every pane, the section above), merge commit `86d2f90` — the section above previously said only "on branch `system-check-span`" without stating it was merged; not silently edited, correction recorded here. PR #21 (cosmetic batch), merge commit `a974610`, commits `62d2a02`, `68af6d1`, `81edcc6`: mode-tile wording; a "Back to start" link; a neutral (not red) height prompt; "fully framed"/"partly framed" display wording (route/engine value unchanged); the "Daylight size" column header (UI text only); span basis text naming the unsupported edge(s) (`span_mm` values unchanged); the stale-response sequence counter moved to the top of `renderSystem()`; and the debounced height field replaced by an explicit trigger (Enter, or an "Update table" button — see the decision below). Full detail is in `AS1288_Full_Project_Summary.md`'s v1.41 changelog entry — not repeated here in full. `SYSTEM_CHECK_ENABLED` remains `False` by default; `schedule.html` and every CSV are untouched by both PRs.

**DECIDED BY SAHIL (30 September 2026).** Full human impact is now IN SCOPE — any earlier wording calling it deferred/conceptual/out of scope is superseded (see the Summary's v1.41 entry, item B.1, for the specific passages found and why each is superseded rather than flagged). Two entry routes exist: the standard Pathways 1-3 (unchanged), and the Configurator route (System check), which is DESIGNED to use the human impact engine via the translation layer (`engine/schedule/translation.py`); this is NOT YET WIRED. Table 5.1 is a human impact table; the 1.5 factor applies to human impact only, under the same Table-5.1-maximum-area-only / both-sides-only / annealed-caps-never-multiplied rule already decided in this document's "System check mode (design, 29 September 2026)" section above — the existing five `get_safety_glass_max_area()` callers stay unchanged (default factor 1.0). Pathways 2 and 3 are **supposed to** take daylight size dimensions — closes this document's open item (referenced above as "Whether Pathways 2 and 3 take daylight size"), as a statement of intent only; the Pathway 2/3 tooltips and code were not checked against it (tracked as the Summary's cosmetic item 11). The System check page must not call the server until the user enters the height and presses Enter or clicks a button — built in PR #21 (`81edcc6`).

**The Configurator variant.** The AS 1288 variant of the vendored Configurator drops the Duce-only door panel styles (`DOOR_PANEL_CATALOG`, styles "D1-D25/D32" — **CORRECTION, see this document's v1.42 entry below: `DOOR_PANEL_CATALOG` actually had 33 keys, including non-sequential names such as `D5L` and `D64H`; `D21` did not exist**) and the price-list default sizes, since the tool is going public; the main Configurator project keeps them for other tools such as pricing. Relevant variant changes are carried back to the main Configurator at the end of this project.

**REPORTED BY CLAUDE CODE (read-only survey, not verified by Sahil).** `get_safety_glass_max_area()` (`engine/wind_load/formulas.py`) has five call sites, all in `engine/`, all positional. No test calls it by name. The annealed exception caps are computed separately in `combine_alts()` (`engine/human_impact/routes.py`) from three CSVs and never call it, so an area factor added to it cannot reach them. `calculate_kpane()` takes only thicknesses. The door panel style catalogue and its picker live entirely in `configurator.html`; `doorPanelStyleId`/`doorPanelZoneChoices` are not present in the exported pane object and nothing in `engine/`, `interfaces/`, or `tests/` reads them; the vendored directory holds only `configurator.html` and `VARIANT_CHANGES.md` (no images); "Duce"/"NGR" appear only in code comments and door-style material option strings.

**INFERRED BY CLAUDE (not verified).** Because exported glazed area never reads `doorPanelStyleId`, a door panel given a solid-timber-zone style would still export as fully glazed, overstating its glass area. **PROPOSED BY CLAUDE (not decided).** Run the variant as a ledger in `VARIANT_CHANGES.md`, one small commit per change tagged "AS1288-only, do not carry back" or "carry back"; delete rather than hide Duce-only content in the variant; bump the schema version on both sides for any export-shape change. Three separately-decidable "default sizes": (a) preset default section widths (Duce's NGR price list); (b) the default sash edge shape (also Duce's NGR data — possibly, unconfirmed, why a new slider door starts with a 40mm sash); (c) the 20mm sliding tuck-in, marked person-confirmed in the vendored code (INFERRED BY CLAUDE from the code comment wording "person-confirmed (Duce)"; not verified), which feeds sightline and daylight size directly — removing it would change already-verified figures, unlike (a)/(b).

**Cosmetic list, DONE and merged (PR #21):** mode tile wording; back button; neutral prompt; "fully framed" wording; "Daylight size" label; the explicit-trigger height field (DECIDED BY SAHIL); span basis naming the edge. **STILL PENDING:** the stale "Wind Loads Only — Internal Use" header text; the Configurator's own intro text (fix belongs in the Configurator project or the variant); renaming "Method"/adding "Type" (design decision needed); rewording the Pathway 1/2/3 dimension tooltips to say "daylight size" (touches live pages). **NEW this entry** (from the cosmetic-branch browser check): show the "Height changed" message even when the pane-table area is already empty; the "Update table" button currently sits below the height field, not beside it; once a valid number is already in the field, the prompt shown on re-edit should say "Press Enter or click Update table", not repeat the empty-field "Enter the height..." text. **PRE-RELEASE:** remove the Duce-only door panel styles from the AS 1288 variant; decide the scope of the Duce/NGR comments and the price-list default sizes (see the three-part breakdown above).

**Open items, unchanged except as closed above:** every item in this document's "Open items (29 September 2026)" list remains open, except (k) (already closed in the "span built for every pane" section above) and the daylight-size intent for Pathways 2/3 (closed as a statement of intent only, per the decision above — the tooltip wording itself is unclosed, tracked as a cosmetic item). New open item: the scope of removing the Configurator variant's default sizes (see above).

**NOT YET VERIFIED (this entry).** The span-basis text naming the unsupported edge(s) for a partly-framed pane has not been checked in a browser after the cosmetic change — only source-level tests cover it. The behaviour of a slow server response arriving after the height field has already been re-edited has not been observed — a local development server responds too fast to reliably trigger that race by hand.

---

## System check mode — Configurator variant: deletions merged, survey findings, decisions and plan (1 October 2026)

**This section mirrors `AS1288_Full_Project_Summary.md`'s v1.42 changelog entry — read that entry for the full detail; only a short summary is kept here.**

**Merged (git log).** PR #23 (merge `0e465be`, variant ledger started, commit `88c4be0`); PR #24 (merge `8634c6e`, price-list default sizes deleted, commit `d7aecdb`); PR #25 (merge `b9253f1`, door panel styles deleted, commits `b347831` and `10b53e3`); PR #26 (merge `013c43a`, `PRESET_SASH_EDGES` deleted, commit `24a9a68`). Only `configurator.html` and `VARIANT_CHANGES.md` changed across all four PRs — nothing else changed.

**VERIFIED BY SAHIL (browser, 30 September - 1 October 2026):** the OX preset build (1800 x 2100 elevation, 60mm frame, sliding door OX at 860/920) gives the same rows after the deletions as on master before them; the "Closest standard size" line and the door-panel-style picker button are gone; a casement C preset still gives sash 40 and the expected daylight size and sightline after the `PRESET_SASH_EDGES` deletion; there is one "Sash frame width" box in the toolbar, not per-edge; the Configurator's own Assigned panes table and the export/System check table show different numbers for the same OX build (O 820 vs 860, X unchanged at 920 made size but 840 export daylight).

**REPORTED BY CLAUDE CODE (read-only survey):** `DOOR_PANEL_CATALOG` had 33 keys, not the "D1-D25/D32" sequential range this document previously stated (corrected above) — includes non-sequential names (`D5L`, `D64H`); `D21` did not exist. Sash is single-box in the UI but already per-edge in the data model, drawing, export and glazed-area calculation. Tuck-in today is a fixed per-edge amount gated only on `hasFrame`/sashless, never on sash width; casement and awning leaves get no tuck-in correction at all; corrections are export-time only, never stored on a leaf, so the table and export can disagree. The OX worked trace and the `SLIDING_OVERLAP_MM` fixed-60 figure are detailed in the Summary's v1.42 entry.

**REPORTED BY SAHIL (product facts):** in an OX slider the O panel has no sash but has a meeting-edge stile; the X's meeting stile overlaps in front of it in a parallel plane; both stiles start on the same line (the O's visible-glass edge); the gap/overlap between the two glass pieces depends on the relative stile widths (full worked cases in the Summary's v1.42 entry, item D).

**DECIDED BY SAHIL (30 September - 1 October 2026):** edit the vendored Configurator directly as a logged fork (`VARIANT_CHANGES.md`, one small commit per change, tagged `AS1288-only` or `carry back`); frame widths start at 60 all sides, every sash stile/rail starts at 40 and all become editable per edge (four boxes replacing the single box); tuck-in becomes an editable per-leaf-edge value for casements, awnings, hinged doors and sliders (not fixed panes), sliders keeping today's 20mm default, everything else starting at 0; a tuck-in cannot exceed its edge's sash width and a sash edge cannot be narrowed below its tuck-in without lowering the tuck-in first; silicone-joint edges stay at sash 0 with no tuck-in; the O panel of an OX has no tuck-in and is only its visible glass, with the preset form's O width meaning glass plus meeting stile; the Configurator's table gains made-size and daylight columns from the same correction code as the export; no legacy-loading path is needed (no saved systems exist). Full plan order (11 steps, casement change through the OX meeting-edge fix) is in the Summary's v1.42 entry, item E.11 — step 5d is the only step that changes OX numbers.

**INFERRED BY CLAUDE / PROPOSED BY CLAUDE / Still OPEN:** see the Summary's v1.42 entry, items F-H, for the full worked model, the proposed export option for the O's meeting stile (schemaVersion 6 to 7, not decided), and the open items (step 5d's scope beyond OX, the Window Schedule page's read of the O, the upstream Configurator baseline commit, the `hasFrame` tuck-in gating, and all v1.41 cosmetic/loose-end items, unchanged).
