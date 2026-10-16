# AS 1288 Glass Thickness Calculator - Table 5.1 guard tests
# Duce Timber Windows and Doors
#
# WHY THIS EXISTS
# These tests were added BEFORE the Table 5.1 data and search move into one
# shared module. They pin behaviour that tests/test_table_5_1_golden.py does
# not reach: the Mode 2 (check_pane_compliance) safety glass gate, check and
# next-compliant scan; the rule that the Table 5.1 comparison uses the raw
# (unrounded) panel area while traces report it rounded to 4 places; lookups
# at non-integer thicknesses; and the order/types of the Table 5.1
# constants. Every expected value is what the code returned before the move.
# Area limits are never typed here - they are read at test time from
# get_safety_glass_max_area().

import os

from engine.wind_load import run_calculation, run_compliance_check
from engine.wind_load.constants import (
    BAL_RULES, GLASS_TYPE_THICKNESSES, SAFETY_GLASS_CATEGORY, SAFETY_GLASS_INELIGIBLE,
)
from engine.wind_load.formulas import get_safety_glass_max_area
from engine.combined import pathway3, pathway4

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, '..', 'data', 'Wind_Load_Check_Tables_Full.csv')
NOMINAL_CSV_PATH = os.path.join(HERE, '..', 'data', 'Table_4_1_Minimum_Glass_Thickness.csv')

MONO_TOUGH = ('Monolithic', 'Toughened')
LAM_TOUGH = ('Laminated', 'Toughened')


def _limit(thickness, subtype=MONO_TOUGH):
    return get_safety_glass_max_area(subtype[0], subtype[1], thickness)


def _mode2(height_mm, width_mm, uls, sls, glass_type, glass_subtype, actual_mm):
    return run_compliance_check(
        csv_path=CSV_PATH, nominal_thickness_csv_path=NOMINAL_CSV_PATH,
        height_mm=height_mm, width_mm=width_mm,
        support_condition='4-edge', span_dimension='width',
        wind_pressure_uls=uls, wind_pressure_sls=sls,
        panes=[{'label': 'Single', 'glass_type': glass_type,
                'glass_subtype': glass_subtype, 'actual_thickness_mm': actual_mm}],
        safety_glass_required=True,
    )[0]


def _sg_check(candidate):
    checks = [c for c in candidate['checks'] if c['check'] == 'SG']
    assert len(checks) == 1
    return checks[0]


def _check_named(candidate, name):
    checks = [c for c in candidate['checks'] if c['check'] == name]
    assert len(checks) == 1
    return checks[0]


# 1. Mode 2 ineligible gate (Table 5.1, 4-edge)
def test_mode2_ineligible_gate_g1():
    r = _mode2(1200, 900, 1.5, 0.6, 'Monolithic', 'Annealed', 5.9)
    assert r['status'] == 'SG_INELIGIBLE'
    assert r['message'] == ('Monolithic Annealed is not classified as safety glass '
                            'and cannot be used when safety glass is required.')
    assert r['nominal_thickness_mm'] == 6
    assert r['panel_area_m2'] == 1.08
    assert r['sg_status'] is None
    assert r['next_compliant_thickness_mm'] is None


# 2. Mode 2 single check, panel clearly under the limit
def test_mode2_sg_pass_g2():
    r = _mode2(1200, 900, 1.0, 0.4, 'Monolithic', 'Toughened', 4.8)
    assert r['status'] == 'PASS'
    assert r['nominal_thickness_mm'] == 5
    assert r['sg_status'] == 'PASS'
    assert r['sg_max_area_m2'] == _limit(5)
    assert isinstance(r['sg_max_area_m2'], float)
    assert r['next_compliant_thickness_mm'] is None
    assert r['next_compliant_trace'] == []


# 3. Mode 2 next-compliant scan: one candidate fails the area check, a later one passes
def test_mode2_next_compliant_sg_fail_g4():
    r = _mode2(1400, 2500, 0.8, 0.4, 'Monolithic', 'Toughened', 3.8)
    assert r['status'] == 'FAIL'
    assert r['nominal_thickness_mm'] == 4
    assert r['sg_status'] == 'FAIL'
    assert r['sg_max_area_m2'] == _limit(4)
    assert r['next_compliant_thickness_mm'] == 6

    trace = r['next_compliant_trace']
    assert len(trace) == 2

    c5, c6 = trace
    assert c5['thickness'] == 5
    assert c5['overall'] == 'FAIL'
    assert c5['fail_reason'] == 'Safety Glass Area Check'
    assert _check_named(c5, 'ULS')['result'] == 'PASS'
    assert _check_named(c5, 'SLS')['result'] == 'PASS'
    sg5 = _sg_check(c5)
    assert sg5['result'] == 'FAIL'
    assert sg5['max_area'] == _limit(5)
    assert sg5['actual_area'] == 3.5

    assert c6['thickness'] == 6
    assert c6['overall'] == 'PASS'
    assert _check_named(c6, 'ULS')['result'] == 'PASS'
    assert _check_named(c6, 'SLS')['result'] == 'PASS'
    sg6 = _sg_check(c6)
    assert sg6['result'] == 'PASS'
    assert sg6['max_area'] == _limit(6)


