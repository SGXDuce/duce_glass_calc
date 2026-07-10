# AS 1288 Glass Thickness Calculator
# engine/combined/pathway4.py
#
# Pathway 4 (Branch 4, Section 14 / 12.12) - Structural Glazing, flat and
# angle-free. Thin orchestrator over engine/structural_glazing/, following
# the same one-orchestrator-per-pathway pattern as engine/combined/pathway3.py
# (Section 13.1's one deliberate exception to "engines don't import each
# other" - this module isn't itself an engine).
#
# Scenario scope gate (Section 12.12 item 8, confirmed by Michael): only
# 'full_perimeter' is available in this version. 'verticals_only' is a real,
# already-built and tested engine capability (Case B of
# tests/test_structural_glazing.py) but Duce's real-world build frequency for
# it as a *user-facing pathway option* is not yet confirmed, so it is gated
# out here, at the orchestrator boundary - NOT in the engine, which remains
# fully capable of computing it (and continues to be tested directly via
# test_structural_glazing.py). 'horizontals_only' was already out of scope at
# the engine level (weatherseal only, no structural bite - Section 12.12
# item 5) and remains so. The out-of-scope branch below is unchanged by the
# v1.22 Table 5.1 wiring - it returns a single make_structural_glazing_result()
# dict, exactly as before, since it never reaches per-subtype work at all.
#
# Table 5.1 human-impact wiring (v1.22, implements the v1.21 documentation-only
# decision - Section 12.12 item 9, Section 14.7): applies to full_perimeter
# ONLY. run_structural_glazing_calculation() has no glass-subtype concept -
# it returns one bite-based nominal thickness per Table 4.1 BROAD category
# (Monolithic/Laminated), shared across every subtype in that category, the
# same way Pathway 3's bite step works. But Table 5.1 eligibility and area
# limits (get_safety_glass_max_area(), SAFETY_GLASS_INELIGIBLE) are keyed per
# SUBTYPE, not broad category - Monolithic Toughened is eligible, Monolithic
# Annealed/Heat-strengthened are not, despite sharing the same bite-based
# thickness. So the full_perimeter branch now runs the shared bite/dead-load
# calculation once (unchanged), then loops over all six subtypes, applying
# Table 5.1 independently per subtype and combining via max() - mirroring
# Pathway 3's own bite-once/human-impact-per-subtype structure exactly.
#
# The Table 5.1 search loop below is a local reimplementation of the same
# shape as pathway3.py's _run_table_5_1_search() (same ascending-scan pattern,
# same shared get_safety_glass_max_area() formula reused), not a cross-import
# from pathway3.py: that function is private to pathway3.py, and importing it
# would create an orchestrator-to-orchestrator dependency this codebase
# doesn't use anywhere else (pathway3.py itself set the precedent of local
# reimplementation over cross-module reuse when the existing implementation
# wasn't cleanly isolatable - see that module's own docstring). This keeps
# Pathway 3 completely untouched, per this session's explicit scope.

from engine.structural_glazing.formulas import run_structural_glazing_calculation
from engine.wind_load.constants import GLASS_TYPE_THICKNESSES, SAFETY_GLASS_INELIGIBLE
from engine.wind_load.formulas import get_safety_glass_max_area
from engine.shared.results import make_structural_glazing_result, make_pathway4_result

SUPPORTED_SCENARIOS_V1 = ('full_perimeter',)

SUBTYPES = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Toughened'),
    ('Monolithic', 'Heat-strengthened'),
    ('Laminated', 'Annealed'),
    ('Laminated', 'Heat-strengthened'),
    ('Laminated', 'Toughened'),
]

BITE_FIELD_FOR_CATEGORY = {
    'Monolithic': 'nominal_monolithic',
    'Laminated': 'nominal_laminated',
}


def _run_table_5_1_search(glass_type, glass_subtype, panel_area_m2, thickness_list):
    """
    Independent ascending scan of this subtype's own stocked thickness range
    for the AS 1288 Table 5.1 Safety Glass Area Check - see module docstring
    for why this is a local reimplementation rather than an import from
    pathway3.py's equivalent private helper.
    """
    if (glass_type, glass_subtype) in SAFETY_GLASS_INELIGIBLE:
        return {'status': 'INELIGIBLE', 'minimum_thickness_mm': None, 'trace': []}

    trace = []
    for thickness in thickness_list:
        max_area = get_safety_glass_max_area(glass_type, glass_subtype, thickness)
        if max_area == 'EXTRAPOLATE':
            trace.append({
                'check': 'SG', 'thickness': thickness, 'max_area': 'EXTRAPOLATE',
                'actual_area': panel_area_m2, 'result': 'EXTRAPOLATE',
            })
            return {'status': 'COMPLIANT', 'minimum_thickness_mm': thickness, 'trace': trace}
        elif max_area is None:
            continue
        elif panel_area_m2 <= max_area:
            trace.append({
                'check': 'SG', 'thickness': thickness, 'max_area': max_area,
                'actual_area': panel_area_m2, 'result': 'PASS',
            })
            return {'status': 'COMPLIANT', 'minimum_thickness_mm': thickness, 'trace': trace}
        else:
            trace.append({
                'check': 'SG', 'thickness': thickness, 'max_area': max_area,
                'actual_area': panel_area_m2, 'result': 'FAIL',
            })

    return {'status': 'NON_COMPLIANT', 'minimum_thickness_mm': None, 'trace': trace}


