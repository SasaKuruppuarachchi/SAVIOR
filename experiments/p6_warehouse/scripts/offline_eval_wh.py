#!/usr/bin/env python3
"""offline_eval_wh.py --seq <seq> --out <yaml> [--inst-out jsonl] [--every N] [--save-stamps s1,s2 --save-dir d]

Offline (deterministic, no ROS graph) evaluation of the P6 perception variants on a SAVIOR-Warehouse bag against the
GT instance segmentation (raw/<seq>/seg0|seg1 + moving.csv, scripts/wh_gt.py). It runs exactly what savior_node
runs (mono8 left image -> YOLO -> SaviorPipeline with the gyro rotation between frames) with the parameters of
run_method.sh, for:
  yolo_naive, yolo_p2, yolo_p4, yolo_p4_nointer, yolo_p4_noext   (fine-tuned YOLO26s, one detection pass shared)
  yolo_coco_person_p4                                             (COCO YOLO26s, person only)
  oracle_moving_warp, oracle_class_naive_warp                     (GT left instances -> stereo warp right; quality of the warp)
Outputs
  * pixel quality of the final left core (255) / core+band mask vs GT moving pixels and vs GT potential-class pixels,
    right core vs GT right moving pixels;
  * GT-centric decisions: every GT instance of a potential class (>= MIN_PX px in cam0) in every frame is
    "masked" if >= 50 % of its pixels are in the core mask; split by class x moving/static and for carried loads
    (box / pallet in a forklift actor block) on moving vs parked forklifts;
  * detection-centric decisions: each detected instance gets the GT instance with the largest overlap (>= 30 % of its
    area, else "none"), its status (root / promoted / unpromoted / still ...) and masked flag;
  * YOLO detection pixel recall / precision per class (fine-tuned vs COCO person).
"""
import argparse
import copy
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml
from rosbags.highlevel import AnyReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wh_gt import POT, SeqGT  # noqa: E402

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
MIN_PX = 200
P4 = {'motion.enable': True, 'gating.link_depth': 'contact', 'gating.max_noise_m': 0.5, 'tracker.enable': False,
      'extension.enable': True, 'motion.still_policy': 'unmask', 'compose.right_fallback': 'median'}
P2 = {'motion.enable': False, 'gating.link_depth': 'contact', 'gating.max_noise_m': 0.5, 'tracker.enable': False,
      'extension.enable': True, 'compose.right_fallback': 'median'}
ORA = {'extension.enable': False, 'tracker.enable': False, 'compose.right_fallback': 'median'}
# name -> (detections: wh | coco | gt_moving | gt_all, roles yaml, overrides)
VARIANTS = {
    'yolo_naive': ('wh', 'warehouse_naive', {'extension.enable': False, 'tracker.enable': False, 'compose.right_fallback': 'median'}),
    'yolo_p2': ('wh', 'warehouse', P2),
    'yolo_p4': ('wh', 'warehouse', P4),
    'yolo_p4_nointer': ('wh', 'warehouse', {**P4, 'gating.promote_contact': False}),
    'yolo_p4_noext': ('wh', 'warehouse', {**P4, 'extension.enable': False}),
    'yolo_p6': ('wh', 'warehouse', {**P4, 'motion.window_unveto_potential': True, 'gating.max_depth': 2}),
    'yolo_coco_person_p4': ('coco', 'person_only', P4),
    'oracle_moving_warp': ('gt_moving', 'warehouse_naive', ORA),
    'oracle_class_naive_warp': ('gt_all', 'warehouse_naive', ORA),
}
# P6 offline sensitivity variants (selection of the post-hoc yolo_p6 configuration; --variants ...)
EXTRA_VARIANTS = {
    'yolo_p4_win': ('wh', 'warehouse', {**P4, 'motion.window_moving_potential': True}),
    'yolo_p4_d2': ('wh', 'warehouse', {**P4, 'gating.max_depth': 2}),
    'yolo_p4_win_d2': ('wh', 'warehouse', {**P4, 'motion.window_moving_potential': True, 'gating.max_depth': 2}),
    'yolo_p4_win_d1': ('wh', 'warehouse', {**P4, 'motion.window_moving_potential': True, 'gating.max_depth': 1}),
    'yolo_p2_d2': ('wh', 'warehouse', {**P2, 'gating.max_depth': 2}),
    'yolo_p4_unveto': ('wh', 'warehouse', {**P4, 'motion.window_unveto_potential': True}),
    'yolo_p4_unveto_d2': ('wh', 'warehouse', {**P4, 'motion.window_unveto_potential': True, 'gating.max_depth': 2}),
    'yolo_p4_unveto_d3': ('wh', 'warehouse', {**P4, 'motion.window_unveto_potential': True, 'gating.max_depth': 3}),
}


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
    y = yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))
    p.update(flatten(y['savior_node']['ros__parameters']))
    p.update(over)
    return p


