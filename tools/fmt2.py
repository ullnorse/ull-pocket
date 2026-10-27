import json,sys
d=json.loads(sys.stdin.read())
for r in d.get("results",[]):
    s=r.get("specs") or {}
    sp=" ".join(f"{k}={v}" for k,v in s.items() if k in ("Capacitance","Voltage Rating","Temperature Coefficient","Resistance","Tolerance","Inductance","Current Rating","Saturation Current (Isat)","DC Resistance (DCR)","Rated Current"))
    print(f'{r["lcsc"]:>10} {r["model"][:24]:24} {str(r.get("manufacturer"))[:16]:16} {r["package"][:10]:10} st={r["stock"]:<8} {r["library_type"]:9} {sp}')
