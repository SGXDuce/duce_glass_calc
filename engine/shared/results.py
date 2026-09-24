def make_mode1_result(status, glass_type=None, glass_subtype=None,
                      message=None, minimum_thickness_mm=None,
                      uls_minimum_thickness_mm=None,
                      sls_minimum_thickness_mm=None,
                      sg_minimum_thickness_mm=None,
                      bal_minimum_thickness_mm=None,
                      table_5_3_minimum_thickness_mm=None,
                      bal_level=None, bal_element_type=None,
                      glazing_config=None, k_pane=None,
                      annealed_area_flag=None, sg_flag=None,
                      panel_area_m2=None,
                      safety_glass_required=False,
                      bushfire_required=False,
                      uls_trace=None, sls_trace=None, sg_trace=None,
                      table_5_3_trace=None):
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
        'table_5_3_minimum_thickness_mm': table_5_3_minimum_thickness_mm,
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
        'table_5_3_trace': table_5_3_trace if table_5_3_trace is not None else [],
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
                      table_5_3_status=None, table_5_3_min_thickness_mm=None,
                      uls_trace=None, sls_trace=None, sg_trace=None,
                      table_5_3_trace=None):
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
        'table_5_3_status': table_5_3_status,
        'table_5_3_min_thickness_mm': table_5_3_min_thickness_mm,
        'status': status,
        'message': message,
        'uls_trace': uls_trace if uls_trace is not None else [],
        'sls_trace': sls_trace if sls_trace is not None else [],
        'table_5_3_trace': table_5_3_trace if table_5_3_trace is not None else [],
        'sg_trace': sg_trace if sg_trace is not None else [],
    }


def make_silicone_result(status, angle_deg=None, f_factor=None, governing_width_mm=None,
                          wind_pressure_kpa=None, required_bite_mm=None, required_bite_raw_mm=None,
                          joint_type=None, mitre_angle_deg=None, nominal_monolithic=None,
                          nominal_laminated=None, usable_bite_monolithic=None,
                          usable_bite_laminated=None,
                          actual_thickness_monolithic=None, actual_thickness_laminated=None,
                          deduction_mm=None, deduction_type=None,
                          message=None):
    """
    Builds a silicone bite result dictionary with a guaranteed, consistent set of keys.
    Every return path in the silicone bite engine must use this function instead of
    building its own dict, so a missing key is structurally impossible.
    Same discipline as make_mode1_result() / make_mode2_result() — see Section 6.4
    of the project summary for rationale.

    required_bite_raw_mm is the pre-6.0mm-floor calculated value;
    required_bite_mm is what actually fed the Table 4.1 lookup (post-floor -
    identical to required_bite_raw_mm when the floor wasn't triggered).
    actual_thickness_monolithic/laminated (Table 4.1 value at
    nominal_monolithic/nominal_laminated) and deduction_mm/deduction_type
    ('chamfer', CHAMFER_ALLOWANCE_MM here) added this session for the
    silicone-bite transparency display - see run_bite_calculation().

    Possible statuses: 'PASS' (calculation completed successfully),
    'ANGLE_OUT_OF_RANGE' (angle outside 90-160), 'NO_COMPLIANT_THICKNESS' (required
    bite exceeds all available sizes), 'INVALID' (bad input), 'ERROR' (unexpected).
    """
    return {
        'status': status,
        'angle_deg': angle_deg,
        'f_factor': f_factor,
        'governing_width_mm': governing_width_mm,
        'wind_pressure_kpa': wind_pressure_kpa,
        'required_bite_mm': required_bite_mm,
        'required_bite_raw_mm': required_bite_raw_mm,
        'joint_type': joint_type,
        'mitre_angle_deg': mitre_angle_deg,
        'nominal_monolithic': nominal_monolithic,
        'nominal_laminated': nominal_laminated,
        'usable_bite_monolithic': usable_bite_monolithic,
        'usable_bite_laminated': usable_bite_laminated,
        'actual_thickness_monolithic': actual_thickness_monolithic,
        'actual_thickness_laminated': actual_thickness_laminated,
        'deduction_mm': deduction_mm,
        'deduction_type': deduction_type,
        'message': message,
    }


