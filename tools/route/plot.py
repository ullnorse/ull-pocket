"""plot.py board.kicad_pcb out.png x0 y0 x1 y1 [scale] [layers=F,B,1,2] [labels=1]
Board coords (origin at KiCad 100,100). Pads labelled with net short names."""
import sys, subprocess, html
import pcbnew
from rt import xy, O

fn, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
S = float(sys.argv[7]) if len(sys.argv) > 7 else 40
LS = sys.argv[8].split(",") if len(sys.argv) > 8 else ["F", "B", "2", "1"]
LBL = (sys.argv[9] != "0") if len(sys.argv) > 9 else True
b = pcbnew.LoadBoard(fn)
COL = {"F": "#d03030", "B": "#3060e0", "1": "#30a030", "2": "#c0a020"}
LID = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "1": pcbnew.In1_Cu, "2": pcbnew.In2_Cu}
W, H = (x1 - x0) * S, (y1 - y0) * S
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
     f'<rect width="{W}" height="{H}" fill="#101010"/>']


def T(x, y):
    return ((x - x0) * S, (y - y0) * S)


def short(n):
    n = n.replace("Net-(", "").replace(")", "").lstrip("/")
    return n[:9]


def poly(sh, col, op, stroke="none"):
    for i in range(sh.OutlineCount()):
        ol = sh.Outline(i)
        pts = " ".join("%.1f,%.1f" % T(*xy(ol.CPoint(j))) for j in range(ol.PointCount()))
        o.append(f'<polygon points="{pts}" fill="{col}" fill-opacity="{op}" stroke="{stroke}" stroke-width="1"/>')


# zones fill
for z in b.Zones():
    if z.GetIsRuleArea():
        for L in LS:
            if z.IsOnLayer(LID[L]):
                poly(z.Outline(), "#ff00ff", 0.06, "#ff00ff")
                break
        continue
    for L in LS[::-1]:
        if z.IsOnLayer(LID[L]) and z.IsFilled():
            poly(z.GetFilledPolysList(LID[L]), COL[L], 0.18)
# edge
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        a, c = T(*xy(d.GetStart())), T(*xy(d.GetEnd()))
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{c[0]:.1f}" y2="{c[1]:.1f}" stroke="#e0e000" stroke-width="2"/>')
# courtyards
for f in b.GetFootprints():
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        poly(cy, "none", 0, "#606060")
# tracks (B first, then F on top)
order = {"2": 0, "1": 1, "B": 2, "F": 3}
tr = [t for t in b.GetTracks()]
for L in sorted(LS, key=lambda l: order[l]):
    for t in tr:
        if t.GetClass() == "PCB_TRACK" and t.GetLayer() == LID[L]:
            a, c = T(*xy(t.GetStart())), T(*xy(t.GetEnd()))
            o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{c[0]:.1f}" y2="{c[1]:.1f}" stroke="{COL[L]}" '
                     f'stroke-opacity="0.85" stroke-width="{t.GetWidth()/1e6*S:.1f}" stroke-linecap="round"/>')
# pads
for f in b.GetFootprints():
    for p in f.Pads():
        sh = p.GetEffectivePolygon(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
        poly(sh, "#ff8080" if p.IsOnLayer(pcbnew.F_Cu) else "#8080ff", 0.55)
        if p.GetDrillSize().x:
            c = T(*xy(p.GetPosition()))
            o.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{p.GetDrillSize().x/2e6*S:.1f}" fill="#000"/>')
# vias
for t in tr:
    if t.GetClass() == "PCB_VIA":
        c = T(*xy(t.GetPosition()))
        o.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{t.GetWidth(pcbnew.F_Cu)/2e6*S:.1f}" fill="#c0c0c0"/>'
                 f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{t.GetDrillValue()/2e6*S:.1f}" fill="#000"/>')
# labels
if LBL:
    fs = max(7, S * 0.22)
    for f in b.GetFootprints():
        c = T(*xy(f.GetPosition()))
        o.append(f'<text x="{c[0]:.1f}" y="{c[1]:.1f}" fill="#ffff80" font-size="{fs*1.3:.0f}" font-family="sans" '
                 f'text-anchor="middle" opacity="0.8">{f.GetReference()}</text>')
        for p in f.Pads():
            if not p.GetNetname():
                continue
            c = T(*xy(p.GetPosition()))
            o.append(f'<text x="{c[0]:.1f}" y="{c[1]+fs/3:.1f}" fill="#ffffff" font-size="{fs:.0f}" font-family="sans" '
                     f'text-anchor="middle">{html.escape(short(p.GetNetname()))}</text>')
# grid ticks every 1 mm
for gx in range(int(x0), int(x1) + 1):
    a = T(gx, y0)
    o.append(f'<text x="{a[0]:.1f}" y="10" fill="#888" font-size="9">{gx}</text>')
for gy in range(int(y0), int(y1) + 1):
    a = T(x0, gy)
    o.append(f'<text x="1" y="{a[1]:.1f}" fill="#888" font-size="9">{gy}</text>')
o.append("</svg>")
open(out + ".svg", "w").write("\n".join(o))
subprocess.run(["rsvg-convert", out + ".svg", "-o", out], check=True)
