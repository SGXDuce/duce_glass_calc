# AS 1288 Glass Thickness Calculator
# engine/silicone_bite/constants.py
#
# Reference data for structural silicone bite thickness sizing per AS 1288
# Section 9 / Appendix F.

# Table 4.1 minimum actual thickness (mm) per nominal thickness (mm).
# Monolithic floors at 4mm per company policy - no 3mm.
TABLE_4_1_MONOLITHIC = {4: 3.8, 5: 4.8, 6: 5.8, 8: 7.7, 10: 9.7, 12: 11.7, 15: 14.5, 19: 18, 25: 23.5}
TABLE_4_1_LAMINATED = {5: 4.6, 6: 5.6, 8: 7.6, 10: 9.6, 12: 11.6, 16: 15.4, 20: 19.4, 24: 23.4}

SIGMA_S = 0.21  # Ultimate limit stress in silicone, MPa (AS 1288 Appendix F / Section 9)
MIN_NOMINAL_THICKNESS = 6  # Dow Corning seal minimum, applies to both monolithic and laminated

CHAMFER_ALLOWANCE_MM = 2  # mm, applies to all nominal thicknesses >= 6mm.
# Below 6mm the chamfer is smaller, but this engine floors at 6mm nominal
# (MIN_NOMINAL_THICKNESS), so those values are never reached.
# Confirmed as a flat 2mm for both monolithic and laminated from 6mm onwards.
