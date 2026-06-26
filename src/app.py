# AS 1288 Glass Thickness Calculator - Flask Web Application
# Duce Timber Windows and Doors

from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import io

# Add the src folder to the path so we can import calculator.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculator import (
    run_calculation,
    run_compliance_check,
    load_nc_table,
    get_pressures_from_nc_rating
)

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
    DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

CSV_PATH = os.path.join(DATA_DIR, 'Wind_Load_Check_Tables_Full.csv')
NC_CSV_PATH = os.path.join(DATA_DIR, 'N_C_Tables.csv')
NOMINAL_CSV_PATH = os.path.join(DATA_DIR, 'Table_4_1_Minimum_Glass_Thickness.csv')

# Load all data tables once at startup instead of on every request
from calculator import load_table_data, load_nc_table, load_nominal_thickness_table

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
    return render_template('index.html')


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
                element_type          = element_type
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
                element_type               = element_type
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


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """
    Receives calculation inputs and results, generates a TXT report,
    and returns it as a downloadable file.
    """
    try:
        data    = request.get_json()
        report  = build_report(data)
        buffer  = io.BytesIO(report.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='text/plain',
            as_attachment=True,
            download_name='AS1288_Calculation_Report.txt'
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# REPORT BUILDER
# ---------------------------------------------------------------------------

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

    def format_trace_entry(entry, lines):
        """Formats a single trace entry into report lines."""
        chk = entry.get('check')
        t   = entry.get('thickness')
        res = entry.get('result')

        if chk in ('ULS', 'SLS'):
            k1  = entry.get('k1')
            k2  = entry.get('k2')
            k3  = entry.get('k3')
            k4  = entry.get('k4')
            p   = entry.get('pressure_kpa')
            B   = entry.get('B')
            sp  = entry.get('span')

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

        elif chk == 'SG':
            max_a    = entry.get('max_area')
            actual_a = entry.get('actual_area')
            if res == 'EXTRAPOLATE':
                lines.append(f"  Thickness {t}mm — EXTRAPOLATE")
                lines.append(f"    Thickness exceeds AS 1288 Table 5.1 scope.")
                lines.append(f"    Manual extrapolation required.")
            elif res == 'PASS':
                lines.append(f"  Thickness {t}mm — PASS")
                lines.append(f"    Panel area {actual_a}m2 <= max area {max_a}m2 — PASS")
            else:
                lines.append(f"  Thickness {t}mm — FAIL")
                lines.append(f"    Panel area {actual_a}m2 > max area {max_a}m2 — FAIL")

        lines.append('')

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
                lines.append(f"Starting from ULS minimum thickness {r.get('uls_minimum_thickness_mm')}mm")
                lines.append('')
                for entry in r.get('sls_trace', []):
                    format_trace_entry(entry, lines)
                lines.append(f"SLS Minimum Thickness = {r.get('sls_minimum_thickness_mm')} mm")
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
                    lines.append(f"Starting from wind load governing thickness")
                    lines.append('')
                    for entry in r.get('sg_trace', []):
                        format_trace_entry(entry, lines)
                    if r.get('sg_flag') == 'EXTRAPOLATE':
                        lines.append(f"Safety Glass Check = Exceeds Table 5.1 scope. Manual extrapolation required.")
                    else:
                        lines.append(f"Safety Glass Minimum Thickness = {r.get('sg_minimum_thickness_mm')} mm")
                    lines.append('')

                lines.append(f"FINAL MINIMUM THICKNESS (GOVERNING) = {r.get('minimum_thickness_mm')} mm")
                lines.append('')

            else:
                lines.append(f"Message: {r.get('message')}")
                lines.append('')

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
                            sg_suffix = ', and Safety Glass Area Check' if sg else ''
                            lines.append(f"  Next compliant thickness = {t}mm — passes ULS and SLS{sg_suffix}.")
                        else:
                            reason = candidate.get('fail_reason', 'unknown check')
                            lines.append(f"  {t}mm does not pass all checks ({reason} failed). Moving to next thickness.")
                        lines.append('')

                elif r.get('next_compliant_thickness_mm'):
                    sg_suffix = ', and Safety Glass Area Check' if sg else ''
                    lines.append(f"Next compliant thickness: {r.get('next_compliant_thickness_mm')}mm — passes ULS and SLS{sg_suffix}.")
                    lines.append('')

    lines.append(sep)
    lines.append('NOTE: Human Impact requirements have not been considered.')
    lines.append('Results are for Wind Load resistance only (AS 1288 Section 4).')
    if sg:
        lines.append('')
        lines.append('NOTE: Safety glass requirement was declared by the user.')
        lines.append('This tool does not assess whether safety glass is required.')
        lines.append('Please refer to AS 1288 Section 5.')
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