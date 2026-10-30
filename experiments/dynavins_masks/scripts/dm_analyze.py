#!/usr/bin/env python3
"""dm_analyze.py [--metric ate|rpe] [--dataset t1|t2|viode] [--root runs] [--out tables] [--up-root DIR] :
DynaVINS + SAVIOR masks (patch P10). Statistics = results/vins_savior/scripts/vs_analyze.py, unchanged (paired per-offset
log ratios vs a reference; failures = ATE > 2 m warehouse / > 1 m VIODE, capped at 10 m; geometric-mean ratio - 1; 95 %
bootstrap CI over runs (20000, seed 0); Wilcoxon signed-rank; Holm within each (group, reference) family; RPE =
shortest rpg sub-length, translation mean, failed runs inf; pose-count rule vs the reference baseline), PLUS a
sequence-level cluster bootstrap (resample sequences with replacement, then the offsets within each drawn sequence;
20000, seed 1): 95 % CI of the geometric-mean change and a two-sided bootstrap p = 2 min(P(T* <= 0), P(T* >= 0)).
Runs in the savior image (numpy / scipy / yaml). -> <out>/{metric}.md|json"""
import json, math, os, sys
import numpy as np, yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
V = WS + '/results/dynavins_masks'
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
METRIC = arg('--metric', 'ate')
DS = arg('--dataset', 't1')
R = V + '/' + arg('--root', 'runs')
OUT = V + '/' + arg('--out', 'tables')
UP_ROOT = arg('--up-root', '')   # upstream DynaVINS runs (t1: results/vins_savior/runs, held-out: results/sota), method dir 'dynavins'
PREFIX = 'viode_' if DS == 'viode' else 'warehouse_'
if DS == 't1':
    SEQS = [f'{e}_t1_L{l}' for e in ('aisles', 'hall') for l in range(4)]
elif DS == 't2':
    SEQS = [f'{e}_t2_L{l}' for e in ('aisles', 'hall', 'dock') for l in range(4)]
else:
    SEQS = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
M = ['dyna_det', 'dyna_ycls', 'dyna_savior', 'dyna_odyn', 'dyna_ocls', 'dyna_zero', 'dyna_up']
LAB = {'dyna_det': 'DynaVINS', 'dyna_ycls': 'DynaVINS+Y-Cls', 'dyna_savior': 'DynaVINS+SAVIOR',
       'dyna_odyn': 'DynaVINS+O-Dyn+B', 'dyna_ocls': 'DynaVINS+O-Cls+B', 'dyna_zero': 'DynaVINS+zero-masks',
       'dyna_up': 'DynaVINS (upstream threads)'}
REFS = {'dyna_det': ['dyna_ycls', 'dyna_savior', 'dyna_odyn', 'dyna_ocls'],
        'dyna_ycls': ['dyna_savior'],
        'dyna_ocls': ['dyna_odyn'],
        'dyna_up': ['dyna_det']}
BASE = 'dyna_det'
FAIL_M, CAP_M = (1.0 if DS == 'viode' else 2.0), 10.0
IDX = list(range(1, 11))
lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
if DS == 'viode':
    GROUPS = {g: (lambda s, g=g: g == 'all' or lev(s) in g.split('+')) for g in
              ('none', 'low', 'mid', 'high', 'none+low', 'mid+high', 'low+mid+high', 'all')}
else:
    GROUPS = {'L0': lambda s: lev(s) == 'L0', 'L1': lambda s: lev(s) == 'L1', 'L2': lambda s: lev(s) == 'L2',
              'L3': lambda s: lev(s) == 'L3', 'L0+L1': lambda s: lev(s) in ('L0', 'L1'),
              'L2+L3': lambda s: lev(s) in ('L2', 'L3'), 'hall_L3': lambda s: s.startswith('hall_') and lev(s) == 'L3',
              'all': lambda s: True}
    if DS == 't2':
        GROUPS['dock_L3'] = lambda s: s.startswith('dock_') and lev(s) == 'L3'
        GROUPS['hall+dock_L3'] = lambda s: s.split('_')[0] in ('hall', 'dock') and lev(s) == 'L3'


def load(seq, m):
    root, md = (UP_ROOT, 'dynavins') if m == 'dyna_up' else (R, m)
    if not root:
        return {}, {}, {}
    fn = f'{root}/{PREFIX}{seq}/{md}/eval_posyaw/eval_summary.yaml'
    out, poses, first = {}, {}, {}
    if not os.path.isfile(fn):
        return out, poses, first
    for t in yaml.safe_load(open(fn)).get('trials', []):
        i = int(t['name'].split('_')[1])
        tf = f'{root}/{PREFIX}{seq}/{md}/run_{i:02d}/stamped_traj_estimate.txt'
        L = [l for l in open(tf) if l.strip() and not l.startswith('#')] if os.path.isfile(tf) else []
        poses[i] = len(L)
        first[i] = float(L[0].split()[0]) if L else math.nan
        if t.get('status') != 'ok':
            out[i] = math.inf
            continue
        ate = t['ate']['trans_m']['rmse']
        if METRIC == 'rpe':
            ks = sorted(t['rpe'], key=float)
            out[i] = t['rpe'][ks[0]]['trans_m']['mean'] if ate <= FAIL_M else math.inf
        else:
            out[i] = ate
    return out, poses, first


D, NP, FIRST = {}, {}, {}
for s in SEQS:
    D[s], NP[s], FIRST[s] = {}, {}, {}
    for m in M:
        D[s][m], NP[s][m], FIRST[s][m] = load(s, m)
M = [m for m in M if any(D[s][m] for s in SEQS)]
missing = [(s, m, i) for s in SEQS for m in M for i in IDX if i not in D[s][m]]


