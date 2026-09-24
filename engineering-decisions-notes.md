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

## Open structural glazing questions

- Sahil proposed an edge-polish deduction (~2mm) for frame/surface-bonded structural glazing, analogous to the chamfer deduction in the faceted engine
- Claude flagged this as structurally questionable: the chamfer deduction is valid in the faceted engine because silicone bonds to the cut edge (bonding surface = thickness dimension), whereas in frame-bonded glazing silicone bonds to the flat face, so an edge-perimeter treatment doesn't obviously reduce face-bond capacity
- Needs Michael's confirmation before deciding whether any deduction applies, and if so its mechanism and magnitude
- Sahil is leaning toward surface-to-glass being a separate UI mode (lowest-priority V2 feature) — not yet decided
- Phase 1C structural glazing scope: Scenario 3 (horizontals sealed only) is out of scope pending Sahil's confirmation; only Scenario 1 (full perimeter) and Scenario 2 (verticals sealed) are in scope
