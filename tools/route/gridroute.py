"""Small 2-layer (F/B) grid router for the leftover signals.

Obstacles come from the board (pads, tracks, vias, edge, keepouts) inflated by clearance + half width.
Octile A* with layer costs, via cost and a turn penalty; results are added as unlocked tracks/vias.
"""
import heapq, math, sys
import numpy as np
import pcbnew
from rt import R, P, xy, MM, LAY

G = 0.05
X0, Y0, X1, Y1 = -0.6, -5.8, 40.6, 44.9
NX, NY = int((X1 - X0) / G) + 1, int((Y1 - Y0) / G) + 1
XS = X0 + np.arange(NX) * G
YS = Y0 + np.arange(NY) * G
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def cl(n):
    return max(0, min(n, NX - 1))


def clyy(n):
    return max(0, min(n, NY - 1))


class Grid:
    def __init__(self, r, keep_boxes, edge=0.35):
        self.r = r
        self.b = r.b
        self.keep = keep_boxes   # list of (layer 'F'/'B'/'V', x0, y0, x1, y1)
        self.edge = edge
        # board inside mask from the edge polygon
        outline = pcbnew.SHAPE_POLY_SET()
        try:
            self.b.GetBoardPolygonOutlines(outline, False)   # KiCad 10 signature
        except TypeError:
            self.b.GetBoardPolygonOutlines(outline)
        self.outline = outline

    def mask_items(self, net, w, clr, via_d):
        """blocked[L] for track centre of width w; vblk for a via of dia via_d."""
        blk = {0: np.zeros((NY, NX), bool), 1: np.zeros((NY, NX), bool)}
        vblk = np.zeros((NY, NX), bool)
        hw = w / 2
        vr = via_d / 2
        # outside board
        key = (round(hw, 3), round(vr, 3))
        if key not in CACHE:
            ol = self.outline.Outline(0)
            ins = poly_mask([xy(ol.CPoint(i)) for i in range(ol.PointCount())])
            CACHE[key] = (~erode(ins, int(math.ceil((self.edge + hw) / G))), ~erode(ins, int(math.ceil((self.edge + vr) / G))))
        out_t, out_v = CACHE[key]
        blk[0] |= out_t
        blk[1] |= out_t
        vblk |= out_v
        for L, x0, y0, x1, y1 in self.keep:
            i0, i1 = cl(int((x0 - X0) / G)), cl(int((x1 - X0) / G) + 1)
            j0, j1 = clyy(int((y0 - Y0) / G)), clyy(int((y1 - Y0) / G) + 1)
            if L in ('F', 'FB'):
                blk[0][j0:j1, i0:i1] = True
            if L in ('B', 'FB'):
                blk[1][j0:j1, i0:i1] = True
            if L in ('V', 'F', 'B', 'FB'):
                vblk[j0:j1, i0:i1] = True
        # rule-area keepouts (tracks not allowed)
        zones = list(self.b.Zones())
        for f in self.b.GetFootprints():
            zones += list(f.Zones())
        for z in zones:
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                ol = z.Outline().Outline(0)
                m = poly_mask([xy(ol.CPoint(i)) for i in range(ol.PointCount())])
                m = dilate(m, int(math.ceil((hw + 0.02) / G)))
                for li, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                    if z.IsOnLayer(lid):
                        blk[li] |= m
                vblk |= dilate(m, int(math.ceil(vr / G)))
        for f in self.b.GetFootprints():
            for p in f.Pads():
                same = p.GetNetname() == net and net
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.IsOnLayer(pcbnew.F_Cu):
                    rect(vblk, p.GetEffectivePolygon(pcbnew.F_Cu).BBox(), 0.27 + vr)   # dog-bone: via edge >= 0.25 mm from any pad
                if same:
                    continue
                c = clr + (0.08 if p.GetNetname() in HOT else 0)
                for li, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                    if p.IsOnLayer(lid):
                        bb = p.GetEffectivePolygon(lid).BBox()
                        rect(blk[li], bb, c + hw)
                if p.GetDrillSize().x or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    d = max(p.GetDrillSize().x, p.GetDrillSize().y) / 1e6
                    circ(vblk, xy(p.GetPosition()), d / 2 + 0.5 + vr)
                    circ(blk[0], xy(p.GetPosition()), d / 2 + 0.3 + hw)
                    circ(blk[1], xy(p.GetPosition()), d / 2 + 0.3 + hw)
                if p.IsOnLayer(pcbnew.F_Cu):
                    bb = p.GetEffectivePolygon(pcbnew.F_Cu).BBox()
                    rect(vblk, bb, c + vr)
                if p.IsOnLayer(pcbnew.B_Cu):
                    bb = p.GetEffectivePolygon(pcbnew.B_Cu).BBox()
                    rect(vblk, bb, c + vr)
        for t in self.b.GetTracks():
            if t.GetNetname() == net and net:
                continue
            c = clr + (0.08 if t.GetNetname() in HOT else 0)
            if t.GetClass() == 'PCB_VIA':
                d = t.GetWidth(pcbnew.F_Cu) / 1e6
                for li in (0, 1):
                    circ(blk[li], xy(t.GetPosition()), d / 2 + c + hw)
                circ(vblk, xy(t.GetPosition()), max(d / 2 + c + vr, t.GetDrillValue() / 2e6 + 0.5 + 0.15))
            else:
                L = t.GetLayer()
                wd = t.GetWidth() / 1e6
                a, z = xy(t.GetStart()), xy(t.GetEnd())
                if L == pcbnew.F_Cu:
                    seg(blk[0], a, z, wd / 2 + c + hw); seg(vblk, a, z, wd / 2 + c + vr)
                elif L == pcbnew.B_Cu:
                    seg(blk[1], a, z, wd / 2 + c + hw); seg(vblk, a, z, wd / 2 + c + vr)
                elif L == pcbnew.In2_Cu:
                    seg(vblk, a, z, wd / 2 + c + vr)
        # BMP585 no-mask window: no foreign copper, own pads leave radially, no vias
        u3 = self.b.FindFootprintByReference('U3')
        if u3:
            cx, cy = xy(u3.GetPosition()); W = 1.75
            win = np.zeros((NY, NX), bool)
            i0, i1 = cl(int((cx - W - hw - X0) / G)), cl(int((cx + W + hw - X0) / G) + 1)
            j0, j1 = clyy(int((cy - W - hw - Y0) / G)), clyy(int((cy + W + hw - Y0) / G) + 1)
            win[j0:j1, i0:i1] = True
            vblk[clyy(j0 - int(vr / G) - 6):j1 + int(vr / G) + 6, cl(i0 - int(vr / G) - 6):i1 + int(vr / G) + 6] = True
            for p in u3.Pads():
                if p.GetNetname() == net and net:
                    bb = p.GetEffectivePolygon(pcbnew.F_Cu).BBox()
                    px0, py0 = xy(bb.GetOrigin()); px1, py1 = xy(bb.GetEnd())
                    pcx, pcy = xy(p.GetPosition())
                    if abs(pcx - cx) > abs(pcy - cy):   # left/right column: strip outward in x
                        xa, xb = (cx - W - 1, px1) if pcx < cx else (px0, cx + W + 1)
                        ya, yb = py0 + 0.1, py1 - 0.1
                    else:
                        ya, yb = (cy - W - 1, py1) if pcy < cy else (py0, cy + W + 1)
                        xa, xb = px0 + 0.1, px1 - 0.1
                    win[clyy(int((ya - Y0) / G)):clyy(int((yb - Y0) / G) + 1), cl(int((xa - X0) / G)):cl(int((xb - X0) / G) + 1)] = False
            blk[0] |= win
        return blk, vblk


