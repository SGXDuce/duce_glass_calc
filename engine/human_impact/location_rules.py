# AS 1288 Glass Thickness Calculator
# engine/human_impact/location_rules.py
#
# AS 1288 Section 5 (Human Impact) location rule matching. Shared by
# determine_fixed() and determine_louvre() - see package __init__.py.
# This module owns the actual clause-by-clause logic; combine_alts() and
# resolve_table_and_thickness() in routes.py then reduce the list of
# matches this produces into one governing answer.
#
# Standalone engine - engine/human_impact must never import from
# engine/wind_load, engine/silicone_bite, or engine/combined, and nothing
# in those engines imports from here. Same dependency direction as the
# rest of the project: engines don't know about faces, engines don't
# import each other.
#
# Duce Timber Windows and Doors

import pandas as pd

# Grade-A-eligible glass type ids used throughout this engine.
GRADE_A_TYPES = ['monolithic_toughened', 'laminated_toughened']

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

LOUVRE_54_SKIP_NOTE = (
    "Louvres are never assessed against Clause 5.4 - a louvre assembly "
    "cannot present as a solid doorway or opening."
)


def _match(clause, grade_a, table=None, type_filter=None, min_thickness=None,
           alt=False, alt_rows=None, alt_source=None):
    """
    One matching rule's contribution. type_filter is a list of glass type
    ids this rule restricts eligibility to (None = no restriction). alt
    marks whether this rule offers an annealed/heat-strengthened
    alternative at all; alt_rows carries the actual exception band rows
    (already normalised to dicts with min_thickness_mm/max_area_m2/
    max_width_mm) when alt is True and rows were loaded. alt_source names
    which CSV/clause the alt rows came from, for trail/why messages.
    """
    return {
        'clause': clause,
        'grade_a': grade_a,
        'table': table,
        'type_filter': type_filter,
        'min_thickness': min_thickness,
        'alt': alt,
        'alt_rows': alt_rows if alt_rows is not None else [],
        'alt_source': alt_source,
    }


