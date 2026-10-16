# AS 1288 Glass Thickness Calculator - Framing Derivation Tests
# Validates engine/shared/framing.py: the "which edges are unframed?" answer
# becomes a framing class plus a stored (not acted on) wind route. Expected
# values are written out by hand, not computed with the module's own logic.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_framing.py

import ast
import copy
import os

from engine.shared.framing import (
    derive_from_edges, derive_from_louvre, sashless_framing_info,
    MISSING_EDGES_TEXT, MISSING_LOUVRE_TEXT,
)


def report(test_id, description, checks):
    overall = all(ok for _, _, _, ok in checks)
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {label}: expected={expected!r} actual={actual!r}")
    for label, expected, actual, ok in checks:
        assert ok, f"TEST {test_id} — {description}: {label}: expected={expected!r} actual={actual!r}"
    return overall


def info_tuple(info):
    return (info['framing'], info['unframed_count'], info['opposite_or_adjacent'],
            info['opposite_pair'], info['wind_route'])


P1, P2_3, P2_2, NA = 'pathway_1', 'pathway_2_three_edge', 'pathway_2_two_edge', 'wind_not_assessed'

# Hand-written table for every one of the 16 edge subsets.
# key: edges ticked; value: (count, shape, pair, wind_route)
GEOMETRY = {
    (): (0, None, None, P1),
    ('head',): (1, None, None, P2_3),
    ('sill',): (1, None, None, P2_3),
    ('left',): (1, None, None, P2_3),
    ('right',): (1, None, None, P2_3),
    ('head', 'sill'): (2, 'opposite', 'head_sill', P2_2),
    ('left', 'right'): (2, 'opposite', 'left_right', P2_2),
    ('head', 'left'): (2, 'adjacent', None, NA),
    ('head', 'right'): (2, 'adjacent', None, NA),
    ('sill', 'left'): (2, 'adjacent', None, NA),
    ('sill', 'right'): (2, 'adjacent', None, NA),
    ('head', 'sill', 'left'): (3, None, None, NA),
    ('head', 'sill', 'right'): (3, None, None, NA),
    ('head', 'left', 'right'): (3, None, None, NA),
    ('sill', 'left', 'right'): (3, None, None, NA),
    ('head', 'sill', 'left', 'right'): (4, None, None, NA),
}

# Framing class for a window, panel or side panel, written out by hand.
NON_DOOR_FRAMING = {
    (): 'fully',
    ('head',): 'partly', ('sill',): 'partly', ('left',): 'partly', ('right',): 'partly',
    ('head', 'sill'): 'partly', ('left', 'right'): 'partly',
    ('head', 'left'): 'unframed', ('head', 'right'): 'unframed',
    ('sill', 'left'): 'unframed', ('sill', 'right'): 'unframed',
    ('head', 'sill', 'left'): 'unframed', ('head', 'sill', 'right'): 'unframed',
    ('head', 'left', 'right'): 'unframed', ('sill', 'left', 'right'): 'unframed',
    ('head', 'sill', 'left', 'right'): 'unframed',
}


def _table_checks(is_door):
    checks = []
    for edges, (count, shape, pair, route) in GEOMETRY.items():
        if is_door:
            framing = 'fully' if count == 0 else 'unframed'
        else:
            framing = NON_DOOR_FRAMING[edges]
        info, missing = derive_from_edges(list(edges), is_door)
        want = (framing, count, shape, pair, route)
        got = info_tuple(info) if info else None
        checks.append((f'{list(edges)}', want, got, got == want and missing is None))
    return checks


def test_fr_nondoor_table():
    report('fr_1', 'Window / panel / side panel: all 16 edge subsets', _table_checks(False))


def test_fr_door_table():
    report('fr_2', 'Door: none ticked is fully, any tick is unframed, all 16 subsets', _table_checks(True))


def test_fr_two_edge_pairs():
    adjacent = [('head', 'left'), ('head', 'right'), ('sill', 'left'), ('sill', 'right')]
    opposite = [('head', 'sill'), ('left', 'right')]
    checks = []
    for pair in adjacent:
        info, _ = derive_from_edges(list(pair), False)
        got = (info['framing'], info['opposite_or_adjacent'], info['wind_route'])
        checks.append((f'adjacent {pair}', ('unframed', 'adjacent', NA), got,
                       got == ('unframed', 'adjacent', NA)))
    for pair in opposite:
        info, _ = derive_from_edges(list(pair), False)
        got = (info['framing'], info['opposite_or_adjacent'], info['wind_route'])
        checks.append((f'opposite {pair}', ('partly', 'opposite', P2_2), got,
                       got == ('partly', 'opposite', P2_2)))
    report('fr_3', 'Exactly two ticks: four adjacent pairs vs two opposite pairs', checks)


