"""Browser regression test for the Configurator's Sash/Leaf size / Daylight size columns (step 5b).

Builds five saved systems by clicking through the real Configurator UI in headless Chromium,
reads the pane table, then exports and compares each export with its saved safety-net file.

Run from the repo root with the project venv:
    .venv\\Scripts\\python tools\\ui_regression.py

Needs: pip install playwright ; python -m playwright install chromium
SYSTEM_CHECK_ENABLED is switched on in the server process only; no file is changed.
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAFETY_DIR = os.path.join(ROOT, 'configurator_safety_net_v6')
PORT = 5001
URL = 'http://127.0.0.1:%d/configurator' % PORT
OUT_DIR = os.path.join(tempfile.gettempdir(), 'ui_regression_exports')

# Expected table values: pane id -> (sash/leaf size, daylight size).
FILES = [
    ('13', 'safety_net_v6_13_sliders_both_sides_of_mullion.json',
     {'.L': ('940 x 2020', '860 x 1940'), '.R': ('780 x 2020', '700 x 1940')}, False),
    ('11', 'safety_net_v6_11_no_frame_slider_1680x1980.json',
     {'F': ('1680 x 1980', '1600 x 1900')}, False),
    ('10', 'safety_net_v6_10_slider_beside_mullion_980.json',
     {'.L': ('900 x 1980', '900 x 1980'), '.R': ('780 x 2020', '700 x 1940')}, False),
    ('08', 'safety_net_v6_08_sashless_OX_840_900.json',
     {'.R': ('840 x 1980', '840 x 1980'), '.S': ('900 x 1980', '900 x 1950')}, False),
    ('09', 'safety_net_v6_09_sashless_double_hung_1020.json',
     {'.S': ('1680 x 1020', '1650 x 1020'), '.R': ('1680 x 1020', '1650 x 1020')}, False),
]
# File 14 (no outer frame, two sliders beside a mullion). The expected numbers are Claude's
# arithmetic, NOT hand values: no frame means the opening is the full 1800 x 2100; mullion
# centre 980, thickness 40, so .L is 960 wide and .R is 800 wide, both 2100 high; sash edges 40.
# (An earlier draft said 780 for .R; that was the framed file 13 value, corrected by Sahil.)
# BEFORE step 5c-2 (no tuck-in with no frame): .L 960 x 2100 / 880 x 2020, .R 800 x 2100 / 720 x 2020.
# AFTER step 5c-2 each slider tucks 20 mm behind the mullion (left/right only): .L is 960 + 20 =
# 980 wide, .R is 800 + 20 = 820 wide, daylight is that less the 40 mm sash edges each side:
# .L 980 x 2100 / 900 x 2020, .R 820 x 2100 / 740 x 2020.
FILE_14_BEFORE_NAME = 'safety_net_v6_14_no_frame_two_sliders_mullion_BEFORE_5c2.json'
FILES.append(('14', 'safety_net_v6_14_no_frame_two_sliders_mullion_AFTER_5c2.json',
              {'.L': ('980 x 2100', '900 x 2020'), '.R': ('820 x 2100', '740 x 2020')}, False))
# Preset files 07, 02, 06 and 12 (step 4 coverage). Expected table values are read from the saved
# export, Claude's arithmetic, not Sahil's hand values: sash/leaf size = widthMM x heightMM; daylight =
# those less sashEdgesMM (a fixed pane has sash edges 0, so its daylight equals its size).
#   07 and 02 (framed OX): .R fixed 860 x 1980 (edges 0); .S slider 920 x 2020, edges 40 -> 840 x 1940.
#   06 (framed double-hung): .S and .R both 1720 x 1040, edges 40 -> 1640 x 960.
#   12 (no-frame double-hung, 1680 x 1980): .S and .R both 1680 x 1020, edges 40 -> 1600 x 940.
FILES.append(('07', 'safety_net_v6_07_framed_OX_window_860_920.json',
              {'.R': ('860 x 1980', '860 x 1980'), '.S': ('920 x 2020', '840 x 1940')}, False))
FILES.append(('02', 'safety_net_v6_02_ox_door_860_920.json',
              {'.R': ('860 x 1980', '860 x 1980'), '.S': ('920 x 2020', '840 x 1940')}, False))
FILES.append(('06', 'safety_net_v6_06_framed_double_hung_1680x1980.json',
              {'.S': ('1720 x 1040', '1640 x 960'), '.R': ('1720 x 1040', '1640 x 960')}, False))
FILES.append(('12', 'safety_net_v6_12_no_frame_double_hung_1680x1980.json',
              {'.S': ('1680 x 1020', '1600 x 940'), '.R': ('1680 x 1020', '1600 x 940')}, False))
NOTE_TEXT = '* Sashless: capping deduction not applied yet.'

fallback_used = []   # (file, what) pairs where a page function replaced a real click


class LabelNotFound(Exception):
    pass


def norm(text):
    return ' '.join(text.replace('×', 'x').split())


# ---------------------------------------------------------------- server

def start_server():
    code = ("from interfaces.flask_app import app as m; m.SYSTEM_CHECK_ENABLED = True; "
            "m.app.run(host='127.0.0.1', port=%d, debug=False, use_reloader=False)" % PORT)
    proc = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if proc.poll() is not None:
            raise RuntimeError('Flask server exited early (code %s)' % proc.returncode)
        try:
            if urllib.request.urlopen(URL, timeout=2).status == 200:
                return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError('Flask server did not answer on ' + URL)


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------- page helpers

def visible_button_texts(page):
    return [norm(t) for t in page.locator('#toolbar button, #toolbar .preset-icon-label, button').all_inner_texts() if t.strip()]


def need(page, locator, what):
    """Return locator if it matches exactly one-or-more elements, else raise with nearby labels."""
    if locator.count() == 0:
        raise LabelNotFound('%s not found. Visible button labels: %s' % (what, sorted(set(visible_button_texts(page)))))
    return locator.first


def click_button(page, text, scope='#toolbar'):
    btn = need(page, page.locator(scope + ' button').filter(has_text=text), 'button "%s"' % text)
    # exact match among candidates (filter has_text is a substring match)
    exact = [b for b in page.locator(scope + ' button').all() if norm(b.inner_text()) == text]
    if not exact:
        raise LabelNotFound('button "%s" not found exactly. Closest: %s' % (text, [norm(b.inner_text()) for b in page.locator(scope + ' button').all()]))
    exact[0].click()


def click_window_sash_type(page, label):
    """Click a type button inside the "Window sashes" group (Door panels has same-named buttons)."""
    row = page.locator('#toolbar .toolbar-row').filter(has=page.locator('.toolbar-group-label', has_text='Window sashes'))
    need(page, row, 'row "Window sashes"')
    for b in row.locator('button').all():
        if norm(b.inner_text()) == label:
            b.click()
            return
    raise LabelNotFound('"%s" not in Window sashes group. Found: %s' % (label, [norm(b.inner_text()) for b in row.locator('button').all()]))


def select_pane(page, index, file_id):
    """Real click on the index-th pane; falls back to the page's own functions if it didn't select."""
    panes = page.locator('#diagram .pane')
    if panes.count() <= index:
        raise LabelNotFound('pane #%d not in drawing (%d panes found)' % (index, panes.count()))
    panes.nth(index).click()
    if 'Click a region to select it' in page.locator('#toolbar').inner_text():
        path = page.evaluate('() => activeElevation().lastLeaves[%d].path' % index)
        page.evaluate('(p) => { const ev = activeElevation(); ev.pendingSplit = null; ev.selected = { path: p, isBar: false }; render(); }', path)
        fallback_used.append((file_id, 'select pane %d via activeElevation().selected + render()' % index))


def set_number(page, selector, value):
    box = page.locator(selector)
    need(page, box, 'input ' + selector)
    box.fill(str(value))
    box.press('Tab')


def set_overall(page, w, h):
    set_number(page, '#frameW', w)
    set_number(page, '#frameH', h)


def add_frame(page):
    click_button(page, 'Add outer frame', scope='body')


def add_mullion(page, file_id):
    select_pane(page, 0, file_id)
    click_button(page, 'Add mullion (split | )')
    set_number(page, '#posInput', 980)
    set_number(page, '#thickInput', 40)
    click_button(page, 'Confirm split')


def pick_preset(page, heading, label):
    xp = ("//div[@id='toolbar']/div[contains(@class,'toolbar-group-label')][normalize-space()='%s']"
          "/following-sibling::div[1]//button[.//div[contains(@class,'preset-icon-label')][normalize-space()='%s']]" % (heading, label))
    btn = page.locator('xpath=' + xp)
    if btn.count() == 0:
        headings = page.locator('#toolbar .toolbar-group-label').all_inner_texts()
        raise LabelNotFound('preset "%s" under "%s" not found. Headings seen: %s' % (label, heading, headings))
    btn.first.click()


def ensure_value(page, selector, target, what):
    box = page.locator(selector)
    need(page, box, what)
    shown = box.input_value()
    print('    form showed %s = %s (wanted %s)' % (what, shown, target))
    if float(shown) != float(target):
        print('    -> typing %s' % target)
        set_number(page, selector, target)


# ---------------------------------------------------------------- recipes

def recipe_13(page, fid):
    set_overall(page, 1800, 2100)
    add_frame(page)
    add_mullion(page, fid)
    select_pane(page, 0, fid); click_window_sash_type(page, 'Horizontal slider')
    select_pane(page, 1, fid); click_window_sash_type(page, 'Horizontal slider')


def recipe_14(page, fid):
    # same as recipe_13 minus add_frame: no outer frame
    set_overall(page, 1800, 2100)
    add_mullion(page, fid)
    select_pane(page, 0, fid); click_window_sash_type(page, 'Horizontal slider')
    select_pane(page, 1, fid); click_window_sash_type(page, 'Horizontal slider')


def recipe_11(page, fid):
    set_overall(page, 1680, 1980)
    select_pane(page, 0, fid)
    click_window_sash_type(page, 'Horizontal slider')


def recipe_10(page, fid):
    add_frame(page)
    add_mullion(page, fid)
    select_pane(page, 0, fid); click_window_sash_type(page, 'Fixed')
    select_pane(page, 1, fid); click_window_sash_type(page, 'Horizontal slider')


def recipe_08(page, fid):
    add_frame(page)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Sliding windows', 'OX')
    cb = page.locator('#toolbar label').filter(has_text='Build sashless').locator('input[type=checkbox]')
    need(page, cb, 'sashless checkbox')
    cb.check()
    ensure_value(page, '#presetWidthInput0', 840, 'Section 1 (O) width')
    ensure_value(page, '#presetWidthInput1', 900, 'Section 2 (X) width')
    click_button(page, 'Confirm preset')


def recipe_09(page, fid):
    add_frame(page)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Double-hung windows', 'D')
    cb = page.locator('#dhSashlessCheckbox')
    need(page, cb, 'sashless checkbox')
    cb.check()
    ensure_value(page, '#dhUnitWidthInput', 1680, 'Unit width')
    ensure_value(page, '#dhTopHeightInput', 1020, 'Top pane height')
    click_button(page, 'Confirm preset')


def recipe_07(page, fid):
    # framed OX sliding window, not sashless, section widths 860 / 920
    set_overall(page, 1800, 2100)
    add_frame(page)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Sliding windows', 'OX')
    ensure_value(page, '#presetWidthInput0', 860, 'Section 1 (O) width')
    ensure_value(page, '#presetWidthInput1', 920, 'Section 2 (X) width')
    click_button(page, 'Confirm preset')


def recipe_02(page, fid):
    # same as recipe_07 but the sliding DOOR family (heading "Sliding doors")
    set_overall(page, 1800, 2100)
    add_frame(page)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Sliding doors', 'OX')
    ensure_value(page, '#presetWidthInput0', 860, 'Section 1 (O) width')
    ensure_value(page, '#presetWidthInput1', 920, 'Section 2 (X) width')
    click_button(page, 'Confirm preset')


def recipe_06(page, fid):
    # framed double-hung, not sashless, unit width 1680, top pane height 1040
    set_overall(page, 1800, 2100)
    add_frame(page)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Double-hung windows', 'D')
    ensure_value(page, '#dhUnitWidthInput', 1680, 'Unit width')
    ensure_value(page, '#dhTopHeightInput', 1040, 'Top pane height')
    click_button(page, 'Confirm preset')


def recipe_12(page, fid):
    # as recipe_06 but NO outer frame; the saved export is 1680 x 1980 overall, top height 1020
    set_overall(page, 1680, 1980)
    select_pane(page, 0, fid)
    click_button(page, 'Apply assembly preset')
    pick_preset(page, 'Double-hung windows', 'D')
    ensure_value(page, '#dhUnitWidthInput', 1680, 'Unit width')
    ensure_value(page, '#dhTopHeightInput', 1020, 'Top pane height')
    click_button(page, 'Confirm preset')


RECIPES = {'14': recipe_14, '13': recipe_13, '11': recipe_11, '10': recipe_10, '08': recipe_08, '09': recipe_09,
           '07': recipe_07, '02': recipe_02, '06': recipe_06, '12': recipe_12}


# ---------------------------------------------------------------- reading and checking

def read_table(page):
    rows = []
    for tr in page.locator('#paneTable tr').all():
        rows.append([norm(c) for c in tr.locator('td').all_inner_texts()])
    return rows


def check_table(rows, note, expected, expect_note, fid):
    ok = True
    by_id = {r[0]: r for r in rows}
    if len(rows) != len(expected):
        print('  FAIL row count: expected %d, got %d' % (len(expected), len(rows)))
        ok = False
    for pid, (made, daylight) in expected.items():
        r = by_id.get(pid)
        if r is None or len(r) < 10:
            print('  FAIL pane %s: row missing or short (%s)' % (pid, r))
            ok = False
            continue
        for name, got, want in (('Sash/Leaf size', r[8], made), ('Daylight size', r[9], daylight)):
            good = got == want
            ok = ok and good
            print('  %s pane %s %s: got "%s", expected "%s"' % ('PASS' if good else 'FAIL', pid, name, got, want))
    want_note = NOTE_TEXT if expect_note else ''
    good = note == want_note
    ok = ok and good
    print('  %s note: got "%s", expected "%s"' % ('PASS' if good else 'FAIL', note, want_note))
    return ok


def run_compare(saved, new):
    res = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'compare_full.py'), saved, new],
                         capture_output=True, text=True, cwd=ROOT)
    out = res.stdout + res.stderr
    print('  compare_full.py output:')
    for line in out.splitlines():
        print('    ' + line)
    schema_ok = 'schemaVersion identical: True' in out
    system_zero = 'system differences: 0' in out
    return schema_ok and system_zero and res.returncode == 0


def info_prints(page, fid):
    print('  [info] Sash T / B / L / R cells and slide dropdowns:')
    rows = read_table(page)
    for r in rows:
        print('    pane %s sash cell: %s' % (r[0], r[7]))
    panes = page.locator('#diagram .pane')
    for i in range(panes.count()):
        select_pane(page, i, fid)
        sels = page.locator('#toolbar select')
        vals = []
        for j in range(sels.count()):
            vals.append(sels.nth(j).input_value())
        print('    pane #%d slide/hinge dropdown value(s): %s' % (i, vals if vals else 'none shown'))


def heading_info(page):
    """Info only (not a check): width and wrapping of the pane table headings (file 13)."""
    info = page.evaluate("""() => {
        const table = document.querySelector('#paneTable').closest('table');
        let box = table.parentElement;
        while (box && box !== document.documentElement) {
            const ox = getComputedStyle(box).overflowX;
            if (ox === 'auto' || ox === 'scroll') break;
            box = box.parentElement;
        }
        const scroller = box && box !== document.documentElement ? box : document.documentElement;
        const heads = {};
        for (const th of table.querySelectorAll('thead th')) {
            const t = th.textContent.trim();
            if (t === 'Sash/Leaf size (mm)' || t === 'Daylight size (mm)') {
                const range = document.createRange();
                range.selectNodeContents(th);
                const tops = new Set(Array.from(range.getClientRects()).map(r => Math.round(r.top)));
                heads[t] = {offsetHeight: th.offsetHeight, lineHeight: getComputedStyle(th).lineHeight, lines: tops.size};
            }
        }
        return {scroller: scroller === document.documentElement ? 'document' : (scroller.id || scroller.tagName),
                scrollWidth: scroller.scrollWidth, clientWidth: scroller.clientWidth, tableWidth: table.offsetWidth, heads: heads};
    }""")
    print('  INFO heading layout (not a check): scroll container %s, scrollWidth %s, clientWidth %s, table width %s' %
          (info['scroller'], info['scrollWidth'], info['clientWidth'], info['tableWidth']))
    for name, h in info['heads'].items():
        print('  INFO heading "%s": offsetHeight %s px, computed line-height %s, %s text line(s) (counted from the rendered text)' %
              (name, h['offsetHeight'], h['lineHeight'], h['lines']))


def run_file(browser, fid, saved_name, expected, expect_note):
    print('\n=== File %s (%s) ===' % (fid, saved_name))
    result = {'table': 'n/a', 'console': 'n/a', 'export': 'n/a'}
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors, ignored = [], [], []

    def on_console(msg):
        if msg.type == 'error':
            if 'favicon' in (msg.location or {}).get('url', ''):
                ignored.append(msg.text)
            else:
                console_errors.append(msg.text)
    page.on('console', on_console)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    try:
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        RECIPES[fid](page, fid)
        page.wait_for_timeout(300)
        rows = read_table(page)
        note = norm(page.locator('#sizeNote').inner_text()) if page.locator('#sizeNote').count() else ''
        print('  Table rows (all cells):')
        for r in rows:
            print('    ' + ' | '.join(r))
        print('  Note under table: "%s"' % note)
        result['table'] = 'PASS' if check_table(rows, note, expected, expect_note, fid) else 'FAIL'

        os.makedirs(OUT_DIR, exist_ok=True)
        with page.expect_download() as dl:
            page.locator('#exportJsonBtn').click()
        new_path = os.path.join(OUT_DIR, 'new_' + saved_name)
        dl.value.save_as(new_path)
        print('  Export saved to %s' % new_path)
        result['export'] = 'PASS' if run_compare(os.path.join(SAFETY_DIR, saved_name), new_path) else 'FAIL'

        if fid == '13':
            heading_info(page)
        if fid == '14':
            print('  Informational (not pass/fail): new export compared with the BEFORE file')
            run_compare(os.path.join(SAFETY_DIR, FILE_14_BEFORE_NAME), new_path)
        if fid in ('08', '09'):
            info_prints(page, fid)
    except LabelNotFound as e:
        print('  STOPPED this file: %s' % e)
        result = {'table': 'STOPPED', 'console': 'n/a', 'export': 'STOPPED'}
    except Exception as e:
        print('  ERROR: %r' % e)
        result = {'table': 'ERROR', 'console': 'n/a', 'export': 'ERROR'}
    finally:
        ok = not console_errors and not page_errors
        if result['console'] == 'n/a':
            result['console'] = 'PASS' if ok else 'FAIL'
        print('  %s console errors: %s | page errors: %s | ignored favicon errors: %d' %
              ('PASS' if ok else 'FAIL', console_errors, page_errors, len(ignored)))
        ctx.close()
    return result


# ---------------------------------------------------------------- step 5c-1: tuck-in scenario

def read_pane(page, pane_id):
    for r in read_table(page):
        if r[0] == pane_id and len(r) >= 10:
            return (r[8], r[9])
    return None


def export_text(page, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    with page.expect_download() as dl:
        page.locator('#exportJsonBtn').click()
    path = os.path.join(OUT_DIR, name)
    dl.value.save_as(path)
    return path


def tuck_error_text(page):
    return norm(' '.join(page.locator('#toolbar .field-error').all_inner_texts()))


def tuck_label(page, edge):
    return norm(page.locator('#tuckInInput-' + edge).locator('xpath=preceding-sibling::span').inner_text())


def run_tuck_scenario(browser):
    """File 13 layout, left pane (.L): typed / refused / reset tuck-in (step 5c-1)."""
    print('\n=== Tuck-in scenario (file 13 layout, pane .L) ===')
    fid, saved_name, expected, _ = FILES[0]
    start = expected['.L']                      # (a) today's values, taken from the file 13 check above
    typed_zero = ('920 x 2020', '840 x 1940')    # (b) Claude's arithmetic (940 - 20, 860 - 20), not read from the app
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []

    def on_console(msg):
        if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', ''):
            console_errors.append(msg.text)
    page.on('console', on_console)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    try:
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_13(page, fid)
        select_pane(page, 0, fid)
        page.wait_for_timeout(200)

        # a) nothing typed: today's values, box says auto
        check('a) .L sash/leaf size and daylight with nothing typed', read_pane(page, '.L') == start, '%s (want %s)' % (read_pane(page, '.L'), start))
        check('a) left tuck-in box is marked auto', 'auto' in tuck_label(page, 'left'),
              '"%s", shows %s' % (tuck_label(page, 'left'), page.locator('#tuckInInput-left').input_value()))

        # b) type left tuck-in = 0
        set_number(page, '#tuckInInput-left', 0)
        page.wait_for_timeout(200)
        check('b) .L after typing left tuck-in 0', read_pane(page, '.L') == typed_zero, '%s (want %s)' % (read_pane(page, '.L'), typed_zero))
        check('b) left tuck-in box is marked typed', 'typed' in tuck_label(page, 'left'), '"%s"' % tuck_label(page, 'left'))
        export_b = export_text(page, 'tuck_b.json')

        # c) left tuck-in larger than the left sash (40): refused, snaps back, reason shown, export unchanged
        set_number(page, '#tuckInInput-left', 500)
        page.wait_for_timeout(200)
        reason = tuck_error_text(page)
        check('c) oversize tuck-in snaps back', page.locator('#tuckInInput-left').input_value() == '0',
              'box shows %s' % page.locator('#tuckInInput-left').input_value())
        check('c) reason shown', 'Tuck-in cannot be more than' in reason, '"%s"' % reason)
        check('c) table unchanged', read_pane(page, '.L') == typed_zero, str(read_pane(page, '.L')))
        export_c = export_text(page, 'tuck_c.json')
        check('c) export identical to (b)', open(export_b, 'rb').read() == open(export_c, 'rb').read())

        # c2) the right edge of .L sits on the 40 mm mullion: more than half of it (20) is refused too
        set_number(page, '#tuckInInput-right', 30)
        page.wait_for_timeout(200)
        reason = tuck_error_text(page)
        check('c2) mullion cap refuses 30', 'half the mullion thickness' in reason and page.locator('#tuckInInput-right').input_value() == '20',
              '"%s", box shows %s' % (reason, page.locator('#tuckInInput-right').input_value()))

        # d) narrowing the left sash below a typed left tuck-in must be refused
        set_number(page, '#tuckInInput-left', 30)
        page.wait_for_timeout(200)
        check('d) typed left tuck-in 30 accepted', page.locator('#tuckInInput-left').input_value() == '30')
        set_number(page, '#sashEdgeInput-left', 20)
        page.wait_for_timeout(200)
        reason = tuck_error_text(page)
        check('d) narrowing left sash to 20 refused',
              'lower the tuck-in first' in tuck_error_text(page) or 'lower the tuck-in first' in norm(page.locator('#toolbar').inner_text()),
              '"%s", sash box shows %s' % (reason, page.locator('#sashEdgeInput-left').input_value()))
        check('d) left sash stays 40', page.locator('#sashEdgeInput-left').input_value() == '40')

        # e) reset to automatic: back to (a), and the export matches the saved file again
        click_button(page, 'Reset tuck-ins to automatic')
        page.wait_for_timeout(200)
        check('e) .L after reset', read_pane(page, '.L') == start, '%s (want %s)' % (read_pane(page, '.L'), start))
        check('e) left tuck-in box is marked auto again', 'auto' in tuck_label(page, 'left'), '"%s"' % tuck_label(page, 'left'))
        export_e = export_text(page, 'tuck_e.json')
        check('e) export matches saved file 13 (compare_full)', run_compare(os.path.join(SAFETY_DIR, saved_name), export_e))

        # g) the tuck-in can never exceed its sash: starting from the reset state (nothing typed),
        # the automatic left tuck-in is 20, so a left sash of 10 must be refused
        set_number(page, '#sashEdgeInput-left', 10)
        page.wait_for_timeout(200)
        reason = tuck_error_text(page)
        check('g) left sash 10 refused (automatic tuck-in is 20)', 'lower the tuck-in first' in reason, '"%s"' % reason)
        check('g) left sash box stays 40', page.locator('#sashEdgeInput-left').input_value() == '40',
              'box shows %s' % page.locator('#sashEdgeInput-left').input_value())

        # h) typed left tuck-in 0 lets the left sash go to 0. Expected numbers are Claude's arithmetic,
        # not hand values: sash/leaf size = 900 drawn + 0 left + 20 right = 920; daylight = 920 - 0 (left sash)
        # - 40 (right sash) = 880 wide, and 2020 - 40 - 40 = 1940 high.
        sash_zero = ('920 x 2020', '880 x 1940')
        set_number(page, '#tuckInInput-left', 0)
        page.wait_for_timeout(200)
        set_number(page, '#sashEdgeInput-left', 0)
        page.wait_for_timeout(200)
        check('h) left sash 0 accepted', page.locator('#sashEdgeInput-left').input_value() == '0',
              'box shows %s, "%s"' % (page.locator('#sashEdgeInput-left').input_value(), tuck_error_text(page)))
        check('h) .L sash/leaf size and daylight with left tuck-in 0 and left sash 0', read_pane(page, '.L') == sash_zero,
              '%s (want %s)' % (read_pane(page, '.L'), sash_zero))

        # i) the left Tuck-in box shows 0 and the Sash/Leaf size column agrees with it
        check('i) left tuck-in box shows 0', page.locator('#tuckInInput-left').input_value() == '0',
              'shows %s' % page.locator('#tuckInInput-left').input_value())
        check('i) sash/leaf size agrees with the box', read_pane(page, '.L')[0] == sash_zero[0], str(read_pane(page, '.L')))

        # j) reset with the left sash still 0: the cap holds the tuck-in at 0, so sash/leaf size stays 920 x 2020
        click_button(page, 'Reset tuck-ins to automatic')
        page.wait_for_timeout(200)
        check('j) after reset with left sash 0, sash/leaf size stays 920 x 2020', read_pane(page, '.L') == sash_zero,
              '%s (want %s)' % (read_pane(page, '.L'), sash_zero))
        check('j) left tuck-in box still shows 0', page.locator('#tuckInInput-left').input_value() == '0')

        # k) left sash back to 40: .L returns to today's values and the export matches saved file 13
        set_number(page, '#sashEdgeInput-left', 40)
        page.wait_for_timeout(200)
        check('k) .L back to 940 x 2020 / 860 x 1940', read_pane(page, '.L') == start, '%s (want %s)' % (read_pane(page, '.L'), start))
        export_k = export_text(page, 'tuck_k.json')
        check('k) export matches saved file 13 (compare_full)', run_compare(os.path.join(SAFETY_DIR, saved_name), export_k))

        # f) the harness has no save/reload path, so none is built here
        print('  f not covered (no save/reload path in this harness)')
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean


def run_no_frame_mullion_scenario(browser):
    """File 14 layout (no outer frame, mullion): typed tuck-in at the mullion edge and the opening edge (step 5c-2)."""
    print('\n=== No-frame mullion tuck-in scenario (file 14 layout, pane .L) ===')
    fid = '14'
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []
    page.on('console', lambda msg: console_errors.append(msg.text)
            if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', '') else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    try:
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_14(page, fid)
        select_pane(page, 0, fid)
        page.wait_for_timeout(200)
        # c) typed value at the mullion edge: 10 accepted (960 + 10 = 970, Claude's arithmetic); 30 refused (half of 40 is 20)
        set_number(page, '#tuckInInput-right', 10)
        page.wait_for_timeout(200)
        check('c) .L right tuck-in 10 accepted, Sash/Leaf size 970 x 2100', (read_pane(page, '.L') or ('', ''))[0] == '970 x 2100',
              '%s, box shows %s' % (read_pane(page, '.L'), page.locator('#tuckInInput-right').input_value()))
        set_number(page, '#tuckInInput-right', 30)
        page.wait_for_timeout(200)
        reason = tuck_error_text(page)
        check('c) 30 refused, box snaps back to 10', 'half the mullion thickness' in reason and page.locator('#tuckInInput-right').input_value() == '10',
              '"%s", box shows %s' % (reason, page.locator('#tuckInInput-right').input_value()))
        # d) the left edge of .L is an opening edge with no frame: box disabled and shows 0
        left = page.locator('#tuckInInput-left')
        check('d) left tuck-in box disabled and shows 0', left.is_disabled() and left.input_value() == '0',
              'disabled=%s, shows %s, title "%s"' % (left.is_disabled(), left.input_value(), left.get_attribute('title')))
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean

# ---------------------------------------------------------------- preset slide-direction lock

LOCK_TIP = 'Slide direction is set by the preset pattern. Choose a different preset to change it.'


def dir_select(page):
    """The horizontal-slider 'Slide direction' select in the toolbar (options left/right), or None."""
    sel = page.locator('#toolbar select:has(option[value=left]):has(option[value=right])')
    return sel.first if sel.count() else None


def run_dirlock_scenario(browser):
    """Slide direction is locked inside OX-family presets, and free everywhere else (preset direction lock)."""
    print('\n=== Preset slide-direction lock scenario ===')
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []
    page.on('console', lambda msg: console_errors.append(msg.text)
            if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', '') else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    def fresh():
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')

    def describe(sel):
        return 'none' if sel is None else 'disabled=%s value=%s title="%s"' % (sel.is_disabled(), sel.input_value(), sel.get_attribute('title'))

    try:
        # a) file 07 layout: the X (.S) is locked
        fresh(); recipe_07(page, '07')
        select_pane(page, 1, '07'); page.wait_for_timeout(200)
        sel = dir_select(page)
        check('a) file 07 X (.S) select exists, disabled, value left, tooltip', sel is not None and sel.is_disabled()
              and sel.input_value() == 'left' and sel.get_attribute('title') == LOCK_TIP, describe(sel))
        # b) the O (.R) is fixed: no slide-direction select
        select_pane(page, 0, '07'); page.wait_for_timeout(200)
        sel = dir_select(page)
        check('b) file 07 O (.R) shows no slide-direction select', sel is None, describe(sel))

        # c) OXXO-win framed 1800 x 2100, prefilled widths
        fresh()
        set_overall(page, 1800, 2100)
        add_frame(page)
        select_pane(page, 0, 'dirlock')
        click_button(page, 'Apply assembly preset')
        pick_preset(page, 'Sliding windows', 'OXXO')
        click_button(page, 'Confirm preset')
        page.wait_for_timeout(300)
        n = page.locator('#diagram .pane').count()
        check('c) OXXO builds 4 panes', n == 4, 'panes=%d' % n)
        for idx, want in ((1, 'left'), (2, 'right')):
            select_pane(page, idx, 'dirlock'); page.wait_for_timeout(200)
            sel = dir_select(page)
            check('c) OXXO pane %d select disabled, value %s, tooltip' % (idx, want), sel is not None and sel.is_disabled()
                  and sel.input_value() == want and sel.get_attribute('title') == LOCK_TIP, describe(sel))

        # d) file 13 layout (lone sliders): .L select enabled and changeable; export matches file 13 once back on left
        fresh(); recipe_13(page, '13')
        select_pane(page, 0, '13'); page.wait_for_timeout(200)
        sel = dir_select(page)
        check('d) file 13 .L select exists and is enabled', sel is not None and sel.is_enabled(), describe(sel))
        sel.select_option('right'); page.wait_for_timeout(300)
        check('d) .L changed to right', dir_select(page).input_value() == 'right', describe(dir_select(page)))
        changed = export_text(page, 'dirlock_d_right.json')
        saved13 = os.path.join(SAFETY_DIR, FILES[0][1])
        print('  compare, .L set to right (expect only .L slideDirection to differ):')
        run_compare(saved13, changed)
        dir_select(page).select_option('left'); page.wait_for_timeout(300)
        back = export_text(page, 'dirlock_d_left.json')
        check('d) .L set back to left: system block matches saved file 13', run_compare(saved13, back))

        # e) file 09 layout (sashless double-hung): the vertical selects are not locked
        fresh(); recipe_09(page, '09')
        for idx in (0, 1):
            select_pane(page, idx, '09'); page.wait_for_timeout(200)
            sel = page.locator('#toolbar select:has(option[value=up]):has(option[value=down])')
            check('e) file 09 pane %d select exists and is enabled' % idx, sel.count() == 1 and sel.first.is_enabled(),
                  'count=%d, enabled=%s' % (sel.count(), sel.first.is_enabled() if sel.count() else None))
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean

# ---------------------------------------------------------------- drawing order (stacking) scenario

# For every .pane (DOM order): its screen rectangle. Used to pick a point and ask what is on top there.
PANE_RECTS_JS = """() => [...document.querySelectorAll('#diagram .pane')].map(e => {
    const r = e.getBoundingClientRect(); return {l: r.left, r: r.right, t: r.top, b: r.bottom}; })"""
# Index (DOM order among .pane) of the pane on top at a screen point, and whether a bar is there.
TOP_AT_JS = """([x, y]) => {
    const el = document.elementFromPoint(x, y);
    const pane = el && el.closest('.pane');
    const bar = el && el.closest('.bar');
    const panes = [...document.querySelectorAll('#diagram .pane')];
    return {pane: pane ? panes.indexOf(pane) : -1, bar: !!bar}; }"""


def build_preset_framed(page, heading, label):
    page.goto(URL)
    page.wait_for_selector('#diagram .pane')
    set_overall(page, 1800, 2100)
    add_frame(page)
    select_pane(page, 0, 'stack')
    click_button(page, 'Apply assembly preset')
    pick_preset(page, heading, label)
    click_button(page, 'Confirm preset')
    page.wait_for_timeout(300)


def top_pane_at(page, x, y):
    return page.evaluate(TOP_AT_JS, [x, y])['pane']


def run_stack_scenario(browser):
    """Sliders paint above fixed panes: an X keeps its overlapped right stile when an O is beside it."""
    print('')
    print('=== Drawing order (stacking) scenario ===')
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []
    page.on('console', lambda msg: console_errors.append(msg.text)
            if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', '') else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    def strip_test(name, x_idx, o_idx):
        # the hidden strip is the part of the O that lies inside the X's right edge; probe 3 px in from the X's right edge
        rects = page.evaluate(PANE_RECTS_JS)
        xr, orr = rects[x_idx], rects[o_idx]
        px, py = xr['r'] - 3, (xr['t'] + xr['b']) / 2
        in_strip = orr['l'] < px < xr['r']
        got = top_pane_at(page, px, py)
        check(name, in_strip and got == x_idx, 'probe (%.1f, %.1f), O starts at %.1f, X ends at %.1f, top pane index %d (want X = %d)'
              % (px, py, orr['l'], xr['r'], got, x_idx))

    try:
        # a) OXXO window: second X (index 2), O on its right (index 3)
        build_preset_framed(page, 'Sliding windows', 'OXXO')
        strip_test('a) OXXO window, second X right stile on top of the O', 2, 3)
        # b) XOX window: first X (index 0), O on its right (index 1)
        build_preset_framed(page, 'Sliding windows', 'XOX')
        strip_test('b) XOX window, first X right stile on top of the O', 0, 1)
        # c) OX window (control): X centre is the X, O centre is the O
        build_preset_framed(page, 'Sliding windows', 'OX')
        rects = page.evaluate(PANE_RECTS_JS)

        def centre(i):
            return (rects[i]['l'] + rects[i]['r']) / 2, (rects[i]['t'] + rects[i]['b']) / 2
        got_x, got_o = top_pane_at(page, *centre(1)), top_pane_at(page, *centre(0))
        check('c) OX window: X centre is the X, O centre is the O', got_x == 1 and got_o == 0,
              'X centre -> %d (want 1), O centre -> %d (want 0)' % (got_x, got_o))
        # d) sliding DOORS, same as a) and b)
        build_preset_framed(page, 'Sliding doors', 'OXXO')
        strip_test('d) OXXO door, second X right stile on top of the O', 2, 3)
        build_preset_framed(page, 'Sliding doors', 'XOX')
        strip_test('d) XOX door, first X right stile on top of the O', 0, 1)
        # e) double-hung meeting rail (file 06 layout): the bottom sash is painted last, so it stays on top
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_06(page, '06')
        rects = page.evaluate(PANE_RECTS_JS)
        top, bottom = rects[0], rects[1]
        px, py = (top['l'] + top['r']) / 2, (bottom['t'] + top['b']) / 2
        got = top_pane_at(page, px, py)
        check('e) double-hung meeting rail overlap: top pane index is unchanged by the change (bottom sash = 1)',
              bottom['t'] < top['b'] and got == 1, 'overlap %.1f to %.1f, probe y %.1f, top pane index %d (before the CSS change it was 1)'
              % (bottom['t'], top['b'], py, got))
        # f) mullion bars stay on top and clickable (file 13 and file 10 layouts)
        for fid in ('13', '10'):
            page.goto(URL)
            page.wait_for_selector('#diagram .pane')
            RECIPES[fid](page, fid)
            page.wait_for_timeout(200)
            box = page.locator('#diagram .bar').first.bounding_box()
            bx, by = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
            res = page.evaluate(TOP_AT_JS, [bx, by])
            check('f) file %s mullion centre: the bar is on top' % fid, res['bar'], 'at (%.1f, %.1f) -> %s' % (bx, by, res))
            page.mouse.click(bx, by)
            page.wait_for_timeout(200)
            tb = norm(page.locator('#toolbar').inner_text())
            check('f) file %s click on the mullion selects the bar ("Remove this split" shown)' % fid, 'Remove this split' in tb)
        # g) OXX window: X1 / X2 overlap, the later X (index 2) is on top, as before
        build_preset_framed(page, 'Sliding windows', 'OXX')
        rects = page.evaluate(PANE_RECTS_JS)
        x1, x2 = rects[1], rects[2]
        px, py = (x2['l'] + x1['r']) / 2, (x2['t'] + x2['b']) / 2
        got = top_pane_at(page, px, py)
        check('g) OXX window: X1 / X2 overlap, top pane index is unchanged (X2 = 2)', x2['l'] < x1['r'] and got == 2,
              'overlap %.1f to %.1f, top pane index %d (before the CSS change it was 2)' % (x2['l'], x1['r'], got))
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean

# ---------------------------------------------------------------- step 4a: head/sill tuck-in in presets

def hs_label(page, edge):
    return norm(page.locator('#headSillTuckInput-' + edge).locator('xpath=preceding-sibling::span').inner_text())


def hs_row_present(page):
    return page.locator('#toolbar').filter(has_text='Head/sill tuck-in (mm)').count() > 0 \
        or page.locator('#headSillTuckInput-top').count() > 0


def exported_pane(path, pane_id):
    import json
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for p in data['system']['elevations'][0]['panes']:
        if p['id'] == pane_id:
            return p
    return None


def run_headsill_scenario(browser):
    """Head/sill tuck-in boxes for the X sash of an OX sliding preset (step 4a), file 07 layout."""
    print('\n=== Head/sill tuck-in scenario (file 07 layout, pane .S) ===')
    fid = '07'
    saved = os.path.join(SAFETY_DIR, 'safety_net_v6_07_framed_OX_window_860_920.json')
    # Expected numbers are Claude's arithmetic, not hand values. The X is drawn 1980 high. Made height =
    # 1980 + top + bottom tuck-in; daylight height = made height - 40 - 40 (sash edges); daylight width
    # stays 840. The export's yMM is measured up from the bottom of the elevation, so it moves with the
    # BOTTOM tuck-in only (60 sill less the bottom tuck-in): a top tuck-in grows the sash upward and
    # leaves yMM alone.
    #   default 20/20:    920 x 2020, daylight 840 x 1940, yMM 40
    #   top 30:           920 x 2030, daylight 840 x 1950, yMM 40
    #   top 30 bottom 10: 920 x 2020, daylight 840 x 1940, yMM 50
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []
    page.on('console', lambda msg: console_errors.append(msg.text)
            if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', '') else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    def box(edge):
        return page.locator('#headSillTuckInput-' + edge)

    def settle():
        page.wait_for_timeout(200)

    try:
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_07(page, fid)

        # a) the O has no head/sill row; the X shows 20 / 20, both auto, and today's sizes
        select_pane(page, 0, fid); settle()
        check('a) O (.R) shows no head/sill row', not hs_row_present(page))
        select_pane(page, 1, fid); settle()
        check('a) boxes show 20 and 20', box('top').input_value() == '20' and box('bottom').input_value() == '20',
              'top %s bottom %s' % (box('top').input_value(), box('bottom').input_value()))
        check('a) both tagged auto', 'auto' in hs_label(page, 'top') and 'auto' in hs_label(page, 'bottom'),
              '"%s" "%s"' % (hs_label(page, 'top'), hs_label(page, 'bottom')))
        check('a) .S 920 x 2020, daylight 840 x 1940', read_pane(page, '.S') == ('920 x 2020', '840 x 1940'), str(read_pane(page, '.S')))
        check('a) .R unchanged 860 x 1980', read_pane(page, '.R') == ('860 x 1980', '860 x 1980'), str(read_pane(page, '.R')))
        export_a = export_text(page, 'headsill_a.json')
        check('a) .S yMM 40', exported_pane(export_a, '.S')['yMM'] == 40, str(exported_pane(export_a, '.S')['yMM']))

        # b) top = 30
        set_number(page, '#headSillTuckInput-top', 30); settle()
        check('b) .S 920 x 2030, daylight 840 x 1950', read_pane(page, '.S') == ('920 x 2030', '840 x 1950'), str(read_pane(page, '.S')))
        check('b) top box tagged typed, bottom still auto', 'typed' in hs_label(page, 'top') and 'auto' in hs_label(page, 'bottom'),
              '"%s" "%s"' % (hs_label(page, 'top'), hs_label(page, 'bottom')))
        export_b = export_text(page, 'headsill_b.json')
        check('b) .S yMM stays 40', exported_pane(export_b, '.S')['yMM'] == 40, str(exported_pane(export_b, '.S')['yMM']))

        # k) export after (b) against saved file 07: print every differing path
        print('  k) compare of the export after (b) with the saved file 07:')
        res = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'compare_full.py'), saved, export_b],
                             capture_output=True, text=True, cwd=ROOT)
        out = res.stdout + res.stderr
        for line in out.splitlines():
            print('    ' + line)
        sys_lines = [l.strip() for l in out.splitlines() if l.strip().startswith('system/')]
        allowed = ('/heightMM', '/yMM', '/areaM2', '/visibleGlazedAreaM2', '/frameLengthMM', '/totalFrameLengthMM')
        check('k) every system difference is an expected field', len(sys_lines) > 0 and all(any(l.split(':')[0].endswith(a) for a in allowed) for l in sys_lines),
              '%d differing path(s)' % len(sys_lines))
        check('k) yMM unchanged', not any(l.split(':')[0].endswith('/yMM') for l in sys_lines))
        check('k) only the .S pane (panes[1]) differs among panes', all(('/panes[' not in l) or '/panes[1]/' in l for l in sys_lines))
        check('k) no width or x difference', not any(l.split(':')[0].endswith(('/widthMM', '/xMM')) for l in sys_lines))

        # g) save and reload through the page's own functions: the typed top must survive
        state = page.evaluate('() => JSON.stringify(window.serializeRawState())')
        page.evaluate('(s) => window.restoreFromRawState(JSON.parse(s))', state)
        fallback_used.append((fid, 'headsill g): reload via window.serializeRawState() / window.restoreFromRawState() (no save/reload UI)'))
        settle()
        select_pane(page, 1, fid); settle()
        check('g) typed top 30 survives the reload', box('top').input_value() == '30' and 'typed' in hs_label(page, 'top'),
              'top %s "%s"' % (box('top').input_value(), hs_label(page, 'top')))
        check('g) .S still 920 x 2030 after the reload', read_pane(page, '.S') == ('920 x 2030', '840 x 1950'), str(read_pane(page, '.S')))

        # c) then bottom = 10
        set_number(page, '#headSillTuckInput-bottom', 10); settle()
        check('c) .S 920 x 2020, daylight 840 x 1940', read_pane(page, '.S') == ('920 x 2020', '840 x 1940'), str(read_pane(page, '.S')))
        export_c = export_text(page, 'headsill_c.json')
        check('c) .S yMM 50', exported_pane(export_c, '.S')['yMM'] == 50, str(exported_pane(export_c, '.S')['yMM']))

        # d) top = 50 is more than the 40 mm top sash: refused, snaps back to 30
        set_number(page, '#headSillTuckInput-top', 50); settle()
        reason = tuck_error_text(page)
        check('d) top 50 refused with the reason', 'Tuck-in cannot be more than the top sash width (40 mm).' in reason, '"%s"' % reason)
        check('d) box snaps back to 30', box('top').input_value() == '30', box('top').input_value())

        # e) top sash 25 is below the typed top tuck-in 30: refused
        set_number(page, '#sashEdgeInput-top', 25); settle()
        reason = tuck_error_text(page)
        check('e) top sash 25 refused', reason.startswith('Sash edge cannot be less than its tuck-in (30 mm)') or 'Sash edge cannot be less than its tuck-in (30 mm)' in reason,
              '"%s", sash box shows %s' % (reason, page.locator('#sashEdgeInput-top').input_value()))
        check('e) top sash stays 40', page.locator('#sashEdgeInput-top').input_value() == '40')

        # f) reset: both auto, 20 / 20, back to the default sizes
        click_button(page, 'Reset head/sill tuck-ins'); settle()
        check('f) both boxes show 20 and are auto', box('top').input_value() == '20' and box('bottom').input_value() == '20'
              and 'auto' in hs_label(page, 'top') and 'auto' in hs_label(page, 'bottom'))
        check('f) .S back to 920 x 2020', read_pane(page, '.S') == ('920 x 2020', '840 x 1940'), str(read_pane(page, '.S')))
        export_f = export_text(page, 'headsill_f.json')
        check('f) .S yMM back to 40', exported_pane(export_f, '.S')['yMM'] == 40, str(exported_pane(export_f, '.S')['yMM']))
        check('f) reset button is disabled again', page.locator('#headSillTuckInResetBtn').is_disabled())

        # h) no outer frame: both boxes disabled and show 0
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        set_overall(page, 1800, 2100)
        select_pane(page, 0, 'headsill-h')
        click_button(page, 'Apply assembly preset')
        pick_preset(page, 'Sliding windows', 'OX')
        click_button(page, 'Confirm preset'); settle()
        select_pane(page, 1, 'headsill-h'); settle()
        check('h) no frame: both boxes disabled and show 0',
              box('top').is_disabled() and box('bottom').is_disabled() and box('top').input_value() == '0' and box('bottom').input_value() == '0',
              'top disabled=%s shows %s; bottom disabled=%s shows %s; title "%s"' % (
                  box('top').is_disabled(), box('top').input_value(), box('bottom').is_disabled(), box('bottom').input_value(), box('top').get_attribute('title')))

        # i) sashless OX: no head/sill row at all
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_08(page, '08')
        select_pane(page, 1, '08'); settle()
        check('i) sashless OX: X shows no head/sill row', not hs_row_present(page))

        # j) double-hung: no head/sill row on either pane
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_06(page, '06')
        select_pane(page, 0, '06'); settle()
        no0 = not hs_row_present(page)
        select_pane(page, 1, '06'); settle()
        check('j) double-hung: no head/sill row on either pane', no0 and not hs_row_present(page))
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean


def table_heights(page):
    """Table rows in DOM order: (id, made height, daylight height) taken from the Sash/Leaf and Daylight columns."""
    out = []
    for r in read_table(page):
        if len(r) >= 10 and r[0]:
            out.append((r[0], int(r[8].split(' x ')[1]), int(r[9].split(' x ')[1])))
    return out


def run_headsill_more_scenario(browser):
    """Step 4a follow-up: Edit assembly widths keeps typed head/sill values (l); per-section values in OXX (m)."""
    print('\n=== Head/sill follow-up scenario (Edit assembly widths, OXX) ===')
    fid = '07'
    # Expected numbers are Claude's arithmetic, not hand values. Made height = 1980 + top + bottom tuck-in;
    # daylight height = made height - 40 - 40. Width after the resize: O 840 drawn; X 940 wide made, less
    # 40 + 40 sash edges = 860 daylight. 840 + 940 - 60 overlap - 40 tuck-in = 1680, the opening.
    ctx = browser.new_context(accept_downloads=True)
    page = ctx.new_page()
    console_errors, page_errors = [], []
    page.on('console', lambda msg: console_errors.append(msg.text)
            if msg.type == 'error' and 'favicon' not in (msg.location or {}).get('url', '') else None)
    page.on('pageerror', lambda e: page_errors.append(str(e)))
    ok = True

    def check(name, good, detail=''):
        nonlocal ok
        ok = ok and good
        print('  %s %s %s' % ('PASS' if good else 'FAIL', name, detail))

    def box(edge):
        return page.locator('#headSillTuckInput-' + edge)

    def settle():
        page.wait_for_timeout(200)

    def state(idx):
        select_pane(page, idx, 'headsill2'); settle()
        return (box('top').input_value(), hs_label(page, 'top'), box('bottom').input_value(), hs_label(page, 'bottom'))

    try:
        # l) Edit assembly widths keeps the typed values
        page.goto(URL)
        page.wait_for_selector('#diagram .pane')
        recipe_07(page, fid)
        select_pane(page, 1, fid); settle()
        set_number(page, '#headSillTuckInput-top', 30); settle()
        check('l) before edit: .S 920 x 2030 / 840 x 1950', read_pane(page, '.S') == ('920 x 2030', '840 x 1950'), str(read_pane(page, '.S')))
        select_pane(page, 1, fid)
        click_button(page, 'Edit assembly widths')
        click_button(page, 'Confirm resize'); settle()
        s = state(1)
        check('l) widths unchanged: top 30 typed, bottom 20 auto', s == ('30', 'Top (typed)', '20', 'Bottom (auto)'), str(s))
        check('l) widths unchanged: .S 920 x 2030 / 840 x 1950', read_pane(page, '.S') == ('920 x 2030', '840 x 1950'), str(read_pane(page, '.S')))
        check('l) widths unchanged: .R 860 x 1980 / 860 x 1980', read_pane(page, '.R') == ('860 x 1980', '860 x 1980'), str(read_pane(page, '.R')))
        click_button(page, 'Edit assembly widths')
        set_number(page, '#presetWidthInput0', 840)
        set_number(page, '#presetWidthInput1', 940)
        click_button(page, 'Confirm resize'); settle()
        s = state(1)
        check('l) widths 840 / 940: top still 30 typed', s[0:2] == ('30', 'Top (typed)'), str(s))
        check('l) widths 840 / 940: .R 840 x 1980 / 840 x 1980', read_pane(page, '.R') == ('840 x 1980', '840 x 1980'), str(read_pane(page, '.R')))
        check('l) widths 840 / 940: .S 940 x 2030 / 860 x 1950', read_pane(page, '.S') == ('940 x 2030', '860 x 1950'), str(read_pane(page, '.S')))

        # m) per-section values in OXX
        build_preset_framed(page, 'Sliding windows', 'OXX')
        print('  table rows (DOM order: 0 = O, 1 = first X, 2 = second X):')
        for r in read_table(page):
            print('    ' + ' | '.join(r))
        check('m) three panes', len(table_heights(page)) == 3, str(table_heights(page)))
        s = state(1)
        set_number(page, '#headSillTuckInput-top', 30); settle()
        s2 = state(2)
        check('m) second X still 20 auto / 20 auto', s2 == ('20', 'Top (auto)', '20', 'Bottom (auto)'), str(s2))
        s1 = state(1)
        check('m) first X top 30 typed, bottom 20 auto', s1 == ('30', 'Top (typed)', '20', 'Bottom (auto)'), str(s1))
        h = table_heights(page)
        check('m) made heights O 1980, X1 2030, X2 2020', [x[1] for x in h] == [1980, 2030, 2020], str(h))
        check('m) daylight heights O 1980, X1 1950, X2 1940', [x[2] for x in h] == [1980, 1950, 1940], str(h))
        state(2)
        set_number(page, '#headSillTuckInput-bottom', 10); settle()
        h = table_heights(page)
        check('m) made heights O 1980, X1 2030, X2 2010', [x[1] for x in h] == [1980, 2030, 2010], str(h))
        s1 = state(1)
        check('m) first X still top 30 typed, bottom 20 auto', s1 == ('30', 'Top (typed)', '20', 'Bottom (auto)'), str(s1))
        s2 = state(2)
        check('m) second X top 20 auto, bottom 10 typed', s2 == ('20', 'Top (auto)', '10', 'Bottom (typed)'), str(s2))
        select_pane(page, 0, 'headsill2'); settle()
        check('m) O shows no head/sill row', not hs_row_present(page))
        exp = export_text(page, 'headsill2_m.json')
        import json
        with open(exp, encoding='utf-8') as f:
            panes = json.load(f)['system']['elevations'][0]['panes']
        print('  [info] exported panes (id, heightMM, yMM): %s' % [(p['id'], p['heightMM'], p['yMM']) for p in panes])
    except Exception as e:
        print('  ERROR: %r' % e)
        ok = False
    finally:
        clean = not console_errors and not page_errors
        print('  %s console errors: %s | page errors: %s' % ('PASS' if clean else 'FAIL', console_errors, page_errors))
        ctx.close()
    return ok and clean


def main():
    proc = None
    results = {}
    tuck_ok = False
    nf_ok = False
    dl_ok = False
    st_ok = False
    hs_ok = False
    hs2_ok = False
    try:
        proc = start_server()
        print('Server up on port %d (SYSTEM_CHECK_ENABLED set at run time only)' % PORT)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for fid, saved_name, expected, expect_note in FILES:
                results[fid] = run_file(browser, fid, saved_name, expected, expect_note)
            tuck_ok = run_tuck_scenario(browser)
            nf_ok = run_no_frame_mullion_scenario(browser)
            dl_ok = run_dirlock_scenario(browser)
            st_ok = run_stack_scenario(browser)
            hs_ok = run_headsill_scenario(browser)
            hs2_ok = run_headsill_more_scenario(browser)
            browser.close()
    finally:
        stop_server(proc)
        print('\nServer stopped.')

    print('\nSummary')
    print('%-6s %-8s %-8s %-8s' % ('file', 'table', 'console', 'export'))
    for fid, *_ in FILES:
        r = results.get(fid, {'table': 'n/a', 'console': 'n/a', 'export': 'n/a'})
        print('%-6s %-8s %-8s %-8s' % (fid, r['table'], r['console'], r['export']))
    print('%-6s %s' % ('tuck', 'PASS' if tuck_ok else 'FAIL'))
    print('%-6s %s' % ('nofr', 'PASS' if nf_ok else 'FAIL'))
    print('%-6s %s' % ('dirlock', 'PASS' if dl_ok else 'FAIL'))
    print('%-6s %s' % ('stack', 'PASS' if st_ok else 'FAIL'))
    print('%-6s %s' % ('headsill', 'PASS' if hs_ok else 'FAIL'))
    print('%-6s %s' % ('headsill2', 'PASS' if hs2_ok else 'FAIL'))
    print('\nFallbacks to page functions: %s' % (fallback_used if fallback_used else 'none (all selections were real clicks)'))
    failed = any(v != 'PASS' for r in results.values() for v in r.values())
    sys.exit(1 if failed or not tuck_ok or not nf_ok or not dl_ok or not st_ok or not hs_ok or not hs2_ok or len(results) != len(FILES) else 0)


if __name__ == '__main__':
    main()