CACHE = {}
HOT = {'/USB_D+', '/USB_D-', '/EPD_PREVGH', '/EPD_PREVGL', 'Net-(D2-A)', 'Net-(D3-A)', '/EPD_GDR', '/EPD_RESE'}


def idx(x, y):
    return int(round((x - X0) / G)), int(round((y - Y0) / G))


def poly_mask(pts):
    m = np.zeros((NY, NX), bool)
    px = np.array([p[0] for p in pts]); py = np.array([p[1] for p in pts])
    Xg, Yg = np.meshgrid(XS, YS)
    inside = np.zeros_like(Xg, bool)
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = px[i], py[i], px[j], py[j]
        cond = ((yi > Yg) != (yj > Yg)) & (Xg < (xj - xi) * (Yg - yi) / ((yj - yi) if yj != yi else 1e-12) + xi)
        inside ^= cond
        j = i
    return inside


def shift(m, dx, dy):
    o = np.zeros_like(m)
    ys = slice(max(dy, 0), NY + min(dy, 0)); yd = slice(max(-dy, 0), NY + min(-dy, 0))
    xs = slice(max(dx, 0), NX + min(dx, 0)); xd = slice(max(-dx, 0), NX + min(-dx, 0))
    o[yd, xd] = m[ys, xs]
    return o


