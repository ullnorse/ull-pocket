"""Zones, GND/+3V3 via fan-out to the planes, edge/keep-out stitching. in: auto.kicad_pcb out: done.kicad_pcb"""
import math, sys
import numpy as np
import pcbnew
from rt import *
from gridroute import Grid, idx, XS, YS, G, NX, NY, X0, Y0, circ

r = R(sys.argv[1] if len(sys.argv) > 1 else 'auto.kicad_pcb')
b = r.b

# ---------------------------------------------------------------- via fan-out for plane nets
keep = []
grid = Grid(r, keep)


def in_v3(x, y):
    return y > 0.7 and ((x < 25.2 and y < 9.4) or (x < 18.8 and y < 31.2) or (x < 14.4))


def all_via_block(vblk):
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            circ(vblk, xy(t.GetPosition()), 0.86)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetDrillSize().x:
                circ(vblk, xy(p.GetPosition()), p.GetDrillSize().x / 2e6 + 0.5 + 0.15)


def place_vias(net, cond, maxd=1.6):
    blk, vblk = grid.mask_items(net, 0.3, 0.15, 0.6)
    all_via_block(vblk)
    vias = [xy(t.GetPosition()) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net]
    added = 0
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != net or not p.IsOnLayer(pcbnew.F_Cu) or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px, py = xy(p.GetPosition())
            if py < 0.7 or not cond(px, py):
                continue
            if any(math.hypot(px - vx, py - vy) < 1.0 for vx, vy in vias):
                continue
            bb = p.GetEffectivePolygon(pcbnew.F_Cu).BBox()
            hw_, hh_ = bb.GetWidth() / 2e6, bb.GetHeight() / 2e6
            best = None
            for rad in np.arange(0.45, maxd, 0.1):
                for a in range(0, 360, 15):
                    vx = px + (hw_ + rad) * math.cos(math.radians(a)) if abs(math.cos(math.radians(a))) > 0.3 else px + rad * math.cos(math.radians(a))
                    vy = py + (hh_ + rad) * math.sin(math.radians(a)) if abs(math.sin(math.radians(a))) > 0.3 else py + rad * math.sin(math.radians(a))
                    i, j = idx(vx, vy)
                    if not (0 <= i < NX and 0 <= j < NY) or vblk[j, i]:
                        continue
                    # stub from pad edge to via must be clear on F
                    n = max(2, int(math.hypot(vx - px, vy - py) / G))
                    okk = True
                    for k in range(n + 1):
                        x = px + (vx - px) * k / n; y = py + (vy - py) * k / n
                        ii, jj = idx(x, y)
                        inside_pad = abs(x - px) <= hw_ and abs(y - py) <= hh_
                        if blk[0][jj, ii] and not inside_pad:
                            okk = False
                            break
                    if okk:
                        best = (vx, vy)
                        break
                if best:
                    break
            if not best:
                print('  no via spot for', f.GetReference(), p.GetNumber(), net)
                continue
            vx, vy = best
            v = r.via(vx, vy, net, 0.6, 0.3)
            r.track([(px, py), (vx, vy)], 0.3, 'F', net)
            vias.append((vx, vy))
            circ(vblk, (vx, vy), 0.86)
            circ(blk[0], (vx, vy), 0.3 + 0.15 + 0.15)
            circ(blk[1], (vx, vy), 0.3 + 0.15 + 0.15)
            added += 1
    print(net, 'vias added', added)


place_vias('GND', lambda x, y: True)
place_vias('+3V3', in_v3)

# ---------------------------------------------------------------- stitching: board edge and module surround
blk, vblk = grid.mask_items('GND', 0.3, 0.15, 0.6)
all_via_block(vblk)
stitched = 0
cand = []
for x in np.arange(1.0, 39.1, 1.6):
    cand += [(x, 0.75), (x, 43.75)]
for y in np.arange(1.0, 43.6, 1.6):
    cand += [(0.75, y), (39.25, y)]
# around the module (outside its courtyard) and between modules pads row and board top edge
for x in np.arange(25.0, 39.4, 1.2):
    cand += [(x, 11.9)]
for y in np.arange(0.8, 11.5, 1.2):
    cand += [(25.2, y), (39.55, y)]
# interior grid
for x in np.arange(2.0, 39.0, 2.4):
    for y in np.arange(2.0, 43.5, 2.4):
        cand.append((x, y))
for x, y in cand:
    i, j = idx(x, y)
    if y < 0.7 or not (0 <= i < NX and 0 <= j < NY) or vblk[j, i]:
        continue
    r.via(x, y, 'GND', 0.6, 0.3)
    circ(vblk, (x, y), 1.2)
    stitched += 1
print('stitching vias', stitched)

from gridroute import astar, emit
def connect_pad(net, ref, num, box):
    blk, vblk = grid.mask_items(net, 0.15, 0.13, 0.45)
    p = r.pad(ref, num); px, py = xy(p.GetPosition())
    i, j = idx(px, py)
    src = [(0, i + a, j + c) for a in (-1, 0, 1) for c in (-1, 0, 1)]
    dst = set()
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net:
            vx, vy = xy(t.GetPosition())
            if box[0] <= vx <= box[2] and box[1] <= vy <= box[3]:
                ii, jj = idx(vx, vy); dst |= {(0, ii, jj), (1, ii, jj)}
    path = astar(src, dst, blk, vblk, (1.0, 1.2), 20)
    if path:
        emit(r, net, path, 0.15, 0.45, 0.2); print('connected', ref, num)
    else:
        print('connect failed', ref, num)
connect_pad('GND', 'U4', '5', (12, 2, 26, 14))
SOLID = {'TP3': ('1',), 'U5': '1469', 'U4': '51012', 'U3': '36', 'J1': ('A1', 'A12', 'B1', 'B12')}
for ref, pads in SOLID.items():
    f = b.FindFootprintByReference(ref)
    for p in f.Pads():
        if p.GetNetname() == 'GND' and (p.GetNumber() in pads if isinstance(pads, tuple) else p.GetNumber() in [c for c in pads] or p.GetNumber() in ('10', '12')):
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
r.save(sys.argv[2] if len(sys.argv) > 2 else 'vias.kicad_pcb')
