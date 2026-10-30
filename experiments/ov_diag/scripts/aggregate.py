#!/usr/bin/env python3
"""aggregate.py : paired ablation statistics vs 'base' on t1 L0/L1 (OpenVINS config diagnostic).

Reads results/ov_diag/analysis/runs.json (timeline.py over every run dir), plus run_info.yaml (status, n_poses).
Failure: no estimate / status != ok / ATE > 2 m / n_poses < 90 % of the base run's n_poses (pose-count check).
Per variant and group (L0, L1, L0+L1): geometric-mean ATE ratio - 1 (failures capped at 10 m), bootstrap 95 % CI
(paired runs, 10000 resamples), Wilcoxon signed-rank p, wins/losses; medians of ATE pos / rot, init time, failures.
Writes results/ov_diag/tables/ablation.{csv,md,json}.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import wilcoxon

WS = Path('/home/sasa/workspace/savior_ws')
D = WS / 'results/ov_diag'
CAP = 10.0
rng = np.random.default_rng(0)


def load(js):
    runs = {}
    for r in json.load(open(js)):
        p = Path(r['run'])
        var, seq, run = p.parts[-2], p.parts[-3].replace('warehouse_', ''), p.parts[-1]
        info = {}
        if (p / 'run_info.yaml').exists():
            info = yaml.safe_load(open(p / 'run_info.yaml'))
        r['status'] = info.get('status', 'ok' if 'error' not in r else 'missing')
        r['n_poses'] = info.get('n_poses', r.get('n', 0))
        runs[(var, seq, run)] = r
    return runs


def main():
    js = sys.argv[1] if len(sys.argv) > 1 else D / 'analysis/runs.json'
    ref = sys.argv[2] if len(sys.argv) > 2 else 'base'
    runs = load(js)
    variants = sorted({k[0] for k in runs})
    seqs = sorted({k[1] for k in runs})
    rows = []
    for v in variants:
        for grp, levels in (('L0', ['L0']), ('L1', ['L1']), ('L0+L1', ['L0', 'L1']), ('L3', ['L3'])):
            a, b, rot_a, rot_b, ti, fa, fb, n = [], [], [], [], [], 0, 0, 0
            for s in seqs:
                if s.split('_')[-1] not in levels:
                    continue
                for i in range(1, 11):
                    k, kb = (v, s, f'run_{i:02d}'), (ref, s, f'run_{i:02d}')
                    if k not in runs or kb not in runs:
                        continue
                    ra, rb = runs[k], runs[kb]
                    def val(r, rr):
                        bad = ('error' in r or r['status'] != 'ok' or r.get('ate', 1e9) > 2.0
                               or r['n_poses'] < (900 if 'vins' in str(r['run']) else (0.45 if 'trk10' in str(r['run']) else (0.3 if 'trk7' in str(r['run']) else 0.9)) * rr.get('n_poses', 0)))
                        return (CAP if bad else r['ate']), bad, (np.nan if bad else r.get('ate_rot', np.nan))
                    x, bx, rx = val(ra, rb); y, by, ry = val(rb, rb)
                    a.append(x); b.append(y); rot_a.append(rx); rot_b.append(ry); fa += bx; fb += by; n += 1
                    if not bx:
                        ti.append(ra['t_first'])
            if n == 0:
                continue
            a, b = np.array(a), np.array(b)
            lr = np.log(a / b)
            boots = [np.exp(np.mean(rng.choice(lr, len(lr)))) - 1 for _ in range(10000)]
            try:
                p = float(wilcoxon(a, b).pvalue) if np.any(a != b) else 1.0
            except ValueError:
                p = 1.0
            rows.append(dict(variant=v, group=grp, n=n, eff=float(np.exp(lr.mean()) - 1),
                             lo=float(np.percentile(boots, 2.5)), hi=float(np.percentile(boots, 97.5)), p=p,
                             wins=int((a < b - 1e-9).sum()), losses=int((a > b + 1e-9).sum()),
                             med_ate=float(np.median(a)), med_ate_ref=float(np.median(b)),
                             med_rot=float(np.nanmedian(rot_a)), med_rot_ref=float(np.nanmedian(rot_b)),
                             fail=int(fa), fail_ref=int(fb), init_t=float(np.median(ti)) if ti else float('nan'),
                             identical=bool(np.all(a == b))))
    out = D / 'tables'
    out.mkdir(exist_ok=True)
    tag = Path(js).stem
    json.dump(rows, open(out / f'ablation_{tag}.json', 'w'), indent=1)
    with open(out / f'ablation_{tag}.csv', 'w') as f:
        f.write(','.join(rows[0].keys()) + '\n')
        for r in rows:
            f.write(','.join(str(x) for x in r.values()) + '\n')
    # per-sequence medians
    lines = [f'| variant | group | n | median ATE [m] (ref {ref}) | median rot [deg] | init t [s] | fail | geo-mean ratio-1 [95% CI] | Wilcoxon p | W/L |',
             '|---|---|--:|--:|--:|--:|--:|---|--:|--:|']
    for r in rows:
        lines.append(f"| {r['variant']} | {r['group']} | {r['n']} | {r['med_ate']:.3f} ({r['med_ate_ref']:.3f}) | {r['med_rot']:.2f} ({r['med_rot_ref']:.2f}) | "
                     f"{r['init_t']:.2f} | {r['fail']} ({r['fail_ref']}) | {100*r['eff']:+.0f} % [{100*r['lo']:+.0f}, {100*r['hi']:+.0f}]"
                     f"{' (identical)' if r['identical'] else ''} | {r['p']:.2g} | {r['wins']}/{r['losses']} |")
    seqlines = ['', '| variant | ' + ' | '.join(seqs) + ' |', '|---|' + '--:|' * len(seqs)]
    for v in variants:
        cells = []
        for s in seqs:
            vals = [runs[(v, s, f'run_{i:02d}')] for i in range(1, 11) if (v, s, f'run_{i:02d}') in runs]
            at = [CAP if ('error' in r or r['status'] != 'ok' or r.get('ate', 1e9) > 2) else r['ate'] for r in vals]
            nf = sum(x >= CAP for x in at)
            cells.append(f"{np.median(at):.3f}{f' [{nf}]' if nf else ''} (n={len(at)})" if at else '-')
        seqlines.append(f'| {v} | ' + ' | '.join(cells) + ' |')
    (out / f'ablation_{tag}.md').write_text('\n'.join(lines + seqlines) + '\n')
    print('\n'.join(lines + seqlines))


if __name__ == '__main__':
    main()
