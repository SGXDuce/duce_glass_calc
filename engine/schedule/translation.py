# AS 1288 Glass Thickness Calculator
# engine/schedule/translation.py
#
# Translates one Configurator export pane (plus its schedule row and any
# hand-supplied answers) into the ctx dict engine/human_impact expects, or
# into a sashless span for determine_sashless(). Pure geometry/derivation -
# no clause text, no table figures, no calls into the human impact engine
# itself (callers pass the result's payload into determine_fixed/
# determine_louvre/determine_sashless as they see fit).
#
# Standalone layer - must never import from engine/wind_load,
# engine/silicone_bite, or engine/combined.
#
# Duce Timber Windows and Doors

# Used only in the bar-warning message text - an unconfirmed assumption
# (see Window_Schedule_Progress_Handover.md section 11) that a slider's
# head/sill tuck-in, where one applies, is the same 20mm-per-end split as
# the confirmed sliding-window/door correction. Never fed into a
# calculation, only quoted in the warning sentence.
ASSUMED_BAR_TUCKIN_MM = 20

# Sahil: 1200mm sightline threshold for the side-panel geometry test comes
# from project notes, not checked against AS 1288 text itself - flagged
# here, not silently treated as verified.
SIDE_PANEL_SIGHTLINE_MAX_MM = 1200
SIDE_PANEL_GAP_MAX_MM = 300

SLIDER_TYPES = ('horizontal-slider', 'vertical-slider')

# The complete set of unframedEdgeReasons values this layer understands
# (configurator schema v6). Any reason not in this set is unrecognised and
# must never be treated as a held edge - see _check_known_edge_reasons().
KNOWN_EDGE_REASONS = frozenset((
    None, 'angled-joint', 'silicone-flat', 'frame-off', 'next-to-sashless',
    'sashless-free-edge',
))

_EDGE_NAMES = ('top', 'bottom', 'left', 'right')
_OPPOSITE_FREE_EDGE_PAIRS = {
    frozenset(('left', 'right')): ('top', 'bottom'),
    frozenset(('top', 'bottom')): ('left', 'right'),
}


def _edge_of_visible_glass(pane, side):
    """
    x-coordinate of the visible-glass edge on the given side ('left' or
    'right'), i.e. the sash edge stripped off the outer frame edge.
    """
    if side == 'left':
        return pane['xMM'] + pane['sashEdgesMM']['left']
    return pane['xMM'] + pane['widthMM'] - pane['sashEdgesMM']['right']


def _height_overlap(a, b):
    """True if panes a and b overlap on the vertical (yMM) axis at all."""
    a_top = a['yMM'] + a['heightMM']
    b_top = b['yMM'] + b['heightMM']
    return a['yMM'] < b_top and b['yMM'] < a_top


def _horizontal_overlap(a, b):
    """True if panes a and b overlap on the horizontal (xMM) axis at all."""
    a_right = a['xMM'] + a['widthMM']
    b_right = b['xMM'] + b['widthMM']
    return a['xMM'] < b_right and b['xMM'] < a_right


def _sightline_mm(pane, row):
    """
    sightline_mm = height of the bottom edge of the visible glass above FFL.
    Returns None if ffl_height_mm is missing (caller decides how to treat
    that - never defaulted here).

    This function never computes tuck-in itself - the Configurator export's
    yMM/heightMM already include whatever tuck-in correction applies
    upstream (see Window_Schedule_Progress_Handover.md sections 11/14).
    """
    ffl = row.get('ffl_height_mm')
    if ffl is None:
        return None
    return ffl + pane['yMM'] + pane['sashEdgesMM']['bottom']


