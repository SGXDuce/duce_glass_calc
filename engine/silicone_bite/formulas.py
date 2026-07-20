# AS 1288 Glass Thickness Calculator
# engine/silicone_bite/formulas.py
#
# Pure math for structural silicone bite thickness sizing per AS 1288
# Section 9 / Appendix F. No side effects, no Flask/UI imports.

from math import cos, radians

from engine.silicone_bite.constants import (
    SIGMA_S,
    MIN_NOMINAL_THICKNESS,
)
from engine.shared.table_4_1 import (
    TABLE_4_1_MONOLITHIC,
    TABLE_4_1_LAMINATED,
    CHAMFER_ALLOWANCE_MM,
    usable_bite,
    find_min_nominal_for_usable_bite,
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
    # Per AS 1288 Section 9 / Clause 9.3.3.1, confirmed with domain expert
    # (spreadsheet author). That spreadsheet's height-capping step was an
    # error - B is simply the larger of the two widths, height is irrelevant.
    return max(width_1_mm, width_2_mm)


def calculate_required_bite(f_factor, governing_width_mm, wind_pressure_kpa, sigma_s=SIGMA_S):
    # AS 1288 equation 9.3(1): t = (F x B x Pz) / sigma_s
    governing_width_m = governing_width_mm / 1000
    bite_mm = (f_factor * governing_width_m * wind_pressure_kpa) / sigma_s
    return bite_mm


def apply_thickness_floor(nominal_thickness, floor=MIN_NOMINAL_THICKNESS):
    # Dow Corning structural silicone seals start at 6mm. Confirmed per
    # internal review to apply to both monolithic and laminated.
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
    required_bite_raw_mm = calculate_required_bite(f_factor, governing_width_mm, wind_pressure_kpa)
    required_bite_mm = max(required_bite_raw_mm, 6.0)

    mitre_angle_deg = calculate_mitre_angle(angle_deg)

    nominal_monolithic_raw, usable_bite_monolithic = find_min_nominal_for_usable_bite(
        required_bite_mm, TABLE_4_1_MONOLITHIC, joint_type, mitre_angle_deg=mitre_angle_deg
    )
    nominal_laminated_raw, usable_bite_laminated = find_min_nominal_for_usable_bite(
        required_bite_mm, TABLE_4_1_LAMINATED, joint_type, mitre_angle_deg=mitre_angle_deg
    )

    nominal_monolithic = apply_thickness_floor(nominal_monolithic_raw)
    nominal_laminated = apply_thickness_floor(nominal_laminated_raw)

    # If the 6mm MIN_NOMINAL_THICKNESS floor raised the nominal above what
    # the Table 4.1 search itself found, usable_bite_{monolithic,laminated}
    # above is stale (computed at the smaller pre-floor nominal the search
    # stopped at) - recompute at the floored nominal actually used/displayed.
    if nominal_monolithic is not None and nominal_monolithic != nominal_monolithic_raw:
        usable_bite_monolithic = usable_bite(
            TABLE_4_1_MONOLITHIC[nominal_monolithic], mitre_angle_deg=mitre_angle_deg
        ) if joint_type == 'mitred' else usable_bite(TABLE_4_1_MONOLITHIC[nominal_monolithic])
    if nominal_laminated is not None and nominal_laminated != nominal_laminated_raw:
        usable_bite_laminated = usable_bite(
            TABLE_4_1_LAMINATED[nominal_laminated], mitre_angle_deg=mitre_angle_deg
        ) if joint_type == 'mitred' else usable_bite(TABLE_4_1_LAMINATED[nominal_laminated])

    actual_thickness_monolithic = TABLE_4_1_MONOLITHIC.get(nominal_monolithic)
    actual_thickness_laminated = TABLE_4_1_LAMINATED.get(nominal_laminated)

    common_fields = dict(
        angle_deg=angle_deg, f_factor=f_factor, governing_width_mm=governing_width_mm,
        wind_pressure_kpa=wind_pressure_kpa, required_bite_mm=required_bite_mm,
        required_bite_raw_mm=required_bite_raw_mm,
        joint_type=joint_type, mitre_angle_deg=mitre_angle_deg,
        nominal_monolithic=nominal_monolithic, nominal_laminated=nominal_laminated,
        usable_bite_monolithic=usable_bite_monolithic, usable_bite_laminated=usable_bite_laminated,
        actual_thickness_monolithic=actual_thickness_monolithic,
        actual_thickness_laminated=actual_thickness_laminated,
        deduction_mm=CHAMFER_ALLOWANCE_MM, deduction_type='chamfer',
    )

    if nominal_monolithic is None and nominal_laminated is None:
        return make_silicone_result(
            status='NO_COMPLIANT_THICKNESS',
            message='Required bite exceeds all available thicknesses for both monolithic and laminated glass',
            **common_fields,
        )

    return make_silicone_result(status='PASS', **common_fields)
