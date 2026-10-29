#!/bin/sh
# copy KiCad-9 working board to the canonical file, refill zones + save in fork format, run DRC (JSON + report)
set -e
cd /home/blueeyes/projects/hardware/ull-pocket
KC=/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli
cp build/route/work.kicad_pcb ull-pocket.kicad_pcb
$KC pcb drc --refill-zones --save-board --schematic-parity --severity-all --format json -o build/route/drc.json ull-pocket.kicad_pcb >/dev/null || true
$KC pcb drc --schematic-parity --severity-all -o build/route/drc.rpt ull-pocket.kicad_pcb | grep -E 'Found' || true
python3 - <<'P'
import json, collections
d = json.load(open('build/route/drc.json'))
c = collections.Counter((v['severity'], v['type']) for v in d['violations'])
for k, n in sorted(c.items()): print(f'{n:5d} {k[0]:8s} {k[1]}')
print('unconnected', len(d['unconnected_items']), 'parity', len(d['schematic_parity']))
P
