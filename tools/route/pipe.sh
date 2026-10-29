#!/bin/sh
set -e
cd /home/blueeyes/projects/hardware/ull-pocket/build/route
python3 route.py 2>&1 | grep -v Debug
timeout 1500 python3 west.py hand.kicad_pcb 2>&1 | grep -v -i "debug\|leak" | grep -v " ok "  || true
timeout 900 python3 finish.py auto.kicad_pcb vias.kicad_pcb 2>&1 | grep -v -i "debug\|leak\|no via spot"
python3 zones.py vias.kicad_pcb done.kicad_pcb 2>&1 | grep -v -i "debug\|leak" || true
./drc.sh done.kicad_pcb "" all 2>&1 | grep -E "^- (clear|hole|short|track_w|copper|starv|conn|track_d|via_d)|^ +[0-9]|^~|unconn" | head -40
