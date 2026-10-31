"""Place the F.Silk reference of the given parts (1.0 mm / 0.15 mm, 0 or 90 deg) beside the part,
clear of pads, bodies, edges and every visible silk item. Reuses silk_polish.py's rasters.

    python3 silk_place.py board.kicad_pcb R27 R28 C27
Parts that find no spot within 2 mm get their reference on F.Fab."""
import sys
import numpy as np
FN, REFS = sys.argv[1], sys.argv[2:]
PADX = 0.25
if REFS and REFS[0].startswith("--pad="):
    PADX = float(REFS.pop(0)[6:])
sys.argv = [sys.argv[0], FN]
src = open(__file__.replace('silk_place.py', 'silk_polish.py')).read()
exec(src[:src.index('FID_OK = []')])
_ext = ext


def ext(s, ang, h=TXT, th=STK):  # DRC tests the text box, not the strokes: pad the stroke extents
    l, t, r_, b_ = _ext(s, ang, h, th)
    return (l - PADX, t - PADX, r_ + PADX, b_ + PADX)


def bdist(bx, x, y):
    return np.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3]))


for ref in REFS:  # hide first so their old positions do not block themselves
    b.FindFootprintByReference(ref).Reference().SetVisible(False)
A = side_obstacles('F') | body_raster()
TX = np.zeros_like(A)
for f in b.GetFootprints():
    for t in list(f.GetFields()) + [x for x in f.GraphicalItems() if x.GetClass() == 'PCB_TEXT']:
        if t.IsVisible() and t.GetLayer() == pcbnew.F_SilkS:
            c = xy(t.GetPosition()); mark(TX, c[0], c[1], ext(t.GetShownText(True), t.GetTextAngleDegrees()), 0.35)
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS:
        c = xy(d.GetPosition()); mark(TX, c[0], c[1], ext(d.GetText(), d.GetTextAngleDegrees()), 0.35)
for ref in REFS:
    f = b.FindFootprintByReference(ref)
    bx = part_box(f)
    best = None
    for ang in (0, 90):
        e = ext(ref, ang)
        for cy in np.arange(bx[1] - 3, bx[3] + 3, 0.05):
            for cx in np.arange(bx[0] - 3.5, bx[2] + 3.5, 0.05):
                tx, ty = cx + (e[0] + e[2]) / 2, cy + (e[1] + e[3]) / 2
                d = bdist(bx, tx, ty) - min((e[2] - e[0]), (e[3] - e[1])) / 2
                if d > 2.0 or (best and d + (0.3 if ang else 0) >= best[0]):
                    continue
                if free(A | TX, cx, cy, e):
                    best = (d + (0.3 if ang else 0), cx, cy, ang, e)
    t = f.Reference()
    if best is None:
        t.SetLayer(pcbnew.F_Fab); t.SetVisible(True)
        print(ref, 'no spot -> F.Fab')
        continue
    t.SetLayer(pcbnew.F_SilkS); t.SetVisible(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(TXT), MM(TXT))); t.SetTextThickness(MM(STK))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(best[3]); t.SetPosition(P(round(best[1], 3), round(best[2], 3)))
    mark(TX, best[1], best[2], best[4], 0.35)
    print(ref, 'at', round(best[1], 2), round(best[2], 2), best[3])
b.Save(FN)
