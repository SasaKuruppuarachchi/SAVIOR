#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""VIODE (Minoda et al., RA-L 2021, AirSim, CC BY 4.0) dataset preparation: inspection, ground truth, IMU noise,
segmentation colours.

Reads the original ROS1 bags directly with `rosbags` (pure python). Run inside the savior image, e.g.

  python3 -I viode_prepare.py inspect   --bag 0_none.bag [--out inspect.yaml]
  python3 -I viode_prepare.py gt        --bag 0_none.bag --out gt/parking_lot_none.txt [--check-out check.yaml]
  python3 -I viode_prepare.py imunoise  --bag 0_none.bag [--out imu_noise.yaml]
  python3 -I viode_prepare.py segcolors --bag 0_none.bag --rgb-ids rgb_ids.txt --vehicle-ids vehicle_ids_x.txt
  python3 -I viode_prepare.py convert   --bag 0_none.bag --dst ros2/parking_lot_none --rgb-ids rgb_ids.txt

`convert` writes a ROS 2 (mcap) bag with /cam{0,1}/image_raw (rgb8, verbatim), /imu0, /odometry (verbatim) and
/cam{0,1}/segmentation re-encoded LOSSLESSLY as mono8 object-id images (pixel = AirSim object id from rgb_ids.txt;
colours not in the table -> 0; measured share 5e-6 on parking_lot high). This cuts the bag from 5.2 to ~3.4 GB; the
oracle colour maps (config/oracle/viode_<env>_colormap.yaml) therefore list grey triplets [id, id, id].

Conversion to ROS 2 is done with bag1_to_ros2.py (same folder).

Frames (checked numerically by `gt`, results in the --check-out yaml):
  * /imu0 and /odometry come from the AirSim ROS wrapper: NED world, NED body (x forward, y right, z down).
    `gt` verifies that the /odometry child frame IS the IMU frame (gyro vs body rate from the differentiated GT
    orientation; accelerometer vs R^T (a - g) from the differentiated GT velocity / position, no lever arm),
    estimates the best rotation between the two (Kabsch on the angular rates) and the time offset (cross-correlation).
  * OpenVINS estimates in a z-UP gravity-aligned world, and posyaw alignment can only rotate about z, so the GT
    world is turned by 180 deg about x (NED -> "NWU-like": x north, y west, z up) before writing:
        T_W'I = R_x(pi) T_WI      (body/IMU frame unchanged: the TUM file is T_world'_imu)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from rosbags.rosbag1 import Reader
from rosbags.typesys import Stores, get_typestore, get_types_from_msg

T_IMU = '/imu0'
T_ODOM = '/odometry'
T_SEG = ('/cam0/segmentation', '/cam1/segmentation')
R_FLIP = np.diag([1.0, -1.0, -1.0])   # R_x(pi): NED world -> z-up world


def open_bag(path):
    r = Reader(Path(path))
    r.open()
    ts = get_typestore(Stores.ROS1_NOETIC)
    add = {}
    for c in r.connections:
        add.update(get_types_from_msg(c.msgdef.data, c.msgtype))
    ts.register(add)
    return r, ts


def stamp(h):
    return int(h.stamp.sec) * 1_000_000_000 + int(h.stamp.nanosec)


def read_topics(r, ts, topics, fn):
    conns = [c for c in r.connections if c.topic in topics]
    for c, t, raw in r.messages(connections=conns):
        fn(c.topic, t, ts.deserialize_ros1(raw, c.msgtype))


def quat_to_rot(q):  # q (N,4) xyzw -> (N,3,3)
    x, y, z, w = q.T
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - z * w); R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w); R[:, 2, 1] = 2 * (y * z + x * w); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def rot_to_quat(R):  # (N,3,3) -> (N,4) xyzw, w >= 0
    from scipy.spatial.transform import Rotation
    q = Rotation.from_matrix(R).as_quat()
    q[q[:, 3] < 0] *= -1
    return q


