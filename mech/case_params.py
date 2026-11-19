"""ull-pocket case: shared dimensions and helpers for the FreeCAD part scripts in mech/.

Ported from the retired CadQuery draft 1 (case.py). Same names, same values, same frame:
  x right and y down from the board's top-left corner (KiCad 100,100), top view on the F side;
  a board y maps to FreeCAD -y, exactly as case.py does, so every part sits in assembly position;
  z up from the PCB's B side (display side, z 0) towards the battery (F side at z 1.6).
  The display faces -z. All lengths in mm.
The parts therefore compare 1:1 with the STEPs case.py wrote, and the bare board (KiCad STEP
exported with --user-origin 100x100mm) drops in without any offset.

Each part script (front_shell.py, back_cover.py, button_N.py) imports this module, builds its
shape, and calls export_part(), which checks it, saves mech/<part>.FCStd, exports mech/<part>.step
with its colour and refreshes the measured features in mech/<part>.fab.json.
Run a part: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/<part>.py
"""
import json
import os
import traceback

import FreeCAD as App
import Part

MECH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MECH)
BUILD = os.path.join(ROOT, "build", "case")

# ---- parts (mm) --------------------------------------------------------------------------------
PCB_W, PCB_H, PCB_T = 40.0, 44.5, 1.6
HOLES = [(2.8, 41.3), (37.2, 41.3)]
DISPLAY = dict(x0=2.48, x1=39.80, y0=4.2, y1=36.0, t=1.0, tape=0.15,   # glass, GDEY0154D67
               va=(4.53, 32.23, 6.25, 33.95))                         # viewing area, datasheet p.6
BATTERY = dict(x0=0.0, x1=40.0, y0=14.0, y1=44.0, t=10.5, shelf=3.5)   # 103040, +0.5 swell
BUTTONS_Y = [20.5, 27.5, 34.5]       # TS24CA actuator tip at x -0.2, centre 0.9 above F
BTN_Z = PCB_T + 0.9
USB = dict(x=20.0, z=PCB_T + 1.63, w=8.94, h=3.26)                    # TYPE-C-31-M-12 mouth
LEDS = [(26.8, PCB_T + 0.3, 1.2, 1.2), (29.8, PCB_T + 0.3, 1.2, 1.2),  # D5, D1: x, z, w, h
        (33.05, PCB_T + 0.5, 1.8, 1.4)]                                # D6 RGB dome
VENT_X = (11.0, 17.0)                # SHT40 island, top wall, F side

# ---- case --------------------------------------------------------------------------------------
WALL, FRONT, BACK = 1.6, 1.8, 1.2
GAP_GLASS = 0.25                     # glass to bezel
IN_X = (-3.2, 41.6)                  # J2 plug + lead pocket left, FPC bend right
IN_Y = (-5.7, 45.4)                  # antenna overhang 5.4 top, D6 dome 0.65 bottom
Z_IN0 = -(DISPLAY["tape"] + DISPLAY["t"] + GAP_GLASS)                 # front wall inner face
Z_IN1 = PCB_T + BATTERY["shelf"] + BATTERY["t"] + 0.2                 # back cover inner face
Z_OUT0, Z_OUT1 = Z_IN0 - FRONT, Z_IN1 + BACK
OUT_X = (IN_X[0] - WALL, IN_X[1] + WALL)
OUT_Y = (IN_Y[0] - WALL, IN_Y[1] + WALL)
R_OUT = 3.0
CLR = 0.15                           # sliding fit
LIP_T, LIP_H = 1.0, 3.0

# ---- colours (r, g, b 0..1) ----------------------------------------------------------------------
HOUSING_COLOR = (0.20, 0.20, 0.22)   # dark grey printed plastic
BUTTON_COLOR = (0.62, 0.62, 0.64)    # lighter grey printed plastic

TOL = 1e-6


# ---- helpers (Part equivalents of case.py's CadQuery helpers) ------------------------------------
def _parallel_edges(shape, axis):
    """Straight edges of `shape` parallel to axis 'x', 'y' or 'z' (CadQuery's '|X' selector)."""
    i = "xyz".index(axis)
    out = []
    for e in shape.Edges:
        if not isinstance(e.Curve, Part.Line):
            continue
        d = e.Vertexes[-1].Point - e.Vertexes[0].Point
        if d.Length > TOL and abs(abs(d[i]) - d.Length) < 1e-7:
            out.append(e)
    return out


def box(x0, x1, y0, y1, z0, z1):
    """Axis box in board coordinates (y down)."""
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, -y1, z0))


def rbox(x0, x1, y0, y1, z0, z1, r):
    """Box with its four vertical edges rounded to r."""
    b = box(x0, x1, y0, y1, z0, z1)
    return b.makeFillet(r, _parallel_edges(b, "z"))


def cyl(x, y, z0, z1, d):
    return Part.makeCylinder(d / 2, z1 - z0, App.Vector(x, -y, z0))


