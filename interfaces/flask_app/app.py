# AS 1288 Glass Thickness Calculator - Flask Web Application
# Duce Timber Windows and Doors

from flask import Flask, render_template, request, jsonify
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from engine.wind_load import run_calculation, run_compliance_check
from engine.silicone_bite import run_bite_calculation
from engine.combined import run_pathway3_calculation, run_pathway4_calculation
from engine.shared.data_loader import load_table_data, load_nc_table, load_nominal_thickness_table, get_pressures_from_nc_rating

# ---------------------------------------------------------------------------
# VERSION / EXPIRY (single source of truth - launcher.py imports EXPIRY_DATE
# from here rather than the other way around, since launcher.py already
# imports `app` and a reverse import would be circular)
# ---------------------------------------------------------------------------

APP_VERSION = '2.1'
EXPIRY_DATE = datetime.datetime(2026, 9, 30, 23, 59, 59)

# ---------------------------------------------------------------------------
# FEATURE FLAGS
# ---------------------------------------------------------------------------

# Pathway 4 (Structural Glazing) is paused pending further development -
# there are reservations about its current scope and audience (v1.28).
# This is a UI-only gate: the landing tile is hidden server-side (index.html
# wraps it in {% if pathway_4_enabled %}) so it does not render at all, not
# just greyed out. /calculate_pathway4, pathway4.py, build_pathway4_report(),
# and every Pathway 4 test are all untouched and fully functional - the
# route stays live but unreachable from the UI. Re-enabling is a single
# flag flip back to True, no other code changes needed.
PATHWAY_4_ENABLED = False

# ---------------------------------------------------------------------------
# FLASK APP SETUP
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Build paths to data files
# When running as a PyInstaller EXE, sys._MEIPASS points to the
# temporary folder where bundled files are unpacked
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(BASE_DIR, 'data')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

CSV_PATH = os.path.join(DATA_DIR, 'Wind_Load_Check_Tables_Full.csv')
NC_CSV_PATH = os.path.join(DATA_DIR, 'N_C_Tables.csv')
NOMINAL_CSV_PATH = os.path.join(DATA_DIR, 'Table_4_1_Minimum_Glass_Thickness.csv')
TABLE_5_3_CSV_PATH = os.path.join(DATA_DIR, 'Table_5_3.csv')