def _slider_warnings(pane, elevation_panes, sightline_mm):
    """
    Builds the bar/vertical slider warnings for FIELD DERIVATION item 1.
    Only the pane's own bottom edge matters for sightline, so only a
    pane directly BELOW this one (in the same elevation, with positive
    horizontal overlap) can trigger the bar warning.
    """
    warnings = []
    pane_type = pane.get('type')
    if pane_type not in SLIDER_TYPES:
        return warnings

    for other in elevation_panes:
        if other is pane:
            continue
        if not _horizontal_overlap(pane, other):
            continue
        other_top = other['yMM'] + other['heightMM']
        # other pane's top edge at or below this pane's bottom edge
        # (yMM) means this pane's bottom sits on a bar, not the frame.
        if other_top <= pane['yMM']:
            warnings.append(
                "This slider's bottom edge sits on a horizontal bar. The "
                "Configurator applies no head/sill tuck-in at a bar; if one "
                "applies in reality, this sightline reads about "
                f"{ASSUMED_BAR_TUCKIN_MM}mm too high."
            )
            break

    if pane_type == 'vertical-slider':
        warnings.append(
            "Vertical slider head/sill tuck-in is confirmed present but its "
            "amount (20mm per end, reused from the horizontal slider) is "
            "not yet confirmed; the sightline may be slightly off."
        )

    return warnings


def _sight_size(pane):
    sight_width_mm = pane['widthMM'] - pane['sashEdgesMM']['left'] - pane['sashEdgesMM']['right']
    sight_height_mm = pane['heightMM'] - pane['sashEdgesMM']['top'] - pane['sashEdgesMM']['bottom']
    return sight_width_mm, sight_height_mm


def _check_known_edge_reasons(pane):
    """
    R1: fail closed on any edge reason this layer doesn't recognise. Checked
    for every pane, sashless or not, before any framing or span logic runs -
    an unrecognised reason must never be silently treated as a held edge.

    Returns an error message naming the bad edge and value, or None if every
    edge's reason is in KNOWN_EDGE_REASONS.
    """
    reasons = pane.get('unframedEdgeReasons')
    if not isinstance(reasons, dict):
        return f"pane {pane.get('id')!r}: unframedEdgeReasons is missing or not a dict"

    for edge in _EDGE_NAMES:
        if edge not in reasons:
            return f"pane {pane.get('id')!r}: edge '{edge}' has no reason entry"
        reason = reasons[edge]
        if reason is not None and not isinstance(reason, str):
            return f"pane {pane.get('id')!r}: edge '{edge}' reason {reason!r} is not a string or None"
        if reason == '':
            return f"pane {pane.get('id')!r}: edge '{edge}' reason is an empty string"
        if reason not in KNOWN_EDGE_REASONS:
            return f"pane {pane.get('id')!r}: edge '{edge}' has unrecognised reason {reason!r}"
    return None


def _sashless_free_and_held_edges(pane):
    """
    R2: a sashless pane must have exactly two 'sashless-free-edge' edges,
    and they must be opposite each other (left+right, or top+bottom) -
    those are the edges with no sash rail, where the glass is unsupported.
    The other two edges are where the glass is actually held, and both
    must have reason None (any other reason on a held edge is a
    contradiction in the export, not a case to guess through).

    Returns (free_edges, held_edges) as frozensets of edge names, or None
    if the pattern doesn't match R2.
    """
    reasons = pane['unframedEdgeReasons']
    free_edges = frozenset(
        edge for edge in _EDGE_NAMES if reasons[edge] == 'sashless-free-edge'
    )
    held_edges = _OPPOSITE_FREE_EDGE_PAIRS.get(free_edges)
    if held_edges is None:
        return None
    for edge in held_edges:
        if reasons[edge] is not None:
            return None
    return free_edges, frozenset(held_edges)


