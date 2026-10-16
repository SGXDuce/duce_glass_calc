# AS 1288 Glass Thickness Calculator - stocked thickness guard tests
# Duce Timber Windows and Doors
#
# WHY THIS EXISTS
# These tests were added BEFORE GLASS_TYPE_THICKNESSES (the stocked nominal
# thicknesses per glass type and subtype) moves out of
# engine/wind_load/constants.py into a CSV plus a shared module. They pin the
# key set, per-list order and type, the exact contents (against
# tests/golden/glass_type_thicknesses_golden.json, generated once from the
# pre-move code and never regenerated), the shared object identity that
# tests/test_table_5_3.py test_11 relies on, and in-place mutation/restore.
# No stock values are typed here.

import json
import os
import re

import engine.wind_load.checks.wind as wind_mod
from engine.combined import pathway3, pathway4
from engine.wind_load import constants
from engine.wind_load.constants import (
    GLASS_TYPE_THICKNESSES, SAFETY_GLASS_CATEGORY, SAFETY_GLASS_INELIGIBLE,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SNAPSHOT_PATH = os.path.join(HERE, 'golden', 'glass_type_thicknesses_golden.json')


def _snapshot_rows():
    with open(SNAPSHOT_PATH, encoding='utf-8') as f:
        return json.load(f)


def _snapshot_dict():
    return {(r['glass_type'], r['glass_subtype']): list(r['thicknesses'])
            for r in _snapshot_rows()}


# 1. Key set and key order
def test_stock_keys():
    assert set(GLASS_TYPE_THICKNESSES) == set(SAFETY_GLASS_CATEGORY) | set(SAFETY_GLASS_INELIGIBLE)
    assert len(GLASS_TYPE_THICKNESSES) == 6
    snapshot_keys = [(r['glass_type'], r['glass_subtype']) for r in _snapshot_rows()]
    assert snapshot_keys == list(GLASS_TYPE_THICKNESSES.keys())


# 2. List properties
def test_stock_list_properties():
    for key, values in GLASS_TYPE_THICKNESSES.items():
        assert isinstance(values, list), key
        assert values, key
        for x in values:
            assert type(x) is int, (key, x)
        assert all(a < b for a, b in zip(values, values[1:])), key
        assert len(set(values)) == len(values), key


# 3. Exact contents, including per-list order
def test_stock_snapshot():
    assert GLASS_TYPE_THICKNESSES == _snapshot_dict()
    for key, values in _snapshot_dict().items():
        assert GLASS_TYPE_THICKNESSES[key] == values, key


# 4. One shared object, no second copy
def test_stock_shared_identity():
    assert wind_mod.GLASS_TYPE_THICKNESSES is constants.GLASS_TYPE_THICKNESSES
    assert pathway3.GLASS_TYPE_THICKNESSES is constants.GLASS_TYPE_THICKNESSES
    assert pathway4.GLASS_TYPE_THICKNESSES is constants.GLASS_TYPE_THICKNESSES

    assignment = re.compile(r'^\s*GLASS_TYPE_THICKNESSES\s*(?::[^=\n]*)?=(?!=)', re.MULTILINE)
    for rel in ('engine/wind_load/checks/wind.py',
                'engine/combined/pathway3.py',
                'engine/combined/pathway4.py'):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            source = f.read()
        assert not assignment.search(source), rel


# 5. In-place patch through the wind module is seen everywhere, and restores
def test_stock_mutation_restore():
    snapshot = _snapshot_dict()
    orig = dict(GLASS_TYPE_THICKNESSES)
    key = next(iter(snapshot))
    try:
        wind_mod.GLASS_TYPE_THICKNESSES[key] = snapshot[key][:-1]
        assert constants.GLASS_TYPE_THICKNESSES[key] == snapshot[key][:-1]
        assert constants.GLASS_TYPE_THICKNESSES != snapshot
    finally:
        wind_mod.GLASS_TYPE_THICKNESSES.clear()
        wind_mod.GLASS_TYPE_THICKNESSES.update(orig)
    assert constants.GLASS_TYPE_THICKNESSES == snapshot
    assert list(constants.GLASS_TYPE_THICKNESSES.keys()) == list(snapshot.keys())
