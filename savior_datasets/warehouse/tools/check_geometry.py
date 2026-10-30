#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render <-> calibration <-> GT consistency of a raw sequence (static pixels only):

1. stereo: warp cam1 into cam0 with the GT depth (d = fx * b / z) for disparity scale s and offset o; the
   photometric error must be minimal at s = 1, o = 0 (validates fx and the baseline);
2. temporal: back-project cam0 depth of frame k with the GT pose, re-project into cam0 of frame k+dk with its GT
   pose; the error must be minimal for the true pose (validates that frames were rendered at the GT camera poses,
   including the IMU->camera extrinsics), tested against +-1 cm / +-0.1 deg perturbations.

  python3 tools/check_geometry.py data/warehouse/raw/<seq> [--frames 10] [--json out.json]
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wh.se3 import quat_to_rot, so3_exp  # noqa: E402


def gray(p):
    return cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY).astype(np.float32)


def bilinear(img, u, v):
    u0, v0 = np.floor(u).astype(int), np.floor(v).astype(int)
    a, b = u - u0, v - v0
    return (img[v0, u0] * (1 - a) * (1 - b) + img[v0, u0 + 1] * a * (1 - b) + img[v0 + 1, u0] * (1 - a) * b
            + img[v0 + 1, u0 + 1] * a * b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seq')
    ap.add_argument('--frames', type=int, default=10)
    ap.add_argument('--dk', type=int, default=4)
    ap.add_argument('--json', default='')
    args = ap.parse_args()
    seq = args.seq
    rig = yaml.safe_load(open(os.path.join(seq, 'calib', 'rig.yaml')))
    c = rig['camera']
    fx, fy, cx, cy, b = (float(c[k]) for k in ('fx', 'fy', 'cx', 'cy', 'baseline'))
    frames = [ln.strip().split(',') for ln in open(os.path.join(seq, 'frames.csv')) if not ln.startswith('#')]
    gt = np.loadtxt(os.path.join(seq, 'gt_cam0_tum.txt'), comments='#')
    Rw = quat_to_rot(gt[:, [7, 4, 5, 6]])
    pw = gt[:, 1:4]
    moving = {}
    for ln in (open(os.path.join(seq, 'moving.csv')) if os.path.exists(os.path.join(seq, 'moving.csv')) else []):
        if not ln.startswith('#'):
            k, s, ids = ln.rstrip('\n').split(',', 2)
            moving[int(k)] = [int(v) for v in ids.split()]
    nr = sum(os.path.exists(os.path.join(seq, 'depth0', f'{f[1]}.png')) for f in frames)   # rendered so far
    ks = np.linspace(nr * 0.1, nr * 0.9 - args.dk, args.frames).astype(int)
    scales, offs = [0.97, 0.99, 1.0, 1.01, 1.03], [-1.0, -0.5, 0.0, 0.5, 1.0]
    E_s = np.zeros(len(scales))
    E_o = np.zeros(len(offs))
    perturb = [('true', np.zeros(3), np.zeros(3))] + [(f't{a}{"+" if sg > 0 else "-"}1cm', sg * 0.01 * np.eye(3)[i], np.zeros(3))
                                                      for i, a in enumerate('xyz') for sg in (-1, 1)] + \
              [(f'r{a}{"+" if sg > 0 else "-"}0.1deg', np.zeros(3), sg * np.deg2rad(0.1) * np.eye(3)[i]) for i, a in enumerate('xyz') for sg in (-1, 1)]
    E_t = np.zeros(len(perturb))
    H, W = int(c['height']), int(c['width'])
    uu, vv = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    for k in ks:
        st, st2 = frames[k][1], frames[k + args.dk][1]
        L, Rr = gray(os.path.join(seq, 'cam0', f'{st}.png')), gray(os.path.join(seq, 'cam1', f'{st}.png'))
        z = cv2.imread(os.path.join(seq, 'depth0', f'{st}.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 1000.0
        seg = cv2.imread(os.path.join(seq, 'seg0', f'{st}.png'), cv2.IMREAD_UNCHANGED)
        ok = (z > 0.3) & (z < 40) & ~np.isin(seg, moving.get(k, []))
        # texture mask (gradients), avoid flat areas dominating
        gx = cv2.Sobel(L, cv2.CV_32F, 1, 0)
        ok &= np.abs(gx) > 20
        for i, s in enumerate(scales):
            d = s * fx * b / np.maximum(z, 1e-3)
            w = cv2.remap(Rr, uu - d, vv, cv2.INTER_LINEAR)
            m = ok & (uu - d > 1)
            E_s[i] += np.mean(np.abs(w[m] - L[m]))
        for i, o in enumerate(offs):
            d = fx * b / np.maximum(z, 1e-3) + o
            w = cv2.remap(Rr, uu - d, vv, cv2.INTER_LINEAR)
            m = ok & (uu - d > 1)
            E_o[i] += np.mean(np.abs(w[m] - L[m]))
        # temporal
        L2 = gray(os.path.join(seq, 'cam0', f'{st2}.png'))
        P = np.stack([(uu - cx) / fx * z, (vv - cy) / fy * z, z], -1)[ok]
        Xw = P @ Rw[k].T + pw[k]
        for i, (_, dt_, dr) in enumerate(perturb):
            R2 = Rw[k + args.dk] @ so3_exp(dr)
            p2 = pw[k + args.dk] + Rw[k + args.dk] @ dt_
            Xc = (Xw - p2) @ R2
            u2, v2 = fx * Xc[:, 0] / Xc[:, 2] + cx, fy * Xc[:, 1] / Xc[:, 2] + cy
            m = (Xc[:, 2] > 0.2) & (u2 > 1) & (u2 < W - 2) & (v2 > 1) & (v2 < H - 2)
            I2 = bilinear(L2, u2[m], v2[m])
            E_t[i] += np.mean(np.abs(I2 - L[ok][m]))
    n = len(ks)
    res = dict(sequence=os.path.basename(os.path.normpath(seq)), frames=n,
               stereo_scale_err={str(s): float(e / n) for s, e in zip(scales, E_s)},
               stereo_offset_err={str(o): float(e / n) for o, e in zip(offs, E_o)},
               temporal_err={p[0]: float(e / n) for p, e in zip(perturb, E_t)})
    res['stereo_best_scale'] = scales[int(np.argmin(E_s))]
    res['stereo_best_offset_px'] = offs[int(np.argmin(E_o))]
    res['temporal_true_is_best'] = bool(np.argmin(E_t) == 0)
    print(json.dumps(res, indent=1))
    if args.json:
        json.dump(res, open(args.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
