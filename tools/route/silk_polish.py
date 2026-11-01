"""Silkscreen polish on a KiCad 9 working copy (board coords: origin = KiCad 100,100).

    python3 silk_polish.py build/route/work.kicad_pcb

F.Silk: every part gets a 1.0 mm / 0.15 mm reference at 0 or 90 deg, beside its courtyard, off pads,
other silk, courtyards and edges. Test points read "TPn NET"; J1/J3/SW1/U2 carry a function label.
Placement is greedy, most-constrained first, on a 0.05 mm raster. Refs that find no spot go to F.Fab.
Also adds three F-side fiducials where a copper-free spot exists, and the B.Silk labels and title block.
"""
import sys
import numpy as np
import pcbnew
from PIL import Image, ImageDraw
from rt import P, xy, MM

FN = sys.argv[1]
b = pcbnew.LoadBoard(FN)
KEEP = []
RES, X0, Y0, W, H = 0.05, -1.0, -1.0, 42.0, 47.0
NX, NY = int(W / RES), int(H / RES)
TXT, STK = 1.0, 0.15
SILK_GAP, PAD_GAP, EDGE_GAP = 0.12, 0.15, 0.2
TXT_GAP = 0.35  # text-to-text: keeps neighbouring refs from reading as one word


def g(x, y):
    return ((x - X0) / RES, (y - Y0) / RES)


def blank():
    return Image.new('1', (NX, NY), 0)


def poly_draw(img, ps, fill=1):
    d = ImageDraw.Draw(img)
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        pts = [g(*xy(o.CPoint(j))) for j in range(o.PointCount())]
        if len(pts) > 2:
            d.polygon(pts, fill=fill)
        for h in range(ps.HoleCount(i)):
            hh = ps.Hole(i, h)
            hp = [g(*xy(hh.CPoint(j))) for j in range(hh.PointCount())]
            if len(hp) > 2:
                d.polygon(hp, fill=1 - fill)


def item_poly(it, layer, clr):
    ps = pcbnew.SHAPE_POLY_SET()
    it.TransformShapeToPolygon(ps, layer, MM(clr), MM(0.01), pcbnew.ERROR_OUTSIDE)
    return ps


def arr(img):
    return np.array(img, dtype=bool)


def side_obstacles(side):
    """Raster of places a silk text may not touch on side 'F' or 'B' (courtyards separate)."""
    cu, silk, mask = (pcbnew.F_Cu, pcbnew.F_SilkS, pcbnew.F_Mask) if side == 'F' else (pcbnew.B_Cu, pcbnew.B_SilkS, pcbnew.B_Mask)
    img = Image.new('1', (NX, NY), 1)
    outl = pcbnew.SHAPE_POLY_SET()
    try:
        b.GetBoardPolygonOutlines(outl, False)   # KiCad 10 signature
    except TypeError:
        b.GetBoardPolygonOutlines(outl)
    poly_draw(img, outl, fill=0)
    d = ImageDraw.Draw(img)
    for dr in b.GetDrawings():  # edge clearance band
        if dr.GetLayer() == pcbnew.Edge_Cuts:
            poly_draw(img, item_poly(dr, pcbnew.Edge_Cuts, EDGE_GAP))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(mask) or p.IsOnLayer(cu) and p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                poly_draw(img, item_poly(p, cu, PAD_GAP + max(0, p.GetSolderMaskExpansion(mask)) / 1e6))
            if p.HasHole():
                c = xy(p.GetPosition()); r = p.GetDrillSize().x / 2e6 + PAD_GAP
                d.ellipse([g(c[0] - r, c[1] - r), g(c[0] + r, c[1] + r)], fill=1)
        for it in list(f.GraphicalItems()):
            if it.GetLayer() == silk and it.GetClass() == 'PCB_SHAPE':
                poly_draw(img, item_poly(it, silk, SILK_GAP))
    for dr in b.GetDrawings():
        if dr.GetLayer() == silk:
            poly_draw(img, item_poly(dr, silk, SILK_GAP))
    for t in b.GetTracks():  # untented via openings only
        if t.GetClass() == 'PCB_VIA' and not b.GetDesignSettings().m_TentViasFront:
            poly_draw(img, item_poly(t, cu, PAD_GAP))
    return arr(img)


def text_obj(parent, s, layer, pos, ang, h=TXT, th=STK, mirror=False):
    t = pcbnew.PCB_TEXT(parent)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h)))
    t.SetTextThickness(MM(th))
    t.SetTextAngleDegrees(ang)
    t.SetMirrored(mirror)
    t.SetPosition(P(*pos))
    return t


