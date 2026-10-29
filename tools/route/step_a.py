import pcbnew, json, subprocess, sys
from rt import *
new = {'D5': ('XL-1606UGC', 'C965863', 'LED green side-view 1.7x0.6, USB power present', 26.8),
       'D1': ('XL-1606SURC', 'C965860', 'LED red side-view 1.7x0.6, charge indicator', 29.8),
       'D6': ('XL-1606UBC', 'C965865', 'LED blue', 32.8)}
lib = '/home/blueeyes/projects/hardware/ull-pocket/lib/ull-pocket.pretty'
r = R('work.kicad_pcb'); b = r.b
if len(sys.argv) > 1:
    for ref, (mpn, lcsc, desc, x) in new.items():
        f = b.FindFootprintByReference(ref)
        for n, v in (('MPN', mpn), ('LCSC', lcsc), ('Manufacturer', 'XINGLIGHT'), ('Description', desc), ('Sim.Pins', '1=K 2=A')):
            f.SetField(n, v)
    for ref in ('R21', 'R6'):
        f = b.FindFootprintByReference(ref)
        for n, v in (('MPN', '0402WGF2001TCE'), ('LCSC', 'C4109'), ('Description', 'Resistor 2k 1% 0402')):
            f.SetField(n, v)
    r.save(); sys.exit()
info = {}
for ref in new:
    old = b.FindFootprintByReference(ref)
    info[ref] = dict(path=old.GetPath().AsString(), value=old.GetValue(), sheetname=old.GetSheetname(),
                     sheetfile=old.GetSheetfile(), attr=old.GetAttributes(),
                     nets={p.GetNumber(): p.GetNetname() for p in old.Pads()},
                     simpins=old.GetFieldText('Sim.Pins'), ds=old.GetFieldText('Datasheet'))
fpsrc = open(lib + '/LED_XL-1606_SideView.kicad_mod').read()
open('/tmp/ledfp.kicad_pcb', 'w').write('(kicad_pcb (version 20241229) (generator "pcbnew") (generator_version "9.0")\n' + fpsrc + ')\n')
tb = pcbnew.LoadBoard('/tmp/ledfp.kicad_pcb')
src = list(tb.GetFootprints())[0]
fps = {ref: pcbnew.FOOTPRINT(src) for ref in new}
for ref, (mpn, lcsc, desc, x) in new.items():
    i = info[ref]
    b.Remove(b.FindFootprintByReference(ref))
    f = fps[ref]
    b.Add(f)
    f.SetFPIDAsString('ull-pocket:LED_XL-1606_SideView')
    f.SetReference(ref); f.SetValue(i['value'])
    f.SetPath(pcbnew.KIID_PATH(i['path'])); f.SetSheetname(i['sheetname']); f.SetSheetfile(i['sheetfile'])
    f.SetAttributes(i['attr'])
    f.SetPosition(P(x, 44.1)); f.SetOrientationDegrees(0)
    for p in f.Pads():
        p.SetNet(r.net(i['nets'][p.GetNumber()]))
for ref, x in (('R21', 26.8), ('R6', 29.8), ('R22', 32.8)):
    f = b.FindFootprintByReference(ref)
    f.SetOrientationDegrees(180); f.SetPosition(P(x, 41.7))
    if ref != 'R22':
        f.SetValue('2kR')
r.save()
subprocess.run([sys.executable, __file__, 'fields'], check=True)
