# AS 1288 Glass Thickness Calculator - Window Schedule / Configurator Route Tests
# Thin translation-layer tests only: confirms /schedule and /configurator serve
# what they're supposed to and carry the required security header. Does not
# re-test the configurator's own internal logic (vendored, unmodified - see
# static/configurator/VARIANT_CHANGES.md) or any AS 1288 engine behaviour.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_schedule_routes.py -v

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interfaces.flask_app.app import app


def get_client():
    app.config['TESTING'] = True
    return app.test_client()


def test_schedule_page_loads():
    client = get_client()
    response = client.get('/schedule')
    assert response.status_code == 200
    assert b'Window Schedule' in response.data
    assert b'Add row' in response.data


def test_schedule_page_references_configurator_route():
    client = get_client()
    response = client.get('/schedule')
    assert b'/configurator' in response.data


def test_configurator_route_serves_vendored_file():
    client = get_client()
    response = client.get('/configurator')
    assert response.status_code == 200
    assert b'Configurator Prototype' in response.data


def test_configurator_route_sets_csp_header():
    client = get_client()
    response = client.get('/configurator')
    assert response.headers.get('Content-Security-Policy') == "frame-ancestors 'self'"


def test_configurator_route_serves_expected_schema_version():
    client = get_client()
    response = client.get('/configurator')
    assert b"schemaVersion: 5" in response.data
