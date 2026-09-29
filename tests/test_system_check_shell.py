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
    # tests/test_schedule_translation.py (test_t11a): span/sight_height_mm
    # 1050mm, held top/bottom (horizontal-slider).
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
    assert row['sight_height_mm'] == 1050


def test_schema_v6_double_hung_translated_as_before():
    # Matches the validated result in test_schedule_translation.py
    # (test_t11b): span/sight_width_mm 1050mm, held left/right
    # (vertical-slider pair).
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
        assert row['sight_width_mm'] == 1050
