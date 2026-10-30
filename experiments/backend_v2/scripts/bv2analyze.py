#!/usr/bin/env python3
"""bv2analyze.py [--metric ate|rpe] [--set t1|t2|viode] : back-end v2 analysis (t1 validation; t2 / viode = held-out, run only after the freeze) (statistics of results/p7/scripts/p7analyze.py and
results/m2b_heldout/scripts/m2banalyze.py: paired per-offset log ratios, failures capped at 10 m, geometric-mean ratio - 1,
95 % bootstrap CI (20000, seed 0), Wilcoxon signed-rank, Holm within each family; failure = ATE > 2 m; RPE = mean trans.
error over the shortest rpg sub-length, failed runs = inf -> capped).
Families (Holm within each family x group):
  vs_openvins_v2 / vs_openvins_v1 : every masking method vs OpenVINS of the same back-end
  key_v2 / key_v1                 : SAVIOR vs Y-Cls, SAVIOR-adaptive vs Y-Cls, SAVIOR-edge vs SAVIOR, O-Dyn+B vs O-Cls+B, O-Dyn vs O-Cls
  v2_vs_v1                        : each method, v2 / v1 at the same offset
  gain_change                     : (m/ref)_v2 vs (m/ref)_v1, i.e. log(m2/r2) - log(m1/r1) per offset, for the key pairs and
                                    every method vs OpenVINS (negative = the relative gain got LARGER with v2)
v1 runs: results/p6_warehouse (openvins, savior_none, oracle_moving, oracle_moving_ext, oracle_class_naive, yolo_naive),
results/p7 (oracle_class_ext, sens_fix1, p7_nb), results/backend_v2/runs_v1 (savior_edge, frozen_edge install).
Held-out sets: v2 runs in results/backend_v2/heldout/runs, v1 = results/m2b_heldout/runs.
-> results/backend_v2/tables/<metric>_<set>.md / .json"""
import json, math, os, sys
import numpy as np, yaml
from scipy import stats
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
H = R + '/backend_v2'
METRIC = sys.argv[sys.argv.index('--metric') + 1] if '--metric' in sys.argv else 'ate'
SET = sys.argv[sys.argv.index('--set') + 1] if '--set' in sys.argv else 't1'   # t1 | t2 | viode (t2/viode: held-out, after the freeze)
IDX = list(range(1, 11))
CAP_M = 10.0
M = ['openvins', 'savior_none', 'oracle_moving', 'oracle_moving_ext', 'oracle_class_naive', 'oracle_class_ext', 'yolo_naive',
     'sens_fix1', 'p7_nb', 'savior_edge']
LAB = yaml.safe_load(open(H + '/backend_config.yaml'))['paper_labels']
MASK = [m for m in M if m not in ('openvins', 'savior_none')]
KEY = [('sens_fix1', 'yolo_naive'), ('p7_nb', 'yolo_naive'), ('savior_edge', 'sens_fix1'), ('oracle_moving_ext', 'oracle_class_ext'),
       ('oracle_moving', 'oracle_class_naive')]
lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
if SET == 't1':
    SEQS = [f'{s}_t1_{l}' for s in ('aisles', 'hall') for l in ('L0', 'L1', 'L2', 'L3')]
    FAIL_M = 2.0
    RUNS2 = H + '/runs'
    V1 = {m: R + '/p6_warehouse' for m in ('openvins', 'savior_none', 'oracle_moving', 'oracle_moving_ext', 'oracle_class_naive', 'yolo_naive')}
    V1.update({m: R + '/p7' for m in ('oracle_class_ext', 'sens_fix1', 'p7_nb')})
    V1['savior_edge'] = H + '/runs_v1'
    GROUPS = {'L0': lambda s: lev(s) == 'L0', 'L1': lambda s: lev(s) == 'L1', 'L2': lambda s: lev(s) == 'L2', 'L3': lambda s: lev(s) == 'L3',
              'L0+L1': lambda s: lev(s) in ('L0', 'L1'), 'L2+L3': lambda s: lev(s) in ('L2', 'L3'),
              'hall_L3': lambda s: s == 'hall_t1_L3', 'all': lambda s: True}