def test_fr_door_opposite_pair_unframed():
    checks = []
    for pair in (['left', 'right'], ['head', 'sill']):
        info, _ = derive_from_edges(pair, True)
        got = (info['framing'], info['opposite_or_adjacent'], info['wind_route'])
        checks.append((f'door {pair}', ('unframed', 'opposite', P2_2), got,
                       got == ('unframed', 'opposite', P2_2)))
    report('fr_4', 'D6: door with two opposite ticks still counts as unframed', checks)


def test_fr_louvre_nondoor():
    fully, m1 = derive_from_louvre('fully', False)
    partly, m2 = derive_from_louvre('partly', False)
    checks = [
        ('fully', ('fully', 0, None, None, P1), info_tuple(fully),
         info_tuple(fully) == ('fully', 0, None, None, P1) and m1 is None),
        ('partly', ('partly', 2, 'opposite', None, P2_2), info_tuple(partly),
         info_tuple(partly) == ('partly', 2, 'opposite', None, P2_2) and m2 is None),
    ]
    report('fr_5', 'Louvre window: fully and partly (two opposite edges)', checks)


def test_fr_louvre_door():
    fully, _ = derive_from_louvre('fully', True)
    partly, _ = derive_from_louvre('partly', True)
    checks = [
        ('door fully', ('fully', 0, None, None, P1), info_tuple(fully),
         info_tuple(fully) == ('fully', 0, None, None, P1)),
        ('L3: door partly counts as unframed', ('unframed', 2, 'opposite', None, P2_2),
         info_tuple(partly), info_tuple(partly) == ('unframed', 2, 'opposite', None, P2_2)),
    ]
    report('fr_6', 'L3: louvre door answered partly counts as unframed', checks)


def test_fr_sashless():
    info = sashless_framing_info()
    want = ('partly', 2, 'opposite', None, P2_2)
    info['framing'] = 'changed'
    fresh = sashless_framing_info()
    checks = [
        ('always partly, two opposite, two-edge route', want, info_tuple(fresh),
         info_tuple(fresh) == want),
        ('each call returns a fresh dict', 'partly', fresh['framing'], fresh['framing'] == 'partly'),
    ]
    report('fr_7', 'Sashless: no question, always partly with two opposite edges', checks)


def test_fr_edge_order():
    a, _ = derive_from_edges(['right', 'left'], False)
    b, _ = derive_from_edges(['left', 'right'], False)
    c, _ = derive_from_edges(['sill', 'head'], True)
    checks = [
        ('right,left equals left,right', info_tuple(b), info_tuple(a), a == b),
        ('sill,head is the head/sill pair', 'head_sill', c['opposite_pair'], c['opposite_pair'] == 'head_sill'),
    ]
    report('fr_8', 'Tick order does not change the result', checks)


def test_fr_empty_list_vs_none():
    answered, m1 = derive_from_edges([], False)
    unanswered, m2 = derive_from_edges(None, False)
    checks = [
        ('[] is answered: fully framed', ('fully', None), (answered['framing'], m1),
         answered['framing'] == 'fully' and m1 is None),
        ('None is unanswered', (None, [MISSING_EDGES_TEXT]), (unanswered, m2),
         unanswered is None and m2 == [MISSING_EDGES_TEXT]),
    ]
    report('fr_9', 'An empty list is an answer; None is not', checks)


def _bad(result):
    info, missing = result
    return (info is None and isinstance(missing, list) and len(missing) > 0
            and all(isinstance(m, str) and m.strip() for m in missing))


def test_fr_invalid_edges():
    bad_values = [None, 'head', ('head',), {'head'}, {'head': 1}, True, 0, '',
                  ['top'], ['Head'], ['head', 'head'], [1], [None], ['head', ''],
                  [['head']], ['head', 'sill', 'sill']]
    checks = []
    for v in bad_values:
        for is_door in (False, True):
            r = derive_from_edges(v, is_door)
            checks.append((f'{v!r} door={is_door}', 'Incomplete, no framing', r, _bad(r)))
    report('fr_10', 'Invalid edges input never gives a framing', checks)


def test_fr_invalid_louvre():
    bad_values = [None, 'unframed', 'Fully', 'PARTLY', '', True, 1, ['fully'], 'fully ']
    checks = []
    for v in bad_values:
        for is_door in (False, True):
            r = derive_from_louvre(v, is_door)
            checks.append((f'{v!r} door={is_door}', 'Incomplete, no framing', r, _bad(r)
                           and r[1] == [MISSING_LOUVRE_TEXT]))
    report('fr_11', 'Invalid louvre answer never gives a framing', checks)


def test_fr_input_not_mutated():
    edges = ['right', 'head']
    before = copy.deepcopy(edges)
    derive_from_edges(edges, False)
    report('fr_12', 'Derivation does not change its input list',
           [('list unchanged', before, edges, edges == before)])


def test_fr_no_forbidden_imports():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine', 'shared', 'framing.py')
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or '')
    forbidden = ('wind_load', 'silicone_bite', 'combined', 'human_impact')
    hits = [n for n in names if any(f in n for f in forbidden)]
    report('fr_13', 'framing.py imports nothing from the four engines',
           [('forbidden imports', [], hits, hits == [])])
