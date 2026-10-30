"""text-edit: drop F.SilkS graphics of SW1/J1/U1 that reach within 0.2 mm of or past the main board outline"""
import math, re, sys
p = sys.argv[1]; s = open(p).read()
def block(i):  # end index of s-expr starting at s[i]=='('
    d = 0
    for j in range(i, len(s)):
        d += (s[j] == '(') - (s[j] == ')')
        if d == 0: return j + 1
xs, ys = [], []
for m in re.finditer(r'\(gr_(?:line|arc|rect)\b', s):
    b = s[m.start():block(m.start())]
    if 'Edge.Cuts' in b:
        for x, y in re.findall(r'\((?:start|end|mid) ([-\d.]+) ([-\d.]+)\)', b): xs.append(float(x)); ys.append(float(y))
# main body only: ignore the SHT31 tab above the body (y < body top)
top = sorted(set(ys))[2] if False else None
x0, x1, y1 = min(xs) + .2, max(xs) - .2, max(ys) - .2
y0 = float(sys.argv[2]) + .2  # body top edge
cut = []
for ref in ('SW1', 'J1', 'U1'):
    m = re.search(r'\(property "Reference" "%s"' % ref, s)
    fs = s.rfind('(footprint ', 0, m.start()); fe = block(fs); fb = s[fs:fe]
    ax, ay, *r = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', fb).groups()
    ax, ay, a = float(ax), float(ay), math.radians(float(r[0] or 0))
    for g in re.finditer(r'\(fp_(?:line|rect|arc|poly)\b', fb):
        gb = fb[g.start():block(fs + g.start()) - fs]
        if '"F.SilkS"' not in gb: continue
        for lx, ly in re.findall(r'\((?:start|end|mid|xy) ([-\d.]+) ([-\d.]+)\)', gb):
            lx, ly = float(lx), float(ly)
            X = ax + lx * math.cos(a) + ly * math.sin(a); Y = ay - lx * math.sin(a) + ly * math.cos(a)
            if not (x0 < X < x1 and y0 < Y < y1):
                cut.append((fs + g.start(), fs + g.start() + len(gb))); break
for a_, b_ in sorted(cut, reverse=True):
    s = s[:a_].rstrip(' \t') + s[b_:]
open(p, 'w').write(s); print('removed', len(cut))
