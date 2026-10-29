#!/bin/sh
# Gerbers + drills + zip for JLCPCB. Needs the KiCad fork CLI (stock KiCad 9 cannot load this board).
# usage: tools/jlc_export.sh   (run from the repo root; BOM/CPL come from tools/jlc_cpl.py)
set -e
K=${KICAD_CLI:-$HOME/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli}
R=$PWD; T=$(mktemp -d); Z=$(mktemp -d)
$K pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts \
  --subtract-soldermask --no-x2 --no-netlist --precision 6 -o "$T" ull-pocket.kicad_pcb
$K pcb export drill --format excellon --excellon-units mm --excellon-separate-th --excellon-zeros-format decimal \
  --drill-origin absolute --generate-map --map-format pdf -o "$T/" ull-pocket.kicad_pcb
mkdir -p production/drill-map
cp "$T"/*drl_map.pdf production/drill-map/
cp "$T"/*.gbl "$T"/*.gbo "$T"/*.gbp "$T"/*.gbs "$T"/*.gm1 "$T"/*.gtl "$T"/*.gto "$T"/*.gtp "$T"/*.gts "$T"/*.g1 "$T"/*.g2 "$T"/*.drl "$Z"/
rm -f production/ull-pocket-r0.5-gerbers.zip
(cd "$Z" && python3 -c "import zipfile,glob;z=zipfile.ZipFile('$R/production/ull-pocket-r0.5-gerbers.zip','w',zipfile.ZIP_DEFLATED);[z.write(f) for f in sorted(glob.glob('*'))]")
