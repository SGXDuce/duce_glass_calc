# AS 1288 Glass Thickness Calculator
# engine/shared/table_4_1.py
#
# Shared AS 1288 Table 4.1 (actual -> nominal glass thickness) reference data
# and lookup helpers. Used by both engine/silicone_bite/ (faceted glazing,
# chamfer/mitre deduction applies) and engine/structural_glazing/ (flat
# glazing, no deduction applies) - see Section 12.4 of the project summary.

import math

# Table 4.1 minimum actual thickness (mm) per nominal thickness (mm).
# Monolithic floors at 4mm per company policy - no 3mm.
TABLE_4_1_MONOLITHIC = {4: 3.8, 5: 4.8, 6: 5.8, 8: 7.7, 10: 9.7, 12: 11.7, 15: 14.5, 19: 18, 25: 23.5}
TABLE_4_1_LAMINATED = {5: 4.6, 6: 5.6, 8: 7.6, 10: 9.6, 12: 11.6, 16: 15.4, 20: 19.4, 24: 23.4}

CHAMFER_ALLOWANCE_MM = 2  # mm, applies to all nominal thicknesses >= 6mm.
# Below 6mm the chamfer is smaller, but the faceted engine floors at 6mm
# nominal, so those values are never reached.
# Confirmed as a flat 2mm for both monolithic and laminated from 6mm onwards.


def find_min_nominal_for_bite(required_bite_mm, thickness_table):
    """
    Returns the smallest nominal thickness whose raw minimum actual
    thickness (undeducted - no chamfer or mitre allowance) satisfies the
    required bite. Returns None if no available size in the table
    satisfies the requirement.

    Used directly by engine/structural_glazing/ - silicone there bonds to
    the flat glass face, not a cut edge, so no chamfer/mitre deduction
    applies (see the NOTE at the top of structural_glazing/formulas.py).
    """
    for nominal in sorted(thickness_table):
        if thickness_table[nominal] >= required_bite_mm:
            return nominal
    return None


def usable_bite(minimum_actual_mm, mitre_angle_deg=None, chamfer_mm=CHAMFER_ALLOWANCE_MM):
    """
    Calculates the usable silicone bite length from a cut glass edge, used
    only by the faceted engine (engine/silicone_bite/).

    For butt/lap joints: usable bite = minimum actual thickness - chamfer
    For mitred joints: usable bite = (minimum actual thickness / cos(mitre angle)) - chamfer

    The mitre angle is NOT the joint angle — it is derived from the joint angle:
    mitre_angle = (180 - joint_angle) / 2
    So a 90° joint gives a 45° mitre angle.

    Mitred edges provide more usable bite per mm of glass because the diagonal
    cut surface is longer than the flat edge thickness.
    """
    if mitre_angle_deg is not None:
        return minimum_actual_mm / math.cos(math.radians(mitre_angle_deg)) - chamfer_mm
    return minimum_actual_mm - chamfer_mm


def find_min_nominal_for_usable_bite(required_bite_mm, thickness_table, joint_type,
                                      mitre_angle_deg=None, chamfer_mm=CHAMFER_ALLOWANCE_MM):
    """
    Returns the smallest nominal thickness whose USABLE bite (after chamfer
    and mitre deduction) satisfies the required bite. Used only by the
    faceted engine (engine/silicone_bite/), where silicone bonds to the cut
    edge itself.

    For butt joints: usable bite = min_actual - chamfer
    For mitred joints: usable bite = min_actual / cos(mitre_angle) - chamfer

    This is different from comparing against raw min_actual — chamfer reduces
    the available contact surface, so thicker glass may be needed.

    Returns (nominal_thickness, usable_bite_value) tuple, or (None, None)
    if no available size satisfies the requirement.
    """
    for nominal in sorted(thickness_table):
        min_actual = thickness_table[nominal]
        if joint_type == 'mitred':
            usable = usable_bite(min_actual, mitre_angle_deg=mitre_angle_deg, chamfer_mm=chamfer_mm)
        else:
            usable = usable_bite(min_actual, chamfer_mm=chamfer_mm)
        if usable >= required_bite_mm:
            return nominal, usable
    return None, None
