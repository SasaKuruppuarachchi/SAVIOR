#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""IMU <-> ground-truth consistency check of a SAVIOR-Warehouse raw sequence (numpy only).

  python3 tools/check_imu.py data/warehouse/raw/<seq> [--json out.json]

1. gyro_clean vs the angular velocity differentiated from the GT orientations (central difference on SO(3)),
2. acc_clean vs R^T (d2p/dt2 + g e3) from the GT positions (central second difference),
3. dead reckoning: the clean IMU integrated (RK4 on SO(3) x R3) from the GT state over 10 s windows,
4. noise: noisy - clean - bias -> white-noise density, diff(bias) -> random walk (vs calib/kalibr_imu_chain.yaml).
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wh.se3 import quat_to_rot, so3_exp, so3_log  # noqa: E402

G = 9.81


def load_csv(path):
    return np.loadtxt(path, delimiter=',', comments='#')


def load_tum(path):
    d = np.loadtxt(path, comments='#')
    q = d[:, [7, 4, 5, 6]]  # w x y z
    return d[:, 0], d[:, 1:4], quat_to_rot(q)


def read_noise(seq):
    import re
    txt = open(os.path.join(seq, 'calib', 'kalibr_imu_chain.yaml')).read()
    get = lambda k: float(re.search(rf'{k}:\s*([0-9.eE+-]+)', txt).group(1))  # noqa: E731
    return dict(gyro_nd=get('gyroscope_noise_density'), gyro_rw=get('gyroscope_random_walk'),
                acc_nd=get('accelerometer_noise_density'), acc_rw=get('accelerometer_random_walk'))