def so3_log(R):
    c = np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)
    th = np.arccos(c)
    v = np.stack([R[:, 2, 1] - R[:, 1, 2], R[:, 0, 2] - R[:, 2, 0], R[:, 1, 0] - R[:, 0, 1]], 1)
    s = np.where(th < 1e-9, 0.5, th / (2 * np.sin(np.maximum(th, 1e-12))))
    return v * s[:, None]


def kabsch(a, b):
    """R minimising |R a_i - b_i| (a, b: N x 3)."""
    H = a.T @ b
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T


# ----------------------------------------------------------------------------------------------- inspect
def cmd_inspect(a):
    import yaml
    r, ts = open_bag(a.bag)
    dur = r.duration / 1e9
    out = {'bag': str(a.bag), 'duration_s': dur, 'start_s': r.start_time / 1e9, 'topics': {}}
    for c in sorted(r.connections, key=lambda c: c.topic):
        out['topics'][c.topic] = {'type': c.msgtype, 'count': c.msgcount, 'rate_hz': round(c.msgcount / dur, 3)}
    first, stamps, bagt = {}, {}, {}

    def fn(topic, t, m):
        if hasattr(m, 'header'):
            stamps.setdefault(topic, []).append(stamp(m.header))
            bagt.setdefault(topic, []).append(t)
        if topic not in first:
            d = {'frame_id': m.header.frame_id if hasattr(m, 'header') else None}
            for k in ('height', 'width', 'encoding', 'step', 'child_frame_id'):
                if hasattr(m, k):
                    d[k] = getattr(m, k)
            first[topic] = d

    read_topics(r, ts, [c.topic for c in r.connections], fn)
    r.close()
    for t, st in stamps.items():
        st = np.asarray(st, np.int64)
        dt = np.diff(np.sort(st)) / 1e9
        bt = np.asarray(bagt[t], np.int64)
        out['topics'][t].update(first[t])
        out['topics'][t].update({
            'stamp_first_s': float(st.min() / 1e9), 'stamp_last_s': float(st.max() / 1e9),
            'dt_median_s': float(np.median(dt)) if dt.size else None, 'dt_min_s': float(dt.min()) if dt.size else None,
            'dt_max_s': float(dt.max()) if dt.size else None, 'n_dup_stamps': int(np.sum(dt == 0)),
            'n_nonmonotonic': int(np.sum(np.diff(st) < 0)),
            'bag_minus_stamp_median_s': float(np.median(bt - st) / 1e9)})
    # stereo / segmentation stamp sync
    def sset(t):
        return set(stamps.get(t, []))
    c0, c1 = sset('/cam0/image_raw'), sset('/cam1/image_raw')
    s0, s1 = sset(T_SEG[0]), sset(T_SEG[1])
    out['sync'] = {'cam0': len(c0), 'cam1': len(c1), 'cam0&cam1': len(c0 & c1), 'cam0&seg0': len(c0 & s0),
                   'cam1&seg1': len(c1 & s1), 'cam0&odom': len(c0 & sset(T_ODOM)), 'cam0&imu': len(c0 & sset(T_IMU))}
    txt = yaml.safe_dump(out, sort_keys=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt)
    print(txt)


# ----------------------------------------------------------------------------------------------- gt
def load_odom_imu(bag):
    r, ts = open_bag(bag)
    odom, imu, frames = [], [], {}

    def fn(topic, t, m):
        if topic == T_ODOM:
            p, q = m.pose.pose.position, m.pose.pose.orientation
            v, w = m.twist.twist.linear, m.twist.twist.angular
            odom.append((stamp(m.header), p.x, p.y, p.z, q.x, q.y, q.z, q.w, v.x, v.y, v.z, w.x, w.y, w.z))
            frames['odom'] = (m.header.frame_id, m.child_frame_id)
        else:
            w, ac = m.angular_velocity, m.linear_acceleration
            imu.append((stamp(m.header), w.x, w.y, w.z, ac.x, ac.y, ac.z))
            frames['imu'] = m.header.frame_id

    read_topics(r, ts, [T_ODOM, T_IMU], fn)
    r.close()
    odom = np.array(sorted(odom), dtype=np.float64)
    _, u = np.unique(odom[:, 0], return_index=True)
    odom = odom[u]
    imu = np.array(sorted(imu), dtype=np.float64)
    _, u = np.unique(imu[:, 0], return_index=True)
    imu = imu[u]
    return odom, imu, frames