def _sashless_span_mm(pane, sight_width_mm, sight_height_mm):
    """
    R3: sashless span is the sight dimension measured between the two HELD
    edges - the distance the glass actually spans, unsupported, between the
    two edges that do hold it. Which edges are held depends on the slider's
    orientation and is read from unframedEdgeReasons, not assumed from the
    pane type.

    Returns (span_mm, error_message). error_message is set (span_mm None)
    on any R1/R2/R4 violation.
    """
    known_error = _check_known_edge_reasons(pane)
    if known_error:
        return None, known_error

    pattern = _sashless_free_and_held_edges(pane)
    if pattern is None:
        return None, (
            f"pane {pane['id']!r}: sashless pane does not have exactly two "
            "opposite 'sashless-free-edge' edges with the remaining two "
            "edges held (reason None)"
        )
    free_edges, _held_edges = pattern

    if free_edges == frozenset(('left', 'right')):
        return sight_height_mm, None
    return sight_width_mm, None


def _is_door_pane(pane, elevation_panes):
    """
    FIELD DERIVATION item 6a. A pane is a door pane if the Configurator
    already labels it productClass 'door', or (Duce interpretation, not
    literal clause text) it is a bare fixed pane immediately beside a
    'door'-labelled horizontal-slider leaf - covers a fixed light built
    into the same sliding-door assembly, which the Configurator doesn't
    itself tag as a door.
    """
    if pane.get('productClass') == 'door':
        return True

    if pane.get('type') != 'fixed':
        return False
    edges = pane['sashEdgesMM']
    if edges['top'] != 0 or edges['bottom'] != 0 or edges['left'] != 0 or edges['right'] != 0:
        return False

    for other in elevation_panes:
        if other is pane:
            continue
        if other.get('productClass') != 'door' or other.get('type') != 'horizontal-slider':
            continue
        if _height_overlap(pane, other):
            return True
    return False


def _side_panel_gap_mm(pane, door_pane):
    """
    Horizontal gap between the visible-glass edges of pane and door_pane,
    sideways only - the edge of each pane facing the other.
    """
    if pane['xMM'] >= door_pane['xMM']:
        # pane is to the right of the door
        pane_edge = _edge_of_visible_glass(pane, 'left')
        door_edge = _edge_of_visible_glass(door_pane, 'right')
    else:
        # pane is to the left of the door
        pane_edge = _edge_of_visible_glass(pane, 'right')
        door_edge = _edge_of_visible_glass(door_pane, 'left')
        return max(0.0, door_edge - pane_edge)
    return max(0.0, pane_edge - door_edge)


def _is_side_panel(pane, elevation_panes, door_panes, sightline_mm, warnings):
    """
    FIELD DERIVATION item 6b. productClass 'side-panel' wins outright (with
    a warning if geometry disagrees); otherwise geometry decides via gap,
    height overlap, and the pane's own sightline.
    """
    labelled = pane.get('productClass') == 'side-panel'

    geometry_says_side_panel = False
    if sightline_mm is not None and sightline_mm <= SIDE_PANEL_SIGHTLINE_MAX_MM:
        for door_pane in door_panes:
            if door_pane is pane:
                continue
            if not _height_overlap(pane, door_pane):
                continue
            gap = _side_panel_gap_mm(pane, door_pane)
            if gap <= SIDE_PANEL_GAP_MAX_MM:
                geometry_says_side_panel = True
                break

    if labelled and not geometry_says_side_panel:
        warnings.append(
            "Pane is labelled a side panel but its geometry doesn't match "
            "the side-panel test (gap/height-overlap/sightline) against any "
            "door pane in this elevation - treated as a side panel anyway "
            "because the Configurator's own label wins."
        )

    return labelled or geometry_says_side_panel


