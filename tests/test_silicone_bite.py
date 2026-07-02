# AS 1288 Glass Thickness Calculator - Silicone Bite Test Runner
# Validates the structural silicone bite engine against known worked examples
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_silicone_bite

from engine.silicone_bite.formulas import (
    calculate_f_factor,
    calculate_governing_width,
    calculate_required_bite,
    find_min_nominal_for_bite,
    apply_thickness_floor,
    calculate_mitre_angle,
    usable_bite,
)
from engine.silicone_bite.constants import TABLE_4_1_MONOLITHIC, TABLE_4_1_LAMINATED
from engine.silicone_bite import run_bite_calculation


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
    # AGG bulletin worked example - 130 deg faceted, Section 9
    angle, width_1, width_2, pressure = 130, 1400, 1400, 2.03

    f_factor = calculate_f_factor(angle)
    governing_width = calculate_governing_width(width_1, width_2)
    required_bite = calculate_required_bite(f_factor, governing_width, pressure)

    checks = [
        ('F factor', 1.183, round(f_factor, 3), close(f_factor, 1.183, 0.001)),
        ('governing width (mm)', 1400, governing_width, governing_width == 1400),
        ('required bite (mm)', 16.01, round(required_bite, 2), close(required_bite, 16.01, 0.01)),
    ]
    return report('1', 'AGG bulletin worked example (130 deg faceted, Section 9)', checks)


def test_2():
    # 90 deg butt joint, Appendix F
    angle, width_1, width_2, pressure = 90, 1400, 1400, 2.03

    f_factor = calculate_f_factor(angle)
    governing_width = calculate_governing_width(width_1, width_2)
    required_bite = calculate_required_bite(f_factor, governing_width, pressure)

    nominal = find_min_nominal_for_bite(required_bite, TABLE_4_1_MONOLITHIC)
    nominal_floored = apply_thickness_floor(nominal)

    checks = [
        ('F factor', 0.5, f_factor, f_factor == 0.5),
        ('required bite (mm)', 6.767, round(required_bite, 3), close(required_bite, 6.767, 0.001)),
        ('nominal thickness pre-floor (mm)', 8, nominal, nominal == 8),
        ('nominal thickness post-floor (mm)', 8, nominal_floored, nominal_floored == 8),
    ]
    return report('2', '90 deg butt joint (Appendix F)', checks)


def test_3():
    # Asymmetric widths - governing width must be the larger, not the first arg
    governing_width = calculate_governing_width(800, 1200)

    checks = [
        ('governing width (mm)', 1200, governing_width, governing_width == 1200),
    ]
    return report('3', 'Asymmetric widths', checks)


def test_4():
    # Angle out of range (high)
    raised = False
    try:
        calculate_f_factor(170)
    except ValueError:
        raised = True

    result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=170, wind_pressure_kpa=2.03
    )

    checks = [
        ('ValueError raised for 170 deg (calculate_f_factor)', True, raised, raised is True),
        (
            "run_bite_calculation status for 170 deg",
            'ANGLE_OUT_OF_RANGE',
            result['status'],
            result['status'] == 'ANGLE_OUT_OF_RANGE',
        ),
    ]
    return report('4', 'Angle out of range (170 deg)', checks)


def test_5():
    # Angle out of range (low)
    raised = False
    try:
        calculate_f_factor(85)
    except ValueError:
        raised = True

    result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=85, wind_pressure_kpa=2.03
    )

    checks = [
        ('ValueError raised for 85 deg (calculate_f_factor)', True, raised, raised is True),
        (
            "run_bite_calculation status for 85 deg",
            'ANGLE_OUT_OF_RANGE',
            result['status'],
            result['status'] == 'ANGLE_OUT_OF_RANGE',
        ),
    ]
    return report('5', 'Angle out of range (85 deg)', checks)


