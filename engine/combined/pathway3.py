# AS 1288 Glass Thickness Calculator
# engine/combined/pathway3.py
#
# Pathway 3 (Branch 3, Section 14.3 / 12.13) - Faceted Structural Silicone
# (90 deg-160 deg). Combines the silicone bite engine, the wind-load engine's
# Mode 1 check, and the angle-appropriate human impact table into one
# server-side calculation per subtype. Not itself an engine - a thin
# orchestrator permitted to import from multiple engines (Section 13.1's one
# deliberate exception), since this sequencing logic has nowhere else
# correct to live.
#
# NOTE (found while building this, not in the original spec): check_glass_type()
# gates the Table 5.1 Safety Glass Area Check on support_condition == '4-edge'
# alone, independent of unframed_edge_condition. Every existing caller only
# ever passes unframed_edge_condition together with support_condition ==
# '2-edge', so Table 5.1 and Table 5.3 have never both been eligible to fire
# in the same call before now. Pathway 3's >90-160 deg branch is the first
# caller that needs support_condition == '4-edge' (bite makes the joint a
# structural edge, Section 14.3) together with a Table 5.3 selector - passing
# both into check_glass_type as-is would incorrectly run Table 5.1's area
# check too. To avoid that, this module never passes unframed_edge_condition
# into check_glass_type: wind ULS/SLS is always fetched with
# safety_glass_required=False, and human impact is computed independently
# below - reusing check_table_5_3_thickness() directly for Table 5.3 (already
# a standalone function), and a small local re-implementation of Table 5.1's
# search loop (mirroring check_glass_type's own STEP 3, reusing the shared
# get_safety_glass_max_area() formula) for the 90 deg case.

from engine.silicone_bite import run_bite_calculation
from engine.wind_load.checks.wind import check_glass_type, check_table_5_3_thickness
from engine.wind_load.formulas import get_safety_glass_max_area
from engine.wind_load.constants import (
    GLASS_TYPE_THICKNESSES,
    SAFETY_GLASS_INELIGIBLE,
    TABLE_5_3_SAFETY_GLASS_INELIGIBLE,
)
from engine.shared.data_loader import load_table_data
from engine.shared.table_5_3 import load_table_5_3
from engine.shared.results import make_pathway3_result

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
    Independent scan of this subtype's own thickness range, ascending, for
    the AS 1288 Table 5.1 Safety Glass Area Check - mirrors check_glass_type()'s
    STEP 3 loop exactly, reusing the shared get_safety_glass_max_area()
    formula. Re-implemented locally (rather than reusing check_glass_type()
    wholesale) because that function's Table 5.1 gate isn't isolatable from
    its Table 5.3 gate when support_condition == '4-edge' - see module
    docstring.
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


