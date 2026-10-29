"""Zones (GND on all layers, +3V3 pour on In2 west) and fill. in -> out"""
import sys
import pcbnew
from rt import *
r = R(sys.argv[1]); b = r.b
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
zone(pcbnew.In2_Cu, 'GND', full, 'GND_In2')
zone(pcbnew.B_Cu, 'GND', full, 'GND_B')
# In2: +3V3 pour over the west half (keeps In2 GND under the USB pair and the east side)
v3 = [(0.2, 0.2), (25.6, 0.2), (25.6, 9.8), (19.2, 9.8), (19.2, 31.6), (14.8, 31.6), (14.8, 44.3), (0.2, 44.3)]
zone(pcbnew.In2_Cu, '+3V3', v3, 'P3V3_In2', prio=1)


pcbnew.ZONE_FILLER(b).Fill(b.Zones())
r.save(sys.argv[2])