def test_6():
    # Required bite exceeds all available thicknesses
    angle, width_1, width_2, pressure = 90, 2000, 2000, 50

    f_factor = calculate_f_factor(angle)
    governing_width = calculate_governing_width(width_1, width_2)
    required_bite = calculate_required_bite(f_factor, governing_width, pressure)

    nominal = find_min_nominal_for_bite(required_bite, TABLE_4_1_MONOLITHIC)
    nominal_floored = apply_thickness_floor(nominal)

    checks = [
        ('required bite exceeds 23.5mm', True, required_bite > 23.5, required_bite > 23.5),
        ('nominal thickness (no size satisfies)', None, nominal, nominal is None),
        ('post-floor result', None, nominal_floored, nominal_floored is None),
    ]
    return report('6', 'Required bite exceeds all available thicknesses', checks)


def test_7():
    # 6mm floor applies - required bite is small enough for 4mm, but floor pushes to 6mm
    angle, width_1, width_2, pressure = 90, 200, 200, 4.2

    f_factor = calculate_f_factor(angle)
    governing_width = calculate_governing_width(width_1, width_2)
    required_bite = calculate_required_bite(f_factor, governing_width, pressure)

    nominal = find_min_nominal_for_bite(required_bite, TABLE_4_1_MONOLITHIC)
    nominal_floored = apply_thickness_floor(nominal)

    checks = [
        ('required bite (mm)', 2.0, round(required_bite, 3), close(required_bite, 2.0, 0.001)),
        ('nominal thickness pre-floor (mm)', 4, nominal, nominal == 4),
        ('nominal thickness post-floor (mm)', 6, nominal_floored, nominal_floored == 6),
    ]
    return report('7', '6mm floor applies', checks)


def test_8():
    # Full run_bite_calculation integration
    result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03
    )

    expected_keys = {
        'angle_deg', 'f_factor', 'governing_width_mm', 'wind_pressure_kpa',
        'required_bite_mm', 'joint_type', 'mitre_angle_deg',
        'nominal_monolithic', 'nominal_laminated',
        'usable_bite_monolithic', 'usable_bite_laminated',
    }
    has_keys = expected_keys.issubset(result.keys())

    mono_ok = result['nominal_monolithic'] is not None and result['nominal_monolithic'] >= 6
    lam_ok = result['nominal_laminated'] is not None and result['nominal_laminated'] >= 6

    checks = [
        ('result has all expected keys', True, has_keys, has_keys),
        ('nominal_monolithic populated and >= 6mm', True, result['nominal_monolithic'], mono_ok),
        ('nominal_laminated populated and >= 6mm', True, result['nominal_laminated'], lam_ok),
    ]
    return report('8', 'Full run_bite_calculation integration', checks)


def test_9():
    # Mitre angle calculation
    m90 = calculate_mitre_angle(90)
    m130 = calculate_mitre_angle(130)
    m160 = calculate_mitre_angle(160)

    checks = [
        ('mitre angle for 90 deg joint', 45.0, m90, m90 == 45.0),
        ('mitre angle for 130 deg joint', 25.0, m130, m130 == 25.0),
        ('mitre angle for 160 deg joint', 10.0, m160, m160 == 10.0),
    ]
    return report('9', 'Mitre angle calculation', checks)


def test_10():
    # Usable bite, butt joint, 6mm monolithic
    min_actual = 5.8
    result = usable_bite(min_actual)

    checks = [
        ('usable bite, butt joint (mm)', 3.8, result, result == 3.8),
    ]
    return report('10', 'Usable bite, butt joint, 6mm monolithic', checks)


def test_11():
    # Usable bite, mitred joint, 6mm monolithic at 90 deg joint
    min_actual = 5.8
    mitre_angle = 45
    result = usable_bite(min_actual, mitre_angle_deg=mitre_angle)

    checks = [
        ('usable bite, mitred joint (mm)', 6.2024, round(result, 4), abs(result - 6.2024) < 0.001),
    ]
    return report('11', 'Usable bite, mitred joint, 6mm monolithic at 90 deg joint', checks)


