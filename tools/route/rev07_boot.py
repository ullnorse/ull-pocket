"""rev 0.7: DN button (BTN3_N) moves from IO15 (U1 pad 20) to IO9/BOOT (pad 23); BOOT net merges into BTN3_N."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
btn = b.FindNet('/BTN3_N')
def near(p, x, y): return abs(p.x - mm(x)) < 20000 and abs(p.y - mm(y)) < 20000
# drop the F.Cu stubs from pad 20 to the via and to R24
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == '/BTN3_N' and t.GetLayer() == pcbnew.F_Cu:
        if any(near(q, 134.2, 110.5) or near(q, 134.2, 110.0) or near(q, 133.55, 109.55) for q in (t.GetStart(), t.GetEnd())):
            b.Delete(t)
u1 = next(f for f in b.GetFootprints() if f.GetReference() == 'U1')
for p in u1.Pads():
    if p.GetNumber() == '20': p.SetNetCode(0)
# BOOT -> BTN3_N
boot = b.FindNet('/BOOT')
for t in b.GetTracks():
    if t.GetNetname() == '/BOOT': t.SetNet(btn)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == '/BOOT': p.SetNet(btn)
def via(x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(mm(0.5)); v.SetDrill(mm(0.3)); v.SetNet(btn); b.Add(v)
def trk(L, *pts, w=0.15):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2)); t.SetWidth(mm(w)); t.SetLayer(L); t.SetNet(btn); b.Add(t)
# R24 stub ends at (134.2, 111.5): drop a via there, join both vias on B.Cu
via(134.2, 111.5)
trk(pcbnew.B_Cu, (134.2, 111.5), (134.2, 109.55))
trk(pcbnew.B_Cu, (133.0, 109.55), (134.2, 109.55), (136.2, 109.55))
b.Save(sys.argv[2])
# second pass (run on the output): drop the via left with only a B.Cu connection, name pad 20's net like the schematic
if len(sys.argv) > 3:
    b = pcbnew.LoadBoard(sys.argv[2])
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA' and abs(t.GetPosition().x - mm(133.0)) < 20000 and abs(t.GetPosition().y - mm(109.55)) < 20000:
            b.Delete(t)
    n = pcbnew.NETINFO_ITEM(b, 'unconnected-(U1-IO15-Pad20)'); b.Add(n)
    for f in b.GetFootprints():
        if f.GetReference() == 'U1':
            for p in f.Pads():
                if p.GetNumber() == '20': p.SetNet(n)
    b.Save(sys.argv[2])
