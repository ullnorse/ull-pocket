import sys, time
from rt import *
from gridroute import *
r = R(sys.argv[1] if len(sys.argv) > 1 else 'hand.kicad_pcb')
keep = [('FB', 26.3, 12.0, 40.6, 45.0), ('FB', 15.0, 30.5, 26.3, 45.0), ('FB', 19.3, 11.65, 26.3, 30.5),
        ('F', 14.6, 13.6, 19.3, 30.5), ('B', 16.9, 14.3, 21.5, 18.9), ('F', 27.2, 1.3, 38.0, 9.95)]
grid = Grid(r, keep)
BAND1 = [('B', 11.0, 3.6, 38.0, 7.6), ('B', 32.0, 3.6, 38.0, 9.7)]
I2C = [('B', 5.2, 7.6, 32.0, 9.1), ('FB', 2.0, -5.5, 8.0, 1.5), ('B', 5.2, 0.3, 7.6, 12.5), ('B', 9.0, 7.6, 17.0, 14.0)]
SOUTH = [('B', 5.2, 9.0, 32.0, 11.65), ('FB', 15.2, 11.9, 19.3, 14.5), ('B', 5.2, 11.9, 19.3, 16.5), ('FB', 9.0, 9.0, 17.0, 16.5)]
J4R = [('FB', 11.0, 2.5, 17.6, 8.6)]
SOUTHX = [('FB', 5.2, 8.3, 32.0, 11.95), ('FB', 15.2, 11.9, 19.3, 14.5), ('FB', 5.2, 11.9, 15.2, 16.5)]
plan = [('/RXD0', BAND1 + J4R), ('/TXD0', BAND1 + J4R), ('/BOOT', BAND1 + J4R), ('/EN', BAND1 + J4R),
        ('/BARO_INT', SOUTHX), ('/BAT_ALRT_N', SOUTHX), ('/SPARE_IO14', SOUTHX),
        ('/I2C_SCL', SOUTHX + [('FB', 2.0, -5.5, 8.0, 1.5), ('B', 5.2, 0.3, 7.6, 12.5), ('F', 17.0, 4.5, 23.0, 11.95)]),
        ('/I2C_SDA', SOUTHX + [('FB', 2.0, -5.5, 8.0, 1.5), ('B', 5.2, 0.3, 7.6, 12.5), ('F', 17.0, 4.5, 23.0, 11.95)]),
        ('/BTN_N', [('B', 2.4, 1.0, 38.0, 7.6), ('FB', 2.4, 3.6, 5.0, 25.0)]),
        ('Net-(Q2-G)', None)]
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
for item in plan:
    n, allow = item[0], item[1]
    pr = item[2] if len(item) > 2 else 1.6
    if only and n not in only:
        continue
    t = time.time()
    ok = route_net(r, grid, n, allow=allow, padr=pr)
    print(n, 'ok' if ok else 'FAIL', '%.1fs' % (time.time() - t), flush=True)
r.save('auto.kicad_pcb')