def ext(s, ang, h=TXT, th=STK):
    """tight stroke extents of text centred at origin: (l, t, r, b)"""
    t = text_obj(b, s, pcbnew.F_SilkS, (0, 0), ang, h, th)
    KEEP.append(t)
    ps = pcbnew.SHAPE_POLY_SET()
    t.TransformShapeToPolygon(ps, pcbnew.F_SilkS, 0, MM(0.005), pcbnew.ERROR_OUTSIDE)
    bb = ps.BBox()
    return tuple(v / 1e6 - 100.0 for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))  # text sat at P(0,0)


def rect_idx(cx, cy, e, m=0.0):
    i0, j0 = g(cx + e[0] - m, cy + e[1] - m)
    i1, j1 = g(cx + e[2] + m, cy + e[3] + m)
    return int(np.floor(j0)), int(np.ceil(j1)), int(np.floor(i0)), int(np.ceil(i1))


def free(A, cx, cy, e):
    r0, r1, c0, c1 = rect_idx(cx, cy, e)
    if r0 < 0 or c0 < 0 or r1 > NY or c1 > NX:
        return False
    return not A[r0:r1, c0:c1].any()


def mark(A, cx, cy, e, m):
    r0, r1, c0, c1 = rect_idx(cx, cy, e, m)
    A[max(r0, 0):r1, max(c0, 0):c1] = True


def crt_box(f):
    if f.GetReference() == 'U1':  # courtyard includes the antenna keep-out; use the module body
        xs, ys = [], []
        for it in f.GraphicalItems():
            if it.GetLayer() == pcbnew.F_Fab and it.GetClass() == 'PCB_SHAPE':
                bb = it.GetBoundingBox()
                o, e = xy(bb.GetOrigin()), xy(bb.GetEnd())
                xs += [o[0], e[0]]; ys += [o[1], e[1]]
        return min(xs), min(ys), max(xs), max(ys)
    ps = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = ps.BBox()
    o, e = xy(bb.GetOrigin()), xy(bb.GetEnd())
    return o[0], o[1], e[0], e[1]


def body_box(f):
    """F.Fab outline box (the part body); falls back to the courtyard"""
    xs, ys = [], []
    for it in f.GraphicalItems():
        if it.GetLayer() == pcbnew.F_Fab and it.GetClass() == 'PCB_SHAPE':
            bb = it.GetBoundingBox()
            o, e = xy(bb.GetOrigin()), xy(bb.GetEnd())
            xs += [o[0], e[0]]; ys += [o[1], e[1]]
    if not xs:
        return crt_box(f)
    return min(xs), min(ys), max(xs), max(ys)


def part_box(f):
    x0, y0, x1, y1 = body_box(f)
    for p in f.Pads():
        bb = p.GetBoundingBox()
        o, e = xy(bb.GetOrigin()), xy(bb.GetEnd())
        x0, y0, x1, y1 = min(x0, o[0]), min(y0, o[1]), max(x1, e[0]), max(y1, e[1])
    return x0, y0, x1, y1


def body_raster():
    img = blank()
    d = ImageDraw.Draw(img)
    for f in b.GetFootprints():
        if f.GetLayer() != pcbnew.F_Cu or f.GetReference().startswith(('ASSY', 'FID', 'H')):
            continue
        x0, y0, x1, y1 = body_box(f)
        d.rectangle([g(x0, y0), g(x1, y1)], fill=1)
    return arr(img)


def crt_raster(skip=()):
    img = blank()
    d = ImageDraw.Draw(img)
    for f in b.GetFootprints():
        if f.GetLayer() != pcbnew.F_Cu or f.GetReference().startswith('ASSY') or f.GetReference() in skip:
            continue
        if f.GetReference() == 'U1':
            x0, y0, x1, y1 = crt_box(f)
            d.rectangle([g(x0, y0), g(x1, y1)], fill=1)
        else:
            poly_draw(img, f.GetCourtyard(pcbnew.F_CrtYd))
    return arr(img)


# ---------------------------------------------------------------- fiducials (before silk, they are obstacles)
def copper_raster(clr):
    img = blank()
    d = ImageDraw.Draw(img)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' or t.GetLayer() == pcbnew.F_Cu:
            poly_draw(img, item_poly(t, pcbnew.F_Cu, clr))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.F_Cu) or p.HasHole():
                poly_draw(img, item_poly(p, pcbnew.F_Cu, clr))
    for dr in b.GetDrawings():
        if dr.GetLayer() == pcbnew.Edge_Cuts:
            poly_draw(img, item_poly(dr, pcbnew.Edge_Cuts, 2.0))
    return arr(img)