def make_pathway3_result(status, subtype=None, glass_type=None, glass_subtype=None,
                          governing_thickness_mm=None,
                          bite_thickness_mm=None,
                          required_bite_raw_mm=None, required_bite_floored_mm=None,
                          usable_bite_mm=None, actual_thickness_mm=None,
                          deduction_mm=None, deduction_type=None, mitre_angle_deg=None,
                          uls_thickness_mm=None, sls_thickness_mm=None,
                          human_impact_thickness_mm=None, human_impact_table=None,
                          angle_deg=None, corner_or_general=None,
                          panel_area_m2=None,
                          safety_glass_required=False,
                          unframed_edge_condition=None,
                          message=None,
                          bite_trace=None, wind_trace=None, human_impact_trace=None):
    """
    Builds a Pathway 3 (combined bite/wind/human-impact) result dictionary
    for a single glass subtype, with a guaranteed, consistent set of keys.
    Every return path in run_pathway3_calculation() must call this instead
    of building its own dict - same discipline as make_mode1_result() etc.,
    see Section 6.4 of the project summary.

    required_bite_raw_mm / required_bite_floored_mm / usable_bite_mm /
    actual_thickness_mm / deduction_mm / deduction_type / mitre_angle_deg
    (added for the silicone-bite transparency display, this session): the
    pre-6.0mm-floor calculated bite, what actually fed the Table 4.1 lookup
    (identical to the raw value when the floor wasn't triggered - compare
    the two to detect the floor, rather than a separate boolean), the
    winning broad category's usable bite (post chamfer/mitre deduction) and
    Table 4.1 actual (minimum) thickness at bite_thickness_mm, the chamfer
    deduction applied (CHAMFER_ALLOWANCE_MM, 'chamfer'), and the mitre angle
    (only meaningful for mitred joints). Only populated on the branches
    where a bite figure exists (i.e. bite_thickness_mm is not None).

    Possible statuses: 'PASS', 'BITE_NO_COMPLIANT_THICKNESS' (short-circuited
    at the broad-category level, Section 12.13 step 2), 'WIND_NO_COMPLIANT_THICKNESS',
    'HUMAN_IMPACT_INELIGIBLE' (subtype not eligible for the applicable table -
    bite/wind results still populated, governing_thickness_mm still computed
    without the human impact figure), 'HUMAN_IMPACT_NOT_PERMITTED' (Table 5.3
    hard gate), 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS', 'ERROR'.
    """
    return {
        'subtype': subtype,
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'status': status,
        'message': message,
        'governing_thickness_mm': governing_thickness_mm,
        'bite_thickness_mm': bite_thickness_mm,
        'required_bite_raw_mm': required_bite_raw_mm,
        'required_bite_floored_mm': required_bite_floored_mm,
        'usable_bite_mm': usable_bite_mm,
        'actual_thickness_mm': actual_thickness_mm,
        'deduction_mm': deduction_mm,
        'deduction_type': deduction_type,
        'mitre_angle_deg': mitre_angle_deg,
        'uls_thickness_mm': uls_thickness_mm,
        'sls_thickness_mm': sls_thickness_mm,
        'human_impact_thickness_mm': human_impact_thickness_mm,
        'human_impact_table': human_impact_table,
        'angle_deg': angle_deg,
        'corner_or_general': corner_or_general,
        'panel_area_m2': panel_area_m2,
        'safety_glass_required': safety_glass_required,
        'unframed_edge_condition': unframed_edge_condition,
        'bite_trace': bite_trace if bite_trace is not None else [],
        'wind_trace': wind_trace if wind_trace is not None else [],
        'human_impact_trace': human_impact_trace if human_impact_trace is not None else [],
    }


