"""Per-run front-end evidence from feature_stats.csv / savior_stats.jsonl / runstats.yaml + init time.
python3 featstats.py -> results/p3a/tables/featstats.{md,csv}"""
import csv
import glob
import json
import os

import numpy as np
import yaml

P3 = '/home/sasa/workspace/savior_ws/results/p3a'
rows_out = []
for rd in sorted(glob.glob(f'{P3}/uhumans2_office_s1_*/*/run_[0-9]*')):
    seq = rd.split('/')[-3].replace('uhumans2_', '')
    m = rd.split('/')[-2]
    fs = f'{rd}/feature_stats.csv'
    est = f'{rd}/stamped_traj_estimate.txt'
    if not (os.path.isfile(fs) and os.path.isfile(est)):
        continue
    E = np.loadtxt(est, comments='#')
    if E.size == 0:
        continue
    t_init = E[0, 0]
    F = np.genfromtxt(fs, delimiter=',', names=True)
    rec = dict(seq=seq, method=m, run=rd[-6:], n_poses=len(E), t_first_pose=round(float(t_init), 3),
               t_last_pose=round(float(E[-1, 0]), 3))
    for c in (0, 1):
        f = F[F['cam_id'] == c]
        kept = f['n_tracked'] + f['n_new']
        pre = f['timestamp'] < t_init
        rec[f'kept_c{c}'] = round(float(kept.mean()), 2)
        rec[f'kept_pre_init_c{c}'] = round(float(kept[pre].mean()), 2) if pre.any() else None
        rec[f'rej_mask_c{c}'] = int(f['n_rejected_mask'].sum())
        rec[f'relaxed_c{c}'] = int(f['relaxed'].sum())
        rec[f'in_core_c{c}'] = int(f['n_in_core'].sum())
        rec[f'in_band_c{c}'] = int(f['n_in_band'].sum())
        rec[f'frac_kept_in_core_c{c}'] = round(float(f['n_in_core'].sum() / max(1, kept.sum())), 5)
        rec[f'frames_with_core_feat_c{c}'] = round(float((f['n_in_core'] > 0).mean()), 4)
        rec[f'max_core_feat_c{c}'] = int(f['n_in_core'].max())
    rs = f'{rd}/runstats.yaml'
    if os.path.isfile(rs):
        r = yaml.safe_load(open(rs))
        ms = r.get('mask_sync') or {}
        rec.update(md5=r.get('traj_md5'), images=r.get('bag_images'), exact=ms.get('exact'), cam_masks=ms.get('cam_masks'),
                   fb_latest=ms.get('fallback_latest'), fb_empty=ms.get('fallback_empty'), late=ms.get('late_masks'),
                   hold_max=ms.get('hold_max_ms'), core_frac=(r.get('savior') or {}).get('core_frac_mean'),
                   ext_frac=(r.get('savior') or {}).get('ext_frac_mean'))
    rows_out.append(rec)
keys = []
for r in rows_out:
    for k in r:
        if k not in keys:
            keys.append(k)
with open(f'{P3}/tables/featstats.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, keys)
    w.writeheader()
    w.writerows(rows_out)
# method-level summary
lines = ['# P3a front-end evidence per method (mean over runs)\n',
         '| seq | method | runs | first pose t [s] | kept/frame cam0 | kept pre-init cam0 | rejected by mask (cam0+1, per run) | '
         'kept on core (cam0, % of kept) | mask exact / cam_masks | fallbacks |',
         '|---|---|--:|--:|--:|--:|--:|--:|---|--:|']
groups = {}
for r in rows_out:
    groups.setdefault((r['seq'], r['method']), []).append(r)
for (s, m), rr in sorted(groups.items()):
    mean = lambda k: np.mean([x[k] for x in rr if x.get(k) is not None]) if any(x.get(k) is not None for x in rr) else float('nan')  # noqa
    fb = sum((x.get('fb_latest') or 0) + (x.get('fb_empty') or 0) + (x.get('late') or 0) for x in rr)
    ex = sum(x.get('exact') or 0 for x in rr)
    cm = sum(x.get('cam_masks') or 0 for x in rr)
    lines.append(f"| {s[-3:]} | {m} | {len(rr)} | {mean('t_first_pose'):.2f} | {mean('kept_c0'):.1f} | {mean('kept_pre_init_c0'):.1f} | "
                 f"{mean('rej_mask_c0') + mean('rej_mask_c1'):.0f} | {100 * mean('frac_kept_in_core_c0'):.3f} | {ex} / {cm} | {fb} |")
open(f'{P3}/tables/featstats.md', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
