import sys, pcbnew
from rt import xy
b = pcbnew.LoadBoard(sys.argv[1])
fps = [f for f in b.GetFootprints() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() and not f.GetReference().startswith('ASSY')]
for i, a in enumerate(fps):
    for c in fps[i+1:]:
        s = pcbnew.SHAPE_POLY_SET(a.GetCourtyard(pcbnew.F_CrtYd)); s.BooleanIntersection(c.GetCourtyard(pcbnew.F_CrtYd))
        if s.OutlineCount() and s.Area() > 1000:
            print('overlap', a.GetReference(), c.GetReference(), '%.3f mm2' % (s.Area() / 1e12))
for r in sys.argv[2:]:
    f = b.FindFootprintByReference(r); ol = f.GetCourtyard(pcbnew.F_CrtYd)
    for k in range(ol.OutlineCount()):
        o = ol.Outline(k); print(r, [tuple(round(v, 2) for v in xy(o.CPoint(j))) for j in range(o.PointCount())])
