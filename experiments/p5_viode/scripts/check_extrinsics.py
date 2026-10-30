#!/usr/bin/env python3
"""check_extrinsics.py <ros2 bag> [t_start t_end]: camera-IMU rotation check on the rotation-only hover at the start:
KLT tracks between consecutive left frames vs the gyro rotation mapped into the camera with R_CI from the kalibr yaml
(pixel residual of the rotation-only prediction; also for a few alternative R_CI and time shifts)."""
import sys
from pathlib import Path
import cv2
import numpy as np
import yaml
from rosbags.highlevel import AnyReader
sys.path.insert(0, str(Path(__file__).resolve().parent))
from viode_common import decode_image  # noqa: E402
from savior_perception.core.motion import GyroIntegrator  # noqa: E402

bag = sys.argv[1]
t_a, t_b = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0.0, 6.0)
K = np.array([[376.0, 0, 376.0], [0, 376.0, 240.0], [0, 0, 1]])
cal = yaml.safe_load(open('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/viode/kalibr_imucam_chain.yaml').read().split('\n', 1)[1])
T = np.array(cal['cam0']['T_imu_cam'])
R_IC = T[:3, :3]
g = GyroIntegrator(max_age_s=1e9)
frames = []
with AnyReader([Path(bag)]) as r:
    conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw')]
    t0 = None
    for c, _, raw in r.messages(connections=conns):
        m = r.deserialize(raw, c.msgtype)
        st = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if c.topic == '/imu0':
            w = m.angular_velocity
            g.add(st, (w.x, w.y, w.z))
        else:
            t0 = st if t0 is None else t0
            if t_a <= st - t0 <= t_b:
                frames.append((st, cv2.cvtColor(decode_image(m), cv2.COLOR_RGB2GRAY)))
alts = {'calib': R_IC, 'flip_x': R_IC @ np.diag([-1, -1, 1]), 'transpose': R_IC.T}
res = {k: [] for k in alts}
res_shift = {d: [] for d in (-0.01, -0.005, 0.0, 0.005, 0.01)}
for (ta, a), (tb, b) in zip(frames[:-1], frames[1:]):
    p0 = cv2.goodFeaturesToTrack(a, 200, 0.01, 10)
    if p0 is None:
        continue
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(21, 21), maxLevel=4)
    ok = st[:, 0] == 1
    p0, p1 = p0[ok, 0], p1[ok, 0]
    if len(p0) < 20:
        continue
    R_I = g.rotation(ta, tb)        # R_{I_a I_b}
    if R_I is None:
        continue
    ang = np.degrees(np.linalg.norm(cv2.Rodrigues(R_I)[0]))
    if ang < 1.0:
        continue
    for k, Rc in alts.items():
        Rcam = Rc.T @ R_I @ Rc       # R_{C_a C_b}
        H = K @ Rcam.T @ np.linalg.inv(K)
        q = cv2.perspectiveTransform(p0[None].astype(np.float64), H)[0]
        res[k].append(np.median(np.linalg.norm(q - p1, axis=1)))
    for d in res_shift:
        R_I2 = g.rotation(ta + d, tb + d)
        Rcam = R_IC.T @ R_I2 @ R_IC
        q = cv2.perspectiveTransform(p0[None].astype(np.float64), K @ Rcam.T @ np.linalg.inv(K))[0]
        res_shift[d].append(np.median(np.linalg.norm(q - p1, axis=1)))
print(f'{bag}: {len(res["calib"])} frame pairs with >1 deg rotation')
for k, v in res.items():
    print(f'  R_CI {k:10s}: median pixel residual {np.median(v):.3f}')
for d, v in res_shift.items():
    print(f'  time shift {d:+.3f}s: median pixel residual {np.median(v):.3f}')
