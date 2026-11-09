"""Rev 0.9 board edits (run once on the rev 0.8 board, after tools/rev09/apply_sch.py and a netlist export).

- Sync footprints and pad nets from build/ull-pocket.net (C3/C4 to 0805, new R35, U8 pin 5 on +3V3).
  Unlike tools/rev08/sync_pcb.py, tracks are never renamed: U8.5 leaving VBUS must not drag the VBUS tracks along.
- VBUS: J1 -> U6 IN moves off In2 (0.5 oz) to B.Cu (1 oz) at 0.5 mm, round the south end of the USB_PGOOD_N
  B.Cu run, up to an 0.8/0.4 via next to U6 pin 13 (it also feeds R4); the C2-to-pin-13 stub widens to 0.5 mm.
- U8 pin 5 to a +3V3 via (In2 plane).
- C3/C4 at 0805 nudged out of U6's courtyard.
- R35 BARO_INT pull-up next to the BARO_INT via, plus a GND via for the pour island it closes off.
- Two more GND vias under U7, either side of the pin-2 via.
- CHG_DIS: IO15 (was LED_G) drives U6 /CE (pin 4, was GND). The old LED_G run is reused from U1 down to y 115,
  hops over LED_B on F.Cu, runs down the B.Cu channel between USB_PGOOD_N and LED_B into the VBUS loop and comes up
  at pin 4. R36 100k pull-down sits under pin 4. R33 and the D6 green tracks go; D6 pad 3 is left unconnected.
- J2 polarity marks at the connector mouth; back-silk texts under the display glass removed.
"""
import os
import sys
import pcbnew
from pcbnew import FromMM as I, ToMM as mm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "rev08"))
from sexp import find, findall, parse  # noqa: E402
from route_sensors_lib import Board  # noqa: E402

PCB = os.path.join(ROOT, "ull-pocket.kicad_pcb")
B = Board(PCB)
b = B.b

# ---------------------------------------------------------------- netlist sync (no track renames)
net = parse(open(os.path.join(ROOT, "build/ull-pocket.net")).read())
pin_net = {}
for n in findall(find(net, "nets"), "net"):
    for node in findall(n, "node"):
        pin_net[(str(find(node, "ref")[1]), str(find(node, "pin")[1]))] = str(find(n, "name")[1])


def netinfo(name):
    ni = b.FindNet(name)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
    return ni


def load(fpid):
    lib, name = fpid.split(":")
    d = os.path.join(ROOT, "lib/ull-pocket.pretty") if lib == "ull-pocket" else "/usr/share/kicad/footprints/%s.pretty" % lib
    f = pcbnew.FootprintLoad(d, name)
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    return f


template = b.FindFootprintByReference("R25")
for c in findall(find(net, "components"), "comp"):
    ref = str(find(c, "ref")[1])
    fpid = str(find(c, "footprint")[1])
    fields = {str(find(f, "name")[1]): str(f[2]) for f in findall(find(c, "fields") or [], "field") if len(f) > 2}
    old = b.FindFootprintByReference(ref)
    if old is not None and old.GetFPIDAsString() == fpid:
        fp = old
    else:
        fp = load(fpid)
        b.Add(fp)
        fp.SetReference(ref)
        if old is not None:
            fp.SetPosition(old.GetPosition())
            fp.SetOrientation(old.GetOrientation())
            fp.Reference().SetVisible(old.Reference().IsVisible())
            fp.Reference().SetLayer(old.Reference().GetLayer())
            b.Delete(old)
        else:
            fp.Reference().SetVisible(False)   # resistor/capacitor refs are hidden (docs/best-practices.md 4)
        fp.SetSheetname(template.GetSheetname())
        fp.SetSheetfile(template.GetSheetfile())
        print("swapped" if old else "added", ref, fpid)
    fp.SetValue(str(find(c, "value")[1]))
    fp.SetPath(pcbnew.KIID_PATH("/" + str(find(c, "tstamps")[1])))
    for k, v in fields.items():
        if k == "Footprint":
            continue
        if k == "Datasheet":
            fp.GetField(pcbnew.FIELD_T_DATASHEET).SetText(v)
        elif k == "Description":
            fp.GetField(pcbnew.FIELD_T_DESCRIPTION).SetText(v)
        elif fp.HasField(k):
            fp.GetField(k).SetText(v)
        else:
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
            f.SetText(v)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            fp.Add(f)
    for p in fp.Pads():
        n = pin_net.get((ref, p.GetNumber()))
        cur = p.GetNetname()
        if cur == (n or "") or (cur.startswith("unconnected-") and (n or "").startswith("unconnected-")):
            continue    # unchanged; J2's two MP pads keep their separate no-connect nets
        print("  %s.%s: %s -> %s" % (ref, p.GetNumber(), cur, n))
        p.SetNet(netinfo(n) if n else b.FindNet(""))

