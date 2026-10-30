#!/usr/bin/env python3
"""coverage_summary.py : t3 coverage table (tools/coverage_report.py output) summarised per level and environment,
next to t1 (data/warehouse/coverage_table.csv) and t2 (coverage_table_heldout.csv). -> tables/coverage_summary.md"""
import csv
import numpy as np
WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
K = [('cov_mean', 100, 'moving cov. mean [%]'), ('cov_p90', 100, 'p90 [%]'), ('frac_gt5', 100, 'frames > 5 % [%]'),
     ('feat_share_mean', 100, 'FAST features on movers [%]'), ('person_cov_mean', 100, 'person cov. [%]'),
     ('moving_instances', 1, 'moving instances'), ('duration_s', 1, 'duration [s]'), ('path_m', 1, 'path [m]')]


def load(f):
    return list(csv.DictReader(open(f)))


def agg(rows, sel):
    r = [x for x in rows if sel(x['sequence'])]
    return len(r), {k: (np.mean([float(x[k]) for x in r]) * s, np.min([float(x[k]) for x in r]) * s,
                        np.max([float(x[k]) for x in r]) * s) for k, s, _ in K} if r else {}


sets = {'t1': load(f'{WS}/data/warehouse/coverage_table.csv'), 't2': load(f'{WS}/data/warehouse/coverage_table_heldout.csv'),
        't3': load(f'{T}/tables/coverage_t3.csv')}
L = ['| split | env | level | n seq | ' + ' | '.join(n for _, _, n in K) + ' |', '|---|---|---|---|' + '---|' * len(K)]
for name, rows in sets.items():
    envs = ['all'] + (['fw', 'sw', 'ms', 'wx'] if name == 't3' else [])
    for e in envs:
        for lv in ('L0', 'L1', 'L2', 'L3'):
            n, a = agg(rows, lambda s: s.endswith(lv) and (e == 'all' or s.startswith(e)))
            if n:
                L.append(f'| {name} | {e} | {lv} | {n} | ' + ' | '.join(
                    f'{a[k][0]:.1f} ({a[k][1]:.1f}-{a[k][2]:.1f})' if k not in ('duration_s', 'path_m', 'moving_instances')
                    else f'{a[k][0]:.0f} ({a[k][1]:.0f}-{a[k][2]:.0f})' for k, _, _ in K) + ' |')
open(f'{T}/tables/coverage_summary.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
