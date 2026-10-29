"""silkscreen text >= 1.0 mm high, 0.153 mm stroke; J3-cap refs off the connector body"""
import sys, pcbnew
from rt import *
r = R(sys.argv[1]); b = r.b
H, TH = MM(1.0), MM(0.153)
def fix(t):
    if t.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and t.IsVisible():
        if t.GetTextHeight() < H or t.GetTextThickness() < TH:
            t.SetTextSize(pcbnew.VECTOR2I(max(H, t.GetTextWidth()), max(H, t.GetTextHeight())))
            t.SetTextThickness(max(TH, t.GetTextThickness()))
n = 0
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT': fix(d); n += 1
for f in b.GetFootprints():
    for fl in f.GetFields(): fix(fl)
    for g in f.GraphicalItems():
        if g.GetClass() == 'PCB_TEXT': fix(g)
for ref in ('C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'R25', 'R26'):
    b.FindFootprintByReference(ref).Reference().SetLayer(pcbnew.F_Fab)
for d in ('D1', 'D5', 'D6'):
    fr = b.FindFootprintByReference(d).Reference(); fr.SetVisible(False); fr.SetLayer(pcbnew.F_Fab)
for g in b.FindFootprintByReference('J4').GraphicalItems():
    if g.GetClass() == 'PCB_TEXT' and g.GetText() == '1':
        g.SetPosition(P(10.7, 1.9))
r.save(sys.argv[1]); print('silk texts checked', n)
