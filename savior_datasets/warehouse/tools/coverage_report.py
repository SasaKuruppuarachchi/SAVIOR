#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coverage / visibility table over raw sequences: python3 tools/coverage_report.py data/warehouse/raw/* [--csv out.csv]

Per sequence: duration, frames, path length, moving-object image coverage (mean / median / p90 / max), share of
frames with > 5 / 10 / 20 % moving coverage, longest continuous run above 5 %, mean person coverage (moving or not),
number of instances that move, per moving instance the longest continuous visibility while moving (median / max), and
the share of OpenVINS-like FAST features (thr 20, 150 points on a 5x5 grid; every 5th frame) on moving objects
(mean, and fraction of frames where it exceeds 10 %).
"""
import argparse
import csv
import json
import os

import numpy as np


def fast_share(gray, movmask, n_pts=150, grid=5, thr=20):
    """Share of OpenVINS-like features (FAST thr 20, best n_pts/grid^2 per cell of a 5x5 grid) on moving pixels."""
    import cv2
    det = cv2.FastFeatureDetector_create(thr, True)
    H, W = gray.shape
    per = max(n_pts // (grid * grid), 1)
    tot = mov = 0
    for gy in range(grid):
        for gx in range(grid):
            y0, y1, x0, x1 = gy * H // grid, (gy + 1) * H // grid, gx * W // grid, (gx + 1) * W // grid
            kps = sorted(det.detect(gray[y0:y1, x0:x1]), key=lambda k: -k.response)[:per]
            for k in kps:
                tot += 1
                mov += bool(movmask[y0 + int(k.pt[1]), x0 + int(k.pt[0])])
    return mov / max(tot, 1)


def runs(mask, dt):
    best, cur = 0, 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best * dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seqs', nargs='+')
    ap.add_argument('--csv', default='')
    args = ap.parse_args()
    out = []
    for seq in sorted(args.seqs):
        if not os.path.exists(os.path.join(seq, 'coverage.csv')):
            continue
        meta = json.load(open(os.path.join(seq, 'meta.json')))
        rows = list(csv.DictReader(open(os.path.join(seq, 'coverage.csv'))))
        cov = np.array([float(r['moving']) for r in rows])
        per = np.array([float(r['person']) for r in rows])
        inst = json.load(open(os.path.join(seq, 'instances.json')))['instances']
        movers = [i for i in inst if i['moving_ever']]
        dt = 1.0 / 20.0
        # visibility of each moving instance while moving: from moving.csv + frames where it is visible (seg0)
        vis_runs, feat = [], []
        if movers:
            import cv2
            frames = [ln.strip().split(',') for ln in open(os.path.join(seq, 'frames.csv')) if not ln.startswith('#')]
            mov = {}
            for ln in open(os.path.join(seq, 'moving.csv')):
                if not ln.startswith('#'):
                    k, s, ids = ln.rstrip('\n').split(',', 2)
                    mov[int(k)] = set(int(v) for v in ids.split())
            ids = [i['id'] for i in movers]
            vis = {i: [] for i in ids}
            for k in range(0, len(frames)):
                s0 = cv2.imread(os.path.join(seq, 'seg0', f'{frames[k][1]}.png'), cv2.IMREAD_UNCHANGED)
                cnt = np.bincount(s0.ravel(), minlength=max(ids) + 1)
                for i in ids:
                    vis[i].append(cnt[i] >= 100 and i in mov.get(k, ()))
                if k % 5 == 0:
                    g = cv2.imread(os.path.join(seq, 'cam0', f'{frames[k][1]}.png'), cv2.IMREAD_GRAYSCALE)
                    feat.append(fast_share(g, np.isin(s0, list(mov.get(k, ())))))
            vis_runs = [runs(v, dt) for v in vis.values() if any(v)]
        r = dict(sequence=meta['sequence'], duration_s=round(meta['duration_s'], 1), frames=meta['frames'],
                 path_m=round(meta['path_length_m'], 1), cov_mean=cov.mean(), cov_median=float(np.median(cov)),
                 cov_p90=float(np.percentile(cov, 90)), cov_max=float(cov.max()), frac_gt5=float(np.mean(cov > 0.05)),
                 frac_gt10=float(np.mean(cov > 0.10)), frac_gt20=float(np.mean(cov > 0.20)),
                 longest_gt5_s=runs(cov > 0.05, dt), person_cov_mean=float(per.mean()), moving_instances=len(movers),
                 vis_run_median_s=float(np.median(vis_runs)) if vis_runs else 0.0,
                 vis_run_max_s=float(np.max(vis_runs)) if vis_runs else 0.0, render_fps=round(meta['fps'], 2),
                 feat_share_mean=float(np.mean(feat)) if feat else 0.0,
                 feat_frames_gt10=float(np.mean(np.array(feat) > 0.10)) if feat else 0.0)
        out.append(r)
    hdr = ['sequence', 'duration_s', 'frames', 'path_m', 'cov_mean', 'cov_median', 'cov_p90', 'cov_max', 'frac_gt5',
           'frac_gt10', 'frac_gt20', 'longest_gt5_s', 'person_cov_mean', 'moving_instances', 'vis_run_median_s',
           'vis_run_max_s', 'feat_share_mean', 'feat_frames_gt10', 'render_fps']
    pct = {'cov_mean', 'cov_median', 'cov_p90', 'cov_max', 'frac_gt5', 'frac_gt10', 'frac_gt20', 'person_cov_mean',
           'feat_share_mean', 'feat_frames_gt10'}
    print('| ' + ' | '.join(hdr) + ' |')
    print('|' + '---|' * len(hdr))
    for r in out:
        print('| ' + ' | '.join(f'{r[h]*100:.1f}' if h in pct else (f'{r[h]:.1f}' if isinstance(r[h], float) else str(r[h]))
                                for h in hdr) + ' |')
    if args.csv:
        with open(args.csv, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(out)


if __name__ == '__main__':
    main()
