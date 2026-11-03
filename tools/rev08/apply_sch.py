"""Rev 0.8 schematic and symbol edits (run once on the rev 0.7 files).

U2 SHT31 -> SHT40, U3 BMP585 -> BMP580, U4 LIS3DH -> LIS2DW12 (same pin positions for the
shared signals, so wires and labels stay), D6 blue LED -> common-anode RGB on IO8/IO15/IO14.
"""
import os, re, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schlib import block, instance, lib_pins, pin_xy, touching

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCH = os.path.join(ROOT, "ull-pocket.kicad_sch")
LIB = os.path.join(ROOT, "lib/ull-pocket.kicad_sym")
s = open(SCH).read()
L = open(LIB).read()


def u():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- symbols
def font(extra=""):
    return "(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)%s\n\t\t\t)" % extra


def sprop(name, val, x=0, y=0, hide=True, just=""):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %g %g 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t%s\n\t\t)\n'
            % (name, val, x, y, font(("\n\t\t\t\t(justify %s)" % just if just else "") + ("\n\t\t\t\t(hide yes)" if hide else ""))))


def spin(kind, x, y, ang, name, num, hide=False):
    f = "(effects\n\t\t\t\t\t\t(font\n\t\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t\t)\n\t\t\t\t\t)"
    return ('\t\t\t(pin %s line\n\t\t\t\t(at %g %g %d)\n\t\t\t\t(length 2.54)\n%s\t\t\t\t(name "%s"\n\t\t\t\t\t%s\n\t\t\t\t)\n\t\t\t\t(number "%s"\n\t\t\t\t\t%s\n\t\t\t\t)\n\t\t\t)\n'
            % (kind, x, y, ang, "\t\t\t\t(hide yes)\n" if hide else "", name, f, num, f))


def symbol(name, props, rect, pins, ref="U", extra_gfx=""):
    (x1, y1), (x2, y2) = rect
    o = '\t(symbol "%s"\n\t\t(pin_names\n\t\t\t(offset 0.508)\n\t\t)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(duplicate_pin_numbers_are_jumpers no)\n' % name
    o += sprop("Reference", ref, x1, y1 + 0.635, False, "left bottom")
    o += sprop("Value", name, x1, y2 - 0.635, False, "left top")
    for k, v in props:
        o += sprop(k, v)
    o += ('\t\t(symbol "%s_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start %g %g)\n\t\t\t\t(end %g %g)\n\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n\t\t\t\t\t(type default)\n\t\t\t\t)\n\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)\n\t\t\t)\n%s\t\t)\n'
          % (name, x1, y1, x2, y2, extra_gfx))
    o += '\t\t(symbol "%s_1_1"\n' % name + "".join(spin(*p) for p in pins) + "\t\t)\n\t\t(embedded_fonts no)\n\t)\n"
    return o


