# AS 1288 Glass Thickness Calculator
# engine/human_impact/__init__.py
#
# AS 1288 Section 5 (Human Impact) engine. Determines whether Grade A
# safety glass is required, and which glass types/thicknesses are
# eligible, for a fixed panel/sash, a louvre, or a sashless window.
#
# Public entry points (the only functions other code should call):
#   determine_fixed(ctx)   -> dict
#   determine_louvre(ctx)  -> dict
#   determine_sashless(span_mm) -> dict
#
# Standalone engine - engine/human_impact must never import from
# engine/wind_load, engine/silicone_bite, or engine/combined, and nothing
# in those engines imports from here. Same dependency direction as the
# rest of the project: engines don't know about faces, engines don't
# import each other.
#
# Duce Timber Windows and Doors

import os

from engine.shared.data_loader import (
    load_human_impact_table_5_4,
    load_mistaken_doorway_exceptions,
    load_sashless_span_table,
    load_door_annealed_exceptions,
)
from engine.shared.results import make_human_impact_result
from engine.human_impact.location_rules import (
    match_location, GRADE_A_TYPES, ALL_TYPES,
)
from engine.human_impact.routes import combine_alts, resolve_table_and_thickness

import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')

TYPE_NAMES = {
    'monolithic_annealed': 'Monolithic Annealed',
    'monolithic_heat_strengthened': 'Monolithic Heat-strengthened',
    'monolithic_toughened': 'Monolithic Toughened',
    'laminated_annealed': 'Laminated Annealed',
    'laminated_heat_strengthened': 'Laminated Heat-strengthened',
    'laminated_toughened': 'Laminated Toughened',
}

# Which broad glass-type id each ALL_TYPES entry belongs to, for
# combine_alts()'s single monolithic/laminated-agnostic cap dict - both
# annealed and heat-strengthened share whatever cap combine_alts() returns.
ANNEALED_HS_TYPES = [
    'monolithic_annealed', 'monolithic_heat_strengthened',
    'laminated_annealed', 'laminated_heat_strengthened',
]


def _load_data(data_dir=None):
    """
    Loads every CSV this engine needs, once. data_dir defaults to the
    project's data/ folder; callers (mainly tests) can override to point
    at a fixture directory.
    """
    d = data_dir if data_dir is not None else _DATA_DIR
    return {
        'table_5_4': load_human_impact_table_5_4(os.path.join(d, 'Table_5_4_Bathroom_Partly_Framed.csv')),
        'mistaken_doorway': load_mistaken_doorway_exceptions(os.path.join(d, 'Mistaken_Doorway_Exceptions.csv')),
        'sashless_span': load_sashless_span_table(os.path.join(d, 'Sashless_Span_Table.csv')),
        'door_annealed': load_door_annealed_exceptions(os.path.join(d, 'Door_Annealed_Exceptions.csv')),
        'side_panel_annealed': pd.read_csv(os.path.join(d, 'Side_Panel_Annealed_Exception.csv')),
        'low_level_annealed': pd.read_csv(os.path.join(d, 'Low_Level_Residential_Annealed_Exception.csv')),
    }


def _table_5_4_thickness_for_type(df_5_4, type_id, area_m2):
    """
    Table 5.4 is area-conditional per the CSV loader: monolithic_toughened
    gets the reduced thickness when area <= area_allowance_max_m2, else the
    flat min_thickness_mm. laminated_toughened has no reduced-thickness
    route in the interim placeholder data (area_allowance_max_m2 is blank)
    so it always uses the flat min_thickness_mm.
    """
    csv_type = 'MT' if type_id == 'monolithic_toughened' else 'LT'
    row = df_5_4[df_5_4['glass_type'] == csv_type].iloc[0]
    flat_min = float(row['min_thickness_mm'])
    allowance_max_area = row['area_allowance_max_m2']
    allowance_min_thickness = row['area_allowance_min_thickness_mm']

    if pd.isna(allowance_max_area) or pd.isna(allowance_min_thickness):
        return flat_min
    if area_m2 is not None and area_m2 <= float(allowance_max_area):
        return float(allowance_min_thickness)
    return flat_min


