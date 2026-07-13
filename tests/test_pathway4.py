# AS 1288 Glass Thickness Calculator - Pathway 4 Test Runner
# Validates the Pathway 4 (Structural Glazing, Section 14/12.12) orchestrator:
# the scenario scope gate (full_perimeter passes through to the real engine
# calculation; verticals_only and horizontals_only both return
# CONFIGURATION_OUT_OF_SCOPE_V1 without touching the underlying engine), and
# (v1.22) the Table 5.1 human-impact wiring for full_perimeter - implements
# the v1.21 documentation-only decision (Section 12.12 item 9, Section 14.7).
# Does NOT re-test the engine's own bite/dead-load math - that is
# test_structural_glazing.py's job, run against
# engine/structural_glazing/formulas.py directly and unchanged by this file's
# existence.
#
# NOTE (v1.22, written before the EXTRAPOLATE bug fix below): this suite was
# originally written on the assumption that a genuine Table 5.1 NON_COMPLIANT
# (search exhausts a subtype's entire stocked thickness list with no pass)
# was structurally UNREACHABLE with real stock data, because
# get_safety_glass_max_area() returned the sentinel string 'EXTRAPOLATE' for
# any thickness >12mm, treated as an automatic pass by every caller
# (including this module's own _run_table_5_1_search()). That bypass has
# since been fixed (see the changelog entry after v1.22): thickness >12mm now
# returns a real computed max area (linear extrapolation, slope 1, anchored
# at the 12mm value), compared against panel_area_m2 like any other row.
# NON_COMPLIANT is therefore genuinely reachable now for a panel large enough
# to exceed even the extrapolated limit at a subtype's largest stocked
# thickness - see test_runner_2.py's TC-U for a worked example (Laminated
# Annealed, 22.75m2 panel, fails all the way to 24mm). This module's tests
# below still use HUMAN_IMPACT_INELIGIBLE for their "failing" toggle-ON case
# rather than a fabricated dimension, which remains a legitimate, reachable
# rejection - not stale, just no longer the *only* way to fail.
#
# NOT YET HAND-VERIFIED BY SAHIL as of this session - do not treat these
# test figures as validated.
#
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_pathway4

from engine.combined.pathway4 import run_pathway4_calculation, SUPPORTED_SCENARIOS_V1
from engine.structural_glazing.formulas import run_structural_glazing_calculation

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

BITE_FIELD_FOR_CATEGORY = {
    'Monolithic': 'nominal_monolithic',
    'Laminated': 'nominal_laminated',
}


def test_1():
    # scenario='full_perimeter' passes through to the real engine calculation
    # - same geometry/pressure as Case A of test_structural_glazing.py.
    # (v1.22): return shape is now a dict keyed by (glass_type, glass_subtype)
    # for all six subtypes, mirroring run_pathway3_calculation() - see
    # pathway4.py's module docstring for why (Table 5.1 is per-subtype, the
    # bite/dead-load engine is only per-broad-category). Each subtype's
    # bite_thickness_mm must equal the direct engine call's corresponding
    # nominal_monolithic/nominal_laminated figure.
    direct = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='full_perimeter'
    )
    via_pathway4 = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, scenario='full_perimeter'
    )

    checks = [
        ('result has all six subtypes', set(SUBTYPES), set(via_pathway4.keys()),
         set(via_pathway4.keys()) == set(SUBTYPES)),
    ]
    for (glass_type, glass_subtype) in SUBTYPES:
        entry = via_pathway4[(glass_type, glass_subtype)]
        expected_bite = direct[BITE_FIELD_FOR_CATEGORY[glass_type]]
        checks.append((
            f'{glass_type} {glass_subtype} status', 'PASS', entry['status'],
            entry['status'] == 'PASS'
        ))
        checks.append((
            f'{glass_type} {glass_subtype} bite_thickness_mm matches direct engine call',
            expected_bite, entry['bite_thickness_mm'],
            entry['bite_thickness_mm'] == expected_bite
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing_thickness_mm == bite (toggle default OFF)',
            expected_bite, entry['governing_thickness_mm'],
            entry['governing_thickness_mm'] == expected_bite
        ))
        checks.append((
            f'{glass_type} {glass_subtype} table_5_1_thickness_mm is None (toggle default OFF)',
            None, entry['table_5_1_thickness_mm'], entry['table_5_1_thickness_mm'] is None
        ))
    return report('1', "scenario='full_perimeter' passes through to run_structural_glazing_calculation(), per-subtype dict, toggle defaults OFF", checks)


