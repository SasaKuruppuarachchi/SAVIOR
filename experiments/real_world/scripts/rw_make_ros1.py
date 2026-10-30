#!/usr/bin/env python3
"""rw_make_ros1.py --zip data/monado/raw/<name>.zip --dst <scratch>/<seq>.bag

ROS 1 bag (UNCOMPRESSED chunks; FREEZE_AMENDMENT A1: the rosbags LZ4 chunks are unreadable by noetic roslz4 -
'ROSLZ4_DATA_ERROR: malformed data to decompress' on the first chunk, so no message was ever played) for the SOTA baselines (VINS-Fusion, DynaVINS in savior-sota:noetic): /cam0/image_raw, /cam1/image_raw
(mono8, ALL 54 Hz stereo pairs: VINS-Fusion with the frozen multiple_thread 1 processes every 2nd image, i.e. the same 27 Hz
as OpenVINS) and /imu0 (1 kHz, imu0/data.csv) - the same decoding as monado_prepare.py convert. Prints message counts."""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
import monado_prepare as mp  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', required=True)
    ap.add_argument('--dst', required=True)
    a = ap.parse_args()
    import cv2
    from rosbags.rosbag1 import Writer
    from rosbags.typesys import Stores, get_typestore
    ts = get_typestore(Stores.ROS1_NOETIC)
    Image, Imu, Header = ts.types['sensor_msgs/msg/Image'], ts.types['sensor_msgs/msg/Imu'], ts.types['std_msgs/msg/Header']
    Time, Q, V3 = ts.types['builtin_interfaces/msg/Time'], ts.types['geometry_msgs/msg/Quaternion'], ts.types['geometry_msgs/msg/Vector3']
    z, root = mp.zopen(a.zip)
    cams = {c: mp.cam_list(z, root, c) for c in ('cam0', 'cam1')}
    ti, w, acc = mp.imu_array(z, root)
    ev = [(t, 1, i, 'imu') for i, t in enumerate(ti)]
    for c, L in cams.items():
        ev += [(t, 0, i, c) for i, (t, _) in enumerate(L)]
    ev.sort(key=lambda e: (e[0], e[1], e[3]))
    dst = Path(a.dst)
    if dst.exists():
        sys.exit(f'{dst} exists')
    wr = Writer(dst)
    # no compression (A1): as the VIODE / warehouse ROS 1 bags (rosbags-convert, uncompressed)
    cov0, covm1 = np.zeros(9), np.zeros(9)
    covm1[0] = -1.0
    counts, t0, seq = {}, time.time(), {}
    with wr:
        conn = {k: wr.add_connection(tp, mt, typestore=ts) for k, tp, mt in
                (('cam0', '/cam0/image_raw', Image.__msgtype__), ('cam1', '/cam1/image_raw', Image.__msgtype__), ('imu', '/imu0', Imu.__msgtype__))}
        for t, _, i, kind in ev:
            st = Time(sec=int(t // 1_000_000_000), nanosec=int(t % 1_000_000_000))
            sq = seq.get(kind, 0)
            seq[kind] = sq + 1
            if kind == 'imu':
                msg = Imu(header=Header(seq=sq, stamp=st, frame_id='imu0'), orientation=Q(x=0.0, y=0.0, z=0.0, w=1.0), orientation_covariance=covm1,
                          angular_velocity=V3(x=float(w[i, 0]), y=float(w[i, 1]), z=float(w[i, 2])), angular_velocity_covariance=cov0,
                          linear_acceleration=V3(x=float(acc[i, 0]), y=float(acc[i, 1]), z=float(acc[i, 2])), linear_acceleration_covariance=cov0)
            else:
                img = cv2.imdecode(np.frombuffer(z.read(f'{root}{kind}/data/{cams[kind][i][1]}'), np.uint8), cv2.IMREAD_UNCHANGED)
                assert img is not None and img.ndim == 2 and img.dtype == np.uint8
                msg = Image(header=Header(seq=sq, stamp=st, frame_id=kind), height=img.shape[0], width=img.shape[1], encoding='mono8',
                            is_bigendian=0, step=img.shape[1], data=np.ascontiguousarray(img).reshape(-1))
            wr.write(conn[kind], int(t), ts.serialize_ros1(msg, msg.__msgtype__))
            counts[kind] = counts.get(kind, 0) + 1
    for k in sorted(counts):
        print(f'{k:6s} {counts[k]:8d}')
    assert counts['cam0'] == len(cams['cam0']) and counts['cam1'] == len(cams['cam1']) and counts['imu'] == len(ti)
    print(f'counts OK; {time.time() - t0:.0f}s -> {dst}')


if __name__ == '__main__':
    main()
