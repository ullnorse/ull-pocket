"""ull-pocket case, draft 1: front shell (display window, PCB bosses, button plungers, USB-C, LED
windows, SHT40 vent, battery rails) + snap-on back cover + 3 button plungers.

Coordinates follow docs/mechanical.md: x right, y down from the board's top-left corner (top view, F
side), z up from the PCB's B side (display side) towards the battery. The display faces -z.
Placeholder sizes for the display and battery: re-measure the real parts and edit DISPLAY/BATTERY.

Run with CadQuery: ~/.venvs/cad/bin/python tools/case/case.py  -> build/case/*.step, *.stl
"""
import os
import cadquery as cq

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "case")

# ---- parts (mm) --------------------------------------------------------------------------------
PCB_W, PCB_H, PCB_T = 40.0, 44.5, 1.6
HOLES = [(2.8, 41.3), (37.2, 41.3)]
DISPLAY = dict(x0=2.48, x1=39.80, y0=4.2, y1=36.0, t=1.0, tape=0.15,   # glass, GDEY0154D67
               va=(4.53, 32.23, 6.25, 33.95))                         # viewing area, datasheet p.6
BATTERY = dict(x0=0.0, x1=40.0, y0=14.0, y1=44.0, t=5.5, shelf=3.5)    # 503040, +0.5 swell
BUTTONS_Y = [20.5, 27.5, 34.5]       # TS24CA actuator tip at x -0.2, centre 0.9 above F
BTN_Z = PCB_T + 0.9
USB = dict(x=20.0, z=PCB_T + 1.63, w=8.94, h=3.26)                    # TYPE-C-31-M-12 mouth
LEDS = [(26.8, PCB_T + 0.3, 1.2, 1.2), (29.8, PCB_T + 0.3, 1.2, 1.2),  # D5, D1: x, z, w, h
        (33.05, PCB_T + 0.5, 1.8, 1.4)]                                # D6 RGB dome
VENT_X = (11.0, 17.0)                # SHT40 island, top wall, F side

# ---- case --------------------------------------------------------------------------------------
WALL, FRONT, BACK = 1.6, 1.8, 1.2
GAP_GLASS = 0.1                      # glass to bezel
IN_X = (-2.4, 41.6)                  # J2 plug + lead pocket left, FPC bend right
IN_Y = (-5.7, 45.4)                  # antenna overhang 5.4 top, D6 dome 0.65 bottom
Z_IN0 = -(DISPLAY["tape"] + DISPLAY["t"] + GAP_GLASS)                 # front wall inner face
Z_IN1 = PCB_T + BATTERY["shelf"] + BATTERY["t"] + 0.2                 # back cover inner face
Z_OUT0, Z_OUT1 = Z_IN0 - FRONT, Z_IN1 + BACK
OUT_X = (IN_X[0] - WALL, IN_X[1] + WALL)
OUT_Y = (IN_Y[0] - WALL, IN_Y[1] + WALL)
R_OUT = 3.0
CLR = 0.15                           # sliding fit
LIP_T, LIP_H = 1.0, 3.0


def box(x0, x1, y0, y1, z0, z1):
    """Axis box in board coordinates (y down)."""
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(
        ((x0 + x1) / 2, -(y0 + y1) / 2, (z0 + z1) / 2))


def rbox(x0, x1, y0, y1, z0, z1, r):
    return box(x0, x1, y0, y1, z0, z1).edges("|Z").fillet(r)


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, -y, z0))


def ybar(x0, x1, y0, y1, zc, h, r):
    """Box along y with rounded edges parallel to y (slots through the top/bottom walls)."""
    b = box(x0, x1, y0, y1, zc - h / 2, zc + h / 2)
    return b.edges("|Y").fillet(r) if r else b


def xbar(x0, x1, y0, y1, zc, h, r):
    b = box(x0, x1, y0, y1, zc - h / 2, zc + h / 2)
    return b.edges("|X").fillet(r) if r else b


