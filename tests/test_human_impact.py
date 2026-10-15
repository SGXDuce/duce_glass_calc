# AS 1288 Glass Thickness Calculator - Human Impact Engine Test Runner
# Validates engine/human_impact (AS 1288 Section 5 - Grade A safety glass
# determination and eligible glass types/thicknesses).
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m tests.test_human_impact

from engine.human_impact import (
    determine_fixed, determine_louvre, determine_sashless,
    _load_data, NEEDS_DIMENSIONS_REASON,
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def report(test_id, description, checks):
    """
    checks is a list of (label, expected, actual, ok) tuples.
    Prints each check, then asserts every one passed - a wrong actual
    value now fails the test under pytest, not just under the __main__
    script runner.
    """
    overall = all(ok for _, _, _, ok in checks)
    marker = 'PASS' if overall else 'FAIL'
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        sub_marker = 'PASS' if ok else 'FAIL'
        print(f"    [{sub_marker}] {label}: expected={expected!r} actual={actual!r}")
    print(f"  -> {marker}")
    for label, expected, actual, ok in checks:
        assert ok, f"TEST {test_id} — {description}: {label}: expected={expected!r} actual={actual!r}"
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
# TESTS 1-2 — Doors, fully framed: monolithic annealed / heat-strengthened
# are not offered, whatever the panel size
# ---------------------------------------------------------------------------

NOT_OFFERED_WHY = "not offered by this tool"


def assert_mono_annealed_hs_not_offered(result):
    """
    Shared checks for every Grade A case: monolithic annealed and monolithic
    heat-strengthened are ok=False with the 'not offered by this tool'
    reason. Returns checks tuples for report().
    """
    ma = get_type(result, 'monolithic_annealed')
    mh = get_type(result, 'monolithic_heat_strengthened')
    return [
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('monolithic_heat_strengthened ok', False, mh['ok'], mh['ok'] is False),
        ('monolithic_annealed why', True, NOT_OFFERED_WHY in (ma['why'] or ''),
         NOT_OFFERED_WHY in (ma['why'] or '')),
        ('monolithic_heat_strengthened why', True, NOT_OFFERED_WHY in (mh['why'] or ''),
         NOT_OFFERED_WHY in (mh['why'] or '')),
    ]

def test_1():
    # Hand calculation: door, fully framed, residential, sightline 0mm,
    # 100 x 800mm = 0.08 m2, width 100mm. Rule matching: opening is a door,
    # not bathroom -> Clause 5.2 only (no school/aged/high-risk; a door never
    # runs 5.4/5.5). Grade A required, Table 5.1, no type filter -> the four
    # Grade A types ok=True. Monolithic annealed and monolithic
    # heat-strengthened are never offered -> ok=False.
    result = determine_fixed(base_ctx(panel_area_m2=0.08, panel_width_mm=100))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('1', 'Door, fully framed, 0.08m²/100mm -> monolithic annealed not offered', checks)


def test_2():
    # Hand calculation: same door as test 1 but 0.60 m2 / 500mm. Same rule
    # (Clause 5.2 only), same result as test 1: panel size has no effect on
    # the monolithic annealed / heat-strengthened answer. Grade A required,
    # Table 5.1, four Grade A types ok=True, the two monolithic annealed /
    # heat-strengthened types ok=False with the "not offered by this tool"
    # reason.
    result = determine_fixed(base_ctx(panel_area_m2=0.60, panel_width_mm=500))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('2', 'Door, fully framed, 0.60m²/500mm -> same as test 1 (size no longer matters)', checks)


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
    report('3', 'Door, unframed -> only toughened family ok, 10mm', checks)


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
    report('4', 'Door, unframed, school, sightline 800mm -> same as test 3 (most-restrictive-wins)', checks)


# ---------------------------------------------------------------------------
# TESTS 5-7 — Side panels
# ---------------------------------------------------------------------------

def test_5():
    # Hand calculation: side panel, fully framed, sightline 1200mm (not
    # below 500mm, so Clause 5.5 does not trigger), 0.25 m2. Rule matching:
    # Clause 5.3.1 only -> Grade A required, Table 5.1, no type filter ->
    # four Grade A types ok=True; monolithic annealed / heat-strengthened
    # ok=False (not offered).
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=1200,
                   panel_area_m2=0.25, panel_width_mm=500)
    result = determine_fixed(ctx)
    checks = [
        ('clauses', ['5.3.1'], result['clauses'], result['clauses'] == ['5.3.1']),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('5', 'Side panel, fully framed, 0.25m² -> monolithic annealed not offered', checks)


def test_6():
    # Hand calculation: same side panel as test 5 at 0.35 m2. Same rule
    # (Clause 5.3.1 only), same result as test 5: size has no effect. Four
    # Grade A types ok=True; monolithic annealed / heat-strengthened
    # ok=False with the "not offered by this tool" reason.
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=1200,
                   panel_area_m2=0.35, panel_width_mm=500)
    result = determine_fixed(ctx)
    checks = [
        ('clauses', ['5.3.1'], result['clauses'], result['clauses'] == ['5.3.1']),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('6', 'Side panel, fully framed, 0.35m² -> same as test 5 (size no longer matters)', checks)


def test_7():
    # Hand calculation: side panel, fully framed, residential, sightline
    # 400mm (below 500mm, so Clause 5.5 also matches alongside 5.3.1), area
    # 1.0 m2. Both rules give Grade A, Table 5.1, no type filter -> four
    # Grade A types ok=True; monolithic annealed ok=False (not offered).
    ctx = base_ctx(opening_type='side_panel', is_side_panel=True, sightline_mm=400,
                   panel_area_m2=1.0, panel_width_mm=800)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
        ('both 5.3.1 and 5.5 matched', True,
         '5.3.1' in result['clauses'] and '5.5' in result['clauses'],
         '5.3.1' in result['clauses'] and '5.5' in result['clauses']),
    ]
    report('7', 'Side panel + low-level stacking -> both clauses listed, four Grade A types', checks)


