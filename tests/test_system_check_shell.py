# AS 1288 Glass Thickness Calculator - System Check Shell Tests
#
# Covers Step 2 of System check mode: the page shell (geometry only - no
# wind calculation, no human impact call, no glass thickness result). Tests
# the /system-check page itself (still gated behind SYSTEM_CHECK_ENABLED)
# and the new /system-check/translate route that turns a Configurator
# export into a geometry-only pane table via engine/schedule/translation.py.
#
# Does not touch schedule.html, the engine, or any data CSV. Real fixtures
# under tests/fixtures/ are reused unmodified except for a copied-and-edited
# schemaVersion field, per the task's own instruction not to invent new
# geometry numbers.
#
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_system_check_shell.py -v

import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interfaces.flask_app import app as app_module

app = app_module.app

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename), encoding='utf-8') as f:
        return json.load(f)


def get_client():
    app.config['TESTING'] = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Page route - flag gating, fixed banner text, schema-constant plumbing
# ---------------------------------------------------------------------------

def test_flag_off_system_check_still_404():
    # Must still pass exactly as before - this shell must not change the
    # flag-off behaviour already locked in by test_system_check_routes.py.
    client = get_client()
    response = client.get('/system-check')
    assert response.status_code == 404


def test_flag_on_page_shows_no_check_banner():
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        assert b'No glass check has been run. Inputs are collected in the next step.' in response.data
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_schema_constant_reaches_page_with_no_second_hand_typed_number():
    # The constant must reach the rendered page (as CONFIGURATOR_SCHEMA_VERSION
    # = 6 in the page's own <script>, sourced from Jinja), and the page source
    # must not ALSO contain some other hand-typed schema-version number
    # (e.g. a stray "schemaVersion: 6" or "=== 6" literal, the pattern this
    # same page's postMessage handshake code uses to check messages against
    # the constant, not a second copy of the constant itself).
    import re

    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        html = response.data.decode('utf-8')
        expected = f'CONFIGURATOR_SCHEMA_VERSION = {app_module.CONFIGURATOR_SCHEMA_VERSION}'
        assert expected in html
        # Exactly one assignment of a numeric literal to
        # CONFIGURATOR_SCHEMA_VERSION should appear in the whole page.
        assignments = re.findall(r'CONFIGURATOR_SCHEMA_VERSION\s*=\s*\d+', html)
        assert assignments == [expected]
        # No other bare numeric literal should be compared/assigned against
        # a schema-version-shaped identifier anywhere in the page source.
        assert re.search(r'schemaVersion["\']?\s*[:=]\s*\d+', html) is None
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_flag_restored_to_false():
    assert app_module.SYSTEM_CHECK_ENABLED is False


def test_back_to_start_link_present():
    # Cosmetic addition: a plain "Back to start" link to "/" - the old
    # placeholder page had one and it was lost when the shell replaced it.
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Back to start' in html
        assert 'href="/"' in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_daylight_size_header_not_sight_size():
    # Cosmetic wording update: the pane table's column header must now read
    # "Daylight size", not "Sight size". Internal field names (sight_width_mm
    # etc.) are unaffected and not checked here.
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Daylight size (W x H mm)' in html
        assert 'Sight size' not in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_render_system_increments_seq_before_first_early_return():
    # Source-level regression test only - this is JavaScript running in a
    # browser, which the Flask test client cannot execute, so this does NOT
    # run renderSystem() or prove its runtime behaviour. It only guards the
    # ORDERING of two lines in the served page's source: the
    # `translateRequestSeq += 1` increment inside renderSystem() must appear
    # BEFORE that function's first early `return` (the `if (!state.export)`
    # block), so that call is counted as stale-invalidating even when it
    # exits early with no state.export, or later with an empty/invalid
    # height field, rather than only when it goes on to send a fetch
    # request. This is the ordering the bugfix depends on: without it, an
    # in-flight request from an earlier renderSystem() call can still match
    # the "current" sequence number by the time its response arrives, and
    # render the pane table over a prompt the user is now looking at.
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        render_system_start = html.index('function renderSystem()')
        increment_pos = html.index('translateRequestSeq += 1', render_system_start)
        first_early_return_pos = html.index(
            'if (!state.export) {', render_system_start
        )
        assert increment_pos < first_early_return_pos, (
            'translateRequestSeq must be incremented before renderSystem()\'s '
            'first early return (if (!state.export)), not only later in the '
            'function - otherwise an in-flight request from an earlier call '
            'is not invalidated by a call that exits early.'
        )
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


