# AS 1288 Glass Thickness Calculator - Human Impact Engine Test Runner
# Validates engine/human_impact (AS 1288 Section 5 - Grade A safety glass
# determination and eligible glass types/thicknesses).
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_human_impact

from engine.human_impact import determine_fixed, determine_louvre, determine_sashless


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def report(test_id, description, checks):
    """
    checks is a list of (label, expected, actual, ok) tuples.
    Prints each check and returns True if all checks passed.
    """
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    return overall


def base_ctx(**overrides):
    """
    A complete, valid ctx dict with sensible defaults - every test
    overrides only the fields it cares about, per the project's existing
    test convention.
    """
    ctx = dict(
        opening_type='door',
        is_side_panel=False,
        is_louvre=False,
        building_use='residential',
        is_bathroom=False,
        high_risk=False,
        framing='fully',
        exposed_edges=None,
        sight_width_mm=None,
        sight_height_mm=None,
        sightline_mm=0,
        opaque_or_patterned=False,
        rail_present=False,
        rail_upper_edge_mm=None,
        rail_lower_edge_mm=None,
        level_difference_mm=None,
        panel_area_m2=None,
        panel_width_mm=None,
    )
    ctx.update(overrides)
    return ctx


def get_type(result, type_id):
    matches = [t for t in result['types'] if t['id'] == type_id]
    assert matches, f"type {type_id!r} not found in result types: {[t['id'] for t in result['types']]}"
    return matches[0]


# ---------------------------------------------------------------------------
# TESTS 1-2 — Doors, fully framed, annealed exception bands
# ---------------------------------------------------------------------------

def test_1():
    # Door, fully framed, residential, sightline 0mm, 100x800mm = 0.08 m²,
    # width 100mm -> within band 1 (3-4mm/0.10m²/125mm) -> ok=True at 3mm.
    result = determine_fixed(base_ctx(panel_area_m2=0.08, panel_width_mm=100))
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('monolithic_annealed ok', True, ma['ok'], ma['ok'] is True),
        ('monolithic_annealed min_thickness', 3.0, ma['min_thickness'], ma['min_thickness'] == 3.0),
    ]
    return report('1', 'Door, fully framed, 0.08m²/100mm -> annealed 3mm available', checks)


def test_2():
    # Same door, area 0.60 m², width 500mm -> exceeds every band (including
    # the top 0.50m² ceiling) -> monolithic annealed ok=False.
    result = determine_fixed(base_ctx(panel_area_m2=0.60, panel_width_mm=500))
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('why cites the exceeded limit', True, 'exception band accommodates' in (ma['why'] or ''),
         'exception band accommodates' in (ma['why'] or '')),
    ]
    return report('2', 'Door, fully framed, 0.60m²/500mm -> no annealed band fits -> ok=False', checks)


# ---------------------------------------------------------------------------
# TESTS 3-4 — Unframed doors
# ---------------------------------------------------------------------------

def test_3():
    # Door, unframed -> only monolithic/laminated toughened ok=True at 10mm;
    # annealed/heat-strengthened all ok=False.
    result = determine_fixed(base_ctx(framing='unframed'))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    ma = get_type(result, 'monolithic_annealed')
    mh = get_type(result, 'monolithic_heat_strengthened')
    la = get_type(result, 'laminated_annealed')
    lh = get_type(result, 'laminated_heat_strengthened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 10), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 10),
        ('laminated_toughened ok/thickness', (True, 10), (lt['ok'], lt['min_thickness']),
         lt['ok'] is True and lt['min_thickness'] == 10),
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('monolithic_heat_strengthened ok', False, mh['ok'], mh['ok'] is False),
        ('laminated_annealed ok', False, la['ok'], la['ok'] is False),
        ('laminated_heat_strengthened ok', False, lh['ok'], lh['ok'] is False),
    ]
    return report('3', 'Door, unframed -> only toughened family ok, 10mm', checks)


def test_4():
    # Door, unframed, building_use=school, sightline 800mm -> SAME result as
    # test 3 (types still narrowed to toughened family at 10mm) - confirms
    # 5.2(c)'s restriction is not overridden by the school rule.
    result = determine_fixed(base_ctx(framing='unframed', building_use='school', sightline_mm=800))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 10), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 10),
        ('laminated_toughened ok/thickness', (True, 10), (lt['ok'], lt['min_thickness']),
         lt['ok'] is True and lt['min_thickness'] == 10),
        ('monolithic_annealed still blocked', False, ma['ok'], ma['ok'] is False),
    ]
    return report('4', 'Door, unframed, school, sightline 800mm -> same as test 3 (most-restrictive-wins)', checks)


