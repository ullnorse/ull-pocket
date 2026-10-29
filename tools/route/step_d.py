"""Review round 2 edits on the routed board (KiCad 9 format), in place.

J4 moves to B.Cu in the top-right strip under U1 (above the panel, away from
the J2 plug and lead); programming nets rerouted short. Silk, U6 EP vias,
VBAT, LDO_OUT, LED_USER and small cleanups.
Usage: python3 step_d.py board.kicad_pcb
"""
import sys, math
import pcbnew

fn = sys.argv[1]
b = pcbnew.LoadBoard(fn)
O = 100.0
MM = 1e6


def P(x, y):
    return pcbnew.VECTOR2I(int(round((x + O) * MM)), int(round((y + O) * MM)))


def xy(v):
    return (round(v.x / MM - O, 3), round(v.y / MM - O, 3))


def near(a, b_, tol=0.02):
    return abs(a[0] - b_[0]) < tol and abs(a[1] - b_[1]) < tol


nets = {n: b.FindNet(n) for n in ('GND', '+3V3', 'VBAT', '/EN', '/BOOT', '/TXD0', '/RXD0',
                                  '/LDO_OUT', '/LED_USER', '/I2C_SCL', '/I2C_SDA', '/U6_EP', 'VSYS')}


def track(pts, layer, net, w):
    for (a, c) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(*a)); t.SetEnd(P(*c)); t.SetLayer(layer); t.SetWidth(int(w * MM))
        t.SetNet(nets[net]); b.Add(t)


def via(x, y, net, d=0.6, h=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(x, y)); v.SetWidth(int(d * MM)); v.SetDrill(int(h * MM))
    v.SetNet(nets[net]); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    b.Add(v)
    return v


tracks = list(b.GetTracks())


def remove_if(pred):
    n = 0
    for t in tracks:
        if pred(t):
            b.Remove(t); n += 1
    return n


def seg(t):
    return xy(t.GetStart()), xy(t.GetEnd())


def is_via(t):
    return t.GetClass() == 'PCB_VIA'


# ---- 5. LED_USER lane: extend the In2 GND corridor 0.5 mm south so the lane
# (y 13.05, x 28-31) runs over solid GND instead of the split (PGOOD via blocks a move)
for z in b.Zones():
    if z.GetLayer() == pcbnew.In2_Cu and z.GetNetname() == 'GND' and not z.GetIsRuleArea():
        o = z.Outline()
        for k in range(o.TotalVertices()):
            v = xy(o.CVertex(k))
            if near(v, (33.25, 12.95)):
                o.SetVertex(k, P(33.25, 13.45))
            elif near(v, (21.45, 12.95)):
                o.SetVertex(k, P(20.95, 13.45))

# ---- U6 EP paste windows out to +-0.51 so the 0.45 mm cross vias clear them
fu = b.FindFootprintByReference('U6'); cu = xy(fu.GetPosition())
for p in fu.Pads():
    if p.GetNumber() == '' and not p.IsOnLayer(pcbnew.F_Cu):
        q = xy(p.GetPosition())
        p.SetPosition(P(cu[0] + (-0.51 if q[0] < cu[0] else 0.51), cu[1] + (-0.51 if q[1] < cu[1] else 0.51)))

# ---- 1. J4 to B.Cu, top-right strip -------------------------------------
want = {'1': (31.0, 0.85), '3': (33.54, 0.85), '5': (36.08, 0.85),
        '2': (31.0, 3.39), '4': (33.54, 3.39), '6': (36.08, 3.39)}
