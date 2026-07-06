# AS 1288 Glass Thickness Calculator - Structural Glazing Test Runner
# Validates the flat, angle-free structural glazing engine (AS 1288 Appendix F
# wind bite + Section 12.11 dead load bite) against hand-calculated cases.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_structural_glazing

from engine.structural_glazing.formulas import run_structural_glazing_calculation

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def close(actual, expected, tol=1e-2):
    return abs(actual - expected) <= tol


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
    # Case A - full perimeter sealed, Pz = 2.0 kPa, wind governs.
    # No deduction is applied in this module (pending Michael's confirmation
    # on frame-bonded edge polishing - see the NOTE in formulas.py), so the
    # lookup is a raw Table 4.1 comparison. Laminated 12mm's min_actual
    # (11.6) falls just short of the required 11.6095mm bite, so laminated
    # jumps to 16mm while monolithic 12mm's min_actual (11.7) clears it.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='full_perimeter'
    )

    checks = [
        ('dead_load_bite_mm', 8.54, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 8.54, 0.01)),
        ('wind_bite_mm (governing)', 11.61, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 11.61, 0.01)),
        ('governing_bite_mm', result['wind_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['wind_bite_mm']),
        ('status', 'PASS', result['status'], result['status'] == 'PASS'),
        ('nominal_monolithic', 12, result['nominal_monolithic'], result['nominal_monolithic'] == 12),
        ('nominal_laminated', 16, result['nominal_laminated'], result['nominal_laminated'] == 16),
    ]
    return report('1', 'Case A - full perimeter sealed, Pz=2.0kPa (wind governs)', checks)


def test_2():
    # Case B - verticals sealed only, Pz = 2.0 kPa, dead load governs and
    # exceeds every available thickness for both glass types.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='verticals_only'
    )

    checks = [
        ('dead_load_bite_mm (governing)', 25.63, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 25.63, 0.01)),
        ('wind_bite_mm', 11.61, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 11.61, 0.01)),
        ('governing_bite_mm', result['dead_load_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['dead_load_bite_mm']),
        ('status', 'NO_COMPLIANT_THICKNESS', result['status'], result['status'] == 'NO_COMPLIANT_THICKNESS'),
        ('nominal_monolithic', None, result['nominal_monolithic'], result['nominal_monolithic'] is None),
        ('nominal_laminated', None, result['nominal_laminated'], result['nominal_laminated'] is None),
    ]
    return report('2', 'Case B - verticals sealed only, Pz=2.0kPa (dead load exceeds all sizes)', checks)


def test_3():
    # Case C - full perimeter sealed, Pz = 0.5 kPa, dead load governs and
    # is satisfied by the thinnest available sizes.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=0.5, sealed_edges='full_perimeter'
    )

    checks = [
        ('dead_load_bite_mm (governing)', 8.54, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 8.54, 0.01)),
        ('wind_bite_mm', 2.90, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 2.90, 0.01)),
        ('governing_bite_mm', result['dead_load_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['dead_load_bite_mm']),
        ('status', 'PASS', result['status'], result['status'] == 'PASS'),
        ('nominal_monolithic', 10, result['nominal_monolithic'], result['nominal_monolithic'] == 10),
        ('nominal_laminated', 10, result['nominal_laminated'], result['nominal_laminated'] == 10),
    ]
    return report('3', 'Case C - full perimeter sealed, Pz=0.5kPa (dead load governs, satisfied)', checks)


def test_4():
    # 'horizontals_only' is explicitly out of scope pending confirmation.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='horizontals_only'
    )

    checks = [
        ('status', 'CONFIGURATION_OUT_OF_SCOPE', result['status'],
         result['status'] == 'CONFIGURATION_OUT_OF_SCOPE'),
        ('sealed_edges echoed', 'horizontals_only', result['sealed_edges'],
         result['sealed_edges'] == 'horizontals_only'),
        ('message populated', True, result['message'] is not None, result['message'] is not None),
    ]
    return report('4', "sealed_edges='horizontals_only' returns CONFIGURATION_OUT_OF_SCOPE", checks)


def test_5():
    # Result dict structural consistency - every status must return an
    # identical key set (Section 6.4 discipline).
    pass_result = run_structural_glazing_calculation(1.219, 2.438, 6, 0.5, 'full_perimeter')
    no_compliant_result = run_structural_glazing_calculation(1.219, 2.438, 6, 2.0, 'verticals_only')
    out_of_scope_result = run_structural_glazing_calculation(1.219, 2.438, 6, 2.0, 'horizontals_only')

    keys_pass = set(pass_result.keys())
    keys_no_compliant = set(no_compliant_result.keys())
    keys_out_of_scope = set(out_of_scope_result.keys())

    all_identical = keys_pass == keys_no_compliant == keys_out_of_scope

    checks = [
        ('PASS status', 'PASS', pass_result['status'], pass_result['status'] == 'PASS'),
        ('NO_COMPLIANT_THICKNESS status', 'NO_COMPLIANT_THICKNESS', no_compliant_result['status'],
         no_compliant_result['status'] == 'NO_COMPLIANT_THICKNESS'),
        ('CONFIGURATION_OUT_OF_SCOPE status', 'CONFIGURATION_OUT_OF_SCOPE', out_of_scope_result['status'],
         out_of_scope_result['status'] == 'CONFIGURATION_OUT_OF_SCOPE'),
        ('all three key sets identical', True, all_identical, all_identical),
    ]
    return report('5', 'Result dict structural consistency', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Structural Glazing Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
