# AS 1288 Glass Thickness Calculator - Pathway 3 Test Runner
# Validates the Pathway 3 (Faceted Structural Silicone, Section 14.3) combined
# orchestration engine against hand-calculable cases, each derived by running
# the existing, already-validated sub-component engines (silicone bite, wind
# load Mode 1, Table 5.3) independently before comparing against
# run_pathway3_calculation()'s output.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_pathway3

import os

from engine.combined.pathway3 import run_pathway3_calculation

# ---------------------------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, '..', 'data', 'Wind_Load_Check_Tables_Full.csv')
csv_path_5_3 = os.path.join(script_dir, '..', 'data', 'Table_5_3.csv')


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def report(test_id, description, checks):
    """
    checks is a list of (label, expected, actual, ok) tuples.
    Prints each check and returns True if all checks passed.
    """
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    return overall


# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_1():
    # Case A - bite governs over wind and human impact.
    # Independently verified sub-components (h=600mm, w=2200/2200mm, angle=130,
    # butt joint, pu=1.0kPa, ps=0.7kPa):
    #   run_bite_calculation(): nominal_monolithic=15, nominal_laminated=16
    #   check_glass_type(Monolithic, Toughened, safety_glass_required=False):
    #       uls=4, sls=4
    #   check_table_5_3(0.6m, 'Toughened', 2.2m, 2 joints): min_thickness_mm=6
    # All three figures are far below the bite figure, so bite (15/16mm) must
    # govern for every eligible subtype.
    res = run_pathway3_calculation(
        height_mm=600, width_1_mm=2200, width_2_mm=2200, angle_deg=130,
        corner_or_general='General', joint_type='butt',
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
        safety_glass_required=True, unframed_edge_condition='2-edge',
        csv_path=csv_path, csv_path_5_3=csv_path_5_3,
    )

    mono_tough = res[('Monolithic', 'Toughened')]
    lam_ann = res[('Laminated', 'Annealed')]

    checks = [
        ('Monolithic Toughened status', 'PASS', mono_tough['status'], mono_tough['status'] == 'PASS'),
        ('Monolithic Toughened bite_thickness_mm', 15, mono_tough['bite_thickness_mm'], mono_tough['bite_thickness_mm'] == 15),
        ('Monolithic Toughened uls_thickness_mm', 4, mono_tough['uls_thickness_mm'], mono_tough['uls_thickness_mm'] == 4),
        ('Monolithic Toughened sls_thickness_mm', 4, mono_tough['sls_thickness_mm'], mono_tough['sls_thickness_mm'] == 4),
        ('Monolithic Toughened human_impact_thickness_mm', 6, mono_tough['human_impact_thickness_mm'], mono_tough['human_impact_thickness_mm'] == 6),
        ('Monolithic Toughened governing_thickness_mm (bite governs)', 15, mono_tough['governing_thickness_mm'], mono_tough['governing_thickness_mm'] == 15),
        ('Laminated Annealed bite_thickness_mm', 16, lam_ann['bite_thickness_mm'], lam_ann['bite_thickness_mm'] == 16),
        ('Laminated Annealed governing_thickness_mm (bite governs)', 16, lam_ann['governing_thickness_mm'], lam_ann['governing_thickness_mm'] == 16),
    ]
    return report('1', 'Case A - bite governs over wind and human impact', checks)


def test_2():
    # Case B - wind (ULS) governs over bite.
    # Independently verified sub-components (h=10000mm, w=2000/2000mm,
    # angle=90, butt joint, pu=3.2kPa, ps=2.24kPa, Monolithic Annealed):
    #   run_bite_calculation(): nominal_monolithic=19
    #   check_glass_type(): uls=25, sls=15
    # ULS (25mm) exceeds bite (19mm), so wind must govern.
    res = run_pathway3_calculation(
        height_mm=10000, width_1_mm=2000, width_2_mm=2000, angle_deg=90,
        corner_or_general='General', joint_type='butt',
        wind_pressure_uls_kpa=3.2, wind_pressure_sls_kpa=2.24,
        safety_glass_required=False, unframed_edge_condition=None,
        csv_path=csv_path,
    )

    mono_ann = res[('Monolithic', 'Annealed')]

    checks = [
        ('status', 'PASS', mono_ann['status'], mono_ann['status'] == 'PASS'),
        ('bite_thickness_mm', 19, mono_ann['bite_thickness_mm'], mono_ann['bite_thickness_mm'] == 19),
        ('uls_thickness_mm', 25, mono_ann['uls_thickness_mm'], mono_ann['uls_thickness_mm'] == 25),
        ('sls_thickness_mm', 15, mono_ann['sls_thickness_mm'], mono_ann['sls_thickness_mm'] == 15),
        ('human_impact_thickness_mm (toggle off)', None, mono_ann['human_impact_thickness_mm'], mono_ann['human_impact_thickness_mm'] is None),
        ('governing_thickness_mm (wind ULS governs)', 25, mono_ann['governing_thickness_mm'], mono_ann['governing_thickness_mm'] == 25),
    ]
    return report('2', 'Case B - wind (ULS) governs over bite', checks)


