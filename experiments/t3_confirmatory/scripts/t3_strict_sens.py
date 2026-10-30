#!/usr/bin/env python3
"""t3_strict_sens.py : AMENDMENT_05 sensitivity analysis. Every primary (P1-P5), secondary (S1-S14), AMENDMENT_03 (X1-X3) and
AMENDMENT_04 (Y1-Y4, D1) comparison recomputed on STRICTLY complete runs only (frames audit ok_strict == 1, i.e. +-0 frames;
runs that are valid only by the AMENDMENT_05 tail clause are dropped, pairwise: a paired offset is used only if both runs are
strict). Model = stats_t3.py (frozen module objects; the same per-comparison code as stats_t3.main().analyse, cap 10 m).
Input: results/t3_confirmatory/tables/frames_audit.csv (written by t3_frames_audit.py with tag '' over all three roots).
-> results/t3_confirmatory/tables/strict_sensitivity.md / .json"""
import csv
import importlib.util
import json
import math

import numpy as np
import yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
spec = importlib.util.spec_from_file_location('stats_t3', f'{T}/scripts/stats_t3.py')
ST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ST)
S3 = ST.S3
EXTRA_OV = ['ovchi_best', 'sf1_chibest', 'sf1_nis', 'ov_nis', 'savior_sg']
COMPS = ([(h[0], h[1], h[2], h[3]) for h in ST.PRIMARY] + list(ST.SECONDARY) +
         [('X1', 'sens_fix1', 'ovchi_best', 'high'), ('X2', 'sf1_chibest', 'ovchi_best', 'high'), ('X3', 'ovchi_best', 'openvins', 'high'),
          ('Y1', 'sf1_nis', 'sens_fix1', 'high'), ('Y2', 'sf1_nis', 'ovchi_best', 'high'), ('Y3', 'sf1_nis', 'ov_nis', 'high'),
          ('Y4', 'sf1_nis', 'openvins', 'static'), ('D1h', 'savior_sg', 'sens_fix1', 'high'), ('D1l', 'savior_sg', 'sens_fix1', 'low'),
          ('D1s', 'savior_sg', 'sens_fix1', 'static')])
pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731
fp = lambda p: '-' if p is None else (f'{p:.1e}' if p < 1e-3 else f'{p:.3f}')  # noqa: E731


def main():
    strict = {}
    for r in csv.DictReader(open(f'{T}/tables/frames_audit.csv')):
        m = r['method']
        strict[(r['seq'], m, int(r['run'].split('_')[1]))] = r['ok_strict'] == '1'
    trajs = [t['id'] for t in ST.DESIGN['dataset']['trajectories']]
    seqs = [f'{t}_t3_L{k}' for t in trajs for k in ST.DESIGN['dataset']['levels']]
    V = {m: {s: ST.load(f'{T}/runs/{s}/{m}/eval/eval_summary.yaml') for s in seqs} for m in ST.OV + EXTRA_OV}
    V.update({m: {s: ST.load(f'{T}/vins_runs/warehouse_{s}/{m}/eval_posyaw/eval_summary.yaml') for s in seqs} for m in ST.VINS})
    dropped = {}
    for m in V:
        for s in seqs:
            for i in list(V[m][s]):
                if not strict.get((s, m, i), False):
                    del V[m][s][i]
                    dropped[m] = dropped.get(m, 0) + 1
    IDX, CAP, FAIL, GROUPS, lev, traj_of = ST.IDX, ST.CAP, ST.FAIL, ST.GROUPS, ST.lev, ST.traj_of

    def analyse(a, b, g):
        X = {}
        for s in seqs:
            if lev(s) not in GROUPS[g]:
                continue
            x = [S3.lr(V[a][s][i], V[b][s][i], CAP, FAIL) for i in IDX if i in V[a][s] and i in V[b][s]]
            x = [v for v in x if v is not None]
            if x:
                X.setdefault(traj_of(s), []).append(float(np.mean(x)))
        X = {k: np.array(v) for k, v in X.items()}
        if len(X) < 2:
            return None
        l = S3.reml_ri(X)
        q, q90 = stats.t.ppf(0.975, l['df']), stats.t.ppf(0.95, l['df'])
        npairs = sum(1 for s in seqs if lev(s) in GROUPS[g] for i in IDX if i in V[a][s] and i in V[b][s])
        return dict(a=a, b=b, group=g, n_traj=len(X), n_pairs=npairs, est=pc(l['mu']), ci95=[pc(l['mu'] - q * l['se']), pc(l['mu'] + q * l['se'])],
                    ci90=[pc(l['mu'] - q90 * l['se']), pc(l['mu'] + q90 * l['se'])], p=l['p'])

    res = dict(dropped_runs=dropped, comparisons=[dict(id=i, **r) for i, a, b, g in COMPS for r in [analyse(a, b, g)] if r])
    json.dump(res, open(f'{T}/tables/strict_sensitivity.json', 'w'), indent=1)
    L = ['# Sensitivity: strictly complete runs only (AMENDMENT_05), cap 10 m, trajectory LMM; raw p, no multiplicity adjustment\n',
         f'runs dropped (not strictly complete, per method): {dropped}\n',
         '| id | comparison | group | estimate [95 % CI] | 90 % CI | p | n traj | paired runs |', '|---|---|---|---|---|---|---|---|']
    for r in res['comparisons']:
        L.append(f"| {r['id']} | {r['a']} vs {r['b']} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | "
                 f"[{r['ci90'][0]:+.1f}, {r['ci90'][1]:+.1f}] | {fp(r['p'])} | {r['n_traj']} | {r['n_pairs']} |")
    open(f'{T}/tables/strict_sensitivity.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
