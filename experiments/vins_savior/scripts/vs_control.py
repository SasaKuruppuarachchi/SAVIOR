#!/usr/bin/env python3
"""vs_control.py <root rel. to results/vins_savior> <out dir rel.> [t1|t2|viode] : empty-mask control (vins_zero == vins_fusion,
md5 of stamped_traj_estimate.txt per run) + mask sync summary of every masked VINS run (estimator.log [SAVIOR] FINAL /
last summary line: frames, found, missing, features left on core). -> <out>/control.md|json"""
import glob, hashlib, json, os, re, sys
V = '/home/sasa/workspace/savior_ws/results/vins_savior'
R, O = V + '/' + sys.argv[1], V + '/' + sys.argv[2]
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None  # noqa: E731
res, sync = [], {}
for d in sorted(glob.glob(R + '/*/vins_fusion/run_*')):
    z = d.replace('/vins_fusion/', '/vins_zero/')
    a, b = md5(d + '/stamped_traj_estimate.txt'), md5(z + '/stamped_traj_estimate.txt')
    if b is not None:
        res.append(dict(run=d[len(R) + 1:], equal=a == b, md5=a, md5_zero=b))
for log in sorted(glob.glob(R + '/*/*/run_*/estimator.log')):
    m = log.split('/')[-3]
    if m in ('vins_fusion', 'dynavins', 'vins_fusion_mt'):
        continue
    lines = [l for l in open(log, errors='replace') if l.startswith('[SAVIOR]') and 'frames=' in l]
    if not lines:
        continue
    kv = dict(re.findall(r'(\w+)=(\d+)', lines[-1]))
    s = sync.setdefault(m, {'runs': 0, 'final': 0})
    s['runs'] += 1; s['final'] += 'FINAL' in lines[-1]
    for k, v in kv.items():
        s[k] = s.get(k, 0) + int(v)
ne = sum(r['equal'] for r in res)
L = [f'# Empty-mask control and mask sync ({sys.argv[1]})\n',
     f'- vins_zero (all-zero masks, gate mode) vs vins_fusion (no masks), both deterministic: **{ne}/{len(res)} md5-identical**',
     ] + [f"  - differs: {r['run']}" for r in res if not r['equal']] + ['', '| method | runs | frames | found | missing | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solver_time_hits |', '|---|' + '--:|' * 15]
for m, s in sync.items():
    L.append(f"| {m} | {s['runs']} | " + ' | '.join(str(s.get(k, 0)) for k in ('frames', 'found', 'missing', 'in_core_l', 'in_core_r', 'drop_tracked_l', 'drop_tracked_r', 'relaxed_l', 'relaxed_r', 'deferred_masks', 'deferred_missing', 'flagged', 'flagged_tracked', 'solver_time_hits')) + ' |')
os.makedirs(O, exist_ok=True)
open(O + '/control.md', 'w').write('\n'.join(L) + '\n')
json.dump({'control': res, 'sync': sync}, open(O + '/control.json', 'w'), indent=1)
print('\n'.join(L))
