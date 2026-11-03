"""No-pour areas behind the panel tabs.

KiKit drills 0.5 mm mouse bites 0.2 mm inside the board edge (tools/panelize.sh),
so each hole reaches 0.45 mm in; pours stop 0.3 mm from the edge. Without these
areas the holes cut into GND / +3V3 copper. Tracks and vias stay allowed.
Tab centres must match the annotations in tools/panelize.sh.
"""
import sys, pcbnew
F = pcbnew.FromMM
path = sys.argv[1] if len(sys.argv) > 1 else "ull-pocket.kicad_pcb"
DEPTH, HALF = 0.75, 2.6          # mm in from the edge; half length (tab holes span +-2.0)
TABS = [("L", 114.5), ("L", 141.5), ("R", 104.0), ("R", 141.5)]
b = pcbnew.LoadBoard(path)
for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName().startswith("tab_keepout"):
        b.Delete(z)
e = b.GetBoardEdgesBoundingBox()
x0, x1 = pcbnew.ToMM(e.GetLeft()) + 0.025, pcbnew.ToMM(e.GetRight()) - 0.025
layers = pcbnew.LSET()
for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    layers.AddLayer(l)
for i, (side, y) in enumerate(TABS):
    xa, xb = (x0, x0 + DEPTH) if side == "L" else (x1 - DEPTH, x1)
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True); z.SetZoneName(f"tab_keepout_{i}"); z.SetLayerSet(layers)
    z.SetDoNotAllowZoneFills(True)
    for f in (z.SetDoNotAllowTracks, z.SetDoNotAllowVias, z.SetDoNotAllowPads, z.SetDoNotAllowFootprints):
        f(False)
    o = z.Outline(); o.NewOutline()
    for x, yy in ((xa, y - HALF), (xb, y - HALF), (xb, y + HALF), (xa, y + HALF)):
        o.Append(F(x), F(yy))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(path)
print("added", len(TABS), "tab keepouts, zones refilled")