def body_rates(odom):
    """Body angular rate between consecutive GT samples (assigned to the interval midpoint)."""
    q = odom[:, 4:8] / np.linalg.norm(odom[:, 4:8], axis=1, keepdims=True)
    R = quat_to_rot(q)
    t = odom[:, 0] / 1e9
    dt = np.diff(t)
    w = so3_log(np.einsum('nji,njk->nik', R[:-1], R[1:])) / dt[:, None]
    return 0.5 * (t[1:] + t[:-1]), w, R, t


def interp(tq, t, x):
    return np.stack([np.interp(tq, t, x[:, j]) for j in range(x.shape[1])], 1)


def cmd_gt(a):
    import yaml
    odom, imu, frames = load_odom_imu(a.bag)
    tm, w_gt, R, t = body_rates(odom)
    ti = imu[:, 0] / 1e9
    chk = {'bag': str(a.bag), 'frames': {k: list(v) if isinstance(v, tuple) else v for k, v in frames.items()},
           'n_odom': int(len(odom)), 'n_imu': int(len(imu)),
           'odom_rate_hz': float(1 / np.median(np.diff(t))), 'imu_rate_hz': float(1 / np.median(np.diff(ti)))}
    # ---- gyro: time offset by cross-correlation of |w|, then residual and best-fit rotation
    w_i = interp(tm, ti, imu[:, 1:4])
    best = None
    for off in np.arange(-0.05, 0.0501, 0.0025):
        wi = interp(tm + off, ti, imu[:, 1:4])
        e = float(np.sqrt(((wi - w_gt) ** 2).sum(1).mean()))
        if best is None or e < best[1]:
            best = (float(off), e)
    chk['gyro_time_offset_s(t_imu=t_gt+off)'] = best[0]
    res = w_i - w_gt
    R_fit = kabsch(w_gt, w_i)
    chk['gyro'] = {'rms_rate_rad_s': float(np.sqrt((w_gt ** 2).sum(1).mean())),
                   'residual_rms_per_axis': np.sqrt((res ** 2).mean(0)).round(6).tolist(),
                   'residual_mean_per_axis(bias)': res.mean(0).round(6).tolist(),
                   'kabsch_R_imu_from_odomchild': R_fit.round(5).tolist(),
                   'kabsch_angle_deg': float(np.degrees(np.linalg.norm(so3_log(R_fit[None])[0])))}
    # ---- accelerometer: GT velocity (twist, if present) or positions, differentiated; NED gravity +z
    acc_i = imu[:, 4:7]
    chk['accel_norm_median'] = float(np.median(np.linalg.norm(acc_i, axis=1)))
    p = odom[:, 1:4]
    v_tw = odom[:, 8:11]
    out_acc = {}
    # velocity from positions (central difference) -> acceleration (central difference of v), smoothed
    v_p = np.gradient(p, t, axis=0)
    for name, v in (('twist_linear', v_tw), ('pos_diff', v_p)):
        if not np.any(v):
            continue
        k = 9
        ker = np.ones(k) / k
        vs = np.stack([np.convolve(v[:, j], ker, 'same') for j in range(3)], 1)
        acc_w = np.gradient(vs, t, axis=0)
        for gname, g in (('ned_g+z', np.array([0, 0, 9.80665])), ('enu_g-z', np.array([0, 0, -9.80665]))):
            for frame in ('world', 'body'):
                if frame == 'world':
                    f = np.einsum('nji,nj->ni', R, acc_w - g)       # specific force in body
                else:   # twist in child (body) frame: a_world = R d(v_b)/dt + w x v ... skip, only report world
                    continue
                fi = interp(t, ti, acc_i)
                sl = slice(k, -k)
                r_ = (fi - f)[sl]
                out_acc[f'{name}/{gname}'] = {'residual_mean': r_.mean(0).round(4).tolist(),
                                              'residual_median_abs': np.median(np.abs(r_), 0).round(4).tolist(),
                                              'residual_rms': np.sqrt((r_ ** 2).mean(0)).round(4).tolist()}
    chk['accel'] = out_acc
    # ---- twist frame check: v_twist vs position derivative in world and in body
    if np.any(v_tw):
        e_w = np.sqrt(((v_tw - v_p) ** 2).sum(1).mean())
        v_pb = np.einsum('nji,nj->ni', R, v_p)
        e_b = np.sqrt(((v_tw - v_pb) ** 2).sum(1).mean())
        chk['twist_linear_frame'] = {'rms_vs_world_posdiff': float(e_w), 'rms_vs_body_posdiff': float(e_b)}
    # ---- write GT, z-up world
    Rw = np.einsum('ij,njk->nik', R_FLIP, R)
    pw = p @ R_FLIP.T
    qw = rot_to_quat(Rw)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as fh:
        fh.write('# timestamp tx ty tz qx qy qz qw  (T_world_imu; VIODE /odometry, NED world turned by R_x(pi) -> z up; '
                 'body = IMU frame, checked by viode_prepare.py gt)\n')
        for k in range(len(odom)):
            fh.write(f'{t[k]:.9f} {pw[k,0]:.6f} {pw[k,1]:.6f} {pw[k,2]:.6f} '
                     f'{qw[k,0]:.9f} {qw[k,1]:.9f} {qw[k,2]:.9f} {qw[k,3]:.9f}\n')
    chk['gt_file'] = str(out)
    chk['gt_span_s'] = [float(t[0]), float(t[-1])]
    chk['path_length_m'] = float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
    txt = yaml.safe_dump(chk, sort_keys=False)
    if a.check_out:
        Path(a.check_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.check_out).write_text(txt)
    print(txt)


