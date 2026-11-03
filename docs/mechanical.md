# ull-pocket mechanical concept (layout phase 1)

Board: 40.0 x 44.5 mm rectangle, 4-layer 1.6 mm (JLC04161H-3313), corners R1. Only internal cut-out: the SHT40 moat.
Envelope with overhangs: 41.2 x 49.9 mm (antenna 5.4 mm up, FPC bend 1.2 mm right). The USB-C mouth adds 0.6 mm at the bottom.
Coordinates below: KiCad top view (F side), origin at board top-left (KiCad 100,100).

## Stack, front to back

| Layer | Thickness |
|---|---|
| GDEY0154D67 panel, display facing out | 1.0 mm |
| Double-sided tape | 0.15 mm |
| PCB, B side bare, F side has all parts | 1.6 mm |
| Battery shelf (case rib or foam) | 3.5 mm |
| 503040 LiPo | 5.0 mm (allow +0.5 mm swell) |

That is about 11.3 mm before case walls.

## E-paper panel

- The panel sits on the bare B side. B is the product front.
- The glass (37.32 x 31.80 mm) is inset 0.2 mm from the right board edge, from y 4.2 to 36.0.
- It covers no parts, so the glass gets a flat bed.
- All SMD parts are on F, so the board needs one assembly pass.

### FPC route

- The 14.3 mm tail leaves the TFT ledge and wraps 180 degrees round the right board edge.
- Bend radius is about 1.2 mm. The bend protrudes about 1.2 mm past the edge. The case needs a 1.5 mm pocket there.
- The tail ends about 10.4 mm in on the F side and plugs into J3.
- The 6 mm stiffener stays flat on the F side. Only the bare flex bends.
- No parts are allowed under the flat run (rule area `FPC_tail_no_parts`).

### Contact side

The gold fingers are on the display side of the tail. Evidence:

- The datasheet page 2 photo shows gold fingers on the front view and the black stiffener on the back view.
- Good Display's DESPI-C02 adapter takes the panel flat, "white side up". Their FAQ says their 24-pin FPC connectors are top-contact.

After the wrap, the fingers face away from the PCB. J3 must therefore contact from the top.

### J3

- J3 is XUNPU FPC-05FB-24PH20 (LCSC C2856831): back flip, dual contact, 2.0 mm high.
- The original FPC-05F-24PH20 (C2856805) is bottom-contact (前翻下接). Its pin order would also come out mirrored (finger 1 on pad 24).
- On FPC-05FB, pin 1 is at the opposite end, so J3 pin n = panel pin n, straight through. Pin 1 is at the top (y 14.4).
- J3 sits at (28.9, 20.15), rotated 90 degrees, with its slot facing the right edge. The FPC goes in about 2.8 mm.
- Tail length (+/-0.3 mm) and the panel position use up this margin. Check the fit with a real panel before routing is frozen.

## Battery

- 503040 cell, 600 mAh, 40 mm along x, from y 14 to 44.
- It lies over the F side on a 3.5 mm shelf.
- Parts under the shelf are at most 3.25 mm tall (USB-C 3.25, L1 3.0, J3 2.0, module 2.4).
- J2 (DEALON PH-2PWB, JST-PH compatible SMD, 5.6 mm tall) is outside the cell outline, at top-left. Its opening faces -x, at the left board edge (rev 0.7: turned 180 degrees so the plug no longer points at the SHT40 island). A mated PH plug sticks out about 0.5 mm past the left edge at y 3-9, and its leads leave to the left; the case needs a pocket there for the plug and the lead bend.
- The cell's lead end is at -x. Leave about 40 mm of lead.
- J2 is marked + (pin 2, VBAT) and - (pin 1, BAT-) on silkscreen.

## TH1 (battery NTC)

- TH1 sits under the centre of the cell at (20.0, 29.6).
- The cell is 3.5 mm above it. Fit a 3 mm thermally conductive gap pad between TH1 and the cell, so the charger's TS input tracks cell temperature.

## Antenna

- The ESP32-C6-MINI-1 sits in the top-right corner.
- Its 5.4 mm antenna region overhangs the top board edge, which Espressif recommends.
- The footprint's 15 mm keep-out falls entirely off the board.
- Keep case metal, screws and the battery away from the overhang.
- Distances: the cell is 14 mm away, the panel 4.2 mm below the edge line, J2 and its leads about 9 mm to the left, and the SHT40 island 10 mm to the left.
- Panelization: the overhanging module needs a cut-out or an open edge in the JLC panel or rail at the top edge. Ask JLC for "components overhang board edge".

## SHT40 island

U2 sits on a thermally isolated island at the top edge, between the J2 opening and U4.

