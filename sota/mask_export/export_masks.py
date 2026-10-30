# SPDX-License-Identifier: GPL-3.0-or-later
"""export_masks.py : offline, deterministic export of the per-frame SAVIOR dynamic masks that the frozen ONLINE
pipeline (savior_node, as launched by savior_bringup/launch/savior.launch.py) publishes for an OpenVINS run, so that
other back-ends (VINS-Fusion, ...) can consume exactly the same masks.

The real `savior_perception.node.SaviorNode` is instantiated with the same parameter list as the launch
(frozen_params.py) and driven directly with the bag messages instead of DDS:
  * messages are read from the ROS 2 bag in bag (log-time) order, starting at `starting_time + start_offset` like
    `ros2 bag play --start-offset` (rosbag2 Player seeks to that time, messages with time >= it are played);
  * only the topics the OpenVINS run played (frozen `topics`), as subscribed by savior_node: left/right image,
    IMU (motion evidence), oracle semantic image;
  * the exact-time synchronizer (message_filters.TimeSynchronizer) is emulated by stamp (all inputs of one stamp
    present -> SaviorNode._on_images); IMU messages go to SaviorNode._on_imu. SaviorNode then holds each frame until
    the gyro covers its stamp (its own deterministic-replay logic); after the last message the remaining frames are
    released the way the online node does when the IMU stream has ended (imu_wait_ms time-out, covered = false);
  * `SaviorNode._publish_masks` is replaced by a capture; everything else (segmenter incl. TensorRT YOLO, pipeline,
    tracker, motion evidence, selective policy, right-mask warp) is the installed node code.
Perception inputs are images, IMU and the oracle segmentation only: savior_node has no subscription to any filter
output (no pose / odometry feedback), so the masks do not depend on the back-end. They DO depend on the start offset
(tracker / motion / selective state start at the first played frame), hence one export per start offset.

Output (per seq / method / offset):  <out>/<seq>/<method>/off_<offset>/{left,right}/<stamp_ns>.png  (mono8, 0/192/255)
  + index.csv (stamp_ns, md5 left, md5 right, core/ext px), stats.jsonl.gz (the /savior/stats JSON of every frame).
PNG files with identical content are stored once (<out>/<seq>/<method>/pool/<md5>.png) and hard-linked.

Run inside the savior image with the install of the method sourced (frozen_edge/install for savior_edge):
  python3 export_masks.py --seq hall_t1_L3 --method sens_fix1 --offsets 0.0 0.2 --out <dir>
  --check-log <launch.log[.gz]>   assert the rebuilt parameter list equals the one logged by an online run
  --zero                          write all-zero masks for every left stamp (empty-mask control), no perception
"""
import argparse
import ast
import gzip
import hashlib
import json
import math
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frozen_params  # noqa: E402

import numpy as np  # noqa: E402
import yaml  # noqa: E402


def png_bytes(mask):
    import cv2
    ok, buf = cv2.imencode('.png', mask, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    assert ok
    return buf.tobytes()


class Store:
    """Content-addressed PNG pool + hard links per offset directory."""

    def __init__(self, mdir):
        self.pool = os.path.join(mdir, 'pool')
        os.makedirs(self.pool, exist_ok=True)

    def put(self, mask, dst):
        data = png_bytes(mask)
        h = hashlib.md5(mask.tobytes()).hexdigest()   # md5 of the raw mono8 pixels (encoder-independent)
        p = os.path.join(self.pool, h + '.png')
        if not os.path.exists(p):
            tmp = p + '.tmp%d' % os.getpid()
            with open(tmp, 'wb') as f:
                f.write(data)
            os.replace(tmp, p)
        if os.path.lexists(dst):
            os.unlink(dst)
        os.link(p, dst)
        return h


def params_yaml(overrides):
    """dict overrides -> params file, as launch_ros does for a dict entry of `parameters` (node-agnostic /**)."""
    f = tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False)
    yaml.safe_dump({'/**': {'ros__parameters': overrides}}, f)
    f.close()
    return f.name


def logged_params(path):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt') as f:
        for line in f:
            if 'savior_node parameters:' in line:
                return ast.literal_eval(line.split('savior_node parameters:', 1)[1].strip())
    raise RuntimeError(f'no parameter line in {path}')


