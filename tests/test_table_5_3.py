# AS 1288 Glass Thickness Calculator - Table 5.3 Test Runner
# Validates the Table 5.3 (glazed panels with unframed side edges) lookup
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_table_5_3

import os

import engine.wind_load.checks.wind as wind_mod
from engine.shared.table_5_3 import load_table_5_3, check_table_5_3
from engine.wind_load import run_calculation

# ---------------------------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', 'Table_5_3.csv')
wind_csv_path = os.path.join(script_dir, '..', 'data', 'Wind_Load_Check_Tables_Full.csv')

TABLE_5_3 = load_table_5_3(csv_path)


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
    # Basic lookup, no restrictions
    result = check_table_5_3(1.0, 'Annealed', 2.0, 2, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
    ]
    return report('1', 'Basic lookup, no restrictions', checks)


def test_2():
    # Height band boundary - 1.2m falls in the <=1.2 band, not the >1.2 band
    result = check_table_5_3(1.2, 'Annealed', 2.0, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
    ]
    return report('2', 'Height band boundary (1.2m)', checks)


def test_3():
    # Taller panel, thicker glass
    result = check_table_5_3(1.5, 'Annealed', 2.0, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 8, result['min_thickness_mm'], result['min_thickness_mm'] == 8),
    ]
    return report('3', 'Taller panel, thicker glass (1.5m)', checks)


def test_4():
    # Width-restricted row applies
    result = check_table_5_3(1.8, 'Toughened', 1.0, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
    ]
    return report('4', 'Width-restricted row applies', checks)


def test_5():
    # Width exceeds restricted row, falls to unrestricted
    result = check_table_5_3(1.8, 'Toughened', 1.5, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 8, result['min_thickness_mm'], result['min_thickness_mm'] == 8),
    ]
    return report('5', 'Width exceeds restricted row, falls to unrestricted', checks)


def test_6():
    # Glass type not permitted at this height
    result = check_table_5_3(3.0, 'Annealed', 1.0, 1, TABLE_5_3)

    checks = [
        ('status', 'NOT_PERMITTED', result['status'], result['status'] == 'NOT_PERMITTED'),
        ('min_thickness_mm', None, result['min_thickness_mm'], result['min_thickness_mm'] is None),
    ]
    return report('6', 'Glass type not permitted at this height', checks)


def test_7():
    # Laminated Toughened uses Toughened rows (Note 2)
    result = check_table_5_3(1.8, 'Laminated Toughened', 1.0, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
        (
            'glass_type_used', 'Toughened', result['glass_type_used'],
            result['glass_type_used'] == 'Toughened',
        ),
    ]
    return report('7', 'Laminated Toughened uses Toughened rows (Note 2)', checks)


def test_8():
    # The worked example - 2 butt joints, width within restricted row's limit
    result = check_table_5_3(1.8, 'Toughened', 1.0, 2, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
    ]
    return report('8', 'Worked example - 2 butt joints', checks)


def test_9():
    # Panel width exactly at the limit - boundary inclusive
    result = check_table_5_3(1.8, 'Toughened', 1.2, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 6, result['min_thickness_mm'], result['min_thickness_mm'] == 6),
    ]
    return report('9', 'Panel width exactly at the limit (1.2m)', checks)


def test_10():
    # Panel width just over the limit - falls to unrestricted row
    result = check_table_5_3(1.8, 'Toughened', 1.21, 1, TABLE_5_3)

    checks = [
        ('status', 'COMPLIANT', result['status'], result['status'] == 'COMPLIANT'),
        ('min_thickness_mm', 8, result['min_thickness_mm'], result['min_thickness_mm'] == 8),
    ]
    return report('10', 'Panel width just over the limit (1.21m)', checks)


def test_11():
    # Table 5.3-driven NO_COMPLIANT_THICKNESS (Mode 1, run_calculation()) -
    # untested since v1.13. With today's real stocked thickness lists, no
    # eligible glass type's Table 5.3 row-band minimum ever exceeds its
    # stocked maximum (confirmed by direct search across every eligible
    # glass type / height band / width combination) - the same class of
    # "structurally unreachable with real data" finding already documented
    # for Table 5.1's NON_COMPLIANT case. To exercise the code path
    # honestly without fabricating fake CSV rows, this test temporarily
    # monkeypatches GLASS_TYPE_THICKNESSES in engine.wind_load.checks.wind
    # (where check_glass_type() actually reads it - not a parameter) to cap
    # Monolithic Toughened's stock at 12mm, restored in a finally block so
    # no other test in this or any other module observes the patched value.
    #
    # Geometry: 3500mm x 2000mm, 2-edge, unrestricted-width row -> Table
    # 5.3 band 3.2-3.6m requires 19mm minimum (data/Table_5_3.csv). Wind
    # pressure kept low (ULS=0.1kPa/SLS=0.05kPa) so ULS/SLS both pass at
    # thin thicknesses (4mm/8mm) well under the patched 12mm cap - the
    # failure is unambiguously Table 5.3 exhausting the whole (patched)
    # stocked list with no PASS, not wind governing.
    orig_thicknesses = dict(wind_mod.GLASS_TYPE_THICKNESSES)
    wind_mod.GLASS_TYPE_THICKNESSES[('Monolithic', 'Toughened')] = [4, 5, 6, 8, 10, 12]

    try:
        results = run_calculation(
            csv_path=wind_csv_path,
            height_mm=3500, width_mm=2000,
            support_condition='2-edge', span_dimension='height',
            wind_pressure_uls=0.1, wind_pressure_sls=0.05,
            selected_glass_types=[('Monolithic', 'Toughened')],
            glazing_config='single',
            safety_glass_required=True,
            unframed_edge_condition='2-edge',
            csv_path_5_3=csv_path,
        )
    finally:
        wind_mod.GLASS_TYPE_THICKNESSES.clear()
        wind_mod.GLASS_TYPE_THICKNESSES.update(orig_thicknesses)

    result = results[0]
    trace_results = [t['result'] for t in result.get('table_5_3_trace', [])]

    checks = [
        ('status', 'NO_COMPLIANT_THICKNESS', result['status'],
         result['status'] == 'NO_COMPLIANT_THICKNESS'),
        ('uls_minimum_thickness_mm', 4, result.get('uls_minimum_thickness_mm'),
         result.get('uls_minimum_thickness_mm') == 4),
        ('sls_minimum_thickness_mm', 8, result.get('sls_minimum_thickness_mm'),
         result.get('sls_minimum_thickness_mm') == 8),
        ('table_5_3_trace all FAIL across the patched stock list (4/5/6/8/10/12mm)',
         ['FAIL'] * 6, trace_results, trace_results == ['FAIL'] * 6),
        ('table_5_3_trace required_min_thickness_mm', 19,
         result['table_5_3_trace'][0]['required_min_thickness_mm'],
         result['table_5_3_trace'][0]['required_min_thickness_mm'] == 19),
        ('message names the Table 5.3 minimum', True,
         '19mm' in result['message'], '19mm' in result['message']),
        ('GLASS_TYPE_THICKNESSES restored after the test', orig_thicknesses,
         dict(wind_mod.GLASS_TYPE_THICKNESSES),
         dict(wind_mod.GLASS_TYPE_THICKNESSES) == orig_thicknesses),
    ]
    return report('11', 'Table 5.3-driven NO_COMPLIANT_THICKNESS (Mode 1, monkeypatched stock list - real data has no reachable case)', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Table 5.3 Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [
        test_1, test_2, test_3, test_4, test_5,
        test_6, test_7, test_8, test_9, test_10,
        test_11,
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
