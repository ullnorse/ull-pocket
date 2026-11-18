"""ull-pocket front shell: display window, PCB bosses and ledges, battery rails and stops,
USB-C, LED windows, SHT40 vent, button plunger holes, snap grooves, pry notch.
Port of tools/case/case.py front_shell(); dimensions live in case_params.py.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/front_shell.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App  # noqa: E402
import Part  # noqa: E402
from case_params import *  # noqa: E402,F401,F403
import case_params as cp  # noqa: E402

NAME = "front_shell"


def front_shell():
    s = fillet_face_edges(rbox(*OUT_X, *OUT_Y, Z_OUT0, Z_IN1, R_OUT), "<Z", 1.0)
    s = s.cut(rbox(*IN_X, *IN_Y, Z_IN0, Z_IN1 + 1, R_OUT - WALL))

    # display window over the viewing area, 0.25 margin, chamfered outward
    x0, x1, y0, y1 = DISPLAY["va"]
    m = 0.25
    cx, cy = (x0 + x1) / 2, -(y0 + y1) / 2
    w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    win = Part.makeLoft([rect_wire(cx, cy, Z_IN0, w, h),
                         rect_wire(cx, cy, Z_IN0 - FRONT - 0.01, w + 2 * FRONT, h + 2 * FRONT)],
                        True, True)
    s = s.cut(win)

    # PCB supports up to the B side (z 0): bosses with M2 pilot holes, ledges on bare edges
    for x, y in HOLES:
        s = s.fuse(cyl(x, y, Z_IN0, 0, 3.4))
        s = s.cut(cyl(x, y, Z_OUT0 + 0.5, 0.01, 1.6))
    s = s.fuse(box(IN_X[0], 1.2, 0.0, 2.2, Z_IN0, 0))                      # top-left, clear of the moat
    s = s.fuse(box(IN_X[0], 1.2, 37.5, 44.5, Z_IN0, 0))                    # left chin
    s = s.fuse(box(18.5, 26.0, -0.01, 1.0, Z_IN0, 0))                      # top edge, clear of J4 pads
    s = s.fuse(box(5.5, 13.5, 43.6, 44.5, Z_IN0, 0))                       # bottom edge, left of J1
    s = s.fuse(box(26.5, 34.5, 43.6, 44.5, Z_IN0, 0))                      # bottom edge, right of J1
    # J1 shell-leg solder tails poke through the B side
    for x in (15.68, 24.32):
        s = s.cut(box(x - 1.1, x + 1.1, 36.8, 43.8, Z_IN0 - 0.8, Z_IN0 + 0.01))

    # battery rails (left and right walls), top at the shelf height
    zs = PCB_T + BATTERY["shelf"]
    # the left rail starts under the -y stop so that stop is joined to the shell (it was a loose block)
    s = s.fuse(box(IN_X[0], 1.0, BATTERY["y0"] - 1.3, BATTERY["y1"], zs - 1.0, zs))
    s = s.fuse(box(39.0, IN_X[1], BATTERY["y0"], BATTERY["y1"], zs - 1.0, zs))
    # stops so the cell can't slide off a rail or into J2; the lead pocket stays open at -x, y < 38
    h, c = 4.0, 0.3
    s = s.fuse(box(-c - 1.5, -c, 38.0, 43.0, zs, zs + h))                   # -x
    s = s.fuse(box(BATTERY["x1"] + c, IN_X[1], 28.0, 43.0, zs, zs + h))     # +x, clear of the FPC bend
    s = s.fuse(box(-c, 1.0, BATTERY["y0"] - c - 1.0, BATTERY["y0"] - c, zs - 1.0, zs + h))   # -y, left
    s = s.fuse(box(39.0, IN_X[1], BATTERY["y0"] - c - 1.0, BATTERY["y0"] - c, zs - 1.0, zs + h))  # -y, right

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
    return clean(s)


def build(log):
    export_part(NAME, "Front shell", front_shell(), HOUSING_COLOR, log)


if __name__ in ("__main__", "front_shell"):
    cp.run(NAME, build)
