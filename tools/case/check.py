"""Fit check: case parts against the full board mesh (every 3D model incl. the display and battery
assembly models, exported by kicad-cli as STL). Reports where case surfaces cut part surfaces.
Run after case.py: ~/.venvs/cad/bin/python tools/case/check.py"""
import os
import subprocess
from collections import defaultdict
import vtk

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "build", "case")
BOARD = os.path.join(D, "board_full.stl")
subprocess.run(["kicad-cli", "pcb", "export", "stl", "-f", "-o", BOARD, os.path.join(ROOT, "ull-pocket.kicad_pcb")],
               check=True, capture_output=True)


def load(path, shift=(0, 0, 0)):
    r = vtk.vtkSTLReader()
    r.SetFileName(path)
    t = vtk.vtkTransform()
    t.Translate(*shift)
    f = vtk.vtkTransformPolyDataFilter()
    f.SetInputConnection(r.GetOutputPort())
    f.SetTransform(t)
    f.Update()
    return f.GetOutput()


board = load(BOARD, (-100 + float(os.environ.get("SHIFT_X", 0)), 100, 0))          # KiCad origin -> case frame (x right, y up = -doc y)
bad = 0
for name in ("front_shell", "back_cover", "button_1", "button_2", "button_3"):
    part = load(os.path.join(D, name + ".stl"))
    c = vtk.vtkCollisionDetectionFilter()
    c.SetInputData(0, part)
    c.SetInputData(1, board)
    c.SetTransform(0, vtk.vtkTransform())
    c.SetTransform(1, vtk.vtkTransform())
    c.SetCollisionModeToAllContacts()
    c.Update()
    pts = c.GetContactsOutput().GetPoints()
    n = pts.GetNumberOfPoints() if pts else 0
    # cluster contacts on a 1 mm grid; ignore the intended PCB seat (B side z 0 on bosses/ledges)
    cells = defaultdict(int)
    for i in range(n):
        x, y, z = pts.GetPoint(i)
        if abs(z) < 0.02 or abs(z - 5.1) < 0.02:      # PCB seat, battery on its rails
            continue
        cells[(round(x), round(-y), round(z, 1))] += 1
    if cells:
        bad += len(cells)
        print(f"{name}: {len(cells)} contact cells, e.g.",
              ", ".join(f"x{x} y{y} z{z}" for x, y, z in sorted(cells)[:12]))
    else:
        print(f"{name}: clear")
print("contact cells:", bad)
