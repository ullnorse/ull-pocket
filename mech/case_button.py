"""ull-pocket button plunger, shared by button_1.py, button_2.py and button_3.py.
Port of the retired CadQuery draft (case.py) plunger(); dimensions live in case_params.py.
"""
from case_params import *  # noqa: F401,F403
import case_params as cp


def plunger(y):
    """Button plunger: cap through the wall, flange inside, nose onto the TS24CA actuator."""
    # 0.23 gap + 0.15 switch travel = 0.38; the cap stands 0.45 proud, so the wall limits the press
    p = xbar(OUT_X[0] - 0.45, IN_X[0], y - 1.2, y + 1.2, BTN_Z, 1.6, 0.5)   # shaft + cap
    p = p.fuse(xbar(IN_X[0], IN_X[0] + 0.8, y - 2.0, y + 2.0, BTN_Z, 2.6, 0))  # flange
    p = p.fuse(xbar(IN_X[0] + 0.8, -0.45, y - 1.0, y + 1.0, BTN_Z, 1.2, 0))    # nose; TS24CA tip at x -0.22
    return clean(p)


def make_button(i):
    """Build, check and export button_<i> (1-based, at BUTTONS_Y[i - 1])."""
    name = "button_%d" % i

    def build(log):
        export_part(name, "Button %d" % i, plunger(BUTTONS_Y[i - 1]), BUTTON_COLOR, log)
    cp.run(name, build)
