"""Report vias inside or within 0.25 mm of any SMD pad (F) and vias in paste windows. usage: vip.py board"""
import sys, pcbnew
from rt import xy
b = pcbnew.LoadBoard(sys.argv[1])
MM = pcbnew.FromMM
vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
THERMAL = {('U6', '17'), ('U1', '49')}
bad = 0; thermal = 0
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or not p.IsOnLayer(pcbnew.F_Cu):
            continue
        sh = p.GetEffectivePolygon(pcbnew.F_Cu)
        for v in vias:
            r = v.GetWidth(pcbnew.F_Cu) // 2
            hit = sh.Collide(pcbnew.SEG(v.GetPosition(), v.GetPosition()), r + MM(0.25 if p.GetNetname() == v.GetNetname() else 0))
            if not hit:
                continue
            key = (f.GetReference(), p.GetNumber())
            inside = sh.Contains(v.GetPosition())
            tag = 'IN-PAD' if inside else 'NEAR(<0.25)'
            if key in THERMAL:
                thermal += 1
                print('thermal', key, tag, tuple(round(c, 3) for c in xy(v.GetPosition())))
            else:
                bad += 1
                print('FAIL', key, p.GetNetname(), tag, tuple(round(c, 3) for c in xy(v.GetPosition())))
# paste windows: any via under paste (incl. thermal pads' paste apertures)
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnLayer(pcbnew.F_Paste):
            continue
        sh = p.GetEffectivePolygon(pcbnew.F_Paste) if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or True else None
        for v in vias:
            if sh.Collide(pcbnew.SEG(v.GetPosition(), v.GetPosition()), v.GetWidth(pcbnew.F_Cu) // 2):
                if (f.GetReference(), p.GetNumber()) in THERMAL and p.GetSize().x < MM(1.0):
                    pass
                print('PASTE', f.GetReference(), p.GetNumber(), tuple(round(c, 3) for c in xy(v.GetPosition())))
                bad += 1
print('summary: violations', bad, 'thermal-pad vias (pad copper, outside paste)', thermal)
