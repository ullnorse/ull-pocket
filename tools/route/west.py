import sys, time
from rt import *
from gridroute import *
r = R(sys.argv[1] if len(sys.argv) > 1 else 'hand.kicad_pcb')
keep = [('FB', 26.3, 12.0, 40.6, 45.0), ('FB', 15.0, 30.5, 26.3, 45.0), ('FB', 19.3, 12.8, 26.3, 30.5),
        ('F', 14.6, 13.6, 19.3, 30.5), ('B', 16.9, 14.3, 21.5, 18.9), ('F', 27.2, 1.3, 38.0, 9.95)]
grid = Grid(r, keep)
BAND1 = [('B', 2.4, 3.9, 38.0, 8.3), ('B', 2.4, 3.9, 5.0, 31.6), ('B', 2.4, 19.5, 14.8, 31.6)]
BAND2 = [('FB', 5.2, 8.3, 32.0, 11.95), ('FB', 2.0, -5.5, 8.0, 1.5), ('F', 4.6, 0.3, 7.6, 12.5), ('B', 5.2, 0.3, 7.6, 12.5), ('FB', 9.0, 8.3, 17.5, 16.5),
         ('F', 17.5, 4.5, 23.0, 11.95)]
plan = [('/SPARE_IO14', BAND1), ('/BOOT', BAND1), ('/EN', BAND1 + [('F', 23.0, 5.5, 27.0, 8.5)]), ('/RXD0', BAND1), ('/TXD0', BAND1),
        ('/BTN_N', BAND1 + [('F', 23.0, 3.5, 27.0, 6.0)]), ('/BARO_INT', BAND2), ('/BAT_ALRT_N', BAND2), ('/I2C_SCL', [b for b in BAND2 if b[1] != 4.6] + [('F', 6.0, 0.3, 7.6, 12.5)]), ('/I2C_SDA', [b for b in BAND2 if b[1] != 4.6] + [('F', 4.6, 0.3, 5.9, 12.5)]),
        ('/ACC_INT1', [('FB', 20.5, 4.5, 27.0, 8.0)]), ('Net-(Q2-G)', None)]
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
for n, allow in plan:
    if only and n not in only:
        continue
    t = time.time()
    ok = route_net(r, grid, n, allow=allow, padr=1.6)
    print(n, 'ok' if ok else 'FAIL', '%.1fs' % (time.time() - t), flush=True)
r.save('auto.kicad_pcb')
