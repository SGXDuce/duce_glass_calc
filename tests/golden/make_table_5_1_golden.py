# AS 1288 Glass Thickness Calculator - Table 5.1 golden snapshot generator
# Duce Timber Windows and Doors
#
# WHY THIS EXISTS
# The next change moves the Table 5.1 data and its area search out of the
# wind load engine into one shared module. That move must not change any
# result. This script records what the CURRENT code returns for the
# Table 5.1 safety glass area check, everywhere it is used, and writes it to
# tests/golden/table_5_1_golden.json. tests/test_table_5_1_golden.py then
# re-runs the same calls and checks they still match, before and after the
# move.
#
# The collect_* functions below are also imported by that test, so the
# generator and the test always make exactly the same calls.
#
# Run from the project root (duce_glass_calc/):
#   python tests/golden/make_table_5_1_golden.py
#
# Only re-run this to deliberately change the snapshot. Do not re-run it
# after the shared-module change to make a failing test pass.

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.wind_load import run_calculation, run_compliance_check
from engine.wind_load.constants import GLASS_TYPE_THICKNESSES
from engine.wind_load.formulas import get_safety_glass_max_area
from engine.combined import pathway3, pathway4

JSON_PATH = os.path.join(HERE, 'table_5_1_golden.json')
DATA_DIR = os.path.join(ROOT, 'data')
CSV_PATH = os.path.join(DATA_DIR, 'Wind_Load_Check_Tables_Full.csv')
NOMINAL_CSV_PATH = os.path.join(DATA_DIR, 'Table_4_1_Minimum_Glass_Thickness.csv')

SUBTYPES = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Toughened'),
    ('Monolithic', 'Heat-strengthened'),
    ('Laminated', 'Annealed'),
    ('Laminated', 'Heat-strengthened'),
    ('Laminated', 'Toughened'),
]


def key_of(subtype):
    return f"{subtype[0]}|{subtype[1]}"


def plain(value):
    """
    Converts a result to plain, JSON-exact Python: numpy numbers and bools
    become int/float/bool, tuples become lists, tuple dict keys become
    'A|B' strings. Anything unexpected raises, so nothing is silently
    stringified.
    """
    if value is None or isinstance(value, (str, bool)):
        return value
    if hasattr(value, 'item') and not isinstance(value, (dict, list, tuple)):
        return plain(value.item())
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, tuple):
                k = '|'.join(str(p) for p in k)
            elif not isinstance(k, str):
                k = str(k)
            out[k] = plain(v)
        return out
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    raise TypeError(f"cannot convert {type(value).__name__} to plain JSON: {value!r}")


# ---------------------------------------------------------------------------
# GROUP A - the area-limit lookup, every subtype, 1 to 40 mm
# ---------------------------------------------------------------------------

def collect_max_area():
    out = {}
    for st in SUBTYPES:
        out[key_of(st)] = {
            str(t): get_safety_glass_max_area(st[0], st[1], t) for t in range(1, 41)
        }
    return plain(out)


# ---------------------------------------------------------------------------
# GROUP B - the Pathway 3 and Pathway 4 search helpers
# ---------------------------------------------------------------------------

def _search_areas(subtype):
    limits = []
    for t in GLASS_TYPE_THICKNESSES[subtype]:
        m = get_safety_glass_max_area(subtype[0], subtype[1], t)
        if m is not None:
            limits.append(m)
    areas = set()
    for m in limits:
        areas.update([m, m + 0.001, m - 0.001])
    areas.update([0.1, 25.0, 30.0])
    return sorted(areas)


def collect_searches():
    out = {}
    for name, module in (('pathway3', pathway3), ('pathway4', pathway4)):
        per_pathway = {}
        for st in SUBTYPES:
            thickness_list = GLASS_TYPE_THICKNESSES[st]
            per_subtype = {}
            for area in _search_areas(st):
                per_subtype[repr(area)] = module._run_table_5_1_search(
                    st[0], st[1], area, thickness_list)
            per_pathway[key_of(st)] = per_subtype
        out[name] = per_pathway
    return plain(out)


# ---------------------------------------------------------------------------
# GROUP C - Pathway 1 full results, safety glass on, 4-edge, single glazing
# Inputs are the safety-glass cases already in tests/test_runner_2.py.
# ---------------------------------------------------------------------------

def _load_runner_2_cases():
    path = os.path.join(ROOT, 'tests', 'test_runner_2.py')
    spec = importlib.util.spec_from_file_location('golden_source_test_runner_2', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TEST_CASES


def collect_pathway1():
    out = {}
    for tc in _load_runner_2_cases():
        if not tc['safety_glass'] or tc['support'] != '4-edge':
            continue
        if tc['mode'] == 1:
            if tc['glazing'] != 'single':
                continue
            res = run_calculation(
                csv_path=CSV_PATH,
                height_mm=tc['height_mm'], width_mm=tc['width_mm'],
                support_condition=tc['support'], span_dimension=tc['span_dim'],
                wind_pressure_uls=float(tc['uls_pa']) / 1000,
                wind_pressure_sls=float(tc['sls_pa']) / 1000,
                selected_glass_types=[(tc['glass_type'], tc['glass_subtype'])],
                glazing_config=tc['glazing'],
                safety_glass_required=tc['safety_glass'],
            )
        else:
            res = run_compliance_check(
                csv_path=CSV_PATH, nominal_thickness_csv_path=NOMINAL_CSV_PATH,
                height_mm=tc['height_mm'], width_mm=tc['width_mm'],
                support_condition=tc['support'], span_dimension=tc['span_dim'],
                wind_pressure_uls=float(tc['uls_pa']) / 1000,
                wind_pressure_sls=float(tc['sls_pa']) / 1000,
                panes=tc['panes'],
                safety_glass_required=tc['safety_glass'],
            )
        out[f"{tc['id']} (mode {tc['mode']})"] = res
    return plain(out)


# ---------------------------------------------------------------------------
# GROUP D - Pathway 3 at 90 degrees and Pathway 4, safety glass on
# Inputs are the safety-glass cases already in tests/test_pathway3.py
# (the 90 degree case) and tests/test_pathway4.py.
# ---------------------------------------------------------------------------

def collect_pathways_3_and_4():
    out = {}
    out['pathway3 90deg h8000 w700/700 mitred'] = pathway3.run_pathway3_calculation(
        height_mm=8000, width_1_mm=700, width_2_mm=700, angle_deg=90,
        corner_or_general='General', joint_type='mitred',
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
        safety_glass_required=True, unframed_edge_condition=None,
        csv_path=CSV_PATH,
    )
    for label, h, w, uls, sls in (
        ('pathway4 h1.219 w2.438', 1.219, 2.438, 4.0, 1.6),
        ('pathway4 h0.35 w15.0', 0.35, 15.0, 0.15, 0.1),
    ):
        out[label] = pathway4.run_pathway4_calculation(
            height_m=h, width_m=w,
            wind_pressure_uls_kpa=uls, wind_pressure_sls_kpa=sls,
            scenario='full_perimeter', safety_glass_required=True,
            csv_path=CSV_PATH,
        )
    return plain(out)


COLLECTORS = {
    'a_max_area': collect_max_area,
    'b_searches': collect_searches,
    'c_pathway1': collect_pathway1,
    'd_pathways_3_and_4': collect_pathways_3_and_4,
}


def main():
    snapshot = {name: fn() for name, fn in COLLECTORS.items()}
    with open(JSON_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(snapshot, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f"Wrote {JSON_PATH} ({os.path.getsize(JSON_PATH)} bytes)")


if __name__ == '__main__':
    main()
