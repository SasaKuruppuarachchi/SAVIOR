#!/usr/bin/env python3
"""stats_t3.py : PRE-REGISTERED analysis of the t3 confirmatory split (results/t3_confirmatory/DESIGN.yaml, analysis_plan).

Same statistical code as results/stats_v3/scripts/stats3_core.py (imported: reml_ri, boot_one_stage, boot_two_stage,
signflip, signtest, holm, lr). Unit of inference = TRAJECTORY (one seed = one static layout + camera trajectory + IMU
noise; its levels are within-trajectory conditions, its start offsets within-sequence repeats):
  y_s  = mean over the 5 offsets of log(min(ATE_A, cap) / min(ATE_B, cap))          (per sequence s)
  model: y_s = mu + b_traj + e_s (REML random intercept per trajectory, stats3_core.reml_ri; t test on mu, df = n_traj-1)
  estimate exp(mu) - 1; 95 % t interval; sensitivity: one-stage cluster bootstrap and exact sign-flip test on the
  trajectory means (2^n_traj, Monte Carlo above 2^20), caps 2 / 5 / 50 m and failures excluded.
Primary (fixed-sequence gatekeeping, each two-sided alpha 0.05, stop at the first non-rejection):
  P1 O-Dyn+B < O-Cls+B at L2+L3   P2 SAVIOR < Y-Cls at L2+L3   P3 SAVIOR < Y-Cls at L0+L1   P4 SAVIOR < OpenVINS at L2+L3
  P5 SAVIOR vs OpenVINS at L0: equivalence, 90 % t interval of exp(mu) inside [0.90, 1.10] (TOST, alpha 0.05)
Secondary (Holm over the secondary family, cap 10): see SECONDARY; failure rates (ATE > 2 m) per method x group with
trajectory-cluster bootstrap CIs and paired failure differences (sign-flip on trajectory differences); non-failed accuracy.
Inputs: results/t3_confirmatory/runs/<seq>/<method>/eval/eval_summary.yaml (OpenVINS-v2 family),
        results/t3_confirmatory/vins_runs/warehouse_<seq>/<method>/eval_posyaw/eval_summary.yaml (VINS family, DynaVINS),
        EXCLUSIONS.yaml (pre-written rule), tables/invalid.txt (must be empty: invalid runs are re-run, never dropped).
-> results/t3_confirmatory/tables/stats_t3.json, primary.md, secondary.md, failures.md, cap_sensitivity.md
"""
import importlib.util
import itertools
import json
import math
import os

import numpy as np
import yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
OUT = f'{T}/tables'
spec = importlib.util.spec_from_file_location('stats3_core', f'{WS}/results/stats_v3/scripts/stats3_core.py')
S3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S3)          # same code as stats_v3 (its module-level t2 loading is not used here)

DESIGN = yaml.safe_load(open(f'{T}/DESIGN.yaml'))
AP = DESIGN['analysis_plan']
FAIL = float(AP['failure_threshold_m'])
CAP = float(AP['cap_m'])
CAPS = [2.0, 5.0, 10.0, 50.0, 'excl']
IDX = list(range(1, len(AP['offsets_s']) + 1))
GROUPS = {'static': ['L0'], 'low': ['L0', 'L1'], 'high': ['L2', 'L3'], 'all': ['L0', 'L1', 'L2', 'L3']}
OV = ['openvins', 'savior_none', 'yolo_naive', 'sens_fix1', 'oracle_moving_ext', 'oracle_class_ext', 'savior_edge']
VINS = ['vins_fusion', 'vins_zero', 'vins_savior', 'vins_ycls', 'vins_odyn', 'vins_ocls', 'dynavins']
LAB = {'openvins': 'OpenVINS', 'savior_none': 'SAVIOR-none (control)', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR',
       'oracle_moving_ext': 'O-Dyn+B', 'oracle_class_ext': 'O-Cls+B', 'savior_edge': 'SAVIOR-edge',
       'vins_fusion': 'VINS-Fusion', 'vins_zero': 'VINS+zero (control)', 'vins_savior': 'VINS+SAVIOR', 'vins_ycls': 'VINS+Y-Cls',
       'vins_odyn': 'VINS+O-Dyn+B', 'vins_ocls': 'VINS+O-Cls+B', 'dynavins': 'DynaVINS'}
PRIMARY = [(h['id'], h['a'], h['b'], h['group'], h['type']) for h in AP['primary']]
SECONDARY = [(h['id'], h['a'], h['b'], h['group']) for h in AP['secondary']['comparisons']]


