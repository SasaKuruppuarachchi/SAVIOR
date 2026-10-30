#!/usr/bin/env python3
"""t3_extras.py : the parts of DESIGN.yaml analysis_plan.secondary.other that the frozen stats_t3.py does not write, plus the
DynaVINS + SAVIOR masks disclosed secondary of AMENDMENT_02 section 3. Written BEFORE any t3 run (md5 in AMENDMENT_02_IMPL.md5).
Uses the frozen stats_t3.py module objects (load, traj_of, lev, GROUPS, IDX, CAP, FAIL, S3 = stats3_core) unchanged; the
per-comparison model is a verbatim copy of stats_t3.main().analyse (paired log ratio, mean over offsets per sequence, REML
random intercept per trajectory, t on mu with df = n_traj - 1).
  1. per-environment breakdown (fw / sw / ms / wx, 6 trajectories each; descriptive, no multiplicity control) of every
     primary and secondary comparison, cap 10 m;
  2. controls: savior_none vs openvins and vins_zero vs vins_fusion (trajectory md5 identity per run, ATE ratio, all levels);
  3. paired failure differences per primary / secondary comparison (difference of per-trajectory failure rates A - B,
     exact sign-flip on the trajectory differences; design 'other');
  4. non-failed accuracy: median / geometric mean ATE of non-failed runs per method x group (the 'excl' cap test is in
     stats_t3 cap_sensitivity);
  5. DynaVINS + SAVIOR masks (results/t3_confirmatory/dyna_masks_runs, P10, deterministic, 1 solver thread). EXPLORATORY,
     outside P1-P5 and the S1-S14 Holm family; Holm only within this DM family (fixed here, before any run):
       DM1 dyna_savior vs dyna_ycls high     DM2 dyna_savior vs dyna_ycls low     DM3 dyna_savior vs dyna_det high
       DM4 dyna_savior vs dyna_det low       DM5 dyna_odyn vs dyna_ocls high      DM6 dyna_ycls vs dyna_det high
       DM7 dyna_savior vs dyna_det static    DM8 dyna_ycls vs dyna_det static     DM9 dyna_det vs dynavins (upstream) high
     control: dyna_zero vs dyna_det (all levels); failures per DM method x group.
-> results/t3_confirmatory/tables/extras.json, per_environment.md, controls.md, failure_diff.md, nonfailed.md, dyna_masks.md"""
import hashlib
import importlib.util
import json
import math
import os

import numpy as np
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
spec = importlib.util.spec_from_file_location('stats_t3', f'{T}/scripts/stats_t3.py')
ST = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ST)
S3 = ST.S3
OUT = ST.OUT
ENVS = ['fw', 'sw', 'ms', 'wx']
DM = ['dyna_det', 'dyna_zero', 'dyna_savior', 'dyna_ycls', 'dyna_odyn', 'dyna_ocls']
DMLAB = {'dyna_det': 'DynaVINS (det.)', 'dyna_zero': 'DynaVINS+zero (control)', 'dyna_savior': 'DynaVINS+SAVIOR',
         'dyna_ycls': 'DynaVINS+Y-Cls', 'dyna_odyn': 'DynaVINS+O-Dyn+B', 'dyna_ocls': 'DynaVINS+O-Cls+B', 'dynavins': 'DynaVINS (upstream)'}
DMCOMP = [('DM1', 'dyna_savior', 'dyna_ycls', 'high'), ('DM2', 'dyna_savior', 'dyna_ycls', 'low'),
          ('DM3', 'dyna_savior', 'dyna_det', 'high'), ('DM4', 'dyna_savior', 'dyna_det', 'low'),
          ('DM5', 'dyna_odyn', 'dyna_ocls', 'high'), ('DM6', 'dyna_ycls', 'dyna_det', 'high'),
          ('DM7', 'dyna_savior', 'dyna_det', 'static'), ('DM8', 'dyna_ycls', 'dyna_det', 'static'),
          ('DM9', 'dyna_det', 'dynavins', 'high')]
fp = lambda p: '-' if p is None else (f'{p:.1e}' if p < 1e-3 else f'{p:.3f}')  # noqa: E731
pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else ''