# ---------------------------------------------------------------------------
# TESTS 5-7 — Side panels
# ---------------------------------------------------------------------------

def test_5():
    # Side panel, fully framed, within 1200mm, area 0.25 m² -> monolithic
    # annealed ok=True at 5mm (within the 0.30m² side-panel cap).
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=1200,
                   panel_area_m2=0.25, panel_width_mm=500)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('monolithic_annealed ok', True, ma['ok'], ma['ok'] is True),
        ('monolithic_annealed min_thickness', 5.0, ma['min_thickness'], ma['min_thickness'] == 5.0),
    ]
    return report('5', 'Side panel, fully framed, 0.25m² -> annealed 5mm available', checks)


def test_6():
    # Same side panel, area 0.35 m² -> monolithic annealed ok=False, reason
    # cites the 0.30m² side panel limit (Clause 5.3.1(a)(i)).
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=1200,
                   panel_area_m2=0.35, panel_width_mm=500)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('why cites area exceeded', True, 'area' in (ma['why'] or ''), 'area' in (ma['why'] or '')),
    ]
    return report('6', 'Side panel, fully framed, 0.35m² -> exceeds 0.30m² cap -> ok=False', checks)


def test_7():
    # Side panel, fully framed, residential, sightline 400mm (triggers BOTH
    # 5.3.1 and 5.5), area 1.0 m² -> Grade A required, no annealed route
    # survives (5.5's 1.2m² cap alone would pass, but 5.3.1's 0.30m² cap
    # does not - combine_alts must satisfy every matching rule).
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=400,
                   panel_area_m2=1.0, panel_width_mm=800)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('both 5.3.1 and 5.5 matched', True,
         '5.3.1' in result['clauses'] and '5.5' in result['clauses'],
         '5.3.1' in result['clauses'] and '5.5' in result['clauses']),
    ]
    return report('7', 'Side panel + low-level stacking, 1.0m² -> 5.3.1 0.30m² cap blocks annealed', checks)


# ---------------------------------------------------------------------------
# TESTS 8-10 — Windows / mistaken-for-a-doorway / low-level
# ---------------------------------------------------------------------------

def test_8():
    # Window, fully framed, residential, sightline 400mm, width 600mm,
    # height 1200mm -> not exempt from 5.4 -> Grade A required, table 5.1.
    # 5.4 offers no alternative at all, so annealed is blocked entirely
    # regardless of 5.5 also matching and offering its own alternative.
    ctx = base_ctx(opening_type='window', sightline_mm=400,
                   sight_width_mm=600, sight_height_mm=1200,
                   panel_area_m2=0.72, panel_width_mm=600)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('both 5.4 and 5.5 matched', True,
         '5.4' in result['clauses'] and '5.5' in result['clauses'],
         '5.4' in result['clauses'] and '5.5' in result['clauses']),
        ('monolithic_annealed blocked by 5.4 no-alt', False, ma['ok'], ma['ok'] is False),
    ]
    return report('8', 'Window not exempt from 5.4, also triggers 5.5 -> 5.4 no-alt blocks annealed entirely', checks)


def test_9():
    # Window, fully framed, residential, sightline 400, width 480mm
    # (<=500) -> exempt from 5.4 via width exception -> falls through to
    # 5.5 alone -> Grade A with annealed alternative up to 1.2m² at 5mm.
    ctx = base_ctx(opening_type='window', sightline_mm=400,
                   sight_width_mm=480, sight_height_mm=1200,
                   panel_area_m2=0.5, panel_width_mm=480)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('5.4 not matched (exempt)', False, '5.4' in result['clauses'], '5.4' not in result['clauses']),
        ('5.5 matched', True, '5.5' in result['clauses'], '5.5' in result['clauses']),
        ('monolithic_annealed ok', True, ma['ok'], ma['ok'] is True),
        ('monolithic_annealed min_thickness', 5.0, ma['min_thickness'], ma['min_thickness'] == 5.0),
    ]
    return report('9', 'Window exempt from 5.4 (width<=500), 5.5 alone -> annealed 5mm available', checks)


