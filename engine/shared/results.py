def make_mode1_result(status, glass_type=None, glass_subtype=None,
                      message=None, minimum_thickness_mm=None,
                      uls_minimum_thickness_mm=None,
                      sls_minimum_thickness_mm=None,
                      sg_minimum_thickness_mm=None,
                      bal_minimum_thickness_mm=None,
                      bal_level=None, bal_element_type=None,
                      glazing_config=None, k_pane=None,
                      annealed_area_flag=None, sg_flag=None,
                      panel_area_m2=None,
                      safety_glass_required=False,
                      bushfire_required=False,
                      uls_trace=None, sls_trace=None, sg_trace=None):
    """
    Builds a Mode 1 result dictionary with a guaranteed, consistent set
    of keys. Every return path in check_glass_type() must call this
    instead of building its own dict.

    Parameters with sensible defaults (None, False, or []) are safe to
    omit — the key will still exist in the returned dictionary.
    """
    return {
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'status': status,
        'message': message,
        'minimum_thickness_mm': minimum_thickness_mm,
        'uls_minimum_thickness_mm': uls_minimum_thickness_mm,
        'sls_minimum_thickness_mm': sls_minimum_thickness_mm,
        'sg_minimum_thickness_mm': sg_minimum_thickness_mm,
        'bal_minimum_thickness_mm': bal_minimum_thickness_mm,
        'bal_level': bal_level,
        'bal_element_type': bal_element_type,
        'glazing_config': glazing_config,
        'k_pane': k_pane,
        'annealed_area_flag': annealed_area_flag,
        'sg_flag': sg_flag,
        'panel_area_m2': panel_area_m2,
        'safety_glass_required': safety_glass_required,
        'bushfire_required': bushfire_required,
        'uls_trace': uls_trace if uls_trace is not None else [],
        'sls_trace': sls_trace if sls_trace is not None else [],
        'sg_trace': sg_trace if sg_trace is not None else [],
    }


def make_mode2_result(status, pane_label=None,
                      glass_type=None, glass_subtype=None,
                      actual_thickness_mm=None, nominal_thickness_mm=None,
                      k_pane=None, message=None,
                      effective_uls_pa=None, effective_sls_pa=None,
                      B_uls_mm=None, B_sls_mm=None, span_mm=None,
                      uls_status=None, sls_status=None, sg_status=None,
                      sg_max_area_m2=None, sg_flag=None,
                      panel_area_m2=None, annealed_area_flag=None,
                      next_compliant_thickness_mm=None,
                      next_compliant_trace=None,
                      safety_glass_required=False,
                      bal_status=None, bal_min_thickness_mm=None,
                      bal_level=None, bal_element_type=None,
                      bushfire_required=False,
                      uls_trace=None, sls_trace=None, sg_trace=None):
    """
    Builds a Mode 2 result dictionary with a guaranteed, consistent set
    of keys. Every return path in check_pane_compliance() must call this
    instead of building its own dict.

    Parameters with sensible defaults (None, False, or []) are safe to
    omit — the key will still exist in the returned dictionary.
    """
    return {
        'pane_label': pane_label,
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'actual_thickness_mm': actual_thickness_mm,
        'nominal_thickness_mm': nominal_thickness_mm,
        'k_pane': k_pane,
        'effective_uls_pa': effective_uls_pa,
        'effective_sls_pa': effective_sls_pa,
        'B_uls_mm': B_uls_mm,
        'B_sls_mm': B_sls_mm,
        'span_mm': span_mm,
        'uls_status': uls_status,
        'sls_status': sls_status,
        'sg_status': sg_status,
        'sg_max_area_m2': sg_max_area_m2,
        'sg_flag': sg_flag,
        'panel_area_m2': panel_area_m2,
        'annealed_area_flag': annealed_area_flag,
        'next_compliant_thickness_mm': next_compliant_thickness_mm,
        'next_compliant_trace': next_compliant_trace if next_compliant_trace is not None else [],
        'safety_glass_required': safety_glass_required,
        'bal_status': bal_status,
        'bal_min_thickness_mm': bal_min_thickness_mm,
        'bal_level': bal_level,
        'bal_element_type': bal_element_type,
        'bushfire_required': bushfire_required,
        'status': status,
        'message': message,
        'uls_trace': uls_trace if uls_trace is not None else [],
        'sls_trace': sls_trace if sls_trace is not None else [],
        'sg_trace': sg_trace if sg_trace is not None else [],
    }
