# AS 1288 Glass Thickness Calculator
# engine/human_impact/location_rules.py
#
# AS 1288 Section 5 (Human Impact) location rule matching. Shared by
# determine_fixed() and determine_louvre() - see package __init__.py.
# This module owns the actual clause-by-clause logic; resolve_table_and_thickness()
# in routes.py then reduces the list of matches this produces into one
# governing table and thickness.
#
# Standalone engine - engine/human_impact must never import from
# engine/wind_load, engine/silicone_bite, or engine/combined, and nothing
# in those engines imports from here. Same dependency direction as the
# rest of the project: engines don't know about faces, engines don't
# import each other.
#
# Duce Timber Windows and Doors

# Glass type ids that count as Grade A safety glass in their own right.
# Toughened glass qualifies because of how it breaks; laminated glass
# qualifies whatever its ply type, because the interlayer holds the broken
# pieces in place - so laminated annealed and laminated heat-strengthened
# belong here alongside the two toughened types. Monolithic annealed and
# monolithic heat-strengthened are never offered where human impact applies
# (decision, 15 Oct 2026), so they are not in this list.
GRADE_A_CAPABLE_TYPES = [
    'monolithic_toughened', 'laminated_annealed',
    'laminated_heat_strengthened', 'laminated_toughened',
]

# The narrower set some rules demand: toughened specifically, not just any
# Grade A glass. Used as the type_filter on those rules, so intersecting it
# with GRADE_A_CAPABLE_TYPES drops laminated annealed/heat-strengthened.
TOUGHENED_TYPES = ['monolithic_toughened', 'laminated_toughened']

# All six glass type ids this engine ever reports on.
ALL_TYPES = [
    'monolithic_annealed', 'monolithic_heat_strengthened', 'monolithic_toughened',
    'laminated_annealed', 'laminated_heat_strengthened', 'laminated_toughened',
]

VANITY_EXEMPTION_NOTE = (
    "AS 1288 provides a limited exemption where a fixed vanity or bench of "
    "specified minimum dimensions sits in front of the glazing. This tool "
    "does not assess that exemption. If you determine it applies, refer to "
    "AS 1288 Clause 5.8 and use the override to record that safety glass is "
    "not required."
)

HIGH_RISK_NOTE = (
    "AS 1288 provides an exemption where the glazing is protected by a "
    "permanent barrier. This tool does not assess whether a barrier removes "
    "the risk of human impact. If you determine the exemption applies, "
    "refer to AS 1288 and use the override to record that safety glass is "
    "not required."
)

LOW_LEVEL_OOS_MESSAGE = (
    "Low-level residential glazing in a window that is not fully framed is "
    "not assessed by this tool. AS 1288 Clause 5.5 does impose a "
    "requirement here - assess it separately."
)

# Closing sentence on every Grade A trail line. Where human impact applies
# this tool never offers monolithic annealed or monolithic heat-strengthened.
NOT_OFFERED_SENTENCE = (
    "Monolithic annealed and monolithic heat-strengthened are not offered by this tool."
)

LOUVRE_54_SKIP_NOTE = (
    "Louvres are never assessed against Clause 5.4 - a louvre assembly "
    "cannot present as a solid doorway or opening."
)


def _match(clause, grade_a, table=None, type_filter=None, min_thickness=None):
    """
    One matching rule's contribution. type_filter is a list of glass type
    ids this rule restricts eligibility to (None = no restriction).
    """
    return {
        'clause': clause,
        'grade_a': grade_a,
        'table': table,
        'type_filter': type_filter,
        'min_thickness': min_thickness,
    }


