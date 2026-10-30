#!/usr/bin/env python3
"""sg_analyze.py [--metric ate|rpe] : SAVIOR-SG t1 analysis with the statistics of results/backend_v2/scripts/bv2analyze.py
(paired per-offset log ratios, failures capped at 10 m, geometric-mean ratio - 1, 95 % bootstrap CI (20000, seed 0),
Wilcoxon signed-rank, Holm within each (family, group); failure = ATE > 2 m; RPE = mean trans. error over the shortest rpg
sub-length, failed runs = inf -> capped) and the pre-declared selection rule of GRID.yaml.
Sources: openvins / sens_fix1 / yolo_naive = results/backend_v2/runs; ovchi_best = results/review_runs/runs/t1/*/ovchi_025;
SG / NIS / sf1_chibest = results/semantic_gate/runs. Grid points with m_b != m_s use their m_b = m_s twin when the audit shows
them md5-identical on the inertness subset (GRID.yaml run_plan). -> tables/<metric>_t1.md / .json"""
import csv, json, math, os, sys
import numpy as np, yaml
from scipy import stats
WS = '/home/sasa/workspace/savior_ws'
SG = f'{WS}/results/semantic_gate'
METRIC = sys.argv[sys.argv.index('--metric') + 1] if '--metric' in sys.argv else 'ate'
IDX = list(range(1, 11))
CAP_M, FAIL_M = 10.0, 2.0
SEQS = [f'{s}_t1_{l}' for s in ('aisles', 'hall') for l in ('L0', 'L1', 'L2', 'L3')]
SRC = {'openvins': f'{WS}/results/backend_v2/runs', 'sens_fix1': f'{WS}/results/backend_v2/runs',
       'yolo_naive': f'{WS}/results/backend_v2/runs', 'ovchi_best': f'{WS}/results/review_runs/runs/t1'}
DIRNAME = {'ovchi_best': 'ovchi_025'}
GRID = [f'sg_s{s}_b{b}_kb{k}' for s in ('025', '050') for b in ('025', '050') for k in (0, 1)]
OWN = GRID + ['sf1_nis', 'ov_nis', 'sf1_chibest']
LAB = {'openvins': 'OpenVINS-v2', 'sens_fix1': 'SAVIOR', 'yolo_naive': 'Y-Cls', 'ovchi_best': 'OV-chi2 x0.25',
       'sf1_chibest': 'SAVIOR+chi2 x0.25', 'sf1_nis': 'SAVIOR+NIS', 'ov_nis': 'OV+NIS'}
for g in GRID:
    LAB[g] = 'SG ' + g[3:]
lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
GROUPS = {'L0': lambda s: lev(s) == 'L0', 'L1': lambda s: lev(s) == 'L1', 'L2': lambda s: lev(s) == 'L2', 'L3': lambda s: lev(s) == 'L3',
          'L0+L1': lambda s: lev(s) in ('L0', 'L1'), 'L2+L3': lambda s: lev(s) in ('L2', 'L3'),
          'hall_L3': lambda s: s == 'hall_t1_L3', 'all': lambda s: True}


def load(base, seq, m):
    fn = f'{base}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                out[i] = math.inf
                continue
            ate = t['ate']['trans_m']['rmse']
            if METRIC == 'rpe':
                ks = sorted(t['rpe'], key=float)
                out[i] = t['rpe'][ks[0]]['trans_m']['mean'] if ate <= FAIL_M else math.inf
            else:
                out[i] = ate
    return {i: v for i, v in out.items() if i in IDX}


# inertness (audit): m_b != m_s point identical to its twin on every compared run -> use the twin's full-t1 values
alias = {}
aud = f'{SG}/tables/audit.csv'
if os.path.isfile(aud):
    rows = list(csv.DictReader(open(aud)))
    for g in GRID:
        if g[4:7] == g[9:12]:
            continue
        rr = [r for r in rows if r['method'] == g]
        twin = f'sg_s{g[4:7]}_b{g[4:7]}_kb{g[-1]}'
        band = sum(int(r[f'{k}_tested'].split('/')[2]) for r in rows if r['method'] == twin for k in ('msckf', 'slam')
                   if r[f'{k}_tested'])
        if rr and all(r['identical'] == '1' for r in rr) and band == 0:
            alias[g] = twin
