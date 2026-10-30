#!/usr/bin/env python3
"""vs_analyze.py [--metric ate|rpe] [--root runs] : back-end-agnostic SAVIOR on VINS-Fusion, warehouse t1.
Protocol = results/m2b_heldout/scripts/m2banalyze.py (P7/M2b statistics): paired per-offset log ratios (failures =
ATE > 2 m, capped at 10 m) vs a reference, geometric-mean ratio - 1, 95 % bootstrap CI (20000, seed 0), Wilcoxon
signed-rank, Holm within each (group, reference) family. RPE = shortest rpg sub-length, translation mean, failed runs inf.
Pose-count rule (M2b): poses >= same-offset reference (VINS-Fusion) pose count - 1, else flagged.
Runs in the savior image (numpy / scipy / yaml). -> results/vins_savior/tables/{metric}.md|json"""
import json, math, os, sys
import numpy as np, yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
V = WS + '/results/vins_savior'
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
METRIC = arg('--metric', 'ate')
DS = arg('--dataset', 't1')            # t1 (tuning) | t2 (warehouse held-out) | viode (held-out)
R = V + '/' + arg('--root', 'runs')
OUT = V + '/' + arg('--out', 'tables')
DYNA_ROOT = arg('--dynavins-root', '')  # held-out: reuse the M3b DynaVINS runs (results/sota), same protocol
PREFIX = 'viode_' if DS == 'viode' else 'warehouse_'
if DS == 't1':
    SEQS = [f'{e}_t1_L{l}' for e in ('aisles', 'hall') for l in range(4)]
elif DS == 't2':
    SEQS = [f'{e}_t2_L{l}' for e in ('aisles', 'hall', 'dock') for l in range(4)]
else:
    SEQS = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
M = ['vins_fusion', 'vins_ycls', 'vins_savior', 'vins_edge', 'vins_odyn', 'vins_ocls', 'dynavins', 'vins_zero', 'vins_fusion_mt']
LAB = {'vins_fusion': 'VINS-Fusion', 'vins_ycls': 'VINS+Y-Cls', 'vins_savior': 'VINS+SAVIOR', 'vins_edge': 'VINS+SAVIOR-edge',
       'vins_odyn': 'VINS+O-Dyn+B', 'vins_ocls': 'VINS+O-Cls+B', 'dynavins': 'DynaVINS', 'vins_zero': 'VINS+zero-masks',
       'vins_fusion_mt': 'VINS-Fusion (upstream threads)'}
REFS = {'vins_fusion': ['vins_ycls', 'vins_savior', 'vins_edge', 'vins_odyn', 'vins_ocls', 'dynavins'],
        'vins_ycls': ['vins_savior', 'vins_edge'],
        'dynavins': ['vins_savior', 'vins_edge'],
        'vins_ocls': ['vins_odyn'],
        'vins_savior': ['vins_edge']}
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
    root = DYNA_ROOT if (m == 'dynavins' and DYNA_ROOT) else R
    fn = f'{root}/{PREFIX}{seq}/{m}/eval_posyaw/eval_summary.yaml'
    out, poses, first = {}, {}, {}
    if not os.path.isfile(fn):
        return out, poses, first
    for t in yaml.safe_load(open(fn)).get('trials', []):
        i = int(t['name'].split('_')[1])
        tf = f'{root}/{PREFIX}{seq}/{m}/run_{i:02d}/stamped_traj_estimate.txt'
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
            x = np.array([lr(D[s][m][i], D[s][ref][i]) for s in SEQS if sel(s) for i in IDX if i in D[s][m] and i in D[s][ref]])
            if x.size < 5:
                continue
            nz = x[np.abs(x) > 1e-12]
            p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
            ci = boot(x)
            fam.append(dict(metric=METRIC, ref=ref, group=g, method=m, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1),
                            ci=[100 * (math.exp(c) - 1) for c in ci], wins=int((x < -1e-12).sum()),
                            losses=int((x > 1e-12).sum()), p=p))
        for r, h in zip(fam, holm([r['p'] for r in fam]) if fam else []):
            r['holm'] = float(h)
        res += fam

nf = {m: {g: sum(sum(v > FAIL_M for v in D[s][m].values()) for s in SEQS if sel(s)) for g, sel in GROUPS.items()} for m in M}
# pose-count rule vs VINS-Fusion (same offset)
pc = {}
for m in M:
    if m == 'vins_fusion':
        continue
    bad = [(s, i, NP[s][m][i], NP[s]['vins_fusion'][i], FIRST[s][m][i] - FIRST[s]['vins_fusion'][i])
           for s in SEQS for i in IDX if i in NP[s][m] and i in NP[s].get('vins_fusion', {})
           and NP[s][m][i] < NP[s]['vins_fusion'][i] - 1]
    pc[m] = bad

L = [f'# VINS-Fusion + SAVIOR masks, {DS}, {METRIC.upper()} ({len(SEQS)} sequences x 10 offsets; failure = ATE > {FAIL_M:g} m, '
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
          f'method(s) per group)\n', '| method | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    for m in ms:
        cells = []
        for g in GROUPS:
            r = next((x for x in res if x['ref'] == ref and x['group'] == g and x['method'] == m), None)
            cells.append('-' if r is None else
                         f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.3g} H={r['holm']:.3g} {r['wins']}/{r['losses']}")
        L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
L.append('\n## Pose-count rule (poses >= same-offset VINS-Fusion poses - 1)\n')
for m, bad in pc.items():
    L.append(f'- {LAB[m]}: {10 * len(SEQS) - len(bad)}/{10 * len(SEQS)} pass' + (
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
