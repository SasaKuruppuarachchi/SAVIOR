#!/usr/bin/env python3
"""rw_refmasks.py --bag data/monado/ros2/<seq> --out data/monado/refmasks/<seq>.npz [--model models/yolo26x-seg.pt]

Reference ("pseudo-GT") person masks for the measurement-share analysis of the real-world study. The Monado dataset has no
GT segmentation, so the share of filter-used measurements on people is measured against an OFFLINE reference segmenter that
SAVIOR never uses at run time: YOLO26x-seg (COCO, the largest model; P2 used the same x model as its reference) at the native
960 px resolution, class person only, ultralytics default conf 0.25 / iou 0.7, retina masks. Masks of cam0 AND cam1, every frame,
max-pooled to 1/4 resolution (240 x 240; a feature at (u, v) is "on a person" if its 4 x 4 cell touches a person pixel).
Output npz (diag_p5.py-compatible keys): stamp_ns, left, right (uint8 0/1, N x 240 x 240), dyn_ids=[1], static_ids=[],
scale=4, plus per-frame person pixel share px_left / px_right (full resolution) and n_person_left.
Run in the savior image with --gpus all."""
import argparse
import time
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bag', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default='/home/sasa/workspace/savior_ws/models/yolo26x-seg.pt')
    ap.add_argument('--imgsz', type=int, default=960)
    ap.add_argument('--scale', type=int, default=4)
    a = ap.parse_args()
    import torch
    from rosbags.highlevel import AnyReader
    from ultralytics import YOLO
    model = YOLO(a.model)
    S = a.scale
    imgs = {'/cam0/image_raw': {}, '/cam1/image_raw': {}}
    out = {k: {} for k in imgs}
    pxs = {k: {} for k in imgs}
    npers = {}
    t0 = time.time()
    with AnyReader([Path(a.bag)]) as r:
        conns = [c for c in r.connections if c.topic in imgs]
        n = 0
        for c, t, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = int(m.header.stamp.sec) * 1_000_000_000 + int(m.header.stamp.nanosec)
            img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width]
            bgr = np.repeat(img[..., None], 3, axis=2)
            res = model.predict(bgr, imgsz=a.imgsz, classes=[0], conf=0.25, iou=0.7, retina_masks=True, verbose=False)[0]
            H, W = img.shape
            if res.masks is not None and len(res.masks):
                mk = (res.masks.data > 0.5).any(0)
                mk = mk[:H, :W]
                full = mk.cpu().numpy()
                pooled = torch.nn.functional.max_pool2d(mk.float()[None, None], S, S)[0, 0].byte().cpu().numpy()
                npers.setdefault(c.topic, {})[st] = int(len(res.masks))
            else:
                full = np.zeros((H, W), bool)
                pooled = np.zeros((H // S, W // S), np.uint8)
                npers.setdefault(c.topic, {})[st] = 0
            out[c.topic][st] = pooled
            pxs[c.topic][st] = float(full.mean())
            n += 1
            if n % 2000 == 0:
                print(f'{n} images {time.time() - t0:.0f}s', flush=True)
    stamps = sorted(set(out['/cam0/image_raw']) & set(out['/cam1/image_raw']))
    L = np.stack([out['/cam0/image_raw'][s] for s in stamps])
    R = np.stack([out['/cam1/image_raw'][s] for s in stamps])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out, stamp_ns=np.array(stamps, np.int64), left=L, right=R, dyn_ids=np.array([1]),
                        static_ids=np.array([], np.int64), scale=S,
                        px_left=np.array([pxs['/cam0/image_raw'][s] for s in stamps]),
                        px_right=np.array([pxs['/cam1/image_raw'][s] for s in stamps]),
                        n_person_left=np.array([npers['/cam0/image_raw'][s] for s in stamps]))
    pl = np.array([pxs['/cam0/image_raw'][s] for s in stamps])
    print(f'{len(stamps)} stereo frames; person pixel share cam0 mean {pl.mean():.4f}, frames with person '
          f'{(pl > 0).mean():.3f}, p90 {np.percentile(pl, 90):.3f}, max {pl.max():.3f}; {time.time() - t0:.0f}s -> {a.out}')


if __name__ == '__main__':
    main()