def load(fn):
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            out[i] = t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf
    return out


def traj_of(s):
    return s.split('_t3_')[0]


def lev(s):
    return s.rsplit('_', 1)[1]


def main():
    os.makedirs(OUT, exist_ok=True)
    ex = set()
    if os.path.isfile(f'{T}/EXCLUSIONS.yaml'):
        ex = {e['trajectory'] for e in (yaml.safe_load(open(f'{T}/EXCLUSIONS.yaml')) or {}).get('excluded', [])}
    trajs = [t['id'] for t in DESIGN['dataset']['trajectories'] if t['id'] not in ex]
    seqs = [f'{t}_t3_L{k}' for t in trajs for k in DESIGN['dataset']['levels']]
    V = {m: {s: load(f'{T}/runs/{s}/{m}/eval/eval_summary.yaml') for s in seqs} for m in OV}
    V.update({m: {s: load(f'{T}/vins_runs/warehouse_{s}/{m}/eval_posyaw/eval_summary.yaml') for s in seqs} for m in VINS})
    missing = [(m, s, i) for m in V for s in seqs for i in IDX if i not in V[m][s]]
    inv = f'{T}/tables/invalid.txt'
    invalid = [l.strip() for l in open(inv) if l.strip()] if os.path.isfile(inv) else []

    def paired(a, b, group, cap):
        """{traj: array of per-sequence mean log ratios}"""
        X = {}
        for s in seqs:
            if lev(s) not in GROUPS[group]:
                continue
            x = [S3.lr(V[a][s][i], V[b][s][i], cap, FAIL) for i in IDX if i in V[a][s] and i in V[b][s]]
            x = [v for v in x if v is not None]
            if x:
                X.setdefault(traj_of(s), []).append(float(np.mean(x)))
        return {k: np.array(v) for k, v in X.items()}

    def signflip(m):
        k = m.size
        if k <= 20:
            return S3.signflip(m)[0]
        rng = np.random.default_rng(0)
        sg = rng.choice([-1, 1], (2 ** 20, k))
        return float(np.mean(np.abs((sg * m).mean(1)) >= abs(m.mean()) - 1e-12))

    def analyse(a, b, group, cap, alpha_ci=0.05):
        X = paired(a, b, group, cap)
        if len(X) < 2:
            return None
        tm = np.array([X[k].mean() for k in X])
        l = S3.reml_ri(X)
        q = stats.t.ppf(1 - alpha_ci / 2, l['df'])
        q90 = stats.t.ppf(0.95, l['df'])
        b1 = S3.boot_one_stage(tm)
        pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731
        return dict(a=a, b=b, group=group, cap=str(cap), n_traj=len(X), n_seq=int(sum(v.size for v in X.values())),
                    est=pc(l['mu']), ci95=[pc(l['mu'] - q * l['se']), pc(l['mu'] + q * l['se'])],
                    ci90=[pc(l['mu'] - q90 * l['se']), pc(l['mu'] + q90 * l['se'])], p=l['p'], lmm=l,
                    boot_ci=[pc(c) for c in np.percentile(b1, [2.5, 97.5])], p_signflip=signflip(tm),
                    traj_better=int((tm < -1e-12).sum()), traj_worse=int((tm > 1e-12).sum()),
                    per_traj={k: pc(X[k].mean()) for k in X})

    res = {'n_traj': len(trajs), 'excluded': sorted(ex), 'missing_runs': len(missing), 'invalid_runs': invalid}
    # ---------------- primary, gatekeeping
    prim, open_gate = [], True
    for hid, a, b, g, typ in PRIMARY:
        r = analyse(a, b, g, CAP)
        if r is None:
            prim.append(dict(id=hid, status='no data')); open_gate = False; continue
        if typ == 'superiority':
            rej = r['p'] < 0.05 and r['est'] < 0
        else:   # equivalence (TOST): 90 % CI inside the margins
            lo, hi = AP['equivalence_margin_pct']
            rej = r['ci90'][0] > lo and r['ci90'][1] < hi
        r.update(id=hid, type=typ, tested=open_gate, rejected=bool(rej and open_gate))
        if open_gate and not rej:
            open_gate = False
        prim.append(r)
    res['primary'] = prim
    # ---------------- secondary (Holm), cap 10
    sec = [dict(id=i, **r) for i, a, b, g in SECONDARY for r in [analyse(a, b, g, CAP)] if r]
    for r, h in zip(sec, S3.holm([r['p'] for r in sec]) if sec else []):
        r['p_holm'] = float(h)
    res['secondary'] = sec
    # ---------------- cap sensitivity for every primary / secondary comparison
    res['cap_sensitivity'] = [dict(id=i, cap=str(c), **{k: v for k, v in (analyse(a, b, g, c) or {}).items()
                                                      if k in ('est', 'ci95', 'p', 'n_traj')})
                              for i, a, b, g, *_ in PRIMARY + [s + (None,) for s in SECONDARY] for c in CAPS]
    # ---------------- failures
    fails = []
    for m in V:
        for g in GROUPS:
            per = {}
            for s in seqs:
                if lev(s) in GROUPS[g]:
                    t = traj_of(s)
                    f, n = per.get(t, (0, 0))
                    per[t] = (f + sum(V[m][s][i] > FAIL for i in IDX if i in V[m][s]), n + sum(i in V[m][s] for i in IDX))
            f = np.array([v[0] for v in per.values()], float)
            n = np.array([v[1] for v in per.values()], float)
            if n.sum() == 0:
                continue
            rng = np.random.default_rng(0)
            si = rng.integers(0, f.size, (20000, f.size))
            rates = f[si].sum(1) / np.maximum(n[si].sum(1), 1)
            fails.append(dict(method=m, group=g, fails=int(f.sum()), runs=int(n.sum()), rate=float(f.sum() / n.sum()),
                              ci=[float(x) for x in np.percentile(rates, [2.5, 97.5])], n_traj_with_fail=int((f > 0).sum())))
    res['failures'] = fails
    json.dump(res, open(f'{OUT}/stats_t3.json', 'w'), indent=1, default=str)
    # ---------------- markdown
    fp = lambda p: '-' if p is None else (f'{p:.1e}' if p < 1e-3 else f'{p:.3f}')  # noqa: E731
    L = [f'# t3 confirmatory analysis (pre-registered), {len(trajs)} trajectories, cap {CAP:g} m, failure > {FAIL:g} m',
         f'excluded (pre-written rule): {sorted(ex) or "none"}; missing runs: {len(missing)}; invalid runs: {len(invalid)}', '',
         '| hyp | comparison | group | estimate [95 % CI] | 90 % CI | p (LMM, df n-1) | sign-flip p | traj better/worse | tested | rejected |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for r in prim:
        if 'est' not in r:
            L.append(f"| {r['id']} | no data | | | | | | | | |"); continue
        L.append(f"| {r['id']} | {LAB[r['a']]} vs {LAB[r['b']]} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, "
                 f"{r['ci95'][1]:+.1f}] | [{r['ci90'][0]:+.1f}, {r['ci90'][1]:+.1f}] | {fp(r['p'])} | {fp(r['p_signflip'])} | "
                 f"{r['traj_better']}/{r['traj_worse']} | {r['tested']} | {r['rejected']} |")
    open(f'{OUT}/primary.md', 'w').write('\n'.join(L) + '\n')
    L = ['| id | comparison | group | estimate [95 % CI] | p | Holm p | traj better/worse |', '|---|---|---|---|---|---|---|']
    for r in sec:
        L.append(f"| {r['id']} | {LAB[r['a']]} vs {LAB[r['b']]} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, "
                 f"{r['ci95'][1]:+.1f}] | {fp(r['p'])} | {fp(r['p_holm'])} | {r['traj_better']}/{r['traj_worse']} |")
    open(f'{OUT}/secondary.md', 'w').write('\n'.join(L) + '\n')
    L = ['| method | group | failures / runs | rate [cluster 95 % CI] | trajectories with a failure |', '|---|---|---|---|---|']
    for f in fails:
        L.append(f"| {LAB[f['method']]} | {f['group']} | {f['fails']} / {f['runs']} | {100 * f['rate']:.1f} % "
                 f"[{100 * f['ci'][0]:.1f}, {100 * f['ci'][1]:.1f}] | {f['n_traj_with_fail']} |")
    open(f'{OUT}/failures.md', 'w').write('\n'.join(L) + '\n')
    L = ['| id | cap | estimate [95 % CI] | p | n traj |', '|---|---|---|---|---|']
    for r in res['cap_sensitivity']:
        if 'est' in r:
            L.append(f"| {r['id']} | {r['cap']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['n_traj']} |")
    open(f'{OUT}/cap_sensitivity.md', 'w').write('\n'.join(L) + '\n')
    print(open(f'{OUT}/primary.md').read())


if __name__ == '__main__':
    main()