def dilate(m, n):
    o = m.copy()
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            if dx * dx + dy * dy <= n * n:
                o |= shift(m, dx, dy)
    return o


def erode(m, n):
    return ~dilate(~m, n)


def rect(m, bb, r):
    x0, y0 = xy(bb.GetOrigin()); x1, y1 = xy(bb.GetEnd())
    i0, i1 = cl(int((x0 - r - X0) / G) - 1), cl(int((x1 + r - X0) / G) + 2)
    j0, j1 = clyy(int((y0 - r - Y0) / G) - 1), clyy(int((y1 + r - Y0) / G) + 2)
    if i1 <= i0 or j1 <= j0:
        return
    X = XS[i0:i1][None, :]; Y = YS[j0:j1][:, None]
    dx = np.maximum(np.maximum(x0 - X, X - x1), 0); dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
    m[j0:j1, i0:i1] |= (dx * dx + dy * dy) < r * r


def circ(m, c, r):
    x, y = c
    i0, i1 = cl(int((x - r - X0) / G) - 1), cl(int((x + r - X0) / G) + 2)
    j0, j1 = clyy(int((y - r - Y0) / G) - 1), clyy(int((y + r - Y0) / G) + 2)
    X = XS[i0:i1][None, :]; Y = YS[j0:j1][:, None]
    m[j0:j1, i0:i1] |= ((X - x) ** 2 + (Y - y) ** 2) < r * r


def seg(m, a, z, r):
    (ax, ay), (bx, by) = a, z
    i0, i1 = cl(int((min(ax, bx) - r - X0) / G) - 1), cl(int((max(ax, bx) + r - X0) / G) + 2)
    j0, j1 = clyy(int((min(ay, by) - r - Y0) / G) - 1), clyy(int((max(ay, by) + r - Y0) / G) + 2)
    X = XS[i0:i1][None, :]; Y = YS[j0:j1][:, None]
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 < 1e-12:
        t = 0
    else:
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
    px, py = ax + t * vx, ay + t * vy
    m[j0:j1, i0:i1] |= ((X - px) ** 2 + (Y - py) ** 2) < r * r


