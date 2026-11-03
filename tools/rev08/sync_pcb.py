"""Update ull-pocket.kicad_pcb from build/ull-pocket.net (what F8 does): swap changed footprints in
place, add new ones, copy fields, set every pad's net, carry renamed nets over to tracks and zones."""
import os, sys
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from sexp import find, findall, parse  # noqa: E402

PCB = os.path.join(ROOT, "ull-pocket.kicad_pcb")
net = parse(open(os.path.join(ROOT, "build/ull-pocket.net")).read())
b = pcbnew.LoadBoard(PCB)

comps = {}
for c in findall(find(net, "components"), "comp"):
    ref = str(find(c, "ref")[1])
    fields = {str(find(f, "name")[1]): str(f[2]) for f in findall(find(c, "fields") or [], "field") if len(f) > 2}
    comps[ref] = dict(value=str(find(c, "value")[1]), fp=str(find(c, "footprint")[1]),
                      uuid=str(find(c, "tstamps")[1]), fields=fields)
pin_net = {}
for n in findall(find(net, "nets"), "net"):
    name = str(find(n, "name")[1])
    for node in findall(n, "node"):
        pin_net[(str(find(node, "ref")[1]), str(find(node, "pin")[1]))] = name


def load(fpid):
    lib, name = fpid.split(":")
    d = os.path.join(ROOT, "lib/ull-pocket.pretty") if lib == "ull-pocket" else "/usr/share/kicad/footprints/%s.pretty" % lib
    return pcbnew.FootprintLoad(d, name)


def netinfo(name):
    ni = b.FindNet(name)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
    return ni


rename = {}
for ref, c in comps.items():
    old = b.FindFootprintByReference(ref)
    same = old is not None and old.GetFPIDAsString() == c["fp"]
    if same:
        fp = old
    else:
        fp = load(c["fp"])
        fp.SetFPID(pcbnew.LIB_ID(*c["fp"].split(":")))
        if old is not None:
            fp.SetPosition(old.GetPosition())
            fp.SetOrientation(old.GetOrientation())
            b.Delete(old)
        else:
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(145), pcbnew.FromMM(120)))  # off-board, placed later
        b.Add(fp)
        fp.SetReference(ref)
        print("swapped" if old else "added", ref, c["fp"])
    fp.SetValue(c["value"])
    fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
    for k, v in c["fields"].items():
        if k in ("Footprint", "Datasheet", "Description"):
            continue
        if fp.HasField(k):
            fp.GetField(k).SetText(v)
        else:
            f = pcbnew.PCB_FIELD(fp, pcbnew.FIELD_T_USER, k)
            f.SetText(v)
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
            fp.Add(f)
    for p in fp.Pads():
        n = pin_net.get((ref, p.GetNumber()))
        if same and p.GetNetname() and n and p.GetNetname() != n:  # pad numbers mean the same thing
            rename.setdefault(p.GetNetname(), set()).add(n)
        p.SetNet(netinfo(n) if n else b.FindNet(""))

# nets renamed (one old name -> one new name): move tracks, vias and zones over
for old, new in rename.items():
    new.discard(None)
    if len(new) == 1:
        (n,) = new
        if n != old:
            ni = netinfo(n)
            moved = 0
            for t in b.GetTracks():
                if t.GetNetname() == old:
                    t.SetNet(ni)
                    moved += 1
            for z in b.Zones():
                if z.GetNetname() == old:
                    z.SetNet(ni)
            print("net %s -> %s (%d tracks)" % (old, n, moved))
    else:
        print("net %s split into %s: tracks left as they are" % (old, sorted(new)))
b.Save(PCB)
