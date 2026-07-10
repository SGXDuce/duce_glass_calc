# AS 1288 Glass Thickness Calculator - Pathway 4 Test Runner
# Validates the Pathway 4 (Structural Glazing, Section 14/12.12) orchestrator's
# scenario scope gate - full_perimeter passes through to the real engine
# calculation; verticals_only and horizontals_only both return the new
# CONFIGURATION_OUT_OF_SCOPE_V1 status without touching the underlying engine.
# Does NOT re-test the engine's own math - that is test_structural_glazing.py's
# job, run against engine/structural_glazing/formulas.py directly and
# unchanged by this file's existence.
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

def test_1():
    # scenario='full_perimeter' passes through to the real engine calculation
    # unchanged - same inputs/outputs as Case A of test_structural_glazing.py.
    direct = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='full_perimeter'
    )
    via_pathway4 = run_pathway4_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, scenario='full_perimeter'
    )

    checks = [
        ('status', 'PASS', via_pathway4['status'], via_pathway4['status'] == 'PASS'),
        ('nominal_monolithic matches direct engine call', direct['nominal_monolithic'],
         via_pathway4['nominal_monolithic'],
         via_pathway4['nominal_monolithic'] == direct['nominal_monolithic']),
        ('nominal_laminated matches direct engine call', direct['nominal_laminated'],
         via_pathway4['nominal_laminated'],
         via_pathway4['nominal_laminated'] == direct['nominal_laminated']),
        ('governing_bite_mm matches direct engine call', direct['governing_bite_mm'],
         via_pathway4['governing_bite_mm'],
         via_pathway4['governing_bite_mm'] == direct['governing_bite_mm']),
    ]
    return report('1', "scenario='full_perimeter' passes through to run_structural_glazing_calculation()", checks)


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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Pathway 4 Orchestrator Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
