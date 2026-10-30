#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the SAVIOR perception pipeline offline on a ROS 2 bag (no ROS graph, deterministic).

Reads the stereo pair from the bag with `rosbags`, runs exactly what savior_node runs
(segmenter -> SaviorPipeline) frame by frame and writes
  --stats  JSON lines (same content as /savior/stats, plus per-instance mask centroid/radius)
  --overlay-dir  PNG debug figures: raw left + left mask | raw right + right mask
Parameters are resolved like the node: savior_perception/config/default.yaml, then the
--params yaml files (savior_node.ros__parameters), then --set key=value overrides.

  python3 perception_offline.py --bag data/openloris/ros2/cafe1-1 \
      --params src/savior/savior_bringup/config/openloris_t265/savior_perception.yaml \
      --calib src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml \
      --roles src/savior/savior_bringup/config/roles/coco_indoor.yaml \
      --set segmenter.model=models/yolo26n-seg.engine --stats /tmp/s.jsonl \
      --overlay-dir /tmp/ov --overlay-every 30
"""
import argparse
import json
import math
import os
import sys
import time

import cv2
import numpy as np
import yaml

from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.compose import render_overlay
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.types import MASK_CORE, MASK_EXTENSION
from savior_perception.params import all_defaults
from savior_perception.segmenters import make_segmenter

TOPICS = {'openloris_t265': ('/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw'),
          'uhumans2': ('/tesse/left_cam/mono/image_raw', '/tesse/right_cam/mono/image_raw')}
IMU_TOPICS = {'openloris_t265': '/t265/imu', 'uhumans2': '/tesse/imu/noisy/imu'}   # P4 motion evidence (gyro)


def read_gyro(bag, topic):
    """All gyro samples of `topic` -> GyroIntegrator (offline: the whole bag, so every frame is covered)."""
    from rosbags.highlevel import AnyReader
    from pathlib import Path
    from savior_perception.core.motion import GyroIntegrator
    g = GyroIntegrator(max_age_s=1e9)
    with AnyReader([Path(bag)]) as reader:
        conns = [c for c in reader.connections if c.topic == topic]
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            w = msg.angular_velocity
            g.add(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9, (w.x, w.y, w.z))
    return g


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        key = f'{prefix}{k}'
        if isinstance(v, dict):
            out.update(flatten(v, key + '.'))
        else:
            out[key] = v
    return out


def load_params(files, sets):
    p = all_defaults()
    for fn in files:
        with open(fn) as fh:
            y = yaml.safe_load(fh) or {}
        p.update(flatten(y.get('savior_node', {}).get('ros__parameters', {})))
    for s in sets:
        k, _, v = s.partition('=')
        p[k] = yaml.safe_load(v) if v != '' else ''
    return p


def read_stereo(bag, left_topic, right_topic, t0=None, t1=None):
    """Yield (stamp_ns, left uint8, right uint8) for exactly-synced pairs, in stamp order."""
    from rosbags.highlevel import AnyReader
    from pathlib import Path
    pending = {}
    with AnyReader([Path(bag)]) as reader:
        conns = [c for c in reader.connections if c.topic in (left_topic, right_topic)]
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            st = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            if t0 is not None and st < t0:
                continue
            if t1 is not None and st > t1:
                break
            img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width].copy()
            slot = pending.setdefault(st, [None, None])
            slot[0 if conn.topic == left_topic else 1] = img
            if slot[0] is not None and slot[1] is not None:
                del pending[st]
                yield st, slot[0], slot[1]


def overlay_pair(left, right, mask_l, mask_r, instances, title=''):
    a = render_overlay(left, mask_l, instances)
    rb = cv2.cvtColor(right, cv2.COLOR_GRAY2BGR) if right.ndim == 2 else right.copy()
    tint = rb.copy()
    tint[mask_r == MASK_CORE] = (0, 0, 255)
    tint[mask_r == MASK_EXTENSION] = (0, 255, 255)
    b = cv2.addWeighted(rb, 0.55, tint, 0.45, 0)
    for img, lab in ((a, 'left (raw) + left mask'), (b, 'right (raw) + right mask')):
        cv2.putText(img, lab, (8, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    out = np.hstack([a, b])
    if title:
        cv2.putText(out, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def inst_geometry(inst, cx, cy):
    ys, xs = np.nonzero(inst.mask[inst.bbox[1]:inst.bbox[3], inst.bbox[0]:inst.bbox[2]])
    if xs.size == 0:
        return None
    mx, my = xs.mean() + inst.bbox[0], ys.mean() + inst.bbox[1]
    return {'cx': round(float(mx), 1), 'cy': round(float(my), 1), 'area': int(xs.size),
            'r': round(float(math.hypot(mx - cx, my - cy)), 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bag', required=True)
    ap.add_argument('--dataset', default='openloris_t265', choices=sorted(TOPICS))
    ap.add_argument('--params', action='append', default=[], help='node params yaml (repeatable, in order)')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE')
    ap.add_argument('--calib', default='')
    ap.add_argument('--roles', default='')
    ap.add_argument('--start', type=float, default=None, help='start [s from first frame]')
    ap.add_argument('--duration', type=float, default=None)
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--imu-topic', default='', help='gyro topic for motion.enable (default per dataset)')
    ap.add_argument('--stats', default='', help='JSON-lines output')
    ap.add_argument('--overlay-dir', default='')
    ap.add_argument('--overlay-every', type=int, default=0, help='save every Nth frame with a dynamic mask')
    ap.add_argument('--overlay-stamps', default='', help='comma separated stamps [s] (nearest frame saved)')
    ap.add_argument('--overlay-status', default='', help='with --overlay-every: only count frames that contain an '
                    'instance with this status (e.g. carried, promoted, held)')
    a = ap.parse_args(argv)

    P = load_params(a.params, a.set)
    cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    roles = RoleTable.from_yaml(a.roles or P['roles_file'])
    calib = a.calib or P['calib_file']
    rect = stereo_from_kalibr(calib, P['cam_left'], P['cam_right'], focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale) if calib else None
    seg = make_segmenter(P['segmenter.backend'], model=P['segmenter.model'], conf=P['segmenter.conf'],
                         iou=P['segmenter.iou'], imgsz=P['segmenter.imgsz'], device=P['segmenter.device'],
                         half=P['segmenter.half'],
                         classes=roles.relevant_classes() if P['segmenter.filter_classes'] else None,
                         colormap_file=P['segmenter.colormap_file'], retina_masks=P['segmenter.retina_masks'])
    static_mask = None
    if cfg.motion.enable and cfg.motion.static_mask_file:
        static_mask = cv2.imread(cfg.motion.static_mask_file, cv2.IMREAD_UNCHANGED)
        if static_mask is not None and static_mask.ndim == 3:
            static_mask = static_mask[:, :, :3].max(axis=2)
    pipe = SaviorPipeline(cfg, roles, rect, static_mask=static_mask)
    gyro = None
    if cfg.motion.enable:
        gyro = read_gyro(a.bag, a.imu_topic or P.get('imu_topic') or IMU_TOPICS[a.dataset])
        print(f'[perception_offline] gyro: {len(gyro.t)} samples', file=sys.stderr)
    prev_t = None
    cx, cy = (rect.cams[0].K[0, 2], rect.cams[0].K[1, 2]) if rect else (0.0, 0.0)
    lt, rt = TOPICS[a.dataset]
    want = sorted(float(s) for s in a.overlay_stamps.split(',') if s.strip())
    if a.overlay_dir:
        os.makedirs(a.overlay_dir, exist_ok=True)
    fo = open(a.stats, 'w') if a.stats else None
    warmed = False
    n = n_dyn = 0
    t_first = None
    t0_ns = t1_ns = None
    for st, left, right in read_stereo(a.bag, lt, rt):
        if t_first is None:
            t_first = st
            if a.start is not None:
                t0_ns = t_first + int(a.start * 1e9)
            if a.duration is not None:
                t1_ns = (t0_ns or t_first) + int(a.duration * 1e9)
        if t0_ns is not None and st < t0_ns:
            continue
        if t1_ns is not None and st > t1_ns:
            break
        if not warmed:
            seg.warmup(left.shape)
            warmed = True
        ts = time.perf_counter()
        inst = seg.predict(left)
        tseg = (time.perf_counter() - ts) * 1e3
        R_imu = None
        if gyro is not None:
            off = cfg.motion.imu_time_offset_s
            if prev_t is not None:
                R_imu = gyro.rotation(prev_t + off, st * 1e-9 + off)
            prev_t = st * 1e-9
        ml, mr, stats = pipe.process(left, right, st * 1e-9, inst, R_imu=R_imu)
        stats['timings_ms']['segment'] = round(tseg, 3)
        stats['stamp_ns'] = st
        for s, i in zip(stats['instances'], pipe.last_result.instances):
            g = inst_geometry(i, cx, cy)
            if g:
                s.update(g)
        stats['right_core_px'] = int(np.count_nonzero(mr == MASK_CORE))
        stats['right_ext_px'] = int(np.count_nonzero(mr == MASK_EXTENSION))
        if fo:
            fo.write(json.dumps(stats, default=lambda o: None if isinstance(o, float) and math.isnan(o)
                                else (o.item() if hasattr(o, 'item') else str(o))) + '\n')
        n += 1
        dyn = stats['core_px'] > 0
        if a.overlay_status:
            dyn = dyn and any(i.status == a.overlay_status for i in pipe.last_result.instances)
        n_dyn += dyn
        save = False
        if a.overlay_dir:
            if a.overlay_every and dyn and (n_dyn % a.overlay_every == 1):
                save = True
            while want and want[0] <= st * 1e-9 + 1e-3:
                want.pop(0)
                save = True
        if save:
            t_rel = (st - t_first) * 1e-9
            title = f't={st * 1e-9:.3f} (+{t_rel:.2f}s) frame {n}'
            fig = overlay_pair(left, right, ml, mr, pipe.last_result.instances, title)
            cv2.imwrite(os.path.join(a.overlay_dir, f'frame_{st}.png'), fig)
        if a.max_frames and n >= a.max_frames:
            break
    if fo:
        fo.close()
    print(f'[perception_offline] {n} frames, {n_dyn} with a dynamic mask', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
