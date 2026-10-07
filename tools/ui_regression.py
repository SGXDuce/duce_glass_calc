"""Browser regression test for the Configurator's Made size / Daylight size columns (step 5b).

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

# Expected table values: pane id -> (made size, daylight size).
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


RECIPES = {'13': recipe_13, '11': recipe_11, '10': recipe_10, '08': recipe_08, '09': recipe_09}


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
        for name, got, want in (('Made size', r[8], made), ('Daylight size', r[9], daylight)):
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
        check('a) .L made/daylight with nothing typed', read_pane(page, '.L') == start, '%s (want %s)' % (read_pane(page, '.L'), start))
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


def main():
    proc = None
    results = {}
    tuck_ok = False
    try:
        proc = start_server()
        print('Server up on port %d (SYSTEM_CHECK_ENABLED set at run time only)' % PORT)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for fid, saved_name, expected, expect_note in FILES:
                results[fid] = run_file(browser, fid, saved_name, expected, expect_note)
            tuck_ok = run_tuck_scenario(browser)
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
    print('\nFallbacks to page functions: %s' % (fallback_used if fallback_used else 'none (all selections were real clicks)'))
    failed = any(v != 'PASS' for r in results.values() for v in r.values())
    sys.exit(1 if failed or not tuck_ok or len(results) != len(FILES) else 0)


if __name__ == '__main__':
    main()