PARTS = {
    "U2": dict(
        name="SHT40-AD1B", rect=((-12.7, 12.7), (12.7, -12.7)),
        props=[("Footprint", "ull-pocket:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x"),
               ("Datasheet", "https://sensirion.com/media/documents/33FD6951/67EB9032/HT_DS_Datasheet_SHT4x_5.pdf"),
               ("Description", "Humidity and temperature sensor, I2C 0x44, DFN-4 1.5x1.5"),
               ("MPN", "SHT40-AD1B-R2"), ("Manufacturer", "Sensirion"), ("LCSC", "C2909890")],
        pins=[("bidirectional", -15.24, 5.08, 0, "SDA", "1"), ("input", -15.24, 2.54, 0, "SCL", "2"),
              ("power_in", 10.16, 15.24, 270, "VDD", "3"), ("power_in", 5.08, -15.24, 90, "VSS", "4")]),
    "U3": dict(
        name="BMP580", rect=((-7.62, 20.32), (7.62, -20.32)),
        props=[("Footprint", "ull-pocket:Bosch_LGA-10_2x2mm_P0.5mm_BMP580"),
               ("Datasheet", "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp580-ds004.pdf"),
               ("Description", "Barometric pressure sensor, I2C 0x46 (SDO=GND), LGA-10 2x2"),
               ("MPN", "BMP580"), ("Manufacturer", "Bosch Sensortec"), ("LCSC", "C22391138")],
        pins=[("input", -10.16, 10.16, 0, "CSB", "6"), ("bidirectional", -10.16, 5.08, 0, "SDI", "4"),
              ("input", -10.16, 2.54, 0, "SCK", "2"), ("passive", -10.16, -2.54, 0, "SDO", "5"),
              ("output", 10.16, 10.16, 180, "INT", "7"), ("power_in", 0, 22.86, 270, "VDDIO", "1"),
              ("power_in", 5.08, 22.86, 270, "VDD", "10"), ("power_in", 5.08, -22.86, 90, "VSS", "3"),
              ("passive", 5.08, -22.86, 90, "VSS", "8", True), ("passive", 5.08, -22.86, 90, "VSS", "9", True)]),
    "U4": dict(
        name="LIS2DW12TR", rect=((-12.7, 15.24), (12.7, -15.24)),
        props=[("Footprint", "Package_LGA:LGA-12_2x2mm_P0.5mm"),
               ("Datasheet", "https://www.st.com/resource/en/datasheet/lis2dw12.pdf"),
               ("Description", "3-axis accelerometer, I2C 0x19 (SA0=1), LGA-12 2x2"),
               ("MPN", "LIS2DW12TR"), ("Manufacturer", "STMicroelectronics"), ("LCSC", "C189624")],
        pins=[("input", -15.24, 5.08, 0, "CS", "2"), ("passive", -15.24, 2.54, 0, "SDO/SA0", "3"),
              ("bidirectional", -15.24, -2.54, 0, "SDA/SDI/SDO", "4"), ("input", -15.24, -5.08, 0, "SCL/SPC", "1"),
              ("output", 15.24, 5.08, 180, "INT1", "12"), ("output", 15.24, 2.54, 180, "INT2", "11"),
              ("power_in", 5.08, 17.78, 270, "VDD_IO", "10"), ("power_in", 10.16, 17.78, 270, "VDD", "9"),
              ("power_in", 5.08, -17.78, 90, "GND", "6"), ("passive", 5.08, -17.78, 90, "GND", "8", True),
              ("passive", 10.16, -17.78, 90, "RES", "7"), ("no_connect", -10.16, -12.7, 90, "NC", "5", True)]),
}
RGB = dict(
    name="LED_RGB_CA", rect=((-2.54, 10.16), (2.54, -10.16)),
    props=[("Footprint", "ull-pocket:LED_MHS110FRGBCT_SideView"),
           ("Datasheet", "https://www.lcsc.com/datasheet/lcsc_datasheet_2006111804_MEIHUA-MHS110FRGBCT_C496820.pdf"),
           ("Description", "Side-view RGB LED, common anode"),
           ("MPN", "MHS110FRGBCT"), ("Manufacturer", "MEIHUA"), ("LCSC", "C496820")],
    pins=[("passive", -5.08, 0, 0, "A", "1"), ("passive", 5.08, 7.62, 180, "R", "4"),
          ("passive", 5.08, 0, 180, "G", "3"), ("passive", 5.08, -7.62, 180, "B", "2")])

OLD = {"U2": "SHT31-DIS-B", "U3": "BMP585", "U4": "LIS3DHTR"}
NEW = dict((r, symbol(p["name"], p["props"], p["rect"], p["pins"])) for r, p in PARTS.items())
NEW["D6"] = symbol(RGB["name"], RGB["props"], RGB["rect"], RGB["pins"], ref="D")


def drop_sym(t, name):
    a, b = block(t, t.index('(symbol "%s"' % name))
    return t[:a].rstrip("\t") + t[b:].lstrip("\n")


# library: replace the three old symbols, add the RGB
for ref, old in OLD.items():
    L = drop_sym(L, old)
L = L[:L.rindex(")")] + "".join(NEW.values()) + ")\n"
open(LIB, "w").write(L)

# schematic cache (lib_symbols): same, with the library prefix
for old in OLD.values():
    s = drop_sym(s, "ull-pocket:" + old)
i = s.index("(lib_symbols")
a, b = block(s, i)
add = "".join(t.replace('\t(symbol "%s"' % PARTS.get(r, RGB)["name"], '\t(symbol "ull-pocket:%s"' % PARTS.get(r, RGB)["name"], 1)
              for r, t in NEW.items())
add = "\n".join("\t" + l if l else l for l in add.split("\n"))
s = s[:b - 1].rstrip() + "\n" + add.rstrip("\t") + "\t)" + s[b:]


# ---------------------------------------------------------------- helpers
def remove_range(a, b):
    global s
    while a > 0 and s[a - 1] in "\t":
        a -= 1
    if s[a - 1] == "\n" and s[b:b + 1] == "\n":
        b += 1
    s = s[:a] + s[b:]


def remove_at(x, y, kinds=("wire", "no_connect", "symbol", "label", "junction")):
    """Remove items touching (x, y); follow wires to their far end."""
    far = []
    for t, lab, a, b in sorted(touching(s, x, y), key=lambda r: -r[2]):
        if t not in kinds or (t == "symbol" and not lab.endswith(":GND")):
            continue
        if t == "wire":
            pts = [tuple(map(float, p)) for p in re.findall(r"\(xy ([-\d.]+) ([-\d.]+)\)", s[a:b])]
            far += [p for p in pts if abs(p[0] - x) > 0.01 or abs(p[1] - y) > 0.01]
        remove_range(a, b)
    for p in far:
        if not any(t == "wire" for t, *_ in touching(s, *p)):
            for t, lab, a, b in sorted(touching(s, *p), key=lambda r: -r[2]):
                if t == "no_connect" or (t == "symbol" and lab.endswith(":GND")):
                    remove_range(a, b)


