"""YOLO26-seg on T265 fisheye: raw vs larger imgsz vs rectified (pinhole) view mapped back to raw.

Pseudo ground truth: union of yolo26x-seg @1280 on the RAW image and yolo26x-seg @1280 on a wide pinhole
view mapped back (greedy merge by mask IoU). Person recall / precision by radial distance from the principal point.
"""
import argparse
import json
import math
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
from savior_perception.core.calibration import StereoRectifier, load_kalibr_imucam_chain  # noqa: E402
from savior_perception.segmenters.yolo import YoloSegmenter  # noqa: E402
from perception_offline import read_stereo  # noqa: E402

CALIB = '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml'
M = '/home/sasa/workspace/savior_ws/models/'


class RectView:
    """Pinhole view of the left fisheye camera; masks are mapped back to raw with nearest lookup."""

    def __init__(self, focal_scale, size_scale):
        cams = load_kalibr_imucam_chain(CALIB)
        self.r = StereoRectifier(cams['cam0'], cams['cam1'], focal_scale=focal_scale, size_scale=size_scale)
        self.mx, self.my = self.r.rect_to_raw_x[0], self.r.rect_to_raw_y[0]
        rx, ry = self.r.raw_to_rect_x[0], self.r.raw_to_rect_y[0]
        rw, rh = self.r.rect_size
        self.valid = (rx > -1e3) & (rx >= 0) & (ry >= 0) & (rx <= rw - 1) & (ry <= rh - 1)
        self.rx = np.where(self.valid, np.rint(rx), 0).astype(np.int32)
        self.ry = np.where(self.valid, np.rint(ry), 0).astype(np.int32)

    def view(self, raw):
        return cv2.remap(raw, self.mx, self.my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def to_raw(self, mask_rect):
        return mask_rect[self.ry, self.rx] & self.valid


def persons(seg, img, view=None):
    if view is not None:
        out = []
        for inst in seg.predict(view.view(img)):
            m = view.to_raw(inst.mask)
            if m.sum() >= 30:
                out.append((m, inst.score))
        return out
    return [(i.mask, i.score) for i in seg.predict(img)]


def iou(a, b):
    i = np.count_nonzero(a & b)
    u = np.count_nonzero(a | b)
    return i / u if u else 0.0


def merge(sets, thr=0.5):
    out = []
    for s in sets:
        for m, sc in s:
            if all(iou(m, o[0]) < thr for o in out):
                out.append((m, sc))
    return out


def radius(m, cx, cy):
    ys, xs = np.nonzero(m)
    return math.hypot(xs.mean() - cx, ys.mean() - cy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bag', default='/home/sasa/workspace/savior_ws/data/openloris/ros2/cafe1-1')
    ap.add_argument('--every', type=int, default=15)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    K = load_kalibr_imucam_chain(CALIB)['cam0'].K
    cx, cy = K[0, 2], K[1, 2]
    views = {'rect_f0.5': RectView(0.5, 1.0), 'rect_f0.4': RectView(0.4, 1.0)}
    cands = {
        'n640': (YoloSegmenter(M + 'yolo26n-seg.engine', classes=['person'], imgsz=640), None),
        's640': (YoloSegmenter(M + 'yolo26s-seg.engine', classes=['person'], imgsz=640), None),
        'n960': (YoloSegmenter(M + 'yolo26n-seg-960.engine', classes=['person'], imgsz=960), None),
        's960': (YoloSegmenter(M + 'yolo26s-seg-960.engine', classes=['person'], imgsz=960), None),
        'n640_rect0.5': (YoloSegmenter(M + 'yolo26n-seg.engine', classes=['person'], imgsz=640), views['rect_f0.5']),
        's640_rect0.5': (YoloSegmenter(M + 'yolo26s-seg.engine', classes=['person'], imgsz=640), views['rect_f0.5']),
    }
    ref_seg = YoloSegmenter(M + 'yolo26x-seg.pt', classes=['person'], imgsz=1280, half=True, device='0')
    shape = (800, 848)
    for seg, v in list(cands.values()) + [(ref_seg, None)]:
        seg.warmup(shape)
        seg.warmup(shape)
    res = {k: {'tp': [], 'fp': [], 't': [], 'iou': [], 'cov': [0, 0], 'area': []} for k in cands}
    ref_r = []
    n = 0
    for i, (st, left, right) in enumerate(read_stereo(a.bag, '/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw')):
        if i % a.every:
            continue
        n += 1
        ref = merge([persons(ref_seg, left), persons(ref_seg, left, views['rect_f0.5']),
                     persons(ref_seg, left, views['rect_f0.4'])])
        ref = [r for r in ref if r[1] >= 0.4]
        rr = [radius(m, cx, cy) for m, _ in ref]
        ref_r += rr
        for k, (seg, v) in cands.items():
            t0 = time.perf_counter()
            det = persons(seg, left, v)
            res[k]['t'].append((time.perf_counter() - t0) * 1e3)
            used = set()
            if ref:
                ref_u = np.logical_or.reduce([m for m, _ in ref])
                det_u = np.logical_or.reduce([m for m, _ in det]) if det else np.zeros_like(ref_u)
                res[k]['cov'][0] += int(np.count_nonzero(ref_u & det_u))
                res[k]['cov'][1] += int(np.count_nonzero(ref_u))
            for j, (m, _) in enumerate(ref):
                best, bi = 0.0, -1
                for di, (dm, _) in enumerate(det):
                    if di in used:
                        continue
                    x = iou(m, dm)
                    if x > best:
                        best, bi = x, di
                ok = best >= 0.5
                if ok:
                    used.add(bi)
                    res[k]['iou'].append(best)
                res[k]['tp'].append((rr[j], int(ok)))
                res[k]['area'].append((int(m.sum()), int(ok)))
            for di, (dm, _) in enumerate(det):
                if di not in used:
                    res[k]['fp'].append(radius(dm, cx, cy))
    bins = [(0, 200), (200, 300), (300, 1000)]
    summary = {'frames': n, 'ref_persons': len(ref_r),
               'ref_by_area': {},
               'ref_by_radius': {f'{lo}-{hi}': int(sum(lo <= r < hi for r in ref_r)) for lo, hi in bins}}
    for k, d in res.items():
        tp = np.array(d['tp']) if d['tp'] else np.zeros((0, 2))
        row = {'recall': round(float(tp[:, 1].mean()), 3) if len(tp) else None,
               'fp_per_frame': round(len(d['fp']) / n, 3),
               'mask_iou_matched': round(float(np.mean(d['iou'])), 3) if d['iou'] else None,
               'ms_median': round(float(np.median(d['t'])), 2), 'ms_p90': round(float(np.percentile(d['t'], 90)), 2)}
        row['person_px_coverage'] = round(d['cov'][0] / max(1, d['cov'][1]), 3)
        ar = np.array(d['area'])
        for lo, hi in [(0, 1000), (1000, 5000), (5000, 10**7)]:
            sel = (ar[:, 0] >= lo) & (ar[:, 0] < hi)
            row[f'recall_area{lo}-{hi}'] = round(float(ar[sel, 1].mean()), 3) if sel.any() else None
        for lo, hi in bins:
            sel = (tp[:, 0] >= lo) & (tp[:, 0] < hi) if len(tp) else np.zeros(0, bool)
            row[f'recall_r{lo}-{hi}'] = round(float(tp[sel, 1].mean()), 3) if sel.any() else None
        summary[k] = row
    with open(a.out, 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
