# AS 1288 Glass Thickness Calculator
# engine/shared/table_5_1.py
#
# AS 1288 Table 5.1 - safety glass (human impact) maximum area lookup and
# thickness search. Category assignment per glass subtype comes from
# data/Table_5_1_Categories.csv; area limits per category and nominal
# thickness come from data/Table_5_1_Max_Area.csv. No table values live in
# this module. Shared across wind_load and the combined pathways. Pure
# lookup logic - no Flask, no UI code, no dependency on wind_load.

import csv
import functools
import os

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')

CATEGORIES_FILE = 'Table_5_1_Categories.csv'
MAX_AREA_FILE = 'Table_5_1_Max_Area.csv'

INELIGIBLE = 'ineligible'
# Thickness above which the limit is extrapolated at slope 1 (1 m2 per mm)
# from the anchor row.
ANCHOR_THICKNESS_MM = 12


@functools.lru_cache(maxsize=None)
def _load_dir(data_dir):
    categories = {}
    ineligible = []
    with open(os.path.join(data_dir, CATEGORIES_FILE), newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key = (row['glass_type'], row['glass_subtype'])
            if row['category'] == INELIGIBLE:
                ineligible.append(key)
            else:
                categories[key] = row['category']

    areas = {}
    with open(os.path.join(data_dir, MAX_AREA_FILE), newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            areas.setdefault(row['category'], {})[int(row['nominal_thickness_mm'])] = (
                float(row['max_area_m2']), row['monolithic_only'] == 'yes'
            )
    return {'categories': categories, 'ineligible': ineligible, 'areas': areas}


def _load(data_dir=None):
    return _load_dir(DEFAULT_DATA_DIR if data_dir is None else data_dir)


def safety_glass_category(data_dir=None):
    """Eligible (glass_type, glass_subtype) -> category, in CSV order."""
    return dict(_load(data_dir)['categories'])


def safety_glass_ineligible(data_dir=None):
    """Ineligible (glass_type, glass_subtype) tuples, in CSV order."""
    return list(_load(data_dir)['ineligible'])


def is_ineligible(glass_type, glass_subtype, data_dir=None):
    return (glass_type, glass_subtype) in _load(data_dir)['ineligible']


def max_area(glass_type, glass_subtype, nominal_thickness_mm, area_factor=1.0, data_dir=None):
    """
    Maximum permitted area in m2 under AS 1288 Table 5.1, or None if the
    subtype has no category / is ineligible, or the row is flagged
    monolithic_only and the glass is Laminated.

    Above the anchor thickness the limit is the anchor row's value plus
    the thickness excess (1 m2 per mm). Otherwise the lookup is on the raw
    argument, so a thickness with no row (e.g. 6.5) gives None.
    area_factor multiplies the final limit (including extrapolated ones)
    and is not applied to None.
    """
    data = _load(data_dir)
    category = data['categories'].get((glass_type, glass_subtype))
    if category is None:
        return None
    table = data['areas'][category]

    if nominal_thickness_mm > ANCHOR_THICKNESS_MM:
        limit = table[ANCHOR_THICKNESS_MM][0] + (nominal_thickness_mm - ANCHOR_THICKNESS_MM)
    else:
        entry = table.get(nominal_thickness_mm)
        if entry is None:
            return None
        value, monolithic_only = entry
        if monolithic_only and glass_type == 'Laminated':
            return None
        limit = value

    if area_factor != 1.0:
        limit = limit * area_factor
    return limit


def search(glass_type, glass_subtype, panel_area_m2, thickness_list,
           area_factor=1.0, round_area=None, data_dir=None):
    """
    Ascending scan of thickness_list for the first thickness whose Table
    5.1 limit admits panel_area_m2. Returns
    {'status': 'INELIGIBLE' | 'COMPLIANT' | 'NON_COMPLIANT',
     'minimum_thickness_mm', 'trace'}.

    The ineligible gate runs first and returns an empty trace. Thicknesses
    with no limit are skipped. The comparison always uses the raw area;
    round_area (decimal places, default None) affects ONLY the reported
    'actual_area' in the trace. The reported 'max_area' is the effective
    (area_factor-scaled) limit.
    """
    if is_ineligible(glass_type, glass_subtype, data_dir):
        return {'status': 'INELIGIBLE', 'minimum_thickness_mm': None, 'trace': []}

    reported_area = panel_area_m2 if round_area is None else round(panel_area_m2, round_area)
    trace = []
    for thickness in thickness_list:
        limit = max_area(glass_type, glass_subtype, thickness, area_factor, data_dir)
        if limit is None:
            continue
        passed = panel_area_m2 <= limit
        trace.append({
            'check': 'SG', 'thickness': thickness, 'max_area': limit,
            'actual_area': reported_area, 'result': 'PASS' if passed else 'FAIL',
        })
        if passed:
            return {'status': 'COMPLIANT', 'minimum_thickness_mm': thickness, 'trace': trace}

    return {'status': 'NON_COMPLIANT', 'minimum_thickness_mm': None, 'trace': trace}
