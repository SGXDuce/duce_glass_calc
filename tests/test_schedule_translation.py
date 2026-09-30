# AS 1288 Glass Thickness Calculator - Schedule Translation Layer Tests
# Validates engine/schedule/translation.py: pure geometry -> ctx/payload
# translation from a Configurator export pane into what engine/human_impact
# expects. All numbers are hand-calculated - see each test's own comment for
# whether its fixture is a real verified export or hand-built.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_schedule_translation.py -v

import json
import os

from engine.schedule.translation import (
    translate_pane, translate_system, ASSUMED_BAR_TUCKIN_MM,
)
from engine.human_impact import determine_fixed, determine_sashless

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename), encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def make_pane(id='F', productClass='window', type='fixed',
              xMM=0, yMM=0, widthMM=1000, heightMM=1000,
              sash_top=0, sash_bottom=0, sash_left=0, sash_right=0,
              unframedEdgeReasons=None, sashless=False,
              bladeWidthMM=None, bladeLengthMM=None):
    return {
        'id': id,
        'productClass': productClass,
        'type': type,
        'bladeWidthMM': bladeWidthMM,
        'bladeLengthMM': bladeLengthMM,
        'xMM': xMM, 'yMM': yMM,
        'widthMM': widthMM, 'heightMM': heightMM,
        'sashEdgesMM': {'top': sash_top, 'bottom': sash_bottom, 'left': sash_left, 'right': sash_right},
        'unframedEdgeReasons': unframedEdgeReasons or {'top': None, 'bottom': None, 'left': None, 'right': None},
        'sashless': sashless,
    }


def make_row(ffl_height_mm=0, building_use='residential', is_bathroom=False, high_risk=False):
    return {
        'ffl_height_mm': ffl_height_mm,
        'building_use': building_use,
        'is_bathroom': is_bathroom,
        'high_risk': high_risk,
    }


NO_ANSWERS = {}


# ---------------------------------------------------------------------------
# T1 - REAL verified export values (handover section 14)
# ---------------------------------------------------------------------------

def test_t1_lone_horizontal_slider_door():
    pane = make_pane(
        productClass='door', type='horizontal-slider',
        xMM=60, yMM=40, widthMM=1680, heightMM=2020,
        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40,
    )
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    assert result['payload']['sightline_mm'] == 80
    assert result['payload']['sight_height_mm'] == pane['heightMM'] - 40 - 40 == 1940
    assert result['payload']['sight_width_mm'] == pane['widthMM'] - 40 - 40
    assert result['warnings'] == []


# ---------------------------------------------------------------------------
# T2 - HAND-BUILT fixed window
# ---------------------------------------------------------------------------

