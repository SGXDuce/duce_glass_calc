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
    # Prints each check, then asserts every one passed - a wrong actual
    # value now fails the test under pytest, not just under the __main__
    # script runner.
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    for label, expected, actual, ok in checks:
        assert ok, f"TEST {test_id} — {description}: {label}: expected={expected!r} actual={actual!r}"
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
    # Mirrors test_human_impact.test_1. Hand calculation: door, fully
    # framed, residential, sightline 0, 100 x 800mm = 0.08 m2 -> Clause 5.2
    # only -> Grade A, Table 5.1, four Grade A types ok=True; monolithic
    # annealed ok=False (not offered by this tool).
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
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('monolithic_annealed why', True, 'not offered by this tool' in (ma['why'] or ''),
         'not offered by this tool' in (ma['why'] or '')),
        ('allowed types', ['laminated_annealed', 'laminated_heat_strengthened', 'laminated_toughened', 'monolithic_toughened'], sorted(t['id'] for t in data['results']['fixed']['types'] if t['ok']),
         sorted(t['id'] for t in data['results']['fixed']['types'] if t['ok']) == ['laminated_annealed', 'laminated_heat_strengthened', 'laminated_toughened', 'monolithic_toughened']),
    ]
    report('1', 'POST /human_impact/check - door, fully framed, 0.08m² -> monolithic annealed not offered', checks)


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
    report('2', 'POST /human_impact/check - door, unframed -> toughened only, 10mm', checks)


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
    report('3', 'POST /human_impact/check - bathroom window, partly framed, 1.5m² -> Table 5.4', checks)


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
    report('4', 'POST /human_impact/check - sashless, span 900mm -> MT 5mm, LT blocked', checks)


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
        # Hand calculation: window reclassified as side panel, sightline 1200
        # (within the limit, stays a side panel), fully framed, 500 x 500mm
        # = 0.25 m2 -> Clause 5.3.1 only -> Grade A, Table 5.1; monolithic
        # annealed ok=False (not offered by this tool).
        ('fixed: monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('fixed: table', '5.1', fixed['table'], fixed['table'] == '5.1'),
        ('louvre result independently returned', True, 'grade_a_required' in louvre, 'grade_a_required' in louvre),
    ]
    report('5', 'POST /human_impact/check - multiple methods + window reclassification', checks)

# ---------------------------------------------------------------------------
# TESTS - side panel height test (1200mm) applied per method by the route
# ---------------------------------------------------------------------------

DOWNGRADE_SENTENCE = (
    "Treated as a window: the bottom of the glass is above 1200 mm, so the "
    "side panel rules (Clause 5.3.1) do not apply. Other provisions were "
    "still checked."
)


def _fixed_side_panel_request(opening_type, reclassified, sightline_mm):
    # Base: test_5's fixed method - fully framed, 0.25 m2 - only opening
    # type, reclassification flag and sightline vary.
    return {
        'opening_type': opening_type,
        'reclassified_as_side_panel': reclassified,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'fixed': {
                'framing': 'fully',
                'sightline_mm': sightline_mm,
                'panel_width_mm': 500,
                'panel_height_mm': 500,  # 0.25 m^2
            },
        },
    }


def test_r1():
    data = post(_fixed_side_panel_request('window', True, 1200))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 in clauses', True, '5.3.1' in fixed['clauses'], '5.3.1' in fixed['clauses']),
        ('grade_a_required', True, fixed['grade_a_required'], fixed['grade_a_required'] is True),
    ]
    report('R1', 'window reclassified Yes, sightline 1200 (inclusive) -> still a side panel', checks)


def test_r2():
    data = post(_fixed_side_panel_request('window', True, 1201))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 not in clauses', False, '5.3.1' in fixed['clauses'], '5.3.1' not in fixed['clauses']),
        ('grade_a_required', False, fixed['grade_a_required'], fixed['grade_a_required'] is False),
        ('trail has downgrade sentence', True, DOWNGRADE_SENTENCE in fixed['trail'],
         DOWNGRADE_SENTENCE in fixed['trail']),
    ]
    report('R2', 'window reclassified Yes, sightline 1201 -> treated as a window', checks)


