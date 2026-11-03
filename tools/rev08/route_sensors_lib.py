"""Board-editing helpers shared by the rev 0.8 routing scripts."""
import pcbnew
from pcbnew import FromMM as I, ToMM as mm


def _near(p, x, y):
    return abs(mm(p.x) - x) < 0.01 and abs(mm(p.y) - y) < 0.01


class Board:
    def __init__(self, path):
        self.path = path
        self.b = pcbnew.LoadBoard(path)

    def fp(self, ref, x, y, rot):
        f = self.b.FindFootprintByReference(ref)
        f.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))
        f.SetOrientationDegrees(rot)

    def track(self, net, pts, w=0.15, layer=pcbnew.F_Cu):
        ni = self.b.FindNet(net)
        assert ni is not None, ("no net", net)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(pcbnew.VECTOR2I(I(x1), I(y1)))
            t.SetEnd(pcbnew.VECTOR2I(I(x2), I(y2)))
            t.SetWidth(I(w))
            t.SetLayer(layer)
            t.SetNet(ni)
            self.b.Add(t)

    def via(self, net, x, y, d=0.6, h=0.3):
        ni = self.b.FindNet(net)
        assert ni is not None, ("no net", net)
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pcbnew.VECTOR2I(I(x), I(y)))
        v.SetWidth(I(d))
        v.SetDrill(I(h))
        v.SetNet(ni)
        self.b.Add(v)

    def drop_track(self, x1, y1, x2, y2):
        n = 0
        for t in list(self.b.GetTracks()):
            if t.GetClass() != "PCB_VIA" and ((_near(t.GetStart(), x1, y1) and _near(t.GetEnd(), x2, y2)) or
                                              (_near(t.GetStart(), x2, y2) and _near(t.GetEnd(), x1, y1))):
                self.b.Delete(t)
                n += 1
        assert n, ("no track", x1, y1, x2, y2)

    def drop_via(self, x, y):
        for t in list(self.b.GetTracks()):
            if t.GetClass() == "PCB_VIA" and _near(t.GetPosition(), x, y):
                self.b.Delete(t)
                return
        raise AssertionError(("no via", x, y))

    def save(self):
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        self.b.Save(self.path)
        print("ok")
