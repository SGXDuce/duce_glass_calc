import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from constants import GLASS_TYPE_THICKNESSES, SAFETY_GLASS_INELIGIBLE
from formulas import (
    get_ar_interpolation_bounds, calculate_ar, calculate_span, get_kpane_for_config,
    get_c1_factor, get_uls_k_values, get_sls_k_values,
    calculate_uls_capacity, calculate_sls_capacity, calculate_kpane,
    check_bal_eligibility, get_bal_min_thickness, get_safety_glass_max_area
)
from data_loader import get_nominal_thickness
from results import make_mode1_result, make_mode2_result


def check_glass_type(df, glass_type, glass_subtype, height_mm, width_mm,
                     support_condition, span_dimension,
                     wind_pressure_uls, wind_pressure_sls,
                     glazing_config, safety_glass_required=False,
                     bushfire_required=False, bal_level=None,
                     element_type=None):
    """
    Runs ULS, SLS, and optionally Safety Glass Area Check for one glass type.
    Finds the minimum compliant thickness across all active checks.

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

    # --- Safety glass eligibility check ---
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

            if max_area == 'EXTRAPOLATE':
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': 'EXTRAPOLATE',
                    'actual_area': round(panel_area, 4),
                    'result': 'EXTRAPOLATE'
                })
                sg_flag = 'EXTRAPOLATE'
                sg_minimum_thickness = thickness
                break
            elif max_area is None:
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

        if sg_minimum_thickness is None and sg_flag != 'EXTRAPOLATE':
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
    )


def check_pane_compliance(df, df_nominal, glass_type, glass_subtype,
                          actual_thickness_mm, all_actual_thicknesses,
                          span, height_mm, width_mm,
                          ar_bounds, support_condition,
                          wind_pressure_uls, wind_pressure_sls,
                          pane_label, glazing_config,
                          safety_glass_required=False,
                          bushfire_required=False, bal_level=None,
                          element_type=None):
    """
    Checks whether a single pane of known thickness passes ULS, SLS,
    and optionally Safety Glass Area Check.

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

    # --- Safety glass eligibility ---
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
        if max_area == 'EXTRAPOLATE':
            sg_status = 'EXTRAPOLATE'
            sg_flag = 'EXTRAPOLATE'
        elif max_area is None:
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
        sg_status == 'FAIL'
    )

    if any_fail:
        uls_confirmed_passing = False

        for candidate in thickness_list:
            if candidate <= nominal_thickness:
                continue

            candidate_trace = {'thickness': candidate, 'checks': []}
            candidate_pass  = True

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

            # Safety Glass Area check
            if safety_glass_required and support_condition == '4-edge':
                cmax = get_safety_glass_max_area(
                    glass_type, glass_subtype, candidate
                )
                if cmax == 'EXTRAPOLATE' or cmax is None:
                    candidate_trace['overall'] = 'PASS'
                    candidate_trace['checks'].append({
                        'check':       'SG',
                        'thickness':   candidate,
                        'max_area':    'EXTRAPOLATE',
                        'actual_area': round(panel_area, 4),
                        'result':      'EXTRAPOLATE'
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
    if sg_status not in (None, 'N/A', 'EXTRAPOLATE'):
        checks.append(sg_status)
    if bal_status is not None:
        checks.append(bal_status)

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
        uls_trace=uls_trace, sls_trace=sls_trace,
        sg_trace=sg_trace if safety_glass_required and support_condition == '4-edge' else [],
    )
