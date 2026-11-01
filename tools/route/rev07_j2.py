"""rev 0.7 review: J2 turned 180 deg so the PH plug enters from the left board edge (it pointed at the SHT31
island). Rips up the routing under J2 (VBAT/BAT_N stubs, the SDA/SCL jogs, four GND vias) and re-routes it by hand.
usage: rev07_j2.py in.kicad_pcb out.kicad_pcb"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pcbnew  # noqa: E402
from rt import R  # noqa: E402

r = R(sys.argv[1]); b = r.b
mm = pcbnew.FromMM
def at(p, x, y, tol=0.03): return abs(p.x - mm(x)) < mm(tol) and abs(p.y - mm(y)) < mm(tol)
def seg(t, a, z): return (at(t.GetStart(), *a) and at(t.GetEnd(), *z)) or (at(t.GetStart(), *z) and at(t.GetEnd(), *a))

j2 = next(f for f in b.GetFootprints() if f.GetReference() == 'J2')
j2.SetOrientationDegrees(270)

kill_seg = {
    'VBAT': [((103.5, 104.6), (102.75, 105.2)), ((102.1, 103.25), (102.75, 103.9)), ((103.5, 103.9), (103.5, 104.6)),
             ((102.75, 103.9), (102.75, 105.2)), ((102.1, 103.25), (102.1, 103.9)), ((102.1, 103.9), (103.5, 103.9)),
             ((101.0, 105.0), (102.1, 103.9))],
    '/BAT_N': [((102.75, 107.2), (104.2, 107.2)), ((104.2, 107.2), (104.2, 113.4)), ((104.2, 113.4), (103.54, 114.0))],
    '/I2C_SDA': [((111.82, 107.6), (108.5, 107.6)), ((108.5, 107.6), (106.95, 106.05)), ((106.95, 106.05), (105.99, 106.05)),
                 ((105.2, 106.84), (105.99, 106.05))],
    '/I2C_SCL': [((106.4, 106.7), (106.4, 111.7)), ((110.6, 110.9), (106.4, 106.7)), ((117.3, 108.4), (108.1, 108.4))],
}
kill_via = {'VBAT': [(102.1, 103.25), (103.5, 103.9)], '/I2C_SCL': [(106.4, 106.7)],
            'GND': [(109.2, 106.8), (102.0, 102.0), (102.0, 109.2), (100.75, 102.6)]}
dead = []
for t in b.GetTracks():
    n = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        if any(at(t.GetPosition(), *v) for v in kill_via.get(n, [])): dead.append(t)
    elif any(seg(t, a, z) for a, z in kill_seg.get(n, [])):
        dead.append(t)
want = sum(map(len, kill_seg.values())) + sum(map(len, kill_via.values()))
print('ripped', len(dead), 'of', want)
assert len(dead) == want
for t in dead: b.Delete(t)
# SCL: keep the B.Cu run from the U4 via to the U2 via (the west part was a dead stub)
r.track([(17.3, 8.4), (13.9, 8.4)], 0.15, 'B', '/I2C_SCL')
# polarity marks at the plug mouth: pin 1 (-) is the upper contact, pin 2 (+) the lower
for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() in ('+', '-') and abs(d.GetPosition().x - mm(101.9)) < mm(0.1):
        y = 110.95 if d.GetText() == '+' else 101.4   # '-' above the mouth (pin 1 side), '+' below (pin 2 side)
        d.SetPosition(pcbnew.VECTOR2I(mm(100.9), mm(y)))
        d.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))

# dead ends after the rip-up: VBAT feed on B.Cu at x 101, SDA stub above its via, SCL stub at U3
for t in list(b.GetTracks()):
    if (t.GetNetname() == 'VBAT' and seg(t, (101.0, 130.4), (101.0, 105.0))) or \
       (t.GetNetname() == '/I2C_SDA' and seg(t, (105.2, 106.84), (105.2, 111.7))) or \
       (t.GetNetname() == '/I2C_SCL' and seg(t, (111.0, 110.9), (110.6, 110.9))):
        b.Delete(t)
O = 100.0
def T(net, w, L, *pts): r.track([(x - O, y - O) for x, y in pts], w, L, net)
def V(net, x, y, d=0.6, dr=0.3): r.via(x - O, y - O, net, d, dr)
# VBAT: J2.2 (108.45, 107.2) -> F.Cu along y 106.2 under the J2 body -> via onto the B.Cu feed at x 101
T('VBAT', 0.6, 'F', (108.45, 107.2), (107.45, 106.2), (101.0, 106.2))
V('VBAT', 101.0, 106.2, 0.8, 0.4)
T('VBAT', 0.6, 'B', (101.0, 106.2), (101.0, 130.4))
# BAT_N: J2.1 (108.45, 105.2) -> via left of the pad -> B.Cu 45 deg, parallel to BTN_N -> down x 103.45 -> Q2.3
T('/BAT_N', 0.6, 'F', (108.45, 105.2), (106.4, 105.2), (105.95, 104.75))
V('/BAT_N', 105.95, 104.75)
T('/BAT_N', 0.6, 'B', (105.95, 104.75), (103.45, 107.25), (103.45, 113.1))
V('/BAT_N', 103.45, 113.1)
T('/BAT_N', 0.6, 'F', (103.45, 113.1), (103.54, 114.0))
# SDA: SHT31 branch end (111.82, 107.6) -> under the J2 pins along y 108.32 -> via (105.2, 108.05) -> U5
T('/I2C_SDA', 0.15, 'F', (111.82, 107.6), (111.1, 108.32), (105.48, 108.32), (105.2, 108.04))
T('/I2C_SDA', 0.15, 'F', (105.2, 108.05), (105.2, 111.7))
# SCL: U5 stub (106.4, 111.7) -> F.Cu to the U3 via (111.0, 110.9) -> B.Cu to the U2/U4 run at (113.9, 108.4)
T('/I2C_SCL', 0.15, 'F', (106.4, 111.7), (109.95, 111.7), (110.75, 110.9), (111.0, 110.9))
T('/I2C_SCL', 0.15, 'B', (111.0, 110.9), (113.5, 108.4), (113.9, 108.4))
r.save(sys.argv[2])
