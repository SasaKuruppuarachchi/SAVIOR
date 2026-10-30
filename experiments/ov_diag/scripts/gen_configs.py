#!/usr/bin/env python3
"""gen_configs.py : write OpenVINS config variants (results/ov_diag/configs/<variant>/) from the frozen warehouse config.

Each variant = the frozen src/savior/savior_bringup/config/warehouse/{estimator_config,kalibr_imu_chain,kalibr_imucam_chain}.yaml
copied verbatim with only the listed `key: value` lines replaced (regex on the top-level / imu0 keys). The frozen files are
only read. Diagnostic (OV-diag), tuning sequences t1 only.
"""
import re
import sys
from pathlib import Path

WS = Path('/home/sasa/workspace/savior_ws')
SRC = WS / 'src/savior/savior_bringup/config/warehouse'
OUT = WS / 'results/ov_diag/configs'

TRUE = dict(accelerometer_noise_density=1.6e-3, accelerometer_random_walk=3.0e-4,
            gyroscope_noise_density=2.44e-4, gyroscope_random_walk=2.0e-5)


def imu_scale(nd, rw):
    return {'accelerometer_noise_density': TRUE['accelerometer_noise_density'] * nd,
            'gyroscope_noise_density': TRUE['gyroscope_noise_density'] * nd,
            'accelerometer_random_walk': TRUE['accelerometer_random_walk'] * rw,
            'gyroscope_random_walk': TRUE['gyroscope_random_walk'] * rw}


# variant -> (estimator overrides, imu overrides)
V = {
    'base': ({}, {}),
    # IMU noise: the frozen values ARE the generator's true densities; test the usual "inflate for discretisation /
    # unmodelled effects" practice (OV rs_d455: white x2, rw x10; OV EuRoC/sim template: acc rw 3e-3 = 10x ours)
    'imu_x2_rw10': ({}, imu_scale(2, 10)),
    'imu_x5': ({}, imu_scale(5, 5)),
    'imu_rw10': ({}, imu_scale(1, 10)),
    # zero-velocity updates (hover start/end)
    'zupt': ({'try_zupt': 'true', 'zupt_chi2_multipler': '1', 'zupt_max_disparity': '0.5', 'zupt_noise_multiplier': '10'}, {}),
    # OV: try_zupt=true also switches the static initialiser to wait_for_jerk=false (VioManagerHelper.cpp:106), i.e. it
    # initialises as soon as both init half-windows are still (in the hover) instead of waiting for the take-off jerk
    'zupt_win1': ({'try_zupt': 'true', 'zupt_chi2_multipler': '1', 'init_window_time': '1.0'}, {}),
    # in-hover init WITHOUT zero-velocity updates (chi2 multiplier 0 + disparity 0 -> every ZUPT rejected)
    'hoverinit_win1': ({'try_zupt': 'true', 'zupt_chi2_multipler': '0', 'zupt_max_disparity': '0', 'init_window_time': '1.0'}, {}),
    # initialisation
    'init_win1': ({'init_window_time': '1.0'}, {}),
    'init_thr015': ({'init_imu_thresh': '0.15'}, {}),
    'initfeat150': ({'init_max_features': '150'}, {}),  # 75/cam before init (= after-init target)
    'init_nodyn': ({'init_dyn_use': 'false'}, {}),
    # features / window
    'feat_sim': ({'num_pts': '250', 'fast_threshold': '15', 'grid_x': '20', 'grid_y': '20', 'min_px_dist': '15'}, {}),
    'fast10': ({'fast_threshold': '10'}, {}),
    'pts250': ({'num_pts': '250'}, {}),
    'pts300': ({'num_pts': '300'}, {}),  # = 150 per camera (OV splits num_pts over the cameras) = VINS-Fusion max_cnt
    'clones15': ({'max_clones': '15', 'max_msckf_in_update': '60'}, {}),
    'clones15only': ({'max_clones': '15'}, {}),
    'msckf60': ({'max_msckf_in_update': '60'}, {}),
    'clones20': ({'max_clones': '20', 'max_msckf_in_update': '80'}, {}),
    'clones30': ({'max_clones': '30', 'max_msckf_in_update': '120'}, {}),
    # clone (and track) every 2nd frame = VINS-Fusion's 10 Hz front-end; window time doubles at equal clone count
    'trk10': ({'track_frequency': '10.5'}, {}),
    'trk10_clones20': ({'track_frequency': '10.5', 'max_clones': '20', 'max_msckf_in_update': '80'}, {}),
    'trk7': ({'track_frequency': '7.0'}, {}),  # every 3rd frame (6.67 Hz)
    'trk10_clones15': ({'track_frequency': '10.5', 'max_clones': '15'}, {}),
    'hist_none': ({'histogram_method': '"NONE"'}, {}),
    'slam0': ({'max_slam': '0'}, {}),
    # camera noise
    'sigma_px05': ({'up_msckf_sigma_px': '0.5', 'up_slam_sigma_px': '0.5'}, {}),
    'sigma_px15': ({'up_msckf_sigma_px': '1.5', 'up_slam_sigma_px': '1.5'}, {}),
    # upstream EuRoC (= frozen file except these 6 keys)
    'euroc': ({'calib_cam_extrinsics': 'true', 'calib_cam_intrinsics': 'true', 'calib_cam_timeoffset': 'true',
               'num_pts': '200', 'init_dyn_use': 'false'}, {}),
}


def sub(text, key, val, path):
    pat = re.compile(r'^(\s*' + re.escape(key) + r':\s*)([^#\n]*?)(\s*(#.*)?)$', re.M)
    n = len(pat.findall(text))
    if n != 1:
        sys.exit(f'{path}: key {key} found {n}x')
    return pat.sub(lambda m: m.group(1) + str(val) + '  # OV-DIAG (was ' + m.group(2).strip() + ')' + (
        ' ' + m.group(4) if m.group(4) else ''), text)


def write(name, est, imu):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    for fn, ov in (('estimator_config.yaml', est), ('kalibr_imu_chain.yaml', imu), ('kalibr_imucam_chain.yaml', {})):
        t = (SRC / fn).read_text()
        for k, v in ov.items():
            t = sub(t, k, f'{v:.6e}' if isinstance(v, float) else v, fn)
        (d / fn).write_text(t)


if __name__ == '__main__':
    extra = {}
    # combos: name=variantA+variantB on the command line
    for a in sys.argv[1:]:
        name, parts = a.split('=')
        est, imu = {}, {}
        for p in parts.split('+'):
            est.update(V[p][0]); imu.update(V[p][1])
        extra[name] = (est, imu)
    for n, (e, i) in {**V, **extra}.items():
        write(n, e, i)
    print('wrote', sorted({**V, **extra}))