M = ['openvins', 'sens_fix1', 'yolo_naive', 'ovchi_best', 'sf1_chibest', 'ov_nis', 'sf1_nis'] + GRID
D = {}
for s in SEQS:
    D[s] = {}
    for m in M:
        src = alias.get(m, m)
        D[s][m] = load(SRC.get(src, f'{SG}/runs'), s, DIRNAME.get(src, src))
complete = {m: all(len(D[s][m]) == 10 for s in SEQS) for m in M}
missing = [(s, m, i) for s in SEQS for m in M for i in IDX if i not in D[s][m] and complete.get(m) is False and
           sum(len(D[x][m]) for x in SEQS) > 20]


def lr(a, b):
    return math.log(min(a, CAP_M) / min(b, CAP_M))


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (n, x.size)).mean(axis=1), [2.5, 97.5])


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def summ(x, **kw):
    x = np.array(x)
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    ci = boot(x)
    return dict(kw, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1), ci=[100 * (math.exp(c) - 1) for c in ci],
                wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), p=p)


def pairs_x(m, ref, sel):
    return [lr(D[s][m][i], D[s][ref][i]) for s in SEQS if sel(s) for i in IDX if i in D[s][m] and i in D[s][ref]]


avail = [m for m in M if complete[m]]
REPS = [g for g in GRID if complete[g] and g not in alias]
FAM = {'vs_openvins': [(m, 'openvins') for m in avail if m != 'openvins'],
       'vs_sens_fix1': [(m, 'sens_fix1') for m in REPS + ['sf1_nis', 'sf1_chibest', 'ovchi_best'] if m in avail],
       'vs_ovchi_best': [(m, 'ovchi_best') for m in REPS + ['ov_nis', 'sf1_nis', 'sens_fix1', 'sf1_chibest'] if m in avail]}
res = []
for fam, items in FAM.items():
    for g, sel in GROUPS.items():
        rs = [summ(pairs_x(m, ref, sel), family=fam, method=m, ref=ref, group=g) for m, ref in items if len(pairs_x(m, ref, sel)) >= 5]
        for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
            r['holm'] = float(h)
        res += rs
nf = {m: {g: sum(sum(v > FAIL_M for v in D[s][m].values()) for s in SEQS if sel(s)) for g, sel in GROUPS.items()} for m in avail}


def get(fam, m, ref, g):
    return next((x for x in res if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g), None)


def cell(r):
    if r is None:
        return '-'
    s = f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.2g} H={r['holm']:.2g} {r['wins']}/{r['losses']}"
    return f'**{s}**' if r['holm'] < 0.05 else s


# ---- pre-declared selection rule (GRID.yaml): lowest gm vs openvins on "all", 0 failures, not significantly worse than SAVIOR at L0
sel_rows = []
for g in GRID:
    src = alias.get(g, g)
    if not complete.get(src):
        continue
    a = get('vs_openvins', src, 'openvins', 'all')
    l0 = get('vs_sens_fix1', src, 'sens_fix1', 'L0')
    ok_f = nf[src]['all'] == 0
    ok_l0 = l0 is not None and not (l0['ci'][0] > 0)
    sel_rows.append(dict(point=g, result_of=src, gm_all_vs_ov=a['gm'], fails=nf[src]['all'], l0_vs_sf1=l0['gm'], l0_ci=l0['ci'],
                         eligible=ok_f and ok_l0))
elig = [r for r in sel_rows if r['eligible']]
best = min(elig, key=lambda r: (round(r['gm_all_vs_ov'], 9), 0 if r['point'] == r['result_of'] else 1)) if elig else None

