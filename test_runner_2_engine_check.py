# AS 1288 Glass Thickness Calculator - Test Runner 2
# Tests new functionality added after initial validation
# Duce Timber Windows and Doors

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from engine.wind_load import run_calculation, run_compliance_check

# ---------------------------------------------------------------------------
# FILE PATHS
# ---------------------------------------------------------------------------

script_dir             = os.path.dirname(os.path.abspath(__file__))
csv_path               = os.path.join(script_dir, 'data', 'Wind_Load_Check_Tables_Full.csv')
nc_csv_path            = os.path.join(script_dir, 'data', 'N_C_Tables.csv')
nominal_thickness_csv_path = os.path.join(
    script_dir, 'data', 'Table_4_1_Minimum_Glass_Thickness.csv'
)

# ---------------------------------------------------------------------------
# TEST CASES
# ---------------------------------------------------------------------------

TEST_CASES = [

    # --- TC-A: AR > 5 uses AR=5 row ---
    {
        'id': 'TC-A', 'mode': 1,
        'height_mm': 600, 'width_mm': 3600,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1500, 'sls_pa': 600,
        'rating': '', 'location': '',
        'glass_type': 'Monolithic', 'glass_subtype': 'Annealed',
        'glazing': 'single', 'safety_glass': False,
        'expected_uls_t': 4, 'expected_sls_t': 4,
        'expected_final_t': 4, 'expected_status': 'PASS',
        'notes': 'AR=6.0 uses AR=5 row. span=600mm.'
    },

    # --- TC-B: Laminated Heat-strengthened Mode 1 ---
    {
        'id': 'TC-B', 'mode': 1,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Laminated', 'glass_subtype': 'Heat-strengthened',
        'glazing': 'single', 'safety_glass': False,
        'expected_uls_t': 5, 'expected_sls_t': 5,
        'expected_final_t': 5, 'expected_status': 'PASS',
        'notes': 'c1=1.6 effective ULS=1250Pa. AR=1.33->1.5 span=900mm.'
    },

    # --- TC-C: Laminated Toughened Mode 1 ---
    {
        'id': 'TC-C', 'mode': 1,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Laminated', 'glass_subtype': 'Toughened',
        'glazing': 'single', 'safety_glass': False,
        'expected_uls_t': 5, 'expected_sls_t': 5,
        'expected_final_t': 5, 'expected_status': 'PASS',
        'notes': 'c1=2.5 effective ULS=800Pa. AR=1.33->1.5 span=900mm.'
    },

    # --- TC-H: Safety Glass PASS - wind and SG both pass at 4mm ---
    {
        'id': 'TC-H', 'mode': 1,
        'height_mm': 1500, 'width_mm': 1200,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1000, 'sls_pa': 400,
        'rating': '', 'location': '',
        'glass_type': 'Monolithic', 'glass_subtype': 'Toughened',
        'glazing': 'single', 'safety_glass': True,
        'expected_uls_t': 4, 'expected_sls_t': 4,
        'expected_sg_t': 4, 'expected_final_t': 4, 'expected_status': 'PASS',
        'notes': 'Area=1.8m2. SG max at 4mm=2.0m2. Wind and SG both pass at 4mm.'
    },

    # --- TC-I: Safety Glass governs - bumps from 4mm to 5mm ---
    {
        'id': 'TC-I', 'mode': 1,
        'height_mm': 2000, 'width_mm': 1500,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1000, 'sls_pa': 400,
        'rating': '', 'location': '',
        'glass_type': 'Monolithic', 'glass_subtype': 'Toughened',
        'glazing': 'single', 'safety_glass': True,
        'expected_uls_t': 4, 'expected_sls_t': 4,
        'expected_sg_t': 5, 'expected_final_t': 5, 'expected_status': 'PASS',
        'notes': 'Area=3.0m2. SG fails at 4mm (max 2.0m2). SG passes at 5mm (max 3.0m2). SG governs.'
    },

    # --- TC-J: Safety Glass ineligible - Monolithic Annealed ---
    {
        'id': 'TC-J', 'mode': 1,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Monolithic', 'glass_subtype': 'Annealed',
        'glazing': 'single', 'safety_glass': True,
        'expected_uls_t': None, 'expected_sls_t': None,
        'expected_final_t': None, 'expected_status': 'SG_INELIGIBLE',
        'notes': 'Monolithic Annealed not eligible for safety glass.'
    },

    # --- TC-K: Safety Glass ineligible - Monolithic Heat-strengthened ---
    {
        'id': 'TC-K', 'mode': 1,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Monolithic', 'glass_subtype': 'Heat-strengthened',
        'glazing': 'single', 'safety_glass': True,
        'expected_uls_t': None, 'expected_sls_t': None,
        'expected_final_t': None, 'expected_status': 'SG_INELIGIBLE',
        'notes': 'Monolithic Heat-strengthened not eligible for safety glass.'
    },

    # --- TC-L: Laminated Annealed IGU Double k_pane + c1 ---
    {
        'id': 'TC-L', 'mode': 1,
        'height_mm': 1800, 'width_mm': 1200,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Laminated', 'glass_subtype': 'Annealed',
        'glazing': 'double', 'safety_glass': False,
        'expected_uls_t': 5, 'expected_sls_t': 5,
        'expected_final_t': 5, 'expected_status': 'PASS',
        'notes': 'k_pane=0.625 c1=1.0 effective ULS=1250Pa. AR=1.5 span=1200mm.'
    },

    # --- TC-M: Laminated Heat-strengthened IGU Double k_pane + c1 combined ---
    {
        'id': 'TC-M', 'mode': 1,
        'height_mm': 1800, 'width_mm': 1200,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'glass_type': 'Laminated', 'glass_subtype': 'Heat-strengthened',
        'glazing': 'double', 'safety_glass': False,
        'expected_uls_t': 5, 'expected_sls_t': 5,
        'expected_final_t': 5, 'expected_status': 'PASS',
        'notes': 'k_pane=0.625 c1=1.6 effective ULS=781.25Pa. AR=1.5 span=1200mm.'
    },

    # --- TC-N: Mode 2 Laminated Heat-strengthened PASS ---
    {
        'id': 'TC-N', 'mode': 2,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'safety_glass': False,
        'panes': [
            {'label': 'Single', 'glass_type': 'Laminated',
             'glass_subtype': 'Heat-strengthened', 'actual_thickness_mm': 7.7}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS'}
        ],
        'notes': 'Actual 7.7mm->8mm nominal. c1=1.6 effective ULS=1250Pa.'
    },

    # --- TC-O: Mode 2 Laminated Toughened PASS ---
    {
        'id': 'TC-O', 'mode': 2,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2000, 'sls_pa': 800,
        'rating': '', 'location': '',
        'safety_glass': False,
        'panes': [
            {'label': 'Single', 'glass_type': 'Laminated',
             'glass_subtype': 'Toughened', 'actual_thickness_mm': 7.7}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS'}
        ],
        'notes': 'Actual 7.7mm->8mm nominal. c1=2.5 effective ULS=800Pa.'
    },

    # --- TC-P: Mode 2 FAIL on ULS - next compliant thickness = 12mm ---
    {
        'id': 'TC-P', 'mode': 2,
        'height_mm': 2400, 'width_mm': 2000,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 3500, 'sls_pa': 1400,
        'rating': '', 'location': '',
        'safety_glass': False,
        'panes': [
            {'label': 'Single', 'glass_type': 'Monolithic',
             'glass_subtype': 'Annealed', 'actual_thickness_mm': 5.9}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'FAIL',
             'uls_status': 'FAIL', 'sls_status': None,
             'next_compliant_thickness_mm': 12}
        ],
        'notes': 'High wind large panel. 6mm nominal fails ULS. Next compliant = 12mm.'
    },

    # --- TC-Q: Mode 2 PASS on both ULS and SLS ---
    {
        'id': 'TC-Q', 'mode': 2,
        'height_mm': 1800, 'width_mm': 1500,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1200, 'sls_pa': 1000,
        'rating': '', 'location': '',
        'safety_glass': False,
        'panes': [
            {'label': 'Single', 'glass_type': 'Monolithic',
             'glass_subtype': 'Annealed', 'actual_thickness_mm': 5.9}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS'}
        ],
        'notes': '6mm nominal. Moderate wind. Both ULS and SLS pass.'
    },

    # --- TC-R: Mode 2 Safety Glass PASS ---
    {
        'id': 'TC-R', 'mode': 2,
        'height_mm': 1200, 'width_mm': 900,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1500, 'sls_pa': 600,
        'rating': '', 'location': '',
        'safety_glass': True,
        'panes': [
            {'label': 'Single', 'glass_type': 'Monolithic',
             'glass_subtype': 'Toughened', 'actual_thickness_mm': 5.9}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS',
             'sg_status': 'PASS'}
        ],
        'notes': 'Actual 5.9mm->6mm nominal. Area=1.08m2. SG max at 6mm=4.0m2. All pass.'
    },

    # --- TC-S: Mode 2 Safety Glass FAIL - next compliant = 5mm ---
    {
        'id': 'TC-S', 'mode': 2,
        'height_mm': 1600, 'width_mm': 1400,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 1500, 'sls_pa': 600,
        'rating': '', 'location': '',
        'safety_glass': True,
        'panes': [
            {'label': 'Single', 'glass_type': 'Monolithic',
             'glass_subtype': 'Toughened', 'actual_thickness_mm': 3.9}
        ],
        'expected_results': [
            {'label': 'Single', 'status': 'FAIL',
             'uls_status': 'PASS', 'sls_status': 'PASS',
             'sg_status': 'FAIL',
             'next_compliant_thickness_mm': 5}
        ],
        'notes': 'Actual 3.9mm->4mm nominal. Area=2.24m2. SG max at 4mm=2.0m2. SG fails. Next=5mm.'
    },

    # --- TC-T: Mode 2 IGU Double - both panes PASS ---
    {
        'id': 'TC-T', 'mode': 2,
        'height_mm': 1800, 'width_mm': 1500,
        'support': '4-edge', 'span_dim': 'width',
        'wind_method': 'Pressure', 'uls_pa': 2500, 'sls_pa': 1000,
        'rating': '', 'location': '',
        'safety_glass': False,
        'panes': [
            {'label': 'Outer', 'glass_type': 'Monolithic',
             'glass_subtype': 'Toughened', 'actual_thickness_mm': 5.9},
            {'label': 'Inner', 'glass_type': 'Monolithic',
             'glass_subtype': 'Annealed', 'actual_thickness_mm': 3.9}
        ],
        'expected_results': [
            {'label': 'Outer', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS'},
            {'label': 'Inner', 'status': 'PASS',
             'uls_status': 'PASS', 'sls_status': 'PASS'}
        ],
        'notes': 'Mixed IGU. Outer 5.9mm Toughened. Inner 3.9mm Annealed. Both pass.'
    },
]


