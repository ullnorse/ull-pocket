"""Plot a board region: tracks by layer, vias, pads with net names, courtyards, edge.
usage: view.py x0 y0 x1 y1 out.png [board] [px_per_mm]"""
import sys
from PIL import Image, ImageDraw, ImageFont
import pcbnew

x0, y0, x1, y1 = map(float, sys.argv[1:5])
out = sys.argv[5]
b = pcbnew.LoadBoard(sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "-" else "ull-pocket.kicad_pcb")
S = float(sys.argv[7]) if len(sys.argv) > 7 else 60
mm = pcbnew.ToMM
COL = {pcbnew.F_Cu: (220, 30, 30, 170), pcbnew.B_Cu: (30, 30, 220, 150), pcbnew.In1_Cu: (30, 160, 30, 150), pcbnew.In2_Cu: (230, 140, 0, 150)}
W, H = int((x1 - x0) * S), int((y1 - y0) * S)
im = Image.new("RGBA", (W, H), "white")
d = ImageDraw.Draw(im, "RGBA")
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 10)
    big = ImageFont.truetype("DejaVuSans-Bold.ttf", 13)
except OSError:
    font = big = ImageFont.load_default()


def P(x, y):
    return ((x - x0) * S, (y - y0) * S)


def poly(shape, **kw):
    for i in range(shape.OutlineCount()):
        o = shape.Outline(i)
        pts = [P(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())]
        if len(pts) > 2:
            d.polygon(pts, **kw)


# grid every 0.5 mm, labelled every 1 mm
g = x0 - x0 % 0.5
while g <= x1:
    d.line([P(g, y0), P(g, y1)], fill=(235, 235, 235) if g % 1 else (210, 210, 210))
    if g % 1 == 0:
        d.text((P(g, y0)[0] + 1, 1), "%g" % g, fill="gray", font=font)
    g += 0.5
g = y0 - y0 % 0.5
while g <= y1:
    d.line([P(x0, g), P(x1, g)], fill=(235, 235, 235) if g % 1 else (210, 210, 210))
    if g % 1 == 0:
        d.text((1, P(x0, g)[1] + 1), "%g" % g, fill="gray", font=font)
    g += 0.5
for z in b.Zones():
    if z.GetIsRuleArea():
        poly(z.Outline(), outline=(150, 150, 150))
for layer in (pcbnew.In2_Cu, pcbnew.In1_Cu, pcbnew.B_Cu, pcbnew.F_Cu):
    for t in b.GetTracks():
        if t.GetClass() != "PCB_VIA" and t.GetLayer() == layer:
            s, e = t.GetStart(), t.GetEnd()
            w = max(1, int(mm(t.GetWidth()) * S))
            a, c = P(mm(s.x), mm(s.y)), P(mm(e.x), mm(e.y))
            d.line([a, c], fill=COL[layer], width=w)
            for q in (a, c):
                d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=COL[layer])
for f in b.Footprints():
    poly(f.GetCourtyard(pcbnew.F_CrtYd), outline=(200, 0, 200))
    for p in f.Pads():
        lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        poly(p.GetEffectivePolygon(lay), fill=(232, 192, 96, 200), outline="black")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        x, y = P(mm(t.GetPosition().x), mm(t.GetPosition().y))
        r, h = mm(t.GetWidth(pcbnew.F_Cu)) / 2 * S, mm(t.GetDrillValue()) / 2 * S
        d.ellipse([x - r, y - r, x + r, y + r], fill=(170, 170, 170), outline="black")
        d.ellipse([x - h, y - h, x + h, y + h], fill="white")
        d.text((x + r, y - r), t.GetNetname().replace("/", "")[:8], fill=(90, 90, 90), font=font)
for f in b.Footprints():
    for p in f.Pads():
        x, y = P(mm(p.GetPosition().x), mm(p.GetPosition().y))
        n = p.GetNetname().replace("/", "").replace("unconnected-", "nc")[:9]
        d.text((x, y), "%s %s" % (p.GetNumber(), n), fill="black", font=font, anchor="mm")
    c = f.GetPosition()
    x, y = P(mm(c.x), mm(c.y))
    d.text((x, y - 12), f.GetReference(), fill=(160, 0, 160), font=big, anchor="mm")
for e in b.GetDrawings():
    if e.GetLayer() == pcbnew.Edge_Cuts:
        s, t = e.GetStart(), e.GetEnd()
        d.line([P(mm(s.x), mm(s.y)), P(mm(t.x), mm(t.y))], fill="black", width=2)
im.save(out)
