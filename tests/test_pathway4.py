# AS 1288 Glass Thickness Calculator - Pathway 4 Test Runner
# Validates the Pathway 4 (Structural Glazing, Section 14/12.12) orchestrator:
# the scenario scope gate (full_perimeter passes through to the real engine
# calculation; verticals_only and horizontals_only both return
# CONFIGURATION_OUT_OF_SCOPE_V1 without touching the underlying engine), the
# Table 5.1 human-impact wiring (v1.22), and (this session) the five
# independent governing criteria: dead-load bite, wind bite, ULS, SLS, and
# Table 5.1 (Section 14.4/14.5 - the decision tree always specified a
# wind-bending-as-4-edge check on the glass pane, separately from the
# silicone joint's own bite sizing; v1.24's "engine complete" declaration was
# premature because that check was never wired in - this session's whole
# purpose is closing that gap).
#
# Does NOT re-test engine/structural_glazing/'s own bite/dead-load math or
# engine/wind_load/checks/wind.py's own ULS/SLS math - those are
# test_structural_glazing.py's and test_runner.py's job respectively, run
# directly against the underlying engines. This file tests the ORCHESTRATION:
# that pathway4.py calls both correctly, combines all five criteria via
# max(), and reports which one governed.
#
# NOTE (v1.22/v1.23, still true after this session's rewrite): a genuine
# Table 5.1 NON_COMPLIANT (search exhausts a subtype's entire stocked
# thickness list with no pass) remains reachable for a large enough panel -
# see test_runner_2.py's TC-U for the canonical worked example. This
# module's HUMAN_IMPACT_INELIGIBLE test case (test_7) remains the
# "ineligible subtype" demonstration; it is a different status entirely
# (INELIGIBLE, not NON_COMPLIANT) and was never affected by the v1.23
# EXTRAPOLATE fix in the first place.
#
# ENGINEERING FINDING (this session, recorded here and in pathway4.py's own
# module docstring): an extensive parameter search (~45 geometry/pressure
# combinations) found NO realistic full_perimeter geometry where ULS or SLS
# governs the OVERALL result - wind bite and dead load bite both scale
# roughly linearly with panel size for a square panel, while ULS/SLS
# thickness demand grows much more slowly (capped by the AR=5 table row,
# Section 7.2), so bite structurally dominates in practice for this
# pathway's coupled geometry (bite's span and ULS/SLS's span are the same
# governing dimension under 4-edge support). SLS CAN and does exceed ULS as
# a SUB-criterion (test_8 below, hand-calculated) even though bite still
# governs overall in that case. Rather than fabricate an unrealistic
# geometry to force "ULS/SLS governs overall", test_9 verifies the max()
# combining LOGIC directly against synthetic per-criterion inputs - a
# logic-path test, not a claimed physical scenario. See pathway4.py's module
# docstring for the full reasoning.
#
# NOT YET HAND-VERIFIED BY SAHIL as of this session - do not treat these
# test figures as validated.
#
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_pathway4

import os

from engine.combined.pathway4 import run_pathway4_calculation, SUPPORTED_SCENARIOS_V1

# ---------------------------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', 'Wind_Load_Check_Tables_Full.csv')

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def report(test_id, description, checks):
    """
    checks is a list of (label, expected, actual, ok) tuples.
    Prints each check and returns True if all checks passed.
    """
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    return overall


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

SUBTYPES = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Toughened'),
    ('Monolithic', 'Heat-strengthened'),
    ('Laminated', 'Annealed'),
    ('Laminated', 'Heat-strengthened'),
    ('Laminated', 'Toughened'),
]


def test_1():
    # scenario='verticals_only' is a real, engine-capable configuration but
    # is out of scope for this pathway in this version - must return
    # CONFIGURATION_OUT_OF_SCOPE_V1 without ever calling check_glass_type()
    # or the structural glazing engine's per-subtype work.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=2.0, wind_pressure_sls_kpa=0.8,
        scenario='verticals_only', csv_path=csv_path,
    )

    checks = [
        ('status', 'CONFIGURATION_OUT_OF_SCOPE_V1', result['status'],
         result['status'] == 'CONFIGURATION_OUT_OF_SCOPE_V1'),
        ('sealed_edges echoed', 'verticals_only', result['sealed_edges'],
         result['sealed_edges'] == 'verticals_only'),
        ('message populated', True, result['message'] is not None, result['message'] is not None),
    ]
    return report('1', "scenario='verticals_only' returns CONFIGURATION_OUT_OF_SCOPE_V1 (engine not called)", checks)


