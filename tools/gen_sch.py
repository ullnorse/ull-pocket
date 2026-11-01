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
                 hide_ref=False, hide_value=False, dnp=False, in_pos=True):
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
        dnp_t = "yes" if dnp else "no"
        pos_t = " (in_pos_files no)" if (dnp or not in_pos) else ""
        ITEMS.append(
            f'(symbol (lib_id "ull-pocket:{lib}") (at {fmt(x)} {fmt(y)} {rot}) (unit 1) '
            f'(exclude_from_sim no) (in_bom {bom}) (on_board yes){pos_t} (dnp {dnp_t}) (uuid "{uid()}") '
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
    """No-connect on a pin; a 2.54 mm stub keeps the cross clear of the pin number."""
    p = part.p(num)
    e = add(p, part.out(num), G)
    wire(p, e)
    nc(e)


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
LED_SIDE_FP = "ull-pocket:LED_XL-1606_SideView"  # XINGLIGHT XL-1606 side-view, emits toward -y (board edge)
SEMCO = "Samsung Electro-Mechanics"
PARTS = {
    "10k": ("10kR", "0402R", "0402WGF1002TCE", UNIROYAL, "C25744", "Resistor 10k 1% 0402"),
    "5k1": ("5.1kR", "0402R", "0402WGF5101TCE", UNIROYAL, "C25905", "Resistor 5.1k 1% 0402"),
    "100k": ("100kR", "0402R", "0402WGF1003TCE", UNIROYAL, "C25741", "Resistor 100k 1% 0402"),
    "3k3": ("3.3kR", "0402R", "0402WGF3301TCE", UNIROYAL, "C25890", "Resistor 3.3k 1% 0402"),
    "1k5": ("1.5kR", "0402R", "0402WGF1501TCE", UNIROYAL, "C25867", "Resistor 1.5k 1% 0402"),
    "2k": ("2kR", "0402R", "0402WGF2001TCE", UNIROYAL, "C4109", "Resistor 2k 1% 0402"),
    "1M": ("1MR", "0402R", "0402WGF1004TCE", UNIROYAL, "C26083", "Resistor 1M 1% 0402"),
    "1M_0603": ("1MR", "0603R", "0603WAF1004T5E", UNIROYAL, "C22935", "Resistor 1M 1% 0603"),
    "2R2_0603": ("2.2R", "0603R", "0603WAF220KT5E", UNIROYAL, "C22939", "Resistor 2.2R 1% 0603"),
    "100n": ("100nF/16V", "0402C", "CL05B104KO5NNNC", SEMCO, "C1525", "MLCC 100nF 16V X7R 0402"),
    "1u": ("1uF/25V", "0402C", "CL05A105KA5NQNC", SEMCO, "C52923", "MLCC 1uF 25V X5R 0402"),
    "10u": ("10uF/10V", "0603C", "CL10A106KP8NNNC", SEMCO, "C19702", "MLCC 10uF 10V X5R 0603"),
    "4n7": ("4.7nF/50V", "0402C", "0402B472K500NT", "FH(Guangdong Fenghua Advanced Tech)", "C1538",
            "MLCC 4.7nF 50V X7R 0402"),
    "1u50": ("1uF/50V", "0603C", "CL10A105KB8NNNC", SEMCO, "C15849", "MLCC 1uF 50V X5R 0603"),
    "0R": ("0R", "0603R", "0603WAF0000T5E", UNIROYAL, "C21189", "Resistor 0R 0603 (sleep-current link)"),
    "470R": ("470R", "0402R", "0402WGF4700TCE", UNIROYAL, "C25117", "Resistor 470R 1% 0402"),
    "1k": ("1kR", "0402R", "0402WGF1001TCE", UNIROYAL, "C11702", "Resistor 1k 1% 0402"),
    "0R_0402": ("0R", "0402R", "0402WGF0000TCE", UNIROYAL, "C17168", "Resistor 0R 0402 (USB shield to GND)"),
    "100R": ("100R", "0402R", "0402WGF1000TCE", UNIROYAL, "C25076", "Resistor 100R 1% 0402"),
    "22u": ("22uF/25V", "0805C", "CL21A226MAQNNNE", SEMCO, "C45783", "MLCC 22uF 25V X5R 0805"),
    "4u7_50": ("4.7uF/50V", "0805C", "CL21A475KBQNNNE", SEMCO, "C98192", "MLCC 4.7uF 50V X5R 0805"),
    "4u7_25": ("4.7uF/25V", "0805C", "CL21A475KAQNNNE", SEMCO, "C1779", "MLCC 4.7uF 25V X5R 0805"),
}


def _passive(lib, prefix, key, c, orient, side="R", fpos=None, dnp=False):
    val, fpk, mpn, mfr, lcsc, desc = PARTS[key]
    rot = 0 if orient == "V" else 90
    ref = nextref(prefix)
    x, y = c
    if fpos is not None:
        pass
    elif orient == "V":
        if side == "RU":  # texts on the right, raised so a label below the node stays clear
            fpos = {"Reference": (x + 1.524, y - 2.159, "left"), "Value": (x + 1.524, y - 0.381, "left")}
        elif side == "R":
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
                        "Description": desc}, fpos=fpos, dnp=dnp, in_bom=not dnp)


