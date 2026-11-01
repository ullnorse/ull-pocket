#!/bin/sh
# Gerbers + drills + zip for JLCPCB. Needs KiCad 10.
# usage: tools/jlc_export.sh [board.kicad_pcb [name]]   (run from the repo root; BOM/CPL come from tools/jlc_cpl.py)
# default: ull-pocket.kicad_pcb -> production/ull-pocket-r0.7-gerbers.zip (+ drill maps)
set -e
K=${KICAD_CLI:-kicad-cli}
R=$PWD; T=$(mktemp -d); Z=$(mktemp -d)
B=${1:-ull-pocket.kicad_pcb}; N=${2:-ull-pocket-r0.7}
$K pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts \
  --subtract-soldermask --no-x2 --no-netlist --precision 6 -o "$T" "$B"
$K pcb export drill --format excellon --excellon-units mm --excellon-separate-th --excellon-zeros-format decimal \
  --drill-origin absolute --generate-map --map-format pdf -o "$T/" "$B"
if [ "$B" = ull-pocket.kicad_pcb ]; then mkdir -p production/drill-map; cp "$T"/*drl_map.pdf production/drill-map/; fi
cp "$T"/*.gbl "$T"/*.gbo "$T"/*.gbp "$T"/*.gbs "$T"/*.gm1 "$T"/*.gtl "$T"/*.gto "$T"/*.gtp "$T"/*.gts "$T"/*.g1 "$T"/*.g2 "$T"/*.drl "$Z"/
rm -f production/$N-gerbers.zip
(cd "$Z" && python3 -c "import zipfile,glob;z=zipfile.ZipFile('$R/production/$N-gerbers.zip','w',zipfile.ZIP_DEFLATED);[z.write(f) for f in sorted(glob.glob('*'))]")
