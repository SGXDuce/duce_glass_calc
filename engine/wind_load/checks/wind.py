from engine.wind_load.constants import (
    GLASS_TYPE_THICKNESSES, SAFETY_GLASS_INELIGIBLE,
    TABLE_5_3_GLASS_TYPE_MAP, UNFRAMED_EDGE_JOINT_COUNTS,
    TABLE_5_3_SAFETY_GLASS_INELIGIBLE,
)
from engine.wind_load.formulas import (
    get_ar_interpolation_bounds, calculate_ar, calculate_span, get_kpane_for_config,
    get_c1_factor, get_uls_k_values, get_sls_k_values,
    calculate_uls_capacity, calculate_sls_capacity, calculate_kpane,
    check_bal_eligibility, get_bal_min_thickness, get_safety_glass_max_area
)
from engine.shared.data_loader import get_nominal_thickness
from engine.shared.results import make_mode1_result, make_mode2_result
from engine.shared.table_5_3 import check_table_5_3


def check_table_5_3_thickness(df_5_3, glass_type, glass_subtype, height_mm, width_mm,
                              unframed_edge_condition, thickness_list):
    """
    Runs an independent AS 1288 Table 5.3 search for one glass type, for
    2-edge/3-edge support conditions only (Table 5.3 replaces Table 5.1
    entirely in this branch - Section 14.2 of the project summary).

    check_table_5_3() itself is a single row-band lookup, not a
    per-thickness pass/fail test - it directly returns the minimum nominal
    thickness required for a given height/width/joint-count combination.
    This function still performs its own independent scan of the glass
    type's full available thickness range, ascending from thinnest (per
    Section 7.6 - not starting from any other check's result), rather than
    assuming the raw Table 5.3 figure is itself a size this glass type
    actually offers.

    Returns a dict:
        'status': 'COMPLIANT' (a stocked nominal thickness satisfies Table 5.3),
                  'NON_COMPLIANT' (no stocked thickness satisfies it, OR no
                  Table 5.3 row satisfies the width/joint-count constraints
                  for this height band),
                  'NOT_PERMITTED' (this glass type is not permitted at all at
                  this height under Table 5.3 - a hard gate, not solvable by
                  choosing a thicker glass; see Section 14.2, "Table 5.3 can
                  act as a gate")
        'minimum_thickness_mm': the thinnest compliant nominal thickness, or None
        'trace': list of per-candidate results (COMPLIANT path), or a single
                 entry describing the row-level result (NON_COMPLIANT /
                 NOT_PERMITTED path, since there's nothing to iterate over)
        'message': human-readable explanation
    """
    glass_type_5_3 = TABLE_5_3_GLASS_TYPE_MAP.get((glass_type, glass_subtype))
    if glass_type_5_3 is None:
        return {
            'status': 'NOT_PERMITTED',
            'minimum_thickness_mm': None,
            'trace': [],
            'message': f'{glass_type} {glass_subtype} has no Table 5.3 mapping.',
        }

    num_butt_joints = UNFRAMED_EDGE_JOINT_COUNTS[unframed_edge_condition]
    height_m = height_mm / 1000.0
    width_m = width_mm / 1000.0

    row_result = check_table_5_3(height_m, glass_type_5_3, width_m, num_butt_joints, df_5_3)

    if row_result['status'] in ('NOT_PERMITTED', 'NON_COMPLIANT'):
        return {
            'status': row_result['status'],
            'minimum_thickness_mm': None,
            'trace': [{
                'check': 'TABLE_5_3',
                'height_m': height_m, 'width_m': width_m,
                'num_butt_joints': num_butt_joints,
                'result': row_result['status'],
                'message': row_result['message'],
            }],
            'message': row_result['message'],
        }

    # COMPLIANT row found - scan this glass type's own available thickness
    # list, ascending, for the first nominal size that actually satisfies
    # the required minimum (mirrors the ULS/SLS/SG search pattern).
    required_min_mm = row_result['min_thickness_mm']
    trace = []
    for thickness in thickness_list:
        result = 'PASS' if thickness >= required_min_mm else 'FAIL'
        trace.append({
            'check': 'TABLE_5_3',
            'thickness': thickness,
            'required_min_thickness_mm': required_min_mm,
            'result': result,
        })
        if result == 'PASS':
            return {
                'status': 'COMPLIANT',
                'minimum_thickness_mm': thickness,
                'trace': trace,
                'message': row_result['message'],
            }

    return {
        'status': 'NON_COMPLIANT',
        'minimum_thickness_mm': None,
        'trace': trace,
        'message': f'No available nominal thickness for {glass_type} {glass_subtype} '
                   f'satisfies the Table 5.3 minimum of {required_min_mm}mm.',
    }