def set_prop(t, name, val):
    return re.sub(r'(\(property "%s" ")[^"]*"' % re.escape(name), lambda m: m.group(1) + val + '"', t, count=1)


def set_pins(t, nums):
    t = re.sub(r'\t*\(pin "[^"]*"\s*\(uuid "[^"]*"\)\s*\)\n', "", t)
    pins = "".join('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, u()) for n in nums)
    i = t.index("\t\t(instances")
    return t[:i] + pins + t[i:]


def wire(x1, y1, x2, y2):
    return '\t(wire\n\t\t(pts\n\t\t\t(xy %g %g) (xy %g %g)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, u())


def label(name, x, y, ang=0):
    just = "left bottom" if ang == 0 else "right bottom"
    return '\t(label "%s"\n\t\t(at %g %g %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (name, x, y, ang, just, u())


def place(template_ref, ref, x, y, rot, props, nums, lib_id=None):
    """Copy a placed symbol, move it to (x, y, rot) keeping its text offsets."""
    a, b, tx, ty, trot, tlib = instance(s, template_ref)
    t = s[a:b]
    t = re.sub(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)',
               lambda m: "(at %g %g %d)" % (round(float(m.group(1)) - tx + x, 3), round(float(m.group(2)) - ty + y, 3), rot), t)
    if lib_id:
        t = t.replace('(lib_id "%s")' % tlib, '(lib_id "%s")' % lib_id)
    t = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), t)
    t = set_prop(t, "Reference", ref)
    t = re.sub(r'(\(reference ")[^"]*"', lambda m: m.group(1) + ref + '"', t)
    for k, v in props.items():
        t = set_prop(t, k, v)
    return "\t" + set_pins(t, nums) + "\n"


def add(text):
    global s
    i = s.rindex("\t(sheet_instances")
    s = s[:i] + text + s[i:]


# ---------------------------------------------------------------- sensors
# stubs on pins that no longer exist (positions from the rev 0.7 symbols)
U2 = instance(s, "U2")
for px, py in [(-15.24, -2.54), (15.24, 5.08), (15.24, 2.54), (10.16, -15.24)]:  # ADDR, ALERT, NRESET, R
    remove_at(*pin_xy(U2[2], U2[3], U2[4], px, py))
U4 = instance(s, "U4")
for px, py in [(15.24, 0), (15.24, -2.54), (15.24, -5.08)]:  # ADC1-3
    remove_at(*pin_xy(U4[2], U4[3], U4[4], px, py))

for ref, p in PARTS.items():
    a, b, *_ = instance(s, ref)
    t = s[a:b].replace('(lib_id "ull-pocket:%s")' % OLD[ref], '(lib_id "ull-pocket:%s")' % p["name"])
    t = set_prop(t, "Value", p["name"])
    for k, v in p["props"]:
        t = set_prop(t, k, v)
    t = set_pins(t, [pin[5] for pin in p["pins"]])
    s = s[:a] + t + s[b:]

# ---------------------------------------------------------------- RGB user LED
# old: label LED_USER - R22 - D6 - GND, vertical at x 365.76
for y in (134.62, 137.16, 147.32):
    remove_at(365.76, y)
for ref in ("D6", "R22"):
    a, b, *_ = instance(s, ref)
    remove_range(a, b)

DX, DY = 373.38, 144.78  # D6 origin; anode pin at DX-5.08, cathodes at DX+5.08
R_DS = {"R": ("R32", "1kR", "0402WGF1001TCE", "C11702", "Resistor 1k 1% 0402"),
        "G": ("R33", "1kR", "0402WGF1001TCE", "C11702", "Resistor 1k 1% 0402"),
        "B": ("R22", "470R", "0402WGF4700TCE", "C25117", "Resistor 470R 1% 0402")}
d6 = place("D1", "D6", DX, DY, 0, {"Value": "MHS110FRGBCT"}, ["1", "2", "3", "4"], lib_id="ull-pocket:LED_RGB_CA")
for k, v in RGB["props"]:
    d6 = set_prop(d6, k, v)