def front_shell():
    s = rbox(*OUT_X, *OUT_Y, Z_OUT0, Z_IN1, R_OUT).faces("<Z").edges().fillet(1.0)
    s = s.cut(rbox(*IN_X, *IN_Y, Z_IN0, Z_IN1 + 1, R_OUT - WALL))

    # display window over the viewing area, 0.25 margin, chamfered outward
    x0, x1, y0, y1 = DISPLAY["va"]
    m = 0.25
    win = (cq.Workplane("XY").workplane(offset=Z_IN0)
           .center((x0 + x1) / 2, -(y0 + y1) / 2).rect(x1 - x0 + 2 * m, y1 - y0 + 2 * m)
           .workplane(offset=-FRONT - 0.01).rect(x1 - x0 + 2 * m + 2 * FRONT, y1 - y0 + 2 * m + 2 * FRONT)
           .loft())
    s = s.cut(win)

    # PCB supports up to the B side (z 0): bosses with M2 pilot holes, ledges on bare edges
    for x, y in HOLES:
        s = s.union(cyl(x, y, Z_IN0, 0, 3.4))
        s = s.cut(cyl(x, y, Z_OUT0 + 0.5, 0.01, 1.6))
    s = s.union(box(IN_X[0], 1.2, 0.0, 2.2, Z_IN0, 0))                      # top-left, clear of the moat
    s = s.union(box(IN_X[0], 1.2, 37.5, 44.5, Z_IN0, 0))                    # left chin
    s = s.union(box(18.5, 26.0, -0.01, 1.0, Z_IN0, 0))                      # top edge, clear of J4 pads
    s = s.union(box(5.5, 13.5, 43.6, 44.5, Z_IN0, 0))                       # bottom edge, left of J1
    s = s.union(box(26.5, 34.5, 43.6, 44.5, Z_IN0, 0))                      # bottom edge, right of J1
    # J1 shell-leg solder tails poke through the B side
    for x in (15.68, 24.32):
        s = s.cut(box(x - 1.1, x + 1.1, 36.8, 43.8, Z_IN0 - 0.8, Z_IN0 + 0.01))

    # battery rails (left and right walls), top at the shelf height
    zs = PCB_T + BATTERY["shelf"]
    s = s.union(box(IN_X[0], 1.0, BATTERY["y0"], BATTERY["y1"], zs - 1.0, zs))
    s = s.union(box(39.0, IN_X[1], BATTERY["y0"], BATTERY["y1"], zs - 1.0, zs))

    # USB-C: opening for the receptacle, recess outside for the plug overmold
    u = USB
    s = s.cut(ybar(u["x"] - u["w"] / 2 - 0.35, u["x"] + u["w"] / 2 + 0.35, IN_Y[1] - 1, OUT_Y[1] + 1,
                   u["z"], u["h"] + 0.7, 1.4))
    s = s.cut(ybar(u["x"] - 5.5, u["x"] + 5.5, IN_Y[1] + 0.1, OUT_Y[1] + 1, u["z"], 6.6, 2.5))
    # LED windows
    for x, z, w, h in LEDS:
        s = s.cut(ybar(x - w / 2, x + w / 2, IN_Y[1] - 1, OUT_Y[1] + 1, z, h, min(w, h) / 2 - 0.01))
    # SHT40 vent: slots in the top wall on the F side
    for i in range(4):
        x = VENT_X[0] + 0.6 + i * 1.6
        s = s.cut(ybar(x, x + 0.8, OUT_Y[0] - 1, IN_Y[0] + 1, PCB_T + 1.9, 3.0, 0.39))
    # button plunger holes
    for y in BUTTONS_Y:
        s = s.cut(xbar(OUT_X[0] - 1, IN_X[0] + 1, y - 1.4, y + 1.4, BTN_Z, 2.0, 0.6))

    # snap grooves for the back cover's lip ridges (left and right walls)
    for y in (10.0, 32.0):
        for x0, x1 in ((IN_X[0] - 0.4, IN_X[0] + 0.1), (IN_X[1] - 0.1, IN_X[1] + 0.4)):
            s = s.cut(box(x0, x1, y - 4.0, y + 4.0, Z_IN1 - 2.2, Z_IN1 - 1.4))
    # pry notch at the bottom edge
    s = s.cut(box(30.0, 36.0, OUT_Y[1] - 0.8, OUT_Y[1] + 1, Z_IN1 - 0.8, Z_IN1 + 1))
    return s


def back_cover():
    c = rbox(*OUT_X, *OUT_Y, Z_IN1, Z_OUT1, R_OUT).faces(">Z").edges().fillet(1.0)
    lx = (IN_X[0] + CLR, IN_X[1] - CLR)
    ly = (IN_Y[0] + CLR, IN_Y[1] - CLR)
    lip = rbox(*lx, *ly, Z_IN1 - LIP_H, Z_IN1, R_OUT - WALL - CLR)
    lip = lip.cut(rbox(lx[0] + LIP_T, lx[1] - LIP_T, ly[0] + LIP_T, ly[1] - LIP_T,
                       Z_IN1 - LIP_H - 1, Z_IN1 + 0.01, R_OUT - WALL - CLR - LIP_T))
    c = c.union(lip)
    # ridges that click into the shell grooves
    for y in (10.0, 32.0):
        for x0, x1 in ((lx[0] - 0.3, lx[0] + 0.01), (lx[1] - 0.01, lx[1] + 0.3)):
            c = c.union(xbar(x0, x1, y - 3.6, y + 3.6, Z_IN1 - 1.8, 0.6, 0))
    # relief slots so the lip flexes at the ridges
    for y in (10.0, 32.0):
        for yy in (y - 4.2, y + 4.2):
            for x0 in (lx[0], lx[1] - LIP_T):
                c = c.cut(box(x0 - 0.01, x0 + LIP_T + 0.01, yy - 0.3, yy + 0.3, Z_IN1 - LIP_H - 1, Z_IN1 - 0.4))
    return c


def plunger(y):
    """Button plunger: cap through the wall, flange inside, nose onto the TS24CA actuator."""
    p = xbar(OUT_X[0] - 0.6, IN_X[0], y - 1.2, y + 1.2, BTN_Z, 1.6, 0.5)    # shaft + cap
    p = p.union(xbar(IN_X[0], IN_X[0] + 0.8, y - 2.0, y + 2.0, BTN_Z, 2.6, 0))  # flange
    p = p.union(xbar(IN_X[0] + 0.8, -0.25, y - 1.0, y + 1.0, BTN_Z, 1.2, 0))    # nose, 0.05 gap
    return p


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = {"front_shell": front_shell(), "back_cover": back_cover()}
    for i, y in enumerate(BUTTONS_Y):
        parts[f"button_{i + 1}"] = plunger(y)
    for name, p in parts.items():
        cq.exporters.export(p, os.path.join(OUT, f"{name}.step"))
        cq.exporters.export(p, os.path.join(OUT, f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
    bb = parts["front_shell"].union(parts["back_cover"]).val().BoundingBox()
    print(f"outer {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
