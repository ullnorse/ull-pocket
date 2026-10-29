"""Zones (GND on all layers, +3V3 pour on In2 west) and fill. in -> out"""
import sys
import pcbnew
from rt import *
r = R(sys.argv[1]); b = r.b
cx, cy = xy(b.FindFootprintByReference('U3').GetPosition())
# ---------------------------------------------------------------- zones
def zone(layer, net, pts, name, prio=0):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(r.net(net))
    z.SetZoneName(name)
    ol = pcbnew.SHAPE_POLY_SET()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x + O), MM(y + O))
    z.SetOutline(ol)
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.15))
    z.SetThermalReliefGap(MM(0.25))
    z.SetThermalReliefSpokeWidth(MM(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
    return z

for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z)
full = [(0.2, 0.2), (39.8, 0.2), (39.8, 44.3), (0.2, 44.3)]
zone(pcbnew.F_Cu, 'GND', full, 'GND_F')
zone(pcbnew.In1_Cu, 'GND', full, 'GND_In1')
zone(pcbnew.B_Cu, 'GND', full, 'GND_B')
# In2: +3V3 pour over the west half (keeps In2 GND under the USB pair and the east side)
# In2 is the +3V3 plane; GND is kept on In2 only under the USB pair (B.Cu) and its hops under J1
zone(pcbnew.In2_Cu, '+3V3', full, 'P3V3_In2', prio=1)
corr = [(19.35, 31.6), (19.35, 13.2), (20.8, 11.75), (30.6, 11.75), (31.1, 10.95), (33.25, 10.95), (33.25, 12.95), (21.45, 12.95), (20.85, 13.55), (20.85, 31.6)]
zone(pcbnew.In2_Cu, 'GND', corr, 'GND_In2_usb', prio=2)
zone(pcbnew.In2_Cu, 'GND', [(18.5, 37.9), (21.8, 37.9), (21.8, 40.3), (18.5, 40.3)], 'GND_In2_hops', prio=2)

# BMP585 no-mask window: no pour and no vias on F inside +-1.75 mm (only the pads' own stubs cross it)
W = 1.75
ra = pcbnew.ZONE(b); ra.SetIsRuleArea(True); ra.SetLayer(pcbnew.F_Cu); ra.SetZoneName('BMP585_window')
ra.SetDoNotAllowCopperPour(True); ra.SetDoNotAllowVias(True); ra.SetDoNotAllowTracks(False)
ra.SetDoNotAllowPads(False); ra.SetDoNotAllowFootprints(False)
ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
for x, y in ((cx - W, cy - W), (cx + W, cy - W), (cx + W, cy + W), (cx - W, cy + W)):
    ol.Append(MM(x + O), MM(y + O))
ra.SetOutline(ol); b.Add(ra)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
r.save(sys.argv[2])