FID_OK = []
if not any(f.GetReference().startswith('FID') for f in b.GetFootprints()):
    cop = copper_raster(0.0)
    oth = crt_raster() | side_obstacles('F')
    # fiducial needs a 1.25 mm radius disc free of copper (2 mm mask + margin) and of courtyards/silk
    yy, xx = np.mgrid[0:NY, 0:NX]
    corners = {'TL': (0, 0), 'TR': (40, 0), 'BL': (0, 44.5), 'BR': (40, 44.5)}
    k = int(np.ceil(1.25 / RES))
    rr = np.add.outer(np.arange(-k, k + 1) ** 2, np.arange(-k, k + 1) ** 2)
    disk_cu = rr <= (1.1 / RES) ** 2   # 2 mm mask opening + 0.1 mm: no foreign copper inside
    disk_ot = rr <= (1.25 / RES) ** 2  # fiducial courtyard vs other courtyards, pads, silk, edge band
    cand = {}
    for name, (cx, cy) in corners.items():
        best = None
        for y in np.arange(1.5, 43.1, 0.1):
            for x in np.arange(1.5, 38.6, 0.1):
                dist = abs(x - cx) + abs(y - cy)
                if dist > 14 or best and dist >= best[0]:
                    continue
                j, i = (int(round((x - X0) / RES)), int(round((y - Y0) / RES)))
                if not (cop[i - k:i + k + 1, j - k:j + k + 1] & disk_cu).any() and not (oth[i - k:i + k + 1, j - k:j + k + 1] & disk_ot).any():
                    best = (dist, x, y)
        cand[name] = best
    print('fiducial candidates', cand)
    ok = [(n, c) for n, c in cand.items() if c]
    if len(ok) >= 3:
        ok.sort(key=lambda q: q[1][0])
        lib = '/usr/share/kicad/footprints/Fiducial.pretty'
        for n, (_, x, y) in ok[:3]:
            fp = pcbnew.FootprintLoad(lib, 'Fiducial_1mm_Mask2mm')
            ref = 'FID%d' % (len(FID_OK) + 1)
            fp.SetReference(ref)
            fp.SetValue('Fiducial')
            fp.SetPosition(P(round(x, 2), round(y, 2)))
            fp.SetExcludedFromBOM(True)
            fp.SetExcludedFromPosFiles(True)
            fp.SetBoardOnly(True)
            fp.SetDNP(True)
            fp.Reference().SetVisible(False)
            fp.Reference().SetLayer(pcbnew.F_Fab)
            b.Add(fp)
            KEEP.append(fp)
            FID_OK.append((ref, n, round(x, 2), round(y, 2)))
    print('fiducials', FID_OK)

# ---------------------------------------------------------------- F.Silk refs
OBS = side_obstacles('F')
CRT = body_raster()
NET = {f.GetReference(): f.Pads()[0].GetNetname().lstrip('/') for f in b.GetFootprints() if f.GetReference().startswith('TP')}
LABEL = {'J1': 'USB-C', 'J3': 'EPD', 'SW1': 'WAKE', 'U2': 'RH/T'}
for k_, v in NET.items():
    LABEL[k_] = v
SKIP = {'H1', 'H2', 'J4'}  # mounting holes already labelled; J4 is on B

fixed, todo = [], []
for f in b.GetFootprints():
    ref = f.GetReference()
    if f.GetLayer() != pcbnew.F_Cu or ref.startswith(('ASSY', 'FID')):
        continue
    r = f.Reference()
    if ref in SKIP:
        if r.IsVisible() and r.GetLayer() == pcbnew.F_SilkS:
            a = r.GetTextAngleDegrees() % 180
            r.SetTextAngleDegrees(a)
            fixed.append(r)
        continue
    if ref not in LABEL and r.IsVisible() and r.GetLayer() == pcbnew.F_SilkS and pcbnew.ToMM(r.GetTextHeight()) >= 1.0:
        a = r.GetTextAngleDegrees() % 180  # 180 -> 0, 270 -> 90: same box, reads upright
        r.SetTextAngleDegrees(a)
        fixed.append(r)
    else:
        todo.append(f)

TXTOBS = np.zeros_like(OBS)
for r in fixed:
    e = ext(r.GetShownText(True), r.GetTextAngleDegrees())
    c = xy(r.GetPosition())
    mark(TXTOBS, c[0], c[1], e, TXT_GAP)
for dr in b.GetDrawings():
    if dr.GetLayer() == pcbnew.F_SilkS and dr.GetClass() == 'PCB_TEXT':
        pass  # already in OBS via item_poly


