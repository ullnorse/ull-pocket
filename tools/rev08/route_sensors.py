"""Rev 0.8 sensor cluster: place SHT40/C11 in the island, BMP580 (rot 270), LIS2DW12 (rot 0) and route them.
Run after sync_pcb.py and ripup.py."""
import pcbnew
from pcbnew import FromMM as I, ToMM as mm

b = pcbnew.LoadBoard("ull-pocket.kicad_pcb")
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def fp(ref, x, y, rot):
    f = b.FindFootprintByReference(ref)
    f.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))
    f.SetOrientationDegrees(rot)


def track(net, pts, w=0.15, layer=F):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(I(x1), I(y1)))
        t.SetEnd(pcbnew.VECTOR2I(I(x2), I(y2)))
        t.SetWidth(I(w))
        t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)


def via(net, x, y, d=0.6, h=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))
    v.SetWidth(I(d))
    v.SetDrill(I(h))
    v.SetNet(b.FindNet(net))
    b.Add(v)


def near(p, x, y):
    return abs(mm(p.x) - x) < 0.01 and abs(mm(p.y) - y) < 0.01


def drop_track(x1, y1, x2, y2):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() != "PCB_VIA" and ((near(t.GetStart(), x1, y1) and near(t.GetEnd(), x2, y2)) or
                                          (near(t.GetStart(), x2, y2) and near(t.GetEnd(), x1, y1))):
            b.Delete(t)
            n += 1
    assert n, ("no track", x1, y1, x2, y2)


def drop_via(x, y):
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" and near(t.GetPosition(), x, y):
            b.Delete(t)
            return
    raise AssertionError(("no via", x, y))


for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName() == "BMP585_window":
        b.Delete(z)

# ---- U2 SHT40 + C11 in the moated island; four 0.15 tracks over the bridge:
# GND x112.2 (into the F.Cu pour left of SDA), SDA x112.75, SCL x113.55, +3V3 x114.35
fp("U2", 113.15, 104.2, 90)      # pads: 1 SDA (112.75,104.9) 2 SCL (113.55,104.9) 3 VDD (113.55,103.5) 4 GND (112.75,103.5)
fp("C11", 113.15, 102.5, 180)    # pad 2 GND (112.67,102.5), pad 1 +3V3 (113.63,102.5)
drop_track(115.25, 102.893, 115.25, 103.77)   # old C11 GND stub
drop_track(112.4, 107.021, 111.821, 107.6)
drop_track(111.82, 107.6, 111.1, 108.32)
track("GND", [(112.75, 103.5), (112.75, 102.5)])
track("+3V3", [(113.55, 103.5), (113.55, 102.5)])
track("GND", [(112.67, 102.5), (112.2, 102.5), (112.2, 107.75)])
track("+3V3", [(113.63, 102.5), (114.35, 102.5), (114.35, 107.6)])
track("/I2C_SDA", [(112.75, 104.9), (112.75, 107.95), (112.38, 108.32), (111.1, 108.32)])
track("/I2C_SCL", [(113.55, 104.9), (113.55, 108.05), (113.9, 108.4)])

# ---- U3 BMP580, rot 270: 1 +3V3 (113.75,111.24) 2 SCL (113.25,111.24) 3 GND (112.74,111.5) 4 SDA (112.74,112.0)
# 5 GND (112.74,112.5) 6 CSB (113.25,112.76) 7 INT (113.75,112.76) 8 GND (114.26,112.5) 9 GND (114.26,112.0) 10 VDD (114.26,111.5)
fp("U3", 113.5, 112.0, 270)
drop_track(113.5, 110.264, 113.914, 109.85)
drop_track(115.25, 112.0, 115.85, 112.48)
X0, X1, Y0, Y1 = 112.7375, 114.2625, 111.2375, 112.7625
track("+3V3", [(113.75, Y0), (113.75, 110.014), (113.914, 109.85)], 0.2)          # VDDIO to the 3V3 run
track("/I2C_SCL", [(113.25, Y0), (113.25, 110.9), (111.0, 110.9)])                # to the SCL via
track("/I2C_SDA", [(X0, 112.0), (111.5, 112.0)])                                  # joins the old run to the SDA via
track("+3V3", [(X1, 111.5), (115.85, 111.5)], 0.2)                                # VDD to C12
track("GND", [(X1, 112.0), (X1, 112.5), (115.85, 112.5)], 0.2)                    # pads 8/9 to C12
track("+3V3", [(113.25, Y1), (113.25, 114.12), (113.5, 114.37)], 0.2)             # CSB to C13
track("/BARO_INT", [(113.75, Y1), (113.75, 113.35), (115.9, 113.35)])             # to the INT via
track("GND", [(X0, 112.5), (112.3, 112.94)])                                      # pad 5 to a GND via
via("GND", 112.3, 113.2, 0.45, 0.2)
track("GND", [(112.3, 112.94), (112.3, 113.2)])
track("GND", [(X0, 111.5), (111.95, 111.5)])                                      # pad 3 into the pour

# ---- U4 LIS2DW12, rot 0: 1 SCL (119.24,105.75) 2 CS 3 SA0 (left, +3V3) 4 SDA (119.24,107.25) 5 NC 6 GND (bottom)
# 7 GND 8 GND 9 VDD 10 VDDIO (right) 11 INT2 12 INT1 (top)
fp("U4", 120.0, 106.5, 0)
L, R, T, Bt = 119.2375, 120.7625, 105.7375, 107.2625
drop_track(121.9, 105.5, 121.9, 106.196)
drop_track(122.2, 105.2, 121.9, 105.5)
drop_track(118.705, 104.6, 120.49, 104.6)
drop_track(120.6, 108.4, 120.6, 109.49)
for x, y in ((121.38, 104.324), (117.541, 104.337), (118.775, 108.245)):
    drop_via(x, y)
track("/ACC_INT1", [(119.75, T), (119.75, 105.2), (122.2, 105.2)])
track("+3V3", [(R, 105.75), (R, 106.25)], 0.2)
track("+3V3", [(R, 106.0), (121.5, 106.0)], 0.2)
via("+3V3", 121.5, 106.0)
track("+3V3", [(L, 106.25), (L, 106.75)], 0.2)
track("+3V3", [(L, 106.5), (118.6, 106.5)], 0.2)
via("+3V3", 118.6, 106.5)
track("/I2C_SCL", [(L, 105.75), (118.15, 105.75), (117.9, 106.0), (117.9, 107.8), (117.3, 108.4)])
track("/I2C_SDA", [(L, 107.25), (L, 109.1375), (119.55, 109.45)])
track("GND", [(120.25, Bt), (R, Bt), (R, 106.75)], 0.2)
track("GND", [(R, 107.0), (122.6, 107.0)], 0.2)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.Save("ull-pocket.kicad_pcb")
print("ok")
