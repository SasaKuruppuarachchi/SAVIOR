#!/usr/bin/env python3
"""rr_analyze_e.py [--metric ate|rpe] : task E (OpenLORIS + uHumans2, original back-end) paired statistics, identical estimators to
rr_analyze.py (run level: geometric-mean ratio, iid bootstrap, Wilcoxon, Holm within family x group; sequence level: stats_v3
functions). Separate script so that the frozen rr_analyze.py stays unchanged. Failure > 1 m (FREEZE.yaml protocol), cap 10 m.
Also: P2-offset subset (runs 1-3 = offsets 0.0/0.2/0.4, the P2 protocol) and a reproduction check of e_openvins vs the P2/P4/P7-D
openvins runs (trajectory md5 by start offset). -> tables/<metric>_e.md / .json"""
import glob, hashlib, json, math, os, sys
import numpy as np, yaml
from scipy import stats
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/stats_v3/scripts')
from stats3_core import boot_two_stage, signflip, reml_ri  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
RR = R + '/review_runs'
RUNS = RR + '/runs/e'
METRIC = sys.argv[sys.argv.index('--metric') + 1] if '--metric' in sys.argv else 'ate'
CAP, FAIL = 10.0, 1.0
OL = ['cafe1-1', 'cafe1-2', 'office1-1', 'office1-2', 'office1-3', 'office1-4', 'office1-5', 'office1-6', 'office1-7']
SEQS = [f'openloris_{s}' for s in OL] + [f'uhumans2_office_s1_{h}' for h in ('00h', '06h', '12h')]
M = ['e_openvins', 'e_savior_none', 'e_yolo_naive', 'e_sens_fix1', 'e_oracle_person']
LAB = {'e_openvins': 'OpenVINS', 'e_savior_none': 'SAVIOR-none', 'e_yolo_naive': 'Y-Cls', 'e_sens_fix1': 'SAVIOR', 'e_oracle_person': 'oracle person'}
HO = [f'openloris_{s}' for s in OL[1:]]
GROUPS = {'openloris_heldout': (HO, None), 'openloris_heldout_P2offsets': (HO, [1, 2, 3]), 'openloris_cafe1-1': (['openloris_cafe1-1'], None),
          'openloris_people': (['openloris_cafe1-2', 'openloris_office1-5', 'openloris_office1-6', 'openloris_office1-7'], None),
          'openloris_all': ([f'openloris_{s}' for s in OL], None),
          'uhumans2_00h': (['uhumans2_office_s1_00h'], None), 'uhumans2_06h': (['uhumans2_office_s1_06h'], None),
          'uhumans2_12h': (['uhumans2_office_s1_12h'], None), 'uhumans2_06h+12h': (['uhumans2_office_s1_06h', 'uhumans2_office_s1_12h'], None),
          'uhumans2_all': ([f'uhumans2_office_s1_{h}' for h in ('00h', '06h', '12h')], None)}
FAM = {'E_vs_openvins': [('e_sens_fix1', 'e_openvins'), ('e_yolo_naive', 'e_openvins'), ('e_oracle_person', 'e_openvins')],
       'E_savior_vs_ycls': [('e_sens_fix1', 'e_yolo_naive')],
       'E_vs_empty_mask': [('e_sens_fix1', 'e_savior_none'), ('e_yolo_naive', 'e_savior_none'), ('e_oracle_person', 'e_savior_none')],
       'E_control': [('e_savior_none', 'e_openvins')]}


def load(m, seq):
    fn = f'{RUNS}/{seq}/{m}/eval/eval_summary.yaml'
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
    return out


D = {s: {m: load(m, s) for m in M} for s in SEQS}
# invalid runs (rr_audit.py, tables/invalid_e.txt: mask-delivery stall after 3 attempts) are excluded pairwise unless INCLUDE_INVALID=1
INV = [l.split() for l in open(f'{RR}/tables/invalid_e.txt')] if os.path.isfile(f'{RR}/tables/invalid_e.txt') else []
if not os.environ.get('INCLUDE_INVALID'):
    for s, m, r in INV:
        D[s][m].pop(int(r[4:]), None)
TAG = '_inclinvalid' if os.environ.get('INCLUDE_INVALID') else ''
lr = lambda a, b: math.log(min(a, CAP) / min(b, CAP))  # noqa: E731
pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def summ(m, ref, g):
    seqs, idx = GROUPS[g]
    by = {s: [lr(D[s][m][i], D[s][ref][i]) for i in sorted(D[s][m]) if i in D[s][ref] and (idx is None or i in idx)] for s in seqs}
    by = {s: v for s, v in by.items() if v}
    x = np.array([v for b in by.values() for v in b])
    if x.size < 3:
        return None
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    ci = np.percentile(np.random.default_rng(0).choice(x, (20000, x.size)).mean(axis=1), [2.5, 97.5])
    X = {s: np.array(v) for s, v in by.items()}
    sm = np.array([v.mean() for v in X.values()])
    seq = None
    if len(X) >= 2:
        bt = np.percentile(boot_two_stage(X), [2.5, 97.5])
        lm = reml_ri(X)
        sf = signflip(sm)
        seq = dict(est=pc(sm.mean()), ci=[pc(c) for c in bt], p_signflip=sf[0], p_signflip_min=sf[1], p_lmm=lm['p'] if lm else None,
                   k=len(X), seq_wins=int((sm < -1e-12).sum()), seq_losses=int((sm > 1e-12).sum()),
                   per_seq={s: pc(v.mean()) for s, v in X.items()})
    return dict(method=m, ref=ref, group=g, n=int(x.size), gm=pc(x.mean()), ci=[pc(c) for c in ci], p=p, seq=seq,
                wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), identical=int((np.abs(x) <= 1e-12).sum()))


