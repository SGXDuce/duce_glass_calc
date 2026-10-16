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

    for fn, end in (('function setReclassified(', 'function setBathroom('),
                    ('function setOpeningType(', 'function setReclassified(')):
        body = src[src.index(fn):src.index(end)]
        assert "syncExposedRow('fixed')" in body and "syncExposedRow('louvre')" in body, fn