def test_2():
    # scenario='verticals_only' is a real, engine-capable configuration
    # (Case B of test_structural_glazing.py) but is out of scope for this
    # pathway in this version - must return CONFIGURATION_OUT_OF_SCOPE_V1
    # without ever calling the engine.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, scenario='verticals_only'
    )

    checks = [
        ('status', 'CONFIGURATION_OUT_OF_SCOPE_V1', result['status'],
         result['status'] == 'CONFIGURATION_OUT_OF_SCOPE_V1'),
        ('sealed_edges echoed', 'verticals_only', result['sealed_edges'],
         result['sealed_edges'] == 'verticals_only'),
        ('message populated', True, result['message'] is not None, result['message'] is not None),
        ('nominal_monolithic not computed', None, result['nominal_monolithic'],
         result['nominal_monolithic'] is None),
        ('nominal_laminated not computed', None, result['nominal_laminated'],
         result['nominal_laminated'] is None),
    ]
    return report('2', "scenario='verticals_only' returns CONFIGURATION_OUT_OF_SCOPE_V1 (engine not called)", checks)


def test_3():
    # scenario='horizontals_only' was already out of scope at the engine
    # level too - confirm the orchestrator gates it the same way as
    # verticals_only, without relying on the engine's own (different)
    # CONFIGURATION_OUT_OF_SCOPE status ever being reached.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, scenario='horizontals_only'
    )

    checks = [
        ('status', 'CONFIGURATION_OUT_OF_SCOPE_V1', result['status'],
         result['status'] == 'CONFIGURATION_OUT_OF_SCOPE_V1'),
        ('sealed_edges echoed', 'horizontals_only', result['sealed_edges'],
         result['sealed_edges'] == 'horizontals_only'),
        ('message populated', True, result['message'] is not None, result['message'] is not None),
    ]
    return report('3', "scenario='horizontals_only' returns CONFIGURATION_OUT_OF_SCOPE_V1 (engine not called)", checks)


def test_4():
    # SUPPORTED_SCENARIOS_V1 is exactly ('full_perimeter',) - locks the
    # scope gate itself, independent of the two rejection tests above, so a
    # future accidental widening of scope shows up here even if the
    # rejection tests happen to still pass for other reasons.
    checks = [
        ('SUPPORTED_SCENARIOS_V1', ('full_perimeter',), SUPPORTED_SCENARIOS_V1,
         SUPPORTED_SCENARIOS_V1 == ('full_perimeter',)),
    ]
    return report('4', 'SUPPORTED_SCENARIOS_V1 is exactly (full_perimeter,)', checks)


def test_5():
    # Toggle OFF (safety_glass_required=False, the default): Table 5.1 is
    # not checked at all - every subtype's governing_thickness_mm equals its
    # bite_thickness_mm, table_5_1_thickness_mm stays None, and the trace is
    # empty. Explicit toggle-OFF case, same geometry/pressure as Case D of
    # test_structural_glazing.py (height=1.219m, width=2.438m, pz=4.0kPa,
    # bite governs at 15mm monolithic / 16mm laminated).
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=4.0, scenario='full_perimeter', safety_glass_required=False
    )

    checks = []
    for (glass_type, glass_subtype) in SUBTYPES:
        entry = result[(glass_type, glass_subtype)]
        expected_bite = 15 if glass_type == 'Monolithic' else 16
        checks.append((
            f'{glass_type} {glass_subtype} status', 'PASS', entry['status'],
            entry['status'] == 'PASS'
        ))
        checks.append((
            f'{glass_type} {glass_subtype} governing == bite', expected_bite,
            entry['governing_thickness_mm'], entry['governing_thickness_mm'] == expected_bite
        ))
        checks.append((
            f'{glass_type} {glass_subtype} table_5_1_thickness_mm', None,
            entry['table_5_1_thickness_mm'], entry['table_5_1_thickness_mm'] is None
        ))
        checks.append((
            f'{glass_type} {glass_subtype} table_5_1_trace empty', [],
            entry['table_5_1_trace'], entry['table_5_1_trace'] == []
        ))
    return report('5', 'Toggle OFF: Table 5.1 not checked, governing == bite for every subtype', checks)


