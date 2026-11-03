"""Delete track segments that end inside the rev 0.7 courtyards of the swapped parts; list the loose ends left."""
import sys, pcbnew
mm, I = pcbnew.ToMM, pcbnew.FromMM
old = pcbnew.LoadBoard(sys.argv[1])
b = pcbnew.LoadBoard("ull-pocket.kicad_pcb")
refs = sys.argv[2].split(",")
boxes = {r: old.FindFootprintByReference(r).GetCourtyard(pcbnew.F_CrtYd).BBox() for r in refs}
gone = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        continue
    for r, bb in boxes.items():
        if bb.Contains(t.GetStart()) or bb.Contains(t.GetEnd()):
            b.Delete(t); gone += 1
            break
print("deleted", gone)
b.Save("ull-pocket.kicad_pcb")
