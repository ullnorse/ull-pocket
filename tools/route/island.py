import sys
from rt import *
r=R(sys.argv[1]); b=r.b
vias=[t.GetPosition() for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
for z in b.Zones():
    if z.IsOnCopperLayer() and not z.GetIsRuleArea() and z.GetNetname()=='GND':
        for L in z.GetLayerSet().Seq():
            fp=z.GetFilledPolysList(L)
            for i in range(fp.OutlineCount()):
                if not any(fp.Contains(v, i) for v in vias):
                    bb=fp.Outline(i).BBox(); print(z.GetZoneName(), 'island', [round(v,2) for v in xy(bb.GetOrigin())+xy(bb.GetEnd())])
