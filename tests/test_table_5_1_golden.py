# AS 1288 Glass Thickness Calculator - Table 5.1 golden snapshot test
# Duce Timber Windows and Doors
#
# WHY THIS EXISTS
# The next change moves the Table 5.1 data and its area search into one
# shared module. That move must not change any result. This test re-runs
# the same calls that tests/golden/make_table_5_1_golden.py made against
# the code as it was before the move, and checks every output still equals
# the saved snapshot (tests/golden/table_5_1_golden.json) exactly.
#
# One test per group: (a) the area-limit lookup, (b) the Pathway 3 and 4
# search helpers, (c) Pathway 1 full results, (d) Pathway 3 at 90 degrees
# and Pathway 4 full results. A failure prints the first key path that
# differs.

import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    'make_table_5_1_golden', os.path.join(HERE, 'golden', 'make_table_5_1_golden.py'))
golden = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(golden)


def _first_difference(expected, actual, path='$'):
    """Returns a description of the first difference, or None if equal."""
    if type(expected) is not type(actual):
        return (f"{path}: expected {expected!r} ({type(expected).__name__}), "
                f"actual {actual!r} ({type(actual).__name__})")
    if isinstance(expected, dict):
        for k in sorted(set(expected) | set(actual)):
            if k not in actual:
                return f"{path}.{k}: missing from actual"
            if k not in expected:
                return f"{path}.{k}: not in snapshot"
            d = _first_difference(expected[k], actual[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: length expected {len(expected)}, actual {len(actual)}"
        for i, (e, a) in enumerate(zip(expected, actual)):
            d = _first_difference(e, a, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if expected == actual else f"{path}: expected {expected!r}, actual {actual!r}"


def _check(group):
    with open(golden.JSON_PATH, encoding='utf-8') as f:
        expected = json.load(f)[group]
    # Round-trip through JSON so the fresh output is compared in exactly the
    # form the snapshot was stored in.
    actual = json.loads(json.dumps(golden.COLLECTORS[group]()))
    diff = _first_difference(expected, actual)
    assert diff is None, f"Table 5.1 snapshot mismatch in group {group}, first difference at {diff}"


def test_golden_a_max_area():
    _check('a_max_area')


def test_golden_b_searches():
    _check('b_searches')


def test_golden_c_pathway1():
    _check('c_pathway1')


def test_golden_d_pathways_3_and_4():
    _check('d_pathways_3_and_4')
