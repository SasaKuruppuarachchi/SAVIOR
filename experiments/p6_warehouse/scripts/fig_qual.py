#!/usr/bin/env python3
"""Qualitative overlays for L2/L3 frames saved by offline_eval_wh.py --save-stamps (offline/qual/*.npz):
raw | oracle moving (GT) | oracle class naive (GT) | yolo_naive | yolo_p4 | yolo_p6. Red = core 255, yellow = band 192;
GT panels: red = moving, blue = static potential class (what naive masking removes)."""
import glob
import os
import re

import sys

import cv2
import numpy as np

sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/p6_warehouse/scripts')
from wh_gt import SeqGT  # noqa: E402

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
Q = R + '/offline/qual'
OUT = R + '/figures'
PANELS = [('raw', None), ('GT moving / static-potential', 'gt'), ('oracle_class_naive', 'oracle_class_naive_warp'),
          ('yolo_naive', 'yolo_naive'), ('yolo_p4', 'yolo_p4'), ('yolo_p6', 'yolo_p6')]


def tint(gray, ml=None, gt=None):
    b = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    t = b.copy()
    if gt is not None:
        t[(gt >= 1) & (gt <= 5)] = (255, 120, 0)
        t[gt >= 11] = (0, 0, 255)
    if ml is not None:
        t[ml == 192] = (0, 220, 255)
        t[ml == 255] = (0, 0, 255)
    return cv2.addWeighted(b, 0.5, t, 0.5, 0)


keys = sorted({re.sub(r'_(yolo|oracle).*\.npz$', '', os.path.basename(f)) for f in glob.glob(Q + '/*.npz')})
for k in keys:
    rows = []
    base = None
    tiles = []
    for title, v in PANELS:
        if v in (None, 'gt'):
            fn = glob.glob(f'{Q}/{k}_yolo_naive.npz')
        else:
            fn = glob.glob(f'{Q}/{k}_{v}.npz')
        if not fn:
            continue
        z = np.load(fn[0])
        img = z['left']
        if title == 'raw':
            im = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif v == 'gt':
            sq, sn = k.rsplit('_', 1)
            im = tint(img, gt=SeqGT(sq).category_image(0, int(sn)))   # (npz gt0 lacks the moving offset)
        else:
            im = tint(img, ml=z['ml'])
            core = 100 * (z['ml'] == 255).mean()
            title = f'{title}  core {core:.0f} %'
        cv2.putText(im, title, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(im)
    if len(tiles) < 2:
        continue
    while len(tiles) % 3:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)])
    seq, st = k.rsplit('_', 1)
    cv2.putText(grid, f'{seq}  t = {(int(st) - 1700000000000000000) * 1e-9:.2f} s', (6, grid.shape[0] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(f'{OUT}/qual_{k}.png', grid)
    print('wrote', f'{OUT}/qual_{k}.png')
