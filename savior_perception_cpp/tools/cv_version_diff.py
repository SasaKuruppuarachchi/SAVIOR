#!/usr/bin/env python3
"""cv_version_diff.py --out <json> [--seqs a,b] [--frames N]: which OpenCV primitives of the pipeline give different results in
the C++ build's OpenCV (savior_cpp.cvops) and in the Python node's cv2 (opencv-python-headless 4.11.0.86, IPP-ICV), on real t1
frames and cached detections, called with exactly the pipeline's arguments:
  resize INTER_AREA (KLT half-res image), goodFeaturesToTrack (background: 150 / 0.01 / 8 / bs 5 with box mask; instance crops:
  25 / 0.01 / 3 / bs 5), calcOpticalFlowPyrLK (11x11, 2 levels, 20 it / 0.03), StereoSGBM 3-way (half-res ROI, 80 disp, bs 5),
  findContours (EXTERNAL, NONE) on instance masks, fillPoly of identical polygons, erode 3x3 (2 it) and elliptic dilate (r 4).
TUNING SET (t1) ONLY."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from equiv_offline import DetCache, SCR, WS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seqs', default='hall_t1_L3,aisles_t1_L3')
    ap.add_argument('--frames', type=int, default=120)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    import savior_cpp
    from rosbags.highlevel import AnyReader
    cv2.setNumThreads(a.threads)
    savior_cpp.set_num_threads(a.threads)
    C = savior_cpp.cvops
    res = {}

    def add(op, same, n=1, extra=None):
        r = res.setdefault(op, {'calls': 0, 'identical': 0, 'units': 0, 'units_diff': 0, 'max_abs': 0.0})
        r['calls'] += 1
        r['identical'] += int(same)
        if extra:
            u, ud, mx = extra
            r['units'] += u
            r['units_diff'] += ud
            r['max_abs'] = max(r['max_abs'], float(mx))

    for seq in a.seqs.split(','):
        assert '_t1_' in seq
        dets = DetCache(f'{SCR}/detcache/{seq}.npz')
        frames = {}
        with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
            conns = [c for c in r.connections if c.topic in ('/cam0/image_raw', '/cam1/image_raw')]
            for c, _, raw in r.messages(connections=conns):
                m = r.deserialize(raw, c.msgtype)
                st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
                if len(frames) > a.frames * 8 + 2:
                    break
        stamps = sorted(s for s in frames if frames[s][0] is not None and frames[s][1] is not None)[::8][:a.frames]
        prev = None
        for st in stamps:
            L, R = frames[st]
            hp = cv2.resize(L, (336, 188), interpolation=cv2.INTER_AREA)
            hc = C.resize_area(L, 336, 188)
            d = np.abs(hp.astype(int) - hc.astype(int))
            add('resize INTER_AREA', np.array_equal(hp, hc), extra=(d.size, int(np.count_nonzero(d)), d.max()))
            insts = dets.get(st)
            mbg = np.full(hp.shape, 255, np.uint8)
            for crop, cls, sc, (x0, y0, x1, y1) in insts:
                mbg[int(y0 * .5):int(np.ceil(y1 * .5)), int(x0 * .5):int(np.ceil(x1 * .5))] = 0
            gp = cv2.goodFeaturesToTrack(hp, maxCorners=150, qualityLevel=0.01, minDistance=8, mask=mbg, blockSize=5)
            gp = np.zeros((0, 2), np.float32) if gp is None else gp.reshape(-1, 2)
            gc = C.gftt(hp, 150, 0.01, 8, mbg, 5)
            add('goodFeaturesToTrack (background)', gp.shape == gc.shape and np.array_equal(gp, gc),
                extra=(len(gp), len(set(map(tuple, gp.tolist())) ^ set(map(tuple, gc.tolist()))), 0))
            for crop, cls, sc, (x0, y0, x1, y1) in insts[:20]:
                sx0, sy0, sx1, sy1 = int(np.floor(x0 * .5)), int(np.floor(y0 * .5)), min(336, int(np.ceil(x1 * .5))), min(188, int(np.ceil(y1 * .5)))
                if sx1 - sx0 < 4 or sy1 - sy0 < 4:
                    continue
                m = cv2.resize(crop.astype(np.uint8), (sx1 - sx0, sy1 - sy0), interpolation=cv2.INTER_NEAREST)
                m = cv2.erode(m, np.ones((7, 7), np.uint8))
                if not m.any():
                    continue
                sub = np.ascontiguousarray(hp[sy0:sy1, sx0:sx1])
                ip = cv2.goodFeaturesToTrack(sub, maxCorners=25, qualityLevel=0.01, minDistance=3, mask=m * 255, blockSize=5)
                ip = np.zeros((0, 2), np.float32) if ip is None else ip.reshape(-1, 2)
                ic = C.gftt(sub, 25, 0.01, 3, m * 255, 5)
                add('goodFeaturesToTrack (instance crop)', ip.shape == ic.shape and np.array_equal(ip, ic),
                    extra=(len(ip), len(set(map(tuple, ip.tolist())) ^ set(map(tuple, ic.tolist()))), 0))
                full = np.zeros(L.shape, np.uint8)
                full[y0:y1, x0:x1] = crop
                e_p = cv2.erode(full[y0:y1, x0:x1].copy(), np.ones((3, 3), np.uint8), iterations=2)
                e_c = C.erode3(full[y0:y1, x0:x1].copy(), 2)
                add('erode 3x3 x2', np.array_equal(e_p, e_c))
                k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
                add('dilate ellipse r4', np.array_equal(cv2.dilate(crop.astype(np.uint8), k), C.dilate_ell(crop.astype(np.uint8), 4)))
                cp_, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cc_ = C.contours(full)
                same = len(cp_) == len(cc_) and all(np.array_equal(x.reshape(-1, 2), y) for x, y in zip(cp_, cc_))
                add('findContours EXTERNAL/NONE', same, extra=(sum(len(x) for x in cp_), 0 if same else 1, 0))
                polys = [x.reshape(-1, 2).astype(np.int32) for x in cp_ if len(x) >= 3]
                fp = np.zeros(L.shape, np.uint8)
                for pg in polys:
                    cv2.fillPoly(fp, [pg.reshape(-1, 1, 2)], 255)
                fc = C.fillpoly(L.shape[0], L.shape[1], polys, 255)
                dd = fp != fc
                add('fillPoly (same polygons)', not dd.any(), extra=(int(fp.size), int(dd.sum()), 0))
            if prev is not None and len(gp):
                p0 = gp.astype(np.float32).reshape(-1, 1, 2)
                q1, s1, _ = cv2.calcOpticalFlowPyrLK(prev, hp, p0, None, winSize=(11, 11), maxLevel=2,
                                                     criteria=(cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, 0.03))
                q2, s2 = C.lk(prev, hp, gp.astype(np.float32), 11, 2)
                q1 = q1.reshape(-1, 2)
                ok = (s1.reshape(-1) == 1) & (s2 == 1)
                dmax = float(np.abs(q1[ok] - q2[ok]).max()) if ok.any() else 0.0
                add('calcOpticalFlowPyrLK', np.array_equal(q1, q2) and np.array_equal(s1.reshape(-1), s2),
                    extra=(len(q1), int(np.count_nonzero((np.abs(q1 - q2) > 0).any(axis=1))), dmax))
            prev = hp
            Lh, Rh = np.ascontiguousarray(L[::2, ::2]), np.ascontiguousarray(R[::2, ::2])
            for (x0, y0, x1, y1) in [b[3] for b in insts[:6]]:
                u0, u1 = max(0, x0 // 2 - 80), min(336, max(x1 // 2 + 2, x0 // 2 - 80 + 80 + 6))
                v0, v1 = y0 // 2, min(188, max(y1 // 2, y0 // 2 + 8))
                if u1 - u0 < 86 or v1 - v0 < 7:
                    continue
                lc, rc = np.ascontiguousarray(Lh[v0:v1, u0:u1]), np.ascontiguousarray(Rh[v0:v1, u0:u1])
                m = cv2.StereoSGBM_create(minDisparity=0, numDisparities=80, blockSize=5, P1=200, P2=800, disp12MaxDiff=1,
                                          uniquenessRatio=10, speckleWindowSize=50, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
                dp = m.compute(lc, rc)
                dc = C.sgbm(lc, rc, 80, 5)
                dd = dp != dc
                add('StereoSGBM 3-way', not dd.any(), extra=(int(dp.size), int(dd.sum()), int(np.abs(dp.astype(int) - dc.astype(int)).max())))
    out = {'opencv_py': cv2.__version__, 'opencv_cpp': savior_cpp.opencv_version, 'ops': res}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    for k, v in res.items():
        print(f"{k:38s} calls {v['calls']:5d} identical {v['identical']:5d}  units {v['units']} diff {v['units_diff']} max {v['max_abs']}")


if __name__ == '__main__':
    main()
