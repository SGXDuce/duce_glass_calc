# AS 1288 Glass Thickness Calculator
# engine/combined/pathway4.py
#
# Pathway 4 (Branch 4, Section 14 / 12.12) - Structural Glazing, flat and
# angle-free. Thin orchestrator over engine/structural_glazing/, following
# the same one-orchestrator-per-pathway pattern as engine/combined/pathway3.py
# (Section 13.1's one deliberate exception to "engines don't import each
# other" - this module isn't itself an engine).
#
# Scenario scope gate (Section 12.12 item 8, confirmed with domain expert): only
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
# ONLY. Table 5.1 eligibility and area limits (get_safety_glass_max_area(),
# SAFETY_GLASS_INELIGIBLE) are keyed per SUBTYPE, not broad category -
# Monolithic Toughened is eligible, Monolithic Annealed/Heat-strengthened are
# not. So the full_perimeter branch loops over all six subtypes, applying
# Table 5.1 independently per subtype and combining via max() - mirroring
# Pathway 3's own bite-once/human-impact-per-subtype structure.
#
# The Table 5.1 search loop below is a local reimplementation of the same
# shape as pathway3.py's _run_table_5_1_search() (same ascending-scan pattern,
# same shared get_safety_glass_max_area() formula reused), not a cross-import
# from pathway3.py - see that module's own docstring for why (private
# function, no orchestrator-to-orchestrator dependency precedent).
#
# Five independent criteria (added this session, closing a gap flagged after
# v1.24's premature "engine complete" declaration - Section 14.4 always
# specified a wind-bending-as-4-edge check on the glass pane itself,
# independent of the silicone joint's own bite sizing, and this was never
# wired in): the joint (silicone bite, wind + dead load) and the pane (Mode 1
# ULS/SLS bending, AS 1288 Clause 4.4.3) are two physically independent
# failure modes - the joint can be adequate while the pane is overstressed,
# or vice versa. Pathway 3 already runs both (Section 12.13 step 3); Pathway
# 4 never got the equivalent step until now.
#
# CRITICAL - the two bite Table 4.1 lookups are done HERE, not inside
# run_structural_glazing_calculation() (which is NOT touched by this
# session - it remains a validated, unchanged engine function returning only
# the raw wind_bite_mm/dead_load_bite_mm figures and its own single combined
# nominal_monolithic/nominal_laminated via max(wind_bite, dead_load_bite)).
# This orchestrator instead calls find_min_nominal_for_usable_bite() twice
# per broad category - once against the raw wind_bite_mm, once against the
# raw dead_load_bite_mm - exactly replicating run_structural_glazing_
# calculation()'s own call pattern (same function, same joint_type=None,
# same chamfer_mm=EDGE_POLISH_DEDUCTION_MM, same MIN_NOMINAL_THICKNESS floor
# applied after) but keeping the two bite criteria as separate, independently
# governing values rather than pre-collapsed via max() inside the engine.
# This is why run_structural_glazing_calculation()'s own nominal_monolithic/
# nominal_laminated fields are no longer used for the governing calculation -
# only its raw wind_bite_mm/dead_load_bite_mm are.
#
# ULS/SLS come from check_glass_type() (engine/wind_load/checks/wind.py),
# support_condition='4-edge' (Section 14.4: "Wind load: 4-edge supported"),
# safety_glass_required=False (Table 5.1 is computed independently below,
# same reason pathway3.py never passes safety_glass_required into
# check_glass_type() either - see that module's own NOTE). span_dimension is
# a don't-care under support_condition='4-edge' - calculate_span() always
# uses min(height_mm, width_mm) for 4-edge regardless of span_dimension's
# value (engine/wind_load/formulas.py) - passed 'height' purely for
# consistency with pathway3.py's own call, never actually read.
#
# ENGINEERING FINDING, not a defect: an extensive parameter search (~45
# geometry/pressure combinations, both glass categories, square and
# elongated panels, wide pressure ranges) found no realistic full_perimeter
# geometry where ULS or SLS governs the OVERALL result - wind_bite and
# dead_load_bite both scale roughly linearly with panel size for a square
# panel, while ULS/SLS thickness demand grows much more slowly (capped by
# the AR=5 table row, Section 7.2), so bite structurally dominates across
# realistic ranges for this pathway's coupled geometry. SLS CAN exceed ULS
# as a sub-criterion (confirmed, e.g. h=1000mm/w=5000mm/ULS=1.0kPa/
# SLS=0.98kPa/Laminated Annealed -> uls=5mm, sls=6mm) even though bite still
# governs overall in that case - see tests/test_pathway4.py. Both criteria
# are still computed and returned unconditionally, per Section 6.1's
# independence principle - this finding does not change that they're real,
# active, independently-searched checks; it just documents why they are not
# expected to be the overall governing criterion in practice.