def test_6():
    # Toggle ON, PASSING: Monolithic Toughened (cat1) and Laminated Annealed
    # (cat2), same Case D geometry (height=1.219m, width=2.438m, pz=4.0kPa ->
    # panel_area_m2 = 1.219 x 2.438 = 2.9719, bite = 15mm/16mm).
    #
    # Monolithic Toughened (cat1, SAFETY_GLASS_AREA_CAT1): search starts at
    # this subtype's smallest stocked size (4mm), ascending, independent of
    # the 15mm bite figure (Section 7.6 discipline - never starts from
    # another check's result):
    #   4mm -> max_area=2.0m2, 2.9719 > 2.0 -> FAIL
    #   5mm -> max_area=3.0m2, 2.9719 <= 3.0 -> PASS, table_5_1_thickness=5
    # governing = max(bite=15, table_5_1=5) = 15mm (bite still governs
    # overall, but Table 5.1's own search result is genuinely 5mm, and the
    # FAIL-then-PASS trace confirms the area-exceeded mechanic works).
    #
    # Laminated Annealed (cat2, SAFETY_GLASS_AREA_CAT2):
    #   5mm -> max_area=2.2m2, 2.9719 > 2.2 -> FAIL
    #   6mm -> max_area=3.0m2, 2.9719 <= 3.0 -> PASS, table_5_1_thickness=6
    # governing = max(bite=16, table_5_1=6) = 16mm.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=4.0, scenario='full_perimeter', safety_glass_required=True
    )

    mono_toughened = result[('Monolithic', 'Toughened')]
    lam_annealed = result[('Laminated', 'Annealed')]

    checks = [
        ('panel_area_m2', 2.9719, mono_toughened['panel_area_m2'],
         abs(mono_toughened['panel_area_m2'] - 2.9719) < 0.0001),
        ('Monolithic Toughened status', 'PASS', mono_toughened['status'],
         mono_toughened['status'] == 'PASS'),
        ('Monolithic Toughened table_5_1_thickness_mm', 5, mono_toughened['table_5_1_thickness_mm'],
         mono_toughened['table_5_1_thickness_mm'] == 5),
        ('Monolithic Toughened trace has a FAIL before the PASS', 'FAIL',
         mono_toughened['table_5_1_trace'][0]['result'],
         mono_toughened['table_5_1_trace'][0]['result'] == 'FAIL' and
         mono_toughened['table_5_1_trace'][-1]['result'] == 'PASS'),
        ('Monolithic Toughened governing_thickness_mm (bite governs)', 15,
         mono_toughened['governing_thickness_mm'], mono_toughened['governing_thickness_mm'] == 15),
        ('Laminated Annealed status', 'PASS', lam_annealed['status'],
         lam_annealed['status'] == 'PASS'),
        ('Laminated Annealed table_5_1_thickness_mm', 6, lam_annealed['table_5_1_thickness_mm'],
         lam_annealed['table_5_1_thickness_mm'] == 6),
        ('Laminated Annealed trace has a FAIL before the PASS', 'FAIL',
         lam_annealed['table_5_1_trace'][0]['result'],
         lam_annealed['table_5_1_trace'][0]['result'] == 'FAIL' and
         lam_annealed['table_5_1_trace'][-1]['result'] == 'PASS'),
        ('Laminated Annealed governing_thickness_mm (bite governs)', 16,
         lam_annealed['governing_thickness_mm'], lam_annealed['governing_thickness_mm'] == 16),
    ]
    return report('6', 'Toggle ON, PASSING: Table 5.1 search runs independently, FAIL-then-PASS trace, bite still governs', checks)


def test_7():
    # Toggle ON, "FAILING": Monolithic Annealed and Monolithic
    # Heat-strengthened are both in SAFETY_GLASS_INELIGIBLE - a genuine,
    # reachable rejection under Table 5.1 with real data. See this file's
    # top-of-module NOTE: a true NON_COMPLIANT (search-exhausted) result is
    # unreachable for any currently-eligible subtype with real stock data,
    # so HUMAN_IMPACT_INELIGIBLE is the realistic "failing" case here, not a
    # fabricated dimension. Per the same fallthrough behaviour as Pathway 3
    # (pathway3.py's identical INELIGIBLE handling), this does NOT
    # short-circuit - governing_thickness_mm still equals the bite figure,
    # only table_5_1_thickness_mm stays None.
    result = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=4.0, scenario='full_perimeter', safety_glass_required=True
    )

    mono_annealed = result[('Monolithic', 'Annealed')]
    mono_hs = result[('Monolithic', 'Heat-strengthened')]

    checks = [
        ('Monolithic Annealed status', 'HUMAN_IMPACT_INELIGIBLE', mono_annealed['status'],
         mono_annealed['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Annealed table_5_1_thickness_mm', None, mono_annealed['table_5_1_thickness_mm'],
         mono_annealed['table_5_1_thickness_mm'] is None),
        ('Monolithic Annealed table_5_1_trace empty (short-circuits before the search loop)', [],
         mono_annealed['table_5_1_trace'], mono_annealed['table_5_1_trace'] == []),
        ('Monolithic Annealed governing_thickness_mm still == bite (no crash/skip)', 15,
         mono_annealed['governing_thickness_mm'], mono_annealed['governing_thickness_mm'] == 15),
        ('Monolithic Heat-strengthened status', 'HUMAN_IMPACT_INELIGIBLE', mono_hs['status'],
         mono_hs['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Heat-strengthened governing_thickness_mm still == bite', 15,
         mono_hs['governing_thickness_mm'], mono_hs['governing_thickness_mm'] == 15),
    ]
    return report('7', 'Toggle ON, HUMAN_IMPACT_INELIGIBLE (realistic "failing" case - see module NOTE on unreachable NON_COMPLIANT)', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Pathway 4 Orchestrator Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5, test_6, test_7]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