def test_3():
    # Case C - angle exactly 90 deg, Table 5.1 governs.
    # Independently verified sub-components (h=8000mm, w=700/700mm, angle=90,
    # mitred joint, pu=1.0kPa, ps=0.7kPa, Monolithic Toughened):
    #   run_bite_calculation(): nominal_monolithic=6
    #   check_glass_type(safety_glass_required=False): uls=4, sls=4
    #   check_glass_type(safety_glass_required=True): sg_minimum_thickness_mm=8
    #     (AS 1288 Table 5.1 Safety Glass Area Check)
    # Table 5.1 (8mm) exceeds bite (6mm) and wind (4mm), so it must govern.
    res = run_pathway3_calculation(
        height_mm=8000, width_1_mm=700, width_2_mm=700, angle_deg=90,
        corner_or_general='General', joint_type='mitred',
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
        safety_glass_required=True, unframed_edge_condition=None,
        csv_path=csv_path,
    )

    mono_tough = res[('Monolithic', 'Toughened')]

    checks = [
        ('status', 'PASS', mono_tough['status'], mono_tough['status'] == 'PASS'),
        ('human_impact_table', '5.1', mono_tough['human_impact_table'], mono_tough['human_impact_table'] == '5.1'),
        ('bite_thickness_mm', 6, mono_tough['bite_thickness_mm'], mono_tough['bite_thickness_mm'] == 6),
        ('uls_thickness_mm', 4, mono_tough['uls_thickness_mm'], mono_tough['uls_thickness_mm'] == 4),
        ('sls_thickness_mm', 4, mono_tough['sls_thickness_mm'], mono_tough['sls_thickness_mm'] == 4),
        ('human_impact_thickness_mm (Table 5.1)', 8, mono_tough['human_impact_thickness_mm'], mono_tough['human_impact_thickness_mm'] == 8),
        ('governing_thickness_mm (Table 5.1 governs)', 8, mono_tough['governing_thickness_mm'], mono_tough['governing_thickness_mm'] == 8),
    ]
    return report('3', 'Case C - angle exactly 90 deg, Table 5.1 governs', checks)


