#!/bin/sh
# JLC assembly panel: one board, 5 mm rails left and right (tooling holes + fiducials), mouse-bite tabs
# placed clear of the buttons, the J2 mouth and the e-paper FPC bend; top and bottom stay open for the
# antenna, USB-C and LED overhangs. Output: build/panel/ull-pocket-panel.kicad_pcb (needs kikit: pipx install kikit).
set -e
cd "$(dirname "$0")/.."
D=build/panel
rm -rf $D && mkdir -p $D/src
cp ull-pocket.kicad_pro ull-pocket.kicad_dru fp-lib-table sym-lib-table $D/src/
ln -s "$PWD/lib" $D/src/lib
KIKIT_FP=$(dirname "$(readlink -f ~/.local/bin/kikit)")/../lib/python3*/site-packages/kikit/resources/kikit.pretty
python3 - ull-pocket.kicad_pcb $D/src/ull-pocket.kicad_pcb $KIKIT_FP <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
# Tab positions must match TABS in tools/route/tab_keepouts.py (no copper pour behind the mouse bites).
# (x, y, rotation): annotation in the gap outside the edge, arrow pointing at the board (0 = +x)
for x, y, rot in ((99.0, 114.5, 0), (99.0, 141.5, 0), (141.0, 104.0, 180), (141.0, 141.5, 180)):
    f = pcbnew.FootprintLoad(sys.argv[3], 'Tab')
    f.SetFPID(pcbnew.LIB_ID('kikit', 'Tab'))
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    f.SetOrientationDegrees(rot)
    b.Add(f)
b.Save(sys.argv[2])
PY
kikit panelize -p :jlcTooling \
  --layout 'grid; rows: 1; cols: 1' \
  --tabs annotation \
  --cuts 'mousebites; drill: 0.5mm; spacing: 0.8mm; offset: 0.2mm; prolong: 0.5mm' \
  --framing 'railslr; width: 5mm; space: 2mm' \
  --tooling '3hole; hoffset: 2.5mm; voffset: 2.5mm; size: 1.152mm' \
  --fiducials '3fid; hoffset: 2.5mm; voffset: 6.5mm; coppersize: 1mm; opening: 2mm' \
  --post 'millradius: 1mm' \
  $D/src/ull-pocket.kicad_pcb $D/ull-pocket-panel.kicad_pcb