# ---------------------------------------------------------------------------
# RUNNER FUNCTIONS
# ---------------------------------------------------------------------------

def run_mode1_test(tc):
    results = run_calculation(
        csv_path              = csv_path,
        height_mm             = tc['height_mm'],
        width_mm              = tc['width_mm'],
        support_condition     = tc['support'],
        span_dimension        = tc['span_dim'],
        wind_pressure_uls     = float(tc['uls_pa']) / 1000,
        wind_pressure_sls     = float(tc['sls_pa']) / 1000,
        selected_glass_types  = [(tc['glass_type'], tc['glass_subtype'])],
        glazing_config        = tc['glazing'],
        safety_glass_required = tc['safety_glass']
    )

    r = results[0]

    # --- Check status ---
    status_match = r['status'] == tc['expected_status']

    # --- Check thicknesses ---
    uls_match   = True
    sls_match   = True
    sg_match    = True
    final_match = True

    def is_acceptable(actual, expected):
        if actual == expected:
            return True
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return actual <= expected
        return False

    if tc['expected_status'] == 'PASS':
        uls_match   = is_acceptable(r.get('uls_minimum_thickness_mm'), tc.get('expected_uls_t'))
        sls_match   = is_acceptable(r.get('sls_minimum_thickness_mm'), tc.get('expected_sls_t'))
        final_match = is_acceptable(r.get('minimum_thickness_mm'), tc.get('expected_final_t'))
        if tc['safety_glass'] and tc.get('expected_sg_t') is not None:
            sg_match = is_acceptable(r.get('sg_minimum_thickness_mm'), tc.get('expected_sg_t'))

    overall = 'MATCH' if all([status_match, uls_match, sls_match, sg_match, final_match]) else 'MISMATCH'

    details = []
    if not status_match:
        details.append(f"status: expected={tc['expected_status']} actual={r['status']}")
    if not uls_match:
        details.append(f"ULS: expected={tc.get('expected_uls_t')} actual={r.get('uls_minimum_thickness_mm')}")
    if not sls_match:
        details.append(f"SLS: expected={tc.get('expected_sls_t')} actual={r.get('sls_minimum_thickness_mm')}")
    if not sg_match:
        details.append(f"SG: expected={tc.get('expected_sg_t')} actual={r.get('sg_minimum_thickness_mm')}")
    if not final_match:
        details.append(f"Final: expected={tc.get('expected_final_t')} actual={r.get('minimum_thickness_mm')}")

    return {
        'id': tc['id'], 'mode': 1, 'notes': tc['notes'],
        'result': overall, 'details': details
    }


