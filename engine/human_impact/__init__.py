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
    load_table_5_4_frameless_max_area,
    load_bathroom_toughened_allowance,
    load_mistaken_doorway_exceptions,
    load_sashless_span_table,
)
from engine.shared.results import make_human_impact_result
from engine.human_impact.location_rules import (
    match_location, GRADE_A_CAPABLE_TYPES, ALL_TYPES,
)
from engine.human_impact.routes import resolve_table_and_thickness

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')

TYPE_NAMES = {
    'monolithic_annealed': 'Monolithic Annealed',
    'monolithic_heat_strengthened': 'Monolithic Heat-strengthened',
    'monolithic_toughened': 'Monolithic Toughened',
    'laminated_annealed': 'Laminated Annealed',
    'laminated_heat_strengthened': 'Laminated Heat-strengthened',
    'laminated_toughened': 'Laminated Toughened',
}

# The four annealed / heat-strengthened type ids (monolithic and laminated).
# determine_sashless() reports all four as not one of the combinations
# listed for sashless glazing.
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
        'table_5_4_max_area': load_table_5_4_frameless_max_area(os.path.join(d, 'Table_5_4_Frameless_Max_Area.csv')),
        'bathroom_toughened_allowance': load_bathroom_toughened_allowance(os.path.join(d, 'Bathroom_Toughened_Allowance.csv')),
        'mistaken_doorway': load_mistaken_doorway_exceptions(os.path.join(d, 'Mistaken_Doorway_Exceptions.csv')),
        'sashless_span': load_sashless_span_table(os.path.join(d, 'Sashless_Span_Table.csv')),
    }


NEEDS_DIMENSIONS_REASON = "daylight width and height needed to set the thickness"


def _table_5_4_largest_area(data):
    """Largest panel area (m2) the bathroom table covers."""
    return float(data['table_5_4_max_area']['max_area_m2'].max())


def _table_5_4_oversize_reason():
    return ("The panel is larger than the largest size the tool covers for "
            "this situation (bathroom glazing, partly framed or unframed). "
            "Human impact is not assessed for this configuration. The wind "
            "load result is still returned.")


def _table_5_4_thickness_for_type(data, type_id, area_m2):
    """
    Minimum thickness for a bathroom panel (partly framed / unframed) of
    the given area. Returns None when area is None - the caller must then
    say the dimensions are needed; no default thickness is assumed.

    Small monolithic toughened panels may use the thinner allowance
    thickness; everything else (and larger monolithic panels) takes the
    thinnest row of the main table that is big enough, limits inclusive.
    The caller must already have confirmed area_m2 is within the table's
    largest size.
    """
    if area_m2 is None:
        return None

    if type_id == 'monolithic_toughened':
        df_allow = data['bathroom_toughened_allowance']
        row = df_allow[df_allow['glass_type'] == 'MT'].iloc[0]
        if area_m2 <= float(row['max_area_m2']):
            return float(row['min_thickness_mm'])

    df = data['table_5_4_max_area']
    qualifying = df[df['max_area_m2'] >= area_m2]
    return float(qualifying.iloc[0]['nominal_thickness_mm'])


MONOLITHIC_ANNEALED_HS_NOT_OFFERED = (
    "Monolithic annealed and monolithic heat-strengthened glass is not "
    "offered by this tool where human impact applies."
)


def _build_types_list(allow, min_thickness_by_type, table, ok_why=None):
    """
    Builds the six-type result list shared by determine_fixed()'s
    Grade-A-required branch.

    allow: list of Grade-A type ids eligible after every matching rule's
    type filter has been intersected (a subset of GRADE_A_CAPABLE_TYPES -
    only the toughened pair when a rule demands toughened).
    min_thickness_by_type: dict of type_id -> min thickness for the
    Grade-A types in `allow` (already resolved, including the Table 5.4
    area-conditional case).
    ok_why: note shown on an allowed type whose thickness could not be
    set (e.g. dimensions missing).

    Monolithic annealed and monolithic heat-strengthened are never offered
    at a Grade A location.
    """
    types = []
    for type_id in ALL_TYPES:
        name = TYPE_NAMES[type_id]
        if type_id in GRADE_A_CAPABLE_TYPES:
            if type_id in allow:
                types.append({
                    'id': type_id, 'name': name, 'ok': True,
                    'min_thickness': min_thickness_by_type[type_id],
                    'why': ok_why if min_thickness_by_type[type_id] is None else None,
                })
            else:
                types.append({
                    'id': type_id, 'name': name, 'ok': False,
                    'min_thickness': None,
                    'why': f"not permitted under Table {table} for this configuration",
                })
        else:
            types.append({
                'id': type_id, 'name': name, 'ok': False,
                'min_thickness': None, 'why': MONOLITHIC_ANNEALED_HS_NOT_OFFERED,
            })
    return types


