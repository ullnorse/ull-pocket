import json, sys, collections
d = json.load(open(sys.argv[1]))
verbose = len(sys.argv) > 2
c = collections.Counter((v['severity'], v['type']) for v in d['violations'])
for k, n in sorted(c.items()): print(f'{n:5d} {k[0]:8s} {k[1]}')
un = collections.defaultdict(list)
for v in d['unconnected_items']:
    it = v['items']
    net = it[0]['description']
    un[it[0].get('description', '')].append(it)
print('unconnected', len(d['unconnected_items']), 'parity', len(d['schematic_parity']))
if verbose:
    for v in d['violations']:
        if v['severity'] == 'error' or sys.argv[2] == 'all':
            print('-', v['type'], '|', ' || '.join('%s @(%.2f,%.2f)' % (i['description'][:70], i['pos']['x'] - 100, i['pos']['y'] - 100) for i in v['items']))
    for v in d['unconnected_items']:
        print('~', ' || '.join('%s @(%.2f,%.2f)' % (i['description'][:60], i['pos']['x'] - 100, i['pos']['y'] - 100) for i in v['items']))