def main():
    import yaml
    ex = set()
    if os.path.isfile(f'{T}/EXCLUSIONS.yaml'):
        ex = {e['trajectory'] for e in (yaml.safe_load(open(f'{T}/EXCLUSIONS.yaml')) or {}).get('excluded', [])}
    trajs = [t['id'] for t in ST.DESIGN['dataset']['trajectories'] if t['id'] not in ex]
    seqs = [f'{t}_t3_L{k}' for t in trajs for k in ST.DESIGN['dataset']['levels']]
    V = {m: {s: ST.load(f'{T}/runs/{s}/{m}/eval/eval_summary.yaml') for s in seqs} for m in ST.OV}
    V.update({m: {s: ST.load(f'{T}/vins_runs/warehouse_{s}/{m}/eval_posyaw/eval_summary.yaml') for s in seqs} for m in ST.VINS})
    V.update({m: {s: ST.load(f'{T}/dyna_masks_runs/warehouse_{s}/{m}/eval_posyaw/eval_summary.yaml') for s in seqs} for m in DM})
    IDX, CAP, FAIL, GROUPS, lev, traj_of = ST.IDX, ST.CAP, ST.FAIL, ST.GROUPS, ST.lev, ST.traj_of

    def paired(a, b, group, cap, tsel=None):
        X = {}
        for s in seqs:
            if lev(s) not in GROUPS[group] or (tsel and traj_of(s) not in tsel):
                continue
            x = [S3.lr(V[a][s][i], V[b][s][i], cap, FAIL) for i in IDX if i in V[a][s] and i in V[b][s]]
            x = [v for v in x if v is not None]
            if x:
                X.setdefault(traj_of(s), []).append(float(np.mean(x)))
        return {k: np.array(v) for k, v in X.items()}

    def signflip(m):   # = stats_t3.main().signflip (exact up to 20 trajectories, Monte Carlo 2^20 above)
        k = m.size
        if k <= 20:
            return S3.signflip(m)[0]
        rng = np.random.default_rng(0)
        sg = rng.choice([-1, 1], (2 ** 20, k))
        return float(np.mean(np.abs((sg * m).mean(1)) >= abs(m.mean()) - 1e-12))

    def analyse(a, b, group, cap=CAP, tsel=None):
        X = paired(a, b, group, cap, tsel)
        if len(X) < 2:
            return None
        tm = np.array([X[k].mean() for k in X])
        l = S3.reml_ri(X)
        q = stats.t.ppf(0.975, l['df'])
        return dict(a=a, b=b, group=group, n_traj=len(X), n_seq=int(sum(v.size for v in X.values())), est=pc(l['mu']),
                    ci95=[pc(l['mu'] - q * l['se']), pc(l['mu'] + q * l['se'])], p=l['p'],
                    p_signflip=signflip(tm),
                    traj_better=int((tm < -1e-12).sum()), traj_worse=int((tm > 1e-12).sum()))

    def failrate(m, group, tsel=None):
        per = {}
        for s in seqs:
            if lev(s) in GROUPS[group] and (not tsel or traj_of(s) in tsel):
                f, n = per.get(traj_of(s), (0, 0))
                per[traj_of(s)] = (f + sum(V[m][s][i] > FAIL for i in IDX if i in V[m][s]), n + sum(i in V[m][s] for i in IDX))
        return per

    def failsum(m, g):
        per = failrate(m, g)
        f = np.array([v[0] for v in per.values()], float)
        n = np.array([v[1] for v in per.values()], float)
        if n.sum() == 0:
            return None
        rng = np.random.default_rng(0)
        si = rng.integers(0, f.size, (20000, f.size))
        r = f[si].sum(1) / np.maximum(n[si].sum(1), 1)
        return dict(method=m, group=g, fails=int(f.sum()), runs=int(n.sum()), rate=float(f.sum() / n.sum()),
                    ci=[float(x) for x in np.percentile(r, [2.5, 97.5])], n_traj_with_fail=int((f > 0).sum()))

    res = {}
    comps = [(h[0], h[1], h[2], h[3]) for h in ST.PRIMARY] + list(ST.SECONDARY)
    lab = dict(ST.LAB, **DMLAB)
    # 1. per environment
    pe = []
    for cid, a, b, g in comps:
        for e in ENVS:
            r = analyse(a, b, g, tsel={t for t in trajs if t.startswith(e)})
            if r:
                pe.append(dict(id=cid, env=e, **r))
    res['per_environment'] = pe
    L = ['# Per-environment breakdown (descriptive; cap 10 m; LMM per environment, df = n_traj - 1; no multiplicity control)\n',
         '| id | comparison | group | env | estimate [95 % CI] | p | sign-flip p | traj better/worse |', '|---|---|---|---|---|---|---|---|']
    for r in pe:
        L.append(f"| {r['id']} | {lab[r['a']]} vs {lab[r['b']]} | {r['group']} | {r['env']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, "
                 f"{r['ci95'][1]:+.1f}] | {fp(r['p'])} | {fp(r['p_signflip'])} | {r['traj_better']}/{r['traj_worse']} |")
    open(f'{OUT}/per_environment.md', 'w').write('\n'.join(L) + '\n')
    # 2. controls
    ctl = []
    for a, b, ra, rb in (('savior_none', 'openvins', 'runs/{s}/{m}', 'runs/{s}/{m}'),
                         ('vins_zero', 'vins_fusion', 'vins_runs/warehouse_{s}/{m}', 'vins_runs/warehouse_{s}/{m}'),
                         ('dyna_zero', 'dyna_det', 'dyna_masks_runs/warehouse_{s}/{m}', 'dyna_masks_runs/warehouse_{s}/{m}')):
        same = tot = 0
        rel = []
        for s in seqs:
            for i in IDX:
                fa = f"{T}/{ra.format(s=s, m=a)}/run_{i:02d}/stamped_traj_estimate.txt"
                fb = f"{T}/{rb.format(s=s, m=b)}/run_{i:02d}/stamped_traj_estimate.txt"
                if os.path.isfile(fa) and os.path.isfile(fb):
                    tot += 1
                    same += md5(fa) == md5(fb)
                if i in V[a][s] and i in V[b][s] and math.isfinite(V[a][s][i]) and math.isfinite(V[b][s][i]):
                    rel.append(abs(V[a][s][i] / V[b][s][i] - 1))
        r = analyse(a, b, 'all')
        ctl.append(dict(a=a, b=b, md5_same=same, pairs=tot, rel_diff_median=float(np.median(rel)) if rel else None,
                        rel_diff_max=float(np.max(rel)) if rel else None, n_rel_gt_1pct=int(sum(x > 0.01 for x in rel)), lmm_all=r))
    res['controls'] = ctl
    L = ['# Controls (all levels)\n', '| control | identical trajectories (md5) | median / max relative ATE difference | pairs > 1 % | LMM all levels |',
         '|---|---|---|---|---|']
    for c in ctl:
        r = c['lmm_all']
        rd = '-' if c['rel_diff_median'] is None else '%.2e / %.2e' % (c['rel_diff_median'], c['rel_diff_max'])
        lm = '-' if not r else '%+.2f %% [%+.2f, %+.2f], p %s' % (r['est'], r['ci95'][0], r['ci95'][1], fp(r['p']))
        L.append(f"| {lab[c['a']]} vs {lab[c['b']]} | {c['md5_same']} / {c['pairs']} | {rd} | {c['n_rel_gt_1pct']} | {lm} |")
    open(f'{OUT}/controls.md', 'w').write('\n'.join(L) + '\n')
    # 3. paired failure differences
    fd = []
    for cid, a, b, g in comps + DMCOMP:
        fa, fb = failrate(a, g), failrate(b, g)
        ks = sorted(set(fa) & set(fb))
        if not ks:
            continue
        d = np.array([fa[k][0] / max(fa[k][1], 1) - fb[k][0] / max(fb[k][1], 1) for k in ks])
        fd.append(dict(id=cid, a=a, b=b, group=g, fails_a=int(sum(fa[k][0] for k in ks)), fails_b=int(sum(fb[k][0] for k in ks)),
                       runs_a=int(sum(fa[k][1] for k in ks)), runs_b=int(sum(fb[k][1] for k in ks)), mean_diff_pp=float(100 * d.mean()),
                       p_signflip=float(S3.signflip(d)[0]) if d.size <= 20 and np.any(d != 0) else (1.0 if not np.any(d != 0) else None),
                       n_traj=len(ks)))
    if any(r['p_signflip'] is None for r in fd):   # > 20 trajectories: Monte Carlo sign-flip as stats_t3.signflip
        for r in fd:
            if r['p_signflip'] is None:
                fa, fb = failrate(r['a'], r['group']), failrate(r['b'], r['group'])
                ks = sorted(set(fa) & set(fb))
                d = np.array([fa[k][0] / max(fa[k][1], 1) - fb[k][0] / max(fb[k][1], 1) for k in ks])
                rng = np.random.default_rng(0)
                sg = rng.choice([-1, 1], (2 ** 20, d.size))
                r['p_signflip'] = float(np.mean(np.abs((sg * d).mean(1)) >= abs(d.mean()) - 1e-12))
    res['failure_diff'] = fd
    L = ['# Paired failure differences (per-trajectory failure rate A - B, sign-flip on trajectories; failure = ATE > 2 m or no estimate)\n',
         '| id | comparison | group | fails A / runs | fails B / runs | mean diff [pp] | sign-flip p | n traj |', '|---|---|---|---|---|---|---|---|']
    for r in fd:
        L.append(f"| {r['id']} | {lab[r['a']]} vs {lab[r['b']]} | {r['group']} | {r['fails_a']} / {r['runs_a']} | {r['fails_b']} / {r['runs_b']} | "
                 f"{r['mean_diff_pp']:+.2f} | {fp(r['p_signflip'])} | {r['n_traj']} |")
    open(f'{OUT}/failure_diff.md', 'w').write('\n'.join(L) + '\n')
    # 4. non-failed accuracy
    nf = []
    for m in V:
        for g in ('static', 'low', 'high', 'all'):
            x = np.array([V[m][s][i] for s in seqs if lev(s) in GROUPS[g] for i in IDX if i in V[m][s] and V[m][s][i] <= FAIL])
            n = sum(i in V[m][s] for s in seqs if lev(s) in GROUPS[g] for i in IDX)
            if n:
                nf.append(dict(method=m, group=g, n_ok=int(x.size), runs=int(n), median=float(np.median(x)) if x.size else None,
                               geomean=float(np.exp(np.log(x).mean())) if x.size else None))
    res['nonfailed'] = nf
    L = ['# Accuracy on non-failed runs (ATE posyaw <= 2 m)\n', '| method | group | non-failed / runs | median ATE [m] | geometric mean [m] |',
         '|---|---|---|---|---|']
    for r in nf:
        md = '-' if r['median'] is None else '%.3f' % r['median']
        gm = '-' if r['geomean'] is None else '%.3f' % r['geomean']
        L.append(f"| {lab[r['method']]} | {r['group']} | {r['n_ok']} / {r['runs']} | {md} | {gm} |")
    open(f'{OUT}/nonfailed.md', 'w').write('\n'.join(L) + '\n')
    # 5. DynaVINS + masks (exploratory)
    dm = [dict(id=cid, **r) for cid, a, b, g in DMCOMP for r in [analyse(a, b, g)] if r]
    for r, h in zip(dm, S3.holm([r['p'] for r in dm]) if dm else []):
        r['p_holm_dm'] = float(h)
    dmf = [f for m in DM for g in ('static', 'low', 'high', 'all') for f in [failsum(m, g)] if f]
    dmcap = [dict(id=cid, cap=str(c), **{k: v for k, v in (analyse(a, b, g, c) or {}).items() if k in ('est', 'ci95', 'p', 'n_traj')})
             for cid, a, b, g in DMCOMP for c in ST.CAPS]
    res['dyna_masks'] = dict(comparisons=dm, failures=dmf, cap_sensitivity=dmcap)
    L = ['# DynaVINS + SAVIOR masks on t3 (AMENDMENT_02 section 3): EXPLORATORY, outside P1-P5 and the S1-S14 Holm family\n',
         'Model as stats_t3 (cap 10 m, trajectory LMM); Holm within DM1-DM9 only.\n',
         '| id | comparison | group | estimate [95 % CI] | p | Holm p (DM family) | sign-flip p | traj better/worse | n traj |',
         '|---|---|---|---|---|---|---|---|---|']
    for r in dm:
        L.append(f"| {r['id']} | {lab[r['a']]} vs {lab[r['b']]} | {r['group']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | "
                 f"{fp(r['p'])} | {fp(r['p_holm_dm'])} | {fp(r['p_signflip'])} | {r['traj_better']}/{r['traj_worse']} | {r['n_traj']} |")
    L += ['\n## Failures (ATE > 2 m), trajectory-cluster bootstrap 95 % CI\n', '| method | group | failures / runs | rate [CI] | traj with a failure |',
          '|---|---|---|---|---|']
    for f in dmf:
        L.append(f"| {lab[f['method']]} | {f['group']} | {f['fails']} / {f['runs']} | {100 * f['rate']:.1f} % [{100 * f['ci'][0]:.1f}, "
                 f"{100 * f['ci'][1]:.1f}] | {f['n_traj_with_fail']} |")
    L += ['\n## Cap sensitivity\n', '| id | cap | estimate [95 % CI] | p | n traj |', '|---|---|---|---|---|']
    for r in dmcap:
        if 'est' in r:
            L.append(f"| {r['id']} | {r['cap']} | {r['est']:+.1f} % [{r['ci95'][0]:+.1f}, {r['ci95'][1]:+.1f}] | {fp(r['p'])} | {r['n_traj']} |")
    open(f'{OUT}/dyna_masks.md', 'w').write('\n'.join(L) + '\n')
    json.dump(res, open(f'{OUT}/extras.json', 'w'), indent=1, default=str)
    for f in ('controls', 'dyna_masks'):
        print(open(f'{OUT}/{f}.md').read())


if __name__ == '__main__':
    main()
