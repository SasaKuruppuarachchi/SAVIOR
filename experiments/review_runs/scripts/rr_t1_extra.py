#!/usr/bin/env python3
"""rr_t1_extra.py : post-freeze descriptive t1 comparisons (tuning split only): SAVIOR / Y-Cls vs the t1-tuned OV-chi2 (x0.25).
Same estimators as rr_analyze.py. -> tables/ate_t1_extra.md"""
import json, math, sys
import numpy as np
from scipy import stats
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/stats_v3/scripts')
from stats3_core import boot_two_stage, signflip  # noqa: E402
A = json.load(open('/home/sasa/workspace/savior_ws/results/review_runs/tables/ate_t1.json'))['values']
G = {'L0+L1': ('L0', 'L1'), 'L2+L3': ('L2', 'L3'), 'all': ('L0', 'L1', 'L2', 'L3')}
L = ['# t1 (tuning split), descriptive: vs OV-chi2 x0.25 (selected on these data)\n', '| comparison | group | run level gm [CI], Wilcoxon p, W/L | seq level [two-stage CI], sign-flip p |', '|---|---|---|---|']
for m in ('sens_fix1', 'yolo_naive', 'p7_nb'):
    for g, lv in G.items():
        X = {}
        for s, d in A.items():
            if s.rsplit('_', 1)[1] in lv:
                a, b = d[m], d['ovchi_025']
                X[s] = np.array([math.log(min(float(a[i]), 10) / min(float(b[i]), 10)) for i in a if i in b])
        x = np.concatenate(list(X.values()))
        ci = np.percentile(np.random.default_rng(0).choice(x, (20000, x.size)).mean(axis=1), [2.5, 97.5])
        sm = np.array([v.mean() for v in X.values()]); bt = np.percentile(boot_two_stage(X), [2.5, 97.5])
        pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731
        L.append(f"| {m} vs ovchi_025 | {g} | {pc(x.mean()):+.1f} % [{pc(ci[0]):+.0f}, {pc(ci[1]):+.0f}] p={stats.wilcoxon(x).pvalue:.2g} "
                 f"{(x < 0).sum()}/{(x > 0).sum()} | {pc(sm.mean()):+.1f} % [{pc(bt[0]):+.0f}, {pc(bt[1]):+.0f}] sf={signflip(sm)[0]:.2g} |")
open('/home/sasa/workspace/savior_ws/results/review_runs/tables/ate_t1_extra.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