# ----------------------------------------------------------------------------------------------- imu noise
def allan(x, dt, taus):
    """Overlapping Allan deviation of rate signal x (N,) sampled at dt for averaging times taus."""
    out = []
    cs = np.concatenate([[0], np.cumsum(x) * dt])
    for tau in taus:
        m = int(round(tau / dt))
        if m < 1 or 2 * m >= len(x):
            out.append(np.nan)
            continue
        th = cs
        d = th[2 * m:] - 2 * th[m:-m] + th[:-2 * m]
        out.append(np.sqrt(np.mean(d ** 2) / (2 * (m * dt) ** 2)))
    return np.array(out)


def cmd_imunoise(a):
    """White-noise density from (imu - GT) residuals. GT body rate / specific force come from the exact simulator
    poses (differentiated), so residual = bias + white noise (+ differentiation error, small for the gyro).
    High-pass (residual minus its 1-s moving average) removes the bias; density = std * sqrt(dt)."""
    import yaml
    odom, imu, _ = load_odom_imu(a.bag)
    tm, w_gt, R, t = body_rates(odom)
    ti = imu[:, 0] / 1e9
    dt = float(np.median(np.diff(ti)))
    w_ref = interp(ti, tm, w_gt)
    res_g = imu[:, 1:4] - w_ref
    p = odom[:, 1:4]
    k = 9
    ker = np.ones(k) / k
    v = np.gradient(p, t, axis=0)
    vs = np.stack([np.convolve(v[:, j], ker, 'same') for j in range(3)], 1)
    acc_w = np.gradient(vs, t, axis=0)
    f = np.einsum('nji,nj->ni', R, acc_w - np.array([0, 0, 9.80665]))
    res_a = imu[:, 4:7] - interp(ti, t, f)
    sl = slice(50, -50)
    out = {'bag': str(a.bag), 'dt': dt}
    nmov = int(round(1.0 / dt))
    for name, res in (('gyro', res_g[sl]), ('accel', res_a[sl])):
        hp = res - np.stack([np.convolve(res[:, j], np.ones(nmov) / nmov, 'same') for j in range(3)], 1)
        hp = hp[nmov:-nmov]
        # first difference: removes the bias and smooth reference errors; white -> var(diff) = 2 sigma_d^2
        d1 = np.diff(res, axis=0)
        out[name] = {
            'density_hp': (hp.std(0) * np.sqrt(dt)).round(7).tolist(),
            'density_diff': (d1.std(0) / np.sqrt(2) * np.sqrt(dt)).round(7).tolist(),
            'lag1_autocorr': [float(np.corrcoef(res[:-1, j] - res[:, j].mean(), res[1:, j] - res[:, j].mean())[0, 1])
                              for j in range(3)],
            'mean(bias)': res.mean(0).round(6).tolist(),
            'allan_dev_tau[0.01,0.1,1,10]': [allan(res[:, j], dt, [0.01, 0.1, 1.0, 10.0]).round(7).tolist()
                                             for j in range(3)]}
    txt = yaml.safe_dump(out, sort_keys=False)
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)


