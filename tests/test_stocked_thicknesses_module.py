# AS 1288 Glass Thickness Calculator - stocked thicknesses module tests
# Duce Timber Windows and Doors
#
# Tests for engine/shared/stocked_thicknesses.py and
# data/Stocked_Glass_Thicknesses.csv. No stock values are typed here: real
# values are read from the module or from
# tests/golden/glass_type_thicknesses_golden.json. Tests marked SYNTHETIC use
# made-up fixture rows in tmp_path purely to exercise loader behaviour.

import json
import os
import shutil
import subprocess
import sys

from engine.shared import stocked_thicknesses

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
CSV_PATH = os.path.join(ROOT, 'data', stocked_thicknesses.THICKNESSES_FILE)
SNAPSHOT_PATH = os.path.join(HERE, 'golden', 'glass_type_thicknesses_golden.json')

HEADER = 'glass_type,glass_subtype,nominal_thickness_mm'


def _snapshot_dict():
    with open(SNAPSHOT_PATH, encoding='utf-8') as f:
        return {(r['glass_type'], r['glass_subtype']): list(r['thicknesses'])
                for r in json.load(f)}


# 1. Header and encoding
def test_csv_header_and_encoding():
    with open(CSV_PATH, 'rb') as f:
        raw = f.read()
    assert not raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8')
    assert text.splitlines()[0] == HEADER


# 2. data_dir override
def test_data_dir_override(tmp_path):
    shutil.copy(CSV_PATH, tmp_path / stocked_thicknesses.THICKNESSES_FILE)
    default = stocked_thicknesses.stocked_thicknesses()
    assert stocked_thicknesses.stocked_thicknesses(data_dir=str(tmp_path)) == default

    # SYNTHETIC: edit one row in the temporary copy only.
    copy = tmp_path / stocked_thicknesses.THICKNESSES_FILE
    lines = copy.read_text(encoding='utf-8').splitlines()
    glass_type, glass_subtype, _ = lines[1].split(',')
    lines[1] = f'{glass_type},{glass_subtype},1'
    copy.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    edited_dir = str(tmp_path / 'edited')
    os.mkdir(edited_dir)
    os.replace(copy, os.path.join(edited_dir, stocked_thicknesses.THICKNESSES_FILE))

    edited = stocked_thicknesses.stocked_thicknesses(data_dir=edited_dir)
    key = (glass_type, glass_subtype)
    assert edited[key][0] == 1
    assert edited != default
    assert stocked_thicknesses.stocked_thicknesses() == default


# 3. Fresh copies
def test_returns_fresh_copies():
    first = stocked_thicknesses.stocked_thicknesses()
    key = next(iter(first))
    expected = {k: list(v) for k, v in first.items()}

    first[key].append(-1)
    first['extra'] = [-1]
    first.pop(next(iter(first)))

    assert stocked_thicknesses.stocked_thicknesses() == expected

    one = stocked_thicknesses.thicknesses_for(*key)
    one.append(-1)
    assert stocked_thicknesses.thicknesses_for(*key) == expected[key]
    assert stocked_thicknesses.stocked_thicknesses() == expected


# 4. Unknown pair
def test_unknown_pair_returns_none():
    assert stocked_thicknesses.thicknesses_for('No such type', 'No such subtype') is None
    for key, values in _snapshot_dict().items():
        result = stocked_thicknesses.thicknesses_for(*key)
        assert isinstance(result, list)
        assert result == values


# 5. Row order preserved
def test_row_order_is_preserved(tmp_path):
    # SYNTHETIC fixture: non-ascending thicknesses, interleaved subtypes.
    rows = [('A', 'x', 9), ('B', 'y', 3), ('A', 'x', 2), ('B', 'y', 7),
            ('A', 'z', 5), ('A', 'x', 4), ('B', 'y', 1)]
    text = HEADER + '\n' + ''.join(f'{t},{s},{n}\n' for t, s, n in rows)
    (tmp_path / stocked_thicknesses.THICKNESSES_FILE).write_text(text, encoding='utf-8')

    result = stocked_thicknesses.stocked_thicknesses(data_dir=str(tmp_path))
    assert list(result.keys()) == [('A', 'x'), ('B', 'y'), ('A', 'z')]
    assert result[('A', 'x')] == [9, 2, 4]
    assert result[('B', 'y')] == [3, 7, 1]
    assert result[('A', 'z')] == [5]
    assert stocked_thicknesses.thicknesses_for('A', 'x', data_dir=str(tmp_path)) == [9, 2, 4]


# 6. Standalone import
def test_module_imports_standalone():
    code = (
        "import sys; import engine.shared.stocked_thicknesses; "
        "print('engine.wind_load' in sys.modules, 'pandas' in sys.modules)"
    )
    out = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split()
    assert out == ['False', 'False']