# ---------------------------------------------------------------------------
# Explicit-trigger height field (replaces the debounce) - source-level tests
# only. This is JavaScript running in a browser, which the Flask test client
# cannot execute, so none of these run onFflHeightInput()/onFflHeightKeydown()/
# renderSystem() or prove runtime behaviour - they only check that the served
# page's source contains the expected strings/handlers.
# ---------------------------------------------------------------------------

def test_update_table_button_present():
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Update table' in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_height_field_has_enter_keydown_handler():
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'onkeydown="onFflHeightKeydown(event)"' in html
        assert "event.key === 'Enter'" in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_debounce_constant_removed():
    # The debounce this task replaces must be gone entirely, not just unused.
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'FFL_HEIGHT_DEBOUNCE_MS' not in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_height_changed_prompt_text_present():
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Height changed. Press Enter or click Update table' in html
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_input_handler_increments_seq():
    # String check confined to onFflHeightInput()'s own body: the increment
    # must be inside that function, not merely present somewhere on the page
    # (renderSystem() already has its own, separate increment).
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        fn_start = html.index('function onFflHeightInput()')
        fn_end = html.index('\n}', fn_start)
        fn_body = html[fn_start:fn_end]
        assert 'translateRequestSeq += 1' in fn_body
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


# ---------------------------------------------------------------------------
# /system-check/translate - schema-version guard using real fixtures
# ---------------------------------------------------------------------------

def _row():
    return {
        'ffl_height_mm': 0,
        'building_use': 'residential',
        'is_bathroom': False,
        'high_risk': False,
    }


def test_schema_v5_marks_sashless_pane_not_assessable_ox_window():
    export = load_fixture('sashless_ox_window.json')
    old_export = copy.deepcopy(export)
    old_export['schemaVersion'] = 5  # only the field the task allows changing

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': old_export['schemaVersion'],
        'system': old_export['system'],
        'row': _row(),
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    panes_by_id = {p['pane_id']: p for p in data['panes']}
    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    assert panes_by_id[sashless_pane_id]['status'] == 'not_assessable'
    assert 'schema' in ' '.join(panes_by_id[sashless_pane_id]['reasons']).lower()


def test_schema_v5_marks_sashless_pane_not_assessable_double_hung():
    export = load_fixture('sashless_double_hung.json')
    old_export = copy.deepcopy(export)
    old_export['schemaVersion'] = 5

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': old_export['schemaVersion'],
        'system': old_export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    for pane in export['system']['elevations'][0]['panes']:
        assert pane['sashless'] is True
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'not_assessable'


def test_missing_schema_version_treated_as_below_6():
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        # schemaVersion omitted entirely
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane_id)
    assert row['status'] == 'not_assessable'


def test_non_integer_schema_version_treated_as_below_6():
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': '6',  # string, not an int - must not be accepted
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    for pane in export['system']['elevations'][0]['panes']:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'not_assessable'


def test_schema_v6_ox_window_translated_as_before():
    # At the current schema version, the sashless pane must translate
    # normally - matching the already-validated result in
    # tests/test_schedule_translation.py (test_t11a): span_mm 1050mm, held
    # top/bottom (horizontal-slider).
    #
    # UPDATED this task: sight_height_mm/sight_width_mm/sightline_mm are no
    # longer backfilled for a sashless row (that recompute used a
    # width/height-based formula that did not know which edges were held -
    # see app.py's _pane_table_row() and _sashless_span_mm()'s own
    # docstring in engine/schedule/translation.py) - span_mm (from the
    # translator's own payload) is the geometry fact asserted here instead.
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    sashless_pane = next(
        p for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane['id'])
    assert row['status'] == 'ready'
    assert row['method'] == 'sashless'
    assert row['span_mm'] == 1050
    assert row['sight_height_mm'] is None


def test_schema_v6_double_hung_translated_as_before():
    # Matches the validated result in test_schedule_translation.py
    # (test_t11b): span_mm 1050mm, held left/right (vertical-slider pair).
    #
    # UPDATED this task: see test_schema_v6_ox_window_translated_as_before
    # above - sight_width_mm is no longer backfilled for a sashless row,
    # span_mm is asserted instead.
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    for pane in export['system']['elevations'][0]['panes']:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'ready'
        assert row['method'] == 'sashless'
        assert row['span_mm'] == 1050
        assert row['sight_width_mm'] is None