print("Loading data tables...")
WIND_LOAD_DF = load_table_data(CSV_PATH)
NC_DF = load_nc_table(NC_CSV_PATH)
NOMINAL_DF = load_nominal_thickness_table(NOMINAL_CSV_PATH)
print("Data tables loaded.")


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Serves the main calculator page."""
    return render_template(
        'index.html',
        app_version=APP_VERSION,
        pathway_4_enabled=PATHWAY_4_ENABLED,
    )


@app.route('/calculate', methods=['POST'])
def calculate():
    """
    Receives form data from the browser, runs the calculation,
    and returns results as JSON for the page to display.
    """
    try:
        data = request.get_json()

        mode                  = data.get('mode')
        height_mm             = float(data.get('height_mm'))
        width_mm              = float(data.get('width_mm'))
        support_condition     = data.get('support_condition')
        span_dimension        = data.get('span_dimension', 'width')
        wind_method           = data.get('wind_method')
        safety_glass_required = data.get('safety_glass_required', False)
        bushfire_required     = data.get('bushfire_required', False)
        bal_level             = data.get('bal_level')
        element_type          = data.get('element_type')
        unframed_edge_condition = data.get('unframed_edge_condition')

        # --- Resolve wind pressures ---
        if wind_method == 'pressure':
            wind_pressure_uls = float(data.get('uls_pa'))
            wind_pressure_sls = float(data.get('sls_pa'))
        else:
            rating   = data.get('nc_rating')
            location = data.get('nc_location')
            df_nc    = load_nc_table(NC_CSV_PATH)
            pressures = get_pressures_from_nc_rating(df_nc, rating, location)
            if pressures is None:
                return jsonify({
                    'success': False,
                    'error': f'Could not find pressure values for {rating} {location}.'
                })
            wind_pressure_uls = pressures['uls']
            wind_pressure_sls = pressures['sls']

        if mode == 'mode1':
            # --- MODE 1: Minimum Thickness Finder ---
            glazing_config       = data.get('glazing_config')
            selected_glass_types = [
                tuple(gt) for gt in data.get('selected_glass_types', [])
            ]

            results = run_calculation(
                csv_path              = CSV_PATH,
                height_mm             = height_mm,
                width_mm              = width_mm,
                support_condition     = support_condition,
                span_dimension        = span_dimension,
                wind_pressure_uls     = wind_pressure_uls,
                wind_pressure_sls     = wind_pressure_sls,
                selected_glass_types  = selected_glass_types,
                glazing_config        = glazing_config,
                safety_glass_required = safety_glass_required,
                bushfire_required     = bushfire_required,
                bal_level             = bal_level,
                element_type          = element_type,
                unframed_edge_condition = unframed_edge_condition,
                csv_path_5_3          = TABLE_5_3_CSV_PATH if unframed_edge_condition else None
            )

            return jsonify({
                'success':              True,
                'mode':                 'mode1',
                'results':              results,
                'glazing_config':       glazing_config,
                'safety_glass_required': safety_glass_required,
                'bushfire_required':    bushfire_required,
                'wind_pressure_uls':    wind_pressure_uls,
                'wind_pressure_sls':    wind_pressure_sls
            })

        else:
            # --- MODE 2: Compliance Checker ---
            panes = data.get('panes', [])

            results = run_compliance_check(
                csv_path                   = CSV_PATH,
                nominal_thickness_csv_path = NOMINAL_CSV_PATH,
                height_mm                  = height_mm,
                width_mm                   = width_mm,
                support_condition          = support_condition,
                span_dimension             = span_dimension,
                wind_pressure_uls          = wind_pressure_uls,
                wind_pressure_sls          = wind_pressure_sls,
                panes                      = panes,
                safety_glass_required      = safety_glass_required,
                bushfire_required          = bushfire_required,
                bal_level                  = bal_level,
                element_type               = element_type,
                unframed_edge_condition    = unframed_edge_condition,
                csv_path_5_3               = TABLE_5_3_CSV_PATH if unframed_edge_condition else None
            )

            return jsonify({
                'success':               True,
                'mode':                  'mode2',
                'results':               results,
                'safety_glass_required': safety_glass_required,
                'bushfire_required':     bushfire_required,
                'wind_pressure_uls':     wind_pressure_uls,
                'wind_pressure_sls':     wind_pressure_sls
            })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'OUT_OF_SCOPE_CALCULATION'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/calculate_silicone', methods=['POST'])
def calculate_silicone():
    """
    Receives silicone bite form data from the browser, runs the structural
    silicone bite calculation, and returns the result as JSON. Fully
    independent of the wind load engine's /calculate route and Mode 1/2 logic.
    """
    try:
        data = request.get_json()

        width_1_mm  = float(data.get('width_1_mm'))
        width_2_mm  = float(data.get('width_2_mm'))
        angle_deg   = float(data.get('angle_deg'))
        joint_type  = data.get('joint_type', 'butt')
        wind_method = data.get('wind_method')

        # --- Resolve ULS wind pressure (Pz) ---
        if wind_method == 'pressure':
            wind_pressure_kpa = float(data.get('wind_pressure_kpa'))
        else:
            rating   = data.get('nc_rating')
            location = data.get('nc_location')
            pressures = get_pressures_from_nc_rating(NC_DF, rating, location)
            if pressures is None:
                return jsonify({
                    'success': False,
                    'error': f'Could not find pressure values for {rating} {location}.'
                })
            wind_pressure_kpa = pressures['uls']

        result = run_bite_calculation(
            width_1_mm        = width_1_mm,
            width_2_mm        = width_2_mm,
            angle_deg         = angle_deg,
            wind_pressure_kpa = wind_pressure_kpa,
            joint_type        = joint_type
        )

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/calculate_pathway3', methods=['POST'])
def calculate_pathway3():
    """
    Receives Pathway 3 (Faceted Structural Silicone, Section 14.3) form data,
    runs the combined bite/wind/human-impact orchestration for all six glass
    subtypes, then filters the response down to only the subtypes the user
    checked. run_pathway3_calculation() itself has no parameter to restrict
    which subtypes it computes (engine/combined/pathway3.py is not modified
    here per standing discipline) - filtering happens at this layer instead.
    """
    try:
        data = request.get_json()

        height_mm   = float(data.get('height_mm'))
        width_1_mm  = float(data.get('width_1_mm'))
        width_2_mm  = float(data.get('width_2_mm'))
        angle_deg   = float(data.get('angle_deg'))
        joint_type  = data.get('joint_type', 'butt')
        wind_method = data.get('wind_method')
        safety_glass_required   = data.get('safety_glass_required', False)
        unframed_edge_condition = data.get('unframed_edge_condition')
        selected_subtypes = [tuple(gt) for gt in data.get('selected_subtypes', [])]

        # --- Resolve wind pressures (ULS/SLS - both needed, unlike the
        # bite-only /calculate_silicone route which only needs ULS) ---
        if wind_method == 'pressure':
            wind_pressure_uls_kpa = float(data.get('uls_kpa'))
            wind_pressure_sls_kpa = float(data.get('sls_kpa'))
            corner_or_general = None
        else:
            rating   = data.get('nc_rating')
            location = data.get('nc_location')
            pressures = get_pressures_from_nc_rating(NC_DF, rating, location)
            if pressures is None:
                return jsonify({
                    'success': False,
                    'error': f'Could not find pressure values for {rating} {location}.'
                })
            wind_pressure_uls_kpa = pressures['uls']
            wind_pressure_sls_kpa = pressures['sls']
            corner_or_general = location

        all_results = run_pathway3_calculation(
            height_mm               = height_mm,
            width_1_mm              = width_1_mm,
            width_2_mm              = width_2_mm,
            angle_deg               = angle_deg,
            corner_or_general       = corner_or_general,
            joint_type              = joint_type,
            wind_pressure_uls_kpa   = wind_pressure_uls_kpa,
            wind_pressure_sls_kpa   = wind_pressure_sls_kpa,
            safety_glass_required   = safety_glass_required,
            unframed_edge_condition = unframed_edge_condition,
            csv_path      = CSV_PATH,
            csv_path_5_3  = TABLE_5_3_CSV_PATH if unframed_edge_condition else None,
        )

        results = [all_results[gt] for gt in selected_subtypes if gt in all_results]

        return jsonify({
            'success':                True,
            'results':                results,
            'height_mm':              height_mm,
            'width_1_mm':             width_1_mm,
            'width_2_mm':             width_2_mm,
            'angle_deg':              angle_deg,
            'joint_type':             joint_type,
            'safety_glass_required':  safety_glass_required,
            'unframed_edge_condition': unframed_edge_condition,
            'wind_pressure_uls':      wind_pressure_uls_kpa,
            'wind_pressure_sls':      wind_pressure_sls_kpa,
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'OUT_OF_SCOPE_CALCULATION'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/calculate_pathway4', methods=['POST'])
def calculate_pathway4():
    """
    Receives Pathway 4 (Structural Glazing, Section 14.4) form data, runs the
    combined five-criteria orchestration (dead-load bite, wind bite, ULS,
    SLS, Table 5.1) for all six glass subtypes, then filters the response
    down to only the subtypes the user checked. Same filtering-at-this-layer
    approach as calculate_pathway3() above - run_pathway4_calculation() has
    no parameter to restrict which subtypes it computes.

    scenario is hardcoded to 'full_perimeter' - SUPPORTED_SCENARIOS_V1 in
    engine/combined/pathway4.py is exactly ('full_perimeter',), and the
    confirmed decision (v1.25 session) is not to expose a scenario selector
    in the UI at all.

    ULS/SLS resolution (this session, replacing the old single pz_kpa field):
    same wind_method dispatch as calculate_pathway3() - direct kPa entry or
    N/C rating lookup via get_pressures_from_nc_rating(). ULS is passed as
    both wind_pressure_uls_kpa (feeds the Mode 1 ULS check) and, inside
    run_pathway4_calculation() itself, as the Appendix F bite formula's Pz -
    same physical quantity, different notation (Section 14.4).

    wind_span_m/dead_load_perimeter_m (pure geometry, no bite calculation)
    are computed inline for the report - same convention as before this
    session, matching run_structural_glazing_calculation()'s own
    full_perimeter formulas (engine/structural_glazing/formulas.py:91-92)
    exactly, without a second call to that engine.
    """
    try:
        data = request.get_json()

        height_m  = float(data.get('height_mm')) / 1000
        width_m   = float(data.get('width_mm')) / 1000
        wind_method = data.get('wind_method')
        safety_glass_required = data.get('safety_glass_required', False)
        selected_subtypes = [tuple(gt) for gt in data.get('selected_subtypes', [])]

        # --- Resolve wind pressures (ULS/SLS - both needed), same dispatch
        # as calculate_pathway3() ---
        if wind_method == 'pressure':
            wind_pressure_uls_kpa = float(data.get('uls_kpa'))
            wind_pressure_sls_kpa = float(data.get('sls_kpa'))
        else:
            rating   = data.get('nc_rating')
            location = data.get('nc_location')
            pressures = get_pressures_from_nc_rating(NC_DF, rating, location)
            if pressures is None:
                return jsonify({
                    'success': False,
                    'error': f'Could not find pressure values for {rating} {location}.'
                })
            wind_pressure_uls_kpa = pressures['uls']
            wind_pressure_sls_kpa = pressures['sls']

        all_results = run_pathway4_calculation(
            height_m               = height_m,
            width_m                = width_m,
            wind_pressure_uls_kpa   = wind_pressure_uls_kpa,
            wind_pressure_sls_kpa   = wind_pressure_sls_kpa,
            scenario                 = 'full_perimeter',
            safety_glass_required    = safety_glass_required,
            csv_path                 = CSV_PATH,
        )

        results = [all_results[gt] for gt in selected_subtypes if gt in all_results]

        return jsonify({
            'success':               True,
            'results':               results,
            'height_mm':             float(data.get('height_mm')),
            'width_mm':              float(data.get('width_mm')),
            'wind_method':           wind_method,
            'uls_kpa':               wind_pressure_uls_kpa,
            'sls_kpa':               wind_pressure_sls_kpa,
            'nc_rating':             data.get('nc_rating'),
            'nc_location':           data.get('nc_location'),
            'safety_glass_required': safety_glass_required,
            'wind_span_m':           min(width_m, height_m),
            'dead_load_perimeter_m': 2 * height_m + 2 * width_m,
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'OUT_OF_SCOPE_CALCULATION'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """
    Receives calculation inputs and results, generates the report text,
    and returns it as JSON for display in an in-page modal (View Report).
    Delivery format only - build_report()/build_pathway3_report()/
    build_pathway4_report() themselves are unchanged.
    """
    try:
        data = request.get_json()
        pathway = data.get('pathway')
        if pathway == 'pathway3':
            report = build_pathway3_report(data)
        elif pathway == 'pathway4':
            report = build_pathway4_report(data)
        else:
            report = build_report(data)

        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# REPORT BUILDER
# ---------------------------------------------------------------------------

def format_trace_entry(entry, lines):
    """Formats a single trace entry into report lines."""
    chk = entry.get('check')
    t   = entry.get('thickness')
    res = entry.get('result')

    if chk in ('ULS', 'SLS'):
        sp  = entry.get('span')
        B   = entry.get('B')

        if sp is None or B is None:
            # Section 6.6's "uls_confirmed_passing" shortcut - a thinner
            # candidate already passed ULS, so this thickness was never
            # re-checked (only 'thickness'/'result'/'note' are present,
            # no k-values/B/span). Render the note rather than crashing
            # on a format spec against None.
            lines.append(f"  Thickness {t}mm — {res}")
            if entry.get('note'):
                lines.append(f"    {entry.get('note')}")
        else:
            k1 = entry.get('k1')
            k2 = entry.get('k2')
            k3 = entry.get('k3')
            k4 = entry.get('k4')
            p  = entry.get('pressure_kpa')

            lines.append(f"  Thickness {t}mm — {res}")
            lines.append(f"    k1={k1}, k2={k2}, k3={k3}, k4={k4}")
            if chk == 'ULS':
                lines.append(f"    B = {k1} x ({p} + {k2})^{k3} + {k4}")
            else:
                lines.append(f"    B = {t} x ({k1} x ({p} + {k2})^{k3} + {k4})")
            lines.append(f"    B = {B} mm")
            if res == 'PASS':
                lines.append(f"    Span {sp:.0f}mm <= B {B}mm — PASS")
            else:
                lines.append(f"    Span {sp:.0f}mm > B {B}mm — FAIL")

    elif chk == 'TABLE_5_3':
        # Table 5.3 trace entries take one of four shapes depending on
        # which code path built them - this branch renders whichever shape
        # is present rather than assuming one, since the engine legitimately
        # produces all of them:
        if res == 'INELIGIBLE':
            # Pathway 3's own eligibility gate (engine/combined/pathway3.py) -
            # no thickness search was ever run for this subtype.
            lines.append(f"  Table 5.3 eligibility — INELIGIBLE")
            lines.append(f"    {entry.get('message')}")
        elif 'height_m' in entry:
            # Row-level gate result (Mode 1 / Mode 2 hard-gate path,
            # before any thickness was tested) - NOT_PERMITTED or
            # NON_COMPLIANT at the row-lookup stage itself.
            lines.append(f"  Table 5.3 row lookup — {res}")
            lines.append(f"    Height = {entry.get('height_m')}m, "
                          f"Width = {entry.get('width_m')}m, "
                          f"Butt joints = {entry.get('num_butt_joints')}")
            lines.append(f"    {entry.get('message')}")
        elif 'nominal_thickness' in entry:
            # Mode 2's own-pane single-shot check (not a search). `res`
            # here is the ROW lookup's own status (COMPLIANT/
            # NON_COMPLIANT/NOT_PERMITTED - i.e. whether a valid Table
            # 5.3 minimum exists for this height/width/joint-count row
            # at all), not whether this specific nominal thickness
            # satisfies it - that comparison is shown separately.
            nt  = entry.get('nominal_thickness')
            req = entry.get('required_min_thickness_mm')
            lines.append(f"  Table 5.3 row lookup — {res}")
            if req is not None:
                passes = nt is not None and nt >= req
                lines.append(f"    Required minimum (Table 5.3 row) = {req}mm")
                lines.append(f"    Nominal thickness {nt}mm {'>=' if passes else '<'} required {req}mm — {'PASS' if passes else 'FAIL'}")
            lines.append(f"    {entry.get('message')}")
        else:
            # Per-thickness ascending search (Mode 1's own search, or
            # Mode 2's next-compliant-thickness search) - result is
            # PASS / FAIL, same vocabulary as ULS/SLS.
            req = entry.get('required_min_thickness_mm')
            lines.append(f"  Thickness {t}mm — {res}")
            if req is not None:
                lines.append(f"    Required minimum (Table 5.3 row) = {req}mm")
                if res == 'PASS':
                    lines.append(f"    Thickness {t}mm >= required {req}mm — PASS")
                else:
                    lines.append(f"    Thickness {t}mm < required {req}mm — FAIL")

    elif chk == 'SG':
        max_a    = entry.get('max_area')
        actual_a = entry.get('actual_area')
        if res == 'PASS':
            lines.append(f"  Thickness {t}mm — PASS")
            lines.append(f"    Panel area {actual_a}m2 <= max area {max_a}m2 — PASS")
        else:
            lines.append(f"  Thickness {t}mm — FAIL")
            lines.append(f"    Panel area {actual_a}m2 > max area {max_a}m2 — FAIL")

    elif chk == 'BITE':
        req = entry.get('required_bite_mm')
        lines.append(f"  Bite check ({entry.get('category')}) — {res}")
        if req is not None:
            lines.append(f"    Required bite = {req:.3f}mm — exceeds all available thicknesses")

    lines.append('')


def active_checks_label(checks):
    """
    Builds a "passes X, Y and Z" label from the actual checks tested
    at a next-compliant candidate, rather than a hardcoded "ULS and
    SLS" string - Table 5.3 (Pathway 2) and Safety Glass (Pathway 1)
    are only sometimes active, and a fixed string silently omits
    whichever check actually governed the search.
    """
    check_labels = {
        'ULS': 'ULS', 'SLS': 'SLS',
        'TABLE_5_3': 'Table 5.3', 'SG': 'Safety Glass Area Check',
    }
    seen = []
    for entry in checks:
        label = check_labels.get(entry.get('check'), entry.get('check'))
        if label and label not in seen:
            seen.append(label)
    if not seen:
        return 'all active checks'
    if len(seen) == 1:
        return seen[0]
    return ', '.join(seen[:-1]) + ' and ' + seen[-1]


def build_usable_bite_line(actual_thickness_mm, usable_bite_mm, required_bite_raw_mm,
                            required_bite_floored_mm, deduction_mm, deduction_type,
                            joint_type=None, mitre_angle_deg=None):
    """
    Builds the plain-language usable-bite transparency sentence shown under
    a silicone bite result (Pathway 3 and Pathway 4, this session) - exposes
    the arithmetic that was always computed (find_min_nominal_for_usable_bite(),
    engine/shared/table_4_1.py) but previously stopped at the final nominal
    thickness with no visible working. Display-only - no calculation change.

    Floor-triggered wording is keyed off required_bite_raw_mm !=
    required_bite_floored_mm, not a separate boolean - this is deliberate:
    Pathway 3's floor is applied to the required bite itself
    (run_bite_calculation()'s max(raw, 6.0)) while Pathway 4's only floor
    point is the final NOMINAL thickness (MIN_NOMINAL_THICKNESS) - see
    pathway4.py's make_pathway4_result() call for how that pathway maps its
    nominal floor back onto this same raw-vs-floored comparison. Both are
    the SAME underlying Dow Corning 6mm minimum-seal-thickness rule enforced
    at two different points in the chain, not two separate justifications -
    confirmed this session - so both use the identical floor-triggered
    prefix below.

    deduction_type: 'chamfer' (Pathway 3, faceted) or 'edge_polish'
    (Pathway 4, flat) - the only wording difference between the two callers.

    joint_type/mitre_angle_deg: Pathway 3 only (mitred joints show the
    /cos(angle) step; Pathway 4 has no mitre concept, both left None there).
    """
    deduction_label = 'chamfer' if deduction_type == 'chamfer' else 'edge polish'

    if joint_type == 'mitred' and mitre_angle_deg is not None:
        basis = (f"{actual_thickness_mm}mm actual thickness ÷ cos({mitre_angle_deg:.0f}°) "
                 f"− {deduction_mm}mm {deduction_label} deduction, mitred joint")
    elif joint_type is not None:
        basis = f"{actual_thickness_mm}mm actual thickness − {deduction_mm}mm {deduction_label} deduction, butt joint"
    else:
        basis = f"{actual_thickness_mm}mm actual thickness − {deduction_mm}mm {deduction_label} deduction"

    line = f"Usable bite: {usable_bite_mm:.1f}mm ({basis}) — meets the required {required_bite_floored_mm:.1f}mm"
    line += ' bite.' if joint_type is not None else '.'

    if required_bite_raw_mm != required_bite_floored_mm:
        line = (f"Required bite calculated at {required_bite_raw_mm:.1f}mm, floored to Dow "
                 f"Corning's 6.0mm minimum glueline/bite requirement. ") + line
    return line


def build_report(data):
    """
    Builds a plain text stepwise calculation report including full
    formula substitution and all thicknesses tested.
    """
    lines = []
    sep   = '=' * 65
    sep2  = '-' * 40

    lines.append(sep)
    lines.append('AS 1288 GLASS THICKNESS CALCULATOR')
    lines.append('Wind Loads Only — Duce Timber Windows and Doors')
    lines.append(sep)
    lines.append('')

    # --- Input summary ---
    lines.append('INPUTS')
    lines.append(sep2)
    lines.append(f"Calculation Mode      : {data.get('mode_label')}")
    lines.append(f"Panel Height          : {data.get('height_mm')} mm")
    lines.append(f"Panel Width           : {data.get('width_mm')} mm")
    lines.append(f"Support Condition     : {data.get('support_condition')}")
    if data.get('support_condition') == '2-edge':
        lines.append(f"Span Dimension        : {data.get('span_dimension')}")
    unframed_edge_condition = data.get('unframed_edge_condition')
    if unframed_edge_condition:
        lines.append(f"Unframed Edge Condition : {unframed_edge_condition} "
                      f"(AS 1288 Table 5.3 human impact check)")
    lines.append(f"Wind Load Method      : {data.get('wind_method_label')}")
    lines.append(f"ULS Wind Pressure     : {data.get('wind_pressure_uls')} kPa")
    lines.append(f"SLS Wind Pressure     : {data.get('wind_pressure_sls')} kPa")
    if data.get('wind_method') == 'nc':
        lines.append(f"N/C Rating            : {data.get('nc_rating')}")
        lines.append(f"Window Location       : {data.get('nc_location')}")
    lines.append(f"Glazing Configuration : {data.get('glazing_config_label')}")
    sg = data.get('safety_glass_required', False)
    lines.append(f"Safety Glass Required : {'Yes' if sg else 'No'}")
    lines.append('')

    # --- Panel geometry ---
    lines.append('PANEL GEOMETRY')
    lines.append(sep2)
    h  = float(data.get('height_mm'))
    w  = float(data.get('width_mm'))
    ar = max(h, w) / min(h, w)
    lines.append(f"Aspect Ratio (AR)     : {ar:.3f} (longest / shortest)")
    sc = data.get('support_condition')
    if sc == '4-edge':
        span = min(h, w)
        table_ars = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 5.0]
        table_ar  = next((t for t in table_ars if ar <= t), 5.0)
        lines.append(f"Table AR Used         : {table_ar} (rounded up conservatively)")
        lines.append(f"Structural Span       : {span:.0f} mm (shortest dimension)")
    else:
        span_dim = data.get('span_dimension')
        span     = h if span_dim == 'height' else w
        lines.append(f"Table AR Used         : Independent (2-edge)")
        lines.append(f"Structural Span       : {span:.0f} mm ({span_dim} dimension)")
    lines.append(f"Panel Area            : {(h * w / 1_000_000):.4f} m2")
    lines.append('')

    mode    = data.get('mode')
    results = data.get('results', [])

    if mode == 'mode1':
        lines.append('RESULTS — MINIMUM THICKNESS')
        lines.append(sep2)

        for r in results:
            lines.append('')
            lines.append(f"GLASS TYPE: {r.get('glass_type')} {r.get('glass_subtype')}")
            lines.append(sep2)
            lines.append(f"Status : {r.get('status')}")
            lines.append('')

            if r.get('status') == 'PASS':
                kp  = r.get('k_pane', 1.0)
                c1s = {'Laminated_Heat-strengthened': 1.6, 'Laminated_Toughened': 2.5}
                c1  = c1s.get(f"{r.get('glass_type')}_{r.get('glass_subtype')}", 1.0)
                uls = float(data.get('wind_pressure_uls'))
                sls = float(data.get('wind_pressure_sls'))

                lines.append(f"Applied pressures:")
                lines.append(f"  k_pane         = {kp:.4f}")
                lines.append(f"  c1 factor      = {c1}")
                lines.append(f"  Effective ULS  = {kp} x {uls:.4f} / {c1} = {(kp * uls / c1):.4f} kPa")
                lines.append(f"  Effective SLS  = {kp} x {sls:.4f} / {c1} = {(kp * sls / c1):.4f} kPa")
                lines.append('')

                # ULS trace
                lines.append(f"ULS CHECK — {r.get('glass_type')} {r.get('glass_subtype')}")
                lines.append(f"Formula: B = k1 x (Pu + k2)^k3 + k4")
                lines.append(f"Structural span = {span:.0f} mm")
                lines.append('')
                for entry in r.get('uls_trace', []):
                    format_trace_entry(entry, lines)
                lines.append(f"ULS Minimum Thickness = {r.get('uls_minimum_thickness_mm')} mm")
                lines.append('')

                # SLS trace
                lines.append(f"SLS CHECK — {r.get('glass_type')} {r.get('glass_subtype')}")
                lines.append(f"Formula: B = t x (k1 x (Ps + k2)^k3 + k4)")
                lines.append(f"Independent search from thinnest available thickness "
                              f"(not dependent on the ULS result — Section 7.6)")
                lines.append('')
                for entry in r.get('sls_trace', []):
                    format_trace_entry(entry, lines)
                lines.append(f"SLS Minimum Thickness = {r.get('sls_minimum_thickness_mm')} mm")
                lines.append('')

                # Table 5.3 trace (2-edge/3-edge only — replaces Table 5.1
                # entirely in this branch, Section 14.2). Labelled as its
                # own section alongside ULS/SLS, not folded into a generic
                # message.
                if r.get('table_5_3_trace'):
                    lines.append(f"TABLE 5.3 CHECK — AS 1288 Table 5.3 "
                                  f"(Unframed Side Edges, {unframed_edge_condition})")
                    lines.append(f"Independent search from thinnest available thickness "
                                  f"(not dependent on ULS/SLS — Section 7.6)")
                    lines.append('')
                    for entry in r.get('table_5_3_trace', []):
                        format_trace_entry(entry, lines)
                    lines.append(f"Table 5.3 Minimum Thickness = {r.get('table_5_3_minimum_thickness_mm')} mm")
                    lines.append('')

                # 3mm Annealed area flag
                if r.get('annealed_area_flag'):
                    flag = r['annealed_area_flag']
                    lines.append(f"3MM ANNEALED AREA RESTRICTION")
                    lines.append(f"  Panel area {flag['actual_area']}m2 exceeds maximum {flag['max_area']}m2.")
                    lines.append(f"  3mm not permitted. Minimum thickness increased to 4mm.")
                    lines.append('')

                # Safety Glass trace
                if sg and r.get('sg_trace'):
                    lines.append(f"SAFETY GLASS AREA CHECK — AS 1288 Table 5.1")
                    lines.append(f"Independent search from thinnest available thickness "
                                  f"(not dependent on ULS/SLS — Section 7.6)")
                    lines.append('')
                    for entry in r.get('sg_trace', []):
                        format_trace_entry(entry, lines)
                    lines.append(f"Safety Glass Minimum Thickness = {r.get('sg_minimum_thickness_mm')} mm")
                    lines.append('')

                lines.append(f"FINAL MINIMUM THICKNESS (GOVERNING) = {r.get('minimum_thickness_mm')} mm")
                lines.append('')

            else:
                lines.append(f"Message: {r.get('message')}")
                lines.append('')
                # TABLE_5_3_NOT_PERMITTED / NO_COMPLIANT_THICKNESS (Table
                # 5.3 branch) still carry a row-level trace even though no
                # PASS was ever reached — show it labelled rather than
                # leaving the raw message as the only explanation.
                if r.get('status') in ('TABLE_5_3_NOT_PERMITTED', 'NO_COMPLIANT_THICKNESS') and r.get('table_5_3_trace'):
                    lines.append(f"TABLE 5.3 CHECK — AS 1288 Table 5.3 "
                                  f"(Unframed Side Edges, {unframed_edge_condition})")
                    lines.append('')
                    for entry in r.get('table_5_3_trace', []):
                        format_trace_entry(entry, lines)

    else:
        lines.append('RESULTS — COMPLIANCE CHECK')
        lines.append(sep2)

        for r in results:
            lines.append('')
            lines.append(f"PANE: {r.get('pane_label')} — {r.get('glass_type')} {r.get('glass_subtype')}")
            lines.append(sep2)
            lines.append(f"Actual Thickness  : {r.get('actual_thickness_mm')} mm")
            lines.append(f"Nominal Thickness : {r.get('nominal_thickness_mm')} mm (AS 1288 Table 4.1)")
            lines.append('')

            if r.get('k_pane') is not None:
                lines.append(f"Applied pressures:")
                lines.append(f"  k_pane         = {r.get('k_pane'):.4f}")
                lines.append(f"  Effective ULS  = {r.get('effective_uls_pa', 0):.0f} Pa = {r.get('effective_uls_pa', 0) / 1000:.4f} kPa")
                lines.append(f"  Effective SLS  = {r.get('effective_sls_pa', 0):.0f} Pa = {r.get('effective_sls_pa', 0) / 1000:.4f} kPa")
                lines.append('')

            lines.append(f"ULS CHECK")
            lines.append(f"Formula: B = k1 x (Pu + k2)^k3 + k4")
            lines.append('')
            for entry in r.get('uls_trace', []):
                format_trace_entry(entry, lines)

            lines.append(f"SLS CHECK")
            lines.append(f"Formula: B = t x (k1 x (Ps + k2)^k3 + k4)")
            lines.append('')
            for entry in r.get('sls_trace', []):
                format_trace_entry(entry, lines)

            # Table 5.3 trace (2-edge/3-edge only — replaces Table 5.1
            # entirely in this branch, Section 14.2). Present even on the
            # TABLE_5_3_NOT_PERMITTED hard-gate early return (which skips
            # the k_pane/ULS/SLS block above but still carries a row-level
            # trace) — labelled here rather than left as a bare status.
            if r.get('table_5_3_trace'):
                lines.append(f"TABLE 5.3 CHECK — AS 1288 Table 5.3 "
                              f"(Unframed Side Edges, {unframed_edge_condition})")
                lines.append('')
                for entry in r.get('table_5_3_trace', []):
                    format_trace_entry(entry, lines)
                if r.get('table_5_3_status'):
                    lines.append(f"Table 5.3 Result = {r.get('table_5_3_status')} "
                                  f"(nominal {r.get('nominal_thickness_mm')}mm vs "
                                  f"required {r.get('table_5_3_min_thickness_mm')}mm)")
                    lines.append('')

            if r.get('status') == 'TABLE_5_3_NOT_PERMITTED':
                lines.append(f"Message: {r.get('message')}")
                lines.append('')

            if r.get('annealed_area_flag'):
                flag = r['annealed_area_flag']
                lines.append(f"3MM ANNEALED AREA RESTRICTION")
                lines.append(f"  Panel area {flag['actual_area']}m2 exceeds maximum {flag['max_area']}m2.")
                lines.append('')

            if sg and r.get('sg_trace'):
                lines.append(f"SAFETY GLASS AREA CHECK — AS 1288 Table 5.1")
                lines.append('')
                for entry in r.get('sg_trace', []):
                    format_trace_entry(entry, lines)

            lines.append(f"OVERALL RESULT : {r.get('status')}")
            lines.append('')

            if r.get('status') == 'FAIL':
                next_trace = r.get('next_compliant_trace', [])
                if next_trace:
                    lines.append('SEARCH FOR NEXT COMPLIANT THICKNESS')
                    lines.append(sep2)
                    lines.append('')

                    for candidate in next_trace:
                        t       = candidate.get('thickness')
                        overall = candidate.get('overall')
                        lines.append(f"Testing thickness {t}mm against all active checks:")
                        lines.append('')

                        for entry in candidate.get('checks', []):
                            format_trace_entry(entry, lines)

                        if overall == 'PASS':
                            lines.append(f"  All active checks pass at {t}mm.")
                            checks_label = active_checks_label(candidate.get('checks', []))
                            lines.append(f"  Next compliant thickness = {t}mm — passes {checks_label}.")
                        else:
                            reason = candidate.get('fail_reason', 'unknown check')
                            lines.append(f"  {t}mm does not pass all checks ({reason} failed). Moving to next thickness.")
                        lines.append('')

                elif r.get('next_compliant_thickness_mm'):
                    # Fallback path - next_compliant_trace is empty but a
                    # thickness was still found. No per-candidate checks
                    # list is available here to derive the label from
                    # (see active_checks_label above), so it's built from
                    # the pane's own active-check flags instead - same
                    # "don't hardcode ULS/SLS" fix, applied with the best
                    # information this branch actually has.
                    check_names = ['ULS', 'SLS']
                    if r.get('table_5_3_status') is not None:
                        check_names.append('Table 5.3')
                    if sg:
                        check_names.append('Safety Glass Area Check')
                    checks_label = check_names[0] if len(check_names) == 1 else ', '.join(check_names[:-1]) + ' and ' + check_names[-1]
                    lines.append(f"Next compliant thickness: {r.get('next_compliant_thickness_mm')}mm — passes {checks_label}.")
                    lines.append('')

    lines.append(sep)
    # Human impact footer (supersedes v1.13's wording entirely, per this
    # session's decision): absent completely when the safety glass toggle
    # is off - the tool made no human impact assessment, so no claim is
    # made either way. When on, names whichever table actually governed
    # this pathway (Table 5.3 for Pathway 2's unframed-edge configurations,
    # Table 5.1 otherwise) - never both, since no case runs both at once.
    # Must match the on-screen footer (updateHumanImpactFooter() in
    # index.html) word for word.
    if sg:
        table_ref = 'Table 5.3' if unframed_edge_condition else 'Table 5.1'
        lines.append(f'NOTE: Safety glass requirements ({table_ref}) have been applied to the')
        lines.append('thickness selection as declared by the user. This tool does not assess')
        lines.append('whether safety glass is required for this application. The user is')
        lines.append('responsible for determining applicability in accordance with AS 1288')
        lines.append('Section 5 and relevant building codes.')
    lines.append(sep)

    return '\n'.join(lines)


def build_pathway3_report(data):
    """
    Builds a plain text stepwise calculation report for Pathway 3 (Faceted
    Structural Silicone, Section 14.3) - one labelled section per selected
    glass subtype, following the same trace-driven structure as build_report()
    (Section 6.5) rather than folding results into an opaque summary string.
    """
    lines = []
    sep   = '=' * 65
    sep2  = '-' * 40

    lines.append(sep)
    lines.append('AS 1288 GLASS THICKNESS CALCULATOR')
    lines.append('Pathway 3 — Faceted Structural Silicone (90-160°)')
    lines.append('Duce Timber Windows and Doors')
    lines.append(sep)
    lines.append('')

    angle_deg = data.get('angle_deg')
    unframed_edge_condition = data.get('unframed_edge_condition')
    sg = data.get('safety_glass_required', False)

    # --- Input summary ---
    lines.append('INPUTS')
    lines.append(sep2)
    lines.append(f"Panel Height          : {data.get('height_mm')} mm")
    lines.append(f"Width 1               : {data.get('width_1_mm')} mm")
    lines.append(f"Width 2               : {data.get('width_2_mm')} mm")
    lines.append(f"Included Angle        : {angle_deg}°")
    lines.append(f"Joint Type            : {data.get('joint_type')}")
    if sg and angle_deg is not None and angle_deg != 90:
        lines.append(f"Unframed Edge Condition : {unframed_edge_condition} "
                      f"(AS 1288 Table 5.3 human impact check)")
    lines.append(f"ULS Wind Pressure     : {data.get('wind_pressure_uls')} kPa")
    lines.append(f"SLS Wind Pressure     : {data.get('wind_pressure_sls')} kPa")
    lines.append(f"Safety Glass Required : {'Yes' if sg else 'No'}")
    lines.append('')

    human_impact_table = 'Table 5.1' if angle_deg == 90 else 'Table 5.3'

    results = data.get('results', [])

    lines.append('RESULTS — PER GLASS SUBTYPE')
    lines.append(sep2)

    for r in results:
        lines.append('')
        lines.append(f"GLASS SUBTYPE: {r.get('glass_type')} {r.get('glass_subtype')}")
        lines.append(sep2)
        lines.append(f"Status : {r.get('status')}")
        lines.append('')

        if r.get('status') == 'BITE_NO_COMPLIANT_THICKNESS':
            lines.append(f"Message: {r.get('message')}")
            lines.append('')
            for entry in r.get('bite_trace', []):
                format_trace_entry(entry, lines)
            continue

        # --- Silicone bite (Section 9 / Clause 9.3.3.1) ---
        lines.append(f"SILICONE BITE CHECK — AS 1288 Section 9")
        lines.append(f"Governing width B = larger of Width 1/Width 2")
        lines.append('')
        req_raw = r.get('required_bite_raw_mm')
        lines.append(f"Bite Minimum Nominal Thickness = {r.get('bite_thickness_mm')} mm"
                      + (f" ({req_raw:.1f}mm required)" if req_raw is not None else ""))
        if r.get('usable_bite_mm') is not None:
            lines.append(build_usable_bite_line(
                actual_thickness_mm=r.get('actual_thickness_mm'),
                usable_bite_mm=r.get('usable_bite_mm'),
                required_bite_raw_mm=r.get('required_bite_raw_mm'),
                required_bite_floored_mm=r.get('required_bite_floored_mm'),
                deduction_mm=r.get('deduction_mm'), deduction_type=r.get('deduction_type'),
                joint_type=data.get('joint_type'), mitre_angle_deg=r.get('mitre_angle_deg'),
            ))
        lines.append('')

        if r.get('status') in ('WIND_NO_COMPLIANT_THICKNESS', 'ERROR'):
            lines.append(f"Message: {r.get('message')}")
            lines.append('')
            continue

        # --- Wind ULS/SLS (Section 4, 4-edge - bite makes the joint a
        # structural edge, Section 14.3) ---
        lines.append(f"WIND LOAD CHECK — AS 1288 Section 4 (4-edge)")
        lines.append('')
        for entry in r.get('wind_trace', []):
            format_trace_entry(entry, lines)
        lines.append(f"ULS Minimum Thickness = {r.get('uls_thickness_mm')} mm")
        lines.append(f"SLS Minimum Thickness = {r.get('sls_thickness_mm')} mm")
        lines.append('')

        # --- Human impact (Table 5.1 at exactly 90 deg, Table 5.3 for
        # >90-160 deg - gated on the safety glass toggle, Section 14.7) ---
        if sg:
            lines.append(f"HUMAN IMPACT CHECK — AS 1288 {human_impact_table}")
            if human_impact_table == 'Table 5.3':
                lines.append(f"Unframed edge condition: {unframed_edge_condition}")
            lines.append('')
            for entry in r.get('human_impact_trace', []):
                format_trace_entry(entry, lines)

            if r.get('status') == 'HUMAN_IMPACT_INELIGIBLE':
                lines.append(f"{r.get('glass_type')} {r.get('glass_subtype')} is not classified as "
                              f"safety glass and cannot be used when safety glass is required.")
                lines.append('')
            elif r.get('status') in ('HUMAN_IMPACT_NOT_PERMITTED', 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS'):
                lines.append(f"Message: {r.get('message')}")
                lines.append('')
            else:
                lines.append(f"{human_impact_table} Minimum Thickness = {r.get('human_impact_thickness_mm')} mm")
                lines.append('')

        if r.get('status') == 'PASS':
            lines.append(f"FINAL GOVERNING THICKNESS = {r.get('governing_thickness_mm')} mm")
            lines.append('')
        elif r.get('status') == 'HUMAN_IMPACT_INELIGIBLE':
            # Bite/wind still govern for this subtype - the tool has not
            # abandoned the calculation, only the human impact component
            # (Section 12.13 step 4 / this pathway's own eligibility gate).
            lines.append(f"FINAL GOVERNING THICKNESS (bite/wind only — ineligible for "
                          f"{human_impact_table}) = {r.get('governing_thickness_mm')} mm")
            lines.append('')

    lines.append(sep)
    # Human impact footer - identical wording/gating rule to build_report()'s
    # (Section 14.7), naming whichever table actually applies for this angle.
    if sg:
        lines.append(f'NOTE: Safety glass requirements ({human_impact_table}) have been applied to the')
        lines.append('thickness selection as declared by the user. This tool does not assess')
        lines.append('whether safety glass is required for this application. The user is')
        lines.append('responsible for determining applicability in accordance with AS 1288')
        lines.append('Section 5 and relevant building codes.')
    lines.append(sep)

    return '\n'.join(lines)


P4_CRITERION_LABELS = {
    'dead_load_bite': 'Silicone bite (dead load)',
    'wind_bite':      'Silicone bite (wind load)',
    'uls':            'ULS wind load (glass)',
    'sls':            'SLS wind load (glass)',
    'table_5_1':      'Table 5.1',
}


def build_pathway4_report(data):
    """
    Builds a plain text stepwise calculation report for Pathway 4 (Structural
    Glazing, Section 14.4) - one labelled section per selected glass subtype,
    same trace-driven structure as build_pathway3_report() (Section 6.5).

    Five independent criteria per subtype (this session, closing the gap
    where Pathway 4 never checked the glass pane's own AS 1288 Clause 4.4.3
    ULS/SLS bending capacity, only the silicone joint's bite sizing - Section
    14.4 always specified both):
    - Silicone bite (dead load) / (wind load): independent Table 4.1 lookups,
      per broad category (Monolithic/Laminated), not per subtype.
    - ULS / SLS wind load on the glass pane: per subtype (c1 factor differs
      by glass_type/glass_subtype), full k-value trace reused via
      format_trace_entry() (same ULS/SLS trace shape as Mode 1/Pathway 3).
    - Table 5.1: per subtype, gated on the safety glass toggle, unchanged
      structure from v1.22.
    Governing criterion is named explicitly per subtype.

    wind_bite_mm/dead_load_bite_mm (raw, pre-Table-4.1-lookup figures) are
    read from the first entry in results (identical across every subtype -
    run_structural_glazing_calculation() is called once per pathway
    invocation with a single fixed glass_thickness_nominal_mm seed).
    wind_span_m/dead_load_perimeter_m come from the request payload (pure
    geometry, computed inline in the /calculate_pathway4 route). This
    breakdown is only ever shown in the TXT report, never on-screen, matching
    Section 6.5's established convention that full trace detail belongs in
    the downloadable report only.
    """
    lines = []
    sep   = '=' * 65
    sep2  = '-' * 40

    lines.append(sep)
    lines.append('AS 1288 GLASS THICKNESS CALCULATOR')
    lines.append('Pathway 4 — Structural Glazing (Flat, No Frame)')
    lines.append('Duce Timber Windows and Doors')
    lines.append(sep)
    lines.append('')

    sg = data.get('safety_glass_required', False)

    # --- Input summary ---
    lines.append('INPUTS')
    lines.append(sep2)
    lines.append(f"Panel Height          : {data.get('height_mm')} mm")
    lines.append(f"Panel Width           : {data.get('width_mm')} mm")
    if data.get('wind_method') == 'pressure':
        lines.append(f"ULS Wind Pressure     : {data.get('uls_kpa')} kPa")
        lines.append(f"SLS Wind Pressure     : {data.get('sls_kpa')} kPa")
    else:
        lines.append(f"Wind Classification   : {data.get('nc_rating')} ({data.get('nc_location')})")
        lines.append(f"Resolved ULS/SLS      : {data.get('uls_kpa')} kPa / {data.get('sls_kpa')} kPa")
    lines.append(f"Scenario              : full_perimeter (sealed on all four edges)")
    lines.append(f"Safety Glass Required : {'Yes' if sg else 'No'}")
    lines.append('')

    results = data.get('results', [])

    # --- Wind bite / dead load breakdown (Appendix F + Section 12.11) ---
    # Dead load is always computed - there is no toggle for it (this
    # session's confirmed decision) - so this section is unconditional.
    # wind_bite_mm/dead_load_bite_mm read from the first result entry -
    # identical across every subtype/category for a given request (see
    # docstring above) - rather than a second call to the structural
    # glazing engine.
    if results:
        wind_bite_mm = results[0].get('wind_bite_mm')
        dead_load_bite_mm = results[0].get('dead_load_bite_mm')

        lines.append('SILICONE BITE CHECK — AS 1288 Appendix F (wind) + Section 12.11 (dead load)')
        lines.append(sep2)
        lines.append(f"Wind span B (shorter of height/width) = {data.get('wind_span_m')} m")
        lines.append(f"Dead load perimeter (full_perimeter = 2xheight + 2xwidth) = {data.get('dead_load_perimeter_m')} m")
        lines.append(f"Wind bite = 0.5 x Pz(ULS) x B / sigma_s = {wind_bite_mm} mm")
        lines.append(f"Dead load bite = (density x g x thickness x area) / (perimeter x allowable stress) = {dead_load_bite_mm} mm")
        lines.append('(Edge-polish deduction of 2mm and 6mm minimum floor applied before/after')
        lines.append('the Table 4.1 lookup, both glass types - see per-subtype nominal figures below)')
        lines.append('')

    lines.append('RESULTS — PER GLASS SUBTYPE')
    lines.append(sep2)

    for r in results:
        lines.append('')
        lines.append(f"GLASS SUBTYPE: {r.get('glass_type')} {r.get('glass_subtype')}")
        lines.append(sep2)
        lines.append(f"Status : {r.get('status')}")
        lines.append('')

        if r.get('status') == 'BITE_NO_COMPLIANT_THICKNESS':
            lines.append(f"Message: {r.get('message')}")
            lines.append('')
            continue

        # --- Silicone bite, independent per-criterion nominal thicknesses ---
        dead_req_raw = r.get('dead_load_required_bite_raw_mm')
        wind_req_raw = r.get('wind_required_bite_raw_mm')
        lines.append(f"Silicone Bite (Dead Load) Minimum Nominal Thickness = {r.get('dead_load_bite_nominal_mm')} mm"
                      + (f" ({dead_req_raw:.1f}mm required)" if dead_req_raw is not None else ""))
        if r.get('dead_load_usable_bite_mm') is not None:
            lines.append(build_usable_bite_line(
                actual_thickness_mm=r.get('dead_load_actual_thickness_mm'),
                usable_bite_mm=r.get('dead_load_usable_bite_mm'),
                required_bite_raw_mm=r.get('dead_load_required_bite_raw_mm'),
                required_bite_floored_mm=r.get('dead_load_required_bite_floored_mm'),
                deduction_mm=r.get('deduction_mm'), deduction_type=r.get('deduction_type'),
            ))
        lines.append(f"Silicone Bite (Wind Load) Minimum Nominal Thickness = {r.get('wind_bite_nominal_mm')} mm"
                      + (f" ({wind_req_raw:.1f}mm required)" if wind_req_raw is not None else ""))
        if r.get('wind_usable_bite_mm') is not None:
            lines.append(build_usable_bite_line(
                actual_thickness_mm=r.get('wind_actual_thickness_mm'),
                usable_bite_mm=r.get('wind_usable_bite_mm'),
                required_bite_raw_mm=r.get('wind_required_bite_raw_mm'),
                required_bite_floored_mm=r.get('wind_required_bite_floored_mm'),
                deduction_mm=r.get('deduction_mm'), deduction_type=r.get('deduction_type'),
            ))
        lines.append('')

        if r.get('status') == 'WIND_NO_COMPLIANT_THICKNESS':
            lines.append(f"Message: {r.get('message')}")
            lines.append('')
            for entry in r.get('wind_trace', []):
                format_trace_entry(entry, lines)
            continue

        # --- Wind bending on the glass pane itself (Clause 4.4.3, 4-edge -
        # new this session, closing the gap flagged after v1.24) ---
        lines.append(f"WIND LOAD CHECK (GLASS PANE) — AS 1288 Section 4 / Clause 4.4.3 (4-edge)")
        lines.append('')
        for entry in r.get('wind_trace', []):
            format_trace_entry(entry, lines)
        lines.append(f"ULS Minimum Thickness = {r.get('uls_thickness_mm')} mm")
        lines.append(f"SLS Minimum Thickness = {r.get('sls_thickness_mm')} mm")
        lines.append('')

        # --- Human impact (Table 5.1, full_perimeter only - Section 14.4/
        # 14.7/12.12 item 9) - gated on the safety glass toggle ---
        if sg:
            lines.append(f"HUMAN IMPACT CHECK — AS 1288 Table 5.1")
            lines.append('')
            for entry in r.get('table_5_1_trace', []):
                format_trace_entry(entry, lines)

            if r.get('status') == 'HUMAN_IMPACT_INELIGIBLE':
                lines.append(f"{r.get('glass_type')} {r.get('glass_subtype')} is not classified as "
                              f"safety glass and cannot be used when safety glass is required.")
                lines.append('')
            elif r.get('status') == 'HUMAN_IMPACT_NO_COMPLIANT_THICKNESS':
                lines.append(f"Message: {r.get('message')}")
                lines.append('')
            else:
                lines.append(f"Table 5.1 Minimum Thickness = {r.get('table_5_1_thickness_mm')} mm")
                lines.append('')

        governing_label = P4_CRITERION_LABELS.get(r.get('governing_criterion'), r.get('governing_criterion'))

        if r.get('status') == 'PASS':
            lines.append(f"Governing criterion: {governing_label}")
            lines.append(f"FINAL GOVERNING THICKNESS = {r.get('governing_thickness_mm')} mm")
            lines.append('')
        elif r.get('status') == 'HUMAN_IMPACT_INELIGIBLE':
            lines.append(f"Governing criterion: {governing_label} (ineligible for Table 5.1)")
            lines.append(f"FINAL GOVERNING THICKNESS = {r.get('governing_thickness_mm')} mm")
            lines.append('')

    lines.append(sep)
    # Human impact footer - identical wording/gating rule to build_report()'s
    # / build_pathway3_report()'s (Section 14.7).
    if sg:
        lines.append('NOTE: Safety glass requirements (Table 5.1) have been applied to the')
        lines.append('thickness selection as declared by the user. This tool does not assess')
        lines.append('whether safety glass is required for this application. The user is')
        lines.append('responsible for determining applicability in accordance with AS 1288')
        lines.append('Section 5 and relevant building codes.')
    lines.append(sep)

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# RUN THE SERVER
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print()
    print('=' * 65)
    print('  AS 1288 Glass Thickness Calculator')
    print('  Duce Timber Windows and Doors')
    print('  Starting server...')
    print('=' * 65)
    print()

    # Get the local IP address to display for network access
    import socket
    try:
        hostname   = socket.gethostname()
        local_ip   = socket.gethostbyname(hostname)
    except Exception:
        local_ip   = '(could not determine IP)'

    print(f"  Local access : http://localhost:5000")
    print(f"  Network access : http://{local_ip}:5000")
    print()
    print("  Share the network address with your team.")
    print("  Press Ctrl+C to stop the server.")
    print()

    app.run(host='0.0.0.0', port=5000, debug=False) 