#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mask-level evaluation of a YOLO-seg model (.pt or TensorRT .engine) on SAVIOR-Warehouse, as savior_node uses it.

GT sources
  --set vio_gray | vio_rgb   VIO-sequence test frames (make_vio_testset.py): exact uint16 seg0 instance masks,
                             instances.json classes, moving.csv flags
  --set val | val_gray       segmentation val split (yolo_inst labels rasterised with cv2.fillPoly, like Ultralytics)
Predictions: Ultralytics predict, imgsz 672 rect (672x384 letterbox; engines use their export shape), retina masks,
conf 0.001 / max_det 300 for AP, the deployed conf (0.25) for everything else.

Metrics (per class)
  * mask AP50 / AP50-95 (COCO-style greedy matching, 101-pt interpolation; GT < 40 px = ignore regions)
  * semantic mask IoU: sum_i |P_c ∩ G_c| / sum_i |P_c ∪ G_c| (P_c / G_c = union of the class' masks, all GT sizes)
  * instance recall vs GT area (IoU >= 0.5, conf >= 0.25), split moving / not moving (VIO set)
  * false positives at conf >= 0.25, by where they land: static structure (rack / guard_rail / window) or
    unlabelled background (walls, floor, ceiling), another class, or a same-class duplicate / poor localisation
  * pixel confusion (highest-score prediction per pixel) for static-GT pixels -> fraction covered by
    dynamic / potential predictions (= features SAVIOR would mask on static structure)
`--coco-person` evaluates a COCO-80 model restricted to class 0 (person) against the person GT only.

  python3 eval_seg.py --model models/warehouse/yolo26s-seg-warehouse.pt --set vio_gray --out results/.../x.json
"""
import argparse
import glob
import json
import os
import time
from collections import defaultdict

import cv2
import numpy as np
import torch

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
NAMES = ['rack', 'guard_rail', 'window', 'forklift', 'box', 'pallet', 'trolley', 'person']
STATIC = {0, 1, 2}
DYNPOT = {3, 4, 5, 6, 7}
SIZE_BINS = [40, 256, 1024, 4096, 16384, 10 ** 9]
SIZE_LABELS = ['40-256', '256-1k', '1k-4k', '4k-16k', '>16k']
IOU_T = np.linspace(0.5, 0.95, 10)
TEST = f'{WS}/data/warehouse/seg_test_vio'
VAL = f'{WS}/data/warehouse/seg_train/yolo_inst'


# ---------------------------------------------------------------- ground truth
class SeqGT:
    def __init__(self):
        self.cls_cache = {}

    def load(self, fr):
        if fr['instances'] not in self.cls_cache:
            inst = json.load(open(fr['instances']))['instances']
            self.cls_cache[fr['instances']] = {i['id']: i['cls'] for i in inst}
        cls_of = self.cls_cache[fr['instances']]
        seg = cv2.imread(fr['seg'], cv2.IMREAD_UNCHANGED)
        moving = set(fr['moving'])
        sem = np.zeros(seg.shape, np.uint8)            # 0 = background / unlabelled, k + 1 = class k
        gts = []
        for i, c in zip(*np.unique(seg, return_counts=True)):
            cl = cls_of.get(int(i))
            if i == 0 or cl not in NAMES:
                continue
            m = seg == i
            k = NAMES.index(cl)
            sem[m] = k + 1
            gts.append(dict(mask=m, cls=k, area=int(c), moving=int(i) in moving, ignore=c < 40))
        return sem, gts


def load_yolo_gt(label_path, H, W):
    gts = []
    if os.path.exists(label_path):
        for line in open(label_path):
            v = line.split()
            if len(v) < 7:
                continue
            p = (np.array(v[1:], np.float64).reshape(-1, 2) * (W, H))
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [np.round(p).astype(np.int32)], 1)
            m = m.astype(bool)
            gts.append(dict(mask=m, cls=int(v[0]), area=int(m.sum()), moving=False, ignore=m.sum() < 40))
    sem = np.zeros((H, W), np.uint8)
    for g in sorted(gts, key=lambda g: -g['area']):    # smaller drawn on top (Ultralytics overlap order)
        sem[g['mask']] = g['cls'] + 1
    return sem, gts


def frames_for(set_name):
    if set_name.startswith('vio'):
        man = json.load(open(f'{TEST}/manifest.json'))['frames']
        var = 'test_gray' if set_name == 'vio_gray' else 'test_rgb'
        return [dict(fr, image=f'{TEST}/images/{var}/{fr["name"]}.png') for fr in man]
    out = []
    for p in sorted(glob.glob(f'{VAL}/images/val/*.jpg')):
        b = os.path.splitext(os.path.basename(p))[0]
        out.append(dict(name=b, image=p, label=f'{VAL}/labels/val/{b}.txt', gray=set_name == 'val_gray'))
    return out


# ---------------------------------------------------------------- matching helpers
def iou_matrix(pm, gm):
    """pm (P,H,W) bool torch, gm (G,H,W) bool torch -> (P,G) IoU."""
    if pm.shape[0] == 0 or gm.shape[0] == 0:
        return torch.zeros((pm.shape[0], gm.shape[0]), device=pm.device)
    p = pm.reshape(pm.shape[0], -1).half()
    g = gm.reshape(gm.shape[0], -1).half()
    inter = (p @ g.T).float()
    union = p.float().sum(1, keepdim=True) + g.float().sum(1)[None] - inter
    return inter / union.clamp(min=1)


def ap_from(scores, tps, n_gt):
    """COCO 101-point AP for one IoU threshold."""
    if n_gt == 0:
        return float('nan')
    if len(scores) == 0:
        return 0.0
    o = np.argsort(-np.asarray(scores), kind='mergesort')
    tp = np.asarray(tps, float)[o]
    ctp, cfp = np.cumsum(tp), np.cumsum(1 - tp)
    rec = ctp / n_gt
    prec = ctp / np.maximum(ctp + cfp, 1e-9)
    prec = np.maximum.accumulate(prec[::-1])[::-1]
    rs = np.linspace(0, 1, 101)
    idx = np.searchsorted(rec, rs, side='left')
    return float(np.mean([prec[i] if i < len(prec) else 0.0 for i in idx]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--set', default='vio_gray', choices=['vio_gray', 'vio_rgb', 'val', 'val_gray'])
    ap.add_argument('--imgsz', type=int, default=672)
    ap.add_argument('--conf', type=float, default=0.25, help='deployed confidence (savior segmenter.conf)')
    ap.add_argument('--coco-person', action='store_true')
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--seqs', default='', help='comma separated sequence filter (VIO set)')
    ap.add_argument('--out', default='')
    a = ap.parse_args()

    from ultralytics import YOLO
    model = YOLO(a.model, task='segment')
    names = model.names
    if a.coco_person:
        pred_cls = {0: NAMES.index('person')}
        classes = [0]
        eval_classes = [NAMES.index('person')]
    else:
        assert [names[i] for i in range(len(names))] == NAMES, names
        pred_cls = {i: i for i in range(8)}
        classes = None
        eval_classes = list(range(8))
    dev = 'cuda'
    frames = frames_for(a.set)
    if a.seqs:
        frames = [f for f in frames if f.get('seq') in a.seqs.split(',')]
    if a.max_frames:
        frames = frames[:a.max_frames]
    seq_gt = SeqGT()

    ap_rec = {c: dict(scores=[], tps=[], n_gt=0) for c in eval_classes}
    inter = defaultdict(int)
    union = defaultdict(int)
    recall_rows = []          # (cls, area, moving, matched)
    fp = defaultdict(lambda: defaultdict(int))
    tp_count = defaultdict(int)
    conf_px = np.zeros((9, 9), np.int64)     # GT (0 = bg, k + 1) x predicted (0 = none, k + 1)
    t_pred = []
    n_frames = 0
    for fr in frames:
        img = cv2.imread(fr['image'], cv2.IMREAD_COLOR)
        H, W = img.shape[:2]
        if fr.get('gray'):
            img = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        if a.set.startswith('vio'):
            sem, gts = seq_gt.load(fr)
        else:
            sem, gts = load_yolo_gt(fr['label'], H, W)
        if a.coco_person:
            gts = [g for g in gts if g['cls'] == NAMES.index('person')]
        t0 = time.perf_counter()
        r = model.predict(img, conf=0.001, iou=0.7, imgsz=a.imgsz, retina_masks=True, max_det=300,
                          classes=classes, verbose=False)[0]
        t_pred.append(time.perf_counter() - t0)
        if r.masks is not None and len(r.boxes):
            pm = r.masks.data.to(dev) > 0.5
            if pm.shape[1:] != (H, W):
                pm = torch.nn.functional.interpolate(pm[None].float(), (H, W), mode='nearest')[0] > 0.5
            pc = np.array([pred_cls[int(c)] for c in r.boxes.cls.cpu().numpy()])
            ps = r.boxes.conf.cpu().numpy()
        else:
            pm = torch.zeros((0, H, W), dtype=torch.bool, device=dev)
            pc, ps = np.zeros(0, int), np.zeros(0)
        gm = torch.from_numpy(np.stack([g['mask'] for g in gts])).to(dev) if gts else \
            torch.zeros((0, H, W), dtype=torch.bool, device=dev)
        gc = np.array([g['cls'] for g in gts], int)
        gign = np.array([g['ignore'] for g in gts], bool)
        IoU = iou_matrix(pm, gm).cpu().numpy()
        n_frames += 1

        # ---- AP (all scores)
        for c in eval_classes:
            pi = np.flatnonzero(pc == c)
            gi = np.flatnonzero(gc == c)
            gi_valid = gi[~gign[gi]]
            ap_rec[c]['n_gt'] += len(gi_valid)
            pi = pi[np.argsort(-ps[pi])]
            matched = np.zeros((len(IOU_T), len(gi)), bool)
            for p in pi:
                row = np.zeros(len(IOU_T), bool)
                drop = False
                for t_i, t in enumerate(IOU_T):
                    best, bj = t, -1
                    for jj, g in enumerate(gi):
                        if matched[t_i, jj] or gign[g]:
                            continue
                        if IoU[p, g] >= best:
                            best, bj = IoU[p, g], jj
                    if bj >= 0:
                        matched[t_i, bj] = True
                        row[t_i] = True
                    elif t_i == 0 and len(gi) and gign[gi].any() and IoU[p, gi[gign[gi]]].max() >= 0.5:
                        drop = True         # matches an ignored (tiny) GT: neither TP nor FP
                        break
                if not drop:
                    ap_rec[c]['scores'].append(float(ps[p]))
                    ap_rec[c]['tps'].append(row)

        # ---- deployed-confidence metrics
        keep = ps >= a.conf
        pmk, pck, psk = pm[keep], pc[keep], ps[keep]
        IoUk = IoU[keep]
        for c in eval_classes:
            P = pmk[torch.from_numpy(pck == c).to(dev)].any(0) if (pck == c).any() else torch.zeros((H, W), dtype=torch.bool, device=dev)
            G = torch.from_numpy(sem == c + 1).to(dev)
            inter[c] += int((P & G).sum())
            union[c] += int((P | G).sum())
        # instance recall (greedy by score, IoU >= 0.5, same class)
        order = np.argsort(-psk)
        g_matched = np.zeros(len(gts), bool)
        p_matched = np.zeros(len(psk), bool)
        for p in order:
            cand = [j for j in range(len(gts)) if gc[j] == pck[p] and not g_matched[j] and IoUk[p, j] >= 0.5]
            if cand:
                j = max(cand, key=lambda j: IoUk[p, j])
                g_matched[j] = True
                p_matched[p] = True
        for j, g in enumerate(gts):
            if not g['ignore'] and g['cls'] in eval_classes:
                recall_rows.append((g['cls'], g['area'], g['moving'], bool(g_matched[j])))
        # false positives: where do the unmatched predictions land?
        for p in np.flatnonzero(~p_matched):
            c = int(pck[p])
            if len(gts) and gign[gc == c].any() and IoUk[p, (gc == c) & gign].max() >= 0.5:
                continue
            m = pmk[p].cpu().numpy()
            area = max(1, int(m.sum()))
            g = sem[m]
            f_static = np.isin(g, [k + 1 for k in STATIC]).sum() / area
            f_bg = (g == 0).sum() / area
            f_same = (g == c + 1).sum() / area
            if f_static + f_bg >= 0.5:
                key = 'static_structure' if f_static >= f_bg else 'background'
            elif f_same >= 0.5:
                key = 'same_class_dup_or_loc'
            else:
                key = 'other_class'
            fp[c][key] += 1
            fp[c]['px_on_static_or_bg'] += int((f_static + f_bg) * area)
        for p in np.flatnonzero(p_matched):
            tp_count[int(pck[p])] += 1
        # pixel confusion: paint predictions in ascending score (highest wins)
        pred_sem = np.zeros((H, W), np.uint8)
        if len(psk):
            pmk_np = pmk.cpu().numpy()
            for p in np.argsort(psk):
                pred_sem[pmk_np[p]] = pck[p] + 1
        conf_px += np.bincount(sem.astype(np.int64).ravel() * 9 + pred_sem.ravel(), minlength=81).reshape(9, 9)

    # ---------------------------------------------------------------- summarise
    res = dict(model=a.model, set=a.set, frames=n_frames, conf=a.conf, imgsz=a.imgsz,
               predict_ms_median=float(np.median(t_pred) * 1e3), per_class={})
    for c in eval_classes:
        R = ap_rec[c]
        tps = np.array(R['tps']).reshape(-1, len(IOU_T))
        aps = [ap_from(R['scores'], tps[:, i] if len(tps) else [], R['n_gt']) for i in range(len(IOU_T))]
        rows = [r for r in recall_rows if r[0] == c]
        rec_bins = {}
        for lo, hi, lab in zip(SIZE_BINS[:-1], SIZE_BINS[1:], SIZE_LABELS):
            sel = [r[3] for r in rows if lo <= r[1] < hi]
            rec_bins[lab] = [float(np.mean(sel)) if sel else None, len(sel)]
        mov = [r[3] for r in rows if r[2]]
        still = [r[3] for r in rows if not r[2]]
        nfp = sum(v for k, v in fp[c].items() if k != 'px_on_static_or_bg')
        res['per_class'][NAMES[c]] = dict(
            n_gt=R['n_gt'], AP50=aps[0], AP50_95=float(np.nanmean(aps)) if R['n_gt'] else float('nan'),
            IoU=inter[c] / union[c] if union[c] else float('nan'),
            recall=float(np.mean([r[3] for r in rows])) if rows else None,
            precision=tp_count[c] / max(1, tp_count[c] + nfp),
            recall_by_area=rec_bins,
            recall_moving=[float(np.mean(mov)) if mov else None, len(mov)],
            recall_not_moving=[float(np.mean(still)) if still else None, len(still)],
            tp=tp_count[c], fp=dict(fp[c]), fp_per_100_frames={k: 100 * v / n_frames for k, v in fp[c].items()
                                                              if k != 'px_on_static_or_bg'})
    tot = conf_px.sum(1)
    res['static_px_covered_by_dynpot'] = {
        (['background'] + NAMES)[g]: float(conf_px[g, [k + 1 for k in DYNPOT]].sum() / max(1, tot[g]))
        for g in [0] + [k + 1 for k in STATIC]}
    res['static_px_covered_by_class'] = {
        (['background'] + NAMES)[g]: {NAMES[k]: float(conf_px[g, k + 1] / max(1, tot[g])) for k in DYNPOT}
        for g in [0] + [k + 1 for k in STATIC]}
    res['image_px_wrongly_dynpot'] = float(sum(conf_px[g, [k + 1 for k in DYNPOT]].sum()
                                               for g in [0] + [k + 1 for k in STATIC]) / conf_px.sum())
    res['confusion_px'] = conf_px.tolist()
    vals = [v for v in res['per_class'].values()]
    res['mean'] = dict(AP50=float(np.nanmean([v['AP50'] for v in vals])),
                       AP50_95=float(np.nanmean([v['AP50_95'] for v in vals])),
                       IoU=float(np.nanmean([v['IoU'] for v in vals])))
    print(json.dumps({k: v for k, v in res.items() if k != 'confusion_px'}, indent=1))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
