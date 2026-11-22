"""ull-pocket front shell: display window, PCB bosses and ledges, USB-C, LED windows, SHT40 vent,
button holes, two cover-screw bosses on the left, hinge grooves on the right, pry notch.
For a filament printer: print it display-face down, no supports. Everything inside rises from the
floor or a wall; the battery sits in the back cover, so no rail hangs over the board and the
board drops straight in. Dimensions live in case_params.py.
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
    s = chamfer_face_edges(rbox(*OUT_X, *OUT_Y, Z_OUT0, Z_IN1, R_OUT), "<Z", EDGE_CHAMFER)
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

    # cover-screw bosses, floor to the cover's inner face, fused into the left corners
    for x, y in SCREWS:
        s = s.fuse(cyl(x, y, Z_IN0, Z_IN1, BOSS_D))
        s = s.fuse(box(IN_X[0], x, y - BOSS_D / 2, y + BOSS_D / 2, Z_IN0, Z_IN1))
        s = s.cut(cyl(x, y, Z_IN1 - PILOT_DEPTH, Z_IN1 + 0.01, PILOT_D))

    # USB-C: opening for the receptacle, recess outside for the plug overmold
    u = USB
    s = s.cut(ybar(u["x"] - u["w"] / 2 - 0.35, u["x"] + u["w"] / 2 + 0.35, IN_Y[1] - 1, OUT_Y[1] + 1,
                   u["z"], u["h"] + 0.7, 1.4))
    s = s.cut(ybar(u["x"] - 5.5, u["x"] + 5.5, IN_Y[1] + 0.1, OUT_Y[1] + 1, u["z"], 6.6, 2.5))
    # LED windows
    for x, z, w, h in LEDS:
        w, h = w + 0.4, h + 0.4          # small holes close up on a filament printer
        s = s.cut(ybar(x - w / 2, x + w / 2, IN_Y[1] - 1, OUT_Y[1] + 1, z, h, min(w, h) / 2 - 0.01))
    # SHT40 vent: slots in the top wall on the F side
    for i in range(3):
        x = VENT_X[0] + 0.4 + i * 2.0
        s = s.cut(ybar(x, x + 1.2, OUT_Y[0] - 1, IN_Y[0] + 1, PCB_T + 1.9, 3.0, 0.59))
    # button holes: the shaft section plus BTN_HOLE all round
    import case_button as cb
    for y in BUTTONS_Y:
        s = s.cut(box(OUT_X[0] - 1, IN_X[0] + 1, y - cb.SHAFT_W / 2 - BTN_HOLE, y + cb.SHAFT_W / 2 + BTN_HOLE,
                      cb.Z0 - BTN_HOLE, cb.Z0 + cb.SHAFT_H + BTN_HOLE))

    # hinge grooves in the right wall for the cover's ridges; the ceiling slopes 45 degrees so it prints
    zr = Z_IN1 - 1.8
    for y in HINGE_Y:
        s = s.cut(prism_xz([(IN_X[1] - 0.05, zr - 0.6), (IN_X[1] + 0.55, zr - 0.6),
                            (IN_X[1] + 0.55, zr + 0.05), (IN_X[1] - 0.05, zr + 0.65)],
                           y - HINGE_HALF - 0.5, y + HINGE_HALF + 0.5))
    # pry notch at the bottom edge
    s = s.cut(box(30.0, 36.0, OUT_Y[1] - 0.8, OUT_Y[1] + 1, Z_IN1 - 0.8, Z_IN1 + 1))
    return clean(s)


def build(log):
    export_part(NAME, "Front shell", front_shell(), HOUSING_COLOR, log)


if __name__ in ("__main__", "front_shell"):
    cp.run(NAME, build)
