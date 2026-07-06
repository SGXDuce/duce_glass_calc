# AS 1288 Glass Thickness Calculator
# engine/silicone_bite/constants.py
#
# Reference data for structural silicone bite thickness sizing per AS 1288
# Section 9 / Appendix F.
#
# Table 4.1 data, the chamfer allowance, and the raw/usable-bite lookup
# helpers now live in engine/shared/table_4_1.py (shared with
# engine/structural_glazing/) - see formulas.py for the import.

SIGMA_S = 0.21  # Ultimate limit stress in silicone, MPa (AS 1288 Appendix F / Section 9)
MIN_NOMINAL_THICKNESS = 6  # Dow Corning seal minimum, applies to both monolithic and laminated
