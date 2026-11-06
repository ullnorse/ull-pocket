#!/bin/sh
# render symbol montage to build/sym_all.png
cd "$(dirname "$0")/.." || exit 1
KC=${KICAD_CLI:-kicad-cli}
# renders the symbols in lib/ull-pocket.kicad_sym (edit the library in KiCad)
rm -rf build/symsvg; mkdir -p build/symsvg; $KC sym export svg lib/ull-pocket.kicad_sym -o build/symsvg >/dev/null
cd build/symsvg
L=""
for f in ESP32-C6-MINI-1-H4 BQ24073RGTR LIS3DHTR BMP585 SHT31-DIS-B MAX17048G+T10 RT9080-33GJ5 USBLC6-2SC6 TS24CA SI1308EDL FPC-05FB-24PH20 TYPE-C-31-M-12 Battery-1.25-2PWB; do rsvg-convert -z 3 -b white ${f}_unit1.svg -o $f.png; L="$L $f.png"; done
python3 ../../tools/montage.py ../sym_all.png $L