def _framing(pane, angle_deg, answers):
    """
    FIELD DERIVATION item 7. Returns (framing, missing, exposed_edges).
    framing is 'fully', 'partly', or 'not_assessable'. 'unframed' is never
    produced here - a genuinely all-round-unframed (3+ edge) pane falls
    into not_assessable instead, since this translation layer has no case
    for it (see Window_Schedule_Progress_Handover.md section 10).
    """
    reasons = pane['unframedEdgeReasons']
    missing = []
    not_held = []
    frame_off_present = False
    frame_off_exposed_yes = False

    for edge in _EDGE_NAMES:
        reason = reasons[edge]
        if reason is None:
            continue
        if reason == 'angled-joint':
            if angle_deg is None:
                return 'not_assessable', missing, None
            if angle_deg == 90:
                continue  # held
            not_held.append(edge)
        elif reason == 'sashless-free-edge':
            # R4: this reason only makes sense on a sashless pane. Reaching
            # here means a non-sashless pane carries it - an inconsistent
            # export, not something to guess through.
            return 'not_assessable', missing, None
        elif reason in ('silicone-flat', 'next-to-sashless', 'frame-off'):
            not_held.append(edge)
            if reason == 'frame-off':
                frame_off_present = True
                exposed = answers.get('frame_off_exposed')
                if exposed is None:
                    missing.append('frame_off_exposed')
                elif exposed == 'y':
                    frame_off_exposed_yes = True

    if missing:
        return 'needs_answer', missing, None

    exposed_edges = None
    if frame_off_present:
        exposed_edges = 'y' if frame_off_exposed_yes else 'n'

    count = len(not_held)
    if count == 0:
        return 'fully', missing, exposed_edges
    if count == 1:
        return 'partly', missing, exposed_edges
    if count == 2:
        opposite_pairs = ({'top', 'bottom'}, {'left', 'right'})
        if set(not_held) in opposite_pairs:
            return 'partly', missing, exposed_edges
        return 'not_assessable', missing, exposed_edges
    return 'not_assessable', missing, exposed_edges


