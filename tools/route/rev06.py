"""rev 0.6 schematic-review changes on the KiCad 9 working copy (board coords: origin = KiCad 100,100).

    python3 rev06.py build/route/work.kicad_pcb
    python3 silk_place.py build/route/work.kicad_pcb R27 R28 C27

1. R3 1M -> 0R (0402, C17168): USB shield straight to GND; C1 4.7 nF becomes DNP (footprint kept).
2. J4.1 becomes VREF: R27 1k from +3V3 on F at (20.4, 2.7), via + B.Cu run along the top edge to the pad.
3. SW1: R28 100R in series (switch side = BTN_SW) and C27 100 nF BTN_N to GND, both just right of SW1.
"""
import sys
import pcbnew
from rt import R, P, xy, MM

r = R(sys.argv[1])
b = r.b
KEEP = []


def rm(x):
    b.Remove(x)
    KEEP.append(x)


def near(a, c, e=0.02):
    return abs(a[0] - c[0]) < e and abs(a[1] - c[1]) < e


def netitem(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        KEEP.append(n)
    return n


def clone(src_ref, ref, value, path, fields, pos, rot, nets):
    src = b.FindFootprintByReference(src_ref)
    f = src.Duplicate()   # fresh UUIDs for the footprint and its children (the copy constructor keeps them)
    f = f.Cast() if not isinstance(f, pcbnew.FOOTPRINT) else f
    b.Add(f)
    KEEP.append(f)
    f.SetReference(ref)
    f.SetValue(value)
    f.SetPath(pcbnew.KIID_PATH('/' + path))
    for k, v in fields.items():
        f.SetField(k, v)
    f.SetPosition(P(*pos))
    f.SetOrientationDegrees(rot)
    for p in f.Pads():
        p.SetNet(netitem(nets[p.GetNumber()]))
    return f


TRACKS = list(b.GetTracks())

# 1. shield
r3 = b.FindFootprintByReference('R3')
r3.SetValue('0R')
for k, v in (('MPN', '0402WGF0000TCE'), ('LCSC', 'C17168'), ('Description', 'Resistor 0R 0402 (USB shield to GND)')):
    r3.SetField(k, v)
c1 = b.FindFootprintByReference('C1')
c1.SetDNP(True)
c1.SetExcludedFromBOM(True)
c1.SetExcludedFromPosFiles(True)

# 2. J4.1 -> VREF through R27 1k
VREF, V3, GND = '/VREF', '+3V3', 'GND'
j4 = b.FindFootprintByReference('J4')
j4.SetField('Description', 'Programming pads: 2x3 grid, 2.54 mm pitch, 1.0 mm round SMD pads; pad 1 VREF is sense-only (1k from +3V3)')
for p in j4.Pads():
    if p.GetNumber() == '1':
        p.SetNet(netitem(VREF))
for t in TRACKS:  # old +3V3 feed of pad 1: via under U1 and its B.Cu stub
    if t.GetClass() == 'PCB_VIA' and near(xy(t.GetPosition()), (31.0, 2.12)):
        rm(t)
    elif t.GetClass() != 'PCB_VIA' and t.GetLayer() == pcbnew.B_Cu and \
            {tuple(round(v, 2) for v in xy(t.GetStart())), tuple(round(v, 2) for v in xy(t.GetEnd()))} == {(31.0, 2.12), (31.0, 0.85)}:
        rm(t)
r27 = clone('R15', 'R27', '1kR', 'f6a7da04-2026-5c84-b64e-f3375fd90234',
            {'MPN': '0402WGF1001TCE', 'LCSC': 'C11702', 'Manufacturer': 'UNI-ROYAL(Uniroyal Elec)',
             'Description': 'Resistor 1k 1% 0402'}, (20.4, 2.7), 0, {'1': VREF, '2': V3})
r.save()
r = R(sys.argv[1])
b = r.b
pa, pb = r.pp('R27', 1), r.pp('R27', 2)
assert pa[0] < pb[0], (pa, pb)   # pad 1 (VREF) on the left
r.track(['R27.2', (pb[0], 3.2), 'C14.1'], 0.2, net=V3)
c14 = b.FindFootprintByReference('C14').Reference()   # R27 took its spot: vertical, left of C14
c14.SetTextAngleDegrees(90)
c14.SetPosition(P(17.95, 1.68))            # +3V3 from C14's pad
r.via(19.9, 1.75, VREF, d=0.5, drill=0.25)
r.track(['R27.1', (19.9, 1.75)], 0.15, net=VREF)
r.track([(19.9, 1.75), (20.65, 1.2), (21.2, 0.65), (21.43, 0.42), (30.6, 0.42), 'J4.1'], 0.15, layer='B', net=VREF)

# 3. SW1: R28 100R (BTN_SW <-> BTN_N) and C27 100 nF BTN_N -> GND
BTN, SWN = '/BTN_N', '/BTN_SW'
sw1 = b.FindFootprintByReference('SW1')
for p in sw1.Pads():
    if p.GetNumber() == '1':
        p.SetNet(netitem(SWN))
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA' or t.GetNetname() != BTN:
        continue
    s, e = xy(t.GetStart()), xy(t.GetEnd())
    seg = {tuple(round(v, 2) for v in s), tuple(round(v, 2) for v in e)}
    if seg in ({(4.05, 22.05), (3.45, 22.65)}, {(3.45, 22.65), (3.45, 23.5)}):
        rm(t)
    elif seg == {(4.05, 16.9), (4.05, 22.05)}:   # now ends at the R14 stub
        (t.SetEnd if near(e, (4.05, 22.05)) else t.SetStart)(P(4.05, 21.05))
clone('R15', 'R28', '100R', '9daa9a3b-746a-5300-9bc3-97c06cdb9a46',
      {'MPN': '0402WGF1000TCE', 'LCSC': 'C25076', 'Manufacturer': 'UNI-ROYAL(Uniroyal Elec)',
       'Description': 'Resistor 100R 1% 0402'}, (5.8, 24.4), -90, {'1': BTN, '2': SWN})
clone('C14', 'C27', '100nF/16V', 'a643fa46-62b6-5611-8e46-24ac788332f5',
      {'MPN': 'CL05B104KO5NNNC', 'LCSC': 'C1525', 'Manufacturer': 'Samsung Electro-Mechanics',
       'Description': 'MLCC 100nF 16V X7R 0402'}, (7.0, 22.4), 0, {'1': BTN, '2': GND})
r.save()
r = R(sys.argv[1])
b = r.b
top, bot = sorted([r.pp('R28', 1), r.pp('R28', 2)], key=lambda q: q[1])
assert near(r.pp('R28', 1), top), 'R28 pad 1 (BTN_N) should be on top'
c1p = r.pp('C27', 1)
assert c1p[0] < r.pp('C27', 2)[0], 'C27 pad 1 (BTN_N) should be on the left'
r.track(['R28.1', (6.05, top[1] - 0.25), (6.05, 22.0), (5.55, 21.5), 'R14.1' if near(r.pp('R14', 1), (4.5, 21.5), 0.1) else 'R14.2'],
        0.15, net=BTN)
r.track([(6.05, c1p[1]), 'C27.1'], 0.15, net=BTN)
sw = r.pp('SW1', 1)
r.track(['SW1.1', (sw[0], 24.2), (3.68, 24.66), (5.55, 24.66), 'R28.2'], 0.15, net=SWN)
r.save()
print('ok')
