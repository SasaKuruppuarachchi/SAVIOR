#!/usr/bin/env python3
"""rr_spill_validate.py <spill dir> : compare the offline replay's per-frame (n_roots, n_promoted, n_held) with the online
/savior/stats of the back-end v2 t1 run_01 (offset 0.0 = bag start) of the same method, record for record."""
import glob, gzip, json, os, sys
WS = '/home/sasa/workspace/savior_ws'
tot = same = 0
out = []
for f in sorted(glob.glob(f'{sys.argv[1]}/*/*.json')):
    d = json.load(open(f))
    m = d['variant']
    on = f'{WS}/results/backend_v2/runs/{d["seq"]}/{m}/run_01/savior_stats.jsonl.gz'
    if not os.path.isfile(on):
        on = f'{WS}/results/review_runs/runs/t1/{d["seq"]}/{m}/run_01/savior_stats.jsonl.gz'
    if not os.path.isfile(on):
        out.append(f'{d["seq"]} {m}: no online run'); continue
    O = {}
    for ln in gzip.open(on, 'rt'):
        r = json.loads(ln)
        O[round(r['stamp']['t'], 3)] = (r['n_roots'], r['n_promoted'], r['n_held'])
    n = s = 0
    for t, a, b, c in d['per_frame']:
        if t in O:
            n += 1; s += O[t] == (a, b, c)
    tot += n; same += s
    out.append(f'{d["seq"]} {m}: {s}/{n} frames identical (online {len(O)}, offline {len(d["per_frame"])})')
print('\n'.join(out)); print(f'TOTAL {same}/{tot}')
