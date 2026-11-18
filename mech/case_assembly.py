"""ull-pocket case assembly: front shell, back cover, three button plungers and the bare board,
all in case_params.py's frame (board top-left at the origin, B side at z 0, F side towards +z).
Exports mech/case_assembly.step. Run the part scripts first; this one inserts their STEPs.

The board comes from KiCad: boards/ull-pocket/ull-pocket.kicad_pcb (or ull-pocket.kicad_pcb in
the project root) exported board-only with --user-origin 100x100mm into build/case/board_only.step,
so KiCad (100, 100) lands on the origin and no further offset is needed. The export runs here when
the STEP is missing or older than the board; if kicad-cli can't run from FreeCAD's sandbox, run:
  kicad-cli pcb export step --board-only --user-origin 100x100mm -f \
      -o build/case/board_only.step boards/ull-pocket/ull-pocket.kicad_pcb
Run: QT_QPA_PLATFORM=offscreen timeout 300 /snap/bin/freecad.cmd mech/case_assembly.py
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App  # noqa: E402
import case_params as cp  # noqa: E402
from case_params import HOLES  # noqa: E402

NAME = "case_assembly"
PARTS = ["front_shell", "back_cover", "button_1", "button_2", "button_3"]
BOARD_COLOR = (0.10, 0.38, 0.16)     # solder-mask green
BOARD_STEP = os.path.join(cp.BUILD, "board_only.step")


def board_pcb():
    for p in (os.path.join(cp.ROOT, "boards", "ull-pocket", "ull-pocket.kicad_pcb"),
              os.path.join(cp.ROOT, "ull-pocket.kicad_pcb")):
        if os.path.exists(p):
            return p
    raise RuntimeError("no ull-pocket.kicad_pcb in boards/ull-pocket/ or the project root")


def export_board(log):
    pcb = board_pcb()
    if os.path.exists(BOARD_STEP) and os.path.getmtime(BOARD_STEP) >= os.path.getmtime(pcb):
        log.write("board: %s is current (from %s)\n" % (BOARD_STEP, pcb))
        return
    cli = os.environ.get("BACKPLANE_KICAD_CLI") or shutil.which("kicad-cli") or "kicad-cli"
    cmd = [cli, "pcb", "export", "step", "--board-only", "--user-origin", "100x100mm", "-f",
           "-o", BOARD_STEP, pcb]
    log.write("board: " + " ".join(cmd) + "\n")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        log.write(r.stdout + r.stderr)
    except Exception as e:  # FreeCAD's snap may not be allowed to run kicad-cli
        log.write("board: kicad-cli failed here (%s)\n" % e)
    if not os.path.exists(BOARD_STEP):
        raise RuntimeError("board STEP missing: run the kicad-cli line in this script's header")
    if os.path.getmtime(BOARD_STEP) < os.path.getmtime(pcb):
        log.write("WARNING board: %s is older than %s; using it anyway, re-export with the "
                  "kicad-cli line in this script's header\n" % (BOARD_STEP, pcb))


def check_holes(board, shell, log):
    """The board's mounting holes must sit on the shell's boss axes."""
    ok = True
    for x, y in HOLES:
        want = App.Vector(x, -y, 0)
        hole = [f for f in board.Faces if f.Surface.TypeId == "Part::GeomCylinder"
                and abs(f.Surface.Radius - 1.1) < 0.01
                and (App.Vector(f.Surface.Center.x, f.Surface.Center.y, 0) - want).Length < 0.5]
        boss = [f for f in shell.Faces if f.Surface.TypeId == "Part::GeomCylinder"
                and abs(f.Surface.Radius - 1.7) < 0.01
                and (App.Vector(f.Surface.Center.x, f.Surface.Center.y, 0) - want).Length < 0.5]
        if not hole or not boss:
            log.write("holes: (%.1f, %.1f) hole found %d, boss found %d\n" % (x, y, len(hole), len(boss)))
            ok = False
            continue
        h, b = hole[0].Surface.Center, boss[0].Surface.Center
        d = ((h.x - b.x) ** 2 + (h.y - b.y) ** 2) ** 0.5
        log.write("holes: board hole (%.3f, %.3f) r %.2f, shell boss (%.3f, %.3f) r %.2f, offset %.4f mm\n"
                  % (h.x, -h.y, hole[0].Surface.Radius, b.x, -b.y, boss[0].Surface.Radius, d))
        ok = ok and d < 0.01
    if not ok:
        raise RuntimeError("board mounting holes do not line up with the shell bosses")


def build(log):
    import ImportGui
    import Part
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import").SetInt("ImportMode", 0)
    export_board(log)
    doc = App.newDocument(NAME)
    board_objs = []
    for label, path in [(p, os.path.join(cp.MECH, p + ".step")) for p in PARTS] + [("board", BOARD_STEP)]:
        before = set(o.Name for o in doc.Objects)
        ImportGui.insert(path, doc.Name)
        new = [o for o in doc.Objects if o.Name not in before]
        for o in new:
            if not o.InList:
                o.Label = label
        if label == "board":
            board_objs = [o for o in new if o.isDerivedFrom("Part::Feature")]
    doc.recompute()
    # colour the board body green (KiCad's board-only STEP carries no useful colour for it)
    board_shape = Part.read(BOARD_STEP)
    bb = board_shape.optimalBoundingBox(False, False)
    log.write("board bbox x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f\n"
              % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    for o in board_objs:
        if o.Shape.Volume > 0 and abs(o.Shape.Volume - board_shape.Volume) < 1e-3:
            o.ViewObject.ShapeColor = BOARD_COLOR
    shell = Part.read(os.path.join(cp.MECH, "front_shell.step"))
    check_holes(board_shape, shell, log)
    # the board must sit inside the closed case's cavity without touching the walls
    cover = Part.read(os.path.join(cp.MECH, "back_cover.step"))
    for nm, s in (("front_shell", shell), ("back_cover", cover)):
        log.write("interference board/%s: %.4f mm3\n" % (nm, board_shape.common(s).Volume))
    tops = [o for o in doc.Objects if not o.InList]
    cp.save_doc(doc, os.path.join(cp.MECH, NAME + ".FCStd"))
    ImportGui.export(tops, os.path.join(cp.MECH, NAME + ".step"))
    log.write("exported %d top-level objects: %s\n" % (len(tops), ", ".join(o.Label for o in tops)))


cp.run(NAME, build)
