#!/usr/bin/env python3
"""Convert a ROS1 bag (compressed or not) to a ROS 2 bag (mcap by default), keeping only selected topics.

Uses the pure-python `rosbags` library (no ROS1 install needed). Messages are converted byte-wise
ROS1 -> CDR with the ROS 2 Humble typestore (std_msgs/Header.seq is dropped). The bag receive time
of every message is kept as the ROS 2 bag timestamp; header stamps are untouched.

Optional IMU merge (for RealSense T265 / D4xx which publish gyro and accel on separate topics with
different rates): `--merge-imu GYRO_TOPIC ACCEL_TOPIC OUT_TOPIC` writes a combined sensor_msgs/Imu
on OUT_TOPIC at every *gyro* sample; the accelerometer is linearly interpolated (per axis) at the gyro
header stamp from the two bracketing accel samples (same scheme as realsense-ros
`unite_imu_method: linear_interpolation`). Gyro samples outside the accel time span are dropped.
Orientation is set to "unknown" (orientation_covariance[0] = -1). The two source topics are only
written as well if they are also listed in --topics.

Optional image encoding rewrite: `--set-encoding TOPIC:ENC` (repeatable) rewrites the `encoding` field of
sensor_msgs/Image on TOPIC (pixel data untouched). OpenLORIS T265 fisheye images are recorded as '8UC1',
which cv_bridge (OpenVINS) refuses to convert to mono8 -> use `--set-encoding /t265/fisheye1/image_raw:mono8`.

Examples (inside the ros2_humble container):
  python3 -I bag1_to_ros2.py --src in.bag --dst out_dir \
      --topics /tesse/left_cam/mono/image_raw /tesse/imu/clean/imu /tf_static
  python3 -I bag1_to_ros2.py --src cafe1-1.bag --dst cafe1-1 \
      --topics /t265/fisheye1/image_raw /t265/fisheye2/image_raw /tf_static \
      --merge-imu /t265/gyro/sample /t265/accel/sample /t265/imu
"""
import argparse
import dataclasses
import sys
import time
from pathlib import Path

import numpy as np
from rosbags.convert.converter import LATCH
from rosbags.rosbag1 import Reader as Reader1
from rosbags.rosbag2 import StoragePlugin, Writer
from rosbags.typesys import Stores, get_typestore, get_types_from_msg

LATCHED_TOPICS = {'/tf_static'}


def ros1_types_store(reader):
    """ROS1 typestore with all types defined in the bag (needed to deserialize non-std msgs)."""
    ts1 = get_typestore(Stores.ROS1_NOETIC)
    add = {}
    for c in reader.connections:
        add.update(get_types_from_msg(c.msgdef.data, c.msgtype))
    ts1.register(add)
    return ts1


