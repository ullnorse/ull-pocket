"""Assembly drawing: every part outline (F.Fab) with its reference sized to fit.

The silkscreen leaves passives unlabelled; this page is where to look them up.
Usage: assembly.py board.kicad_pcb out.pdf
"""
import os, subprocess, sys, tempfile, shutil, pcbnew
F, M = pcbnew.FromMM, pcbnew.ToMM
src, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp()
board = os.path.join(tmp, "a.kicad_pcb")
shutil.copy(src, board)
b = pcbnew.LoadBoard(board)
edge = b.GetBoardEdgesBoundingBox()
for f in b.GetFootprints():
    if f.IsFlipped() or f.GetReference().startswith("ASSY"):
        continue
    fab = [g for g in f.GraphicalItems() if g.GetClass() == "PCB_TEXT" and g.GetLayer() == pcbnew.F_Fab and "REFERENCE" in g.GetText()]
    bb = f.GetBoundingBox(False, )
    w, h = M(bb.GetWidth()), M(bb.GetHeight())
    if not fab:
        t = pcbnew.PCB_TEXT(f); t.SetText("${REFERENCE}"); t.SetLayer(pcbnew.F_Fab); f.Add(t); fab = [t]
    for g in list(f.GraphicalItems()) + [f.Value(), f.Reference()] + list(f.GetFields()):
        if g.GetClass() in ("PCB_TEXT", "PCB_FIELD") and g.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab) and g.m_Uuid.AsString() != fab[0].m_Uuid.AsString():
            g.SetLayer(pcbnew.Cmts_User)
    t = fab[0]
    bb = bb.Intersect(edge)
    n = len(f.GetReference())
    along = max(w, h); across = min(w, h)
    size = max(0.35, min(1.2, across * 0.55, along / (n * 0.85)))
    t.SetTextSize(pcbnew.VECTOR2I(F(size), F(size))); t.SetTextThickness(F(size * 0.15))
    t.SetPosition(bb.GetCenter())
    t.SetTextAngleDegrees(90 if h > w * 1.2 else 0)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    t.SetKeepUpright(True)
b.Save(board)
svg = os.path.join(tmp, "a.svg")
subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", "F.Fab,Edge.Cuts", "--mode-single",
                "--fit-page-to-board", "--exclude-drawing-sheet", "--black-and-white", "-o", svg, board],
               check=True, capture_output=True)
subprocess.run(["rsvg-convert", "-f", "pdf", "-z", "4", "-b", "white", "-o", out, svg], check=True)
shutil.rmtree(tmp)
print("wrote", out)