# ----------------------------------------------------------------------------------------------- segmentation
def cmd_segcolors(a):
    """Colour histogram of the segmentation images (every --every frame): checks the encoding (rgb/bgr) against
    rgb_ids.txt, lists unknown colours (anti-aliasing?) and the per-vehicle pixel share per camera."""
    import yaml
    ids = {}
    for line in open(a.rgb_ids):
        parts = [x.strip() for x in line.split(',')]
        if len(parts) == 4 and parts[0].isdigit():
            ids[(int(parts[1]), int(parts[2]), int(parts[3]))] = int(parts[0])
    veh = {}
    if a.vehicle_ids:
        for line in open(a.vehicle_ids):
            parts = [x.strip() for x in line.split(',')]
            if len(parts) == 2 and parts[0].isdigit():
                veh[int(parts[0])] = parts[1]
    r, ts = open_bag(a.bag)
    hist = {T_SEG[0]: {}, T_SEG[1]: {}}
    nfr = {T_SEG[0]: 0, T_SEG[1]: 0}
    veh_frames = {T_SEG[0]: {}, T_SEG[1]: {}}
    dyn_share = {T_SEG[0]: [], T_SEG[1]: []}
    enc = {}
    cnt = {T_SEG[0]: 0, T_SEG[1]: 0}

    def fn(topic, t, m):
        cnt[topic] += 1
        if (cnt[topic] - 1) % a.every:
            return
        enc[topic] = m.encoding
        img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width * 3].reshape(m.height, m.width, 3)
        if m.encoding.lower().startswith('bgr'):
            img = img[:, :, ::-1]   # -> rgb
        key = (img[..., 0].astype(np.int64) << 16) | (img[..., 1].astype(np.int64) << 8) | img[..., 2]
        u, c = np.unique(key, return_counts=True)
        h = hist[topic]
        npx = img.shape[0] * img.shape[1]
        dyn = 0
        for kk, cc in zip(u.tolist(), c.tolist()):
            h[kk] = h.get(kk, 0) + cc
            rgb = ((kk >> 16) & 255, (kk >> 8) & 255, kk & 255)
            i = ids.get(rgb)
            if i in veh:
                veh_frames[topic][i] = veh_frames[topic].get(i, 0) + 1
                if 'dynamic' in veh[i]:
                    dyn += cc
        dyn_share[topic].append(dyn / npx)
        nfr[topic] += 1

    read_topics(r, ts, list(T_SEG), fn)
    r.close()
    out = {'bag': str(a.bag), 'every': a.every, 'encoding': enc}
    for topic in T_SEG:
        h = hist[topic]
        tot = sum(h.values())
        rows = []
        unknown = 0
        for kk, cc in sorted(h.items(), key=lambda x: -x[1]):
            rgb = ((kk >> 16) & 255, (kk >> 8) & 255, kk & 255)
            i = ids.get(rgb, None)
            if i is None:
                unknown += cc
            rows.append({'rgb': list(rgb), 'id': i, 'name': veh.get(i, ''), 'share': round(cc / tot, 6)})
        ds = np.asarray(dyn_share[topic])
        out[topic] = {'frames': nfr[topic], 'n_colours': len(h), 'unknown_colour_share': round(unknown / tot, 6),
                      'colours': rows[:a.top], 'vehicle_rows': [r_ for r_ in rows if r_['name']],
                      'vehicle_frames': {veh[i]: n for i, n in sorted(veh_frames[topic].items())},
                      'dynamic_px_share_mean': float(ds.mean()) if ds.size else 0.0,
                      'dynamic_px_share_max': float(ds.max()) if ds.size else 0.0,
                      'frames_dyn_gt_5pct': float((ds > 0.05).mean()) if ds.size else 0.0}
    txt = yaml.safe_dump(out, sort_keys=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt)
    print(txt)


