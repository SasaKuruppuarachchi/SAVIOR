#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Monado SLAM Dataset (MSD, Collabora / TUM, de Mayo, Cremers, Pire, arXiv 2508.00088, CC BY 4.0) preparation for the
Valve Index sequences (MI_valve_index, EuRoC/ASL layout inside one zip per sequence).

Reads the sequence zip directly (no extraction). Run inside the savior image, e.g.

  python3 -I monado_prepare.py inspect --zip MIO13_moving_person.zip [--out inspect.yaml]
  python3 -I monado_prepare.py gt      --zip MIO13_moving_person.zip --out gt/MIO13.txt [--check-out check.yaml]
  python3 -I monado_prepare.py calib   --json calibration.json --out-dir <config dir>
  python3 -I monado_prepare.py convert --zip MIO13_moving_person.zip --dst ros2/MIO13

convert : ROS 2 (mcap; --zstd: rosbag2 message-mode zstd, lossless) bag with /cam0/image_raw, /cam1/image_raw (mono8, 960x960, the PNGs decoded verbatim, header
          stamp = camX/data.csv timestamp, which the dataset already aligned to the IMU clock) and /imu0
          (sensor_msgs/Imu from imu0/data.csv = the bias / scale-misalignment corrected IMU, as the dataset README
          recommends for calibration.json). Nothing is resampled, cropped or rescaled; --track-hz 28.35 keeps only the
          stereo pairs that OpenVINS track_frequency 28.35 tracks (every 2nd of 54 Hz), IMU untouched.
gt      : TUM file (t[s] x y z qx qy qz qw) of T_W'I from gt/data.csv (lighthouse pose already converted by the dataset
          authors to the IMU frame and IMU clock). SteamVR's world is y-up; OpenVINS estimates in a z-up gravity-aligned
          world and posyaw alignment only rotates about z, so the GT world is rotated by the minimal rotation that maps
          the measured gravity direction (mean of R_WI a_I over the sequence) to +z. Checks (gyro vs GT body rate,
          accelerometer vs GT, time offset by cross-correlation) go to --check-out.
calib   : writes kalibr_imucam_chain.yaml / kalibr_imu_chain.yaml from the dataset's own Basalt calibration.json
          (kb4 = OpenVINS equidistant; T_imu_cam is Basalt's T_i_c = OpenVINS R_CtoI / p_CinI; IMU noise = Basalt's
          continuous-time accel/gyro noise and bias random-walk values, used verbatim).