def bag_reader(bag, topics, start_ns):
    import rosbag2_py
    # message-level zstd bags (SAVIOR-Warehouse) need the compression reader (ros2 bag play uses it too)
    # uncompressed bags (VIODE) are rejected by the compression reader -> plain sequential reader
    try:
        r = rosbag2_py.SequentialCompressionReader()
        r.open(rosbag2_py.StorageOptions(uri=bag, storage_id=''), rosbag2_py.ConverterOptions('', ''))
    except ValueError:
        r = rosbag2_py.SequentialReader()
        r.open(rosbag2_py.StorageOptions(uri=bag, storage_id=''), rosbag2_py.ConverterOptions('', ''))
    meta = r.get_metadata()
    t0 = meta.starting_time.nanoseconds if hasattr(meta.starting_time, 'nanoseconds') else \
        int(meta.starting_time.timestamp() * 1e9)
    types = {t.name: t.type for t in r.get_all_topics_and_types()}
    r.set_filter(rosbag2_py.StorageFilter(topics=[t for t in topics if t in types]))
    if start_ns:
        r.seek(t0 + start_ns)
    return r, types, t0


def run_offset(args, P, offset, out_dir, store):
    import rclpy
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    from savior_perception.node import SaviorNode

    over = dict(P['overrides'])
    pf = params_yaml(over)
    cli = ['--ros-args']
    for f in P['param_files'] + [pf]:
        cli += ['--params-file', f]
    rclpy.init(args=None)
    node = SaviorNode(cli_args=cli)
    os.unlink(pf)
    Pn = node.P
    left_t, right_t, imu_t = Pn['left_topic'], Pn['right_topic'], Pn['imu_topic']
    seg_t = Pn['seg_topic'] if node.uses_aux else ''
    segr_t = Pn['seg_right_topic'] if node.uses_aux_right else ''
    need = [left_t, right_t] + ([seg_t] if seg_t else []) + ([segr_t] if segr_t else [])
    use_imu = node.gyro is not None
    # online, savior_node only sees the topics the bag player publishes (frozen `topics`)
    played = set(P['topics'])
    for t in need + ([imu_t] if use_imu else []):
        assert t in played, f'{t} is not played in the frozen run (topics {sorted(played)})'

    captured = []

    def capture(left_msg, right_msg, mask_l, mask_r):
        st = left_msg.header.stamp
        captured.append((st.sec * 1000000000 + st.nanosec, mask_l.copy(), mask_r.copy()))

    node._publish_masks = capture

    class _Pub:
        def __init__(self):
            self.msgs = []

        def publish(self, msg):
            self.msgs.append(msg.data)

    node.pub_stats = _Pub()
    # while feeding, a frame waits for the gyro without a wall-clock time-out (online: the IMU stream never pauses
    # during the bag; a time-out there only happens when it ends, emulated below)
    wait_ms = Pn['imu_wait_ms']
    Pn['imu_wait_ms'] = 1e12

    start_ns = int(round(offset * 1e9))
    reader, types, t0 = bag_reader(P['bag'], need + ([imu_t] if use_imu else []), start_ns)
    cls = {t: get_message(types[t]) for t in types}
    pend = {}
    n_in = 0
    tic = time.time()
    while reader.has_next():
        topic, data, t = reader.read_next()
        if t < t0 + start_ns:
            continue
        msg = deserialize_message(data, cls[topic])
        n_in += 1
        if topic == imu_t and use_imu:
            node._on_imu(msg)
            continue
        st = msg.header.stamp.sec * 1000000000 + msg.header.stamp.nanosec
        slot = pend.setdefault(st, {})
        slot[topic] = msg
        if all(k in slot for k in need):
            del pend[st]
            node._on_images(slot[left_t], slot[right_t], slot.get(seg_t) if seg_t else None,
                            slot.get(segr_t) if segr_t else None)
    if use_imu:  # end of the bag: IMU silent -> pending frames time out (covered = false), in order
        Pn['imu_wait_ms'] = wait_ms
        node._last_imu_wall = -math.inf
        node._pending = type(node._pending)((a, b, c, d, -math.inf) for (a, b, c, d, _) in node._pending)
        node._flush()
        assert not node._pending
    n_unsynced = len(pend)
    stats = node.pub_stats.msgs
    node.destroy_node()
    rclpy.shutdown()

    os.makedirs(os.path.join(out_dir, 'left'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'right'), exist_ok=True)
    rows = []
    for st, ml, mr in captured:
        hl = store.put(ml, os.path.join(out_dir, 'left', f'{st}.png'))
        hr = store.put(mr, os.path.join(out_dir, 'right', f'{st}.png'))
        rows.append((st, hl, hr, int(np.count_nonzero(ml == 255)), int(np.count_nonzero(ml == 192)),
                     int(np.count_nonzero(mr == 255)), int(np.count_nonzero(mr == 192))))
    with open(os.path.join(out_dir, 'index.csv'), 'w') as f:
        f.write('stamp_ns,md5_left,md5_right,core_left,band_left,core_right,band_right\n')
        for r in rows:
            f.write(','.join(map(str, r)) + '\n')
    with gzip.open(os.path.join(out_dir, 'stats.jsonl.gz'), 'wt') as f:
        for s in stats:
            f.write(s + '\n')
    h = hashlib.md5()
    for st, hl, hr, *_ in rows:
        h.update(f'{st}{hl}{hr}'.encode())
    info = dict(seq=args.seq, method=args.method, start_offset=offset, n_frames=len(rows), n_messages=n_in,
                n_unsynced=n_unsynced, first_stamp_ns=rows[0][0] if rows else None,
                last_stamp_ns=rows[-1][0] if rows else None, masks_md5=h.hexdigest(),
                n_fail=node._n_fail, imu_timeouts=getattr(node, '_imu_timeouts', 0),
                wall_s=round(time.time() - tic, 1), install=P['install'], param_files=P['param_files'],
                overrides=P['overrides'], topics=P['topics'], bag=P['bag'],
                savior_perception=__import__('savior_perception').__file__)
    with open(os.path.join(out_dir, 'export_info.yaml'), 'w') as f:
        yaml.safe_dump(info, f, sort_keys=False)
    print(f"{args.seq} {args.method} off {offset}: {len(rows)} frames, md5 {info['masks_md5']}, fail {info['n_fail']}, "
          f"imu_timeouts {info['imu_timeouts']}, {info['wall_s']} s", flush=True)
    return info


