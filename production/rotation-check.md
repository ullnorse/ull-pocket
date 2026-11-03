# Rotation check (JLCPCB CPL)

Each unique KiCad footprint + LCSC pair is compared against the EasyEDA footprint JLC places for that LCSC
number (`easyeda2kicad --footprint`). Pads are matched by name (LEDs: by function), giving
`EE_pad = Rot(delta) * KiCad_pad + t` in the KiCad frame (y down, CCW positive).
CPL rotation = KiCad rotation - delta. CPL position = KiCad position - Rot(CPL rotation) * t.

Pin-1 vectors are pad-1 centres relative to the footprint origin (mm, footprint-local, unrotated).
`match` is the worst pad-centre residual of the best fit / of the second-best rotation (mm);
a large second-best number means the rotation is unambiguous (symmetric passives are 0/180-ambiguous only
in the unpolarised sense and need no correction). Origin shifts under 0.1 mm are ignored.

| Refs | KiCad footprint | LCSC | KiCad pin-1 | EE footprint | EE pin-1 | delta | origin shift t | match |
|---|---|---|---|---|---|---|---|---|
| C2,C18,C20,C21,C22,C23,C24,C25,C26 | C_0603_1608Metric | C15849 | (-0.78, 0.00) | C0603 | (-0.70, 0.00) | 0 deg | 0 | 0.08 / 1.04 |
| C3,C4,C16 | C_0603_1608Metric | C19702 | (-0.78, 0.00) | C0603 | (-0.70, 0.00) | 0 deg | 0 | 0.08 / 1.04 |
| C5,C9,C11,C12,C13,C14,C15,C27,C28,C29 | C_0402_1005Metric | C1525 | (-0.48, 0.00) | C0402 | (-0.42, 0.00) | 0 deg | 0 | 0.06 / 0.64 |
| C6,C7,C10 | C_0402_1005Metric | C52923 | (-0.48, 0.00) | C0402 | (-0.42, 0.00) | 0 deg | 0 | 0.06 / 0.64 |
| C8 | C_0805_2012Metric | C45783 | (-0.95, 0.00) | C0805 | (-1.00, 0.00) | 0 deg | 0 | 0.05 / 1.38 |
| C17 | C_0805_2012Metric | C1779 | (-0.95, 0.00) | C0805 | (-1.00, 0.00) | 0 deg | 0 | 0.05 / 1.38 |
| C19 | C_0805_2012Metric | C98192 | (-0.95, 0.00) | C0805 | (-1.00, 0.00) | 0 deg | 0 | 0.05 / 1.38 |
| D1 | LED_XL-1606_SideView | C965860 | (0.81, -0.28) (cathode) | LED-SMD_L1.7-W1.1-RD_RED-SIDE | (-0.85, 0.00) (cathode) | 180 deg | (0.00, -0.28) | 0.04 / 1.18 |
| D2,D3,D4 | D_SOD-123 | C82046 | (-1.65, 0.00) | SOD-123_L2.7-W1.6-LS3.7-RD-1 | (-1.70, 0.00) | 0 deg | 0 | 0.05 / 2.37 |
| D5 | LED_XL-1606_SideView | C965863 | (0.81, -0.28) (cathode) | LED-SMD_L1.7-W1.1-R-RD_ORANGE | (-0.75, 0.00) (cathode) | 180 deg | (0.00, -0.28) | 0.06 / 1.11 |
| D6 | LED_MHS110FRGBCT_SideView | C496820 | (-1.40, 0.20) | LED-ARRAY-SMD_MHS110FRGBCT | (1.40, -0.20) | 180 deg | 0 | 0.00 / 2.00 |
| J1 | USB_C_Receptacle_HRO_TYPE-C-31-M-12 | C165948 | (-3.25, -4.04) | USB-C_SMD-TYPE-C-31-M-12_1 | (-3.20, -2.47) | 0 deg | (0.00, 1.57) | 0.00 / 2.47 |
| J2 | JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal | C2905019 | (-1.00, -2.85) | FPC-SMD_2P-P2.00_DEALON_PH-2PWB | (-1.00, -2.85) | 0 deg | 0 | 0.00 / 1.41 |
| J3 | FPC-SMD_24P-P0.50_FPC-05FB-24PH20 | C2856831 | (5.75, -1.62) | FPC-SMD_24P-P0.50_FPC-05FB-24PH20 | (5.75, -1.62) | 0 deg | 0 | 0.00 / 11.16 |
| L1 | IND-SMD_L4.0-W4.0_FNR40XXS | C167888 | (-1.50, 0.00) | IND-SMD_L4.0-W4.0_FNR40XXS | (-1.50, 0.00) | 0 deg | 0 | 0.00 / 2.12 |
| Q1 | SOT-323_SC-70 | C469327 | (-0.89, -0.65) | SOT-323_L2.0-W1.3-P1.30-LS2.1-BR | (0.80, 0.65) | 180 deg | 0 | 0.12 / 1.59 |
| Q2 | SOT-23 | C20917 | (-0.94, -0.95) | SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR | (1.00, 0.95) | 180 deg | 0 | 0.08 / 1.83 |
| R1,R2 | R_0402_1005Metric | C25905 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R3 | R_0402_1005Metric | C17168 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R4,R5,R7,R11,R12,R14,R25,R26,R29 | R_0402_1005Metric | C25741 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R6,R21 | R_0402_1005Metric | C4109 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R9,R10 | R_0402_1005Metric | C25890 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R13 | R_0603_1608Metric | C21189 | (-0.82, 0.00) | R0603 | (-0.75, 0.00) | 0 deg | 0 | 0.07 / 1.11 |
| R15,R16,R17,R18,R24 | R_0402_1005Metric | C25744 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R19 | R_0603_1608Metric | C22935 | (-0.82, 0.00) | R0603 | (-0.75, 0.00) | 0 deg | 0 | 0.07 / 1.11 |
| R20 | R_0603_1608Metric | C22939 | (-0.82, 0.00) | R0603 | (-0.75, 0.00) | 0 deg | 0 | 0.07 / 1.11 |
| R22 | R_0402_1005Metric | C25117 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R27,R32,R33 | R_0402_1005Metric | C11702 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| R28,R30,R31 | R_0402_1005Metric | C25076 | (-0.51, 0.00) | R0402 | (-0.43, 0.00) | 0 deg | 0 | 0.08 / 0.67 |
| SW1,SW2,SW3 | SW-SMD_2P-TS24CA | C393942 | (-1.70, 0.97) | SW-SMD_2P-TS24CA | (-1.70, 0.97) | 0 deg | 0 | 0.00 / 3.30 |
| TH1 | R_0603_1608Metric | C279936 | (-0.82, 0.00) | R0603 | (-0.75, 0.00) | 0 deg | 0 | 0.07 / 1.11 |
| U1 | ESP32-C6-MINI-1 | C5736265 | (-5.90, -4.00) | WIFIM-SMD_61P-L16.6-W13.2-P0.80-ESP32-C6-MINI-1-N4 | (-5.90, -3.98) | 0 deg | 0 | 0.06 / 10.96 |
| U2 | Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x | C2909890 | (-0.70, -0.40) | DFN-4_L1.5-W1.5-P0.8-TL-EP | (-0.68, -0.40) | 0 deg | 0 | 0.02 / 1.14 |
| U3 | Bosch_LGA-10_2x2mm_P0.5mm_BMP580 | C22391138 | (-0.76, -0.25) | LGA-10_L2.0-W2.0-P0.50-TL_BMP580 | (-0.78, -0.25) | 0 deg | 0 | 0.02 / 1.31 |
| U4 | LGA-12_2x2mm_P0.5mm | C189624 | (-0.76, -0.75) | LGA-12_L2.0-W2.0-P0.50-BL | (-0.75, 0.88) | 90 deg | 0 | 0.12 / 1.63 |
| U5 | TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2 | C2682616 | (-0.75, 0.94) | TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2 | (-0.75, 0.94) | 0 deg | 0 | 0.00 / 1.70 |
| U6 | VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm | C15220 | (-1.46, -0.75) | QFN-16_L3.0-W3.0-P0.50-TL-EP1.7 | (-1.50, -0.75) | 0 deg | 0 | 0.04 / 2.36 |
| U7 | TSOT-23-5 | C841192 | (-1.14, -0.95) | TSOT-23-5_L2.9-W1.6-P0.95-LS2.8-BL | (-0.95, 1.15) | 90 deg | 0 | 0.01 / 2.37 |
| U8 | SOT-23-6 | C2687116 | (-1.14, -0.95) | SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL | (-0.95, 1.15) | 90 deg | 0 | 0.01 / 2.11 |

