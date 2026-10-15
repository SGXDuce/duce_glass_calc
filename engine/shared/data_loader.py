# AS 1288 Glass Thickness Calculator
# engine/shared/data_loader.py
#
# Loads the three CSV reference tables and converts an actual measured
# glass thickness to its nominal classification per AS 1288 Table 4.1.
# These functions have no dependency on anything else in the engine -
# they are pure data access.
#
# Moved unchanged from calculator.py during the V1.1 refactor.
# Duce Timber Windows and Doors

import pandas as pd


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
# HUMAN IMPACT (engine/human_impact) DATA LOADERS
#
# Added for the human_impact engine (AS 1288 Section 5). Same pure-data-
# access discipline as the loaders above - no dependency on anything else
# in the engine.
# ---------------------------------------------------------------------------

def load_table_5_4_frameless_max_area(csv_path):
    """
    Loads the bathroom (partly framed / unframed) maximum-area table from
    CSV. One row per nominal thickness: the largest panel area that
    thickness can serve. Returns a pandas DataFrame with columns
    nominal_thickness_mm, max_area_m2, sorted thinnest first - callers
    rely on this order to find the thinnest row that is big enough.
    """
    df = pd.read_csv(csv_path)
    numeric_columns = ['nominal_thickness_mm', 'max_area_m2']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    return df.sort_values('nominal_thickness_mm').reset_index(drop=True)


def load_bathroom_toughened_allowance(csv_path):
    """
    Loads the bathroom allowance that lets small monolithic toughened
    panels use a thinner glass than the main table would give. Returns a
    pandas DataFrame with columns glass_type, min_thickness_mm,
    max_area_m2 (currently a single MT row).
    """
    df = pd.read_csv(csv_path)
    numeric_columns = ['min_thickness_mm', 'max_area_m2']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    return df


def load_mistaken_doorway_exceptions(csv_path):
    """
    Loads AS 1288 Clause 5.4 "mistaken for a doorway" exceptions from CSV.
    Returns a pandas DataFrame with columns: exception_id, test, comparator,
    threshold, notes_plain. 'threshold' is left as-is (str) since it can be
    numeric (mm figures) or 'true' (boolean-style test) - callers coerce
    per-row based on 'test'.
    """
    return pd.read_csv(csv_path)


def load_sashless_span_table(csv_path):
    """
    Loads the AS 1288 Clause 5.15 sashless span table from CSV.
    Returns a pandas DataFrame with columns: glass_type, max_span_mm,
    min_thickness_mm. glass_type is 'MT' (monolithic toughened) or 'L'
    (any laminated type: annealed, heat-strengthened or toughened). Rows are in ascending max_span_mm order per glass
    type - callers rely on this order to find the first (narrowest)
    qualifying band.
    """
    df = pd.read_csv(csv_path)
    numeric_columns = ['max_span_mm', 'min_thickness_mm']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col])
    return df
