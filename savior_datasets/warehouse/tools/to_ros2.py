#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Convert a SAVIOR-Warehouse raw sequence to a ROS 2 bag (mcap, zstd message compression) + TUM GT.

Run inside the SAVIOR Docker image (pure-python `rosbags`, no ROS needed):
  src/savior/docker/exec.sh python3 -I src/savior/savior_datasets/warehouse/tools/to_ros2.py \\
      --raw data/warehouse/raw/<seq> [--out data/warehouse/ros2/<seq>] [--gt data/warehouse/gt/<seq>.txt]

Topics (header.stamp = exact simulator stamps; bag time = header stamp):
  /cam0/image_raw, /cam1/image_raw          sensor_msgs/Image mono8 (BT.601 luma of the rendered RGB)
  /cam0/camera_info, /cam1/camera_info      sensor_msgs/CameraInfo (rectified pinhole, D = 0, P[3] = -fx*b on cam1)
  /imu0, /imu0_clean                        sensor_msgs/Imu 200 Hz (noisy = clean + bias + white noise)
  /cam0/segmentation                        sensor_msgs/Image rgb8, every warehouse-class instance in its class colour
  /cam0/segmentation_moving                 sensor_msgs/Image rgb8, only instances MOVING in that frame (> 0.05 m/s)
  /cam1/segmentation, /cam1/segmentation_moving   the same for the RIGHT camera (seg1/, with --seg-right; P6: GT
                                            right masks for the oracle via savior_node seg_right_topic)
  /cam0/instance_id                         sensor_msgs/Image mono16 instance ids (with --instances)
  /cam0/image_rgb                           sensor_msgs/Image rgb8 (with --rgb)
  /gt/pose                                  geometry_msgs/PoseStamped 200 Hz, T_world_imu (frame 'world')
  /tf_static                                imu0 -> cam0 / cam1