# ---------------------------------------------------------------------------
# TESTS 8-10 — Windows / mistaken-for-a-doorway / low-level
# ---------------------------------------------------------------------------

def test_8():
    # Hand calculation: window, fully framed, residential, sightline 400mm,
    # sight 600 x 1200mm. Width 600 is over 500, height 1200 is over 1000 and
    # sightline 400 is below 500, so no Clause 5.4 exception is met -> 5.4
    # matches; sightline below 500 also triggers 5.5. Both give Grade A,
    # Table 5.1. Monolithic annealed ok=False (not offered).
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
        ('monolithic_annealed not offered', False, ma['ok'], ma['ok'] is False),
    ]
    report('8', 'Window not exempt from 5.4, also triggers 5.5 -> Table 5.1, monolithic annealed not offered', checks)


def test_9():
    # Hand calculation: window, fully framed, residential, sightline 400mm,
    # sight width 480mm. Width 480 is not over 500, so Clause 5.4 is exempt
    # by width. Sightline 400 is below 500, so Clause 5.5 matches alone ->
    # Grade A required, Table 5.1, no type filter -> four Grade A types
    # ok=True; monolithic annealed / heat-strengthened ok=False (not offered).
    ctx = base_ctx(opening_type='window', sightline_mm=400,
                   sight_width_mm=480, sight_height_mm=1200,
                   panel_area_m2=0.5, panel_width_mm=480)
    result = determine_fixed(ctx)
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('5.4 not matched (exempt)', False, '5.4' in result['clauses'], '5.4' not in result['clauses']),
        ('5.5 matched', True, '5.5' in result['clauses'], '5.5' in result['clauses']),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('9', 'Window exempt from 5.4 (width<=500), 5.5 alone -> monolithic annealed not offered', checks)


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
    report('10', 'Window, partly framed, low-level, not side panel -> out of scope', checks)


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
    report('11', 'Bathroom, partly framed, 1.5m² -> MT 5mm, LT flat 6mm', checks)


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
    report('12', 'Bathroom, partly framed, 3.0m² (exceeds allowance) -> MT 6mm', checks)


def test_13():
    # Bathroom door, fully framed -> table 5.1, Grade A, confirm the DOOR
    # rule did NOT also run (5.8 replaces 5.2 entirely for a door).
    ctx = base_ctx(opening_type='door', is_bathroom=True, framing='fully', sightline_mm=1000)
    result = determine_fixed(ctx)
    checks = [
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('only 5.8 matched, not 5.2', ['5.8'], result['clauses'], result['clauses'] == ['5.8']),
    ]
    report('13', 'Bathroom door, fully framed -> 5.8 only, 5.2 does not also run', checks)


def test_14():
    # Bathroom side panel, fully framed, area 0.2 m² -> confirm BOTH 5.8
    # and 5.3.1 matches present, table resolves to "5.1". Hand calculation:
    # bathroom, sightline 1000mm (within 2000mm) -> 5.8; side panel, fully
    # framed -> 5.3.1; both Table 5.1. Monolithic annealed ok=False (not
    # offered), monolithic toughened ok=True.
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
        ('monolithic_annealed not offered', False, ma['ok'], ma['ok'] is False),
        ('monolithic_toughened still ok', True, mt['ok'], mt['ok'] is True),
    ]
    report('14', 'Bathroom side panel, fully framed, 0.2m² -> 5.8 and 5.3.1, monolithic annealed not offered', checks)


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
    report('15', 'Louvre, no Grade A trigger -> all types ok, 5.12 note', checks)


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
    report('16', 'Louvre, high risk, blade within envelope -> MT only, 5mm', checks)


def test_17():
    # Louvre, bathroom, partly framed, blade 150x800mm, area 1.0m² -> MT
    # ok=True at 5mm (both 5.12's 5mm floor and Table 5.4's reduced
    # allowance agree here). Separately, a large opening area (3.0m²) must
    # NOT push the thickness up: a louvre is read against the area of one
    # blade, which stays small.
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
        ('opening area 3.0m² -> MT ok/thickness (blade area governs, not opening area)',
         (True, 5.0), (mt_high['ok'], mt_high['min_thickness']),
         mt_high['ok'] is True and mt_high['min_thickness'] == 5.0),
    ]
    report('17', 'Louvre + bathroom Table 5.4 area-conditional thickness, most-restrictive-wins', checks)


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
    report('18', 'Louvre, blade exceeds 230mm envelope -> out of scope, specific design', checks)


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
    report('19', 'Louvre, would-be 5.4 geometry -> 5.4 skipped entirely, no Grade A established', checks)


# ---------------------------------------------------------------------------
# TESTS SA-SP — Sashless glazing through the location rules (Clause 5.15)
# ---------------------------------------------------------------------------

def sashless_ctx(**overrides):
    """A window ctx for sashless tests. framing is deliberately left at the
    base_ctx default ('fully'): the engine must set 'partly' itself."""
    overrides.setdefault('opening_type', 'window')
    return base_ctx(**overrides)


def tvals(result, type_id):
    t = get_type(result, type_id)
    return (t['ok'], t['min_thickness'])


def sashless_checks(result, expected):
    """expected: dict of type_id -> thickness (ok=True) for the types that
    must be ok; every other type must be ok=False."""
    checks = []
    for type_id in ('monolithic_toughened', 'laminated_annealed',
                    'laminated_heat_strengthened', 'laminated_toughened'):
        want = (True, float(expected[type_id])) if type_id in expected else (False, None)
        checks.append((type_id, want, tvals(result, type_id), tvals(result, type_id) == want))
    return checks