def match_location(ctx, data):
    """
    Runs every AS 1288 Section 5 location clause against ctx and returns:
      {
        "matches": [...],  # list of _match() dicts, grade_a True or False
        "alts": [],         # reserved for future non-rule-attached alt
                             # sources; currently every alt route travels
                             # on its owning match's alt_rows, so this is
                             # always empty - combine_alts() reads alt_rows
                             # off matches directly. Kept in the return
                             # shape per the spec's documented contract.
        "oos": [...],       # list of out-of-scope reason strings
        "notes": [...],     # informational, non-blocking notes
        "trail": [...],     # ordered human-readable audit trail
      }

    data: dict of preloaded DataFrames, keyed
      'table_5_4', 'mistaken_doorway', 'door_annealed',
      'side_panel_annealed', 'low_level_annealed'
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
            matches.append(_match('5.8', grade_a=True, table='5.1', alt=False))
            trail.append("Clause 5.8 (bathroom, fully framed, sightline <=2000mm): "
                          "Grade A required, Table 5.1, no alternative offered.")
        else:
            df_5_4 = data['table_5_4']
            mt_min = float(df_5_4[df_5_4['glass_type'] == 'MT']['min_thickness_mm'].iloc[0])
            matches.append(_match(
                '5.8', grade_a=True, table='5.4',
                type_filter=['monolithic_toughened', 'laminated_toughened'],
                min_thickness=mt_min, alt=False,
            ))
            trail.append("Clause 5.8 (bathroom, partly/unframed, sightline <=2000mm): "
                          "Grade A required, Table 5.4, types restricted to "
                          "monolithic/laminated toughened.")
        notes.append(VANITY_EXEMPTION_NOTE)
    elif is_bathroom:
        trail.append("Clause 5.8 (bathroom) considered but sightline "
                      f"{sightline_mm}mm is above the 2000mm trigger - not matched.")

    # --- Doors (Clause 5.2) --- only when not bathroom-triggered
    if opening_type == 'door' and not bathroom_triggered:
        if framing == 'unframed':
            matches.append(_match(
                '5.2', grade_a=True, table='5.1',
                type_filter=['monolithic_toughened', 'laminated_toughened'],
                min_thickness=10, alt=False,
            ))
            trail.append("Clause 5.2 (unframed door): Grade A required, Table 5.1, "
                          "types restricted to monolithic/laminated toughened at "
                          "10mm minimum. This type restriction governs regardless "
                          "of what any other matching clause (e.g. school/aged-care) "
                          "would otherwise permit - most-restrictive-wins, this is "
                          "correct behaviour, not a bug.")
        else:
            alt_rows = []
            if framing == 'fully':
                df_door = data['door_annealed']
                for _, row in df_door.iterrows():
                    alt_rows.append({
                        'min_thickness_mm': float(row['min_thickness_mm']),
                        'max_area_m2': None if pd.isna(row['max_area_m2']) else float(row['max_area_m2']),
                        'max_width_mm': None if pd.isna(row['max_width_mm']) else float(row['max_width_mm']),
                        'notes_plain': row['notes_plain'],
                    })
            matches.append(_match(
                '5.2', grade_a=True, table='5.1', alt=True,
                alt_rows=alt_rows, alt_source='Door_Annealed_Exceptions.csv',
            ))
            trail.append(
                f"Clause 5.2 ({framing} framed door): Grade A required, Table 5.1, "
                f"alternative offered={'yes, ' + str(len(alt_rows)) + ' band(s) loaded' if alt_rows else 'no (not fully framed)' if framing != 'fully' else 'yes but no bands loaded'}."
            )

    # --- Side panels (Clause 5.3.1) ---
    if is_side_panel:
        if framing == 'fully':
            df_sp = data['side_panel_annealed']
            row = df_sp.iloc[0]
            alt_rows = [{
                'min_thickness_mm': float(row['min_thickness_mm']),
                'max_area_m2': float(row['max_area_m2']),
                'max_width_mm': None,
                'notes_plain': row['notes_plain'],
            }]
            matches.append(_match(
                '5.3.1', grade_a=True, table='5.1', alt=True,
                alt_rows=alt_rows, alt_source='Side_Panel_Annealed_Exception.csv',
            ))
            trail.append("Clause 5.3.1 (fully framed side panel): Grade A required, "
                          "Table 5.1, annealed/heat-strengthened alternative up to "
                          f"{alt_rows[0]['max_area_m2']}m2 at {alt_rows[0]['min_thickness_mm']}mm offered.")
        else:
            exposed_edges = ctx.get('exposed_edges')
            if exposed_edges == 'y':
                matches.append(_match(
                    '5.3.1', grade_a=True, table='5.3',
                    type_filter=['monolithic_toughened', 'laminated_toughened'],
                    min_thickness=10, alt=False,
                ))
                trail.append("Clause 5.3.1 (partly/unframed side panel, exposed edges): "
                              "Grade A required, Table 5.3, types restricted to "
                              "monolithic/laminated toughened at 10mm minimum, no alternative.")
            else:
                matches.append(_match('5.3.1', grade_a=True, table='5.3', alt=False))
                trail.append("Clause 5.3.1 (partly/unframed side panel, no exposed "
                              "edges): Grade A required, Table 5.3, no type filter, "
                              "no alternative.")

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
                matches.append(_match('5.4', grade_a=True, table=table_54, alt=False))
                trail.append(f"Clause 5.4 (mistaken for a doorway): no exception "
                              f"satisfied ({reason}) - Grade A required, Table {table_54}, "
                              f"no type filter, no alternative.")

    # --- Low-level residential (Clause 5.5) ---
    low_level_triggered = (building_use == 'residential' and sightline_mm is not None
                            and sightline_mm < 500 and opening_type != 'door')
    if low_level_triggered:
        if is_side_panel:
            if framing == 'fully':
                df_ll = data['low_level_annealed']
                row = df_ll.iloc[0]
                alt_rows = [{
                    'min_thickness_mm': float(row['min_thickness_mm']),
                    'max_area_m2': float(row['max_area_m2']),
                    'max_width_mm': None,
                    'notes_plain': row['notes_plain'],
                }]
                matches.append(_match(
                    '5.5', grade_a=True, table='5.1', alt=True,
                    alt_rows=alt_rows, alt_source='Low_Level_Residential_Annealed_Exception.csv',
                ))
            trail.append("Low-level glazing (below 500mm) - also a side panel, so "
                          "Clause 5.3.1 governs and Clause 5.5 adds nothing further.")
        else:
            if framing == 'fully':
                df_ll = data['low_level_annealed']
                row = df_ll.iloc[0]
                alt_rows = [{
                    'min_thickness_mm': float(row['min_thickness_mm']),
                    'max_area_m2': float(row['max_area_m2']),
                    'max_width_mm': None,
                    'notes_plain': row['notes_plain'],
                }]
                matches.append(_match(
                    '5.5', grade_a=True, table='5.1', alt=True,
                    alt_rows=alt_rows, alt_source='Low_Level_Residential_Annealed_Exception.csv',
                ))
                trail.append("Clause 5.5 (low-level residential window, fully framed): "
                              "Grade A required, Table 5.1, annealed/heat-strengthened "
                              f"alternative up to {alt_rows[0]['max_area_m2']}m2 at "
                              f"{alt_rows[0]['min_thickness_mm']}mm offered.")
            else:
                oos.append(LOW_LEVEL_OOS_MESSAGE)
                trail.append("Clause 5.5 (low-level residential window, not fully "
                              "framed): OUT OF SCOPE - open AGWA question, not assessed.")

    # --- Schools and early childhood centres (Clause 5.10.2) ---
    if building_use == 'school' and ((sightline_mm is not None and sightline_mm <= 1000)
                                       or opening_type == 'door'):
        table_school = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.10.2', grade_a=True, table=table_school, alt=False))
        trail.append(f"Clause 5.10.2 (school/early childhood): Grade A required, "
                      f"Table {table_school}, no type filter, no alternative.")

    # --- Aged care and nursing homes (Clause 5.10.3) ---
    if building_use == 'aged' and ((sightline_mm is not None and sightline_mm <= 1500)
                                     or opening_type == 'door'):
        table_aged = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.10.3', grade_a=True, table=table_aged, alt=False))
        trail.append(f"Clause 5.10.3 (aged care/nursing home): Grade A required, "
                      f"Table {table_aged}, no type filter, no alternative.")

    # --- High risk of breakage (Clause 5.24) ---
    if high_risk:
        table_hr = '5.1' if framing == 'fully' else '5.3'
        matches.append(_match('5.24', grade_a=True, table=table_hr, alt=False))
        trail.append(f"Clause 5.24 (high risk of breakage): Grade A required, "
                      f"Table {table_hr}, no type filter, no alternative.")
        notes.append(HIGH_RISK_NOTE)

    return {
        'matches': matches,
        'alts': [],
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