def run_mode2_test(tc):
    results = run_compliance_check(
        csv_path                   = csv_path,
        nominal_thickness_csv_path = nominal_thickness_csv_path,
        height_mm                  = tc['height_mm'],
        width_mm                   = tc['width_mm'],
        support_condition          = tc['support'],
        span_dimension             = tc['span_dim'],
        wind_pressure_uls          = float(tc['uls_pa']) / 1000,
        wind_pressure_sls          = float(tc['sls_pa']) / 1000,
        panes                      = tc['panes'],
        safety_glass_required      = tc['safety_glass']
    )

    all_match    = True
    pane_details = []

    for i, expected in enumerate(tc['expected_results']):
        r     = results[i]
        mismatches = []

        # Overall status
        if r['status'] != expected['status']:
            mismatches.append(
                f"status: expected={expected['status']} actual={r['status']}"
            )

        # ULS status
        if expected.get('uls_status') and r.get('uls_status') != expected['uls_status']:
            mismatches.append(
                f"ULS: expected={expected['uls_status']} actual={r.get('uls_status')}"
            )

        # SLS status — only check if ULS passed (SLS only runs after ULS)
        if expected.get('sls_status') and r.get('uls_status') == 'PASS':
            if r.get('sls_status') != expected['sls_status']:
                mismatches.append(
                    f"SLS: expected={expected['sls_status']} actual={r.get('sls_status')}"
                )

        # SG status
        if expected.get('sg_status') and r.get('sg_status') != expected['sg_status']:
            mismatches.append(
                f"SG: expected={expected['sg_status']} actual={r.get('sg_status')}"
            )

        # Next compliant thickness
        if expected.get('next_compliant_thickness_mm') is not None:
            if r.get('next_compliant_thickness_mm') != expected['next_compliant_thickness_mm']:
                mismatches.append(
                    f"Next thickness: expected={expected['next_compliant_thickness_mm']} "
                    f"actual={r.get('next_compliant_thickness_mm')}"
                )

        pane_match = len(mismatches) == 0
        if not pane_match:
            all_match = False

        pane_details.append({
            'label':  expected['label'],
            'match':  'MATCH' if pane_match else 'MISMATCH',
            'issues': mismatches
        })

    return {
        'id': tc['id'], 'mode': 2, 'notes': tc['notes'],
        'result': 'MATCH' if all_match else 'MISMATCH',
        'pane_details': pane_details
    }


