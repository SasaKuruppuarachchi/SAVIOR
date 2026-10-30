#!/usr/bin/env python3
"""t3_amend04.py : AMENDMENT_04 disclosed exploratory family Y1-Y4 (own Holm family; outside P1-P5, S1-S14 and X1-X3).
  Y1 sf1_nis vs sens_fix1 high   Y2 sf1_nis vs ovchi_best high   Y3 sf1_nis vs ov_nis high
  Y4 sf1_nis vs openvins static (L0): equivalence as P5 (90 % t interval inside [-10, +10] %; TOST p = max of the two
     one-sided t tests, df n_traj - 1; Holm over the Y1-Y3 two-sided p and the Y4 TOST p).
  Descriptive (no test family): savior_sg vs sens_fix1 at high / low / static.
Written from t3_amend03.py (same model / code); the parameter diff allows only the FREEZE.yaml deltas (ov_set keys of
ovset_add, pset key compose.movable_static_value=64 for savior_sg) and checks INSTALL = results/semantic_gate/install in the
runs' t3_settings files.
Model = stats_t3.py (frozen module objects reused: load, S3 = stats3_core, groups, cap 10 m, failure 2 m): paired log ratio,
mean over the 5 offsets per sequence, REML random intercept per trajectory, t on mu (df n_traj - 1); sign-flip on trajectory
means; cap sensitivity 2 / 5 / 10 / 50 / excl; failures per method x group with trajectory-cluster bootstrap CIs; per environment.
Also: parameter diff of the run_info.yaml launch commands (ovchi_best vs openvins, sf1_chibest vs sens_fix1, same sequence and
run): only the FREEZE.yaml deltas are allowed (plus output paths / method names).
-> results/t3_confirmatory/tables/amend04.md, amend04.json"""
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
X = [('Y1', 'sf1_nis', 'sens_fix1', 'high'), ('Y2', 'sf1_nis', 'ovchi_best', 'high'), ('Y3', 'sf1_nis', 'ov_nis', 'high'),
     ('Y4', 'sf1_nis', 'openvins', 'static')]
DESC = [('D1', 'savior_sg', 'sens_fix1', g) for g in ('high', 'low', 'static')]
M = ['openvins', 'sens_fix1', 'ovchi_best', 'sf1_nis', 'ov_nis', 'savior_sg']
LAB = dict(ST.LAB, ovchi_best='OpenVINS chi2 x0.25', sf1_nis='SAVIOR + NIS gate', ov_nis='OpenVINS + NIS gate', savior_sg='SAVIOR-SG')
fp = lambda p: '-' if p is None else (f'{p:.1e}' if p < 1e-3 else f'{p:.3f}')  # noqa: E731
pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


ALLOWED = {('sf1_nis', 'sens_fix1'): {('ov_set', 'savior_nis_gate=true', '')},
           ('ov_nis', 'openvins'): {('ov_set', 'savior_nis_gate=true', '')},
           ('savior_sg', 'sens_fix1'): {('ov_set', 'savior_semantic_gate=true savior_sg_keep_band=false savior_sg_mult_band=0.25 savior_sg_mult_static=0.25', ''),
                                        ('pset', 'compose.movable_static_value=64', '')}}


