# AS 1288 Glass Thickness Calculator
# engine/silicone_bite/formulas.py
#
# Pure math for structural silicone bite thickness sizing per AS 1288
# Section 9 / Appendix F. No side effects, no Flask/UI imports.

import math
from math import cos, radians

from engine.silicone_bite.constants import (
    SIGMA_S,
    MIN_NOMINAL_THICKNESS,
    TABLE_4_1_MONOLITHIC,
    TABLE_4_1_LAMINATED,
    CHAMFER_ALLOWANCE_MM,
)
from engine.shared.results import make_silicone_result


def calculate_f_factor(angle_deg):
    """
    Returns the geometry factor F used in the bite equation.
    """
    # 90 degrees is a special case: it comes from AS 1288 Appendix F, a
    # separate physical geometry to the general glazing angle formula in
    # Section 9 Clause 9.3.3.1, and does not reduce to that formula at
    # angle_deg == 90. Confirmed by AGG bulletin and engineer input.
    if angle_deg == 90:
        return 0.5
    if 90 < angle_deg <= 160:
        return 1 / (2 * cos(radians(angle_deg / 2)))
    raise ValueError(
        f"Angle {angle_deg} deg is outside the structural silicone scope (90-160 deg inclusive)"
    )


def calculate_governing_width(width_1_mm, width_2_mm):
    # Per AS 1288 Section 9 / Clause 9.3.3.1, confirmed directly with Michael
    # (spreadsheet author). His spreadsheet's height-capping step was an
    # error - B is simply the larger of the two widths, height is irrelevant.
    return max(width_1_mm, width_2_mm)


def calculate_required_bite(f_factor, governing_width_mm, wind_pressure_kpa, sigma_s=SIGMA_S):
    # AS 1288 equation 9.3(1): t = (F x B x Pz) / sigma_s
    governing_width_m = governing_width_mm / 1000
    bite_mm = (f_factor * governing_width_m * wind_pressure_kpa) / sigma_s
    return bite_mm


def find_min_nominal_for_bite(required_bite_mm, thickness_table):
    # Comparison is against worst-case minimum actual thickness per AS 1288
    # Table 4.1, not the nominal label - see Table 9.1 Note 1.
    for nominal in sorted(thickness_table):
        if thickness_table[nominal] >= required_bite_mm:
            return nominal
    return None


def apply_thickness_floor(nominal_thickness, floor=MIN_NOMINAL_THICKNESS):
    # Dow Corning structural silicone seals start at 6mm. Confirmed by
    # Michael to apply to both monolithic and laminated.
    if nominal_thickness is None:
        return None
    return max(nominal_thickness, floor)


def calculate_mitre_angle(joint_angle_deg):
    """
    Converts the joint angle (angle between two adjacent panels) to the
    mitre angle (the angle at which each glass edge is cut).
    mitre_angle = (180 - joint_angle_deg) / 2
    So a 90 deg joint gives a 45 deg mitre angle.
    """
    return (180 - joint_angle_deg) / 2


def usable_bite(minimum_actual_mm, mitre_angle_deg=None, chamfer_mm=CHAMFER_ALLOWANCE_MM):
    """
    Calculates the usable silicone bite length from a glass edge.

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


def _normalise_joint_type(joint_type):
    normalised = joint_type.strip().lower()
    if normalised == 'mitre':
        normalised = 'mitred'
    if normalised not in ('butt', 'mitred'):
        raise ValueError(
            f"Unknown joint_type '{joint_type}' - expected 'butt', 'mitred', or 'mitre'"
        )
    return normalised


def run_bite_calculation(width_1_mm, width_2_mm, angle_deg, wind_pressure_kpa, joint_type='butt'):
    """
    Main entry point: chains the bite sizing steps and returns nominal
    thicknesses and usable bite for both monolithic and laminated glass.
    Every return path goes through make_silicone_result() - see Section 6.4.
    """
    try:
        joint_type = _normalise_joint_type(joint_type)
    except ValueError as e:
        return make_silicone_result(status='INVALID', message=str(e))

    try:
        f_factor = calculate_f_factor(angle_deg)
    except ValueError as e:
        return make_silicone_result(status='ANGLE_OUT_OF_RANGE', angle_deg=angle_deg, message=str(e))

    governing_width_mm = calculate_governing_width(width_1_mm, width_2_mm)
    required_bite_mm = calculate_required_bite(f_factor, governing_width_mm, wind_pressure_kpa)

    nominal_monolithic = find_min_nominal_for_bite(required_bite_mm, TABLE_4_1_MONOLITHIC)
    nominal_laminated = find_min_nominal_for_bite(required_bite_mm, TABLE_4_1_LAMINATED)

    nominal_monolithic = apply_thickness_floor(nominal_monolithic)
    nominal_laminated = apply_thickness_floor(nominal_laminated)

    mitre_angle_deg = calculate_mitre_angle(angle_deg)

    usable_bite_monolithic = None
    if nominal_monolithic is not None:
        min_actual_mono = TABLE_4_1_MONOLITHIC[nominal_monolithic]
        if joint_type == 'mitred':
            usable_bite_monolithic = usable_bite(min_actual_mono, mitre_angle_deg=mitre_angle_deg)
        else:
            usable_bite_monolithic = usable_bite(min_actual_mono)

    usable_bite_laminated = None
    if nominal_laminated is not None:
        min_actual_lam = TABLE_4_1_LAMINATED[nominal_laminated]
        if joint_type == 'mitred':
            usable_bite_laminated = usable_bite(min_actual_lam, mitre_angle_deg=mitre_angle_deg)
        else:
            usable_bite_laminated = usable_bite(min_actual_lam)

    if nominal_monolithic is None and nominal_laminated is None:
        return make_silicone_result(
            status='NO_COMPLIANT_THICKNESS',
            angle_deg=angle_deg, f_factor=f_factor, governing_width_mm=governing_width_mm,
            wind_pressure_kpa=wind_pressure_kpa, required_bite_mm=required_bite_mm,
            joint_type=joint_type, mitre_angle_deg=mitre_angle_deg,
            nominal_monolithic=nominal_monolithic, nominal_laminated=nominal_laminated,
            usable_bite_monolithic=usable_bite_monolithic, usable_bite_laminated=usable_bite_laminated,
            message='Required bite exceeds all available thicknesses for both monolithic and laminated glass',
        )

    return make_silicone_result(
        status='PASS',
        angle_deg=angle_deg, f_factor=f_factor, governing_width_mm=governing_width_mm,
        wind_pressure_kpa=wind_pressure_kpa, required_bite_mm=required_bite_mm,
        joint_type=joint_type, mitre_angle_deg=mitre_angle_deg,
        nominal_monolithic=nominal_monolithic, nominal_laminated=nominal_laminated,
        usable_bite_monolithic=usable_bite_monolithic, usable_bite_laminated=usable_bite_laminated,
    )
