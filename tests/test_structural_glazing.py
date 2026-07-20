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
    # Case A - full perimeter sealed, Pz = 2.0 kPa.
    # wind_span_m FIX (confirmed with domain expert): AS 1288
    # Appendix F's B is the SPAN - the SHORTER of the two supported
    # dimensions when sealed on all four sides, not the longer one. The
    # engine previously used max(width_m, height_m) here, incorrectly
    # inherited from Pathway 3's Section 9 faceted-joint formula (a
    # different physical scenario with its own, different B convention).
    # Fixed to min(width_m, height_m).
    #   height=1.219m, width=2.438m -> span = min(2.438, 1.219) = 1.219m
    #   (was 2.438m pre-fix).
    #   wind_bite_mm = 0.5 x 2.0 x 1.219 / 0.21 = 5.8048mm (was 11.6095mm
    #   pre-fix - roughly halved, since span roughly halved).
    #   dead_load_bite_mm is unaffected by this fix (8.5417mm, computed
    #   from height_m/width_m directly, not wind_span_m).
    #   GOVERNING LOAD CASE FLIPS: dead load (8.5417mm) now exceeds wind
    #   (5.8048mm) - dead load governs post-fix, where wind governed
    #   pre-fix.
    # EDGE_POLISH_DEDUCTION_MM (2mm, confirmed per internal review - Section 12.12
    # item 6) still applies at the Table 4.1 step: usable = actual - 2mm.
    # Required bite is now 8.5417mm (dead load governs):
    #   Monolithic: 10mm usable = 9.7-2 = 7.7 (fails), 12mm usable = 11.7-2
    #   = 9.7 (passes) -> nominal_monolithic = 12.
    #   Laminated: 10mm usable = 9.6-2 = 7.6 (fails), 12mm usable = 11.6-2
    #   = 9.6 (passes) -> nominal_laminated = 12.
    # Case A and Case C (below) now produce identical governing figures,
    # since dead load - not wind - governs both, and dead load doesn't
    # depend on pz_kpa at all.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=2.0, sealed_edges='full_perimeter'
    )

    checks = [
        ('wind_span_m', 1.219, result['wind_span_m'], close(result['wind_span_m'], 1.219, 0.001)),
        ('wind_bite_mm', 5.80, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 5.80, 0.01)),
        ('dead_load_bite_mm (governing)', 8.54, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 8.54, 0.01)),
        ('governing_bite_mm', result['dead_load_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['dead_load_bite_mm']),
        ('status', 'PASS', result['status'], result['status'] == 'PASS'),
        ('nominal_monolithic', 12, result['nominal_monolithic'], result['nominal_monolithic'] == 12),
        ('nominal_laminated', 12, result['nominal_laminated'], result['nominal_laminated'] == 12),
    ]
    return report('1', 'Case A - full perimeter sealed, Pz=2.0kPa (span fix: dead load now governs, edge-polish deduction applied)', checks)


def test_2():
    # Case B - verticals sealed only, Pz = 2.0 kPa, dead load governs and
    # exceeds every available thickness for both glass types. Required bite
    # (25.63mm) already exceeds the largest available raw thickness before
    # any deduction (monolithic 25mm=23.5, laminated 24mm=23.4), so the
    # EDGE_POLISH_DEDUCTION_MM 2mm deduction (Section 12.12 item 6) makes no
    # difference to the outcome here - status and None results are unchanged.
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
    # Case C - full perimeter sealed, Pz = 0.5 kPa, dead load governs (both
    # before and after the wind_span_m fix - dead load already governed
    # here pre-fix, so this case's governing load case doesn't flip, unlike
    # Case A above).
    # wind_span_m FIX (see test_1's comment for full detail): span =
    # min(width_m, height_m) = min(2.438, 1.219) = 1.219m (was 2.438m).
    #   wind_bite_mm = 0.5 x 0.5 x 1.219 / 0.21 = 1.4512mm (was 2.9024mm
    #   pre-fix - roughly halved). Still well below dead load either way,
    #   so this doesn't change which load case governs here.
    # dead_load_bite_mm is unaffected by this fix (8.5417mm, computed from
    # height_m/width_m directly, not wind_span_m) - same as Case A, since
    # dead load doesn't depend on pz_kpa at all. Required bite is 8.5417mm.
    # With EDGE_POLISH_DEDUCTION_MM (2mm, Section 12.12 item 6) applied:
    #   Monolithic: 10mm usable = 9.7-2 = 7.7 (fails), 12mm usable = 11.7-2
    #   = 9.7 (passes) -> nominal_monolithic = 12.
    #   Laminated: 10mm usable = 9.6-2 = 7.6 (fails), 12mm usable = 11.6-2
    #   = 9.6 (passes) -> nominal_laminated = 12.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=0.5, sealed_edges='full_perimeter'
    )

    checks = [
        ('wind_span_m', 1.219, result['wind_span_m'], close(result['wind_span_m'], 1.219, 0.001)),
        ('wind_bite_mm', 1.45, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 1.45, 0.01)),
        ('dead_load_bite_mm (governing)', 8.54, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 8.54, 0.01)),
        ('governing_bite_mm', result['dead_load_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['dead_load_bite_mm']),
        ('status', 'PASS', result['status'], result['status'] == 'PASS'),
        ('nominal_monolithic', 12, result['nominal_monolithic'], result['nominal_monolithic'] == 12),
        ('nominal_laminated', 12, result['nominal_laminated'], result['nominal_laminated'] == 12),
    ]
    return report('3', 'Case C - full perimeter sealed, Pz=0.5kPa (dead load governs, span fix + edge-polish deduction applied)', checks)


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


def test_6():
    # Case D - full perimeter sealed, Pz = 4.0 kPa, wind governs. Added
    # (v1.20) to close a coverage gap left by the v1.19 wind_span_m fix:
    # once the span was corrected to min(width_m, height_m), Case A and
    # Case C both landed on dead load governing (8.5417mm, fixed for this
    # geometry regardless of Pz) - leaving zero remaining test coverage for
    # the full_perimeter wind-load code path, which is exactly the path the
    # v1.19 bug was in. Case D uses a higher Pz to push wind back above
    # dead load for the same geometry as Case A/C.
    #   span_m = min(1.219, 2.438) = 1.219 (same geometry as Case A/C).
    #   wind_bite_mm = 0.5 x 4.0 x 1.219 / 0.21 = 11.6095mm.
    #   dead_load_bite_mm = 8.5417mm - unchanged from Case A/C, since dead
    #   load depends only on height_m/width_m/thickness, not pz_kpa.
    #   governing_bite_mm = 11.6095mm - WIND governs this time (11.6095 >
    #   8.5417), unlike Case A/C.
    # EDGE_POLISH_DEDUCTION_MM (2mm, Section 12.12 item 6) applied at the
    # Table 4.1 step: usable = actual - 2mm. Required bite is 11.6095mm:
    #   Monolithic: 12mm usable = 11.7-2 = 9.7 (fails), 15mm usable =
    #   14.5-2 = 12.5 (passes) -> nominal_monolithic = 15.
    #   Laminated: 12mm usable = 11.6-2 = 9.6 (fails), 16mm usable =
    #   15.4-2 = 13.4 (passes) -> nominal_laminated = 16.
    # These figures are numerically identical to Case A's OLD, pre-span-fix
    # 15mm/16mm result - a coincidence of this session's chosen Pz (4.0kPa
    # here happens to reproduce the same 11.6095mm bite Case A's old,
    # incorrect 2.438m span produced at 2.0kPa), not a shortcut taken in
    # computing this case - the lookup was performed independently against
    # this case's own governing_bite_mm.
    result = run_structural_glazing_calculation(
        height_m=1.219, width_m=2.438, glass_thickness_nominal_mm=6,
        pz_kpa=4.0, sealed_edges='full_perimeter'
    )

    checks = [
        ('wind_span_m', 1.219, result['wind_span_m'], close(result['wind_span_m'], 1.219, 0.001)),
        ('wind_bite_mm (governing)', 11.61, round(result['wind_bite_mm'], 2),
         close(result['wind_bite_mm'], 11.61, 0.01)),
        ('dead_load_bite_mm', 8.54, round(result['dead_load_bite_mm'], 2),
         close(result['dead_load_bite_mm'], 8.54, 0.01)),
        ('governing_bite_mm', result['wind_bite_mm'], result['governing_bite_mm'],
         result['governing_bite_mm'] == result['wind_bite_mm']),
        ('status', 'PASS', result['status'], result['status'] == 'PASS'),
        ('nominal_monolithic', 15, result['nominal_monolithic'], result['nominal_monolithic'] == 15),
        ('nominal_laminated', 16, result['nominal_laminated'], result['nominal_laminated'] == 16),
    ]
    return report('6', 'Case D - full perimeter sealed, Pz=4.0kPa (wind governs, edge-polish deduction applied)', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Structural Glazing Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5, test_6]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
