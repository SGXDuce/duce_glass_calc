# AS 1288 Glass Thickness Calculator - Room Question Tests
# Validates engine/shared/room.py: the room question (bathroom, ensuite or spa
# room / kitchen / neither) and when the room rule applies.
# Duce Timber Windows and Doors
#
# Run from the project root (duce_glass_calc/):
#   python -m pytest tests/test_room.py

import ast
import os

from engine.shared.room import (
    validate_room, room_rule_applies, ROOMS, ROOM_SIGHTLINE_LIMIT_MM, MISSING_ROOM_TEXT,
)


def report(test_id, description, checks):
    overall = all(ok for _, _, _, ok in checks)
    print()
    print(f"TEST {test_id} — {description}")
    for label, expected, actual, ok in checks:
        print(f"    [{'PASS' if ok else 'FAIL'}] {label}: expected={expected!r} actual={actual!r}")
    for label, expected, actual, ok in checks:
        assert ok, f"TEST {test_id} — {description}: {label}: expected={expected!r} actual={actual!r}"
    return overall


def test_room_validation():
    checks = []
    for room in ('bathroom', 'kitchen', 'neither'):
        got = validate_room(room)
        checks.append((f'{room!r} is valid', (room, None), got, got == (room, None)))
    checks.append(('three answers only', ('bathroom', 'kitchen', 'neither'), ROOMS,
                   ROOMS == ('bathroom', 'kitchen', 'neither')))
    for bad in (None, '', 'Bathroom', 'KITCHEN', 'ensuite', 'shower', True, 0, ['bathroom'], {'a': 1}):
        got = validate_room(bad)
        checks.append((f'{bad!r} is unanswered', (None, [MISSING_ROOM_TEXT]), got,
                       got == (None, [MISSING_ROOM_TEXT])))
    report('room_1', 'Only the three answers are valid; anything else is unanswered, never neither', checks)


def test_room_rule_applies():
    limit = ROOM_SIGHTLINE_LIMIT_MM
    checks = []
    for room in ('bathroom', 'kitchen'):
        checks.append((f'{room} well inside', True, room_rule_applies(room, 1000),
                       room_rule_applies(room, 1000) is True))
        checks.append((f'{room} exactly at the limit (inclusive)', True, room_rule_applies(room, limit),
                       room_rule_applies(room, limit) is True))
        checks.append((f'{room} just above the limit', False, room_rule_applies(room, limit + 1),
                       room_rule_applies(room, limit + 1) is False))
        checks.append((f'{room} missing sightline', False, room_rule_applies(room, None),
                       room_rule_applies(room, None) is False))
    for other in ('neither', None, 'Bathroom', True):
        checks.append((f'{other!r} never applies', False, room_rule_applies(other, 0),
                       room_rule_applies(other, 0) is False))
    report('room_2', 'Room rule: bathroom and kitchen alike, inclusive at the limit', checks)


def test_room_no_forbidden_imports():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'engine', 'shared', 'room.py')
    with open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or '')
    forbidden = ('wind_load', 'silicone_bite', 'combined', 'human_impact')
    hits = [n for n in names if any(x in n for x in forbidden)]
    report('room_3', 'room.py imports nothing from the four engines', [('forbidden imports', [], hits, hits == [])])