def _build_types_list(allow, min_thickness_by_type, combo, panel_area_m2, panel_width_mm, table, matches_used):
    """
    Builds the six-type result list shared by determine_fixed()'s and
    determine_louvre()'s Grade-A-required branches.

    allow: list of Grade-A type ids eligible after every matching rule's
    type filter has been intersected (monolithic_toughened and/or
    laminated_toughened).
    min_thickness_by_type: dict of type_id -> min thickness for the
    Grade-A types in `allow` (already resolved, including the Table 5.4
    area-conditional case).
    combo: combine_alts() result - None (blocked), {} (no route offered),
    or a cap dict.
    """
    types = []
    for type_id in ALL_TYPES:
        name = TYPE_NAMES[type_id]
        if type_id in GRADE_A_TYPES:
            if type_id in allow:
                types.append({
                    'id': type_id, 'name': name, 'ok': True,
                    'min_thickness': min_thickness_by_type[type_id],
                    'cap': None, 'why': None,
                })
            else:
                types.append({
                    'id': type_id, 'name': name, 'ok': False,
                    'min_thickness': None, 'cap': None,
                    'why': f"not permitted under Table {table} for this configuration",
                })
        else:
            # annealed / heat-strengthened. combine_alts() has already
            # tested every candidate band against the actual panel
            # area/width - combo is None if nothing fit (either blocked
            # outright by some rule offering no alternative at all, or no
            # band accommodated these dimensions), so no further area/
            # width re-check is needed here (see routes.combine_alts
            # docstring for the "test against actual dimensions" guard).
            if combo is None or not combo:
                reason = _annealed_blocked_reason(matches_used, panel_area_m2, panel_width_mm)
                types.append({
                    'id': type_id, 'name': name, 'ok': False,
                    'min_thickness': None, 'cap': None, 'why': reason,
                })
            else:
                types.append({
                    'id': type_id, 'name': name, 'ok': True,
                    'min_thickness': combo['min_thickness_mm'],
                    'cap': {'max_area_m2': combo['max_area_m2'], 'max_width_mm': combo['max_width_mm']},
                    'why': None,
                })
    return types


def _annealed_blocked_reason(matches, panel_area_m2, panel_width_mm):
    """
    Builds a human-readable reason for why no annealed/heat-strengthened
    route survived, distinguishing "some rule offers no alternative at
    all" from "no band's area/width accommodated this panel".
    """
    grade_a_matches = [m for m in matches if m['grade_a']]
    no_alt_clauses = [m['clause'] for m in grade_a_matches if not m['alt']]
    if no_alt_clauses:
        return (f"Grade A required with no annealed/heat-strengthened alternative "
                f"offered at all under Clause(s) {', '.join(no_alt_clauses)}")

    empty_alt_clauses = [m['clause'] for m in grade_a_matches if m['alt'] and not m['alt_rows']]
    if empty_alt_clauses:
        return (f"Clause(s) {', '.join(empty_alt_clauses)} offer an alternative in "
                f"principle but no exception band applies to this framing")

    dims = []
    if panel_area_m2 is not None:
        dims.append(f"area {panel_area_m2}m2")
    if panel_width_mm is not None:
        dims.append(f"width {panel_width_mm}mm")
    dims_str = " / ".join(dims) if dims else "these panel dimensions"
    return f"no annealed/heat-strengthened exception band accommodates {dims_str}"


def _all_types_ok_no_restriction():
    return [
        {'id': t, 'name': TYPE_NAMES[t], 'ok': True, 'min_thickness': None,
         'cap': None, 'why': None}
        for t in ALL_TYPES
    ]


def determine_fixed(ctx, data_dir=None):
    """
    Determines Grade A requirement and eligible glass types/thicknesses
    for a fixed panel or sash, per AS 1288 Section 5.

    ctx: dict of inputs - see location_rules.match_location() for the full
    field list. Also expects (for the annealed/heat-strengthened
    area/width tests): panel_area_m2, panel_width_mm.

    Returns a dict built by make_human_impact_result().
    """
    data = _load_data(data_dir)
    r = match_location(ctx, data)

    if r['oos']:
        return make_human_impact_result(
            scope=False, out_of_scope_reasons=r['oos'], trail=r['trail'],
            notes=r['notes'],
        )

    grade_a_required = any(m['grade_a'] for m in r['matches'])
    clauses = sorted({m['clause'] for m in r['matches']})

    if not grade_a_required:
        return make_human_impact_result(
            scope=True, grade_a_required=False, table=None,
            types=_all_types_ok_no_restriction(), notes=r['notes'],
            trail=r['trail'], clauses=clauses,
        )

    table, min_thickness = resolve_table_and_thickness(r['matches'])

    grade_a_matches = [m for m in r['matches'] if m['grade_a']]
    type_filters = [set(m['type_filter']) for m in grade_a_matches if m['type_filter']]
    allow = set(GRADE_A_TYPES)
    for tf in type_filters:
        allow &= tf
    allow = list(allow)

    panel_area_m2 = ctx.get('panel_area_m2')
    panel_width_mm = ctx.get('panel_width_mm')

    combo = combine_alts(r['matches'], panel_area_m2, panel_width_mm)

    min_thickness_by_type = {}
    if table == '5.4':
        for type_id in allow:
            min_thickness_by_type[type_id] = _table_5_4_thickness_for_type(
                data['table_5_4'], type_id, panel_area_m2,
            )
    else:
        for type_id in allow:
            min_thickness_by_type[type_id] = min_thickness

    types = _build_types_list(allow, min_thickness_by_type, combo, panel_area_m2, panel_width_mm, table, r['matches'])

    return make_human_impact_result(
        scope=True, grade_a_required=True, table=table, types=types,
        notes=r['notes'], trail=r['trail'], clauses=clauses,
    )


