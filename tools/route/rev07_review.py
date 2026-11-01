"""rev 0.7 review fixes: SW1-SW3 shell tabs (pads 3/4) off GND; drop the GND vias in SW3's tab pads."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.FromMM
kill = []
for f in b.GetFootprints():
    if f.GetReference() not in ('SW1', 'SW2', 'SW3'): continue
    for p in f.Pads():
        if p.GetNumber() not in ('3', '4'): continue
        for t in b.GetTracks():
            if t.GetNetname() != 'GND': continue
            if t.GetClass() == 'PCB_VIA':
                if p.HitTest(t.GetPosition(), mm(0.35)): kill.append(t)
            elif p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()):
                kill.append(t)
        p.SetNetCode(0)
uniq = list({t.m_Uuid.AsString(): t for t in kill}.values())
for t in uniq: b.Delete(t)
print('removed', len(uniq))
for f in b.GetFootprints():
    if f.GetReference() in ('SW1', 'SW2', 'SW3'):
        f.SetField('Description', 'Side-actuated SMD tactile switch 4.7x1.9 mm, SPST-NO; shell tabs 3/4 have no pins (left unconnected)')
b.Save(sys.argv[2])
# second pass on the output: GND stitching vias at x 100.75, y 131.4 / 133.0 sit too close to SW3's floating pad 3
if len(sys.argv) > 3:
    b = pcbnew.LoadBoard(sys.argv[2])
    for t in list(b.GetTracks()):
        if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and abs(t.GetPosition().x - mm(100.75)) < 20000 and min(abs(t.GetPosition().y - mm(131.4)), abs(t.GetPosition().y - mm(133.0))) < 20000:
            b.Delete(t)
    b.Save(sys.argv[2])
# The 0.15 mm stroke on UP/OK/DN and the J1 label was a text edit to the board file. (U3 keeps its single
# mask opening over the body: BMP585 datasheet 9.3.3 asks for no solder mask under the sensor.)