def run_zero(args, P, out_dir, store):
    """All-zero masks for every left image stamp of the bag (empty-mask control)."""
    left_t = P['overrides'].get('left_topic', '/cam0/image_raw')
    reader, types, t0 = bag_reader(P['bag'], [left_t], 0)
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    C = get_message(types[left_t])
    os.makedirs(os.path.join(out_dir, 'left'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'right'), exist_ok=True)
    n = 0
    z = None
    with open(os.path.join(out_dir, 'index.csv'), 'w') as f:
        f.write('stamp_ns,md5_left,md5_right,core_left,band_left,core_right,band_right\n')
        while reader.has_next():
            _, data, _ = reader.read_next()
            m = deserialize_message(data, C)
            if z is None:
                z = np.zeros((m.height, m.width), np.uint8)
            st = m.header.stamp.sec * 1000000000 + m.header.stamp.nanosec
            h = store.put(z, os.path.join(out_dir, 'left', f'{st}.png'))
            store.put(z, os.path.join(out_dir, 'right', f'{st}.png'))
            f.write(f'{st},{h},{h},0,0,0,0\n')
            n += 1
    print(f'{args.seq} zero masks: {n} frames', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seq', required=True)
    ap.add_argument('--method', required=True, help='frozen method key (sens_fix1, savior_edge, yolo_naive, '
                    'oracle_moving_ext, oracle_class_ext, ...) or "zero"')
    ap.add_argument('--offsets', nargs='+', type=float, default=[0.0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='', help='output method dir name (default: --method)')
    ap.add_argument('--check-log', default='', help='launch.log(.gz) of an online run: parameter lists must match')
    ap.add_argument('--refuse', default='', help='comma list of substrings: refuse sequences containing any')
    a = ap.parse_args()
    for s in filter(None, a.refuse.split(',')):
        if s in a.seq:
            sys.exit(f'refusing {a.seq} ({s})')
    mdir = os.path.join(a.out, a.seq, a.name or a.method)
    store = Store(mdir)
    if a.method == 'zero':
        P = frozen_params.method_params(a.seq, 'savior_none')
        run_zero(a, P, os.path.join(mdir, 'off_all'), store)
        return
    P = frozen_params.method_params(a.seq, a.method)
    if P['install'] not in __import__('savior_perception').__file__:
        sys.exit(f"wrong install sourced: method needs {P['install']}, got {__import__('savior_perception').__file__}")
    if a.check_log:
        L = logged_params(a.check_log)
        mine = P['param_files'] + [P['overrides']]
        if L != mine:
            print('logged :', L, '\nrebuilt:', mine)
            # model / colormap paths may legitimately point at a copy (edge study scratch); report key differences
            dl, dm = L[-1], mine[-1]
            diff = {k: (dl.get(k), dm.get(k)) for k in set(dl) | set(dm) if dl.get(k) != dm.get(k)}
            print('PARAM-DIFF', json.dumps(diff, default=str), 'files', L[:-1] == mine[:-1])
        else:
            print('PARAM-CHECK identical to', a.check_log)
    for off in a.offsets:
        run_offset(a, P, off, os.path.join(mdir, f'off_{off:.1f}'), store)


if __name__ == '__main__':
    main()
