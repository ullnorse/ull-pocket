"""Dump pin number->name tables from a kicad_sym file (sexp)."""
import re, sys
txt = open(sys.argv[1]).read()
# split top-level symbols
for m in re.finditer(r'\n\s\(symbol "([^"]+)"', txt):
    pass
syms = re.split(r'\n\t?\s?\(symbol "', txt)
cur=None
for blk in re.finditer(r'\(symbol "([^"_]+(?:_[^"]*)?)"\s*\n?\s*\(', txt):
    pass
# simpler: track names
out={}
name=None
for line in txt.splitlines():
    m=re.match(r'\s*\(symbol "([^"]+)"', line)
    if m and not re.search(r'_\d+_\d+$', m.group(1)):
        name=m.group(1); out[name]=[]
pinre=re.compile(r'\(pin (\w+) \w+.*?\(name "([^"]*)".*?\(number "([^"]*)"', re.S)
for nm in out:
    i=txt.find(f'(symbol "{nm}"')
    j=txt.find('\n  (symbol "', i+10)
    if j<0: j=len(txt)
    blk=txt[i:j]
    pins=sorted(((n,na,t) for t,na,n in pinre.findall(blk)), key=lambda x:(int(x[0]) if x[0].isdigit() else 999, x[0]))
    print(f'== {nm} ({len(pins)} pins)')
    print('  '+'  '.join(f'{n}:{na}[{t[:3]}]' for n,na,t in pins))