# 4. Mode 1 rounding: raw area is compared, rounded area is reported
def test_mode1_rounding_compares_raw_area_g5a():
    raw = (1032 * 1938) / 1_000_000
    limit4 = _limit(4)
    assert raw > limit4
    assert round(raw, 4) == limit4

    r = run_calculation(
        csv_path=CSV_PATH, height_mm=1032, width_mm=1938,
        support_condition='4-edge', span_dimension='width',
        wind_pressure_uls=0.5, wind_pressure_sls=0.3,
        selected_glass_types=[MONO_TOUGH], glazing_config='single',
        safety_glass_required=True,
    )[0]

    assert r['status'] == 'PASS'
    trace = r['sg_trace']
    assert trace[0]['thickness'] == 4
    assert trace[0]['result'] == 'FAIL'
    assert trace[0]['max_area'] == limit4
    assert trace[0]['actual_area'] == limit4
    assert trace[1]['thickness'] == 5
    assert trace[1]['result'] == 'PASS'
    assert r['sg_minimum_thickness_mm'] == 5
    assert r['panel_area_m2'] == limit4


# 5. Mode 2 rounding: same rule inside the next-compliant scan
def test_mode2_rounding_compares_raw_area_g5b():
    raw = (1026 * 2924) / 1_000_000
    limit5 = _limit(5)
    assert raw > limit5
    assert round(raw, 4) == limit5

    r = _mode2(1026, 2924, 0.5, 0.3, 'Monolithic', 'Toughened', 3.8)
    assert r['status'] == 'FAIL'
    assert r['sg_status'] == 'FAIL'
    assert r['panel_area_m2'] == limit5
    assert r['next_compliant_thickness_mm'] == 6

    c5, c6 = r['next_compliant_trace']
    assert c5['thickness'] == 5
    sg5 = _sg_check(c5)
    assert sg5['result'] == 'FAIL'
    assert sg5['max_area'] == limit5
    assert sg5['actual_area'] == limit5
    assert _sg_check(c6)['result'] == 'PASS'


# 6. Non-integer thickness lookups: the raw value is the key
def test_non_integer_thickness_lookup_t6():
    assert get_safety_glass_max_area('Monolithic', 'Toughened', 6.5) is None
    assert _limit(12.0) == _limit(12)
    assert _limit(13.5) == _limit(12) + 1.5
    assert _limit(3.0) == _limit(3)
    assert _limit(3.0, LAM_TOUGH) == _limit(3, LAM_TOUGH)
    assert _limit(3, LAM_TOUGH) is None
    assert _limit(4, LAM_TOUGH) is None


# 7. Order and types of the Table 5.1 constants
def test_order_and_types_t7():
    assert isinstance(SAFETY_GLASS_CATEGORY, dict)
    assert list(SAFETY_GLASS_CATEGORY.keys()) == [
        ('Monolithic', 'Toughened'),
        ('Laminated', 'Toughened'),
        ('Laminated', 'Annealed'),
        ('Laminated', 'Heat-strengthened'),
    ]
    assert isinstance(SAFETY_GLASS_INELIGIBLE, list)
    assert SAFETY_GLASS_INELIGIBLE == [
        ('Monolithic', 'Annealed'),
        ('Monolithic', 'Heat-strengthened'),
    ]
    eligible = BAL_RULES[('12.5', 'Door')]['eligible_types']
    assert isinstance(eligible, list)
    assert eligible == [
        ('Monolithic', 'Toughened'),
        ('Laminated', 'Toughened'),
        ('Laminated', 'Annealed'),
        ('Laminated', 'Heat-strengthened'),
    ]


# 8. Pathway 3 and 4 searches compare and report the area exactly as passed
def test_pathways_do_not_round_t9():
    area = _limit(4) + 0.00002
    thickness_list = GLASS_TYPE_THICKNESSES[MONO_TOUGH]
    for module in (pathway3, pathway4):
        res = module._run_table_5_1_search('Monolithic', 'Toughened', area, thickness_list)
        first = res['trace'][0]
        assert first['thickness'] == 4
        assert first['result'] == 'FAIL'
        assert first['actual_area'] == area