def test_4():
    # Case D - angle 90-160 deg (130 deg), Table 5.3 governs. Run with both
    # the 2-edge and 3-edge selector.
    #
    # Independently verified sub-components (h=3000mm, w=1000/1000mm,
    # angle=130, mitred joint, pu=1.0kPa, ps=0.7kPa, Monolithic Toughened):
    #   run_bite_calculation(): nominal_monolithic=8
    #   check_glass_type(safety_glass_required=False): uls=4, sls=5
    #   check_table_5_3(3.0m, 'Toughened', 1.0m, 2 joints): min_thickness_mm=12
    #   check_table_5_3(3.0m, 'Toughened', 1.0m, 1 joint):  min_thickness_mm=12
    #
    # NOTE: 2-edge and 3-edge produce IDENTICAL Table 5.3 figures here - this
    # is a genuine property of the current Table_5_3.csv data, not a bug in
    # this orchestrator. The "Butt Joints max" column only ever restricts to
    # 1 joint for Annealed/Heat-Strengthened rows, and both of those glass
    # types are in TABLE_5_3_SAFETY_GLASS_INELIGIBLE - so no glass type
    # actually eligible for Table 5.3 can ever have a row where 2-edge (2
    # joints) and 3-edge (1 joint) qualify differently. Both selectors are
    # exercised below to confirm the parameter is correctly threaded through
    # the whole pipeline, not to show a numeric difference.
    checks = []
    for edge_condition in ('2-edge', '3-edge'):
        res = run_pathway3_calculation(
            height_mm=3000, width_1_mm=1000, width_2_mm=1000, angle_deg=130,
            corner_or_general='General', joint_type='mitred',
            wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
            safety_glass_required=True, unframed_edge_condition=edge_condition,
            csv_path=csv_path, csv_path_5_3=csv_path_5_3,
        )
        mono_tough = res[('Monolithic', 'Toughened')]

        checks.extend([
            (f'[{edge_condition}] status', 'PASS', mono_tough['status'], mono_tough['status'] == 'PASS'),
            (f'[{edge_condition}] human_impact_table', '5.3', mono_tough['human_impact_table'], mono_tough['human_impact_table'] == '5.3'),
            (f'[{edge_condition}] bite_thickness_mm', 8, mono_tough['bite_thickness_mm'], mono_tough['bite_thickness_mm'] == 8),
            (f'[{edge_condition}] uls_thickness_mm', 4, mono_tough['uls_thickness_mm'], mono_tough['uls_thickness_mm'] == 4),
            (f'[{edge_condition}] sls_thickness_mm', 5, mono_tough['sls_thickness_mm'], mono_tough['sls_thickness_mm'] == 5),
            (f'[{edge_condition}] human_impact_thickness_mm (Table 5.3)', 12, mono_tough['human_impact_thickness_mm'], mono_tough['human_impact_thickness_mm'] == 12),
            (f'[{edge_condition}] governing_thickness_mm (Table 5.3 governs)', 12, mono_tough['governing_thickness_mm'], mono_tough['governing_thickness_mm'] == 12),
        ])
    return report('4', 'Case D - angle 130 deg, Table 5.3 governs (2-edge and 3-edge)', checks)


def test_5():
    # Case E - bite NO_COMPLIANT_THICKNESS for one broad category only.
    # Independently verified sub-components (h=1000mm, w=1700/1700mm,
    # angle=90, butt joint, pu=5.3kPa, ps=3.7kPa):
    #   run_bite_calculation(): status='PASS' overall (not both None),
    #       nominal_monolithic=25, nominal_laminated=None
    #       (required bite 21.45mm exceeds Laminated's largest usable bite
    #       of 21.4mm at 24mm nominal, but is within Monolithic's 21.5mm at
    #       25mm nominal - confirms the category-level short-circuit must be
    #       read from nominal_monolithic/nominal_laminated, never from the
    #       overall status field, since status alone would say 'PASS' here)
    #   check_glass_type(Monolithic, Annealed): uls=10, sls=6
    res = run_pathway3_calculation(
        height_mm=1000, width_1_mm=1700, width_2_mm=1700, angle_deg=90,
        corner_or_general='General', joint_type='butt',
        wind_pressure_uls_kpa=5.3, wind_pressure_sls_kpa=3.7,
        safety_glass_required=False, unframed_edge_condition=None,
        csv_path=csv_path,
    )

    mono_ann = res[('Monolithic', 'Annealed')]
    lam_ann = res[('Laminated', 'Annealed')]
    lam_tough = res[('Laminated', 'Toughened')]

    checks = [
        ('Monolithic Annealed status (unaffected)', 'PASS', mono_ann['status'], mono_ann['status'] == 'PASS'),
        ('Monolithic Annealed bite_thickness_mm', 25, mono_ann['bite_thickness_mm'], mono_ann['bite_thickness_mm'] == 25),
        ('Monolithic Annealed uls_thickness_mm', 10, mono_ann['uls_thickness_mm'], mono_ann['uls_thickness_mm'] == 10),
        ('Monolithic Annealed sls_thickness_mm', 6, mono_ann['sls_thickness_mm'], mono_ann['sls_thickness_mm'] == 6),
        ('Monolithic Annealed governing_thickness_mm', 25, mono_ann['governing_thickness_mm'], mono_ann['governing_thickness_mm'] == 25),
        ('Laminated Annealed status (short-circuited)', 'BITE_NO_COMPLIANT_THICKNESS', lam_ann['status'], lam_ann['status'] == 'BITE_NO_COMPLIANT_THICKNESS'),
        ('Laminated Annealed bite_thickness_mm', None, lam_ann['bite_thickness_mm'], lam_ann['bite_thickness_mm'] is None),
        ('Laminated Annealed uls_thickness_mm (wind never run)', None, lam_ann['uls_thickness_mm'], lam_ann['uls_thickness_mm'] is None),
        ('Laminated Annealed governing_thickness_mm', None, lam_ann['governing_thickness_mm'], lam_ann['governing_thickness_mm'] is None),
        ('Laminated Toughened status (short-circuited too)', 'BITE_NO_COMPLIANT_THICKNESS', lam_tough['status'], lam_tough['status'] == 'BITE_NO_COMPLIANT_THICKNESS'),
    ]
    return report('5', 'Case E - bite NO_COMPLIANT_THICKNESS for Laminated only, Monolithic unaffected', checks)


