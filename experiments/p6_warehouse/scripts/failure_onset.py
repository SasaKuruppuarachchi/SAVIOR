#!/usr/bin/env python3
"""Failure anatomy: for every run with ATE > FAIL_M, the onset time of divergence (first time the 1 s-smoothed estimated
speed exceeds 2.5 m/s; the true speed never exceeds 1.1 m/s) or, if it never diverges, "drift" (e.g. the hall L3
"stand still" failure). Bag time is relative to the first frame (hover 0-3 s, take-off at 3 s, static init ~3.6 s).
-> tables/failure_onset.md"""
import glob
import math
import os
from collections import defaultdict

import numpy as np
import yaml

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
FAIL_M = float(os.environ.get('FAIL_M', '2.0'))
rows = defaultdict(list)
for fn in sorted(glob.glob(f'{R}/*_t1_L*/*/eval/eval_summary.yaml')):
    seq, m = fn.split('/')[-4], fn.split('/')[-3]
    if m.startswith('diag_'):
        continue
    for t in yaml.safe_load(open(fn))['trials']:
        ate = t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf
        if ate <= FAIL_M:
            continue
        a = np.loadtxt(t['est_file'])
        tt = a[:, 0] - 1700000000.0
        v = np.linalg.norm(np.diff(a[:, 1:4], axis=0), axis=1) / np.maximum(np.diff(tt), 1e-3)
        vs = np.convolve(v, np.ones(20) / 20, mode='same')
        bad = np.flatnonzero(vs > 2.5)
        rows[(seq, m)].append((t['name'], ate, round(float(tt[bad[0] + 1]), 1) if bad.size else None))
L = [f'# failure anatomy (ATE > {FAIL_M} m): divergence onset [s from bag start] (speed > 2.5 m/s), "drift" = failed without '
     'diverging\n', '| seq | method | failed runs | onsets (run: ATE m @ onset s) |', '|---|---|--:|---|']
for (s, m), v in sorted(rows.items()):
    L.append(f'| {s} | {m} | {len(v)} | ' + ', '.join(f"{n[-2:]}: {a:.3g} @ {o if o is not None else 'drift'}" for n, a, o in v) + ' |')
open(f'{R}/tables/failure_onset.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
