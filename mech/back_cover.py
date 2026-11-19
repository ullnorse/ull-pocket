"""ull-pocket back cover: snap-on lid with an inner lip, ridges that click into the shell's
grooves, and relief slots so the lip flexes at the ridges.
Port of the retired CadQuery draft (case.py) back_cover(); dimensions live in case_params.py.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/back_cover.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App  # noqa: E402
from case_params import *  # noqa: E402,F401,F403
import case_params as cp  # noqa: E402

NAME = "back_cover"


def back_cover():
    c = fillet_face_edges(rbox(*OUT_X, *OUT_Y, Z_IN1, Z_OUT1, R_OUT), ">Z", 1.0)
    lx = (IN_X[0] + CLR, IN_X[1] - CLR)
    ly = (IN_Y[0] + CLR, IN_Y[1] - CLR)
    lip = rbox(*lx, *ly, Z_IN1 - LIP_H, Z_IN1, R_OUT - WALL - CLR)
    lip = lip.cut(rbox(lx[0] + LIP_T, lx[1] - LIP_T, ly[0] + LIP_T, ly[1] - LIP_T,
                       Z_IN1 - LIP_H - 1, Z_IN1 + 0.01, R_OUT - WALL - CLR - LIP_T))
    c = c.fuse(lip)
    # ridges that click into the shell grooves
    for y in (10.0, 32.0):
        for x0, x1 in ((lx[0] - 0.4, lx[0] + 0.01), (lx[1] - 0.01, lx[1] + 0.4)):
            c = c.fuse(xbar(x0, x1, y - 3.6, y + 3.6, Z_IN1 - 1.8, 0.6, 0.15))
    # relief slots so the lip flexes at the ridges
    for y in (10.0, 32.0):
        for yy in (y - 4.2, y + 4.2):
            for x0 in (lx[0], lx[1] - LIP_T):
                c = c.cut(box(x0 - 0.01, x0 + LIP_T + 0.01, yy - 0.3, yy + 0.3, Z_IN1 - LIP_H - 1, Z_IN1 - 0.4))
    return clean(c)


def build(log):
    export_part(NAME, "Back cover", back_cover(), HOUSING_COLOR, log)


if __name__ in ("__main__", "back_cover"):
    cp.run(NAME, build)
