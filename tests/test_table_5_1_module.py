# AS 1288 Glass Thickness Calculator - Table 5.1 shared module tests
# Duce Timber Windows and Doors
#
# Tests for engine/shared/table_5_1.py and its data CSVs. No Table 5.1 values
# are typed here: limits are read from the module, and checks are relations
# (scaling, extrapolation, ordering) rather than literals.

import csv
import glob
import os
import re
import shutil

from engine.shared import table_5_1
from engine.wind_load.constants import GLASS_TYPE_THICKNESSES, TABLE_5_3_SAFETY_GLASS_INELIGIBLE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
DATA_DIR = os.path.join(ROOT, 'data')
INDEX_HTML = os.path.join(ROOT, 'interfaces', 'flask_app', 'templates', 'index.html')

MONO_TOUGH = ('Monolithic', 'Toughened')
LAM_TOUGH = ('Laminated', 'Toughened')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _thicknesses():
    # Thicknesses at, below and above the extrapolation anchor.
    return [5, 6, 8, 10, 12, 15, 19, 25]


# 1. Headers and encoding
def test_csv_headers_and_encoding():
    expected = {
        'Table_5_1_Categories.csv': ['glass_type', 'glass_subtype', 'category'],
        'Table_5_1_Max_Area.csv': ['category', 'nominal_thickness_mm', 'max_area_m2',
                                   'monolithic_only'],
    }
    for name, header in expected.items():
        path = os.path.join(DATA_DIR, name)
        with open(path, 'rb') as f:
            raw = f.read()
        assert not raw.startswith(b'\xef\xbb\xbf')
        raw.decode('utf-8')
        with open(path, newline='', encoding='utf-8') as f:
            assert next(csv.reader(f)) == header


# 2. Module exports agree with the order pinned in the guard test
def test_module_exports_match_constants():
    cat = table_5_1.safety_glass_category()
    inel = table_5_1.safety_glass_ineligible()
    assert isinstance(cat, dict)
    assert isinstance(inel, list)
    assert list(cat.keys()) == [
        ('Monolithic', 'Toughened'),
        ('Laminated', 'Toughened'),
        ('Laminated', 'Annealed'),
        ('Laminated', 'Heat-strengthened'),
    ]
    assert inel == [
        ('Monolithic', 'Annealed'),
        ('Monolithic', 'Heat-strengthened'),
    ]
    for key in inel:
        assert table_5_1.is_ineligible(*key)
    for key in cat:
        assert not table_5_1.is_ineligible(*key)


# 3. Above-anchor extrapolation reads the CSV (synthetic fixture data)
def test_above_12mm_extrapolates_from_csv_value(tmp_path):
    for name in (table_5_1.CATEGORIES_FILE, table_5_1.MAX_AREA_FILE):
        shutil.copy(os.path.join(DATA_DIR, name), tmp_path / name)

    real_12 = table_5_1.max_area(*MONO_TOUGH, 12)
    real_15 = table_5_1.max_area(*MONO_TOUGH, 15)
    assert real_15 == real_12 + 3

    # SYNTHETIC: bump the cat1 anchor row in the temporary copy only.
    path = tmp_path / table_5_1.MAX_AREA_FILE
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if row['category'] == 'cat1' and row['nominal_thickness_mm'] == '12':
            row['max_area_m2'] = repr(real_12 + 100.0)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    fixture_dir = str(tmp_path)
    assert table_5_1.max_area(*MONO_TOUGH, 12, data_dir=fixture_dir) == real_12 + 100.0
    assert table_5_1.max_area(*MONO_TOUGH, 15, data_dir=fixture_dir) == real_15 + 100.0


# 4. area_factor relation
def test_area_factor_relation():
    for subtype in (MONO_TOUGH, LAM_TOUGH, ('Laminated', 'Annealed')):
        for t in _thicknesses() + [3, 4, 6.5]:
            base = table_5_1.max_area(*subtype, t, 1.0)
            assert table_5_1.max_area(*subtype, t) == base
            scaled = table_5_1.max_area(*subtype, t, 1.5)
            if base is None:
                assert scaled is None
            else:
                assert scaled == 1.5 * base
    assert table_5_1.max_area('Monolithic', 'Annealed', 6, 1.5) is None