def R(key, c, orient="V", side="R", fpos=None, dnp=False):
    return _passive("R_Small_US", "R", key, c, orient, side, fpos, dnp)


def C(key, c, orient="V", side="R", fpos=None, dnp=False):
    return _passive("C_Small", "C", key, c, orient, side, fpos, dnp)


def cap_down(key, top, side="R", gnd=True):
    """Vertical cap whose pin1 sits at `top`; GND symbol at its bottom."""
    c = C(key, (top[0], top[1] + G), "V", side)
    if gnd:
        pwr("GND", c.p(2))
    return c


def res_down(key, top, side="R", gnd=True, dnp=False):
    r = R(key, (top[0], top[1] + G), "V", side, dnp=dnp)
    if gnd:
        pwr("GND", r.p(2))
    return r


def res_up(key, bottom, rail, side="R"):
    r = R(key, (bottom[0], bottom[1] - G), "V", side)
    pwr(rail, r.p(1))
    return r


def ic(lib, ref, x, y, **kw):
    return Part(lib, ref, x, y, 0, **kw)


def tp(name, pt, rot=0, show=True):
    """Test pad. rot 0: pad above the pin point; rot 90: pad to the left. Ref hidden."""
    ref = nextref("TP")
    if rot == 0:
        vx = (pt[0], pt[1] - 5.334, None)
    else:
        vx = (pt[0] - 4.826, pt[1], "right")
    return Part("TestPoint", ref, pt[0], pt[1], rot, value=name, in_bom=False, hide_ref=True,
                hide_value=not show,
                fields={"Footprint": "TestPoint:TestPoint_Pad_1.0x1.0mm",
                        "Description": "Test pad 1.0 mm square, not a BOM part"},
                fpos={"Reference": (pt[0], pt[1], None), "Value": vx})


def S(v):
    """snap to 1.27 grid"""
    return r3(round(v / 1.27) * 1.27)


# =============================================================== layout
def hcap_row(pin, name, key, cap_dx=22.86, bus_dx=30.48):
    """Panel decoupling cap on a J3 pin: wire + net label, horizontal cap, ends on a vertical bus."""
    x, y = pin
    wire(pin, (x + cap_dx - 2.54, y))
    label(name, (x + 3.81, y), "R")
    c = C(key, (x + cap_dx, y), "H", fpos={"Reference": (x + cap_dx, y - 1.9, None),
                                          "Value": (x + cap_dx, y + 1.9, None)})
    wire(c.p(2), (x + bus_dx, y))
    return (x + bus_dx, y)


def rail_caps(part, pins, caps, rise, step=20.32, side="R"):
    """3V3 rail above the supply pins with caps hanging to the right. Returns (y_rail, x_first_pin)."""
    pts = [part.p(p) for p in pins]
    y = pts[0][1] - rise
    for p in pts:
        wire(p, (p[0], y))
    xl, xr = min(p[0] for p in pts), max(p[0] for p in pts)
    if xl != xr:
        wire((xl, y), (xr, y))
    x, prev = xr + 7.62, xr
    for k in caps:
        wire((prev, y), (x, y))
        cap_down(k, (x, y), side)
        prev, x = x, x + step
    return y, xl


SW_PTS, J4_PTS = [], []


def hres(key, a, b, below=False):
    """horizontal resistor whose pins land on a and b (5.08 mm apart, same y)"""
    x, y = (a[0] + b[0]) / 2, a[1]
    fp = {"Reference": (x + 1.27, y + 2.286, None), "Value": (x + 1.27, y + 4.064, None)} if below else \
        {"Reference": (x, y - 2.286, None), "Value": (x, y + 2.286, None)}
    r = R(key, (x, y), "H", fpos=fp)
    pts = sorted([r.p(1), r.p(2)])
    assert pts == sorted([a, b]), (pts, a, b)
    return r


