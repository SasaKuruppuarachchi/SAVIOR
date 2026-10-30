#!/usr/bin/env python3
"""rw_expected_frames.py [--out prep/expected_frames.yaml] : FREEZE_AMENDMENT 2 validity rule - the number of stereo pairs a run
must process = bag stereo pairs whose bag time is >= bag start + start_offset (ros2 bag play --start-offset / rosbag play -s:
offset relative to the earliest message of the bag).
  ros2 (OpenVINS family): data/monado/ros2/<seq> (27 Hz pairs, the frames OpenVINS tracks), counted from the mcap;
  ros1 (VINS-Fusion / DynaVINS): the 54 Hz pairs of the raw zip, exactly what rw_make_ros1.py writes (bag time = stamp).
Run in the savior image (rosbags)."""
import argparse
import sys

import numpy as np
import yaml

WS = '/home/sasa/workspace/savior_ws'
sys.path.insert(0, f'{WS}/src/savior/savior_bringup/tools')
ZIP = {'MIO13': 'MIO13_moving_person', 'MIO15': 'MIO15_moving_person_props', 'MIO16': 'MIO16_moving_screens_person_props',
       'MIO07': 'MIO07_mapping_easy'}
OFFS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]


def count(t_cam, t0):
    return {f'{o:.1f}': int(np.sum(t_cam >= t0 + int(round(o * 1e9)))) for o in OFFS}


def ros2(seq):
    from rosbags.highlevel import AnyReader
    from pathlib import Path
    t_all, t_c0, t_c1 = [], [], []
    with AnyReader([Path(f'{WS}/data/monado/ros2/{seq}')]) as r:
        for c, t, _ in r.messages():
            t_all.append(t)
            if c.topic == '/cam0/image_raw':
                t_c0.append(t)
            elif c.topic == '/cam1/image_raw':
                t_c1.append(t)
    assert t_c0 == t_c1, 'cam0/cam1 bag times differ'
    return np.array(t_c0, np.int64), int(min(t_all))


def ros1(seq):
    import monado_prepare as mp
    z, root = mp.zopen(f'{WS}/data/monado/raw/{ZIP[seq]}.zip')
    c0 = np.array([t for t, _ in mp.cam_list(z, root, 'cam0')], np.int64)
    c1 = np.array([t for t, _ in mp.cam_list(z, root, 'cam1')], np.int64)
    assert np.array_equal(c0, c1), 'cam0/cam1 stamps differ'
    ti = mp.imu_array(z, root)[0]
    return c0, int(min(c0.min(), ti.min()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=f'{WS}/results/real_world/prep/expected_frames.yaml')
    a = ap.parse_args()
    out = {}
    for s in ZIP:
        c2, s2 = ros2(s)
        c1, s1 = ros1(s)
        out[s] = {'ros2_pairs': count(c2, s2), 'ros1_pairs': count(c1, s1)}
        print(s, out[s], flush=True)
    yaml.safe_dump(out, open(a.out, 'w'), sort_keys=False)


if __name__ == '__main__':
    main()
