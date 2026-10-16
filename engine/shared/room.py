# AS 1288 Glass Thickness Calculator
# engine/shared/room.py
#
# The room question: is the glazing in a bathroom, ensuite or spa room, in a
# kitchen, or in neither? Pure functions with no file I/O, and nothing is
# imported from wind_load, silicone_bite, combined or human_impact.
#
# An unanswered or invalid room is never read as 'neither': validate_room()
# returns the missing-answer text so the caller can report Incomplete.
#
# Duce Timber Windows and Doors

ROOMS = ('bathroom', 'kitchen', 'neither')

# Glazing whose lowest sightline is at or below this height (mm) is covered
# by the room rule. The test is inclusive.
ROOM_SIGHTLINE_LIMIT_MM = 2000

MISSING_ROOM_TEXT = (
    "Which room is this glazing in (for a door, the room it serves or opens "
    "into)? Choose Bathroom, ensuite or spa room, Kitchen, or Neither."
)


def validate_room(room):
    """Returns (room, None) for a valid answer, otherwise (None, [MISSING_ROOM_TEXT])."""
    if type(room) is str and room in ROOMS:
        return room, None
    return None, [MISSING_ROOM_TEXT]


def room_rule_applies(room, sightline_mm):
    """
    True only for a bathroom or kitchen with a known sightline at or below
    the limit. 'neither', an unanswered room, a missing sightline or a
    sightline above the limit all give False.
    """
    if type(room) is not str or room not in ('bathroom', 'kitchen'):
        return False
    return sightline_mm is not None and sightline_mm <= ROOM_SIGHTLINE_LIMIT_MM
