# AS 1288 Glass Thickness Calculator
# engine/human_impact/routes.py
#
# Reduces the list of matching AS 1288 Section 5 clauses produced by
# location_rules.match_location() into one governing table/thickness and
# one combined annealed/heat-strengthened alternative envelope, per the
# "most restrictive wins" principle used throughout this tool.
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


def _rows_band_for_thickness(alt_rows, thickness_mm):
    """
    A clause's alt_rows are tiered bands (e.g. Clause 5.2's 3-4mm/5-8mm/
    10mm+ door bands), each naming the minimum thickness at which that
    band's area/width caps start applying. A candidate thickness falls
    into the band whose min_thickness_mm is the highest one <= thickness_mm
    (the same "look up the floor beneath you" logic Table 4.1 lookups use
    elsewhere in this project). Returns that row, or None if thickness_mm
    is below every band's floor.
    """
    candidates = [row for row in alt_rows if row['min_thickness_mm'] <= thickness_mm]
    if not candidates:
        return None
    return max(candidates, key=lambda row: row['min_thickness_mm'])


def combine_alts(matches, panel_area_m2, panel_width_mm):
    """
    Combines every annealed/heat-strengthened alternative offered by every
    matching Grade-A rule into one governing thickness/area/width for the
    ACTUAL panel dimensions supplied.

    Algorithm (search upward over candidate thicknesses, since each rule's
    alt_rows are tiered bands rather than simultaneous requirements - a
    single clause like 5.2 offers three bands, 3-4mm/5-8mm/10mm+, and a
    panel need only fit inside whichever band its chosen thickness lands
    in, not all three at once):
      1. Collect every distinct min_thickness_mm across every contributing
         rule's alt_rows - these are the only candidate thicknesses worth
         testing (a thickness between two band floors behaves identically
         to the lower one, since the band it lands in doesn't change).
      2. For each candidate thickness, ascending:
         - For every matching Grade-A rule:
             - If the rule offers no alternative at all (alt=False),
               annealed is blocked outright - return None immediately
               (this doesn't depend on thickness, so it short-circuits
               before the search even starts).
             - Otherwise find that rule's own applicable band for this
               candidate thickness (_rows_band_for_thickness). If no band
               applies at this thickness, this candidate fails - move on.
             - If a band applies, it must accommodate the actual panel:
               panel_area_m2 <= band's max_area_m2 (if any) AND
               panel_width_mm <= band's max_width_mm (if any). If not,
               this candidate fails for this rule - move on to the next
               candidate thickness.
         - If every rule's band accommodates the panel at this candidate
           thickness, this is the governing thickness - return it along
           with the tightest (min) area/width cap across the rules'
           applicable bands at this thickness (for display/reporting).
      3. If no candidate thickness satisfies every rule, no annealed route
         exists for this panel - return None.

    matches: the 'matches' list from match_location() (only grade_a=True
    entries matter here).
    panel_area_m2, panel_width_mm: the actual panel's dimensions - the
    route is only offered if it genuinely fits, never displayed
    unconditionally (see module docs on the earlier-prototype bug this
    guards against).

    Returns:
      None -> no annealed/heat-strengthened route available for this
              panel (either explicitly blocked by some rule offering no
              alternative at all, or no candidate thickness fits every
              matching rule's own band for these dimensions)
      {}   -> no Grade-A rule matched at all (nothing to combine; callers
              shouldn't normally reach this - see make_human_impact_result
              callers)
      {'min_thickness_mm', 'max_area_m2', 'max_width_mm'} -> combined cap
              at the thinnest thickness that satisfies every matching
              rule, shared by monolithic and laminated annealed/heat-
              strengthened alike (the source CSVs don't currently
              distinguish monolithic vs laminated annealed bands)
    """
    grade_a_matches = [m for m in matches if m['grade_a']]

    if not grade_a_matches:
        return {}

    for m in grade_a_matches:
        if not m['alt']:
            return None

    if any(not m['alt_rows'] for m in grade_a_matches):
        # Some matching rule is alt=True in principle but loaded no usable
        # band (e.g. a partly-framed door - alt=True per Clause 5.2, but
        # bands only load when fully framed). No band exists for that
        # rule at any thickness, so no candidate can ever satisfy it.
        return None

    candidate_thicknesses = sorted({
        row['min_thickness_mm'] for m in grade_a_matches for row in m['alt_rows']
    })

    for thickness in candidate_thicknesses:
        bands = []
        for m in grade_a_matches:
            band = _rows_band_for_thickness(m['alt_rows'], thickness)
            if band is None:
                bands = None
                break
            bands.append(band)

        if bands is None:
            continue

        area_caps = [b['max_area_m2'] for b in bands if b['max_area_m2'] is not None]
        width_caps = [b['max_width_mm'] for b in bands if b['max_width_mm'] is not None]
        max_area = min(area_caps) if area_caps else None
        max_width = min(width_caps) if width_caps else None

        area_ok = max_area is None or panel_area_m2 is None or panel_area_m2 <= max_area
        width_ok = max_width is None or panel_width_mm is None or panel_width_mm <= max_width

        if area_ok and width_ok:
            return {
                'min_thickness_mm': thickness,
                'max_area_m2': max_area,
                'max_width_mm': max_width,
            }

    return None
