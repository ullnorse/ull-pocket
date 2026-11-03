"""Try to show hidden reference designators next to their part.

A spot is accepted only if the 1.0 mm text keeps 0.15 mm from every pad,
0.1 mm from other silk, 0.3 mm from the board edge, stays off other parts'
bodies (courtyards), and its owner is the nearest part. Reports what it
could not place. Usage: place_refs.py board REF...  (no args: hidden refs)
"""
import sys, pcbnew
F, M = pcbnew.FromMM, pcbnew.ToMM
SKIP = {"ASSY1", "ASSY2", "J1", "J2", "J3", "J4", "SW1", "SW2", "SW3", "D1", "D5", "D6",
        "TP1", "TP3", "TP4", "TP5", "U2"}  # labelled by board text or deliberately hidden

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
fps = {f.GetReference(): f for f in b.GetFootprints()}
want = sys.argv[2:] or [r for r, f in fps.items() if (not f.Reference().IsVisible() or f.Reference().GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS)) and r not in SKIP]
edge = b.GetBoardEdgesBoundingBox(); edge.Inflate(-F(0.3))

def rect(bb):
    return (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())

def srect(item):
    """Stroke extents; GetBoundingBox() pads text by ~0.5 mm."""
    return rect(item.GetEffectiveShape().BBox())

def grow(r, cl):
    c = F(cl); return (r[0] - c, r[1] - c, r[2] + c, r[3] + c)

def inter(a, c):
    return a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]

def dist2(r, x, y):
    dx = max(r[0] - x, 0, x - r[2]); dy = max(r[1] - y, 0, y - r[3]); return dx * dx + dy * dy

SILK = {}
for f in b.GetFootprints():
    for g in list(f.GraphicalItems()) + [f.Reference(), f.Value()]:
        if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and g.IsVisible() if g.GetClass() == "PCB_FIELD" else g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            SILK.setdefault(g.GetLayer(), []).append((f.GetReference(), srect(g)))
for d in b.GetDrawings():
    if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        SILK.setdefault(d.GetLayer(), []).append(("", srect(d)))
PADS = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
for f in b.GetFootprints():
    for p in f.Pads():
        for l in PADS:
            if p.IsOnLayer(l): PADS[l].append(rect(p.GetBoundingBox()))
VIAS = [rect(v.GetBoundingBox()) for v in b.GetTracks() if v.GetClass() == "PCB_VIA"]
CRT = {}
for f in b.GetFootprints():
    for l in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        poly = f.GetCourtyard(l)
        if poly.OutlineCount(): CRT.setdefault(l, []).append((f.GetReference(), rect(poly.BBox())))
PADREFS = {f.GetReference(): [rect(p.GetBoundingBox()) for p in f.Pads()] for f in b.GetFootprints() if len(f.Pads())}
BODY = {f.GetReference(): rect(f.GetBoundingBox(False)) for f in b.GetFootprints()}
E = rect(edge)

placed, failed = [], []
for ref in want:
    f = fps[ref]; t = f.Reference(); top = not f.IsFlipped()
    silk = pcbnew.F_SilkS if top else pcbnew.B_SilkS
    crt = pcbnew.F_CrtYd if top else pcbnew.B_CrtYd
    others = [r for o, r in SILK.get(silk, []) if not (o == ref and False)]
    pads = PADS[pcbnew.F_Cu if top else pcbnew.B_Cu]
    crts = [r for o, r in CRT.get(crt, []) if o != ref]
    own = BODY[ref]
    orig = (t.IsVisible(), t.GetLayer(), t.GetPosition(), t.GetTextAngleDegrees(), t.GetTextSize(), t.GetTextThickness())
    others = [r for o, r in SILK.get(silk, []) if r != srect(t) or o != ref] if orig[0] else others
    t.SetVisible(True); t.SetLayer(silk); t.SetTextSize(pcbnew.VECTOR2I(F(1), F(1))); t.SetTextThickness(F(0.15))
    best = None
    cx, cy = (own[0] + own[2]) // 2, (own[1] + own[3]) // 2
    w, h = (own[2] - own[0]) // 2, (own[3] - own[1]) // 2
    for ang in (0, 90):
        t.SetTextAngleDegrees(ang)
        t.SetPosition(pcbnew.VECTOR2I(cx, cy)); r0 = srect(t)
        tw, th = (r0[2] - r0[0]) // 2, (r0[3] - r0[1]) // 2
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            for gap in (0.15, 0.35, 0.6):
                x = cx + dx * (w + tw + F(gap)); y = cy + dy * (h + th + F(gap))
                tb = (r0[0] + x - cx, r0[1] + y - cy, r0[2] + x - cx, r0[3] + y - cy)
                if not (tb[0] >= E[0] and tb[1] >= E[1] and tb[2] <= E[2] and tb[3] <= E[3]): continue
                if any(inter(grow(o, 0.15), tb) for o in pads): continue
                if any(inter(grow(o, 0.1), tb) for o in VIAS + others): continue
                if any(inter(c, tb) for c in crts): continue
                mx, my = (tb[0] + tb[2]) // 2, (tb[1] + tb[3]) // 2
                dn = min((min(dist2(r, mx, my) for r in rs), o) for o, rs in PADREFS.items() if o != ref)
                if min(dist2(r, mx, my) for r in PADREFS[ref]) * 1.44 > dn[0]: continue
                score = gap + (0 if ang == 0 else 0.05) + (0 if (dx == 0 or dy == 0) else 0.3)
                if best is None or score < best[0]: best = (score, ang, int(x), int(y), tb)
    if best:
        t.SetTextAngleDegrees(best[1]); t.SetPosition(pcbnew.VECTOR2I(best[2], best[3])); placed.append(ref)
        SILK.setdefault(silk, []).append((ref, best[4]))
    else:
        t.SetVisible(orig[0]); t.SetLayer(orig[1]); t.SetPosition(orig[2]); t.SetTextAngleDegrees(orig[3])
        t.SetTextSize(orig[4]); t.SetTextThickness(orig[5]); failed.append(ref)
b.Save(path)
print("placed", placed); print("no room", failed)
