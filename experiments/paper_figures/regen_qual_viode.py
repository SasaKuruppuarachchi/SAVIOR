#!/usr/bin/env python3
"""regen_qual_viode.py --seq parking_lot_high --stamps s1,s2,... [--out-dir d]

Deterministic regeneration of the per-frame left masks of the P5 offline evaluation for the qualitative figure
(Fig. fig:qual, row a). P5 stored only per-instance decisions (results/p5_viode/offline/<seq>_inst.jsonl), not the
masks, so this script re-runs exactly the offline_eval.py pipeline (same YOLO26s engine, same VIODE perception
parameters, same roles and overrides, same gyro rotation between frames) for the two variants shown:
  yolo_naive   = Y-Cls     (roles viode_vehicles_dynamic, no extension band)
  yolo_p4_pot  = SAVIOR-PM (roles viode_vehicles_potential, promotion + motion evidence + band)
from the first frame up to the last requested stamp (the motion evidence is stateful), and saves for each requested
stamp an npz with the RGB left image, the final left mask (255 core / 192 band) and the per-instance decisions.
It also checks the decisions against the stored P5 jsonl rows of the same stamp (reproduction check).
Run in the savior image with the workspace install sourced and the GPU (TensorRT engine).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader

WS = '/home/sasa/workspace/savior_ws'
P5 = WS + '/results/p5_viode'
sys.path.insert(0, P5 + '/scripts')
import offline_eval as oe  # noqa: E402
from viode_common import decode_image  # noqa: E402

from savior_perception.core.calibration import stereo_from_kalibr  # noqa: E402
from savior_perception.core.config import PipelineConfig  # noqa: E402
from savior_perception.core.motion import GyroIntegrator  # noqa: E402
from savior_perception.core.pipeline import SaviorPipeline  # noqa: E402
from savior_perception.core.roles import RoleTable  # noqa: E402
from savior_perception.segmenters import make_segmenter  # noqa: E402

SHOW = ['yolo_naive', 'yolo_p4_pot']


def cfg_of(P):
    return PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', default='parking_lot_high')
    ap.add_argument('--stamps', required=True)
    ap.add_argument('--out-dir', default=P5 + '/offline/qual')
    ap.add_argument('--model', default=WS + '/models/yolo26s-seg.engine')
    a = ap.parse_args()
    want = sorted(int(s) for s in a.stamps.split(','))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    B = oe.B
    gt = np.load(f'{WS}/data/viode/gt/masks/{a.seq}.npz')
    gt_idx = {int(s): i for i, s in enumerate(gt['stamp_ns'])}
    dyn_ids, sta_ids = gt['dyn_ids'], gt['static_ids']
    P0 = oe.params({})
    c0 = cfg_of(P0)
    rect = stereo_from_kalibr(f'{B}/viode/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=c0.depth.rect_focal_scale,
                              size_scale=c0.depth.rect_size_scale, max_scale=c0.depth.rect_max_scale)
    roles_dyn = RoleTable.from_yaml(f'{B}/roles/viode_vehicles_dynamic.yaml')
    yolo = make_segmenter('yolo', model=a.model, conf=P0['segmenter.conf'], iou=P0['segmenter.iou'],
                          imgsz=P0['segmenter.imgsz'], classes=roles_dyn.relevant_classes(),
                          retina_masks=P0['segmenter.retina_masks'])
    pipes = {}
    for name in SHOW:
        roles, over = oe.VARIANTS[name]
        pipes[name] = SaviorPipeline(cfg_of(oe.params(over)), RoleTable.from_yaml(f'{B}/roles/{roles}.yaml'), rect)
    g = GyroIntegrator(max_age_s=1e9)
    frames = {}
    with AnyReader([Path(f'{WS}/data/viode/ros2/{a.seq}')]) as r:
        conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw', '/cam1/image_raw')]
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            if c.topic == '/imu0':
                w = m.angular_velocity
                g.add(st * 1e-9, (w.x, w.y, w.z))
            elif st <= want[-1]:
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = m
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None and s in gt_idx]
    stored = {}
    for line in open(f'{P5}/offline/{a.seq}_inst.jsonl'):
        row = json.loads(line)
        if row['v'] in SHOW:
            stored.setdefault((row['v'], row['t']), []).append(row)
    prev_t = None
    warm = False
    for st in stamps:
        lm, rm = frames.pop(st)
        left_rgb, right_rgb = decode_image(lm), decode_image(rm)
        left, right = np.ascontiguousarray(left_rgb[:, :, ::-1]), np.ascontiguousarray(right_rgb[:, :, ::-1])
        if not warm:
            yolo.warmup(left.shape)
            warm = True
        t = st * 1e-9
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        det = yolo.predict(left)
        idL = gt['left'][gt_idx[st]]
        for name, pipe in pipes.items():
            ml, mr, _ = pipe.process(left, right, t, copy.deepcopy(det), R_imu=R_imu)
            if st not in want:
                continue
            inst = []
            for x in pipe.last_result.instances:
                if x.cls not in oe.VEH or x.mask is None:
                    continue
                ids, cnt = np.unique(idL[x.mask], return_counts=True)
                area = int(x.mask.sum())
                vi = {int(i): int(c) for i, c in zip(ids, cnt) if i > 0}
                n_dyn = sum(c for i, c in vi.items() if i in dyn_ids)
                n_sta = sum(c for i, c in vi.items() if i in sta_ids)
                lab = 'none'
                if n_dyn + n_sta >= 0.3 * area:
                    lab = 'dynamic' if n_dyn >= n_sta else 'static'
                gid = max(vi, key=vi.get) if vi and lab != 'none' else 0
                inst.append(dict(cls=x.cls, area=area, lab=lab, gid=gid, status=x.status, masked=bool(x.is_dynamic)))
            ref = sorted((r_['gid'], r_['cls'], r_['masked'], r_['status']) for r_ in stored.get((name, round(t, 3)), []))
            new = sorted((i['gid'], i['cls'], i['masked'], i['status']) for i in inst)
            print(f'{name} {st}: regenerated {new}\n{" " * len(name)} stored      {ref}  match={new == ref}', flush=True)
            np.savez_compressed(out / f'{a.seq}_{st}_{name}.npz', left_rgb=left_rgb, ml=ml, gt_left=idL,
                                dyn_ids=dyn_ids, static_ids=sta_ids, inst=json.dumps(inst), match=new == ref)


if __name__ == '__main__':
    main()
