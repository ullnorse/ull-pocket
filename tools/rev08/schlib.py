"""Small S-expression helpers for editing ull-pocket.kicad_sch by text."""
import re

def block(s, start):
    d = 0
    for j in range(start, len(s)):
        d += (s[j] == '(') - (s[j] == ')')
        if d == 0:
            return start, j + 1
    raise ValueError("unbalanced")

def instance(s, ref):
    """(start, end, x, y, rot, lib_id) of the placed symbol with this reference."""
    for m in re.finditer(r'\n\t\(symbol\s*\(lib_id "([^"]*)"\)\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)', s):
        a, b = block(s, m.start() + 2)
        if re.search(r'\(property "Reference" "%s"' % re.escape(ref), s[a:b]):
            return a, b, float(m.group(2)), float(m.group(3)), int(m.group(4)), m.group(1)
    raise KeyError(ref)

def lib_pins(s, name):
    i = s.index('(symbol "%s"' % name)
    a, b = block(s, i)
    return [(n, nm, float(x), float(y)) for _, x, y, nm, n in
            re.findall(r'\(pin (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+) \d+\).*?\(name "([^"]*)".*?\(number "([^"]*)"', s[a:b], re.S)]

def pin_xy(x, y, rot, px, py):
    # schematic Y is down; library Y is up
    if rot == 0: return round(x + px, 2), round(y - py, 2)
    if rot == 90: return round(x - py, 2), round(y - px, 2)
    if rot == 180: return round(x - px, 2), round(y + py, 2)
    if rot == 270: return round(x + py, 2), round(y + px, 2)

def touching(s, x, y):
    out = []
    for m in re.finditer(r'\n\t\((wire|label|global_label|hierarchical_label|no_connect|junction|symbol)\b', s):
        a, b = block(s, m.start() + 2)
        t = s[a:b]
        pts = re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', t) if m.group(1) == 'wire' else re.findall(r'^\((?:\w+)[^\n]*?\(at ([-\d.]+) ([-\d.]+)', t) or re.findall(r'\(at ([-\d.]+) ([-\d.]+)', t)[:1]
        for px, py in pts:
            if abs(float(px) - x) < 0.01 and abs(float(py) - y) < 0.01:
                lab = re.search(r'^\(\w+ "([^"]*)"', t)
                lid = re.search(r'\(lib_id "([^"]*)"', t)
                out.append((m.group(1), (lab or lid).group(1) if (lab or lid) else '', a, b))
    return out
