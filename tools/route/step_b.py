# placement tweaks for routing (boost loop, J3 cap fan-in, EPD pull-ups)
from rt import *
r = R('work.kicad_pcb'); b = r.b
def mv(ref, x, y, rot=None):
    f = b.FindFootprintByReference(ref)
    f.SetPosition(P(x, y))
    if rot is not None: f.SetOrientationDegrees(rot)
mv('Q1', 24.5, 14.9, 270)
mv('R20', 23.35, 11.85, 90)
mv('R19', 24.95, 11.85, 90)
for ref, y in (('C21', 17.25), ('C22', 20.4), ('C23', 22.0), ('C24', 23.6), ('C25', 25.2), ('C26', 26.8)):
    mv(ref, 24.6, y)
mv('R25', 28.6, 28.75, 0)
mv('R26', 30.6, 28.75, 0)
mv('U8', 20.0, 33.4, 270)          # D- top-left, GND top-middle, D+ top-right; VBUS bottom-middle
mv('R1', 17.7, 34.3, 90)           # CC pull-downs between VBUS and the D lines
mv('R2', 22.3, 34.3, 90)
mv('R4', 31.0, 37.4, 180)          # EN1 pad under U6.6, VBUS pad outward
mv('R10', 33.75, 32.2, 90)
mv('R8', 24.4, 30.6, 180)          # TS pad east, GND west
mv('TH1', 20.0, 29.6, 180)
mv('C8', 23.2, 1.5, 180)
mv('C10', 24.8, 7.8, 180)
mv('R24', 34.6, 12.2, 180)         # IO15 pad under U1.20, +3V3 outward
mv('R16', 36.6, 12.2, 180)         # IO8 pad under U1.22
mv('R25', 38.0, 37.6, 270)         # EPD RST/CS pull-ups fed from the SPI lanes' extension
mv('R26', 39.1, 37.6, 270)
mv('R7', 28.2, 38.0, 270)          # PGOOD pull-up on the PGOOD lane
mv('C16', 36.6, 37.0, -90)         # +3V3 pad up, next to the LDO link
mv('C7', 39.35, 29.0)
mv('TP1', 14.0, 34.3, 0)           # VBUS test pad next to the receptacle
mv('TP2', 35.5, 32.5, 0)           # VSYS test pad on the VSYS trunk
mv('TP6', 13.5, 24.5, 0)           # IO14 test pad next to the PROG pads
mv('R18', 20.6, 10.0, 270)         # I2C pull-ups on the bus next to U4 (+3V3 pad up)
mv('R17', 21.65, 10.0, 270)
mv('C11', 6.6, -3.1, 270)          # SHT31 decoupler: +3V3 pad toward pin 5           # +3V3 pad next to C9 / U1 pin 3
r.save()
for p in ['Q1.1', 'Q1.2', 'Q1.3', 'R20.1', 'R20.2', 'R19.1', 'R19.2', 'R25.1', 'R25.2', 'R26.2']:
    print(p, r.pp(*p.split('.')), r.pad(*p.split('.')).GetNetname())