# ----------------------------------------------------------------------------------------------- convert
def cmd_convert(a):
    from rosbags.rosbag2 import StoragePlugin, Writer
    from rosbags.typesys import get_typestore as gts
    import dataclasses
    import time
    ids = {}
    for line in open(a.rgb_ids):
        parts = [x.strip() for x in line.split(',')]
        if len(parts) == 4 and parts[0].isdigit():
            ids[(int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])] = int(parts[0])
    keys = np.array(sorted(ids), np.int64)
    vals = np.array([ids[k] for k in keys], np.uint8)
    dst = Path(a.dst)
    if dst.exists():
        sys.exit(f'destination {dst} exists, refusing to overwrite')
    ts2 = gts(Stores.ROS2_HUMBLE)
    r, ts1 = open_bag(a.bag)
    topics = ['/cam0/image_raw', '/cam1/image_raw', '/cam0/segmentation', '/cam1/segmentation', '/imu0', '/odometry']
    t0 = time.time()
    counts, unknown, total = {}, 0, 0
    with Writer(dst, version=8, storage_plugin=StoragePlugin.MCAP) as w:
        wc = {}
        for c in r.connections:
            if c.topic in topics and c.topic not in wc:
                wc[c.topic] = w.add_connection(c.topic, c.msgtype, typestore=ts2)
        conns = [c for c in r.connections if c.topic in topics]
        for c, t, raw in r.messages(connections=conns):
            cdr = ts2.ros1_to_cdr(raw, c.msgtype)
            if c.topic.endswith('/segmentation'):
                m = ts2.deserialize_cdr(cdr, c.msgtype)
                if m.encoding != 'rgb8':
                    sys.exit(f'unexpected segmentation encoding {m.encoding}')
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width * 3].reshape(m.height, m.width, 3)
                k = (img[..., 0].astype(np.int64) << 16) | (img[..., 1].astype(np.int64) << 8) | img[..., 2]
                i = np.clip(np.searchsorted(keys, k), 0, len(keys) - 1)
                hit = keys[i] == k
                out = np.where(hit, vals[i], 0).astype(np.uint8)
                unknown += int((~hit).sum())
                total += hit.size
                m = dataclasses.replace(m, encoding='mono8', step=m.width, data=out.reshape(-1))
                cdr = ts2.serialize_cdr(m, c.msgtype)
            w.write(wc[c.topic], t, cdr)
            counts[c.topic] = counts.get(c.topic, 0) + 1
    r.close()
    for k in sorted(counts):
        print(f'{k:30s} {counts[k]:8d}')
    print(f'segmentation: unknown colour share {unknown / max(1, total):.2e} ({unknown} px) -> id 0')
    print(f'done in {time.time() - t0:.1f}s -> {dst}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('inspect'); p.add_argument('--bag', required=True); p.add_argument('--out', default='')
    p = sub.add_parser('gt'); p.add_argument('--bag', required=True); p.add_argument('--out', required=True)
    p.add_argument('--check-out', default='')
    p = sub.add_parser('imunoise'); p.add_argument('--bag', required=True); p.add_argument('--out', default='')
    p = sub.add_parser('segcolors'); p.add_argument('--bag', required=True); p.add_argument('--out', default='')
    p.add_argument('--rgb-ids', required=True); p.add_argument('--vehicle-ids', default='')
    p.add_argument('--every', type=int, default=20); p.add_argument('--top', type=int, default=25)
    p = sub.add_parser('convert'); p.add_argument('--bag', required=True); p.add_argument('--dst', required=True)
    p.add_argument('--rgb-ids', required=True)
    a = ap.parse_args()
    {'convert': cmd_convert, 'inspect': cmd_inspect, 'gt': cmd_gt, 'imunoise': cmd_imunoise, 'segcolors': cmd_segcolors}[a.cmd](a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
