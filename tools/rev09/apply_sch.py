"""Rev 0.9 schematic edits (run once on the rev 0.8 file).

- WAKE POLARITY note: BMP580 INT resets active-low, open-drain, disabled (INT_CONFIG 0x14 = 0x35, datasheet 7.5 p.53).
- R35 100k BARO_INT pull-up to +3V3 (open-drain INT would leave IO4 floating).
- U8 (USBLC6-2SC6) pin 5 from VBUS to +3V3: the D+ pull-up no longer back-feeds VBUS on battery.
- C3, C4: 10uF 25V X5R 0805 (C15850, basic).
"""
import os, re, sys, uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rev08"))
from schlib import block, instance

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCH = os.path.join(ROOT, "ull-pocket.kicad_sch")
s = open(SCH).read()
u = lambda: str(uuid.uuid4())


def set_prop(t, name, val):
    t, n = re.subn(r'(\(property "%s" ")[^"]*"' % re.escape(name), lambda m: m.group(1) + val + '"', t, count=1)
    assert n == 1, name
    return t


def move(t, x0, y0, x, y):
    return re.sub(r'\(at ([-\d.]+) ([-\d.]+)', lambda m: "(at %g %g" % (round(float(m.group(1)) - x0 + x, 3), round(float(m.group(2)) - y0 + y, 3)), t)


def add(text):
    global s
    i = s.rindex("\t(sheet_instances")
    s = s[:i] + text + s[i:]


def wire(x1, y1, x2, y2):
    return '\t(wire\n\t\t(pts\n\t\t\t(xy %g %g) (xy %g %g)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, u())


# ---- 1. notes
OLD = ("WAKE POLARITY (ext1, one level)\\nACC_INT1, BARO_INT: active-high by default.\\nBTN_N, BTN2_N, BAT_ALRT_N, USB_PGOOD_N:\\n"
       "active-low. Set LIS2DW12 H_LACTIVE and\\nBMP580 int_pol to active-low so one ext1\\nlevel wakes all. BTN3_N (IO9) is polled.")
NEW = ("WAKE POLARITY (ext1, one level)\\nACC_INT1: push-pull, active-high by default;\\nset LIS2DW12 H_LACTIVE. BARO_INT: BMP580 resets\\n"
       "active-low, open-drain, INT disabled; R35 100k\\npulls IO4 high. BTN_N, BTN2_N, BAT_ALRT_N,\\nUSB_PGOOD_N: active-low. BTN3_N (IO9) is polled.")
assert OLD in s
s = s.replace(OLD, NEW)
OLD = "also the pull-up of SW3 (DN). IO15 drives\\nLED_G (strap only if JTAG_SEL burned)."
assert OLD in s
s = s.replace(OLD, OLD[:-1] + ".\\nR35: 100k to +3V3 on BARO_INT (open-drain).")

# ---- 2. R35 + its +3V3 symbol, right of the BARO_INT label at U3 INT (wire 262.89-265.43 at y 127)
RX, RY = 278.13, 124.46
a, b, tx, ty, _, _ = instance(s, "R25")
t = move(s[a:b], tx, ty, RX, RY)
t = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), t)
t = set_prop(t, "Reference", "R35")
t = re.sub(r'(\(reference ")R25"', r'\1R35"', t)
add("\t" + t + "\n")
add(wire(265.43, 127, RX, 127))
m = re.search(r'\n\t\(symbol\s*\(lib_id "ull-pocket:\+3V3"\)', s)
a, b = block(s, m.start() + 2)
t = s[a:b]
ox, oy = map(float, re.search(r"\(at ([-\d.]+) ([-\d.]+) \d+\)", t).groups())
t = move(t, ox, oy, RX, RY - 2.54)
t = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), t)
n = max(int(x) for x in re.findall(r'"#PWR(\d+)"', s)) + 1
t = re.sub(r'"#PWR\d+"', '"#PWR%03d"' % n, t)
add("\t" + t + "\n")

# ---- 3. U8 pin 5: the VBUS power symbol at the end of its stub becomes +3V3
m = re.search(r'\n\t\(symbol\s*\(lib_id "ull-pocket:VBUS"\)\s*\(at 83\.82 48\.26 0\)', s)
a, b = block(s, m.start() + 2)
t = s[a:b].replace('(lib_id "ull-pocket:VBUS")', '(lib_id "ull-pocket:+3V3")')
t = set_prop(t, "Value", "+3V3")
s = s[:a] + t + s[b:]
OLD = '(text "USB-C INPUT + ESD"'
i = s.index(OLD)
a, b = block(s, i)
note = s[a:b].replace(OLD, '(text "U8 pin 5 on +3V3, not VBUS: the D+\\npull-up cannot back-feed VBUS.\\nD+/D- < 3.6 V, below 3.3 V + Vf."')
note = note.replace("(at 13.97 13.97 0)", "(at 41.91 76.2 0)").replace("(size 2.54 2.54)", "(size 1.27 1.27)")
note = re.sub(r"\s*\(thickness [^)]*\)\s*\(bold yes\)\s*\(color [^)]*\)", "", note)
note = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), note)
add("\t" + note + "\n")

# ---- 4. C3, C4
for ref in ("C3", "C4"):
    a, b, *_ = instance(s, ref)
    t = s[a:b]
    for k, v in (("Value", "10uF/25V"), ("Footprint", "Capacitor_SMD:C_0805_2012Metric"), ("Description", "MLCC 10uF 25V X5R 0805"),
                 ("MPN", "CL21A106KAYNNNE"), ("LCSC", "C15850")):
        t = set_prop(t, k, v)
    s = s[:a] + t + s[b:]

open(SCH, "w").write(s)
print("ok")