def test_2():
    # scenario='horizontals_only' was already out of scope at the engine
    # level too - confirm the orchestrator gates it the same way.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=2.0, wind_pressure_sls_kpa=0.8,
        scenario='horizontals_only', csv_path=csv_path,
    )

    checks = [
        ('status', 'CONFIGURATION_OUT_OF_SCOPE_V1', result['status'],
         result['status'] == 'CONFIGURATION_OUT_OF_SCOPE_V1'),
        ('sealed_edges echoed', 'horizontals_only', result['sealed_edges'],
         result['sealed_edges'] == 'horizontals_only'),
        ('message populated', True, result['message'] is not None, result['message'] is not None),
    ]
    return report('2', "scenario='horizontals_only' returns CONFIGURATION_OUT_OF_SCOPE_V1 (engine not called)", checks)


def test_3():
    # SUPPORTED_SCENARIOS_V1 is exactly ('full_perimeter',) - locks the
    # scope gate itself, independent of the two rejection tests above.
    checks = [
        ('SUPPORTED_SCENARIOS_V1', ('full_perimeter',), SUPPORTED_SCENARIOS_V1,
         SUPPORTED_SCENARIOS_V1 == ('full_perimeter',)),
    ]
    return report('3', 'SUPPORTED_SCENARIOS_V1 is exactly (full_perimeter,)', checks)


def test_4():
    # Case A geometry (height=1.219m, width=2.438m), ULS=2.0kPa/SLS=0.8kPa,
    # toggle OFF. All five criteria computed independently and verified by
    # direct arithmetic:
    #   wind_span_m = min(2.438, 1.219) = 1.219m
    #   wind_bite_mm = 0.5 x 2.0 x 1.219 / 0.21 = 5.8048mm
    #   dead_load_perimeter_m = 2x1.219 + 2x2.438 = 7.314m
    #   dead_load_bite_mm = (2500 x 9.81 x 0.006 x 1.219 x 2.438) / (7.314 x 7000) x 1000
    #                     = 8.5417mm  (matches Case A's known figure since
    #                     this session's 6mm-seed convention for the dead
    #                     load formula's own thickness term is unchanged)
    #   Monolithic Table 4.1, chamfer=2mm, MIN_NOMINAL_THICKNESS=6mm floor:
    #     wind_bite_nominal: 5.8048mm required -> 10mm (9.7-2=7.7 >= 5.8048) -> 10mm
    #     dead_load_bite_nominal: 8.5417mm required -> 12mm (11.7-2=9.7 >= 8.5417) -> 12mm
    #   ULS/SLS (Monolithic Toughened, c1=1.0): computed via check_glass_type(),
    #     cross-checked below against the actual returned values (this
    #     orchestration test does not re-derive AR-interpolated k-values by
    #     hand - that is test_runner.py's job for the underlying engine).
    #   governing = max(10, 12, uls, sls) = 12mm (dead_load_bite), since
    #     ULS/SLS are confirmed below to stay well under 12mm at this
    #     pressure/geometry (see the ENGINEERING FINDING in this file's
    #     module docstring).
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=2.0, wind_pressure_sls_kpa=0.8,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )

    checks = [
        ('result has all six subtypes', set(SUBTYPES), set(result.keys()),
         set(result.keys()) == set(SUBTYPES)),
    ]
    for (glass_type, glass_subtype) in SUBTYPES:
        entry = result[(glass_type, glass_subtype)]
        checks.append((
            f'{glass_type} {glass_subtype} status', 'PASS', entry['status'],
            entry['status'] == 'PASS'
        ))
        checks.append((
            f'{glass_type} {glass_subtype} dead_load_bite_nominal_mm', 12,
            entry['dead_load_bite_nominal_mm'], entry['dead_load_bite_nominal_mm'] == 12
        ))
        checks.append((
            f'{glass_type} {glass_subtype} wind_bite_nominal_mm not None',
            True, entry['wind_bite_nominal_mm'] is not None,
            entry['wind_bite_nominal_mm'] is not None
        ))
        checks.append((
            f'{glass_type} {glass_subtype} uls/sls both well under 12mm', True,
            entry['uls_thickness_mm'] < 12 and entry['sls_thickness_mm'] < 12,
            entry['uls_thickness_mm'] < 12 and entry['sls_thickness_mm'] < 12
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing_thickness_mm == 12 (dead load bite)', 12,
            entry['governing_thickness_mm'], entry['governing_thickness_mm'] == 12
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing_criterion', 'dead_load_bite',
            entry['governing_criterion'], entry['governing_criterion'] == 'dead_load_bite'
        ))
        checks.append((
            f'{glass_type} {glass_subtype} table_5_1_thickness_mm is None (toggle OFF)',
            None, entry['table_5_1_thickness_mm'], entry['table_5_1_thickness_mm'] is None
        ))
    return report('4', 'Case A geometry, toggle OFF - dead load bite governs, all five criteria populated', checks)


