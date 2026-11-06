"""Fit the board to the 103040 cell (PH-1.25 plug): J2 -> DEALON 1.25-2PWB on the Molex 53261 land, R9 -> 2.2k."""
import pcbnew
from route_sensors_lib import Board

PCB = "ull-pocket.kicad_pcb"
LIB = "/usr/share/kicad/footprints/Connector_Molex.pretty"
NAME = "Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal"
P = 100.0  # board origin in KiCad coordinates

B = Board(PCB)
b = B.b
old = b.FindFootprintByReference("J2")
nets = {p.GetNumber(): p.GetNet() for p in old.Pads() if p.GetNumber() in ("1", "2")}
mp_nets = [p.GetNet() for p in sorted((p for p in old.Pads() if p.GetNumber() == "MP"), key=lambda p: p.GetPosition().y)]
new = pcbnew.FootprintLoad(LIB, NAME)
new.SetFPID(pcbnew.LIB_ID("Connector_Molex", NAME))
new.SetReference("J2")
new.SetValue("1.25-2PWB")
new.SetPath(old.GetPath())
new.SetSheetname(old.GetSheetname())
new.SetSheetfile(old.GetSheetfile())
for k, v in (("Datasheet", "https://www.lcsc.com/datasheet/C2905009.pdf"),
             ("Description", "1.25 mm 2-pin SMD right-angle battery socket (DEALON 1.25-2PWB, PicoBlade series, Molex 53261 land)"),
             ("Manufacturer", "DEALON"), ("MPN", "1.25-2PWB"), ("LCSC", "C2905009")):
    new.SetField(k, v)
for f in new.GetFields():
    if f.GetName() not in ("Reference", "Value"):
        f.SetVisible(False)
b.Delete(old)
b.Add(new)
new.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(P + 3.4), pcbnew.FromMM(P + 6.2)))
new.SetOrientationDegrees(-90)
for p in new.Pads():
    if p.GetNumber() in nets:
        p.SetNet(nets[p.GetNumber()])
for p, n in zip(sorted((p for p in new.Pads() if p.GetNumber() == "MP"), key=lambda p: p.GetPosition().y), mp_nets):
    p.SetNet(n)
new.Reference().SetVisible(False)

t = lambda *a: tuple(P + v for v in a)
B.drop_track(*t(8.45, 7.2), *t(7.45, 6.2))
B.drop_track(*t(7.45, 6.2), *t(1.0, 6.2))
B.drop_track(*t(8.45, 5.2), *t(6.4, 5.2))
B.drop_track(*t(6.4, 5.2), *t(5.95, 4.75))
B.track("VBAT", [t(5.8, 6.825), t(1.625, 6.825), t(1.0, 6.2)], w=0.6)
B.track("/BAT_N", [t(5.8, 5.575), t(5.95, 4.75)], w=0.6)

r = b.FindFootprintByReference("R9")
r.SetValue("2.2kR")
for k, v in (("Description", "Resistor 2.2k 1% 0402"), ("MPN", "0402WGF2201TCE"), ("LCSC", "C25879")):
    r.SetField(k, v)
B.save()