res = []
for fam, items in FAM.items():
    for g in GROUPS:
        rs = [r for r in (summ(m, ref, g) for m, ref in items) if r]
        for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
            r['holm'] = float(h); r['family'] = fam
        res += rs


def cell(r):
    if r is None:
        return '-'
    q = r['seq']
    s = f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] H={r['holm']:.2g} {r['wins']}/{r['losses']}"
    if q:
        s += f" / seq {q['est']:+.1f} % [{q['ci'][0]:+.0f}, {q['ci'][1]:+.0f}] sf={q['p_signflip']:.2g} lmm={q['p_lmm']:.2g} {q['seq_wins']}/{q['seq_losses']}"
    return f'**{s}**' if r['holm'] < 0.05 else s


# reproduction of the earlier openvins runs (same original estimator config) by start offset
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest() if os.path.isfile(p) else None  # noqa: E731
rep = {}
for s in SEQS:
    mine = {}
    for rd in glob.glob(f'{RUNS}/{s}/e_openvins/run_*'):
        try:
            off = float(next(a for a in yaml.safe_load(open(f'{rd}/run_info.yaml'))['cmd'] if a.startswith('start_offset:=')).split(':=')[1])
            mine[off] = md5(f'{rd}/stamped_traj_estimate.txt')
        except Exception:
            pass
    for src in ('p2', 'p4', 'p3a', 'p7/noharm'):
        for rd in glob.glob(f'{R}/{src}/{s}/openvins/run_*'):
            try:
                off = float(next(a for a in yaml.safe_load(open(f'{rd}/run_info.yaml'))['cmd'] if a.startswith('start_offset:=')).split(':=')[1])
            except Exception:
                continue
            if off in mine:
                e = rep.setdefault(f'{src}', [0, 0]); e[1] += 1; e[0] += mine[off] == md5(f'{rd}/stamped_traj_estimate.txt')
U = METRIC.upper()
L = [f'# Task E: final SAVIOR (sens_fix1, COCO instantiation) and Y-Cls on OpenLORIS + uHumans2, ORIGINAL back-end ({U})\n',
     'Cells: RUN level: geometric-mean ratio - 1 [iid bootstrap CI], Holm-adjusted Wilcoxon p (within family x group), wins/losses of the '
     'paired offsets / SEQUENCE level (stats_v3): exp(mean of per-sequence mean log ratios) - 1 [two-stage cluster bootstrap CI], exact '
     'sign-flip p (sf; minimum attainable 2/2^k), LMM p, sequences better/worse. Negative = first method better. Single-sequence groups have '
     'no sequence-level statistic. P2offsets = runs 1-3 (start offsets 0.0/0.2/0.4 s, the P2 protocol).\n',
     f'## Median {U} [m] per sequence (n runs; [k] failures > {FAIL:g} m)\n', '| seq | ' + ' | '.join(LAB[m] for m in M) + ' |', '|---|' + '--:|' * len(M)]
for s in SEQS:
    cs = []
    for m in M:
        v = list(D[s][m].values())
        cs.append('-' if not v else f'{float(np.median(np.minimum(v, 1e4))):.4f} (n={len(v)})' + (f' [{sum(x > FAIL for x in v)}]' if any(x > FAIL for x in v) else ''))
    L.append(f'| {s} | ' + ' | '.join(cs) + ' |')
for fam, items in FAM.items():
    L += [f'\n## {fam}\n', '| comparison | group | result |', '|---|---|---|']
    for m, ref in items:
        for g in GROUPS:
            r = next((x for x in res if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g), None)
            if r:
                L.append(f'| {LAB[m]} vs {LAB[ref]} | {g} | {cell(r)} |')
L.append(f'\nInvalid runs excluded pairwise ({"no" if TAG else len(INV)}): ' + ', '.join('/'.join(x) for x in INV))
L.append('\nReproduction of earlier OpenVINS runs (same original estimator config, same start offset, trajectory md5): '
         + ', '.join(f'{k}: {a}/{b} identical' for k, (a, b) in rep.items()))
open(f'{RR}/tables/{METRIC}_e{TAG}.md', 'w').write('\n'.join(L) + '\n')
json.dump({'values': D, 'paired': res, 'repro': rep, 'labels': LAB}, open(f'{RR}/tables/{METRIC}_e{TAG}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
