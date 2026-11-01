"""rev 0.6 menu buttons (board coords: origin = KiCad 100,100). Edits the board in place with pcbnew.

    python3 tools/route/rev06_buttons.py ull-pocket.kicad_pcb build/ull-pocket.net
    (cd tools/route && python3 silk_place.py ../../ull-pocket.kicad_pcb R30 R31 R3)
    kicad-cli pcb drc --refill-zones --save-board --schematic-parity --severity-all --format json -o /tmp/drc.json ull-pocket.kicad_pcb

Three TS24CA side buttons on the left edge at 7.0 mm pitch, each with the SW1 circuit to its right:
    SW1 UP  y 20.5  IO2  BTN_N   (moved up 1.5 mm)  ext1 wake
    SW2 OK  y 27.5  IO5  BTN2_N  (new)              ext1 wake
    SW3 DN  y 34.5  IO15 BTN3_N  (new, R24 10k strap is its pull-up) polled
LED_USER moves from IO5 to IO14; SPARE_IO14 and TP6 are gone. TP4/TP5 move below the DN group.
IO15 takes over the old IO14 B.Cu run to the TP6 spot; the rest of the feeds and the IO14 LED stub
are routed with the grid router.
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import pcbnew  # noqa: E402
from rt import R, P, xy  # noqa: E402
from gridroute import Grid, route_net  # noqa: E402

FN, NET = sys.argv[1], sys.argv[2]
Y0 = 22.0                      # SW1 template row
ROWS = {'SW1': 20.5, 'SW2': 27.5, 'SW3': 34.5}


def comps(netfile):
    """ref -> (tstamp, fields) from the KiCad netlist."""
    s = open(netfile).read()
    out = {}
    for blk in re.split(r'\(comp\s', s)[1:]:
        ref = re.search(r'\(ref "([^"]+)"', blk).group(1)
        ts = [t for t in re.findall(r'\(tstamps "([^"]+)"', blk) if t != '/'][0]
        flds = dict(re.findall(r'\(name "([^"]+)"\) "([^"]*)"', blk))
        flds['Value'] = re.search(r'\(value "([^"]*)"', blk).group(1)
        flds['Description'] = (re.search(r'\(description "([^"]*)"', blk) or [None, ''])[1]
        out[ref] = (ts, flds)
    return out


C = comps(NET)
r = R(FN)
b = r.b
KEEP = []


def rnd(p):
    return (round(p[0], 3), round(p[1], 3))


def near(a, c, e=0.02):
    return abs(a[0] - c[0]) < e and abs(a[1] - c[1]) < e


def rm(x):
    b.Remove(x)
    KEEP.append(x)


def netitem(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        KEEP.append(n)
    return n


def ends(t):
    return rnd(xy(t.GetStart())), rnd(xy(t.GetEnd()))


def in_box(p, x0, y0, x1, y1):
    return x0 <= p[0] <= x1 and y0 <= p[1] <= y1


# ---------------------------------------------------------------- 1. net changes at the MCU
u1 = b.FindFootprintByReference('U1')
for p in u1.Pads():
    n = {'10': '/BTN2_N', '19': '/LED_USER', '20': '/BTN3_N'}.get(p.GetNumber())
    if n:
        p.SetNet(netitem(n))
for p in b.FindFootprintByReference('R24').Pads():
    if p.GetNetname() == 'Net-(U1-IO15)':
        p.SetNet(netitem('/BTN3_N'))
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if n == 'Net-(U1-IO15)':
        t.SetNet(netitem('/BTN3_N'))
    elif n == '/SPARE_IO14':
        # the old IO14 -> TP6 run becomes the IO15 (BTN3_N) feed; drop its IO14 and TP6 stubs
        if t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.F_Cu:
            rm(t)
        else:
            t.SetNet(netitem('/BTN3_N'))
    elif n == '/LED_USER':
        if t.GetClass() == 'PCB_VIA':
            if near(xy(t.GetPosition()), (27.6, 13.45)):
                rm(t)
        else:
            a, z = ends(t)
            if t.GetLayer() == pcbnew.F_Cu and max(a[1], z[1]) < 14:   # IO5 stub
                rm(t)
            elif t.GetLayer() == pcbnew.B_Cu and a[1] == z[1] == 13.05 or {a, z} == {(27.6, 13.45), (28.0, 13.05)}:
                rm(t)
tp6 = b.FindFootprintByReference('TP6')
rm(tp6)
r.track(['U1.20', (34.2, 10.0), (33.55, 9.55), (33.0, 9.55)], 0.15, net='/BTN3_N')   # IO15 -> old IO14 via

# ---------------------------------------------------------------- 2. button groups
# SW1 becomes a fresh library instance (the board copy had drifted from the library), then gets cloned
LIBDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'lib', 'ull-pocket.pretty')
old = b.FindFootprintByReference('SW1')
new = pcbnew.FootprintLoad(LIBDIR, 'SW-SMD_2P-TS24CA')
new.SetFPIDAsString('ull-pocket:SW-SMD_2P-TS24CA')
b.Add(new)
KEEP.append(new)
new.SetPosition(old.GetPosition())
new.SetOrientation(old.GetOrientation())
for fld in old.GetFields():
    if fld.GetName() not in ('Reference', 'Value', 'Footprint'):
        new.SetField(fld.GetName(), fld.GetText())
        nf = new.GetField(fld.GetName())
        nf.SetVisible(fld.IsVisible())
        nf.SetLayer(fld.GetLayer())
        nf.SetPosition(new.GetPosition())
new.SetReference('SW1')
new.SetValue(old.GetValue())
new.SetPath(old.GetPath())
new.Reference().SetLayer(pcbnew.F_Fab)
new.Reference().SetVisible(False)
nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
for p in new.Pads():
    p.SetNet(nets[p.GetNumber()])
rm(old)

TEMPLATE = ['SW1', 'R14', 'R28', 'C27']
GROUP_BOX = (0.5, 18.5, 7.9, 25.2)            # SW1 group copper (tracks/vias) around Y0, excl. the feed
grp_tracks = []
for t in b.GetTracks():
    nm = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        p = rnd(xy(t.GetPosition()))
        if in_box(p, *GROUP_BOX) and (nm in ('/BTN_N', '/BTN_SW', '+3V3') or
                                       (nm == 'GND' and p in ((2.015, 18.715), (2.553, 24.792), (3.393, 21.237)))):
            grp_tracks.append(t)
    else:
        a, z = ends(t)
        if in_box(a, *GROUP_BOX) and in_box(z, *GROUP_BOX) and nm in ('/BTN_N', '/BTN_SW', 'GND', '+3V3'):
            if nm == 'GND' and not ({a, z} & {(3.22, 20.3), (1.28, 19.88), (1.28, 24.12)}):
                continue
            if {a, z} == {(4.3, 21.3), (4.05, 21.05)}:
                continue                         # SW1 feed bend, shifted separately
            grp_tracks.append(t)
assert len(grp_tracks) == 17, len(grp_tracks)

# GND stitching vias (unlocked, on the 2.4 mm grid) that the new groups / test pads displace
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and not t.IsLocked() and t not in grp_tracks:
        if rnd(xy(t.GetPosition())) in ((4.4, 23.6), (4.4, 26.0), (6.8, 26.0), (2.0, 26.0), (4.4, 28.4), (2.0, 28.4),
                                        (6.8, 28.4), (6.8, 30.8), (6.8, 21.2), (4.4, 30.8), (2.0, 33.2), (6.8, 33.2), (2.0, 35.6),
                                        (4.4, 38.0), (6.8, 38.0), (9.2, 38.0), (2.0, 38.0), (6.8, 40.4), (9.2, 40.4)):
            rm(t)


def clone_fp(src, ref, dy, rot=None):
    s = b.FindFootprintByReference(src)
    f = s.Duplicate(False)
    f = f.Cast() if not isinstance(f, pcbnew.FOOTPRINT) else f
    b.Add(f)
    KEEP.append(f)
    ts, flds = C[ref]
    f.SetReference(ref)
    f.SetValue(flds['Value'])
    f.SetPath(pcbnew.KIID_PATH('/' + ts))
    for k in ('MPN', 'LCSC', 'Manufacturer', 'Description'):
        if k in flds:
            f.SetField(k, flds[k])
    f.Move(P(0, dy) - P(0, 0))
    return f


def clone_track(t, dy, netmap):
    n = netitem(netmap.get(t.GetNetname(), t.GetNetname()))
    if t.GetClass() == 'PCB_VIA':
        c = pcbnew.PCB_VIA(b)
        c.SetPosition(t.GetPosition())
        c.SetWidth(t.GetWidth(pcbnew.F_Cu))
        c.SetDrill(t.GetDrillValue())
        c.SetViaType(pcbnew.VIATYPE_THROUGH)
    else:
        c = pcbnew.PCB_TRACK(b)
        c.SetStart(t.GetStart())
        c.SetEnd(t.GetEnd())
        c.SetWidth(t.GetWidth())
        c.SetLayer(t.GetLayer())
    c.Move(P(0, dy) - P(0, 0))
    c.SetNet(n)
    b.Add(c)
    KEEP.append(c)
    return c


# new groups first (cloned from the SW1 group at Y0), then move SW1 itself
for sw, rp, rs, cc, net, swn in (('SW2', 'R29', 'R30', 'C28', '/BTN2_N', '/BTN2_SW'),
                                 ('SW3', None, 'R31', 'C29', '/BTN3_N', '/BTN3_SW')):
    dy = ROWS[sw] - Y0
    nm = {'/BTN_N': net, '/BTN_SW': swn}
    for src, ref in zip(TEMPLATE, (sw, rp, rs, cc)):
        if ref is None:
            continue
        f = clone_fp(src, ref, dy)
        for p in f.Pads():
            p.SetNet(netitem(nm.get(p.GetNetname(), p.GetNetname())))
    for t in grp_tracks:
        if sw == 'SW3' and t.GetNetname() == 'GND' and (
                (t.GetClass() == 'PCB_VIA' and near(xy(t.GetPosition()), (2.015, 18.715))) or
                (t.GetClass() != 'PCB_VIA' and (1.28, 19.88) in ends(t))):
            continue     # SW3 tab-3 via would sit on the VBAT B.Cu diagonal; the tab joins the F pour
        if rp is None:   # no pull-up: skip the R14 pad tie and the +3V3 via
            if t.GetNetname() == '+3V3':
                continue
            if t.GetClass() != 'PCB_VIA' and set(ends(t)) == {(5.55, 21.5), (4.5, 21.49)}:
                continue
        clone_track(t, dy, nm)

dy = ROWS['SW1'] - Y0
for ref in TEMPLATE:
    b.FindFootprintByReference(ref).Move(P(0, dy) - P(0, 0))
for t in grp_tracks:
    if t.GetClass() == 'PCB_VIA' and near(xy(t.GetPosition()), (2.015, 18.715)):
        rm(t)            # would land on the VBAT B.Cu run at y 17.6; the tab joins the F pour instead
        continue
    if t.GetClass() != 'PCB_VIA' and (1.28, 19.88) in ends(t):
        rm(t)
        continue
    t.Move(P(0, dy) - P(0, 0))
r.via(2.3, 18.45, 'GND')
r.track(['SW1.3', (2.3, 18.45)], 0.3, net='GND')
for t in b.GetTracks():
    if t.GetNetname() == '/BTN_N' and t.GetClass() != 'PCB_VIA':
        a, z = ends(t)
        if {a, z} == {(4.3, 21.3), (4.05, 21.05)}:
            t.SetStart(P(4.3, 21.3 + dy))
            t.SetEnd(P(4.05, 21.05 + dy))
        elif {a, z} == {(4.05, 16.9), (4.05, 21.05)}:
            (t.SetEnd if near(z, (4.05, 21.05)) else t.SetStart)(P(4.05, 21.05 + dy))

# ---------------------------------------------------------------- 3. TP4 (VBAT) / TP5 (+3V3) below the DN group
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        if rnd(xy(t.GetPosition())) in ((5.0, 32.4), (8.67, 36.1)):
            rm(t)
    elif set(ends(t)) in ({(5.0, 32.4), (5.0, 36.1)}, {(7.5, 36.1), (8.67, 36.1)}):
        rm(t)
TPPOS = {'TP4': (9.3, 39.3), 'TP5': (9.3, 42.6)}
for ref, (x, y) in TPPOS.items():
    f = b.FindFootprintByReference(ref)
    f.SetPosition(P(x, y))
    for t in f.GraphicalItems():       # "TPn\nNET" label, two lines, left of the pad
        if t.GetClass() == 'PCB_TEXT' and t.GetLayer() == pcbnew.F_SilkS:
            t.SetText(t.GetText().replace(' ', '\n', 1))
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
            t.SetTextAngleDegrees(0)
            t.SetPosition(P(x - 0.95, y))
r.track([(10.4, 32.4), (10.4, 39.3)], 0.4, layer='B', net='VBAT')
r.via(10.4, 39.3, 'VBAT')
r.track([(10.4, 39.3), 'TP4.1'], 0.4, net='VBAT')
r.via(9.3, 40.95, '+3V3')
r.track([(9.3, 40.95), 'TP5.1'], 0.3, net='+3V3')
for t in b.GetFootprints():
    if t.GetReference() == 'J1':                    # "J1 USB-C" label: two lines, left of the receptacle
        for x in t.GraphicalItems():
            if x.GetClass() == 'PCB_TEXT' and 'USB-C' in x.GetText():
                x.SetText('${REFERENCE}\nUSB-C')
                x.SetPosition(P(12.6, 41.3))
                x.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
                x.SetTextThickness(pcbnew.FromMM(0.12))

# button labels: board texts "UP" / "OK" / "DN" (0.8 mm) in the gap below each switch. The old
# "${REFERENCE} WAKE" footprint text goes, so the switches match the library footprint again.
for sw, lbl in (('SW1', 'UP'), ('SW2', 'OK'), ('SW3', 'DN')):
    f = b.FindFootprintByReference(sw)
    for t in list(f.GraphicalItems()):
        if t.GetClass() == 'PCB_TEXT' and 'WAKE' in t.GetText():
            f.Remove(t)
    t = pcbnew.PCB_TEXT(b)
    t.SetText(lbl)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
    t.SetTextThickness(pcbnew.FromMM(0.12))
    t.SetPosition(P(2.2, ROWS[sw] + 3.5))
    b.Add(t)
    KEEP.append(t)

c1r = b.FindFootprintByReference('C1').Reference()   # its old spot is taken by the TP4 label
c1r.SetLayer(pcbnew.F_SilkS)
c1r.SetVisible(True)
c1r.SetTextAngleDegrees(0)
c1r.SetPosition(P(13.4, 38.95))

# revision r0.6: F silk rev text, B silk title line, title block
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'r0.5':
        d.SetText('r0.6')
        d.SetPosition(P(11.8, 43.6))
    elif d.GetClass() == 'PCB_TEXT' and d.GetText().startswith('rev 0.5'):
        d.SetText('rev 0.6  2026-11')
tb = b.GetTitleBlock()
tb.SetRevision('0.6')
tb.SetDate('2026-11-01')

# JLC order-number text sat where the OK group goes
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText().startswith('JLC'):
        d.SetPosition(P(11.0, 24.3))
        d.SetTextAngleDegrees(90)

r.save()

# ---------------------------------------------------------------- 4. feeds (grid router)
r = R(FN)
b = r.b
grid = Grid(r, [])
for net in ('/LED_USER', '/BTN3_N', '/BTN2_N'):
    ok = route_net(r, grid, net, w=0.15, clr=0.2, via=(0.6, 0.3), via_cost=30)
    print(net, 'ok' if ok else 'FAIL')
# cleanup: the old TP6 via is now a B.Cu-only joint; the old IO5 LED run above y 28.2 is dead
for t in list(b.GetTracks()):
    n = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        if n == '/BTN3_N' and near(xy(t.GetPosition()), (18.5, 12.35)):
            rm(t)
    elif n == '/LED_USER' and t.GetLayer() == pcbnew.B_Cu:
        a, z = ends(t)
        if {a, z} == {(31.0, 13.05), (31.0, 28.2)}:
            rm(t)
        elif {a, z} == {(31.0, 28.2), (34.0, 28.2)}:
            (t.SetStart if a == (31.0, 28.2) else t.SetEnd)(P(32.6, 28.2))
r.save()
print('saved', FN)
