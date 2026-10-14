# AS 1288 Glass Thickness Calculator
# engine/shared/side_panel.py
#
# The two limits that decide whether glass beside a doorway counts as a
# "side panel". Glass is a side panel only if BOTH hold:
#   (a) the bottom of the visible glass is no higher than
#       SIDE_PANEL_SIGHTLINE_MAX_MM above the finished floor, and
#   (b) the glass is within SIDE_PANEL_GAP_MAX_MM of the edge of a doorway.
# Both limits are inclusive (exactly on the limit still counts). If either
# test fails the glass is treated as an ordinary window, even if someone
# labelled it a side panel.
#
# Engineering reason: a person walking through or stumbling beside a door
# is likely to hit glass that is close to the door opening AND low enough
# to be reached by the body. Glass that is high up or well away from the
# door is not exposed to that kind of accidental impact.
#
# Sahil confirmed the 1200 mm sightline and 300 mm gap limits on
# 14 Oct 2026; not yet checked against the AS 1288 text itself.
#
# Kept in one place so the Configurator-schedule layer (which can measure
# both limits from geometry) and the standalone human impact page (which
# can only measure the height) can never drift apart.
#
# Duce Timber Windows and Doors

SIDE_PANEL_SIGHTLINE_MAX_MM = 1200
SIDE_PANEL_GAP_MAX_MM = 300


def sightline_within_side_panel_limit(sightline_mm):
    """
    True only when the lowest sightline is known and is at or below the
    side panel height limit. A missing sightline returns False - callers
    decide what an unknown height means for them.
    """
    return sightline_mm is not None and sightline_mm <= SIDE_PANEL_SIGHTLINE_MAX_MM