else:   # held-out: v1 = the M2b runs (no v1 runs of the two no-band oracles)
    A = yaml.safe_load(open(R + '/p7/final_config_addendum.yaml'))
    RUNS2 = H + '/heldout/runs'
    V1 = {m: R + '/m2b_heldout/runs' for m in M}
    if SET == 't2':
        SEQS = A['warehouse_heldout']['sequences']
        FAIL_M = 2.0
        GROUPS = {'L0': lambda s: lev(s) == 'L0', 'L1': lambda s: lev(s) == 'L1', 'L2': lambda s: lev(s) == 'L2', 'L3': lambda s: lev(s) == 'L3',
                  'L0+L1': lambda s: lev(s) in ('L0', 'L1'), 'L2+L3': lambda s: lev(s) in ('L2', 'L3'),
                  'hall_L3': lambda s: s == 'hall_t2_L3', 'dock_L3': lambda s: s == 'dock_t2_L3',
                  'hall+dock_L3': lambda s: s in ('hall_t2_L3', 'dock_t2_L3'), 'all': lambda s: True}
    else:
        SEQS = A['viode']['sequences']
        FAIL_M = A['viode']['failure_threshold_m']
        GROUPS = {g: (lambda s, g=g: g == 'all' or lev(s) in g.split('+')) for g in A['analysis_plan']['groups_viode']}


def load(base, seq, m):
    fn = f'{base}/{seq}/{m}/eval/eval_summary.yaml'
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


D = {'v2': {s: {m: load(RUNS2, s, m) for m in M} for s in SEQS},
     'v1': {s: {m: load(V1[m], s, m) for m in M} for s in SEQS}}
missing = [(b, s, m, i) for b in D for s in SEQS for m in M for i in IDX if i not in D[b][s][m]]


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


def summ(x, **kw):
    x = np.array(x)
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    ci = boot(x)
    return dict(kw, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1), ci=[100 * (math.exp(c) - 1) for c in ci],
                wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), p=p)


def pairs_x(b, m, ref, sel):
    return [lr(D[b][s][m][i], D[b][s][ref][i]) for s in SEQS if sel(s) for i in IDX if i in D[b][s][m] and i in D[b][s][ref]]


res = []
FAM = {'vs_openvins_v2': [('v2', m, 'openvins') for m in MASK], 'vs_openvins_v1': [('v1', m, 'openvins') for m in MASK],
       'key_v2': [('v2', m, r) for m, r in KEY], 'key_v1': [('v1', m, r) for m, r in KEY]}
for fam, items in FAM.items():
    for g, sel in GROUPS.items():
        rs = [summ(pairs_x(b, m, ref, sel), family=fam, backend=b, method=m, ref=ref, group=g) for b, m, ref in items
              if len(pairs_x(b, m, ref, sel)) >= 5]
        for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
            r['holm'] = float(h)
        res += rs
for g, sel in GROUPS.items():   # v2 vs v1 per method (same offset)
    rs = []
    for m in M:
        x = [lr(D['v2'][s][m][i], D['v1'][s][m][i]) for s in SEQS if sel(s) for i in IDX if i in D['v2'][s][m] and i in D['v1'][s][m]]
        if len(x) >= 5:
            rs.append(summ(x, family='v2_vs_v1', backend='v2/v1', method=m, ref=m, group=g))
    for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
        r['holm'] = float(h)
    res += rs
for g, sel in GROUPS.items():   # change of the relative gain (difference in differences)
    rs = []
    for m, ref in KEY + [(m, 'openvins') for m in MASK]:
        x = [lr(D['v2'][s][m][i], D['v2'][s][ref][i]) - lr(D['v1'][s][m][i], D['v1'][s][ref][i]) for s in SEQS if sel(s) for i in IDX
             if all(i in D[b][s][k] for b in D for k in (m, ref))]
        if len(x) >= 5:
            rs.append(summ(x, family='gain_change', backend='v2-v1', method=m, ref=ref, group=g))
    for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
        r['holm'] = float(h)
    res += rs

nf = {b: {m: {g: sum(sum(v > FAIL_M for v in D[b][s][m].values()) for s in SEQS if sel(s)) for g, sel in GROUPS.items()} for m in M}
      for b in D}
