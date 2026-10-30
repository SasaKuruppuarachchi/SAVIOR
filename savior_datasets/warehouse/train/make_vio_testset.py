#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Domain-relevant TEST set from the SAVIOR-Warehouse VIO sequences (raw/<seq>/cam0 + seg0 + instances.json),
plus a frame-leakage check against the segmentation training set.

Frames: every `--stride` frames (default 40 = 2 s at 20 Hz) of all 8 sequences. Level Lk starts at offset
k * stride / 4, so the four levels (same camera trajectory) do not contribute four copies of the same view.
Two image variants share one label set:
  images/test_rgb/   cam0 RGB as rendered (PNG, lossless)
  images/test_gray/  BT.601 luma replicated to 3 channels = exactly what savior_node feeds YOLO from the mono8
                     /cam0/image_raw of the bags (cv2.COLOR_GRAY2BGR)
Labels (YOLO-seg, one line per GT instance, multi-part instances bridged as in make_yolo_inst.py) are written for
the 8 warehouse classes, instances >= --min-area px (same 40 px as the training set). manifest.json lists every
frame with its sequence, stamp, seg0 path and the instance ids that move in that frame (moving.csv).

Leakage check: 96x54 grey thumbnails, zero-mean normalised cross-correlation (NCC) of every test frame against
all 2720 train+val images. References: NCC between the same frame of L0 and L1 (identical camera pose and static
scene, only the actors differ) and between consecutive frames (50 ms apart). Frame leakage would show up as
test-vs-train NCC at the level of those references.

  python3 make_vio_testset.py [--out data/warehouse/seg_test_vio] [--stride 40]