# ---------------------------------------------------------------------------
# Floor-height (ffl_height_mm) field, exact schema match, span_mm column -
# the three fixes this task adds. The page's own "must not call translate
# until the field is filled" behaviour is client-side JS and is not directly
# testable from here (see the last test in this section and STEP D's report
# for what that leaves unverified) - what IS tested here is the route's own
# behaviour when the field is missing, which the reproduction step (STEP A)
# showed marks every pane not_assessable with blank geometry.
# ---------------------------------------------------------------------------

def test_translate_with_empty_row_marks_every_pane_not_assessable_blank_geometry():
    # This is exactly what the page used to send before the floor-height
    # field existed (row: {}), reproduced here so the route's behaviour with
    # no ffl_height_mm stays pinned: every pane (sashless or not) comes back
    # not_assessable with blank sight/sightline geometry, because
    # translate_pane() cannot compute sightline_mm without ffl_height_mm
    # (engine/schedule/translation.py's _sightline_mm() returns None, which
    # translate_pane() treats as not_assessable for every pane, not just
    # sashless ones).
    #
    # What this test does NOT and CANNOT verify: that the page itself
    # refuses to call this route until the field is filled and valid. That
    # gating (getFflHeightMM()/renderSystem() in system_check.html) runs in
    # browser JS with no server round-trip when the field is empty, so it
    # is outside what a Flask test-client request can observe - see STEP D.
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': {},  # no ffl_height_mm - the page must never send this now
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    for pane in export['system']['elevations'][0]['panes']:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'not_assessable'
        assert row['sight_width_mm'] is None
        assert row['sight_height_mm'] is None
        assert row['sightline_mm'] is None


def test_schema_v7_newer_than_current_marks_sashless_pane_not_assessable():
    # Exact-match requirement: a NEWER schema version (not just older) must
    # also be treated as non-current. Before this fix the guard used
    # `raw_version >= CONFIGURATOR_SCHEMA_VERSION`, which would have wrongly
    # accepted 7 as current.
    export = load_fixture('sashless_ox_window.json')
    newer_export = copy.deepcopy(export)
    newer_export['schemaVersion'] = 7

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': newer_export['schemaVersion'],
        'system': newer_export['system'],
        'row': _row(),
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane_id)
    assert row['status'] == 'not_assessable'
    assert 'does not match' in ' '.join(row['reasons']).lower()


def test_schema_v6_span_mm_matches_test_schedule_translation_ox_window():
    # span_mm in the row must equal the translator's own span_mm - the value
    # already validated in tests/test_schedule_translation.py::test_t11a
    # (1050mm, held top/bottom). Not re-derived here; just checked that the
    # route's response carries the same number the engine test already
    # locks in.
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane_id)
    assert row['span_mm'] == 1050


def test_schema_v6_span_mm_matches_test_schedule_translation_double_hung():
    # Matches tests/test_schedule_translation.py::test_t11b (1050mm, held
    # left/right) for both panes in this fixture.
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    for pane in export['system']['elevations'][0]['panes']:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['span_mm'] == 1050


def test_sashless_rows_have_none_sight_and_sightline_fields():
    # For sashless panes, the shell must not recompute sight_width_mm/
    # sight_height_mm/sightline_mm from sashEdgesMM/yMM (that formula did
    # not know which edges were held and could disagree with the
    # translator's own span_mm) - these three fields must come back None
    # for a sashless row, straight from translate_pane()'s own payload
    # (which never sets them for a sashless pane), not backfilled.
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane_id)
    assert row['status'] == 'ready'
    assert row['method'] == 'sashless'
    assert row['sight_width_mm'] is None
    assert row['sight_height_mm'] is None
    assert row['sightline_mm'] is None
    assert row['span_mm'] == 1050