## Notes

- Parts imported from EasyEDA (L1, J3, U3, U5, SW1, U1) and the stock R/C/D footprints need delta 0 and no shift.
- Q1, Q2, U2, U7, U8: the EE footprint is the KiCad one rotated (delta in the table); CPL rotation = KiCad rotation - delta.
- LEDs D1, D5: both EE footprints have the cathode (pad 1) on the -x pad. D6 (C496820, RGB): EE pad 1 is the
  common anode, as in our footprint; the EE footprint is ours turned 180. Check D1, D5, D6 orientation in
  JLC's placement preview.
  The 0.28 mm y shift is the KiCad pad centre being off the origin (pads are 0.28 mm above the origin).
- J1: signal pads give a 1.57 mm shift; the shell legs differ by 1.42 mm (KiCad and EE footprints disagree by 0.15 mm
  between signal and shell pads), the 1.57 mm signal-pad value is used. EE pin 1 shown is pad A1B12.
- J2 (DEALON PH-2PWB): pads 1 and 2 coincide with our footprint, no shift. The EE origin is used as the part centre. It differs from the EE pad-bounding-box centre by
  <= 0.15 mm everywhere except SW1 (0.30 mm), so the origin-vs-centre ambiguity is at most 0.3 mm (SW1).
- Coordinates are in the Gerber frame (absolute page coordinates, y up), the same frame as the Gerber and drill files.
- Not verifiable offline: JLC's own assembly DB can differ from the EasyEDA footprint. Confirm the placement preview.
