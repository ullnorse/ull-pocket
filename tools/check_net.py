#!/usr/bin/env python3
"""Deterministic netlist checks for ull-pocket (reads build/ull-pocket.net)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import find, findall, parse  # noqa: E402

NET = os.path.join(os.path.dirname(__file__), "..", "build", "ull-pocket.net")
t = parse(open(NET).read())
nets = {}
pin2net = {}
for n in findall(find(t, "nets"), "net"):
    name = str(find(n, "name")[1]).lstrip("/")
    nodes = {(str(find(x, "ref")[1]), str(find(x, "pin")[1])) for x in findall(n, "node")}
    nets[name] = nodes
    for nd in nodes:
        pin2net[nd] = name
comps = {}
for c in findall(find(t, "components"), "comp"):
    ref = str(find(c, "ref")[1])
    fields = {str(f[1][1]) if isinstance(f[1], list) else "": "" for f in []}
    comps[ref] = {"value": str(find(c, "value")[1]),
                  "fp": str(find(c, "footprint")[1]) if find(c, "footprint") else ""}
    fl = find(c, "fields")
    if fl:
        for f in findall(fl, "field"):
            comps[ref][str(find(f, "name")[1])] = str(f[-1]) if not isinstance(f[-1], list) else ""

bad = []
# DNP / BOM / placement exclusion flags: empty netlist properties named like the flag
flags = {}
for c in findall(find(t, "components"), "comp"):
    names = {str(find(pp, "name")[1]) for pp in findall(c, "property")}
    flags[str(find(c, "ref")[1])] = names & {"dnp", "exclude_from_bom", "exclude_from_pos_files"}


def net(ref, pin):
    return pin2net.get((ref, str(pin)))


def expect(ref, pin, name):
    got = net(ref, pin)
    if got != name:
        bad.append(f"{ref}.{pin}: expected {name}, got {got}")


def same(*pins):
    ns = {net(r, p) for r, p in pins}
    if len(ns) != 1 or None in ns:
        bad.append(f"not same net: {pins} -> {ns}")
    return ns.pop() if len(ns) == 1 else None


def between(ref, a, b):
    """two-terminal part ref connects nets a and b (any order)"""
    got = {net(ref, 1), net(ref, 2)}
    if got != {a, b}:
        bad.append(f"{ref}: expected between {a} & {b}, got {got}")


def nc(ref, pin):
    n = net(ref, pin)
    if n is not None and len(nets[n]) > 1:
        bad.append(f"{ref}.{pin} should be unconnected, on {n} {nets[n]}")


# ---------------- ESP32-C6 GPIO map
ESP = {"8": "EN", "23": "BTN3_N", "22": None, "30": "RXD0", "31": "TXD0", "20": "NC", "17": "USB_D-", "18": "USB_D+",
       "12": "BAT_ALRT_N", "13": "USB_PGOOD_N", "5": "BTN_N", "6": "ACC_INT1", "9": "BARO_INT", "10": "BTN2_N",
       "15": "I2C_SDA", "16": "I2C_SCL", "19": "LED_USER", "24": "EPD_BUSY", "25": "EPD_RST_N",
       "26": "EPD_DC", "27": "EPD_CS_N", "28": "EPD_SCK", "29": "EPD_MOSI", "3": "+3V3", "1": "GND"}
for pin, nm in ESP.items():
    if nm == "NC":
        nc("U1", pin)
    elif nm:
        expect("U1", pin, nm)
for p in [2, 11, 14] + list(range(36, 54)):
    expect("U1", p, "GND")
for p in (4, 7, 21, 32, 33, 34, 35):
    nc("U1", p)
# LP-capable checks (GPIO0-7 = pins 12,13,5,6,9,10,15,16)
LP = {"12": 0, "13": 1, "5": 2, "6": 3, "9": 4, "10": 5, "15": 6, "16": 7}
for pin in ("5", "6", "9", "10"):  # BTN, ACC INT1, BARO INT, BTN2 must be LP GPIO for deep-sleep wake
    assert pin in LP
# EN RC
en = net("U1", 8)
for ref in comps:
    pass
# strap pins
io8 = net("U1", 22)
io9 = net("U1", 23)

# ---------------- I2C bus: every device on the same SDA/SCL
for ref, sda, scl in (("U2", 1, 4), ("U3", 2, 1), ("U4", 6, 4), ("U5", 8, 7)):
    expect(ref, sda, "I2C_SDA")
    expect(ref, scl, "I2C_SCL")
# address straps
expect("U2", 2, "GND")          # SHT31 ADDR=0 -> 0x44
expect("U3", 3, "GND")          # BMP585 SDO=0 -> 0x46
expect("U3", 7, "+3V3")         # BMP585 CSB=VDDIO -> I2C
expect("U4", 7, "+3V3")         # LIS3DH SA0=1 -> 0x19
expect("U4", 8, "+3V3")         # LIS3DH CS=1 -> I2C
expect("U4", 11, "ACC_INT1")
expect("U3", 5, "BARO_INT")
# sensor power
for ref, pins in (("U2", (5,)), ("U3", (4, 8)), ("U4", (1, 14))):
    for p in pins:
        expect(ref, p, "+3V3")
for ref, pins in (("U2", (8, 9, 7)), ("U3", (6,)), ("U4", (5, 12, 10)), ("U5", (4, 9, 1, 6))):
    for p in pins:
        expect(ref, p, "GND")
for ref, p in (("U2", 3), ("U2", 6), ("U4", 9), ("U4", 13), ("U4", 15), ("U4", 16)):
    nc(ref, p)

# ---------------- fuel gauge
expect("U5", 2, "VBAT")
expect("U5", 3, "VBAT")
expect("U5", 5, "BAT_ALRT_N")

# ---------------- power path
expect("J1", "A4", "VBUS")
for p in ("A9", "B4", "B9"):
    expect("J1", p, "VBUS")
for p in ("A1", "A12", "B1", "B12"):
    expect("J1", p, "GND")
same(("J1", "A6"), ("J1", "B6"), ("U8", 1), ("U8", 6), ("U1", 18))
same(("J1", "A7"), ("J1", "B7"), ("U8", 3), ("U8", 4), ("U1", 17))
expect("J1", "A6", "USB_D+")
expect("J1", "A7", "USB_D-")
expect("U8", 5, "VBUS")
expect("U8", 2, "GND")
nc("J1", "A8")
nc("J1", "B8")
expect("U6", 13, "VBUS")
for p in (10, 11):
    expect("U6", p, "VSYS")
for p in (2, 3):
    expect("U6", p, "VBAT")
for p in (8, 17, 4, 5, 15):
    expect("U6", p, "GND")       # VSS, EP, /CE, EN2, TD
nc("U6", 14)                    # TMR open: default timers
expect("U6", 7, "USB_PGOOD_N")
expect("U7", 1, "VSYS")
expect("U7", 3, "VSYS")
expect("U7", 5, "LDO_OUT")
expect("U7", 2, "GND")
expect("J2", 2, "VBAT")
expect("J2", 1, "BAT_N")
nc("J2", "MP")
assert ("U3", "9") not in pin2net, "BMP585 pin 9 is a marking area, not a pad"
# reverse-polarity FET: drain = BAT_N, source = GND, gate = VBAT via 100k
expect("Q2", 3, "BAT_N")
expect("Q2", 2, "GND")

# ---------------- e-paper FPC pinout (J3 pin n = panel pin n)
FPC = {1: "NC", 2: "EPD_GDR", 3: "EPD_RESE", 4: "NC", 6: "NC", 7: "NC", 8: "GND", 9: "EPD_BUSY",
       10: "EPD_RST_N", 11: "EPD_DC", 12: "EPD_CS_N", 13: "EPD_SCK", 14: "EPD_MOSI", 15: "+3V3",
       16: "+3V3", 17: "GND", 19: "NC", 21: "EPD_PREVGH", 23: "EPD_PREVGL", 25: "GND", 26: "GND",
       5: "EPD_VSH2", 18: "EPD_VDD", 20: "EPD_VSH1", 22: "EPD_VSL", 24: "EPD_VCOM"}
for p, nm in FPC.items():
    if nm == "NC":
        nc("J3", p)
    else:
        expect("J3", p, nm)
# side buttons (rev 0.6): SW1 UP IO2, SW2 OK IO5, SW3 DN IO9 (= BOOT, rev 0.7); each 100R series + 100 nF debounce
for sw, rs, node, swn in (("SW1", "R28", "BTN_N", "BTN_SW"), ("SW2", "R30", "BTN2_N", "BTN2_SW"),
                          ("SW3", "R31", "BTN3_N", "BTN3_SW")):
    expect(sw, 2, "GND")                       # shell tabs (pads 3/4) have no pins: left unconnected
    expect(sw, 1, swn)
    between(rs, node, swn)
    if comps[rs]["value"] != "100R" or comps[rs]["LCSC"] != "C25076":
        bad.append(f"{rs} should be 100R C25076")
    if comps[sw]["LCSC"] != "C393942":
        bad.append(f"{sw} should be TS24CA C393942")


# ---------------- passives by topology
def parts_on(netname, prefix):
    return sorted(r for r, p in nets.get(netname, ()) if r.startswith(prefix))


def two_term(ref):
    return {net(ref, 1), net(ref, 2)}


def find_part(a, b, value=None):
    hits = [r for r in comps if r[0] in "RCLDT" and two_term(r) == {a, b}
            and (value is None or comps[r]["value"] == value)]
    if not hits:
        bad.append(f"missing part {value or ''} between {a} and {b}")
    return hits


find_part("I2C_SDA", "+3V3", "10kR")
find_part("I2C_SCL", "+3V3", "10kR")
find_part("BTN_N", "+3V3", "100kR")
find_part("BTN_N", "GND", "100nF/16V")          # debounce with R28
find_part("BTN2_N", "+3V3", "100kR")
find_part("BTN2_N", "GND", "100nF/16V")         # debounce with R30
find_part("BTN3_N", "GND", "100nF/16V")         # debounce with R31; pull-up is R24 (IO9 strap)
find_part("BAT_ALRT_N", "+3V3", "100kR")
find_part("USB_PGOOD_N", "+3V3", "100kR")
find_part(net("U1", 8), "+3V3", "10kR")
find_part("BTN3_N", "+3V3", "10kR")             # IO9 BOOT strap pull-up = SW3 pull-up (DN held at reset -> download mode)
if parts_on("BTN3_N", "R") != ["R24", "R31"]:
    bad.append(f"BTN3_N should carry only R24 (pull-up) and R31: {parts_on('BTN3_N', 'R')}")
find_part("EPD_CS_N", "+3V3", "100kR")           # e-paper sleep pull-ups
find_part("EPD_RST_N", "+3V3", "100kR")
# programming pogo cluster J4: +3V3, GND, EN, BOOT (BTN3_N), TXD0, RXD0; no BOM, no placement
for pin, nm in ((1, "VREF"), (2, "GND"), (3, "EN"), (4, "BTN3_N"), (5, "TXD0"), (6, "RXD0")):
    expect("J4", pin, nm)
find_part("VREF", "+3V3", "1kR")           # J4.1 is a sense-only VREF; programmer cannot feed +3V3
if flags["J4"] != {"exclude_from_bom", "exclude_from_pos_files"}:
    bad.append(f"J4 should be excluded from BOM and placement: {flags['J4']}")
if "PogoPads_2x3_P2.54mm" not in comps["J4"]["fp"]:
    bad.append("J4 footprint should be the 2x3 pogo pad cluster")
find_part(net("U1", 8), "GND", "1uF/25V")
find_part(net("U1", 22), "+3V3", "10kR")
find_part("+3V3", "GND", "22uF/25V")      # C8 U1 bulk
find_part("+3V3", "GND", "10uF/10V")
find_part(net("J1", "A5"), "GND", "5.1kR")
find_part(net("J1", "B5"), "GND", "5.1kR")
if net("J1", "A5") == net("J1", "B5"):
    bad.append("CC1 and CC2 shorted")
sh0 = find_part(net("J1", "SH"), "GND", "0R")        # plastic case: shield straight to GND
if sh0 and comps[sh0[0]]["LCSC"] != "C17168":
    bad.append("shield 0R should be 0402 C17168")
shc = find_part(net("J1", "SH"), "GND", "4.7nF/50V")  # RC option kept as a DNP footprint
if shc and flags[shc[0]] != {"dnp", "exclude_from_bom", "exclude_from_pos_files"}:
    bad.append("shield 4.7 nF should be DNP + excluded from BOM and placement")
ts = net("U6", 1)
th = find_part(ts, "GND", "NTC10k")[0]
if comps[th]["LCSC"] != "C279936" or "0603" not in comps[th]["fp"]:
    bad.append("TH1 should be the Sunlord 0603 NTC B3950 C279936")
fb = find_part(ts, "GND", "10kR")           # DNP fixed-10k fallback in parallel
if len(fb) != 1 or flags[fb[0]] != {"dnp", "exclude_from_bom", "exclude_from_pos_files"}:
    bad.append("fallback 10k on TS missing or not DNP + excluded from BOM and placement")
find_part(net("U6", 16), "GND", "3.3kR")    # ISET
find_part(net("U6", 12), "GND", "3.3kR")    # ILIM
find_part(net("U6", 6), "VBUS", "100kR")    # EN1 divider top
find_part(net("U6", 6), "GND", "100kR")     # EN1 divider bottom
find_part("VBUS", "GND", "1uF/50V")
find_part("VSYS", "GND", "10uF/10V")
find_part("VBAT", "GND", "10uF/10V")
find_part("VBAT", "GND", "100nF/16V")
find_part("VSYS", "GND", "1uF/25V")
find_part("LDO_OUT", "GND", "1uF/25V")   # C7 on the LDO side of the link
find_part("LDO_OUT", "+3V3", "0R")        # sleep-current link
gate = net("Q2", 1)
find_part(gate, "VBAT", "100kR")
if gate in ("GND", "VBAT"):
    bad.append("Q2 gate must be on its own node")
if "SPARE_IO14" in nets or "TP6" in comps:
    bad.append("SPARE_IO14 / TP6 retired in rev 0.6")
for nm in ("VBUS", "VBAT", "VSYS", "+3V3", "GND"):
    if not [r for r in comps if r.startswith("TP") and comps[r]["value"] == nm and net(r, 1) == nm]:
        bad.append(f"missing test pad on {nm}")
for nm in ("EPD_VSH1", "EPD_VSH2", "EPD_VSL", "EPD_VCOM", "EPD_VDD", "EPD_PREVGH", "EPD_PREVGL", "LDO_OUT", "BAT_N"):
    if nm not in nets:
        bad.append(f"net {nm} missing")
# CHG LED chain: CHG -> LED K, LED A -> 2k -> VSYS
led = [r for r in comps if comps[r]["value"] == "RED"][0]
expect(led, 1, net("U6", 9))
find_part(net(led, 2), "VSYS", "2kR")
# power LED: VBUS -> 2k -> green -> GND
g = [r for r in comps if comps[r]["value"] == "GREEN"][0]
expect(g, 1, "GND")
find_part(net(g, 2), "VBUS", "2kR")
# user LED: GPIO -> R -> LED -> GND, active high; only one user LED (D6), no D7/R23
assert "D7" not in comps and "R23" not in comps, "D7/R23 retired in rev 0.5"
assert len([r for r in comps if r.startswith("D") and "LED" in comps[r].get("Description", "")]) == 3
assert comps["D6"]["LCSC"] == "C965865"  # XL-1606UBC side-view
for r_, l_ in (("D1", "C965860"), ("D5", "C965863")):
    assert comps[r_]["LCSC"] == l_, r_
for nm, val, col in (("LED_USER", "470R", "BLUE"),):
    ld = [r for r in comps if comps[r]["value"] == col][0]
    expect(ld, 1, "GND")
    find_part(nm, net(ld, 2), val)
# no addressable LEDs
for r, c in comps.items():
    if "WS2812" in c["value"].upper() or "SK6812" in c["value"].upper():
        bad.append(f"{r}: addressable LED not allowed")
# e-paper boost (Good Display reference)
sw = net("Q1", 3)
expect("Q1", 1, "EPD_GDR")
expect("Q1", 2, "EPD_RESE")
find_part("EPD_GDR", "GND", "1MR")
find_part("EPD_RESE", "GND", "2.2R")
l1 = find_part("+3V3", sw, "47uH")
if l1 != ["L1"] or comps["L1"]["fp"] != "ull-pocket:IND-SMD_L4.0-W4.0_FNR40XXS" or comps["L1"]["LCSC"] != "C167888":
    bad.append("L1 should be FNR4030S470MT C167888 with the FNR40XXS footprint")
find_part("+3V3", "GND", "4.7uF/25V")
d = {r: (net(r, 1), net(r, 2)) for r in comps if comps[r]["value"] == "MBR0530"}   # (K, A)
x = [n for k, a in d.values() for n in (k, a) if n not in (sw, "GND", "EPD_PREVGH", "EPD_PREVGL")]
xnode = x[0] if x else None
got = {(k, a) for k, a in d.values()}
if got != {("EPD_PREVGH", sw), ("GND", xnode), (xnode, "EPD_PREVGL")}:
    bad.append(f"boost diodes (K,A) wrong: {got}, sw={sw} x={xnode}")
find_part(sw, xnode, "4.7uF/50V")    # C19
find_part("EPD_PREVGH", "GND", "1uF/50V")
find_part("EPD_PREVGL", "GND", "1uF/50V")
for p in (5, 18, 20, 22, 24):
    find_part(net("J3", p), "GND", "1uF/50V")
find_part("+3V3", "GND", "1uF/50V")   # VCI cap
same(("J3", 15), ("J3", 16))

# every BOM part has MPN/LCSC/footprint
for r, c in sorted(comps.items()):
    if r.startswith("#") or r.startswith("TP") or r == "J4":
        continue
    for k in ("MPN", "Manufacturer", "LCSC"):
        if not c.get(k):
            bad.append(f"{r} missing field {k}")
    if not c["fp"]:
        bad.append(f"{r} missing footprint")

print(f"{len(nets)} nets, {len([r for r in comps if not r.startswith('#')])} parts")
for b in bad:
    print("FAIL", b)
print("RESULT:", "PASS" if not bad else f"{len(bad)} FAIL")
sys.exit(1 if bad else 0)
