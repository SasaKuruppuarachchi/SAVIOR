#!/usr/bin/env python3
"""m2banalyze.py --dataset warehouse|viode [--metric ate|rpe] : M2b held-out analysis, pre-specified in
results/p7/final_config_addendum.yaml (analysis_plan) = the P6/P7 statistics (p7analyze.py): median matrix with failures,
paired per-offset log ratios (failures capped at 10 m) vs references, geometric-mean ratio - 1, 95 % bootstrap CI (20000,
seed 0), Wilcoxon signed-rank, Holm within each (dataset, group, reference) family. -> results/m2b_heldout/tables/"""
import json, math, os, sys
import numpy as np, yaml
from scipy import stats
WS = '/home/sasa/workspace/savior_ws'
H = WS + '/results/m2b_heldout'
R = H + '/runs'
A = yaml.safe_load(open(WS + '/results/p7/final_config_addendum.yaml'))
AP = A['analysis_plan']
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
DS = arg('--dataset', 'warehouse')
METRIC = arg('--metric', 'ate')
M = A['final_methods']
LAB = A['paper_labels']
if DS == 'warehouse':
    SEQS = A['warehouse_heldout']['sequences']
    FAIL_M = 2.0
    lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
    GROUPS = {g: (lambda s, g=g: (g == 'all') or (lev(s) in g.split('+')) or
                  (g.endswith('_L3') and lev(s) == 'L3' and s.split('_')[0] in g[:-3].split('+'))) for g in AP['groups_warehouse']}
else:
    SEQS = A['viode']['sequences']
    FAIL_M = A['viode']['failure_threshold_m']
    lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
    GROUPS = {g: (lambda s, g=g: (g == 'all') or (lev(s) in g.split('+'))) for g in AP['groups_viode']}
CAP_M = 10.0
IDX = list(range(1, 11))


def load(seq, m):
    fn = f'{R}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                out[i] = math.inf; continue
            ate = t['ate']['trans_m']['rmse']
            if METRIC == 'rpe':
                ks = sorted(t['rpe'], key=float)
                out[i] = t['rpe'][ks[0]]['trans_m']['mean'] if ate <= FAIL_M else math.inf
            else:
                out[i] = ate
    return {i: v for i, v in out.items() if i in IDX}


D = {s: {m: load(s, m) for m in M} for s in SEQS}
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
for ref, ms in AP['references'].items():
    for g, sel in GROUPS.items():
        fam = []
        for m in ms:
            x = [lr(D[s][m][i], D[s][ref][i]) for s in SEQS if sel(s) for i in IDX if i in D[s][m] and i in D[s][ref]]
            x = np.array(x)
            if x.size < 5:
                continue
            nz = x[np.abs(x) > 1e-12]
            p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
            ci = boot(x)
            fam.append(dict(dataset=DS, metric=METRIC, ref=ref, group=g, method=m, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1),
                            ci=[100 * (math.exp(c) - 1) for c in ci], wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), p=p))
        for r, h in zip(fam, holm([r['p'] for r in fam]) if fam else []):
            r['holm'] = float(h)
        res += fam
nf = {m: {g: sum(sum(v > FAIL_M for v in D[s][m].values()) for s in SEQS if sel(s)) for g, sel in GROUPS.items()} for m in M}
L = [f'# M2b held-out {DS} {METRIC.upper()} ({len(SEQS)} sequences x 10 offsets; failure = ATE > {FAIL_M:g} m, capped at {CAP_M:g} m)\n',
     f'## Median {METRIC.upper()} [m] ([n] = failures)\n', '| seq | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for s in SEQS:
    cells = []
    for m in M:
        v = list(D[s][m].values())
        if not v:
            cells.append('-'); continue
        k = sum(x > FAIL_M for x in (D[s][m].values() if METRIC == 'ate' else [x for x in v]))
        cells.append(f'{float(np.median(np.minimum(v, 1e4))):.3f}' + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
    L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
L.append('\n## Failures per group\n')
L += ['| group | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for g in GROUPS:
    L.append(f'| {g} | ' + ' | '.join(str(nf[m][g]) for m in M) + ' |')
for ref, ms in AP['references'].items():
    L += [f'\n## Paired vs {LAB[ref]} (geometric-mean {METRIC.upper()} ratio - 1; negative = better; Holm over {len(ms)} methods per group)\n',
          '| method | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    for m in ms:
        cells = []
        for g in GROUPS:
            r = next((x for x in res if x['ref'] == ref and x['group'] == g and x['method'] == m), None)
            cells.append('-' if r is None else
                         f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.3g} H={r['holm']:.3g} {r['wins']}/{r['losses']}")
        L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
if missing:
    L.append(f'\n**MISSING runs: {len(missing)}** ' + ', '.join(f'{s}/{m}/{i}' for s, m, i in missing[:30]))
os.makedirs(H + '/tables', exist_ok=True)
open(f'{H}/tables/{METRIC}_{DS}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': {s: {m: D[s][m] for m in M} for s in SEQS}, 'paired': res, 'failures': nf, 'fail_m': FAIL_M},
          open(f'{H}/tables/{METRIC}_{DS}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