"""
import argparse
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np


def zopen(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    # locate the 'mav0/' (EuRoC) root inside the zip
    roots = sorted({n.split('mav0/')[0] + 'mav0/' for n in names if 'mav0/' in n})
    if len(roots) != 1:
        sys.exit(f'expected one mav0/ root in {path}, got {roots[:5]}')
    return z, roots[0]


def read_csv(z, name):
    rows = []
    with z.open(name) as fh:
        for line in io.TextIOWrapper(fh, 'utf-8'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            rows.append(line.split(','))
    return rows


def cam_list(z, root, cam):
    rows = read_csv(z, f'{root}{cam}/data.csv')
    return [(int(r[0]), r[1].strip()) for r in rows]


def imu_array(z, root):
    rows = read_csv(z, f'{root}imu0/data.csv')
    a = np.array([[float(x) for x in r[:7]] for r in rows])
    return a[:, 0].astype(np.int64), a[:, 1:4], a[:, 4:7]   # t_ns, w (rad/s), a (m/s^2)


def gt_array(z, root):
    rows = read_csv(z, f'{root}gt/data.csv')
    a = np.array([[float(x) for x in r[:8]] for r in rows])
    return a[:, 0].astype(np.int64), a[:, 1:4], a[:, 4:8]    # t_ns, p, q (w x y z)


def quat_wxyz_to_rot(q):
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q.T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], 1)


def rot_to_quat_xyzw(R):
    import cv2  # noqa: F401  (only to keep the savior image's numpy/cv2 pairing consistent)
    out = np.zeros((len(R), 4))
    for i, M in enumerate(R):
        tr = np.trace(M)
        if tr > 0:
            s = np.sqrt(tr + 1.0) * 2
            w, x, y, z = 0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s
        elif M[0, 0] > M[1, 1] and M[0, 0] > M[2, 2]:
            s = np.sqrt(1.0 + M[0, 0] - M[1, 1] - M[2, 2]) * 2
            w, x, y, z = (M[2, 1] - M[1, 2]) / s, 0.25 * s, (M[0, 1] + M[1, 0]) / s, (M[0, 2] + M[2, 0]) / s
        elif M[1, 1] > M[2, 2]:
            s = np.sqrt(1.0 + M[1, 1] - M[0, 0] - M[2, 2]) * 2
            w, x, y, z = (M[0, 2] - M[2, 0]) / s, (M[0, 1] + M[1, 0]) / s, 0.25 * s, (M[1, 2] + M[2, 1]) / s
        else:
            s = np.sqrt(1.0 + M[2, 2] - M[0, 0] - M[1, 1]) * 2
            w, x, y, z = (M[1, 0] - M[0, 1]) / s, (M[0, 2] + M[2, 0]) / s, (M[1, 2] + M[2, 1]) / s, 0.25 * s
        q = np.array([x, y, z, w])
        out[i] = q if w >= 0 else -q
    return out


def so3_log(R):
    c = np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)
    th = np.arccos(c)
    v = np.stack([R[:, 2, 1] - R[:, 1, 2], R[:, 0, 2] - R[:, 2, 0], R[:, 1, 0] - R[:, 0, 1]], -1)
    s = np.where(th > 1e-9, th / (2 * np.sin(np.maximum(th, 1e-9))), 0.5)
    return v * s[:, None]


def min_rot(a, b):
    """rotation R with R a = b (unit vectors)"""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v, c = np.cross(a, b), float(a @ b)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def cmd_inspect(a):
    z, root = zopen(a.zip)
    out = {'zip': str(a.zip), 'root': root}
    for cam in ('cam0', 'cam1'):
        L = cam_list(z, root, cam)
        t = np.array([x[0] for x in L])
        out[cam] = {'n': len(L), 't0_ns': int(t[0]), 't1_ns': int(t[-1]), 'dur_s': float((t[-1] - t[0]) * 1e-9),
                    'rate_hz': float((len(t) - 1) / ((t[-1] - t[0]) * 1e-9)), 'dt_max_ms': float(np.diff(t).max() * 1e-6)}
        info = z.getinfo(root + f'{cam}/data/' + L[0][1])
        out[cam]['first_png_bytes'] = info.file_size
    t0 = np.array([x[0] for x in cam_list(z, root, 'cam0')])
    t1 = np.array([x[0] for x in cam_list(z, root, 'cam1')])
    out['stereo_same_stamps'] = bool(len(t0) == len(t1) and np.all(t0 == t1))
    ti, w, acc = imu_array(z, root)
    out['imu0'] = {'n': len(ti), 'dur_s': float((ti[-1] - ti[0]) * 1e-9), 'rate_hz': float((len(ti) - 1) / ((ti[-1] - ti[0]) * 1e-9)),
                   'acc_norm_mean': float(np.linalg.norm(acc, axis=1).mean())}
    tg, p, q = gt_array(z, root)
    out['gt'] = {'n': len(tg), 'dur_s': float((tg[-1] - tg[0]) * 1e-9), 'rate_hz': float((len(tg) - 1) / ((tg[-1] - tg[0]) * 1e-9)),
                 't0_minus_cam0_t0_s': float((tg[0] - t0[0]) * 1e-9), 'path_m': float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())}
    # first-second accelerometer excitation (static start?)
    m = ti < ti[0] + 1_000_000_000
    out['imu0']['first_1s_acc_var'] = float(np.var(np.linalg.norm(acc[m], axis=1)))
    out['files_top'] = sorted({n[len(root):].split('/')[0] for n in z.namelist() if n.startswith(root)})
    import yaml
    s = yaml.safe_dump(out, sort_keys=False)
    print(s)
    if a.out:
        Path(a.out).write_text(s)


def interp_rot(tq, t, R):
    """nearest-neighbour-free SO(3) interpolation: R(t) = R_i Exp(alpha log(R_i^T R_{i+1}))"""
    i = np.clip(np.searchsorted(t, tq) - 1, 0, len(t) - 2)
    al = np.clip((tq - t[i]) / np.maximum(t[i + 1] - t[i], 1), 0, 1)
    D = np.einsum('nji,njk->nik', R[i], R[i + 1])
    v = so3_log(D) * al[:, None]
    th = np.linalg.norm(v, axis=1)
    k = v / np.maximum(th, 1e-12)[:, None]
    K = np.zeros((len(v), 3, 3))
    K[:, 0, 1], K[:, 0, 2], K[:, 1, 2] = -k[:, 2], k[:, 1], -k[:, 0]
    K[:, 1, 0], K[:, 2, 0], K[:, 2, 1] = k[:, 2], -k[:, 1], k[:, 0]
    E = np.eye(3)[None] + np.sin(th)[:, None, None] * K + (1 - np.cos(th))[:, None, None] * K @ K
    return R[i] @ E


def cmd_gt(a):
    z, root = zopen(a.zip)
    tg, p, q = gt_array(z, root)
    o = np.argsort(tg, kind='stable')
    tg, p, q = tg[o], p[o], q[o]
    keep = np.concatenate([[True], np.diff(tg) > 0])
    tg, p, q = tg[keep], p[keep], q[keep]
    R = quat_wxyz_to_rot(q)
    ti, w, acc = imu_array(z, root)
    m = (ti > tg[0]) & (ti < tg[-1])
    ti, w, acc = ti[m], w[m], acc[m]
    Ri = interp_rot(ti.astype(float), tg.astype(float), R)
    f_w = np.einsum('nij,nj->ni', Ri, acc)          # world specific force = a_W + g_up
    # world acceleration from the GT positions (central differences on a 100 Hz grid) to remove it from the mean
    tt = np.arange(tg[0], tg[-1], 10_000_000).astype(float)
    pp = np.stack([np.interp(tt, tg.astype(float), p[:, k]) for k in range(3)], -1)
    acc_w = np.gradient(np.gradient(pp, 0.01, axis=0), 0.01, axis=0)
    g_up = f_w.mean(0) - acc_w.mean(0)
    Ra = min_rot(g_up, np.array([0.0, 0.0, 1.0]))
    p2 = p @ Ra.T
    R2 = Ra[None] @ R
    qq = rot_to_quat_xyzw(R2)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, 'w') as fh:
        fh.write('# timestamp tx ty tz qx qy qz qw  (T_world_imu, Monado MSD gt/data.csv, world rotated gravity-up by monado_prepare.py)\n')
        for k in range(len(tg)):
            fh.write(f'{tg[k] * 1e-9:.9f} {p2[k, 0]:.6f} {p2[k, 1]:.6f} {p2[k, 2]:.6f} '
                     f'{qq[k, 0]:.9f} {qq[k, 1]:.9f} {qq[k, 2]:.9f} {qq[k, 3]:.9f}\n')
    chk = {'n_gt': int(len(tg)), 'gt_rate_hz': float((len(tg) - 1) / ((tg[-1] - tg[0]) * 1e-9)),
           'g_up_world_raw': [float(x) for x in g_up / np.linalg.norm(g_up)], 'g_norm_est': float(np.linalg.norm(g_up)),
           'align_angle_deg': float(np.degrees(np.arccos(np.clip(np.trace(Ra) * 0.5 - 0.5, -1, 1))))}
    # gyro vs GT body rate on a 200 Hz grid, with a cross-correlation time offset
    tgr = np.arange(tg[0] + 50_000_000, tg[-1] - 50_000_000, 5_000_000).astype(float)
    Rg = interp_rot(tgr, tg.astype(float), R)
    wb = so3_log(np.einsum('nji,njk->nik', Rg[:-1], Rg[1:])) / 0.005
    tm = 0.5 * (tgr[:-1] + tgr[1:])
    wi = np.stack([np.interp(tm, ti.astype(float), w[:, k]) for k in range(3)], -1)
    err = np.linalg.norm(wb - wi, axis=1)
    chk['gyro_vs_gt_rate_rms_rad_s'] = float(np.sqrt(np.mean(err ** 2)))
    chk['gyro_rms_rad_s'] = float(np.sqrt(np.mean(np.sum(wi ** 2, 1))))
    sa, sb = np.linalg.norm(wb, axis=1), np.linalg.norm(wi, axis=1)
    sa, sb = sa - sa.mean(), sb - sb.mean()
    lags = np.arange(-40, 41)
    cc = [np.dot(sa[max(0, -L):len(sa) - max(0, L)], sb[max(0, L):len(sb) - max(0, -L)]) for L in lags]
    chk['gyro_gt_best_lag_ms'] = float(lags[int(np.argmax(cc))] * 5.0)
    # accelerometer check: R^T (a_W + g z) vs measured accel
    g = np.linalg.norm(g_up)
    accw2 = acc_w @ Ra.T
    ai = np.stack([np.interp(tt, ti.astype(float), acc[:, k]) for k in range(3)], -1)
    Rt = Ra[None] @ interp_rot(tt, tg.astype(float), R)
    pred = np.einsum('nji,nj->ni', Rt, accw2 + np.array([0, 0, g]))
    chk['acc_vs_gt_rms_m_s2'] = float(np.sqrt(np.mean(np.sum((pred[5:-5] - ai[5:-5]) ** 2, 1))))
    chk['path_m'] = float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
    chk['duration_s'] = float((tg[-1] - tg[0]) * 1e-9)
    import yaml
    s = yaml.safe_dump(chk, sort_keys=False)
    print(s)
    if a.check_out:
        Path(a.check_out).write_text(s)


def cmd_calib(a):
    C = json.load(open(a.json))['value0']
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def T(d):
        q = np.array([[d['qw'], d['qx'], d['qy'], d['qz']]])
        M = np.eye(4)
        M[:3, :3] = quat_wxyz_to_rot(q)[0]
        M[:3, 3] = [d['px'], d['py'], d['pz']]
        return M
    lines = ['%YAML:1.0', '',
             '# Monado SLAM Dataset, Valve Index (MI_valve_index). Generated by savior_bringup/tools/monado_prepare.py calib',
             '# from the dataset file MI_valve_index/extras/calibration.json (basalt_calibrate_imu on MIC01/MIC04; cam-IMU time',
             '# offset already applied to the released sequences, hence timeshift 0). kb4 = OpenVINS equidistant.',
             '# T_imu_cam = Basalt T_i_c (camera -> IMU: R_CtoI, p_CinI).', '']
    for k in range(2):
        M = T(C['T_imu_cam'][k])
        I = C['intrinsics'][k]
        assert I['camera_type'] == 'kb4'
        ii = I['intrinsics']
        lines += [f'cam{k}:', '  T_imu_cam: #rotation from camera to IMU R_CtoI, position of camera in IMU p_CinI']
        lines += [f'    - [{M[r, 0]:.12f}, {M[r, 1]:.12f}, {M[r, 2]:.12f}, {M[r, 3]:.12f}]' for r in range(3)]
        lines += ['    - [0.0, 0.0, 0.0, 1.0]', f'  cam_overlaps: [{1 - k}]', '  camera_model: pinhole',
                  f"  distortion_coeffs: [{ii['k1']!r}, {ii['k2']!r}, {ii['k3']!r}, {ii['k4']!r}]",
                  '  distortion_model: equidistant',
                  f"  intrinsics: [{ii['fx']!r}, {ii['fy']!r}, {ii['cx']!r}, {ii['cy']!r}] #fu, fv, cu, cv",
                  f"  resolution: [{C['resolution'][k][0]}, {C['resolution'][k][1]}]",
                  f'  rostopic: /cam{k}/image_raw', '  timeshift_cam_imu: 0.0', '']
    (out / 'kalibr_imucam_chain.yaml').write_text('\n'.join(lines))
    an, gn = C['accel_noise_std'], C['gyro_noise_std']
    ab, gb = C['accel_bias_std'], C['gyro_bias_std']
    assert len(set(an)) == len(set(gn)) == len(set(ab)) == len(set(gb)) == 1, 'anisotropic noise not supported'
    assert all(v == 0 for v in C['calib_accel_bias']) and all(v == 0 for v in C['calib_gyro_bias'])
    eye = ['    - [ 1.0, 0.0, 0.0 ]', '    - [ 0.0, 1.0, 0.0 ]', '    - [ 0.0, 0.0, 1.0 ]']
    zero = ['    - [ 0.0, 0.0, 0.0 ]'] * 3
    L = ['%YAML:1.0', '', 'imu0:', '  T_i_b:', '    - [1.0, 0.0, 0.0, 0.0]', '    - [0.0, 1.0, 0.0, 0.0]',
         '    - [0.0, 0.0, 1.0, 0.0]', '    - [0.0, 0.0, 0.0, 1.0]',
         '  # [SAVIOR] Monado MSD Valve Index calibration.json, verbatim (Basalt continuous-time values: accel_noise_std,',
         '  # gyro_noise_std = white-noise densities; accel_bias_std, gyro_bias_std = bias random walks). The dataset README',
         '  # states these were not identified (Basalt defaults). No inflation, no tuning. imu0/data.csv is already',
         '  # bias / scale-misalignment corrected (calib_*_bias all zero in calibration.json), hence identity Tw/Ta, zero Tg.',
         f'  accelerometer_noise_density: {an[0]!r}', f'  accelerometer_random_walk: {ab[0]!r}',
         f'  gyroscope_noise_density: {gn[0]!r}', f'  gyroscope_random_walk: {gb[0]!r}',
         '  rostopic: /imu0', '  time_offset: 0.0', f"  update_rate: {C['imu_update_rate']!r}", '  model: "kalibr"',
         '  Tw:'] + eye + ['  R_IMUtoGYRO:'] + eye + ['  Ta:'] + eye + ['  R_IMUtoACC:'] + eye + ['  Tg:'] + zero + ['']
    (out / 'kalibr_imu_chain.yaml').write_text('\n'.join(L))
    print('wrote', out / 'kalibr_imucam_chain.yaml', out / 'kalibr_imu_chain.yaml')


def cmd_convert(a):
    import cv2
    from rosbags.rosbag2 import StoragePlugin, Writer
    from rosbags.typesys import Stores, get_typestore
    dst = Path(a.dst)
    if dst.exists():
        sys.exit(f'destination {dst} exists, refusing to overwrite')
    ts = get_typestore(Stores.ROS2_HUMBLE)
    Image = ts.types['sensor_msgs/msg/Image']
    Imu = ts.types['sensor_msgs/msg/Imu']
    Header = ts.types['std_msgs/msg/Header']
    Time = ts.types['builtin_interfaces/msg/Time']
    Q = ts.types['geometry_msgs/msg/Quaternion']
    V3 = ts.types['geometry_msgs/msg/Vector3']
    z, root = zopen(a.zip)
    cams = {c: cam_list(z, root, c) for c in ('cam0', 'cam1')}
    ti, w, acc = imu_array(z, root)
    ev = [(t, 1, i, 'imu') for i, t in enumerate(ti)]
    for c, L in cams.items():
        keep, last = [], None
        for i, (t, _) in enumerate(L):   # OpenVINS track_frequency rule: keep a frame if t >= last kept + 1/track_hz
            if last is None or t >= last + int(round(1e9 / a.track_hz)) if a.track_hz > 0 else True:
                keep.append(i)
                last = t
        ev += [(L[i][0], 0, i, c) for i in keep]
    ev.sort(key=lambda e: (e[0], e[1], e[3]))
    cov0 = np.zeros(9)
    covm1 = np.zeros(9)
    covm1[0] = -1.0
    t0 = time.time()
    counts = {}
    shape = None
    wr = Writer(dst, version=8, storage_plugin=StoragePlugin.MCAP)
    if a.zstd:
        from rosbags.rosbag2 import CompressionFormat, CompressionMode
        wr.set_compression(CompressionMode.MESSAGE, CompressionFormat.ZSTD)
    if a.limit_s > 0:
        ev = [e for e in ev if e[0] < ev[0][0] + int(a.limit_s * 1e9)]
    with wr:
        conn = {'cam0': wr.add_connection('/cam0/image_raw', Image.__msgtype__, typestore=ts),
                'cam1': wr.add_connection('/cam1/image_raw', Image.__msgtype__, typestore=ts),
                'imu': wr.add_connection('/imu0', Imu.__msgtype__, typestore=ts)}
        for t, _, i, kind in ev:
            st = Time(sec=int(t // 1_000_000_000), nanosec=int(t % 1_000_000_000))
            if kind == 'imu':
                msg = Imu(header=Header(stamp=st, frame_id='imu0'), orientation=Q(x=0.0, y=0.0, z=0.0, w=1.0),
                          orientation_covariance=covm1,
                          angular_velocity=V3(x=float(w[i, 0]), y=float(w[i, 1]), z=float(w[i, 2])), angular_velocity_covariance=cov0,
                          linear_acceleration=V3(x=float(acc[i, 0]), y=float(acc[i, 1]), z=float(acc[i, 2])),
                          linear_acceleration_covariance=cov0)
            else:
                name = cams[kind][i][1]
                buf = np.frombuffer(z.read(f'{root}{kind}/data/{name}'), np.uint8)
                img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
                if img is None:
                    sys.exit(f'cannot decode {kind}/{name}')
                if img.ndim != 2 or img.dtype != np.uint8:
                    sys.exit(f'unexpected image {img.shape} {img.dtype} in {kind}/{name}')
                if shape is None:
                    shape = img.shape
                assert img.shape == shape
                msg = Image(header=Header(stamp=st, frame_id=kind), height=img.shape[0], width=img.shape[1], encoding='mono8',
                            is_bigendian=0, step=img.shape[1], data=np.ascontiguousarray(img).reshape(-1))
            wr.write(conn[kind], int(t), ts.serialize_cdr(msg, msg.__msgtype__))
            counts[kind] = counts.get(kind, 0) + 1
            if counts[kind] % 2000 == 0 and kind != 'imu':
                print(f'  {kind} {counts[kind]} ({time.time() - t0:.0f}s)', flush=True)
    for k in sorted(counts):
        print(f'{k:6s} {counts[k]:8d}')
    print(f'image shape {shape}; done in {time.time() - t0:.1f}s -> {dst}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('inspect'); p.add_argument('--zip', required=True); p.add_argument('--out', default='')
    p = sub.add_parser('gt'); p.add_argument('--zip', required=True); p.add_argument('--out', required=True)
    p.add_argument('--check-out', default='')
    p = sub.add_parser('calib'); p.add_argument('--json', required=True); p.add_argument('--out-dir', required=True)
    p = sub.add_parser('convert'); p.add_argument('--zip', required=True); p.add_argument('--dst', required=True)
    p.add_argument('--zstd', action='store_true', help='rosbag2 MESSAGE-mode zstd compression (lossless; ~3x smaller)')
    p.add_argument('--limit-s', type=float, default=0.0, help='convert only the first N seconds (tests)')
    p.add_argument('--track-hz', type=float, default=0.0, help='keep only the stereo pairs OpenVINS track_frequency=HZ would track '
                   '(t >= last kept + 1/HZ, from the first frame); 0 = all; IMU untouched')
    a = ap.parse_args()
    {'inspect': cmd_inspect, 'gt': cmd_gt, 'calib': cmd_calib, 'convert': cmd_convert}[a.cmd](a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