def make_pathway4_result(status, subtype=None, glass_type=None, glass_subtype=None,
                          governing_thickness_mm=None,
                          governing_criterion=None,
                          dead_load_bite_nominal_mm=None,
                          wind_bite_nominal_mm=None,
                          dead_load_required_bite_raw_mm=None,
                          dead_load_required_bite_floored_mm=None,
                          wind_required_bite_raw_mm=None,
                          wind_required_bite_floored_mm=None,
                          dead_load_usable_bite_mm=None,
                          wind_usable_bite_mm=None,
                          dead_load_actual_thickness_mm=None,
                          wind_actual_thickness_mm=None,
                          deduction_mm=None, deduction_type=None,
                          uls_thickness_mm=None,
                          sls_thickness_mm=None,
                          wind_bite_mm=None,
                          dead_load_bite_mm=None,
                          table_5_1_thickness_mm=None,
                          panel_area_m2=None,
                          safety_glass_required=False,
                          message=None,
                          bite_trace=None, wind_trace=None, table_5_1_trace=None):
    """
    Builds a Pathway 4 (structural glazing, full_perimeter) result dictionary
    for a single glass subtype, with a guaranteed, consistent set of keys.
    Every return path in run_pathway4_calculation()'s full_perimeter branch
    must call this instead of building its own dict - same discipline as
    make_pathway3_result() etc., see Section 6.4 of the project summary.

    Only used for the full_perimeter scenario - the CONFIGURATION_OUT_OF_SCOPE_V1
    branch (verticals_only/horizontals_only) still returns a single
    make_structural_glazing_result() dict, unchanged, since it never reaches
    per-subtype work at all.

    Five independent criteria (Section 7.6 independence principle), added
    v1.26 to close a gap where Pathway 4 sized the silicone joint but
    never checked the glass pane's own AS 1288 Clause 4.4.3 ULS/SLS bending
    capacity - the joint and the pane are two independent failure modes:
    - dead_load_bite_nominal_mm / wind_bite_nominal_mm: independent Table 4.1
      lookups (find_min_nominal_for_usable_bite(), EDGE_POLISH_DEDUCTION_MM)
      against the raw dead_load_bite_mm/wind_bite_mm figures from
      run_structural_glazing_calculation() - per BROAD CATEGORY (Monolithic/
      Laminated), not per subtype, same as the old single bite_thickness_mm
      was. Deliberately two separate lookups, not one lookup against
      max(wind_bite_mm, dead_load_bite_mm) - see module docstring for why.
    - uls_thickness_mm / sls_thickness_mm: from check_glass_type()
      (support_condition='4-edge', safety_glass_required=False) - genuinely
      PER SUBTYPE (c1 factor differs by glass_type/glass_subtype).
    - table_5_1_thickness_mm: per subtype, unchanged from v1.22.
    governing_thickness_mm = max() of whichever of the above are active;
    governing_criterion names which one produced that max (one of
    'dead_load_bite', 'wind_bite', 'uls', 'sls', 'table_5_1').

    wind_bite_mm / dead_load_bite_mm (raw mm, pre-Table-4.1-lookup) are kept
    for the report's bite-arithmetic breakdown.

    Silicone-bite transparency fields (this session, display-only, no
    calculation change): dead_load_required_bite_raw_mm/wind_required_bite_raw_mm
    are IDENTICAL to dead_load_bite_mm/wind_bite_mm above (there is no
    pre-lookup required-bite floor in this pathway, unlike Pathway 3 -
    both names are kept because the display code shares one wording
    helper with Pathway 3, which does have a real raw-vs-floored
    distinction at this point). dead_load_required_bite_floored_mm/
    wind_required_bite_floored_mm is what actually fed the Table 4.1
    lookup - identical to the _raw_mm figure here for the same reason,
    UNLESS the MIN_NOMINAL_THICKNESS (6mm) floor raised the final nominal
    beyond what the Table 4.1 lookup itself returned, in which case it is
    set to the required bite implied by that floored nominal's own Table
    4.1 actual thickness (so the raw != floored comparison used to detect
    "was a floor applied" still fires correctly for this pathway's only
    real floor point - see module docstring's floor explanation).
    dead_load_usable_bite_mm/wind_usable_bite_mm and
    dead_load_actual_thickness_mm/wind_actual_thickness_mm are the usable
    bite and Table 4.1 actual (minimum) thickness at the nominal actually
    used/displayed (post-floor). deduction_mm/deduction_type
    (EDGE_POLISH_DEDUCTION_MM, 'edge_polish') are shared across both
    criteria - the same deduction applies to both dead load and wind bite
    lookups in this pathway.

    Possible statuses: 'PASS', 'BITE_NO_COMPLIANT_THICKNESS' (both bite
    lookups returned None for this subtype's broad category),
    'WIND_NO_COMPLIANT_THICKNESS' (check_glass_type() found no compliant
    ULS/SLS thickness), 'HUMAN_IMPACT_INELIGIBLE' (subtype not eligible for
    Table 5.1 - all other criteria still populated, governing_thickness_mm
    still computed without the Table 5.1 figure), 'HUMAN_IMPACT_NO_COMPLIANT_
    THICKNESS' (Table 5.1 search exhausted this subtype's stocked thickness
    range with no pass).
    """
    return {
        'subtype': subtype,
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'status': status,
        'message': message,
        'governing_thickness_mm': governing_thickness_mm,
        'governing_criterion': governing_criterion,
        'dead_load_bite_nominal_mm': dead_load_bite_nominal_mm,
        'wind_bite_nominal_mm': wind_bite_nominal_mm,
        'dead_load_required_bite_raw_mm': dead_load_required_bite_raw_mm,
        'dead_load_required_bite_floored_mm': dead_load_required_bite_floored_mm,
        'wind_required_bite_raw_mm': wind_required_bite_raw_mm,
        'wind_required_bite_floored_mm': wind_required_bite_floored_mm,
        'dead_load_usable_bite_mm': dead_load_usable_bite_mm,
        'wind_usable_bite_mm': wind_usable_bite_mm,
        'dead_load_actual_thickness_mm': dead_load_actual_thickness_mm,
        'wind_actual_thickness_mm': wind_actual_thickness_mm,
        'deduction_mm': deduction_mm,
        'deduction_type': deduction_type,
        'uls_thickness_mm': uls_thickness_mm,
        'sls_thickness_mm': sls_thickness_mm,
        'wind_bite_mm': wind_bite_mm,
        'dead_load_bite_mm': dead_load_bite_mm,
        'table_5_1_thickness_mm': table_5_1_thickness_mm,
        'panel_area_m2': panel_area_m2,
        'safety_glass_required': safety_glass_required,
        'bite_trace': bite_trace if bite_trace is not None else [],
        'wind_trace': wind_trace if wind_trace is not None else [],
        'table_5_1_trace': table_5_1_trace if table_5_1_trace is not None else [],
    }


