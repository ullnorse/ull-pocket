"""B.Cu signal tracks: In2 plane under them; report +3V3<->GND transitions and gaps > 0.8 mm."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
zs = [(z.GetNetname(), z.GetFilledPolysList(pcbnew.In2_Cu)) for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(pcbnew.In2_Cu)]
def under(x, y):
    v = pcbnew.VECTOR2I(int(x), int(y))
    for n, ps in sorted(zs, key=lambda q: q[0] != 'GND'):
        if ps.Contains(v): return n
    return '-'
out = {}
for t in b.GetTracks():
    if t.GetClass() != 'PCB_TRACK' or t.GetLayer() != pcbnew.B_Cu: continue
    s, e = t.GetStart(), t.GetEnd(); L = mm(t.GetLength()); k = max(2, int(L / 0.05))
    seq = []
    for i in range(k + 1):
        x = s.x + (e.x - s.x) * i / k; y = s.y + (e.y - s.y) * i / k
        u = under(x, y)
        if not seq or seq[-1][0] != u: seq.append([u, (round(mm(x) - 100, 2), round(mm(y) - 100, 2)), 0.0])
        seq[-1][2] += L / k
    nets = [q for q in seq if q[0] != '-']
    trans = any(a[0] != c[0] for a, c in zip(nets, nets[1:]))
    gap = any(q[0] == '-' and q[2] > 0.8 for q in seq)
    if trans or gap:
        out.setdefault(t.GetNetname(), []).append([(q[0], q[1], round(q[2], 2)) for q in seq])
for n, v in sorted(out.items()):
    print(n); [print('   ', s) for s in v]
print('nets with B.Cu reference changes:', len(out))
