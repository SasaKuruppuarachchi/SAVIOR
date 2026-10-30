#!/usr/bin/env python3
"""offline_eval.py --seq <env_level> --out <yaml> [--every N]

Offline (deterministic, no ROS graph) evaluation of the SAVIOR perception variants on a VIODE bag against the GT
segmentation (vehicle-id images from gt_masks.py):
  * mask quality (pixel TP/FP/FN of the final core 255 / core+band masks vs GT dynamic and GT all-vehicle masks),
    left and right (right: stereo warp vs GT /cam1/segmentation);
  * per-instance motion-evidence classification: each YOLO vehicle instance gets a GT label (dynamic / static /
    none) from the GT ids under its mask; decision = masked (core) or not; per GT vehicle the share of its frames
    that are masked.
Variants (same YOLO detections for all): yolo_naive, yolo_full_p2, yolo_p4_dyn, yolo_p4_pot, oracle_dynamic_warp
(GT left mask -> stereo warp right) and oracle_all_vehicles_warp.
Run in the savior image with the workspace install sourced (savior_perception importable).
"""
import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from rosbags.highlevel import AnyReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from viode_common import decode_image, vehicle_ids  # noqa: E402

from savior_perception.core.calibration import stereo_from_kalibr  # noqa: E402
from savior_perception.core.config import PipelineConfig  # noqa: E402
from savior_perception.core.motion import GyroIntegrator  # noqa: E402
from savior_perception.core.pipeline import SaviorPipeline  # noqa: E402
from savior_perception.core.roles import RoleTable  # noqa: E402
from savior_perception.core.types import Instance  # noqa: E402
from savior_perception.params import all_defaults  # noqa: E402
from savior_perception.segmenters import make_segmenter  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
B = WS + '/src/savior/savior_bringup/config'
P4 = {'motion.enable': True, 'gating.link_depth': 'contact', 'gating.max_noise_m': 0.5, 'tracker.enable': False,
      'extension.enable': True, 'motion.still_policy': 'unmask', 'compose.right_fallback': 'median'}
VARIANTS = {
    'yolo_naive': ('viode_vehicles_dynamic', {'extension.enable': False, 'tracker.enable': False}),
    'yolo_full_p2': ('viode_vehicles_dynamic', {'tracker.enable': False}),
    'yolo_p4_dyn': ('viode_vehicles_dynamic', P4),
    'yolo_p4_pot': ('viode_vehicles_potential', P4),
    'oracle_dynamic_warp': ('viode_oracle_dynamic', {'extension.enable': False, 'tracker.enable': False,
                                                     'compose.right_fallback': 'median'}),
    'oracle_all_vehicles_warp': ('viode_oracle_all_vehicles', {'extension.enable': False, 'tracker.enable': False,
                                                               'compose.right_fallback': 'median'}),
}
# P5 offline-only sensitivity variants (not run online): --variants yolo_p4_pot_win,yolo_p4_dyn_norad
EXTRA_VARIANTS = {
    'yolo_p4_pot_win': ('viode_vehicles_potential', {**P4, 'motion.window_moving_potential': True}),
    'yolo_p4_dyn_norad': ('viode_vehicles_dynamic', {**P4, 'motion.radial_static_required': False}),
}
VEH = {'car', 'truck', 'bus', 'motorcycle', 'bicycle'}


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flatten(v, f'{prefix}{k}.'))
        else:
            out[f'{prefix}{k}'] = v
    return out


def params(over):
    p = all_defaults()
    y = yaml.safe_load(open(f'{B}/viode/savior_perception.yaml'))
    p.update(flatten(y['savior_node']['ros__parameters']))
    p.update(over)
    return p


