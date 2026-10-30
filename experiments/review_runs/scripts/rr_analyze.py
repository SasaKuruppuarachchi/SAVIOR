#!/usr/bin/env python3
"""rr_analyze.py --set t1|t2|viode [--metric ate|rpe] [--chi2best tag] : paired statistics of the review runs.
Statistics = results/backend_v2/scripts/bv2analyze.py (paired per-offset log ratio, failures capped at 10 m, geometric-mean
ratio - 1, bootstrap 95 % CI over the pooled pairs (20000, seed 0), Wilcoxon signed-rank, Holm within each family x group)
PLUS the sequence-level analysis of results/stats_v3/scripts/stats3_core.py (functions imported, not copied): estimate =
exp(mean of per-sequence mean log ratios) - 1, two-stage cluster bootstrap CI (sequences, then offsets; 20000, seed 0), exact
sign-flip permutation p on the per-sequence means, REML random-intercept LMM p (df = k - 1).
Reference runs (existing back-end v2): t1 results/backend_v2/runs, held-out results/backend_v2/heldout/runs.
Review variants: results/review_runs/runs/{t1,heldout}. -> results/review_runs/tables/<metric>_<set>.md / .json"""
import json, math, os, sys
import numpy as np, yaml
from scipy import stats
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/stats_v3/scripts')
from stats3_core import boot_two_stage, signflip, reml_ri  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
RR = R + '/review_runs'
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
SET, METRIC = arg('--set', 't1'), arg('--metric', 'ate')
IDX = list(range(1, 11))
CAP = 10.0
A = yaml.safe_load(open(R + '/p7/final_config_addendum.yaml'))
lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
LAB = {'openvins': 'OpenVINS', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR-adaptive',
       'sf1_noint': 'SAVIOR w/o interaction', 'sf1_nomotion': 'SAVIOR w/o motion', 'ovchi_050': 'OV chi2x0.5',
       'ovchi_025': 'OV chi2x0.25', 'ovchi_010': 'OV chi2x0.1', 'ovchi_best': 'OV-chi2 (tuned)', 'sf1_chibest': 'SAVIOR+OV-chi2',
       'oracle_moving_ext': 'O-Dyn+B', 'oracle_class_ext': 'O-Cls+B'}
for d in range(5):
    LAB[f'gate_fix{d}'] = f'fixed {d} m'
for k in (1, 2, 3, 4):
    LAB[f'gate_k{k}'] = f'adaptive k={k}'
for k in (1, 3):
    LAB[f'gate_kmed{k}'] = f'adaptive-median k={k}'
REUSE = {'gate_fix1': 'sens_fix1', 'gate_k3': 'p7_nb'}
if SET == 't1':
    SEQS = [f'{s}_t1_{l}' for s in ('aisles', 'hall') for l in ('L0', 'L1', 'L2', 'L3')]
    REF, RUNS, FAIL = R + '/backend_v2/runs', RR + '/runs/t1', 2.0
    GROUPS = {'L0': ['L0'], 'L1': ['L1'], 'L2': ['L2'], 'L3': ['L3'], 'L0+L1': ['L0', 'L1'], 'L2+L3': ['L2', 'L3'], 'hall_L3': 'hall_t1_L3',
              'all': None}
    GATE = [f'gate_fix{d}' for d in range(5)] + [f'gate_k{k}' for k in (1, 2, 3, 4)] + ['gate_kmed1', 'gate_kmed3']
    CHI = ['ovchi_050', 'ovchi_025', 'ovchi_010']
    M = ['openvins', 'yolo_naive', 'sens_fix1', 'p7_nb'] + CHI + GATE
    FAM = {'B_chi2_vs_openvins': [(m, 'openvins') for m in CHI],
           'C_gate_vs_ycls': [(m, 'yolo_naive') for m in GATE],
           'C_gate_vs_savior': [(m, 'sens_fix1') for m in GATE if m != 'gate_fix1']}