def test_SA():
    # A: residential, sightline 900, sight 1000 x 1400, span 1000.
    # 5.5 skipped (sashless). 5.4: width 1000 > 500, height 1400 > 1000, but
    # sightline 900 >= 500 -> exempt. Nothing else matches -> no requirement.
    # All six types ok; note lists low-level glazing for louvres and sashless.
    result = determine_sashless(1000, sashless_ctx(
        sightline_mm=900, sight_width_mm=1000, sight_height_mm=1400))
    checks = [
        ('scope', True, result['scope'], result['scope'] is True),
        ('grade_a_required', False, result['grade_a_required'], result['grade_a_required'] is False),
        ('all six ok', True, all(t['ok'] for t in result['types']) and len(result['types']) == 6,
         all(t['ok'] for t in result['types']) and len(result['types']) == 6),
        ('note lists low-level for louvres and sashless', True,
         any('low-level' in n and 'louvres or sashless' in n for n in result['notes']),
         any('low-level' in n and 'louvres or sashless' in n for n in result['notes'])),
        ('trail: 5.5 not applied', True,
         any('5.5' in t and 'not applied to sashless' in t for t in result['trail']),
         any('5.5' in t and 'not applied to sashless' in t for t in result['trail'])),
    ]
    report('SA', 'Sashless, residential, sightline 900 -> no requirement', checks)


def test_SB():
    # B: building 'other', sightline 300, sight 1000 x 1400, span 1000.
    # 5.4: width 1000 > 500, height 1400 > 1000, sightline 300 < 500, no
    # opaque/rail/level -> not exempt -> Grade A, no type filter.
    # 5.15: MT row up to 1000 covers span 1000 (limit inclusive) -> 5.
    # L row tops out below 1000 -> laminated types not covered.
    result = determine_sashless(1000, sashless_ctx(
        building_use='other', sightline_mm=300, sight_width_mm=1000, sight_height_mm=1400))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('clauses', ['5.15', '5.4'], result['clauses'], result['clauses'] == ['5.15', '5.4']),
    ] + sashless_checks(result, {'monolithic_toughened': 5}) + assert_mono_annealed_hs_not_offered(result)
    report('SB', 'Sashless, other, sightline 300, span 1000 -> Grade A, MT 5 only', checks)


def test_SC():
    # C: as B but 700 x 1400, span 700. Width 700 > 500 -> still not exempt.
    # MT row (limit 1000) covers 700 -> 5. L row (limit 750) covers 700 -> 6
    # for all three laminated types.
    result = determine_sashless(700, sashless_ctx(
        building_use='other', sightline_mm=300, sight_width_mm=700, sight_height_mm=1400))
    checks = sashless_checks(result, {
        'monolithic_toughened': 5, 'laminated_annealed': 6,
        'laminated_heat_strengthened': 6, 'laminated_toughened': 6,
    }) + assert_mono_annealed_hs_not_offered(result)
    report('SC', 'Sashless, span 700 -> MT 5, every laminated type 6', checks)


def test_SD():
    # D: as B, 1100 x 1400, span 1100. MT first row (limit 1000) too small;
    # second row (limit 1200) covers -> 6. L (limit 750) does not cover.
    result = determine_sashless(1100, sashless_ctx(
        building_use='other', sightline_mm=300, sight_width_mm=1100, sight_height_mm=1400))
    checks = sashless_checks(result, {'monolithic_toughened': 6}) + assert_mono_annealed_hs_not_offered(result)
    report('SD', 'Sashless, span 1100 -> MT 6 only', checks)


def test_SE():
    # E: as B, 1300 x 1400, span 1300. Above the largest MT limit (1200) and
    # the L limit -> no type covered -> scope False.
    result = determine_sashless(1300, sashless_ctx(
        building_use='other', sightline_mm=300, sight_width_mm=1300, sight_height_mm=1400))
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('reason mentions span beyond 5.15', True,
         any('span beyond 5.15' in x for x in result['out_of_scope_reasons']),
         any('span beyond 5.15' in x for x in result['out_of_scope_reasons'])),
    ]
    report('SE', 'Sashless, span 1300 -> out of scope', checks)


def test_SF():
    # F: residential, sightline 300, 1000 x 1400, span 1000.
    # 5.5 would trigger (residential, sightline < 500) but is skipped for
    # sashless. 5.4: not exempt (as B) -> Grade A. MT 5 only.
    result = determine_sashless(1000, sashless_ctx(
        sightline_mm=300, sight_width_mm=1000, sight_height_mm=1400))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('5.5 not in clauses', False, '5.5' in result['clauses'], '5.5' not in result['clauses']),
        ('5.4 in clauses', True, '5.4' in result['clauses'], '5.4' in result['clauses']),
        ('trail: 5.5 not applied', True,
         any('5.5' in t and 'not applied to sashless' in t for t in result['trail']),
         any('5.5' in t and 'not applied to sashless' in t for t in result['trail'])),
    ] + sashless_checks(result, {'monolithic_toughened': 5}) + assert_mono_annealed_hs_not_offered(result)
    report('SF', 'Sashless, residential, sightline 300, 5.5 skipped, 5.4 applies', checks)


def test_SF2():
    # F2: residential, sightline 300, 400 x 1400, span 400.
    # 5.4: width 400 <= 500 -> exempt. 5.5 skipped. Nothing matches ->
    # no requirement, all six ok, low-level note present.
    result = determine_sashless(400, sashless_ctx(
        sightline_mm=300, sight_width_mm=400, sight_height_mm=1400))
    checks = [
        ('grade_a_required', False, result['grade_a_required'], result['grade_a_required'] is False),
        ('all six ok', True, all(t['ok'] for t in result['types']), all(t['ok'] for t in result['types'])),
        ('low-level note present', True,
         any('low-level' in n for n in result['notes']), any('low-level' in n for n in result['notes'])),
    ]
    report('SF2', 'Sashless, residential, sightline 300, 400 wide -> 5.4 exempt, no requirement', checks)


