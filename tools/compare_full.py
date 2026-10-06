"""Compare two Configurator exports in full: every difference, no line cap.
Usage: python tools/compare_full.py <saved.json> <new.json>"""
import json, sys

def diff(a, b, path=''):
    # Walk both trees together and list every place where they differ.
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append(path + '/' + k + ' only in NEW')
            elif k not in b: out.append(path + '/' + k + ' only in SAVED')
            else: out += diff(a[k], b[k], path + '/' + k)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)): out += diff(x, y, path + '[' + str(i) + ']')
    elif a != b:
        out.append(path + ': saved=' + repr(a) + ' new=' + repr(b))
    return out

def load(p):
    with open(p, encoding='utf-8-sig') as f: return json.load(f)

saved, new = load(sys.argv[1]), load(sys.argv[2])
print('schemaVersion identical:', saved.get('schemaVersion') == new.get('schemaVersion'))
for block in ('system', 'rawState'):
    d = diff(saved.get(block), new.get(block), block)
    print(block + ' differences:', len(d))
    for line in d: print('  ', line)
