# review round 1 placement changes (idempotent, applied to placed.kicad_pcb)
from rt import *
r = R('placed.kicad_pcb'); b = r.b
def mv(ref, x, y, rot=None):
    f = b.FindFootprintByReference(ref)
    f.SetPosition(P(x, y))
    if rot is not None: f.SetOrientationDegrees(rot)
mv('J1', 20.0, 41.45)              # USB-C mouth 0.6 mm past the bottom edge
mv('J4', 12.63, 1.9, 0)            # PROG pogo pads in the top-left strip, next to U1
mv('TP6', 17.6, 13.3, 0)           # IO14 test pad between U3 and L1
mv('R18', 20.6, 10.0, 270)
mv('R17', 21.65, 10.0, 270)
mv('R25', 24.6, 18.55, 0)          # EPD RST/CS pull-ups beside J3 pins 10/12
mv('R26', 24.6, 19.6, 0)
for ref, y in (('C22', 20.9), ('C23', 22.5), ('C24', 24.1), ('C25', 25.7), ('C26', 27.3)):
    mv(ref, 24.6, y)
# U6 exposed pad: 4 smaller paste windows leaving a 0.4 mm cross for the thermal via
f = b.FindFootprintByReference('U6'); c = xy(f.GetPosition())
k = 0
for p in f.Pads():
    if p.GetNumber() == '' and not p.IsOnLayer(pcbnew.F_Cu):
        dx = -0.48 if xy(p.GetPosition())[0] < c[0] else 0.48
        dy = -0.48 if xy(p.GetPosition())[1] < c[1] else 0.48
        p.SetSize(pcbnew.VECTOR2I(MM(0.55), MM(0.55)))
        p.SetPosition(P(c[0] + dx, c[1] + dy)); k += 1
print('U6 paste windows', k)
f.SetFPIDAsString('ull-pocket:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm')
r.save()