def test_SG():
    # G: residential, sightline 900, high_risk, 1000 x 1400, span 1000.
    # 5.4 exempt (sightline >= 500). 5.24 (high risk) -> Grade A, no filter.
    # MT row covers 1000 -> 5; L does not cover.
    result = determine_sashless(1000, sashless_ctx(
        sightline_mm=900, high_risk=True, sight_width_mm=1000, sight_height_mm=1400))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('5.24 in clauses', True, '5.24' in result['clauses'], '5.24' in result['clauses']),
    ] + sashless_checks(result, {'monolithic_toughened': 5}) + assert_mono_annealed_hs_not_offered(result)
    report('SG', 'Sashless, high risk -> Grade A, MT 5 only', checks)


def test_SH():
    # H: bathroom, residential, sightline 1000 (<= 2000), 1000 x 1000
    # = 1.0 m2, span 1000. 5.8 (framing set to partly) -> Table 5.4,
    # toughened only. 5.4 exempt (sightline >= 500).
    # MT: 5.15 -> 5. Table 5.4 allowance row (MT, max 2.2 m2) covers 1.0 -> 5.
    # Larger of 5 and 5 = 5. Laminated: filtered out by toughened-only (and
    # L row does not cover 1000 anyway). laminated_toughened excluded by L row.
    ctx = sashless_ctx(is_bathroom=True, sightline_mm=1000, sight_width_mm=1000, sight_height_mm=1000)
    result = determine_sashless(1000, ctx)
    data = _load_data()
    print(f"    Table 5.4 allowance row used for MT at 1.0 m2:\n{data['bathroom_toughened_allowance'].to_string(index=False)}")
    checks = [
        ('5.8 in clauses', True, '5.8' in result['clauses'], '5.8' in result['clauses']),
    ] + sashless_checks(result, {'monolithic_toughened': 5}) + assert_mono_annealed_hs_not_offered(result)
    report('SH', 'Sashless bathroom 1.0 m2, span 1000 -> MT 5 only', checks)


def test_SI():
    # I: bathroom, 700 x 1000 = 0.7 m2, span 700, sightline 1000.
    # MT: 5.15 -> 5; allowance row (max 2.2 m2) covers 0.7 -> 5; larger = 5.
    # laminated_toughened: 5.15 L row (limit 750) -> 6; Table 5.4 main table,
    # first row with max area >= 0.7 is the 3.0 m2 row -> 6; larger = 6.
    # laminated_annealed / laminated_heat_strengthened: removed by the
    # toughened-only filter -> not ok.
    ctx = sashless_ctx(is_bathroom=True, sightline_mm=1000, sight_width_mm=700, sight_height_mm=1000)
    result = determine_sashless(700, ctx)
    data = _load_data()
    print(f"    Table 5.4 rows used - MT allowance row:\n{data['bathroom_toughened_allowance'].to_string(index=False)}")
    print(f"    laminated_toughened main-table row (first max_area >= 0.7):\n"
          f"{data['table_5_4_max_area'][data['table_5_4_max_area']['max_area_m2'] >= 0.7].head(1).to_string(index=False)}")
    checks = sashless_checks(result, {'monolithic_toughened': 5, 'laminated_toughened': 6}) \
        + assert_mono_annealed_hs_not_offered(result)
    report('SI', 'Sashless bathroom 0.7 m2, span 700 -> MT 5, LT 6 only', checks)


def test_SJ():
    # J: bathroom, 1300 x 1000, span 1300. Area 1.3 m2 is within Table 5.4,
    # but no 5.15 row covers 1300 -> scope False (span beyond 5.15).
    ctx = sashless_ctx(is_bathroom=True, sightline_mm=1000, sight_width_mm=1300, sight_height_mm=1000)
    result = determine_sashless(1300, ctx)
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('reason mentions span beyond 5.15', True,
         any('span beyond 5.15' in x for x in result['out_of_scope_reasons']),
         any('span beyond 5.15' in x for x in result['out_of_scope_reasons'])),
    ]
    report('SJ', 'Sashless bathroom, span 1300 -> out of scope', checks)


def test_SK():
    # K: side panel, residential, sightline 900, 1000 x 1400, span 1000.
    # Caller passes exposed_edges='n'; the engine overrides it to 'y'.
    # 5.3.1 partly + exposed -> toughened only, 10 mm minimum. 5.4 does not
    # run for a side panel; 5.5 skipped.
    # MT: larger of 10 and 5.15 (5) = 10. L row does not cover 1000.
    result = determine_sashless(1000, sashless_ctx(
        opening_type='side_panel', is_side_panel=True, exposed_edges='n',
        sightline_mm=900, sight_width_mm=1000, sight_height_mm=1400))
    checks = [
        ('trail: free edges treated as exposed', True,
         any('Sashless free edges are treated as exposed edges' in t for t in result['trail']),
         any('Sashless free edges are treated as exposed edges' in t for t in result['trail'])),
        ('5.3.1 in clauses', True, '5.3.1' in result['clauses'], '5.3.1' in result['clauses']),
    ] + sashless_checks(result, {'monolithic_toughened': 10}) + assert_mono_annealed_hs_not_offered(result)
    report('SK', 'Sashless side panel, span 1000 -> MT 10 only', checks)