def pix(pred, gt):
    tp = int(np.count_nonzero(pred & gt))
    return np.array([tp, int(np.count_nonzero(pred)) - tp, int(np.count_nonzero(gt)) - tp], np.int64)


def prf(v):
    tp, fp, fn = (int(x) for x in v)
    return {'precision': round(tp / (tp + fp), 4) if tp + fp else None, 'recall': round(tp / (tp + fn), 4) if tp + fn else None,
            'iou': round(tp / (tp + fp + fn), 4) if tp + fp + fn else None, 'tp_fp_fn': [tp, fp, fn]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--inst-out', default='')
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--every', type=int, default=1, help='evaluate every Nth frame (pipelines still run on all)')
    ap.add_argument('--variants', default='')
    ap.add_argument('--save-stamps', default='', help='comma list of ns stamps: save raw + masks (npz) for figures')
    ap.add_argument('--save-dir', default='')
    a = ap.parse_args()
    V = {k: {**VARIANTS, **EXTRA_VARIANTS}[k] for k in a.variants.split(',')} if a.variants else VARIANTS
    gt = SeqGT(a.seq)
    bag = f'{WS}/data/warehouse/ros2_stereoseg/{a.seq}'
    P0 = params({})
    cfg0 = PipelineConfig.from_flat({k: v for k, v in P0.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(f'{B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=cfg0.depth.rect_focal_scale,
                              size_scale=cfg0.depth.rect_size_scale, max_scale=cfg0.depth.rect_max_scale)
    segs = {}
    if any(v[0] == 'wh' for v in V.values()):
        segs['wh'] = make_segmenter('yolo', model=WS + '/models/warehouse/yolo26s-seg-warehouse.engine', conf=P0['segmenter.conf'],
                                    iou=P0['segmenter.iou'], imgsz=P0['segmenter.imgsz'], classes=list(POT),
                                    retina_masks=P0['segmenter.retina_masks'])
    if any(v[0] == 'coco' for v in V.values()):
        segs['coco'] = make_segmenter('yolo', model=WS + '/models/yolo26s-seg.engine', conf=P0['segmenter.conf'],
                                      iou=P0['segmenter.iou'], imgsz=P0['segmenter.imgsz'], classes=['person'],
                                      retina_masks=P0['segmenter.retina_masks'])
    pipes = {}
    for name, (src, roles, over) in V.items():
        P = params(over)
        cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
        pipes[name] = SaviorPipeline(cfg, RoleTable.from_yaml(f'{B}/roles/{roles}.yaml'), rect)
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
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    if a.max_frames:
        stamps = stamps[:a.max_frames]
    save = set(int(s) for s in a.save_stamps.split(',') if s.strip())
    if save:
        Path(a.save_dir).mkdir(parents=True, exist_ok=True)
    pixacc = {v: {} for v in V}
    gtc = {v: {} for v in V}            # GT-centric: key -> [n, masked]
    detc = {v: [] for v in V}
    detpix = {k: {} for k in segs}
    fo = open(a.inst_out, 'w') if a.inst_out else None
    prev_t = None
    t0 = time.time()
    for s in segs.values():
        s.warmup(frames[stamps[0]][0].shape)
    n_eval = 0
    for k, st in enumerate(stamps):
        left, right = frames.pop(st)
        t = st * 1e-9
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        ev = (k % a.every == 0)
        ids0, ids1 = gt.seg(0, st), gt.seg(1, st)
        mv = gt.moving.get(st, set())
        mvarr = np.fromiter(mv, np.int64) if mv else np.zeros(0, np.int64)
        code0 = gt.code[ids0]
        pot0 = (code0 >= 1) & (code0 <= 5)
        mov0 = np.isin(ids0, mvarr) & (ids0 > 0)
        mov1 = np.isin(ids1, mvarr) & (ids1 > 0)
        det = {kk: s.predict(left) for kk, s in segs.items()}
        # GT oracle instances (one per GT instance id, like the oracle colormap backend minus component merging)
        ora_all, ora_mov = [], []
        if any(v[0].startswith('gt') for v in V.values()):
            uid = [int(i) for i in np.unique(ids0) if i > 0 and gt.code[i] in (1, 2, 3, 4, 5)]
            for i in uid:
                m = ids0 == i
                if m.sum() < 30:
                    continue
                ys, xs = np.nonzero(m)
                ins = Instance(mask=m, cls=gt.cls[i], score=1.0, bbox=(int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
                ora_all.append(ins)
                if i in mv:
                    ora_mov.append(ins)
        if ev:
            for kk, dl in det.items():
                for c in POT:
                    u = np.zeros_like(pot0)
                    for d in dl:
                        if d.cls == c:
                            u |= d.mask
                    gm = code0 == (POT.index(c) + 1)
                    gmm = gm | (code0 == POT.index(c) + 11)
                    acc = detpix[kk].setdefault(c, {'all': np.zeros(3, np.int64), 'moving': np.zeros(3, np.int64)})
                    acc['all'] += pix(u, gmm)
                    acc['moving'] += pix(u, gmm & mov0)
            # GT instances in frame
            gids, gcnt = np.unique(ids0, return_counts=True)
            ginst = [(int(i), int(n)) for i, n in zip(gids, gcnt) if i > 0 and gt.code[i] in (1, 2, 3, 4, 5) and n >= MIN_PX]
            n_eval += 1
        for name, (src, roles, over) in V.items():
            pipe = pipes[name]
            inp = copy.deepcopy(det[src] if src in det else (ora_mov if src == 'gt_moving' else ora_all))
            ml, mr, stats = pipe.process(left, right, t, inp, R_imu=R_imu)
            if st in save:
                np.savez_compressed(f'{a.save_dir}/{a.seq}_{st}_{name}.npz', left=left, ml=ml, mr=mr, gt0=gt.category_image(0, st))
            if not ev:
                continue
            core, anyl = ml == 255, ml >= 128
            A = pixacc[name]
            for key, pr, gm in (('L_core_vs_moving', core, mov0), ('L_any_vs_moving', anyl, mov0),
                                ('L_core_vs_potential', core, pot0), ('R_core_vs_moving', mr == 255, mov1)):
                A[key] = A.get(key, np.zeros(3, np.int64)) + pix(pr, gm)
            A['core_px'] = A.get('core_px', 0) + int(core.sum())
            A['band_px'] = A.get('band_px', 0) + int((ml == 192).sum())
            A['static_pot_core_px'] = A.get('static_pot_core_px', 0) + int((core & pot0 & ~mov0).sum())
            # GT-centric
            G = gtc[name]
            cnt_core = np.bincount(ids0.ravel(), weights=core.ravel(), minlength=gt.max_id + 1)
            for i, n in ginst:
                frac = float(cnt_core[i]) / n
                masked = frac >= 0.5
                c = gt.cls[i]
                moving = i in mv
                keys = [f'{c}:{"moving" if moving else "static"}']
                f = gt.carried_by(i)
                if f is not None and c in ('box', 'pallet'):
                    keys.append(f'carried_{c}:{"moving" if moving else "static"}')
                if c == 'person' and i >= 5000 and gt.carried_by(i) is not None:
                    keys.append(f'driver:{"moving" if moving else "static"}')
                for kk in keys:
                    e = G.setdefault(kk, [0, 0])
                    e[0] += 1
                    e[1] += int(masked)
            # detection-centric
            if src in ('wh', 'coco'):
                for x in pipe.last_result.instances:
                    if x.mask is None or x.role not in ('dynamic', 'potential'):
                        continue
                    area = int(x.mask.sum())
                    if area == 0:
                        continue
                    ii, cc = np.unique(ids0[x.mask], return_counts=True)
                    best, bn = 0, 0
                    for i, n in zip(ii, cc):
                        if i > 0 and gt.code[i] in (1, 2, 3, 4, 5) and n > bn:
                            best, bn = int(i), int(n)
                    lab = 'none'
                    if best and bn >= 0.3 * area:
                        lab = 'moving' if best in mv else 'static'
                    carried = gt.carried_by(best) if best else None
                    mo = x.motion or {}
                    row = dict(v=name, t=round(t, 3), cls=x.cls, gcls=gt.cls.get(best) if best else None, gid=best,
                               area=area, lab=lab, status=x.status, masked=bool(x.is_dynamic),
                               carried=(None if carried is None else ('moving' if carried in mv else 'static')),
                               depth=round(float(x.depth), 2) if x.depth is not None and np.isfinite(x.depth) else None,
                               l=mo.get('l'), state=mo.get('state'))
                    detc[name].append(row)
                    if fo:
                        fo.write(json.dumps(row) + '\n')
        if k % 200 == 0:
            print(f'[{a.seq}] frame {k}/{len(stamps)} {time.time() - t0:.0f}s', flush=True)
    if fo:
        fo.close()
    npx = float(n_eval * pot0.size)
    out = {'seq': a.seq, 'frames': len(stamps), 'frames_eval': n_eval, 'min_px': MIN_PX, 'variants': {}, 'gt_centric': {},
           'detection_centric': {}, 'yolo_pixels': {}}
    for name, A in pixacc.items():
        o = {k: prf(v) for k, v in A.items() if isinstance(v, np.ndarray)}
        o['core_share'] = round(A.get('core_px', 0) / npx, 5)
        o['band_share'] = round(A.get('band_px', 0) / npx, 5)
        o['static_potential_core_share'] = round(A.get('static_pot_core_px', 0) / npx, 5)
        out['variants'][name] = o
        out['gt_centric'][name] = {k: {'n': v[0], 'masked': v[1], 'rate': round(v[1] / v[0], 4)} for k, v in sorted(gtc[name].items())}
        rows = detc[name]
        if rows:
            d = {}
            for c in list(POT) + ['all']:
                rr = [r for r in rows if c == 'all' or r['gcls'] == c or (r['lab'] == 'none' and r['cls'] == c)]
                tp = sum(1 for r in rr if r['lab'] == 'moving' and r['masked'])
                fp_s = sum(1 for r in rr if r['lab'] == 'static' and r['masked'])
                fp_n = sum(1 for r in rr if r['lab'] == 'none' and r['masked'])
                fn = sum(1 for r in rr if r['lab'] == 'moving' and not r['masked'])
                ns = sum(1 for r in rr if r['lab'] == 'static')
                d[c] = {'n': len(rr), 'n_moving': tp + fn, 'n_static': ns, 'n_none': sum(1 for r in rr if r['lab'] == 'none'),
                        'moving_precision': round(tp / (tp + fp_s), 4) if tp + fp_s else None,
                        'moving_precision_incl_fp_det': round(tp / (tp + fp_s + fp_n), 4) if tp + fp_s + fp_n else None,
                        'moving_recall': round(tp / (tp + fn), 4) if tp + fn else None,
                        'static_kept': round((ns - fp_s) / ns, 4) if ns else None,
                        'status_moving': {s: sum(1 for r in rr if r['lab'] == 'moving' and r['status'] == s) for s in sorted({r['status'] for r in rr})},
                        'status_static': {s: sum(1 for r in rr if r['lab'] == 'static' and r['status'] == s) for s in sorted({r['status'] for r in rr})}}
            for cm in ('moving', 'static'):
                rr = [r for r in rows if r['carried'] == cm and r['gcls'] in ('box', 'pallet')]
                d[f'carried_load_on_{cm}_forklift'] = {'n': len(rr), 'masked': sum(r['masked'] for r in rr),
                                                       'status': {s: sum(1 for r in rr if r['status'] == s) for s in sorted({r['status'] for r in rr})}}
            out['detection_centric'][name] = d
    for kk, D in detpix.items():
        out['yolo_pixels'][kk] = {c: {'all': prf(v['all']), 'moving': prf(v['moving'])} for c, v in D.items()}
    out['runtime_s'] = round(time.time() - t0, 1)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    yaml.safe_dump(json.loads(json.dumps(out)), open(a.out, 'w'), sort_keys=False)
    print('done', a.seq, out['runtime_s'])


if __name__ == '__main__':
    main()