def check_glass_type(df, glass_type, glass_subtype, height_mm, width_mm,
                     support_condition, span_dimension,
                     wind_pressure_uls, wind_pressure_sls,
                     glazing_config, safety_glass_required=False,
                     bushfire_required=False, bal_level=None,
                     element_type=None, unframed_edge_condition=None,
                     df_5_3=None):
    """
    Runs ULS, SLS, and optionally Safety Glass Area Check for one glass type.
    Finds the minimum compliant thickness across all active checks.

    unframed_edge_condition: None (default - Table 5.3 does not apply),
    '2-edge', or '3-edge'. Independent of support_condition, which the wind
    formulas only ever see as '4-edge'/'2-edge' (3-edge is treated as
    2-edge for wind bending - Section 14.2). When set AND safety_glass_required
    is True, Table 5.3 runs instead of the Table 5.1 Safety Glass Area Check
    above, and its result enters the governing max() alongside ULS/SLS - both
    human impact tables only run when safety glass is required. df_5_3 (the
    loaded Table 5.3 dataframe) must be supplied whenever unframed_edge_condition
    is set, regardless of safety_glass_required.

    Returns a dict describing the full result for that glass type.
    """

    actual_ar = calculate_ar(height_mm, width_mm)
    span      = calculate_span(height_mm, width_mm, support_condition, span_dimension)
    panel_area = (height_mm * width_mm) / 1_000_000

    # Determine AR interpolation bounds for table lookup
    if support_condition == '4-edge':
        ar_bounds = get_ar_interpolation_bounds(actual_ar)
    else:
        ar_bounds = None

    # Get k_pane for this glazing configuration (equal thickness assumption)
    k_pane = get_kpane_for_config(glazing_config)

    # Get c1 factor for Laminated variants - divides wind pressures
    c1 = get_c1_factor(glass_type, glass_subtype)

    # Apply k_pane and c1 to get effective pressures
    effective_uls = (k_pane * wind_pressure_uls) / c1
    effective_sls = (k_pane * wind_pressure_sls) / c1

    thickness_list = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype))
    if thickness_list is None:
        return make_mode1_result(
            status='ERROR',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message=f'Unknown glass type: {glass_type} {glass_subtype}',
            glazing_config=glazing_config, k_pane=k_pane,
        )

    # --- Safety glass eligibility check (Table 5.1, 4-edge only) ---
    if safety_glass_required and support_condition == '4-edge':
        if (glass_type, glass_subtype) in SAFETY_GLASS_INELIGIBLE:
            return make_mode1_result(
                status='SG_INELIGIBLE',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass and cannot be used when safety glass '
                        f'is required.',
                glazing_config=glazing_config, k_pane=k_pane,
                safety_glass_required=safety_glass_required,
            )

    # --- Safety glass eligibility check (Table 5.3, 2-edge/3-edge only) ---
    # A separate rule from the Table 5.1 check above - Table 5.3 replaces
    # Table 5.1 entirely in this branch (Section 14.2). Frontend hook: when
    # Pathway 2's UI is built, its safety-glass toggle must filter the
    # glass-type checkbox list against TABLE_5_3_SAFETY_GLASS_INELIGIBLE
    # (not SAFETY_GLASS_INELIGIBLE) whenever the 2-edge/3-edge selector is
    # active - same two-place filtering discipline as Section 6.2.
    if safety_glass_required and unframed_edge_condition in ('2-edge', '3-edge'):
        if (glass_type, glass_subtype) in TABLE_5_3_SAFETY_GLASS_INELIGIBLE:
            return make_mode1_result(
                status='SG_INELIGIBLE',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass under AS 1288 Table 5.3 and cannot be '
                        f'used when safety glass is required.',
                glazing_config=glazing_config, k_pane=k_pane,
                safety_glass_required=safety_glass_required,
            )

    # --- Bushfire (BAL) eligibility check ---
    if bushfire_required and bal_level and element_type:
        if not check_bal_eligibility(bal_level, element_type, glass_type, glass_subtype):
            return make_mode1_result(
                status='BAL_INELIGIBLE',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'{glass_type} {glass_subtype} is not permitted '
                        f'under BAL-{bal_level} for a {element_type.lower()}.',
                glazing_config=glazing_config, k_pane=k_pane,
                bushfire_required=bushfire_required,
                bal_level=bal_level, bal_element_type=element_type,
            )

    # --- STEP 1: ULS CHECK ---
    uls_minimum_thickness = None
    uls_trace = []
    sls_k_values = get_sls_k_values(df, support_condition, ar_bounds)

    for thickness in thickness_list:
        k_values = get_uls_k_values(
            df, glass_type, glass_subtype,
            thickness, support_condition, ar_bounds
        )
        if k_values is None:
            continue

        B_uls = calculate_uls_capacity(
            k_values['k1'], k_values['k2'],
            k_values['k3'], k_values['k4'],
            effective_uls
        )

        result = 'PASS' if span <= B_uls else 'FAIL'
        uls_trace.append({
            'check': 'ULS',
            'thickness': thickness,
            'k1': k_values['k1'], 'k2': k_values['k2'],
            'k3': k_values['k3'], 'k4': k_values['k4'],
            'pressure_kpa': round(effective_uls, 4),
            'B': round(B_uls, 2),
            'span': span,
            'result': result
        })

        if span <= B_uls:
            uls_minimum_thickness = thickness
            break

    if uls_minimum_thickness is None:
        return make_mode1_result(
            status='NO_COMPLIANT_THICKNESS',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='No compliant thickness available under the applied '
                    'ULS wind pressure.',
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # --- STEP 2: SLS CHECK ---
    if sls_k_values is None:
        return make_mode1_result(
            status='ERROR',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='Could not find SLS k values in table.',
            uls_minimum_thickness_mm=uls_minimum_thickness,
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # SLS now searches its OWN full thickness range independently of ULS,
    # rather than starting from the ULS minimum. This reports SLS's true
    # minimum thickness on its own terms. The governing thickness (highest
    # of all checks) is still calculated correctly further below.
    sls_minimum_thickness = None
    sls_trace = []

    for thickness in thickness_list:
        B_sls = calculate_sls_capacity(
            sls_k_values['k1'], sls_k_values['k2'],
            sls_k_values['k3'], sls_k_values['k4'],
            thickness,
            effective_sls
        )

        result = 'PASS' if span <= B_sls else 'FAIL'
        sls_trace.append({
            'check': 'SLS',
            'thickness': thickness,
            'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
            'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
            'pressure_kpa': round(effective_sls, 4),
            'B': round(B_sls, 2),
            'span': span,
            'result': result
        })

        if span <= B_sls:
            sls_minimum_thickness = thickness
            break

    if sls_minimum_thickness is None:
        return make_mode1_result(
            status='NO_COMPLIANT_THICKNESS',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='No compliant thickness available under the applied '
                    'SLS wind pressure.',
            uls_minimum_thickness_mm=uls_minimum_thickness,
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace, sls_trace=sls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # --- STEP 3: SAFETY GLASS AREA CHECK ---
    sg_minimum_thickness = None
    sg_flag = None

    if safety_glass_required and support_condition == '4-edge':
        # Safety Glass now searches its OWN full thickness range
        # independently, reporting its true minimum on its own terms,
        # rather than starting from the wind load governing thickness.
        sg_trace = []

        for thickness in thickness_list:
            max_area = get_safety_glass_max_area(
                glass_type, glass_subtype, thickness
            )

            if max_area is None:
                continue
            elif panel_area <= max_area:
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': max_area,
                    'actual_area': round(panel_area, 4),
                    'result': 'PASS'
                })
                sg_minimum_thickness = thickness
                break
            else:
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': max_area,
                    'actual_area': round(panel_area, 4),
                    'result': 'FAIL'
                })

        if sg_minimum_thickness is None:
            return make_mode1_result(
                status='NO_COMPLIANT_THICKNESS',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message='No compliant thickness available under the Safety '
                        'Glass Area Check (AS 1288 Table 5.1).',
                uls_minimum_thickness_mm=uls_minimum_thickness,
                sls_minimum_thickness_mm=sls_minimum_thickness,
                glazing_config=glazing_config, k_pane=k_pane,
                uls_trace=uls_trace, sls_trace=sls_trace, sg_trace=sg_trace,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
            )

    # --- STEP 4: TABLE 5.3 CHECK (2-edge/3-edge only) ---
    # Replaces the Table 5.1 Safety Glass Area Check above entirely for
    # this branch (Section 14.2) - the two never both run for the same
    # glass type, since support_condition == '4-edge' gates Table 5.1 and
    # unframed_edge_condition in ('2-edge', '3-edge') gates this. Both
    # human-impact tables (5.1 and 5.3) are additionally gated on the
    # safety_glass toggle, per the product decision that human impact
    # checks only run when safety glass is required.
    table_5_3_minimum_thickness = None
    table_5_3_trace = []

    if safety_glass_required and unframed_edge_condition in ('2-edge', '3-edge'):
        if df_5_3 is None:
            return make_mode1_result(
                status='ERROR',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message='Table 5.3 data was not supplied for a 2-edge/3-edge calculation.',
                uls_minimum_thickness_mm=uls_minimum_thickness,
                sls_minimum_thickness_mm=sls_minimum_thickness,
                glazing_config=glazing_config, k_pane=k_pane,
                uls_trace=uls_trace, sls_trace=sls_trace,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
            )

        table_5_3_result = check_table_5_3_thickness(
            df_5_3, glass_type, glass_subtype, height_mm, width_mm,
            unframed_edge_condition, thickness_list
        )
        table_5_3_trace = table_5_3_result['trace']

        if table_5_3_result['status'] == 'NOT_PERMITTED':
            # A hard gate (Section 14.2) - this glass type/height/width/
            # joint-count combination is never permitted under Table 5.3,
            # no matter how thick the glass is. Distinct status, same
            # dedicated-status pattern as SG_INELIGIBLE/BAL_INELIGIBLE.
            return make_mode1_result(
                status='TABLE_5_3_NOT_PERMITTED',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=table_5_3_result['message'],
                uls_minimum_thickness_mm=uls_minimum_thickness,
                sls_minimum_thickness_mm=sls_minimum_thickness,
                glazing_config=glazing_config, k_pane=k_pane,
                uls_trace=uls_trace, sls_trace=sls_trace,
                table_5_3_trace=table_5_3_trace,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
            )

        if table_5_3_result['status'] == 'NON_COMPLIANT':
            return make_mode1_result(
                status='NO_COMPLIANT_THICKNESS',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=table_5_3_result['message'],
                uls_minimum_thickness_mm=uls_minimum_thickness,
                sls_minimum_thickness_mm=sls_minimum_thickness,
                glazing_config=glazing_config, k_pane=k_pane,
                uls_trace=uls_trace, sls_trace=sls_trace,
                table_5_3_trace=table_5_3_trace,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
            )

        table_5_3_minimum_thickness = table_5_3_result['minimum_thickness_mm']

    # --- Bushfire (BAL) minimum thickness check ---
    # This governs if higher than the wind load / safety glass result,
    # following the same "highest of all active checks" pattern.
    bal_minimum_thickness = None
    if bushfire_required and bal_level and element_type:
        bal_minimum_thickness = get_bal_min_thickness(bal_level, element_type)

    candidates_with_bal = [uls_minimum_thickness, sls_minimum_thickness]
    if sg_minimum_thickness is not None:
        candidates_with_bal.append(sg_minimum_thickness)
    if bal_minimum_thickness is not None:
        candidates_with_bal.append(bal_minimum_thickness)
    if table_5_3_minimum_thickness is not None:
        candidates_with_bal.append(table_5_3_minimum_thickness)
    final_thickness = max(candidates_with_bal)

    return make_mode1_result(
        status='PASS',
        glass_type=glass_type, glass_subtype=glass_subtype,
        message='PASS',
        minimum_thickness_mm=final_thickness,
        uls_minimum_thickness_mm=uls_minimum_thickness,
        sls_minimum_thickness_mm=sls_minimum_thickness,
        sg_minimum_thickness_mm=sg_minimum_thickness,
        bal_minimum_thickness_mm=bal_minimum_thickness,
        table_5_3_minimum_thickness_mm=table_5_3_minimum_thickness,
        bal_level=bal_level if bushfire_required else None,
        bal_element_type=element_type if bushfire_required else None,
        glazing_config=glazing_config,
        k_pane=k_pane,
        sg_flag=sg_flag,
        panel_area_m2=round(panel_area, 4),
        safety_glass_required=safety_glass_required,
        bushfire_required=bushfire_required,
        uls_trace=uls_trace,
        sls_trace=sls_trace,
        sg_trace=sg_trace if safety_glass_required and support_condition == '4-edge' else [],
        table_5_3_trace=table_5_3_trace,
    )


