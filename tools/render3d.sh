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
s = ''.join(out)
# JLC swaps this silk text for its order number; hide the placeholder in renders only
s = re.sub(r'\n\t\(gr_text "JLCJLCJLCJLC".*?\n\t\)(?=\n)', '', s, flags=re.S)
s = s.replace('#14307AD9', '#0F3FA8D9')  # reads as JLC blue under these lights
open(sys.argv[2], 'w').write(s)
PY
r() { $KC pcb render -o $O/$1 -w 1800 -h 1500 --quality high --background transparent --use-board-stackup-colors --light-top 0.17 --light-bottom 0.1 --light-side 0.17 --light-camera 0.02 $2 $T/ull-pocket.kicad_pcb >/dev/null; }
r top_bare.png "--side top --zoom 0.8"
r back_bare.png "--side bottom --zoom 0.8"
r iso_bare.png "--side top --perspective --rotate -50,0,30 --zoom 0.9"
python3 - $O <<'PY'
# neutral card
import sys
from PIL import Image
for n in ('top_bare', 'back_bare', 'iso_bare'):
    p = f'{sys.argv[1]}/{n}.png'
    im = Image.open(p).convert('RGBA')
    bg = Image.new('RGBA', im.size, (236, 238, 241, 255))
    # the renderer leaves a faint hard-edged halo in alpha; cut it
    im.putalpha(im.getchannel('A').point(lambda v: 0 if v < 170 else min(255, (v - 170) * 3)))
    bg.alpha_composite(im)
    bg.convert('RGB').save(p)
PY
ls $O
