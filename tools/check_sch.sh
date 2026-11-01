#!/bin/sh
# Schematic checks and exports: ERC, netlist (for check_net.py), PDF + PNG into build/.
set -e
cd "$(dirname "$0")/.."
KC=${KICAD_CLI:-kicad-cli}
mkdir -p build/review build/erc
$KC sch erc --severity-all --format report -o build/erc/erc.rpt ull-pocket.kicad_sch >/dev/null || true
$KC sch export netlist --format kicadsexpr -o build/ull-pocket.net ull-pocket.kicad_sch >/dev/null
$KC sch export pdf -o build/review/ull-pocket-schematic.pdf ull-pocket.kicad_sch >/dev/null
$KC sch export svg -o build/review ull-pocket.kicad_sch >/dev/null
rsvg-convert -b white -w 4200 build/review/ull-pocket.svg -o build/review/full.png
grep -E "ERC messages" build/erc/erc.rpt
python3 -I tools/check_net.py | tail -1
python3 -I tools/check_pins.py | tail -1