ISLAND = (11.75, 1.75, 15.9, 5.65)
BOXES = {f.GetReference(): (ISLAND if f.GetReference() == 'U2' else part_box(f)) for f in b.GetFootprints()
         if f.GetLayer() == pcbnew.F_Cu and not f.GetReference().startswith(('ASSY', 'FID'))}


def bdist(bx, x, y):
    return np.hypot(max(bx[0] - x, 0, x - bx[2]), max(bx[1] - y, 0, y - bx[3]))


def candidates(f, strs):
    ref = f.GetReference()
    x0, y0, x1, y1 = BOXES[ref]
    out = []
    pref = 90 if round(f.GetOrientationDegrees()) % 180 == 90 else 0
    for si, s in enumerate(strs):
        for ang in (0, 90):
            e = ext(s, ang)
            w, h = e[2] - e[0], e[3] - e[1]
            for gap in np.arange(0.1, 2.2, 0.1):
                sides = [('T', (x0 - w / 2, x1 + w / 2), y0 - gap - e[3]), ('B', (x0 - w / 2, x1 + w / 2), y1 + gap - e[1]),
                         ('L', (y0 - h / 2, y1 + h / 2), x0 - gap - e[2]), ('R', (y0 - h / 2, y1 + h / 2), x1 + gap - e[0])]
                for sd, (lo, hi), fix in sides:
                    mid = ((x0 + x1) / 2 if sd in 'TB' else (y0 + y1) / 2)
                    for v in np.arange(lo, hi + 1e-6, 0.1):
                        cx, cy = (v, fix) if sd in 'TB' else (fix, v)
                        if sd in 'TB':
                            cx -= (e[0] + e[2]) / 2
                        else:
                            cy -= (e[1] + e[3]) / 2
                        if gap > 0.5:  # far labels must still be closest to their own part
                            tx, ty = cx + (e[0] + e[2]) / 2, cy + (e[1] + e[3]) / 2
                            own = bdist(BOXES[ref], tx, ty)
                            if any(bdist(bx, tx, ty) < own - 0.1 for r_, bx in BOXES.items() if r_ != ref):
                                continue
                        score = gap + 0.25 * abs(v - mid) + (0.6 if ang != pref else 0) + 2.0 * si
                        out.append((score, cx, cy, ang, e, s))
    out.sort(key=lambda q: q[0])
    return out


def valid(c, A):
    return free(A, c[1], c[2], c[4])


ALT = {'TP6': ['TP6 SPARE_IO14', 'TP6\nSPARE_IO14', 'TP6 IO14', 'TP6'], 'U2': ['U2 RH/T', 'U2\nRH/T']}


def strs(f):
    r_ = f.GetReference()
    if r_ in ALT:
        return ALT[r_]
    if r_ in LABEL:
        return [r_ + ' ' + LABEL[r_], r_ + '\n' + LABEL[r_], r_]  # bare ref as last resort
    return [r_]


import random
A0 = OBS | CRT | TXTOBS
FORCE = {'U2': (13.8, 7.95, 0, 'U2 RH/T')}  # just below the bridge (the island has no room); DRC-checked
CAND = {}
for f in todo:
    r_ = f.GetReference()
    if r_ in FORCE:
        x, y, a_, s_ = FORCE[r_]
        e = ext(s_, a_)
        CAND[r_] = [(0, x - (e[0] + e[2]) / 2, y - (e[1] + e[3]) / 2, a_, e, s_)]
    else:
        CAND[r_] = [c for c in candidates(f, strs(f)) if valid(c, A0)]
FOOT = {f.GetReference(): f for f in todo}


def rect(c, m=0.0):
    e = c[4]
    return (c[1] + e[0] - m, c[2] + e[1] - m, c[1] + e[2] + m, c[2] + e[3] + m)


def hit(r1, r2):
    return r1[0] < r2[2] and r2[0] < r1[2] and r1[1] < r2[3] and r2[1] < r1[3]


def greedy(rng):
    rects, got = [], {}
    pend = set(CAND)
    while pend:
        opts = {k_: [c for c in CAND[k_] if not any(hit(rect(c), r) for r in rects)] for k_ in pend}
        live = [k_ for k_ in pend if opts[k_]]
        if not live:
            break
        k_ = min(live, key=lambda q: (len(opts[q]) + (rng.random() * 3 if rng else 0)))
        pend.discard(k_)
        o = opts[k_]
        c = o[0] if rng is None else o[min(int(rng.random() ** 3 * 4), len(o) - 1)]
        got[k_] = c
        rects.append(rect(c, TXT_GAP))
    return got


