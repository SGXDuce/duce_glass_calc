from engine.wind_load.constants import (
    TABLE_AR_VALUES, BAL_RULES, SAFETY_GLASS_CATEGORY,
    SAFETY_GLASS_AREA_CAT1, SAFETY_GLASS_AREA_CAT2,
    KPANE_SINGLE, KPANE_DOUBLE, KPANE_TRIPLE,
    C1_FACTORS
)


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


def get_c1_factor(glass_type, glass_subtype):
    """
    Returns the c1 factor for a given glass type combination.
    Returns 1.0 for Monolithic glass (no modification).
    """
    return C1_FACTORS.get((glass_type, glass_subtype), 1.0)


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
