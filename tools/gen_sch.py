#!/usr/bin/env python3
"""Generate ull-pocket.kicad_sch (single A3 sheet) from a placement script.

All symbols come from lib/ull-pocket.kicad_sym. Coordinates in mm, screen y down.
Run tools/build_sch.sh afterwards (KiCad round-trip + ERC + renders).
"""
import math
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from sexp import Q, dump, find, findall, parse, walk  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = os.path.join(ROOT, "lib", "ull-pocket.kicad_sym")
SCH = os.path.join(ROOT, "ull-pocket.kicad_sch")
TEMPLATE = os.path.join(ROOT, "tools", "template.kicad_sch")
G = 2.54

_lib = {str(s[1]): s for s in findall(parse(open(LIB).read()), "symbol")}
_ucount = [0]


def uid():
    _ucount[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ull-pocket/{_ucount[0]}"))


def r3(v):
    return round(v * 1000) / 1000


def fmt(v):
    s = f"{r3(v):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pins_of(name):
    out = {}
    for n in walk(_lib[name]):
        if n and n[0] == "pin":
            num = str(find(n, "number")[1])
            at = find(n, "at")
            if num not in out:
                out[num] = (float(at[1]), float(at[2]), float(at[3]))
    return out


def props_of(name):
    d = {}
    for p in findall(_lib[name], "property"):
        d[str(p[1])] = (str(p[2]), p)
    return d


ITEMS = []      # sexp text snippets
WIRES = []      # (x1,y1,x2,y2)
PINPTS = []     # all symbol pin connection points
USED = set()
REFCOUNT = {}
ROOT_UUID = None


class Part:
    def __init__(self, lib, ref, x, y, rot=0, value=None, fields=None, fpos=None, in_bom=True,
                 hide_ref=False, hide_value=False):
        x, y = r3(x), r3(y)
        self.lib, self.ref, self.x, self.y, self.rot = lib, ref, x, y, rot
        self.pins = pins_of(lib)
        USED.add(lib)
        lp = props_of(lib)
        val = value if value is not None else lp["Value"][0]
        fields = dict(fields or {})
        fpos = dict(fpos or {})
        props = []
        order = ["Reference", "Value", "Footprint", "Datasheet", "Description"]
        allkeys = order + [k for k in lp if k not in order and not k.startswith("ki_")] + \
            [k for k in fields if k not in lp and k not in order]
        for k in allkeys:
            if k == "Reference":
                v = ref
            elif k == "Value":
                v = val
            else:
                v = fields.get(k, lp.get(k, ("", None))[0])
            hide = k not in ("Reference", "Value") or (k == "Reference" and hide_ref) or \
                (k == "Value" and hide_value)
            if k in fpos:
                px, py, just = fpos[k]
                if just and self.rot in (90, 180):
                    # field angle + symbol angle = 180 -> KiCad flips text, so mirror justification
                    just = just.replace("left", "@").replace("right", "left").replace("@", "right")
            elif k in ("Reference", "Value") and k in lp:
                at = find(lp[k][1], "at")
                ax, ay = self._xf(float(at[1]), float(at[2]))
                px, py = ax, ay
                j = find(find(lp[k][1], "effects"), "justify")
                just = " ".join(str(a) for a in j[1:]) if j else None
                if just and self.rot in (180,):
                    just = just.replace("left", "@").replace("right", "left").replace("@", "right")
            else:
                px, py, just = self.x, self.y, None
            jtxt = f" (justify {just})" if just else ""
            htxt = " (hide yes)" if hide else ""
            v = v.replace("\\", "\\\\").replace('"', '\\"')
            props.append(f'(property "{k}" "{v}" (at {fmt(px)} {fmt(py)} {self.rot % 180}) '
                         f'(effects (font (size 1.27 1.27)){jtxt}{htxt}))')
        pins = " ".join(f'(pin "{n}" (uuid "{uid()}"))' for n in self.pins)
        # include hidden stacked pins too
        allnums = []
        for n in walk(_lib[lib]):
            if n and n[0] == "pin":
                allnums.append(str(find(n, "number")[1]))
        pins = " ".join(f'(pin "{n}" (uuid "{uid()}"))' for n in dict.fromkeys(allnums))
        bom = "yes" if in_bom else "no"
        ITEMS.append(
            f'(symbol (lib_id "ull-pocket:{lib}") (at {fmt(x)} {fmt(y)} {rot}) (unit 1) '
            f'(exclude_from_sim no) (in_bom {bom}) (on_board yes) (dnp no) (uuid "{uid()}") '
            + " ".join(props) + " " + pins
            + f' (instances (project "ull-pocket" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1)))))')
        for n in self.pins:
            PINPTS.append(self.p(n))

    def _xf(self, lx, ly):
        a = math.radians(self.rot)
        rx = lx * math.cos(a) - ly * math.sin(a)
        ry = lx * math.sin(a) + ly * math.cos(a)
        return r3(self.x + rx), r3(self.y - ry)

    def p(self, num):
        lx, ly, _ = self.pins[str(num)]
        return self._xf(lx, ly)

    def out(self, num):
        """Unit vector pointing away from the body at pin num (screen coords)."""
        _, _, ang = self.pins[str(num)]
        a = math.radians(ang + 180 + self.rot)
        return (round(math.cos(a)), round(-math.sin(a)))


def nextref(prefix):
    REFCOUNT[prefix] = REFCOUNT.get(prefix, 0) + 1
    return f"{prefix}{REFCOUNT[prefix]}"


def wire(*pts):
    pts = [(r3(p[0]), r3(p[1])) for p in pts]
    for a, b in zip(pts, pts[1:]):
        if a == b:
            continue
        assert a[0] == b[0] or a[1] == b[1], f"non-orthogonal wire {a}->{b}"
        WIRES.append((r3(a[0]), r3(a[1]), r3(b[0]), r3(b[1])))
        ITEMS.append(f'(wire (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})) '
                     f'(stroke (width 0) (type default)) (uuid "{uid()}"))')


def label(name, pt, d):
    """d: direction text extends: 'R','L','U','D'."""
    ang, just = {"R": (0, "left bottom"), "L": (180, "right bottom"),
                 "U": (90, "left bottom"), "D": (270, "right bottom")}[d]
    ITEMS.append(f'(label "{name}" (at {fmt(pt[0])} {fmt(pt[1])} {ang}) '
                 f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid()}"))')


def nc(pt):
    ITEMS.append(f'(no_connect (at {fmt(pt[0])} {fmt(pt[1])}) (uuid "{uid()}"))')


PWR_N = [0]


def pwr(name, pt):
    PWR_N[0] += 1
    if name == "PWR_FLAG":
        ref = f"#FLG0{PWR_N[0]:02d}"
        Part("PWR_FLAG", ref, pt[0], pt[1], hide_ref=True)
    else:
        ref = f"#PWR0{PWR_N[0]:02d}"
        Part(name, ref, pt[0], pt[1], hide_ref=True, hide_value=(name == "GND"))


def rect(x1, y1, x2, y2, rgb, title):
    r, g, b = rgb
    ITEMS.append(f'(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) '
                 f'(stroke (width 0.3) (type default) (color {r} {g} {b} 1)) '
                 f'(fill (type color) (color {r} {g} {b} 0.08)) (uuid "{uid()}"))')
    ITEMS.append(f'(text "{title}" (exclude_from_sim no) (at {fmt(x1 + 1.27)} {fmt(y1 + 1.27)} 0) '
                 f'(effects (font (size 2.54 2.54) (thickness 0.508) (bold yes) (color {r} {g} {b} 1)) '
                 f'(justify left top)) (uuid "{uid()}"))')


def note(text, pt, size=1.27):
    ITEMS.append(f'(text "{text}" (exclude_from_sim no) (at {fmt(pt[0])} {fmt(pt[1])} 0) '
                 f'(effects (font (size {size} {size})) (justify left top)) (uuid "{uid()}"))')


def add(a, d, k=1.0):
    return (r3(a[0] + d[0] * k), r3(a[1] + d[1] * k))


def stub(part, num, name, length=G):
    p = part.p(num)
    d = part.out(num)
    e = add(p, d, length)
    wire(p, e)
    label(name, e, {(1, 0): "R", (-1, 0): "L", (0, -1): "U", (0, 1): "D"}[d])
    return e


def pin_nc(part, num):
    nc(part.p(num))


def pin_pwr(part, num, name, length=G):
    p = part.p(num)
    e = add(p, part.out(num), length)
    wire(p, e)
    pwr(name, e)
    return e


# --------------------------------------------------------------- passives
FP = {"0402R": "Resistor_SMD:R_0402_1005Metric", "0603R": "Resistor_SMD:R_0603_1608Metric",
      "0402C": "Capacitor_SMD:C_0402_1005Metric", "0603C": "Capacitor_SMD:C_0603_1608Metric",
      "0805C": "Capacitor_SMD:C_0805_2012Metric"}
UNIROYAL = "UNI-ROYAL(Uniroyal Elec)"
SEMCO = "Samsung Electro-Mechanics"
PARTS = {
    "10k": ("10kR", "0402R", "0402WGF1002TCE", UNIROYAL, "C25744", "Resistor 10k 1% 0402"),
    "5k1": ("5.1kR", "0402R", "0402WGF5101TCE", UNIROYAL, "C25905", "Resistor 5.1k 1% 0402"),
    "100k": ("100kR", "0402R", "0402WGF1003TCE", UNIROYAL, "C25741", "Resistor 100k 1% 0402"),
    "3k3": ("3.3kR", "0402R", "0402WGF3301TCE", UNIROYAL, "C25890", "Resistor 3.3k 1% 0402"),
    "1k5": ("1.5kR", "0402R", "0402WGF1501TCE", UNIROYAL, "C25867", "Resistor 1.5k 1% 0402"),
    "1M": ("1MR", "0402R", "0402WGF1004TCE", UNIROYAL, "C26083", "Resistor 1M 1% 0402"),
    "1M_0603": ("1MR", "0603R", "0603WAF1004T5E", UNIROYAL, "C22935", "Resistor 1M 1% 0603"),
    "2R2_0603": ("2.2R", "0603R", "0603WAF220KT5E", UNIROYAL, "C22939", "Resistor 2.2R 1% 0603"),
    "100n": ("100nF/16V", "0402C", "CL05B104KO5NNNC", SEMCO, "C1525", "MLCC 100nF 16V X7R 0402"),
    "1u": ("1uF/25V", "0402C", "CL05A105KA5NQNC", SEMCO, "C52923", "MLCC 1uF 25V X5R 0402"),
    "10u": ("10uF/10V", "0603C", "CL10A106KP8NNNC", SEMCO, "C19702", "MLCC 10uF 10V X5R 0603"),
    "4n7": ("4.7nF/50V", "0402C", "0402B472K500NT", "FH(Guangdong Fenghua Advanced Tech)", "C1538",
            "MLCC 4.7nF 50V X7R 0402"),
    "1u50": ("1uF/50V", "0603C", "CL10A105KB8NNNC", SEMCO, "C15849", "MLCC 1uF 50V X5R 0603"),
    "4u7_25": ("4.7uF/25V", "0805C", "CL21A475KAQNNNE", SEMCO, "C1779", "MLCC 4.7uF 25V X5R 0805"),
}


def _passive(lib, prefix, key, c, orient, side="R"):
    val, fpk, mpn, mfr, lcsc, desc = PARTS[key]
    rot = 0 if orient == "V" else 90
    ref = nextref(prefix)
    x, y = c
    if orient == "V":
        if side == "R":
            fpos = {"Reference": (x + 1.524, y - 0.889, "left"), "Value": (x + 1.524, y + 0.889, "left")}
        else:
            fpos = {"Reference": (x - 1.524, y - 0.889, "right"), "Value": (x - 1.524, y + 0.889, "right")}
    else:
        if side == "R":  # text above/below
            fpos = {"Reference": (x, y - 2.286, None), "Value": (x, y + 2.286, None)}
        elif side == "B":  # both below
            fpos = {"Reference": (x, y + 2.286, None), "Value": (x, y + 4.064, None)}
        else:
            fpos = {"Reference": (x, y - 3.81, None), "Value": (x, y - 2.286, None)}
    return Part(lib, ref, x, y, rot, value=val,
                fields={"Footprint": FP[fpk], "MPN": mpn, "Manufacturer": mfr, "LCSC": lcsc,
                        "Description": desc}, fpos=fpos)


def R(key, c, orient="V", side="R"):
    return _passive("R_Small_US", "R", key, c, orient, side)


def C(key, c, orient="V", side="R"):
    return _passive("C_Small", "C", key, c, orient, side)


def cap_down(key, top, side="R", gnd=True):
    """Vertical cap whose pin1 sits at `top`; GND symbol at its bottom."""
    c = C(key, (top[0], top[1] + G), "V", side)
    if gnd:
        pwr("GND", c.p(2))
    return c


def res_down(key, top, side="R", gnd=True):
    r = R(key, (top[0], top[1] + G), "V", side)
    if gnd:
        pwr("GND", r.p(2))
    return r


def res_up(key, bottom, rail, side="R"):
    r = R(key, (bottom[0], bottom[1] - G), "V", side)
    pwr(rail, r.p(1))
    return r


def ic(lib, ref, x, y, **kw):
    return Part(lib, ref, x, y, 0, **kw)


def tp(name, pt, rot=0):
    """Test pad. rot 0: pad above the pin point; rot 90: pad to the left. Ref hidden, name shown."""
    ref = nextref("TP")
    if rot == 0:
        vx = (pt[0], pt[1] - 5.334, None)
    else:
        vx = (pt[0] - 4.826, pt[1], "right")
    return Part("TestPoint", ref, pt[0], pt[1], rot, value=name, in_bom=False, hide_ref=True,
                fields={"Footprint": "TestPoint:TestPoint_Pad_1.0x1.0mm",
                        "Description": "Test pad 1.0 mm square, not a BOM part"},
                fpos={"Reference": (pt[0], pt[1], None), "Value": vx})


def S(v):
    """snap to 1.27 grid"""
    return r3(round(v / 1.27) * 1.27)


# =============================================================== layout
def build():
    # ------------------------------------------------------------ colours
    C_USB = (0, 132, 80)
    C_PWR = (194, 24, 7)
    C_BAT = (204, 102, 0)
    C_LDO = (150, 60, 160)
    C_MCU = (0, 90, 200)
    C_SNS = (0, 128, 128)
    C_EPD = (110, 110, 0)
    C_UI = (90, 90, 90)

    # ============================ USB-C input + ESD =====================
    bx, by = 12.7, 12.7
    rect(bx, by, bx + 88.9, by + 69.85, C_USB, "USB-C INPUT + ESD")
    j1 = ic("TYPE-C-31-M-12", "J1", bx + 20.32, by + 35.56)
    vb = j1.p("A4")
    vbn = add(vb, (1, 0), 7.62)
    wire(vb, vbn)
    pwr("VBUS", vbn)
    vbf = add(vbn, (1, 0), 10.16)
    wire(vbn, vbf)
    pwr("PWR_FLAG", vbf)
    # CC pull-downs: Rd = 5.1k each (sink)
    cc1, cc2 = j1.p("A5"), j1.p("B5")
    x_cc2 = cc2[0] + 12.7
    x_cc1 = cc2[0] + 22.86
    wire(cc1, (x_cc1, cc1[1]))
    wire(cc2, (x_cc2, cc2[1]))
    res_down("5k1", (x_cc1, cc1[1]))
    res_down("5k1", (x_cc2, cc2[1]))
    for pn, nm in (("A6", "USB_D+"), ("B6", "USB_D+"), ("A7", "USB_D-"), ("B7", "USB_D-")):
        stub(j1, pn, nm)
    pin_nc(j1, "A8")
    pin_nc(j1, "B8")
    g = j1.p("A1")
    pwr("GND", g)
    sh = j1.p("SH")
    shn = add(sh, (0, 1), G)
    wire(sh, shn)
    xl, xr = shn[0] - 2.54, shn[0] + 2.54
    wire((xl, shn[1]), (xr, shn[1]))
    r_sh = R("1M", (xl, shn[1] + G), "V", side="L")
    c_sh = C("4n7", (xr, shn[1] + G), "V", side="R")
    bot = r_sh.p(2)
    wire(bot, c_sh.p(2))
    pwr("GND", (shn[0], bot[1]))
    u8 = ic("USBLC6-2SC6", "U8", bx + 63.5, by + 50.8)
    for pn, nm in (("1", "USB_D+"), ("3", "USB_D-"), ("6", "USB_D+"), ("4", "USB_D-")):
        stub(u8, pn, nm)
    pin_pwr(u8, "5", "VBUS")
    pin_pwr(u8, "2", "GND", 0)

    # ============================ Charger ==============================
    bx, by = 105.41, 12.7
    rect(bx, by, bx + 132.08, by + 69.85, C_PWR, "CHARGER + POWER PATH (BQ24073)")
    u6 = ic("BQ24073RGTR", "U6", bx + 50.8, by + 33.02)
    pin_in = u6.p("13")
    n_in = add(pin_in, (-1, 0), 7.62)
    wire(pin_in, n_in)
    pwr("VBUS", n_in)
    cap_down("1u", n_in, side="L")
    # EN1 = VBUS/2 (USB500 mode only while VBUS present; no drain from the cell)
    p_en1 = u6.p("6")
    n_en1 = add(p_en1, (-1, 0), 17.78)
    wire(p_en1, n_en1)
    r_top = R("100k", add(n_en1, (-1, 0), 7.62), "H", side="B")
    wire(r_top.p(2), n_en1)
    pwr("VBUS", r_top.p(1))
    res_down("100k", n_en1)
    xg = p_en1[0] - 2.54
    for pn in ("5", "4", "15"):
        wire(u6.p(pn), (xg, u6.p(pn)[1]))
    wire((xg, u6.p("5")[1]), (xg, u6.p("15")[1]))
    pwr("GND", (xg, u6.p("15")[1]))
    # OUT -> VSYS + 10uF
    p_out = u6.p("10")
    n_out = add(p_out, (1, 0), 7.62)
    wire(p_out, n_out)
    pwr("VSYS", n_out)
    cap_down("10u", n_out)
    # BAT -> VBAT + 10uF
    p_bat = u6.p("2")
    n_bat = add(p_bat, (1, 0), 15.24)
    wire(p_bat, n_bat)
    pwr("VBAT", n_bat)
    cap_down("10u", n_bat)
    # CHG -> LED (K) ; LED (A) -> 1.5k -> VSYS
    p_chg = u6.p("9")
    x_led = p_chg[0] + 25.4
    led_c = (x_led, p_chg[1] - G)
    led = Part("LED_Small", nextref("D"), led_c[0], led_c[1], 90, value="RED",
               fields={"Footprint": "LED_SMD:LED_0603_1608Metric", "MPN": "KT-0603R",
                       "Manufacturer": "Hubei KENTO Elec", "LCSC": "C2286",
                       "Description": "LED red 0603, charge indicator"},
               fpos={"Reference": (x_led + 1.524, led_c[1] - 0.889, "left"),
                     "Value": (x_led + 1.524, led_c[1] + 0.889, "left")})
    wire(p_chg, led.p("1"))
    r_led = R("1k5", (x_led, led.p("2")[1] - G))
    pwr("VSYS", r_led.p(1))
    # PGOOD -> 100k pull-up to 3V3 -> USB_PGOOD_N
    p_pg = u6.p("7")
    n_pg = add(p_pg, (1, 0), 43.18)
    wire(p_pg, n_pg)
    res_up("100k", n_pg, "+3V3", side="L")
    e_pg = add(n_pg, (1, 0), 2.54)
    wire(n_pg, e_pg)
    label("USB_PGOOD_N", e_pg, "R")
    # bottom: TS 10k (no NTC), ISET 3.3k, ILIM 3.3k, TMR open (default timers), VSS
    res_down("10k", u6.p("1"))
    res_down("3k3", u6.p("16"))
    res_down("3k3", u6.p("12"))
    pin_nc(u6, "14")
    pwr("GND", u6.p("8"))
    note("ICHG = KISET/RISET = 890/3.3k = 270 mA\\nUSB500: EN1=1, EN2=0 -> IIN <= 500 mA\\n"
         "TS: 10k fixed (no NTC), TMR open: 5 h timer", (bx + 78.74, by + 55.88))

    # ============================ Battery + gauge ======================
    bx, by = 241.3, 12.7
    rect(bx, by, bx + 68.58, by + 69.85, C_BAT, "BATTERY + FUEL GAUGE")
    j2 = Part("S2B-PH-SM4-TB", "J2", bx + 7.62, by + 17.78, 180,
              fpos={"Reference": (bx + 3.81, by + 10.16, None),
                    "Value": (bx + 13.97, by + 22.86, None)})
    p_bp = j2.p("2")   # pin 2 = BAT+, pin 1 = BAT- (assumed, see note)
    p_bn = j2.p("1")
    n_bp = add(p_bp, (1, 0), 5.08)
    wire(p_bp, n_bp)
    pwr("VBAT", n_bp)
    f_bp = add(n_bp, (1, 0), 10.16)
    wire(n_bp, f_bp)
    pwr("PWR_FLAG", f_bp)
    n_bn = add(p_bn, (1, 0), 5.08)
    wire(p_bn, n_bn)
    pwr("GND", n_bn)
    f_bn = add(n_bn, (1, 0), 25.4)
    wire(n_bn, f_bn)
    pwr("PWR_FLAG", f_bn)
    pin_nc(j2, "MP")
    note("J2: pin 2 = BAT+, pin 1 = BAT-\\n(verify against cell lead polarity)", (bx + 2.54, by + 26.67))

    u5 = ic("MAX17048G+T10", "U5", bx + 27.94, by + 50.8)
    p_vdd = u5.p("3")
    n_vdd = add(p_vdd, (0, -1), 5.08)
    wire(p_vdd, n_vdd)
    pwr("VBAT", n_vdd)
    c_g = add(n_vdd, (1, 0), 5.08)
    wire(n_vdd, c_g)
    cap_down("100n", c_g)
    p_cell = u5.p("2")
    n_cell = add(p_cell, (-1, 0), 7.62)
    wire(p_cell, n_cell)
    pwr("VBAT", n_cell)
    xg = p_cell[0] - 2.54
    wire(u5.p("1"), (xg, u5.p("1")[1]))
    wire(u5.p("6"), (xg, u5.p("6")[1]))
    wire((xg, u5.p("1")[1]), (xg, u5.p("6")[1]))
    pwr("GND", (xg, u5.p("6")[1]))
    stub(u5, "8", "I2C_SDA")
    stub(u5, "7", "I2C_SCL")
    p_al = u5.p("5")
    n_al = add(p_al, (1, 0), 12.7)
    wire(p_al, n_al)
    res_up("100k", n_al, "+3V3")
    e_al = add(n_al, (0, 1), 5.08)
    wire(n_al, e_al)
    label("BAT_ALRT_N", e_al, "L")
    pwr("GND", u5.p("4"))

    # ============================ 3V3 LDO ==============================
    bx, by = 313.69, 12.7
    rect(bx, by, bx + 66.04, by + 40.64, C_LDO, "3V3 LDO (RT9080)")
    u7 = ic("RT9080-33GJ5", "U7", bx + 33.02, by + 22.86)
    p_vin = u7.p("1")
    n_vin = add(p_vin, (-1, 0), 7.62)
    wire(p_vin, n_vin)
    pwr("VSYS", n_vin)
    cap_down("1u", n_vin, side="L")
    p_en = u7.p("3")
    x_e = p_en[0] - 2.54
    wire(p_en, (x_e, p_en[1]), (x_e, p_vin[1]))
    p_vo = u7.p("5")
    n_vo = add(p_vo, (1, 0), 7.62)
    wire(p_vo, n_vo)
    pwr("+3V3", n_vo)
    cap_down("1u", n_vo)
    pwr("GND", u7.p("2"))

    # ============================ MCU ==================================
    bx, by = 12.7, 86.36
    rect(bx, by, bx + 101.6, by + 93.98, C_MCU, "MCU (ESP32-C6-MINI-1)")
    u1 = ic("ESP32-C6-MINI-1-H4", "U1", bx + 60.96, by + 55.88)
    p33 = u1.p("3")
    n33 = add(p33, (0, -1), 10.16)
    wire(p33, n33)
    pwr("+3V3", n33)
    ca = add(n33, (-1, 0), 15.24)
    cb = add(n33, (-1, 0), 30.48)
    wire(n33, cb)
    c10 = cap_down("10u", ca, gnd=False)
    c01 = cap_down("100n", cb, gnd=False)
    wire(c01.p(2), c10.p(2))
    pwr("GND", c10.p(2))
    pwr("GND", u1.p("1"))
    # EN: 10k to 3V3 + 1uF to GND (Espressif RC), test pad
    p_en = u1.p("8")
    n_en = add(p_en, (-1, 0), 25.4)
    wire(p_en, n_en)
    res_up("10k", n_en, "+3V3", side="L")
    cap_down("1u", n_en, side="L")
    tp("EN", add(p_en, (-1, 0), 5.08))
    # IO9 = BOOT strap pad (internal pull-up); IO8 10k pull-up (download boot needs IO8=1)
    p9 = u1.p("23")
    e9 = add(p9, (-1, 0), 5.08)
    wire(p9, e9)
    tp("BOOT", e9, 90)
    p8 = u1.p("22")
    r8 = R("10k", add(p8, (-1, 0), 15.24), "H", side="B")
    wire(p8, r8.p(2))
    pwr("+3V3", r8.p(1))
    pin_nc(u1, "20")
    stub(u1, "17", "USB_D-")
    stub(u1, "18", "USB_D+")
    for pn, nm in (("30", "RXD0"), ("31", "TXD0")):
        p = u1.p(pn)
        e = add(p, (-1, 0), 5.08)
        wire(p, e)
        tp(nm, e, 90)
    gp = (u1.p("31")[0] - 5.08, u1.p("31")[1] + 7.62)
    tp("GND", gp, 0)
    pwr("GND", gp)
    for pn, nm in (("12", "BAT_ALRT_N"), ("13", "USB_PGOOD_N"), ("5", "BTN_N"), ("6", "ACC_INT1"),
                   ("15", "I2C_SDA"), ("16", "I2C_SCL"), ("19", "BARO_INT"), ("24", "EPD_BUSY"),
                   ("25", "EPD_RST_N"), ("26", "EPD_DC"), ("27", "EPD_CS_N"), ("28", "EPD_SCK"),
                   ("29", "EPD_MOSI")):
        stub(u1, pn, nm)
    for pn in ("9", "10"):
        pin_nc(u1, pn)
    note("LP GPIO (deep-sleep wake):\\nIO0 BAT_ALRT_N, IO1 USB_PGOOD_N,\\nIO2 BTN_N, IO3 ACC_INT1.\\n"
         "IO6/IO7 = LP_I2C SDA/SCL.\\nStraps: IO8 10k pull-up,\\nIO9 BOOT pad, IO15 open.",
         (bx + 2.54, by + 74.93))

    # ============================ Sensors ==============================
    bx, by = 118.11, 86.36
    rect(bx, by, bx + 233.68, by + 71.12, C_SNS, "SENSORS (I2C, 3V3)")
    px = bx + 12.7
    py = by + 27.94
    for i, nm in enumerate(("I2C_SDA", "I2C_SCL")):
        x = px + i * 12.7
        r = res_up("10k", (x, py), "+3V3")
        e = (x, py + 5.08)
        wire(r.p(2), e)
        label(nm, e, "D")
    note("I2C addresses:\\nSHT31 0x44 (ADDR=GND)\\nBMP585 0x46 (SDO=GND)\\nLIS3DH 0x19 (SA0=3V3)\\n"
         "MAX17048 0x36", (bx + 2.54, by + 50.8))

    def top_decouple(part, pins, caps_right, rise=12.7):
        pts = [part.p(p) for p in pins]
        y = pts[0][1] - rise
        for p in pts:
            wire(p, (p[0], y))
        wire((pts[0][0], y), (pts[-1][0], y))
        pwr("+3V3", (pts[-1][0], y))
        xr = pts[-1][0] + 7.62
        prev = pts[-1][0]
        for k in caps_right:
            wire((prev, y), (xr, y))
            cap_down(k, (xr, y))
            prev = xr
            xr += 15.24
        return y

    u2 = ic("SHT31-DIS-B", "U2", bx + 66.04, by + 50.8)
    top_decouple(u2, ["5"], ["100n"])
    stub(u2, "1", "I2C_SDA")
    stub(u2, "4", "I2C_SCL")
    pin_pwr(u2, "2", "GND")
    pin_nc(u2, "3")
    pin_nc(u2, "6")
    pwr("GND", u2.p("8"))
    pwr("GND", u2.p("7"))

    u3 = ic("BMP585", "U3", bx + 129.54, by + 45.72)
    yn = top_decouple(u3, ["4", "8"], ["100n", "100n"], rise=7.62)
    p_csb = u3.p("7")
    x_b = p_csb[0] - 2.54
    wire(p_csb, (x_b, p_csb[1]), (x_b, yn), (u3.p("4")[0], yn))
    stub(u3, "2", "I2C_SDA")
    stub(u3, "1", "I2C_SCL")
    pin_pwr(u3, "3", "GND")
    stub(u3, "5", "BARO_INT")
    pwr("GND", u3.p("6"))

    u4 = ic("LIS3DHTR", "U4", bx + 196.85, by + 48.26)
    yn = top_decouple(u4, ["1", "14"], ["100n", "100n", "10u"], rise=7.62)
    p_cs = u4.p("8")
    p_sa = u4.p("7")
    x_l = p_cs[0] - 2.54
    wire(p_sa, (x_l, p_sa[1]), (x_l, yn), (u4.p("1")[0], yn))
    wire(p_cs, (x_l, p_cs[1]))
    stub(u4, "6", "I2C_SDA")
    stub(u4, "4", "I2C_SCL")
    stub(u4, "11", "ACC_INT1")
    for pn in ("9", "16", "15", "13"):
        pin_nc(u4, pn)
    pwr("GND", u4.p("5"))
    pwr("GND", u4.p("10"))

    # ============================ Wake button ==========================
    bx, by = 118.11, 161.29
    rect(bx, by, bx + 66.04, by + 21.59, C_UI, "WAKE BUTTON (side)")
    sw1 = Part("TS24CA", "SW1", bx + 43.18, by + 13.97, 0)
    p1 = sw1.p("1")
    n1 = add(p1, (-1, 0), 12.7)
    wire(p1, n1)
    res_up("100k", n1, "+3V3")
    e1 = add(n1, (-1, 0), 2.54)
    wire(n1, e1)
    label("BTN_N", e1, "L")
    p2 = sw1.p("2")
    n2 = add(p2, (1, 0), 2.54)
    wire(p2, n2)
    pwr("GND", n2)
    pwr("GND", sw1.p("3"))

    # ============================ E-paper ==============================
    bx, by = 12.7, 184.15
    rect(bx, by, bx + 228.6, by + 99.06, C_EPD, "E-PAPER (GDEY0154D67 ref. circuit)")
    x0, y0 = bx + 15.24, by + 50.8
    pwr("+3V3", (x0, y0))
    cap_down("4u7_25", (x0, y0), side="L")
    l1 = Part("L_Small", "L1", x0 + 10.16, y0, 90, value="47uH",
              fields={"Footprint": "ull-pocket:IND-SMD_L4.0-W4.0_SWPA4018S", "MPN": "SWPA4018S470MT",
                      "Manufacturer": "Sunlord", "LCSC": "C83445",
                      "Description": "Power inductor 47uH 20% Isat 570mA 4x4x1.8mm"},
              fpos={"Reference": (x0 + 10.16, y0 - 2.286, None), "Value": (x0 + 10.16, y0 + 2.286, None)})
    wire((x0, y0), l1.p("1"))
    sw = (x0 + 22.86, y0)
    wire(l1.p("2"), sw)
    q1 = Part("SI1308EDL", "Q1", sw[0] - 2.54, sw[1] + 10.16, 0,
              fpos={"Reference": (sw[0] + 3.81, sw[1] + 9.271, "left"),
                    "Value": (sw[0] + 3.81, sw[1] + 11.049, "left")})
    wire(sw, q1.p("3"))
    pg = q1.p("1")
    ng = add(pg, (-1, 0), 5.08)
    wire(pg, ng)
    lg = add(ng, (-1, 0), 2.54)
    wire(ng, lg)
    label("EPD_GDR", lg, "L")
    res_down("1M_0603", ng, side="L")
    ps = q1.p("2")
    ns = add(ps, (0, 1), 2.54)
    wire(ps, ns)
    ls = add(ns, (1, 0), 5.08)
    wire(ns, ls)
    label("EPD_RESE", ls, "R")
    res_down("2R2_0603", ns, side="L")
    d_fields = {"Footprint": "Diode_SMD:D_SOD-123", "MPN": "MBR0530T1G", "Manufacturer": "onsemi",
                "LCSC": "C82046", "Description": "Schottky 30V 0.5A SOD-123"}

    def diode(c, rot):
        ref = nextref("D")
        fpos = {"Reference": (c[0], c[1] - 2.286, None), "Value": (c[0], c[1] + 2.286, None)}
        return Part("D_Schottky_Small", ref, c[0], c[1], rot, value="MBR0530", fields=d_fields, fpos=fpos)

    d3 = diode((sw[0] + 10.16, sw[1]), 180)       # SW -> PREVGH
    wire(sw, d3.p("2"))
    n_gh = add(d3.p("1"), (1, 0), 5.08)
    wire(d3.p("1"), n_gh)
    cap_down("1u50", n_gh)
    e_gh = add(n_gh, (1, 0), 7.62)
    wire(n_gh, e_gh)
    label("PREVGH", e_gh, "R")
    c3 = C("4u7_25", (sw[0], sw[1] - 7.62), "V", side="L")
    wire(sw, c3.p(2))
    nx = add(c3.p(1), (0, -1), 5.08)
    wire(c3.p(1), nx)
    d2 = diode((nx[0] + 10.16, nx[1]), 180)       # X -> GND (A at X)
    wire(nx, d2.p("2"))
    g2 = add(d2.p("1"), (1, 0), 5.08)
    wire(d2.p("1"), g2)
    pwr("GND", g2)
    ny = add(nx, (0, -1), 10.16)
    wire(nx, ny)
    d1 = diode((ny[0] + 10.16, ny[1]), 0)          # PREVGL -> X (K at X)
    wire(ny, d1.p("1"))
    e_gl = add(d1.p("2"), (1, 0), 12.7)
    wire(d1.p("2"), e_gl)
    label("PREVGL", e_gl, "R")
    cap_down("1u50", add(e_gl, (-1, 0), 5.08))

    j3 = ic("FPC-05F-24PH20", "J3", bx + 109.22, by + 50.8)
    P = lambda n: j3.p(str(n))  # noqa: E731
    for n in (1, 4, 6, 7, 19):
        nc(P(n))
    stub(j3, 2, "EPD_GDR")
    stub(j3, 3, "EPD_RESE")
    for n, nm in ((9, "EPD_BUSY"), (10, "EPD_RST_N"), (11, "EPD_DC"), (12, "EPD_CS_N"),
                  (13, "EPD_SCK"), (14, "EPD_MOSI")):
        stub(j3, n, nm)
    stub(j3, 21, "PREVGH")
    xbs = P(8)[0] + 20.32
    wire(P(8), (xbs, P(8)[1]))
    pwr("GND", (xbs, P(8)[1]))
    xc2 = P(5)[0] + 25.4
    wire(P(5), (xc2, P(5)[1]))
    cap_down("1u50", (xc2, P(5)[1]))
    # VGL (23): PREVGL label + C on the pin, staircase of panel caps (lower rows shorter)
    stub(j3, 23, "PREVGL")
    stair = [(24, 22.86), (22, 35.56), (20, 48.26), (18, 60.96)]
    for n, dx in stair:
        x = P(n)[0] + dx
        wire(P(n), (x, P(n)[1]))
        cap_down("1u50", (x, P(n)[1]))
    x17 = P(17)[0] + 73.66
    wire(P(17), (x17, P(17)[1]))
    pwr("GND", (x17, P(17)[1]))
    x16 = P(16)[0] + 86.36
    wire(P(16), (x16, P(16)[1]))
    cap_down("1u50", (x16, P(16)[1]))
    x15 = P(15)[0] + 78.74
    wire(P(15), (x15, P(15)[1]), (x15, P(16)[1]))
    pwr("+3V3", (x15, P(15)[1]))
    pwr("GND", P(25))
    pwr("GND", P(26))
    note("J3 pin n = panel pin n (straight FPC). FPC-05F-24PH20 is\\nbottom-contact: panel FPC contacts face the PCB. VERIFY.",
         (bx + 2.54, by + 86.36))
    note("BS=GND: 4-wire SPI. TSCL/TSDA/VPP/NC open.", (bx + 2.54, by + 92.71))


def main():
    global ROOT_UUID
    t = parse(open(TEMPLATE).read())
    ROOT_UUID = str(find(t, "uuid")[1])
    build()
    # junctions: wire endpoints where >=3 connections meet (incl. T on wire interior)
    from collections import Counter
    ends = Counter()
    for x1, y1, x2, y2 in WIRES:
        ends[(x1, y1)] += 1
        ends[(x2, y2)] += 1
    pinset = Counter(PINPTS)
    junctions = []
    for pt, n in ends.items():
        cnt = n + pinset.get(pt, 0)
        for x1, y1, x2, y2 in WIRES:
            if (x1 == x2 == pt[0] and min(y1, y2) < pt[1] < max(y1, y2)) or \
               (y1 == y2 == pt[1] and min(x1, x2) < pt[0] < max(x1, x2)):
                cnt += 2
        if cnt >= 3:
            junctions.append(pt)
    for pt in junctions:
        ITEMS.append(f'(junction (at {fmt(pt[0])} {fmt(pt[1])}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')

    libsyms = []
    for name in sorted(USED):
        s = parse(dump(_lib[name]))
        s[1] = Q("ull-pocket:" + name)
        libsyms.append(dump(s, 2))
    head = (f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") '
            f'(uuid "{ROOT_UUID}") (paper "A3") ')
    tb = dump(find(t, "title_block"))
    tb = tb.replace('">>TITLE<<"', '"ull-pocket: pocket environment meter"').replace(
        '">>REVISION<<"', '"0.1"').replace('">>CLIENT<<"', '"ESP32-C6, SHT31, BMP585, LIS3DH, MAX17048, 1.54in e-paper"')
    body = "\n".join(ITEMS)
    tail = ('(sheet_instances (path "/" (page "1"))) (embedded_fonts no) '
            + dump(find(t, "embedded_files")) + ")")
    out = head + tb + "\n(lib_symbols\n" + "\n".join(libsyms) + "\n)\n" + body + "\n" + tail
    # sanity parse
    parse(out)
    open(SCH, "w").write(out + "\n")
    print(f"wrote {SCH}: {len(ITEMS)} items, {len(WIRES)} wires, {len(junctions)} junctions")


if __name__ == "__main__":
    main()
