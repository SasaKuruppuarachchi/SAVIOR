#!/usr/bin/env python3
"""uHumans2 (TESSE) dataset preparation: inspection, ground truth, IMU noise identification.

Reads the original ROS1 bag directly with `rosbags` (pure python, handles compressed bags).
Run inside the ros2_humble container, e.g.

  python3 -I uhumans2_prepare.py inspect  --bag uHumans2_office_s1_00h.bag [--out inspect.yaml]
  python3 -I uhumans2_prepare.py gt       --bag uHumans2_office_s1_00h.bag --out gt/office_s1_00h.txt
  python3 -I uhumans2_prepare.py imunoise --bag uHumans2_office_s1_00h.bag [--out imu_noise.yaml]
  python3 -I uhumans2_prepare.py segcolors --bag ... [--every 50]

Conversion to ROS 2 is done with bag1_to_ros2.py (same folder).

Frames (from /tf_static and message headers of office_s1_00h):
  * IMU messages: frame_id = base_link_gt;  /tesse/odom: frame world -> child base_link_gt.
    => the GT pose already IS the IMU pose (T_world_imu); no extrinsic needs to be applied.
    `gt` additionally verifies this numerically: the clean gyro is compared with the body angular
    rate obtained by differentiating the GT orientation (residual must be ~0), and the clean accel
    with R^T (p_dd - g) from the GT positions (residual small => no lever arm between odom and IMU).
  * base_link_gt -> left_cam  t=(0, +0.05, 0), base_link_gt -> right_cam t=(0, -0.05, 0),
    q(xyzw)=(0.5,-0.5,0.5,-0.5)  (camera z = body x, camera x = -body y, camera y = -body z).

IMU noise method (`imunoise`): TESSE publishes clean (ideal) IMU, noisy IMU and the injected biases.
  model: noisy_k = clean_k + b_k + n_k, n_k white with discrete std sigma_d.
  * white noise density   sigma_c = std(noisy - clean - bias) * sqrt(dt)          [unit/sqrt(Hz)]
  * bias random walk      sigma_bc = std(b_{k+1} - b_k) / sqrt(dt)                [unit/s/sqrt(Hz)]
  * cross-check: overlapping Allan deviation of (noisy - clean): N = adev(tau=1s) on the -1/2 slope
    segment, K = adev(tau)*sqrt(3/tau) on the +1/2 slope segment.
  dt is the median IMU sampling period (200 Hz -> 0.005 s). Samples are matched by exact header stamp.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from rosbags.rosbag1 import Reader
from rosbags.typesys import Stores, get_typestore, get_types_from_msg

T_IMU_CLEAN = '/tesse/imu/clean/imu'
T_IMU_NOISY = '/tesse/imu/noisy/imu'
T_BIAS_A = '/tesse/imu/noisy/biases/accel'
T_BIAS_G = '/tesse/imu/noisy/biases/gyro'
T_ODOM = '/tesse/odom'


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
    """fn(topic, bagtime_ns, msg) for every message of the given topics."""
    conns = [c for c in r.connections if c.topic in topics]
    for c, t, raw in r.messages(connections=conns):
        fn(c.topic, t, ts.deserialize_ros1(raw, c.msgtype))


# ----------------------------------------------------------------------------------------------- inspect
def cmd_inspect(a):
    r, ts = open_bag(a.bag)
    dur = r.duration / 1e9
    out = {'bag': str(a.bag), 'duration_s': dur, 'start_s': r.start_time / 1e9, 'topics': {}}
    for c in sorted(r.connections, key=lambda c: c.topic):
        out['topics'][c.topic] = {'type': c.msgtype, 'count': c.msgcount, 'rate_hz': round(c.msgcount / dur, 3)}
    first = {}
    stamps = {}

    def fn(topic, t, m):
        if hasattr(m, 'header'):
            stamps.setdefault(topic, []).append(stamp(m.header))
        if topic in first:
            return
        if topic.endswith('camera_info'):
            first[topic] = {'frame_id': m.header.frame_id, 'width': int(m.width), 'height': int(m.height),
                            'distortion_model': m.distortion_model, 'D': m.D.tolist(), 'K': m.K.tolist(),
                            'R': m.R.tolist(), 'P': m.P.tolist()}
        elif m.__msgtype__ == 'sensor_msgs/msg/Image':
            first[topic] = {'frame_id': m.header.frame_id, 'width': int(m.width), 'height': int(m.height),
                            'encoding': m.encoding, 'step': int(m.step)}
        elif topic == '/tf_static':
            first[topic] = [{'parent': tr.header.frame_id, 'child': tr.child_frame_id,
                             't': [tr.transform.translation.x, tr.transform.translation.y, tr.transform.translation.z],
                             'q_xyzw': [tr.transform.rotation.x, tr.transform.rotation.y, tr.transform.rotation.z,
                                        tr.transform.rotation.w]} for tr in m.transforms]
        elif topic == T_ODOM:
            first[topic] = {'frame_id': m.header.frame_id, 'child_frame_id': m.child_frame_id}
        elif hasattr(m, 'header'):
            first[topic] = {'frame_id': m.header.frame_id}

    skip = {'/tesse/left_cam/rgb/image_raw', '/tesse/right_cam/rgb/image_raw', '/tesse/depth_cam/mono/image_raw',
            '/tesse/front_lidar/scan', '/tesse/rear_lidar/scan'} if a.fast else set()
    read_topics(r, ts, [c.topic for c in r.connections if c.topic not in skip and c.topic != '/tf'], fn)
    out['first_msgs'] = first
    out['header_stamp_stats'] = {}
    for k, v in stamps.items():
        v = np.asarray(sorted(v))
        if len(v) > 2:
            d = np.diff(v) / 1e9
            out['header_stamp_stats'][k] = {'n': len(v), 'dt_median': float(np.median(d)), 'dt_min': float(d.min()),
                                            'dt_max': float(d.max()), 'n_dup': int((d == 0).sum())}
    r.close()
    import yaml
    txt = yaml.safe_dump(out, sort_keys=False, default_flow_style=None, width=140)
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)


# ----------------------------------------------------------------------------------------------- quaternion utils
def quat_to_rot(q):  # q (N,4) xyzw -> (N,3,3)
    x, y, z, w = q.T
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - z * w); R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w); R[:, 2, 1] = 2 * (y * z + x * w); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def so3_log(R):
    c = np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)
    th = np.arccos(c)
    v = np.stack([R[:, 2, 1] - R[:, 1, 2], R[:, 0, 2] - R[:, 2, 0], R[:, 1, 0] - R[:, 0, 1]], 1)
    s = np.where(th < 1e-9, 0.5, th / (2 * np.sin(np.maximum(th, 1e-12))))
    return v * s[:, None]


# ----------------------------------------------------------------------------------------------- gt
def cmd_gt(a):
    r, ts = open_bag(a.bag)
    odom, imu = [], []

    def fn(topic, t, m):
        if topic == T_ODOM:
            p, q = m.pose.pose.position, m.pose.pose.orientation
            odom.append((stamp(m.header), p.x, p.y, p.z, q.x, q.y, q.z, q.w))
            if m.child_frame_id != 'base_link_gt':
                sys.exit(f'unexpected odom child frame {m.child_frame_id}')
        else:
            w, ac = m.angular_velocity, m.linear_acceleration
            imu.append((stamp(m.header), w.x, w.y, w.z, ac.x, ac.y, ac.z))
            if m.header.frame_id != 'base_link_gt':
                sys.exit(f'unexpected imu frame {m.header.frame_id}')

    read_topics(r, ts, [T_ODOM, T_IMU_CLEAN], fn)
    r.close()
    odom = np.array(sorted(odom), dtype=np.float64)
    # dedupe identical stamps
    _, uidx = np.unique(odom[:, 0], return_index=True)
    odom = odom[uidx]
    q = odom[:, 4:8] / np.linalg.norm(odom[:, 4:8], axis=1, keepdims=True)
    tsec = odom[:, 0] / 1e9
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as f:
        f.write('# timestamp tx ty tz qx qy qz qw  (T_world_imu, frame base_link_gt = IMU, from /tesse/odom)\n')
        for k in range(len(odom)):
            f.write(f'{tsec[k]:.9f} {odom[k,1]:.6f} {odom[k,2]:.6f} {odom[k,3]:.6f} '
                    f'{q[k,0]:.9f} {q[k,1]:.9f} {q[k,2]:.9f} {q[k,3]:.9f}\n')
    print(f'wrote {len(odom)} poses to {out}  ({tsec[0]:.3f} .. {tsec[-1]:.3f} s)')

    # ---- verification that base_link_gt == IMU frame (rotation and lever arm)
    imu = np.array(sorted(imu), dtype=np.float64)
    common, io, ii = np.intersect1d(odom[:, 0], imu[:, 0], return_indices=True)
    R = quat_to_rot(q[io])
    dt = np.diff(common) / 1e9
    w_gt = so3_log(np.einsum('nji,njk->nik', R[:-1], R[1:])) / dt[:, None]  # body rate (forward diff)
    w_imu = 0.5 * (imu[ii[:-1], 1:4] + imu[ii[1:], 1:4])
    res_w = w_gt - w_imu
    print(f'gyro check: |w_imu| rms {np.sqrt((w_imu**2).sum(1).mean()):.4f} rad/s, '
          f'residual rms per axis {np.sqrt((res_w**2).mean(0))} rad/s')
    # accel: central second difference of position, 5-sample smoothing
    p = odom[io, 1:4]
    tt = common / 1e9
    pdd = np.zeros_like(p)
    pdd[1:-1] = 2 * ((p[2:] - p[1:-1]) / (tt[2:] - tt[1:-1])[:, None] - (p[1:-1] - p[:-2]) / (tt[1:-1] - tt[:-2])[:, None]) \
        / (tt[2:] - tt[:-2])[:, None]
    for g in (9.81, 9.80665):
        f_pred = np.einsum('nji,nj->ni', R, pdd + np.array([0, 0, g]))
        res_a = f_pred[1:-1] - imu[ii[1:-1], 4:7]
        k = 5
        ker = np.ones(k) / k
        res_s = np.stack([np.convolve(res_a[:, j], ker, 'same') for j in range(3)], 1)
        print(f'accel check (g={g}): residual mean {res_s.mean(0)} median-abs {np.median(np.abs(res_s),0)} m/s^2')
    acc_norm = np.linalg.norm(imu[:, 4:7], axis=1)
    print(f'clean accel norm: median {np.median(acc_norm):.5f} m/s^2')


# ----------------------------------------------------------------------------------------------- imu noise
def allan(x, dt, taus):
    """Overlapping Allan deviation of rate signal x (N,) sampled at dt for averaging times taus."""
    th = np.cumsum(x) * dt
    th = np.concatenate([[0.0], th])
    N = len(th)
    out = []
    for tau in taus:
        m = int(round(tau / dt))
        if m < 1 or 2 * m >= N:
            out.append(np.nan); continue
        d = th[2 * m:] - 2 * th[m:-m] + th[:-2 * m]
        out.append(np.sqrt(np.sum(d * d) / (2 * (m * dt) ** 2 * (N - 2 * m))))
    return np.array(out)


def cmd_imunoise(a):
    r, ts = open_bag(a.bag)
    data = {T_IMU_CLEAN: {}, T_IMU_NOISY: {}, T_BIAS_A: {}, T_BIAS_G: {}}

    def fn(topic, t, m):
        s = stamp(m.header)
        if topic in (T_IMU_CLEAN, T_IMU_NOISY):
            w, ac = m.angular_velocity, m.linear_acceleration
            data[topic][s] = (w.x, w.y, w.z, ac.x, ac.y, ac.z)
        else:
            data[topic][s] = (m.vector.x, m.vector.y, m.vector.z)

    read_topics(r, ts, list(data), fn)
    r.close()
    keys = sorted(set(data[T_IMU_CLEAN]) & set(data[T_IMU_NOISY]) & set(data[T_BIAS_A]) & set(data[T_BIAS_G]))
    print({k: len(v) for k, v in data.items()}, 'common stamps', len(keys))
    st = np.array(keys, dtype=np.int64)
    dt = float(np.median(np.diff(st))) / 1e9
    clean = np.array([data[T_IMU_CLEAN][k] for k in keys])
    noisy = np.array([data[T_IMU_NOISY][k] for k in keys])
    ba = np.array([data[T_BIAS_A][k] for k in keys])
    bg = np.array([data[T_BIAS_G][k] for k in keys])
    gaps = np.diff(st) / 1e9
    print(f'dt median {dt:.6f}s, gaps>1.5dt: {(gaps > 1.5 * dt).sum()}')
    d = noisy - clean
    res = {}
    for name, sl, b in (('gyroscope', slice(0, 3), bg), ('accelerometer', slice(3, 6), ba)):
        n = d[:, sl] - b
        sig_d = n.std(0)
        nd = sig_d * np.sqrt(dt)
        ok = gaps < 1.5 * dt  # bias increments only across regular steps
        db = np.diff(b, axis=0)[ok]
        rw = db.std(0) / np.sqrt(dt)
        # Allan cross-check on noisy-clean (contains noise + bias walk)
        taus = np.logspace(np.log10(dt), np.log10(len(st) * dt / 10), 40)
        ad = np.array([allan(d[:, sl][:, j], dt, taus) for j in range(3)])
        # white noise: adev*sqrt(tau) on the short-tau (-1/2 slope) end; bias walk: adev*sqrt(3/tau) on the
        # long-tau end (upper bound, the +1/2 slope is only partly reached in 500 s)
        N_allan = np.array([np.median((ad[j] * np.sqrt(taus))[:8]) for j in range(3)])
        K_allan = np.array([np.nanmedian((ad[j] * np.sqrt(3 / taus))[-8:]) for j in range(3)])
        res[name] = {
            'white_noise_discrete_std': sig_d.tolist(),
            'noise_density': nd.tolist(), 'noise_density_mean': float(nd.mean()),
            'random_walk': rw.tolist(), 'random_walk_mean': float(rw.mean()),
            'noise_mean': n.mean(0).tolist(),
            'bias_initial': b[0].tolist(), 'bias_final': b[-1].tolist(), 'bias_std': b.std(0).tolist(),
            'allan_N_from_short_tau': N_allan.tolist(), 'allan_K_from_long_tau': K_allan.tolist(),
            'allan_taus': taus.tolist(), 'allan_dev': ad.tolist(),
        }
        print(f'{name:14s} noise_density {nd} (mean {nd.mean():.4e})  random_walk {rw} (mean {rw.mean():.4e})')
        print(f'{"":14s} allan N {N_allan}  allan K(long tau, upper bound) {K_allan}')
        print(f'{"":14s} bias first {b[0]} last {b[-1]}')
    # is the noise really white? lag-1 autocorrelation
    for j, nm in enumerate(['gx', 'gy', 'gz', 'ax', 'ay', 'az']):
        bb = bg if j < 3 else ba
        n = d[:, j] - bb[:, j % 3]
        n = n - n.mean()
        print(f'{nm}: lag-1 autocorr {np.dot(n[1:], n[:-1]) / np.dot(n, n):+.4f}')
    res['dt'] = dt
    res['n_samples'] = len(st)
    if a.out:
        import yaml
        Path(a.out).write_text(yaml.safe_dump(res, sort_keys=False, default_flow_style=None, width=200))


# ----------------------------------------------------------------------------------------------- seg colors
def cmd_segcolors(a):
    r, ts = open_bag(a.bag)
    conns = [c for c in r.connections if c.topic == '/tesse/seg_cam/rgb/image_raw']
    hist = {}
    nimg = 0
    for i, (c, t, raw) in enumerate(r.messages(connections=conns)):
        if i % a.every:
            continue
        m = ts.deserialize_ros1(raw, c.msgtype)
        img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.width, 3)
        cols, cnt = np.unique(img.reshape(-1, 3), axis=0, return_counts=True)
        for col, n in zip(map(tuple, cols), cnt):
            hist[col] = hist.get(col, 0) + int(n)
        nimg += 1
    r.close()
    tot = sum(hist.values())
    print(f'{nimg} images, {len(hist)} distinct colors')
    for col, n in sorted(hist.items(), key=lambda kv: -kv[1])[: a.top]:
        print(f'{col}: {100 * n / tot:.4f}%')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('inspect'); p.add_argument('--bag', required=True); p.add_argument('--out')
    p.add_argument('--fast', action='store_true', help='skip rgb/depth/lidar topics')
    p = sub.add_parser('gt'); p.add_argument('--bag', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('imunoise'); p.add_argument('--bag', required=True); p.add_argument('--out')
    p = sub.add_parser('segcolors'); p.add_argument('--bag', required=True)
    p.add_argument('--every', type=int, default=50); p.add_argument('--top', type=int, default=40)
    a = ap.parse_args()
    {'inspect': cmd_inspect, 'gt': cmd_gt, 'imunoise': cmd_imunoise, 'segcolors': cmd_segcolors}[a.cmd](a)


if __name__ == '__main__':
    main()
