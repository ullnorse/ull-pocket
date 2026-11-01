#!/usr/bin/env python3
"""Generate the JLCPCB BOM, CPL and rotation-check table from the PCB.

usage: jlc_cpl.py <ull-pocket.kicad_pcb> <ee-dir> <out-dir>
ee-dir holds one <LCSC>/lib.pretty/*.kicad_mod per LCSC number
(easyeda2kicad --footprint --lcsc_id=Cxxx --output=<ee-dir>/Cxxx/lib).

For every unique KiCad footprint + LCSC pair the EasyEDA footprint pads are matched
to the KiCad pads (same pad name, or the same function for the LEDs) to find the
rotation delta and origin shift between the two footprints:
    EE_pad = Rot(delta) * KiCad_pad + t         (KiCad frame, y down, CCW positive)
so that  CPL_rot = KiCad_rot - delta,  CPL_pos = KiCad_pos - Rot(CPL_rot) * t.
"""
import collections, csv, glob, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexp

pcb_path, ee_dir, out_dir = sys.argv[1:4]
name = sys.argv[4] if len(sys.argv) > 4 else "ull-pocket-r0.7"
EXCLUDE_PREFIX = ("TP", "H", "ASSY")
# EE pad name that is the same *function* as KiCad pad "1" (cathode on the LEDs).
# C965865's EE symbol numbers anode=1, cathode=2; the datasheet (and our footprint) has 1 = cathode.
FUNC_PAD1 = {"C965865": "2"}
T_MIN = 0.1  # ignore origin shifts below this (fit noise from differing pad shapes)


def rot(p, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)


def pads(fp):
    out = collections.defaultdict(list)
    for p in fp:
        if isinstance(p, list) and p and p[0] == "pad":
            at = next(q for q in p if isinstance(q, list) and q[0] == "at")
            out[str(p[1])].append((float(at[1]), float(at[2])))
    return out


def mean(l):
    return (sum(a for a, b in l) / len(l), sum(b for a, b in l) / len(l))


def fit(pk, pe, d, names, rename):
    pts = []
    for n in names:
        b = mean(pe[rename.get(n, n)])
        a = rot(mean(pk[n]), d)
        pts.append((a, b))
    t = (sum(b[0] - a[0] for a, b in pts) / len(pts), sum(b[1] - a[1] for a, b in pts) / len(pts))
    res = max(math.hypot(b[0] - a[0] - t[0], b[1] - a[1] - t[1]) for a, b in pts)
    return t, res


def match(pk, pe, lcsc):
    rename = {}
    if lcsc in FUNC_PAD1:  # swap 1<->2 on the EE side
        rename = {"1": FUNC_PAD1[lcsc], "2": "1" if FUNC_PAD1[lcsc] == "2" else "2"}
    names = [n for n in pk if n and rename.get(n, n) in pe]
    cand = []
    for d in (0, 90, 180, 270):
        t, res = fit(pk, pe, d, names, rename)
        cand.append((res, d, t))
    cand.sort()
    return cand[0][1], cand[0][2], cand[0][0], cand[1][0], len(names), rename


tree = sexp.parse(open(pcb_path).read())
parts = []
for f in tree:
    if isinstance(f, list) and f and f[0] == "footprint":
        d = {p[1]: p[2] for p in f if isinstance(p, list) and p[0] == "property"}
        a = next((p[1:] for p in f if isinstance(p, list) and p[0] == "attr"), [])
        at = next(p for p in f if isinstance(p, list) and p[0] == "at")
        x, y = at[1:3]
        r = float(at[3]) if len(at) > 3 else 0.0
        layer = next(p[1] for p in f if isinstance(p, list) and p[0] == "layer")
        ref = d["Reference"]
        if "dnp" in a or "exclude_from_bom" in a or ref.startswith(EXCLUDE_PREFIX):
            continue
        parts.append(dict(ref=ref, val=d["Value"], fp=f[1], lcsc=d["LCSC"], x=float(x), y=float(y), rot=r,
                          pads=pads(f), layer=layer))
assert all(p["layer"] == "F.Cu" for p in parts), "bottom-side part found"
missing = [p["ref"] for p in parts if not p["lcsc"].startswith("C")]
assert not missing, missing


def natkey(r):
    return (r.rstrip("0123456789"), int("".join(c for c in r if c.isdigit())))


# ---- per-pair analysis
pairs = collections.OrderedDict()
for p in sorted(parts, key=lambda p: natkey(p["ref"])):
    pairs.setdefault((p["fp"], p["lcsc"]), []).append(p)
info = {}
for (fp, lcsc), ps in pairs.items():
    eefile = glob.glob(os.path.join(ee_dir, lcsc, "lib.pretty", "*.kicad_mod"))[0]
    pe = pads(sexp.parse(open(eefile).read()))
    pk = ps[0]["pads"]
    d, t, res, res2, n, rename = match(pk, pe, lcsc)
    if math.hypot(*t) < T_MIN:
        t = (0.0, 0.0)
    info[(fp, lcsc)] = dict(delta=d, t=t, res=res, res2=res2, n=n, ee=os.path.basename(eefile)[:-10],
                            p1k=mean(pk["1"]) if "1" in pk else mean(pk.get("A1", [(0, 0)])),
                            p1e=mean(pe["A1B12"] if "A1B12" in pe else pe[rename.get("1", "1")]))

