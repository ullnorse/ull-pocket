"""Slow, cool charging: R9 back to 3.3k (270 mA), new R34 68k on U6 TMR so the safety timer outlasts a full charge.
VBUS now drops to F.Cu at (32.25, 32.9), freeing the spot above U6 pin 14 for R34."""
import re
import sys
import uuid
import pcbnew
sys.path.insert(0, "tools/rev08")
from schlib import block, instance
from route_sensors_lib import Board

SCH, PCB, P = "ull-pocket.kicad_sch", "ull-pocket.kicad_pcb", 100.0
R9 = dict(Value="3.3kR", Description="Resistor 3.3k 1% 0402", MPN="0402WGF3301TCE", LCSC="C25890")
R34 = dict(Value="68kR", Description="Resistor 68k 1% 0402", MPN="0402WGF6802TCE", LCSC="C36871")
u = lambda: str(uuid.uuid4())


def set_props(t, props):
    for k, v in props.items():
        t, n = re.subn(r'(property "%s" ")[^"]*"' % k, lambda m: m.group(1) + v + '"', t)
        assert n == 1, k
    return t


def clone(s, ref, new, x, y, props):
    a, b, tx, ty, _, _ = instance(s, ref)
    t = s[a:b]
    t = re.sub(r'\(at ([-\d.]+) ([-\d.]+)', lambda m: "(at %g %g" % (round(float(m.group(1)) - tx + x, 3), round(float(m.group(2)) - ty + y, 3)), t)
    t = re.sub(r'\(uuid "[^"]*"\)', lambda m: '(uuid "%s")' % u(), t)
    t = t.replace('"%s"' % ref, '"%s"' % new)
    return "\t" + set_props(t, props) + "\n"


s = open(SCH).read()
a, b, *_ = instance(s, "R9")
s = s[:a] + set_props(s[a:b], R9) + s[b:]
# TMR stub and its no-connect go; the resistor's top pin lands on the U6 pin
for pat in (r'\n\t\(wire\s*\(pts\s*\(xy 167\.64 66\.04\) \(xy 167\.64 68\.58\)', r'\n\t\(no_connect\s*\(at 167\.64 68\.58'):
    m = re.search(pat, s)
    x, y = block(s, m.start() + 2)
    s = s[:m.start() + 1] + s[y:].lstrip("\n")
r34 = clone(s, "R10", "R34", 167.64, 68.58, R34)
pwr = clone(s, "#PWR023", "#PWR101", 167.64, 71.12, {})
i = s.rindex("\t(sheet_instances")
s = s[:i] + r34 + pwr + s[i:]
a0 = "ICHG = 890/2.2k = 405 mA"
assert a0 in s
s = s.replace(a0, "ICHG = 890/3.3k = 270 mA, cool and slow")
a1 = "TMR open: 4-6 h timer"
assert a1 in s
s = s.replace(a1, "TMR 68k: 6.8-11 h timer")
open(SCH, "w").write(s)
ruid = re.search(r'\(uuid "([^"]*)"\)', r34).group(1)

B = Board(PCB)
b = B.b
r9 = b.FindFootprintByReference("R9")
r9.SetValue(R9["Value"])
r9.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(P + 29.54), r9.GetPosition().y))  # courtyard room for R34
for k in ("Description", "MPN", "LCSC"):
    r9.SetField(k, R9[k])

t = lambda *a: tuple(P + v for v in a)
B.drop_via(*t(30.5, 31.55))
B.drop_track(*t(30.5, 31.55), *t(31.75, 31.625))
B.via("VBUS", *t(32.25, 32.9), d=0.6, h=0.3)
B.track("VBUS", [t(32.25, 32.9), t(31.75, 32.9)], w=0.3)

f = pcbnew.FootprintLoad("/usr/share/kicad/footprints/Resistor_SMD.pretty", "R_0402_1005Metric")
f.SetFPID(pcbnew.LIB_ID("Resistor_SMD", "R_0402_1005Metric"))
f.SetReference("R34")
f.SetValue(R34["Value"])
f.SetPath(pcbnew.KIID_PATH("/" + ruid))
f.SetSheetname(r9.GetSheetname())
f.SetSheetfile(r9.GetSheetfile())
for k in ("Description", "MPN", "LCSC", "Manufacturer"):
    f.SetField(k, R34.get(k, "UNI-ROYAL(Uniroyal Elec)"))
for x in f.GetFields():
    if x.GetName() != "Value":
        x.SetVisible(False)
b.Add(f)
f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(P + 30.52), pcbnew.FromMM(P + 31.39)))
f.SetOrientationDegrees(90)
tmr = b.FindNet("unconnected-(U6-TMR-Pad14)")
net = pcbnew.NETINFO_ITEM(b, "Net-(U6-TMR)")
b.Add(net)
b.FindFootprintByReference("U6").FindPadByNumber("14").SetNet(net)
f.FindPadByNumber("1").SetNet(net)
f.FindPadByNumber("2").SetNet(b.FindNet("GND"))
B.track("Net-(U6-TMR)", [t(31.25, 33.037), t(31.25, 32.4), t(30.52, 31.87)], w=0.15)
B.track("GND", [t(30.52, 30.91), t(30.52, 30.6), t(31.75, 30.075)], w=0.2)
B.save()
