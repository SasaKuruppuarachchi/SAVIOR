#!/usr/bin/env python3
"""t3_checks.py : mechanical application of the PRE-WRITTEN exclusion rule (DESIGN.yaml: exclusion_rule) to the t3 split.

Inputs (per trajectory <id>, sequences <id>_t3_L0..L3):
  data/warehouse/raw/<seq>/{meta.json, frames.csv, imu_noisy.csv}   render output (symlinks to the HDD)
  data/warehouse/ros2_stereoseg/<seq>/metadata.yaml, data/warehouse/gt/<seq>.txt   conversion output
  results/t3_confirmatory/checks/imu_<id>.json (tools/check_imu.py on L0), geom_<id>.json (tools/check_geometry.py on L3)
  results/t3_confirmatory/sanity/<seq>/{openvins,oracle_moving_ext}/eval/eval_summary.yaml (offsets 0.0 / 0.3 / 0.6 s)
Writes results/t3_confirmatory/EXCLUSIONS.yaml and tables/checks.md. Only the rule's criteria are used.
"""
import hashlib
import json
import math
import os

import yaml

WS = '/home/sasa/workspace/savior_ws'
T = f'{WS}/results/t3_confirmatory'
D = yaml.safe_load(open(f'{T}/DESIGN.yaml'))
R = D['exclusion_rule']['tolerances']
FAIL = float(D['analysis_plan']['failure_threshold_m'])


def md5(f):
    h = hashlib.md5()
    with open(f, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sanity(seq, m):
    fn = f'{T}/sanity/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            out[int(t['name'].split('_')[1])] = t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf
    return [out.get(i, math.inf) for i in (1, 2, 3)]


def main():
    rows, excl = [], []
    for tr in D['dataset']['trajectories']:
        tid = tr['id']
        why = []
        md5s = {}
        for k in D['dataset']['levels']:
            seq = f'{tid}_t3_L{k}'
            raw = f'{WS}/data/warehouse/raw/{seq}'
            if not os.path.isfile(f'{raw}/meta.json'):
                why.append(f'R1 {seq}: no render'); continue
            meta = json.load(open(f'{raw}/meta.json'))
            n_fr = sum(1 for l in open(f'{raw}/frames.csv') if not l.startswith('#'))
            n_png = len(os.listdir(f'{raw}/cam0'))
            if n_fr != meta['frames'] or n_png != n_fr or len(os.listdir(f'{raw}/cam1')) != n_fr:
                why.append(f'R1 {seq}: frame count {n_fr} / png {n_png}')
            if not os.path.isfile(f'{WS}/data/warehouse/ros2_stereoseg/{seq}/metadata.yaml') or \
                    not os.path.isfile(f'{WS}/data/warehouse/gt/{seq}.txt'):
                why.append(f'R1 {seq}: no bag / GT')
            md5s[k] = md5(f'{raw}/imu_noisy.csv')
        if len(set(md5s.values())) > 1:
            why.append('R1 imu_noisy.csv md5 differs across levels')
        ij = f'{T}/checks/imu_{tid}.json'
        if os.path.isfile(ij):
            c = json.load(open(ij))
            bad = [k for k, lim in (('gyro_vs_gt_rms', R['gyro_vs_gt_rms_max']), ('acc_vs_gt_rms', R['acc_vs_gt_rms_max']),
                                    ('dr_pos_err_max_m', R['dr_pos_err_max_m'])) if c[k] > lim]
            for k in ('gyro_noise_density', 'acc_noise_density'):
                r = c[f'{k}_est'] / c[f'{k}_cfg']
                if abs(r - 1) > R['noise_density_rel_tol']:
                    bad.append(f'{k} ratio {r:.3f}')
            if bad:
                why.append(f'R1 IMU check: {bad}')
        else:
            why.append('R1 IMU check missing'); c = {}
        gj = f'{T}/checks/geom_{tid}.json'
        if os.path.isfile(gj):
            g = json.load(open(gj))
            if abs(g['stereo_best_scale'] - 1.0) > 1e-6 or abs(g['stereo_best_offset_px']) > 1e-6 or not g['temporal_true_is_best']:
                why.append(f"R1 geometry check: scale {g['stereo_best_scale']} offset {g['stereo_best_offset_px']} "
                           f"temporal {g['temporal_true_is_best']}")
        else:
            why.append('R1 geometry check missing'); g = {}
        ov0 = sanity(f'{tid}_t3_L0', 'openvins')
        od0 = sanity(f'{tid}_t3_L0', 'oracle_moving_ext')
        ov3 = sanity(f'{tid}_t3_L3', 'openvins')
        od3 = sanity(f'{tid}_t3_L3', 'oracle_moving_ext')
        n_bad0 = sum((not math.isfinite(v)) or v > FAIL for v in ov0)
        if n_bad0 >= R['sanity_L0_min_failed_offsets']:
            why.append(f'R2 L0 OpenVINS failed on {n_bad0}/3 offsets (ATE {ov0})')
        rows.append(dict(id=tid, site=tr['site'], seed=tr['seed'], imu_md5_identical=len(set(md5s.values())) == 1,
                         gyro_rms=c.get('gyro_vs_gt_rms'), acc_rms=c.get('acc_vs_gt_rms'), dr_max=c.get('dr_pos_err_max_m'),
                         geom=(g.get('stereo_best_scale'), g.get('stereo_best_offset_px'), g.get('temporal_true_is_best')),
                         ov_L0=ov0, od_L0=od0, ov_L3=ov3, od_L3=od3, reasons=why))
        if why:
            excl.append(dict(trajectory=tid, reasons=why))
    yaml.safe_dump(dict(rule='DESIGN.yaml exclusion_rule (pre-written, applied mechanically by t3_checks.py)',
                        excluded=excl), open(f'{T}/EXCLUSIONS.yaml', 'w'), sort_keys=False, width=140)
    f3 = lambda v: 'fail' if not math.isfinite(v) else (f'{v:.3f}' if v < 100 else 'div.')  # noqa: E731
    L = ['| traj | site | seed | IMU md5 equal | gyro / acc RMS vs GT | DR 10 s max [mm] | stereo scale / offset / temporal | '
         'sanity L0 OpenVINS | L0 O-Dyn+B | L3 OpenVINS | L3 O-Dyn+B | excluded |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['id']} | {r['site']} | {r['seed']} | {r['imu_md5_identical']} | "
                 f"{(r['gyro_rms'] or 0):.1e} / {(r['acc_rms'] or 0):.1e} | {1e3 * (r['dr_max'] or 0):.2f} | "
                 f"{r['geom'][0]} / {r['geom'][1]} / {r['geom'][2]} | " + ' | '.join(' / '.join(f3(v) for v in r[k])
                 for k in ('ov_L0', 'od_L0', 'ov_L3', 'od_L3')) + f" | {'; '.join(r['reasons']) or 'no'} |")
    os.makedirs(f'{T}/tables', exist_ok=True)
    open(f'{T}/tables/checks.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('excluded:', [e['trajectory'] for e in excl])


if __name__ == '__main__':
    main()