j4 = b.FindFootprintByReference('J4')
if j4.GetLayer() != pcbnew.B_Cu:
    j4.Flip(j4.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
ok = False
for ang in (0, 90, 180, 270):
    j4.SetOrientationDegrees(ang)
    pads = {p.GetNumber(): xy(p.GetPosition()) for p in j4.Pads()}
    p1 = pads['1']
    j4.Move(P(want['1'][0] - p1[0] - O + O, want['1'][1] - p1[1]) - P(0, 0))
    pads = {p.GetNumber(): xy(p.GetPosition()) for p in j4.Pads()}
    if all(near(pads[k], want[k], 0.01) for k in want):
        ok = True
        break
assert ok, pads
for p in j4.Pads():
    p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
ref = j4.Reference(); ref.SetLayer(pcbnew.B_Fab); ref.SetVisible(False)
val = j4.Value(); val.SetLayer(pcbnew.B_SilkS); val.SetVisible(True)
val.SetTextAngleDegrees(90); val.SetPosition(P(38.95, 2.12))
val.SetTextSize(pcbnew.VECTOR2I(int(1.0 * MM), int(1.0 * MM))); val.SetTextThickness(int(0.153 * MM))
val.SetMirrored(True)
for it in j4.GraphicalItems():
    if it.GetClass() == 'PCB_TEXT' and it.GetText() == '1':
        it.SetLayer(pcbnew.B_SilkS); it.SetMirrored(True); it.SetTextAngleDegrees(0)
        it.SetPosition(P(29.7, 0.85))
for it in list(j4.GraphicalItems()):
    if it.GetClass() == 'PCB_SHAPE' and it.GetLayer() == pcbnew.B_SilkS:
        j4.Remove(it)
    elif it.GetClass() == 'PCB_SHAPE' and it.GetLayer() == pcbnew.B_CrtYd:
        it.SetStart(P(30.35, 0.2)); it.SetEnd(P(36.73, 4.04))
j4.SetLibDescription('Programming pads, 2x3 grid, 2.54 mm pitch, 1.0 mm round SMD pads (pogo pins only; courtyard is pads + 0.15 mm, no room for a header)')

# old programming routes: keep only the U1-side F stubs and their vias
keep_vias = [(24.7, 5.75), (36.2, 9.55), (36.65, 5.6), (37.45, 4.8)]
n_rm = remove_if(lambda t: t.GetNetname() in ('/EN', '/BOOT', '/TXD0', '/RXD0') and (
    (is_via(t) and not any(near(xy(t.GetStart()), k) for k in keep_vias)) or
    (not is_via(t) and t.GetLayer() == pcbnew.B_Cu) or
    (not is_via(t) and t.GetLayer() == pcbnew.F_Cu and max(seg(t)[0][0], seg(t)[1][0]) < 20.0)))
# GND stitch vias that sit on the new pads/lanes, with their F stubs
gvias = [(36.14, 2.8), (37.4, 2.37), (35.92, 3.8)]
n_rm += remove_if(lambda t: t.GetNetname() == 'GND' and (
    (is_via(t) and any(near(xy(t.GetStart()), k) for k in gvias)) or
    (not is_via(t) and any(near(e, k) for e in seg(t) for k in gvias))))
# old J4 pin-1 feed: F stub and its +3V3 via
n_rm += remove_if(lambda t: t.GetNetname() == '+3V3' and (
    (is_via(t) and near(xy(t.GetStart()), (13.7, 1.9))) or
    (not is_via(t) and any(near(e, (12.63, 1.9)) for e in seg(t)))))
print('removed', n_rm)

W = 0.2
B = pcbnew.B_Cu
track([(37.45, 4.8), (37.45, 1.45), (36.85, 0.85), (36.08, 0.85)], B, '/TXD0', W)
track([(36.65, 5.6), (36.08, 5.03), (36.08, 3.39)], B, '/RXD0', W)
track([(36.2, 9.55), (34.6, 7.95), (34.6, 4.35), (33.54, 3.39)], B, '/BOOT', W)
track([(24.7, 5.75), (32.6, 5.75), (32.6, 1.79), (33.54, 0.85)], B, '/EN', W)
via(31.0, 2.12, '+3V3')
track([(31.0, 2.12), (31.0, 0.85)], B, '+3V3', 0.4)

# ---- 3. U6 EP: four more thermal vias in the paste cross gap -------------
for (x, y) in ((31.0, 33.95), (31.0, 35.05), (30.45, 34.5), (31.55, 34.5)):
    v = via(x, y, 'GND', 0.45, 0.2)
    ep = [p for p in b.FindFootprintByReference('U6').Pads() if p.GetNumber() == '17'][0]
    v.SetNet(ep.GetNet())

# ---- 4. VBAT: wider B trunk, second vias ---------------------------------
# 0.8 mm on the short B legs; the two long runs pass GND vias and SW1's peg hole, so 0.6 mm
for t in tracks:
    if not is_via(t) and t.GetNetname() == 'VBAT' and t.GetLayer() == pcbnew.B_Cu and t.GetWidth() == int(0.5 * MM):
        s_, e_ = seg(t)
        short_j2 = t.GetLength() < 10 * MM and max(s_[0], e_[0]) < 5.0
        t.SetWidth(int((0.8 if short_j2 else 0.6) * MM))
via(2.1, 3.25, 'VBAT', 0.8, 0.4)
track([(2.1, 3.25), (2.1, 3.9)], B, 'VBAT', 0.8)
track([(2.1, 3.25), (2.75, 3.9), (2.75, 5.2)], pcbnew.F_Cu, 'VBAT', 0.6)
via(27.55, 32.35, 'VBAT', 0.6, 0.3)
track([(27.55, 32.35), (27.6, 33.25)], pcbnew.F_Cu, 'VBAT', 0.5)
track([(27.55, 32.35), (27.6, 33.25)], B, 'VBAT', 0.6)

# ---- 6. zero-length segments, U7.2 fold-back -----------------------------
for t in tracks:
    if is_via(t):
        continue
    s, e = seg(t)
    if t.GetLength() < 1000 or (t.GetNetname() == 'GND' and near(s, (35.463, 29.6)) and near(e, (37.495, 29.6))):
        b.Remove(t)

# ---- 7. LDO_OUT: 0.4 mm; the run past U7.4 and C7 is 0.35 mm, nudged to x 38.72
for t in tracks:
    if not is_via(t) and t.GetNetname() == '/LDO_OUT':
        s_, e_ = seg(t)
        if near(s_, (38.675, 28.65)) and near(e_, (38.675, 33.0)) or near(s_, (38.675, 33.0)):
            b.Remove(t)
        elif t.GetWidth() < int(0.4 * MM):
            t.SetWidth(int(0.4 * MM))
track([(38.72, 28.64), (38.72, 33.0)], pcbnew.F_Cu, '/LDO_OUT', 0.35)
track([(38.72, 33.0), (38.4, 33.575)], pcbnew.F_Cu, '/LDO_OUT', 0.4)

# ---- silk ------------------------------------------------------------------
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'PROG' and d.GetLayer() == pcbnew.F_SilkS:
        b.Remove(d)
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in ('PWR', 'CHG', 'USR'):
        d.SetTextSize(pcbnew.VECTOR2I(int(0.75 * MM), int(1.0 * MM)))
for refd, pos in (('TP1', (14.0, 32.75)), ('TP2', (37.8, 32.5)), ('TP3', (10.0, 32.0)),
                  ('TP4', (5.0, 37.96)), ('TP5', (7.5, 34.25))):
    r_ = b.FindFootprintByReference(refd).Reference()
    r_.SetLayer(pcbnew.F_SilkS); r_.SetVisible(True); r_.SetPosition(P(*pos))
    r_.SetTextSize(pcbnew.VECTOR2I(int(1.0 * MM), int(1.0 * MM))); r_.SetTextThickness(int(0.153 * MM))

# ---- SW1 3D model: actuator to the footprint's edge ----------------------
for m in b.FindFootprintByReference('SW1').Models():
    m.m_Offset = pcbnew.VECTOR3D(0, 1, 0)

b.Save(fn)
print('J4 pads', {p.GetNumber(): xy(p.GetPosition()) for p in j4.Pads()})
