"""Move the SHT31 (U2) off the top tab onto a moated island inside the rectangular outline.

Run on a KiCad 9 working copy (board coords: origin = KiCad 100,100):
    python3 sht_island.py build/route/work.kicad_pcb
Island x 11.75..15.9, y 1.75..5.65; 1.0 mm moat on top/left/right, wrapping the bottom
corners; bridge x 11.75..14.75 (3.0 wide), y 5.65..7.15 (1.5 long) carries SDA, GND, SCL, +3V3.
"""
import math
import sys
import pcbnew
from rt import R, P, xy, MM

r = R(sys.argv[1])
b = r.b
KEEP = []  # hold SWIG wrappers of removed/created items; letting them be collected corrupts the type table


def rm(x, parent=None):
    (parent or b).Remove(x)
    KEEP.append(x)
CX, CY = 13.15, 3.85            # U2 centre
C11 = (15.25, 4.25)             # rot 90: pad 2 (GND) on top, pad 1 (+3V3) below
ISL = (11.75, 1.75, 15.9, 5.65)  # island x0 y0 x1 y1
BR = (11.75, 14.75)             # bridge x0 x1
MOAT, BRLEN, RAD = 1.0, 1.5, 0.5
OX0, OY0, OX1 = ISL[0] - MOAT, ISL[1] - MOAT, ISL[2] + MOAT
OY1 = ISL[3] + BRLEN


def near(a, c, e=0.02):
    return abs(a[0] - c[0]) < e and abs(a[1] - c[1]) < e


# 3. old tab copper and its feed chains
dead_vias = [(4.0, 0.9), (5.6, 1.4), (5.55, -4.4), (10.6, 0.75), (12.2, 0.75), (13.8, 0.75),
             (15.4, 0.75), (17.0, 0.75), (16.236, 1.9)]
dead_trk = [((4.0, -1.6), (4.0, 0.9)), ((4.75, -2.325), (4.75, 0.55)), ((4.75, 0.55), (6.4, 0.55)),
            ((3.25, -2.325), (3.25, 1.7)), ((3.25, 1.7), (3.95, 2.4)), ((3.95, 2.4), (5.2, 2.4)),
            ((4.95, -2.0), (4.95, 0.8)), ((4.95, 0.8), (5.6, 1.4)), ((15.17, 1.9), (16.236, 1.9)),
            ((24.95, 4.9), (7.45, 4.9))]
trim = {((6.4, 0.55), (6.4, 11.7)): (6.4, 6.7), ((5.2, 2.4), (5.2, 11.7)): (5.2, 6.05)}
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        p = xy(t.GetPosition())
        if p[1] < 0 or any(near(p, q) for q in dead_vias):
            rm(t)
        continue
    s, e = xy(t.GetStart()), xy(t.GetEnd())
    if min(s[1], e[1]) < 0 or any(near(s, a) and near(e, c) or near(s, c) and near(e, a) for a, c in dead_trk):
        rm(t)
        continue
    for (a, c), ns in trim.items():
        if near(s, a) and near(e, c):
            t.SetStart(P(*ns))
        elif near(e, a) and near(s, c):
            t.SetEnd(P(*ns))

# 4. parts
u2 = b.FindFootprintByReference('U2')
u2.SetPosition(P(CX, CY))
c11 = b.FindFootprintByReference('C11')
c11.SetPosition(P(*C11))
c11.SetOrientationDegrees(90)
for g in list(u2.GraphicalItems()):  # left body line would sit on the moat edge
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE' and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        s, e = xy(g.GetStart()), xy(g.GetEnd())
        if abs(s[0] - e[0]) < 0.01 and s[0] < CX - 1:
            rm(g, u2)
u2.Reference().SetPosition(P(17.65, 2.2))

