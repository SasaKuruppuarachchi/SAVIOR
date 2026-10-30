#!/usr/bin/env python3
"""p7noharm.py: stage D no-harm check (results/p7/noharm/<seq>/<method>/eval/eval_summary.yaml): median ATE / RPE and
paired per-offset log ratios vs openvins and vs yolo_naive (geometric-mean ratio - 1, bootstrap 95 % CI, Wilcoxon,
Holm within each (reference, metric) family over sequences x methods) -> tables/noharm.{md,json}. Run in the image (scipy)."""
import json, math, os
import numpy as np, yaml
from scipy import stats
R = '/home/sasa/workspace/savior_ws/results/p7/noharm'
SEQS = ['uhumans2_office_s1_06h', 'openloris_cafe1-1']
M = ['openvins', 'savior_none', 'yolo_naive', os.environ.get('MAIN', 'p7_nb')]
FAIL = {'uhumans2_office_s1_06h': 5.0, 'openloris_cafe1-1': 2.0}   # ~2 % of path length (264 m / ~100 m)


def load(seq, m, metric):
    fn = f'{R}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if not os.path.isfile(fn):
        return out
    for t in yaml.safe_load(open(fn)).get('trials', []):
        i = int(t['name'].split('_')[1])
        if t.get('status') != 'ok':
            out[i] = math.inf; continue
        if metric == 'ate':
            out[i] = t['ate']['trans_m']['rmse']
        else:
            ks = sorted(t['rpe'], key=float)
            out[i] = t['rpe'][ks[0]]['trans_m']['mean']
    return out


def boot(x, n=20000):
    b = np.random.default_rng(0).choice(x, (n, x.size)).mean(axis=1)
    return np.percentile(b, [2.5, 97.5])


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


L = ['# P7 stage D no-harm check (COCO YOLO26s-seg, person dynamic; main with coco_indoor roles, '
     'prior_static_classes chair,suitcase,backpack,handbag,cart); 10 offsets 0.0-1.8 s, rate 0.5\n']
res = {}
for metric in ('ate', 'rpe'):
    D = {s: {m: load(s, m, metric) for m in M} for s in SEQS}
    A = {s: {m: load(s, m, 'ate') for m in M} for s in SEQS}
    L += [f'## Median {metric.upper()} [m] (n runs; [k] = failures, ATE > ~2 % of path)\n', '| seq | ' + ' | '.join(M) + ' |', '|---|' + '--:|' * len(M)]
    for s in SEQS:
        cells = []
        for m in M:
            v = list(D[s][m].values())
            nf = sum(a > FAIL[s] for a in A[s][m].values())
            cells.append(f'{np.median(v):.4f} (n={len(v)})' + (f' [{nf}]' if nf else '') if v else '-')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    for ref in ('openvins', 'yolo_naive'):
        fam = []
        for s in SEQS:
            for m in M:
                if m == ref:
                    continue
                x = np.array([math.log(min(D[s][m][i], 1e3) / min(D[s][ref][i], 1e3)) for i in D[s][m] if i in D[s][ref]])
                if x.size < 5:
                    continue
                nz = x[np.abs(x) > 1e-12]
                p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
                ci = boot(x)
                fam.append(dict(seq=s, method=m, ref=ref, metric=metric, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1),
                                ci=[100 * (math.exp(c) - 1) for c in ci], wins=int((x < 0).sum()), losses=int((x > 0).sum()),
                                identical=int((np.abs(x) <= 1e-12).sum()), p=p))
        for r, h in zip(fam, holm([r['p'] for r in fam])):
            r['holm'] = float(h)
        res[f'{metric}_vs_{ref}'] = fam
        L += [f'\n### Paired {metric.upper()} vs {ref} (geometric-mean ratio - 1; Holm over seq x method)\n',
              '| seq | method | n | change [95 % CI] | p | Holm p | wins/losses/identical |', '|---|---|--:|---|--:|--:|---|']
        L += [f"| {r['seq']} | {r['method']} | {r['n']} | {r['gm']:+.1f} % [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] | {r['p']:.3f} | {r['holm']:.3f} | {r['wins']}/{r['losses']}/{r['identical']} |" for r in fam]
    L.append('')
open('/home/sasa/workspace/savior_ws/results/p7/tables/noharm.md', 'w').write('\n'.join(L) + '\n')
json.dump(res, open('/home/sasa/workspace/savior_ws/results/p7/tables/noharm.json', 'w'), indent=1)
print('\n'.join(L))