else:
    REF, RUNS = R + '/backend_v2/heldout/runs', RR + '/runs/heldout'
    if SET == 't2':
        SEQS, FAIL = A['warehouse_heldout']['sequences'], 2.0
        GROUPS = {g: (g.split('+') if g.startswith('L') else None if g == 'all' else
                      [f"{x.split('_')[0]}_t2_L3" for x in g.split('+')] if '+' in g else f"{g.split('_')[0]}_t2_L3")
                  for g in A['analysis_plan']['groups_warehouse']}
        GROUPS['hall+dock_L3'] = ['hall_t2_L3', 'dock_t2_L3']
    else:
        SEQS, FAIL = A['viode']['sequences'], A['viode']['failure_threshold_m']
        GROUPS = {g: (None if g == 'all' else g.split('+')) for g in A['analysis_plan']['groups_viode']}
    M = ['openvins', 'yolo_naive', 'sens_fix1', 'p7_nb', 'oracle_moving_ext', 'oracle_class_ext', 'sf1_noint', 'sf1_nomotion',
         'ovchi_best', 'sf1_chibest']
    FAM = {'A_ablation_vs_savior': [('sf1_noint', 'sens_fix1'), ('sf1_nomotion', 'sens_fix1')],
           'A_vs_ycls': [('sens_fix1', 'yolo_naive'), ('sf1_noint', 'yolo_naive'), ('sf1_nomotion', 'yolo_naive')],
           'A_vs_openvins': [('sens_fix1', 'openvins'), ('sf1_noint', 'openvins'), ('sf1_nomotion', 'openvins')],
           'B_vs_openvins': [('ovchi_best', 'openvins'), ('sf1_chibest', 'openvins')],
           'B_vs_robust': [('sens_fix1', 'ovchi_best'), ('yolo_naive', 'ovchi_best'), ('sf1_chibest', 'ovchi_best'),
                           ('sf1_chibest', 'sens_fix1')]}


def insel(s, g):
    sel = GROUPS[g]
    if sel is None:
        return True
    if isinstance(sel, str):
        return s == sel
    return (lev(s) in sel) or (s in sel)


def load(m, seq):
    base = RUNS if (m not in ('openvins', 'yolo_naive', 'sens_fix1', 'p7_nb', 'oracle_moving_ext', 'oracle_class_ext')
                    and m not in REUSE) else REF
    mm = REUSE.get(m, m)
    fn = f'{base}/{seq}/{mm}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                out[i] = math.inf; continue
            ate = t['ate']['trans_m']['rmse']
            if METRIC == 'rpe':
                ks = sorted(t['rpe'], key=float)
                out[i] = t['rpe'][ks[0]]['trans_m']['mean'] if ate <= FAIL else math.inf
            else:
                out[i] = ate
    return {i: v for i, v in out.items() if i in IDX}


D = {s: {m: load(m, s) for m in M} for s in SEQS}
lr = lambda a, b: math.log(min(a, CAP) / min(b, CAP))  # noqa: E731


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def summ(m, ref, g):
    by = [[lr(D[s][m][i], D[s][ref][i]) for i in IDX if i in D[s][m] and i in D[s][ref]] for s in SEQS if insel(s, g)]
    x = np.array([v for b in by for v in b])
    if x.size < 5:
        return None
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    rng = np.random.default_rng(0)
    ci = np.percentile(rng.choice(x, (20000, x.size)).mean(axis=1), [2.5, 97.5])
    pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731
    X = {j: np.array(b) for j, b in enumerate(by) if b}
    sm = np.array([v.mean() for v in X.values()])
    seq = None
    if len(X) >= 2:
        bt = np.percentile(boot_two_stage(X), [2.5, 97.5])
        lm = reml_ri(X)
        seq = dict(est=pc(sm.mean()), ci=[pc(c) for c in bt], p_signflip=signflip(sm)[0], p_signflip_min=signflip(sm)[1],
                   p_lmm=lm['p'] if lm else None, k=len(X), seq_wins=int((sm < -1e-12).sum()), seq_losses=int((sm > 1e-12).sum()))
    return dict(method=m, ref=ref, group=g, n=int(x.size), n_seq=len(X), gm=pc(x.mean()), ci=[pc(c) for c in ci],
                ci_cluster=seq['ci'] if seq else [None, None], seq=seq, wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()),
                p=p, identical=int((np.abs(x) <= 1e-12).sum()))