def test_10():
    # Window, partly framed, residential, sightline 300mm, not reclassified
    # as side panel -> OUT OF SCOPE (open AGWA question case).
    ctx = base_ctx(opening_type='window', framing='partly', sightline_mm=300,
                   sight_width_mm=900, sight_height_mm=1500)
    result = determine_fixed(ctx)
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('out_of_scope_reasons non-empty', True, len(result['out_of_scope_reasons']) > 0,
         len(result['out_of_scope_reasons']) > 0),
        ('no table returned', None, result['table'], result['table'] is None),
    ]
    return report('10', 'Window, partly framed, low-level, not side panel -> out of scope', checks)


# ---------------------------------------------------------------------------
# TESTS 11-14 — Bathroom
# ---------------------------------------------------------------------------

def test_11():
    # Bathroom, partly framed, area 1.5 m² -> table 5.4, monolithic
    # toughened at 5mm (within the interim 2.2m² allowance), laminated
    # toughened at flat 6mm (no allowance in interim data).
    ctx = base_ctx(opening_type='window', is_bathroom=True, framing='partly',
                   sightline_mm=1000, panel_area_m2=1.5)
    result = determine_fixed(ctx)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('table', '5.4', result['table'], result['table'] == '5.4'),
        ('monolithic_toughened min_thickness', 5.0, mt['min_thickness'], mt['min_thickness'] == 5.0),
        ('laminated_toughened min_thickness', 6.0, lt['min_thickness'], lt['min_thickness'] == 6.0),
    ]
    return report('11', 'Bathroom, partly framed, 1.5m² -> MT 5mm, LT flat 6mm', checks)


def test_12():
    # Bathroom, partly framed, area 3.0 m² -> monolithic toughened at 6mm
    # (exceeds the 2.2m² allowance, falls back to the flat minimum).
    ctx = base_ctx(opening_type='window', is_bathroom=True, framing='partly',
                   sightline_mm=1000, panel_area_m2=3.0)
    result = determine_fixed(ctx)
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('monolithic_toughened min_thickness', 6.0, mt['min_thickness'], mt['min_thickness'] == 6.0),
    ]
    return report('12', 'Bathroom, partly framed, 3.0m² (exceeds allowance) -> MT 6mm', checks)


def test_13():
    # Bathroom door, fully framed -> table 5.1, Grade A, confirm the DOOR
    # rule did NOT also run (5.8 replaces 5.2 entirely for a door).
    ctx = base_ctx(opening_type='door', is_bathroom=True, framing='fully', sightline_mm=1000)
    result = determine_fixed(ctx)
    checks = [
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('only 5.8 matched, not 5.2', ['5.8'], result['clauses'], result['clauses'] == ['5.8']),
    ]
    return report('13', 'Bathroom door, fully framed -> 5.8 only, 5.2 does not also run', checks)


def test_14():
    # Bathroom side panel, fully framed, area 0.2 m² -> confirm BOTH 5.8
    # and 5.3.1 matches present, table resolves to "5.1". Per Sahil's
    # confirmed correction: 5.8's no-alt-at-all blocks the annealed route
    # entirely, even though 5.3.1's own 0.30m² cap would have permitted
    # 0.2m² on its own - the global combine_alts "any no-alt rule blocks
    # everything" rule governs over 5.3.1's more generous allowance.
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, is_bathroom=True,
                   framing='fully', sightline_mm=1000, panel_area_m2=0.2, panel_width_mm=400)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('both 5.8 and 5.3.1 matched', True,
         '5.8' in result['clauses'] and '5.3.1' in result['clauses'],
         '5.8' in result['clauses'] and '5.3.1' in result['clauses']),
        ('monolithic_annealed blocked by 5.8 no-alt', False, ma['ok'], ma['ok'] is False),
        ('monolithic_toughened still ok', True, mt['ok'], mt['ok'] is True),
    ]
    return report('14', 'Bathroom side panel, fully framed, 0.2m² -> 5.8 no-alt blocks annealed despite 5.3.1', checks)


# ---------------------------------------------------------------------------
# TESTS 15-19 — Louvres
# ---------------------------------------------------------------------------