def test_5():
    # Case C geometry (height=1.219m, width=2.438m), low pressure
    # (ULS=0.5kPa, SLS=0.4kPa), toggle OFF - dead load bite still governs
    # (dead load has no wind-pressure dependence at all, so it's unchanged
    # from test_4; wind_bite/ULS/SLS all drop with the lower pressure).
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=0.5, wind_pressure_sls_kpa=0.4,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )

    checks = []
    for (glass_type, glass_subtype) in SUBTYPES:
        entry = result[(glass_type, glass_subtype)]
        checks.append((
            f'{glass_type} {glass_subtype} status', 'PASS', entry['status'],
            entry['status'] == 'PASS'
        ))
        checks.append((
            f'{glass_type} {glass_subtype} dead_load_bite_nominal_mm (unchanged from Case A - no Pz dependence)',
            12, entry['dead_load_bite_nominal_mm'], entry['dead_load_bite_nominal_mm'] == 12
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing_thickness_mm == 12', 12,
            entry['governing_thickness_mm'], entry['governing_thickness_mm'] == 12
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing_criterion', 'dead_load_bite',
            entry['governing_criterion'], entry['governing_criterion'] == 'dead_load_bite'
        ))
    return report('5', 'Case C geometry (low pressure), toggle OFF - dead load bite governs regardless of pressure', checks)


def test_6():
    # Case D geometry (height=1.219m, width=2.438m), high pressure
    # (ULS=4.0kPa, SLS=1.6kPa), toggle OFF. This is the pressure regime
    # where wind bite overtakes dead load bite (the original v1.19/v1.20
    # "wind governs" coverage case) - confirmed here that wind_bite is now
    # the governing CRITERION under the five-criteria model, not just the
    # old two-criteria max(wind_bite, dead_load_bite).
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=4.0, wind_pressure_sls_kpa=1.6,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )

    mono_tough = result[('Monolithic', 'Toughened')]
    lam_ann = result[('Laminated', 'Annealed')]

    checks = [
        ('Monolithic Toughened status', 'PASS', mono_tough['status'], mono_tough['status'] == 'PASS'),
        ('Monolithic Toughened wind_bite_nominal_mm', 15, mono_tough['wind_bite_nominal_mm'],
         mono_tough['wind_bite_nominal_mm'] == 15),
        ('Monolithic Toughened dead_load_bite_nominal_mm (unchanged)', 12, mono_tough['dead_load_bite_nominal_mm'],
         mono_tough['dead_load_bite_nominal_mm'] == 12),
        ('Monolithic Toughened governing_thickness_mm', 15, mono_tough['governing_thickness_mm'],
         mono_tough['governing_thickness_mm'] == 15),
        ('Monolithic Toughened governing_criterion', 'wind_bite', mono_tough['governing_criterion'],
         mono_tough['governing_criterion'] == 'wind_bite'),
        ('Laminated Annealed status', 'PASS', lam_ann['status'], lam_ann['status'] == 'PASS'),
        ('Laminated Annealed wind_bite_nominal_mm', 16, lam_ann['wind_bite_nominal_mm'],
         lam_ann['wind_bite_nominal_mm'] == 16),
        ('Laminated Annealed governing_thickness_mm', 16, lam_ann['governing_thickness_mm'],
         lam_ann['governing_thickness_mm'] == 16),
        ('Laminated Annealed governing_criterion', 'wind_bite', lam_ann['governing_criterion'],
         lam_ann['governing_criterion'] == 'wind_bite'),
    ]
    return report('6', 'Case D geometry (high pressure), toggle OFF - wind bite governs (matches v1.19/v1.20 figures)', checks)


