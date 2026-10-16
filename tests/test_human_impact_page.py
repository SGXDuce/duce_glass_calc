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