GT = list(GROUPS)
U = METRIC.upper()
L = [f'# SAVIOR-SG, warehouse t1: {U} (8 sequences x 10 offsets; failure = ATE > {FAIL_M:g} m, capped at {CAP_M:g} m)\n',
     f'Cells: geometric-mean {U} ratio - 1 [95 % bootstrap CI], Wilcoxon p, Holm-adjusted p (H, within family x group), wins/losses '
     'of the paired offsets. Negative = first method better. Bold = Holm < 0.05. t1 is the tuning split of SAVIOR, the back-end v2 '
     'and the chi2 x0.25 value: every number here is optimistic.\n']
if alias:
    L.append('Grid points reported through their m_b = m_s twin (md5-identical on the inertness subset, 0 band-labelled chi2 tests): '
             + ', '.join(f'{k} = {v}' for k, v in sorted(alias.items())) + '\n')
L += [f'## Median {U} [m] ([k] = failures > {FAIL_M:g} m)\n', '| seq | ' + ' | '.join(LAB[m] for m in avail) + ' |', '|---|' + '--:|' * len(avail)]
for s in SEQS:
    cs = []
    for m in avail:
        v = list(D[s][m].values())
        k = sum(x > FAIL_M for x in v) if METRIC == 'ate' else sum(math.isinf(x) for x in v)
        cs.append(f'{float(np.median(np.minimum(v, 1e4))):.3f}' + (f' [{k}]' if k else ''))
    L.append(f'| {s} | ' + ' | '.join(cs) + ' |')
L += ['', f'## Failures (ATE > {FAIL_M:g} m) per group\n', '| group | ' + ' | '.join(LAB[m] for m in avail) + ' |', '|---|' + '--:|' * len(avail)]
for g in GT:
    L.append(f'| {g} | ' + ' | '.join(str(nf[m][g]) for m in avail) + ' |')
TITLE = {'vs_openvins': 'Each method vs OpenVINS-v2 (Holm over the family)', 'vs_sens_fix1': 'Gate variants vs SAVIOR (sens_fix1)',
         'vs_ovchi_best': 'Descriptive: vs the t1-tuned global chi2 x0.25 (OV-chi2, selected on these data)'}
for fam in FAM:
    L += [f'\n## {TITLE[fam]}\n', '| comparison | ' + ' | '.join(GT) + ' |', '|---|' + '---|' * len(GT)]
    for m, ref in FAM[fam]:
        L.append(f'| {LAB[m]} vs {LAB[ref]} | ' + ' | '.join(cell(get(fam, m, ref, g)) for g in GT) + ' |')
if METRIC == 'ate':
    L += ['\n## Pre-declared selection (GRID.yaml)\n', '| grid point | result of | gm vs OpenVINS-v2 (all) | failures (80) | vs SAVIOR at L0 [CI] | eligible |',
          '|---|---|--:|--:|---|---|']
    for r in sel_rows:
        L.append(f"| {r['point']} | {r['result_of']} | {r['gm_all_vs_ov']:+.1f} % | {r['fails']} | {r['l0_vs_sf1']:+.1f} % "
                 f"[{r['l0_ci'][0]:+.0f}, {r['l0_ci'][1]:+.0f}] | {'yes' if r['eligible'] else 'no'} |")
    L.append(f"\n**Selected: {best['point'] if best else 'none (no point satisfies the constraints)'}**"
             + (f" (result of {best['result_of']}, {best['gm_all_vs_ov']:+.1f} % vs OpenVINS-v2 on all)" if best else ''))
if missing:
    L.append(f'\n**MISSING runs: {len(missing)}** ' + ', '.join(f'{s}/{m}/{i}' for s, m, i in missing[:40]))
os.makedirs(f'{SG}/tables', exist_ok=True)
open(f'{SG}/tables/{METRIC}_t1.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': D, 'paired': res, 'failures': nf, 'alias': alias, 'selection': sel_rows, 'selected': best and best['point'],
           'labels': LAB}, open(f'{SG}/tables/{METRIC}_t1.json', 'w'), indent=1, default=str)
print('\n'.join(L))
