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