def test_non_sashless_pane_sightline_80mm_hand_built_lone_slider_door():
    # HAND-BUILT pane, wrapped into a minimal system object for this route -
    # NOT a real Configurator export. Values are claimed from a real export
    # per tests/test_schedule_translation.py::test_t1_lone_horizontal_slider_door
    # (its own docstring/comment there calls it a "REAL verified export
    # value", handover section 14): a door, horizontal-slider,
    # xMM=60, yMM=40, widthMM=1680, heightMM=2020, all four sash edges 40mm.
    # CORRECTION (Sahil's browser check): the real Configurator export gave
    # a daylight width of 1640mm, not the 1600mm this object's widthMM 1680
    # would produce (1680 - 40 - 40) - so this widthMM is probably NOT the
    # real export's actual value. Only sightline (80) and the height figures
    # match the real export; width was never independently confirmed here.
    # With ffl_height_mm=0, that test asserts sightline_mm == 80 (0 + yMM 40
    # + bottom sash edge 40). This test re-uses the exact same numbers,
    # wrapped in a one-elevation/one-pane system dict, to confirm this
    # route's non-sashless path (which does NOT recompute anything - it
    # takes payload['sightline_mm'] straight from translate_pane()) returns
    # that same 80mm through the HTTP layer.
    pane = {
        'id': 'F',
        'productClass': 'door',
        'type': 'horizontal-slider',
        'xMM': 60, 'yMM': 40,
        'widthMM': 1680, 'heightMM': 2020,
        'bladeWidthMM': None, 'bladeLengthMM': None,
        'sashEdgesMM': {'top': 40, 'bottom': 40, 'left': 40, 'right': 40},
        'unframedEdgeReasons': {'top': None, 'bottom': None, 'left': None, 'right': None},
        'sashless': False,
    }
    system = {
        'angledJoinAngleDeg': None,
        'elevations': [
            {'panes': [pane]},
        ],
    }

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': app_module.CONFIGURATOR_SCHEMA_VERSION,
        'system': system,
        'row': {'ffl_height_mm': 0, 'building_use': 'residential',
                 'is_bathroom': False, 'high_risk': False},
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    row = next(p for p in data['panes'] if p['pane_id'] == 'F')
    assert row['status'] == 'ready'
    assert row['sightline_mm'] == 80


def test_non_sashless_ready_pane_has_span_mm_and_span_basis():
    # Span (mm) must be populated for every ready pane, not just sashless
    # ones (this task's change) - same HAND-BUILT pane/values as
    # test_non_sashless_pane_sightline_80mm_hand_built_lone_slider_door
    # above. NOT a real Configurator export: per that test's own comment,
    # Sahil's browser check found the real export's daylight width was
    # 1640mm, not the 1600mm this object's widthMM 1680 computes
    # (1680 - 40 - 40) - so this pane's widthMM is probably not the real
    # export's actual value. Only sightline (80) and the height match the
    # real export. fully framed (all sashEdgesMM 40, no
    # unframedEdgeReasons), sight_width_mm 1680 - 40 - 40 = 1600,
    # sight_height_mm 2020 - 40 - 40 = 1940 -> span is the shorter, 1600
    # (a value this hand-built object actually produces, whatever the real
    # export's own width is).
    pane = {
        'id': 'F',
        'productClass': 'door',
        'type': 'horizontal-slider',
        'xMM': 60, 'yMM': 40,
        'widthMM': 1680, 'heightMM': 2020,
        'bladeWidthMM': None, 'bladeLengthMM': None,
        'sashEdgesMM': {'top': 40, 'bottom': 40, 'left': 40, 'right': 40},
        'unframedEdgeReasons': {'top': None, 'bottom': None, 'left': None, 'right': None},
        'sashless': False,
    }
    system = {
        'angledJoinAngleDeg': None,
        'elevations': [
            {'panes': [pane]},
        ],
    }

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': app_module.CONFIGURATOR_SCHEMA_VERSION,
        'system': system,
        'row': {'ffl_height_mm': 0, 'building_use': 'residential',
                 'is_bathroom': False, 'high_risk': False},
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    row = next(p for p in data['panes'] if p['pane_id'] == 'F')
    assert row['status'] == 'ready'
    assert row['method'] == 'fixed'
    assert row['span_mm'] == 1600
    assert row['span_basis'] is not None


# ---------------------------------------------------------------------------
# Schema-mismatch guard must also clear span_mm/span_basis for a sashless
# pane it demotes to not_assessable - regression for the defect where the
# guard cleared payload/method/status but left the top-level span_mm/
# span_basis translate_pane() had already computed (a not_assessable row
# showing a span, e.g. 1050, from before the guard downgraded it).
# ---------------------------------------------------------------------------

def _assert_all_sashless_panes_span_none(data, export):
    sashless_panes = [
        pane for pane in export['system']['elevations'][0]['panes']
        if pane['sashless']
    ]
    assert sashless_panes  # both fixtures have at least one
    for pane in sashless_panes:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'not_assessable'
        assert row['span_mm'] is None
        assert row['span_basis'] is None


