# AS 1288 Glass Thickness Calculator
# engine/shared/framing.py
#
# Turns the "which edges are unframed?" answer into the framing class the
# human impact rules use, plus a stored (not acted on) wind route. Pure
# functions: no file I/O, and nothing is imported from wind_load,
# silicone_bite, combined or human_impact.
#
# Every function returns (framing_info, missing_answers). Exactly one of the
# two is None. An unanswered or invalid input never turns into a default:
# it returns missing_answers so the caller can report Incomplete.
#
# framing_info = {framing, unframed_count, opposite_or_adjacent,
#                 opposite_pair, wind_route}
# The wind route is recorded only. Nothing reads it.
#
# Duce Timber Windows and Doors

EDGES = ('head', 'sill', 'left', 'right')

_OPPOSITE_PAIRS = {
    frozenset({'head', 'sill'}): 'head_sill',
    frozenset({'left', 'right'}): 'left_right',
}

WIND_ROUTES = (
    'pathway_1', 'pathway_2_three_edge', 'pathway_2_two_edge', 'wind_not_assessed',
)

MISSING_EDGES_TEXT = (
    "Which edges are unframed? Tick the unframed edges, or choose "
    "“None unframed (fully framed)”."
)

MISSING_LOUVRE_TEXT = (
    "Is the louvre fully framed or partly framed (two opposite edges)? Choose one."
)


def _info(framing, unframed_count, shape, pair, wind_route):
    return {
        'framing': framing,
        'unframed_count': unframed_count,
        'opposite_or_adjacent': shape,
        'opposite_pair': pair,
        'wind_route': wind_route,
    }


def _valid_edges(value):
    if not isinstance(value, list):
        return False
    if not all(type(e) is str and e in EDGES for e in value):
        return False
    return len(set(value)) == len(value)


def derive_from_edges(unframed_edges, is_door):
    """
    unframed_edges: list of edge names ('head', 'sill', 'left', 'right').
    An empty list means "answered: none unframed". None or anything invalid
    means unanswered. is_door: doors treat any unframed edge as unframed.
    """
    if not _valid_edges(unframed_edges):
        return None, [MISSING_EDGES_TEXT]

    n = len(unframed_edges)
    edge_set = frozenset(unframed_edges)
    shape = None
    pair = None

    if n == 0:
        wind_route = 'pathway_1'
    elif n == 1:
        wind_route = 'pathway_2_three_edge'
    elif n == 2 and edge_set in _OPPOSITE_PAIRS:
        shape = 'opposite'
        pair = _OPPOSITE_PAIRS[edge_set]
        wind_route = 'pathway_2_two_edge'
    else:
        if n == 2:
            shape = 'adjacent'
        wind_route = 'wind_not_assessed'

    if n == 0:
        framing = 'fully'
    elif is_door:
        framing = 'unframed'
    elif n == 1 or shape == 'opposite':
        framing = 'partly'
    else:
        framing = 'unframed'

    return _info(framing, n, shape, pair, wind_route), None


def derive_from_louvre(louvre_framing, is_door):
    """
    louvre_framing: 'fully' or 'partly' (two opposite edges). Anything else,
    including None, is unanswered. A louvre door answered 'partly' counts as
    unframed.
    """
    if type(louvre_framing) is str and louvre_framing == 'fully':
        return _info('fully', 0, None, None, 'pathway_1'), None
    if type(louvre_framing) is str and louvre_framing == 'partly':
        framing = 'unframed' if is_door else 'partly'
        return _info(framing, 2, 'opposite', None, 'pathway_2_two_edge'), None
    return None, [MISSING_LOUVRE_TEXT]


def sashless_framing_info():
    """Sashless glazing: no question, always partly with two opposite edges."""
    return _info('partly', 2, 'opposite', None, 'pathway_2_two_edge')