def determine_louvre(ctx, data_dir=None):
    """
    Determines Grade A requirement and eligible glass types/thicknesses
    for a louvre assembly, per AS 1288 Clause 5.12 (which narrows the type
    list and adds a 5mm floor, but never stands alone - see module docs
    for why resolve_table_and_thickness() is still used) plus whichever
    other Section 5 clauses match (Clause 5.4 is always skipped for
    louvres - see location_rules.py).

    ctx: same fields as determine_fixed(), plus blade_width_mm,
    blade_length_mm (the louvre blade envelope test).
    """
    ctx = dict(ctx)
    ctx['is_louvre'] = True

    data = _load_data(data_dir)
    r = match_location(ctx, data)

    if r['oos']:
        return make_human_impact_result(
            scope=False, out_of_scope_reasons=r['oos'], trail=r['trail'],
            notes=r['notes'],
        )

    grade_a_required = any(m['grade_a'] for m in r['matches'])
    clauses = sorted({m['clause'] for m in r['matches']})

    if not grade_a_required:
        types = _all_types_ok_no_restriction()
        notes = list(r['notes']) + [
            "Clause 5.12: in all other (non-Grade-A) areas, annealed glass may be used."
        ]
        return make_human_impact_result(
            scope=True, grade_a_required=False, table=None, types=types,
            notes=notes, trail=r['trail'], clauses=clauses,
        )

    blade_width_mm = ctx.get('blade_width_mm')
    blade_length_mm = ctx.get('blade_length_mm')
    envelope_ok = (blade_width_mm is not None and blade_width_mm <= 230
                   and blade_length_mm is not None and blade_length_mm <= 1000)

    if not envelope_ok:
        return make_human_impact_result(
            scope=False, grade_a_required=True,
            out_of_scope_reasons=[
                "Louvre blades larger than 230mm wide or 1000mm long fall "
                "outside the sizes tabulated in AS 1288 Clause 5.12 and "
                "require specific design. Human impact is not assessed for "
                "this configuration. The wind load result is still returned."
            ],
            trail=r['trail'], notes=r['notes'], clauses=clauses,
        )

    table, min_thickness = resolve_table_and_thickness(r['matches'])

    if table == '5.4':
        # Table 5.4's monolithic_toughened figure is area-conditional (see
        # _table_5_4_thickness_for_type) - the flat min_thickness stored on
        # the match itself is only the non-reduced ceiling, so re-resolve
        # it here the same way determine_fixed() does rather than trusting
        # resolve_table_and_thickness()'s flat max().
        panel_area_m2 = ctx.get('panel_area_m2')
        min_thickness = _table_5_4_thickness_for_type(
            data['table_5_4'], 'monolithic_toughened', panel_area_m2,
        )

    final_min = max(min_thickness, 5) if min_thickness is not None else 5

    types = []
    for type_id in ALL_TYPES:
        if type_id == 'monolithic_toughened':
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': True,
                'min_thickness': final_min, 'cap': None, 'why': None,
            })
        else:
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
                'min_thickness': None, 'cap': None,
                'why': "Clause 5.12 permits toughened only",
            })

    return make_human_impact_result(
        scope=True, grade_a_required=True, table=table, types=types,
        notes=r['notes'], trail=r['trail'], clauses=clauses,
    )


def determine_sashless(span_mm, data_dir=None):
    """
    Determines Grade A requirement and eligible glass types/thicknesses
    for a sashless window, per AS 1288 Clause 5.15. Self-contained - does
    NOT call match_location() at all (Sahil confirmed other location
    clauses add nothing here, since 5.15 already forces Grade A on its own
    with its own complete type/thickness scheme).

    TODO (next session): when this gets wired into the calculator's glass-
    type checkboxes, the resulting per-type minimum thickness must combine
    with wind load via max() - span sets a floor, wind can raise it, never
    lower it. Not implemented here since this session is engine/data only.
    """
    data = _load_data(data_dir)
    df = data['sashless_span']

    types = []
    any_ok = False
    for type_id, csv_type in (('monolithic_toughened', 'MT'), ('laminated_toughened', 'LT')):
        type_rows = df[df['glass_type'] == csv_type].sort_values('max_span_mm')
        qualifying = type_rows[type_rows['max_span_mm'] >= span_mm]
        if len(qualifying) > 0:
            best = qualifying.iloc[0]
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': True,
                'min_thickness': float(best['min_thickness_mm']), 'cap': None, 'why': None,
            })
            any_ok = True
        else:
            highest_span = float(type_rows['max_span_mm'].max())
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
                'min_thickness': None, 'cap': None,
                'why': f"span exceeds {highest_span:g}mm - outside AS 1288",
            })

    for type_id in ANNEALED_HS_TYPES:
        types.append({
            'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
            'min_thickness': None, 'cap': None,
            'why': "Clause 5.15 requires Grade A",
        })

    if not any_ok:
        return make_human_impact_result(
            scope=False,
            out_of_scope_reasons=[
                f"No combination in Clause 5.15 covers a span of {span_mm:g}mm "
                "for any permitted glass type. This configuration is outside "
                "AS 1288 as currently modelled."
            ],
        )

    return make_human_impact_result(
        scope=True, grade_a_required=True, table=None, types=types,
        clauses=['5.15'],
    )
