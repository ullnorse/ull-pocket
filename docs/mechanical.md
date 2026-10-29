# ull-pocket mechanical concept (layout phase 1)

Board: 40.0 x 44.5 mm, 4-layer 1.6 mm (JLC04161H-3313), corners R1.
Envelope with overhangs: 41.2 x 49.9 mm (antenna 5.4 mm up, SHT31 tab 5.4 mm up, FPC bend 1.2 mm right).
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
- J2 (JST PH SMD, 5.5 mm tall) is outside the cell outline, at top-left. Its opening faces +x.
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
- Distances: the cell is 14 mm away, the panel 4.2 mm below the edge line, and J2 and its leads about 9 mm to the left.
- Panelization: the overhanging module needs a cut-out or an open edge in the JLC panel or rail at the top edge. Ask JLC for "components overhang board edge".

## SHT31 tab and other parts

- **SHT31 (U2):** on a 6.8 x 3.8 mm tab above the top-left edge, joined by a 3 mm neck. It has no copper pour (rule area). It is outside the panel and battery outlines, and about 25 mm from the module and charger. Vent the case at the tab.
- **BMP585 (U3):** at the tab root, also clear of the heat sources.
- **USB-C (J1):** bottom centre. Its THT shell legs are below the panel outline, in the 8.5 mm bottom chin on the front.
- **SW1:** left edge (the right side seen from the front). The actuator is 0.3 mm past the edge.
- **LEDs:** D5 PWR, D1 CHG and D6 USR are XL-1606 side-view LEDs on the F-side bottom edge, right of J1 (x 26.8, 29.8, 32.8). Each emits outward through the bottom edge; the face sits 0.1 mm inside the edge. The case needs a small window or light pipe at each one, centred about 0.6 mm above the PCB top surface.
- **Mounting holes:** two M2 holes in the chin, at (2.8, 41.3) and (37.2, 41.3). Bosses go on the front shell. Screws go in from the back, under the battery shelf.
- **Programming and test points:** J4 pogo pads and TP1-TP6 are under the cell. Reach them with the battery unplugged.
