import json,sys
d=json.loads(sys.stdin.read())
for r in d.get("results",[]):
    print(f'{r["lcsc"]:>10} {r["model"][:28]:28} {r["package"][:22]:22} stock={r["stock"]:<7} ${r["price"]:.2f} {r["library_type"]}')