d6 = re.sub(r'\t*\(property "Sim.Pins".*?\n\t\t\)\n', "", d6, flags=re.S)  # LED_Small leftover
# texts centred above and below the body
d6 = re.sub(r'(\(property "Reference" "D6"\s*\(at )[-\d.]+ [-\d.]+ \d+', r"\g<1>%g %g 0" % (DX, DY - 11.43), d6)
d6 = re.sub(r'(\(property "Value" "MHS110FRGBCT"\s*\(at )[-\d.]+ [-\d.]+ \d+', r"\g<1>%g %g 0" % (DX, DY + 11.43), d6)
d6 = re.sub(r'\s*\(justify [^)]*\)', '', d6)
out = d6
ax = DX - 5.08
out += wire(ax, DY, ax - 2.54, DY)
for col, dy in (("R", -7.62), ("G", 0), ("B", 7.62)):
    ref, val, mpn, lcsc, desc = R_DS[col]
    y = DY + dy
    out += wire(DX + 5.08, y, DX + 7.62, y)
    out += place("R24", ref, DX + 10.16, y, 270, {"Value": val, "MPN": mpn, "LCSC": lcsc, "Description": desc}, ["1", "2"])
    out += label("LED_" + col, DX + 12.7, y)
add(out)

# +3V3 for the anode: copy an existing +3V3 power symbol
m = re.search(r'\n\t\(symbol\s*\(lib_id "ull-pocket:\+3V3"\)', s)
a, b = block(s, m.start() + 2)
t = s[a:b]
ox, oy = map(float, re.search(r"\(at ([-\d.]+) ([-\d.]+) \d+\)", t).groups())
t = re.sub(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)', lambda m: "(at %g %g %s)" % (round(float(m.group(1)) - ox + ax - 2.54, 3), round(float(m.group(2)) - oy + DY, 3), m.group(3)), t)
t = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), t)
n = max(int(x) for x in re.findall(r'"#PWR(\d+)"', s)) + 1
t = re.sub(r'"#PWR\d+"', '"#PWR%03d"' % n, t)
add("\t" + t + "\n")

# ---------------------------------------------------------------- MCU side labels
U1 = instance(s, "U1")
io = dict((nm, pin_xy(U1[2], U1[3], U1[4], px, py)) for n, nm, px, py in lib_pins(s, "ull-pocket:ESP32-C6-MINI-1-H4"))
# IO15: drop the no-connect, label it; shorten the R24 BTN3_N stub so the labels don't collide
remove_at(*io["IO15"], kinds=("no_connect",))
s = s.replace("(xy 53.34 137.16) (xy 38.1 137.16)", "(xy 45.72 137.16) (xy 38.1 137.16)")
s = re.sub(r'(\(label "BTN3_N"\s*\(at )53\.34 137\.16', r"\g<1>45.72 137.16", s)
add(label("LED_G", *io["IO15"], ang=180))
add(label("LED_R", *io["IO8"], ang=180))
s = s.replace('(label "LED_USER"', '(label "LED_B"')

# ---------------------------------------------------------------- notes, title
REPL = [
    ("I2C addresses:\\nSHT31 0x44 (ADDR=GND)\\nBMP585 0x46 (SDO=GND)\\nLIS3DH 0x19 (SA0=3V3)",
     "I2C addresses:\\nSHT40 0x44\\nBMP580 0x46 (SDO=GND)\\nLIS2DW12 0x19 (SA0=3V3)"),
    ("IO8 10k pull-up\\nIO14 LED_USER\\nIO9 BTN3_N (DN/BOOT, no wake)\\nIO15 unconnected",
     "IO8 LED_R (strap)\\nIO14 LED_B\\nIO15 LED_G\\nIO9 BTN3_N (DN/BOOT)"),
    ("also the pull-up of SW3 (DN). IO15 is\\nunconnected (strap only if JTAG_SEL burned).",
     "also the pull-up of SW3 (DN). IO15 drives\\nLED_G (strap only if JTAG_SEL burned)."),
    ('"USER LED (IO14)"', '"USER LED (RGB)"'),
    ("IO14 -> 470R -> blue: ~1 mA\\nGPIO high = on, 3.3 V\\nSilk: PWR, CHG, USR",
     "Common anode on +3V3; GPIO low = on.\\nR 1k ~1.5 mA, G 1k ~0.7 mA, B 470R ~1.5 mA\\nIO8 high at reset (R16): red stays off,\\nstrap unaffected. Silk: PWR, CHG, USR"),
    ('(rev "0.7")', '(rev "0.8")'),
    ("ESP32-C6, SHT31, BMP585, LIS3DH, MAX17048", "ESP32-C6, SHT40, BMP580, LIS2DW12, MAX17048"),
]
# BMP585-only layout note (marking area under the body)
m = re.search(r'\n\t\(text "U3 pin 9 \(marking', s)
a, b = block(s, m.start() + 2)
remove_range(a, b)
for a_, b_ in REPL:
    assert a_ in s, a_
    s = s.replace(a_, b_)
open(SCH, "w").write(s)
print("ok")