Colours: savior_bringup/config/oracle/warehouse_colormap(.yaml|_moving.yaml) (wh/classes.py).
"""
import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import yaml
from rosbags.rosbag2 import StoragePlugin, Writer
from rosbags.rosbag2.enums import CompressionFormat, CompressionMode
from rosbags.typesys import Stores, get_typestore

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wh.classes import COLOR, NAMES  # noqa: E402
from wh.se3 import rot_to_quat  # noqa: E402

cv2.setNumThreads(2)


def stamp(ts, ns):
    return ts.types['builtin_interfaces/msg/Time'](sec=int(ns // 1_000_000_000), nanosec=int(ns % 1_000_000_000))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--raw', required=True, type=Path)
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--gt', type=Path, default=None)
    ap.add_argument('--instances', action='store_true')
    ap.add_argument('--rgb', action='store_true')
    ap.add_argument('--seg-right', action='store_true', help='also /cam1/segmentation(_moving) from seg1/')
    ap.add_argument('--no-compress', action='store_true')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    raw = args.raw.resolve()
    seq = raw.name
    root = raw.parent.parent
    out = (args.out or root / 'ros2' / seq).resolve()
    gt_out = (args.gt or root / 'gt' / f'{seq}.txt').resolve()
    if out.exists():
        if not args.force:
            sys.exit(f'{out} exists (use --force)')
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    gt_out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ts = get_typestore(Stores.ROS2_HUMBLE)
    T = ts.types
    Header, Image, CameraInfo, Imu = T['std_msgs/msg/Header'], T['sensor_msgs/msg/Image'], T['sensor_msgs/msg/CameraInfo'], T['sensor_msgs/msg/Imu']
    Vec3, Quat, Pose, PoseStamped, Point = T['geometry_msgs/msg/Vector3'], T['geometry_msgs/msg/Quaternion'], \
        T['geometry_msgs/msg/Pose'], T['geometry_msgs/msg/PoseStamped'], T['geometry_msgs/msg/Point']
    TF, TFS, Transform = T['tf2_msgs/msg/TFMessage'], T['geometry_msgs/msg/TransformStamped'], T['geometry_msgs/msg/Transform']
    RoI = T['sensor_msgs/msg/RegionOfInterest']

    rig = yaml.safe_load(open(raw / 'calib' / 'rig.yaml'))
    cam = rig['camera']
    W, H = int(cam['width']), int(cam['height'])
    fx, fy, cx, cy, b = (float(cam[k]) for k in ('fx', 'fy', 'cx', 'cy', 'baseline'))
    inst = json.load(open(raw / 'instances.json'))
    max_id = max([i['id'] for i in inst['instances']] + [1])
    lut_cls = np.zeros((max_id + 1, 3), np.uint8)
    for i in inst['instances']:
        lut_cls[i['id']] = COLOR[i['cls']]
    frames = [ln.strip().split(',') for ln in open(raw / 'frames.csv') if not ln.startswith('#')]
    stamps = [int(f[1]) for f in frames]
    moving = {}
    for ln in open(raw / 'moving.csv'):
        if ln.startswith('#'):
            continue
        k, s, ids = ln.rstrip('\n').split(',', 2)
        moving[int(s)] = [int(v) for v in ids.split()] if ids.strip() else []
    imu_ns = {n: np.loadtxt(raw / n, delimiter=',', comments='#', usecols=0, dtype=np.int64) for n in ('imu_noisy.csv', 'imu_clean.csv')}
    imu_v = {n: np.loadtxt(raw / n, delimiter=',', comments='#')[:, 1:] for n in imu_ns}
    gt = np.loadtxt(raw / 'gt_imu_tum.txt', comments='#', usecols=(1, 2, 3, 4, 5, 6, 7))
    im = rig['imu']
    dt = 1.0 / float(im['rate_hz'])
    cg = (float(im['gyroscope_noise_density']) ** 2 / dt)
    ca = (float(im['accelerometer_noise_density']) ** 2 / dt)

    writer = Writer(out, version=8, storage_plugin=StoragePlugin.MCAP)
    if not args.no_compress:
        writer.set_compression(CompressionMode.MESSAGE, CompressionFormat.ZSTD)
    writer.open()
    from rosbags.convert.converter import LATCH
    C = {}

    def conn(topic, typ, latch=False):
        if topic not in C:
            C[topic] = writer.add_connection(topic, typ, typestore=ts, offered_qos_profiles=LATCH if latch else ())
        return C[topic]

    def write(topic, typ, ns, msg, latch=False):
        writer.write(conn(topic, typ, latch), int(ns), ts.serialize_cdr(msg, typ))

    # --- static tf + camera info
    from wh.rig import cam_extrinsics
    T_IC = cam_extrinsics(rig)
    tfs = []
    for i, Tm in enumerate(T_IC):
        q = rot_to_quat(Tm[:3, :3])
        tfs.append(TFS(header=Header(stamp=stamp(ts, stamps[0]), frame_id='imu0'), child_frame_id=f'cam{i}',
                       transform=Transform(translation=Vec3(x=Tm[0, 3], y=Tm[1, 3], z=Tm[2, 3]),
                                           rotation=Quat(x=q[1], y=q[2], z=q[3], w=q[0]))))
    write('/tf_static', 'tf2_msgs/msg/TFMessage', stamps[0], TF(transforms=tfs), latch=True)

    def cinfo(i, ns):
        P = [fx, 0.0, cx, -fx * b if i == 1 else 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        return CameraInfo(header=Header(stamp=stamp(ts, ns), frame_id=f'cam{i}'), height=H, width=W,
                          distortion_model='plumb_bob', d=np.zeros(5), k=np.array([fx, 0, cx, 0, fy, cy, 0, 0, 1.0]),
                          r=np.eye(3).ravel(), p=np.array(P), binning_x=0, binning_y=0,
                          roi=RoI(x_offset=0, y_offset=0, height=0, width=0, do_rectify=False))

    def img(ns, frame, enc, arr):
        step = arr.shape[1] * (arr.shape[2] if arr.ndim == 3 else 1) * arr.itemsize
        return Image(header=Header(stamp=stamp(ts, ns), frame_id=frame), height=arr.shape[0], width=arr.shape[1],
                     encoding=enc, is_bigendian=0, step=step, data=np.ascontiguousarray(arr).view(np.uint8).ravel())

    def load(ns):
        c0 = cv2.imread(str(raw / 'cam0' / f'{ns}.png'), cv2.IMREAD_COLOR)
        c1 = cv2.imread(str(raw / 'cam1' / f'{ns}.png'), cv2.IMREAD_COLOR)
        s0 = cv2.imread(str(raw / 'seg0' / f'{ns}.png'), cv2.IMREAD_UNCHANGED)
        s1 = cv2.imread(str(raw / 'seg1' / f'{ns}.png'), cv2.IMREAD_UNCHANGED) if args.seg_right else None
        return c0, c1, s0, s1

    # --- all streams in time order (IMU / GT samples up to each frame stamp, then the frame)
    ins, nv, cv_ = imu_ns['imu_noisy.csv'], imu_v['imu_noisy.csv'], imu_v['imu_clean.csv']
    assert np.array_equal(ins, imu_ns['imu_clean.csv'])
    j_imu = 0

    def write_imu_until(ns_max):
        nonlocal j_imu
        while j_imu < len(ins) and ins[j_imu] <= ns_max:
            ns = ins[j_imu]
            for topic, v in (('/imu0', nv[j_imu]), ('/imu0_clean', cv_[j_imu])):
                write(topic, 'sensor_msgs/msg/Imu', ns, Imu(
                    header=Header(stamp=stamp(ts, ns), frame_id='imu0'), orientation=Quat(x=0.0, y=0.0, z=0.0, w=1.0),
                    orientation_covariance=np.array([-1.0] + [0.0] * 8),
                    angular_velocity=Vec3(x=v[0], y=v[1], z=v[2]), angular_velocity_covariance=np.eye(3).ravel() * cg,
                    linear_acceleration=Vec3(x=v[3], y=v[4], z=v[5]),
                    linear_acceleration_covariance=np.eye(3).ravel() * ca))
            g = gt[j_imu]
            write('/gt/pose', 'geometry_msgs/msg/PoseStamped', ns, PoseStamped(
                header=Header(stamp=stamp(ts, ns), frame_id='world'),
                pose=Pose(position=Point(x=g[0], y=g[1], z=g[2]), orientation=Quat(x=g[3], y=g[4], z=g[5], w=g[6]))))
            j_imu += 1

    with ThreadPoolExecutor(6) as pool:
        for c0_ in range(0, len(stamps), 48):
            chunk = stamps[c0_:c0_ + 48]
            for ns, (c0, c1, s0, s1) in zip(chunk, pool.map(load, chunk)):
                write_imu_until(ns)
                for i, c in enumerate((c0, c1)):
                    write(f'/cam{i}/image_raw', 'sensor_msgs/msg/Image', ns,
                          img(ns, f'cam{i}', 'mono8', cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)))
                    write(f'/cam{i}/camera_info', 'sensor_msgs/msg/CameraInfo', ns, cinfo(i, ns))
                s0 = np.minimum(s0, max_id)
                write('/cam0/segmentation', 'sensor_msgs/msg/Image', ns, img(ns, 'cam0', 'rgb8', lut_cls[s0]))
                lm = np.zeros_like(lut_cls)
                mv = [m for m in moving.get(ns, []) if m <= max_id]
                lm[mv] = lut_cls[mv]
                write('/cam0/segmentation_moving', 'sensor_msgs/msg/Image', ns, img(ns, 'cam0', 'rgb8', lm[s0]))
                if s1 is not None:
                    s1 = np.minimum(s1, max_id)
                    write('/cam1/segmentation', 'sensor_msgs/msg/Image', ns, img(ns, 'cam1', 'rgb8', lut_cls[s1]))
                    write('/cam1/segmentation_moving', 'sensor_msgs/msg/Image', ns, img(ns, 'cam1', 'rgb8', lm[s1]))
                if args.instances:
                    write('/cam0/instance_id', 'sensor_msgs/msg/Image', ns, img(ns, 'cam0', 'mono16', s0.astype(np.uint16)))
                if args.rgb:
                    write('/cam0/image_rgb', 'sensor_msgs/msg/Image', ns, img(ns, 'cam0', 'rgb8', c0[..., ::-1]))
    write_imu_until(ins[-1])
    writer.close()
    # --- TUM GT (IMU frame, 200 Hz) for savior-eval
    with open(raw / 'gt_imu_tum.txt') as src, open(gt_out, 'w') as dst:
        for ln in src:
            dst.write(ln if not ln.startswith('#') else
                      f'# timestamp tx ty tz qx qy qz qw  (T_world_imu, IMU = body FLU, 200 Hz; SAVIOR-Warehouse {seq})\n')
    size = sum(f.stat().st_size for f in out.iterdir())
    print(f'[to_ros2] {seq}: {len(stamps)} stereo frames, {len(imu_ns["imu_noisy.csv"])} IMU -> {out} '
          f'({size / 1e9:.2f} GB) + {gt_out} in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
