"""ull-pocket button plunger 3 (y = BUTTONS_Y[2] in case_params.py); shape in case_button.py.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/button_3.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from case_button import make_button  # noqa: E402

make_button(3)
