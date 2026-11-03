"""Rev 0.8 footprints and 3D models for lib/ull-pocket.pretty / .3dshapes.

SHT40: KiCad stock SHT4x NoCentralPad land pattern (= Sensirion), JLC 3D model.
BMP580: KiCad ST_HLGA-10 geometry with Bosch's pads (land pattern = terminals, 0.25 x 0.275).
MHS110FRGBCT: JLC/EasyEDA pads (C496820) rotated so the dome points to +y, JLC 3D model.
"""
import os, re, shutil, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOCK = "/usr/share/kicad/footprints"
EE = os.path.join(ROOT, "build/review/prod/ee")
PRETTY = os.path.join(ROOT, "lib/ull-pocket.pretty")
SHAPES = os.path.join(ROOT, "lib/ull-pocket.3dshapes")
MODEL = "${KIPRJMOD}/lib/ull-pocket.3dshapes/"


def u():
    return str(uuid.uuid4())


def set_model(t, name, rot=0):
    m = '\t(model "%s%s"\n\t\t(offset\n\t\t\t(xyz 0 0 0)\n\t\t)\n\t\t(scale\n\t\t\t(xyz 1 1 1)\n\t\t)\n\t\t(rotate\n\t\t\t(xyz 0 0 %g)\n\t\t)\n\t)\n' % (MODEL, name, rot)
    t = re.sub(r'\t\(model .*?\n\t\)\n', '', t, flags=re.S)
    return t[:t.rindex(')')] + m + ')\n'


def copy_model(lcsc, src, dst):
    shutil.copy(os.path.join(EE, lcsc, "lib.3dshapes", src), os.path.join(SHAPES, dst))


def rename(t, old, new, descr=None):
    t = t.replace('(footprint "%s"' % old, '(footprint "%s"' % new, 1)
    t = re.sub(r'(\(property "Value" ")[^"]*"', r'\g<1>%s"' % new, t, count=1)
    if descr:
        t = re.sub(r'\(descr "[^"]*"\)', '(descr "%s")' % descr, t, count=1)
    return t


# ---- SHT40
t = open(os.path.join(STOCK, "Sensor_Humidity.pretty/Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad.kicad_mod")).read()
t = rename(t, "Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad", "Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x",
           "Sensirion SHT4x DFN-4 1.5x1.5 mm, land pattern per SHT4x datasheet (4x 0.5x0.3, centre die pad not soldered, no copper under the sensor); JLC 3D model (C2909890)")
copy_model("C2909890", "DFN-4_L1.5-W1.5-P0.8.wrl", "Sensirion_DFN-4_1.5x1.5_ee.wrl")
open(os.path.join(PRETTY, "Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x.kicad_mod"), "w").write(set_model(t, "Sensirion_DFN-4_1.5x1.5_ee.wrl"))

# ---- BMP580: Bosch says use the terminal outline as the land pattern
t = open(os.path.join(STOCK, "Package_LGA.pretty/ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y.kicad_mod")).read()
t = rename(t, "ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y", "Bosch_LGA-10_2x2mm_P0.5mm_BMP580",
           "Bosch BMP580 LGA-10 2x2x0.8 mm; pads = terminals per datasheet 8.1.2/8.2 (0.25 x 0.275 at +-0.7625); port hole on top; JLC 3D model (C22391138)")


def bosch_pad(m):
    num, x, y = m.group(1), float(m.group(2)), float(m.group(3))
    size = "0.275 0.25" if abs(abs(x) - 0.7625) < 1e-3 else "0.25 0.275"
    return '(pad "%s" smd rect\n\t\t(at %s %s)\n\t\t(size %s)' % (num, m.group(2), m.group(3), size)


t = re.sub(r'\(pad "(\d+)" smd roundrect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size [\d.]+ [\d.]+\)', bosch_pad, t)
t = re.sub(r'\s*\(roundrect_rratio [\d.]+\)', '', t)
copy_model("C22391138", "LGA-10_L2.0-W2.0-P0.50-TL_BMP580.wrl", "Bosch_LGA-10_2x2_BMP580_ee.wrl")
open(os.path.join(PRETTY, "Bosch_LGA-10_2x2mm_P0.5mm_BMP580.kicad_mod"), "w").write(set_model(t, "Bosch_LGA-10_2x2_BMP580_ee.wrl"))

# ---- MHS110FRGBCT side-view RGB, common anode. EasyEDA C496820 pads rotated 180 deg:
# dome (emitting face) toward +y = board edge. Body 3.2 wide, back y=-0.04, front y=0.48, dome tip y=1.47.
PADS = [("1", -1.4, 0.2, 0.55, 0.8), ("2", -0.4, -0.2, 0.5, 0.5), ("3", 0.4, -0.2, 0.5, 0.5), ("4", 1.4, 0.2, 0.55, 0.8)]


