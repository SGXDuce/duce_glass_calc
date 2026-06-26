# AS 1288 Glass Thickness Calculator
# Phase 1 - Core calculation engine
# Duce Timber Windows and Doors

import pandas as pd
import os

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_table_data(csv_path):
    """
    Loads the wind load coefficient table from the CSV file.
    Returns a pandas DataFrame with all 315 rows of k values.
    """
    df = pd.read_csv(csv_path)
    numeric_columns = ['k1', 'k2', 'k3', 'k4']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    return df


def load_nc_table(csv_path):
    """
    Loads the N/C wind classification pressure table from CSV.
    Returns a pandas DataFrame.
    """
    return pd.read_csv(csv_path)


def load_nominal_thickness_table(csv_path):
    """
    Loads the Table 4.1 nominal thickness lookup table from CSV.
    Returns a pandas DataFrame.
    """
    return pd.read_csv(csv_path)


# ---------------------------------------------------------------------------
# SAFETY GLASS AREA TABLE (AS 1288 Table 5.1) - hardcoded
# ---------------------------------------------------------------------------
# Category 1: Monolithic Toughened and Toughened Laminated
# Category 2: Laminated Annealed and Heat-strengthened Laminated
# All entries are for 4-edge supported panels only
# Key: nominal thickness in mm, Value: maximum area in m2
# 3mm and 4mm apply to Monolithic Toughened only

SAFETY_GLASS_AREA_CAT1 = {
    3:  1.0,
    4:  2.0,
    5:  3.0,
    6:  4.0,
    8:  6.0,
    10: 8.0,
    12: 10.0,
}

SAFETY_GLASS_AREA_CAT2 = {
    5:  2.2,
    6:  3.0,
    8:  5.0,
    10: 7.0,
    12: 9.0,
}

# Maps each eligible glass type to its safety glass area category
SAFETY_GLASS_CATEGORY = {
    ('Monolithic', 'Toughened'):          'cat1',
    ('Laminated',  'Toughened'):          'cat1',
    ('Laminated',  'Annealed'):           'cat2',
    ('Laminated',  'Heat-strengthened'):  'cat2',
}

# Glass types ineligible for safety glass
SAFETY_GLASS_INELIGIBLE = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Heat-strengthened'),
]


# ---------------------------------------------------------------------------
# BUSHFIRE (BAL) FILTER - AS 3959
# ---------------------------------------------------------------------------
# Each BAL level + element type combination defines:
#   'min_thickness': minimum nominal thickness required, or None if no minimum
#   'eligible_types': None means no glass type restriction, otherwise a list
#                      of (glass_type, glass_subtype) tuples that are allowed
#   'conditional_note': warning text shown to the user, or None if not applicable

MONOLITHIC_TOUGHENED_ONLY = [('Monolithic', 'Toughened')]

