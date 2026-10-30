#!/usr/bin/env python3
"""edge_analyze.py (EDGE study; derived from results/p7/scripts/p7analyze.py, same statistics; reference = frozen main sens_fix1 from results/p7)
p7analyze.py [--methods m1,m2] : closed-loop ATE on the t1 tuning set: median matrix with failures (> FAIL_M), paired
per-offset log ratios (failures capped at 10 m) vs references, per level / L0+L1 / L2+L3 groups, geometric-mean ratio - 1,
95 % bootstrap CI, Wilcoxon signed-rank, Holm within each (group, reference) family. Reused P6 runs: openvins,
oracle_moving_ext, yolo_naive (bit-identical poses after the P7 rebuild, checked). -> results/p7/tables/ate_*.md"""
import glob, json, math, os, sys
import numpy as np, yaml
from scipy import stats
R = '/home/sasa/workspace/savior_ws/results'
P7, P6 = R + '/p7', R + '/p6_warehouse'
E = R + '/edge_study/runs'
OUT = R + '/edge_study/tables'
REUSE = {'openvins', 'oracle_moving_ext', 'yolo_naive', 'oracle_moving', 'oracle_class_naive'}   # P6 runs (0 fallbacks; deterministic)
METRIC = sys.argv[sys.argv.index('--metric') + 1] if '--metric' in sys.argv else os.environ.get('METRIC', 'ate')   # ate | rpe (mean trans error over the shortest rpg sub-length, ~9.6 m)
SEQS = [f'{s}_t1_{l}' for s in ('aisles', 'hall') for l in ('L0', 'L1', 'L2', 'L3')]
IDX = list(range(1, 11))
FAIL_M, CAP_M = float(os.environ.get('FAIL_M', '2.0')), 10.0
arg = sys.argv[sys.argv.index('--methods') + 1].split(',') if '--methods' in sys.argv else None
refs = sys.argv[sys.argv.index('--refs') + 1].split(',') if '--refs' in sys.argv else ['sens_fix1']
tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'main'


def load(seq, m):
    base = E if os.path.isdir(f'{E}/{seq}/{m}') else (P6 if (m in REUSE and not os.path.isdir(f'{P7}/{seq}/{m}/eval')) else P7)
    fn = f'{base}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                out[i] = math.inf
                continue
            if METRIC == 'rpe':
                ks = sorted(t['rpe'], key=float)
                out[i] = t['rpe'][ks[0]]['trans_m']['mean'] if t['ate']['trans_m']['rmse'] <= FAIL_M else math.inf
            else:
                out[i] = t['ate']['trans_m']['rmse']
    for rd in glob.glob(f'{base}/{seq}/{m}/run_*'):
        i = int(rd.rsplit('_', 1)[1])
        out.setdefault(i, math.inf)
    return {i: v for i, v in out.items() if i in IDX}


def methods():
    ms = set()
    for s in SEQS:
        for d in glob.glob(f'{P7}/{s}/*/eval/eval_summary.yaml'):
            ms.add(d.split('/')[-3])
    return sorted(ms | REUSE)


M = arg or methods()
D = {s: {m: load(s, m) for m in set(M) | set(refs)} for s in SEQS}


def lr(a, b):
    a, b = min(a, CAP_M), min(b, CAP_M)
    return math.log(a / b)


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    b = rng.choice(x, (n, x.size)).mean(axis=1)
    return np.percentile(b, [2.5, 97.5])


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


L = [f'# P7 closed-loop {METRIC.upper()} (t1 tuning set, 10 offsets 0.0-1.8 s; failure = ATE > {FAIL_M:g} m)\n', f'## Median {METRIC.upper()} [m] ([n] = failures; RPE: failed runs (ATE > FAIL_M) count as inf)\n',
     '| seq | ' + ' | '.join(M) + ' |', '|---|' + '--:|' * len(M)]
for s in SEQS:
    cells = []
    for m in M:
        v = list(D[s][m].values())
        if not v:
            cells.append('-'); continue
        nf = sum(x > FAIL_M for x in v)
        med = float(np.median(np.minimum(v, 1e4)))
        cells.append(f'{med:.3f}' + (f' [{nf}]' if nf else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
    L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
L.append('\n| failures (all) | ' + ' | '.join(str(sum(sum(x > FAIL_M for x in D[s][m].values()) for s in SEQS)) for m in M) + ' |')
GROUPS = {'L0+L1': ['L0', 'L1'], 'L2+L3': ['L2', 'L3'], 'all': ['L0', 'L1', 'L2', 'L3'], 'hall_L3': ['hall_t1_L3'], 'L2': ['L2'], 'L3': ['L3']}
res = []
for ref in refs:
    for g, pats in GROUPS.items():
        fam = []
        for m in M:
            if m == ref:
                continue
            x = []
            for s in SEQS:
                if not any(s.endswith(p) or s == p for p in pats):
                    continue
                for i in IDX:
                    if i in D[s][m] and i in D[s][ref]:
                        x.append(lr(D[s][m][i], D[s][ref][i]))
            x = np.array(x)
            if x.size < 5:
                continue
            nz = x[x != 0]
            p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
            ci = boot(x)
            fam.append(dict(ref=ref, group=g, method=m, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1),
                            ci=[100 * (math.exp(c) - 1) for c in ci], wins=int((x < 0).sum()), losses=int((x > 0).sum()), p=p))
        for r, h in zip(fam, holm([r['p'] for r in fam]) if fam else []):
            r['holm'] = float(h)
        res += fam
for ref in refs:
    L += [f'\n## Paired vs {ref} (geometric-mean {METRIC.upper()} ratio - 1; negative = better; Holm over the methods within each group)\n',
          '| method | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    for m in M:
        if m == ref:
            continue
        cells = []
        for g in GROUPS:
            r = [x for x in res if x['ref'] == ref and x['group'] == g and x['method'] == m]
            if not r:
                cells.append('-'); continue
            r = r[0]
            cells.append(f"{r['gm']:+.0f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.3f} (H {r['holm']:.3f}) {r['wins']}/{r['losses']}")
        L.append(f'| {m} | ' + ' | '.join(cells) + ' |')
os.makedirs(OUT, exist_ok=True)
open(f'{OUT}/{METRIC}_{tag}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'median': {s: {m: D[s][m] for m in M} for s in SEQS}, 'paired': res}, open(f'{OUT}/{METRIC}_{tag}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