# ---- CPL
os.makedirs(out_dir, exist_ok=True)
rows = []
for p in sorted(parts, key=lambda p: natkey(p["ref"])):
    i = info[(p["fp"], p["lcsc"])]
    r = (p["rot"] - i["delta"]) % 360
    dx, dy = rot(i["t"], r)
    rows.append((p["ref"], p["x"] - dx, -(p["y"] - dy), "T", r))
with open(os.path.join(out_dir, name + "-cpl.csv"), "w", newline="") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref, x, y, l, r in rows:
        w.writerow([ref, f"{x:.4f}", f"{y:.4f}", l, f"{r:g}"])

# ---- BOM
groups = collections.OrderedDict()
for p in sorted(parts, key=lambda p: natkey(p["ref"])):
    groups.setdefault((p["val"], p["fp"].split(":")[-1], p["lcsc"]), []).append(p["ref"])
with open(os.path.join(out_dir, name + "-bom.csv"), "w", newline="") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(["Comment", "Designator", "Footprint", "LCSC"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: natkey(kv[1][0])):
        w.writerow([val, ",".join(refs), fp, lcsc])

# ---- rotation-check.md
def v(p):
    return "(%.2f, %.2f)" % (p[0] + 0.0, p[1] + 0.0)

lines = ["# Rotation check (JLCPCB CPL)", "",
         "Each unique KiCad footprint + LCSC pair is compared against the EasyEDA footprint JLC places for that LCSC",
         "number (`easyeda2kicad --footprint`). Pads are matched by name (LEDs: by function), giving",
         "`EE_pad = Rot(delta) * KiCad_pad + t` in the KiCad frame (y down, CCW positive).",
         "CPL rotation = KiCad rotation - delta. CPL position = KiCad position - Rot(CPL rotation) * t.", "",
         "Pin-1 vectors are pad-1 centres relative to the footprint origin (mm, footprint-local, unrotated).",
         "`match` is the worst pad-centre residual of the best fit / of the second-best rotation (mm);",
         "a large second-best number means the rotation is unambiguous (symmetric passives are 0/180-ambiguous only",
         "in the unpolarised sense and need no correction). Origin shifts under 0.1 mm are ignored.", "",
         "| Refs | KiCad footprint | LCSC | KiCad pin-1 | EE footprint | EE pin-1 | delta | origin shift t | match |",
         "|---|---|---|---|---|---|---|---|---|"]
for (fp, lcsc), ps in pairs.items():
    i = info[(fp, lcsc)]
    refs = ",".join(p["ref"] for p in ps)
    k1 = v(i["p1k"]) + (" (cathode)" if lcsc in ("C965860", "C965863", "C965865", "C8598") else "")
    e1 = v(i["p1e"]) + (" (pad 2 = cathode)" if lcsc == "C965865" else
                        " (cathode)" if lcsc in ("C965860", "C965863", "C8598") else "")
    lines.append(f"| {refs} | {fp.split(':')[-1]} | {lcsc} | {k1} | {i['ee']} | {e1} | {i['delta']} deg | "
                 f"{v(i['t']) if i['t']!=(0.0,0.0) else '0'} | {i['res']:.2f} / {i['res2']:.2f} |")
lines += ["", "## Notes", "",
          "- Parts imported from EasyEDA (L1, J3, U3, U5, SW1, U1) and the stock R/C/D footprints need delta 0 and no shift.",
          "- Q1, Q2, U2, U7, U8: the EE footprint is the KiCad one rotated (delta in the table); CPL rotation = KiCad rotation - delta.",
          "- LEDs D1, D5, D6: all three EE footprints have the cathode on the -x pad. For C965860/C965863 that is pad 1;",
          "  for C965865 the EE symbol numbers anode = 1, cathode = 2 (datasheet and our footprint: 1 = cathode), so the",
          "  match is by function and D6 also gets delta 180. Check D1, D5, D6 polarity in JLC's placement preview.",
          "  The 0.28 mm y shift is the KiCad pad centre being off the origin (pads are 0.28 mm above the origin).",
          "- J1: signal pads give a 1.57 mm shift; the shell legs differ by 1.42 mm (KiCad and EE footprints disagree by 0.15 mm",
          "  between signal and shell pads), the 1.57 mm signal-pad value is used. EE pin 1 shown is pad A1B12.",
          "- J2 (DEALON PH-2PWB): pads 1 and 2 coincide with our footprint, no shift. The EE origin is used as the part centre. It differs from the EE pad-bounding-box centre by",
          "  <= 0.15 mm everywhere except SW1 (0.30 mm), so the origin-vs-centre ambiguity is at most 0.3 mm (SW1).",
          "- Coordinates are in the Gerber frame (absolute page coordinates, y up), the same frame as the Gerber and drill files.",
          "- Not verifiable offline: JLC's own assembly DB can differ from the EasyEDA footprint. Confirm the placement preview."]
if name == "ull-pocket-r0.7":
    open(os.path.join(out_dir, "rotation-check.md"), "w").write("\n".join(lines) + "\n")
print(len(rows), "CPL rows,", len(groups), "BOM lines")
nz = [(k, i) for k, i in info.items() if i["delta"] or i["t"] != (0.0, 0.0)]
for (fp, lcsc), i in nz:
    print(lcsc, fp.split(":")[-1], [p["ref"] for p in pairs[(fp, lcsc)]], "delta", i["delta"], "t", i["t"])
