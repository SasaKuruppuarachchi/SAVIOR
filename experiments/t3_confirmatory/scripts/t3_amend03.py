#!/usr/bin/env python3
"""t3_amend03.py : AMENDMENT_03 disclosed exploratory family X1-X3 (own Holm family; outside P1-P5 and S1-S14).
  X1 sens_fix1 vs ovchi_best high (L2+L3)   X2 sf1_chibest vs ovchi_best high   X3 ovchi_best vs openvins high
Model = stats_t3.py (frozen module objects reused: load, S3 = stats3_core, groups, cap 10 m, failure 2 m): paired log ratio,
mean over the 5 offsets per sequence, REML random intercept per trajectory, t on mu (df n_traj - 1); sign-flip on trajectory
means; cap sensitivity 2 / 5 / 10 / 50 / excl; failures per method x group with trajectory-cluster bootstrap CIs; per environment.
Also: parameter diff of the run_info.yaml launch commands (ovchi_best vs openvins, sf1_chibest vs sens_fix1, same sequence and
run): the only allowed delta is the two chi2 multipliers (plus output paths / method names).
-> results/t3_confirmatory/tables/amend03.md, amend03.json"""
import glob
import importlib.util
import json
import math
import os
import re

import numpy as np
import yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
spec = importlib.util.spec_from_file_location('stats_t3', f'{T}/scripts/stats_t3.py')
ST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ST)
S3 = ST.S3
X = [('X1', 'sens_fix1', 'ovchi_best', 'high'), ('X2', 'sf1_chibest', 'ovchi_best', 'high'), ('X3', 'ovchi_best', 'openvins', 'high')]
M = ['openvins', 'sens_fix1', 'ovchi_best', 'sf1_chibest']
LAB = dict(ST.LAB, ovchi_best='OpenVINS chi2 x0.25', sf1_chibest='SAVIOR + chi2 x0.25')
fp = lambda p: '-' if p is None else (f'{p:.1e}' if p < 1e-3 else f'{p:.3f}')  # noqa: E731
pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def param_diff(seqs):
    out = {}
    for a, b in (('ovchi_best', 'openvins'), ('sf1_chibest', 'sens_fix1')):
        deltas, n = set(), 0
        for s in seqs:
            for ra in sorted(glob.glob(f'{T}/runs/{s}/{a}/run_*/run_info.yaml')):
                rb = ra.replace(f'/{a}/', f'/{b}/')
                if not os.path.isfile(rb):
                    continue
                ca = [str(x).replace(f'/{a}/', '/M/') for x in yaml.safe_load(open(ra))['cmd']]
                cb = [str(x).replace(f'/{b}/', '/M/') for x in yaml.safe_load(open(rb))['cmd']]
                n += 1
                da = {x for x in ca if x not in cb}
                db = {x for x in cb if x not in ca}
                for x, y in zip(sorted(da), sorted(db)):
                    if x.startswith('ov_set:=') and y.startswith('ov_set:='):
                        ka, kb = set(x[8:].split()), set(y[8:].split())
                        deltas.add(('ov_set', ' '.join(sorted(ka - kb)), ' '.join(sorted(kb - ka))))
                    else:
                        deltas.add((x, y))
                if len(da) != len(db):
                    deltas.add(('unpaired', ' '.join(sorted(da)), ' '.join(sorted(db))))
        allowed = {('ov_set', 'up_msckf_chi2_multipler=0.25 up_slam_chi2_multipler=0.25', '')}
        out[f'{a} vs {b}'] = dict(pairs=n, deltas=sorted(map(list, deltas)), ok=bool(n) and deltas <= allowed)
    return out