# ---------------------------------------------------------------- C3/C4 0805: clear of U6's courtyard
B.fp("C3", 134.95, 134.5, 0)
B.fp("C4", 127.0, 134.5, 180)
B.drop_via(128.4, 135.6)            # GND stitching via under the new C4 pad 1; pin 4 has its own via
# C16's +3V3 via moves right, away from the wider C3 pad 2
B.drop_track(138.4, 135.225, 136.6, 135.2)
B.drop_track(136.6, 135.2, 136.6, 136.225)
B.drop_via(136.6, 135.2)
B.via("+3V3", 136.95, 135.2)
B.track("+3V3", [(138.4, 135.225), (136.95, 135.2), (136.6, 136.225)], w=0.5)
u6ref = b.FindFootprintByReference("U6").Reference()     # clear of C4's silk
u6ref.SetPosition(pcbnew.VECTOR2I(u6ref.GetPosition().x, u6ref.GetPosition().y + I(0.25)))

# ---------------------------------------------------------------- U8 pin 5 -> +3V3
B.drop_track(120.0, 134.5375, 120.0, 135.75)
B.drop_via(120.0, 135.75)
B.drop_track(116.6, 135.4, 120.0, 135.75)
B.drop_track(120.0, 135.75, 123.4, 135.4)
B.track("VBUS", [(116.6, 135.4), (123.4, 135.4)], w=0.5, layer=pcbnew.B_Cu)
B.track("+3V3", [(120.0, 134.5375), (120.0, 136.15)], w=0.3)
B.via("+3V3", 120.0, 136.15, d=0.6, h=0.3)

# ---------------------------------------------------------------- VBUS off In2
for seg in [((123.4, 135.4), (124.6, 134.2)), ((124.6, 134.2), (124.6, 132.2)), ((124.6, 132.2), (125.3, 131.55)),
            ((125.3, 131.55), (130.7, 131.55)), ((130.5, 131.55), (130.9, 131.55)), ((130.9, 131.55), (132.4, 133.05)),
            ((132.4, 133.05), (132.4, 137.4))]:
    B.drop_track(*seg[0], *seg[1])
B.drop_via(132.25, 132.9)
B.via("VBUS", 132.25, 132.9, d=0.8, h=0.4)
# GND stitching vias in the way: move two, drop R5's (its pad sits in the F.Cu GND pour)
B.drop_via(126.0, 138.0)
B.via("GND", 126.3, 138.0)
B.drop_via(128.4, 140.4)
B.via("GND", 127.9, 141.0)
B.drop_via(132.4, 138.75)
B.drop_track(131.51, 138.5, 132.4, 138.75)
B.track("VBUS", [(123.4, 135.4), (125.3, 135.4), (125.3, 139.2), (127.7, 139.2), (128.6, 140.1), (132.3, 140.1),
                 (132.3, 133.1), (132.25, 132.9)], w=0.5, layer=pcbnew.B_Cu)
# C2 -> pin 13 stub: 0.5 mm down to where pin 14 / TMR clearance allows, 0.3 into the 0.25 mm pad
B.drop_track(131.75, 131.625, 131.75, 133.0375)
B.track("VBUS", [(131.75, 131.625), (131.75, 132.2)], w=0.5)
B.track("VBUS", [(131.75, 132.2), (131.75, 133.0375)], w=0.3)

