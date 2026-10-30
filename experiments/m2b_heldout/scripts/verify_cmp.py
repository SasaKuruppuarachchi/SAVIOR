#!/usr/bin/env python3
"""verify_cmp.py: md5 comparison of the pre-freeze verification runs (results/m2b_heldout/verify) against the reference runs:
  verify/edge_install/<seq>/sens_fix1 (frozen_edge install, all edge flags off) vs results/p7/<seq>/sens_fix1
  verify/<seq>/savior_edge (frozen_edge install + addendum config)           vs results/edge_study/runs/<seq>/e_c_n672_L250dfronly
Prints a JSON summary (input to mkaddendum.py)."""
import glob, hashlib, json, os
R = '/home/sasa/workspace/savior_ws/results'
V = R + '/m2b_heldout/verify'
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None  # noqa: E731
out = {}
for name, pat, ref in (('flags_off_vs_frozen_sens_fix1', f'{V}/edge_install/*/sens_fix1/run_*', R + '/p7/{seq}/sens_fix1/{run}'),
                       ('savior_edge_vs_edge_study', f'{V}/*_t1_*/savior_edge/run_*', R + '/edge_study/runs/{seq}/e_c_n672_L250dfronly/{run}')):
    rows = []
    for rd in sorted(glob.glob(pat)):
        seq, m, run = rd.split('/')[-3:]
        a = md5(f'{rd}/stamped_traj_estimate.txt'); b = md5(ref.format(seq=seq, run=run) + '/stamped_traj_estimate.txt')
        rows.append({'seq': seq, 'run': run, 'md5': a, 'ref_md5': b, 'equal': bool(a and a == b)})
    out[name] = {'n': len(rows), 'n_equal': sum(r['equal'] for r in rows), 'runs': rows}
print(json.dumps(out, indent=1))
