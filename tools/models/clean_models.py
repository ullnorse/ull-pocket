#!/usr/bin/env python3
"""Render polish for vendor 3D models, in place: true part colours, EasyEDA logos gone.
Geometry and origins are untouched. One-shot; rerun from `git checkout` originals.
Run with the CAD venv (needs OCP)."""
import re
from pathlib import Path
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString as E
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorSurf, XCAFDoc_ColorGen
from OCP.TDF import TDF_LabelSequence
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS

L = Path(__file__).resolve().parents[2] / "lib/ull-pocket.3dshapes"
METAL = (0.62, 0.64, 0.66, 0.25, 0.25)
PLASTIC = (0.07, 0.07, 0.08, 0.3, 0.3)
PCB = (0.05, 0.06, 0.07, 0.3, 0.4)
GOLD = (0.83, 0.65, 0.22, 0.8, 0.5)


def patch(x0, x1, y0, y1, z):
    """Flat quad over the hole a removed logo leaves; copies its host shape's material."""
    return (x0, x1, y0, y1, z)


def quad(host, q):
    x0, x1, y0, y1, z = q
    app = re.search(r"appearance Appearance \{.*?\n    \}\n", host, re.S).group(0)
    return f"""Shape{{ {app} geometry IndexedFaceSet {{ ccw TRUE solid FALSE creaseAngle 0
 coord Coordinate {{ point [ {x0} {y0} {z}, {x1} {y0} {z}, {x1} {y1} {z}, {x0} {y1} {z} ] }}
 coordIndex [ 0,1,2,-1,0,2,3,-1 ] }} }}
"""


def wrl(name, colours=None, drop=(), keep=None, patches=()):
    """colours {shape: material}; drop shapes; keep {shape: face predicate(xyz list)}.
    Flat shading (creaseAngle) stops the mottling that smoothed normals give these meshes."""
    p = L / name
    parts = re.split(r"(?=Shape\s*\{)", p.read_text())
    out = [parts[0]]
    for i, sh in enumerate(parts[1:]):
        if i in drop:
            continue
        if colours and i in colours:
            r, g, b = colours[i][:3]
            spec, shine = colours[i][3:]
            sh = re.sub(r"diffuseColor [^\n]+", f"diffuseColor {r} {g} {b}", sh)
            sh = re.sub(r"specularColor [^\n]+", f"specularColor {spec} {spec} {spec}", sh)
            sh = re.sub(r"shininess [^\n]+", f"shininess {shine}", sh)
        if keep and i in keep:
            pts = re.search(r"point \[(.*?)\]", sh, re.S).group(1)
            v = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", pts)]
            m = re.search(r"coordIndex \[(.*?)\]", sh, re.S)
            ids = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
            faces, cur = [], []
            for n in ids:
                if n < 0:
                    faces.append(cur)
                    cur = []
                else:
                    cur.append(n)
            good = [f for f in faces if all(keep[i](v[3 * n:3 * n + 3]) for n in f)]
            assert good, (name, i)
            text = ",".join(",".join(map(str, f)) + ",-1" for f in good)
            sh = sh[: m.start(1)] + text + sh[m.end(1):]
        sh = sh.replace("solid FALSE", "solid FALSE\n        creaseAngle 0.4", 1)
        out.append(sh)
    p.write_text("".join(out) + "".join(quad(out[1], q) for q in patches))


def step(name, recolour):
    """recolour {(r, g, b) rounded to 2 dp: (r, g, b)}, applied face by face."""
    p = str(L / name)
    doc = TDocStd_Document(E("x"))
    rd = STEPCAFControl_Reader()
    rd.SetColorMode(True)
    rd.ReadFile(p)
    rd.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    e = TopExp_Explorer(st.GetShape_s(free.Value(1)), TopAbs_FACE)
    n = 0
    while e.More():
        f = TopoDS.Face_s(e.Current())
        c = Quantity_Color()
        if ct.GetColor(f, XCAFDoc_ColorSurf, c) or ct.GetColor(f, XCAFDoc_ColorGen, c):
            k = (round(c.Red(), 2), round(c.Green(), 2), round(c.Blue(), 2))
            if k in recolour:
                ct.SetColor(f, Quantity_Color(*recolour[k], Quantity_TOC_RGB), XCAFDoc_ColorSurf)
                n += 1
        e.Next()
    assert n, name
    w = STEPCAFControl_Writer()
    w.SetColorMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    w.Write(p)


wrl("USB_C_HRO_TYPE-C-31-M-12_ee.wrl", {0: METAL, 2: METAL, 4: METAL, 6: GOLD}, drop=(7, 8, 9))
wrl("ESP32-C6-MINI-1_ee.wrl",
    {0: METAL, 6: METAL, 7: PCB, 1: PCB, 2: PCB, 3: PCB, 5: PCB, 4: GOLD, 8: GOLD},
    drop=range(9, 21), patches=[patch(0.40, 1.90, -1.62, -1.10, 0.992)])
wrl("VQFN-16_3x3_EP1.68_ee.wrl", {0: PLASTIC, 1: METAL}, drop=range(3, 14),
    patches=[patch(0.08, 0.50, -0.50, -0.33, 0.31)], keep={2: lambda c: c[0] < -0.2})  # shape 2 holds the pin-1 dot and part of the logo
wrl("Bosch_LGA-10_2x2_BMP580_ee.wrl", {2: METAL, 1: GOLD}, drop=range(4, 15),
    keep={3: lambda c: c[2] > 0.31})  # shape 3 holds the vent hole and part of the logo

LENS = (0.80, 0.82, 0.85, 0.5, 0.5)
wrl("LED_MHS110FRGBCT_ee.wrl", {3: LENS, 12: LENS})

BEIGE = (0.68, 0.63, 0.53)
step("SW-SMD_2P-TS24CA.step", {(0.0, 0.0, 0.0): BEIGE})
step("TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2.step", {(1.0, 1.0, 1.0): (0.05, 0.05, 0.05)})
step("FPC-SMD_24P-P0.50_FPC-05FB-24PH20.step", {(0.0, 0.0, 0.0): BEIGE})
