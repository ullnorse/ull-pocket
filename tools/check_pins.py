#!/usr/bin/env python3
"""Deterministic symbol checks.

1. Every project IC symbol: pin number -> name equals the easyeda2kicad symbol
   (ground truth pin table), except a documented allow-list of renames.
2. Every project symbol with a footprint: set of symbol pin numbers == set of
   footprint pad numbers (ignoring unnumbered NPTH pads).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import find, findall, parse, walk  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LIB = os.path.join(ROOT, "lib", "ull-pocket.kicad_sym")
EE = os.path.join(ROOT, "build", "ee", "ee.kicad_sym")
FPSTD = "/home/blueeyes/.backplane-bend/kicad/10.99.0-bp.4/share/kicad/footprints"

# project symbol -> easyeda symbol name
EEMAP = {
    "ESP32-C6-MINI-1-H4": "ESP32-C6-MINI-1-H4", "SHT31-DIS-B": "SHT31-DIS-B",
    "BMP585": "BMP585_C18184976", "LIS3DHTR": "LIS3DHTR_C15134", "MAX17048G+T10": "MAX17048G+T10",
    "BQ24073RGTR": "BQ24073RGTR", "RT9080-33GJ5": "RT9080-33GJ5", "USBLC6-2SC6": "USBLC6-2SC6_C2687116",
    "FPC-05FB-24PH20": "FPC-05FB-24PH20", "TS24CA": "TS24CA", "SI1308EDL": "SI1308EDL-T1-GE3",
}
# documented, intentional name differences (symbol, pin): (easyeda, ours)
ALLOW = {
    ("SHT31-DIS-B", "9"): ("EPAD", "VSS"),
    ("MAX17048G+T10", "9"): ("EP", "GND"),
    ("BQ24073RGTR", "17"): ("EP", "VSS"),
    ("TS24CA", "3"): ("3", "MP"), ("TS24CA", "4"): ("4", "MP"),
}
# easyeda pins deliberately dropped: BMP585 pin 9 is a laser-marking area under solder resist, not a pad
REMOVED = {("BMP585", "9")}
FPC_PANEL = ["NC", "GDR", "RESE", "NC", "VSH2", "TSCL", "TSDA", "BS", "BUSY", "RES#", "D/C#", "CS#",
             "SCL", "SDA", "VDDIO", "VCI", "VSS", "VDD", "VPP", "VSH1", "VGH", "VSL", "VGL", "VCOM"]


def pins_of(sym):
    out = {}
    for n in walk(sym):
        if n and n[0] == "pin":
            out.setdefault(str(find(n, "number")[1]), set()).add(str(find(n, "name")[1]))
    return out


def norm(s):
    return re.sub(r"~\{([^}]*)\}", r"\1", s)


def symbols(path):
    t = parse(open(path).read())
    return {str(s[1]): s for s in findall(t, "symbol")}


def fp_pads(fp):
    lib, name = fp.split(":")
    base = os.path.join(ROOT, "lib", "ull-pocket.pretty") if lib == "ull-pocket" else os.path.join(FPSTD, lib + ".pretty")
    t = parse(open(os.path.join(base, name + ".kicad_mod")).read())
    return {str(p[1]) for p in findall(t, "pad") if str(p[1]) != ""}


def main():
    ours = symbols(LIB)
    ee = symbols(EE)
    bad = 0
    for s, e in EEMAP.items():
        a, b = pins_of(ours[s]), pins_of(ee[e])
        for rs, rn in REMOVED:
            if rs == s:
                b.pop(rn, None)
        if set(a) != set(b):
            print(f"FAIL {s}: pin numbers differ: ours-only {set(a)-set(b)} ee-only {set(b)-set(a)}")
            bad += 1
            continue
        for num in sorted(a, key=lambda x: (len(x), x)):
            na = {norm(x) for x in a[num]}
            nb = {norm(x) for x in b[num]}
            if s == "FPC-05FB-24PH20":
                exp = {FPC_PANEL[int(num) - 1]} if int(num) <= 24 else {"MP"}
                if na != exp:
                    print(f"FAIL {s} pin {num}: {na} != panel {exp}")
                    bad += 1
                continue
            if na != nb:
                if ALLOW.get((s, num)) == (next(iter(nb)), next(iter(na))):
                    continue
                print(f"FAIL {s} pin {num}: ours {na} easyeda {nb}")
                bad += 1
        print(f"ok   {s}: {len(a)} pins match easyeda")
    for name, sym in ours.items():
        fp = None
        for p in findall(sym, "property"):
            if p[1] == "Footprint":
                fp = str(p[2])
        if not fp:
            continue
        pads = fp_pads(fp)
        pins = set(pins_of(sym))
        if pads != pins:
            print(f"FAIL {name} vs {fp}: pins-only {sorted(pins-pads)} pads-only {sorted(pads-pins)}")
            bad += 1
        else:
            print(f"ok   {name}: {len(pins)} pins == pads of {fp}")
    print("RESULT:", "PASS" if not bad else f"{bad} FAIL")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
