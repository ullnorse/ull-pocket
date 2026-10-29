#!/bin/sh
# drc.sh board.kicad_pcb [refill]  -> chk/drc.json summary (fork DRC with project rules)
P=/home/blueeyes/projects/hardware/ull-pocket
KC=/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli
C=$P/build/route/chk
cp $P/ull-pocket.kicad_pro $P/ull-pocket.kicad_dru $P/ull-pocket.kicad_sch $P/fp-lib-table $P/sym-lib-table $C/
ln -sfn $P/lib $C/lib
cp "$1" $C/ull-pocket.kicad_pcb
if [ "$2" = "refill" ]; then R="--refill-zones"; else R=""; fi
$KC pcb drc $R --schematic-parity --severity-all --format json -o $C/drc.json $C/ull-pocket.kicad_pcb >/dev/null 2>&1
python3 $P/build/route/drcsum.py $C/drc.json $3