def test_15():
    # Louvre, not in any Grade A location -> all six types ok=True,
    # Clause 5.12 note about permitting annealed outside Grade A areas.
    ctx = base_ctx(opening_type='window', building_use='other',
                   sight_width_mm=900, sight_height_mm=1500)
    ctx['blade_width_mm'] = 150
    ctx['blade_length_mm'] = 800
    result = determine_louvre(ctx)
    all_ok = all(t['ok'] for t in result['types'])
    checks = [
        ('grade_a_required', False, result['grade_a_required'], result['grade_a_required'] is False),
        ('all six types ok', True, all_ok, all_ok),
        ('5.12 note present', True,
         any('5.12' in n for n in result['notes']), any('5.12' in n for n in result['notes'])),
    ]
    return report('15', 'Louvre, no Grade A trigger -> all types ok, 5.12 note', checks)


def test_16():
    # Louvre, high_risk=Yes, blade 150x800mm (within envelope) -> only
    # monolithic toughened ok=True at 5mm.
    ctx = base_ctx(opening_type='window', high_risk=True,
                   sight_width_mm=900, sight_height_mm=1500)
    ctx['blade_width_mm'] = 150
    ctx['blade_length_mm'] = 800
    result = determine_louvre(ctx)
    mt = get_type(result, 'monolithic_toughened')
    others_blocked = all(
        get_type(result, tid)['ok'] is False
        for tid in ('monolithic_annealed', 'monolithic_heat_strengthened',
                    'laminated_annealed', 'laminated_heat_strengthened', 'laminated_toughened')
    )
    checks = [
        ('monolithic_toughened ok/thickness', (True, 5), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5),
        ('every other type blocked', True, others_blocked, others_blocked),
    ]
    return report('16', 'Louvre, high risk, blade within envelope -> MT only, 5mm', checks)


def test_17():
    # Louvre, bathroom, partly framed, blade 150x800mm, area 1.0m² -> MT
    # ok=True at 5mm (both 5.12's 5mm floor and Table 5.4's reduced
    # allowance agree here). Separately, area >2.2m² pushes Table 5.4 to
    # 6mm, and 5.12 must NOT cap it back down to 5mm.
    ctx_low = base_ctx(opening_type='window', is_bathroom=True, framing='partly',
                       sightline_mm=1000, panel_area_m2=1.0,
                       sight_width_mm=900, sight_height_mm=1500)
    ctx_low['blade_width_mm'] = 150
    ctx_low['blade_length_mm'] = 800
    result_low = determine_louvre(ctx_low)
    mt_low = get_type(result_low, 'monolithic_toughened')

    ctx_high = dict(ctx_low)
    ctx_high['panel_area_m2'] = 3.0
    result_high = determine_louvre(ctx_high)
    mt_high = get_type(result_high, 'monolithic_toughened')

    checks = [
        ('area 1.0m² -> MT ok/thickness', (True, 5.0), (mt_low['ok'], mt_low['min_thickness']),
         mt_low['ok'] is True and mt_low['min_thickness'] == 5.0),
        ('area 3.0m² -> MT ok/thickness (most-restrictive-wins, 5.12 does not cap down)',
         (True, 6.0), (mt_high['ok'], mt_high['min_thickness']),
         mt_high['ok'] is True and mt_high['min_thickness'] == 6.0),
    ]
    return report('17', 'Louvre + bathroom Table 5.4 area-conditional thickness, most-restrictive-wins', checks)


def test_18():
    # Louvre, blade 300mm wide (exceeds 230mm envelope), high_risk=True ->
    # out of scope, specific design message, even though Grade A was
    # genuinely established.
    ctx = base_ctx(opening_type='window', high_risk=True,
                   sight_width_mm=900, sight_height_mm=1500)
    ctx['blade_width_mm'] = 300
    ctx['blade_length_mm'] = 800
    result = determine_louvre(ctx)
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('grade_a_required still recorded True', True, result['grade_a_required'],
         result['grade_a_required'] is True),
        ('out_of_scope message mentions specific design', True,
         any('specific design' in r for r in result['out_of_scope_reasons']),
         any('specific design' in r for r in result['out_of_scope_reasons'])),
    ]
    return report('18', 'Louvre, blade exceeds 230mm envelope -> out of scope, specific design', checks)


