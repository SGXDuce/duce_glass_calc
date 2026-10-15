# AS 1288 Glass Thickness Calculator
# engine/human_impact/routes.py
#
# Reduces the list of matching AS 1288 Section 5 clauses produced by
# location_rules.match_location() into one governing table and minimum
# thickness, per the "most restrictive wins" principle used throughout
# this tool.
#
# Standalone engine - see location_rules.py header for the dependency
# rules this package follows.
#
# Duce Timber Windows and Doors

TABLE_PRECEDENCE = {'5.4': 3, '5.3': 2, '5.1': 1}


def resolve_table_and_thickness(matches):
    """
    Table precedence when more than one table is implicated: 5.4 beats 5.3
    beats 5.1. Minimum thickness is the max across every matching rule's
    own minimum (None entries - rules with no explicit floor - are
    ignored).

    matches: list of match dicts from location_rules.match_location()'s
    'matches' list (grade_a True entries only are meaningful here - callers
    should already have confirmed grade_a_required before calling this).

    Returns (table: str|None, min_thickness: float|None).
    """
    grade_a_matches = [m for m in matches if m['grade_a']]
    if not grade_a_matches:
        return None, None

    tables = [m['table'] for m in grade_a_matches if m['table'] is not None]
    table = None
    if tables:
        table = max(tables, key=lambda t: TABLE_PRECEDENCE.get(t, 0))

    thicknesses = [m['min_thickness'] for m in grade_a_matches if m['min_thickness'] is not None]
    min_thickness = max(thicknesses) if thicknesses else None

    return table, min_thickness
