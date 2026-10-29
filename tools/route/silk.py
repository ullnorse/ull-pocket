import json, re, sys
import pcbnew
from rt import *
r = R(sys.argv[1])
d = json.load(open('drc.json'))
refs = set()
for v in d['violations']:
    if v['type'] in ('silk_over_copper', 'silk_overlap'):
        for i in v['items']:
            m = re.match(r'Reference field of (\S+)', i['description'])
            if m: refs.add(m.group(1))
for ref in sorted(refs):
    r.b.FindFootprintByReference(ref).Reference().SetLayer(pcbnew.F_Fab)
print(sorted(refs))
r.save(sys.argv[1])
