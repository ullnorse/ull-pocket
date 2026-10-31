#!/usr/bin/env python3
"""Generate lib/ull-pocket.kicad_sym: clean project symbols.

IC symbols are drawn here from datasheet pin tables (cross-checked against the
easyeda2kicad symbols by tools/check_pins.py). Standard KiCad symbols used by the
project (passives, power, test point, USB-C, MOSFET, JST) are copied in so the
project library is self-contained.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import Q, dump, find, findall, parse, walk  # noqa: E402

STD = "/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/share/kicad/symbols"
OUT = os.path.join(os.path.dirname(__file__), "..", "lib", "ull-pocket.kicad_sym")
G = 2.54
CHW = 1.2  # approx char width (mm) of 1.27 mm KiCad font (measured from renders)


def fmt(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def eff(hide=False, justify=None):
    j = f" (justify {justify})" if justify else ""
    h = " (hide yes)" if hide else ""
    return f"(effects (font (size 1.27 1.27)){j}{h})"


def prop(name, value, x=0, y=0, hide=False, justify=None, rot=0):
    return (f'(property "{name}" "{value}" (at {fmt(x)} {fmt(y)} {rot}) (show_name no) (do_not_autoplace no) '
            f"{eff(hide, justify)})")


def pin(typ, x, y, ang, num, name, hide=False, length=G):
    h = " (hide yes)" if hide else ""
    return (f'(pin {typ} line (at {fmt(x)} {fmt(y)} {ang}) (length {fmt(length)}){h} '
            f'(name "{name}" {eff()}) (number "{num}" {eff()}))')


def tlen(s):
    import re
    s = re.sub(r"~\{([^}]*)\}", r"\1", s)
    return len(s)


def ic(name, ref, left=(), right=(), top=(), bottom=(), nc=(), fields=None, desc="", min_w=0,
       top_pitch=G, bottom_pitch=G):
    """Build an IC symbol. Entries: (nums, name, type) with nums 'a,b' stacked; None = gap.

    Layout rules: Reference above body (left). Value above body (stacked) when there are no
    top pins, else below body (left). Top/bottom pins are right-aligned when they could
    collide with the Reference/Value text; side pins start below the vertical pin-name
    region of top pins and end above that of bottom pins.
    """
    lmax = max([tlen(p[1]) for p in left if p] + [0])
    rmax = max([tlen(p[1]) for p in right if p] + [0])
    tmax = max([tlen(p[1]) for p in top if p] + [0])
    bmax = max([tlen(p[1]) for p in bottom if p] + [0])
    val_below = bool(top)
    w = (lmax + rmax) * CHW + 2.0
    w = max(w, (len(top) - 1) * top_pitch + 2 * G, (len(bottom) - 1) * bottom_pitch + 2 * G, min_w)
    if val_below and bottom:
        w = max(w, tlen(name) * CHW + 3.5 + (len(bottom) - 1) * bottom_pitch + G)
    if top:
        w = max(w, len(ref) * CHW + 2.5 + (len(top) - 1) * top_pitch + G)
    half_w = math.ceil(w / 2 / G) * G
    nside = max(len(left), len(right))
    t_res = math.ceil((tmax * CHW + 2.6) / G) * G if top else G
    b_res = math.ceil((bmax * CHW + 2.6) / G) * G if bottom else G
    # side pins must not sit under vertical names if those overlap side-name columns
    h = t_res + (nside - 1) * G + b_res if nside else t_res + b_res
    h = max(h, 2 * G)
    half_h = math.ceil(h / 2 / G) * G
    body = []
    pins = []

    def place(nums, nm, typ, x, y, ang):
        ns = [n.strip() for n in nums.split(",")]
        pins.append(pin(typ, x, y, ang, ns[0], nm))
        for n in ns[1:]:
            pins.append(pin("passive", x, y, ang, n, nm, hide=True))

    y0 = half_h - t_res
    for i, p in enumerate(left):
        if p:
            place(p[0], p[1], p[2], -half_w - G, y0 - i * G, 0)
    for i, p in enumerate(right):
        if p:
            place(p[0], p[1], p[2], half_w + G, y0 - i * G, 180)
    xs = half_w - G - (len(top) - 1) * top_pitch
    for i, p in enumerate(top):
        if p:
            place(p[0], p[1], p[2], xs + i * top_pitch, half_h + G, 270)
    if val_below:
        xs = half_w - G - (len(bottom) - 1) * bottom_pitch
    else:
        xs = round(-(len(bottom) - 1) * bottom_pitch / 2 / G) * G
    for i, p in enumerate(bottom):
        if p:
            place(p[0], p[1], p[2], xs + i * bottom_pitch, -half_h - G, 90)
    for i, (num, nm) in enumerate(nc):
        pins.append(pin("no_connect", -half_w + G + i * G, -half_h + G, 90, num, nm, hide=True, length=0))

    body.append(f"(rectangle (start {fmt(-half_w)} {fmt(half_h)}) (end {fmt(half_w)} {fmt(-half_h)}) "
                f"(stroke (width 0.254) (type default)) (fill (type background)))")
    f = dict(fields or {})
    if val_below:
        rp = prop("Reference", ref, -half_w, half_h + 0.635, justify="left bottom")
        vp = prop("Value", name, -half_w, -half_h - 0.635, justify="left top")
    else:
        rp = prop("Reference", ref, -half_w, half_h + 2.54, justify="left bottom")
        vp = prop("Value", name, -half_w, half_h + 0.635, justify="left bottom")
    props = [
        rp, vp,
        prop("Footprint", f.pop("Footprint", ""), hide=True),
        prop("Datasheet", f.pop("Datasheet", ""), hide=True),
        prop("Description", desc, hide=True),
    ]
    for k, v in f.items():
        props.append(prop(k, v, hide=True))
    return (f'(symbol "{name}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes) '
            f"(in_pos_files yes) (duplicate_pin_numbers_are_jumpers no) "
            + " ".join(props)
            + f' (symbol "{name}_0_1" ' + " ".join(body) + ")"
            + f' (symbol "{name}_1_1" ' + " ".join(pins) + ")"
            + " (embedded_fonts no))")


def std(libdir, name):
    path = os.path.join(STD, f"{libdir}.kicad_symdir", f"{name}.kicad_sym")
    t = parse(open(path).read())
    s = find(t, "symbol")
    assert s[1] == name, s[1]
    return s


def rename(sym, new):
    old = sym[1]
    sym[1] = Q(new)
    for n in walk(sym):
        if n and n[0] == "symbol" and isinstance(n[1], str) and n[1].startswith(old + "_"):
            n[1] = Q(new + n[1][len(old):])
    return sym


def setprop(sym, key, value, hide=None):
    for p in findall(sym, "property"):
        if p[1] == key:
            p[2] = Q(value)
            return p
    # add new hidden property after last property
    idx = max(i for i, c in enumerate(sym) if isinstance(c, list) and c and c[0] == "property")
    newp = parse(prop(key, value, hide=True))
    sym.insert(idx + 1, newp)
    return newp


def power_from_vdd(net, desc):
    s = rename(std("power", "VDD"), net)
    setprop(s, "Value", net)
    setprop(s, "Description", desc)
    for n in walk(s):
        if n and n[0] == "pin":
            nm = find(n, "name")
            if nm[1] == "VDD":
                nm[1] = Q(net)
    for p in findall(s, "property"):
        if p[1] == "ki_keywords":
            p[2] = Q("global power")
    return s


def main():
    out = []
    LCSC = "LCSC"

    def F(fp, ds, mpn, mfr, lcsc):
        return {"Footprint": fp, "Datasheet": ds, "MPN": mpn, "Manufacturer": mfr, LCSC: lcsc}

    # ---------------- ESP32-C6-MINI-1-H4 ----------------
    out.append(ic(
        "ESP32-C6-MINI-1-H4", "U",
        left=[("8", "EN", "input"), None, ("23", "IO9", "bidirectional"), None, ("22", "IO8", "bidirectional"),
              None, ("20", "IO15", "bidirectional"), None,
              ("17", "IO12", "bidirectional"), ("18", "IO13", "bidirectional"), None,
              ("30", "RXD0", "bidirectional"), ("31", "TXD0", "bidirectional")],
        right=[("12", "IO0", "bidirectional"), ("13", "IO1", "bidirectional"), ("5", "IO2", "bidirectional"),
               ("6", "IO3", "bidirectional"), ("9", "IO4", "bidirectional"), ("10", "IO5", "bidirectional"),
               ("15", "IO6", "bidirectional"), ("16", "IO7", "bidirectional"), None,
               ("19", "IO14", "bidirectional"), ("24", "IO18", "bidirectional"), ("25", "IO19", "bidirectional"),
               ("26", "IO20", "bidirectional"), ("27", "IO21", "bidirectional"), ("28", "IO22", "bidirectional"),
               ("29", "IO23", "bidirectional")],
        top=[("3", "3V3", "power_in")],
        bottom=[("1,2,11,14," + ",".join(str(i) for i in range(36, 54)), "GND", "power_in")],
        nc=[("4", "NC"), ("7", "NC"), ("21", "NC"), ("32", "NC"), ("33", "NC"), ("34", "NC"), ("35", "NC")],
        fields=F("RF_Module:ESP32-C6-MINI-1",
                 "https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_mini-1u_datasheet_en.pdf",
                 "ESP32-C6-MINI-1-H4", "Espressif Systems", "C6553337"),
        desc="ESP32-C6 module, Wi-Fi 6/BLE/802.15.4, 4 MB flash, PCB antenna", min_w=20.32))

    # ---------------- SHT31-DIS-B ----------------
    out.append(ic(
        "SHT31-DIS-B", "U",
        left=[("1", "SDA", "bidirectional"), ("4", "SCL", "input"), None, ("2", "ADDR", "input")],
        right=[("3", "ALERT", "output"), ("6", "NRESET", "input")],
        top=[("5", "VDD", "power_in")],
        bottom=[("8,9", "VSS", "power_in"), ("7", "R", "passive")],
        fields=F("Sensor_Humidity:Sensirion_DFN-8-1EP_2.5x2.5mm_P0.5mm_EP1.1x1.7mm",
                 "https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf",
                 "SHT31-DIS-B2.5kS", "Sensirion", "C80862"),
        desc="Digital humidity and temperature sensor, I2C, DFN-8", bottom_pitch=2 * G))

    # ---------------- BMP585 ----------------
    out.append(ic(
        "BMP585", "U",
        left=[("7", "CSB", "input"), None, ("2", "SDX", "bidirectional"), ("1", "SCX", "input"), None,
              ("3", "SDO", "passive")],
        right=[("5", "INT", "output")],
        top=[("4", "VDDIO", "power_in"), ("8", "VDD", "power_in")],
        bottom=[("6", "VSSIO/VSS", "power_in")],
        fields=F("ull-pocket:LGA-9_L3.3-W3.3-P1.10-TL",
                 "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp585-ds003.pdf",
                 "BMP585", "Bosch Sensortec", "C18184976"),
        desc="Barometric pressure sensor, I2C/I3C/SPI, LGA-9 (pin 9 marking area is not a pad)", top_pitch=2 * G))

    # ---------------- LIS3DHTR ----------------
    out.append(ic(
        "LIS3DHTR", "U",
        left=[("8", "CS", "input"), ("7", "SDO/SA0", "passive"), None,
              ("6", "SDA/SDI/SDO", "bidirectional"), ("4", "SCL/SPC", "input")],
        right=[("11", "INT1", "output"), ("9", "INT2", "output"), ("16", "ADC1", "passive"),
               ("15", "ADC2", "passive"), ("13", "ADC3", "passive")],
        top=[("1", "VDD_IO", "power_in"), ("14", "VDD", "power_in")],
        bottom=[("5,12", "GND", "power_in"), ("10", "RES", "passive")],
        nc=[("2", "NC"), ("3", "NC")],
        fields=F("Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y",
                 "https://www.st.com/resource/en/datasheet/lis3dh.pdf",
                 "LIS3DHTR", "STMicroelectronics", "C15134"),
        desc="3-axis accelerometer, I2C/SPI, LGA-16", top_pitch=2 * G, bottom_pitch=2 * G))

    # ---------------- MAX17048G+T10 ----------------
    out.append(ic(
        "MAX17048G+T10", "U",
        left=[("2", "CELL", "passive"), ("1", "CTG", "passive"), ("6", "QSTRT", "input")],
        right=[("8", "SDA", "bidirectional"), ("7", "SCL", "input"), ("5", "~{ALRT}", "open_collector")],
        top=[("3", "VDD", "power_in")],
        bottom=[("4,9", "GND", "power_in")],
        fields=F("ull-pocket:TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2",
                 "https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf",
                 "MAX17048G+T10", "Analog Devices", "C2682616"),
        desc="1-cell Li-ion fuel gauge, ModelGauge, I2C, 3 uA hibernate"))

    # ---------------- BQ24073RGTR ----------------
    out.append(ic(
        "BQ24073RGTR", "U",
        left=[("13", "IN", "power_in"), None, None, None, ("6", "EN1", "input"), ("5", "EN2", "input"),
              ("4", "~{CE}", "input"), ("15", "TD", "input")],
        right=[("10,11", "OUT", "power_out"), None, None, None, ("2,3", "BAT", "passive"), None, None,
               None, ("9", "~{CHG}", "open_collector"), ("7", "~{PGOOD}", "open_collector")],
        bottom=[("1", "TS", "passive"), ("16", "ISET", "passive"), ("12", "ILIM", "passive"),
                ("14", "TMR", "passive"), ("8,17", "VSS", "power_in")],
        fields=F("ull-pocket:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm",
                 "https://www.ti.com/lit/ds/symlink/bq24073.pdf",
                 "BQ24073RGTR", "Texas Instruments", "C15220"),
        desc="1-cell Li-ion charger with power path, 4.4 V OUT regulation, QFN-16",
        bottom_pitch=4 * G))

    # ---------------- RT9080-33GJ5 ----------------
    out.append(ic(
        "RT9080-33GJ5", "U",
        left=[("1", "VIN", "power_in"), ("3", "EN", "input")],
        right=[("5", "VOUT", "power_out")],
        bottom=[("2", "GND", "power_in")],
        nc=[("4", "NC")],
        fields=F("Package_TO_SOT_SMD:TSOT-23-5",
                 "https://www.richtek.com/assets/product_file/RT9080/DS9080-05.pdf",
                 "RT9080-33GJ5", "Richtek", "C841192"),
        desc="3.3 V 600 mA LDO, 2 uA Iq, TSOT-23-5"))

    # ---------------- USBLC6-2SC6 ----------------
    out.append(ic(
        "USBLC6-2SC6", "U",
        left=[("1", "I/O1", "passive"), ("3", "I/O2", "passive")],
        right=[("6", "I/O1", "passive"), ("4", "I/O2", "passive")],
        top=[("5", "VBUS", "power_in")],
        bottom=[("2", "GND", "power_in")],
        fields=F("Package_TO_SOT_SMD:SOT-23-6",
                 "https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
                 "USBLC6-2SC6", "UMW", "C2687116"),
        desc="2-line USB ESD protection with VBUS clamp, SOT-23-6"))

    # ---------------- FPC 24P (e-paper) ----------------
    panel = ["NC", "GDR", "RESE", "NC", "VSH2", "TSCL", "TSDA", "BS", "BUSY", "RES#", "D/C#", "CS#",
             "SCL", "SDA", "VDDIO", "VCI", "VSS", "VDD", "VPP", "VSH1", "VGH", "VSL", "VGL", "VCOM"]
    out.append(ic(
        "FPC-05FB-24PH20", "J",
        right=[e for i in range(24) for e in ([(str(i + 1), panel[i], "passive")] +
                                              ([None] if 14 <= i < 23 else []))],
        bottom=[("25", "MP", "passive"), ("26", "MP", "passive")],
        fields=F("ull-pocket:FPC-SMD_24P-P0.50_FPC-05FB-24PH20",
                 "https://www.lcsc.com/datasheet/C2856831.pdf",
                 "FPC-05FB-24PH20", "XUNPU", "C2856831"),
        desc="FPC connector 24P 0.5 mm, back flip lock, dual (top+bottom) contact; pin names = GDEY0154D67 panel pins",
        bottom_pitch=2 * G))

    # ---------------- PROG: 6-pad pogo programming cluster (no BOM, no placement) ----------------
    prog = ic(
        "PROG", "J",
        right=[("1", "VREF", "passive"), ("2", "GND", "passive"), ("3", "EN", "passive"),
              ("4", "IO9/BOOT", "passive"), ("5", "TXD0", "passive"), ("6", "RXD0", "passive")],
        fields=F("ull-pocket:PogoPads_2x3_P2.54mm_D1.0",
                 "", "PROG", "-", "-"),
        desc="Programming pads: 2x3 grid, 2.54 mm pitch, 1.0 mm round SMD pads; pad 1 VREF is sense-only (1k from +3V3)")
    prog = prog.replace("(in_bom yes)", "(in_bom no)", 1).replace("(in_pos_files yes)", "(in_pos_files no)", 1)
    out.append(prog)

    # ---------------- TS24CA side switch ----------------
    sw = ('(symbol "TS24CA" (pin_names (offset 1.016) (hide yes)) (exclude_from_sim no) (in_bom yes) (on_board yes) '
          '(in_pos_files yes) (duplicate_pin_numbers_are_jumpers no) '
          + prop("Reference", "SW", 0, 5.334) + " " + prop("Value", "TS24CA", 0, 3.556)
          + " " + prop("Footprint", "ull-pocket:SW-SMD_2P-TS24CA", hide=True)
          + " " + prop("Datasheet", "https://www.lcsc.com/datasheet/C393942.pdf", hide=True)
          + " " + prop("Description", "Side-actuated SMD tactile switch 4.7x1.9 mm, SPST-NO; pins 3/4 = shell tabs", hide=True)
          + " " + prop("MPN", "TS24CA", hide=True) + " " + prop("Manufacturer", "SHOU HAN", hide=True)
          + " " + prop("LCSC", "C393942", hide=True)
          + ' (symbol "TS24CA_0_1" '
          '(circle (center -2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none))) '
          '(circle (center 2.032 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none))) '
          '(polyline (pts (xy -2.54 1.524) (xy 2.54 1.524)) (stroke (width 0) (type default)) (fill (type none))) '
          '(polyline (pts (xy 0 1.524) (xy 0 2.54)) (stroke (width 0) (type default)) (fill (type none))) '
          '(polyline (pts (xy 0 -0.508) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none))) '
          ') (symbol "TS24CA_1_1" '
          + pin("passive", -5.08, 0, 0, "1", "1") + " " + pin("passive", 5.08, 0, 180, "2", "2")
          + " " + pin("passive", 0, -3.81, 90, "3", "MP", length=2.54)
          + " " + pin("passive", 0, -3.81, 90, "4", "MP", hide=True, length=2.54)
          + ") (embedded_fonts no))")
    out.append(sw)

    text = "(kicad_symbol_lib (version 20251024) (generator \"kicad_symbol_editor\") (generator_version \"10.0\") " \
        + " ".join(out) + ")"
    lib = parse(text)

    # ---------------- copied standard symbols ----------------
    for libdir, name, new in [("Device", "R_Small_US", None), ("Device", "C_Small", None),
                              ("Device", "L_Small", None), ("Device", "LED_Small", None), ("Device", "Thermistor_NTC_US", None),
                              ("Device", "D_Schottky_Small", None), ("Connector", "TestPoint", None),
                              ("power", "GND", None), ("power", "PWR_FLAG", None)]:
        lib.append(std(libdir, name))

    for net, d in [("+3V3", "3.3 V system rail (RT9080 output)"), ("VBUS", "USB-C VBUS"),
                   ("VSYS", "BQ24073 power-path output"), ("VBAT", "Li-ion cell positive")]:
        lib.append(power_from_vdd(net, d))

    usb = rename(std("Connector", "USB_C_Receptacle_USB2.0_16P"), "TYPE-C-31-M-12")
    setprop(usb, "Value", "TYPE-C-31-M-12")
    setprop(usb, "Footprint", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12")
    setprop(usb, "Datasheet", "https://www.lcsc.com/datasheet/C165948.pdf")
    setprop(usb, "MPN", "TYPE-C-31-M-12")
    setprop(usb, "Manufacturer", "Korean Hroparts Elec")
    setprop(usb, "LCSC", "C165948")
    lib.append(usb)

    q = rename(std("Device", "Q_NMOS"), "SI1308EDL")
    setprop(q, "Value", "SI1308EDL")
    numap = {"G": "1", "S": "2", "D": "3"}
    for n in walk(q):
        if n and n[0] == "pin":
            num = find(n, "number")
            num[1] = Q(numap[num[1]])
    setprop(q, "Footprint", "Package_TO_SOT_SMD:SOT-323_SC-70")
    setprop(q, "Datasheet", "https://www.vishay.com/docs/63399/si1308edl.pdf")
    setprop(q, "Description", "N-MOSFET 30 V 1.5 A, Vgs(th) <= 1.5 V, SOT-323 (1=G 2=S 3=D)")
    setprop(q, "MPN", "SI1308EDL-T1-GE3")
    setprop(q, "Manufacturer", "Vishay")
    setprop(q, "LCSC", "C469327")
    lib.append(q)

    q2 = rename(std("Device", "Q_NMOS"), "AO3400A")
    setprop(q2, "Value", "AO3400A")
    for n in walk(q2):
        if n and n[0] == "pin":
            num = find(n, "number")
            num[1] = Q(numap[num[1]])
    setprop(q2, "Footprint", "Package_TO_SOT_SMD:SOT-23")
    setprop(q2, "Datasheet", "https://www.lcsc.com/datasheet/lcsc_datasheet_1811081213_Alpha---Omega-Semicon-AO3400A_C20917.pdf")
    setprop(q2, "Description", "N-MOSFET 30 V 5.7 A, Vgs(max) 12 V, SOT-23 (1=G 2=S 3=D)")
    setprop(q2, "MPN", "AO3400A")
    setprop(q2, "Manufacturer", "Alpha & Omega Semicon")
    setprop(q2, "LCSC", "C20917")
    lib.append(q2)

    jst = rename(std("Connector_Generic_MountingPin", "Conn_01x02_MountingPin"), "S2B-PH-SM4-TB")
    for n in walk(jst):  # drop the body "Mounting" text: it overlaps the MP stub in the schematic
        if n and n[0] == "symbol":
            n[:] = [c for c in n if not (isinstance(c, list) and c and c[0] == "text")]
    setprop(jst, "Value", "S2B-PH-SM4-TB")
    setprop(jst, "Footprint", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal")
    setprop(jst, "Datasheet", "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf")
    setprop(jst, "Description", "JST PH 2-pin SMD right-angle battery connector")
    setprop(jst, "MPN", "S2B-PH-SM4-TB(LF)(SN)")
    setprop(jst, "Manufacturer", "JST")
    setprop(jst, "LCSC", "C295747")
    lib.append(jst)

    with open(OUT, "w") as fh:
        fh.write(dump(lib) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