def match_location(ctx, data):
    """
    Runs every AS 1288 Section 5 location clause against ctx and returns:
      {
        "matches": [...],  # list of _match() dicts, grade_a True or False
        "oos": [...],       # list of out-of-scope reason strings
        "notes": [...],     # informational, non-blocking notes
        "trail": [...],     # ordered human-readable audit trail
      }

    ctx['is_sashless'] (default False) skips Clause 5.5 and records that in
    the trail; it changes nothing else.

    data: dict of preloaded DataFrames, keyed
      'mistaken_doorway'
    (callers load these once via engine/shared/data_loader.py and pass
    them in - this function does no file I/O itself).
    """
    matches = []
    oos = []
    notes = []
    trail = []

    opening_type = ctx['opening_type']
    is_side_panel = ctx.get('is_side_panel', False)
    is_louvre = ctx.get('is_louvre', False)
    building_use = ctx.get('building_use', 'other')
    is_bathroom = ctx.get('is_bathroom', False)
    high_risk = ctx.get('high_risk', False)
    framing = ctx['framing']
    sight_width_mm = ctx.get('sight_width_mm')
    sight_height_mm = ctx.get('sight_height_mm')
    sightline_mm = ctx.get('sightline_mm')
    opaque_or_patterned = ctx.get('opaque_or_patterned', False)
    rail_present = ctx.get('rail_present', False)
    rail_upper_edge_mm = ctx.get('rail_upper_edge_mm')
    rail_lower_edge_mm = ctx.get('rail_lower_edge_mm')
    level_difference_mm = ctx.get('level_difference_mm')

    bathroom_triggered = is_bathroom and sightline_mm is not None and sightline_mm <= 2000

    # --- Bathroom (Clause 5.8) ---
    if bathroom_triggered:
        if framing == 'fully':
            matches.append(_match('5.8', grade_a=True, table='5.1'))
            trail.append("Clause 5.8 (bathroom, fully framed, sightline <=2000mm): "
                          "Grade A required, Table 5.1. " + NOT_OFFERED_SENTENCE)
        else:
            # No fixed thickness here: the thickness depends on panel area
            # and glass type, so the engine works it out per type from the
            # supplied dimensions (see human_impact/__init__.py). Leaving
            # it None also stops a made-up default leaking into the
            # "most restrictive wins" comparison.
            matches.append(_match(
                '5.8', grade_a=True, table='5.4',
                type_filter=TOUGHENED_TYPES,
                min_thickness=None,
            ))
            trail.append("Clause 5.8 (bathroom, partly/unframed, sightline <=2000mm): "
                          "Grade A required, Table 5.4, types restricted to "
                          "monolithic/laminated toughened. " + NOT_OFFERED_SENTENCE)
        notes.append(VANITY_EXEMPTION_NOTE)
    elif is_bathroom:
        if sightline_mm is None:
            trail.append("Clause 5.8 (bathroom) could not be checked - sightline not "
                          "provided, so the 2000mm trigger was not tested.")
        else:
            trail.append("Clause 5.8 (bathroom) considered but "
                          f"sightline {sightline_mm}mm is above the 2000mm trigger - not matched.")

    # --- Doors (Clause 5.2) --- only when not bathroom-triggered
    if opening_type == 'door' and not bathroom_triggered:
        if framing == 'unframed':
            matches.append(_match(
                '5.2', grade_a=True, table='5.1',
                type_filter=TOUGHENED_TYPES,
                min_thickness=10,
            ))
            trail.append("Clause 5.2 (unframed door): Grade A required, Table 5.1, "
                          "types restricted to monolithic/laminated toughened at "
                          "10mm minimum. This type restriction governs regardless "
                          "of what any other matching clause (e.g. school/aged-care) "
                          "would otherwise permit - most-restrictive-wins, this is "
                          "correct behaviour, not a bug. " + NOT_OFFERED_SENTENCE)
        else:
            matches.append(_match('5.2', grade_a=True, table='5.1'))
            trail.append(
                f"Clause 5.2 ({framing} framed door): Grade A required, Table 5.1, "
                "no type filter. " + NOT_OFFERED_SENTENCE
            )

    # --- Side panels (Clause 5.3.1) ---
    if is_side_panel:
        if framing == 'fully':
            matches.append(_match('5.3.1', grade_a=True, table='5.1'))
            trail.append("Clause 5.3.1 (fully framed side panel): Grade A required, "
                          "Table 5.1. " + NOT_OFFERED_SENTENCE)
        else:
            exposed_edges = ctx.get('exposed_edges')
            if exposed_edges == 'y':
                matches.append(_match(
                    '5.3.1', grade_a=True, table='5.3',
                    type_filter=TOUGHENED_TYPES,
                    min_thickness=10,
                ))
                trail.append("Clause 5.3.1 (partly/unframed side panel, exposed edges): "
                              "Grade A required, Table 5.3, types restricted to "
                              "monolithic/laminated toughened at 10mm minimum. " + NOT_OFFERED_SENTENCE)
            else:
                matches.append(_match('5.3.1', grade_a=True, table='5.3'))
                trail.append("Clause 5.3.1 (partly/unframed side panel, no exposed "
                              "edges): Grade A required, Table 5.3, no type filter. "
                              + NOT_OFFERED_SENTENCE)

    # --- Mistaken for a doorway (Clause 5.4) ---
    if opening_type == 'window' and not is_side_panel:
        if is_louvre:
            trail.append(LOUVRE_54_SKIP_NOTE)
        else:
            exempted, reason = _check_mistaken_doorway_exceptions(
                data['mistaken_doorway'], sight_width_mm, sight_height_mm,
                sightline_mm, opaque_or_patterned, rail_present,
                rail_upper_edge_mm, rail_lower_edge_mm, level_difference_mm,
            )
            if exempted:
                trail.append(f"Clause 5.4 (mistaken for a doorway): exempt - {reason}")
            else:
                table_54 = '5.1' if framing == 'fully' else '5.3'
                matches.append(_match('5.4', grade_a=True, table=table_54))
                trail.append(f"Clause 5.4 (mistaken for a doorway): no exception "
                              f"satisfied ({reason}) - Grade A required, Table {table_54}, "
                              f"no type filter. " + NOT_OFFERED_SENTENCE)

    # --- Low-level residential (Clause 5.5) ---
    # Sashless glazing skips this clause entirely (Duce interpretation).
    is_sashless = ctx.get('is_sashless', False)
    low_level_triggered = (building_use == 'residential' and sightline_mm is not None
                            and sightline_mm < 500 and opening_type != 'door')
    if is_sashless:
        trail.append("Clause 5.5 (low-level residential) is not applied to sashless "
                      "glazing (Duce interpretation, less conservative than the printed clause).")
    elif low_level_triggered:
        if is_side_panel:
            if framing == 'fully':
                matches.append(_match('5.5', grade_a=True, table='5.1'))
            trail.append("Low-level glazing (below 500mm) - also a side panel, so "
                          "Clause 5.3.1 governs and Clause 5.5 adds nothing further.")
        else:
            if framing == 'fully':
                matches.append(_match('5.5', grade_a=True, table='5.1'))
                trail.append("Clause 5.5 (low-level residential window, fully framed): "
                              "Grade A required, Table 5.1. " + NOT_OFFERED_SENTENCE)
            else:
                oos.append(LOW_LEVEL_OOS_MESSAGE)
                trail.append("Clause 5.5 (low-level residential window, not fully "
                              "framed): OUT OF SCOPE - open AGWA question, not assessed.")

    # --- Schools and early childhood centres (Clause 5.10.2) ---
    if building_use == 'school' and ((sightline_mm is not None and sightline_mm <= 1000)
                                       or opening_type == 'door'):
        table_school = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.10.2', grade_a=True, table=table_school))
        trail.append(f"Clause 5.10.2 (school/early childhood): Grade A required, "
                      f"Table {table_school}, no type filter. " + NOT_OFFERED_SENTENCE)

    # --- Aged care and nursing homes (Clause 5.10.3) ---
    if building_use == 'aged' and ((sightline_mm is not None and sightline_mm <= 1500)
                                     or opening_type == 'door'):
        table_aged = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.10.3', grade_a=True, table=table_aged))
        trail.append(f"Clause 5.10.3 (aged care/nursing home): Grade A required, "
                      f"Table {table_aged}, no type filter. " + NOT_OFFERED_SENTENCE)

    # --- High risk of breakage (Clause 5.24) ---
    if high_risk:
        table_hr = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.24', grade_a=True, table=table_hr))
        trail.append(f"Clause 5.24 (high risk of breakage): Grade A required, "
                      f"Table {table_hr}, no type filter. " + NOT_OFFERED_SENTENCE)
        notes.append(HIGH_RISK_NOTE)

    return {
        'matches': matches,
        'oos': oos,
        'notes': notes,
        'trail': trail,
    }


