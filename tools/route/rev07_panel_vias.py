"""rev 0.7: drop the edge-fence GND vias that the panel's bottom mouse-bite tabs (tools/panelize.sh) would cut."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.FromMM
gone = [(100.75, 139.4), (100.75, 141.0), (101.0, 143.75), (139.25, 139.4), (139.25, 141.0), (139.25, 142.6)]
n = 0
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA' and t.GetNetname() == 'GND' and \
       any(abs(t.GetPosition().x - mm(x)) < mm(0.03) and abs(t.GetPosition().y - mm(y)) < mm(0.03) for x, y in gone):
        b.Delete(t); n += 1
assert n == len(gone), n
b.Save(sys.argv[2])
print('removed', n)