def ybar(x0, x1, y0, y1, zc, h, r):
    """Box along y with rounded edges parallel to y (slots through the top/bottom walls)."""
    b = box(x0, x1, y0, y1, zc - h / 2, zc + h / 2)
    return b.makeFillet(r, _parallel_edges(b, "y")) if r else b


def xbar(x0, x1, y0, y1, zc, h, r):
    b = box(x0, x1, y0, y1, zc - h / 2, zc + h / 2)
    return b.makeFillet(r, _parallel_edges(b, "x")) if r else b


def fillet_face_edges(shape, side, r):
    """Round every edge of the planar face at the z extreme (case.py's faces('<Z' / '>Z').edges())."""
    zs = [f.CenterOfMass.z for f in shape.Faces]
    z = min(zs) if side == "<Z" else max(zs)
    face = [f for f in shape.Faces if abs(f.CenterOfMass.z - z) < TOL][0]
    return shape.makeFillet(r, face.Edges)


def rect_wire(cx, cy, z, w, h):
    """Rectangle wire centred on (cx, cy) in FreeCAD coordinates, at height z."""
    pts = [App.Vector(cx - w / 2, cy - h / 2, z), App.Vector(cx + w / 2, cy - h / 2, z),
           App.Vector(cx + w / 2, cy + h / 2, z), App.Vector(cx - w / 2, cy + h / 2, z)]
    return Part.makePolygon(pts + [pts[0]])


def clean(shape):
    """Merge coplanar faces left by booleans (CadQuery's clean=True)."""
    return shape.removeSplitter()


# ---- output ------------------------------------------------------------------------------------
def measure(shape):
    """Volume, area and tight bounding box of a shape, as the fab file wants them."""
    bb = shape.optimalBoundingBox(False, False)
    size = sorted([bb.XLength, bb.YLength, bb.ZLength], reverse=True)
    return {
        "volume_cm3": round(shape.Volume / 1000.0, 4),
        "area_cm2": round(shape.Area / 100.0, 3),
        "size_x_mm": round(size[0], 2),
        "size_y_mm": round(size[1], 2),
        "size_z_mm": round(size[2], 2),
    }


def open_log(name):
    os.makedirs(BUILD, exist_ok=True)
    return open(os.path.join(BUILD, name + ".log"), "w")


def write_fab(name, title, shape):
    """Write mech/<name>.fab.json, keeping any keys a person added, with fresh features."""
    path = os.path.join(MECH, name + ".fab.json")
    fab = {}
    if os.path.exists(path):
        with open(path) as f:
            fab = json.load(f)
    fab.update({"kind": "3dp", "name": fab.get("name", title), "source": name + ".step"})
    fab.setdefault("qty", 1)
    fab.setdefault("order", False)
    fab.setdefault("options", {"process": "mjf", "material": "pa12", "color": "black"})
    fab["features"] = measure(shape)
    with open(path, "w") as f:
        json.dump(fab, f, indent=2)
        f.write("\n")
    return fab


def save_doc(doc, path):
    """Save the document, replacing the old file outright (no .FCBak backup left in mech/)."""
    if os.path.exists(path):
        os.remove(path)
    doc.saveAs(path)


def export_part(name, title, shape, color, log, single_solid=True):
    """Check the shape, save mech/<name>.FCStd, export mech/<name>.step in colour, write the fab file."""
    import ImportGui
    if not shape.isValid():
        raise RuntimeError(name + ": shape is not valid")
    n = len(shape.Solids)
    if n != 1:
        msg = "%s: %d solids (expected 1)" % (name, n)
        if single_solid:
            raise RuntimeError(msg)
        log.write("WARNING " + msg + ": " + ", ".join(
            "%.3f mm3" % s.Volume for s in shape.Solids) + "\n")
    doc = App.newDocument(name)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    doc.recompute()
    if App.GuiUp:
        obj.ViewObject.ShapeColor = color
    save_doc(doc, os.path.join(MECH, name + ".FCStd"))
    ImportGui.export([obj], os.path.join(MECH, name + ".step"))
    fab = write_fab(name, title, shape)
    bb = shape.optimalBoundingBox(False, False)
    log.write("%s: valid, %d solid(s), volume %.4f mm3, area %.4f mm2\n" % (name, n, shape.Volume, shape.Area))
    log.write("  bbox x %.4f..%.4f  y %.4f..%.4f  z %.4f..%.4f\n" % (
        bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    log.write("  fab features %s\n" % json.dumps(fab["features"]))
    return obj


def start_gui():
    """Bring up FreeCAD's GUI (offscreen under QT_QPA_PLATFORM=offscreen) so colours reach the STEP."""
    if not App.GuiUp:
        import FreeCADGui
        FreeCADGui.showMainWindow()


def run(name, build, log_name=None):
    """Run a part script's build function in the offscreen GUI: log, then always quit."""
    log = open_log(log_name or name)
    code = 0
    try:
        start_gui()
        build(log)
        log.write("OK\n")
    except Exception:
        log.write(traceback.format_exc())
        code = 1
    log.close()
    os._exit(code)
