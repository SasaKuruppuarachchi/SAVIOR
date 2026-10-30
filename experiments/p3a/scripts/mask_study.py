"""P3a offline mask study on a uHumans2 bag (runs inside the savior image, uses the INSTALLED savior_perception).

Per frame (exact-stamp left/right/seg triplets):
  * oracle human mask from /tesse/seg_cam (exact colour (35,213,234), all pixels) -> coverage, components
  * oracle pipeline masks exactly as savior_node publishes them for `oracle_person`
    (oracle_colormap, person_only, ext/tracker off): left core + right (stereo warp)
  * YOLO26s-seg person-only masks (as `yolo_naive`) and the yolo_full pipeline masks (coco_indoor, ext on,
    tracker off) -> pixel IoU / recall / precision vs the oracle human mask, instance recall per oracle component
Writes <out>/<seq>_frames.csv and <out>/<seq>_masks.npz (bit-packed oracle left/right/human masks of frames with humans).
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.types import MASK_CORE, MASK_EXTENSION
from savior_perception.params import all_defaults
from savior_perception.segmenters import make_segmenter

WS = '/home/sasa/workspace/savior_ws'
SHARE = WS + '/install/savior_bringup/share/savior_bringup'
CALIB = SHARE + '/config/uhumans2/kalibr_imucam_chain.yaml'
CMAP = SHARE + '/config/oracle/uhumans2_colormap.yaml'
LT, RT, ST = '/tesse/left_cam/mono/image_raw', '/tesse/right_cam/mono/image_raw', '/tesse/seg_cam/rgb/image_raw'
HUMAN_RGB = (35, 213, 234)


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        key = f'{prefix}{k}'
        out.update(flatten(v, key + '.') if isinstance(v, dict) else {key: v})
    return out


def make(sets, roles_file, backend):
    p = all_defaults()
    with open(SHARE + '/config/uhumans2/savior_perception.yaml') as fh:
        p.update(flatten(yaml.safe_load(fh)['savior_node']['ros__parameters']))
    p.update(sets)
    p['segmenter.backend'] = backend
    cfg = PipelineConfig.from_flat({k: v for k, v in p.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    roles = RoleTable.from_yaml(roles_file)
    rect = stereo_from_kalibr(CALIB, 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    seg = make_segmenter(backend, model=WS + '/models/yolo26s-seg.engine', conf=p['segmenter.conf'], iou=p['segmenter.iou'],
                         imgsz=p['segmenter.imgsz'], classes=roles.relevant_classes(), colormap_file=CMAP,
                         retina_masks=p['segmenter.retina_masks'])
    return seg, SaviorPipeline(cfg, roles, rect)


def frames(bag):
    from rosbags.highlevel import AnyReader
    pending = {}
    with AnyReader([Path(bag)]) as reader:
        conns = [c for c in reader.connections if c.topic in (LT, RT, ST)]
        for conn, _, raw in reader.messages(connections=conns):
            msg = reader.deserialize(raw, conn.msgtype)
            st = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            ch = 3 if conn.topic == ST else 1
            img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width * ch]
            img = img.reshape(msg.height, msg.width, ch).copy() if ch == 3 else img.copy()
            slot = pending.setdefault(st, {})
            slot[conn.topic] = img
            if len(slot) == 3:
                del pending[st]
                yield st, slot[LT], slot[RT], slot[ST]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-yolo', action='store_true')
    ap.add_argument('--max-frames', type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    person = SHARE + '/config/roles/person_only.yaml'
    coco = SHARE + '/config/roles/coco_indoor.yaml'
    o_seg, o_pipe = make({'tracker.enable': False, 'extension.enable': False}, person, 'oracle_colormap')
    if not a.no_yolo:
        y_seg, y_pipe = make({'tracker.enable': False, 'extension.enable': False}, person, 'yolo')
        f_seg, f_pipe = make({'tracker.enable': False}, coco, 'yolo')
        y_seg.warmup((480, 720))
        f_seg.warmup((480, 720))
    fo = open(os.path.join(a.out, f'{a.seq}_frames.csv'), 'w', newline='')
    wr = csv.writer(fo)
    cols = ['stamp_ns', 'human_px', 'n_comp', 'n_comp30', 'human_px_small', 'orc_left_core', 'orc_right_core',
            'human_bbox_frac', 'y_px', 'y_inter', 'y_n', 'f_core', 'f_core_inter', 'f_band', 'f_band_inter',
            'n_comp_det', 'comp_areas', 'comp_recall', 'y_fp_inst']
    wr.writerow(cols)
    pk_st, pk_h, pk_l, pk_r = [], [], [], []
    hr, hg, hb = HUMAN_RGB
    n = 0
    t0 = time.time()
    for st, left, right, segimg in frames(f'{WS}/data/uhumans2/ros2/{a.seq}'):
        n += 1
        hum = (segimg[..., 0] == hr) & (segimg[..., 1] == hg) & (segimg[..., 2] == hb)
        hpx = int(hum.sum())
        bgr = segimg[..., ::-1]
        o_inst = o_seg.predict(np.ascontiguousarray(bgr))
        ml, mr, _ = o_pipe.process(left, right, st * 1e-9, o_inst)
        ncomp = ncomp30 = small = 0
        areas, crec = [], []
        bbfrac = 0.0
        if hpx:
            nl, lab, stats, _ = cv2.connectedComponentsWithStats(hum.view(np.uint8), connectivity=8)
            ncomp = nl - 1
            ar = stats[1:, cv2.CC_STAT_AREA]
            ncomp30 = int((ar >= 30).sum())
            small = int(ar[ar < 30].sum())
            ys, xs = np.nonzero(hum)
            bbfrac = (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1) / hum.size
        row = dict(stamp_ns=st, human_px=hpx, n_comp=ncomp, n_comp30=ncomp30, human_px_small=small,
                   orc_left_core=int((ml == MASK_CORE).sum()), orc_right_core=int((mr == MASK_CORE).sum()),
                   human_bbox_frac=round(bbfrac, 5))
        if not a.no_yolo:
            yinst = y_seg.predict(left)
            ym = np.zeros(hum.shape, bool)
            fp = 0
            for i in yinst:
                ym |= i.mask
                if hpx == 0 or np.count_nonzero(i.mask & hum) < 0.1 * max(1, np.count_nonzero(i.mask)):
                    fp += 1
            finst = f_seg.predict(left)
            fl, fr, _ = f_pipe.process(left, right, st * 1e-9, finst)
            fcore, fband = fl == MASK_CORE, fl == MASK_EXTENSION
            row.update(y_px=int(ym.sum()), y_inter=int((ym & hum).sum()), y_n=len(yinst),
                       f_core=int(fcore.sum()), f_core_inter=int((fcore & hum).sum()),
                       f_band=int(fband.sum()), f_band_inter=int((fband & hum).sum()), y_fp_inst=fp)
            ndet = 0
            if hpx:
                for k in range(1, nl):
                    if stats[k, cv2.CC_STAT_AREA] < 30:
                        continue
                    cm = lab == k
                    rec = np.count_nonzero(cm & ym) / np.count_nonzero(cm)
                    areas.append(int(stats[k, cv2.CC_STAT_AREA]))
                    crec.append(round(rec, 3))
                    ndet += rec >= 0.5
            row.update(n_comp_det=ndet, comp_areas=' '.join(map(str, areas)), comp_recall=' '.join(map(str, crec)))
        wr.writerow([row.get(c, '') for c in cols])
        if hpx:
            pk_st.append(st)
            pk_h.append(np.packbits(hum))
            pk_l.append(np.packbits(ml == MASK_CORE))
            pk_r.append(np.packbits(mr == MASK_CORE))
        if n % 500 == 0:
            print(f'{a.seq}: {n} frames {time.time() - t0:.0f}s', file=sys.stderr, flush=True)
        if a.max_frames and n >= a.max_frames:
            break
    fo.close()
    if pk_st:
        np.savez_compressed(os.path.join(a.out, f'{a.seq}_masks.npz'), stamp_ns=np.array(pk_st, np.int64),
                            human=np.array(pk_h), left=np.array(pk_l), right=np.array(pk_r), shape=np.array([480, 720]))
    print(f'{a.seq}: done {n} frames, {len(pk_st)} with humans, {time.time() - t0:.0f}s', file=sys.stderr)


if __name__ == '__main__':
    main()