def _all_types_ok_no_restriction():
    return [
        {'id': t, 'name': TYPE_NAMES[t], 'ok': True, 'min_thickness': None,
         'why': None}
        for t in ALL_TYPES
    ]


def determine_fixed(ctx, data_dir=None):
    """
    Determines Grade A requirement and eligible glass types/thicknesses
    for a fixed panel or sash, per AS 1288 Section 5.

    ctx: dict of inputs - see location_rules.match_location() for the full
    field list. Also expects panel_area_m2 (used for the Table 5.4
    thickness) and panel_width_mm (carried in the ctx, not used by the
    engine).

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
    allow = set(GRADE_A_CAPABLE_TYPES)
    for tf in type_filters:
        allow &= tf
    allow = list(allow)

    panel_area_m2 = ctx.get('panel_area_m2')

    min_thickness_by_type = {}
    ok_why = None
    if table == '5.4':
        # Only the bathroom rule (partly framed / unframed) uses this table.
        if panel_area_m2 is not None and panel_area_m2 > _table_5_4_largest_area(data):
            return make_human_impact_result(
                scope=False, grade_a_required=True,
                out_of_scope_reasons=[_table_5_4_oversize_reason()],
                trail=r['trail'], notes=r['notes'], clauses=clauses,
            )
        for type_id in allow:
            table_thickness = _table_5_4_thickness_for_type(
                data, type_id, panel_area_m2,
            )
            # Other matching rules (e.g. a side panel with exposed edges)
            # can demand a thicker glass than the bathroom table does. The
            # most stringent requirement governs, so take the larger. If
            # the table figure is None (no area given) it stays None.
            if table_thickness is not None and min_thickness is not None:
                table_thickness = max(table_thickness, min_thickness)
            min_thickness_by_type[type_id] = table_thickness
        if panel_area_m2 is None:
            ok_why = NEEDS_DIMENSIONS_REASON
    else:
        for type_id in allow:
            min_thickness_by_type[type_id] = min_thickness

    types = _build_types_list(allow, min_thickness_by_type, table, ok_why=ok_why)

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
        # A louvre is made of separate blades, so the bathroom table is
        # read against the area of one blade, not the whole opening. The
        # blade size check above has already confirmed both dimensions
        # are present and within the blade limits.
        blade_area_m2 = blade_width_mm * blade_length_mm / 1_000_000
        table_thickness = _table_5_4_thickness_for_type(data, 'monolithic_toughened', blade_area_m2)
        # Other matching rules can demand a thicker glass than the
        # bathroom table does; the most stringent requirement governs, so
        # take the larger before the louvre floor is applied below.
        if table_thickness is not None and min_thickness is not None:
            table_thickness = max(table_thickness, min_thickness)
        min_thickness = table_thickness

    final_min = max(min_thickness, 5) if min_thickness is not None else 5

    types = []
    for type_id in ALL_TYPES:
        if type_id == 'monolithic_toughened':
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': True,
                'min_thickness': final_min, 'why': None,
            })
        else:
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
                'min_thickness': None,
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
                'min_thickness': float(best['min_thickness_mm']), 'why': None,
            })
            any_ok = True
        else:
            highest_span = float(type_rows['max_span_mm'].max())
            types.append({
                'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
                'min_thickness': None,
                'why': f"span exceeds {highest_span:g}mm - outside AS 1288",
            })

    for type_id in ANNEALED_HS_TYPES:
        types.append({
            'id': type_id, 'name': TYPE_NAMES[type_id], 'ok': False,
            'min_thickness': None,
            'why': "not one of the glass combinations listed for sashless glazing under Clause 5.15",
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