def test_SL():
    # L: as K, 700 x 1400, span 700.
    # MT: max(10, 5) = 10. laminated_toughened: max(10, 6) = 10.
    # laminated_annealed / heat_strengthened removed by toughened-only.
    result = determine_sashless(700, sashless_ctx(
        opening_type='side_panel', is_side_panel=True,
        sightline_mm=900, sight_width_mm=700, sight_height_mm=1400))
    checks = sashless_checks(result, {'monolithic_toughened': 10, 'laminated_toughened': 10}) \
        + assert_mono_annealed_hs_not_offered(result)
    report('SL', 'Sashless side panel, span 700 -> MT 10, LT 10 only', checks)


def test_SM():
    # M: opening_type 'door' -> out of scope, checked first (even with the
    # sightline missing).
    result = determine_sashless(1000, base_ctx(opening_type='door', sightline_mm=None))
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('reason', ['Sashless doors are not assessed by this tool'],
         result['out_of_scope_reasons'],
         result['out_of_scope_reasons'] == ['Sashless doors are not assessed by this tool']),
    ]
    report('SM', 'Sashless door -> not assessed', checks)


def test_SN():
    # N: sightline None -> stop-gap out of scope.
    result = determine_sashless(1000, sashless_ctx(sightline_mm=None))
    checks = [
        ('scope', False, result['scope'], result['scope'] is False),
        ('reason', ['Sightline above floor is needed'], result['out_of_scope_reasons'],
         result['out_of_scope_reasons'] == ['Sightline above floor is needed']),
    ]
    report('SN', 'Sashless, no sightline -> sightline needed', checks)


def test_SO():
    # O: building 'other', sightline 300, sight sizes missing, span 1000.
    # The 5.4 size exceptions cannot be tested -> 5.4 treated as not exempt
    # (sightline 300 < 500 so no other exception) -> Grade A, MT 5 only,
    # and the trail says so.
    result = determine_sashless(1000, sashless_ctx(building_use='other', sightline_mm=300))
    checks = [
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('trail says sizes not given', True,
         any('could not be tested' in t for t in result['trail']),
         any('could not be tested' in t for t in result['trail'])),
    ] + sashless_checks(result, {'monolithic_toughened': 5})
    report('SO', 'Sashless, sight sizes missing -> 5.4 treated as not exempt', checks)


def test_SP():
    # P: bathroom, sightline 1000, sight sizes missing, span 700. Area cannot
    # be worked out: types allowed (toughened only) with thickness None and
    # the "daylight width and height needed" reason, as determine_fixed does.
    result = determine_sashless(700, sashless_ctx(is_bathroom=True, sightline_mm=1000))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('MT ok / thickness / why', (True, None, NEEDS_DIMENSIONS_REASON),
         (mt['ok'], mt['min_thickness'], mt['why']),
         mt['ok'] and mt['min_thickness'] is None and mt['why'] == NEEDS_DIMENSIONS_REASON),
        ('LT ok / thickness', (True, None), (lt['ok'], lt['min_thickness']),
         lt['ok'] and lt['min_thickness'] is None),
    ]
    report('SP', 'Sashless bathroom, no dimensions -> thickness None', checks)


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
        determine_sashless(1000, sashless_ctx(sightline_mm=300, sight_width_mm=1000,
                                              sight_height_mm=1400)),
        determine_sashless(1000, sashless_ctx(sightline_mm=900, sight_width_mm=1000,
                                              sight_height_mm=1400)),
        determine_sashless(1300, sashless_ctx(building_use='other', sightline_mm=300,
                                              sight_width_mm=1300, sight_height_mm=1400)),
        determine_sashless(1000, base_ctx(opening_type='door')),
        determine_sashless(1000, sashless_ctx(sightline_mm=None)),
    ]
    key_sets = [frozenset(r.keys()) for r in results]
    all_same = len(set(key_sets)) == 1
    checks = [
        ('every return path has an identical key set', True, all_same, all_same),
    ]
    if not all_same:
        for i, ks in enumerate(key_sets):
            print(f"    result {i} keys: {sorted(ks)}")
    report('24', 'Structural consistency - identical key set across every return path', checks)


# ---------------------------------------------------------------------------
# TEST 25 — Bathroom trail text with a missing sightline (no "None" leak)
# ---------------------------------------------------------------------------

MISSING_SIGHTLINE_TRAIL = ("Clause 5.8 (bathroom) could not be checked - sightline not "
                            "provided, so the 2000mm trigger was not tested.")
ABOVE_TRIGGER_TEXT = "is above the 2000mm trigger"