res = []
for fam, items in FAM.items():
    for g in GROUPS:
        rs = [r for r in (summ(m, ref, g) for m, ref in items) if r]
        for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
            r['holm'] = float(h); r['family'] = fam
        res += rs
nf = {m: {g: sum(sum(v > FAIL for v in D[s][m].values()) for s in SEQS if insel(s, g)) for g in GROUPS} for m in M}
nrun = {m: {g: sum(len(D[s][m]) for s in SEQS if insel(s, g)) for g in GROUPS} for m in M}


def cell(r):
    if r is None:
        return '-'
    q = r['seq']
    cls = (f" / seq {q['est']:+.0f} % [{q['ci'][0]:+.0f}, {q['ci'][1]:+.0f}] sf={q['p_signflip']:.2g} {q['seq_wins']}/{q['seq_losses']}"
           if q else '')
    s = f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] H={r['holm']:.2g} {r['wins']}/{r['losses']}{cls}"
    return f'**{s}**' if r['holm'] < 0.05 else s


U = METRIC.upper()
L = [f'# Review runs, set {SET}: {U} ({len(SEQS)} sequences x 10 offsets; failure = ATE > {FAIL:g} m, capped at {CAP:g} m)\n',
     f'Cells: RUN level: geometric-mean {U} ratio - 1 [95 % iid bootstrap CI], Holm-adjusted Wilcoxon p (H, within family x group), '
     'wins/losses of the paired offsets; / SEQUENCE level (stats_v3): exp(mean of per-sequence mean log ratios) - 1 [two-stage cluster '
     'bootstrap CI], exact sign-flip p (sf), sequences better/worse. Negative = first method better. Bold = run-level Holm < 0.05.\n', f'## Median {U} [m] per sequence ([k] = failures)\n', '| seq | ' + ' | '.join(LAB.get(m, m) for m in M) + ' |',
     '|---|' + '--:|' * len(M)]
for s in SEQS:
    cs = []
    for m in M:
        v = list(D[s][m].values())
        if not v:
            cs.append('-'); continue
        k = sum(x > FAIL for x in v) if METRIC == 'ate' else sum(math.isinf(x) for x in v)
        cs.append(f'{float(np.median(np.minimum(v, 1e4))):.3f}' + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
    L.append(f'| {s} | ' + ' | '.join(cs) + ' |')
L += ['', f'## Failures (ATE > {FAIL:g} m) / runs per group\n', '| group | ' + ' | '.join(LAB.get(m, m) for m in M) + ' |', '|---|' + '--:|' * len(M)]
for g in GROUPS:
    L.append(f'| {g} | ' + ' | '.join(f"{nf[m][g]}/{nrun[m][g]}" for m in M) + ' |')
for fam, items in FAM.items():
    L += [f'\n## {fam}\n', '| comparison | ' + ' | '.join(GROUPS) + ' |', '|---|' + '---|' * len(GROUPS)]
    for m, ref in items:
        L.append(f'| {LAB.get(m, m)} vs {LAB.get(ref, ref)} | ' + ' | '.join(
            cell(next((x for x in res if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g), None)) for g in GROUPS) + ' |')
missing = [(s, m, i) for s in SEQS for m in M for i in IDX if i not in D[s][m]]
if missing:
    L.append(f'\n**MISSING runs: {len(missing)}** ' + ', '.join(f'{s}/{m}/{i}' for s, m, i in missing[:30]))
os.makedirs(RR + '/tables', exist_ok=True)
open(f'{RR}/tables/{METRIC}_{SET}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': D, 'paired': res, 'failures': nf, 'runs': nrun, 'fail_m': FAIL, 'labels': LAB, 'missing': len(missing)},
          open(f'{RR}/tables/{METRIC}_{SET}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
