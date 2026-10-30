#!/usr/bin/env python3
"""p7eval.py --out-dir D --seqs s1,s2 --variants v1,v2 [--extra-json file] [--jobs N]

Offline (deterministic) evaluation of SAVIOR perception variants on the t1 (TUNING) warehouse bags against the GT instance
segmentation + per-frame moving flags (p6 scripts/wh_gt.py). YOLO detections come from the cache of detcache.py (fine-tuned
YOLO26s, deployed settings; identical to the node's), then exactly the node's SaviorPipeline runs with the gyro rotation
between frames. One process per (sequence, variant). Output D/<seq>/<variant>.json with
  * gt_centric: per key (class:moving|static, carried_box/pallet:moving|static, driver:...) [n instance-frames, n masked]
    (masked = >= 50 % of the GT instance's cam0 pixels in the final core 255 mask; GT instances >= MIN_PX px);
  * init window (t in [2.5, 8] s) masked counts of moving instances (take-off / filter initialisation);
  * onset: for every static->moving transition of a GT instance (and the first in-view frame of an instance that is
    already moving), latency [s] to the first masked frame (in-view frames only, capped at 3 s);
  * flicker: per GT instance, masked-state toggles between consecutive in-view frames; P6 core-area jump metric
    (share of frames with > 30 % core-area change, frames with >= 2000 core px);
  * pixel shares: core / band, core on static potential pixels, core recall of moving pixels, right core vs GT right moving;
  * timings of the pipeline stages (CPU, 1 thread per process).
"""
import argparse
import copy
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_k] = '1'
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

cv2.setNumThreads(1)
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/p6_warehouse/scripts')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wh_gt import SeqGT  # noqa: E402
from variants import VARIANTS  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
B = WS + '/src/savior/savior_bringup/config'
S = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN'
CACHE = S + '/detcache'
MIN_PX = 200
INIT = (2.5, 8.0)


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flatten(v, f'{prefix}{k}.'))
        else:
            out[f'{prefix}{k}'] = v
    return out


def load_frames(seq):
    from rosbags.highlevel import AnyReader
    from savior_perception.core.motion import GyroIntegrator
    g = GyroIntegrator(max_age_s=1e9)
    frames = {}
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
        conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw', '/cam1/image_raw')]
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            if c.topic == '/imu0':
                w = m.angular_velocity
                g.add(st * 1e-9, (w.x, w.y, w.z))
            else:
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
    return g, frames


class DetCache:
    """Cached YOLO detections of one sequence; masks decoded per frame (lazily)."""

    def __init__(self, seq):
        z = np.load(f'{CACHE}/{seq}.npz')
        self.h, self.w = (int(v) for v in z['shape'])
        self.cls, self.score, self.bbox, self.bits = z['cls'], z['score'], z['bbox'], z['bits']
        self.offs = np.concatenate([[0], np.cumsum(z['lens'])])
        first = np.concatenate([[0], np.cumsum(z['nper'])])
        self.idx = {int(st): (int(first[j]), int(first[j + 1])) for j, st in enumerate(z['stamps'])}

    def get(self, st, Instance):
        a, b = self.idx.get(int(st), (0, 0))
        out = []
        for j in range(a, b):
            x0, y0, x1, y1 = (int(v) for v in self.bbox[j])
            m = np.zeros((self.h, self.w), bool)
            n = (y1 - y0) * (x1 - x0)
            m[y0:y1, x0:x1] = np.unpackbits(self.bits[self.offs[j]:self.offs[j + 1]])[:n].reshape(y1 - y0, x1 - x0).astype(bool)
            out.append(Instance(mask=m, cls=str(self.cls[j]), score=float(self.score[j]), bbox=(x0, y0, x1, y1)))
        return out