def test_schema_v5_sashless_span_cleared_ox_window():
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': 5,
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_schema_v5_sashless_span_cleared_double_hung():
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': 5,
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_schema_v7_sashless_span_cleared_ox_window():
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': 7,
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_schema_v7_sashless_span_cleared_double_hung():
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': 7,
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_missing_schema_version_sashless_span_cleared_ox_window():
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        # schemaVersion omitted entirely
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_missing_schema_version_sashless_span_cleared_double_hung():
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        # schemaVersion omitted entirely
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_string_schema_version_6_sashless_span_cleared_ox_window():
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': '6',  # string, not an int - must not be accepted
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_string_schema_version_6_sashless_span_cleared_double_hung():
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': '6',  # string, not an int - must not be accepted
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True
    _assert_all_sashless_panes_span_none(data, export)


def test_schema_v6_sashless_span_still_1050_ox_window():
    # At the current schema version the guard never fires - span_mm must
    # still be populated (1050), same value already locked in by
    # test_schema_v6_span_mm_matches_test_schedule_translation_ox_window.
    export = load_fixture('sashless_ox_window.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    sashless_pane_id = next(
        p['id'] for p in export['system']['elevations'][0]['panes'] if p['sashless']
    )
    row = next(p for p in data['panes'] if p['pane_id'] == sashless_pane_id)
    assert row['status'] == 'ready'
    assert row['span_mm'] == 1050
    assert row['span_basis'] is not None


def test_schema_v6_sashless_span_still_1050_double_hung():
    # Matches test_schema_v6_span_mm_matches_test_schedule_translation_double_hung.
    export = load_fixture('sashless_double_hung.json')
    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': export['schemaVersion'],
        'system': export['system'],
        'row': _row(),
    })
    data = response.get_json()
    assert data['success'] is True

    for pane in export['system']['elevations'][0]['panes']:
        row = next(p for p in data['panes'] if p['pane_id'] == pane['id'])
        assert row['status'] == 'ready'
        assert row['span_mm'] == 1050
        assert row['span_basis'] is not None


def test_not_assessable_or_needs_answer_pane_never_has_span_hand_built():
    # Defence-in-depth proof at _pane_table_row() level, independent of the
    # schema guard above: a hand-built pane whose framing is not_assessable
    # (adjacent unsupported edges - top and right) must never carry a
    # span_mm, regardless of what translate_pane() itself returned at the
    # top level.
    not_assessable_pane = {
        'id': 'NA',
        'productClass': 'window',
        'type': 'fixed',
        'xMM': 60, 'yMM': 60,
        'widthMM': 1080, 'heightMM': 1380,
        'bladeWidthMM': None, 'bladeLengthMM': None,
        'sashEdgesMM': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
        'unframedEdgeReasons': {
            'top': 'silicone-flat', 'bottom': None,
            'left': None, 'right': 'silicone-flat',
        },
        'sashless': False,
    }
    # frame-off with no answer supplied -> needs_answer (no answers are
    # ever sent by this route, so this always resolves to needs_answer).
    needs_answer_pane = {
        'id': 'NEEDS',
        'productClass': 'window',
        'type': 'fixed',
        'xMM': 60, 'yMM': 60,
        'widthMM': 1080, 'heightMM': 1380,
        'bladeWidthMM': None, 'bladeLengthMM': None,
        'sashEdgesMM': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
        'unframedEdgeReasons': {
            'top': None, 'bottom': None,
            'left': 'frame-off', 'right': None,
        },
        'sashless': False,
    }
    system = {
        'angledJoinAngleDeg': None,
        'elevations': [
            {'panes': [not_assessable_pane, needs_answer_pane]},
        ],
    }

    client = get_client()
    response = client.post('/system-check/translate', json={
        'schemaVersion': app_module.CONFIGURATOR_SCHEMA_VERSION,
        'system': system,
        'row': {'ffl_height_mm': 0, 'building_use': 'residential',
                 'is_bathroom': False, 'high_risk': False},
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

    na_row = next(p for p in data['panes'] if p['pane_id'] == 'NA')
    assert na_row['status'] == 'not_assessable'
    assert na_row['span_mm'] is None
    assert na_row['span_basis'] is None

    needs_row = next(p for p in data['panes'] if p['pane_id'] == 'NEEDS')
    assert needs_row['status'] == 'needs_answer'
    assert needs_row['span_mm'] is None
    assert needs_row['span_basis'] is None
