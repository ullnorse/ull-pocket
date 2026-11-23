"""ull-pocket back cover: snaps on, no screws. Ridges on its lip click into grooves in the
shell's left and right walls; the walls bow out to let them pass.
For a filament printer: print it outer-face down, no supports. The battery is stuck to the
inside with double-sided tape, between the lip and two locating ribs, so it hangs 3.5 mm above
the board's parts. Dimensions live in case_params.py.
A finger reaches down to the board's bare top edge and keeps the board seated on its pegs.
Fit it: press it straight on until both sides click. Open it with a fingernail or a coin in the
notch at the bottom edge.
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
    c = c.fuse(lip)
    # snap ridges on the left and right lip: the face towards the bed slopes 45 degrees so it
    # prints, the leading face is a long ramp so the cover presses on easily
    zr = Z_IN1 - 1.8
    for y in SNAP_Y:
        for xl, d in ((lx[1], 1), (lx[0], -1)):
            c = c.fuse(prism_xz([(xl - 0.01 * d, zr + SNAP_IN + 0.1), (xl + SNAP_IN * d, zr + 0.1),
                                 (xl + SNAP_IN * d, zr - 0.2), (xl - 0.01 * d, zr - 0.2 - SNAP_IN)],
                                y - SNAP_HALF, y + SNAP_HALF))
    # hold-down finger onto the board's bare top edge (clear of R27 and C8), 0.15 above the board
    hx0, hx1, hy0, hy1 = HOLD
    c = c.fuse(box(hx0, hx1, hy0, hy1, PCB_T + 0.15, Z_IN1))
    # battery locating ribs: the lip stops the cell at +x and +y, these at -x and -y.
    # The -x rib leaves y 14..33 open for the cell's leads on their way to J2.
    b = BATTERY
    c = c.fuse(box(-1.6, -0.4, 34.0, 42.0, Z_IN1 - RIB_H, Z_IN1))
    c = c.fuse(box(8.0, 32.0, b["y0"] - 1.6, b["y0"] - 0.4, Z_IN1 - RIB_H, Z_IN1))
    return clean(c)


def build(log):
    export_part(NAME, "Back cover", back_cover(), HOUSING_COLOR, log)


if __name__ in ("__main__", "back_cover"):
    cp.run(NAME, build)
