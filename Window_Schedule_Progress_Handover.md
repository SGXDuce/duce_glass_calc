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
| Sashless orientation | Sashless always means the glass **horizontal** edges have no sash rail, with thin stiles left/right. Span = distance between stiles = pane width. Constant, so no export field needed. |
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

1. **Schedule row fields.** Room type vocabulary is undefined. It must map onto the human impact location categories already implemented (ordinary, bathroom/ensuite/spa, school/early-childhood, aged-care, none-of-these). Building type and FFL entry also need defining.
2. **Per-pane height above FFL.** The row gives the system's lowest point above FFL; each pane's own Y offset comes from the configurator export. Per-pane height = system base + pane offset. **Each pane can trigger a different clause** — do not apply one verdict to the whole system based on the lowest pane.
3. **Exposed edges (Clause 5.3.1(b)) — DECIDED.** `unframedEdgeReasons` (configurator schema v5) gives four reasons an edge can be unframed: `angled-joint`, `silicone-flat`, `frame-off`, `next-to-sashless`. Decision: only `frame-off` asks the schedule-row/pane user whether the edge is exposed. The other three reasons are joined to another pane (sealed or overlapping), so they default to not exposed.
4. **Multi-panel uniform glass thickness.** Blocked on Michael: is picking one thickness for a multi-panel system and checking it against every panel safe (monotonic) across Tables 4.1 / 5.1 / 5.3? This feature is exactly the use case that forces the answer.
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
| `sashless: true` (per pane) | 2-edge, span=width — engine already supports this (§9) | Clause 5.15 |

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
- **Sashless span = `widthMM` minus both stile widths** (previously documented, incorrectly, as "span = pane width" — see §4). The stiles are the vertical side members left when the two horizontal edges are unframed.
- **Framing comes from `unframedEdgeReasons`** per §8 and §10's opposite-vs-adjacent rule. `'unframed'` (all four edges unsupported) is never produced by the translation layer. Three or more unframed edges are not assessed. An angled-joint edge at exactly 90° counts as held; over 90° counts as not held; a missing angle value makes that edge not assessable.
- **Stub answers default to no exemption** — a question-driven field without a real answer yet (§14's "still need a real question" table) defaults to the position that assumes the exemption does NOT apply, never the more permissive assumption. Sightline is never passed to the human impact engine as `None` (see `human-impact-engine-notes.md` on fail-open behaviour); a pane missing its FFL height is marked not assessable rather than guessed.
- **Slider handling: no refusal.** The translation layer does not block or reject a slider pane pending the open tuck-in questions (§11) — it proceeds and attaches two warnings instead, as built: a BAR warning (top/bottom tuck-in at a real horizontal bar is unconfirmed upstream) and a VERTICAL warning (a vertical slider's own head/sill tuck-in reuses the horizontal slider's unconfirmed 20mm/end figure).
- **Test fixtures.** Only the lone-slider case (sightline 80mm, §14's worked example) and the slider-warning harness values are taken from real Configurator output. Every other test fixture in `tests/test_schedule_translation.py` is hand-built, not exported. The sashless span test assumes a 20mm stile width, which is unverified against a real product. Fixtures built from real Configurator exports are still to be added.

### Open items (28 September 2026)

- The sight-size-for-human-impact-caps question above, for Michael.
- The 1200mm side-panel sightline figure needs checking against the standard.