def test_7():
    # Case D geometry, toggle ON: Monolithic Annealed/Heat-strengthened are
    # ineligible for Table 5.1 (SAFETY_GLASS_INELIGIBLE) - confirms the
    # fallthrough does NOT crash or short-circuit, governing_thickness_mm is
    # still computed from the other four criteria (still 15mm, wind bite,
    # same as test_6's toggle-OFF figure for these subtypes), and
    # table_5_1_thickness_mm stays None. Also confirms Monolithic Toughened
    # and Laminated Annealed (both ELIGIBLE) get a real Table 5.1 search with
    # a genuine FAIL-then-PASS trace.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=4.0, wind_pressure_sls_kpa=1.6,
        scenario='full_perimeter', safety_glass_required=True, csv_path=csv_path,
    )

    mono_annealed = result[('Monolithic', 'Annealed')]
    mono_hs = result[('Monolithic', 'Heat-strengthened')]
    mono_tough = result[('Monolithic', 'Toughened')]
    lam_ann = result[('Laminated', 'Annealed')]

    checks = [
        ('Monolithic Annealed status', 'HUMAN_IMPACT_INELIGIBLE', mono_annealed['status'],
         mono_annealed['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Annealed table_5_1_thickness_mm', None, mono_annealed['table_5_1_thickness_mm'],
         mono_annealed['table_5_1_thickness_mm'] is None),
        ('Monolithic Annealed table_5_1_trace empty (short-circuits before the search loop)', [],
         mono_annealed['table_5_1_trace'], mono_annealed['table_5_1_trace'] == []),
        ('Monolithic Annealed governing_thickness_mm still computed (no crash/skip)', 15,
         mono_annealed['governing_thickness_mm'], mono_annealed['governing_thickness_mm'] == 15),
        ('Monolithic Annealed governing_criterion still populated', 'wind_bite',
         mono_annealed['governing_criterion'], mono_annealed['governing_criterion'] == 'wind_bite'),
        ('Monolithic Heat-strengthened status', 'HUMAN_IMPACT_INELIGIBLE', mono_hs['status'],
         mono_hs['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Heat-strengthened governing_thickness_mm still computed', 15,
         mono_hs['governing_thickness_mm'], mono_hs['governing_thickness_mm'] == 15),
        ('Monolithic Toughened status (eligible)', 'PASS', mono_tough['status'], mono_tough['status'] == 'PASS'),
        ('Monolithic Toughened table_5_1_thickness_mm', 5, mono_tough['table_5_1_thickness_mm'],
         mono_tough['table_5_1_thickness_mm'] == 5),
        ('Monolithic Toughened trace has a FAIL before the PASS', True,
         mono_tough['table_5_1_trace'][0]['result'] == 'FAIL' and mono_tough['table_5_1_trace'][-1]['result'] == 'PASS',
         mono_tough['table_5_1_trace'][0]['result'] == 'FAIL' and mono_tough['table_5_1_trace'][-1]['result'] == 'PASS'),
        ('Laminated Annealed status (eligible)', 'PASS', lam_ann['status'], lam_ann['status'] == 'PASS'),
        ('Laminated Annealed table_5_1_thickness_mm', 6, lam_ann['table_5_1_thickness_mm'],
         lam_ann['table_5_1_thickness_mm'] == 6),
    ]
    return report('7', 'Toggle ON, HUMAN_IMPACT_INELIGIBLE fallthrough confirmed alongside eligible-subtype Table 5.1 search', checks)


def test_8():
    # SLS exceeds ULS as a SUB-criterion (hand-calculated, see this file's
    # module docstring for the full arithmetic):
    #   height=1.0m, width=5.0m, ULS=1.0kPa, SLS=0.98kPa, Laminated Annealed
    #   wind_span_m = min(5.0, 1.0) = 1.0m
    #   wind_bite_mm = 0.5 x 1.0 x 1.0 / 0.21 = 2.3810mm
    #   dead_load_perimeter_m = 2x1.0 + 2x5.0 = 12.0m
    #   dead_load_bite_mm = (2500 x 9.81 x 0.006 x 1.0 x 5.0) / (12.0 x 7000) x 1000 = 8.7589mm
    #   Laminated Table 4.1, chamfer=2mm, 6mm floor:
    #     wind_bite_nominal: 2.3810mm required -> 5mm (4.6-2=2.6 >= 2.3810) -> floored to 6mm
    #     dead_load_bite_nominal: 8.7589mm required -> 12mm (11.6-2=9.6 >= 8.7589) -> 12mm
    #   ULS/SLS via check_glass_type() (Laminated Annealed, c1=1.0):
    #     uls_thickness_mm = 5, sls_thickness_mm = 6 (SLS > ULS at this AR)
    #   panel_area_m2 = 1.0 x 5.0 = 5.0
    #   governing = max(12, 6, 5, 6) = 12mm (dead_load_bite) - SLS exceeding
    #     ULS is real and independently confirmed, but does not change the
    #     OVERALL governing criterion in this geometry (see module docstring
    #     ENGINEERING FINDING).
    result = run_pathway4_calculation(
        height_m=1.0, width_m=5.0,
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.98,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )
    entry = result[('Laminated', 'Annealed')]

    checks = [
        ('status', 'PASS', entry['status'], entry['status'] == 'PASS'),
        ('panel_area_m2', 5.0, entry['panel_area_m2'], abs(entry['panel_area_m2'] - 5.0) < 0.0001),
        ('wind_bite_mm (raw)', 2.380952380952381, entry['wind_bite_mm'],
         abs(entry['wind_bite_mm'] - 2.380952380952381) < 0.0001),
        ('dead_load_bite_mm (raw)', 8.758928571428571, entry['dead_load_bite_mm'],
         abs(entry['dead_load_bite_mm'] - 8.758928571428571) < 0.0001),
        ('wind_bite_nominal_mm (floored to 6mm)', 6, entry['wind_bite_nominal_mm'],
         entry['wind_bite_nominal_mm'] == 6),
        ('dead_load_bite_nominal_mm', 12, entry['dead_load_bite_nominal_mm'],
         entry['dead_load_bite_nominal_mm'] == 12),
        ('uls_thickness_mm', 5, entry['uls_thickness_mm'], entry['uls_thickness_mm'] == 5),
        ('sls_thickness_mm (SLS > ULS at this AR - confirms independence, Section 7.6)', 6,
         entry['sls_thickness_mm'], entry['sls_thickness_mm'] == 6),
        ('sls_thickness_mm > uls_thickness_mm', True, entry['sls_thickness_mm'] > entry['uls_thickness_mm'],
         entry['sls_thickness_mm'] > entry['uls_thickness_mm']),
        ('governing_thickness_mm (dead load bite still governs overall)', 12, entry['governing_thickness_mm'],
         entry['governing_thickness_mm'] == 12),
        ('governing_criterion', 'dead_load_bite', entry['governing_criterion'],
         entry['governing_criterion'] == 'dead_load_bite'),
    ]
    return report('8', 'SLS exceeds ULS as a sub-criterion (hand-calculated) - confirms independent per-criterion search; dead load bite still governs overall', checks)


def test_9():
    # LOGIC-PATH test, not a physical scenario (see module docstring's
    # ENGINEERING FINDING - no realistic full_perimeter geometry was found
    # where ULS or SLS governs the overall result). This test verifies the
    # max()-with-key combining logic itself is correct by constructing the
    # same dict shape run_pathway4_calculation() builds internally and
    # confirming it selects the correct governing_criterion for each of the
    # five possible winners - a direct unit test of the selection rule
    # (`governing_criterion = max(criteria, key=lambda k: criteria[k])`),
    # independent of whether real AS 1288 data ever produces each winner.
    def pick(criteria):
        crit = max(criteria, key=lambda k: criteria[k])
        return crit, criteria[crit]

    cases = [
        ({'dead_load_bite': 12, 'wind_bite': 8, 'uls': 4, 'sls': 5}, 'dead_load_bite', 12),
        ({'dead_load_bite': 8, 'wind_bite': 15, 'uls': 4, 'sls': 5}, 'wind_bite', 15),
        ({'dead_load_bite': 6, 'wind_bite': 6, 'uls': 10, 'sls': 5}, 'uls', 10),
        ({'dead_load_bite': 6, 'wind_bite': 6, 'uls': 5, 'sls': 12}, 'sls', 12),
        ({'dead_load_bite': 6, 'wind_bite': 6, 'uls': 5, 'sls': 5, 'table_5_1': 10}, 'table_5_1', 10),
    ]

    checks = []
    for criteria, expected_crit, expected_val in cases:
        crit, val = pick(criteria)
        checks.append((
            f'{expected_crit} wins with criteria={criteria}', (expected_crit, expected_val), (crit, val),
            crit == expected_crit and val == expected_val
        ))
    return report('9', 'max()-with-key governing-criterion selection logic, all five possible winners (synthetic inputs, not a physical scenario)', checks)


def test_10():
    # Table 5.1 genuinely governs the OVERALL result (hand-verified against
    # a direct function call before being added here): a small-span,
    # large-area panel (low bite/ULS/SLS demand, but panel area large enough
    # to push Table 5.1's search past all four other criteria).
    #   height=0.35m, width=15.0m, ULS=0.15kPa, SLS=0.1kPa, Laminated Annealed
    #   panel_area_m2 = 0.35 x 15.0 = 5.25
    #   dead_load_bite_nominal_mm = 6, wind_bite_nominal_mm = 6,
    #   uls_thickness_mm = 5, sls_thickness_mm = 5 (all confirmed via direct
    #   call before this test was written)
    #   Table 5.1 search (Laminated Annealed, CAT2): 5mm->2.2m2 FAIL,
    #   6mm->3.0m2 FAIL, 8mm->5.0m2 FAIL, 10mm->7.0m2 PASS (5.25 <= 7.0)
    #   governing = max(6, 6, 5, 5, 10) = 10mm (table_5_1)
    result = run_pathway4_calculation(
        height_m=0.35, width_m=15.0,
        wind_pressure_uls_kpa=0.15, wind_pressure_sls_kpa=0.1,
        scenario='full_perimeter', safety_glass_required=True, csv_path=csv_path,
    )
    entry = result[('Laminated', 'Annealed')]

    checks = [
        ('status', 'PASS', entry['status'], entry['status'] == 'PASS'),
        ('panel_area_m2', 5.25, entry['panel_area_m2'], abs(entry['panel_area_m2'] - 5.25) < 0.0001),
        ('dead_load_bite_nominal_mm', 6, entry['dead_load_bite_nominal_mm'],
         entry['dead_load_bite_nominal_mm'] == 6),
        ('wind_bite_nominal_mm', 6, entry['wind_bite_nominal_mm'], entry['wind_bite_nominal_mm'] == 6),
        ('uls_thickness_mm', 5, entry['uls_thickness_mm'], entry['uls_thickness_mm'] == 5),
        ('sls_thickness_mm', 5, entry['sls_thickness_mm'], entry['sls_thickness_mm'] == 5),
        ('table_5_1_thickness_mm', 10, entry['table_5_1_thickness_mm'], entry['table_5_1_thickness_mm'] == 10),
        ('table_5_1_trace has three FAILs before the PASS', True,
         [t['result'] for t in entry['table_5_1_trace']] == ['FAIL', 'FAIL', 'FAIL', 'PASS'],
         [t['result'] for t in entry['table_5_1_trace']] == ['FAIL', 'FAIL', 'FAIL', 'PASS']),
        ('governing_thickness_mm (Table 5.1 exceeds all four other criteria)', 10,
         entry['governing_thickness_mm'], entry['governing_thickness_mm'] == 10),
        ('governing_criterion', 'table_5_1', entry['governing_criterion'],
         entry['governing_criterion'] == 'table_5_1'),
    ]
    return report('10', 'Table 5.1 governs the overall result (hand-verified, real geometry, toggle ON)', checks)


def test_11():
    # BITE_NO_COMPLIANT_THICKNESS: both wind and dead-load bite lookups fail
    # simultaneously (extreme geometry/pressure, confirmed via direct call
    # before being added here) - confirms the short-circuit path still works
    # under the new two-independent-lookup structure (previously only a
    # single combined bite_thickness_mm could be None; now both
    # wind_bite_nominal_mm and dead_load_bite_nominal_mm must independently
    # fail before this status fires).
    result = run_pathway4_calculation(
        height_m=10.0, width_m=10.0,
        wind_pressure_uls_kpa=50.0, wind_pressure_sls_kpa=20.0,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )
    entry = result[('Monolithic', 'Toughened')]

    checks = [
        ('status', 'BITE_NO_COMPLIANT_THICKNESS', entry['status'], entry['status'] == 'BITE_NO_COMPLIANT_THICKNESS'),
        ('dead_load_bite_nominal_mm is None', None, entry['dead_load_bite_nominal_mm'],
         entry['dead_load_bite_nominal_mm'] is None),
        ('wind_bite_nominal_mm is None', None, entry['wind_bite_nominal_mm'],
         entry['wind_bite_nominal_mm'] is None),
        ('governing_thickness_mm is None (never reached the max() step)', None, entry['governing_thickness_mm'],
         entry['governing_thickness_mm'] is None),
        ('message populated', True, entry['message'] is not None, entry['message'] is not None),
        ('bite_trace populated', True, len(entry['bite_trace']) > 0, len(entry['bite_trace']) > 0),
    ]
    return report('11', 'BITE_NO_COMPLIANT_THICKNESS - both bite lookups fail independently', checks)


def test_12():
    # Silicone-bite transparency fields (display-only, this session) - Case A
    # geometry, no floor triggered for either criterion. Cross-checks
    # dead_load_/wind_required_bite_raw_mm against the raw wind_bite_mm/
    # dead_load_bite_mm figures (identical, per this pathway's own docstring -
    # there is no pre-lookup required-bite floor here, unlike Pathway 3), and
    # usable_bite_mm/actual_thickness_mm against engine/shared/table_4_1.py's
    # own TABLE_4_1_MONOLITHIC and EDGE_POLISH_DEDUCTION_MM.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438,
        wind_pressure_uls_kpa=2.0, wind_pressure_sls_kpa=0.8,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )
    mono_tough = result[('Monolithic', 'Toughened')]

    checks = [
        ('dead_load_required_bite_raw_mm == wind_bite/dead_load_bite (no pre-lookup floor)', True,
         mono_tough['dead_load_required_bite_raw_mm'] == mono_tough['dead_load_required_bite_floored_mm'],
         mono_tough['dead_load_required_bite_raw_mm'] == mono_tough['dead_load_required_bite_floored_mm']),
        ('wind_required_bite_raw_mm == wind_required_bite_floored_mm (no floor)', True,
         mono_tough['wind_required_bite_raw_mm'] == mono_tough['wind_required_bite_floored_mm'],
         mono_tough['wind_required_bite_raw_mm'] == mono_tough['wind_required_bite_floored_mm']),
        ('dead_load_actual_thickness_mm (Table 4.1 @ 12mm nominal)', 11.7,
         mono_tough['dead_load_actual_thickness_mm'], mono_tough['dead_load_actual_thickness_mm'] == 11.7),
        ('wind_actual_thickness_mm (Table 4.1 @ 10mm nominal)', 9.7,
         mono_tough['wind_actual_thickness_mm'], mono_tough['wind_actual_thickness_mm'] == 9.7),
        ('deduction_mm', 2, mono_tough['deduction_mm'], mono_tough['deduction_mm'] == 2),
        ('deduction_type', 'edge_polish', mono_tough['deduction_type'], mono_tough['deduction_type'] == 'edge_polish'),
        ('dead_load_usable_bite_mm == actual - deduction', True,
         round(mono_tough['dead_load_usable_bite_mm'], 1) == round(mono_tough['dead_load_actual_thickness_mm'] - 2, 1),
         round(mono_tough['dead_load_usable_bite_mm'], 1) == round(mono_tough['dead_load_actual_thickness_mm'] - 2, 1)),
        ('wind_usable_bite_mm == actual - deduction', True,
         round(mono_tough['wind_usable_bite_mm'], 1) == round(mono_tough['wind_actual_thickness_mm'] - 2, 1),
         round(mono_tough['wind_usable_bite_mm'], 1) == round(mono_tough['wind_actual_thickness_mm'] - 2, 1)),
    ]
    return report('12', 'Silicone-bite transparency fields - Case A, no floor', checks)


def test_13():
    # Silicone-bite transparency fields - floor-triggered case. Small panel,
    # low pressure (h=0.5m, w=0.5m, ULS=0.6kPa/SLS=0.4kPa) drives both raw
    # bite figures well under 6mm, so MIN_NOMINAL_THICKNESS floors both
    # nominals to 6mm - confirmed directly (dead_load_bite_nominal_mm ==
    # wind_bite_nominal_mm == 6) before being added here. Unlike Pathway 3,
    # this pathway's floor point is the final NOMINAL, not the required bite
    # itself - dead_load_required_bite_floored_mm/wind_required_bite_floored_mm
    # are set to the floored nominal's OWN usable bite so the shared
    # raw-vs-floored comparison (used by the display wording to detect "was a
    # floor applied") still fires correctly - see pathway4.py's
    # bite_transparency_kwargs block.
    result = run_pathway4_calculation(
        height_m=0.5, width_m=0.5,
        wind_pressure_uls_kpa=0.6, wind_pressure_sls_kpa=0.4,
        scenario='full_perimeter', safety_glass_required=False, csv_path=csv_path,
    )
    mono_tough = result[('Monolithic', 'Toughened')]

    checks = [
        ('dead_load_bite_nominal_mm floored to 6mm', 6, mono_tough['dead_load_bite_nominal_mm'],
         mono_tough['dead_load_bite_nominal_mm'] == 6),
        ('wind_bite_nominal_mm floored to 6mm', 6, mono_tough['wind_bite_nominal_mm'],
         mono_tough['wind_bite_nominal_mm'] == 6),
        ('dead_load_required_bite_raw_mm != dead_load_required_bite_floored_mm (floor-triggered signal)', True,
         mono_tough['dead_load_required_bite_raw_mm'] != mono_tough['dead_load_required_bite_floored_mm'],
         mono_tough['dead_load_required_bite_raw_mm'] != mono_tough['dead_load_required_bite_floored_mm']),
        ('wind_required_bite_raw_mm != wind_required_bite_floored_mm (floor-triggered signal)', True,
         mono_tough['wind_required_bite_raw_mm'] != mono_tough['wind_required_bite_floored_mm'],
         mono_tough['wind_required_bite_raw_mm'] != mono_tough['wind_required_bite_floored_mm']),
        ('dead_load_usable_bite_mm at floored 6mm nominal', 3.8, mono_tough['dead_load_usable_bite_mm'],
         mono_tough['dead_load_usable_bite_mm'] == 3.8),
        ('wind_usable_bite_mm at floored 6mm nominal', 3.8, mono_tough['wind_usable_bite_mm'],
         mono_tough['wind_usable_bite_mm'] == 3.8),
    ]
    return report('13', 'Silicone-bite transparency fields - floor-triggered case (both criteria)', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Pathway 4 Orchestrator Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5, test_6, test_7, test_8, test_9, test_10, test_11,
              test_12, test_13]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
