"""acute (<90 deg) junctions between same-net tracks, ignoring vertices inside pads or vias"""
import sys, math, collections, pcbnew
from rt import xy
b = pcbnew.LoadBoard(sys.argv[1])
pads = [(p, p.GetNetname()) for f in b.GetFootprints() for p in f.Pads()]
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
ends = collections.defaultdict(list)
for t in b.GetTracks():
    if t.GetClass() != 'PCB_TRACK': continue
    for a, c in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        ends[(t.GetLayer(), round(a.x / 2000), round(a.y / 2000))].append((t, a, c))
n = 0
for k, v in ends.items():
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            t1, a, c1 = v[i]; t2, _, c2 = v[j]
            if t1.GetNetname() != t2.GetNetname(): continue
            u = (c1.x - a.x, c1.y - a.y); w = (c2.x - a.x, c2.y - a.y); nn = math.hypot(*u) * math.hypot(*w)
            if nn == 0: continue
            ang = math.degrees(math.acos(max(-1, min(1, (u[0] * w[0] + u[1] * w[1]) / nn))))
            if ang >= 89: continue
            if any(p.IsOnLayer(k[0]) and p.GetEffectivePolygon(k[0]).Contains(a) for p, nm in pads): continue
            if any(abs(vv.GetPosition().x - a.x) < 20000 and abs(vv.GetPosition().y - a.y) < 20000 for vv in vias): continue
            n += 1; print('acute %.0f deg' % ang, t1.GetNetname(), b.GetLayerName(k[0]), tuple(round(q, 2) for q in xy(a)))
print('acute junctions outside pads/vias:', n)
