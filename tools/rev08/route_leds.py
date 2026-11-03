"""Rev 0.8 RGB user LED: D6 MHS110FRGBCT at the bottom edge, R22/R33/R32 above it, LED_G and LED_R
on B.Cu beside LED_B from U1 pads 20/22. Also two sensor-area fixups. Run after route_sensors.py."""
import pcbnew
from pcbnew import FromMM as I, ToMM as mm
from route_sensors_lib import Board

bd = Board("ull-pocket.kicad_pcb")
track, via, drop_track, drop_via, fp = bd.track, bd.via, bd.drop_track, bd.drop_via, bd.fp
F, B = pcbnew.F_Cu, pcbnew.B_Cu

# ---- sensor fixups: C14/R27 +3V3 back onto the plane, drop the BMP585's spare +3V3 via
via("+3V3", 121.38, 104.324)
track("+3V3", [(120.48, 103.9), (120.956, 103.9), (121.38, 104.324)], 0.2)
drop_via(112.565, 114.741)
# GND_F islands: the SHT40 GND tail gets a via; BMP580 pad 3's pocket opens up by taking SDA to B.Cu
# right beside pad 4 (on the existing B.Cu diagonal) instead of through the dogleg to (110.9,112.6)
via("GND", 110.42, 107.89, 0.45, 0.2)
drop_track(111.5, 112.0, 110.9, 112.6)
drop_track(112.737, 112.0, 111.5, 112.0)
drop_track(112.737, 111.5, 111.95, 111.5)
drop_track(113.9, 109.6, 110.9, 112.6)
drop_via(110.9, 112.6)
track("/I2C_SDA", [(113.9, 109.6), (111.75, 111.75), (110.9, 112.6)], layer=B)
track("/I2C_SDA", [(112.737, 112.0), (112.0, 112.0), (111.75, 111.75)])
via("/I2C_SDA", 111.75, 111.75, 0.45, 0.2)
track("GND", [(112.737, 111.5), (112.3, 111.5)])

# ---- U1 fan-out (pads 19 LED_B 133.4, 20 LED_G 134.2, 21 NC, 22 LED_R 135.8, 23 BTN3_N 136.6; y 110.5)
# BTN3_N drop moves from under pad 20 to under pad 21; R24 flips so its BTN3_N pad is under that via
drop_via(134.2, 111.5)
drop_track(134.2, 111.5, 134.2, 109.55)
drop_track(134.2, 111.5, 134.09, 112.2)
track("/BTN3_N", [(135.0, 109.55), (135.0, 111.5)], layer=B)
via("/BTN3_N", 135.0, 111.5, 0.45, 0.2)
fp("R24", 134.6, 112.2, 0)                     # pad 1 +3V3 134.09, pad 2 BTN3_N 135.11
track("/BTN3_N", [(135.0, 111.5), (135.11, 112.2)])
drop_track(135.11, 112.2, 134.59, 113.144)
drop_track(135.11, 112.2, 135.11, 112.558)
drop_track(135.403, 112.85, 135.11, 112.558)
drop_track(135.4, 113.6, 135.4, 112.85)
drop_via(134.59, 113.144)
drop_via(135.4, 113.6)
track("+3V3", [(134.09, 112.2), (134.09, 112.6), (134.34, 112.85), (135.403, 112.85)], 0.25)

# LED_G: pad 20 straight down to a via, then B.Cu x 134.45
track("/LED_G", [(134.2, 110.5), (134.2, 111.5)])
via("/LED_G", 134.2, 111.5, 0.45, 0.2)
# LED_R: via on the pad-22 run to R16, then B.Cu x 134.9
via("/LED_R", 135.8, 111.5, 0.45, 0.2)

# ---- bottom: D6 at the edge, resistors in a staircase above it (pad 1 = GPIO side on top)
fp("D6", 133.05, 143.7, 0)         # pads 1 A (131.65,143.9) 2 B (132.65,143.5) 3 G (133.45,143.5) 4 R (134.45,143.9); 0.2 to the edge
for ref, x, y in (("R22", 132.1, 141.3), ("R33", 133.15, 141.8), ("R32", 134.2, 142.1)):
    fp(ref, x, y, 270)                                    # pad 1 on top
for seg in ((132.29, 141.7, 131.985, 142.9), (131.985, 142.9, 131.985, 143.825), (133.615, 143.825, 133.615, 142.6),
            (133.615, 143.825, 134.67, 143.825), (134.0, 140.9, 133.31, 141.7), (134.0, 128.83, 134.0, 140.9)):
    drop_track(*seg)
for x, y in ((133.9, 142.35), (134.67, 143.825), (134.0, 140.9)):
    drop_via(x, y)

# B.Cu runs: LED_B x 134.0 (existing upper part), LED_G x 134.45, LED_R x 134.9; staggered vias
track("/LED_B", [(134.0, 128.83), (134.0, 140.4)], layer=B)
via("/LED_B", 134.0, 140.4, 0.45, 0.2)
track("/LED_G", [(134.2, 111.5), (134.2, 112.6), (134.45, 112.85), (134.45, 140.95)], layer=B)
via("/LED_G", 134.45, 140.95, 0.45, 0.2)
track("/LED_R", [(135.8, 111.5), (135.8, 112.55), (134.9, 113.45), (134.9, 141.5)], layer=B)
via("/LED_R", 134.9, 141.5, 0.45, 0.2)

# F.Cu: vias to resistor tops (under the VSYS run at y 140.0), resistor bottoms to D6
track("/LED_B", [(134.0, 140.4), (132.1, 140.4), (132.1, 140.79)])
track("/LED_G", [(134.45, 140.95), (133.15, 140.95), (133.15, 141.29)])
track("/LED_R", [(134.9, 141.5), (134.71, 141.59), (134.2, 141.59)])
track("Net-(D6-B)", [(132.1, 141.81), (132.1, 142.4), (132.65, 142.95), (132.65, 143.5)], 0.2)
track("Net-(D6-G)", [(133.15, 142.31), (133.15, 142.9), (133.45, 143.2), (133.45, 143.5)], 0.2)
track("Net-(D6-R)", [(134.2, 142.61), (134.45, 142.86), (134.45, 143.9)], 0.2)
# common anode to the In2 +3V3 plane
track("+3V3", [(131.65, 143.9), (131.65, 142.75)], 0.2)
via("+3V3", 131.65, 142.75, 0.45, 0.2)

bd.save()