def make_human_impact_result(scope=True, grade_a_required=None, table=None,
                              types=None, notes=None, trail=None,
                              clauses=None, out_of_scope_reasons=None):
    """
    Builds an engine/human_impact result dictionary with a guaranteed,
    consistent set of keys. Every return path in determine_fixed(),
    determine_louvre(), and determine_sashless() must call this instead of
    building its own dict - same "one constructor, every return path goes
    through it" discipline as make_mode1_result() etc., see Section 6.4 of
    the project summary. Lets the structural-consistency test pattern
    extend cleanly to this engine.

    scope: False means this configuration is not assessed by the tool at
    all (see out_of_scope_reasons) - grade_a_required and table are then
    meaningless and left None, types is empty.

    grade_a_required: None only when scope is False. Otherwise True/False.

    types: list of dicts, one per glass type actually reported on this
    call - {id, name, ok, min_thickness, cap, why}. 'cap' is the
    area/width cap dict (or None) for annealed/heat-strengthened
    alternative routes; 'why' explains an ok=False result (or None).

    notes: informational, non-blocking messages (e.g. the bathroom
    vanity/bench exemption note, the high-risk permanent-barrier note).

    trail: ordered list of human-readable strings recording which clauses
    were tested and why they did or didn't match - the audit trail for
    match_location()'s reasoning.

    clauses: the AS 1288 clause references actually engaged for this
    result (e.g. ['5.2', '5.8']).

    out_of_scope_reasons: populated only when scope is False.
    """
    return {
        'scope': scope,
        'grade_a_required': grade_a_required,
        'table': table,
        'types': types if types is not None else [],
        'notes': notes if notes is not None else [],
        'trail': trail if trail is not None else [],
        'clauses': clauses if clauses is not None else [],
        'out_of_scope_reasons': out_of_scope_reasons if out_of_scope_reasons is not None else [],
    }


def make_structural_glazing_result(status, height_m=None, width_m=None,
                                    glass_thickness_nominal_mm=None, pz_kpa=None,
                                    sealed_edges=None, wind_span_m=None,
                                    dead_load_perimeter_m=None, wind_bite_mm=None,
                                    dead_load_bite_mm=None, governing_bite_mm=None,
                                    nominal_monolithic=None, nominal_laminated=None,
                                    message=None):
    """
    Builds a structural glazing result dictionary with a guaranteed,
    consistent set of keys. Every return path in run_structural_glazing_calculation()
    must use this function instead of building its own dict, so a missing
    key is structurally impossible. Same discipline as make_silicone_result()
    - see Section 6.4 of the project summary for rationale.

    Possible statuses: 'PASS' (calculation completed successfully),
    'NO_COMPLIANT_THICKNESS' (required bite exceeds all available sizes for
    both glass types), 'CONFIGURATION_OUT_OF_SCOPE' (unsupported sealed_edges value).
    """
    return {
        'status': status,
        'height_m': height_m,
        'width_m': width_m,
        'glass_thickness_nominal_mm': glass_thickness_nominal_mm,
        'pz_kpa': pz_kpa,
        'sealed_edges': sealed_edges,
        'wind_span_m': wind_span_m,
        'dead_load_perimeter_m': dead_load_perimeter_m,
        'wind_bite_mm': wind_bite_mm,
        'dead_load_bite_mm': dead_load_bite_mm,
        'governing_bite_mm': governing_bite_mm,
        'nominal_monolithic': nominal_monolithic,
        'nominal_laminated': nominal_laminated,
        'message': message,
    }
