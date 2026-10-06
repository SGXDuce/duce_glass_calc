import json, sys
def diff(a, b, path=''):
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
saved = json.load(open(sys.argv[1], encoding='utf-8'))
new = json.load(open(sys.argv[2], encoding='utf-8'))
print('system identical:', saved['system'] == new['system'])
print('schemaVersion identical:', saved['schemaVersion'] == new['schemaVersion'])
d = diff(saved['rawState'], new['rawState'], 'rawState')
print('rawState differences:', len(d))
for line in d[:40]: print('  ', line)
