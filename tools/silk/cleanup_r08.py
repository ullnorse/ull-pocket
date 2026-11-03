"""Rev 0.8 silkscreen cleanup: rings round the mounting holes (H1/H2 refs hidden),
a chin mark under the display (back: screen frame line, name), no revision or date on the silk. Idempotent: removes
its own items (tagged by width 0.151) before adding them again."""
import os
import pcbnew
from pcbnew import FromMM as I

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PCB = os.path.join(ROOT, "ull-pocket.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
W = 0.151  # line width; the odd 0.001 tags this script's shapes

for d in list(b.GetDrawings()):
    if d.GetClass() == "PCB_SHAPE" and d.GetLayer() in (F, B) and abs(pcbnew.ToMM(d.GetWidth()) - W) < 1e-4:
        b.Delete(d)
    elif d.GetClass() == "PCB_TEXT" and d.GetLayer() == B and d.GetText() in ("ull-pocket", "rev 0.8"):
        b.Delete(d)


def seg(layer, x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(I(x1), I(y1)))
    s.SetEnd(pcbnew.VECTOR2I(I(x2), I(y2)))
    s.SetLayer(layer)
    s.SetWidth(I(W))
    b.Add(s)


def ring(layer, x, y, r):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(pcbnew.VECTOR2I(I(x), I(y)))
    s.SetEnd(pcbnew.VECTOR2I(I(x + r), I(y)))
    s.SetLayer(layer)
    s.SetWidth(I(W))
    b.Add(s)


def text(layer, s, x, y, h, bold=False):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))
    t.SetTextSize(pcbnew.VECTOR2I(I(h), I(h)))
    t.SetTextThickness(I(h * (0.2 if bold else 0.15)))
    t.SetBold(bold)
    t.SetMirrored(layer == B)
    b.Add(t)


# no boxes round UP/OK/DN or PWR/CHG/USR: the switch tab pads and R5/R22 leave no 0.1 mm clearance

# both sides: rings round the M2 holes
for layer in (F, B):
    for x in (102.8, 137.2):
        ring(layer, x, 141.3, 1.7)
for ref in ("H1", "H2"):
    b.FindFootprintByReference(ref).Reference().SetVisible(False)

# back chin (product face, below the glass which ends at y 137.0): frame line split round the USB-C legs,
# name beside the receptacle (x is mirrored when you look at the back)
seg(B, 104.6, 137.6, 114.7, 137.6)
seg(B, 125.3, 137.6, 135.4, 137.6)
text(B, "ull-pocket", 130.4, 140.4, 1.2, bold=True)

for d in list(b.GetDrawings()):
    if d.GetClass() == "PCB_TEXT" and d.GetText() in ("rev 0.7  2026-11", "rev 0.8  2026-11", "r0.8"):
        b.Delete(d)
b.Save(PCB)
print("ok")