def run_one(args):
    seq, name, spec, out_path = args
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.config import PipelineConfig
    from savior_perception.core.pipeline import SaviorPipeline
    from savior_perception.core.roles import RoleTable
    from savior_perception.core.types import Instance
    from savior_perception.params import all_defaults
    src, roles, over = spec
    t_start = time.time()
    P = all_defaults()
    y = yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))
    P.update(flatten(y['savior_node']['ros__parameters']))
    P.update(over)
    cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(f'{B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    pipe = SaviorPipeline(cfg, RoleTable.from_yaml(f'{B}/roles/{roles}.yaml'), rect)
    gt = SeqGT(seq)
    g, frames = load_frames(seq)
    dets = DetCache(seq) if src == 'wh' else None
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    if int(os.environ.get('P7_MAX_FRAMES', '0')) > 0:
        stamps = stamps[:int(os.environ['P7_MAX_FRAMES'])]
    t0s = stamps[0] * 1e-9
    gtc = {}
    init = {}
    core_px = []
    pixacc = {k: np.zeros(3, np.int64) for k in ('L_core_vs_moving', 'L_any_vs_moving', 'R_core_vs_moving')}
    shares = {'core': 0, 'band': 0, 'static_pot_core': 0, 'static_pot': 0}
    hist = {}          # gid -> list of (k, masked, moving)
    timings = {}
    diag = {}
    prev_t = None
    for k, st in enumerate(stamps):
        left, right = frames.pop(st)
        t = st * 1e-9
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        ids0 = gt.seg(0, st)
        mv = gt.moving.get(st, set())
        if src == 'wh':
            inp = dets.get(st, Instance)
        else:
            inp = []
            for i in np.unique(ids0):
                i = int(i)
                if i <= 0 or gt.code[i] not in (1, 2, 3, 4, 5) or (src == 'gt_moving' and i not in mv):
                    continue
                m = ids0 == i
                if m.sum() >= 30:
                    inp.append(Instance(mask=m, cls=gt.cls[i]))
        ml, mr, stats = pipe.process(left, right, t, inp, R_imu=R_imu)
        if src == 'wh':                         # detection-level diagnostics (matched GT instance >= 30 % of the det)
            for x in pipe.last_result.instances:
                if x.role != 'potential' or x.status == 'carried':
                    continue
                x0, y0, x1, y1 = x.bbox
                sub = ids0[y0:y1, x0:x1][x.mask[y0:y1, x0:x1]]
                if sub.size == 0:
                    continue
                ii, cc = np.unique(sub, return_counts=True)
                j = int(np.argmax(cc))
                gid = int(ii[j]) if cc[j] >= 0.3 * sub.size else 0
                gl = 'none' if gid == 0 or gt.code[gid] not in (1, 2, 3, 4, 5) else ('moving' if gid in mv else 'static')
                mo = x.motion or {}
                zb = 'na' if not np.isfinite(x.depth) else ('<3' if x.depth < 3 else ('<6' if x.depth < 6 else '>6'))
                key = f"{x.cls}|{gl}|{mo.get('sel_obs', '-')}|{mo.get('sel', '-')}|{x.status}|{zb}"
                diag[key] = diag.get(key, 0) + 1
        for kk, v in stats['timings_ms'].items():
            timings.setdefault(kk, []).append(v)
        core = ml == 255
        core_px.append(int(core.sum()))
        mvarr = np.fromiter(mv, np.int64) if mv else np.zeros(0, np.int64)
        code0 = gt.code[ids0]
        pot0 = (code0 >= 1) & (code0 <= 5)
        mov0 = np.isin(ids0, mvarr) & (ids0 > 0)
        ids1 = gt.seg(1, st)
        mov1 = np.isin(ids1, mvarr) & (ids1 > 0)
        for key, pr, gm in (('L_core_vs_moving', core, mov0), ('L_any_vs_moving', ml >= 128, mov0), ('R_core_vs_moving', mr == 255, mov1)):
            tp = int(np.count_nonzero(pr & gm))
            pixacc[key] += (tp, int(np.count_nonzero(pr)) - tp, int(np.count_nonzero(gm)) - tp)
        shares['core'] += int(core.sum())
        shares['band'] += int((ml == 192).sum())
        sp = pot0 & ~mov0
        shares['static_pot_core'] += int((core & sp).sum())
        shares['static_pot'] += int(sp.sum())
        cnt = np.bincount(ids0.ravel(), minlength=gt.max_id + 1)
        cnt_core = np.bincount(ids0.ravel(), weights=core.ravel(), minlength=gt.max_id + 1)
        for i in np.flatnonzero(cnt >= MIN_PX):
            i = int(i)
            if i == 0 or gt.code[i] not in (1, 2, 3, 4, 5):
                continue
            masked = cnt_core[i] >= 0.5 * cnt[i]
            c = gt.cls[i]
            moving = i in mv
            tag = 'moving' if moving else 'static'
            keys = [f'{c}:{tag}']
            f = gt.carried_by(i)
            if f is not None and c in ('box', 'pallet'):
                keys.append(f'carried_{c}:{tag}')
            if c == 'person' and i >= 5000 and f is not None:
                keys.append(f'driver:{tag}')
            for kk in keys:
                e = gtc.setdefault(kk, [0, 0])
                e[0] += 1
                e[1] += int(masked)
            if moving and INIT[0] <= t - t0s <= INIT[1]:
                e = init.setdefault(c, [0, 0])
                e[0] += 1
                e[1] += int(masked)
            hist.setdefault(i, []).append((k, bool(masked), moving))
    # onset latency + per-instance flicker
    onset = {}
    flick = {}
    dt = 0.05
    for i, hs in hist.items():
        c = gt.cls[i]
        prev = None
        for j, (k, masked, moving) in enumerate(hs):
            start = moving and (prev is None or not prev[2] or k - prev[0] > 10)
            if start:
                lat = None
                for k2, m2, mv2 in hs[j:]:
                    if (k2 - k) * dt > 3.0 or not mv2:
                        break
                    if m2:
                        lat = (k2 - k) * dt
                        break
                kind = 'transition' if (prev is not None and not prev[2] and k - prev[0] <= 10) else 'appear'
                onset.setdefault(f'{c}:{kind}', []).append(lat)
            if prev is not None and k - prev[0] == 1:
                tag = 'moving' if moving else 'static'
                e = flick.setdefault(f'{c}:{tag}', [0, 0])
                e[0] += 1
                e[1] += int(masked != prev[1])
            prev = (k, masked, moving)
    ch = [abs(a - b) / max(a, b) for a, b in zip(core_px, core_px[1:]) if max(a, b) > 2000]
    npx = float(len(stamps) * 672 * 376)
    out = {'seq': seq, 'variant': name, 'frames': len(stamps), 'gt_centric': gtc, 'init_window': init, 'onset': onset,
           'flicker_inst': flick, 'flicker_core_jump': round(sum(x > 0.3 for x in ch) / max(1, len(ch)), 5),
           'pix': {k: [int(x) for x in v] for k, v in pixacc.items()},
           'core_share': shares['core'] / npx, 'band_share': shares['band'] / npx,
           'static_pot_core_share_of_static_pot': shares['static_pot_core'] / max(1, shares['static_pot']),
           'timing_ms': {kk: [round(float(np.percentile(v, q)), 3) for q in (50, 90, 99)] for kk, v in timings.items()},
           'diag': diag, 'runtime_s': round(time.time() - t_start, 1), 'overrides': {k: v for k, v in over.items()}, 'roles': roles}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, 'w'))
    return seq, name, out['runtime_s']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--seqs', required=True)
    ap.add_argument('--variants', required=True)
    ap.add_argument('--extra-json', default='', help='json {name: [src, roles, overrides]} of extra variants')
    ap.add_argument('--jobs', type=int, default=16)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--max-frames', type=int, default=0)
    a = ap.parse_args()
    if a.max_frames:
        os.environ['P7_MAX_FRAMES'] = str(a.max_frames)
    V = dict(VARIANTS)
    if a.extra_json:
        V.update({k: tuple(v) for k, v in json.load(open(a.extra_json)).items()})
    seqs = a.seqs.split(',')
    assert all('_t1_' in s for s in seqs), 'tuning set (t1) only'
    tasks = []
    for s in seqs:
        for v in a.variants.split(','):
            p = f'{a.out_dir}/{s}/{v}.json'
            if a.force or not os.path.isfile(p):
                tasks.append((s, v, V[v], p))
    # longest first (aisles, motion variants)
    tasks.sort(key=lambda x: ('aisles' not in x[0], not x[2][2].get('motion.enable', False)))
    print(len(tasks), 'tasks', flush=True)
    t0 = time.time()
    with mp.get_context('spawn').Pool(a.jobs, maxtasksperchild=1) as pool:
        for s, v, rt in pool.imap_unordered(run_one, tasks):
            print(f'{time.time() - t0:7.0f}s done {s} {v} ({rt}s)', flush=True)


if __name__ == '__main__':
    main()