def test_12():
    # Full run_bite_calculation - mitred joint, 90 deg corner (also exercises
    # joint_type normalisation: whitespace/case/'mitre' alias)
    result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=90, wind_pressure_kpa=2.03,
        joint_type=' MITRE '
    )

    joint_type_ok = result['joint_type'] == 'mitred'
    mitre_angle_ok = result['mitre_angle_deg'] == 45.0
    nominal_mono_ok = result['nominal_monolithic'] == 8
    nominal_lam_ok = result['nominal_laminated'] == 8
    usable_mono_ok = abs(result['usable_bite_monolithic'] - 8.8894) < 0.001
    usable_lam_ok = abs(result['usable_bite_laminated'] - 8.7480) < 0.001

    invalid_result = run_bite_calculation(1400, 1400, 90, 2.03, joint_type='bogus')
    invalid_ok = invalid_result['status'] == 'INVALID'

    checks = [
        ("joint_type normalised to 'mitred'", 'mitred', result['joint_type'], joint_type_ok),
        ('mitre_angle_deg', 45.0, result['mitre_angle_deg'], mitre_angle_ok),
        ('nominal_monolithic', 8, result['nominal_monolithic'], nominal_mono_ok),
        ('nominal_laminated', 8, result['nominal_laminated'], nominal_lam_ok),
        ('usable_bite_monolithic (mm)', 8.8894, round(result['usable_bite_monolithic'], 4), usable_mono_ok),
        ('usable_bite_laminated (mm)', 8.7480, round(result['usable_bite_laminated'], 4), usable_lam_ok),
        ("invalid joint_type returns status='INVALID'", 'INVALID', invalid_result['status'], invalid_ok),
    ]
    return report('12', 'Full run_bite_calculation - mitred joint, 90 deg corner', checks)


def test_13():
    # Mitred usable bite must exceed butt usable bite for identical inputs -
    # confirms the mitre geometry advantage is correctly wired through
    butt_result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03,
        joint_type='butt'
    )
    mitred_result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03,
        joint_type='mitred'
    )

    mono_greater = mitred_result['usable_bite_monolithic'] > butt_result['usable_bite_monolithic']
    lam_greater = mitred_result['usable_bite_laminated'] > butt_result['usable_bite_laminated']

    checks = [
        (
            'usable_bite_monolithic: mitred > butt',
            f"> {butt_result['usable_bite_monolithic']}",
            mitred_result['usable_bite_monolithic'],
            mono_greater,
        ),
        (
            'usable_bite_laminated: mitred > butt',
            f"> {butt_result['usable_bite_laminated']}",
            mitred_result['usable_bite_laminated'],
            lam_greater,
        ),
    ]
    return report('13', 'Mitred usable bite > butt usable bite for same inputs', checks)


def test_14():
    # Invalid joint type returns status='INVALID' (caught internally and
    # routed through make_silicone_result, not raised out of the function)
    result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03,
        joint_type='diagonal'
    )

    checks = [
        (
            "status for joint_type='diagonal'",
            'INVALID',
            result['status'],
            result['status'] == 'INVALID',
        ),
    ]
    return report('14', 'Invalid joint type returns INVALID status', checks)


def test_15():
    # Result dict structural consistency - mirrors test_structural_consistency.py's
    # approach for the wind load engine. Every return path must have an
    # identical key set regardless of status.
    pass_result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03
    )
    angle_result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=170, wind_pressure_kpa=2.03
    )
    invalid_result = run_bite_calculation(
        width_1_mm=1400, width_2_mm=1400, angle_deg=130, wind_pressure_kpa=2.03,
        joint_type='diagonal'
    )

    pass_keys = frozenset(pass_result.keys())
    angle_keys = frozenset(angle_result.keys())
    invalid_keys = frozenset(invalid_result.keys())

    keys_match = pass_keys == angle_keys == invalid_keys

    checks = [
        ('PASS status', 'PASS', pass_result['status'], pass_result['status'] == 'PASS'),
        (
            'ANGLE_OUT_OF_RANGE status', 'ANGLE_OUT_OF_RANGE', angle_result['status'],
            angle_result['status'] == 'ANGLE_OUT_OF_RANGE',
        ),
        ('INVALID status', 'INVALID', invalid_result['status'], invalid_result['status'] == 'INVALID'),
        (
            'all three key sets identical', True, keys_match, keys_match,
        ),
    ]
    return report('15', 'Result dict structural consistency', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Silicone Bite Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [
        test_1, test_2, test_3, test_4, test_5, test_6, test_7, test_8,
        test_9, test_10, test_11, test_12, test_13, test_14, test_15,
    ]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
