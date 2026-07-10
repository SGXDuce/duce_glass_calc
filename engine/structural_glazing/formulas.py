# AS 1288 Glass Thickness Calculator
# engine/structural_glazing/formulas.py
#
# Pure math for flat, angle-free structural glazing bite sizing per AS 1288
# Appendix F (wind load) and the dead load shear formula (Section 12.11 of
# the project summary). No side effects, no Flask/UI imports.
#
# Edge-polish deduction confirmed by Michael (Section 12.12 item 6): a flat
# 2mm deduction (EDGE_POLISH_DEDUCTION_MM), all nominal thicknesses, both
# glass types. Applied via find_min_nominal_for_usable_bite() (engine/shared/
# table_4_1.py), the same usable-thickness search mechanism the faceted engine
# uses, passed joint_type=None so it always takes that function's non-mitred
# branch (usable = actual - deduction) - there is no mitre concept here.

from engine.structural_glazing.constants import (
    SIGMA_S,
    MIN_NOMINAL_THICKNESS,
    EDGE_POLISH_DEDUCTION_MM,
    GLASS_DENSITY_KG_M3,
    GRAVITY_M_S2,
    ALLOWABLE_DEAD_LOAD_STRESS_PA,
)
from engine.shared.table_4_1 import (
    TABLE_4_1_MONOLITHIC,
    TABLE_4_1_LAMINATED,
    find_min_nominal_for_usable_bite,
)
from engine.shared.results import make_structural_glazing_result

SUPPORTED_SEALED_EDGES = ('full_perimeter', 'verticals_only')


def calculate_wind_bite(pz_kpa, span_m):
    # AS 1288 Appendix F: t = 0.5 x Pz x B / sigma_s
    return 0.5 * pz_kpa * span_m / SIGMA_S


def calculate_dead_load_bite(glass_thickness_m, height_m, width_m, sealed_perimeter_m):
    # Dead load shear formula (Section 12.11): the panel's own weight,
    # carried in shear by the bonded perimeter, rather than tension from wind.
    panel_weight_n = GLASS_DENSITY_KG_M3 * GRAVITY_M_S2 * glass_thickness_m * height_m * width_m
    bite_m = panel_weight_n / (sealed_perimeter_m * ALLOWABLE_DEAD_LOAD_STRESS_PA)
    return bite_m * 1000  # metres -> mm


def apply_thickness_floor(nominal_thickness, floor=MIN_NOMINAL_THICKNESS):
    # Dow Corning structural silicone seals start at 6mm. Applies to both
    # monolithic and laminated (same policy as the faceted engine).
    if nominal_thickness is None:
        return None
    return max(nominal_thickness, floor)


def run_structural_glazing_calculation(height_m, width_m, glass_thickness_nominal_mm,
                                        pz_kpa, sealed_edges):
    """
    Main entry point: sizes the structural silicone bite for a flat,
    angle-free panel against both wind load (Appendix F) and dead load
    (Section 12.11), and looks up the governing (larger) bite against
    Table 4.1 for both monolithic and laminated glass.

    sealed_edges determines which edges are bonded and therefore which
    span/perimeter values apply:
    - 'full_perimeter': all four edges sealed. Wind span (B) is the shorter
      of width/height, per AS 1288 Appendix F's flat structural glazing
      convention; dead load is carried by the full bonded perimeter.
    - 'verticals_only': only the two vertical edges sealed. Wind spans
      horizontally between them (width); dead load is carried only by
      the two vertical edges (2 x height).

    Every return path goes through make_structural_glazing_result() - see
    Section 6.4 of the project summary.
    """
    if sealed_edges not in SUPPORTED_SEALED_EDGES:
        return make_structural_glazing_result(
            status='CONFIGURATION_OUT_OF_SCOPE',
            sealed_edges=sealed_edges,
            message=(
                f"sealed_edges '{sealed_edges}' is not supported - "
                f"expected one of {SUPPORTED_SEALED_EDGES}"
            ),
        )

    if sealed_edges == 'full_perimeter':
        # B = the span = the SHORTER of the two supported dimensions when
        # sealed on all four sides (AS 1288 Appendix F flat structural
        # glazing convention, confirmed by Sahil - not the same convention
        # as Pathway 3's Section 9 faceted-joint formula, where the larger
        # width governs). Was previously max(), inherited incorrectly from
        # that other formula's B convention - fixed here.
        wind_span_m = min(width_m, height_m)
        dead_load_perimeter_m = 2 * height_m + 2 * width_m
    else:  # 'verticals_only'
        wind_span_m = width_m
        dead_load_perimeter_m = 2 * height_m

    wind_bite_mm = calculate_wind_bite(pz_kpa, wind_span_m)

    glass_thickness_m = glass_thickness_nominal_mm / 1000
    dead_load_bite_mm = calculate_dead_load_bite(
        glass_thickness_m, height_m, width_m, dead_load_perimeter_m
    )

    governing_bite_mm = max(wind_bite_mm, dead_load_bite_mm)

    # Table 4.1 lookup against usable thickness (actual - edge-polish
    # deduction), not raw actual - see EDGE_POLISH_DEDUCTION_MM (constants.py).
    nominal_monolithic, _ = find_min_nominal_for_usable_bite(
        governing_bite_mm, TABLE_4_1_MONOLITHIC, joint_type=None,
        chamfer_mm=EDGE_POLISH_DEDUCTION_MM,
    )
    nominal_laminated, _ = find_min_nominal_for_usable_bite(
        governing_bite_mm, TABLE_4_1_LAMINATED, joint_type=None,
        chamfer_mm=EDGE_POLISH_DEDUCTION_MM,
    )

    nominal_monolithic = apply_thickness_floor(nominal_monolithic)
    nominal_laminated = apply_thickness_floor(nominal_laminated)

    common_fields = dict(
        height_m=height_m, width_m=width_m,
        glass_thickness_nominal_mm=glass_thickness_nominal_mm, pz_kpa=pz_kpa,
        sealed_edges=sealed_edges, wind_span_m=wind_span_m,
        dead_load_perimeter_m=dead_load_perimeter_m,
        wind_bite_mm=wind_bite_mm, dead_load_bite_mm=dead_load_bite_mm,
        governing_bite_mm=governing_bite_mm,
        nominal_monolithic=nominal_monolithic, nominal_laminated=nominal_laminated,
    )

    if nominal_monolithic is None and nominal_laminated is None:
        return make_structural_glazing_result(
            status='NO_COMPLIANT_THICKNESS',
            message='Required bite exceeds all available thicknesses for both monolithic and laminated glass',
            **common_fields,
        )

    return make_structural_glazing_result(status='PASS', **common_fields)