# 5. island and bridge copper (0.15 mm, F.Cu)
pin = lambda n: r.pp('U2', n)
Y1, Y8 = pin(1)[1], pin(8)[1]
x1, x2, x4, x5 = pin(1)[0], pin(2)[0], pin(4)[0], pin(5)[0]
xv = 14.35  # +3V3 riser between U2 and C11
W = 0.15
r.track(['U2.8', 'U2.7'], W)
r.track(['U2.7', (x2, CY - 0.5)], W)
r.track(['U2.2', (x2, CY + 0.5)], W)
r.track(['U2.7', (x2, Y8 - 0.5), (C11[0], Y8 - 0.5), 'C11.2'], W)          # cap GND over the top
r.track(['U2.5', (xv, Y8), (xv, r.pp('C11', 1)[1]), 'C11.1'], W)
r.track([(xv, r.pp('C11', 1)[1]), (xv, 7.6), (14.73, 7.98), (14.73, 9.85)], W, net='+3V3')
r.track(['U2.4', (x4, 8.4)], W)
r.via(x4, 8.4, '/I2C_SCL', d=0.5, drill=0.25)                                 # onto the B.Cu SCL run
r.track(['U2.1', (x1, 7.6), (8.5, 7.6), (6.95, 6.05), (5.2, 6.05)], W)      # to the U5 SDA riser
r.track(['U2.2', (x2, 7.9)], W)                                              # GND into the F pour

# 6. BTN_N (B.Cu) detours under the moat
r.track([(7.45, 4.9), (9.75, 4.9), (10.25, 5.4), (10.25, 7.1), (10.75, 7.6), (17.0, 7.6),
         (17.55, 7.05), (17.55, 5.45), (18.1, 4.9), (24.95, 4.9)], W, layer='B', net='/BTN_N')

# 7. keepout over rim, moat, island and bridge
for z in b.Zones():
    if z.GetZoneName() == 'SHT_TAB_no_pour':
        z.SetZoneName('SHT_island_no_pour')
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for p in [(OX0, 0), (OX1, 0), (OX1, OY1), (OX0, OY1)]:
            o.Append(P(*p))
# 1. outline: drop the tab and neck, close the top edge
for d in list(b.GetDrawings()):
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    s, e = xy(d.GetStart()), xy(d.GetEnd())
    if min(s[1], e[1]) < -0.01 or (abs(s[1]) < 0.01 and abs(e[1]) < 0.01):
        rm(d)


def edge_line(a, c):
    if math.dist(a, c) < 1e-6:
        return
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a))
    s.SetEnd(P(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    b.Add(s)
    KEEP.append(s)


def edge_arc(a, m, c):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(P(*a), P(*m), P(*c))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.05))
    b.Add(s)
    KEEP.append(s)


edge_line((1, 0), (39, 0))

# 2. moat: closed slot outline; corners convex to the slot get the 1 mm cutter radius
V = [((BR[1], OY1), 1), ((OX1, OY1), 1), ((OX1, OY0), 1), ((OX0, OY0), 1), ((OX0, OY1), 1),
     ((ISL[0], OY1), 1), ((ISL[0], ISL[1]), 0), ((ISL[2], ISL[1]), 0), ((ISL[2], ISL[3]), 0),
     ((BR[1], ISL[3]), 1)]
n = len(V)
pts = []  # (enter, mid, exit) per vertex
for i, (p, rnd) in enumerate(V):
    pa, pc = V[i - 1][0], V[(i + 1) % n][0]
    d1 = ((p[0] - pa[0]) / math.dist(p, pa), (p[1] - pa[1]) / math.dist(p, pa))
    d2 = ((pc[0] - p[0]) / math.dist(p, pc), (pc[1] - p[1]) / math.dist(p, pc))
    if not rnd:
        pts.append((p, None, p))
        continue
    t1 = (p[0] - RAD * d1[0], p[1] - RAD * d1[1])
    t2 = (p[0] + RAD * d2[0], p[1] + RAD * d2[1])
    c = (t1[0] + RAD * d2[0], t1[1] + RAD * d2[1])
    k = math.dist(p, c)
    m = (c[0] + RAD * (p[0] - c[0]) / k, c[1] + RAD * (p[1] - c[1]) / k)
    pts.append((t1, m, t2))
for i in range(n):
    t1, m, t2 = pts[i]
    if m:
        edge_arc(t1, m, t2)
    edge_line(t2, pts[(i + 1) % n][0])

r.save()
print('ok')