def test_t2_fixed_window():
    pane = make_pane(
        productClass='window', type='fixed',
        xMM=60, yMM=60, widthMM=1080, heightMM=1380,
    )
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    ctx = result['payload']
    assert ctx['sightline_mm'] == 360
    assert ctx['sight_width_mm'] == 1080
    assert ctx['sight_height_mm'] == 1380
    assert round(ctx['panel_area_m2'], 4) == 1.4904
    assert ctx['framing'] == 'fully'
    assert ctx['opening_type'] == 'window'
    assert ctx['is_side_panel'] is False

    engine_result = determine_fixed(ctx)
    assert engine_result['grade_a_required'] is True
    assert engine_result['table'] == '5.1'
    annealed = next(t for t in engine_result['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is False


def test_t2b_opaque_still_blocked_by_area():
    pane = make_pane(
        productClass='window', type='fixed',
        xMM=60, yMM=60, widthMM=1080, heightMM=1380,
    )
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, {'opaque_or_patterned': True})
    ctx = result['payload']
    assert ctx['opaque_or_patterned'] is True

    engine_result = determine_fixed(ctx)
    annealed = next(t for t in engine_result['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is False


def test_t2c_short_pane_allows_annealed():
    pane = make_pane(
        productClass='window', type='fixed',
        xMM=60, yMM=60, widthMM=1080, heightMM=880,
    )
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, {'opaque_or_patterned': True})
    ctx = result['payload']
    assert round(ctx['panel_area_m2'], 4) == 0.9504

    engine_result = determine_fixed(ctx)
    annealed = next(t for t in engine_result['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is True
    assert annealed['min_thickness'] == 5


# ---------------------------------------------------------------------------
# T3 - bathroom sightline threshold
# ---------------------------------------------------------------------------

def test_t3_bathroom_blocks_annealed():
    pane = make_pane(
        productClass='window', type='fixed',
        xMM=60, yMM=60, widthMM=1080, heightMM=1380,
    )
    row = make_row(ffl_height_mm=1200, building_use='residential', is_bathroom=True)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    ctx = result['payload']
    assert ctx['sightline_mm'] == 1260

    engine_result = determine_fixed(ctx)
    assert engine_result['clauses'] == ['5.8']
    assert engine_result['table'] == '5.1'
    annealed = next(t for t in engine_result['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is False


def test_t3b_bathroom_sightline_boundary():
    pane = make_pane(
        productClass='window', type='fixed',
        xMM=60, yMM=60, widthMM=1080, heightMM=1380,
    )
    row_in = make_row(ffl_height_mm=1940, building_use='residential', is_bathroom=True)
    result_in = translate_pane(pane, [pane], None, row_in, NO_ANSWERS)
    assert result_in['payload']['sightline_mm'] == 2000
    engine_in = determine_fixed(result_in['payload'])
    assert '5.8' in engine_in['clauses']

    row_out = make_row(ffl_height_mm=1941, building_use='residential', is_bathroom=True)
    result_out = translate_pane(pane, [pane], None, row_out, NO_ANSWERS)
    assert result_out['payload']['sightline_mm'] == 2001
    engine_out = determine_fixed(result_out['payload'])
    assert engine_out['grade_a_required'] is False


# ---------------------------------------------------------------------------
# T4 - side panel from geometry (HAND-BUILT)
# ---------------------------------------------------------------------------

def _t4_door():
    return make_pane(
        id='door', productClass='door', type='hinged',
        xMM=60, yMM=60, widthMM=900, heightMM=2000,
        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40,
    )


def test_t4_side_panel_gap_100_right():
    door = _t4_door()
    sidelight = make_pane(
        id='side', productClass='window', type='fixed',
        xMM=1020, yMM=60, widthMM=330, heightMM=2000,
    )
    row = make_row(ffl_height_mm=0, building_use='residential')
    panes = [door, sidelight]

    result = translate_pane(sidelight, panes, None, row, NO_ANSWERS)
    ctx = result['payload']
    assert ctx['is_side_panel'] is True
    assert ctx['sightline_mm'] == 60
    assert round(ctx['panel_area_m2'], 4) == 0.66

    engine_result = determine_fixed(ctx)
    assert '5.3.1' in engine_result['clauses']
    assert engine_result['table'] == '5.1'
    annealed = next(t for t in engine_result['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is False


def test_t4_side_panel_gap_boundary():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    sidelight_300 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=1220, yMM=60, widthMM=330, heightMM=2000)
    panes_300 = [door, sidelight_300]
    result_300 = translate_pane(sidelight_300, panes_300, None, row, NO_ANSWERS)
    assert result_300['payload']['is_side_panel'] is True

    sidelight_301 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=1221, yMM=60, widthMM=330, heightMM=2000)
    panes_301 = [door, sidelight_301]
    result_301 = translate_pane(sidelight_301, panes_301, None, row, NO_ANSWERS)
    ctx_301 = result_301['payload']
    assert ctx_301['is_side_panel'] is False

    engine_301 = determine_fixed(ctx_301)
    assert '5.4' not in engine_301['clauses']  # exempt: sight width 330 <= 500
    annealed = next(t for t in engine_301['types'] if t['id'] == 'monolithic_annealed')
    assert annealed['ok'] is True
    assert round(ctx_301['panel_area_m2'], 4) == 0.66


def test_t4_side_panel_mirrored_left():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    # door visible left edge = 60 + 40 = 100; sidelight to the left, gap 100
    # -> sidelight right edge (visible) = 100 - 100 = 0 -> width 330, xMM = -330
    sidelight = make_pane(id='side', productClass='window', type='fixed',
                           xMM=-330, yMM=60, widthMM=330, heightMM=2000)
    panes = [door, sidelight]
    result = translate_pane(sidelight, panes, None, row, NO_ANSWERS)
    assert result['payload']['is_side_panel'] is True


def test_t4_side_panel_gap_boundary_door_on_right_of_pane():
    # Door at xMM 3000, sash 40 all edges -> visible left edge 3040.
    # Sidelight sits to the LEFT of the door - this exercises the buggy
    # branch directly (regression for the door-edge - pane-edge sign fix).
    door = make_pane(
        id='door', productClass='door', type='hinged',
        xMM=3000, yMM=60, widthMM=900, heightMM=2000,
        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40,
    )
    row = make_row(ffl_height_mm=0, building_use='residential')

    sidelight_100 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=2610, yMM=60, widthMM=330, heightMM=2000)
    result_100 = translate_pane(sidelight_100, [door, sidelight_100], None, row, NO_ANSWERS)
    assert result_100['payload']['is_side_panel'] is True

    sidelight_300 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=2410, yMM=60, widthMM=330, heightMM=2000)
    result_300 = translate_pane(sidelight_300, [door, sidelight_300], None, row, NO_ANSWERS)
    assert result_300['payload']['is_side_panel'] is True

    sidelight_301 = make_pane(id='side', productClass='window', type='fixed',
                              xMM=2409, yMM=60, widthMM=330, heightMM=2000)
    result_301 = translate_pane(sidelight_301, [door, sidelight_301], None, row, NO_ANSWERS)
    assert result_301['payload']['is_side_panel'] is False

    sidelight_1000 = make_pane(id='side', productClass='window', type='fixed',
                                xMM=1710, yMM=60, widthMM=330, heightMM=2000)
    result_1000 = translate_pane(sidelight_1000, [door, sidelight_1000], None, row, NO_ANSWERS)
    assert result_1000['payload']['is_side_panel'] is False


def test_t4_side_panel_gap_boundary_door_on_left_of_pane():
    # Mirror image of the standard (already-covered) right-hand-branch
    # case: door to the LEFT of the pane, pane to its right, at the same
    # four gap values, so both directions are covered at the boundary.
    # Pane fixed at xMM 1000 (visible left edge 1000, sash 0); door width
    # 900, sash 40 all edges, so door visible right edge = door_xMM + 860.
    # gap = pane_left - door_right = 1000 - (door_xMM + 860).
    row = make_row(ffl_height_mm=0, building_use='residential')

    def door_at(xMM):
        return make_pane(
            id='door', productClass='door', type='hinged',
            xMM=xMM, yMM=60, widthMM=900, heightMM=2000,
            sash_top=40, sash_bottom=40, sash_left=40, sash_right=40,
        )

    sidelight_100 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=1000, yMM=60, widthMM=330, heightMM=2000)
    door_100 = door_at(40)
    result_100 = translate_pane(sidelight_100, [door_100, sidelight_100], None, row, NO_ANSWERS)
    assert result_100['payload']['is_side_panel'] is True

    sidelight_300 = make_pane(id='side', productClass='window', type='fixed',
                               xMM=1000, yMM=60, widthMM=330, heightMM=2000)
    door_300 = door_at(-160)
    result_300 = translate_pane(sidelight_300, [door_300, sidelight_300], None, row, NO_ANSWERS)
    assert result_300['payload']['is_side_panel'] is True

    sidelight_301 = make_pane(id='side', productClass='window', type='fixed',
                              xMM=1000, yMM=60, widthMM=330, heightMM=2000)
    door_301 = door_at(-161)
    result_301 = translate_pane(sidelight_301, [door_301, sidelight_301], None, row, NO_ANSWERS)
    assert result_301['payload']['is_side_panel'] is False

    sidelight_1000 = make_pane(id='side', productClass='window', type='fixed',
                                xMM=1000, yMM=60, widthMM=330, heightMM=2000)
    door_1000 = door_at(-860)
    result_1000 = translate_pane(sidelight_1000, [door_1000, sidelight_1000], None, row, NO_ANSWERS)
    assert result_1000['payload']['is_side_panel'] is False


def test_t4_side_panel_yMM_boundary():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    sidelight_in = make_pane(id='side', productClass='window', type='fixed',
                              xMM=1020, yMM=1200, widthMM=330, heightMM=810)
    panes_in = [door, sidelight_in]
    result_in = translate_pane(sidelight_in, panes_in, None, row, NO_ANSWERS)
    assert result_in['payload']['sightline_mm'] == 1200
    assert result_in['payload']['is_side_panel'] is True

    sidelight_out = make_pane(id='side', productClass='window', type='fixed',
                               xMM=1020, yMM=1201, widthMM=330, heightMM=809)
    panes_out = [door, sidelight_out]
    result_out = translate_pane(sidelight_out, panes_out, None, row, NO_ANSWERS)
    assert result_out['payload']['sightline_mm'] == 1201
    assert result_out['payload']['is_side_panel'] is False


def test_t4_split_sidelight():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    lower = make_pane(id='lower', productClass='window', type='fixed',
                       xMM=1020, yMM=60, widthMM=330, heightMM=1000)
    upper = make_pane(id='upper', productClass='window', type='fixed',
                       xMM=1020, yMM=1300, widthMM=330, heightMM=760)
    panes = [door, lower, upper]

    result_lower = translate_pane(lower, panes, None, row, NO_ANSWERS)
    assert result_lower['payload']['is_side_panel'] is True

    result_upper = translate_pane(upper, panes, None, row, NO_ANSWERS)
    assert result_upper['payload']['sightline_mm'] == 1300
    assert result_upper['payload']['is_side_panel'] is False


def test_t4_pane_entirely_above_door_never_beside_it():
    door = _t4_door()  # yMM 60, heightMM 2000 -> top edge 2060
    row = make_row(ffl_height_mm=0, building_use='residential')

    above = make_pane(id='above', productClass='window', type='fixed',
                       xMM=1020, yMM=2060, widthMM=330, heightMM=300)
    panes = [door, above]
    result = translate_pane(above, panes, None, row, NO_ANSWERS)
    # no height overlap with the door at all, regardless of gap
    assert result['payload']['is_side_panel'] is False


def test_t4_labelled_side_panel_far_from_door_still_side_panel_with_warning():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    far = make_pane(id='far', productClass='side-panel', type='fixed',
                     xMM=5000, yMM=60, widthMM=330, heightMM=2000)
    panes = [door, far]
    result = translate_pane(far, panes, None, row, NO_ANSWERS)
    assert result['payload']['is_side_panel'] is True
    assert len(result['warnings']) == 1


def test_t4_fixed_sidelight_not_reclassified_as_door():
    door = _t4_door()
    row = make_row(ffl_height_mm=0, building_use='residential')

    sidelight = make_pane(id='side', productClass='window', type='fixed',
                           xMM=1020, yMM=60, widthMM=330, heightMM=2000)
    panes = [door, sidelight]
    result = translate_pane(sidelight, panes, None, row, NO_ANSWERS)
    assert result['payload']['opening_type'] == 'window'


# ---------------------------------------------------------------------------
# T5 - fixed light beside sliding leaf (HAND-BUILT)
# ---------------------------------------------------------------------------

def test_t5_fixed_beside_sliding_door_leaf_becomes_door():
    fixed = make_pane(id='fixed', productClass='window', type='fixed',
                       xMM=60, yMM=60, widthMM=500, heightMM=2000)
    slider = make_pane(id='slider', productClass='door', type='horizontal-slider',
                        xMM=620, yMM=60, widthMM=1000, heightMM=2000,
                        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0, building_use='residential')
    panes = [fixed, slider]

    result = translate_pane(fixed, panes, None, row, NO_ANSWERS)
    assert result['payload']['opening_type'] == 'door'


def test_t5_fixed_beside_sliding_window_leaf_stays_window():
    fixed = make_pane(id='fixed', productClass='window', type='fixed',
                       xMM=60, yMM=60, widthMM=500, heightMM=2000)
    slider = make_pane(id='slider', productClass='window', type='horizontal-slider',
                        xMM=620, yMM=60, widthMM=1000, heightMM=2000,
                        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0, building_use='residential')
    panes = [fixed, slider]

    result = translate_pane(fixed, panes, None, row, NO_ANSWERS)
    assert result['payload']['opening_type'] == 'window'


# ---------------------------------------------------------------------------
# T6 - framing, edge reasons only
# ---------------------------------------------------------------------------

def _edges(**kwargs):
    e = {'top': None, 'bottom': None, 'left': None, 'right': None}
    e.update(kwargs)
    return e


def test_t6_framing_all_null_fully():
    pane = make_pane(unframedEdgeReasons=_edges())
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['payload']['framing'] == 'fully'


def test_t6_framing_one_edge_partly():
    pane = make_pane(unframedEdgeReasons=_edges(left='next-to-sashless'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['payload']['framing'] == 'partly'


def test_t6_framing_opposite_edges_partly():
    pane = make_pane(unframedEdgeReasons=_edges(left='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['payload']['framing'] == 'partly'


def test_t6_framing_adjacent_edges_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(top='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t6_framing_three_edges_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(top='silicone-flat', left='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t6_framing_angled_joint_90_fully():
    pane = make_pane(unframedEdgeReasons=_edges(left='angled-joint'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], 90, row, NO_ANSWERS)
    assert result['payload']['framing'] == 'fully'


def test_t6_framing_angled_joint_135_partly():
    pane = make_pane(unframedEdgeReasons=_edges(left='angled-joint'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], 135, row, NO_ANSWERS)
    assert result['payload']['framing'] == 'partly'


def test_t6_framing_angled_joint_no_angle_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(left='angled-joint'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


# ---------------------------------------------------------------------------
# T7 - frame-off exposed edges question
# ---------------------------------------------------------------------------

def test_t7_frame_off_needs_answer():
    pane = make_pane(unframedEdgeReasons=_edges(left='frame-off'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'needs_answer'
    assert 'frame_off_exposed' in result['missing']


def test_t7_frame_off_answered_yes():
    pane = make_pane(unframedEdgeReasons=_edges(left='frame-off'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, {'frame_off_exposed': 'y'})
    assert result['status'] == 'ready'
    assert result['payload']['framing'] == 'partly'
    assert result['payload']['exposed_edges'] == 'y'


def test_t7_frame_off_answered_no():
    pane = make_pane(unframedEdgeReasons=_edges(left='frame-off'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, {'frame_off_exposed': 'n'})
    assert result['status'] == 'ready'
    assert result['payload']['exposed_edges'] == 'n'


# ---------------------------------------------------------------------------
# T8 - slider warnings (T8a-c from Configurator's own verified harness run;
# widthMM 1720 for the stacked panes is HAND-BUILT, matching the lone-slider
# width)
# ---------------------------------------------------------------------------

def test_t8a_side_by_side_horizontal_sliders_no_warnings():
    left = make_pane(id='left', productClass='door', type='horizontal-slider',
                      xMM=40, yMM=40, widthMM=855, heightMM=2020,
                      sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    right = make_pane(id='right', productClass='door', type='horizontal-slider',
                       xMM=905, yMM=40, widthMM=855, heightMM=2020,
                       sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0)
    panes = [left, right]

    for pane in panes:
        result = translate_pane(pane, panes, None, row, NO_ANSWERS)
        assert result['payload']['sightline_mm'] == 80
        assert result['payload']['sight_height_mm'] == 1940
        assert result['payload']['sight_width_mm'] == 775
        assert result['warnings'] == []


def test_t8b_stacked_vertical_sliders():
    bottom = make_pane(id='bottom', productClass='door', type='vertical-slider',
                        xMM=40, yMM=40, widthMM=1720, heightMM=985,
                        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    top = make_pane(id='top', productClass='door', type='vertical-slider',
                     xMM=40, yMM=1075, widthMM=1720, heightMM=985,
                     sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0)
    panes = [bottom, top]

    result_bottom = translate_pane(bottom, panes, None, row, NO_ANSWERS)
    assert result_bottom['payload']['sightline_mm'] == 80
    assert result_bottom['payload']['sight_height_mm'] == 905
    assert len(result_bottom['warnings']) == 1  # VERTICAL only

    result_top = translate_pane(top, panes, None, row, NO_ANSWERS)
    assert result_top['payload']['sightline_mm'] == 1115
    assert result_top['payload']['sight_height_mm'] == 905
    assert len(result_top['warnings']) == 2  # BAR and VERTICAL
    assert any(str(ASSUMED_BAR_TUCKIN_MM) in w for w in result_top['warnings'])


def test_t8c_stacked_horizontal_sliders():
    bottom = make_pane(id='bottom', productClass='door', type='horizontal-slider',
                        xMM=40, yMM=40, widthMM=1720, heightMM=985,
                        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    top = make_pane(id='top', productClass='door', type='horizontal-slider',
                     xMM=40, yMM=1075, widthMM=1720, heightMM=985,
                     sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0)
    panes = [bottom, top]

    result_bottom = translate_pane(bottom, panes, None, row, NO_ANSWERS)
    assert result_bottom['warnings'] == []

    result_top = translate_pane(top, panes, None, row, NO_ANSWERS)
    assert len(result_top['warnings']) == 1  # BAR only


def test_t8d_fixed_beside_slider_no_horizontal_overlap_no_warnings():
    fixed = make_pane(id='fixed', productClass='window', type='fixed',
                       xMM=60, yMM=60, widthMM=815, heightMM=1980)
    slider = make_pane(id='slider', productClass='door', type='horizontal-slider',
                        xMM=905, yMM=40, widthMM=855, heightMM=2020,
                        sash_top=40, sash_bottom=40, sash_left=40, sash_right=40)
    row = make_row(ffl_height_mm=0)
    panes = [fixed, slider]

    result_fixed = translate_pane(fixed, panes, None, row, NO_ANSWERS)
    assert result_fixed['warnings'] == []
    result_slider = translate_pane(slider, panes, None, row, NO_ANSWERS)
    assert result_slider['warnings'] == []


# ---------------------------------------------------------------------------
# T9 - missing FFL
# ---------------------------------------------------------------------------

def test_t9_missing_ffl_not_assessable():
    pane = make_pane()
    row = make_row(ffl_height_mm=None)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


def test_t9_no_ready_result_ever_has_none_sightline():
    # Sweep every T-series fixture shape that reaches 'ready' and confirm
    # none of them carry a None sightline_mm.
    fixtures = []

    door = _t4_door()
    sidelight = make_pane(id='side', productClass='window', type='fixed',
                           xMM=1020, yMM=60, widthMM=330, heightMM=2000)
    fixtures.append((sidelight, [door, sidelight]))

    fixed = make_pane(xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    fixtures.append((fixed, [fixed]))

    row = make_row(ffl_height_mm=0, building_use='residential')
    for pane, panes in fixtures:
        result = translate_pane(pane, panes, None, row, NO_ANSWERS)
        if result['status'] == 'ready' and result['method'] != 'sashless':
            assert result['payload']['sightline_mm'] is not None


# ---------------------------------------------------------------------------
# T10 - louvre
# ---------------------------------------------------------------------------

def test_t10_louvre_pane():
    pane = make_pane(type='louvre', bladeWidthMM=150, bladeLengthMM=900)
    row = make_row(ffl_height_mm=0, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'ready'
    assert result['method'] == 'louvre'
    assert result['payload']['blade_width_mm'] == 150
    assert result['payload']['blade_length_mm'] == 900
    assert result['payload']['is_louvre'] is True


# ---------------------------------------------------------------------------
# T11 - sashless span, orientation read from unframedEdgeReasons
#
# REWRITTEN for Configurator batch 63 / schema v6. The old version of this
# test hand-built a horizontal-slider with a hard-coded 20mm stile and
# asserted span = widthMM minus both stile widths - that was the pre-batch-63
# orientation (glass held left/right). Upstream now corrects this: a
# horizontal slider's glass is held top/bottom (free left/right), and a
# vertical slider (double-hung) is the mirror - held left/right, free
# top/bottom. Span is now derived from which edges unframedEdgeReasons marks
# 'sashless-free-edge', never from the pane type or a hand-picked stile
# figure. See R1-R4 in engine/schedule/translation.py.
# ---------------------------------------------------------------------------

def test_t11a_sashless_ox_window_real_export():
    # REAL verified Configurator export (schema v6, batch 63):
    # tests/fixtures/sashless_ox_window.json. The sashless pane is a
    # horizontal-slider: free edges left/right, held top/bottom -> span is
    # measured top-to-bottom (sight_height_mm).
    #
    # sight_width_mm (900) != sight_height_mm (1050) for this pane, so the
    # assertions below discriminate direction directly: span must equal the
    # HELD-edge dimension (sight_height_mm) and must NOT equal the other
    # dimension (sight_width_mm) - this fails against the pre-batch-63
    # width-based formula, which returns 900 here (confirmed: swapping in
    # master's translation.py makes this test fail).
    export = load_fixture('sashless_ox_window.json')
    panes = export['system']['elevations'][0]['panes']
    sashless_pane = next(p for p in panes if p['sashless'])
    assert sashless_pane['type'] == 'horizontal-slider'

    reasons = sashless_pane['unframedEdgeReasons']
    assert reasons['left'] == 'sashless-free-edge'
    assert reasons['right'] == 'sashless-free-edge'
    assert reasons['top'] is None
    assert reasons['bottom'] is None

    sight_width_mm = sashless_pane['widthMM'] - sashless_pane['sashEdgesMM']['left'] - sashless_pane['sashEdgesMM']['right']
    sight_height_mm = sashless_pane['heightMM'] - sashless_pane['sashEdgesMM']['top'] - sashless_pane['sashEdgesMM']['bottom']
    assert sight_width_mm != sight_height_mm  # fixture can discriminate direction

    row = make_row(ffl_height_mm=0)
    result = translate_pane(sashless_pane, panes, None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    assert result['method'] == 'sashless'
    assert result['payload']['span_mm'] == 1050
    assert result['payload']['span_mm'] == sight_height_mm  # held top/bottom -> span = sight_height
    assert result['payload']['span_mm'] != sight_width_mm   # not the width axis


def test_t11b_sashless_double_hung_real_export():
    # REAL verified Configurator export (schema v6, batch 63):
    # tests/fixtures/sashless_double_hung.json. Both panes are
    # vertical-sliders (double-hung mirror image): free edges top/bottom
    # (including the meeting-rail edge), held left/right -> span is
    # measured left-to-right (sight_width_mm).
    #
    # NOTE: this test only confirms the real double-hung export gives
    # span_mm == 1050 - it does NOT prove the held-left/right direction is
    # being read correctly. For this fixture, the pre-batch-63 formula
    # (widthMM minus left/right sash) computes the same width-axis
    # expression as the correct one and ALSO returns 1050, so this test
    # still passes against the old, pre-batch-63 translation.py (confirmed
    # by swapping it in). The sight_width_mm != sight_height_mm and
    # span-must-not-equal-sight_height_mm assertions below narrow things
    # down but do not close that gap either, for the same reason.
    # test_t11d_sashless_span_follows_reasons_not_width_axis is the test
    # that actually guards the held-left/right direction (it fails against
    # the old code).
    export = load_fixture('sashless_double_hung.json')
    panes = export['system']['elevations'][0]['panes']

    row = make_row(ffl_height_mm=0)
    for pane in panes:
        assert pane['type'] == 'vertical-slider'

        reasons = pane['unframedEdgeReasons']
        assert reasons['top'] == 'sashless-free-edge'
        assert reasons['bottom'] == 'sashless-free-edge'
        assert reasons['left'] is None
        assert reasons['right'] is None

        sight_width_mm = pane['widthMM'] - pane['sashEdgesMM']['left'] - pane['sashEdgesMM']['right']
        sight_height_mm = pane['heightMM'] - pane['sashEdgesMM']['top'] - pane['sashEdgesMM']['bottom']
        assert sight_width_mm != sight_height_mm  # fixture can discriminate direction

        result = translate_pane(pane, panes, None, row, NO_ANSWERS)

        assert result['status'] == 'ready'
        assert result['method'] == 'sashless'
        assert result['payload']['span_mm'] == 1050
        assert result['payload']['span_mm'] == sight_width_mm  # held left/right -> span = sight_width
        assert result['payload']['span_mm'] != sight_height_mm  # not the height axis

    engine_result = determine_sashless(1050)
    mono_tough = next(t for t in engine_result['types'] if t['id'] == 'monolithic_toughened')
    assert mono_tough['ok'] is True
    assert mono_tough['min_thickness'] == 6
    # 1050mm exceeds the 1000mm ceiling for 5mm monolithic toughened -
    # confirms the span is actually driving the thickness lookup, not just
    # returning a plausible-looking number.


def test_t11c_sashless_horizontal_slider_hand_built():
    # HAND-BUILT, orientation per R3: horizontal-slider free edges are
    # left/right, held top/bottom -> span = sight_height_mm.
    pane = make_pane(
        type='horizontal-slider', widthMM=1040, heightMM=1050,
        sash_top=15, sash_bottom=15, sashless=True,
        unframedEdgeReasons=_edges(left='sashless-free-edge', right='sashless-free-edge'),
    )
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'ready'
    assert result['method'] == 'sashless'
    assert result['payload']['span_mm'] == 1020  # 1050 - 15 - 15


def test_t11d_sashless_span_follows_reasons_not_width_axis():
    # HAND-BUILT companion for T11b. The real double-hung fixture
    # (tests/fixtures/sashless_double_hung.json) cannot discriminate old
    # vs. new code: its held edges are left/right, and the pre-batch-63
    # formula (`widthMM - sashLeft - sashRight`) ALWAYS computes the width
    # axis regardless of pane type - so for ANY pane held left/right, old
    # and new code compute the identical expression and always agree,
    # whatever the numbers are. Confirmed directly: swapping in master's
    # translation.py against the real fixture still passed (see this
    # branch's earlier task report). Only a pane held top/bottom can ever
    # disagree with the old width-only formula.
    #
    # This test proves direction is read from unframedEdgeReasons, not
    # defaulted to width, a different way: two panes with IDENTICAL
    # widthMM/heightMM/sashEdgesMM but OPPOSITE free-edge assignments must
    # produce DIFFERENT spans. The old code, which ignores
    # unframedEdgeReasons entirely for span, would compute the same
    # width-based number for both - this test fails against it for the
    # held-top/bottom pane, the same way T11a/T11c do.
    common_kwargs = dict(
        type='vertical-slider', widthMM=1080, heightMM=870,
        sash_top=15, sash_bottom=15, sash_left=15, sash_right=15,
        sashless=True,
    )

    held_left_right = make_pane(
        unframedEdgeReasons=_edges(top='sashless-free-edge', bottom='sashless-free-edge'),
        **common_kwargs,
    )
    held_top_bottom = make_pane(
        unframedEdgeReasons=_edges(left='sashless-free-edge', right='sashless-free-edge'),
        **common_kwargs,
    )

    row = make_row(ffl_height_mm=0)
    result_lr = translate_pane(held_left_right, [held_left_right], None, row, NO_ANSWERS)
    result_tb = translate_pane(held_top_bottom, [held_top_bottom], None, row, NO_ANSWERS)

    assert result_lr['status'] == 'ready' and result_tb['status'] == 'ready'
    assert result_lr['payload']['span_mm'] == 1050   # held left/right -> sight_width_mm
    assert result_tb['payload']['span_mm'] == 840    # held top/bottom -> sight_height_mm
    assert result_lr['payload']['span_mm'] != result_tb['payload']['span_mm']


# ---------------------------------------------------------------------------
# T12 - R1 fail-closed on unknown/malformed edge reasons
# ---------------------------------------------------------------------------

def test_t12_unknown_reason_sashless_pane_not_assessable():
    pane = make_pane(
        type='horizontal-slider', sashless=True,
        unframedEdgeReasons=_edges(left='sashless-free-edge', right='bogus-reason'),
    )
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


def test_t12_unknown_reason_non_sashless_pane_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(left='bogus-reason'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


def test_t12_missing_edge_key_not_assessable():
    pane = make_pane(unframedEdgeReasons={'top': None, 'bottom': None, 'left': None})
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


def test_t12_wrong_case_reason_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(left='Silicone-Flat'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


def test_t12_empty_string_reason_not_assessable():
    pane = make_pane(unframedEdgeReasons=_edges(left=''))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'
    assert result['payload'] is None


# ---------------------------------------------------------------------------
# T13 - R2 sashless edge pattern: exactly two OPPOSITE free edges
# ---------------------------------------------------------------------------

def test_t13_sashless_one_free_edge_not_assessable():
    pane = make_pane(sashless=True, unframedEdgeReasons=_edges(left='sashless-free-edge'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t13_sashless_three_free_edges_not_assessable():
    pane = make_pane(sashless=True, unframedEdgeReasons=_edges(
        top='sashless-free-edge', left='sashless-free-edge', right='sashless-free-edge',
    ))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t13_sashless_two_adjacent_free_edges_not_assessable():
    pane = make_pane(sashless=True, unframedEdgeReasons=_edges(
        top='sashless-free-edge', left='sashless-free-edge',
    ))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t13_sashless_zero_free_edges_not_assessable():
    pane = make_pane(sashless=True, unframedEdgeReasons=_edges())
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


def test_t13_sashless_held_edge_with_other_reason_not_assessable():
    # left/right free (opposite pair, valid pattern), but the top held edge
    # carries 'frame-off' instead of None - must not be treated as held.
    pane = make_pane(sashless=True, unframedEdgeReasons=_edges(
        left='sashless-free-edge', right='sashless-free-edge', top='frame-off',
    ))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


# ---------------------------------------------------------------------------
# T14 - R4: 'sashless-free-edge' on a non-sashless pane is inconsistent
# ---------------------------------------------------------------------------

def test_t14_sashless_free_edge_on_non_sashless_pane_not_assessable():
    pane = make_pane(sashless=False, unframedEdgeReasons=_edges(left='sashless-free-edge'))
    row = make_row(ffl_height_mm=0)
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)
    assert result['status'] == 'not_assessable'


# ---------------------------------------------------------------------------
# translate_system - elevation nesting / pane id scoping
# ---------------------------------------------------------------------------

def test_translate_system_keys_by_elevation_and_pane_id():
    pane_a = make_pane(id='F', xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    pane_b = make_pane(id='F', xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    export = {
        'angledJoinAngleDeg': None,
        'elevations': [
            {'panes': [pane_a]},
            {'panes': [pane_b]},
        ],
    }
    row = make_row(ffl_height_mm=0, building_use='residential')
    results = translate_system(export, row, {})

    assert len(results) == 2
    assert results[0]['elevation_index'] == 0
    assert results[1]['elevation_index'] == 1
    # Both panes share id 'F' across elevations but are translated
    # independently without collision.
    assert results[0]['pane_id'] == results[1]['pane_id'] == 'F'


# ---------------------------------------------------------------------------
# T15 - span_mm / span_basis at the top level of translate_pane()'s result
#
# DECIDED (Sahil): span is measured on daylight size, between the supported
# edges. Four edges supported = the shorter daylight dimension. Three
# supported edges = the daylight length between the one opposite pair of
# supported edges. Two supported edges (the opposite pair) = the daylight
# length between them. Two adjacent unsupported edges, or three or more
# unsupported edges, stay not_assessable (span None). Sashless panes keep
# the existing held-edge rule.
#
# All fixed/louvre expected values below are derived from the same pane's
# own sight_width_mm/sight_height_mm (reusing test_t2's 1080 x 1380 fixed
# pane and test_t10's louvre pane), never invented numbers.
# ---------------------------------------------------------------------------

def test_t15a_span_fully_framed_shorter_dimension():
    # Same pane as test_t2_fixed_window: sight_width_mm 1080, sight_height_mm
    # 1380 -> span is the shorter, 1080.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    sight_width_mm = result['payload']['sight_width_mm']
    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == min(sight_width_mm, sight_height_mm) == 1080
    assert result['span_basis'] is not None
    assert 'span_mm' not in result['payload']
    assert 'span_basis' not in result['payload']


def test_t15b_span_one_edge_unsupported_left():
    # left unsupported -> the intact opposite pair is top/bottom -> span is
    # the height (sight_height_mm).
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(left='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == sight_height_mm == 1380


def test_t15b2_span_one_edge_unsupported_right():
    # right unsupported -> same axis as left -> span is still the height.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(right='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == sight_height_mm == 1380


def test_t15b3_span_one_edge_unsupported_top():
    # top unsupported -> the intact opposite pair is left/right -> span is
    # the width (sight_width_mm).
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_width_mm = result['payload']['sight_width_mm']
    assert result['span_mm'] == sight_width_mm == 1080


def test_t15b4_span_one_edge_unsupported_bottom():
    # bottom unsupported -> same axis as top -> span is still the width.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(bottom='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_width_mm = result['payload']['sight_width_mm']
    assert result['span_mm'] == sight_width_mm == 1080


def test_t15b_span_basis_names_the_unsupported_edge_left():
    # Same pane/data as test_t15b_span_one_edge_unsupported_left - span_mm
    # unchanged, span_basis must name the specific unsupported edge rather
    # than a generic "one edge unsupported".
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(left='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == sight_height_mm == 1380
    assert result['span_basis'] == 'height (top and bottom edges supported, left edge unsupported)'


def test_t15b3_span_basis_names_the_unsupported_edge_top():
    # Same pane/data as test_t15b3_span_one_edge_unsupported_top.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    sight_width_mm = result['payload']['sight_width_mm']
    assert result['span_mm'] == sight_width_mm == 1080
    assert result['span_basis'] == 'width (left and right edges supported, top edge unsupported)'


def test_t15c_span_basis_names_both_unsupported_edges():
    # Same pane/data as test_t15c_span_left_and_right_unsupported - the
    # opposite-pair case names both unsupported edges.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(left='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == sight_height_mm == 1380
    assert result['span_basis'] == 'height (top and bottom edges supported; left and right edges unsupported)'


def test_t15d_span_basis_names_both_unsupported_edges():
    # Same pane/data as test_t15d_span_top_and_bottom_unsupported.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat', bottom='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    sight_width_mm = result['payload']['sight_width_mm']
    assert result['span_mm'] == sight_width_mm == 1080
    assert result['span_basis'] == 'width (left and right edges supported; top and bottom edges unsupported)'


def test_t15_span_basis_all_four_supported_unchanged():
    # The all-four-supported sentence must stay exactly as it was (task
    # explicitly says this sentence does not change) - same pane/data as
    # test_t15a_span_fully_framed_shorter_dimension.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['span_mm'] == 1080
    assert result['span_basis'] == 'shorter of 1080 x 1380 (all four edges supported)'


def test_t15c_span_left_and_right_unsupported():
    # left+right unsupported (the opposite pair) -> held pair is top/bottom
    # -> span is the height.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(left='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == sight_height_mm == 1380


def test_t15d_span_top_and_bottom_unsupported():
    # top+bottom unsupported (the opposite pair) -> held pair is left/right
    # -> span is the width.
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat', bottom='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['payload']['framing'] == 'partly'
    sight_width_mm = result['payload']['sight_width_mm']
    assert result['span_mm'] == sight_width_mm == 1080


def test_t15e_span_adjacent_pair_unsupported_none():
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'not_assessable'
    assert result['span_mm'] is None
    assert result['span_basis'] is None


def test_t15f_span_three_edges_unsupported_none():
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380,
                      unframedEdgeReasons=_edges(top='silicone-flat', left='silicone-flat', right='silicone-flat'))
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'not_assessable'
    assert result['span_mm'] is None
    assert result['span_basis'] is None


def test_t15g_span_louvre_pane():
    # Same pane as test_t10_louvre_pane: 1000 x 1000, fully framed.
    pane = make_pane(type='louvre', bladeWidthMM=150, bladeLengthMM=900)
    row = make_row(ffl_height_mm=0, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    assert result['method'] == 'louvre'
    sight_width_mm = result['payload']['sight_width_mm']
    sight_height_mm = result['payload']['sight_height_mm']
    assert result['span_mm'] == min(sight_width_mm, sight_height_mm) == 1000
    assert result['span_basis'] is not None


def test_t15h_span_sashless_matches_payload_span_mm_ox_window():
    # REAL export, same fixture/pane as test_t11a: payload span_mm 1050.
    # The decided rule keeps the existing sashless (held-edge) formula -
    # span_mm at the top level must equal the payload's own span_mm.
    export = load_fixture('sashless_ox_window.json')
    panes = export['system']['elevations'][0]['panes']
    sashless_pane = next(p for p in panes if p['sashless'])
    row = make_row(ffl_height_mm=0)
    result = translate_pane(sashless_pane, panes, None, row, NO_ANSWERS)

    assert result['status'] == 'ready'
    assert result['method'] == 'sashless'
    assert result['span_mm'] == result['payload']['span_mm'] == 1050
    assert result['span_basis'] is not None
    assert '1050' in result['span_basis']


def test_t15i_span_sashless_matches_payload_span_mm_double_hung():
    # REAL export, same fixture/panes as test_t11b: payload span_mm 1050
    # for both panes.
    export = load_fixture('sashless_double_hung.json')
    panes = export['system']['elevations'][0]['panes']
    row = make_row(ffl_height_mm=0)

    for pane in panes:
        result = translate_pane(pane, panes, None, row, NO_ANSWERS)
        assert result['status'] == 'ready'
        assert result['method'] == 'sashless'
        assert result['span_mm'] == result['payload']['span_mm'] == 1050
        assert result['span_basis'] is not None


def test_t15j_ctx_unchanged_for_fixed_pane():
    # Proves the ctx dict passed to determine_fixed() is byte-identical to
    # master's pre-span-change output - built from the SAME test_t2 pane/row
    # (xMM=60, yMM=60, widthMM=1080, heightMM=1380, ffl_height_mm=300,
    # residential), with the expected dict captured by running this exact
    # scenario against master before this branch's changes (span_mm/
    # span_basis were not added to it; every other key/value is unchanged).
    pane = make_pane(productClass='window', type='fixed',
                      xMM=60, yMM=60, widthMM=1080, heightMM=1380)
    row = make_row(ffl_height_mm=300, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    expected_ctx = {
        'opening_type': 'window', 'is_side_panel': False, 'is_louvre': False,
        'building_use': 'residential', 'is_bathroom': False, 'high_risk': False,
        'framing': 'fully', 'exposed_edges': None,
        'sight_width_mm': 1080, 'sight_height_mm': 1380,
        'panel_area_m2': 1.4904, 'panel_width_mm': 1080, 'sightline_mm': 360,
        'opaque_or_patterned': False, 'rail_present': False,
        'rail_upper_edge_mm': None, 'rail_lower_edge_mm': None,
        'level_difference_mm': None,
    }
    assert result['payload'] == expected_ctx


def test_t15k_ctx_unchanged_for_louvre_pane():
    # Same proof for the louvre ctx, built from the SAME test_t10 pane/row
    # (bladeWidthMM=150, bladeLengthMM=900, 1000x1000, ffl_height_mm=0,
    # residential), expected dict captured against master before this
    # branch's changes.
    pane = make_pane(type='louvre', bladeWidthMM=150, bladeLengthMM=900)
    row = make_row(ffl_height_mm=0, building_use='residential')
    result = translate_pane(pane, [pane], None, row, NO_ANSWERS)

    expected_ctx = {
        'opening_type': 'window', 'is_side_panel': False, 'is_louvre': True,
        'building_use': 'residential', 'is_bathroom': False, 'high_risk': False,
        'framing': 'fully', 'exposed_edges': None,
        'sight_width_mm': 1000, 'sight_height_mm': 1000,
        'panel_area_m2': 1.0, 'panel_width_mm': 1000, 'sightline_mm': 0,
        'opaque_or_patterned': False, 'rail_present': False,
        'rail_upper_edge_mm': None, 'rail_lower_edge_mm': None,
        'level_difference_mm': None,
        'blade_width_mm': 150, 'blade_length_mm': 900,
    }
    assert result['payload'] == expected_ctx