"""
import argparse
import csv
import glob
import json
import os

import cv2
import numpy as np

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
NAMES = ['rack', 'guard_rail', 'window', 'forklift', 'box', 'pallet', 'trolley', 'person']
SEQS = [f'{s}_t1_L{k}' for s in ('aisles', 'hall') for k in range(4)]


def instance_polygon(m):
    from ultralytics.data.converter import merge_multi_segment
    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    segs = [c.reshape(-1).astype(np.float64).tolist() for c in cnts if len(c) >= 3]
    if not segs:
        return None
    if len(segs) == 1:
        return np.array(segs[0]).reshape(-1, 2)
    return np.concatenate(merge_multi_segment(segs), axis=0).reshape(-1, 2)


def thumb(img):
    g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    t = cv2.resize(g, (96, 54), interpolation=cv2.INTER_AREA).astype(np.float32).reshape(-1)
    t -= t.mean()
    return t / (np.linalg.norm(t) + 1e-6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=f'{WS}/data/warehouse/raw')
    ap.add_argument('--segtrain', default=f'{WS}/data/warehouse/seg_train')
    ap.add_argument('--out', default=f'{WS}/data/warehouse/seg_test_vio')
    ap.add_argument('--stride', type=int, default=40)
    ap.add_argument('--min-area', type=int, default=40)
    ap.add_argument('--leak-json', default='')
    a = ap.parse_args()
    for v in ('test_rgb', 'test_gray'):
        os.makedirs(os.path.join(a.out, 'images', v), exist_ok=True)
        os.makedirs(os.path.join(a.out, 'labels', v), exist_ok=True)
    manifest, thumbs, counts = [], [], {n: 0 for n in NAMES}
    ref_level, ref_consec = [], []
    for seq in SEQS:
        d = os.path.join(a.raw, seq)
        inst = json.load(open(os.path.join(d, 'instances.json')))
        cls_of = {i['id']: i['cls'] for i in inst['instances']}
        moving = {}
        with open(os.path.join(d, 'moving.csv')) as fh:
            for row in csv.reader(fh):
                if row and not row[0].startswith('#'):
                    moving[int(row[1])] = [int(x) for x in row[2].split()] if len(row) > 2 and row[2] else []
        stamps = sorted(int(os.path.basename(p)[:-4]) for p in glob.glob(os.path.join(d, 'cam0', '*.png')))
        lvl = int(seq[-1])
        for fi in range(lvl * a.stride // 4, len(stamps), a.stride):
            st = stamps[fi]
            rgb = cv2.imread(os.path.join(d, 'cam0', f'{st}.png'), cv2.IMREAD_COLOR)
            seg = cv2.imread(os.path.join(d, 'seg0', f'{st}.png'), cv2.IMREAD_UNCHANGED)
            H, W = seg.shape
            name = f'{seq}_{st}'
            cv2.imwrite(os.path.join(a.out, 'images', 'test_rgb', name + '.png'), rgb)
            gray = cv2.cvtColor(cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            cv2.imwrite(os.path.join(a.out, 'images', 'test_gray', name + '.png'), gray)
            ids, cnt = np.unique(seg, return_counts=True)
            lines = []
            for i, c in zip(ids, cnt):
                cl = cls_of.get(int(i))
                if i == 0 or cl not in NAMES or c < a.min_area:
                    continue
                p = instance_polygon(seg == i)
                if p is None:
                    continue
                p = (p / (W, H)).clip(0, 1)
                lines.append(f'{NAMES.index(cl)} ' + ' '.join(f'{v:.5f}' for v in p.reshape(-1)))
                counts[cl] += 1
            for v in ('test_rgb', 'test_gray'):
                with open(os.path.join(a.out, 'labels', v, name + '.txt'), 'w') as fh:
                    fh.write('\n'.join(lines) + ('\n' if lines else ''))
            manifest.append(dict(name=name, seq=seq, frame=fi, stamp_ns=st, seg=os.path.join(d, 'seg0', f'{st}.png'),
                                 instances=os.path.join(d, 'instances.json'), moving=moving.get(st, [])))
            thumbs.append(thumb(rgb))
            # references for the leakage check
            if fi + 1 < len(stamps) and len(ref_consec) < 400:
                nxt = cv2.imread(os.path.join(d, 'cam0', f'{stamps[fi + 1]}.png'), cv2.IMREAD_COLOR)
                ref_consec.append(float(thumb(rgb) @ thumb(nxt)))
            if lvl == 1:
                p0 = os.path.join(a.raw, seq[:-1] + '0', 'cam0', f'{st}.png')
                if os.path.exists(p0):
                    ref_level.append(float(thumb(rgb) @ thumb(cv2.imread(p0, cv2.IMREAD_COLOR))))
        print(f'{seq}: {sum(m["seq"] == seq for m in manifest)} frames')
    json.dump(dict(stride=a.stride, min_area=a.min_area, frames=manifest, instances=counts),
              open(os.path.join(a.out, 'manifest.json'), 'w'), indent=1)
    with open(os.path.join(a.out, 'data.yaml'), 'w') as fh:
        fh.write('# SAVIOR-Warehouse VIO-sequence test frames (make_vio_testset.py); val split = test_gray or test_rgb\n'
                 f'path: {a.out}\ntrain: images/test_gray\nval: images/test_gray\ntest_rgb: images/test_rgb\n'
                 'names:\n' + ''.join(f'  {k}: {n}\n' for k, n in enumerate(NAMES)))
    with open(os.path.join(a.out, 'data_rgb.yaml'), 'w') as fh:
        fh.write(f'path: {a.out}\ntrain: images/test_rgb\nval: images/test_rgb\nnames:\n' +
                 ''.join(f'  {k}: {n}\n' for k, n in enumerate(NAMES)))
    print('test instances', counts)

    # ---- leakage check against the training set
    T = np.stack(thumbs)
    tr_paths = sorted(glob.glob(os.path.join(a.segtrain, 'images', '*', '*.jpg')))
    S = np.stack([thumb(cv2.imread(p, cv2.IMREAD_COLOR)) for p in tr_paths])
    ncc = T @ S.T
    best = ncc.max(1)
    arg = ncc.argmax(1)
    worst = np.argsort(-best)[:10]
    res = dict(n_test=len(T), n_train=len(S),
               test_vs_train_max_ncc=dict(mean=float(best.mean()), p50=float(np.median(best)),
                                          p95=float(np.percentile(best, 95)), max=float(best.max())),
               ref_same_pose_L0_vs_L1=dict(mean=float(np.mean(ref_level)), p05=float(np.percentile(ref_level, 5)),
                                           min=float(np.min(ref_level))),
               ref_consecutive_frames=dict(mean=float(np.mean(ref_consec)), p05=float(np.percentile(ref_consec, 5)),
                                           min=float(np.min(ref_consec))),
               n_test_above_ref_p05=int((best >= min(np.percentile(ref_level, 5), np.percentile(ref_consec, 5))).sum()),
               top_matches=[dict(test=manifest[i]['name'], train=os.path.relpath(tr_paths[arg[i]], a.segtrain),
                                 ncc=float(best[i])) for i in worst])
    print(json.dumps(res, indent=1))
    if a.leak_json:
        os.makedirs(os.path.dirname(a.leak_json), exist_ok=True)
        json.dump(res, open(a.leak_json, 'w'), indent=1)
        # side-by-side of the closest pairs for visual inspection
        tiles = []
        for i in worst[:6]:
            t = cv2.imread(os.path.join(a.out, 'images', 'test_rgb', manifest[i]['name'] + '.png'))
            s = cv2.imread(tr_paths[arg[i]])
            tile = np.hstack([cv2.resize(t, (336, 188)), cv2.resize(s, (336, 188))])
            cv2.putText(tile, f'NCC {best[i]:.3f}', (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            tiles.append(tile)
        cv2.imwrite(a.leak_json.replace('.json', '_closest.jpg'), np.vstack(tiles))


if __name__ == '__main__':
    main()
