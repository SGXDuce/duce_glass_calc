# AS 1288 Glass Thickness Calculator
# engine/structural_glazing/constants.py
#
# Reference data for flat, angle-free structural glazing bite sizing per
# AS 1288 Appendix F (wind load) and the dead load shear formula
# (Section 12.11 of the project summary).

SIGMA_S = 0.21  # Ultimate limit stress in silicone, MPa (AS 1288 Appendix F)
MIN_NOMINAL_THICKNESS = 6  # Dow Corning seal minimum, applies to both monolithic and laminated

EDGE_POLISH_DEDUCTION_MM = 2  # Flat deduction for edge polishing on frame-bonded
# (flat, angle-free) glazing, confirmed by Michael (Section 12.12 item 6). Applies
# to all nominal thicknesses, both monolithic and laminated, at the Table 4.1
# comparison step. Deliberately NOT the same named constant as
# CHAMFER_ALLOWANCE_MM (engine/shared/table_4_1.py) even though the value is
# identical - that constant exists because silicone bonds to the cut edge itself
# (the bonding surface IS the through-thickness dimension) in the faceted engine.
# Here silicone bonds to the flat glass face; the deduction instead accounts for
# the perimeter edge-polish treatment reducing usable contact thickness. Same
# number, different physical justification - kept as separate named constants
# so the code doesn't misrepresent why either number exists.

GLASS_DENSITY_KG_M3 = 2500  # Specific mass of float glass, consistent across
# annealed, toughened, heat-strengthened, and laminated (Section 12.11)
GRAVITY_M_S2 = 9.81
ALLOWABLE_DEAD_LOAD_STRESS_PA = 7000  # Max allowable sustained (dead load)
# design stress for DOWSIL 983/993N/795/995 structural sealants - far lower
# than the wind load allowable (210,000 Pa) because dead load is permanent
# and sustained, and silicone creeps under sustained stress.