BAL_RULES = {
    ('12.5', 'Window'): {
        'min_thickness': None,
        'eligible_types': None,
        'conditional_note': 'Glass within 400mm of ground, or another '
                             'structure within 18 degrees of horizontal, '
                             'must be safety glass, minimum 4mm.'
    },
    ('12.5', 'Door'): {
        'min_thickness': 4,
        'eligible_types': SAFETY_GLASS_CATEGORY,  # placeholder, replaced below
        'conditional_note': None
    },
    ('19', 'Window'): {
        'min_thickness': None,
        'eligible_types': None,
        'conditional_note': 'Glass within 400mm of ground, or another '
                             'structure within 18 degrees of horizontal, '
                             'must be Monolithic Toughened, minimum 5mm.'
    },
    ('19', 'Door'): {
        'min_thickness': 5,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
    ('29', 'Window'): {
        'min_thickness': 5,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
    ('29', 'Door'): {
        'min_thickness': 6,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
}

# BAL-12.5 Door uses the same eligible glass types as Safety Glass
# (Monolithic Toughened, Laminated Annealed, Laminated Heat-strengthened,
# Laminated Toughened) - fix the placeholder above now that
# SAFETY_GLASS_CATEGORY exists
BAL_RULES[('12.5', 'Door')]['eligible_types'] = list(SAFETY_GLASS_CATEGORY.keys())


def get_bal_rule(bal_level, element_type):
    """
    Returns the BAL rule dict for a given BAL level ('12.5', '19', '29')
    and element type ('Window' or 'Door'), or None if not found.
    """
    return BAL_RULES.get((bal_level, element_type))


def check_bal_eligibility(bal_level, element_type, glass_type, glass_subtype):
    """
    Returns True if the given glass type is eligible under this BAL rule,
    False if it is restricted out.
    """
    rule = get_bal_rule(bal_level, element_type)
    if rule is None or rule['eligible_types'] is None:
        return True
    return (glass_type, glass_subtype) in rule['eligible_types']


def get_bal_min_thickness(bal_level, element_type):
    """
    Returns the minimum nominal thickness required under this BAL rule,
    or None if there is no minimum.
    """
    rule = get_bal_rule(bal_level, element_type)
    if rule is None:
        return None
    return rule['min_thickness']


def get_safety_glass_max_area(glass_type, glass_subtype, nominal_thickness_mm):
    """
    Returns the maximum permitted area in m2 for a given glass type
    and nominal thickness under AS 1288 Table 5.1.

    Returns:
        float  : maximum area in m2 if found in table
        'EXTRAPOLATE' : if thickness exceeds 12mm
        None   : if glass type is not eligible for safety glass
    """
    category = SAFETY_GLASS_CATEGORY.get((glass_type, glass_subtype))
    if category is None:
        return None

    if nominal_thickness_mm > 12:
        return 'EXTRAPOLATE'

    if category == 'cat1':
        # 3mm and 4mm only apply to Monolithic Toughened, not Toughened Laminated
        if glass_type == 'Laminated' and nominal_thickness_mm in (3, 4):
            return None
        return SAFETY_GLASS_AREA_CAT1.get(nominal_thickness_mm)
    else:
        return SAFETY_GLASS_AREA_CAT2.get(nominal_thickness_mm)


# ---------------------------------------------------------------------------
# NOMINAL THICKNESS LOOKUP (AS 1288 Table 4.1)
# ---------------------------------------------------------------------------

def get_nominal_thickness(df_nominal, glass_type, actual_thickness_mm):
    """
    Converts an actual measured glass thickness to a nominal thickness
    using AS 1288 Table 4.1.

    Uses the broad glass type only: 'Monolithic' or 'Laminated'.
    Laminated Heat-strengthened and Laminated Toughened use 'Laminated' row.

    Returns nominal thickness as int, or None if too thin to classify.
    """
    # Map new laminated subtypes to broad type for Table 4.1 lookup
    lookup_type = 'Laminated' if glass_type == 'Laminated' else 'Monolithic'

    type_rows = df_nominal[df_nominal['Glass Type'] == lookup_type].copy()
    type_rows = type_rows.sort_values('Nominal Thickness (mm)', ascending=True)

    nominal_thickness = None
    for _, row in type_rows.iterrows():
        if actual_thickness_mm >= row['Minimum Thickness (mm)']:
            nominal_thickness = int(row['Nominal Thickness (mm)'])

    return nominal_thickness


# ---------------------------------------------------------------------------
# ASPECT RATIO LOGIC
# ---------------------------------------------------------------------------

TABLE_AR_VALUES = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 5.0]


def calculate_ar(height_mm, width_mm):
    """
    Calculates the aspect ratio of the panel.
    AR = longest dimension / shortest dimension. Always >= 1.0
    """
    return max(height_mm, width_mm) / min(height_mm, width_mm)


def calculate_span(height_mm, width_mm, support_condition, span_dimension):
    """
    Determines the structural span of the panel in mm.
    4-edge: span = shortest dimension.
    2-edge: span = dimension between supported edges (user confirmed).
    """
    if support_condition == '4-edge':
        return min(height_mm, width_mm)
    else:
        return height_mm if span_dimension == 'height' else width_mm


def get_ar_interpolation_bounds(actual_ar):
    """
    Returns the AR interpolation parameters needed to look up and blend
    k-values per AS 1288 Clause 4.4.3 (linear interpolation permitted
    between table AR values).

    If AR >= 5.0, the AR=5 row applies directly, no interpolation (AS 1288
    caps at AR=5, there is no value above it to interpolate toward).
    If AR exactly matches a table value, that row is used directly with
    no interpolation needed.
    Otherwise, returns the two bracketing table AR values and the
    fraction (0 to 1) of how far actual_ar sits between them, for use
    in blending k1-k4 from both rows.

    Returns a dict:
        {'exact': True, 'ar': value}  -- use this single AR value directly
        {'exact': False, 'ar_low': x, 'ar_high': y, 'fraction': f}
                                       -- interpolate between these two rows
    """
    if actual_ar >= 5.0:
        return {'exact': True, 'ar': 5.0}

    for table_ar in TABLE_AR_VALUES:
        if abs(actual_ar - table_ar) < 1e-9:
            return {'exact': True, 'ar': table_ar}

    for i in range(len(TABLE_AR_VALUES) - 1):
        ar_low = TABLE_AR_VALUES[i]
        ar_high = TABLE_AR_VALUES[i + 1]
        if ar_low < actual_ar < ar_high:
            fraction = (actual_ar - ar_low) / (ar_high - ar_low)
            return {
                'exact': False,
                'ar_low': ar_low,
                'ar_high': ar_high,
                'fraction': fraction
            }

    # actual_ar is below the smallest table value (below 1.0) - should not
    # occur since AR is always >= 1.0 by definition, but fall back safely
    return {'exact': True, 'ar': TABLE_AR_VALUES[0]}


def interpolate_k_values(k_low, k_high, fraction):
    """
    Linearly blends two sets of k1-k4 values based on the interpolation
    fraction, per AS 1288 Clause 4.4.3.

    k_low and k_high are dicts with keys 'k1', 'k2', 'k3', 'k4'.
    Returns a blended dict in the same shape.
    """
    return {
        key: k_low[key] + fraction * (k_high[key] - k_low[key])
        for key in ('k1', 'k2', 'k3', 'k4')
    }


# ---------------------------------------------------------------------------
# IGU LOAD SHARING CONSTANTS (Mode 1 - equal thickness assumption)
# ---------------------------------------------------------------------------

# For Mode 1, all panes assumed equal thickness so k_pane is a fixed constant
# Single: k_pane = 1.0
# Double: k_pane = 1.25 / 2 = 0.625
# Triple: k_pane = 1.25 / 3 = 0.4167
KPANE_SINGLE = 1.0
KPANE_DOUBLE = 1.25 / 2
KPANE_TRIPLE = 1.25 / 3


def get_kpane_for_config(glazing_config):
    """
    Returns the k_pane constant for a given glazing configuration.
    glazing_config: 'single', 'double', or 'triple'
    """
    if glazing_config == 'double':
        return KPANE_DOUBLE
    elif glazing_config == 'triple':
        return KPANE_TRIPLE
    else:
        return KPANE_SINGLE


def calculate_kpane(t_pane, all_thicknesses):
    """
    Calculates load sharing factor for a single pane in an IGU (Mode 2).
    k_pane = 1.25 x t_pane^3 / sum(ti^3), capped at 1.0.
    Uses actual measured thicknesses.
    """
    numerator = 1.25 * (t_pane ** 3)
    denominator = sum(t ** 3 for t in all_thicknesses)
    return min(numerator / denominator, 1.0)


# ---------------------------------------------------------------------------
# C1 FACTORS FOR LAMINATED GLASS VARIANTS (AS 1288 Clause 4.4.5)
# ---------------------------------------------------------------------------

# c1 divides wind pressures before entering the formula for laminated variants
# Monolithic glass is unaffected (c1 = 1.0 implicitly)
C1_FACTORS = {
    ('Laminated', 'Annealed'):          1.0,
    ('Laminated', 'Heat-strengthened'): 1.6,
    ('Laminated', 'Toughened'):         2.5,
}


def get_c1_factor(glass_type, glass_subtype):
    """
    Returns the c1 factor for a given glass type combination.
    Returns 1.0 for Monolithic glass (no modification).
    """
    return C1_FACTORS.get((glass_type, glass_subtype), 1.0)


# ---------------------------------------------------------------------------
# TABLE LOOKUP
# ---------------------------------------------------------------------------

def _fetch_k_row(df, wind_load_type, glass_type, lookup_subtype,
                 thickness_str, support_condition, ar_str):
    """
    Internal helper - fetches a single matching row's k1-k4 from the table.
    Returns a dict, or None if no match found.
    """
    mask = (
        (df['Wind Load Type'] == wind_load_type) &
        (df['Glass Type'] == glass_type) &
        (df['Glass sub-type 1'] == lookup_subtype) &
        (df['Nominal Thickness (mm)'] == thickness_str) &
        (df['Support Condition'] == support_condition) &
        (df['AR'] == ar_str)
    )
    matching_rows = df[mask]
    if len(matching_rows) == 0:
        return None
    row = matching_rows.iloc[0]
    return {
        'k1': row['k1'], 'k2': row['k2'],
        'k3': row['k3'], 'k4': row['k4']
    }


def get_uls_k_values(df, glass_type, glass_subtype, thickness_mm,
                     support_condition, ar_bounds):
    """
    Looks up ULS k values for a given combination, applying linear
    interpolation between bracketing AR table rows per AS 1288
    Clause 4.4.3 where the actual AR does not land exactly on a table value.

    For Laminated Heat-strengthened and Toughened, uses Laminated Annealed
    rows since those glass types share the same table (Clause 4.4.5).

    ar_bounds is the dict returned by get_ar_interpolation_bounds, or None
    for 2-edge support (AR = Independent, no interpolation applicable).

    Returns a dict with k1-k4, or None if no matching row(s) found.
    """
    lookup_subtype = 'Annealed' if glass_type == 'Laminated' else glass_subtype
    thickness_str = str(thickness_mm)

    if support_condition == '2-edge':
        return _fetch_k_row(
            df, 'ULS', glass_type, lookup_subtype,
            thickness_str, support_condition, 'Independent'
        )

    if ar_bounds['exact']:
        ar_str = str(ar_bounds['ar']).rstrip('0').rstrip('.')
        if ar_str == '':
            ar_str = '0'
        return _fetch_k_row(
            df, 'ULS', glass_type, lookup_subtype,
            thickness_str, support_condition, ar_str
        )

    ar_low_str = str(ar_bounds['ar_low']).rstrip('0').rstrip('.')
    ar_high_str = str(ar_bounds['ar_high']).rstrip('0').rstrip('.')

    k_low = _fetch_k_row(
        df, 'ULS', glass_type, lookup_subtype,
        thickness_str, support_condition, ar_low_str
    )
    k_high = _fetch_k_row(
        df, 'ULS', glass_type, lookup_subtype,
        thickness_str, support_condition, ar_high_str
    )

    if k_low is None or k_high is None:
        return None

    return interpolate_k_values(k_low, k_high, ar_bounds['fraction'])


def get_sls_k_values(df, support_condition, ar_bounds):
    """
    Looks up SLS k values from the table, applying linear interpolation
    between bracketing AR table rows per AS 1288 Clause 4.4.3 where the
    actual AR does not land exactly on a table value.

    SLS rows apply to all glass types (Glass Type = All).

    ar_bounds is the dict returned by get_ar_interpolation_bounds, or None
    for 2-edge support (AR = Independent, no interpolation applicable).

    Returns a dict with k1-k4, or None if no matching row(s) found.
    """
    def fetch_sls_row(ar_str):
        mask = (
            (df['Wind Load Type'] == 'SLS') &
            (df['Support Condition'] == support_condition) &
            (df['AR'] == ar_str)
        )
        matching_rows = df[mask]
        if len(matching_rows) == 0:
            return None
        row = matching_rows.iloc[0]
        return {
            'k1': row['k1'], 'k2': row['k2'],
            'k3': row['k3'], 'k4': row['k4']
        }

    if support_condition == '2-edge':
        return fetch_sls_row('Independent')

    if ar_bounds['exact']:
        ar_str = str(ar_bounds['ar']).rstrip('0').rstrip('.')
        if ar_str == '':
            ar_str = '0'
        return fetch_sls_row(ar_str)

    ar_low_str = str(ar_bounds['ar_low']).rstrip('0').rstrip('.')
    ar_high_str = str(ar_bounds['ar_high']).rstrip('0').rstrip('.')

    k_low = fetch_sls_row(ar_low_str)
    k_high = fetch_sls_row(ar_high_str)

    if k_low is None or k_high is None:
        return None

    return interpolate_k_values(k_low, k_high, ar_bounds['fraction'])


# ---------------------------------------------------------------------------
# CALCULATION FORMULAS
# ---------------------------------------------------------------------------

def calculate_uls_capacity(k1, k2, k3, k4, wind_pressure_uls_kpa):
    """
    B = k1 x (Pu + k2)^k3 + k4
    wind_pressure_uls_kpa is already in kPa. Returns B in mm.

    Raises a ValueError with the exact inputs if the calculation produces
    an invalid (NaN) result - this happens when (Pu + k2) is negative and
    k3 is a non-integer exponent, mathematically undefined in real numbers.
    This typically occurs at unusually low wind pressures outside the
    intended scope of the table.
    """
    base = wind_pressure_uls_kpa + k2
    result = k1 * base ** k3 + k4

    is_nan = isinstance(result, float) and result != result
    is_inf = isinstance(result, float) and (result == float('inf') or result == float('-inf'))

    if isinstance(result, complex) or is_nan or is_inf:
        reason = "is negative" if base < 0 else "is zero or extremely close to zero"
        raise ValueError(
            f"ULS calculation produced an invalid result. "
            f"wind_pressure_uls={wind_pressure_uls_kpa}kPa, "
            f"k1={k1}, k2={k2}, k3={k3}, k4={k4}, "
            f"base (Pu+k2)={base:.6f} {reason}, which is undefined or "
            f"infinite when raised to a non-integer power (k3={k3}). "
            f"This wind pressure may be outside the scope of AS 1288 for "
            f"this glass type and thickness."
        )

    return result


def calculate_sls_capacity(k1, k2, k3, k4, thickness_mm, wind_pressure_sls_kpa):
    """
    B/t = k1 x (Ps + k2)^k3 + k4
    Therefore: B = t x (k1 x (Ps + k2)^k3 + k4)
    wind_pressure_sls_kpa is already in kPa. Returns B in mm.

    Raises a ValueError with the exact inputs if the calculation produces
    an invalid (NaN) result - this happens when (Ps + k2) is negative and
    k3 is a non-integer exponent, mathematically undefined in real numbers.
    This typically occurs at unusually low wind pressures outside the
    intended scope of the table.
    """
    base = wind_pressure_sls_kpa + k2
    inner = k1 * base ** k3 + k4
    result = thickness_mm * inner

    is_nan = isinstance(result, float) and result != result
    is_inf = isinstance(result, float) and (result == float('inf') or result == float('-inf'))

    if isinstance(result, complex) or is_nan or is_inf:
        reason = "is negative" if base < 0 else "is zero or extremely close to zero"
        raise ValueError(
            f"SLS calculation produced an invalid result. "
            f"wind_pressure_sls={wind_pressure_sls_kpa}kPa, "
            f"thickness_mm={thickness_mm}, "
            f"k1={k1}, k2={k2}, k3={k3}, k4={k4}, "
            f"base (Ps+k2)={base:.6f} {reason}, which is undefined or "
            f"infinite when raised to a non-integer power (k3={k3}). "
            f"This wind pressure may be outside the scope of AS 1288 for "
            f"this glass type and thickness."
        )

    return result


# ---------------------------------------------------------------------------
# GLASS TYPE DEFINITIONS
# ---------------------------------------------------------------------------

GLASS_TYPE_THICKNESSES = {
    ('Monolithic', 'Annealed'):           [4, 5, 6, 8, 10, 12, 15, 19, 25],
    ('Monolithic', 'Toughened'):          [4, 5, 6, 8, 10, 12, 15, 19, 25],
    ('Monolithic', 'Heat-strengthened'):  [3, 4, 5, 6, 8, 10, 12],
    ('Laminated',  'Annealed'):           [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Heat-strengthened'):  [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Toughened'):          [5, 6, 8, 10, 12, 16, 20, 24],
}


# ---------------------------------------------------------------------------
# RESULT DICTIONARY CONSTRUCTORS
# ---------------------------------------------------------------------------
# Every return path in check_glass_type (Mode 1) and check_pane_compliance
# (Mode 2) MUST use these constructors instead of building dicts by hand.
# This guarantees every result has the exact same set of keys, regardless
# of which exit path produced it. Missing keys caused multiple frontend
# "could not connect" errors in past sessions — this makes that bug class
# structurally impossible.
#
# During the V2 restructure, these move to engine/shared/results.py.

def make_mode1_result(status, glass_type=None, glass_subtype=None,
                      message=None, minimum_thickness_mm=None,
                      uls_minimum_thickness_mm=None,
                      sls_minimum_thickness_mm=None,
                      sg_minimum_thickness_mm=None,
                      bal_minimum_thickness_mm=None,
                      bal_level=None, bal_element_type=None,
                      glazing_config=None, k_pane=None,
                      annealed_area_flag=None, sg_flag=None,
                      panel_area_m2=None,
                      safety_glass_required=False,
                      bushfire_required=False,
                      uls_trace=None, sls_trace=None, sg_trace=None):
    """
    Builds a Mode 1 result dictionary with a guaranteed, consistent set
    of keys. Every return path in check_glass_type() must call this
    instead of building its own dict.

    Parameters with sensible defaults (None, False, or []) are safe to
    omit — the key will still exist in the returned dictionary.
    """
    return {
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'status': status,
        'message': message,
        'minimum_thickness_mm': minimum_thickness_mm,
        'uls_minimum_thickness_mm': uls_minimum_thickness_mm,
        'sls_minimum_thickness_mm': sls_minimum_thickness_mm,
        'sg_minimum_thickness_mm': sg_minimum_thickness_mm,
        'bal_minimum_thickness_mm': bal_minimum_thickness_mm,
        'bal_level': bal_level,
        'bal_element_type': bal_element_type,
        'glazing_config': glazing_config,
        'k_pane': k_pane,
        'annealed_area_flag': annealed_area_flag,
        'sg_flag': sg_flag,
        'panel_area_m2': panel_area_m2,
        'safety_glass_required': safety_glass_required,
        'bushfire_required': bushfire_required,
        'uls_trace': uls_trace if uls_trace is not None else [],
        'sls_trace': sls_trace if sls_trace is not None else [],
        'sg_trace': sg_trace if sg_trace is not None else [],
    }


def make_mode2_result(status, pane_label=None,
                      glass_type=None, glass_subtype=None,
                      actual_thickness_mm=None, nominal_thickness_mm=None,
                      k_pane=None, message=None,
                      effective_uls_pa=None, effective_sls_pa=None,
                      B_uls_mm=None, B_sls_mm=None, span_mm=None,
                      uls_status=None, sls_status=None, sg_status=None,
                      sg_max_area_m2=None, sg_flag=None,
                      panel_area_m2=None, annealed_area_flag=None,
                      next_compliant_thickness_mm=None,
                      next_compliant_trace=None,
                      safety_glass_required=False,
                      bal_status=None, bal_min_thickness_mm=None,
                      bal_level=None, bal_element_type=None,
                      bushfire_required=False,
                      uls_trace=None, sls_trace=None, sg_trace=None):
    """
    Builds a Mode 2 result dictionary with a guaranteed, consistent set
    of keys. Every return path in check_pane_compliance() must call this
    instead of building its own dict.

    Parameters with sensible defaults (None, False, or []) are safe to
    omit — the key will still exist in the returned dictionary.
    """
    return {
        'pane_label': pane_label,
        'glass_type': glass_type,
        'glass_subtype': glass_subtype,
        'actual_thickness_mm': actual_thickness_mm,
        'nominal_thickness_mm': nominal_thickness_mm,
        'k_pane': k_pane,
        'effective_uls_pa': effective_uls_pa,
        'effective_sls_pa': effective_sls_pa,
        'B_uls_mm': B_uls_mm,
        'B_sls_mm': B_sls_mm,
        'span_mm': span_mm,
        'uls_status': uls_status,
        'sls_status': sls_status,
        'sg_status': sg_status,
        'sg_max_area_m2': sg_max_area_m2,
        'sg_flag': sg_flag,
        'panel_area_m2': panel_area_m2,
        'annealed_area_flag': annealed_area_flag,
        'next_compliant_thickness_mm': next_compliant_thickness_mm,
        'next_compliant_trace': next_compliant_trace if next_compliant_trace is not None else [],
        'safety_glass_required': safety_glass_required,
        'bal_status': bal_status,
        'bal_min_thickness_mm': bal_min_thickness_mm,
        'bal_level': bal_level,
        'bal_element_type': bal_element_type,
        'bushfire_required': bushfire_required,
        'status': status,
        'message': message,
        'uls_trace': uls_trace if uls_trace is not None else [],
        'sls_trace': sls_trace if sls_trace is not None else [],
        'sg_trace': sg_trace if sg_trace is not None else [],
    }


# ---------------------------------------------------------------------------
# MODE 1 - MINIMUM THICKNESS FINDER
# ---------------------------------------------------------------------------

def check_glass_type(df, glass_type, glass_subtype, height_mm, width_mm,
                     support_condition, span_dimension,
                     wind_pressure_uls, wind_pressure_sls,
                     glazing_config, safety_glass_required=False,
                     bushfire_required=False, bal_level=None,
                     element_type=None):
    """
    Runs ULS, SLS, and optionally Safety Glass Area Check for one glass type.
    Finds the minimum compliant thickness across all active checks.

    Returns a dict describing the full result for that glass type.
    """

    actual_ar = calculate_ar(height_mm, width_mm)
    span      = calculate_span(height_mm, width_mm, support_condition, span_dimension)
    panel_area = (height_mm * width_mm) / 1_000_000

    # Determine AR interpolation bounds for table lookup
    if support_condition == '4-edge':
        ar_bounds = get_ar_interpolation_bounds(actual_ar)
    else:
        ar_bounds = None

    # Get k_pane for this glazing configuration (equal thickness assumption)
    k_pane = get_kpane_for_config(glazing_config)

    # Get c1 factor for Laminated variants - divides wind pressures
    c1 = get_c1_factor(glass_type, glass_subtype)

    # Apply k_pane and c1 to get effective pressures
    effective_uls = (k_pane * wind_pressure_uls) / c1
    effective_sls = (k_pane * wind_pressure_sls) / c1

    thickness_list = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype))
    if thickness_list is None:
        return make_mode1_result(
            status='ERROR',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message=f'Unknown glass type: {glass_type} {glass_subtype}',
            glazing_config=glazing_config, k_pane=k_pane,
        )

    # --- Safety glass eligibility check ---
    if safety_glass_required and support_condition == '4-edge':
        if (glass_type, glass_subtype) in SAFETY_GLASS_INELIGIBLE:
            return make_mode1_result(
                status='SG_INELIGIBLE',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass and cannot be used when safety glass '
                        f'is required.',
                glazing_config=glazing_config, k_pane=k_pane,
                safety_glass_required=safety_glass_required,
            )

    # --- Bushfire (BAL) eligibility check ---
    if bushfire_required and bal_level and element_type:
        if not check_bal_eligibility(bal_level, element_type, glass_type, glass_subtype):
            return make_mode1_result(
                status='BAL_INELIGIBLE',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message=f'{glass_type} {glass_subtype} is not permitted '
                        f'under BAL-{bal_level} for a {element_type.lower()}.',
                glazing_config=glazing_config, k_pane=k_pane,
                bushfire_required=bushfire_required,
                bal_level=bal_level, bal_element_type=element_type,
            )

    # --- STEP 1: ULS CHECK ---
    uls_minimum_thickness = None
    uls_trace = []
    sls_k_values = get_sls_k_values(df, support_condition, ar_bounds)

    for thickness in thickness_list:
        k_values = get_uls_k_values(
            df, glass_type, glass_subtype,
            thickness, support_condition, ar_bounds
        )
        if k_values is None:
            continue

        B_uls = calculate_uls_capacity(
            k_values['k1'], k_values['k2'],
            k_values['k3'], k_values['k4'],
            effective_uls
        )

        result = 'PASS' if span <= B_uls else 'FAIL'
        uls_trace.append({
            'check': 'ULS',
            'thickness': thickness,
            'k1': k_values['k1'], 'k2': k_values['k2'],
            'k3': k_values['k3'], 'k4': k_values['k4'],
            'pressure_kpa': round(effective_uls, 4),
            'B': round(B_uls, 2),
            'span': span,
            'result': result
        })

        if span <= B_uls:
            uls_minimum_thickness = thickness
            break

    if uls_minimum_thickness is None:
        return make_mode1_result(
            status='NO_COMPLIANT_THICKNESS',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='No compliant thickness available under the applied '
                    'ULS wind pressure.',
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # --- STEP 2: SLS CHECK ---
    if sls_k_values is None:
        return make_mode1_result(
            status='ERROR',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='Could not find SLS k values in table.',
            uls_minimum_thickness_mm=uls_minimum_thickness,
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # SLS now searches its OWN full thickness range independently of ULS,
    # rather than starting from the ULS minimum. This reports SLS's true
    # minimum thickness on its own terms. The governing thickness (highest
    # of all checks) is still calculated correctly further below.
    sls_minimum_thickness = None
    sls_trace = []

    for thickness in thickness_list:
        B_sls = calculate_sls_capacity(
            sls_k_values['k1'], sls_k_values['k2'],
            sls_k_values['k3'], sls_k_values['k4'],
            thickness,
            effective_sls
        )

        result = 'PASS' if span <= B_sls else 'FAIL'
        sls_trace.append({
            'check': 'SLS',
            'thickness': thickness,
            'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
            'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
            'pressure_kpa': round(effective_sls, 4),
            'B': round(B_sls, 2),
            'span': span,
            'result': result
        })

        if span <= B_sls:
            sls_minimum_thickness = thickness
            break

    if sls_minimum_thickness is None:
        return make_mode1_result(
            status='NO_COMPLIANT_THICKNESS',
            glass_type=glass_type, glass_subtype=glass_subtype,
            message='No compliant thickness available under the applied '
                    'SLS wind pressure.',
            uls_minimum_thickness_mm=uls_minimum_thickness,
            glazing_config=glazing_config, k_pane=k_pane,
            uls_trace=uls_trace, sls_trace=sls_trace,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
            bushfire_required=bushfire_required,
        )

    # --- STEP 3: SAFETY GLASS AREA CHECK ---
    sg_minimum_thickness = None
    sg_flag = None

    if safety_glass_required and support_condition == '4-edge':
        # Safety Glass now searches its OWN full thickness range
        # independently, reporting its true minimum on its own terms,
        # rather than starting from the wind load governing thickness.
        sg_trace = []

        for thickness in thickness_list:
            max_area = get_safety_glass_max_area(
                glass_type, glass_subtype, thickness
            )

            if max_area == 'EXTRAPOLATE':
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': 'EXTRAPOLATE',
                    'actual_area': round(panel_area, 4),
                    'result': 'EXTRAPOLATE'
                })
                sg_flag = 'EXTRAPOLATE'
                sg_minimum_thickness = thickness
                break
            elif max_area is None:
                continue
            elif panel_area <= max_area:
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': max_area,
                    'actual_area': round(panel_area, 4),
                    'result': 'PASS'
                })
                sg_minimum_thickness = thickness
                break
            else:
                sg_trace.append({
                    'check': 'SG',
                    'thickness': thickness,
                    'max_area': max_area,
                    'actual_area': round(panel_area, 4),
                    'result': 'FAIL'
                })

        if sg_minimum_thickness is None and sg_flag != 'EXTRAPOLATE':
            return make_mode1_result(
                status='NO_COMPLIANT_THICKNESS',
                glass_type=glass_type, glass_subtype=glass_subtype,
                message='No compliant thickness available under the Safety '
                        'Glass Area Check (AS 1288 Table 5.1).',
                uls_minimum_thickness_mm=uls_minimum_thickness,
                sls_minimum_thickness_mm=sls_minimum_thickness,
                glazing_config=glazing_config, k_pane=k_pane,
                uls_trace=uls_trace, sls_trace=sls_trace, sg_trace=sg_trace,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
            )

    # --- Bushfire (BAL) minimum thickness check ---
    # This governs if higher than the wind load / safety glass result,
    # following the same "highest of all active checks" pattern.
    bal_minimum_thickness = None
    if bushfire_required and bal_level and element_type:
        bal_minimum_thickness = get_bal_min_thickness(bal_level, element_type)

    candidates_with_bal = [uls_minimum_thickness, sls_minimum_thickness]
    if sg_minimum_thickness is not None:
        candidates_with_bal.append(sg_minimum_thickness)
    if bal_minimum_thickness is not None:
        candidates_with_bal.append(bal_minimum_thickness)
    final_thickness = max(candidates_with_bal)

    return make_mode1_result(
        status='PASS',
        glass_type=glass_type, glass_subtype=glass_subtype,
        message='PASS',
        minimum_thickness_mm=final_thickness,
        uls_minimum_thickness_mm=uls_minimum_thickness,
        sls_minimum_thickness_mm=sls_minimum_thickness,
        sg_minimum_thickness_mm=sg_minimum_thickness,
        bal_minimum_thickness_mm=bal_minimum_thickness,
        bal_level=bal_level if bushfire_required else None,
        bal_element_type=element_type if bushfire_required else None,
        glazing_config=glazing_config,
        k_pane=k_pane,
        sg_flag=sg_flag,
        panel_area_m2=round(panel_area, 4),
        safety_glass_required=safety_glass_required,
        bushfire_required=bushfire_required,
        uls_trace=uls_trace,
        sls_trace=sls_trace,
        sg_trace=sg_trace if safety_glass_required and support_condition == '4-edge' else [],
    )


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