def run_pathway4_calculation(height_m, width_m, glass_thickness_nominal_mm,
                              pz_kpa, scenario, safety_glass_required=False):
    """
    Master function for Pathway 4 - Structural Glazing (flat, angle-free).
    Section 14's decision tree routes here for frame-bonded glazing with no
    silicone joint angle and no supporting frame on the sealed edges.

    scenario: which edges are sealed. Only 'full_perimeter' is in scope for
    this version (Section 12.12 item 8) - any other value (including the
    engine-capable 'verticals_only', and the engine-out-of-scope
    'horizontals_only') returns a single CONFIGURATION_OUT_OF_SCOPE_V1 dict
    without calling run_structural_glazing_calculation() at all - unchanged
    from before this session.

    safety_glass_required: the safety-glass toggle (Section 14.7) - defaults
    to False (OFF), matching the project-wide rule that human impact tables
    are user-declared, never automatic. Only meaningful for full_perimeter;
    ignored (not even accepted meaningfully) for out-of-scope scenarios since
    that branch returns before any subtype work.

    Return shape differs by branch, deliberately: the out-of-scope branch
    returns a single make_structural_glazing_result() dict (unchanged); the
    full_perimeter branch returns a dict keyed by (glass_type, glass_subtype)
    tuples for all six subtypes, each value a make_pathway4_result() dict -
    mirroring run_pathway3_calculation()'s return shape, since Table 5.1 is
    inherently per-subtype (see module docstring).
    """
    if scenario not in SUPPORTED_SCENARIOS_V1:
        return make_structural_glazing_result(
            status='CONFIGURATION_OUT_OF_SCOPE_V1',
            height_m=height_m, width_m=width_m,
            glass_thickness_nominal_mm=glass_thickness_nominal_mm, pz_kpa=pz_kpa,
            sealed_edges=scenario,
            message=(
                f"Scenario '{scenario}' is not yet available in this version of "
                f"the tool and may be added in a future release. Only "
                f"'full_perimeter' is currently supported for Pathway 4."
            ),
        )

    bite_result = run_structural_glazing_calculation(
        height_m=height_m, width_m=width_m,
        glass_thickness_nominal_mm=glass_thickness_nominal_mm,
        pz_kpa=pz_kpa, sealed_edges=scenario,
    )

    # panel_area_m2 for Table 5.1 is the raw panel area (height x width) -
    # NOT the wind-bite span (min(width_m, height_m), Section 12.12 item 6/
    # the v1.19 fix). Confirmed distinct concepts: Table 5.1's area check has
    # nothing to do with which dimension governs the wind-bite calculation.
    panel_area_m2 = round(height_m * width_m, 4)

    results = {}

    for (glass_type, glass_subtype) in SUBTYPES:
        subtype_key = (glass_type, glass_subtype)
        bite_thickness_mm = bite_result[BITE_FIELD_FOR_CATEGORY[glass_type]]

        # --- broad-category short circuit (bite/dead-load engine result) ---
        if bite_thickness_mm is None:
            results[subtype_key] = make_pathway4_result(
                status='BITE_NO_COMPLIANT_THICKNESS', subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'Required bite ({round(bite_result["governing_bite_mm"], 3)}mm) '
                        f'exceeds all available {glass_type} thicknesses.',
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                bite_trace=[{
                    'check': 'BITE', 'category': glass_type, 'result': 'FAIL',
                    'required_bite_mm': bite_result['governing_bite_mm'],
                }],
            )
            continue

        # --- Table 5.1, gated on the toggle (Section 14.7) ---
        table_5_1_thickness_mm = None
        table_5_1_trace = []
        table_5_1_status = None  # None = not applicable / not run

        if safety_glass_required:
            thickness_list = GLASS_TYPE_THICKNESSES[subtype_key]
            table_5_1_result = _run_table_5_1_search(
                glass_type, glass_subtype, panel_area_m2, thickness_list
            )
            table_5_1_trace = table_5_1_result['trace']
            if table_5_1_result['status'] == 'INELIGIBLE':
                table_5_1_status = 'HUMAN_IMPACT_INELIGIBLE'
            elif table_5_1_result['status'] == 'NON_COMPLIANT':
                table_5_1_status = 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS'
            else:
                table_5_1_thickness_mm = table_5_1_result['minimum_thickness_mm']

        if table_5_1_status == 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS':
            results[subtype_key] = make_pathway4_result(
                status=table_5_1_status, subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'No compliant thickness for {glass_type} {glass_subtype} '
                        f'under AS 1288 Table 5.1.',
                bite_thickness_mm=bite_thickness_mm,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                table_5_1_trace=table_5_1_trace,
            )
            continue

        # --- governing thickness: max(bite, Table 5.1 if it ran and passed) ---
        candidates = [bite_thickness_mm]
        if table_5_1_thickness_mm is not None:
            candidates.append(table_5_1_thickness_mm)
        governing_thickness_mm = max(candidates)

        results[subtype_key] = make_pathway4_result(
            status='PASS' if table_5_1_status is None else table_5_1_status,
            subtype=subtype_key, glass_type=glass_type, glass_subtype=glass_subtype,
            message='PASS',
            governing_thickness_mm=governing_thickness_mm,
            bite_thickness_mm=bite_thickness_mm,
            table_5_1_thickness_mm=table_5_1_thickness_mm,
            panel_area_m2=panel_area_m2,
            safety_glass_required=safety_glass_required,
            table_5_1_trace=table_5_1_trace,
        )

    return results
