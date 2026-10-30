#!/usr/bin/env python3
"""phases.py : where the ATE comes from. For each (variant, seq) mean over runs of the posyaw-aligned position / yaw error
RMS in phases: take-off transient [init, 10 s], cruise [10, 90 s], late [90 s, end]; plus the first-pose tilt error and
the max tilt in [init, init+1.5 s]. Reads analysis/runs/*.npz.  usage: phases.py var1,var2,...
"""
import glob
import sys
from collections import defaultdict

import numpy as np

A = '/home/sasa/workspace/savior_ws/results/ov_diag/analysis/runs'
PH = [('init-10s', None, 10), ('10-90s', 10, 90), ('90s-end', 90, 1e9)]
out = defaultdict(list)
for v in sys.argv[1].split(','):
    for f in sorted(glob.glob(f'{A}/*__{v}__run_*.npz')):
        seq = f.split('/')[-1].split('__')[0].replace('warehouse_', '')
        z = np.load(f); t = z['t']
        row = []
        for _, a, b in PH:
            m = (t >= (a if a is not None else t[0])) & (t < b)
            row += [np.sqrt(np.mean(z['err'][m] ** 2)), np.sqrt(np.mean(z['yaw'][m] ** 2))]
        m15 = t < t[0] + 1.5
        row += [z['tilt'][0], z['tilt'][m15].max(), np.sqrt(np.mean(z['err'] ** 2))]
        out[(v, seq)].append(row)
print('variant seq n | pos RMS / yaw RMS: ' + ' | '.join(p[0] for p in PH) + ' | tilt first, max(1.5s) | ATE')
for (v, s), rows in sorted(out.items(), key=lambda k: (k[0][1], k[0][0])):
    r = np.mean(rows, 0)
    print(f'{v:15s} {s:13s} {len(rows):2d} | ' + ' | '.join(f'{r[2*i]:.3f} m / {r[2*i+1]:.2f} deg' for i in range(3))
          + f' | {r[6]:.2f} / {r[7]:.2f} deg | {r[8]:.3f}')