# 5. area_factor changes a search outcome
def test_search_area_factor_changes_outcome():
    t = 8
    limit = table_5_1.max_area(*MONO_TOUGH, t)
    area = limit * 1.25  # above the plain limit, below 1.5x the limit
    assert area > limit and area <= 1.5 * limit

    plain = table_5_1.search(*MONO_TOUGH, area, [t])
    assert plain['status'] == 'NON_COMPLIANT'
    assert plain['trace'][0]['result'] == 'FAIL'

    scaled = table_5_1.search(*MONO_TOUGH, area, [t], area_factor=1.5)
    assert scaled['status'] == 'COMPLIANT'
    assert scaled['minimum_thickness_mm'] == t
    assert scaled['trace'][0]['result'] == 'PASS'
    assert scaled['trace'][0]['max_area'] == 1.5 * limit


# 6. round_area only changes the reported area
def test_search_round_area_reports_only():
    t = 8
    limit = table_5_1.max_area(*MONO_TOUGH, t)
    # Raw area just above the limit, but rounds to the limit at 4 places.
    area = limit + 0.00001
    assert area > limit and round(area, 4) == limit

    res = table_5_1.search(*MONO_TOUGH, area, [t], round_area=4)
    assert res['status'] == 'NON_COMPLIANT'
    assert res['trace'][0]['result'] == 'FAIL'
    assert res['trace'][0]['actual_area'] == round(area, 4)

    raw = table_5_1.search(*MONO_TOUGH, area, [t])
    assert raw['trace'][0]['actual_area'] == area


# 7. Ineligible and non-compliant outcomes
def test_search_ineligible_and_non_compliant():
    thicknesses = GLASS_TYPE_THICKNESSES[('Monolithic', 'Annealed')]
    res = table_5_1.search('Monolithic', 'Annealed', 0.1, thicknesses)
    assert res == {'status': 'INELIGIBLE', 'minimum_thickness_mm': None, 'trace': []}

    thicknesses = GLASS_TYPE_THICKNESSES[MONO_TOUGH]
    largest = max(table_5_1.max_area(*MONO_TOUGH, t) for t in thicknesses)
    res = table_5_1.search(*MONO_TOUGH, largest + 1.0, thicknesses)
    assert res['status'] == 'NON_COMPLIANT'
    assert res['minimum_thickness_mm'] is None
    assert len(res['trace']) == len(thicknesses)
    assert all(e['result'] == 'FAIL' for e in res['trace'])


# 8. index.html client-side ineligible lists mirror the engine lists
def _js_pairs(html, name):
    m = re.search(r'const ' + name + r'\s*=\s*\[(.*?)\];', html, re.S)
    assert m, name
    return set(re.findall(r"\[\s*'([^']+)'\s*,\s*'([^']+)'\s*\]", m.group(1)))


def test_index_html_ineligible_lists_match():
    html = _read(INDEX_HTML)
    table_5_1_set = set(table_5_1.safety_glass_ineligible())
    assert _js_pairs(html, 'P3_SG_INELIGIBLE') == table_5_1_set
    assert re.search(r'const P4_SG_INELIGIBLE\s*=\s*P3_SG_INELIGIBLE\s*;', html)
    # Pathway 2 uses Table 5.3 only.
    assert _js_pairs(html, 'P2_SG_INELIGIBLE') == set(TABLE_5_3_SAFETY_GLASS_INELIGIBLE)


# 9. human_impact does not import the other engines
def _import_lines(path):
    return [ln for ln in _read(path).splitlines()
            if re.match(r'\s*(import|from)\s', ln)]


def test_human_impact_does_not_import_other_engines():
    files = glob.glob(os.path.join(ROOT, 'engine', 'human_impact', '*.py'))
    assert files
    for path in files:
        for ln in _import_lines(path):
            assert not re.search(r'wind_load|silicone_bite|combined', ln), (path, ln)


# 10. table_5_1 stays independent of wind_load
def test_table_5_1_does_not_import_wind_load():
    path = os.path.join(ROOT, 'engine', 'shared', 'table_5_1.py')
    for ln in _import_lines(path):
        assert 'wind_load' not in ln, ln
