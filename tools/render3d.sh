#!/bin/sh
# Bare-board 3D renders (battery and panel ASSY_* models hidden) into build/render3d.
set -e
cd "$(dirname "$0")/.."
KC=${KICAD_CLI:-kicad-cli}
O=build/render3d
T=$O/src
rm -rf $O && mkdir -p $T
cp ull-pocket.kicad_pro ull-pocket.kicad_dru fp-lib-table sym-lib-table $T/
ln -s "$PWD/lib" $T/lib
# hide the models of the ASSY_* reference footprints
python3 - ull-pocket.kicad_pcb $T/ull-pocket.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read()
out, i = [], 0
for m in re.finditer(r'\n\t\(footprint "[^"]*ASSY_[^"]*"', s):
    out.append(s[i:m.start()])
    d, j = 0, m.start() + 2
    while True:
        d += (s[j] == '(') - (s[j] == ')')
        j += 1
        if d == 0:
            break
    out.append(re.sub(r'(\(model "[^"]*")', r'\1 (hide yes)', s[m.start():j]))
    i = j
out.append(s[i:])
open(sys.argv[2], 'w').write(''.join(out))
PY
r() { $KC pcb render -o $O/$1 -w 1800 -h 1500 --quality high --floor --perspective --background opaque --use-board-stackup-colors $2 $T/ull-pocket.kicad_pcb >/dev/null; }
r top_bare.png "--side top"
r back_bare.png "--side bottom"
r iso_bare.png "--side top --rotate -50,0,30 --zoom 0.9"
ls $O