def pix(pred, gt):
    tp = int(np.count_nonzero(pred & gt))
    return [tp, int(np.count_nonzero(pred)) - tp, int(np.count_nonzero(gt)) - tp]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default=WS + '/models/yolo26s-seg.engine')
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--inst-out', default='', help='per-instance JSON lines')
    ap.add_argument('--variants', default='', help='comma list (default: all of VARIANTS)')
    a = ap.parse_args()
    global VARIANTS
    if a.variants:
        allv = {**VARIANTS, **EXTRA_VARIANTS}
        VARIANTS = {k: allv[k] for k in a.variants.split(',')}
    env = a.seq.rsplit('_', 1)[0]
    bag = f'{WS}/data/viode/ros2/{a.seq}'
    gt = np.load(f'{WS}/data/viode/gt/masks/{a.seq}.npz')
    gt_idx = {int(s): i for i, s in enumerate(gt['stamp_ns'])}
    dyn_ids, sta_ids = gt['dyn_ids'], gt['static_ids']
    veh = vehicle_ids(env)

    P0 = params({})
    calib = f'{B}/viode/kalibr_imucam_chain.yaml'
    cfg0 = PipelineConfig.from_flat({k: v for k, v in P0.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(calib, 'cam0', 'cam1', focal_scale=cfg0.depth.rect_focal_scale,
                              size_scale=cfg0.depth.rect_size_scale, max_scale=cfg0.depth.rect_max_scale)
    roles_dyn = RoleTable.from_yaml(f'{B}/roles/viode_vehicles_dynamic.yaml')
    yolo = make_segmenter('yolo', model=a.model, conf=P0['segmenter.conf'], iou=P0['segmenter.iou'],
                          imgsz=P0['segmenter.imgsz'], classes=roles_dyn.relevant_classes(),
                          retina_masks=P0['segmenter.retina_masks'])
    pipes = {}
    for name, (roles, over) in VARIANTS.items():
        P = params(over)
        cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
        pipes[name] = SaviorPipeline(cfg, RoleTable.from_yaml(f'{B}/roles/{roles}.yaml'), rect)
    # gyro (whole bag) + frames
    g = GyroIntegrator(max_age_s=1e9)
    frames = {}
    with AnyReader([Path(bag)]) as r:
        conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw', '/cam1/image_raw')]
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            if c.topic == '/imu0':
                w = m.angular_velocity
                g.add(st * 1e-9, (w.x, w.y, w.z))
            else:
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = m
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None and s in gt_idx]
    if a.max_frames:
        stamps = stamps[:a.max_frames]
    acc = {v: {'L_dyn_core': [0, 0, 0], 'L_dyn_any': [0, 0, 0], 'L_all_core': [0, 0, 0], 'R_dyn_core': [0, 0, 0],
               'R_all_core': [0, 0, 0], 'core_px': 0, 'band_px': 0, 'frames': 0} for v in VARIANTS}
    inst_rows = []
    per_vehicle = {}   # (variant, gt id) -> [frames seen, frames masked]
    yolo_pix = {'all': [0, 0, 0], 'dyn': [0, 0, 0]}
    yolo_tp_inst = []
    prev_t = None
    t0 = time.time()
    warm = False
    fo = open(a.inst_out, 'w') if a.inst_out else None
    for k, st in enumerate(stamps):
        lm, rm = frames.pop(st)
        left_rgb, right_rgb = decode_image(lm), decode_image(rm)
        left, right = np.ascontiguousarray(left_rgb[:, :, ::-1]), np.ascontiguousarray(right_rgb[:, :, ::-1])  # BGR
        if not warm:
            yolo.warmup(left.shape)
            warm = True
        gi = gt_idx[st]
        idL, idR = gt['left'][gi], gt['right'][gi]
        gdyn, gall = np.isin(idL, dyn_ids), idL > 0
        gdynR, gallR = np.isin(idR, dyn_ids), idR > 0
        t = st * 1e-9
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        det = yolo.predict(left)
        det_v = [d for d in det if d.cls in VEH]
        um = np.zeros_like(gall)
        for d in det_v:
            um |= d.mask
        for key, gm in (('all', gall), ('dyn', gdyn)):
            p_ = pix(um, gm)
            for j in range(3):
                yolo_pix[key][j] += p_[j]
        # oracle instances from the GT id image (one instance per vehicle id)
        ora = []
        for i in np.unique(idL):
            if i == 0:
                continue
            m = idL == i
            if m.sum() < 20:
                continue
            ys, xs = np.nonzero(m)
            ora.append(Instance(mask=m, cls='dyn_vehicle' if i in dyn_ids else 'static_vehicle', score=1.0,
                                bbox=(int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)))
        for name, pipe in pipes.items():
            inst = copy.deepcopy(ora if name.startswith('oracle') else det)
            ml, mr, stats = pipe.process(left, right, t, inst, R_imu=R_imu)
            A = acc[name]
            core, anyl = ml == 255, ml >= 128
            for key, pr, gm in (('L_dyn_core', core, gdyn), ('L_dyn_any', anyl, gdyn), ('L_all_core', core, gall),
                                ('R_dyn_core', mr == 255, gdynR), ('R_all_core', mr == 255, gallR)):
                p_ = pix(pr, gm)
                for j in range(3):
                    A[key][j] += p_[j]
            A['core_px'] += int(core.sum())
            A['band_px'] += int((ml == 192).sum())
            A['frames'] += 1
            if name.startswith('oracle'):
                continue
            for x in pipe.last_result.instances:
                if x.cls not in VEH or x.mask is None:
                    continue
                ids, cnt = np.unique(idL[x.mask], return_counts=True)
                area = int(x.mask.sum())
                vi = {int(i): int(c) for i, c in zip(ids, cnt) if i > 0}
                n_dyn = sum(c for i, c in vi.items() if i in dyn_ids)
                n_sta = sum(c for i, c in vi.items() if i in sta_ids)
                lab = 'none'
                if n_dyn + n_sta >= 0.3 * area:
                    lab = 'dynamic' if n_dyn >= n_sta else 'static'
                masked = bool(x.is_dynamic)
                gid = max(vi, key=vi.get) if vi and lab != 'none' else 0
                if gid:
                    pv = per_vehicle.setdefault(f'{name}:{gid}:{veh.get(gid, "?")}', [0, 0])
                    pv[0] += 1
                    pv[1] += masked
                mo = x.motion or {}
                row = dict(v=name, t=round(t, 3), cls=x.cls, area=area, lab=lab, gid=gid, status=x.status,
                           masked=masked, depth=round(float(x.depth), 2) if x.depth is not None and np.isfinite(x.depth) else None,
                           l=mo.get('l'), state=mo.get('state'), mid=mo.get('id'))
                inst_rows.append(row)
                if fo:
                    fo.write(json.dumps(row) + '\n')
        if k % 200 == 0:
            print(f'[{a.seq}] frame {k}/{len(stamps)} {time.time() - t0:.0f}s', flush=True)
    if fo:
        fo.close()

    def prf(v):
        tp, fp, fn = v
        return {'precision': round(tp / (tp + fp), 4) if tp + fp else None,
                'recall': round(tp / (tp + fn), 4) if tp + fn else None,
                'iou': round(tp / (tp + fp + fn), 4) if tp + fp + fn else None, 'tp_fp_fn': v}
    out = {'seq': a.seq, 'frames': len(stamps), 'gt_dyn_share_mean': float(gt['dyn_share'].mean()),
           'gt_static_share_mean': float(gt['static_share'].mean()),
           'yolo_vehicle_union': {k: prf(v) for k, v in yolo_pix.items()}, 'variants': {}}
    npx = float(len(stamps) * gall.size)
    for name, A in acc.items():
        out['variants'][name] = {k: prf(A[k]) for k in ('L_dyn_core', 'L_dyn_any', 'L_all_core', 'R_dyn_core', 'R_all_core')}
        out['variants'][name]['core_share'] = round(A['core_px'] / npx, 5)
        out['variants'][name]['band_share'] = round(A['band_px'] / npx, 5)
    # instance-level classification (masked vs GT label)
    cls = {}
    for name in VARIANTS:
        rows = [r for r in inst_rows if r['v'] == name]
        if not rows:
            continue
        c = {}
        for lab in ('dynamic', 'static', 'none'):
            rr = [r for r in rows if r['lab'] == lab]
            c[lab] = {'n': len(rr), 'masked': sum(r['masked'] for r in rr)}
        tp = c['dynamic']['masked']
        fp = c['static']['masked']
        fn = c['dynamic']['n'] - tp
        tn = c['static']['n'] - fp
        c['moving_precision'] = round(tp / (tp + fp), 4) if tp + fp else None
        c['moving_recall'] = round(tp / (tp + fn), 4) if tp + fn else None
        c['static_kept_rate'] = round(tn / (tn + fp), 4) if tn + fp else None
        c['status_by_label'] = {lab: {s: sum(1 for r in rows if r['lab'] == lab and r['status'] == s)
                                      for s in sorted({r['status'] for r in rows})} for lab in ('dynamic', 'static', 'none')}
        cls[name] = c
    out['instances'] = cls
    out['per_vehicle_masked_frac'] = {k: [v[0], round(v[1] / v[0], 3)] for k, v in sorted(per_vehicle.items())}
    out['runtime_s'] = round(time.time() - t0, 1)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump(out, open(a.out, 'w'), sort_keys=False)
    print(yaml.safe_dump({k: out[k] for k in ('seq', 'frames', 'yolo_vehicle_union')}, sort_keys=False))


if __name__ == '__main__':
    main()