def check_pane_compliance(df, df_nominal, glass_type, glass_subtype,
                          actual_thickness_mm, all_actual_thicknesses,
                          span, height_mm, width_mm,
                          ar_bounds, support_condition,
                          wind_pressure_uls, wind_pressure_sls,
                          pane_label, glazing_config,
                          safety_glass_required=False,
                          bushfire_required=False, bal_level=None,
                          element_type=None, unframed_edge_condition=None,
                          df_5_3=None):
    """
    Checks whether a single pane of known thickness passes ULS, SLS,
    and optionally Safety Glass Area Check.

    unframed_edge_condition: None (default - Table 5.3 does not apply),
    '2-edge', or '3-edge'. When set AND safety_glass_required is True, Table
    5.3 checks this pane's specific nominal thickness against the AS 1288
    row-band minimum instead of running the Table 5.1 Safety Glass Area Check
    (Section 14.2) - both human impact tables only run when safety glass is
    required. df_5_3 (the loaded Table 5.3 dataframe) must be supplied
    whenever unframed_edge_condition is set, regardless of safety_glass_required.

    KNOWN SCOPE GAP: the "next compliant thickness" search below re-verifies
    ULS/SLS/Safety-Glass per candidate but does NOT yet re-verify Table 5.3
    per candidate - a recommended next_compliant_thickness_mm could in
    theory still fail Table 5.3. Flagged rather than silently assumed
    correct; revisit when Pathway 2's UI is built.

    Returns a dict describing the full compliance result for this pane.
    """

    panel_area = (height_mm * width_mm) / 1_000_000

    # --- Nominal thickness lookup ---
    nominal_thickness = get_nominal_thickness(
        df_nominal, glass_type, actual_thickness_mm
    )

    if nominal_thickness is None:
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            message=f'Actual thickness {actual_thickness_mm}mm is too thin '
                    f'to classify under AS 1288 Table 4.1.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # Check that this nominal thickness is actually offered for this glass type
    available_thicknesses = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype), [])
    if available_thicknesses and nominal_thickness < min(available_thicknesses):
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            message=f'No DTS solution for glass selection of '
                    f'{glass_type} {glass_subtype} of thickness '
                    f'{nominal_thickness}mm available.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # Monolithic Annealed minimum nominal thickness is 4mm
    if glass_type == 'Monolithic' and glass_subtype == 'Annealed' and \
       nominal_thickness == 3:
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            message='Minimum thickness allowed by tool: 4mm. '
                    'Monolithic Annealed glass below 4mm nominal '
                    'is not permitted.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # --- Safety glass eligibility (Table 5.1, 4-edge only) ---
    if safety_glass_required and support_condition == '4-edge':
        if (glass_type, glass_subtype) in SAFETY_GLASS_INELIGIBLE:
            return make_mode2_result(
                status='SG_INELIGIBLE',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass and cannot be used when safety glass '
                        f'is required.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
            )

    # --- Safety glass eligibility (Table 5.3, 2-edge/3-edge only) ---
    # A separate rule from the Table 5.1 check above - see the matching
    # comment in check_glass_type(). Frontend hook: same as noted there,
    # Pathway 2's Mode 2 pane dropdown must filter against
    # TABLE_5_3_SAFETY_GLASS_INELIGIBLE, not SAFETY_GLASS_INELIGIBLE.
    if safety_glass_required and unframed_edge_condition in ('2-edge', '3-edge'):
        if (glass_type, glass_subtype) in TABLE_5_3_SAFETY_GLASS_INELIGIBLE:
            return make_mode2_result(
                status='SG_INELIGIBLE',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass under AS 1288 Table 5.3 and cannot be '
                        f'used when safety glass is required.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
            )

    # --- Bushfire (BAL) eligibility ---
    # Only applies to the Outer pane (or the only pane, if Single glazed) -
    # Inner and Middle panes are not subject to bushfire requirements
    is_bushfire_pane = pane_label in ('Outer', 'Single')

    if bushfire_required and is_bushfire_pane and bal_level and element_type:
        if not check_bal_eligibility(bal_level, element_type, glass_type, glass_subtype):
            return make_mode2_result(
                status='BAL_INELIGIBLE',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=f'{glass_type} {glass_subtype} is not permitted '
                        f'under BAL-{bal_level} for a {element_type.lower()}.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
                bal_level=bal_level, bal_element_type=element_type,
            )

    # --- Table 5.3 check (2-edge/3-edge only) ---
    # Replaces the Table 5.1 Safety Glass Area Check for this branch
    # (Section 14.2). Unlike Mode 1's search, Mode 2 already knows the
    # pane's nominal thickness - this checks that specific thickness
    # against the row-band minimum rather than searching for one. Gated
    # on safety_glass_required, same as Table 5.1 - both human impact
    # tables only run when safety glass is toggled on.
    table_5_3_status = None
    table_5_3_min_thickness = None
    table_5_3_trace = []

    if safety_glass_required and unframed_edge_condition in ('2-edge', '3-edge'):
        if df_5_3 is None:
            return make_mode2_result(
                status='ERROR',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message='Table 5.3 data was not supplied for a 2-edge/3-edge calculation.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
            )

        glass_type_5_3 = TABLE_5_3_GLASS_TYPE_MAP.get((glass_type, glass_subtype))
        if glass_type_5_3 is None:
            row_result = {
                'status': 'NOT_PERMITTED',
                'min_thickness_mm': None,
                'message': f'{glass_type} {glass_subtype} has no Table 5.3 mapping.',
            }
        else:
            num_butt_joints = UNFRAMED_EDGE_JOINT_COUNTS[unframed_edge_condition]
            row_result = check_table_5_3(
                height_mm / 1000.0, glass_type_5_3, width_mm / 1000.0,
                num_butt_joints, df_5_3
            )

        table_5_3_trace = [{
            'check': 'TABLE_5_3',
            'nominal_thickness': nominal_thickness,
            'required_min_thickness_mm': row_result.get('min_thickness_mm'),
            'result': row_result['status'],
            'message': row_result['message'],
        }]

        if row_result['status'] == 'NOT_PERMITTED':
            # A hard gate (Section 14.2), same dedicated-status pattern as
            # SG_INELIGIBLE/BAL_INELIGIBLE - not solvable by a thicker pane.
            return make_mode2_result(
                status='TABLE_5_3_NOT_PERMITTED',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=row_result['message'],
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                table_5_3_trace=table_5_3_trace,
            )

        if row_result['status'] == 'NON_COMPLIANT':
            table_5_3_status = 'FAIL'
        else:
            table_5_3_min_thickness = row_result['min_thickness_mm']

            # If no stocked nominal thickness for this glass type reaches
            # the Table 5.3 minimum, no candidate the next-compliant search
            # could try would ever pass either - this is a genuine
            # NO_COMPLIANT_THICKNESS case (Section 7.6/Mode 1's existing
            # pattern), not just this pane's specific thickness failing.
            available_thicknesses_5_3 = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype), [])
            if available_thicknesses_5_3 and max(available_thicknesses_5_3) < table_5_3_min_thickness:
                return make_mode2_result(
                    status='NO_COMPLIANT_THICKNESS',
                    pane_label=pane_label,
                    glass_type=glass_type, glass_subtype=glass_subtype,
                    actual_thickness_mm=actual_thickness_mm,
                    nominal_thickness_mm=nominal_thickness,
                    message=f'No available nominal thickness for {glass_type} '
                            f'{glass_subtype} satisfies the Table 5.3 minimum '
                            f'of {table_5_3_min_thickness}mm.',
                    span_mm=span,
                    panel_area_m2=round(panel_area, 4),
                    safety_glass_required=safety_glass_required,
                    table_5_3_trace=table_5_3_trace,
                )

            table_5_3_status = 'PASS' if nominal_thickness >= table_5_3_min_thickness else 'FAIL'

    # --- k_pane calculation ---
    k_pane = calculate_kpane(actual_thickness_mm, all_actual_thicknesses)

    # --- c1 factor ---
    c1 = get_c1_factor(glass_type, glass_subtype)

    # --- Effective pressures ---
    effective_uls = (k_pane * wind_pressure_uls) / c1
    effective_sls = (k_pane * wind_pressure_sls) / c1

    # --- ULS k values lookup ---
    k_values = get_uls_k_values(
        df, glass_type, glass_subtype,
        nominal_thickness, support_condition, ar_bounds
    )

    if k_values is None:
        return make_mode2_result(
            status='ERROR',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            k_pane=k_pane,
            message=f'No wind load data available for '
                    f'{glass_type} {glass_subtype} at {nominal_thickness}mm '
                    f'nominal thickness. This thickness is not offered for '
                    f'this glass type.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    sls_k_values = get_sls_k_values(df, support_condition, ar_bounds)
    if sls_k_values is None:
        return make_mode2_result(
            status='ERROR',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            k_pane=k_pane,
            message='Could not find SLS k values in table.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # --- ULS and SLS capacities ---
    B_uls = calculate_uls_capacity(
        k_values['k1'], k_values['k2'],
        k_values['k3'], k_values['k4'],
        effective_uls
    )

    uls_trace = [{
        'check': 'ULS',
        'thickness': nominal_thickness,
        'k1': k_values['k1'], 'k2': k_values['k2'],
        'k3': k_values['k3'], 'k4': k_values['k4'],
        'pressure_kpa': round(effective_uls, 4),
        'B': round(B_uls, 2),
        'span': span,
        'result': 'PASS' if span <= B_uls else 'FAIL'
    }]

    B_sls = calculate_sls_capacity(
        sls_k_values['k1'], sls_k_values['k2'],
        sls_k_values['k3'], sls_k_values['k4'],
        nominal_thickness, effective_sls
    )

    sls_trace = [{
        'check': 'SLS',
        'thickness': nominal_thickness,
        'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
        'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
        'pressure_kpa': round(effective_sls, 4),
        'B': round(B_sls, 2),
        'span': span,
        'result': 'PASS' if span <= B_sls else 'FAIL'
    }]

    uls_status = 'PASS' if span <= B_uls else 'FAIL'
    sls_status = 'PASS' if span <= B_sls else 'FAIL'

    # --- Safety Glass Area Check ---
    sg_status = None
    sg_max_area = None
    sg_flag = None
    sg_trace = []

    if safety_glass_required and support_condition == '4-edge':
        max_area = get_safety_glass_max_area(
            glass_type, glass_subtype, nominal_thickness
        )
        if max_area is None:
            sg_status = 'N/A'
        elif panel_area <= max_area:
            sg_status = 'PASS'
            sg_max_area = max_area
        else:
            sg_status = 'FAIL'
            sg_max_area = max_area

    # --- Find next compliant thickness if any check fails ---
    thickness_list = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype), [])
    next_compliant       = None
    next_compliant_trace = []

    any_fail = (
        uls_status == 'FAIL' or
        sls_status == 'FAIL' or
        sg_status == 'FAIL' or
        table_5_3_status == 'FAIL'
    )

    if any_fail:
        uls_confirmed_passing = False

        for candidate in thickness_list:
            if candidate <= nominal_thickness:
                continue

            candidate_trace = {'thickness': candidate, 'checks': []}

            # ULS check
            ck = get_uls_k_values(
                df, glass_type, glass_subtype,
                candidate, support_condition, ar_bounds
            )
            if ck is None:
                continue

            if uls_confirmed_passing:
                # A thinner candidate already passed ULS — any thicker
                # glass is guaranteed to also pass, since allowable span
                # only increases with thickness. Skip the recalculation
                # and go straight to SLS.
                uls_result = 'PASS'
                candidate_trace['checks'].append({
                    'check':     'ULS',
                    'thickness': candidate,
                    'result':    'PASS',
                    'note':      'Confirmed passing at a thinner thickness; '
                                 'not re-checked (thicker glass always passes ULS).'
                })
            else:
                cB_uls     = calculate_uls_capacity(
                    ck['k1'], ck['k2'], ck['k3'], ck['k4'], effective_uls
                )
                uls_result = 'PASS' if span <= cB_uls else 'FAIL'
                candidate_trace['checks'].append({
                    'check':        'ULS',
                    'thickness':    candidate,
                    'k1': ck['k1'], 'k2': ck['k2'],
                    'k3': ck['k3'], 'k4': ck['k4'],
                    'pressure_kpa': round(effective_uls, 4),
                    'B':            round(cB_uls, 2),
                    'span':         span,
                    'result':       uls_result
                })
                if uls_result == 'PASS':
                    uls_confirmed_passing = True

            if uls_result == 'FAIL':
                candidate_trace['overall'] = 'FAIL'
                candidate_trace['fail_reason'] = 'ULS'
                next_compliant_trace.append(candidate_trace)
                continue

            # SLS check
            cB_sls     = calculate_sls_capacity(
                sls_k_values['k1'], sls_k_values['k2'],
                sls_k_values['k3'], sls_k_values['k4'],
                candidate, effective_sls
            )
            sls_result = 'PASS' if span <= cB_sls else 'FAIL'
            candidate_trace['checks'].append({
                'check':        'SLS',
                'thickness':    candidate,
                'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
                'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
                'pressure_kpa': round(effective_sls, 4),
                'B':            round(cB_sls, 2),
                'span':         span,
                'result':       sls_result
            })
            if sls_result == 'FAIL':
                candidate_trace['overall'] = 'FAIL'
                candidate_trace['fail_reason'] = 'SLS'
                next_compliant_trace.append(candidate_trace)
                continue

            # Table 5.3 check (2-edge/3-edge only) - table_5_3_min_thickness
            # is a fixed value from the row lookup above (height/width/joint
            # count don't change per candidate), so this is a per-candidate
            # comparison only, not a per-candidate recalculation. A None
            # value here means the row itself was NON_COMPLIANT (unsolvable
            # by any thickness), so every candidate fails it.
            if safety_glass_required and unframed_edge_condition in ('2-edge', '3-edge'):
                candidate_5_3_result = (
                    'PASS' if table_5_3_min_thickness is not None
                    and candidate >= table_5_3_min_thickness else 'FAIL'
                )
                candidate_trace['checks'].append({
                    'check':                    'TABLE_5_3',
                    'thickness':                candidate,
                    'required_min_thickness_mm': table_5_3_min_thickness,
                    'result':                   candidate_5_3_result
                })
                if candidate_5_3_result == 'FAIL':
                    candidate_trace['overall'] = 'FAIL'
                    # Distinguish the unsolvable-by-thickness row rejection
                    # (NON_COMPLIANT - width/joint-count, not thickness) from
                    # an ordinary too-thin candidate, so build_report() never
                    # implies a thicker candidate could fix a gate failure.
                    candidate_trace['fail_reason'] = (
                        'TABLE_5_3_GATE_FAIL' if table_5_3_min_thickness is None
                        else 'TABLE_5_3'
                    )
                    next_compliant_trace.append(candidate_trace)
                    continue

            # Safety Glass Area check
            if safety_glass_required and support_condition == '4-edge':
                cmax = get_safety_glass_max_area(
                    glass_type, glass_subtype, candidate
                )
                if cmax is None:
                    candidate_trace['overall'] = 'PASS'
                    candidate_trace['checks'].append({
                        'check':       'SG',
                        'thickness':   candidate,
                        'max_area':    None,
                        'actual_area': round(panel_area, 4),
                        'result':      'N/A'
                    })
                    next_compliant_trace.append(candidate_trace)
                    next_compliant = candidate
                    break
                sg_result = 'PASS' if panel_area <= cmax else 'FAIL'
                candidate_trace['checks'].append({
                    'check':       'SG',
                    'thickness':   candidate,
                    'max_area':    cmax,
                    'actual_area': round(panel_area, 4),
                    'result':      sg_result
                })
                if sg_result == 'FAIL':
                    candidate_trace['overall']     = 'FAIL'
                    candidate_trace['fail_reason'] = 'Safety Glass Area Check'
                    next_compliant_trace.append(candidate_trace)
                    continue

            candidate_trace['overall'] = 'PASS'
            next_compliant_trace.append(candidate_trace)
            next_compliant = candidate
            break

    # --- Bushfire (BAL) minimum thickness check ---
    # Only applies to the Outer/Single pane. Governs if higher than the
    # nominal thickness already determined by wind load / safety glass.
    bal_status = None
    bal_min_thickness = None
    if bushfire_required and is_bushfire_pane and bal_level and element_type:
        bal_min_thickness = get_bal_min_thickness(bal_level, element_type)
        if bal_min_thickness is not None:
            bal_status = 'PASS' if nominal_thickness >= bal_min_thickness else 'FAIL'

    # --- Overall status ---
    checks = [uls_status, sls_status]
    if sg_status not in (None, 'N/A'):
        checks.append(sg_status)
    if bal_status is not None:
        checks.append(bal_status)
    if table_5_3_status is not None:
        checks.append(table_5_3_status)

    overall_status = 'PASS' if all(c == 'PASS' for c in checks) else 'FAIL'

    return make_mode2_result(
        status=overall_status,
        pane_label=pane_label,
        glass_type=glass_type, glass_subtype=glass_subtype,
        actual_thickness_mm=actual_thickness_mm,
        nominal_thickness_mm=nominal_thickness,
        k_pane=k_pane,
        message=overall_status,
        effective_uls_pa=effective_uls,
        effective_sls_pa=effective_sls,
        B_uls_mm=B_uls, B_sls_mm=B_sls,
        span_mm=span,
        uls_status=uls_status, sls_status=sls_status,
        sg_status=sg_status,
        sg_max_area_m2=sg_max_area,
        sg_flag=sg_flag,
        panel_area_m2=round(panel_area, 4),
        next_compliant_thickness_mm=next_compliant,
        next_compliant_trace=next_compliant_trace,
        safety_glass_required=safety_glass_required,
        bal_status=bal_status,
        bal_min_thickness_mm=bal_min_thickness,
        bal_level=bal_level if (bushfire_required and is_bushfire_pane) else None,
        bal_element_type=element_type if (bushfire_required and is_bushfire_pane) else None,
        bushfire_required=bushfire_required,
        table_5_3_status=table_5_3_status,
        table_5_3_min_thickness_mm=table_5_3_min_thickness,
        uls_trace=uls_trace, sls_trace=sls_trace,
        sg_trace=sg_trace if safety_glass_required and support_condition == '4-edge' else [],
        table_5_3_trace=table_5_3_trace,
    )