from engine.structural_glazing.formulas import run_structural_glazing_calculation
from engine.wind_load.checks.wind import check_glass_type
from engine.wind_load.constants import GLASS_TYPE_THICKNESSES, SAFETY_GLASS_INELIGIBLE
from engine.wind_load.formulas import get_safety_glass_max_area
from engine.shared.data_loader import load_table_data
from engine.shared.table_4_1 import (
    TABLE_4_1_MONOLITHIC, TABLE_4_1_LAMINATED, find_min_nominal_for_usable_bite,
)
from engine.structural_glazing.constants import EDGE_POLISH_DEDUCTION_MM, MIN_NOMINAL_THICKNESS
from engine.structural_glazing.formulas import apply_thickness_floor
from engine.shared.results import make_structural_glazing_result, make_pathway4_result

SUPPORTED_SCENARIOS_V1 = ('full_perimeter',)

TABLE_4_1_FOR_CATEGORY = {
    'Monolithic': TABLE_4_1_MONOLITHIC,
    'Laminated': TABLE_4_1_LAMINATED,
}

SUBTYPES = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Toughened'),
    ('Monolithic', 'Heat-strengthened'),
    ('Laminated', 'Annealed'),
    ('Laminated', 'Heat-strengthened'),
    ('Laminated', 'Toughened'),
]


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
        if max_area is None:
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