def integrate(R0, v0, p0, w, a, dt):
    """RK4-style on SO(3) x R3 with linearly interpolated IMU (clean) between samples k and k+1."""
    R, v, p = R0.copy(), v0.copy(), p0.copy()
    g = np.array([0, 0, -G])
    for k in range(len(w) - 1):
        w0, w1, a0, a1 = w[k], w[k + 1], a[k], a[k + 1]
        wm = 0.5 * (w0 + w1)
        # orientation: 4th order (Magnus with commutator term)
        dth = dt * wm + dt * dt / 12.0 * np.cross(w0, w1)
        R1 = R @ so3_exp(dth)
        Rmid = R @ so3_exp(0.5 * dt * (0.75 * w0 + 0.25 * w1))
        f0, f1, fm = R @ a0 + g, R1 @ a1 + g, Rmid @ (0.5 * (a0 + a1)) + g
        v1 = v + dt / 6.0 * (f0 + 4 * fm + f1)
        p = p + dt * v + dt * dt / 6.0 * (f0 + 2 * fm)
        v, R = v1, R1
    return R, v, p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('seq')
    ap.add_argument('--json', default='')
    ap.add_argument('--window', type=float, default=10.0)
    args = ap.parse_args()
    seq = args.seq
    t, p, R = load_tum(os.path.join(seq, 'gt_imu_tum.txt'))
    c = load_csv(os.path.join(seq, 'imu_clean.csv'))
    n = load_csv(os.path.join(seq, 'imu_noisy.csv'))
    b = load_csv(os.path.join(seq, 'imu_bias.csv'))
    vel = load_csv(os.path.join(seq, 'gt_imu_vel.csv'))
    ns = np.loadtxt(os.path.join(seq, 'imu_clean.csv'), delimiter=',', comments='#', usecols=0, dtype=np.int64)
    ti = (ns - ns[0]) * 1e-9   # exact integer ns (float64 cannot hold 1.7e18 ns exactly)
    assert len(ti) == len(t) and np.allclose(ti, t - t[0], atol=1e-6), 'IMU and GT stamps differ'
    dt = float(np.median(np.diff(ti)))
    w_c, a_c = c[:, 1:4], c[:, 4:7]
    # 1. gyro vs SO(3) central difference
    dR = np.einsum('nji,njk->nik', R[:-2], R[2:])
    w_num = so3_log(dR) / (2 * dt)
    # central difference of R estimates w at the midpoint in a frame rotated by half a step -> compare in body frame
    e_w = w_num - w_c[1:-1]
    # 2. accel vs second difference
    a_num = (p[2:] - 2 * p[1:-1] + p[:-2]) / dt ** 2
    f_num = np.einsum('nji,nj->ni', R[1:-1], a_num + np.array([0, 0, G]))
    e_a = f_num - a_c[1:-1]
    # GT velocity vs first difference
    v_num = (p[2:] - p[:-2]) / (2 * dt)
    e_v = v_num - vel[1:-1, 1:4]
    # 3. dead reckoning over windows
    win = int(round(args.window / dt))
    drift_p, drift_r = [], []
    for k0 in range(0, len(t) - win, win):
        k1 = k0 + win
        R1, v1, p1 = integrate(R[k0], vel[k0, 1:4], p[k0], w_c[k0:k1 + 1], a_c[k0:k1 + 1], dt)
        drift_p.append(float(np.linalg.norm(p1 - p[k1])))
        drift_r.append(float(np.rad2deg(np.linalg.norm(so3_log(R[k1].T @ R1)))))
    # 4. noise statistics
    nz = read_noise(seq)
    wn = n[:, 1:4] - w_c - b[:, 1:4]
    an = n[:, 4:7] - a_c - b[:, 4:7]
    res = dict(
        sequence=os.path.basename(os.path.normpath(seq)), samples=int(len(t)), dt=dt,
        gyro_vs_gt_rms=float(np.sqrt(np.mean(e_w ** 2))), gyro_vs_gt_max=float(np.abs(e_w).max()),
        gyro_signal_rms=float(np.sqrt(np.mean(w_c ** 2))),
        acc_vs_gt_rms=float(np.sqrt(np.mean(e_a ** 2))), acc_vs_gt_max=float(np.abs(e_a).max()),
        acc_dyn_signal_rms=float(np.sqrt(np.mean(a_num ** 2))),
        vel_vs_gt_rms=float(np.sqrt(np.mean(e_v ** 2))),
        dead_reckoning_window_s=args.window, dr_pos_err_mean_m=float(np.mean(drift_p)), dr_pos_err_max_m=float(np.max(drift_p)),
        dr_rot_err_max_deg=float(np.max(drift_r)),
        gyro_noise_density_est=float(np.mean(np.std(wn, 0)) * np.sqrt(dt)), gyro_noise_density_cfg=nz['gyro_nd'],
        acc_noise_density_est=float(np.mean(np.std(an, 0)) * np.sqrt(dt)), acc_noise_density_cfg=nz['acc_nd'],
        gyro_rw_est=float(np.mean(np.std(np.diff(b[:, 1:4], axis=0), 0)) / np.sqrt(dt)), gyro_rw_cfg=nz['gyro_rw'],
        acc_rw_est=float(np.mean(np.std(np.diff(b[:, 4:7], axis=0), 0)) / np.sqrt(dt)), acc_rw_cfg=nz['acc_rw'],
        gyro_bias0=b[0, 1:4].tolist(), acc_bias0=b[0, 4:7].tolist(),
        max_rate_deg_s=float(np.rad2deg(np.linalg.norm(w_c, axis=1).max())),
        max_yaw_rate_deg_s=float(np.rad2deg(np.abs(w_c[:, 2]).max())),
        max_speed_m_s=float(np.linalg.norm(vel[:, 1:4], axis=1).max()),
        mean_speed_moving_m_s=float(np.mean(np.linalg.norm(vel[:, 1:4], axis=1)[np.linalg.norm(vel[:, 1:4], axis=1) > 0.1])),
        max_tilt_deg=float(np.rad2deg(np.arccos(np.clip(R[:, 2, 2], -1, 1))).max()),
    )
    for k, v in res.items():
        print(f'{k:28s} {v}')
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(res, fh, indent=1)


if __name__ == '__main__':
    main()