def translate_pane(pane, elevation_panes, angle_deg, row, answers):
    """
    Translates one pane into a schedule-translation result:
      {pane_id, status, method, payload, reasons, warnings, missing}

    pane: one Configurator export pane dict.
    elevation_panes: every pane in the SAME elevation as `pane` (including
    `pane` itself), needed for door/side-panel geometry and the slider bar
    warning.
    angle_deg: system.angledJoinAngleDeg, or None on a single-elevation
    system.
    row: dict with ffl_height_mm, building_use, is_bathroom, high_risk.
    answers: dict of hand-supplied per-pane stub answers (see module
    callers) - opaque_or_patterned, rail_present, rail_upper_edge_mm,
    rail_lower_edge_mm, level_difference_mm, frame_off_exposed.
    """
    warnings = []
    reasons = []
    missing = []

    # R1: fail closed on any unrecognised edge reason, before any framing
    # or span logic runs - never treat an unrecognised reason as held.
    edge_reason_error = _check_known_edge_reasons(pane)
    if edge_reason_error:
        reasons.append(edge_reason_error)
        return {
            'pane_id': pane['id'], 'status': 'not_assessable', 'method': None,
            'payload': None, 'reasons': reasons, 'warnings': warnings,
            'missing': missing,
        }

    sightline_mm = _sightline_mm(pane, row)
    if sightline_mm is None:
        missing.append('ffl_height_mm')
        return {
            'pane_id': pane['id'], 'status': 'not_assessable', 'method': None,
            'payload': None, 'reasons': reasons, 'warnings': warnings,
            'missing': missing,
        }

    warnings.extend(_slider_warnings(pane, elevation_panes, sightline_mm))

    sight_width_mm, sight_height_mm = _sight_size(pane)
    panel_area_m2 = sight_width_mm * sight_height_mm / 1e6

    # Sashless panes skip match_location() entirely - determine_sashless()
    # is self-contained (see engine/human_impact/__init__.py docstring).
    if pane.get('sashless'):
        span_mm, span_error = _sashless_span_mm(pane, sight_width_mm, sight_height_mm)
        if span_error:
            reasons.append(span_error)
            return {
                'pane_id': pane['id'], 'status': 'not_assessable', 'method': None,
                'payload': None, 'reasons': reasons, 'warnings': warnings,
                'missing': missing,
            }
        return {
            'pane_id': pane['id'], 'status': 'ready', 'method': 'sashless',
            'payload': {'span_mm': span_mm}, 'reasons': reasons,
            'warnings': warnings, 'missing': missing,
        }

    door_panes = [p for p in elevation_panes if _is_door_pane(p, elevation_panes)]

    if _is_door_pane(pane, elevation_panes):
        opening_type = 'door'
        is_side_panel = False
    else:
        opening_type = 'window'
        is_side_panel = _is_side_panel(pane, elevation_panes, door_panes, sightline_mm, warnings)

    framing, framing_missing, exposed_edges = _framing(pane, angle_deg, answers)
    if framing == 'needs_answer':
        return {
            'pane_id': pane['id'], 'status': 'needs_answer', 'method': None,
            'payload': None, 'reasons': reasons, 'warnings': warnings,
            'missing': framing_missing,
        }
    if framing == 'not_assessable':
        return {
            'pane_id': pane['id'], 'status': 'not_assessable', 'method': None,
            'payload': None, 'reasons': reasons, 'warnings': warnings,
            'missing': missing,
        }

    is_louvre = pane.get('type') == 'louvre'

    ctx = {
        'opening_type': opening_type,
        'is_side_panel': is_side_panel,
        'is_louvre': is_louvre,
        'building_use': row.get('building_use'),
        'is_bathroom': row.get('is_bathroom'),
        'high_risk': row.get('high_risk'),
        'framing': framing,
        'exposed_edges': exposed_edges,
        'sight_width_mm': sight_width_mm,
        'sight_height_mm': sight_height_mm,
        # DECISION (Sahil): sight size feeds the annealed/heat-strengthened
        # area/width caps too, not true glass size. Less conservative than
        # true glass size for a sashed pane - open question for Michael,
        # not changed here.
        'panel_area_m2': panel_area_m2,
        'panel_width_mm': sight_width_mm,
        'sightline_mm': sightline_mm,
        'opaque_or_patterned': answers.get('opaque_or_patterned', False),
        'rail_present': answers.get('rail_present', False),
        'rail_upper_edge_mm': answers.get('rail_upper_edge_mm'),
        'rail_lower_edge_mm': answers.get('rail_lower_edge_mm'),
        'level_difference_mm': answers.get('level_difference_mm'),
    }
    if is_louvre:
        ctx['blade_width_mm'] = pane.get('bladeWidthMM')
        ctx['blade_length_mm'] = pane.get('bladeLengthMM')

    method = 'louvre' if is_louvre else 'fixed'

    return {
        'pane_id': pane['id'], 'status': 'ready', 'method': method,
        'payload': ctx, 'reasons': reasons, 'warnings': warnings,
        'missing': missing,
    }


def translate_system(export, row, answers_by_pane):
    """
    Translates every pane in a Configurator export into a list of
    translate_pane() results.

    export: the Configurator export's top-level dict (export['system']).
    row: schedule row dict (ffl_height_mm, building_use, is_bathroom,
    high_risk).
    answers_by_pane: dict of (elevation_index, pane_id) -> answers dict.
    Pane ids are generated per-elevation from the split tree and are NOT
    guaranteed unique across elevations (confirmed against
    buildExportElevation/collectExportGeometry in the vendored
    configurator), so every pane is keyed by (elevation_index, pane_id),
    never pane_id alone.
    """
    angle_deg = export.get('angledJoinAngleDeg')
    results = []
    for elevation_index, elevation in enumerate(export['elevations']):
        elevation_panes = elevation['panes']
        for pane in elevation_panes:
            key = (elevation_index, pane['id'])
            answers = answers_by_pane.get(key, {})
            result = translate_pane(pane, elevation_panes, angle_deg, row, answers)
            result['elevation_index'] = elevation_index
            results.append(result)
    return results