def test_6():
    # Case F - a subtype ineligible for the active human impact table (toggle
    # ON) must still return bite/wind results, not crash or silently skip.
    # Reuses Case A's inputs (Monolithic Annealed/Heat-strengthened are both
    # in TABLE_5_3_SAFETY_GLASS_INELIGIBLE, so they're ineligible for the
    # >90-160 deg branch's Table 5.3 check).
    res = run_pathway3_calculation(
        height_mm=600, width_1_mm=2200, width_2_mm=2200, angle_deg=130,
        corner_or_general='General', joint_type='butt',
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
        safety_glass_required=True, unframed_edge_condition='2-edge',
        csv_path=csv_path, csv_path_5_3=csv_path_5_3,
    )

    mono_ann = res[('Monolithic', 'Annealed')]
    mono_hs = res[('Monolithic', 'Heat-strengthened')]

    checks = [
        ('Monolithic Annealed status', 'HUMAN_IMPACT_INELIGIBLE', mono_ann['status'], mono_ann['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Annealed bite_thickness_mm still populated', 15, mono_ann['bite_thickness_mm'], mono_ann['bite_thickness_mm'] == 15),
        ('Monolithic Annealed uls_thickness_mm still populated', 4, mono_ann['uls_thickness_mm'], mono_ann['uls_thickness_mm'] == 4),
        ('Monolithic Annealed sls_thickness_mm still populated', 4, mono_ann['sls_thickness_mm'], mono_ann['sls_thickness_mm'] == 4),
        ('Monolithic Annealed human_impact_thickness_mm', None, mono_ann['human_impact_thickness_mm'], mono_ann['human_impact_thickness_mm'] is None),
        ('Monolithic Annealed governing_thickness_mm (bite/wind still govern)', 15, mono_ann['governing_thickness_mm'], mono_ann['governing_thickness_mm'] == 15),
        ('Monolithic Heat-strengthened status', 'HUMAN_IMPACT_INELIGIBLE', mono_hs['status'], mono_hs['status'] == 'HUMAN_IMPACT_INELIGIBLE'),
        ('Monolithic Heat-strengthened governing_thickness_mm still populated', 15, mono_hs['governing_thickness_mm'], mono_hs['governing_thickness_mm'] == 15),
    ]
    return report('6', 'Case F - ineligible subtype still returns bite/wind results, not a crash', checks)


def test_7():
    # Result dict structural consistency - mirrors test_structural_consistency.py's
    # and test_silicone_bite.py's test_15 approach. Every subtype's result,
    # across every status this run produces, must have an identical key set.
    res = run_pathway3_calculation(
        height_mm=600, width_1_mm=2200, width_2_mm=2200, angle_deg=130,
        corner_or_general='General', joint_type='butt',
        wind_pressure_uls_kpa=1.0, wind_pressure_sls_kpa=0.7,
        safety_glass_required=True, unframed_edge_condition='2-edge',
        csv_path=csv_path, csv_path_5_3=csv_path_5_3,
    )

    key_sets = {subtype: frozenset(result.keys()) for subtype, result in res.items()}
    all_keys_match = len(set(key_sets.values())) == 1

    statuses_present = {result['status'] for result in res.values()}

    checks = [
        ('all six subtypes present', 6, len(res), len(res) == 6),
        ('all result key sets identical', True, all_keys_match, all_keys_match),
        (
            'multiple distinct statuses exercised (PASS and HUMAN_IMPACT_INELIGIBLE)',
            True,
            statuses_present,
            {'PASS', 'HUMAN_IMPACT_INELIGIBLE'}.issubset(statuses_present),
        ),
    ]
    return report('7', 'Result dict structural consistency across subtypes/statuses', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Pathway 3 Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [test_1, test_2, test_3, test_4, test_5, test_6, test_7]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
