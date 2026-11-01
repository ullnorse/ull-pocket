"""chamfer.py in.kicad_pcb out.kicad_pcb: replace sharp track corners (bend >= 60 deg) with a
diagonal; DRC after each pass and shrink/undo chamfers that cause violations."""
import sys, math, json, collections, subprocess, os, pcbnew
P = os.path.dirname(os.path.abspath(__file__)) + '/../..'
CHK = P + '/build/route/chk'
IU = 1e6
src, dst = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
pads = [p for f in b.GetFootprints() for p in f.Pads()]
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']

def corners():
    ends = collections.defaultdict(list)
    for t in b.GetTracks():
        if t.GetClass() != 'PCB_TRACK': continue
        for a, c in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
            ends[(t.GetLayer(), a.x, a.y)].append((t, c))
    out = []
    for (L, x, y), v in ends.items():
        if len(v) != 2: continue
        (t1, c1), (t2, c2) = v
        if t1.GetNetCode() != t2.GetNetCode(): continue
        u = (c1.x - x, c1.y - y); w = (c2.x - x, c2.y - y)
        l1, l2 = math.hypot(*u), math.hypot(*w)
        if l1 == 0 or l2 == 0: continue
        bend = 180 - math.degrees(math.acos(max(-1, min(1, (u[0]*w[0] + u[1]*w[1]) / l1 / l2))))
        if bend < 60: continue
        a = pcbnew.VECTOR2I(x, y)
        if any(abs(vv.GetPosition().x - x) < 20000 and abs(vv.GetPosition().y - y) < 20000 for vv in vias): continue
        if any(p.IsOnLayer(L) and p.GetEffectivePolygon(L).Contains(a) for p in pads): continue
        out.append((t1, t2, x, y, u, w, l1, l2, bend))
    return out

def end_at(t, x, y):
    return 'S' if (t.GetStart().x, t.GetStart().y) == (x, y) else 'E'

def setend(t, which, p):
    (t.SetStart if which == 'S' else t.SetEnd)(p)

def apply(c, d):
    t1, t2, x, y, u, w, l1, l2, bend = c
    d = min(d, 0.45 * l1, 0.45 * l2)
    if d < 0.08 * IU: return None
    p1 = pcbnew.VECTOR2I(int(round(x + u[0] / l1 * d)), int(round(y + u[1] / l1 * d)))
    p2 = pcbnew.VECTOR2I(int(round(x + w[0] / l2 * d)), int(round(y + w[1] / l2 * d)))
    e1, e2 = end_at(t1, x, y), end_at(t2, x, y)
    setend(t1, e1, p1); setend(t2, e2, p2)
    n = pcbnew.PCB_TRACK(b)
    n.SetStart(p1); n.SetEnd(p2); n.SetWidth(min(t1.GetWidth(), t2.GetWidth()))
    n.SetLayer(t1.GetLayer()); n.SetNetCode(t1.GetNetCode()); b.Add(n)
    return (c, d, n, e1, e2)

def undo(r):
    (t1, t2, x, y, *_), d, n, e1, e2 = r
    a = pcbnew.VECTOR2I(x, y)
    setend(t1, e1, a); setend(t2, e2, a); b.Remove(n)

def drc_bad():
    tmp = CHK + '/ull-pocket.kicad_pcb'
    for f in ('ull-pocket.kicad_pro', 'ull-pocket.kicad_dru', 'ull-pocket.kicad_sch', 'fp-lib-table', 'sym-lib-table'):
        subprocess.run(['cp', P + '/' + f, CHK + '/'])
    if not os.path.exists(CHK + '/lib'): os.symlink(os.path.abspath(P + '/lib'), CHK + '/lib')
    b.Save(tmp)
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--severity-all', '--format', 'json',
                    '-o', CHK + '/drc.json', tmp], capture_output=True)
    j = json.load(open(CHK + '/drc.json'))
    ids, kinds = set(), collections.Counter()
    for v in j['violations'] + j.get('unconnected_items', []):
        if v['type'] == 'lib_footprint_mismatch': continue
        kinds[v['type']] += 1
        for it in v['items']: ids.add(it['uuid'])
    return ids, kinds

done = []
for c in corners():
    r = apply(c, float(os.environ.get("CH_MM", "1.2")) * IU)
    if r: done.append(r)
print('chamfered', len(done))
for it in range(6):
    ids, kinds = drc_bad()
    bad = [r for r in done if {r[2].m_Uuid.AsString(), r[0][0].m_Uuid.AsString(), r[0][1].m_Uuid.AsString()} & ids]
    print('pass', it, dict(kinds), 'offending', len(bad))
    if not kinds: break
    for r in bad:
        undo(r); done.remove(r)
        if it < 4:
            r2 = apply(r[0], r[1] * 0.5)
            if r2: done.append(r2)
print('kept', len(done))
b.Save(dst)
