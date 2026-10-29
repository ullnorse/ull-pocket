#!/bin/sh
# Layout review renders into build/layout: copper layers, 2D top/bottom with silk, 3D views.
set -e
cd "$(dirname "$0")/.."
KC=/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli
PCB=ull-pocket.kicad_pcb
O=build/layout
rm -rf $O && mkdir -p $O
svg() { # name layers [extra]
  $KC pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet --drill-shape-opt 2 -l "$2" $3 -o $O/$1.svg $PCB >/dev/null
  rsvg-convert -b white -w 1800 $O/$1.svg -o $O/$1.png
}
svg cu_F_Cu "F.Cu,Edge.Cuts"
svg cu_In1_Cu "In1.Cu,Edge.Cuts"
svg cu_In2_Cu "In2.Cu,Edge.Cuts"
svg cu_B_Cu "B.Cu,Edge.Cuts" --mirror
svg 2d_top "F.Cu,F.Mask,F.SilkS,Edge.Cuts"
svg 2d_bottom "B.Cu,B.Mask,B.SilkS,Edge.Cuts" --mirror
r3() { $KC pcb render -o $O/$1.png -w 1600 -h 1300 --quality high --background opaque --preset follow_plot_settings $2 $PCB >/dev/null; }
r3 3d_front_components "--side top"
r3 3d_back_panel "--side bottom"
r3 3d_angle "--side top --rotate -45,0,25 --perspective --zoom 0.9"
r3 3d_led_edge "--side front --zoom 2.2 --pan 0,0,0"
ls $O
