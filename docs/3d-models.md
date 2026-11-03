# 3D model check (rev 0.8, 2026-11-03)

Each part's 3D model was compared with the manufacturer's package drawing: body size and height, pin-1 / polarity at footprint pad 1, leads on pads, and the direction of mouths, actuators and lenses. Heights are above the PCB surface. Footprints match the datasheet land patterns throughout; the fixes below are to the models only.

| Ref | Part | Datasheet | Model now | Result |
|---|---|---|---|---|
| U1 | ESP32-C6-MINI-1 | 13.2 x 16.6 x 2.4 | 13.2 x 16.6 x 2.5 | OK (shield drawn 1 mm longer, cosmetic) |
| U2 | SHT4x DFN-4 | 1.5 x 1.5 x 0.54 | 1.52 x 1.52 x 0.55, EasyEDA-derived `Sensirion_DFN-4_1.5x1.5_ee.wrl` | OK |
| U3 | BMP580 LGA-10 | 2.0 x 2.0 x 0.8 max | 2.0 x 2.0 x 0.8, EasyEDA-derived `Bosch_LGA-10_2x2_BMP580_ee.wrl` | OK |
| U4 | LIS2DW12 LGA-12 | 2 x 2 | KiCad stock `LGA-12_2x2mm_P0.5mm` | OK (stock model) |
| U5 | MAX17048 TDFN-8 | 2 x 2 x 0.8 max | 2 x 2 x 0.78 | OK; exposed pad size not checked (drawing 21-0168 unavailable) |
| U6 | BQ24073 VQFN-16 RGT | 3 x 3 x 0.8-1.0 | 3 x 3 x 1.0 | Fixed: was 0.77 tall (sits under the panel) |
| U7 | RT9080 TSOT-23-5 | 2.9 x 2.8 x 1.0 max | 2.9 x 2.8 x 0.95 | OK |
| U8 | USBLC6-2SC6 SOT-23-6 | 1.25 max (UMW) / 1.45 max (ST) | 1.24 | Fixed: was 1.55 |
| Q1, Q2 | SC-70, SOT-23 | | | OK (pinout G/S/D checked) |
| D2-D4 | MBR0530 SOD-123 | | | OK (cathode band at pad 1) |
| D1, D5 | XL-1606 side-view LED | 1.7 x 1.1 footprint, 0.6 tall, lying flat | same | Fixed: model stood 1.1 tall. Lens sticks out 0.3-0.4 mm past the bottom edge |
| D6 | MHS110FRGBCT RGB side-view LED | 3.2 x 1.5 (base 0.5 + dome R1.0), 1.0 tall | 3.2 x 1.5 x 1.0, EasyEDA-derived `LED_MHS110FRGBCT_ee.wrl`, rotated 180 in the footprint; dome 0.65 past the bottom edge | OK |
| J1 | HRO TYPE-C-31-M-12 | mouth 0.6 past the edge | 0.6 | Fixed: model was 0.78 mm too far out (pegs missed their holes) |
| J2 | DEALON PH-2PWB | 7.95 x 7.6 x 5.6 | JST S2B-PH-SM4-TB 7.9 x 7.6 x 5.5 | OK (JST-compatible body, 0.1 mm lower) |
| J3 | FPC-05FB-24PH20 | body over the pads | same | Fixed: model was 1.7 mm toward the slot |
| SW1-SW3 | TS24CA | sits on the board, actuator 0.22 past the edge | same | Fixed: model was sunk 0.8 mm into the board |
| L1 | FNR4030S 47 uH | 4 x 4 x 3.0 | 4 x 4 x 3.0 | Fixed: was the 2.6 mm FNR4026S |
| TH1 | NTC 0603 | 1.6 x 0.8 x 0.8 | 0.8 | Fixed: used the 0.45 mm resistor model |
| R, C | 0402 / 0603 / 0805 | per value | | OK (MLCC thickness codes checked per value) |
| ASSY1 | GDEY0154D67 panel | 37.32 x 31.8 x 1.0, AA 27 x 27 | same | OK |
| ASSY2 | 503040 LiPo | 40 x 30 x 5 | same | OK |

## Open: LED polarity vs lens direction

The XL-1606 cannot be placed mirrored, so the cathode position fixes which way the lens points. JLC's library footprint and 3D model for both LEDs (C965860, C965863) have the cathode mark at -x with the lens at -y. With the CPL rotation in `production/rotation-check.md` this gives the cathode on our pad 1 and the lens toward the board edge, as intended. The XINGLIGHT land-pattern drawing (datasheet p.7) appears to show the mirror image. Before paying for assembly, check D1 and D5 in JLC's placement preview, and ask JLC to confirm that the lens faces the board edge with the cathode on pad 1.
