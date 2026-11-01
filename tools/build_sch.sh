#!/bin/sh
# Regenerate schematic, round-trip through KiCad 10, run ERC, export netlist + renders.
set -e
cd "$(dirname "$0")/.."
KC=${KICAD_CLI:-kicad-cli}
python3 -I tools/gen_sch.py
$KC sch upgrade --force ull-pocket.kicad_sch >/dev/null
mkdir -p build/review build/erc
$KC sch erc --severity-all --format report -o build/erc/erc.rpt ull-pocket.kicad_sch >/dev/null || true
$KC sch export netlist --format kicadsexpr -o build/ull-pocket.net ull-pocket.kicad_sch >/dev/null
$KC sch export svg -o build/review ull-pocket.kicad_sch >/dev/null
rsvg-convert -b white -w 4200 build/review/ull-pocket.svg -o build/review/full.png
grep -E "^\*\*|violations|Total" build/erc/erc.rpt | tail -3
# per-subcircuit crops (sheet mm)
python3 tools/crop.py sub_usb 10 10 104 85
python3 tools/crop.py sub_charger 103 10 238 85
python3 tools/crop.py sub_battery 236 10 342 85
python3 tools/crop.py sub_ldo 341 10 410 56
python3 tools/crop.py sub_button 341 55 410 85
python3 tools/crop.py sub_mcu 10 84 117 180
python3 tools/crop.py sub_sensors 116 84 265 180
python3 tools/crop.py sub_sensors2 260 84 410 180
python3 tools/crop.py sub_epaper 10 180 160 288
python3 tools/crop.py sub_notes 157 180 410 252