- Island: x 11.75-15.9, y 1.75-5.65 (4.15 x 3.9 mm). It carries U2 and its decoupling cap C11 only. U2 (SHT40) is 0.54 mm tall.
- Moat: a 1.0 mm non-plated milled slot (Edge.Cuts cut-out) on the top, left and right, wrapping both bottom corners. Outer extent x 10.75-16.9, y 0.75-7.15. Convex slot corners are drawn R0.5 (1 mm cutter).
- Bridge: x 11.75-14.75 (3.0 mm wide), y 5.65-7.15 (1.5 mm long), at the island's bottom-left. It carries four 0.15 mm F.Cu tracks: SDA, GND, SCL, +3V3.
- Rim: 0.75 mm of bare FR4 between the moat and the top edge.
- No copper pour on any layer over the rim, moat, island or bridge (rule area `SHT_island_no_pour`).
- Heat sources are far away: the module 10 mm, the boost inductor L1 9 mm, the charger and the LDO about 30 mm. U4 (LIS2DW12, 2x2 mm LGA-12, microamps) is 2.1 mm right of the moat.
- The island is clear of the battery outline (the cell starts at y 14). On the B side its lower 1.45 mm and the bridge lie under the panel glass (from y 4.2).

### Case vent

- Put the vent in the top wall over x 11-17, on the F side (battery side) of the PCB. U2's sensing opening faces F.
- Leave an open air path from the vent to the island above the F side. The cavity there is open up to the battery shelf at y 14.
- Keep the battery leads off the island. The plug enters J2 from the left edge, around y 3-9; run the leads down the left side to the cell's lead end (above SW1 at y 18), not across the board.
- Back side: do not tape the panel to the PCB over x 10.5-17, y 4.2-7.5. Tape there would bridge the moat to the glass.
- Keep the wall rib or boss off the rim and island. A clamp there would also bridge the moat.

## Other parts

- **BMP580 (U3, LGA-10 2x2 mm):** below the island at (13.5, 12.0), clear of the heat sources.
- **USB-C (J1):** bottom centre. The receptacle mouth overhangs the bottom edge by 0.6 mm so a plug seats through a thin case wall. Its THT shell legs are below the panel outline, in the 8.5 mm bottom chin on the front.
- **Buttons SW1-SW3:** three TS24CA side buttons on the left edge (the right side seen from the front), 7.0 mm pitch. Each actuator is about 0.2 mm past the edge (TS24CA datasheet), on the F (battery) side. Give each its own cut-out or cap.

  | Button | Function | Centre y | GPIO |
  |---|---|---|---|
  | SW1 | UP | 20.5 | IO2 (ext1 wake) |
  | SW2 | OK | 27.5 | IO5 (ext1 wake) |
  | SW3 | DN | 34.5 | IO9 (polled, no wake; also BOOT) |

  The row spans y 18.2-36.8 (switch bodies). It stays clear of Q2 (ends at y 15.7) and of the H2 boss (hole at y 41.3).
- **LEDs:** D5 PWR, D1 CHG and D6 USR are side-view LEDs on the F-side bottom edge, right of J1 (x 26.8, 29.8, 33.05). D5 and D1 are XL-1606: they lie flat (0.6 mm tall) with the lens pointing out through the bottom edge; the lens tip sticks out about 0.3-0.4 mm past the edge (0.26 in JLC's model, 0.42 from the XINGLIGHT land pattern). D6 is the MHS110FRGBCT RGB LED: its dome is 1.0 mm tall and overhangs the bottom edge by 0.65 mm. The case needs a small window or light pipe at each one: centred about 0.3 mm above the PCB top surface for D5/D1, covering the full 1.0 mm dome height for D6.
- **Mounting holes:** two M2 holes in the chin, at (2.8, 41.3) and (37.2, 41.3). Bosses go on the front shell. Screws go in from the back, under the battery shelf.
- **Programming and test points:** J4 (PROG) pogo pads (VREF, GND, EN, IO9/BOOT, TXD0, RXD0) are on the back, top-right strip under the module (x 30.5-36.6, y 0.35-3.9), between the board edge and the panel (panel starts at y 4.2). They are clear of the J2 plug and its lead on the front, and reachable with the battery fitted. Pogo pins only: there is no room for a 2x3 header. TP1-TP5 are under the cell; reach them with the battery unplugged. TP4 (VBAT) and TP5 (+3V3) sit between the DN button and USB-C.

## Programming access

- USB-C (J1) is the primary programming path.
- J4 (PROG pads on the back) is for recovery only. Use a press-on pogo fixture.
- Power the board from USB or the battery while programming. J4 pad 1 (VREF) is a sense-only reference: it is fed from +3V3 through R27 1k, so the programmer reads the target voltage but its target-power output does nothing.
- The pogo pins must protrude at least 2 mm: the panel glass is 0.8 mm away from the pads, and the antenna overhang leaves no room for edge clips.
- Program the board before taping the panel on, where possible.
