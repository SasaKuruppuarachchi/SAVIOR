#!/usr/bin/env python3
"""m3b_merge.py : controlled-comparison table = M3b SOTA baselines (results/sota/tables/merge_<ds>.json) + M2b held-out methods
(results/m2b_heldout/runs/<seq>/<method>/eval/eval_summary.yaml, read directly so it works while M2b is in progress).
Same metric (posyaw ATE RMSE, full sequence), same 10 offsets, same failure thresholds (VIODE 1 m, warehouse 2 m).
-> results/sota/tables/controlled_<viode|warehouse_t2>.{md,csv}. Columns whose runs are not (yet) available print '-' / (n=k)."""
import csv, json, math, os
import numpy as np, yaml

WS = '/home/sasa/workspace/savior_ws'
T = WS + '/results/sota/tables'
M2B = WS + '/results/m2b_heldout/runs'
COLS = [('openvins', 'OpenVINS'), ('vins_fusion', 'VINS-Fusion'), ('dynavins', 'DynaVINS'), ('orbslam3', 'ORB-SLAM3'),
        ('yolo_naive', 'Y-Cls'), ('sens_fix1', 'SAVIOR'), ('savior_edge', 'SAVIOR-edge'), ('p7_nb', 'SAVIOR-adaptive'),
        ('oracle_moving_ext', 'O-Dyn+B'), ('oracle_class_ext', 'O-Cls+B')]
SOTA = {'vins_fusion', 'dynavins', 'orbslam3'}


def m2b(seq, m):
    f = f'{M2B}/{seq}/{m}/eval/eval_summary.yaml'
    if not os.path.isfile(f):
        return {}
    out = {}
    for t in yaml.safe_load(open(f)).get('trials', []):
        out[int(t['name'].split('_')[1])] = t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf
    return out


for tag, groups in (('viode', ['none', 'low', 'mid', 'high', 'all']), ('warehouse_t2', ['L0', 'L1', 'L2', 'L3', 'L0+L1', 'L2+L3', 'all'])):
    fn = f'{T}/merge_{tag}.json'
    if not os.path.isfile(fn):
        continue
    J = json.load(open(fn))
    FAIL = J['fail_m']
    seqs = list(J['values'])
    V = {s: {} for s in seqs}
    for s in seqs:
        for m, _ in COLS:
            V[s][m] = ({int(k): float(v) for k, v in J['values'][s][m].items()} if m in SOTA else m2b(s, m))
    L = [f'# Controlled comparison, {tag} ({len(seqs)} sequences x 10 late-start offsets; posyaw ATE RMSE [m], median; [n] = failures > {FAIL:g} m)\n',
         'SOTA = M3b (results/sota); OpenVINS / Y-Cls / SAVIOR / SAVIOR-edge / oracles = M2b held-out runs (results/m2b_heldout/runs), '
         'same offsets and evaluation. (n=k) = only k of 10 runs available.\n',
         '| seq | ' + ' | '.join(l for _, l in COLS) + ' |', '|---|' + '--:|' * len(COLS)]
    rows = []
    for s in seqs:
        cells = []
        for m, l in COLS:
            v = list(V[s][m].values())
            if not v:
                cells.append('-'); continue
            k = sum(not x <= FAIL for x in v); md = float(np.median(np.minimum(v, 1e9)))
            rows.append(dict(seq=s, method=m, label=l, n=len(v), median_ate_m=md if md < 1e9 else 'inf', failures=k))
            cells.append(('fail' if md >= 1e9 else (f'{md:.3g}' if md >= 10 else f'{md:.3f}')) + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
    L += ['\n## Failures / runs per group\n', '| group | ' + ' | '.join(l for _, l in COLS) + ' |', '|---|' + '--:|' * len(COLS)]
    for g in groups:
        cells = []
        for m, _ in COLS:
            v = [x for s in seqs if g == 'all' or lev(s) in g.split('+') for x in V[s][m].values()]
            cells.append(f'{sum(not x <= FAIL for x in v)}/{len(v)}' if v else '-')
        L.append(f'| {g} | ' + ' | '.join(cells) + ' |')
    open(f'{T}/controlled_{tag}.md', 'w').write('\n'.join(L) + '\n')
    with open(f'{T}/controlled_{tag}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, ['seq', 'method', 'label', 'n', 'median_ate_m', 'failures']); w.writeheader(); w.writerows(rows)
    print('\n'.join(L), '\n')
