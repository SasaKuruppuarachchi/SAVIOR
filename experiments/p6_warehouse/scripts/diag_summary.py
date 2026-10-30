#!/usr/bin/env python3
"""Feature fates per sequence and method from the diagnostic runs (diag_p6.yaml): openvins = mean of 3 offsets,
masking methods = offset 0.0 (run_01, trajectory identical to the main run_01). -> tables/feature_fates.md|csv"""
import csv
import glob

import numpy as np
import yaml

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
METH = ['openvins', 'oracle_moving', 'oracle_class_naive', 'yolo_naive', 'yolo_p4', 'yolo_p6']
rows = []
for seq in sorted({p.split('/')[-3] for p in glob.glob(f'{R}/*_t1_L*/diag_*/')}):
    for m in METH:
        fs = sorted(glob.glob(f'{R}/{seq}/diag_{m}/run_*/diag_p6.yaml'))
        if not fs:
            continue
        v = [yaml.safe_load(open(f)) for f in fs]

        def g(f):
            x = [f(d) for d in v]
            x = [y for y in x if y is not None]
            return float(np.mean(x)) if x else float('nan')
        rows.append(dict(seq=seq, method=m, runs=len(v),
                         kept_per_frame=g(lambda d: d['kept_per_frame_cam0']),
                         kept_moving=g(lambda d: d['frac_kept_obs_on_human_cam0']),
                         kept_static_pot=g(lambda d: d['frac_kept_obs_on_static_potential_cam0']),
                         used_moving=g(lambda d: d['post_init']['frac_msckf_used_meas_human']),
                         used_static_pot=g(lambda d: d['post_init']['frac_msckf_used_meas_static_potential']),
                         slam_moving=g(lambda d: d['post_init']['frac_slam_update_meas_human']),
                         slam_static_pot=g(lambda d: d['post_init']['frac_slam_update_meas_static_potential']),
                         chi2_moving=g(lambda d: d['post_init']['human'].get('msckf_chi2_reject_rate')),
                         chi2_other=g(lambda d: d['post_init']['non_human'].get('msckf_chi2_reject_rate')),
                         chi2_static_pot=g(lambda d: d['post_init']['static_potential'].get('msckf_chi2_reject_rate')),
                         len_static_pot=g(lambda d: d['post_init']['static_potential'].get('len_frames_median')),
                         len_other=g(lambda d: d['post_init']['non_human'].get('len_frames_median')),
                         msckf_used_total=g(lambda d: d['post_init']['all']['msckf_used_meas']),
                         slam_used_total=g(lambda d: d['post_init']['all']['slam_update_meas'])))
with open(f'{R}/tables/feature_fates.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
P = lambda x: '-' if x != x else f'{100 * x:.1f}'  # noqa: E731
L = ['# feature fates (diagnostic OpenVINS build, logging only): shares of kept cam0 observations / of post-init MSCKF-used '
     'measurements / of SLAM-update measurements on MOVING objects and on STATIC potentially-dynamic objects (parked forklifts, '
     'pallets, boxes, standing people, trolleys = what naive class masking removes); MSCKF chi2 rejection rate of tracks on moving '
     'objects / on everything else / on static potential objects; median track length [frames] static-potential vs other\n',
     '| seq | method | runs | kept/frame | kept mov % | kept static-pot % | MSCKF used mov % | used static-pot % | SLAM mov % | '
     'SLAM static-pot % | chi2 rej mov / other / static-pot | track len static-pot / other | MSCKF used meas | SLAM update meas |',
     '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|--:|']
for r in rows:
    L.append(f"| {r['seq']} | {r['method']} | {r['runs']} | {r['kept_per_frame']:.1f} | {P(r['kept_moving'])} | {P(r['kept_static_pot'])} | "
             f"{P(r['used_moving'])} | {P(r['used_static_pot'])} | {P(r['slam_moving'])} | {P(r['slam_static_pot'])} | "
             f"{r['chi2_moving']:.2f} / {r['chi2_other']:.2f} / {r['chi2_static_pot']:.2f} | {r['len_static_pot']:.0f} / {r['len_other']:.0f} | "
             f"{r['msckf_used_total']:.0f} | {r['slam_used_total']:.0f} |")
open(f'{R}/tables/feature_fates.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
