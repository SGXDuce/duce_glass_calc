# AS 1288 engineering decisions — locked-in precision rules and open questions

Locked-in AS 1288 engineering decisions, precision rules, and the open questions still awaiting Michael's sign-off.

## Precision and liability

- No rounding at the Table 4.1 compliance comparison step anywhere in the engine — exact float comparison only
- Rounding is permitted only for display/report output, strictly after the pass/fail decision is made on the unrounded value; this is liability-driven
- Flag to Michael as a possible discrepancy vs. Duce's manual spreadsheet process if that process rounds before comparing

## Locked-in decisions

- Table 5.1 applies at exactly 90° (Michael confirmed); Table 5.3 for all other faceted cases (>90°–160°)
- `full_perimeter` structural glazing uses Table 5.1 — confirmed via Adam Davies (AGWA) and Siddharth Kumaran (Viridian Glass); continuous four-edge silicone bonding treated as structurally equivalent to framing
- AS 3959 bushfire exclusion unaffected — silicone bonding doesn't satisfy AS 3959's "fully framed" definition (mechanical frame support required)
- IGUs excluded from Pathways 2 and 3 as a deliberate product scope decision
- 6mm minimum applies to final nominal glass thickness after Table 4.1 lookup, both monolithic and laminated (Dow Corning seal sizing)
- B (governing panel dimension) = `max(Width 1, Width 2)` — no height capping; height-capping in Michael's original spreadsheet confirmed as an error
- Human impact tables run only when the safety glass toggle is ON — the user retains full responsibility for determining whether safety glass is required under AS 1288 Section 5
- A separate determination layer that answers this Section 5 question itself (rather than relying on the manual toggle) is being designed as a new feature — see the human-impact-engine notes for the full rule set, architecture, and open AGWA questions
- Standing 45-combination finding: no realistic geometry exists where ULS or SLS governs overall for `full_perimeter` panels — bite structurally dominates due to linear vs. AR-capped scaling; documented as a standing finding, not requiring artificial test cases
- Kitchens are treated the same as bathrooms/ensuites/spa rooms for human impact — this is a genuine NCC 2022 requirement (clause 8.4.6 groups them together, same 2.0m FFL threshold), not a Duce-only safety margin. Cite as NCC 2022 8.4.6 alongside the existing AS 1288 5.8 reference
- Schedule row classification is two-level: building type (aged care / school-early-childhood / residential / others), room type (bathrooms, kitchens-as-bathrooms, others). "High risk of breakage" is NOT a room type — it's a separate yes/no question asked on every job, layered on top of whichever room type applies
- Wind rating for a schedule system defaults to one rating for the whole system, with an optional per-pane override. The results view must show which panes use an override
- Translation layer decisions (`engine/schedule/translation.py`, see `Window_Schedule_Progress_Handover.md` section 15): door/side-panel classification is geometric and same-elevation only — gap measured sideways between visible-glass edges, `<= 300`mm inclusive, pane must overlap the door in height, pane's own sightline `<= 1200`mm inclusive (1200 still to be checked against the standard), each pane judged separately, a `productClass: 'side-panel'` label always counts (warning if geometry disagrees), no measurement across an angled join. A fixed no-sash pane beside a sliding door leaf counts as a door (Duce interpretation, not literal clause text), no chaining, sliding windows never trigger it; a fixed sidelight beside a hinged door is a side panel, not a door. Human impact areas/widths, including annealed caps, use sight size (open question for Michael, less conservative than true glass size for sashed panes). Sashless span = `widthMM` minus both stile widths (replaces "span = pane width"). Framing comes from `unframedEdgeReasons` per sections 8/10; `'unframed'` is never produced; 3+ unframed edges are not assessed; an angled-joint at exactly 90° counts as held, over 90° as not held, missing angle not assessable. Stub answers default to no exemption; sightline is never passed to the engine as `None`; a missing FFL height makes the pane not assessable. Slider handling has no refusal — two warnings only (bar warning, vertical slider warning), as built. Test fixtures: only the lone-slider case (sightline 80) and the slider harness values come from real Configurator output; every other fixture is hand-built; the sashless test assumes a 20mm stile (unverified); real-export fixtures still to be added
- `sightline_mm` definition and formula: height of the bottom edge of the visible glass above finished floor level (FFL). `sightline_mm = row's height of lowest part of system above FFL + pane.yMM + pane.sashEdgesMM.bottom`. `yMM` (per the Configurator export) is measured from the elevation's main origin (bottom-left corner of the outer frame, or of the opening if there is no frame), Y increasing upward, and is the pane's own bottom-left corner — the Configurator's internal drawing coordinates are top-down and the export code converts them; the AS 1288 tool only ever consumes the exported (bottom-up) version. For fixed panes `sashEdgesMM` is zero, so the sash rail term is zero. Sliders outside a D/DD/DDD or OX-style preset (single leaf or manually split) are now corrected per edge upstream (batch 60, `dad98aa` + `24f1e45`), both slider types the same; top/bottom edges are corrected only where they touch the frame, not at a horizontal bar between two panes; a fixed pane next to a slider is uncorrected. This repo's vendored configurator is still `dad98aa` alone (no per-edge fix) until re-vendored. Open product questions (28 September 2026): the vertical slider's own head/sill tuck-in amount is unconfirmed (the horizontal slider's 20mm/end figure is reused); top/bottom tuck-in at a real horizontal bar is not built upstream at all. The translation layer's BAR and VERTICAL warnings are the stopgap for both

## Open items — 28 September 2026

- Sight size (not true glass size) is used for the human impact area/width caps, including the annealed exception caps, in the translation layer — open question for Michael, since true glass size is always larger for a sashed pane and this is less conservative
- The 1200mm side-panel sightline ceiling used by the translation layer's geometric side-panel test comes from project notes and still needs to be checked against the standard

## Open structural glazing questions

- Sahil proposed an edge-polish deduction (~2mm) for frame/surface-bonded structural glazing, analogous to the chamfer deduction in the faceted engine
- Claude flagged this as structurally questionable: the chamfer deduction is valid in the faceted engine because silicone bonds to the cut edge (bonding surface = thickness dimension), whereas in frame-bonded glazing silicone bonds to the flat face, so an edge-perimeter treatment doesn't obviously reduce face-bond capacity
- Needs Michael's confirmation before deciding whether any deduction applies, and if so its mechanism and magnitude
- Sahil is leaning toward surface-to-glass being a separate UI mode (lowest-priority V2 feature) — not yet decided
- Phase 1C structural glazing scope: Scenario 3 (horizontals sealed only) is out of scope pending Sahil's confirmation; only Scenario 1 (full perimeter) and Scenario 2 (verticals sealed) are in scope
