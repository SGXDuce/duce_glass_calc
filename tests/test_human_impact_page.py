# AS 1288 Glass Thickness Calculator - Human Impact Page Source Guard
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_human_impact_page.py

import os
import re

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                        'interfaces', 'flask_app', 'templates', 'human_impact.html')

INCOMPLETE_WORDING = "Incomplete: answer the questions listed below to see a result."


def test_page_inc_template_guard():
    """
    Reads human_impact.html as text. This proves wording and branch order
    only, NOT rendering: there is no JavaScript runtime in this suite, so
    the actual on-screen result must be checked by hand.

    Checks: the exact Incomplete wording is present; the outcome check for
    'incomplete' comes before the !result.scope check inside
    renderMethodResult; the incomplete branch never says "No requirement
    found"; and the .hi-verdict.incomplete style exists.
    """
    with open(TEMPLATE, encoding='utf-8') as f:
        src = f.read()

    assert INCOMPLETE_WORDING in src, "Incomplete wording missing"

    fn_start = src.index('function renderMethodResult(')
    body = src[fn_start:]
    inc_pos = body.index("result.outcome === 'incomplete'")
    scope_pos = body.index('!result.scope')
    assert inc_pos < scope_pos, "incomplete check must come before the !result.scope check"

    branch = body[inc_pos:scope_pos]
    assert 'No requirement found' not in branch, "incomplete branch must not say 'No requirement found'"
    assert 'hi-type-grid' not in branch and 'Apply to calculator' not in branch

    assert re.search(r'\.hi-verdict\.incomplete\s*\{', src), ".hi-verdict.incomplete style missing"


def _read_template():
    with open(TEMPLATE, encoding='utf-8') as f:
        return f.read()


def test_page_fr_nothing_preselected():
    """
    Source-text guard (no JavaScript runtime here): both framing answers start
    unanswered (null), the old three-way Framing toggle and its handlers are
    gone, and no default 'fully' framing is sent.
    """
    src = _read_template()
    state_start = src.index('const hiMethodState = {')
    state_block = src[state_start:src.index('};', state_start)]
    assert 'unframed_edges: null' in state_block, "fixed framing must start unanswered (null)"
    assert 'louvre_framing: null' in state_block, "louvre framing must start unanswered (null)"
    assert 'setFixedFraming' not in src, "old Fully/Partly/Unframed toggle must be gone"
    assert "framing: 'fully'" not in src and 'framing: "fully"' not in src
    assert 'hi-fixed-framing-' not in src and 'hi-louvre-framing-fully' not in src
    # Neither louvre button is rendered active from a fixed class.
    assert 'class="toggle-btn active" id="hi-louvre-layout' not in src
    assert 'None unframed (fully framed)' in src
    assert 'Treated as partly framed (two opposite edges).' in src


def test_page_fr_payload_and_exposed():
    """
    buildPayload sends unframed_edges and louvre_framing and no bare 'framing'
    key; an unticked last edge returns to null (not []); the exposed value is
    forced to 'n' whenever its row is hidden.
    """
    src = _read_template()
    start = src.index('function buildPayload()')
    body = src[start:src.index('// RUN CHECK', start)]
    assert 'unframed_edges: hiMethodState.fixed.unframed_edges' in body
    assert 'louvre_framing: hiMethodState.louvre.louvre_framing' in body
    assert not re.search(r'(?<![_a-z])framing:', body), "no bare 'framing' key in the payload"
    assert "exposedRowVisible('fixed') ? hiMethodState.fixed.exposed_edges : 'n'" in body
    assert "exposedRowVisible('louvre') ? hiMethodState.louvre.exposed_edges : 'n'" in body

    toggled = src[src.index('function onEdgeToggled('):src.index('function onNoneUnframedToggled(')]
    assert 'next.length ? next : null' in toggled, "unticking the last edge must return to null"
    none_fn = src[src.index('function onNoneUnframedToggled('):src.index('function syncEdgeChecks(')]
    assert 'checked ? [] : null' in none_fn
    sync = src[src.index('function syncExposedRow('):src.index('function onEdgeToggled(')]
    assert "exposed_edges = 'n'" in sync


def test_page_fr_exposed_row_always_built():
    """
    Source-text guard only (no JavaScript runtime here): proves structure, not
    on-screen behaviour. The exposed-edges row is built for both cards
    whatever the opening type is when the card is drawn (hidden by default
    through exposedRowVisible), and both the doorway question and the opening
    type call syncExposedRow for the fixed and louvre methods.
    """
    src = _read_template()
    build = src[src.index('function buildExposedRow('):src.index('function buildFixedCard(')]
    assert 'if (!isSidePanel) return' not in build, "row must not depend on the opening type at draw time"
    assert "exposedRowVisible(method) ? '' : 'hidden'" in build
    assert "buildExposedRow('fixed')" in src and "buildExposedRow('louvre')" in src

    for fn, end in (('function setReclassified(', 'function setRoom('),
                    ('function setOpeningType(', 'function setReclassified(')):
        body = src[src.index(fn):src.index(end)]
        assert "syncExposedRow('fixed')" in body and "syncExposedRow('louvre')" in body, fn


def test_page_room_nothing_preselected():
    """
    Source-text guard only (no JavaScript runtime here): the room question
    starts unanswered (null) with three answers including Kitchen and none
    pre-selected, the old bathroom Yes/No toggle is gone, and the payload
    sends room and no is_bathroom.
    """
    src = _read_template()
    state_start = src.index('const hiState = {')
    state_block = src[state_start:src.index('};', state_start)]
    assert 'room: null' in state_block, "room must start unanswered (null)"
    assert 'isBathroom' not in src and 'is_bathroom' not in src and 'setBathroom' not in src
    assert 'hi-bathroom-no' not in src and 'hi-bathroom-yes' not in src
    for label in ('Bathroom, ensuite or spa room', 'Kitchen', 'Neither'):
        assert label in src, label
    for r in ('bathroom', 'kitchen', 'neither'):
        assert f'id="hi-room-{r}" onclick="setRoom(' in src
        assert f'class="toggle-btn active" id="hi-room-{r}"' not in src, "no room answer may start active"
    payload = src[src.index('return {\n        opening_type: hiState.openingType'):]
    assert 'room: hiState.room' in payload[:400]


def test_page_room_label_door():
    """
    Source-text guard only: the room label mentions kitchens, and for a door
    it asks about the room the door serves or opens into.
    """
    src = _read_template()
    assert 'Is the glazing in a bathroom, ensuite, spa room or kitchen?' in src
    update = src[src.index('function updateRoomLabel('):]
    update = update[:update.index('\n}\n')]
    assert "hiState.openingType === 'door'" in update
    assert 'Room the door serves or opens into' in update
    set_opening = src[src.index('function setOpeningType('):src.index('function setReclassified(')]
    assert 'updateRoomLabel()' in set_opening


def test_page_room_label_set_on_load():
    """
    Source-text guard only (no JavaScript runtime here): proves structure, not
    on-screen behaviour. The page's load handler calls updateRoomLabel(), so
    the room label already matches the default opening type (Door) on first
    load, before setOpeningType() has been used.
    """
    src = _read_template()
    start = src.index("document.addEventListener('DOMContentLoaded'")
    init = src[start:src.index('});', start)]
    assert 'updateRoomLabel()' in init
    assert 'buildMethodCards()' in init, "must sit with the initial card build"
    assert "openingType: 'door'" in src, "label depends on the default opening type"