def test_19():
    # Louvre, window mistaken-for-a-doorway geometry that would otherwise
    # require Grade A under 5.4 for an ordinary window -> confirm 5.4 is
    # SKIPPED entirely for the louvre method -> no other clause matches ->
    # grade_a_required=False.
    ctx = base_ctx(opening_type='window', building_use='other',
                   sight_width_mm=900, sight_height_mm=1500, sightline_mm=0,
                   opaque_or_patterned=False, rail_present=False)
    ctx['blade_width_mm'] = 150
    ctx['blade_length_mm'] = 800
    result = determine_louvre(ctx)
    checks = [
        ('grade_a_required', False, result['grade_a_required'], result['grade_a_required'] is False),
        ('5.4 not in clauses', False, '5.4' in result['clauses'], '5.4' not in result['clauses']),
        ('trail records the 5.4 skip', True,
         any('never assessed against Clause 5.4' in t for t in result['trail']),
         any('never assessed against Clause 5.4' in t for t in result['trail'])),
    ]
    return report('19', 'Louvre, would-be 5.4 geometry -> 5.4 skipped entirely, no Grade A established', checks)


# ---------------------------------------------------------------------------
# TESTS 20-23 — Sashless (Clause 5.15)
# ---------------------------------------------------------------------------

def test_20():
    # Sashless, span 900mm -> MT ok=True/5mm, LT ok=False (exceeds 750mm).
    result = determine_sashless(900)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 5.0), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5.0),
        ('laminated_toughened ok', False, lt['ok'], lt['ok'] is False),
    ]
    return report('20', 'Sashless, span 900mm -> MT 5mm, LT out of range', checks)


def test_21():
    # Sashless, span 1100mm -> MT ok=True/6mm (crosses into 1000-1200
    # tier), LT ok=False.
    result = determine_sashless(1100)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 6.0), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 6.0),
        ('laminated_toughened ok', False, lt['ok'], lt['ok'] is False),
    ]
    return report('21', 'Sashless, span 1100mm -> MT 6mm (crosses tier), LT out of range', checks)


def test_22():
    # Sashless, span 1400mm -> every type ok=False, scope=False.
    result = determine_sashless(1400)
    all_blocked = all(t['ok'] is False for t in result.get('types', []))
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('out_of_scope_reasons non-empty', True, len(result['out_of_scope_reasons']) > 0,
         len(result['out_of_scope_reasons']) > 0),
    ]
    return report('22', 'Sashless, span 1400mm -> no combination covers it, out of scope', checks)


def test_23():
    # Sashless, span 700mm -> MT ok=True/5mm, LT ok=True/6mm (both within
    # their respective caps).
    result = determine_sashless(700)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('monolithic_toughened ok/thickness', (True, 5.0), (mt['ok'], mt['min_thickness']),
         mt['ok'] is True and mt['min_thickness'] == 5.0),
        ('laminated_toughened ok/thickness', (True, 6.0), (lt['ok'], lt['min_thickness']),
         lt['ok'] is True and lt['min_thickness'] == 6.0),
    ]
    return report('23', 'Sashless, span 700mm -> MT 5mm, LT 6mm (both within caps)', checks)


# ---------------------------------------------------------------------------
# TEST 24 — Structural consistency: identical key set across every return
# path (same discipline as tests/test_structural_consistency.py)
# ---------------------------------------------------------------------------

def test_24():
    results = [
        determine_fixed(base_ctx()),
        determine_fixed(base_ctx(framing='unframed')),
        determine_fixed(base_ctx(opening_type='window', framing='partly', sightline_mm=300,
                                  sight_width_mm=900, sight_height_mm=1500)),
        determine_louvre(dict(base_ctx(opening_type='window', building_use='other',
                                        sight_width_mm=900, sight_height_mm=1500),
                               blade_width_mm=150, blade_length_mm=800)),
        determine_louvre(dict(base_ctx(opening_type='window', high_risk=True,
                                        sight_width_mm=900, sight_height_mm=1500),
                               blade_width_mm=300, blade_length_mm=800)),
        determine_sashless(900),
        determine_sashless(1400),
    ]
    key_sets = [frozenset(r.keys()) for r in results]
    all_same = len(set(key_sets)) == 1
    checks = [
        ('every return path has an identical key set', True, all_same, all_same),
    ]
    if not all_same:
        for i, ks in enumerate(key_sets):
            print(f"    result {i} keys: {sorted(ks)}")
    return report('24', 'Structural consistency - identical key set across every return path', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    print('=' * 70)
    print('  AS 1288 Calculator — Human Impact Engine Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [
        test_1, test_2, test_3, test_4, test_5, test_6, test_7, test_8,
        test_9, test_10, test_11, test_12, test_13, test_14, test_15,
        test_16, test_17, test_18, test_19, test_20, test_21, test_22,
        test_23, test_24,
    ]
    results = [t() for t in tests]

    passed = sum(1 for r in results if r)
    total = len(results)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
