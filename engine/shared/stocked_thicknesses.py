# AS 1288 Glass Thickness Calculator
# engine/shared/stocked_thicknesses.py
#
# Stocked nominal thicknesses (mm) per glass type and subtype, read from
# data/Stocked_Glass_Thicknesses.csv. These are Duce stock sizes, not AS 1288
# table values. Shared so that wind_load and human_impact can both read the
# list without importing each other. Pure lookup logic - no Flask, no UI
# code, no dependency on wind_load.
#
# Row order in the CSV is the order returned: subtypes in first-appearance
# order, each subtype's thicknesses in row order. Nothing is sorted or
# deduplicated. Callers always receive fresh dicts and lists, never the
# cached internals.

import csv
import functools
import os

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')

THICKNESSES_FILE = 'Stocked_Glass_Thicknesses.csv'


@functools.lru_cache(maxsize=None)
def _load_dir(data_dir):
    grouped = {}
    with open(os.path.join(data_dir, THICKNESSES_FILE), newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key = (row['glass_type'], row['glass_subtype'])
            grouped.setdefault(key, []).append(int(row['nominal_thickness_mm']))
    return tuple((key, tuple(values)) for key, values in grouped.items())


def _load(data_dir=None):
    return _load_dir(DEFAULT_DATA_DIR if data_dir is None else data_dir)


def stocked_thicknesses(data_dir=None):
    """(glass_type, glass_subtype) -> [nominal thickness, ...], in CSV order. Fresh dict and lists."""
    return {key: list(values) for key, values in _load(data_dir)}


def thicknesses_for(glass_type, glass_subtype, data_dir=None):
    """Fresh list of stocked thicknesses, or None for an unknown pair (like dict.get)."""
    for key, values in _load(data_dir):
        if key == (glass_type, glass_subtype):
            return list(values)
    return None