# ---------------------------------------------------------------------------
# MODE 2 - COMPLIANCE CHECKER
# ---------------------------------------------------------------------------

def check_pane_compliance(df, df_nominal, glass_type, glass_subtype,
                          actual_thickness_mm, all_actual_thicknesses,
                          span, height_mm, width_mm,
                          ar_bounds, support_condition,
                          wind_pressure_uls, wind_pressure_sls,
                          pane_label, glazing_config,
                          safety_glass_required=False,
                          bushfire_required=False, bal_level=None,
                          element_type=None):
    """
    Checks whether a single pane of known thickness passes ULS, SLS,
    and optionally Safety Glass Area Check.

    Returns a dict describing the full compliance result for this pane.
    """

    panel_area = (height_mm * width_mm) / 1_000_000

    # --- Nominal thickness lookup ---
    nominal_thickness = get_nominal_thickness(
        df_nominal, glass_type, actual_thickness_mm
    )

    if nominal_thickness is None:
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            message=f'Actual thickness {actual_thickness_mm}mm is too thin '
                    f'to classify under AS 1288 Table 4.1.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # Check that this nominal thickness is actually offered for this glass type
    available_thicknesses = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype), [])
    if available_thicknesses and nominal_thickness < min(available_thicknesses):
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            message=f'No DTS solution for glass selection of '
                    f'{glass_type} {glass_subtype} of thickness '
                    f'{nominal_thickness}mm available.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # Monolithic Annealed minimum nominal thickness is 4mm
    if glass_type == 'Monolithic' and glass_subtype == 'Annealed' and \
       nominal_thickness == 3:
        return make_mode2_result(
            status='INVALID',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            message='Minimum thickness allowed by tool: 4mm. '
                    'Monolithic Annealed glass below 4mm nominal '
                    'is not permitted.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # --- Safety glass eligibility ---
    if safety_glass_required and support_condition == '4-edge':
        if (glass_type, glass_subtype) in SAFETY_GLASS_INELIGIBLE:
            return make_mode2_result(
                status='SG_INELIGIBLE',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=f'{glass_type} {glass_subtype} is not classified as '
                        f'safety glass and cannot be used when safety glass '
                        f'is required.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
            )

    # --- Bushfire (BAL) eligibility ---
    # Only applies to the Outer pane (or the only pane, if Single glazed) -
    # Inner and Middle panes are not subject to bushfire requirements
    is_bushfire_pane = pane_label in ('Outer', 'Single')

    if bushfire_required and is_bushfire_pane and bal_level and element_type:
        if not check_bal_eligibility(bal_level, element_type, glass_type, glass_subtype):
            return make_mode2_result(
                status='BAL_INELIGIBLE',
                pane_label=pane_label,
                glass_type=glass_type, glass_subtype=glass_subtype,
                actual_thickness_mm=actual_thickness_mm,
                nominal_thickness_mm=nominal_thickness,
                message=f'{glass_type} {glass_subtype} is not permitted '
                        f'under BAL-{bal_level} for a {element_type.lower()}.',
                span_mm=span,
                panel_area_m2=round(panel_area, 4),
                safety_glass_required=safety_glass_required,
                bushfire_required=bushfire_required,
                bal_level=bal_level, bal_element_type=element_type,
            )

    # --- k_pane calculation ---
    k_pane = calculate_kpane(actual_thickness_mm, all_actual_thicknesses)

    # --- c1 factor ---
    c1 = get_c1_factor(glass_type, glass_subtype)

    # --- Effective pressures ---
    effective_uls = (k_pane * wind_pressure_uls) / c1
    effective_sls = (k_pane * wind_pressure_sls) / c1

    # --- ULS k values lookup ---
    k_values = get_uls_k_values(
        df, glass_type, glass_subtype,
        nominal_thickness, support_condition, ar_bounds
    )

    if k_values is None:
        return make_mode2_result(
            status='ERROR',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            k_pane=k_pane,
            message=f'No wind load data available for '
                    f'{glass_type} {glass_subtype} at {nominal_thickness}mm '
                    f'nominal thickness. This thickness is not offered for '
                    f'this glass type.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    sls_k_values = get_sls_k_values(df, support_condition, ar_bounds)
    if sls_k_values is None:
        return make_mode2_result(
            status='ERROR',
            pane_label=pane_label,
            glass_type=glass_type, glass_subtype=glass_subtype,
            actual_thickness_mm=actual_thickness_mm,
            nominal_thickness_mm=nominal_thickness,
            k_pane=k_pane,
            message='Could not find SLS k values in table.',
            span_mm=span,
            panel_area_m2=round(panel_area, 4),
            safety_glass_required=safety_glass_required,
        )

    # --- ULS and SLS capacities ---
    B_uls = calculate_uls_capacity(
        k_values['k1'], k_values['k2'],
        k_values['k3'], k_values['k4'],
        effective_uls
    )

    uls_trace = [{
        'check': 'ULS',
        'thickness': nominal_thickness,
        'k1': k_values['k1'], 'k2': k_values['k2'],
        'k3': k_values['k3'], 'k4': k_values['k4'],
        'pressure_kpa': round(effective_uls, 4),
        'B': round(B_uls, 2),
        'span': span,
        'result': 'PASS' if span <= B_uls else 'FAIL'
    }]

    B_sls = calculate_sls_capacity(
        sls_k_values['k1'], sls_k_values['k2'],
        sls_k_values['k3'], sls_k_values['k4'],
        nominal_thickness, effective_sls
    )

    sls_trace = [{
        'check': 'SLS',
        'thickness': nominal_thickness,
        'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
        'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
        'pressure_kpa': round(effective_sls, 4),
        'B': round(B_sls, 2),
        'span': span,
        'result': 'PASS' if span <= B_sls else 'FAIL'
    }]

    uls_status = 'PASS' if span <= B_uls else 'FAIL'
    sls_status = 'PASS' if span <= B_sls else 'FAIL'

    # --- Safety Glass Area Check ---
    sg_status = None
    sg_max_area = None
    sg_flag = None
    sg_trace = []

    if safety_glass_required and support_condition == '4-edge':
        max_area = get_safety_glass_max_area(
            glass_type, glass_subtype, nominal_thickness
        )
        if max_area == 'EXTRAPOLATE':
            sg_status = 'EXTRAPOLATE'
            sg_flag = 'EXTRAPOLATE'
        elif max_area is None:
            sg_status = 'N/A'
        elif panel_area <= max_area:
            sg_status = 'PASS'
            sg_max_area = max_area
        else:
            sg_status = 'FAIL'
            sg_max_area = max_area

    # --- Find next compliant thickness if any check fails ---
    thickness_list = GLASS_TYPE_THICKNESSES.get((glass_type, glass_subtype), [])
    next_compliant       = None
    next_compliant_trace = []

    any_fail = (
        uls_status == 'FAIL' or
        sls_status == 'FAIL' or
        sg_status == 'FAIL'
    )

    if any_fail:
        uls_confirmed_passing = False

        for candidate in thickness_list:
            if candidate <= nominal_thickness:
                continue

            candidate_trace = {'thickness': candidate, 'checks': []}
            candidate_pass  = True

            # ULS check
            ck = get_uls_k_values(
                df, glass_type, glass_subtype,
                candidate, support_condition, ar_bounds
            )
            if ck is None:
                continue

            if uls_confirmed_passing:
                # A thinner candidate already passed ULS — any thicker
                # glass is guaranteed to also pass, since allowable span
                # only increases with thickness. Skip the recalculation
                # and go straight to SLS.
                uls_result = 'PASS'
                candidate_trace['checks'].append({
                    'check':     'ULS',
                    'thickness': candidate,
                    'result':    'PASS',
                    'note':      'Confirmed passing at a thinner thickness; '
                                 'not re-checked (thicker glass always passes ULS).'
                })
            else:
                cB_uls     = calculate_uls_capacity(
                    ck['k1'], ck['k2'], ck['k3'], ck['k4'], effective_uls
                )
                uls_result = 'PASS' if span <= cB_uls else 'FAIL'
                candidate_trace['checks'].append({
                    'check':        'ULS',
                    'thickness':    candidate,
                    'k1': ck['k1'], 'k2': ck['k2'],
                    'k3': ck['k3'], 'k4': ck['k4'],
                    'pressure_kpa': round(effective_uls, 4),
                    'B':            round(cB_uls, 2),
                    'span':         span,
                    'result':       uls_result
                })
                if uls_result == 'PASS':
                    uls_confirmed_passing = True

            if uls_result == 'FAIL':
                candidate_trace['overall'] = 'FAIL'
                candidate_trace['fail_reason'] = 'ULS'
                next_compliant_trace.append(candidate_trace)
                continue

            # SLS check
            cB_sls     = calculate_sls_capacity(
                sls_k_values['k1'], sls_k_values['k2'],
                sls_k_values['k3'], sls_k_values['k4'],
                candidate, effective_sls
            )
            sls_result = 'PASS' if span <= cB_sls else 'FAIL'
            candidate_trace['checks'].append({
                'check':        'SLS',
                'thickness':    candidate,
                'k1': sls_k_values['k1'], 'k2': sls_k_values['k2'],
                'k3': sls_k_values['k3'], 'k4': sls_k_values['k4'],
                'pressure_kpa': round(effective_sls, 4),
                'B':            round(cB_sls, 2),
                'span':         span,
                'result':       sls_result
            })
            if sls_result == 'FAIL':
                candidate_trace['overall'] = 'FAIL'
                candidate_trace['fail_reason'] = 'SLS'
                next_compliant_trace.append(candidate_trace)
                continue

            # Safety Glass Area check
            if safety_glass_required and support_condition == '4-edge':
                cmax = get_safety_glass_max_area(
                    glass_type, glass_subtype, candidate
                )
                if cmax == 'EXTRAPOLATE' or cmax is None:
                    candidate_trace['overall'] = 'PASS'
                    candidate_trace['checks'].append({
                        'check':       'SG',
                        'thickness':   candidate,
                        'max_area':    'EXTRAPOLATE',
                        'actual_area': round(panel_area, 4),
                        'result':      'EXTRAPOLATE'
                    })
                    next_compliant_trace.append(candidate_trace)
                    next_compliant = candidate
                    break
                sg_result = 'PASS' if panel_area <= cmax else 'FAIL'
                candidate_trace['checks'].append({
                    'check':       'SG',
                    'thickness':   candidate,
                    'max_area':    cmax,
                    'actual_area': round(panel_area, 4),
                    'result':      sg_result
                })
                if sg_result == 'FAIL':
                    candidate_trace['overall']     = 'FAIL'
                    candidate_trace['fail_reason'] = 'Safety Glass Area Check'
                    next_compliant_trace.append(candidate_trace)
                    continue

            candidate_trace['overall'] = 'PASS'
            next_compliant_trace.append(candidate_trace)
            next_compliant = candidate
            break

    # --- Bushfire (BAL) minimum thickness check ---
    # Only applies to the Outer/Single pane. Governs if higher than the
    # nominal thickness already determined by wind load / safety glass.
    bal_status = None
    bal_min_thickness = None
    if bushfire_required and is_bushfire_pane and bal_level and element_type:
        bal_min_thickness = get_bal_min_thickness(bal_level, element_type)
        if bal_min_thickness is not None:
            bal_status = 'PASS' if nominal_thickness >= bal_min_thickness else 'FAIL'

    # --- Overall status ---
    checks = [uls_status, sls_status]
    if sg_status not in (None, 'N/A', 'EXTRAPOLATE'):
        checks.append(sg_status)
    if bal_status is not None:
        checks.append(bal_status)

    overall_status = 'PASS' if all(c == 'PASS' for c in checks) else 'FAIL'

    return make_mode2_result(
        status=overall_status,
        pane_label=pane_label,
        glass_type=glass_type, glass_subtype=glass_subtype,
        actual_thickness_mm=actual_thickness_mm,
        nominal_thickness_mm=nominal_thickness,
        k_pane=k_pane,
        message=overall_status,
        effective_uls_pa=effective_uls,
        effective_sls_pa=effective_sls,
        B_uls_mm=B_uls, B_sls_mm=B_sls,
        span_mm=span,
        uls_status=uls_status, sls_status=sls_status,
        sg_status=sg_status,
        sg_max_area_m2=sg_max_area,
        sg_flag=sg_flag,
        panel_area_m2=round(panel_area, 4),
        next_compliant_thickness_mm=next_compliant,
        next_compliant_trace=next_compliant_trace,
        safety_glass_required=safety_glass_required,
        bal_status=bal_status,
        bal_min_thickness_mm=bal_min_thickness,
        bal_level=bal_level if (bushfire_required and is_bushfire_pane) else None,
        bal_element_type=element_type if (bushfire_required and is_bushfire_pane) else None,
        bushfire_required=bushfire_required,
        uls_trace=uls_trace, sls_trace=sls_trace,
        sg_trace=sg_trace if safety_glass_required and support_condition == '4-edge' else [],
    )


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


# ---------------------------------------------------------------------------
# N/C RATING LOOKUP
# ---------------------------------------------------------------------------

def get_pressures_from_nc_rating(df_nc, rating, location):
    """
    Looks up ULS and SLS pressures in Pa for a given N/C rating and location.
    Returns a dict with keys 'uls' and 'sls', or None if not found.
    """
    uls_rows = df_nc[(df_nc['Rating'] == rating) &
                     (df_nc['Pressure Type'] == 'ULS')]
    sls_rows = df_nc[(df_nc['Rating'] == rating) &
                     (df_nc['Pressure Type'] == 'SLS')]

    if len(uls_rows) == 0 or len(sls_rows) == 0:
        return None

    return {
        'uls': float(uls_rows.iloc[0][location]),
        'sls': float(sls_rows.iloc[0][location])
    }


# ---------------------------------------------------------------------------
# RESULTS DISPLAY
# ---------------------------------------------------------------------------

def print_results_mode1(results):
    """
    Prints Mode 1 results — minimum thickness finder.
    Shows ULS, SLS, Safety Glass (if applicable), and final governing thickness.
    """
    print()
    print('=' * 65)
    print('RESULTS - Minimum Thickness')
    print('=' * 65)

    for result in results:
        print()
        print(f"  Glass Type : {result['glass_type']} {result['glass_subtype']}")
        print(f"  Status     : {result['status']}")

        if result['status'] == 'PASS':
            print(f"  k_pane                                   : "
                  f"{result['k_pane']:.4f}")
            print(f"  ULS Minimum Thickness                    : "
                  f"{result['uls_minimum_thickness_mm']} mm")
            print(f"  SLS Minimum Thickness                    : "
                  f"{result['sls_minimum_thickness_mm']} mm")

            # Show 3mm Annealed area flag if triggered
            if result.get('annealed_area_flag'):
                flag = result['annealed_area_flag']
                print(f"  *** 3mm not permitted — panel area "
                      f"{flag['actual_area']}m2 exceeds maximum "
                      f"{flag['max_area']}m2 for this glazing configuration. "
                      f"Minimum thickness increased to 4mm.")

            # Show Safety Glass result only if safety glass was required
            if result.get('safety_glass_required'):
                if result['sg_minimum_thickness_mm'] is not None:
                    if result.get('sg_flag') == 'EXTRAPOLATE':
                        print(f"  Safety Glass Area Check (AS 1288 Table 5.1) : "
                              f"Thickness exceeds table scope. "
                              f"Manual extrapolation required.")
                    else:
                        print(f"  Safety Glass Min Thickness (Table 5.1)      : "
                              f"{result['sg_minimum_thickness_mm']} mm")

            print(f"  Final Minimum Thickness (governing)      : "
                  f"{result['minimum_thickness_mm']} mm")

        elif result['status'] == 'SG_INELIGIBLE':
            print(f"  Message    : {result['message']}")
        else:
            print(f"  Message    : {result['message']}")

    # IGU assumption note
    glazing_config = results[0]['glazing_config'] if results else 'single'
    print()
    if glazing_config == 'double':
        print('  NOTE: IGU Double — minimum thickness applies to each pane '
              'equally.')
        print('  All panes assumed to be the same glass type and thickness.')
    elif glazing_config == 'triple':
        print('  NOTE: IGU Triple — minimum thickness applies to each pane '
              'equally.')
        print('  All panes assumed to be the same glass type and thickness.')

    print()
    print('  NOTE: Human Impact requirements have not been considered.')
    print('  Results are for Wind Load resistance only (AS 1288 Section 4).')
    print('=' * 65)


def print_results_mode2(results):
    """
    Prints Mode 2 results — compliance checker.
    Shows k_pane, effective pressures, ULS/SLS/SG pass/fail per pane.
    """
    print()
    print('=' * 65)
    print('RESULTS - Compliance Check')
    print('=' * 65)

    for result in results:
        print()
        print(f"  Pane       : {result['pane_label']}")
        print(f"  Glass Type : {result['glass_type']} {result['glass_subtype']}")
        print(f"  Actual Thickness  : {result['actual_thickness_mm']} mm")

        if result['nominal_thickness_mm'] is not None:
            print(f"  Nominal Thickness : {result['nominal_thickness_mm']} mm "
                  f"(AS 1288 Table 4.1)")

        if result['k_pane'] is not None:
            print(f"  k_pane            : {result['k_pane']:.4f}")

        if result['status'] in ('PASS', 'FAIL'):
            print(f"  Effective ULS     : {result['effective_uls_pa']:.0f} Pa")
            print(f"  Effective SLS     : {result['effective_sls_pa']:.0f} Pa")
            print(f"  ULS Check         : {result['uls_status']} "
                  f"(span {result['span_mm']:.0f}mm vs "
                  f"B_uls {result['B_uls_mm']:.0f}mm)")
            print(f"  SLS Check         : {result['sls_status']} "
                  f"(span {result['span_mm']:.0f}mm vs "
                  f"B_sls {result['B_sls_mm']:.0f}mm)")

            # 3mm Annealed area flag
            if result.get('annealed_area_flag'):
                flag = result['annealed_area_flag']
                print(f"  *** 3mm Annealed area restriction FAIL — "
                      f"actual area {flag['actual_area']}m2 exceeds "
                      f"maximum {flag['max_area']}m2.")

            # Safety Glass check — only if required
            if result.get('safety_glass_required') and \
               result['sg_status'] not in (None, 'N/A'):
                if result['sg_status'] == 'EXTRAPOLATE':
                    print(f"  Safety Glass Check: Thickness exceeds AS 1288 "
                          f"Table 5.1 scope. Manual extrapolation required.")
                else:
                    print(f"  Safety Glass Check: {result['sg_status']} "
                          f"(panel area {result['panel_area_m2']}m2 vs "
                          f"max {result['sg_max_area_m2']}m2)")

            print(f"  Overall           : {result['status']}")

            # Next compliant thickness recommendation
            if result['status'] == 'FAIL' and \
               result.get('next_compliant_thickness_mm') is not None:
                sg_text = (', and Safety Glass Area Check'
                           if result.get('safety_glass_required') else '')
                print(f"  *** Next compliant thickness: "
                      f"{result['next_compliant_thickness_mm']}mm — "
                      f"passes ULS and SLS{sg_text}.")

        else:
            print(f"  Status    : {result['status']}")
            print(f"  Message   : {result['message']}")

    print()
    print('  NOTE: Human Impact requirements have not been considered.')
    print('  Results are for Wind Load resistance only (AS 1288 Section 4).')
    print('=' * 65)


# ---------------------------------------------------------------------------
# INTERACTIVE INPUT HELPERS
# ---------------------------------------------------------------------------

def get_float_input(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return float(value)
        except ValueError:
            print("  Please enter a valid number.")


def get_choice_input(prompt, valid_choices):
    while True:
        value = input(prompt).strip()
        if value in valid_choices:
            return value
        print(f"  Please enter one of: {', '.join(valid_choices)}")


def get_glass_type_selection(safety_glass_required=False):
    """
    Asks the user which glass types to check for Mode 1.
    If safety glass is required, ineligible types are excluded.
    Returns a list of (glass_type, glass_subtype) tuples.
    """
    print()
    print("  Select glass type(s) to check.")
    print("  You can select multiple by typing their numbers")
    print("  separated by commas. Example: 1,3")
    print()

    if safety_glass_required:
        options = {
            '1': ('Monolithic', 'Toughened'),
            '2': ('Laminated',  'Annealed'),
            '3': ('Laminated',  'Heat-strengthened'),
            '4': ('Laminated',  'Toughened'),
        }
        print("  1 - Monolithic Toughened")
        print("  2 - Laminated Annealed")
        print("  3 - Laminated Heat-strengthened")
        print("  4 - Laminated Toughened")
    else:
        options = {
            '1': ('Monolithic', 'Annealed'),
            '2': ('Monolithic', 'Toughened'),
            '3': ('Monolithic', 'Heat-strengthened'),
            '4': ('Laminated',  'Annealed'),
            '5': ('Laminated',  'Heat-strengthened'),
            '6': ('Laminated',  'Toughened'),
        }
        print("  1 - Monolithic Annealed")
        print("  2 - Monolithic Toughened")
        print("  3 - Monolithic Heat-strengthened")
        print("  4 - Laminated Annealed")
        print("  5 - Laminated Heat-strengthened")
        print("  6 - Laminated Toughened")

    print()

    while True:
        raw = input("  Enter selection: ").strip()
        selections = [s.strip() for s in raw.split(',')]

        if all(s in options for s in selections):
            seen = []
            for s in selections:
                if options[s] not in seen:
                    seen.append(options[s])
            return seen

        print(f"  Please enter numbers from the list above, "
              f"separated by commas.")


def get_single_glass_type(safety_glass_required=False):
    """
    Asks the user to select a single glass type for one pane in Mode 2.
    Returns a (glass_type, glass_subtype) tuple.
    """
    print()
    if safety_glass_required:
        options = {
            '1': ('Monolithic', 'Toughened'),
            '2': ('Laminated',  'Annealed'),
            '3': ('Laminated',  'Heat-strengthened'),
            '4': ('Laminated',  'Toughened'),
        }
        print("    1 - Monolithic Toughened")
        print("    2 - Laminated Annealed")
        print("    3 - Laminated Heat-strengthened")
        print("    4 - Laminated Toughened")
    else:
        options = {
            '1': ('Monolithic', 'Annealed'),
            '2': ('Monolithic', 'Toughened'),
            '3': ('Monolithic', 'Heat-strengthened'),
            '4': ('Laminated',  'Annealed'),
            '5': ('Laminated',  'Heat-strengthened'),
            '6': ('Laminated',  'Toughened'),
        }
        print("    1 - Monolithic Annealed")
        print("    2 - Monolithic Toughened")
        print("    3 - Monolithic Heat-strengthened")
        print("    4 - Laminated Annealed")
        print("    5 - Laminated Heat-strengthened")
        print("    6 - Laminated Toughened")

    choice = get_choice_input("    Enter selection: ", list(options.keys()))
    return options[choice]


def get_wind_loads(nc_csv_path):
    """
    Asks the user how to enter wind loads.
    Returns (wind_pressure_uls, wind_pressure_sls) in Pa.
    """
    print()
    print("  WIND LOAD INPUT METHOD")
    print("  1 - Enter ULS and SLS pressures directly (AS 1170.2)")
    print("  2 - Select N/C wind classification (AS 4055)")
    wind_method = get_choice_input("  Enter 1 or 2: ", ['1', '2'])

    if wind_method == '1':
        print()
        print("  WIND PRESSURES")
        wind_pressure_uls = get_float_input("  ULS wind pressure (Pa): ")
        wind_pressure_sls = get_float_input("  SLS wind pressure (Pa): ")
    else:
        valid_ratings = ['N1','N2','N3','N4','N5','N6',
                         'C1','C2','C3','C4']
        print()
        print("  WIND CLASSIFICATION")
        print("  Valid ratings: N1, N2, N3, N4, N5, N6, C1, C2, C3, C4")
        rating = get_choice_input("  Enter rating: ", valid_ratings)

        print()
        print("  WINDOW LOCATION")
        print("  G - General")
        print("  C - Corner")
        location_input = get_choice_input(
            "  Enter G or C: ", ['G','C','g','c']
        )
        location = 'General' if location_input.lower() == 'g' else 'Corner'

        df_nc     = load_nc_table(nc_csv_path)
        pressures = get_pressures_from_nc_rating(df_nc, rating, location)

        if pressures is None:
            print(f"  ERROR: Could not find pressure values for "
                  f"{rating} {location}.")
            exit()

        wind_pressure_uls = pressures['uls']
        wind_pressure_sls = pressures['sls']

        print()
        print(f"  Using pressures for {rating} {location}:")
        print(f"  ULS: {wind_pressure_uls} Pa")
        print(f"  SLS: {wind_pressure_sls} Pa")

    return wind_pressure_uls, wind_pressure_sls


def get_panel_geometry():
    """
    Asks for panel dimensions and support condition.
    Returns height_mm, width_mm, support_condition, span_dimension.
    """
    print()
    print("  PANEL DIMENSIONS")
    height_mm = get_float_input("  Height (mm): ")
    width_mm  = get_float_input("  Width  (mm): ")

    print()
    print("  SUPPORT CONDITION")
    print("  4 - Four edge supported")
    print("  2 - Two edge supported")
    support_input     = get_choice_input("  Enter 4 or 2: ", ['4','2'])
    support_condition = '4-edge' if support_input == '4' else '2-edge'

    span_dimension = 'width'
    if support_condition == '2-edge':
        print()
        print("  SPAN DIRECTION")
        print("  Specify which dimension sits between the two supported edges.")
        print("  H - Height is the span")
        print("  W - Width is the span")
        span_input     = get_choice_input(
            "  Enter H or W: ", ['H','W','h','w']
        )
        span_dimension = 'height' if span_input.lower() == 'h' else 'width'

    return height_mm, width_mm, support_condition, span_dimension


# ---------------------------------------------------------------------------
# INTERACTIVE INPUT RUNNER
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(
        script_dir, '..', 'data', 'Wind_Load_Check_Tables_Full.csv'
    )
    nc_csv_path = os.path.join(
        script_dir, '..', 'data', 'N_C_Tables.csv'
    )
    nominal_thickness_csv_path = os.path.join(
        script_dir, '..', 'data', 'Table_4_1_Minimum_Glass_Thickness.csv'
    )

    print()
    print('=' * 65)
    print('  AS 1288 Glass Thickness Calculator — Wind Loads Only')
    print('  Duce Timber Windows and Doors')
    print('=' * 65)

    # --- Calculation mode ---
    print()
    print("  CALCULATION MODE")
    print("  1 - Minimum Thickness Finder")
    print("      Find the minimum compliant thickness for a glass type")
    print("  2 - Compliance Checker")
    print("      Check if a known glass thickness meets wind load requirements")
    mode = get_choice_input("  Enter 1 or 2: ", ['1', '2'])

    # --- Panel geometry ---
    height_mm, width_mm, support_condition, span_dimension = get_panel_geometry()

    # --- Wind loads ---
    wind_pressure_uls, wind_pressure_sls = get_wind_loads(nc_csv_path)

    # --- Safety Glass Area Check toggle ---
    print()
    print("  SAFETY GLASS AREA CHECK (Beta)")
    print("  Is safety glass required for this application?")
    print("  Y - Yes")
    print("  N - No")
    sg_input          = get_choice_input("  Enter Y or N: ", ['Y','N','y','n'])
    safety_glass_required = sg_input.lower() == 'y'

    if safety_glass_required:
        if support_condition == '2-edge':
            print()
            print("  NOTE: Safety Glass Area Check is not available for")
            print("  2-edge supported panels in this version. The check")
            print("  will be skipped.")
            safety_glass_required = False
        else:
            print()
            print("  IMPORTANT: Safety glass requirement is declared by the user.")
            print("  This tool does not assess whether safety glass is required")
            print("  for this application. The user is responsible for")
            print("  determining applicability in accordance with AS 1288 and")
            print("  relevant building codes.")
            print("  Note: This feature is in beta. 2-edge supported panels are")
            print("  not covered in this version. There may be other governing")
            print("  requirements that restrict glass dimensions and thickness")
            print("  for human impact considerations. Please refer to Section 5")
            print("  of AS 1288 to confirm those details.")

    if mode == '1':
        # --- MODE 1 ---
        print()
        print("  GLAZING CONFIGURATION")
        print("  S - Single Glazed")
        print("  D - IGU Double (2 panes, equal thickness assumed)")
        print("  T - IGU Triple (3 panes, equal thickness assumed)")
        glazing_input  = get_choice_input(
            "  Enter S, D, or T: ", ['S','D','T','s','d','t']
        )
        glazing_config = {'s':'single','d':'double','t':'triple'}[
            glazing_input.lower()
        ]

        selected_glass_types = get_glass_type_selection(safety_glass_required)

        print()
        print("  Running calculation...")

        results = run_calculation(
            csv_path             = csv_path,
            height_mm            = height_mm,
            width_mm             = width_mm,
            support_condition    = support_condition,
            span_dimension       = span_dimension,
            wind_pressure_uls    = wind_pressure_uls,
            wind_pressure_sls    = wind_pressure_sls,
            selected_glass_types = selected_glass_types,
            glazing_config       = glazing_config,
            safety_glass_required = safety_glass_required
        )

        print_results_mode1(results)

    else:
        # --- MODE 2 ---
        print()
        print("  GLAZING CONFIGURATION")
        print("  S - Single Glazed")
        print("  D - IGU Double (2 panes)")
        print("  T - IGU Triple (3 panes)")
        glazing_input = get_choice_input(
            "  Enter S, D, or T: ", ['S','D','T','s','d','t']
        )

        pane_labels = {
            's': ['Single'],
            'd': ['Outer', 'Inner'],
            't': ['Outer', 'Middle', 'Inner']
        }[glazing_input.lower()]

        panes = []
        for label in pane_labels:
            print()
            print(f"  {label.upper()} PANE")
            print(f"  Select glass type for {label} pane:")
            glass_type, glass_subtype = get_single_glass_type(safety_glass_required)
            actual_thickness = get_float_input(
                f"  Actual thickness of {label} pane (mm): "
            )
            panes.append({
                'label':              label,
                'glass_type':         glass_type,
                'glass_subtype':      glass_subtype,
                'actual_thickness_mm': actual_thickness
            })

        print()
        print("  Running compliance check...")

        results = run_compliance_check(
            csv_path                   = csv_path,
            nominal_thickness_csv_path = nominal_thickness_csv_path,
            height_mm                  = height_mm,
            width_mm                   = width_mm,
            support_condition          = support_condition,
            span_dimension             = span_dimension,
            wind_pressure_uls          = wind_pressure_uls,
            wind_pressure_sls          = wind_pressure_sls,
            panes                      = panes,
            safety_glass_required      = safety_glass_required
        )

        print_results_mode2(results)