def test_25():
    # Hand calculation for the types: bathroom window, fully framed,
    # sightline None -> the 5.8 trigger cannot be tested, so no 5.8; window
    # not a side panel and no 5.4 exception met (all dimensions None) ->
    # Clause 5.4 only, Table 5.1, no type filter -> four Grade A types
    # ok=True with no thickness, monolithic annealed / heat-strengthened
    # ok=False with the "not offered by this tool" reason.
    # Bathroom, sightline_mm=None -> the "not matched" trail message must
    # read in plain words, never interpolate the missing value raw. Also
    # pins grade_a_required/table/types to the pre-fix values so the fix
    # is confirmed to only change trail wording, not any matching result.
    ctx = base_ctx(opening_type='window', is_bathroom=True, framing='fully',
                   sightline_mm=None, panel_area_m2=1.0, panel_width_mm=1000)
    result = determine_fixed(ctx)
    no_none_in_trail = all('None' not in line for line in result['trail'])
    has_new_message = any(MISSING_SIGHTLINE_TRAIL in line for line in result['trail'])
    no_above_trigger_text = all(ABOVE_TRIGGER_TEXT not in line for line in result['trail'])
    expected_types = [
        {'id': 'monolithic_annealed', 'name': 'Monolithic Annealed', 'ok': False, 'min_thickness': None, 'why': 'Monolithic annealed and monolithic heat-strengthened glass is not offered by this tool where human impact applies.'},
        {'id': 'monolithic_heat_strengthened', 'name': 'Monolithic Heat-strengthened', 'ok': False, 'min_thickness': None, 'why': 'Monolithic annealed and monolithic heat-strengthened glass is not offered by this tool where human impact applies.'},
        {'id': 'monolithic_toughened', 'name': 'Monolithic Toughened', 'ok': True, 'min_thickness': None, 'why': None},
        {'id': 'laminated_annealed', 'name': 'Laminated Annealed', 'ok': True, 'min_thickness': None, 'why': None},
        {'id': 'laminated_heat_strengthened', 'name': 'Laminated Heat-strengthened', 'ok': True, 'min_thickness': None, 'why': None},
        {'id': 'laminated_toughened', 'name': 'Laminated Toughened', 'ok': True, 'min_thickness': None, 'why': None},
    ]
    checks = [
        ('no "None" in trail', True, no_none_in_trail, no_none_in_trail),
        ('new "could not be checked" message present', True, has_new_message, has_new_message),
        ('old "is above the 2000mm trigger" text absent', True, no_above_trigger_text, no_above_trigger_text),
        ('grade_a_required unchanged', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('table unchanged', '5.1', result['table'], result['table'] == '5.1'),
        ('types unchanged', expected_types, result['types'], result['types'] == expected_types),
    ]

    # Real sightline (2100mm, above the 2000mm trigger) must keep the
    # original wording unchanged.
    ctx_real = base_ctx(opening_type='window', is_bathroom=True, framing='fully',
                        sightline_mm=2100, panel_area_m2=1.0, panel_width_mm=1000)
    result_real = determine_fixed(ctx_real)
    has_above_trigger_text = any(ABOVE_TRIGGER_TEXT in line for line in result_real['trail'])
    checks.append(('sightline=2100 keeps "is above the 2000mm trigger" wording',
                   True, has_above_trigger_text, has_above_trigger_text))

    report('25', 'Bathroom fixed panel, sightline_mm=None -> exact new trail wording, result unchanged', checks)


def test_26():
    # Same missing-sightline check for determine_louvre.
    ctx = base_ctx(opening_type='window', is_bathroom=True, framing='fully',
                   sightline_mm=None, panel_area_m2=1.0, panel_width_mm=1000,
                   blade_width_mm=200, blade_length_mm=900)
    result = determine_louvre(ctx)
    no_none_in_trail = all('None' not in line for line in result['trail'])
    has_new_message = any(MISSING_SIGHTLINE_TRAIL in line for line in result['trail'])
    no_above_trigger_text = all(ABOVE_TRIGGER_TEXT not in line for line in result['trail'])
    expected_types = [
        {'id': t, 'name': n, 'ok': True, 'min_thickness': None, 'why': None}
        for t, n in [
            ('monolithic_annealed', 'Monolithic Annealed'),
            ('monolithic_heat_strengthened', 'Monolithic Heat-strengthened'),
            ('monolithic_toughened', 'Monolithic Toughened'),
            ('laminated_annealed', 'Laminated Annealed'),
            ('laminated_heat_strengthened', 'Laminated Heat-strengthened'),
            ('laminated_toughened', 'Laminated Toughened'),
        ]
    ]
    checks = [
        ('no "None" in trail', True, no_none_in_trail, no_none_in_trail),
        ('new "could not be checked" message present', True, has_new_message, has_new_message),
        ('old "is above the 2000mm trigger" text absent', True, no_above_trigger_text, no_above_trigger_text),
        ('grade_a_required unchanged', False, result['grade_a_required'], result['grade_a_required'] is False),
        ('table unchanged', None, result['table'], result['table'] is None),
        ('types unchanged', expected_types, result['types'], result['types'] == expected_types),
    ]

    # Real sightline (2100mm) must keep the original wording for louvres too.
    ctx_real = base_ctx(opening_type='window', is_bathroom=True, framing='fully',
                        sightline_mm=2100, panel_area_m2=1.0, panel_width_mm=1000,
                        blade_width_mm=200, blade_length_mm=900)
    result_real = determine_louvre(ctx_real)
    has_above_trigger_text = any(ABOVE_TRIGGER_TEXT in line for line in result_real['trail'])
    checks.append(('sightline=2100 keeps "is above the 2000mm trigger" wording',
                   True, has_above_trigger_text, has_above_trigger_text))

    report('26', 'Bathroom louvre, sightline_mm=None -> exact new trail wording, result unchanged', checks)


# ---------------------------------------------------------------------------
# TESTS 27-32 — Laminated annealed/heat-strengthened count as Grade A
# (hand-derived expectations - not copied from engine output)
# ---------------------------------------------------------------------------

def ok_ids(result):
    return sorted(t['id'] for t in result['types'] if t['ok'])


TOUGHENED_ONLY = sorted(['monolithic_toughened', 'laminated_toughened'])
GRADE_A_CAPABLE = sorted(['monolithic_toughened', 'laminated_toughened',
                          'laminated_annealed', 'laminated_heat_strengthened'])


def test_27():
    # A: school window, sightline 800mm, sight 900x1200mm, fully framed, no
    # other triggers -> Table 5.1, clause 5.10.2, the four Grade A capable
    # types allowed, monolithic annealed/heat-strengthened blocked.
    ctx = base_ctx(opening_type='window', building_use='school', framing='fully',
                   sightline_mm=800, sight_width_mm=900, sight_height_mm=1200,
                   panel_area_m2=1.08, panel_width_mm=900)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    mh = get_type(result, 'monolithic_heat_strengthened')
    checks = [
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('clauses', ['5.10.2'], result['clauses'], result['clauses'] == ['5.10.2']),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('monolithic_heat_strengthened ok', False, mh['ok'], mh['ok'] is False),
    ]
    report('27', 'School window, fully framed -> Table 5.1, laminated annealed/HS allowed', checks)


def test_28():
    # B: same as test 27 but unframed -> Table 5.3, same allowed/blocked lists.
    ctx = base_ctx(opening_type='window', building_use='school', framing='unframed',
                   sightline_mm=800, sight_width_mm=900, sight_height_mm=1200,
                   panel_area_m2=1.08, panel_width_mm=900)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    mh = get_type(result, 'monolithic_heat_strengthened')
    checks = [
        ('table', '5.3', result['table'], result['table'] == '5.3'),
        ('clauses', ['5.10.2'], result['clauses'], result['clauses'] == ['5.10.2']),
        ('allowed types', GRADE_A_CAPABLE, ok_ids(result), ok_ids(result) == GRADE_A_CAPABLE),
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('monolithic_heat_strengthened ok', False, mh['ok'], mh['ok'] is False),
    ]
    report('28', 'School window, unframed -> Table 5.3, laminated annealed/HS allowed', checks)


def test_29():
    # Hand calculation: fully framed door, 0.08 m2, building use other, not
    # bathroom -> Clause 5.2 only, Grade A, Table 5.1, no type filter. Four
    # Grade A types ok=True (laminated annealed/HS allowed outright);
    # monolithic annealed ok=False (not offered).
    ctx = base_ctx(opening_type='door', building_use='other', framing='fully',
                   panel_area_m2=0.08, panel_width_mm=100)
    result = determine_fixed(ctx)
    ma = get_type(result, 'monolithic_annealed')
    la = get_type(result, 'laminated_annealed')
    lh = get_type(result, 'laminated_heat_strengthened')
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('monolithic_annealed ok', False, ma['ok'], ma['ok'] is False),
        ('laminated_annealed ok', True, la['ok'], la['ok'] is True),
        ('laminated_heat_strengthened ok', True, lh['ok'], lh['ok'] is True),
        ('monolithic_toughened ok', True, mt['ok'], mt['ok'] is True),
        ('laminated_toughened ok', True, lt['ok'], lt['ok'] is True),
    ]
    report('29', 'Door, fully framed, 0.08m² -> MA not offered, laminated annealed/HS and toughened allowed', checks)