def run_pathway4_calculation(height_m, width_m, wind_pressure_uls_kpa,
                              wind_pressure_sls_kpa, scenario,
                              safety_glass_required=False,
                              csv_path=None, preloaded_df=None):
    """
    Master function for Pathway 4 - Structural Glazing (flat, angle-free).
    Section 14's decision tree routes here for frame-bonded glazing with no
    silicone joint angle and no supporting frame on the sealed edges.

    wind_pressure_uls_kpa / wind_pressure_sls_kpa: replaces the old single
    pz_kpa parameter (this session). ULS feeds BOTH the Appendix F silicone
    bite formula (same value, Section 14.4 calls it Pz - same physical
    quantity, different notation) and the Mode 1 ULS check; SLS feeds only
    the Mode 1 SLS check - dead load bite has no wind-pressure input at all
    (Section 12.11's shear formula depends only on geometry/thickness).

    scenario: which edges are sealed. Only 'full_perimeter' is in scope for
    this version (Section 12.12 item 8) - any other value (including the
    engine-capable 'verticals_only', and the engine-out-of-scope
    'horizontals_only') returns a single CONFIGURATION_OUT_OF_SCOPE_V1 dict
    without calling run_structural_glazing_calculation() at all - unchanged
    from before this session.

    safety_glass_required: the safety-glass toggle (Section 14.7) - defaults
    to False (OFF), matching the project-wide rule that human impact tables
    are user-declared, never automatic.

    csv_path/preloaded_df: the wind-load coefficient table needed by
    check_glass_type() (this session's new ULS/SLS criterion) - same
    preloaded-takes-precedence pattern as run_pathway3_calculation().

    Return shape differs by branch, deliberately: the out-of-scope branch
    returns a single make_structural_glazing_result() dict (unchanged); the
    full_perimeter branch returns a dict keyed by (glass_type, glass_subtype)
    tuples for all six subtypes, each value a make_pathway4_result() dict.
    """
    if scenario not in SUPPORTED_SCENARIOS_V1:
        return make_structural_glazing_result(
            status='CONFIGURATION_OUT_OF_SCOPE_V1',
            height_m=height_m, width_m=width_m,
            pz_kpa=wind_pressure_uls_kpa,
            sealed_edges=scenario,
            message=(
                f"Scenario '{scenario}' is not yet available in this version of "
                f"the tool and may be added in a future release. Only "
                f"'full_perimeter' is currently supported for Pathway 4."
            ),
        )

    df = preloaded_df if preloaded_df is not None else load_table_data(csv_path)

    # glass_thickness_nominal_mm=6 is a seed value only used by
    # run_structural_glazing_calculation() for its OWN internal dead-load
    # bite calc and its own (now-unused) Table 4.1 lookup - the actual dead
    # load bite requirement (dead_load_bite_mm) does depend on this seed
    # (Section 12.11's formula includes the glass's own weight), but not
    # strongly enough to matter for a seed value, and the real nominal
    # thickness is determined below via this orchestrator's own independent
    # Table 4.1 lookups against the raw bite figures - same convention as
    # before this session (the old bite_thickness_mm also came from a
    # 6mm-seeded call).
    bite_result = run_structural_glazing_calculation(
        height_m=height_m, width_m=width_m,
        glass_thickness_nominal_mm=6,
        pz_kpa=wind_pressure_uls_kpa, sealed_edges=scenario,
    )
    wind_bite_mm = bite_result['wind_bite_mm']
    dead_load_bite_mm = bite_result['dead_load_bite_mm']

    height_mm = height_m * 1000
    width_mm = width_m * 1000

    # panel_area_m2 for Table 5.1 is the raw panel area (height x width) -
    # NOT the wind-bite span (min(width_m, height_m), Section 12.12 item 6/
    # the v1.19 fix). Confirmed distinct concepts: Table 5.1's area check has
    # nothing to do with which dimension governs the wind-bite calculation.
    panel_area_m2 = round(height_m * width_m, 4)

    # --- Two independent Table 4.1 lookups per broad category (not per
    # subtype - the bite/dead-load engine has no subtype concept, see module
    # docstring) - exactly replicating run_structural_glazing_calculation()'s
    # own call pattern, but kept separate rather than pre-collapsed via
    # max() inside the engine. ---
    bite_nominal_by_category = {}
    for category, table in TABLE_4_1_FOR_CATEGORY.items():
        wind_nom, wind_usable = find_min_nominal_for_usable_bite(
            wind_bite_mm, table, joint_type=None, chamfer_mm=EDGE_POLISH_DEDUCTION_MM,
        )
        dead_nom, dead_usable = find_min_nominal_for_usable_bite(
            dead_load_bite_mm, table, joint_type=None, chamfer_mm=EDGE_POLISH_DEDUCTION_MM,
        )
        wind_nom_floored = apply_thickness_floor(wind_nom, MIN_NOMINAL_THICKNESS)
        dead_nom_floored = apply_thickness_floor(dead_nom, MIN_NOMINAL_THICKNESS)

        # Usable bite / actual thickness at the FLOORED nominal (the one
        # actually used/displayed) - if the floor raised the nominal beyond
        # what find_min_nominal_for_usable_bite() searched to, the usable
        # bite at that floored nominal is looked up fresh, since the search
        # stopped at the smaller pre-floor nominal.
        wind_usable_at_floor = (
            wind_usable if wind_nom_floored == wind_nom
            else table[wind_nom_floored] - EDGE_POLISH_DEDUCTION_MM
        ) if wind_nom_floored is not None else None
        dead_usable_at_floor = (
            dead_usable if dead_nom_floored == dead_nom
            else table[dead_nom_floored] - EDGE_POLISH_DEDUCTION_MM
        ) if dead_nom_floored is not None else None

        # Unlike Pathway 3, there is no pre-lookup required-bite floor here -
        # wind_bite_mm/dead_load_bite_mm ARE already the true raw required
        # bite (see module docstring). The only floor point is the final
        # nominal (MIN_NOMINAL_THICKNESS). To let the shared display wording
        # detect "was a floor applied" via required_bite_raw_mm !=
        # required_bite_floored_mm (same convention as Pathway 3), the
        # floored figure is set to the floored nominal's own usable bite
        # when the floor actually raised the nominal - otherwise it's
        # identical to the raw required bite, same as Pathway 3's unfloored
        # case.
        bite_nominal_by_category[category] = {
            'wind_bite_nominal_mm': wind_nom_floored,
            'dead_load_bite_nominal_mm': dead_nom_floored,
            'wind_required_bite_floored_mm': (
                wind_usable_at_floor if wind_nom is not None and wind_nom_floored != wind_nom
                else wind_bite_mm
            ),
            'dead_load_required_bite_floored_mm': (
                dead_usable_at_floor if dead_nom is not None and dead_nom_floored != dead_nom
                else dead_load_bite_mm
            ),
            'wind_usable_bite_mm': wind_usable_at_floor,
            'dead_load_usable_bite_mm': dead_usable_at_floor,
            'wind_actual_thickness_mm': table.get(wind_nom_floored) if wind_nom_floored is not None else None,
            'dead_load_actual_thickness_mm': table.get(dead_nom_floored) if dead_nom_floored is not None else None,
        }

    results = {}

    for (glass_type, glass_subtype) in SUBTYPES:
        subtype_key = (glass_type, glass_subtype)
        category_bite = bite_nominal_by_category[glass_type]
        wind_bite_nominal_mm = category_bite['wind_bite_nominal_mm']
        dead_load_bite_nominal_mm = category_bite['dead_load_bite_nominal_mm']

        # --- broad-category short circuit (both bite lookups failed) ---
        if wind_bite_nominal_mm is None and dead_load_bite_nominal_mm is None:
            results[subtype_key] = make_pathway4_result(
                status='BITE_NO_COMPLIANT_THICKNESS', subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'Required bite (wind {round(wind_bite_mm, 3)}mm, dead load '
                        f'{round(dead_load_bite_mm, 3)}mm) exceeds all available '
                        f'{glass_type} thicknesses.',
                wind_bite_mm=wind_bite_mm,
                dead_load_bite_mm=dead_load_bite_mm,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                bite_trace=[{
                    'check': 'BITE', 'category': glass_type, 'result': 'FAIL',
                    'required_bite_mm': max(wind_bite_mm, dead_load_bite_mm),
                }],
            )
            continue

        # --- Silicone-bite transparency fields (this session), same shape
        # as pathway3.py's equivalent block - looked up once per subtype's
        # broad category and reused across every remaining return path. ---
        bite_transparency_kwargs = dict(
            dead_load_required_bite_raw_mm=dead_load_bite_mm,
            dead_load_required_bite_floored_mm=category_bite['dead_load_required_bite_floored_mm'],
            wind_required_bite_raw_mm=wind_bite_mm,
            wind_required_bite_floored_mm=category_bite['wind_required_bite_floored_mm'],
            dead_load_usable_bite_mm=category_bite['dead_load_usable_bite_mm'],
            wind_usable_bite_mm=category_bite['wind_usable_bite_mm'],
            dead_load_actual_thickness_mm=category_bite['dead_load_actual_thickness_mm'],
            wind_actual_thickness_mm=category_bite['wind_actual_thickness_mm'],
            deduction_mm=EDGE_POLISH_DEDUCTION_MM, deduction_type='edge_polish',
        )

        # --- ULS/SLS wind bending check on the glass pane itself (new this
        # session) - independent of the silicone joint's own bite sizing
        # above (Section 6.1/7.6 independence principle). safety_glass_
        # required=False: Table 5.1 is computed independently below, same
        # reason pathway3.py never passes it into check_glass_type() either. ---
        wind_result = check_glass_type(
            df, glass_type, glass_subtype, height_mm, width_mm,
            support_condition='4-edge', span_dimension='height',
            wind_pressure_uls=wind_pressure_uls_kpa, wind_pressure_sls=wind_pressure_sls_kpa,
            glazing_config='single', safety_glass_required=False,
            bushfire_required=False,
        )

        if wind_result['status'] != 'PASS':
            status = 'WIND_NO_COMPLIANT_THICKNESS' if wind_result['status'] == 'NO_COMPLIANT_THICKNESS' else 'ERROR'
            results[subtype_key] = make_pathway4_result(
                status=status, subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=wind_result['message'],
                dead_load_bite_nominal_mm=dead_load_bite_nominal_mm,
                wind_bite_nominal_mm=wind_bite_nominal_mm,
                wind_bite_mm=wind_bite_mm,
                dead_load_bite_mm=dead_load_bite_mm,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
                **bite_transparency_kwargs,
            )
            continue

        uls_thickness_mm = wind_result['uls_minimum_thickness_mm']
        sls_thickness_mm = wind_result['sls_minimum_thickness_mm']

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
                dead_load_bite_nominal_mm=dead_load_bite_nominal_mm,
                wind_bite_nominal_mm=wind_bite_nominal_mm,
                uls_thickness_mm=uls_thickness_mm,
                sls_thickness_mm=sls_thickness_mm,
                wind_bite_mm=wind_bite_mm,
                dead_load_bite_mm=dead_load_bite_mm,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
                table_5_1_trace=table_5_1_trace,
                **bite_transparency_kwargs,
            )
            continue

        # --- governing thickness: max() across all active criteria
        # (Section 6.1/7.6) - dead load bite and wind bite are always
        # active; ULS/SLS are always active (this session's fix); Table 5.1
        # only when the toggle is ON and the search passed. ---
        criteria = {
            'dead_load_bite': dead_load_bite_nominal_mm,
            'wind_bite': wind_bite_nominal_mm,
            'uls': uls_thickness_mm,
            'sls': sls_thickness_mm,
        }
        if table_5_1_thickness_mm is not None:
            criteria['table_5_1'] = table_5_1_thickness_mm

        governing_criterion = max(criteria, key=lambda k: criteria[k])
        governing_thickness_mm = criteria[governing_criterion]

        results[subtype_key] = make_pathway4_result(
            status='PASS' if table_5_1_status is None else table_5_1_status,
            subtype=subtype_key, glass_type=glass_type, glass_subtype=glass_subtype,
            message='PASS',
            governing_thickness_mm=governing_thickness_mm,
            governing_criterion=governing_criterion,
            dead_load_bite_nominal_mm=dead_load_bite_nominal_mm,
            wind_bite_nominal_mm=wind_bite_nominal_mm,
            uls_thickness_mm=uls_thickness_mm,
            sls_thickness_mm=sls_thickness_mm,
            wind_bite_mm=wind_bite_mm,
            dead_load_bite_mm=dead_load_bite_mm,
            table_5_1_thickness_mm=table_5_1_thickness_mm,
            panel_area_m2=panel_area_m2,
            safety_glass_required=safety_glass_required,
            wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
            table_5_1_trace=table_5_1_trace,
            **bite_transparency_kwargs,
        )

    return results
