import pandas as pd
GLASS_TYPE_THICKNESSES = {
    ('Monolithic', 'Annealed'):           [4, 5, 6, 8, 10, 12, 15, 19, 25],
    ('Monolithic', 'Toughened'):          [4, 5, 6, 8, 10, 12, 15, 19, 25],
    ('Monolithic', 'Heat-strengthened'):  [3, 4, 5, 6, 8, 10, 12],
    ('Laminated',  'Annealed'):           [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Heat-strengthened'):  [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Toughened'):          [5, 6, 8, 10, 12, 16, 20, 24],
}
SAFETY_GLASS_AREA_CAT1 = {
    3:  1.0,
    4:  2.0,
    5:  3.0,
    6:  4.0,
    8:  6.0,
    10: 8.0,
    12: 10.0,
}
SAFETY_GLASS_AREA_CAT2 = {
    5:  2.2,
    6:  3.0,
    8:  5.0,
    10: 7.0,
    12: 9.0,
}
SAFETY_GLASS_CATEGORY = {
    ('Monolithic', 'Toughened'):          'cat1',
    ('Laminated',  'Toughened'):          'cat1',
    ('Laminated',  'Annealed'):           'cat2',
    ('Laminated',  'Heat-strengthened'):  'cat2',
}

# Glass types ineligible for safety glass
SAFETY_GLASS_INELIGIBLE = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Heat-strengthened'),
]

MONOLITHIC_TOUGHENED_ONLY = [('Monolithic', 'Toughened')]

BAL_RULES = {
    ('12.5', 'Window'): {
        'min_thickness': None,
        'eligible_types': None,
        'conditional_note': 'Glass within 400mm of ground, or another '
                             'structure within 18 degrees of horizontal, '
                             'must be safety glass, minimum 4mm.'
    },
    ('12.5', 'Door'): {
        'min_thickness': 4,
        'eligible_types': SAFETY_GLASS_CATEGORY,  # placeholder, replaced below
        'conditional_note': None
    },
    ('19', 'Window'): {
        'min_thickness': None,
        'eligible_types': None,
        'conditional_note': 'Glass within 400mm of ground, or another '
                             'structure within 18 degrees of horizontal, '
                             'must be Monolithic Toughened, minimum 5mm.'
    },
    ('19', 'Door'): {
        'min_thickness': 5,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
    ('29', 'Window'): {
        'min_thickness': 5,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
    ('29', 'Door'): {
        'min_thickness': 6,
        'eligible_types': MONOLITHIC_TOUGHENED_ONLY,
        'conditional_note': None
    },
}
BAL_RULES[('12.5', 'Door')]['eligible_types'] = list(SAFETY_GLASS_CATEGORY.keys())

C1_FACTORS = {
    ('Laminated', 'Annealed'):          1.0,
    ('Laminated', 'Heat-strengthened'): 1.6,
    ('Laminated', 'Toughened'):         2.5,
}


TABLE_AR_VALUES = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 5.0]

# ---------------------------------------------------------------------------
# TABLE 5.3 (unframed side edges / partly framed glazing) - a human impact
# check for 2-edge and 3-edge support conditions ONLY. Table 5.3 replaces
# Table 5.1 (the Safety Glass Area Check above) entirely in this branch -
# see Section 14.2 of the project summary. It never runs for 4-edge.
# ---------------------------------------------------------------------------

# Maps this engine's (glass_type, glass_subtype) tuples onto the glass type
# strings used as row keys in data/Table_5_3.csv. Confirmed directly against
# the live CSV (not assumed from prose): the CSV's own column value is
# 'Heat Strengthened' (space, capital S, no hyphen) - a real mismatch trap
# against this engine's 'Heat-strengthened'. Laminated Toughened maps to the
# literal string 'Laminated Toughened', which check_table_5_3() itself
# further redirects to the Toughened rows per Table 5.3 Note 2 (see
# engine/shared/table_5_3.py's GLASS_TYPE_LOOKUP_OVERRIDES).
TABLE_5_3_GLASS_TYPE_MAP = {
    ('Monolithic', 'Annealed'):          'Annealed',
    ('Monolithic', 'Heat-strengthened'): 'Heat Strengthened',
    ('Monolithic', 'Toughened'):         'Toughened',
    ('Laminated',  'Annealed'):          'Laminated',
    ('Laminated',  'Heat-strengthened'): 'Laminated',
    ('Laminated',  'Toughened'):         'Laminated Toughened',
}

# 3-edge is treated as 2-edge for wind load bending (Section 4 / Section
# 14.2) - the wind_load engine's own support_condition parameter never
# carries a '3-edge' value. Table 5.3's "maximum vertical butt joints"
# column distinguishes them for human impact instead: 2-edge = 2 unframed
# vertical edges = 2 joints, 3-edge = 1 unframed vertical edge = 1 joint.
UNFRAMED_EDGE_JOINT_COUNTS = {
    '2-edge': 2,
    '3-edge': 1,
}

# Safety glass eligibility WITHIN Table 5.3 (Section 14.2 / v1.11 changelog).
# This is a separate rule from SAFETY_GLASS_INELIGIBLE above, which governs
# the Table 5.1 check (4-edge only, a different table entirely). Currently
# identical in practice, but kept as its own list since the two tables'
# eligibility rules are independent business rules that could diverge later.
TABLE_5_3_SAFETY_GLASS_INELIGIBLE = [
    ('Monolithic', 'Annealed'),
    ('Monolithic', 'Heat-strengthened'),
]

# ---------------------------------------------------------------------------
# IGU LOAD SHARING CONSTANTS (Mode 1 - equal thickness assumption)
# ---------------------------------------------------------------------------

# For Mode 1, all panes assumed equal thickness so k_pane is a fixed constant
# Single: k_pane = 1.0
# Double: k_pane = 1.25 / 2 = 0.625
# Triple: k_pane = 1.25 / 3 = 0.4167
KPANE_SINGLE = 1.0
KPANE_DOUBLE = 1.25 / 2
KPANE_TRIPLE = 1.25 / 3