def test_30():
    # D: unframed door -> toughened-only filter excludes laminated
    # annealed/HS; only the two toughened types at 10mm.
    result = determine_fixed(base_ctx(framing='unframed'))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('allowed types', TOUGHENED_ONLY, ok_ids(result), ok_ids(result) == TOUGHENED_ONLY),
        ('monolithic_toughened min_thickness', 10, mt['min_thickness'], mt['min_thickness'] == 10),
        ('laminated_toughened min_thickness', 10, lt['min_thickness'], lt['min_thickness'] == 10),
    ]
    report('30', 'Door, unframed -> toughened only at 10mm, laminated annealed/HS excluded', checks)


def test_31():
    # E: window within 300mm of a doorway (side panel), bottom of glass at
    # 800mm, partly framed, exposed edges -> toughened-only filter, 10mm.
    ctx = base_ctx(opening_type='window', is_side_panel=True, framing='partly',
                   exposed_edges='y', sightline_mm=800)
    result = determine_fixed(ctx)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('allowed types', TOUGHENED_ONLY, ok_ids(result), ok_ids(result) == TOUGHENED_ONLY),
        ('monolithic_toughened min_thickness', 10, mt['min_thickness'], mt['min_thickness'] == 10),
        ('laminated_toughened min_thickness', 10, lt['min_thickness'], lt['min_thickness'] == 10),
    ]
    report('31', 'Side panel, partly framed, exposed edges -> toughened only at 10mm', checks)


def test_32():
    # F: bathroom window, partly framed, bottom of glass 1000mm -> Table 5.4
    # toughened-only filter, laminated annealed/HS excluded.
    ctx = base_ctx(opening_type='window', is_bathroom=True, framing='partly',
                   sightline_mm=1000)
    result = determine_fixed(ctx)
    checks = [
        ('allowed types', TOUGHENED_ONLY, ok_ids(result), ok_ids(result) == TOUGHENED_ONLY),
    ]
    report('32', 'Bathroom window, partly framed -> toughened only', checks)


def test_33():
    # Removal never turns "Grade A required" into "no requirement". Hand
    # calculation: fully framed door, 0.08 m2 (100 x 800mm) - a size that
    # used to fit every exception - matches Clause 5.2, so Grade A is still
    # required and Table 5.1 is still returned, with the four Grade A types
    # allowed and monolithic annealed / heat-strengthened not offered.
    result = determine_fixed(base_ctx(panel_area_m2=0.08, panel_width_mm=100))
    checks = [
        ('in scope', True, result['scope'], result['scope'] is True),
        ('grade_a_required', True, result['grade_a_required'], result['grade_a_required'] is True),
        ('table', '5.1', result['table'], result['table'] == '5.1'),
        ('clauses', ['5.2'], result['clauses'], result['clauses'] == ['5.2']),
    ] + assert_mono_annealed_hs_not_offered(result)
    report('33', 'Door, fully framed, 0.08m² -> still Grade A required, Table 5.1', checks)


# ---------------------------------------------------------------------------
# BATHROOM (CLAUSE 5.8, PARTLY FRAMED / UNFRAMED) - HAND-DERIVED EXPECTATIONS
# ---------------------------------------------------------------------------

def _bathroom_ctx(area):
    return base_ctx(opening_type='window', is_bathroom=True, framing='partly',
                    sightline_mm=1000, panel_area_m2=area)


