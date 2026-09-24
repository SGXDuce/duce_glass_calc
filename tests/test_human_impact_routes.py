# AS 1288 Glass Thickness Calculator - Human Impact Route Wiring Test
# Confirms /human_impact/check correctly translates request JSON into the
# engine.human_impact ctx shape and returns the same result the unit tests
# in tests/test_human_impact.py already proved correct. This is NOT
# re-testing rule correctness (that's test_human_impact.py's job) - only
# that the Flask route is a faithful, lossless translation layer.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_human_impact_routes

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'interfaces', 'flask_app'))

import app as flask_app_module

client = flask_app_module.app.test_client()


def report(test_id, description, checks):
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    return overall


def post(payload):
    r = client.post('/human_impact/check', json=payload)
    return r.get_json()


def get_type(result, type_id):
    return next(t for t in result['types'] if t['id'] == type_id)


# ---------------------------------------------------------------------------
# TESTS — reused directly from test_human_impact.py's cases 1, 3, 11, 20
# ---------------------------------------------------------------------------

def test_1():
    # Mirrors test_human_impact.test_1: door, fully framed, 0.08m2/100mm ->
    # monolithic annealed ok=True at 3mm.
    data = post({
        'opening_type': 'door',
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'fixed': {
                'framing': 'fully',
                'sightline_mm': 0,
                'panel_width_mm': 100,
                'panel_height_mm': 800,
            }
        },
    })
    ma = get_type(data['results']['fixed'], 'monolithic_annealed')
    checks = [
        ('success', True, data['success'], data['success'] is True),
        ('monolithic_annealed ok', True, ma['ok'], ma['ok'] is True),
        ('monolithic_annealed min_thickness', 3.0, ma['min_thickness'], ma['min_thickness'] == 3.0),
    ]
    return report('1', 'POST /human_impact/check - door, fully framed, 0.08m² -> annealed 3mm', checks)


def test_2():
    # Mirrors test_human_impact.test_3: door, unframed -> only toughened
    # family ok, 10mm.
    data = post({
        'opening_type': 'door',
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'fixed': {
                'framing': 'unframed',
                'sightline_mm': 0,
            }
        },
    })
    mt = get_type(data['results']['fixed'], 'monolithic_toughened')
    ma = get_type(data['results']['fixed'], 'monolithic_annealed')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 10), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 10),
        ('monolithic_annealed blocked', False, ma['ok'], ma['ok'] is False),
    ]
    return report('2', 'POST /human_impact/check - door, unframed -> toughened only, 10mm', checks)


def test_3():
    # Mirrors test_human_impact.test_11: bathroom window, partly framed,
    # area 1.5m² -> table 5.4, MT 5mm / LT flat 6mm.
    data = post({
        'opening_type': 'window',
        'reclassified_as_side_panel': False,
        'building_use': 'other',
        'is_bathroom': True,
        'high_risk': False,
        'methods': {
            'fixed': {
                'framing': 'partly',
                'sightline_mm': 1000,
                'panel_width_mm': 1000,
                'panel_height_mm': 1500,  # 1.5m^2
            }
        },
    })
    result = data['results']['fixed']
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('table', '5.4', result['table'], result['table'] == '5.4'),
        ('monolithic_toughened min_thickness', 5.0, mt['min_thickness'], mt['min_thickness'] == 5.0),
        ('laminated_toughened min_thickness', 6.0, lt['min_thickness'], lt['min_thickness'] == 6.0),
    ]
    return report('3', 'POST /human_impact/check - bathroom window, partly framed, 1.5m² -> Table 5.4', checks)


def test_4():
    # Mirrors test_human_impact.test_20: sashless, span 900mm -> MT ok/5mm,
    # LT blocked (exceeds 750mm cap).
    data = post({
        'opening_type': 'window',
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'sashless': {'span_mm': 900},
        },
    })
    result = data['results']['sashless']
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 5.0), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5.0),
        ('laminated_toughened ok', False, lt['ok'], lt['ok'] is False),
    ]
    return report('4', 'POST /human_impact/check - sashless, span 900mm -> MT 5mm, LT blocked', checks)


def test_5():
    # Confirms multiple methods in one request each get their own result,
    # and the window-reclassified-as-side-panel flag actually reaches the
    # engine (mirrors test_human_impact.test_9's exemption path, but via
    # the reclassification flag rather than opening_type='side_panel'
    # directly - this is the route's own translation responsibility).
    data = post({
        'opening_type': 'window',
        'reclassified_as_side_panel': True,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'fixed': {
                'framing': 'fully',
                'sightline_mm': 1200,
                'panel_width_mm': 500,
                'panel_height_mm': 500,  # 0.25 m^2
            },
            'louvre': {
                'framing': 'fully',
                'sightline_mm': 1200,
                'blade_width_mm': 150,
                'blade_length_mm': 800,
            },
        },
    })
    fixed = data['results']['fixed']
    louvre = data['results']['louvre']
    ma = get_type(fixed, 'monolithic_annealed')
    checks = [
        ('both methods present in response', True,
         'fixed' in data['results'] and 'louvre' in data['results'],
         'fixed' in data['results'] and 'louvre' in data['results']),
        ('reclassified window matched as side panel (5.3.1)', True,
         '5.3.1' in fixed['clauses'], '5.3.1' in fixed['clauses']),
        ('fixed: monolithic_annealed ok at 5mm (0.25m² side panel cap)', (True, 5.0),
         (ma['ok'], ma['min_thickness']), ma['ok'] is True and ma['min_thickness'] == 5.0),
        ('louvre result independently returned', True, 'grade_a_required' in louvre, 'grade_a_required' in louvre),
    ]
    return report('5', 'POST /human_impact/check - multiple methods + window reclassification', checks)


def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Human Impact Route Wiring Test')
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