def _check_mistaken_doorway_exceptions(df, sight_width_mm, sight_height_mm,
                                        sightline_mm, opaque_or_patterned,
                                        rail_present, rail_upper_edge_mm,
                                        rail_lower_edge_mm, level_difference_mm):
    """
    Evaluates the Clause 5.4 exception rows against ctx values. Rows 5/6
    (rail/transom) are only tested if rail_present is True, and are
    satisfied by EITHER row alone (OR, not AND). Returns (exempted: bool,
    reason: str).
    """
    rows = {int(r['exception_id']): r for _, r in df.iterrows()}

    if sight_width_mm is not None and sight_width_mm <= float(rows[1]['threshold']):
        return True, f"sight width {sight_width_mm}mm <= {rows[1]['threshold']}mm ({rows[1]['notes_plain']})"

    if sight_height_mm is not None and sight_height_mm <= float(rows[2]['threshold']):
        return True, f"sight height {sight_height_mm}mm <= {rows[2]['threshold']}mm ({rows[2]['notes_plain']})"

    if sightline_mm is not None and sightline_mm >= float(rows[3]['threshold']):
        return True, f"sightline {sightline_mm}mm >= {rows[3]['threshold']}mm ({rows[3]['notes_plain']})"

    if opaque_or_patterned:
        return True, f"opaque or patterned glazing ({rows[4]['notes_plain']})"

    if rail_present:
        upper_ok = rail_upper_edge_mm is not None and rail_upper_edge_mm >= float(rows[5]['threshold'])
        lower_ok = rail_lower_edge_mm is not None and rail_lower_edge_mm <= float(rows[6]['threshold'])
        if upper_ok or lower_ok:
            which = "upper edge test" if upper_ok else "lower edge test"
            return True, f"crash/chair rail or transom present, satisfies the {which}"

    if level_difference_mm is not None and level_difference_mm >= float(rows[7]['threshold']):
        return True, f"protects a level difference of {level_difference_mm}mm ({rows[7]['notes_plain']})"

    return False, "no Clause 5.4 exception satisfied"