def _bathroom_case(test_id, area, mt_expected, lt_expected):
    result = determine_fixed(_bathroom_ctx(area))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('in scope', True, result['scope'], result['scope'] is True),
        ('table', '5.4', result['table'], result['table'] == '5.4'),
        ('monolithic_toughened min_thickness', mt_expected, mt['min_thickness'],
         mt['min_thickness'] == mt_expected),
        ('laminated_toughened min_thickness', lt_expected, lt['min_thickness'],
         lt['min_thickness'] == lt_expected),
    ]
    report(test_id, f'Bathroom partly framed, {area}m² -> MT {mt_expected}mm, LT {lt_expected}mm', checks)


def test_B1():
    _bathroom_case('B1', 1.0, 5.0, 6.0)


def test_B2():
    _bathroom_case('B2', 2.2, 5.0, 6.0)


def test_B3():
    _bathroom_case('B3', 2.5, 6.0, 6.0)


def test_B4():
    _bathroom_case('B4', 3.0, 6.0, 6.0)


def test_B5():
    _bathroom_case('B5', 3.5, 8.0, 8.0)


def test_B6():
    _bathroom_case('B6', 5.0, 10.0, 10.0)


def test_B7():
    _bathroom_case('B7', 7.5, 12.0, 12.0)


def test_B8():
    result = determine_fixed(_bathroom_ctx(8.0))
    checks = [
        ('out of scope', False, result['scope'], result['scope'] is False),
        ('has a reason', True, result['out_of_scope_reasons'],
         len(result['out_of_scope_reasons']) == 1),
    ]
    report('B8', 'Bathroom partly framed, 8.0m² -> out of scope', checks)


def test_B9():
    result = determine_fixed(_bathroom_ctx(None))
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('allowed types', TOUGHENED_ONLY, ok_ids(result), ok_ids(result) == TOUGHENED_ONLY),
        ('MT min_thickness None', None, mt['min_thickness'], mt['min_thickness'] is None),
        ('LT min_thickness None', None, lt['min_thickness'], lt['min_thickness'] is None),
        ('reason mentions daylight width and height', True, mt['why'],
         'daylight width and height' in (mt['why'] or '')),
    ]
    report('B9', 'Bathroom partly framed, no area -> types allowed, thickness None with reason', checks)


def test_B10():
    ctx = _bathroom_ctx(None)
    ctx['blade_width_mm'] = 230
    ctx['blade_length_mm'] = 1000
    result = determine_louvre(ctx)
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('allowed types', ['monolithic_toughened'], ok_ids(result),
         ok_ids(result) == ['monolithic_toughened']),
        ('monolithic_toughened min_thickness', 5.0, mt['min_thickness'], mt['min_thickness'] == 5.0),
    ]
    report('B10', 'Bathroom louvre, blade 230x1000 -> monolithic toughened 5mm only', checks)


def test_B11():
    # Bathroom side panel with exposed edges: the side-panel rule's higher
    # minimum governs over the bathroom table.
    ctx = base_ctx(opening_type='window', is_side_panel=True, is_bathroom=True,
                   framing='partly', exposed_edges='y', sightline_mm=800,
                   panel_area_m2=1.0)
    result = determine_fixed(ctx)
    mt = get_type(result, 'monolithic_toughened')
    lt = get_type(result, 'laminated_toughened')
    checks = [
        ('table', '5.4', result['table'], result['table'] == '5.4'),
        ('allowed types', TOUGHENED_ONLY, ok_ids(result), ok_ids(result) == TOUGHENED_ONLY),
        ('monolithic_toughened min_thickness', 10.0, mt['min_thickness'], mt['min_thickness'] == 10.0),
        ('laminated_toughened min_thickness', 10.0, lt['min_thickness'], lt['min_thickness'] == 10.0),
    ]
    report('B11', 'Bathroom side panel, exposed edges -> other rule 10mm governs', checks)


def test_B12():
    ctx = base_ctx(opening_type='window', is_side_panel=True, is_bathroom=True,
                   framing='partly', exposed_edges='y', sightline_mm=800)
    ctx['blade_width_mm'] = 150
    ctx['blade_length_mm'] = 900
    result = determine_louvre(ctx)
    mt = get_type(result, 'monolithic_toughened')
    checks = [
        ('allowed types', ['monolithic_toughened'], ok_ids(result),
         ok_ids(result) == ['monolithic_toughened']),
        ('monolithic_toughened min_thickness', 10.0, mt['min_thickness'], mt['min_thickness'] == 10.0),
    ]
    report('B12', 'Bathroom side-panel louvre, exposed edges -> other rule 10mm governs', checks)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run_tests():
    # report() now asserts internally, so a test function either completes
    # (pass) or raises AssertionError (fail) - it no longer returns a bool.
    # This loop catches per-test AssertionErrors itself so the script-mode
    # runner still tallies and prints a pass count, matching its previous
    # behaviour.
    print('=' * 70)
    print('  AS 1288 Calculator — Human Impact Engine Test Runner')
    print('  Duce Timber Windows and Doors')
    print('=' * 70)

    tests = [
        test_1, test_2, test_3, test_4, test_5, test_6, test_7, test_8,
        test_9, test_10, test_11, test_12, test_13, test_14, test_15,
        test_16, test_17, test_18, test_19,
        test_SA, test_SB, test_SC, test_SD, test_SE, test_SF, test_SF2, test_SG,
        test_SH, test_SI, test_SJ, test_SK, test_SL, test_SM, test_SN, test_SO,
        test_SP, test_24, test_25, test_26, test_27, test_28, test_29,
        test_30, test_31, test_32, test_33,
        test_B1, test_B2, test_B3, test_B4, test_B5, test_B6, test_B7,
        test_B8, test_B9, test_B10, test_B11, test_B12,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"    ASSERTION FAILED: {e}")
    total = len(tests)

    print()
    print('=' * 70)
    print(f"{passed}/{total} tests passed.")
    print('=' * 70)


if __name__ == '__main__':
    run_tests()