# ---------------------------------------------------------------- R35 BARO_INT pull-up
B.fp("R35", 117.6, 112.2, 270)
r35 = b.FindFootprintByReference("R35")
p1, p2 = (r35.FindPadByNumber(n).GetPosition() for n in ("1", "2"))
assert mm(p1.y) < mm(p2.y) and r35.FindPadByNumber("1").GetNetname() == "+3V3"
B.track("+3V3", [(mm(p1.x), mm(p1.y)), (116.73, 111.52)], w=0.2)
B.track("/BARO_INT", [(mm(p2.x), mm(p2.y)), (116.95, 113.35), (115.9, 113.35)], w=0.15)
B.via("GND", 115.0, 112.45)          # R35's tracks close off the U3/C12 GND pour island; stitch it down

# ---------------------------------------------------------------- U7 thermal vias
for y in (128.9, 130.3):
    B.via("GND", 136.6, y, d=0.45, h=0.2)
    B.track("GND", [(136.6, 129.6), (136.6, y)], w=0.3)

# ---------------------------------------------------------------- CHG_DIS: IO15 -> U6 /CE
b.Remove(b.FindFootprintByReference("R33"))
for seg in [((133.15, 142.31), (133.15, 142.9)), ((133.15, 142.9), (133.45, 143.2)), ((133.45, 143.2), (133.45, 143.5)),
            ((134.45, 140.95), (133.15, 140.95)), ((133.15, 140.95), (133.15, 141.29)), ((134.45, 112.85), (134.45, 140.95))]:
    B.drop_track(*seg[0], *seg[1])
B.drop_via(134.45, 140.95)
chg = netinfo("/CHG_DIS")
for t in b.GetTracks():
    if t.GetNetname() == "/LED_G":     # U1 pin 20 to its via and the B.Cu jog: kept, renamed
        t.SetNet(chg)
assert b.FindNet("/LED_G") is None or not [t for t in b.GetTracks() if t.GetNetname() == "/LED_G"]
B.track("/CHG_DIS", [(134.45, 112.85), (134.45, 114.35), (133.6, 115.2)], layer=pcbnew.B_Cu)
B.via("/CHG_DIS", 133.6, 115.2, d=0.45, h=0.2)
B.track("/CHG_DIS", [(133.6, 115.2), (131.6, 115.2)])                     # F.Cu over LED_B
B.via("/CHG_DIS", 131.6, 115.2, d=0.45, h=0.2)
B.track("/CHG_DIS", [(131.6, 115.2), (131.6, 126.6), (130.99, 127.21), (130.99, 131.6), (129.6, 132.99), (129.6, 135.95)],
        layer=pcbnew.B_Cu)
# pin 4 leaves GND: its EP link and GND via go, a CHG_DIS via takes the via's place
B.drop_track(129.537, 135.25, 130.4, 135.25)
B.drop_track(129.537, 135.25, 129.537, 135.945)
B.drop_via(129.5375, 135.945)
B.via("/CHG_DIS", 129.6, 135.95, d=0.45, h=0.2)
B.track("/CHG_DIS", [(129.537, 135.25), (129.6, 135.95)], w=0.2)
B.fp("R36", 129.55, 137.7, 270)
r36 = b.FindFootprintByReference("R36")
q1, q2 = (r36.FindPadByNumber(n).GetPosition() for n in ("1", "2"))
assert mm(q1.y) < mm(q2.y) and r36.FindPadByNumber("1").GetNetname() == "/CHG_DIS"
B.track("/CHG_DIS", [(mm(q1.x), mm(q1.y)), (129.6, 135.95)], w=0.2)
# pad 2 (GND) joins the F.Cu GND pour, as R5 pad 2 next to it does

# ---------------------------------------------------------------- silk
for d in list(b.GetDrawings()):
    if d.GetClass() != "PCB_TEXT":
        continue
    if d.GetLayer() == pcbnew.B_SilkS and d.GetText() in ("ULL-POCKET", "ESP32-C6 pocket environment meter", "LiPo 3.7 V 1S", "mind polarity"):
        b.Remove(d)
    elif d.GetLayer() == pcbnew.F_SilkS and d.GetText() == "-":    # J2 pin 1 (BAT-), upper pin
        d.SetPosition(pcbnew.VECTOR2I(I(100.9), I(103.3)))
    elif d.GetLayer() == pcbnew.F_SilkS and d.GetText() == "+":    # J2 pin 2 (BAT+), lower pin
        d.SetPosition(pcbnew.VECTOR2I(I(100.9), I(109.1)))

B.save()
