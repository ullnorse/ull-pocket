"""ull-pocket back cover: screws down on the left, hinges on a ridge in the shell's right wall.
For a filament printer: print it outer-face down, no supports. The battery is stuck to the
inside with double-sided tape, between the lip and two locating ribs, so it hangs 3.5 mm above
the board's parts. Dimensions live in case_params.py.
Fit it: hook the right edge's ridges into the shell's grooves, swing the left edge down, two screws.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/back_cover.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App  # noqa: E402
from case_params import *  # noqa: E402,F401,F403
import case_params as cp  # noqa: E402

NAME = "back_cover"
RIB_H = 5.0                          # battery locating ribs, down from the cover's inner face


def back_cover():
    c = chamfer_face_edges(rbox(*OUT_X, *OUT_Y, Z_IN1, Z_OUT1, R_OUT), ">Z", EDGE_CHAMFER)
    lx = (IN_X[0] + CLR, IN_X[1] - CLR)
    ly = (IN_Y[0] + CLR, IN_Y[1] - CLR)
    lip = rbox(*lx, *ly, Z_IN1 - LIP_H, Z_IN1, R_OUT - WALL - CLR)
    lip = lip.cut(rbox(lx[0] + LIP_T, lx[1] - LIP_T, ly[0] + LIP_T, ly[1] - LIP_T,
                       Z_IN1 - LIP_H - 1, Z_IN1 + 0.01, R_OUT - WALL - CLR - LIP_T))
    # the lip stops short of the shell's screw bosses
    for x, y in SCREWS:
        lip = lip.cut(box(IN_X[0] - 1, x + BOSS_D / 2 + 0.4, y - BOSS_D / 2 - 0.4, y + BOSS_D / 2 + 0.4,
                          Z_IN1 - LIP_H - 1, Z_IN1))
    c = c.fuse(lip)
    # hinge ridges on the right lip; the face towards the bed slopes 45 degrees so it prints
    zr = Z_IN1 - 1.8
    for y in HINGE_Y:
        c = c.fuse(prism_xz([(lx[1] - 0.01, zr + 0.75), (lx[1] + 0.65, zr + 0.1),
                             (lx[1] + 0.65, zr - 0.2), (lx[1] - 0.01, zr - 0.5)],
                            y - HINGE_HALF, y + HINGE_HALF))
    # battery locating ribs: the lip stops the cell at +x and +y, these at -x and -y.
    # The -x rib leaves y 14..33 open for the cell's leads on their way to J2.
    b = BATTERY
    c = c.fuse(box(-1.6, -0.4, 34.0, 42.0, Z_IN1 - RIB_H, Z_IN1))
    c = c.fuse(box(8.0, 32.0, b["y0"] - 1.6, b["y0"] - 0.4, Z_IN1 - RIB_H, Z_IN1))
    # screw holes with a counterbore for the head
    for x, y in SCREWS:
        c = c.cut(cyl(x, y, Z_IN1 - 0.01, Z_OUT1 + 0.01, SCREW_CLEAR_D))
        c = c.cut(cyl(x, y, Z_OUT1 - HEAD_DEPTH, Z_OUT1 + 0.01, HEAD_D))
    return clean(c)


def build(log):
    export_part(NAME, "Back cover", back_cover(), HOUSING_COLOR, log)


if __name__ in ("__main__", "back_cover"):
    cp.run(NAME, build)