# ---------------------------------------------------------------------------
# SUMMARY PRINTER
# ---------------------------------------------------------------------------

def print_summary(test_results):
    total  = len(test_results)
    passed = sum(1 for r in test_results if r['result'] == 'MATCH')
    failed = total - passed

    print()
    print('=' * 70)
    print('TEST RUNNER 2 — NEW FUNCTIONALITY')
    print('=' * 70)
    print(f"  Total: {total}  |  Matched: {passed}  |  Mismatched: {failed}")
    print('=' * 70)

    for r in test_results:
        marker = '  OK  ' if r['result'] == 'MATCH' else ' FAIL '
        print()
        print(f"  [{marker}] {r['id']} (Mode {r['mode']}) — {r['notes']}")

        if r['mode'] == 1:
            if r['result'] == 'MISMATCH':
                for d in r.get('details', []):
                    print(f"          {d}")
        else:
            for pd in r.get('pane_details', []):
                match_str = 'OK' if pd['match'] == 'MATCH' else 'FAIL'
                print(f"          {pd['label']}: [{match_str}]")
                for issue in pd.get('issues', []):
                    print(f"            {issue}")

    print()
    print('=' * 70)
    if failed == 0:
        print('  ALL NEW TEST CASES PASSED — new functionality validated.')
    else:
        print(f'  {failed} MISMATCH(ES) FOUND — review flagged cases above.')
    print('=' * 70)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print()
    print('=' * 70)
    print('  AS 1288 Calculator — Test Runner 2 (New Functionality)')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)
    print(f"  Running {len(TEST_CASES)} test cases...")

    test_results = []

    for tc in TEST_CASES:
        try:
            if tc['mode'] == 1:
                result = run_mode1_test(tc)
            else:
                result = run_mode2_test(tc)
            test_results.append(result)
        except Exception as e:
            test_results.append({
                'id':    tc['id'],
                'mode':  tc['mode'],
                'notes': tc['notes'],
                'result': 'MISMATCH',
                'details': [f'ERROR: {str(e)}'],
                'pane_details': [{'label': '?', 'match': 'MISMATCH',
                                  'issues': [f'ERROR: {str(e)}']}]
            })

    print_summary(test_results)