def build():
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
    vbe = add(vbn, (1, 0), 22.86)
    wire(vbn, vbe)
    pwr("PWR_FLAG", add(vbn, (1, 0), 10.16))
    tp("VBUS", vbe)
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
    pwr("GND", j1.p("A1"))
    sh = j1.p("SH")
    shn = add(sh, (0, 1), G)
    wire(sh, shn)
    xl, xr = shn[0] - 2.54, shn[0] + 2.54
    wire((xl, shn[1]), (xr, shn[1]))
    # plastic case: shield straight to GND through a 0R; the 4.7 nF RC option stays as a DNP footprint
    r_sh = R("0R_0402", (xl, shn[1] + G), "V", side="L")
    c_sh = C("4n7", (xr, shn[1] + G), "V", side="R", dnp=True)
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
    rect(bx, by, bx + 130.81, by + 69.85, C_PWR, "CHARGER + POWER PATH (BQ24073)")
    u6 = ic("BQ24073RGTR", "U6", bx + 52.07, by + 33.02)
    pin_in = u6.p("13")
    n_in = add(pin_in, (-1, 0), 7.62)
    wire(pin_in, n_in)
    pwr("VBUS", n_in)
    cap_down("1u50", n_in, side="L")
    # EN1 = VBUS/2 (USB500 mode only while VBUS present; no drain from the cell)
    p_en1 = u6.p("6")
    n_en1 = add(p_en1, (-1, 0), 22.86)
    wire(p_en1, n_en1)
    res_up("100k", n_en1, "VBUS", side="R")
    res_down("100k", n_en1, side="R")
    xg = p_en1[0] - 2.54
    for pn in ("5", "4", "15"):
        wire(u6.p(pn), (xg, u6.p(pn)[1]))
    wire((xg, u6.p("5")[1]), (xg, u6.p("15")[1]))
    pwr("GND", (xg, u6.p("15")[1]))
    # OUT -> VSYS + 10uF + test pad
    p_out = u6.p("10")
    n_out = add(p_out, (1, 0), 7.62)
    wire(p_out, n_out)
    pwr("VSYS", n_out)
    cap_down("10u", n_out)
    e_out = add(n_out, (1, 0), 17.78)
    wire(n_out, e_out)
    tp("VSYS", e_out)
    # BAT -> VBAT + 10uF
    p_bat = u6.p("2")
    n_bat = add(p_bat, (1, 0), 12.7)
    wire(p_bat, n_bat)
    pwr("VBAT", n_bat)
    cap_down("10u", n_bat, side="L")
    # CHG -> LED (K) ; LED (A) -> 2k -> VSYS
    p_chg = u6.p("9")
    x_led = p_chg[0] + 20.32
    led_c = (x_led, p_chg[1] - G)
    led = Part("LED_Small", nextref("D"), led_c[0], led_c[1], 90, value="RED",
               fields={"Footprint": LED_SIDE_FP, "MPN": "XL-1606SURC",
                       "Manufacturer": "XINGLIGHT", "LCSC": "C965860",
                       "Description": "LED red side-view 1.7x0.6, charge indicator"},
               fpos={"Reference": (x_led + 1.524, led_c[1] - 0.889, "left"),
                     "Value": (x_led + 1.524, led_c[1] + 0.889, "left")})
    wire(p_chg, led.p("1"))
    r_led = R("2k", (x_led, led.p("2")[1] - G))
    pwr("VSYS", r_led.p(1))
    # PGOOD -> 100k pull-up to 3V3 -> USB_PGOOD_N
    p_pg = u6.p("7")
    n_pg = (x_led + 11.43, p_pg[1])
    wire(p_pg, n_pg)
    res_up("100k", n_pg, "+3V3", side="RU")
    e_pg = add(n_pg, (1, 0), 2.54)
    wire(n_pg, e_pg)
    label("USB_PGOOD_N", e_pg, "R")
    # bottom: TS 10k (no NTC), ISET 3.3k, ILIM 3.3k, TMR open (default timers), VSS
    # TS: 10k NTC (103AT type, B=3435) left of the pin, DNP fixed 10k fallback (R8) in parallel
    p_ts = u6.p("1")
    nt = (p_ts[0] - 5.08, p_ts[1])
    wire(p_ts, nt)
    th = Part("Thermistor_NTC_US", "TH1", nt[0], nt[1] + 3.81, 0, value="NTC10k",
              fields={"Footprint": FP["0603R"], "MPN": "SDNT1608X103F3435FTF", "Manufacturer": "Sunlord",
                      "LCSC": "C525660", "Description": "NTC 10k 1% B3435 0603; place under/against the cell"},
              fpos={"Reference": (nt[0] - 3.8, nt[1] + 2.921, "right"),
                    "Value": (nt[0] - 3.8, nt[1] + 4.699, "right")})
    pwr("GND", th.p(2))
    r8 = R("10k", (p_ts[0], p_ts[1] + G), "V", "R", dnp=True,
           fpos={"Reference": (p_ts[0] + 3.4, p_ts[1] + G - 0.889, "left"),
                 "Value": (p_ts[0] + 3.4, p_ts[1] + G + 0.889, "left")})
    pwr("GND", r8.p(2))
    res_down("3k3", u6.p("16"))
    res_down("3k3", u6.p("12"))
    pin_nc(u6, "14")
    pwr("GND", u6.p("8"))
    note("ICHG = 890/3.3k = 270 mA\\nUSB500: EN1=1, EN2=0\\n-> IIN <= 500 mA\\n"
         "TS: TH1 10k NTC (B3435), R8 10k DNP\\nCharge window 0.5..50.8 C (see NOTES)\\nTMR open: 5 h timer", (bx + 86.36, by + 56.0))
    # bring-up ground pad
    gx = (bx + 3.81, by + 54.61)
    pwr("GND", gx)
    tp("GND", gx)
    gf = add(gx, (1, 0), 7.62)
    wire(gx, gf)
    pwr("PWR_FLAG", gf)

    # ============================ Battery + gauge ======================
    bx, by = 238.76, 12.7
    rect(bx, by, bx + 100.33, by + 69.85, C_BAT, "BATTERY + FUEL GAUGE")
    jx, jy = bx + 22.86, by + 20.32
    j2 = Part("S2B-PH-SM4-TB", "J2", jx, jy, 180, value="PH-2PWB",
              fields={"MPN": "PH-2PWB", "Manufacturer": "DEALON", "LCSC": "C2905019",
                      "Description": "JST PH 2.0 mm 2-pin SMD right-angle (DEALON PH-2PWB, pad-compatible with S2B-PH-SM4-TB)"},
              fpos={"Reference": (jx - 3.81, jy - 1.27, "right"),
                    "Value": (jx - 3.81, jy + 1.27, "right")})
    p_bp = j2.p("2")   # pin 2 = BAT+, pin 1 = BAT- (assumed, see note)
    p_bn = j2.p("1")
    pin_nc(j2, "MP")
    n_bp = add(p_bp, (1, 0), 7.62)
    wire(p_bp, n_bp)
    pwr("VBAT", n_bp)
    e_bp = add(n_bp, (1, 0), 22.86)
    wire(n_bp, e_bp)
    pwr("PWR_FLAG", add(n_bp, (1, 0), 10.16))
    tp("VBAT", e_bp)
    # reverse-polarity low-side FET: BAT- -> BAT_N -> Q2 drain, source = GND, gate = VBAT via 100k
    q2 = Part("AO3400A", "Q2", bx + 33.02, by + 33.02, 0,
              fpos={"Reference": (bx + 40.64, by + 32.131, "left"),
                    "Value": (bx + 40.64, by + 33.909, "left")})
    d_q = q2.p("3")
    wire(p_bn, (p_bn[0] + 2.54, p_bn[1]), (p_bn[0] + 2.54, by + 24.13), (d_q[0], by + 24.13), d_q)
    label("BAT_N", (p_bn[0] + 5.08, by + 24.13), "R")
    pwr("GND", q2.p("2"))
    g_q = q2.p("1")
    n_g = add(g_q, (-1, 0), 5.08)
    wire(g_q, n_g)
    res_up("100k", n_g, "VBAT", side="L")
    note("J2 pin 2 = BAT+\\nJ2 pin 1 = BAT-\\nQ2 blocks a reversed\\ncell. Silkscreen:\\nmark + and -", (bx + 2.54, by + 58.42))

    u5 = ic("MAX17048G+T10", "U5", bx + 50.8, by + 50.8)
    p_vdd = u5.p("3")
    n_vdd = add(p_vdd, (0, -1), 5.08)
    wire(p_vdd, n_vdd)
    pwr("VBAT", n_vdd)
    c_g = add(n_vdd, (1, 0), 7.62)
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
    n_al = add(p_al, (1, 0), 15.24)
    wire(p_al, n_al)
    res_up("100k", n_al, "+3V3", side="RU")
    e_al = add(n_al, (1, 0), 2.54)
    wire(n_al, e_al)
    label("BAT_ALRT_N", e_al, "R")
    pwr("GND", u5.p("4"))

    # ============================ 3V3 LDO ==============================
    bx, by = 342.9, 12.7
    rect(bx, by, bx + 64.77, by + 40.64, C_LDO, "3V3 LDO (RT9080)")
    u7 = ic("RT9080-33GJ5", "U7", bx + 30.48, by + 22.86)
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
    cap_down("1u", n_vo)
    r0 = R("0R", (n_vo[0], n_vo[1] - G), "V", "L")
    e_lo = add(n_vo, (1, 0), 2.54)
    wire(n_vo, e_lo)
    label("LDO_OUT", e_lo, "R")
    top = r0.p(1)
    n3 = add(top, (0, -1), 5.08)
    wire(top, n3)
    pwr("+3V3", n3)
    tp_pt = (top[0] + 7.62, top[1] - 2.54)
    wire((top[0], tp_pt[1]), tp_pt)
    tp("+3V3", tp_pt)
    pwr("GND", u7.p("2"))

    # ============================ Wake button ==========================
    bx, by = 342.9, 57.15
    rect(bx, by, bx + 64.77, by + 25.4, C_UI, "WAKE BUTTON (side)")
    sw1 = Part("TS24CA", "SW1", bx + 43.18, by + 13.97, 0)
    p1 = sw1.p("1")
    n1 = add(p1, (-1, 0), 10.16)
    SW_PTS.extend([p1, n1])   # 100R series + 100 nF debounce are added at the end (stable refs)
    res_up("100k", n1, "+3V3", side="RU")
    e1 = add(n1, (-1, 0), 2.54)
    wire(n1, e1)
    label("BTN_N", e1, "L")
    p2 = sw1.p("2")
    n2 = add(p2, (1, 0), 2.54)
    wire(p2, n2)
    pwr("GND", n2)
    pwr("GND", sw1.p("3"))

    # ============================ MCU ==================================
    bx, by = 12.7, 86.36
    rect(bx, by, bx + 132.08, by + 91.44, C_MCU, "MCU (ESP32-C6-MINI-1)")
    u1 = ic("ESP32-C6-MINI-1-H4", "U1", bx + 76.2, by + 55.88)
    p33 = u1.p("3")
    n33 = add(p33, (0, -1), 10.16)
    wire(p33, n33)
    pwr("+3V3", n33)
    f33 = add(n33, (-1, 0), 17.78)
    wire(n33, f33)
    pwr("PWR_FLAG", f33)
    ca = add(n33, (1, 0), 7.62)
    cb = add(n33, (-1, 0), 7.62)
    wire(cb, ca)
    c10 = cap_down("22u", ca, side="R", gnd=False)
    c01 = cap_down("100n", cb, side="L", gnd=False)
    wire(c01.p(2), c10.p(2))
    pwr("GND", c10.p(2))
    # all 22 GND pins drawn on the bottom edge, tied by one bus wire
    gnd_pins = ["1", "2", "11", "14"] + [str(i) for i in range(36, 54)]
    for a, b in zip(gnd_pins, gnd_pins[1:]):
        wire(u1.p(a), u1.p(b))
    pwr("GND", u1.p("1"))
    # EN: 10k to 3V3 + 1uF to GND (Espressif RC), test pad, net EN
    p_en = u1.p("8")
    x_en = p_en[0] - 12.7
    y_top = p_en[1] - 10.16
    wire(p_en, (x_en, p_en[1]), (x_en, y_top))
    res_up("10k", (x_en, y_top), "+3V3", side="L")
    m = (x_en, p_en[1] - 5.08)
    cm = (x_en - 7.62, m[1])
    wire(m, cm)
    cap_down("1u", cm, side="L")
    label("EN", add(p_en, (-1, 0), 2.54), "L")
    # IO9 = BOOT strap pad (internal pull-up); IO8 10k pull-up (download boot needs IO8=1)
    stub(u1, "23", "BOOT")
    p8 = u1.p("22")
    n8 = add(p8, (-1, 0), 25.4)
    wire(p8, n8)
    res_up("10k", n8, "+3V3", side="L")
    stub(u1, "17", "USB_D-")
    stub(u1, "18", "USB_D+")
    stub(u1, "30", "RXD0")
    stub(u1, "31", "TXD0")
    for pn, nm in (("12", "BAT_ALRT_N"), ("13", "USB_PGOOD_N"), ("5", "BTN_N"), ("6", "ACC_INT1"),
                   ("9", "BARO_INT"), ("15", "I2C_SDA"), ("16", "I2C_SCL"), ("24", "EPD_BUSY"),
                   ("25", "EPD_RST_N"), ("26", "EPD_DC"), ("27", "EPD_CS_N"), ("28", "EPD_SCK"),
                   ("29", "EPD_MOSI"), ("10", "LED_USER"), ("19", "SPARE_IO14")):
        stub(u1, pn, nm)
    note("LP GPIO (IO0-IO4 wake):\\nIO0 BAT_ALRT_N\\nIO1 USB_PGOOD_N\\nIO2 BTN_N\\nIO3 ACC_INT1\\n"
         "IO4 BARO_INT\\nIO5 LED_USER\\nIO6/7 LP_I2C\\nIO8 10k pull-up",
         (bx + 2.54, by + 7.0))

    # ============================ Sensors ==============================
    bx, by = 118.11, 86.36
    sx = bx + 30.48   # box starts right of the widened MCU box; parts keep their places
    rect(sx, by, bx + 289.56, by + 91.44, C_SNS, "SENSORS (I2C, 3V3)")
    # I2C pull-ups next to the bus (labels horizontal)
    for i, nm in enumerate(("I2C_SDA", "I2C_SCL")):
        x = sx + 5.08 + i * 12.7
        node = (x, by + 30.48)
        r = res_up("10k", node, "+3V3", side="RU")
        e = add(node, (1, 0), 2.54)
        wire(node, e)
        label(nm, e, "R")
    note("I2C addresses:\\nSHT31 0x44 (ADDR=GND)\\nBMP585 0x46 (SDO=GND)\\nLIS3DH 0x19 (SA0=3V3)\\n"
         "MAX17048 0x36", (sx + 2.54, by + 58.42))

    u2 = ic("SHT31-DIS-B", "U2", bx + 76.2, by + 48.26)
    y, _ = rail_caps(u2, ["5"], ["100n"], 10.16)
    pwr("+3V3", (u2.p("5")[0], y))
    stub(u2, "1", "I2C_SDA")
    stub(u2, "4", "I2C_SCL")
    pin_pwr(u2, "2", "GND")
    pin_nc(u2, "3")
    pin_nc(u2, "6")
    pwr("GND", u2.p("8"))
    pwr("GND", u2.p("7"))

    u3 = ic("BMP585", "U3", bx + 134.62, by + 50.8)
    y, x0 = rail_caps(u3, ["4", "8"], ["100n", "100n"], 7.62)
    p_csb = u3.p("7")
    x_b = p_csb[0] - 5.08
    wire(p_csb, (x_b, p_csb[1]), (x_b, y), (x0, y))
    pwr("+3V3", (x_b, y))
    stub(u3, "2", "I2C_SDA")
    stub(u3, "1", "I2C_SCL")
    pin_pwr(u3, "3", "GND")
    stub(u3, "5", "BARO_INT")
    pwr("GND", u3.p("6"))
    # rule area (keepout) is part of the footprint; note here
    note("U3 pin 9 (marking\\narea) is not a pad.\\nKeepout and F.Mask\\nopening: footprint.\\nLayout: only each\\npad's own trace may\\nenter the band under\\nthe body.", (bx + 98, by + 62))

    u4 = ic("LIS3DHTR", "U4", bx + 203.2, by + 48.26)
    y, x0 = rail_caps(u4, ["1", "14"], ["100n", "100n", "10u"], 7.62)
    p_cs, p_sa = u4.p("8"), u4.p("7")
    x_l = p_cs[0] - 5.08
    wire(p_cs, (x_l, p_cs[1]))
    wire(p_sa, (x_l, p_sa[1]), (x_l, y), (x0, y))
    pwr("+3V3", (x_l, y))
    stub(u4, "6", "I2C_SDA")
    stub(u4, "4", "I2C_SCL")
    stub(u4, "11", "ACC_INT1")
    for pn in ("9", "16", "15", "13"):
        pin_nc(u4, pn)
    pwr("GND", u4.p("5"))
    pwr("GND", u4.p("10"))

    # ============================ E-paper ==============================
    bx, by = 12.7, 181.61
    rect(bx, by, bx + 143.51, by + 104.14, C_EPD, "E-PAPER (GDEY0154D67 ref. circuit)")
    x0, y0 = bx + 12.7, by + 45.72
    pwr("+3V3", (x0, y0))
    cap_down("4u7_25", (x0, y0), side="L")
    l1 = Part("L_Small", "L1", x0 + 10.16, y0, 90, value="47uH",
              fields={"Footprint": "ull-pocket:IND-SMD_L4.0-W4.0_FNR40XXS", "MPN": "FNR4030S470MT",
                      "Manufacturer": "cjiang (Changjiang Microelectronics Tech)", "LCSC": "C167888",
                      "Description": "Power inductor 47uH 20% Isat 1A Irms 800mA 4x4x3mm shielded"},
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
    label("EPD_PREVGH", e_gh, "R")
    c3 = C("4u7_50", (sw[0], sw[1] - 7.62), "V", side="L")
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
    label("EPD_PREVGL", e_gl, "R")
    cap_down("1u50", add(e_gl, (-1, 0), 5.08))

    ly1 = pins_of("FPC-05FB-24PH20")["1"][1]
    j3 = ic("FPC-05FB-24PH20", "J3", bx + 95.25, by + 7.62 + ly1)
    P = lambda n: j3.p(str(n))  # noqa: E731
    for n in (1, 4, 6, 7, 19):
        pin_nc(j3, n)
    stub(j3, 2, "EPD_GDR")
    stub(j3, 3, "EPD_RESE")
    hcap_row(P(5), "EPD_VSH2", "1u50")
    g5 = (P(5)[0] + 30.48, P(5)[1])
    pwr("GND", g5)
    # BS = GND: long stub so the ground symbol clears the signal labels below
    wire(P(8), (P(8)[0] + 19.05, P(8)[1]))
    pwr("GND", (P(8)[0] + 19.05, P(8)[1]))
    for n, nm in ((9, "EPD_BUSY"), (10, "EPD_RST_N"), (11, "EPD_DC"), (12, "EPD_CS_N"),
                  (13, "EPD_SCK"), (14, "EPD_MOSI")):
        stub(j3, n, nm)
    # 3V3: VDDIO(15) + VCI(16) tied, one cap
    x15 = P(15)[0]
    wire(P(15), (x15 + 20.32, P(15)[1]))
    pwr("+3V3", (x15 + 20.32, P(15)[1]))
    wire(P(16), (x15 + 2.54, P(16)[1]), (x15 + 2.54, P(15)[1]))
    cap_down("1u50", (x15 + 7.62, P(15)[1]), side="R")
    # VSS(17) + panel caps on a ground bus
    bus_top = (P(17)[0] + 30.48, P(17)[1])
    wire(P(17), bus_top)
    hcap_row(P(18), "EPD_VDD", "1u50")
    hcap_row(P(20), "EPD_VSH1", "1u50")
    hcap_row(P(22), "EPD_VSL", "1u50")
    bus_bot = hcap_row(P(24), "EPD_VCOM", "1u50")
    wire(bus_top, bus_bot)
    pwr("GND", bus_bot)
    stub(j3, 21, "EPD_PREVGH")
    stub(j3, 23, "EPD_PREVGL")
    pwr("GND", P(25))
    pwr("GND", P(26))
    note("J3 pin n = panel pin n (straight FPC). FPC-05FB-24PH20 is dual contact:\\npanel tail wraps round the board edge, contacts face away from the PCB.",
         (bx + 2.54, by + 93.98))
    note("BS=GND: 4-wire SPI. TSCL/TSDA/VPP/NC open.", (bx + 2.54, by + 99.06))

    # ============================ Notes ================================
    bx, by = 159.38, 181.61
    rect(bx, by, 407.67, by + 68.58, C_UI, "NOTES")
    NS = 1.65
    c1, c2, c3 = bx + 2.54, bx + 85.0, bx + 167.0
    note("WAKE POLARITY (ext1, one level)\\n"
         "ACC_INT1, BARO_INT: active-high by default.\\n"
         "BTN_N, BAT_ALRT_N, USB_PGOOD_N: active-low.\\n"
         "Set LIS3DH INT_POLARITY and BMP585 int_pol\\n"
         "to active-low so one ext1 level wakes all.", (c1, by + 10.0), NS)
    note("PROGRAMMING (J4 pads)\\n"
         "+3V3, GND, EN, IO9/BOOT, TXD0, RXD0.\\n"
         "2x3 pads at 2.54 mm: pogo clip or header.\\n"
         "Hold BOOT low, pulse EN for download mode.\\n"
         "Pin 1 (+3V3) is sense/reference only: do not\\n"
         "feed 3.3 V with no battery fitted (RT9080\\n"
         "back-feed).", (c1, by + 27.0), NS)
    note("FIRMWARE\\n"
         "Set the MAX17048 VALRT / cutoff and the\\n"
         "brownout level to about 3.5 V: the RT9080\\n"
         "drops out below that.", (c1, by + 50.0), NS)
    note("BRING-UP\\n"
         "Sleep current: replace R13 (0R, LDO_OUT to\\n"
         "+3V3) with an ammeter. Include the e-paper\\n"
         "boost path in the measurement.\\n"
         "Test pads: VBUS, VBAT, VSYS, +3V3, GND.", (c2, by + 10.0), NS)
    note("BATTERY\\n"
         "Q2 (AO3400A) in the BAT- lead blocks a\\n"
         "reversed cell. MAX17048 and BQ24073 see\\n"
         "system GND. Mark + and - on the J2 silk.", (c2, by + 31.0), NS)
    note("PULL-UPS / PULL-DOWNS\\n"
         "EPD_CS_N, EPD_RST_N: 100k to +3V3 keep the\\n"
         "panel idle while the MCU sleeps.\\n"
         "IO15: 10k to +3V3 (strap). If JTAG_SEL is\\n"
         "burned, selects USB Serial/JTAG, not pad JTAG.", (c2, by + 50.0), NS)
    note("LEDS: XL-1606 side-view, bottom edge (1.1-1.5 mA)\\n"
         "D5 green: VBUS-2k, (5.0-2.6)/2k = 1.2 mA.\\n"
         "   Lit with USB present, 0 on battery.\\n"
         "D1 red CHG: VSYS(4.4)-2k, Vf 1.8: 1.3 mA.\\n"
         "D6 blue IO5: 470R, Vf 2.6-2.8 @1 mA: 1.1-1.5 mA.\\n"
         "Silkscreen: D5 PWR, D1 CHG, D6 USR.\\n"
         "No addressable LEDs: idle current.", (c3, by + 10.0), NS)
    note("BATTERY TEMPERATURE (TS)\\n"
         "TH1 10k NTC B3435 (0603): place against the\\n"
         "cell. R8 10k (DNP) is the fallback.\\n"
         "75 uA bias trips at 0.30 V and 2.1 V:\\n"
         "charging 0.5..50.8 C (resume < 47.9, > 3.9 C).\\n"
         "Bias flows only while VBUS is present.", (c3, by + 37.0), NS)

    # ============================ Indicator LEDs (added rev 0.3, appended to keep refs stable) =====
    led_f = lambda col, fp, mpn, mfr, lcsc: {  # noqa: E731
        "Footprint": fp, "MPN": mpn, "Manufacturer": mfr, "LCSC": lcsc, "Description": f"LED {col}"}

    def led_chain(x, ytop, rkey, col, fp, mpn, mfr, lcsc, top):
        """vertical: top(pt) -> R -> LED (A up, K down) -> GND. ytop = R pin 1."""
        r = R(rkey, (x, ytop + G), "V", "R")
        lc = (x, r.p(2)[1] + G)
        d = Part("LED_Small", nextref("D"), lc[0], lc[1], 90, value=col,
                 fields=led_f(col.lower(), fp, mpn, mfr, lcsc),
                 fpos={"Reference": (x + 2.8, lc[1] - 0.889, "left"), "Value": (x + 2.8, lc[1] + 0.889, "left")})
        pwr("GND", d.p("1"))
        return r, d

    # power LED: VBUS -> 2k -> green LED -> GND (USB present; zero drain on battery)
    xp = 91.44
    rp = R("2k", (xp, 30.48), "V", "L")
    pwr("VBUS", rp.p(1))
    lcp = (xp, rp.p(2)[1] + G)
    Part("LED_Small", nextref("D"), lcp[0], lcp[1], 90, value="GREEN",
         fields=led_f("green side-view 1.7x0.6, USB power present", LED_SIDE_FP, "XL-1606UGC",
                      "XINGLIGHT", "C965863"),
         fpos={"Reference": (xp - 2.7, lcp[1] - 0.889, "right"), "Value": (xp - 2.7, lcp[1] + 0.889, "right")})
    pwr("GND", (xp, lcp[1] + G))

    # user LED (GPIO, active high) + spare-GPIO test pad in a small block in the free corner of the sensor area
    ux, uy = 353.06, 121.92
    rect(ux, uy, ux + 50.8, uy + 45.72, C_UI, "USER LED / SPARE GPIO")
    x = ux + 12.7
    r, d = led_chain(x, uy + 15.24, "470R", "BLUE", LED_SIDE_FP, "XL-1606UBC", "XINGLIGHT", "C965865", None)
    e = add(r.p(1), (0, -1), G)
    wire(r.p(1), e)
    label("LED_USER", e, "R")
    REFCOUNT["R"] = REFCOUNT.get("R", 0) + 1   # rev 0.5: R23 retired; keep R24/R25/R26 stable
    xs = ux + 38.1
    tp_s = (xs, uy + 20.32)
    es = (xs, uy + 22.86)
    wire(tp_s, es)
    label("SPARE_IO14", es, "R")
    tp("SPARE_IO14", tp_s, show=False)
    note("IO5 -> 470R -> blue: ~1 mA\\nGPIO high = on, 3.3 V\\nSilk: PWR, CHG, USR", (ux + 2.54, uy + 38.1))
    note("IO14: spare GPIO,\\ntest pad only", (ux + 27.94, uy + 30.48))

    # ============================ rev 0.4 additions (appended so existing refs stay stable) =====
    mx, my = 12.7, 86.36   # MCU box origin
    # programming pogo cluster J4: +3V3, GND, EN, IO9/BOOT, TXD0, RXD0 (no BOM, no placement)
    j4 = Part("PROG", "J4", 25.4, 157.48, 0, in_bom=False, in_pos=False)
    J4_PTS.extend([j4.p("1"), j4.out("1")])   # 1k sense resistor to +3V3 added at the end (stable refs)
    pin_pwr(j4, "2", "GND", 10.16)
    for pn, nm in (("3", "EN"), ("4", "BOOT"), ("5", "TXD0"), ("6", "RXD0")):
        stub(j4, pn, nm)
    # IO15 strap: 10k pull-up (horizontal, left of the USB labels)
    p15 = u1.p("20")
    xr = p15[0] - 17.78
    wire(p15, (xr, p15[1]))
    r15 = R("10k", (xr - 2.54, p15[1]), "H", fpos={"Reference": (xr - 0.8, p15[1] + 2.286, None),
                                                 "Value": (xr - 0.8, p15[1] + 4.064, None)})
    pwr("+3V3", r15.p(2) if r15.p(2)[0] < r15.p(1)[0] else r15.p(1))
    # e-paper sleep pull-ups on CS# and RST# (right of the J3 labels)
    for n, xo, side, dy in ((10, 24.13, "RU", 2.54), (12, 36.83, "L", 0)):
        pt = P(n)
        e = (pt[0] + xo, pt[1] + dy)
        if dy:   # R25 sits 2.54 mm lower (its +3V3 arrow clears C21's value): dog-leg down
            wire((pt[0] + G, pt[1]), (e[0] - 2.54, pt[1]), (e[0] - 2.54, e[1]), e)
        else:
            wire((pt[0] + G, pt[1]), e)
        res_up("100k", e, "+3V3", side=side)

    # ============================ rev 0.6 review changes (appended so existing refs stay stable) =====
    # J4.1 is a sense-only VREF for the programmer: 1k from +3V3, so a programmer cannot feed the rail
    p, d = J4_PTS
    a = add(p, d, G)
    b = add(p, d, G + 5.08)
    e = add(p, d, 10.16)
    wire(p, a)
    hres("1k", a, b) if a[0] < b[0] else hres("1k", b, a)
    wire(b, e)
    pwr("+3V3", e)
    label("VREF", a, {(1, 0): "U", (-1, 0): "U", (0, -1): "R", (0, 1): "R"}[d])
    # SW1: 100R series (ESD/debounce) between the switch and the BTN_N node, 100 nF BTN_N to GND
    p1, n1 = SW_PTS
    ra, rb = add(p1, (-1, 0), 5.08), n1   # R28 lands directly on the BTN_N node
    wire(p1, ra)
    hres("100R", rb, ra, below=True)
    label("BTN_SW", add(p1, (-1, 0), G), "D")
    cap_down("100n", n1, side="L")


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
    cand = set(ends)
    for pt in pinset:
        for x1, y1, x2, y2 in WIRES:
            if (x1 == x2 == pt[0] and min(y1, y2) < pt[1] < max(y1, y2)) or \
               (y1 == y2 == pt[1] and min(x1, x2) < pt[0] < max(x1, x2)):
                cand.add(pt)
    for pt in cand:
        n = ends.get(pt, 0)
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
        '">>REVISION<<"', '"0.5"').replace('">>CLIENT<<"', '"ESP32-C6, SHT31, BMP585, LIS3DH, MAX17048, 1.54in e-paper"')
    tb = tb.replace('(rev "0.5")', '(date "2026-10-28") (rev "0.5")')
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
