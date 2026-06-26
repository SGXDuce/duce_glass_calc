import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'checks'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from data_loader import load_table_data, load_nominal_thickness_table
from wind import check_glass_type, check_pane_compliance
from formulas import get_ar_interpolation_bounds, calculate_span, calculate_ar


def run_calculation(csv_path, height_mm, width_mm, support_condition,
                    span_dimension, wind_pressure_uls, wind_pressure_sls,
                    selected_glass_types, glazing_config,
                    safety_glass_required=False, preloaded_df=None,
                    bushfire_required=False, bal_level=None,
                    element_type=None):
    """
    Master function for Mode 1 - Minimum Thickness Finder.
    Runs the full check for every selected glass type.
    Returns a list of result dicts, one per selected glass type.

    preloaded_df: optional - if provided, skips reloading the CSV from disk.
    """
    df = preloaded_df if preloaded_df is not None else load_table_data(csv_path)

    results = []
    for (glass_type, glass_subtype) in selected_glass_types:
        result = check_glass_type(
            df, glass_type, glass_subtype,
            height_mm, width_mm,
            support_condition, span_dimension,
            wind_pressure_uls, wind_pressure_sls,
            glazing_config, safety_glass_required,
            bushfire_required, bal_level, element_type
        )
        results.append(result)

    return results


def run_compliance_check(csv_path, nominal_thickness_csv_path,
                         height_mm, width_mm,
                         support_condition, span_dimension,
                         wind_pressure_uls, wind_pressure_sls,
                         panes, safety_glass_required=False,
                         preloaded_df=None, preloaded_df_nominal=None,
                         bushfire_required=False, bal_level=None,
                         element_type=None):
    """
    Master function for Mode 2 - Compliance Checker.

    panes is a list of dicts, one per pane:
        [{'label': 'Outer', 'glass_type': 'Monolithic',
          'glass_subtype': 'Toughened', 'actual_thickness_mm': 6.0}, ...]

    preloaded_df / preloaded_df_nominal: optional - if provided, skips
    reloading the CSVs from disk.

    Returns a list of compliance result dicts, one per pane.
    """
    df         = preloaded_df if preloaded_df is not None else load_table_data(csv_path)
    df_nominal = preloaded_df_nominal if preloaded_df_nominal is not None else load_nominal_thickness_table(nominal_thickness_csv_path)

    actual_ar = calculate_ar(height_mm, width_mm)
    span      = calculate_span(height_mm, width_mm, support_condition, span_dimension)

    ar_bounds = get_ar_interpolation_bounds(actual_ar) if support_condition == '4-edge' else None

    glazing_config_map = {1: 'single', 2: 'double', 3: 'triple'}
    glazing_config = glazing_config_map.get(len(panes), 'single')

    all_actual_thicknesses = [pane['actual_thickness_mm'] for pane in panes]

    results = []
    for pane in panes:
        result = check_pane_compliance(
            df, df_nominal,
            pane['glass_type'], pane['glass_subtype'],
            pane['actual_thickness_mm'],
            all_actual_thicknesses,
            span, height_mm, width_mm,
            ar_bounds, support_condition,
            wind_pressure_uls, wind_pressure_sls,
            pane['label'], glazing_config,
            safety_glass_required,
            bushfire_required, bal_level, element_type
        )
        results.append(result)

    return results
