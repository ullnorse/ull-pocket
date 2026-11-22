"""ull-pocket button plunger, shared by button_1.py, button_2.py and button_3.py.
Dimensions live in case_params.py. Shaped for a filament printer: the shaft, flange and nose share
one flat underside, so the part prints lying on that face with no overhang.
"""
from case_params import *  # noqa: F401,F403
import case_params as cp

SHAFT_W, SHAFT_H = 2.6, 1.8          # along y, along z
FLANGE_W, FLANGE_T = 4.6, 1.0        # wider than the wall hole, so the button can't fall out
NOSE_W, NOSE_H = 2.0, 1.2
Z0 = BTN_Z - SHAFT_H / 2             # the shared flat face


def plunger(y):
    """Button plunger: cap through the wall, flange inside, nose onto the TS24CA actuator."""
    # 0.23 gap + 0.15 switch travel = 0.38; the cap stands 0.6 proud, so the wall limits the press
    p = box(OUT_X[0] - 0.6, IN_X[0], y - SHAFT_W / 2, y + SHAFT_W / 2, Z0, Z0 + SHAFT_H)        # shaft + cap
    p = p.fuse(box(IN_X[0], IN_X[0] + FLANGE_T, y - FLANGE_W / 2, y + FLANGE_W / 2, Z0, Z0 + SHAFT_H))  # flange
    p = p.fuse(box(IN_X[0] + FLANGE_T, -0.45, y - NOSE_W / 2, y + NOSE_W / 2, Z0, Z0 + NOSE_H))  # nose; tip at x -0.22
    # soften the cap's outer corners (vertical when printed flat, so no overhang)
    p = p.makeChamfer(0.4, [e for e in cp._parallel_edges(p, "z")
                            if abs(e.Vertexes[0].Point.x - (OUT_X[0] - 0.6)) < 1e-6])
    return clean(p)


def make_button(i):
    """Build, check and export button_<i> (1-based, at BUTTONS_Y[i - 1])."""
    name = "button_%d" % i

    def build(log):
        export_part(name, "Button %d" % i, plunger(BUTTONS_Y[i - 1]), BUTTON_COLOR, log)
    cp.run(name, build)
