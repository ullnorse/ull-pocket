"""Offscreen VTK renders of the case with the board inside -> build/case/*.png.
Run after case.py and check.py: ~/.venvs/cad/bin/python tools/case/render.py"""
import os
import vtk

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "build", "case")

# board_full.stl comes from check.py (kicad-cli STL export: every model incl. display and battery);
# KiCad origin -> case frame
BOARD_SHIFT = (-100, 100, 0)


def actor(name, color, opacity=1.0, offset=(0, 0, 0)):
    r = vtk.vtkSTLReader()
    r.SetFileName(os.path.join(D, name + ".stl"))
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(r.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*color)
    a.GetProperty().SetOpacity(opacity)
    a.SetPosition(*[o + (bs if name == "board_full" else 0) for o, bs in zip(offset, BOARD_SHIFT)])
    return a


def render(fname, actors, pos, up, focal=(19.6, -20, 4), zoom=1.0):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.93, 0.93, 0.95)
    for a in actors:
        ren.AddActor(a)
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*pos)
    cam.SetViewUp(*up)
    ren.ResetCamera()
    cam.Zoom(zoom)
    w = vtk.vtkRenderWindow()
    w.SetOffScreenRendering(1)
    w.AddRenderer(ren)
    w.SetSize(1200, 1000)
    w.Render()
    g = vtk.vtkWindowToImageFilter()
    g.SetInput(w)
    g.Update()
    png = vtk.vtkPNGWriter()
    png.SetFileName(os.path.join(D, fname))
    png.SetInputConnection(g.GetOutputPort())
    png.Write()


SHELL, COVER, BTN, PCB = (0.16, 0.19, 0.24), (0.30, 0.34, 0.40), (0.85, 0.45, 0.15), (0.2, 0.35, 0.75)
btns = [actor(f"button_{i}", BTN) for i in (1, 2, 3)]
board = actor("board_full", PCB)
render("front.png", [actor("front_shell", SHELL), board] + btns, (60, -95, -90), (0, 1, 0), zoom=1.1)
render("exploded.png", [actor("front_shell", SHELL), board, actor("back_cover", COVER, offset=(0, 0, 25))] + btns,
       (-40, -110, 110), (0, 0, 1), zoom=1.0)
render("open.png", [actor("front_shell", SHELL), board] + btns, (25, -60, 120), (0, 1, 0), zoom=1.2)
render("bottom.png", [actor("front_shell", SHELL), actor("back_cover", COVER), board] + btns,
       (19.6, -120, 4), (0, 0, 1), zoom=1.6)
render("left.png", [actor("front_shell", SHELL), actor("back_cover", COVER), board] + btns,
       (-100, -20, 4), (0, 0, 1), zoom=1.4)
print("ok")
