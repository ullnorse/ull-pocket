"""Rev 0.8 board fixups after routing: silk refs (rev 0.7 conventions), J2 MP pad nets, footprint
Datasheet/Description fields from the netlist, rev text."""
import os, sys
import pcbnew
from pcbnew import FromMM as I

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from sexp import find, findall, parse  # noqa: E402

PCB = os.path.join(ROOT, "ull-pocket.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
fp = b.FindFootprintByReference


def ref_at(ref, x=None, y=None, visible=True, layer=None):
    r = fp(ref).Reference()
    r.SetVisible(visible)
    if layer is not None:
        r.SetLayer(layer)
    if x is not None:
        r.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))


# LED refs on F.Fab like D1/D5, resistor refs and the island sensor hidden, U3/U4 at their rev 0.7 spots
ref_at("D6", 133.05, 142.5, layer=pcbnew.F_Fab)
for r in ("R32", "R33", "U2"):
    ref_at(r, visible=False)
ref_at("U3", 113.5, 109.27)
ref_at("U4", 118.01, 104.11)

# J2's two MP pads are separate no-connect nets, as in rev 0.7
mp = [p for p in fp("J2").Pads() if p.GetNumber() == "MP"]
name = "unconnected-(J2-MountPin-PadMP)_1"
ni = b.FindNet(name) or pcbnew.NETINFO_ITEM(b, name)
if b.FindNet(name) is None:
    b.Add(ni)
mp[0].SetNet(ni)

# Datasheet/Description from the netlist
net = parse(open(os.path.join(ROOT, "build/ull-pocket.net")).read())
for c in findall(find(net, "components"), "comp"):
    f = fp(str(find(c, "ref")[1]))
    fields = {str(find(x, "name")[1]): str(x[2]) for x in findall(find(c, "fields") or [], "field") if len(x) > 2}
    for k, fid in (("Datasheet", pcbnew.FIELD_T_DATASHEET), ("Description", pcbnew.FIELD_T_DESCRIPTION)):
        if k in fields and f.GetField(fid).GetText() != fields[k]:
            f.GetField(fid).SetText(fields[k])

for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and d.GetText() == "r0.7":
        d.SetText("r0.8")
    if d.GetClass() == "PCB_TEXT" and d.GetText() in ("PWR", "CHG", "USR"):   # LED labels clear of R22
        d.SetPosition(pcbnew.VECTOR2I(d.GetPosition().x, I(139.8)))
b.Save(PCB)
print("ok")