if METRIC == 'ate':   # failures are defined on ATE; for RPE the same runs are inf
    pass


def get(fam, m, ref, g):
    return next((x for x in res if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g), None)


def cell(r):
    if r is None:
        return '-'
    s = f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.2g} H={r['holm']:.2g} {r['wins']}/{r['losses']}"
    return f'**{s}**' if r['holm'] < 0.05 else s


GT = list(GROUPS)
U = METRIC.upper()
L = [f'# Back-end v2, set {SET}: {U} ({len(SEQS)} sequences x 10 offsets; failure = ATE > {FAIL_M:g} m, capped at {CAP_M:g} m)\n',
     f'Cells: geometric-mean {U} ratio - 1 [95 % bootstrap CI], Wilcoxon p, Holm-adjusted p (H), wins/losses of the paired offsets. '
     'Negative = first method better. Bold = Holm < 0.05.\n']
for b in ('v2', 'v1'):
    L += [f'## Median {U} [m], back-end {b} ([k] = failures > {FAIL_M:g} m)\n', '| seq | ' + ' | '.join(LAB[m] for m in M) + ' |',
          '|---|' + '--:|' * len(M)]
    for s in SEQS:
        cs = []
        for m in M:
            v = list(D[b][s][m].values())
            if not v:
                cs.append('-'); continue
            k = sum(x > FAIL_M for x in v) if METRIC == 'ate' else sum(math.isinf(x) for x in v)
            cs.append(f'{float(np.median(np.minimum(v, 1e4))):.3f}' + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
        L.append(f'| {s} | ' + ' | '.join(cs) + ' |')
    L.append('')
L += [f'## Failures (ATE > {FAIL_M:g} m) per group, v2 / v1\n', '| group | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for g in GT:
    L.append(f'| {g} | ' + ' | '.join(f"{nf['v2'][m][g]} / {nf['v1'][m][g]}" for m in M) + ' |')
TITLE = {'vs_openvins_v2': 'Each method vs OpenVINS, back-end v2 (Holm over 8 methods)',
         'vs_openvins_v1': 'Each method vs OpenVINS, back-end v1 (reference; Holm over 8 methods)',
         'key_v2': 'Key head-to-head comparisons, back-end v2 (Holm over 5 pairs)',
         'key_v1': 'Key head-to-head comparisons, back-end v1 (reference; Holm over 5 pairs)',
         'v2_vs_v1': 'Back-end v2 vs v1 per method, same offset (Holm over 10 methods)',
         'gain_change': 'Change of the relative effect, (m/ref)_v2 vs (m/ref)_v1 (difference of paired log ratios; Holm over 13; '
                        'negative = effect more favourable to m with v2)'}
for fam in ('vs_openvins_v2', 'key_v2', 'v2_vs_v1', 'gain_change', 'vs_openvins_v1', 'key_v1'):
    rows = sorted({(x['method'], x['ref']) for x in res if x['family'] == fam},
                  key=lambda mr: ([m for m, _ in KEY].index(mr[0]) if fam in ('key_v2', 'key_v1') else M.index(mr[0]),
                                  M.index(mr[1])))
    if fam == 'gain_change':
        rows = [r for r in KEY + [(m, 'openvins') for m in MASK] if r in rows]
    L += [f'\n## {TITLE[fam]}\n', '| comparison | ' + ' | '.join(GT) + ' |', '|---|' + '---|' * len(GT)]
    for m, ref in rows:
        name = LAB[m] if fam == 'v2_vs_v1' else f'{LAB[m]} vs {LAB[ref]}'
        L.append(f'| {name} | ' + ' | '.join(cell(get(fam, m, ref, g)) for g in GT) + ' |')
if missing:
    L.append(f'\n**MISSING runs: {len(missing)}** ' + ', '.join(f'{b}/{s}/{m}/{i}' for b, s, m, i in missing[:40]))
os.makedirs(H + '/tables', exist_ok=True)
open(f'{H}/tables/{METRIC}_{SET}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': D, 'paired': res, 'failures': nf, 'fail_m': FAIL_M, 'labels': LAB}, open(f'{H}/tables/{METRIC}_{SET}.json', 'w'),
          indent=1, default=str)
print('\n'.join(L))
