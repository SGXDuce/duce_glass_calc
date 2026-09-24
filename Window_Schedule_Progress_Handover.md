# Window Schedule feature — progress handover

**Project:** AS 1288 Tool (Duce Glass Calc)
**Date:** 24 September 2026
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

All verified directly against the diff, not just the batch report. `widthMM`/`heightMM` are now trustworthy for both axes, both families, framed and sashless.

---

## 12. Step A (schedule page + configurator embed) — built and verified

Live on branch `claude/determined-allen-duepf4` of github.com/SGXDuce/duce_glass_calc. Vendored configurator at commit `6cc789e` (needs re-vendoring to pick up batches 57–59 before Step C work starts).

Full click-through test passed via Claude in Chrome: add row, edit geometry, build a sashless OX, Done, pane table populated correctly (sashless + `unframedEdgeReasons` both matched), reopen round-trips the same layout, close-without-Done leaves data unchanged. All 8 existing test suites still pass, no engine code touched.

---

## 13. Working notes

- Nothing from AGWA's codebase is referenced or reused.
- No AS 1288 table, figure or clause text reproduced in code, comments or docs — clause/table numbers only. Data in CSVs, logic in code.
- Engineering logic gets validated by hand, against Michael, or against the standard **before** code is written.
- The configurator project has no visibility into this project, so every handoff must be self-contained.
- **Verification status note:** `side_panel_rule_tester.html`, referenced in the configurator's own project summary as "built and verified," could not be found in either project's repo or files. Treat the side-panel rule (§6.3-referenced in the configurator's own docs) as documented but **unverified** on both sides until it turns up or is rebuilt.