def stamp_ns(header):
    return int(header.stamp.sec) * 1_000_000_000 + int(header.stamp.nanosec)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True, type=Path, help='input ROS1 .bag')
    ap.add_argument('--dst', required=True, type=Path, help='output ROS2 bag directory (must not exist)')
    ap.add_argument('--topics', nargs='+', default=[], help='topics to copy verbatim')
    ap.add_argument('--storage', choices=['mcap', 'sqlite3'], default='mcap')
    ap.add_argument('--merge-imu', nargs=3, metavar=('GYRO', 'ACCEL', 'OUT'), default=None,
                    help='write combined Imu on OUT at gyro rate, accel linearly interpolated')
    ap.add_argument('--merge-imu-frame', default=None, help='frame_id for merged IMU (default: gyro frame_id)')
    ap.add_argument('--set-encoding', action='append', default=[], metavar='TOPIC:ENC',
                    help='rewrite sensor_msgs/Image encoding on TOPIC (e.g. 8UC1 -> mono8)')
    args = ap.parse_args()
    set_enc = dict(x.rsplit(':', 1) for x in args.set_encoding)

    if args.dst.exists():
        sys.exit(f'destination {args.dst} exists, refusing to overwrite')
    ts2 = get_typestore(Stores.ROS2_HUMBLE)
    storage = StoragePlugin.MCAP if args.storage == 'mcap' else StoragePlugin.SQLITE3

    t0 = time.time()
    with Reader1(args.src) as reader:
        avail = {c.topic for c in reader.connections}
        missing = [t for t in args.topics if t not in avail]
        if missing:
            sys.exit(f'topics not in bag: {missing}')
        ts1 = ros1_types_store(reader)

        # ---- optional pass 1: collect accel samples for interpolation
        accel_t = accel_v = None
        if args.merge_imu:
            g_topic, a_topic, out_topic = args.merge_imu
            for t in (g_topic, a_topic):
                if t not in avail:
                    sys.exit(f'merge topic not in bag: {t}')
            conns = [c for c in reader.connections if c.topic == a_topic]
            ts_l, v_l = [], []
            for c, _, raw in reader.messages(connections=conns):
                m = ts1.deserialize_ros1(raw, c.msgtype)
                ts_l.append(stamp_ns(m.header))
                a = m.linear_acceleration
                v_l.append((a.x, a.y, a.z))
            order = np.argsort(ts_l, kind='stable')
            accel_t = np.asarray(ts_l, dtype=np.int64)[order]
            accel_v = np.asarray(v_l, dtype=np.float64)[order]
            # drop duplicate stamps (keep first)
            keep = np.concatenate([[True], np.diff(accel_t) > 0])
            accel_t, accel_v = accel_t[keep], accel_v[keep]
            print(f'[merge-imu] {len(accel_t)} accel samples from {a_topic}', flush=True)

        # ---- pass 2: copy / merge
        with Writer(args.dst, version=8, storage_plugin=storage) as writer:
            wconn = {}
            for c in reader.connections:
                if c.topic in args.topics and c.topic not in wconn:
                    qos = LATCH if (c.topic in LATCHED_TOPICS or getattr(c.ext, 'latching', 0)) else []
                    wconn[c.topic] = writer.add_connection(c.topic, c.msgtype, typestore=ts2,
                                                           offered_qos_profiles=qos)
            merge_conn = None
            if args.merge_imu:
                merge_conn = writer.add_connection(out_topic, 'sensor_msgs/msg/Imu', typestore=ts2)
                Imu = ts2.types['sensor_msgs/msg/Imu']
                Header = ts2.types['std_msgs/msg/Header']
                Time = ts2.types['builtin_interfaces/msg/Time']
                Vector3 = ts2.types['geometry_msgs/msg/Vector3']
                Quaternion = ts2.types['geometry_msgs/msg/Quaternion']
            read_topics = set(args.topics) | ({args.merge_imu[0]} if args.merge_imu else set())
            conns = [c for c in reader.connections if c.topic in read_topics]
            counts = {}
            n_drop = 0
            for c, t, raw in reader.messages(connections=conns):
                if c.topic in wconn:
                    cdr = ts2.ros1_to_cdr(raw, c.msgtype)
                    if c.topic in set_enc:
                        m = ts2.deserialize_cdr(cdr, c.msgtype)
                        if m.encoding != set_enc[c.topic]:
                            m = dataclasses.replace(m, encoding=set_enc[c.topic])
                            cdr = ts2.serialize_cdr(m, c.msgtype)
                    writer.write(wconn[c.topic], t, cdr)
                    counts[c.topic] = counts.get(c.topic, 0) + 1
                if args.merge_imu and c.topic == args.merge_imu[0]:
                    g = ts1.deserialize_ros1(raw, c.msgtype)
                    st = stamp_ns(g.header)
                    if st < accel_t[0] or st > accel_t[-1]:
                        n_drop += 1
                        continue
                    acc = [float(np.interp(st, accel_t, accel_v[:, k])) for k in range(3)]
                    msg = Imu(
                        header=Header(stamp=Time(sec=st // 1_000_000_000, nanosec=st % 1_000_000_000),
                                      frame_id=args.merge_imu_frame or g.header.frame_id),
                        orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                        orientation_covariance=np.array([-1.0] + [0.0] * 8),
                        angular_velocity=Vector3(x=g.angular_velocity.x, y=g.angular_velocity.y,
                                                 z=g.angular_velocity.z),
                        angular_velocity_covariance=np.asarray(g.angular_velocity_covariance, dtype=np.float64),
                        linear_acceleration=Vector3(x=acc[0], y=acc[1], z=acc[2]),
                        linear_acceleration_covariance=np.zeros(9),
                    )
                    writer.write(merge_conn, t, ts2.serialize_cdr(msg, 'sensor_msgs/msg/Imu'))
                    counts[out_topic] = counts.get(out_topic, 0) + 1
    for k in sorted(counts):
        print(f'{k:50s} {counts[k]:8d}')
    if args.merge_imu:
        print(f'[merge-imu] dropped {n_drop} gyro samples outside accel span')
    print(f'done in {time.time() - t0:.1f}s -> {args.dst}')


if __name__ == '__main__':
    main()
