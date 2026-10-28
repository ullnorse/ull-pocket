# ull-pocket parts (stock checked on JLCPCB via pcbparts.dev, 2026-10-28)

| Ref | Function | Part | LCSC | Package | Note |
|---|---|---|---|---|---|
| U1 | MCU + Wi-Fi/BLE/802.15.4 | ESP32-C6-MINI-1-H4 | C6553337 | 16.6x13.2 module, PCB antenna | 4 MB flash; antenna at board edge with keep-out |
| U2 | Temp / RH | SHT31-DIS-B2.5kS | C80862 | DFN-8 2.5x2.5 | on thermally slotted tab; ull-sht3x driver exists |
| U3 | Pressure | BMP585 | C18184976 | LGA-8 3.3x3.3 (pads 1-8) | replaces BMP390 (not stocked); datasheet pin 9 is a laser-marking area, not a pad (removed from symbol and footprint); footprint has a via/track/pour keepout rule area over the body |
| U4 | Accelerometer | LIS3DHTR | C15134 | LGA-16 3x3 | INT1 to an LP GPIO for wake |
| U5 | Fuel gauge | MAX17048G+T10 | C2682616 | DFN-8 2x2 | |
| U6 | Li-ion charger, power path | BQ24073RGTR | C15220 | QFN-16 3x3 | 4.4 V OUT regulation; replaces BQ24074 (17 in stock) |
| U7 | 3.3 V LDO, ~2 uA Iq, 600 mA | RT9080-33GJ5 | C841192 | TSOT-23-5 | |
| C2 | U6 IN cap | CL10A105KB8NNNC 1uF/50V X5R | C15849 | 0603 | was 1uF/25V 0402 (C52923); 50 V rating for VBUS transients, basic part, 13M in stock |
| Q2 | Battery reverse-polarity FET (low side, BAT- lead) | AO3400A | C20917 | SOT-23 | basic part, 1.13M in stock; Vgs(max) 12 V; drain = BAT_N (J2 pin 1), source = GND, gate = VBAT via R11 100k |
| R13 | Sleep-current link, LDO_OUT to +3V3 | 0603WAF0000T5E 0R | C21189 | 0603 | basic part, 21.6M in stock; replace with an ammeter to measure sleep current |
| TP1-TP10 | Test pads: VBUS, VSYS, GND (x2), VBAT, +3V3, EN, BOOT, RXD0, TXD0 | TestPoint_Pad_1.0x1.0mm | - | 1.0 mm pad | footprint only, excluded from BOM |
| U8 | USB ESD | USBLC6-2SC6 | C2687116 | SOT-23-6 | |
| J1 | USB-C | TYPE-C-31-M-12 | C165948 | 16-pin SMD | 5.1k CC pull-downs |
| J2 | Battery | S2B-PH-SM4-TB | C295747 | JST-PH 2P SMD | 503040 LiPo with protection PCB; pin 2 = BAT+, pin 1 = BAT- (via Q2); silkscreen must mark + and - |
| J3 | E-paper FPC | FPC-05F-24PH20 | C2856805 | 24P 0.5 mm | verify contact side vs panel |
| SW1 | Side button | TS24CA (verify side-actuated) | C393942 | 4.6x1.8 | wake button on LP GPIO; locating pegs are 0.7 mm NPTH holes (no pad) |
| Q1 | E-paper boost switch | SI1308EDL-T1-GE3 | C469327 | SOT-323 | per panel reference circuit |
| D2-D4 | E-paper boost | MBR0530T1G | C82046 | SOD-123 | |
| D1 | CHG indicator (red) | KT-0603R | C2286 | 0603 | basic, 7.5M in stock; from VSYS via R6 1.5k: 1.3-1.7 mA, only while charging |
| D5 + R21 | Power LED (green), VBUS - 1.5k - LED - GND | KT-0603G | C12624 | 0603 | extended (no basic green 0603; basic green is 0805 C2297); 432k in stock; (5.0-2.8)/1.5k = 1.5 mA, 0 on battery. R21 = 0402WGF1501TCE C25867 (basic) |
| D6 + R22 | LED_USER1 yellow on IO5 (LP GPIO), 1k | KT-0805Y | C2296 | 0805 | basic, 671k in stock; ~1.35 mA. R22 = 0402WGF1001TCE C11702 (basic, 18M) |
| D7 + R23 | LED_USER2 white on IO14, 470R | KT-0603W | C2290 | 0603 | basic, 1.49M in stock; ~1.3 mA. R23 = 0402WGF4700TCE C25117 (basic, 1.1M). No basic blue exists; extended alternative KT-0603B C2288 (160k) |
| TH1 | Battery NTC on BQ24073 TS | SDNT1608X103F3435FTF 10k 1% B3435 | C525660 | 0603 | extended; 87.6k in stock; place under/against the cell. Window 0.5..50.8 C (75 uA bias: 28k / 4.0k trips); resume 3.9 / 47.9 C |
| R8 | TS fallback fixed 10k, parallel to TH1 | 0402WGF1002TCE | C25744 | 0402 | DNP; excluded from BOM and placement; fixed 10k = 25 C |
| L1 | E-paper boost | FNR4030S470MT 47 uH (Isat 1 A, Irms 800 mA, DCR 579 mR, 20%) | C167888 | 4x4x3 mm shielded | extended; 82k in stock; replaces SWPA4018S470MT (Isat 570 mA); panel reference needs 47 uH / 500 mA; footprint + 3D from easyeda2kicad, pads 1,2 match L_Small |
| DISP | E-paper panel | Good Display GDEY0154D67 (SSD1681, 200x200) | — | — | not at LCSC; hand-fit after assembly |