def lr(a, b):
    return math.log(min(a, CAP_M) / min(b, CAP_M))


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (n, x.size)).mean(axis=1), [2.5, 97.5])


def cluster_boot(xs, n=20000):
    """xs: list of per-sequence arrays of paired log ratios. Two-stage resampling (sequences, then offsets)."""
    rng = np.random.default_rng(1)
    k = len(xs)
    T = np.empty(n)
    for b in range(n):
        tot, cnt = 0.0, 0
        for j in rng.integers(0, k, k):
            x = xs[j]
            tot += x[rng.integers(0, x.size, x.size)].sum(); cnt += x.size
        T[b] = tot / cnt
    lo, hi = np.percentile(T, [2.5, 97.5])
    p = min(1.0, 2 * min((T <= 0).mean(), (T >= 0).mean()))
    return lo, hi, float(p)


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


res = []
for ref, ms in REFS.items():
    if ref not in M:
        continue
    for g, sel in GROUPS.items():
        fam = []
        for m in ms:
            if m not in M:
                continue
            per = [np.array([lr(D[s][m][i], D[s][ref][i]) for i in IDX if i in D[s][m] and i in D[s][ref]])
                   for s in SEQS if sel(s)]
            per = [x for x in per if x.size]
            x = np.concatenate(per) if per else np.array([])
            if x.size < 5:
                continue
            nz = x[np.abs(x) > 1e-12]
            p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
            ci = boot(x)
            clo, chi, cp = cluster_boot(per)
            fam.append(dict(metric=METRIC, ref=ref, group=g, method=m, n=int(x.size), n_seq=len(per),
                            gm=100 * (math.exp(x.mean()) - 1), ci=[100 * (math.exp(c) - 1) for c in ci],
                            wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), p=p,
                            cci=[100 * (math.exp(clo) - 1), 100 * (math.exp(chi) - 1)], cp=cp))
        for r, h, hc in zip(fam, holm([r['p'] for r in fam]) if fam else [], holm([r['cp'] for r in fam]) if fam else []):
            r['holm'] = float(h); r['cholm'] = float(hc)
        res += fam

nf = {m: {g: sum(sum(v > FAIL_M for v in D[s][m].values()) for s in SEQS if sel(s)) for g, sel in GROUPS.items()} for m in M}
pc = {}
for m in M:
    if m == BASE or BASE not in M:
        continue
    bad = [(s, i, NP[s][m][i], NP[s][BASE][i], FIRST[s][m][i] - FIRST[s][BASE][i])
           for s in SEQS for i in IDX if i in NP[s][m] and i in NP[s].get(BASE, {})
           and NP[s][m][i] < NP[s][BASE][i] - 1]
    pc[m] = bad

L = [f'# DynaVINS + SAVIOR masks (P10), {DS}, {METRIC.upper()} ({len(SEQS)} sequences x 10 offsets; failure = ATE > {FAIL_M:g} m, '
     f'capped at {CAP_M:g} m)\n', f'## Median {METRIC.upper()} [m] ([n] = failures)\n',
     '| seq | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for s in SEQS:
    cells = []
    for m in M:
        v = list(D[s][m].values())
        if not v:
            cells.append('-'); continue
        k = sum(x > FAIL_M for x in D[s][m].values()) if METRIC == 'ate' else sum(math.isinf(x) for x in v)
        cells.append(f'{float(np.median(np.minimum(v, 1e4))):.3f}' + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
    L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
L.append(f'\n## Failures (ATE > {FAIL_M:g} m) per group\n')
L += ['| group | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for g in GROUPS:
    L.append(f'| {g} | ' + ' | '.join(str(nf[m][g]) for m in M) + ' |')
for ref, ms in REFS.items():
    if ref not in M:
        continue
    ms = [m for m in ms if m in M]
    L += [f'\n## Paired vs {LAB[ref]} (geometric-mean {METRIC.upper()} ratio - 1; negative = better; Holm over {len(ms)} '
          f'method(s) per group)\n',
          'Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap '
          '95 % CI, bootstrap p / Holm (n_seq sequences).\n',
          '| method | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    for m in ms:
        cells = []
        for g in GROUPS:
            r = next((x for x in res if x['ref'] == ref and x['group'] == g and x['method'] == m), None)
            cells.append('-' if r is None else
                         f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.3g} H={r['holm']:.3g} {r['wins']}/{r['losses']}"
                         f"<br>clu [{r['cci'][0]:+.0f}, {r['cci'][1]:+.0f}] p={r['cp']:.3g} H={r['cholm']:.3g} (k={r['n_seq']})")
        L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
L.append(f'\n## Pose-count rule (poses >= same-offset {LAB[BASE]} poses - 1)\n')
for m, bad in pc.items():
    n = sum(1 for s in SEQS for i in IDX if i in NP[s][m] and i in NP[s].get(BASE, {}))
    L.append(f'- {LAB[m]}: {n - len(bad)}/{n} pass' + (
        ('; flagged: ' + ', '.join(f'{s}/run_{i:02d} ({a} vs {b}, first pose {d:+.2f} s)' for s, i, a, b, d in bad[:12])
         + (' ...' if len(bad) > 12 else '')) if bad else ''))
if missing:
    L.append(f'\n**MISSING runs: {len(missing)}** ' + ', '.join(f'{s}/{m}/{i}' for s, m, i in missing[:30]))
os.makedirs(OUT, exist_ok=True)
open(f'{OUT}/{METRIC}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': {s: {m: D[s][m] for m in M} for s in SEQS}, 'poses': NP, 'paired': res, 'failures': nf,
           'pose_count_flags': pc, 'fail_m': FAIL_M, 'labels': LAB},
          open(f'{OUT}/{METRIC}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