def param_diff(seqs):
    out = {}
    for (a, b), allowed in ALLOWED.items():
        deltas, n, inst = set(), 0, set()
        for s in seqs:
            for f in glob.glob(f'{T}/runs/{s}/{a}/t3_settings_*.txt'):
                inst |= {l.strip() for l in open(f) if l.startswith('INSTALL=')}
            for ra in sorted(glob.glob(f'{T}/runs/{s}/{a}/run_*/run_info.yaml')):
                rb = ra.replace(f'/{a}/', f'/{b}/')
                if not os.path.isfile(rb):
                    continue
                ca = [str(x).replace(f'/{a}/', '/M/') for x in yaml.safe_load(open(ra))['cmd']]
                cb = [str(x).replace(f'/{b}/', '/M/') for x in yaml.safe_load(open(rb))['cmd']]
                n += 1
                da = sorted(x for x in ca if x not in cb)
                db = sorted(x for x in cb if x not in ca)
                for x, y in zip(da, db):
                    k = x.split(':=')[0]
                    if k in ('ov_set', 'pset') and y.startswith(k + ':='):
                        ka, kb = set(x[len(k) + 2:].split()), set(y[len(k) + 2:].split())
                        deltas.add((k, ' '.join(sorted(ka - kb)), ' '.join(sorted(kb - ka))))
                    else:
                        deltas.add((x, y))
                if len(da) != len(db):
                    deltas.add(('unpaired', ' '.join(da), ' '.join(db)))
        ok = bool(n) and deltas <= allowed and inst == {f'INSTALL={WS}/results/semantic_gate/install'}
        out[f'{a} vs {b}'] = dict(pairs=n, deltas=sorted(map(list, deltas)), install=sorted(inst), ok=ok)
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
        q90 = stats.t.ppf(0.95, l['df'])
        lo, hi = (math.log(1 + x / 100) for x in ST.AP['equivalence_margin_pct'])
        p_tost = max(stats.t.sf((l['mu'] - lo) / l['se'], l['df']), stats.t.cdf((l['mu'] - hi) / l['se'], l['df']))
        return dict(a=a, b=b, group=g, cap=str(cap), n_traj=len(Xd), n_seq=int(sum(v.size for v in Xd.values())), est=pc(l['mu']),
                    ci95=[pc(l['mu'] - q * l['se']), pc(l['mu'] + q * l['se'])], p=l['p'], p_signflip=signflip(tm),
                    ci90=[pc(l['mu'] - q90 * l['se']), pc(l['mu'] + q90 * l['se'])], p_tost=float(p_tost),
                    traj_better=int((tm < -1e-12).sum()), traj_worse=int((tm > 1e-12).sum()))

    res = dict(missing_runs=missing, param_diff=param_diff(seqs))
    xs = [dict(id=i, **r) for i, a, b, g in X for r in [analyse(a, b, g)] if r]
    for r in xs:
        if r['id'] == 'Y4':   # TOST on the log scale against the P5 margins
            lo, hi = ST.AP['equivalence_margin_pct']
            q90 = r['ci90']
            r['equivalent'] = bool(q90[0] > lo and q90[1] < hi)
            r['p_test'] = r['p_tost']
        else:
            r['p_test'] = r['p']
    for r, h in zip(xs, S3.holm([r['p_test'] for r in xs]) if xs else []):
        r['p_holm_x'] = float(h)
    res['descriptive'] = [dict(id=i, **r) for i, a, b, g in DESC for r in [analyse(a, b, g)] if r]
    res['X'] = xs
    res['cap_sensitivity'] = [dict(id=i, **{k: v for k, v in (analyse(a, b, g, c) or {}).items() if k in ('cap', 'est', 'ci95', 'p', 'n_traj')})
                              for i, a, b, g in X + DESC for c in ST.CAPS]
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
    json.dump(res, open(f'{T}/tables/amend04.json', 'w'), indent=1, default=str)
    L = ['# AMENDMENT_04: Y1-Y4 (exploratory, own Holm family; outside P1-P5, S1-S14, X1-X3), cap 10 m, trajectory LMM\n',
         f'missing runs ({len(M)} methods): {missing}\n', '## Parameter diff (run_info launch commands, same sequence and run)\n']
    for k, v in res['param_diff'].items():
        L.append(f"- {k}: {v['pairs']} run pairs, deltas {v['deltas']}, install {v['install']}, only the FREEZE.yaml deltas: {v['ok']}")
    L += ['\n| id | comparison | group | estimate [95 % CI] | 90 % CI | p (two-sided; Y4: TOST) | Holm p (Y family) | sign-flip p | traj better/worse | n traj |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for r in xs + res['descriptive']:
        L.append(f"| {r['id']} | {LAB[r['a']]} vs {LAB[r['b']]} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | "
                 f"[{r['ci90'][0]:+.1f}, {r['ci90'][1]:+.1f}] | {fp(r.get('p_test', r['p']))} | {fp(r.get('p_holm_x'))} | {fp(r['p_signflip'])} | "
                 f"{r['traj_better']}/{r['traj_worse']} | {r['n_traj']} |")
    L.append('\nD1 rows (savior_sg vs sens_fix1) are descriptive, not in the Y Holm family. Y4 equivalent (90 % CI inside the P5 margins): '
             + str([r.get('equivalent') for r in xs if r['id'] == 'Y4']))
    L += ['\n## Cap sensitivity\n', '| id | cap | estimate [95 % CI] | p | n traj |', '|---|---|---|---|---|']
    L += [f"| {r['id']} | {r['cap']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['n_traj']} |"
          for r in res['cap_sensitivity'] if 'est' in r]
    L += ['\n## Per environment (descriptive)\n', '| id | env | estimate [95 % CI] | p | traj better/worse |', '|---|---|---|---|---|']
    L += [f"| {r['id']} | {r['env']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['traj_better']}/{r['traj_worse']} |"
          for r in res['per_environment']]
    L += ['\n## Failures (ATE > 2 m)\n', '| method | group | failures / runs | rate [cluster 95 % CI] |', '|---|---|---|---|']
    L += [f"| {LAB[f['method']]} | {f['group']} | {f['fails']} / {f['runs']} | {100 * f['rate']:.1f} % [{100 * f['ci'][0]:.1f}, {100 * f['ci'][1]:.1f}] |"
          for f in fl]
    open(f'{T}/tables/amend04.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
