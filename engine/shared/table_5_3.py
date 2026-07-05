# AS 1288 Glass Thickness Calculator
# engine/shared/table_5_3.py
#
# AS 1288 Table 5.3 - "Glazed panels with unframed side edges" lookup.
# Determines minimum glass thickness for panels not fully framed on all
# four edges, based on height (span), glass type, panel width, and number
# of unframed vertical edges (butt joints). Shared across wind_load,
# silicone_bite, and structural glazing engines. Pure lookup logic - no
# Flask, no UI code.

import pandas as pd

GLASS_TYPE_LOOKUP_OVERRIDES = {
    # AS 1288 Table 5.3 Note 2: the values for toughened safety glass are
    # also applicable to laminated toughened safety glass.
    'Laminated Toughened': 'Toughened',
}


def load_table_5_3(csv_path):
    """
    Loads AS 1288 Table 5.3 from CSV. "Null" entries mean no restriction
    for that constraint and are converted to None (NaN once the column is
    coerced to numeric).
    """
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df = df.replace('Null', None)

    numeric_columns = ['Height Min', 'Height Max', 'Width Max', 'Thickness Min', 'Butt Joints max']
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def _row_in_height_band(row, height_m):
    # The first band (Height Min == 0) is inclusive at zero: height_m <=
    # Height Max. Every other band is Height Min < height_m <= Height Max,
    # so a height sitting exactly on a boundary belongs to the lower band.
    if row['Height Min'] == 0:
        return height_m <= row['Height Max']
    return row['Height Min'] < height_m <= row['Height Max']


def _row_satisfies_panel(row, panel_width_m, num_butt_joints):
    joints_ok = pd.isna(row['Butt Joints max']) or num_butt_joints <= row['Butt Joints max']
    width_ok = pd.isna(row['Width Max']) or panel_width_m <= row['Width Max']
    return joints_ok and width_ok


def check_table_5_3(height_m, glass_type, panel_width_m, num_butt_joints, table_data):
    """
    Checks a panel configuration against AS 1288 Table 5.3.

    Args:
        height_m: panel height/span in metres (per Clause 1.4.51, height = span)
        glass_type: one of 'Annealed', 'Heat Strengthened', 'Toughened',
                    'Laminated', 'Laminated Toughened'
        panel_width_m: width of the single panel in metres
        num_butt_joints: number of unframed vertical edges on this panel (1 or 2)
        table_data: dataframe from load_table_5_3()

    Returns a dict with:
        'status': 'COMPLIANT', 'NON_COMPLIANT', or 'NOT_PERMITTED'
        'min_thickness_mm': minimum nominal thickness required (None if not permitted)
        'max_width_m': maximum panel width allowed (None if no limit or not permitted)
        'max_butt_joints': maximum butt joints allowed (None if no limit or not permitted)
        'message': human-readable explanation
        'glass_type_used': the glass type actually looked up (Note 2 override
                            for Laminated Toughened)
    """
    glass_type_used = GLASS_TYPE_LOOKUP_OVERRIDES.get(glass_type, glass_type)

    type_rows = table_data[table_data['Glass Type'] == glass_type_used]

    band_rows = type_rows[type_rows.apply(_row_in_height_band, axis=1, height_m=height_m)]

    if len(band_rows) == 0:
        max_height_for_type = type_rows['Height Max'].max() if len(type_rows) > 0 else None
        if max_height_for_type is not None:
            message = (
                f"{glass_type} glass is not permitted for heights above "
                f"{max_height_for_type}m under Table 5.3"
            )
        else:
            message = f"No Table 5.3 data found for glass type '{glass_type}'"
        return {
            'status': 'NOT_PERMITTED',
            'min_thickness_mm': None,
            'max_width_m': None,
            'max_butt_joints': None,
            'message': message,
            'glass_type_used': glass_type_used,
        }

    qualifying_rows = band_rows[
        band_rows.apply(_row_satisfies_panel, axis=1, panel_width_m=panel_width_m,
                         num_butt_joints=num_butt_joints)
    ]

    if len(qualifying_rows) == 0:
        max_widths = [w for w in band_rows['Width Max'] if not pd.isna(w)]
        max_joints = [j for j in band_rows['Butt Joints max'] if not pd.isna(j)]

        reasons = []
        if max_widths and panel_width_m > max(max_widths):
            reasons.append(
                f"panel width {panel_width_m}m exceeds the maximum permitted "
                f"width of {max(max_widths)}m for this height band"
            )
        if max_joints and num_butt_joints > max(max_joints):
            reasons.append(
                f"{num_butt_joints} butt joints exceeds the maximum of "
                f"{max(max_joints)} permitted for this height band"
            )
        if not reasons:
            reasons.append("panel configuration exceeds the constraints for all matching Table 5.3 rows")

        return {
            'status': 'NON_COMPLIANT',
            'min_thickness_mm': None,
            'max_width_m': None,
            'max_butt_joints': None,
            'message': "; ".join(reasons),
            'glass_type_used': glass_type_used,
        }

    best_row = qualifying_rows.loc[qualifying_rows['Thickness Min'].idxmin()]
    min_thickness_mm = int(best_row['Thickness Min'])
    max_width_m = None if pd.isna(best_row['Width Max']) else float(best_row['Width Max'])
    max_butt_joints = None if pd.isna(best_row['Butt Joints max']) else int(best_row['Butt Joints max'])

    return {
        'status': 'COMPLIANT',
        'min_thickness_mm': min_thickness_mm,
        'max_width_m': max_width_m,
        'max_butt_joints': max_butt_joints,
        'message': (
            f"{glass_type_used} glass at {height_m}m height requires minimum "
            f"{min_thickness_mm}mm nominal thickness under Table 5.3"
        ),
        'glass_type_used': glass_type_used,
    }
