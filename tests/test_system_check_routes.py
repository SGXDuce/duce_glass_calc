# AS 1288 Glass Thickness Calculator - System Check Mode-Select Route Tests
# Confirms the mode-select screen and /system-check route are fully inert
# when SYSTEM_CHECK_ENABLED is False (the shipped default), and behave as
# designed when the flag is flipped on for a request. Does not touch any
# pathway logic, engine file, or existing route.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_system_check_routes.py -v

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interfaces.flask_app import app as app_module

app = app_module.app


def get_client():
    app.config['TESTING'] = True
    return app.test_client()


def test_flag_off_landing_unchanged():
    client = get_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b"showPathway('pathway1')" in response.data
    assert b"showPathway('pathway2')" in response.data
    assert b"showPathway('pathway3')" in response.data
    assert b'id="mode-select-view"' not in response.data
    assert b'Check a single glass' not in response.data
    assert b'Build a system' not in response.data


def test_flag_off_system_check_404():
    client = get_client()
    response = client.get('/system-check')
    assert response.status_code == 404


def test_flag_on_shows_mode_select():
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/')
        assert response.status_code == 200
        assert b'id="mode-select-view"' in response.data
        assert b'Check a single glass' in response.data
        assert b'Build a system' in response.data
        assert b"showPathway('pathway1')" in response.data
        assert b"showPathway('pathway2')" in response.data
        assert b"showPathway('pathway3')" in response.data
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_flag_on_system_check_page_loads():
    # The placeholder "under construction" text was replaced by the real
    # page shell (System check step 2) - see tests/test_system_check_shell.py
    # for the shell's own content assertions. This test now only confirms
    # the route still loads at 200 when the flag is on, which is what it
    # was always really guarding.
    app_module.SYSTEM_CHECK_ENABLED = True
    try:
        client = get_client()
        response = client.get('/system-check')
        assert response.status_code == 200
    finally:
        app_module.SYSTEM_CHECK_ENABLED = False


def test_flag_restored_to_false():
    assert app_module.SYSTEM_CHECK_ENABLED is False
