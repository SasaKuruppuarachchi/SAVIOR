#!/usr/bin/env python3
"""equiv_yolo.py --seq <t1 seq> --engine <.engine> --cache <detcache dir> --out <json> [--max-frames N] [--ultra]

C++ TensorRT YOLO26-seg segmenter (savior_cpp.Yolo, same .engine) vs the Ultralytics detections of the deployed Python
segmenter (detcache.py: segmenters/yolo.py, conf 0.25, iou 0.7, retina_masks, fast_masks, person/forklift/box/pallet/trolley)
on every left frame of a t1 bag. Per frame: number of detections, per detection (same order) class / box / score / crop mask;
full-frame union-mask pixel agreement; per-instance mask IoU. --ultra: also re-run Ultralytics in-process (sanity check of the
cache itself) and time both. TUNING SET (t1) ONLY.
"""
import os
import argparse
import json
import time
from pathlib import Path

import numpy as np

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
CLASSES = ['person', 'forklift', 'box', 'pallet', 'trolley']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True)
    ap.add_argument('--engine', required=True)
    ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--ultra', action='store_true')
    a = ap.parse_args()
    assert '_t1_' in a.seq
    import savior_cpp
    from rosbags.highlevel import AnyReader
    from equiv_offline import DetCache
    dets = DetCache(f'{a.cache}/{a.seq}.npz')
    yc = savior_cpp.Yolo(a.engine, 0.25, 0.7, CLASSES)
    yc.warmup(376, 672)
    yu = None
    if a.ultra:
        from savior_perception.segmenters import make_segmenter
        yu = make_segmenter('yolo', model=a.engine, conf=0.25, iou=0.7, imgsz=672, classes=CLASSES, retina_masks=True,
                            fast_masks=True)
        yu.warmup((376, 672))
    acc = dict(frames=0, frames_same_n=0, frames_identical=0, dets_ref=0, dets_cpp=0, dets_matched=0, cls_equal=0,
               bbox_equal=0, score_absdiff_max=0.0, mask_px=0, mask_px_equal=0, union_px=0, union_px_equal=0,
               inst_iou_sum=0.0, inst_iou_min=1.0, frames_ultra_identical_to_cache=0)
    tim = {'cpp': [], 'cpp_infer': [], 'cpp_masks': [], 'ultra': []}
    diffs = []
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{a.seq}')]) as r:
        conns = [c for c in r.connections if c.topic == '/cam0/image_raw']
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            if a.max_frames and acc['frames'] >= a.max_frames:
                break
            img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            ref = dets.get(st)
            t0 = time.perf_counter()
            out = yc.predict(img)
            tim['cpp'].append((time.perf_counter() - t0) * 1e3)
            tt = yc.timings()
            tim['cpp_infer'].append(tt['infer'])
            tim['cpp_masks'].append(tt['masks'])
            if yu is not None:
                t0 = time.perf_counter()
                uo = yu.predict(img)
                tim['ultra'].append((time.perf_counter() - t0) * 1e3)
                same = len(uo) == len(ref) and all(
                    u.cls == rr[1] and tuple(u.bbox) == rr[3] and np.array_equal(u.mask[rr[3][1]:rr[3][3], rr[3][0]:rr[3][2]],
                                                                                    rr[0].astype(bool)) for u, rr in zip(uo, ref))
                acc['frames_ultra_identical_to_cache'] += int(same)
            acc['frames'] += 1
            acc['dets_ref'] += len(ref)
            acc['dets_cpp'] += len(out)
            acc['frames_same_n'] += int(len(ref) == len(out))
            h, w = img.shape
            U_r = np.zeros((h, w), bool)
            U_c = np.zeros((h, w), bool)
            ident = len(ref) == len(out)
            items = []
            for k, rr in enumerate(ref):
                x0, y0, x1, y1 = rr[3]
                U_r[y0:y1, x0:x1] |= rr[0].astype(bool)
            for k, cc in enumerate(out):
                x0, y0, x1, y1 = cc[3]
                U_c[y0:y1, x0:x1] |= cc[0].astype(bool)
            for rr, cc in zip(ref, out):
                acc['dets_matched'] += 1
                acc['cls_equal'] += int(rr[1] == cc[1])
                acc['bbox_equal'] += int(tuple(rr[3]) == tuple(cc[3]))
                acc['score_absdiff_max'] = max(acc['score_absdiff_max'], abs(float(np.float32(cc[2])) - rr[2]))
                mr = np.zeros((h, w), bool)
                mc = np.zeros((h, w), bool)
                mr[rr[3][1]:rr[3][3], rr[3][0]:rr[3][2]] = rr[0].astype(bool)
                mc[cc[3][1]:cc[3][3], cc[3][0]:cc[3][2]] = cc[0].astype(bool)
                bx = (min(rr[3][0], cc[3][0]), min(rr[3][1], cc[3][1]), max(rr[3][2], cc[3][2]), max(rr[3][3], cc[3][3]))
                sr, sc = mr[bx[1]:bx[3], bx[0]:bx[2]], mc[bx[1]:bx[3], bx[0]:bx[2]]
                eq = int(np.count_nonzero(sr == sc))
                acc['mask_px'] += sr.size
                acc['mask_px_equal'] += eq
                inter, uni = int(np.count_nonzero(sr & sc)), int(np.count_nonzero(sr | sc))
                iou = inter / uni if uni else 1.0
                acc['inst_iou_sum'] += iou
                acc['inst_iou_min'] = min(acc['inst_iou_min'], iou)
                same = rr[1] == cc[1] and tuple(rr[3]) == tuple(cc[3]) and eq == sr.size
                ident &= same
                if not same:
                    items.append({'cls': [rr[1], cc[1]], 'bbox': [list(rr[3]), list(cc[3])], 'diff_px': sr.size - eq,
                                  'score': [rr[2], cc[2]]})
            acc['union_px'] += h * w
            acc['union_px_equal'] += int(np.count_nonzero(U_r == U_c))
            acc['frames_identical'] += int(ident)
            if not ident:
                diffs.append({'stamp': st, 'n': [len(ref), len(out)], 'items': items[:6]})

    def pct(v):
        if not v:
            return None
        v = np.asarray(v, float)
        return {q: round(float(np.percentile(v, q)), 3) for q in (50, 90, 99)} | {'mean': round(float(v.mean()), 3)}
    out = {'seq': a.seq, 'engine': a.engine, 'acc': acc, 'timing_ms': {k: pct(v) for k, v in tim.items()},
           'n_diff_frames': len(diffs), 'diffs': diffs[:300]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    A = acc
    print(f"{a.seq}: frames {A['frames']} identical {A['frames_identical']} same_n {A['frames_same_n']} dets {A['dets_ref']}/"
          f"{A['dets_cpp']} union px agree {A['union_px_equal'] / max(1, A['union_px']):.7f} inst px agree "
          f"{A['mask_px_equal'] / max(1, A['mask_px']):.7f} min IoU {A['inst_iou_min']:.4f}", flush=True)


if __name__ == '__main__':
    main()