def main():
    ex = set()
    if os.path.isfile(f'{T}/EXCLUSIONS.yaml'):
        ex = {e['trajectory'] for e in (yaml.safe_load(open(f'{T}/EXCLUSIONS.yaml')) or {}).get('excluded', [])}
    trajs = [t['id'] for t in ST.DESIGN['dataset']['trajectories'] if t['id'] not in ex]
    seqs = [f'{t}_t3_L{k}' for t in trajs for k in ST.DESIGN['dataset']['levels']]
    V = {m: {s: ST.load(f'{T}/runs/{s}/{m}/eval/eval_summary.yaml') for s in seqs} for m in M}
    IDX, CAP, FAIL, GROUPS, lev, traj_of = ST.IDX, ST.CAP, ST.FAIL, ST.GROUPS, ST.lev, ST.traj_of
    missing = sum(1 for m in M for s in seqs for i in IDX if i not in V[m][s])

    def signflip(m):
        if m.size <= 20:
            return S3.signflip(m)[0]
        rng = np.random.default_rng(0)
        sg = rng.choice([-1, 1], (2 ** 20, m.size))
        return float(np.mean(np.abs((sg * m).mean(1)) >= abs(m.mean()) - 1e-12))

    def analyse(a, b, g, cap=CAP, tsel=None):
        Xd = {}
        for s in seqs:
            if lev(s) not in GROUPS[g] or (tsel and traj_of(s) not in tsel):
                continue
            x = [S3.lr(V[a][s][i], V[b][s][i], cap, FAIL) for i in IDX if i in V[a][s] and i in V[b][s]]
            x = [v for v in x if v is not None]
            if x:
                Xd.setdefault(traj_of(s), []).append(float(np.mean(x)))
        Xd = {k: np.array(v) for k, v in Xd.items()}
        if len(Xd) < 2:
            return None
        tm = np.array([Xd[k].mean() for k in Xd])
        l = S3.reml_ri(Xd)
        q = stats.t.ppf(0.975, l['df'])
        return dict(a=a, b=b, group=g, cap=str(cap), n_traj=len(Xd), n_seq=int(sum(v.size for v in Xd.values())), est=pc(l['mu']),
                    ci95=[pc(l['mu'] - q * l['se']), pc(l['mu'] + q * l['se'])], p=l['p'], p_signflip=signflip(tm),
                    traj_better=int((tm < -1e-12).sum()), traj_worse=int((tm > 1e-12).sum()))

    res = dict(missing_runs=missing, param_diff=param_diff(seqs))
    xs = [dict(id=i, **r) for i, a, b, g in X for r in [analyse(a, b, g)] if r]
    for r, h in zip(xs, S3.holm([r['p'] for r in xs]) if xs else []):
        r['p_holm_x'] = float(h)
    res['X'] = xs
    res['cap_sensitivity'] = [dict(id=i, **{k: v for k, v in (analyse(a, b, g, c) or {}).items() if k in ('cap', 'est', 'ci95', 'p', 'n_traj')})
                              for i, a, b, g in X for c in ST.CAPS]
    res['per_environment'] = [dict(id=i, env=e, **r) for i, a, b, g in X for e in ('fw', 'sw', 'ms', 'wx')
                              for r in [analyse(a, b, g, tsel={t for t in trajs if t.startswith(e)})] if r]
    fl = []
    for m in M:
        for g in ('static', 'low', 'high', 'all'):
            per = {}
            for s in seqs:
                if lev(s) in GROUPS[g]:
                    f, n = per.get(traj_of(s), (0, 0))
                    per[traj_of(s)] = (f + sum(V[m][s][i] > FAIL for i in IDX if i in V[m][s]), n + sum(i in V[m][s] for i in IDX))
            f = np.array([v[0] for v in per.values()], float)
            n = np.array([v[1] for v in per.values()], float)
            if n.sum() == 0:
                continue
            rng = np.random.default_rng(0)
            si = rng.integers(0, f.size, (20000, f.size))
            r = f[si].sum(1) / np.maximum(n[si].sum(1), 1)
            fl.append(dict(method=m, group=g, fails=int(f.sum()), runs=int(n.sum()), rate=float(f.sum() / n.sum()),
                           ci=[float(x) for x in np.percentile(r, [2.5, 97.5])]))
    res['failures'] = fl
    json.dump(res, open(f'{T}/tables/amend03.json', 'w'), indent=1, default=str)
    L = ['# AMENDMENT_03: X1-X3 (exploratory, own Holm family; outside P1-P5 and S1-S14), cap 10 m, trajectory LMM\n',
         f'missing runs (4 methods): {missing}\n', '## Parameter diff (run_info launch commands, same sequence and run)\n']
    for k, v in res['param_diff'].items():
        L.append(f"- {k}: {v['pairs']} run pairs, deltas {v['deltas']}, only the two chi2 multipliers: {v['ok']}")
    L += ['\n| id | comparison | group | estimate [95 % CI] | p | Holm p (X family) | sign-flip p | traj better/worse | n traj |',
          '|---|---|---|---|---|---|---|---|---|']
    for r in xs:
        L.append(f"| {r['id']} | {LAB[r['a']]} vs {LAB[r['b']]} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | "
                 f"{fp(r['p'])} | {fp(r['p_holm_x'])} | {fp(r['p_signflip'])} | {r['traj_better']}/{r['traj_worse']} | {r['n_traj']} |")
    L += ['\n## Cap sensitivity\n', '| id | cap | estimate [95 % CI] | p | n traj |', '|---|---|---|---|---|']
    L += [f"| {r['id']} | {r['cap']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['n_traj']} |"
          for r in res['cap_sensitivity'] if 'est' in r]
    L += ['\n## Per environment (descriptive)\n', '| id | env | estimate [95 % CI] | p | traj better/worse |', '|---|---|---|---|---|']
    L += [f"| {r['id']} | {r['env']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['traj_better']}/{r['traj_worse']} |"
          for r in res['per_environment']]
    L += ['\n## Failures (ATE > 2 m)\n', '| method | group | failures / runs | rate [cluster 95 % CI] |', '|---|---|---|---|']
    L += [f"| {LAB[f['method']]} | {f['group']} | {f['fails']} / {f['runs']} | {100 * f['rate']:.1f} % [{100 * f['ci'][0]:.1f}, {100 * f['ci'][1]:.1f}] |"
          for f in fl]
    open(f'{T}/tables/amend03.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
