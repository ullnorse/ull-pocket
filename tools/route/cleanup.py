"""remove track segments fully covered by another same-net, same-layer segment of >= width (collinear overlap)"""
import sys, math
from rt import *
r = R(sys.argv[1]); b = r.b
ts = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
def cov(a, c):   # is segment a inside segment c (collinear, within 0.01 mm)
    (ax0, ay0), (ax1, ay1) = xy(a.GetStart()), xy(a.GetEnd()); (cx0, cy0), (cx1, cy1) = xy(c.GetStart()), xy(c.GetEnd())
    vx, vy = cx1 - cx0, cy1 - cy0; L = math.hypot(vx, vy)
    if L < 1e-6: return False
    for px, py in ((ax0, ay0), (ax1, ay1)):
        if abs((px - cx0) * vy - (py - cy0) * vx) / L > 0.01: return False
        t = ((px - cx0) * vx + (py - cy0) * vy) / (L * L)
        if t < -0.001 or t > 1.001: return False
    return True
rm = set()
for i, a in enumerate(ts):
    for j, c in enumerate(ts):
        if i == j or j in rm or a.GetNetname() != c.GetNetname() or a.GetLayer() != c.GetLayer(): continue
        if c.GetWidth() >= a.GetWidth() and cov(a, c) and (c.GetWidth() > a.GetWidth() or i > j):
            rm.add(i); break
for i in rm: b.Remove(ts[i])
print('removed', len(rm), 'covered segments')
r.save(sys.argv[2])
