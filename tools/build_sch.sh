#!/bin/sh
# Regenerate schematic, round-trip through KiCad 10 fork, run ERC, export netlist + renders.
set -e
cd "$(dirname "$0")/.."
KC=/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli
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
python3 tools/crop.py sub_charger 103 10 240 85
python3 tools/crop.py sub_battery 239 10 312 85
python3 tools/crop.py sub_ldo 311 10 384 58
python3 tools/crop.py sub_mcu 10 84 117 183
python3 tools/crop.py sub_sensors 116 84 354 157
python3 tools/crop.py sub_button 116 156 187 183
python3 tools/crop.py sub_epaper 10 182 232 286
