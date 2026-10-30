#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Latency of savior_perception's YoloSegmenter.predict() (exactly the node's segment stage) on warehouse frames.

Frames: hall_t1_L2 cam0, converted to mono8 like /cam0/image_raw (the segmenter replicates it to 3 channels).
Classes filtered to the warehouse role table's dynamic + potential classes (segmenter.filter_classes).

  python3 bench_segmenter.py --models a.engine b.pt ... [--frames 300] [--out bench.json]
"""
import argparse
import glob
import json
import os
import time

import cv2
import numpy as np

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', nargs='+', required=True)
    ap.add_argument('--seq', default=f'{WS}/data/warehouse/raw/hall_t1_L2')
    ap.add_argument('--frames', type=int, default=300)
    ap.add_argument('--imgsz', type=int, default=672)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    from savior_perception.core.roles import RoleTable
    from savior_perception.segmenters import make_segmenter
    roles = RoleTable.from_yaml(f'{WS}/src/savior/savior_bringup/config/roles/warehouse.yaml')
    paths = sorted(glob.glob(os.path.join(a.seq, 'cam0', '*.png')))
    paths = paths[60:60 + a.frames]
    imgs = [cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY) for p in paths]
    res = {}
    for m in a.models:
        coco = 'warehouse' not in os.path.basename(m)
        cls = ['person'] if coco else roles.relevant_classes()
        seg = make_segmenter('yolo', model=m, conf=0.25, iou=0.7, imgsz=a.imgsz, classes=cls, retina_masks=True)
        speeds = []
        orig = seg.model.predict

        def wrapped(*args, **kw):
            r = orig(*args, **kw)
            speeds.append(r[0].speed)
            return r
        seg.model.predict = wrapped
        for _ in range(20):
            seg.predict(imgs[0])
        speeds.clear()
        t, n = [], []
        for im in imgs:
            t0 = time.perf_counter()
            out = seg.predict(im)
            t.append((time.perf_counter() - t0) * 1e3)
            n.append(len(out))
        t = np.array(t)
        sp = {k: float(np.median([s[k] for s in speeds])) for k in speeds[0]}
        res[os.path.basename(m)] = dict(median_ms=float(np.median(t)), p90_ms=float(np.percentile(t, 90)),
                                        mean_ms=float(t.mean()), mean_instances=float(np.mean(n)), classes=cls,
                                        ultralytics_median_ms=sp)
        print(os.path.basename(m), json.dumps(res[os.path.basename(m)]))
        del seg
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
