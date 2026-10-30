#!/usr/bin/env python3
"""quick.py [seq-glob] : per-run ATE (posyaw) trans RMSE from <method>/eval/eval_summary.yaml (as written by savior-run)."""
import glob, sys, yaml, os
R = '/home/sasa/workspace/savior_ws/results/p5_viode'
pat = sys.argv[1] if len(sys.argv) > 1 else '*'
for d in sorted(glob.glob(f'{R}/{pat}/*/eval/eval_summary.yaml')):
    s = yaml.safe_load(open(d))
    seq, m = d.split('/')[-4], d.split('/')[-3]
    vals = []
    for t in s.get('trials', []):
        if t.get('status') != 'ok':
            vals.append(f"{t['name'][-2:]}:FAIL")
            continue
        vals.append(f"{t['name'][-2:]}:{t['ate']['trans_m']['rmse']:.3f}")
    print(f'{seq:20s} {m:28s} ' + ' '.join(vals))
