#!/usr/bin/env python3
"""dm_control.py <root rel. to results/dynavins_masks> <out dir rel.> : empty-mask control (dyna_zero == dyna_det, md5 of
stamped_traj_estimate.txt per run; otherwise the ATE difference) + mask sync summary of every DynaVINS run with
[SAVIOR] counters (estimator.log FINAL / last summary line: frames, found, missing, features left on core, solver time
hits). = results/vins_savior/scripts/vs_control.py for DynaVINS. -> <out>/control.md|json"""
import glob, hashlib, json, os, re, sys
import yaml
V = '/home/sasa/workspace/savior_ws/results/dynavins_masks'
R, O = V + '/' + sys.argv[1], V + '/' + sys.argv[2]
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None  # noqa: E731


def ate(mdir, run):
    f = mdir + '/eval_posyaw/eval_summary.yaml'
    if not os.path.isfile(f):
        return None
    for t in yaml.safe_load(open(f)).get('trials', []):
        if t['name'] == run and t.get('status') == 'ok':
            return t['ate']['trans_m']['rmse']
    return None


res, sync = [], {}
for d in sorted(glob.glob(R + '/*/dyna_det/run_*')):
    z = d.replace('/dyna_det/', '/dyna_zero/')
    a, b = md5(d + '/stamped_traj_estimate.txt'), md5(z + '/stamped_traj_estimate.txt')
    if b is not None:
        run = os.path.basename(d)
        x, y = ate(os.path.dirname(d), run), ate(os.path.dirname(z), run)
        res.append(dict(run=d[len(R) + 1:], equal=a == b, md5=a, md5_zero=b, ate=x, ate_zero=y))
for log in sorted(glob.glob(R + '/*/*/run_*/estimator.log')):
    m = log.split('/')[-3]
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
     f'- dyna_zero (all-zero masks, gate mode) vs dyna_det (no masks), both deterministic: **{ne}/{len(res)} md5-identical**']
for r in res:
    if not r['equal']:
        d = '' if r['ate'] is None or r['ate_zero'] is None else f" (ATE {r['ate']:.4f} vs {r['ate_zero']:.4f} m)"
        L.append(f"  - differs: {r['run']}{d}")
L += ['', '| method | runs | FINAL | frames | found | missing | bad_size | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solves | solver_time_hits |',
      '|---|' + '--:|' * 18]
for m, s in sorted(sync.items()):
    L.append(f"| {m} | {s['runs']} | {s['final']} | " + ' | '.join(str(s.get(k, 0)) for k in (
        'frames', 'found', 'missing', 'bad_size', 'in_core_l', 'in_core_r', 'drop_tracked_l', 'drop_tracked_r', 'relaxed_l',
        'relaxed_r', 'deferred_masks', 'deferred_missing', 'flagged', 'flagged_tracked', 'solves', 'solver_time_hits')) + ' |')
os.makedirs(O, exist_ok=True)
open(O + '/control.md', 'w').write('\n'.join(L) + '\n')
json.dump({'control': res, 'sync': sync}, open(O + '/control.json', 'w'), indent=1)
print('\n'.join(L))