def test_r3():
    data = post(_fixed_side_panel_request('side_panel', False, 800))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 in clauses', True, '5.3.1' in fixed['clauses'], '5.3.1' in fixed['clauses']),
        ('grade_a_required', True, fixed['grade_a_required'], fixed['grade_a_required'] is True),
    ]
    report('R3', 'side panel picked directly, sightline 800 -> side panel', checks)


def test_r4():
    data = post(_fixed_side_panel_request('side_panel', False, 1500))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 not in clauses', False, '5.3.1' in fixed['clauses'], '5.3.1' not in fixed['clauses']),
        ('grade_a_required', False, fixed['grade_a_required'], fixed['grade_a_required'] is False),
        ('trail has downgrade sentence', True, DOWNGRADE_SENTENCE in fixed['trail'],
         DOWNGRADE_SENTENCE in fixed['trail']),
    ]
    report('R4', 'side panel picked directly, sightline 1500 -> treated as a window', checks)


def test_r5():
    data = post(_fixed_side_panel_request('window', False, 800))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 not in clauses', False, '5.3.1' in fixed['clauses'], '5.3.1' not in fixed['clauses']),
        ('grade_a_required', False, fixed['grade_a_required'], fixed['grade_a_required'] is False),
    ]
    report('R5', 'window, reclassified No, sightline 800 -> unchanged, not a side panel', checks)


def test_r6():
    data = post(_fixed_side_panel_request('side_panel', False, None))
    fixed = data['results']['fixed']
    checks = [
        ('5.3.1 in clauses', True, '5.3.1' in fixed['clauses'], '5.3.1' in fixed['clauses']),
    ]
    report('R6', 'side panel, sightline missing -> the choice stands', checks)


def _louvre_side_panel_request(exposed_edges):
    return {
        'opening_type': 'side_panel',
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
        'methods': {
            'louvre': {
                'framing': 'partly',
                'exposed_edges': exposed_edges,
                'sightline_mm': 800,
                'blade_width_mm': 150,
                'blade_length_mm': 900,
            },
        },
    }


def _only_allowed_type(result):
    return [t['id'] for t in result['types'] if t['ok']]


def test_r7():
    result = post(_louvre_side_panel_request('n'))['results']['louvre']
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 5), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5),
        ('only allowed type', ['monolithic_toughened'], _only_allowed_type(result),
         _only_allowed_type(result) == ['monolithic_toughened']),
    ]
    report('R7', 'louvre side panel, partly framed, exposed_edges n -> MT 5mm only', checks)


def test_r8():
    result = post(_louvre_side_panel_request('y'))['results']['louvre']
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 10), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 10),
    ]
    report('R8', 'louvre side panel, partly framed, exposed_edges y -> MT 10mm', checks)


def test_r9():
    from engine.shared.side_panel import sightline_within_side_panel_limit
    checks = [
        ('1200', True, sightline_within_side_panel_limit(1200), sightline_within_side_panel_limit(1200) is True),
        ('1201', False, sightline_within_side_panel_limit(1201), sightline_within_side_panel_limit(1201) is False),
        ('None', False, sightline_within_side_panel_limit(None), sightline_within_side_panel_limit(None) is False),
    ]
    report('R9', 'sightline_within_side_panel_limit boundary and None', checks)


def run_tests():
    # report() now asserts internally, so a test function either completes
    # (pass) or raises AssertionError (fail) - it no longer returns a bool.
    # This loop catches per-test AssertionErrors itself so the script-mode
    # runner still tallies and prints a pass count, matching its previous
    # behaviour.
    print('=' * 70)
    print('  AS 1288 Calculator — Human Impact Route Wiring Test')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5,
             test_r1, test_r2, test_r3, test_r4, test_r5, test_r6, test_r7, test_r8, test_r9]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"    ASSERTION FAILED: {e}")
    total = len(tests)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
