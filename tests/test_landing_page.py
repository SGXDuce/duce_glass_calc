# AS 1288 Glass Thickness Calculator - Landing Page Route Tests
# Confirms the landing page shows the pathway tiles directly (no mode-select
# screen) and that the removed Configurator, schedule and system check
# routes are gone.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_landing_page.py -v

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from interfaces.flask_app import app as app_module

app = app_module.app


def get_client():
    app.config['TESTING'] = True
    return app.test_client()


def test_landing_page_shows_pathway_tiles_and_no_mode_select():
    # Hand reasoning: GET / renders index.html. PATHWAY_4_ENABLED is False
    # (shipped default), so tiles 1, 2 and 3 render and tile 4 does not.
    # The mode-select block and its /system-check link are removed, so
    # neither 'mode-select-view' nor '/system-check' may appear in the page.
    assert app_module.PATHWAY_4_ENABLED is False
    response = get_client().get('/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    for tile_id in ('tile-pathway1', 'tile-pathway2', 'tile-pathway3'):
        assert f'id="{tile_id}"' in body
    assert 'id="tile-pathway4"' not in body
    assert 'mode-select-view' not in body
    assert '/system-check' not in body


def test_removed_routes_are_gone():
    # Hand reasoning: none of these URL rules exist any more, so Flask
    # answers 404 for each GET. The POST URL also no longer exists as a
    # rule at all, so it is 404 too (405 would only appear if the rule
    # existed for another method).
    client = get_client()
    for url in ('/configurator', '/schedule', '/system-check'):
        assert client.get(url).status_code == 404, url
    assert client.post('/system-check/translate', json={}).status_code == 404