def net_cells(r, net):
    """connected copper groups of a net as cell sets: returns ({name: cells}, []) where every group is one island."""
    items = []
    for f in r.b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != net:
                continue
            cells = set()
            for li, lid in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                if p.IsOnLayer(lid):
                    bb = p.GetEffectivePolygon(lid).BBox()
                    x0, y0 = xy(bb.GetOrigin()); x1, y1 = xy(bb.GetEnd())
                    cx, cy = xy(p.GetPosition())
                    for i in range(cl(int((x0 - X0) / G)), cl(int((x1 - X0) / G) + 1)):
                        for j in range(clyy(int((y0 - Y0) / G)), clyy(int((y1 - Y0) / G) + 1)):
                            x, y = XS[i], YS[j]
                            if abs(x - cx) <= max(0.05, (x1 - x0) / 2 - 0.08) and abs(y - cy) <= max(0.05, (y1 - y0) / 2 - 0.08):
                                cells.add((li, i, j))
            items.append((f.GetReference() + '.' + p.GetNumber(), cells))
    for t in r.b.GetTracks():
        if t.GetNetname() != net:
            continue
        cells = set()
        if t.GetClass() == 'PCB_VIA':
            i, j = idx(*xy(t.GetPosition()))
            cells |= {(0, i, j), (1, i, j)}
        else:
            L = {pcbnew.F_Cu: 0, pcbnew.B_Cu: 1}.get(t.GetLayer())
            if L is None:
                continue
            a, z = xy(t.GetStart()), xy(t.GetEnd())
            n = max(1, int(math.hypot(z[0] - a[0], z[1] - a[1]) / G))
            for k in range(n + 1):
                cells.add((L,) + idx(a[0] + (z[0] - a[0]) * k / n, a[1] + (z[1] - a[1]) * k / n))
        items.append(('trk', cells))
    # union-find on touching cells (8-neighbourhood, same layer)
    par = list(range(len(items)))
    def fnd(k):
        while par[k] != k:
            par[k] = par[par[k]]; k = par[k]
        return k
    owner = {}
    for k, (_, cells) in enumerate(items):
        for c in cells:
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    o = owner.get((c[0], c[1] + di, c[2] + dj))
                    if o is not None:
                        par[fnd(k)] = fnd(o)
            owner[c] = k
    comp = {}
    for k, (name, cells) in enumerate(items):
        key = fnd(k)
        nm, cs = comp.get(key, (None, set()))
        if nm is None or (nm == 'trk' and name != 'trk'):
            nm = name
        comp[key] = (nm, cs | cells)
    return {('%s#%d' % (nm, k)): cs for k, (nm, cs) in comp.items()}, []


def astar(src, dst, blk, vblk, lcost, via_cost, turn=1.2):
    """multi-source A*. state (layer, i, j, dir)."""
    dl = list(dst)
    if not dl:
        return None
    dxs = np.array([d[1] for d in dl]); dys = np.array([d[2] for d in dl])
    tx, ty = dxs.mean(), dys.mean()
    dset = set(dst)

    def h(i, j):
        dx, dy = abs(i - tx), abs(j - ty)
        return (max(dx, dy) + 0.414 * min(dx, dy)) * min(lcost) * 0.9

    openq = []
    g = {}
    par = {}
    for s in src:
        L, i, j = s
        if blk[L][j, i]:
            pass  # pad cells may sit inside the inflated area of neighbours: allow starting
        st = (L, i, j, -1)
        g[st] = 0
        heapq.heappush(openq, (h(i, j), 0, st))
    seen = 0
    while openq:
        f, gc, st = heapq.heappop(openq)
        if g.get(st, 1e18) < gc - 1e-9:
            continue
        L, i, j, d = st
        if (L, i, j) in dset:
            path = [st]
            while st in par:
                st = par[st]
                path.append(st)
            return path[::-1]
        seen += 1
        if seen > 3_000_000:
            return None
        for k, (di, dj) in enumerate(DIRS):
            ni, nj = i + di, j + dj
            if not (0 <= ni < NX and 0 <= nj < NY):
                continue
            if blk[L][nj, ni] and (L, ni, nj) not in dset:
                continue
            step = (1.7 if k >= 4 else 1.0) * lcost[L]
            if d >= 0 and d != k:
                step += turn
            ns = (L, ni, nj, k)
            ng = gc + step
            if ng < g.get(ns, 1e18):
                g[ns] = ng
                par[ns] = st
                heapq.heappush(openq, (ng + h(ni, nj), ng, ns))
        # via
        if not vblk[j, i]:
            OL = 1 - L
            if not blk[OL][j, i] or (OL, i, j) in dset:
                ns = (OL, i, j, -1)
                ng = gc + via_cost
                if ng < g.get(ns, 1e18):
                    g[ns] = ng
                    par[ns] = st
                    heapq.heappush(openq, (ng + h(i, j), ng, ns))
    return None


