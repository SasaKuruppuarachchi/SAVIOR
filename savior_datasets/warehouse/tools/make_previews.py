#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Preview PNGs per sequence: [cam0 | cam1] over [cam0 + class-colour seg overlay | moving-only mask], plus a
coverage-over-time strip.  python3 tools/make_previews.py data/warehouse/raw/<seq> [...] [--n 4]
Output: data/warehouse/preview/<seq>_fNNNNN.png and <seq>_coverage.png"""
import argparse
import csv
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wh.classes import COLOR, NAMES  # noqa: E402


def overlay(img, seg, lut, alpha=0.45):
    col = lut[np.minimum(seg, len(lut) - 1)]
    m = seg > 0
    out = img.copy()
    out[m] = (img[m] * (1 - alpha) + col[m][:, ::-1] * alpha).astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seqs', nargs='+')
    ap.add_argument('--n', type=int, default=4)
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    for seq in args.seqs:
        seq = os.path.abspath(seq)
        name = os.path.basename(seq)
        out = args.out or os.path.join(os.path.dirname(os.path.dirname(seq)), 'preview')
        os.makedirs(out, exist_ok=True)
        inst = json.load(open(os.path.join(seq, 'instances.json')))['instances']
        mx = max(i['id'] for i in inst) + 1
        lut = np.zeros((mx, 3), np.uint8)
        for i in inst:
            lut[i['id']] = COLOR[i['cls']]
        rows = list(csv.DictReader(open(os.path.join(seq, 'coverage.csv'))))
        cov = np.array([float(r['moving']) for r in rows])
        frames = [ln.strip().split(',') for ln in open(os.path.join(seq, 'frames.csv')) if not ln.startswith('#')]
        moving = {}
        for ln in open(os.path.join(seq, 'moving.csv')):
            if not ln.startswith('#'):
                k, s, ids = ln.rstrip('\n').split(',', 2)
                moving[int(k)] = [int(v) for v in ids.split()]
        n = len(frames)
        pick = list(np.linspace(n * 0.08, n * 0.92, args.n).astype(int))
        if cov.max() > 0:
            pick.append(int(np.argmax(cov)))
        for k in sorted(set(pick)):
            st = frames[k][1]
            c0 = cv2.imread(os.path.join(seq, 'cam0', f'{st}.png'))
            c1 = cv2.imread(os.path.join(seq, 'cam1', f'{st}.png'))
            s0 = cv2.imread(os.path.join(seq, 'seg0', f'{st}.png'), cv2.IMREAD_UNCHANGED)
            lm = np.zeros_like(lut)
            mv = [m for m in moving.get(k, []) if m < mx]
            lm[mv] = lut[mv]
            mov = overlay(c0, np.where(np.isin(s0, mv), s0, 0), lm, 0.6)
            for m_ in mv:
                cnt, _ = cv2.findContours((s0 == m_).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(mov, cnt, -1, (255, 255, 255), 1)
            top = np.concatenate([c0, c1], 1)
            bot = np.concatenate([overlay(c0, s0, lut), mov], 1)
            im = np.concatenate([top, bot], 0)
            txt = f'{name}  frame {k}  t={float(rows[k]["t"]):.2f}s  moving {cov[k]*100:.1f}%'
            cv2.putText(im, txt, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
            cv2.putText(im, txt, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            y = im.shape[0] // 2 + 18
            for j, cname in enumerate(NAMES):
                c = COLOR[cname][::-1]
                cv2.rectangle(im, (8 + 92 * j, y - 10), (18 + 92 * j, y), c, -1)
                cv2.putText(im, cname, (22 + 92 * j, y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
            cv2.imwrite(os.path.join(out, f'{name}_f{k:05d}.png'), im)
        # coverage strip
        W, H = 1000, 160
        g = np.full((H, W, 3), 255, np.uint8)
        t = np.array([float(r['t']) for r in rows])
        ymax = max(0.4, float(cov.max()))
        pts = np.c_[(t - t[0]) / max(t[-1] - t[0], 1e-6) * (W - 40) + 30, H - 20 - cov / ymax * (H - 40)].astype(np.int32)
        for yy in np.arange(0, ymax + 1e-9, 0.1):
            v = int(H - 20 - yy / ymax * (H - 40))
            cv2.line(g, (30, v), (W - 10, v), (220, 220, 220), 1)
            cv2.putText(g, f'{yy*100:.0f}%', (0, v + 4), 0, 0.35, (0, 0, 0), 1)
        cv2.polylines(g, [pts], False, (0, 0, 200), 1)
        cv2.putText(g, f'{name}: moving-object image coverage (mean {cov.mean()*100:.1f} %)', (35, 14), 0, 0.45, (0, 0, 0), 1)
        cv2.imwrite(os.path.join(out, f'{name}_coverage.png'), g)
        print(f'[previews] {name}: {len(set(pick))} frames -> {out}')


if __name__ == '__main__':
    main()
