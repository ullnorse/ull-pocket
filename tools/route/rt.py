"""Routing helpers on the KiCad 9 working copy (board coords: origin = KiCad (100,100))."""
import pcbnew

O = 100.0
MM = pcbnew.FromMM
LAY = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "1": pcbnew.In1_Cu, "2": pcbnew.In2_Cu}


def P(x, y):
    return pcbnew.VECTOR2I(MM(float(x) + O), MM(float(y) + O))


def xy(v):
    return (v.x / 1e6 - O, v.y / 1e6 - O)


class R:
    def __init__(self, path):
        self.path = path
        self.b = pcbnew.LoadBoard(path)

    def net(self, name):
        n = self.b.FindNet(name)
        assert n is not None, name
        return n

    def pad(self, ref, num):
        f = self.b.FindFootprintByReference(ref)
        for p in f.Pads():
            if p.GetNumber() == str(num):
                return p
        raise KeyError(ref + "." + str(num))

    def pp(self, ref, num):
        return xy(self.pad(ref, num).GetPosition())

    def track(self, pts, w, layer="F", net=None, lock=False):
        """pts: list of (x,y) or 'Ref.pad' strings."""
        q = [self.pp(*p.split(".")) if isinstance(p, str) else p for p in pts]
        n = self.net(net) if net else None
        if n is None and isinstance(pts[0], str):
            n = self.pad(*pts[0].split(".")).GetNet()
        out = []
        for a, c in zip(q, q[1:]):
            if abs(a[0] - c[0]) < 1e-6 and abs(a[1] - c[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(*a))
            t.SetEnd(P(*c))
            t.SetWidth(MM(w))
            t.SetLayer(LAY[layer])
            t.SetNet(n)
            t.SetLocked(lock)
            self.b.Add(t)
            out.append(t)
        return out

    def via(self, x, y, net, d=0.6, drill=0.3, lock=False):
        if isinstance(x, str):
            x, y = self.pp(*x.split("."))
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y))
        v.SetWidth(MM(d))
        v.SetDrill(MM(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetNet(self.net(net))
        v.SetLocked(lock)
        self.b.Add(v)
        return v

    def clear_routing(self, keep_locked=False):
        for t in list(self.b.GetTracks()):
            if keep_locked and t.IsLocked():
                continue
            self.b.Remove(t)

    def save(self, path=None):
        self.b.Save(path or self.path)