best = greedy(None)
for t_ in range(20):
    gotr = greedy(random.Random(t_))
    if (len(gotr), -sum(c[0] for c in gotr.values())) > (len(best), -sum(c[0] for c in best.values())):
        best = gotr
placed = {k_: (FOOT[k_], c[5].replace(k_, '${REFERENCE}', 1) if c[5] != k_ else '${REFERENCE}', c) for k_, c in best.items()}
failed = sorted(set(CAND) - set(best))

for k_, (f, s, c) in placed.items():
    r = f.Reference()
    if s == '${REFERENCE}':
        t = r
    else:
        r.SetVisible(False)
        t = pcbnew.PCB_TEXT(f)
        t.SetText(s)
        f.Add(t)
        KEEP.append(t)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetVisible(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(TXT), MM(TXT)))
    t.SetTextThickness(MM(STK))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetTextAngleDegrees(c[3])
    t.SetPosition(P(round(c[1], 3), round(c[2], 3)))
for k_ in failed:
    r = b.FindFootprintByReference(k_).Reference()
    r.SetLayer(pcbnew.F_Fab)
    r.SetVisible(True)
print('placed', len(placed), 'failed', sorted(failed))
if len(sys.argv) > 2:  # debug raster: obstacles grey, bodies dark, texts white, failed part boxes red
    im = np.zeros((NY, NX, 3), np.uint8)
    im[OBS] = (90, 90, 90); im[CRT] = (40, 40, 140); im[TXTOBS] = (230, 230, 230)
    dimg = Image.fromarray(im); dd = ImageDraw.Draw(dimg)
    for k_ in failed:
        x0, y0, x1, y1 = part_box(b.FindFootprintByReference(k_))
        dd.rectangle([g(x0, y0), g(x1, y1)], outline=(255, 0, 0)); dd.text(g(x0, y1), k_, fill=(255, 80, 80))
    dimg.save(sys.argv[2])

# ---------------------------------------------------------------- B.Silk
for dr in list(b.GetDrawings()):  # old one-line B mark becomes the title block
    if dr.GetLayer() == pcbnew.B_SilkS and dr.GetClass() == 'PCB_TEXT' and dr.GetText() == 'ull-pocket r0.5':
        b.Remove(dr)
        KEEP.append(dr)
for dr in list(b.GetDrawings()):  # stale note from the tab layout
    if dr.GetClass() == 'PCB_TEXT' and dr.GetText().startswith('SHT31 tab'):
        b.Remove(dr)
        KEEP.append(dr)


def btext(s, pos, h, th, ang=0, bold=False):
    t = text_obj(b, s, pcbnew.B_SilkS, pos, ang, h, th, mirror=True)
    t.SetBold(bold)
    b.Add(t)
    KEEP.append(t)
    return t


j4 = b.FindFootprintByReference('J4')
SIG = {'+3V3': '3V3', 'GND': 'GND', '/EN': 'EN', '/BOOT': 'BOOT', '/TXD0': 'TX', '/RXD0': 'RX'}
for p in j4.Pads():
    x, y = xy(p.GetPosition())
    t = pcbnew.PCB_TEXT(j4)
    t.SetText(SIG[p.GetNetname()])
    t.SetLayer(pcbnew.B_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    t.SetTextThickness(MM(0.15))
    t.SetMirrored(True)
    t.SetTextAngleDegrees(0)
    dx = {'GND': -0.45, 'BOOT': 0.3, 'RX': 0.3}.get(t.GetText(), 0) if y > 2 else 0  # bottom row: GND + BOOT are wider than the pitch
    t.SetPosition(P(x + dx, y + 1.27))  # every label sits just below its pad
    j4.Add(t)
    KEEP.append(t)

btext('ULL-POCKET', (20.6, 15.5), 3.0, 0.5, bold=True)
btext('ESP32-C6 pocket environment meter', (20.6, 19.0), 1.2, 0.18)
btext('rev 0.5  2026-10', (20.6, 21.2), 1.2, 0.18)
btext('LiPo 3.7 V 1S', (5.5, 5.0), 0.8, 0.15)  # behind J2, the battery connector
btext('mind polarity', (5.5, 6.2), 0.8, 0.15)

# J2: the ref would sit flush against the existing "BAT" label; merge them into one "J2 BAT" label
j2 = b.FindFootprintByReference('J2')
for dr in b.GetDrawings():
    if dr.GetClass() == 'PCB_TEXT' and dr.GetLayer() == pcbnew.F_SilkS and dr.GetText() == 'BAT':
        dr.SetText('J2 BAT')
        dr.SetPosition(P(5.4, 0.95))
        j2.Reference().SetVisible(False)
b.Save(FN)
print('saved')
