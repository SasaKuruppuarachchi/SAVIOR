#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sim-to-real proxy for the person class: fine-tuned (sim-only) warehouse model vs the COCO-pretrained YOLO26s on
REAL images without instance GT (OpenLORIS cafe / market, RealSense T265 fisheye mono8, 848x800).

Pseudo-GT = COCO-pretrained person detections with conf >= 0.5 (the COCO model is trained on real people). Reported:
fraction of pseudo-GT persons the fine-tuned model also finds (mask IoU >= 0.5 at its deployed conf 0.25, by area),
and fine-tuned person detections that no COCO detection (conf >= 0.1) supports. Not an accuracy measurement; it
only shows whether sim-only fine-tuning lost real-person recognition.

  python3 real_person_check.py --ft models/warehouse/yolo26s-seg-warehouse.pt --coco models/yolo26s-seg.pt
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)


def frames(bag, topic, every):
    from rosbags.highlevel import AnyReader
    with AnyReader([Path(bag)]) as r:
        conns = [c for c in r.connections if c.topic == topic]
        for i, (conn, _, raw) in enumerate(r.messages(connections=conns)):
            if i % every:
                continue
            m = r.deserialize(raw, conn.msgtype)
            yield np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()


def persons(model, img, conf, cls):
    import cv2
    im = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    r = model.predict(im, conf=conf, iou=0.7, imgsz=672, retina_masks=True, classes=[cls], verbose=False)[0]
    if r.masks is None or not len(r.boxes):
        return np.zeros((0,) + im.shape[:2], bool), np.zeros(0)
    return (r.masks.data.cpu().numpy() > 0.5), r.boxes.conf.cpu().numpy()


def iou(a, b):
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    A = a.reshape(len(a), -1).astype(np.float32)
    B = b.reshape(len(b), -1).astype(np.float32)
    inter = A @ B.T
    return inter / (A.sum(1)[:, None] + B.sum(1)[None] - inter + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ft', required=True)
    ap.add_argument('--coco', default=f'{WS}/models/yolo26s-seg.pt')
    ap.add_argument('--bags', default='cafe1-1,cafe1-2,market1-1')
    ap.add_argument('--topic', default='/t265/fisheye1/image_raw')
    ap.add_argument('--every', type=int, default=15)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    from ultralytics import YOLO
    ft, coco = YOLO(a.ft, task='segment'), YOLO(a.coco, task='segment')
    ft_person = [k for k, v in ft.names.items() if v == 'person'][0]
    bins = [0, 1024, 4096, 16384, 10 ** 9]
    labels = ['<1k', '1k-4k', '4k-16k', '>16k']
    hit = {l: [0, 0] for l in labels}
    ft_unsupported = ft_total = n = 0
    for b in a.bags.split(','):
        for img in frames(f'{WS}/data/openloris/ros2/{b}', a.topic, a.every):
            n += 1
            cm, cs = persons(coco, img, 0.1, 0)
            fm, _ = persons(ft, img, 0.25, ft_person)
            gt = cm[cs >= 0.5]
            M = iou(gt, fm)
            for j, g in enumerate(gt):
                area = g.sum()
                lab = labels[np.searchsorted(bins, area, side='right') - 1]
                hit[lab][1] += 1
                hit[lab][0] += int(M.shape[1] > 0 and M[j].max() >= 0.5)
            S = iou(fm, cm)
            ft_total += len(fm)
            ft_unsupported += int(sum(1 for i in range(len(fm)) if S.shape[1] == 0 or S[i].max() < 0.3))
    res = dict(frames=n, bags=a.bags, topic=a.topic,
               ft_recall_of_coco_persons={k: [v[0] / v[1] if v[1] else None, v[1]] for k, v in hit.items()},
               ft_recall_all=sum(v[0] for v in hit.values()) / max(1, sum(v[1] for v in hit.values())),
               ft_person_detections=ft_total, ft_unsupported_by_coco=ft_unsupported)
    print(json.dumps(res, indent=1))
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