def emit(r, net, path, w, via_d, via_dr):
    """path: list of (L,i,j,dir) -> tracks + vias; collinear merge."""
    segs = []
    cur = [path[0]]
    for st in path[1:]:
        if st[0] != cur[-1][0]:
            segs.append(cur)
            cur = [st]
        else:
            cur.append(st)
    segs.append(cur)
    n = r.net(net)
    made = []
    for k, sg in enumerate(segs):
        L = sg[0][0]
        pts = [(round(float(XS[s[1]]), 4), round(float(YS[s[2]]), 4)) for s in sg]
        # collinear merge
        simp = [pts[0]]
        for a in range(1, len(pts) - 1):
            p0, p1, p2 = simp[-1], pts[a], pts[a + 1]
            d1 = (round((p1[0] - p0[0]) / G), round((p1[1] - p0[1]) / G))
            d2 = (round((p2[0] - p1[0]) / G), round((p2[1] - p1[1]) / G))
            n1 = (np.sign(d1[0]), np.sign(d1[1])); n2 = (np.sign(d2[0]), np.sign(d2[1]))
            if n1 != n2:
                simp.append(p1)
        simp.append(pts[-1])
        for a, z in zip(simp, simp[1:]):
            t = pcbnew.PCB_TRACK(r.b)
            t.SetStart(P(*a)); t.SetEnd(P(*z)); t.SetWidth(MM(w)); t.SetLayer(LAY['F' if L == 0 else 'B']); t.SetNet(n)
            r.b.Add(t); made.append(t)
        if k + 1 < len(segs):
            x, y = pts[-1]
            v = pcbnew.PCB_VIA(r.b); v.SetPosition(P(x, y)); v.SetWidth(MM(via_d)); v.SetDrill(MM(via_dr))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetNet(n); r.b.Add(v); made.append(v)
    return made


def route_net(r, grid, net, w=0.15, clr=0.15, via=(0.6, 0.3), lcost=(1.25, 1.0), via_cost=25, order=None, allow=None, padr=1.2):
    pads, tc = net_cells(r, net)
    groups = sorted([set(c) for c in pads.values() if c], key=len, reverse=True)
    if order:
        pass
    if len(groups) < 2:
        return True
    blk, vblk = grid.mask_items(net, w, clr, via[0])
    if allow:
        am = {0: np.zeros((NY, NX), bool), 1: np.zeros((NY, NX), bool)}
        for L, x0, y0, x1, y1 in allow:
            i0, i1 = cl(int((x0 - X0) / G)), cl(int((x1 - X0) / G) + 1)
            j0, j1 = clyy(int((y0 - Y0) / G)), clyy(int((y1 - Y0) / G) + 1)
            for li in ((0,) if L == 'F' else (1,) if L == 'B' else (0, 1)):
                am[li][j0:j1, i0:i1] = True
        for gi_, gset in enumerate(groups):
            for (L, i, j) in gset:
                n = int(padr / G)
                am[0][max(0, j - n):j + n, max(0, i - n):i + n] = True
                am[1][max(0, j - n):j + n, max(0, i - n):i + n] = True
        blk[0] |= ~am[0]; blk[1] |= ~am[1]
        vblk |= ~(am[0] & am[1])
    tree = groups[0]
    todo = groups[1:]
    ok = True
    while todo:
        # connect the nearest remaining group
        best = None
        for gi, gset in enumerate(todo):
            path = astar(list(gset), tree, blk, vblk, lcost, via_cost)
            if path is None:
                continue
            cost = len(path)
            if best is None or cost < best[0]:
                best = (cost, gi, path)
            break  # take the first routable group (keeps runtime down)
        if best is None:
            print('  FAIL', net, 'groups left', len(todo))
            ok = False
            break
        _, gi, path = best
        made = emit(r, net, path, w, *via)
        tree |= todo.pop(gi)
        for st in path:
            tree.add(st[:3])
    return ok
