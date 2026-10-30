#!/usr/bin/env python3
"""P6 node timing per stage (online savior_stats.jsonl of every run): median / p90 / p99 per method and per level
(L0+L1 vs L2+L3), plus instances per frame. Desktop numbers under load (other GPU jobs + ~14 parallel runs).

python3 timing.py -> tables/timing.md, tables/timing.csv
"""
import csv
import glob
import json
from collections import defaultdict

import numpy as np

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
STAGES = ['convert', 'segment', 'depth', 'motion', 'gating', 'tracking', 'extension', 'compose', 'total', 'node_total']
acc = defaultdict(lambda: defaultdict(list))
inst = defaultdict(list)
for f in sorted(glob.glob(f'{R}/*_t1_L*/*/run_*/savior_stats.jsonl')):
    seq, m = f.split('/')[-4], f.split('/')[-3]
    if m.startswith('diag_'):
        continue
    grp = 'L0+L1' if seq[-2:] in ('L0', 'L1') else 'L2+L3'
    for ln in open(f):
        try:
            x = json.loads(ln)
        except ValueError:
            continue
        t = x.get('timings_ms', {})
        for k in STAGES:
            if k in t:
                acc[(m, grp)][k].append(t[k])
                acc[(m, 'all')][k].append(t[k])
        inst[(m, grp)].append(x.get('n_instances', 0))
        inst[(m, 'all')].append(x.get('n_instances', 0))
rows = []
for (m, g), d in sorted(acc.items()):
    r = dict(method=m, group=g, frames=len(d.get('total', [])), inst_per_frame=float(np.mean(inst[(m, g)])))
    for k in STAGES:
        v = np.array(d.get(k, []), float)
        r[f'{k}_med'] = float(np.median(v)) if v.size else np.nan
        r[f'{k}_p90'] = float(np.percentile(v, 90)) if v.size else np.nan
        r[f'{k}_p99'] = float(np.percentile(v, 99)) if v.size else np.nan
    rows.append(r)
with open(f'{R}/tables/timing.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
L = ['# savior_node timing per stage [ms], median (p90) over all frames of all online runs; desktop RTX PRO 6000 shared with '
     'other GPU jobs (93-95 % busy) and ~14 parallel runs; node_total = convert + segment + pipeline total\n',
     '| method | group | frames | inst/frame | ' + ' | '.join(STAGES) + ' | node_total p99 |', '|---|---|--:|--:|' + '--:|' * (len(STAGES) + 1)]
for r in rows:
    L.append(f"| {r['method']} | {r['group']} | {r['frames']} | {r['inst_per_frame']:.1f} | " +
             ' | '.join('-' if np.isnan(r[f'{k}_med']) else f"{r[f'{k}_med']:.1f} ({r[f'{k}_p90']:.1f})" for k in STAGES) +
             f" | {r['node_total_p99']:.1f} |")
open(f'{R}/tables/timing.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
