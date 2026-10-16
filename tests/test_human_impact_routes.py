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
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'fixed': {
                'unframed_edges': [],
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
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'fixed': {
                'unframed_edges': ['head'],
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
        'room': 'bathroom',
        'high_risk': False,
        'methods': {
            'fixed': {
                'unframed_edges': ['left', 'right'],
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
    # Sashless through the route: window, residential, sightline 300, sight
    # 1000 x 1400, span 1000. 5.5 skipped (sashless); 5.4 not exempt (width
    # over 500, height over 1000, sightline under 500) -> Grade A. The 5.15
    # MT row (limit 1000) covers 1000 -> 5; laminated rows (limit 750) do
    # not cover it. Mirrors test_human_impact.test_SF.
    data = post({
        'opening_type': 'window',
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'sashless': {'span_mm': 1000, 'sightline_mm': 300,
                         'sight_width_mm': 1000, 'sight_height_mm': 1400},
        },
    })
    result = data['results']['sashless']
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('monolithic_toughened ok/thickness', (True, 5.0), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5.0),
        ('laminated_toughened ok', False, lt['ok'], lt['ok'] is False),
    ]
    report('4', 'POST /human_impact/check - sashless, sightline 300, span 1000 -> Grade A, MT 5mm', checks)


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
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'fixed': {
                'unframed_edges': [],
                'sightline_mm': 1200,
                'panel_width_mm': 500,
                'panel_height_mm': 500,  # 0.25 m^2
            },
            'louvre': {
                'louvre_framing': 'fully',
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
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'fixed': {
                'unframed_edges': [],
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
        'room': 'neither',
        'high_risk': False,
        'methods': {
            'louvre': {
                'louvre_framing': 'partly',
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


def test_route_inc_1():
    # determine_fixed is imported by name into the app module, so patching
    # the module attribute swaps what the route calls. The route must pass
    # an Incomplete result through intact.
    from engine.shared.results import make_human_impact_incomplete
    answers = ['Which edges are unframed?']
    original = flask_app_module.determine_fixed
    flask_app_module.determine_fixed = lambda ctx: make_human_impact_incomplete(answers)
    try:
        data = post({
            'opening_type': 'door', 'reclassified_as_side_panel': False,
            'building_use': 'residential', 'room': 'neither', 'high_risk': False,
            'methods': {'fixed': {'unframed_edges': [], 'sightline_mm': 0}},
        })
    finally:
        flask_app_module.determine_fixed = original
    result = data['results']['fixed']
    checks = [
        ('success', True, data['success'], data['success'] is True),
        ('outcome', 'incomplete', result['outcome'], result['outcome'] == 'incomplete'),
        ('missing_answers', answers, result['missing_answers'], result['missing_answers'] == answers),
        ('grade_a_required', None, result['grade_a_required'], result['grade_a_required'] is None),
        ('types', [], result['types'], result['types'] == []),
    ]
    report('inc_1', 'POST /human_impact/check - Incomplete result passes through the route', checks)


def test_route_inc_2():
    door = post({
        'opening_type': 'door', 'reclassified_as_side_panel': False,
        'building_use': 'residential', 'room': 'neither', 'high_risk': False,
        'methods': {'fixed': {'unframed_edges': [], 'sightline_mm': 0,
                              'panel_width_mm': 100, 'panel_height_mm': 800}},
    })['results']['fixed']
    # Low-level residential window, partly framed: not assessed by this tool.
    oos = post({
        'opening_type': 'window', 'reclassified_as_side_panel': False,
        'building_use': 'residential', 'room': 'neither', 'high_risk': False,
        'methods': {'fixed': {'unframed_edges': ['left', 'right'], 'sightline_mm': 300,
                              'sight_width_mm': 900, 'sight_height_mm': 1500}},
    })['results']['fixed']
    checks = [
        ('door outcome', 'determined', door['outcome'], door['outcome'] == 'determined'),
        ('door has missing_answers []', [], door['missing_answers'], door['missing_answers'] == []),
        ('out-of-scope scope', False, oos['scope'], oos['scope'] is False),
        ('out-of-scope outcome', 'out_of_scope', oos['outcome'], oos['outcome'] == 'out_of_scope'),
    ]
    report('inc_2', 'POST /human_impact/check - determined and out_of_scope outcomes present', checks)


# ---------------------------------------------------------------------------
# TESTS route_fr_ — the edges / louvre framing answers through the route
# ---------------------------------------------------------------------------

from engine.shared.framing import MISSING_EDGES_TEXT, MISSING_LOUVRE_TEXT


def _request(opening_type, methods, reclassified=False):
    return {
        'opening_type': opening_type,
        'reclassified_as_side_panel': reclassified,
        'building_use': 'residential',
        'room': 'neither',
        'high_risk': False,
        'methods': methods,
    }


def _not_a_verdict(result):
    return (result['outcome'] == 'incomplete' and result['scope'] is False
            and result['grade_a_required'] is None and result['types'] == []
            and result['framing_info'] is None)


def test_route_fr_unanswered_fixed():
    checks = []
    for name, fixed in (('key absent', {'sightline_mm': 0}),
                        ('null', {'unframed_edges': None, 'sightline_mm': 0})):
        data = post(_request('door', {'fixed': fixed}))
        r = data['results']['fixed']
        checks.append((f'{name}: success', True, data['success'], data['success'] is True))
        checks.append((f'{name}: Incomplete with the question', [MISSING_EDGES_TEXT], r['missing_answers'],
                       _not_a_verdict(r) and r['missing_answers'] == [MISSING_EDGES_TEXT]))
    report('route_fr_1', 'Framing unanswered -> outcome incomplete, not a verdict', checks)


def test_route_fr_unanswered_louvre():
    base = {'sightline_mm': 800, 'blade_width_mm': 150, 'blade_length_mm': 900}
    checks = []
    for name, extra in (('key absent', {}), ('null', {'louvre_framing': None}),
                        ('unframed', {'louvre_framing': 'unframed'})):
        r = post(_request('window', {'louvre': dict(base, **extra)}))['results']['louvre']
        checks.append((name, [MISSING_LOUVRE_TEXT], r['missing_answers'],
                       _not_a_verdict(r) and r['missing_answers'] == [MISSING_LOUVRE_TEXT]))
    report('route_fr_2', 'Louvre framing unanswered or invalid -> outcome incomplete', checks)


def test_route_fr_stale_framing_key():
    fixed = post(_request('door', {'fixed': {'framing': 'fully', 'sightline_mm': 0}}))['results']['fixed']
    louvre = post(_request('window', {'louvre': {
        'framing': 'fully', 'sightline_mm': 800, 'blade_width_mm': 150, 'blade_length_mm': 900,
    }}))['results']['louvre']
    checks = [
        ('old fixed payload is Incomplete', True, _not_a_verdict(fixed), _not_a_verdict(fixed)),
        ('old louvre payload is Incomplete', True, _not_a_verdict(louvre), _not_a_verdict(louvre)),
    ]
    report('route_fr_3', "An old client sending only 'framing' is never read as fully framed", checks)


def test_route_fr_invalid_values():
    checks = []
    for name, value in (('unknown edge', ['top']), ('string', 'head'), ('duplicate', ['head', 'head'])):
        data = post(_request('door', {'fixed': {'unframed_edges': value, 'sightline_mm': 0}}))
        r = data['results']['fixed']
        checks.append((name, 'success true, Incomplete', (data['success'], r['outcome']),
                       data['success'] is True and _not_a_verdict(r)))
    report('route_fr_4', 'Invalid edges over the route -> Incomplete, no server error', checks)


def test_route_fr_door_opposite():
    data = post(_request('door', {'fixed': {'unframed_edges': ['left', 'right'], 'sightline_mm': 0}}))
    r = data['results']['fixed']
    mt = get_type(r, 'monolithic_toughened')
    ids = sorted(t['id'] for t in r['types'] if t['ok'])
    want_info = {'framing': 'unframed', 'unframed_count': 2, 'opposite_or_adjacent': 'opposite',
                 'opposite_pair': 'left_right', 'wind_route': 'pathway_2_two_edge'}
    checks = [
        ('D6: toughened only, 10 mm', (['laminated_toughened', 'monolithic_toughened'], 10),
         (ids, mt['min_thickness']),
         ids == ['laminated_toughened', 'monolithic_toughened'] and mt['min_thickness'] == 10),
        ('framing_info in the response', want_info, r['framing_info'], r['framing_info'] == want_info),
    ]
    report('route_fr_5', 'D6: door with left+right ticked via the route', checks)


def test_route_fr_none_unframed():
    r = post(_request('door', {'fixed': {'unframed_edges': [], 'sightline_mm': 0}}))['results']['fixed']
    ids = sorted(t['id'] for t in r['types'] if t['ok'])
    four = ['laminated_annealed', 'laminated_heat_strengthened', 'laminated_toughened', 'monolithic_toughened']
    checks = [
        ('fully framed door result', ('5.1', four), (r['table'], ids), r['table'] == '5.1' and ids == four),
        ('wind route', 'pathway_1', r['framing_info']['wind_route'], r['framing_info']['wind_route'] == 'pathway_1'),
    ]
    report('route_fr_6', 'Empty list = answered "none unframed" -> fully framed', checks)


def test_route_fr_louvre_door_partly():
    r = post(_request('door', {'louvre': {
        'louvre_framing': 'partly', 'sightline_mm': 0, 'blade_width_mm': 150, 'blade_length_mm': 900,
    }}))['results']['louvre']
    mt = get_type(r, 'monolithic_toughened')
    checks = [
        ('L3: toughened at 10 mm', 10, mt['min_thickness'], mt['min_thickness'] == 10),
        ('framing_info', ('unframed', 'pathway_2_two_edge'),
         (r['framing_info']['framing'], r['framing_info']['wind_route']),
         r['framing_info']['framing'] == 'unframed' and r['framing_info']['wind_route'] == 'pathway_2_two_edge'),
    ]
    report('route_fr_7', 'L3: louvre door answered partly via the route', checks)


def test_route_fr_sashless_info():
    r = post(_request('window', {'sashless': {
        'span_mm': 1000, 'sightline_mm': 900, 'sight_width_mm': 1000, 'sight_height_mm': 1400,
    }}))['results']['sashless']
    want = {'framing': 'partly', 'unframed_count': 2, 'opposite_or_adjacent': 'opposite',
            'opposite_pair': None, 'wind_route': 'pathway_2_two_edge'}
    report('route_fr_8', 'Sashless response carries the two-edge framing_info',
           [('framing_info', want, r['framing_info'], r['framing_info'] == want)])


def test_route_fr_exposed_ignored_at_zero():
    def run(exposed):
        return post(_request('side_panel', {'fixed': {
            'unframed_edges': [], 'exposed_edges': exposed, 'sightline_mm': 800,
            'panel_width_mm': 500, 'panel_height_mm': 500,
        }}))['results']['fixed']
    n, y = run('n'), run('y')
    same = (n['table'], n['types'], n['clauses']) == (y['table'], y['types'], y['clauses'])
    checks = [
        ('exposed y and n give the same result at zero ticks', True, same, same),
        ('fully framed side panel table', '5.1', y['table'], y['table'] == '5.1'),
    ]
    report('route_fr_9', 'exposed_edges has no effect when nothing is unframed', checks)


# ---------------------------------------------------------------------------
# TESTS route_room_ — the room question through the route (900 x 2000 mm
# opening, 1.8 m2; hand-derived expectations)
# ---------------------------------------------------------------------------

from engine.shared.room import MISSING_ROOM_TEXT

MIRRORS_NOTE = "Mirrors and backed annealed glass are not assessed by this tool."


def _room_request(opening_type, room, method_name, method, **top):
    body = {
        'opening_type': opening_type,
        'reclassified_as_side_panel': False,
        'building_use': 'residential',
        'high_risk': False,
        'methods': {method_name: method},
    }
    if room is not _ABSENT:
        body['room'] = room
    body.update(top)
    return body


_ABSENT = object()
_FIXED = {'sightline_mm': 1000, 'panel_width_mm': 900, 'panel_height_mm': 2000}


def test_route_room_unanswered():
    checks = []
    methods = {
        'fixed': dict(_FIXED, unframed_edges=[]),
        'louvre': {'sightline_mm': 1000, 'louvre_framing': 'fully', 'blade_width_mm': 150, 'blade_length_mm': 800},
        'sashless': {'span_mm': 1000, 'sightline_mm': 1000, 'sight_width_mm': 1000, 'sight_height_mm': 1000},
    }
    for name, method in methods.items():
        opening = 'window'
        for label, room in (('absent', _ABSENT), ('null', None)):
            data = post(_room_request(opening, room, name, method))
            r = data['results'][name]
            ok = (data['success'] is True and r['outcome'] == 'incomplete'
                  and r['missing_answers'] == [MISSING_ROOM_TEXT] and r['grade_a_required'] is None)
            checks.append((f'{name}, room {label}', 'incomplete, room question', r['outcome'], ok))
        old = _room_request(opening, _ABSENT, name, method, is_bathroom=True)
        r = post(old)['results'][name]
        checks.append((f'{name}, old client sending only is_bathroom', 'incomplete', r['outcome'],
                       r['outcome'] == 'incomplete'))
    report('route_room_1', 'Room unanswered (or only the old is_bathroom flag) -> Incomplete on every method', checks)


def test_route_room_bathroom_door():
    none = post(_room_request('door', 'bathroom', 'fixed', dict(_FIXED, unframed_edges=[])))['results']['fixed']
    one = post(_room_request('door', 'bathroom', 'fixed', dict(_FIXED, unframed_edges=['head'])))['results']['fixed']
    adj = post(_room_request('door', 'bathroom', 'fixed', dict(_FIXED, unframed_edges=['head', 'left'])))['results']['fixed']
    mt1, lt1 = get_type(one, 'monolithic_toughened'), get_type(one, 'laminated_toughened')
    mta = get_type(adj, 'monolithic_toughened')
    checks = [
        ('R6: none unframed, room rule only', ('5.1', ['5.8']), (none['table'], none['clauses']),
         none['table'] == '5.1' and none['clauses'] == ['5.8']),
        ('R7: one edge, partly rule (not the 10 mm door rule)', ('5.4', 5, 6),
         (one['table'], mt1['min_thickness'], lt1['min_thickness']),
         one['table'] == '5.4' and mt1['min_thickness'] == 5 and lt1['min_thickness'] == 6),
        ('R8: adjacent, unframed rule, no allowance', ('5.4', 6), (adj['table'], mta['min_thickness']),
         adj['table'] == '5.4' and mta['min_thickness'] == 6),
        ('mirrors note present for a bathroom', True, MIRRORS_NOTE in one['notes'], MIRRORS_NOTE in one['notes']),
    ]
    report('route_room_2', 'R6-R8, R13: a bathroom door through the route', checks)


def test_route_room_kitchen_window():
    kitchen = post(_room_request('window', 'kitchen', 'fixed',
                                 dict(_FIXED, unframed_edges=['head', 'left'], sight_width_mm=900,
                                      sight_height_mm=2000, opaque_or_patterned=True)))['results']['fixed']
    bathroom = post(_room_request('window', 'bathroom', 'fixed',
                                  dict(_FIXED, unframed_edges=['head', 'left'], sight_width_mm=900,
                                       sight_height_mm=2000, opaque_or_patterned=True)))['results']['fixed']
    mt = get_type(kitchen, 'monolithic_toughened')
    checks = [
        ('kitchen unframed: table and MT minimum', ('5.4', 6), (kitchen['table'], mt['min_thickness']),
         kitchen['table'] == '5.4' and mt['min_thickness'] == 6),
        ('kitchen equals bathroom result', True, kitchen['types'] == bathroom['types'],
         kitchen['types'] == bathroom['types'] and kitchen['table'] == bathroom['table']),
        ('no mirrors note for a kitchen', False, MIRRORS_NOTE in kitchen['notes'], MIRRORS_NOTE not in kitchen['notes']),
    ]
    report('route_room_3', 'R9, R13: a kitchen window through the route', checks)


def test_route_room_louvre():
    checks = []
    for answer in ('fully', 'partly'):
        r = post(_room_request('window', 'kitchen', 'louvre', {
            'sightline_mm': 1000, 'louvre_framing': answer, 'blade_width_mm': 150, 'blade_length_mm': 900,
        }))['results']['louvre']
        mt = get_type(r, 'monolithic_toughened')
        checks.append((f'louvre {answer} in a kitchen', ('5.4', 6), (r['table'], mt['min_thickness']),
                       r['table'] == '5.4' and mt['min_thickness'] == 6))
    report('route_room_4', 'R11: louvre in a kitchen follows the explicit rule via the route', checks)


def test_route_room_invalid_value():
    checks = []
    for value in ('Bathroom', 'shower', True, ['bathroom'], ''):
        data = post(_room_request('window', value, 'fixed', dict(_FIXED, unframed_edges=[])))
        r = data['results']['fixed']
        checks.append((f'{value!r}', 'success true, Incomplete', (data['success'], r['outcome']),
                       data['success'] is True and r['outcome'] == 'incomplete'
                       and r['missing_answers'] == [MISSING_ROOM_TEXT]))
    report('route_room_5', 'An invalid room value over the route -> Incomplete, no server error', checks)


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
             test_r1, test_r2, test_r3, test_r4, test_r5, test_r6, test_r7, test_r8, test_r9,
             test_route_inc_1, test_route_inc_2,
             test_route_fr_unanswered_fixed, test_route_fr_unanswered_louvre,
             test_route_fr_stale_framing_key, test_route_fr_invalid_values,
             test_route_fr_door_opposite, test_route_fr_none_unframed,
             test_route_fr_louvre_door_partly, test_route_fr_sashless_info,
             test_route_fr_exposed_ignored_at_zero,
             test_route_room_unanswered, test_route_room_bathroom_door,
             test_route_room_kitchen_window, test_route_room_louvre,
             test_route_room_invalid_value]
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