def line(x1, y1, x2, y2, layer, w):
    return '\t(fp_line\n\t\t(start %g %g)\n\t\t(end %g %g)\n\t\t(stroke\n\t\t\t(width %g)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer "%s")\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, x2, y2, w, layer, u())


def arc(x1, y1, xm, ym, x2, y2, layer, w):
    return '\t(fp_arc\n\t\t(start %g %g)\n\t\t(mid %g %g)\n\t\t(end %g %g)\n\t\t(stroke\n\t\t\t(width %g)\n\t\t\t(type solid)\n\t\t)\n\t\t(layer "%s")\n\t\t(uuid "%s")\n\t)\n' % (x1, y1, xm, ym, x2, y2, w, layer, u())


def prop(name, val, x, y, layer, size, hide=False):
    return '\t(property "%s" "%s"\n\t\t(at %g %g 0)\n\t\t(layer "%s")\n%s\t\t(uuid "%s")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %g %g)\n\t\t\t\t(thickness %g)\n\t\t\t)\n\t\t)\n\t)\n' % (
        name, val, x, y, layer, "\t\t(hide yes)\n" if hide else "", u(), size, size, round(size / 6, 3))


name = "LED_MHS110FRGBCT_SideView"
o = '(footprint "%s"\n\t(version 20260206)\n\t(generator "pcbnew")\n\t(generator_version "10.0")\n\t(layer "F.Cu")\n' % name
o += '\t(descr "MEIHUA MHS110FRGBCT side-view RGB LED, common anode, body 3.2 x 0.5 x 1.0 mm + dome R1.0; JLC/EasyEDA pads (C496820): pad 1 anode, 2 blue K, 3 green K, 4 red K; dome toward +y, place it at the board edge")\n'
o += '\t(tags "LED RGB side view right angle MHS110FRGBCT C496820")\n'
o += prop("Reference", "REF**", 0, -1.3, "F.SilkS", 0.8)
o += prop("Value", name, 0, 2.2, "F.Fab", 0.5)
o += prop("Datasheet", "", 0, 0, "F.Fab", 1, True)
o += prop("Description", "Side-view RGB LED, common anode", 0, 0, "F.Fab", 1, True)
o += '\t(attr smd)\n'
# fab: body and dome
o += line(-1.6, -0.04, 1.6, -0.04, "F.Fab", 0.05) + line(1.6, -0.04, 1.6, 0.48, "F.Fab", 0.05)
o += line(1.6, 0.48, -1.6, 0.48, "F.Fab", 0.05) + line(-1.6, 0.48, -1.6, -0.04, "F.Fab", 0.05)
o += arc(-1.0, 0.48, 0, 1.48, 1.0, 0.48, "F.Fab", 0.05)
# silk: back edge, and a pin-1 (anode) bar behind pad 1
o += line(-0.9, -0.7, 0.9, -0.7, "F.SilkS", 0.12)
o += line(-1.6, -0.6, -1.2, -0.6, "F.SilkS", 0.12)
# courtyard: pads + 0.1 and the dome
o += line(-1.78, -0.55, 1.78, -0.55, "F.CrtYd", 0.05) + line(1.78, -0.55, 1.78, 0.7, "F.CrtYd", 0.05)
o += line(1.78, 0.7, 1.08, 0.7, "F.CrtYd", 0.05) + arc(1.08, 0.7, 0, 1.58, -1.08, 0.7, "F.CrtYd", 0.05)
o += line(-1.08, 0.7, -1.78, 0.7, "F.CrtYd", 0.05) + line(-1.78, 0.7, -1.78, -0.55, "F.CrtYd", 0.05)
o += '\t(fp_text user "${REFERENCE}"\n\t\t(at 0 0.22 0)\n\t\t(layer "F.Fab")\n\t\t(uuid "%s")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 0.3 0.3)\n\t\t\t\t(thickness 0.05)\n\t\t\t)\n\t\t)\n\t)\n' % u()
for n, x, y, w, h in PADS:
    o += '\t(pad "%s" smd rect\n\t\t(at %g %g)\n\t\t(size %g %g)\n\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n\t\t(uuid "%s")\n\t)\n' % (n, x, y, w, h, u())
o += '\t(embedded_fonts no)\n)\n'
copy_model("C496820", "LED-ARRAY-SMD_MHS110FRGBCT.wrl", "LED_MHS110FRGBCT_ee.wrl")
open(os.path.join(PRETTY, name + ".kicad_mod"), "w").write(set_model(o, "LED_MHS110FRGBCT_ee.wrl", 180))
print("ok")
