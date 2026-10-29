# ull-pocket parts, rev 0.5 (2026-10-28) (stock checked on JLCPCB via pcbparts.dev, 2026-10-28; LEDs 2026-10-29)

| Ref | Function | Part | LCSC | Package | Note |
|---|---|---|---|---|---|
| U1 | MCU + Wi-Fi/BLE/802.15.4 | ESP32-C6-MINI-1-H4 | C6553337 | 16.6x13.2 module, PCB antenna | 4 MB flash; antenna at board edge with keep-out |
| U2 | Temp / RH | SHT31-DIS-B2.5kS | C80862 | DFN-8 2.5x2.5 | on thermally slotted tab; ull-sht3x driver exists |
| U3 | Pressure | BMP585 | C18184976 | LGA-8 3.3x3.3 (pads 1-8) | replaces BMP390 (not stocked); 2875 in stock; datasheet pin 9 is a laser-marking area, not a pad (removed from symbol and footprint); footprint has a via/track/pour keepout rule area over the body, +-0.9 mm (inside the pads' inner edges at +-0.955) so tracks and vias reach the pads. Set INT polarity to active-low in firmware. Footprint also has an F.Mask opening +-1.67 mm over the body (datasheet 9.3.3: no solder mask under the sensor); layout: only each pad's own trace may enter the band under the body |
| U4 | Accelerometer | LIS3DHTR | C15134 | LGA-16 3x3 | INT1 to an LP GPIO for wake; set INT_POLARITY active-low |
| U5 | Fuel gauge | MAX17048G+T10 | C2682616 | DFN-8 2x2 | |
| U6 | Li-ion charger, power path | BQ24073RGTR | C15220 | VQFN-16 3x3, EP 1.68 (stock `VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm`) | 4.4 V OUT regulation; replaces BQ24074 (17 in stock) |
| U7 | 3.3 V LDO, ~2 uA Iq, 600 mA | RT9080-33GJ5 | C841192 | TSOT-23-5 | |
| C2 | U6 IN cap | CL10A105KB8NNNC 1uF/50V X5R | C15849 | 0603 | was 1uF/25V 0402 (C52923); 50 V rating for VBUS transients, basic part, 13M in stock |
| Q2 | Battery reverse-polarity FET (low side, BAT- lead) | AO3400A | C20917 | SOT-23 | basic part, 1.13M in stock; Vgs(max) 12 V; drain = BAT_N (J2 pin 1), source = GND, gate = VBAT via R11 100k |
| R13 | Sleep-current link, LDO_OUT to +3V3 | 0603WAF0000T5E 0R | C21189 | 0603 | basic part, 21.6M in stock; replace with an ammeter to measure sleep current |
| TP1-TP6 | Test pads: VBUS, VSYS, GND, VBAT, +3V3, SPARE_IO14 (spare GPIO, IO14) | TestPoint_Pad_1.0x1.0mm | - | 1.0 mm pad | footprint only, excluded from BOM |
| J4 | PROG pogo pads: +3V3, GND, EN, IO9/BOOT, TXD0, RXD0 | PogoPads_2x3_P2.54mm_D1.0 | - | 2x3 grid, 2.54 mm pitch, 1.0 mm round SMD pads | footprint only, excluded from BOM and placement; on B.Cu above the panel; mates with a 2x3 pogo fixture (no room for a header); pad 1 (+3V3) is a sense/reference pin only: do not feed 3.3 V from a programmer with no battery fitted (back-feed through the RT9080) |
| C8 | U1 3V3 bulk | CL21A226MAQNNNE 22uF/25V X5R | C45783 | 0805 | basic, 4.05M in stock |
| C19 | E-paper boost coupling cap | CL21A475KBQNNNE 4.7uF/50V X5R | C98192 | 0805 | extended, 366k in stock |
| R25, R26 | 100k pull-ups to +3V3 on EPD_RST_N, EPD_CS_N (panel idle in sleep) | 0402WGF1003TCE | C25741 | 0402 | basic |
| R24 | IO15 10k pull-up to +3V3 (if the JTAG_SEL eFuse is ever burned, selects USB Serial/JTAG instead of pad JTAG on IO4-7) | 0402WGF1002TCE | C25744 | 0402 | basic |
| U8 | USB ESD | USBLC6-2SC6 | C2687116 | SOT-23-6 | |
| J1 | USB-C | TYPE-C-31-M-12 | C165948 | 16-pin SMD | 5.1k CC pull-downs |
| J2 | Battery | PH-2PWB (DEALON) | C2905019 | JST-PH 2P SMD | extended; 88k in stock, $0.03; replaces S2B-PH-SM4-TB C295747 (0 in stock, 41-piece minimum). Pin 1/2 pads at the same positions as our S2B-PH-SM4-TB footprint (+-1.0, -2.85); mount tabs +-3.3 vs our +-3.35 (0.05 mm, covered by our pads); body 8.0 x 7.6 mm (JST 7.9 x 8.6), 5.6 mm tall (JST 5.5), mouth on the same side. Mates with a standard JST-PH 2.0 plug. Kept the S2B-PH-SM4-TB board footprint. 503040 LiPo with protection PCB; pin 2 = BAT+, pin 1 = BAT- (via Q2); silkscreen must mark + and - |
| J3 | E-paper FPC | FPC-05FB-24PH20 | C2856831 | 24P 0.5 mm, back flip, dual contact, H2.0 | panel tail wraps round the board edge so its fingers (display side) face away from the PCB; FPC-05F-24PH20 (C2856805) is bottom-contact and would mirror the pin order. Straight map: J3 pin n = panel pin n. See docs/mechanical.md |
| SW1 | Side button | TS24CA (verify side-actuated) | C393942 | 4.6x1.8 | wake button on LP GPIO; locating pegs are 0.7 mm NPTH holes (no pad) |
| Q1 | E-paper boost switch | SI1308EDL-T1-GE3 | C469327 | SOT-323 | per panel reference circuit |
| D2-D4 | E-paper boost | B5819W SL | C8598 | SOD-123 | basic, 558k in stock; 40 V 1 A Schottky, replaces MBR0530T1G (C82046, extended); pad 1 = cathode, same footprint |
| D1 + R6 | CHG indicator (red), side-view on bottom edge | XL-1606SURC (XINGLIGHT) | C965860 | SMD 1.7x0.6, H1.1, side-view | extended; 221k in stock; Vf 1.9-2.3 V @20 mA, ~1.8 V @1 mA; from VSYS (4.4 V while charging) via R6 2k: (4.4-1.8)/2k = 1.3 mA, only while charging. R6 = 0402WGF2001TCE C4109 (basic); silkscreen CHG (D5 PWR, D6 USR) |
| D5 + R21 | Power LED (green), side-view on bottom edge, VBUS - 2k - LED - GND | XL-1606UGC (XINGLIGHT) | C965863 | SMD 1.7x0.6, H1.1, side-view | extended; 238k in stock; InGaN emerald, Vf 2.6-3.4 V @20 mA, ~2.6 V @1 mA: (5.0-2.6)/2k = 1.2 mA, 0 on battery. R21 = 0402WGF2001TCE C4109 (basic) |
| D6 + R22 | LED_USER blue on IO5 (LP GPIO), side-view on bottom edge, 470R; silkscreen USR | XL-1606UBC (XINGLIGHT) | C965865 | SMD 1.7x0.6, H1.1, side-view | extended; 55k in stock; Vf 2.7-3.3 V @20 mA, 2.6-2.8 V @1 mA (datasheet I-V curve): (3.3-2.6..2.8)/470 = 1.1-1.5 mA. R22 = 0402WGF4700TCE C25117 (basic) |
| TH1 | Battery NTC on BQ24073 TS | SDNT1608X103F3435FTF 10k 1% B3435 | C525660 | 0603 | extended; 87.6k in stock; place under/against the cell. Window 0.5..50.8 C (75 uA bias: 28k / 4.0k trips); resume 3.9 / 47.9 C |
| R8 | TS fallback fixed 10k, parallel to TH1 | 0402WGF1002TCE | C25744 | 0402 | DNP; excluded from BOM and placement; fixed 10k = 25 C |
| L1 | E-paper boost | FNR4030S470MT 47 uH (Isat 1 A, Irms 800 mA, DCR 579 mR, 20%) | C167888 | 4x4x3 mm shielded | extended; 82k in stock; replaces SWPA4018S470MT (Isat 570 mA); panel reference needs 47 uH / 500 mA; footprint + 3D from easyeda2kicad, pads 1,2 match L_Small |
| DISP | E-paper panel | Good Display GDEY0154D67 (SSD1681, 200x200) | — | — | not at LCSC; hand-fit after assembly |

LEDs D1/D5/D6 share footprint `ull-pocket:LED_XL-1606_SideView` (datasheet land pattern 2x 0.77x0.95 mm, pad 1 = cathode). The emitting face sits 0.1 mm inside the bottom board edge (pads 0.2 mm from the edge, custom DRC rule); the case needs a window or light pipe at each LED.
