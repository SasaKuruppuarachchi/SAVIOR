#!/usr/bin/env python3
"""dm_extra.py : post-hoc descriptive breakdowns (not frozen, not used for any held-out decision):
per-environment geometric-mean ATE change vs DynaVINS (VIODE city_* = no DynaVINS failures; parking_lot) and medians."""
import json, math
import numpy as np
V = '/home/sasa/workspace/savior_ws/results/dynavins_masks'
for d in ('tables', 'tables_t2', 'tables_viode'):
    J = json.load(open(f'{V}/{d}/ate.json')); W = J['values']; cap = 10.0
    print(d, 'median ATE all runs:', {m: round(float(np.median([min(x, 1e4) for s in W for x in W[s][m].values()])), 3) for m in W[next(iter(W))]})
    envs = sorted({s.rsplit('_', 1)[0] for s in W})
    for e in envs:
        out = []
        for m in ('dyna_ycls', 'dyna_savior', 'dyna_odyn', 'dyna_ocls'):
            x = [math.log(min(W[s][m][i], cap) / min(W[s]['dyna_det'][i], cap)) for s in W if s.rsplit('_', 1)[0] == e for i in W[s][m]]
            out.append(f'{m[5:]} {100 * (math.exp(np.mean(x)) - 1):+.1f}%')
        print('  ', e, ', '.join(out))