def run_pathway3_calculation(height_mm, width_1_mm, width_2_mm, angle_deg,
                             corner_or_general, joint_type,
                             wind_pressure_uls_kpa, wind_pressure_sls_kpa,
                             safety_glass_required, unframed_edge_condition=None,
                             csv_path=None, preloaded_df=None,
                             csv_path_5_3=None, preloaded_df_5_3=None):
    """
    Master function for Pathway 3 - Faceted Structural Silicone (90-160 deg).
    Runs one combined calculation per glass subtype (Section 12.13).

    corner_or_general: not used in any calculation here - wind_pressure_uls_kpa/
    wind_pressure_sls_kpa are already-resolved figures. Carried through purely
    as descriptive metadata for the result/report layer.

    Wind ULS/SLS and panel area both use governing_width_mm = max(width_1_mm,
    width_2_mm) - the same governing width the bite calculation uses (Section
    9/Appendix F convention: the larger of the two panel widths governs), so
    bite, wind, and human impact are all evaluated against the same
    conservative panel geometry.

    Glazing is assumed single (glazing_config='single') - Section 14.3 does
    not describe an IGU variant of the faceted branch. Bushfire is always
    disallowed (bushfire_required=False) per Section 14.3/14.5 item 1 - BAL
    requires fully framed glazing.

    unframed_edge_condition ('2-edge' or '3-edge'): required when
    safety_glass_required is True and 90 < angle_deg <= 160 (Table 5.3
    branch). Not used, and not required, for angle_deg == 90 (Table 5.1 has
    no joint-count concept) or when safety_glass_required is False.

    csv_path/preloaded_df, csv_path_5_3/preloaded_df_5_3: same
    preloaded-takes-precedence pattern as run_calculation() in
    engine/wind_load/__init__.py. df_5_3 is only loaded when needed (Table
    5.3 branch, toggle on).

    Returns a dict keyed by (glass_type, glass_subtype) tuples for all six
    subtypes, each value a make_pathway3_result() dict.
    """
    df = preloaded_df if preloaded_df is not None else load_table_data(csv_path)

    df_5_3 = None
    needs_table_5_3 = safety_glass_required and 90 < angle_deg <= 160
    if needs_table_5_3:
        if preloaded_df_5_3 is not None:
            df_5_3 = preloaded_df_5_3
        elif csv_path_5_3 is not None:
            df_5_3 = load_table_5_3(csv_path_5_3)

    governing_width_mm = max(width_1_mm, width_2_mm)
    panel_area_m2 = round((height_mm * governing_width_mm) / 1_000_000, 4)

    # One call, cached, reused for all six subtypes - run_bite_calculation()
    # has no glass_type parameter and always computes both categories
    # together (Section 12.13 step 1).
    bite_result = run_bite_calculation(
        width_1_mm=width_1_mm, width_2_mm=width_2_mm,
        angle_deg=angle_deg, wind_pressure_kpa=wind_pressure_uls_kpa,
        joint_type=joint_type,
    )

    results = {}

    for (glass_type, glass_subtype) in SUBTYPES:
        subtype_key = (glass_type, glass_subtype)

        # --- Bad-input short circuit (angle out of scope / bad joint_type) ---
        if bite_result['status'] in ('ANGLE_OUT_OF_RANGE', 'INVALID'):
            results[subtype_key] = make_pathway3_result(
                status='ERROR', subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=bite_result['message'],
                angle_deg=angle_deg, corner_or_general=corner_or_general,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                unframed_edge_condition=unframed_edge_condition,
            )
            continue

        # --- STEP 2: per-broad-category short circuit ---
        # NO_COMPLIANT_THICKNESS status only fires when BOTH categories fail
        # at once - category-level pass/fail must be read from
        # nominal_monolithic/nominal_laminated directly, not from status.
        bite_thickness_mm = bite_result[BITE_FIELD_FOR_CATEGORY[glass_type]]

        if bite_thickness_mm is None:
            results[subtype_key] = make_pathway3_result(
                status='BITE_NO_COMPLIANT_THICKNESS', subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'Required silicone bite ({round(bite_result["required_bite_mm"], 3)}mm) '
                        f'exceeds all available {glass_type} thicknesses.',
                angle_deg=angle_deg, corner_or_general=corner_or_general,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                unframed_edge_condition=unframed_edge_condition,
                bite_trace=[{
                    'check': 'BITE', 'category': glass_type, 'result': 'FAIL',
                    'required_bite_mm': bite_result['required_bite_mm'],
                }],
            )
            continue

        # --- STEP 3: wind ULS/SLS, independent of human impact ---
        wind_result = check_glass_type(
            df, glass_type, glass_subtype, height_mm, governing_width_mm,
            support_condition='4-edge', span_dimension='height',
            wind_pressure_uls=wind_pressure_uls_kpa, wind_pressure_sls=wind_pressure_sls_kpa,
            glazing_config='single', safety_glass_required=False,
            bushfire_required=False,
        )

        if wind_result['status'] != 'PASS':
            status = 'WIND_NO_COMPLIANT_THICKNESS' if wind_result['status'] == 'NO_COMPLIANT_THICKNESS' else 'ERROR'
            results[subtype_key] = make_pathway3_result(
                status=status, subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=wind_result['message'],
                bite_thickness_mm=bite_thickness_mm,
                angle_deg=angle_deg, corner_or_general=corner_or_general,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                unframed_edge_condition=unframed_edge_condition,
                wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
            )
            continue

        uls_thickness_mm = wind_result['uls_minimum_thickness_mm']
        sls_thickness_mm = wind_result['sls_minimum_thickness_mm']

        # --- STEP 4: angle-appropriate human impact check, gated on toggle ---
        human_impact_thickness_mm = None
        human_impact_table = None
        human_impact_trace = []
        human_impact_status = None  # None = not applicable / not run

        if safety_glass_required:
            thickness_list = GLASS_TYPE_THICKNESSES[subtype_key]

            if angle_deg == 90:
                human_impact_table = '5.1'
                table_5_1_result = _run_table_5_1_search(
                    glass_type, glass_subtype, panel_area_m2, thickness_list
                )
                human_impact_trace = table_5_1_result['trace']
                if table_5_1_result['status'] == 'INELIGIBLE':
                    human_impact_status = 'HUMAN_IMPACT_INELIGIBLE'
                elif table_5_1_result['status'] == 'NON_COMPLIANT':
                    human_impact_status = 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS'
                else:
                    human_impact_thickness_mm = table_5_1_result['minimum_thickness_mm']

            elif 90 < angle_deg <= 160:
                human_impact_table = '5.3'
                if subtype_key in TABLE_5_3_SAFETY_GLASS_INELIGIBLE:
                    human_impact_status = 'HUMAN_IMPACT_INELIGIBLE'
                    human_impact_trace = [{
                        'check': 'TABLE_5_3', 'result': 'INELIGIBLE',
                        'message': f'{glass_type} {glass_subtype} is not classified as '
                                   f'safety glass under AS 1288 Table 5.3.',
                    }]
                else:
                    table_5_3_result = check_table_5_3_thickness(
                        df_5_3, glass_type, glass_subtype, height_mm, governing_width_mm,
                        unframed_edge_condition, thickness_list,
                    )
                    human_impact_trace = table_5_3_result['trace']
                    if table_5_3_result['status'] == 'NOT_PERMITTED':
                        human_impact_status = 'HUMAN_IMPACT_NOT_PERMITTED'
                    elif table_5_3_result['status'] == 'NON_COMPLIANT':
                        human_impact_status = 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS'
                    else:
                        human_impact_thickness_mm = table_5_3_result['minimum_thickness_mm']

        if human_impact_status in ('HUMAN_IMPACT_NOT_PERMITTED', 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS'):
            results[subtype_key] = make_pathway3_result(
                status=human_impact_status, subtype=subtype_key,
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'No compliant configuration for {glass_type} {glass_subtype} '
                        f'under AS 1288 Table {human_impact_table}.',
                bite_thickness_mm=bite_thickness_mm,
                uls_thickness_mm=uls_thickness_mm, sls_thickness_mm=sls_thickness_mm,
                human_impact_table=human_impact_table,
                angle_deg=angle_deg, corner_or_general=corner_or_general,
                panel_area_m2=panel_area_m2,
                safety_glass_required=safety_glass_required,
                unframed_edge_condition=unframed_edge_condition,
                wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
                human_impact_trace=human_impact_trace,
            )
            continue

        # --- STEP 5: governing thickness ---
        candidates = [bite_thickness_mm, uls_thickness_mm, sls_thickness_mm]
        if human_impact_thickness_mm is not None:
            candidates.append(human_impact_thickness_mm)
        governing_thickness_mm = max(candidates)

        results[subtype_key] = make_pathway3_result(
            status='PASS' if human_impact_status is None else human_impact_status,
            subtype=subtype_key, glass_type=glass_type, glass_subtype=glass_subtype,
            message='PASS',
            governing_thickness_mm=governing_thickness_mm,
            bite_thickness_mm=bite_thickness_mm,
            uls_thickness_mm=uls_thickness_mm, sls_thickness_mm=sls_thickness_mm,
            human_impact_thickness_mm=human_impact_thickness_mm,
            human_impact_table=human_impact_table,
            angle_deg=angle_deg, corner_or_general=corner_or_general,
            panel_area_m2=panel_area_m2,
            safety_glass_required=safety_glass_required,
            unframed_edge_condition=unframed_edge_condition,
            wind_trace=wind_result['uls_trace'] + wind_result['sls_trace'],
            human_impact_trace=human_impact_trace,
        )

    return results
