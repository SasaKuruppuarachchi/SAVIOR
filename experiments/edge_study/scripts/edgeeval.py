#!/usr/bin/env python3
"""edgeeval.py --out-dir D --seqs s1,s2 --variants v1,v2 [--jobs N] [--force]

EDGE study offline evaluation (t1 tuning set ONLY). Replays cached YOLO detections (detcache, deployed settings) through
the frozen main (sens_fix1, = reference) and an EDGE variant side by side, frame by frame, with the gyro between frames.
Per (sequence, variant) -> D/<seq>/<variant>.json with
  * the P7 GT metrics of the VARIANT's final masks (p7eval.py definitions: gt_centric masked counts per class:moving|static,
    onset latency, flicker, pixel recall of moving pixels, static-potential core share);
  * agreement with the reference: per-frame IoU of the left core (255) / left any (>= 128) / right core masks (mean over
    frames whose union is non-empty, and pooled), share of frames with identical left masks;
  * instance agreement (same detections, non-async variants): |z_var - z_ref| / z_ref per relevant detection (median / p90,
    share within 5 / 10 %), status agreement (masked vs not) and confusion, depth availability;
  * per-frame CPU time of the variant (ms; keyframe pipeline + prediction), 1 thread.
Variants: edge_variants.py VARIANTS {name: dict(over=..., det=cache dir key)} on top of MAIN (= sens_fix1 overrides).
Runs inside the savior image with the EDGE scratch copy first on PYTHONPATH (epy.sh)."""
import argparse
import json
import math
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
from edge_variants import MAIN, VARIANTS, CACHES, BASES  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
B = WS + '/src/savior/savior_bringup/config'
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
    def __init__(self, path):
        z = np.load(path)
        self.h, self.w = (int(v) for v in z['shape'])
        self.cls, self.score, self.bbox, self.bits = z['cls'], z['score'], z['bbox'], z['bits']
        self.offs = np.concatenate([[0], np.cumsum(z['lens'])])
        first = np.concatenate([[0], np.cumsum(z['nper'])])
        self.idx = {int(st): (int(first[j]), int(first[j + 1])) for j, st in enumerate(z['stamps'])}
        self.seg_ms = z['seg_ms'] if 'seg_ms' in z.files else None

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


def make_pipe(over, roles):
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.config import PipelineConfig
    from savior_perception.core.pipeline import SaviorPipeline
    from savior_perception.core.roles import RoleTable
    from savior_perception.params import all_defaults
    from savior_perception.core.asyncseg import scaled_config
    P = all_defaults()
    y = yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))
    P.update(flatten(y['savior_node']['ros__parameters']))
    P.update(over)
    cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(f'{B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    pcfg = scaled_config(cfg)
    return SaviorPipeline(pcfg, RoleTable.from_yaml(f'{B}/roles/{roles}.yaml'), rect), cfg, rect


def iou(a, b):
    u = int(np.count_nonzero(a | b))
    return (int(np.count_nonzero(a & b)), u)


def run_one(args):
    seq, name, out_path = args
    from savior_perception.core.types import Instance, ROLE_DYNAMIC, ROLE_POTENTIAL
    from savior_perception.core.asyncseg import AsyncSegDriver
    spec = VARIANTS[name]
    roles = spec.get('roles', 'warehouse')
    t_start = time.time()
    ref, _, rect = make_pipe(MAIN, 'warehouse')
    vover = {**BASES[spec.get('base', 'main')], **spec.get('over', {})}
    var, vcfg, _ = make_pipe(vover, roles)
    gt = SeqGT(seq)
    g, frames = load_frames(seq)
    dref = DetCache(CACHES['s672'] + f'/{seq}.npz')
    dvar = DetCache(CACHES[spec.get('det', 's672')] + f'/{seq}.npz')
    asyn = vcfg.asyncseg.enable
    drv = AsyncSegDriver(var, vcfg.asyncseg, rect, g.rotation) if asyn else None
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    if int(os.environ.get('EDGE_MAX_FRAMES', '0')) > 0:  # smoke tests
        stamps = stamps[:int(os.environ['EDGE_MAX_FRAMES'])]
    t0s = stamps[0] * 1e-9
    gtc, init, hist = {}, {}, {}
    pixacc = {k: np.zeros(3, np.int64) for k in ('L_core_vs_moving', 'L_any_vs_moving', 'R_core_vs_moving')}
    shares = {'core': 0, 'band': 0, 'static_pot_core': 0, 'static_pot': 0}
    agree = {'Lcore': [], 'Lany': [], 'Rcore': [], 'Lcore_pool': [0, 0], 'Lany_pool': [0, 0], 'Rcore_pool': [0, 0], 'same': 0,
             'n': 0}
    inst_ag = {'dz_rel': [], 'n_rel': 0, 'ref_depth': 0, 'var_depth': 0, 'both_depth': 0,
               'status': {'mm': 0, 'mu': 0, 'um': 0, 'uu': 0}, 'by_cls': {}}
    cpu_ms, key_ms, seg_ms = [], [], []
    prev_t = None
    nkey = 0
    for k, st in enumerate(stamps):
        left, right = frames.pop(st)
        t = st * 1e-9
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        ml_r, mr_r, _ = ref.process(left, right, t, dref.get(st, Instance), R_imu=R_imu)
        c0 = time.process_time()
        if asyn:
            if drv.is_key(t):
                drv.process_key(left, right, t, dvar.get(st, Instance), drv.key_rotation(t))
                nkey += 1
                key_ms.append((time.process_time() - c0) * 1e3)
                if dvar.seg_ms is not None:
                    seg_ms.append(float(dvar.seg_ms[k]) if k < len(dvar.seg_ms) else math.nan)
            ml, mr = drv.output(t, left.shape[:2], right.shape[:2])
        else:
            ml, mr, _ = var.process(left, right, t, dvar.get(st, Instance), R_imu=R_imu)
            nkey += 1
        cpu_ms.append((time.process_time() - c0) * 1e3)
        # ---- agreement with the reference
        for key, a, b in (('Lcore', ml == 255, ml_r == 255), ('Lany', ml >= 128, ml_r >= 128), ('Rcore', mr == 255, mr_r == 255)):
            i_, u_ = iou(a, b)
            agree[key + '_pool'][0] += i_
            agree[key + '_pool'][1] += u_
            if u_ > 0:
                agree[key].append(i_ / u_)
        agree['same'] += int(np.array_equal(ml, ml_r))
        agree['n'] += 1
        if not asyn and spec.get('det', 's672') == 's672':
            ri, vi = ref.last_result.instances, var.last_result.instances
            nd = min(len([x for x in ri if x.status != 'carried']), len([x for x in vi if x.status != 'carried']))
            for a, b in zip(ri[:nd], vi[:nd]):
                if a.role not in (ROLE_DYNAMIC, ROLE_POTENTIAL):
                    continue
                inst_ag['n_rel'] += 1
                fa, fb_ = math.isfinite(a.depth), math.isfinite(b.depth)
                inst_ag['ref_depth'] += fa
                inst_ag['var_depth'] += fb_
                if fa and fb_:
                    inst_ag['both_depth'] += 1
                    inst_ag['dz_rel'].append(abs(b.depth - a.depth) / a.depth)
                sa, sb = a.is_dynamic, b.is_dynamic
                kk = ('m' if sa else 'u') + ('m' if sb else 'u')
                inst_ag['status'][kk] += 1
                e = inst_ag['by_cls'].setdefault(a.cls, {'mm': 0, 'mu': 0, 'um': 0, 'uu': 0})
                e[kk] += 1
        # ---- GT metrics of the variant (p7eval definitions)
        ids0 = gt.seg(0, st)
        mv = gt.moving.get(st, set())
        core = ml == 255
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
        shares['band'] += int(((ml >= 128) & (ml < 255)).sum())
        sp = pot0 & ~mov0
        shares['static_pot_core'] += int((core & sp).sum())
        shares['static_pot'] += int(sp.sum())
        cnt = np.bincount(ids0.ravel(), minlength=gt.max_id + 1)
        cnt_core = np.bincount(ids0.ravel(), weights=core.ravel(), minlength=gt.max_id + 1)
        cnt_any = np.bincount(ids0.ravel(), weights=(ml >= 128).ravel(), minlength=gt.max_id + 1)
        for i in np.flatnonzero(cnt >= MIN_PX):
            i = int(i)
            if i == 0 or gt.code[i] not in (1, 2, 3, 4, 5):
                continue
            masked = cnt_core[i] >= 0.5 * cnt[i]
            masked_any = cnt_any[i] >= 0.5 * cnt[i]
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
                e = gtc.setdefault(kk, [0, 0, 0])
                e[0] += 1
                e[1] += int(masked)
                e[2] += int(masked_any)
            if moving and INIT[0] <= t - t0s <= INIT[1]:
                e = init.setdefault(c, [0, 0])
                e[0] += 1
                e[1] += int(masked)
            hist.setdefault(i, []).append((k, bool(masked), moving))
    onset, flick = {}, {}
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
    npx = float(len(stamps) * 672 * 376)
    dz = np.array(inst_ag.pop('dz_rel'))
    if dz.size:
        inst_ag.update(dz_med=float(np.median(dz)), dz_p90=float(np.percentile(dz, 90)), dz_w5=float(np.mean(dz <= 0.05)),
                       dz_w10=float(np.mean(dz <= 0.10)), n_dz=int(dz.size))
    out = {'seq': seq, 'variant': name, 'frames': len(stamps), 'n_key': nkey, 'gt_centric': gtc, 'init_window': init,
           'onset': onset, 'flicker_inst': flick,
           'pix': {k: [int(x) for x in v] for k, v in pixacc.items()},
           'core_share': shares['core'] / npx, 'band_share': shares['band'] / npx,
           'static_pot_core_share_of_static_pot': shares['static_pot_core'] / max(1, shares['static_pot']),
           'agree': {'Lcore_mean': float(np.mean(agree['Lcore'])) if agree['Lcore'] else 1.0,
                     'Lany_mean': float(np.mean(agree['Lany'])) if agree['Lany'] else 1.0,
                     'Rcore_mean': float(np.mean(agree['Rcore'])) if agree['Rcore'] else 1.0,
                     'Lcore_pool': agree['Lcore_pool'][0] / max(1, agree['Lcore_pool'][1]),
                     'Lany_pool': agree['Lany_pool'][0] / max(1, agree['Lany_pool'][1]),
                     'Rcore_pool': agree['Rcore_pool'][0] / max(1, agree['Rcore_pool'][1]),
                     'same_frac': agree['same'] / max(1, agree['n'])},
           'inst_agree': inst_ag,
           'cpu_ms': [float(np.percentile(cpu_ms, q)) for q in (50, 90, 99)] + [float(np.mean(cpu_ms))],
           'key_cpu_ms': ([float(np.percentile(key_ms, q)) for q in (50, 90, 99)] + [float(np.mean(key_ms))]) if key_ms else None,
           'runtime_s': round(time.time() - t_start, 1), 'over': spec.get('over', {}), 'det': spec.get('det', 's672')}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, 'w'))
    return seq, name, out['runtime_s']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--seqs', required=True)
    ap.add_argument('--variants', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--max-frames', type=int, default=0)
    a = ap.parse_args()
    if a.max_frames:
        os.environ['EDGE_MAX_FRAMES'] = str(a.max_frames)
    seqs = a.seqs.split(',')
    assert all('_t1_' in s for s in seqs), 'tuning set (t1) only'
    tasks = []
    for s in seqs:
        for v in a.variants.split(','):
            p = f'{a.out_dir}/{s}/{v}.json'
            if a.force or not os.path.isfile(p):
                tasks.append((s, v, p))
    tasks.sort(key=lambda x: 'aisles' not in x[0])
    print(len(tasks), 'tasks', flush=True)
    t0 = time.time()
    with mp.get_context('spawn').Pool(a.jobs, maxtasksperchild=1) as pool:
        for s, v, rt in pool.imap_unordered(run_one, tasks):
            print(f'{time.time() - t0:7.0f}s done {s} {v} ({rt}s)', flush=True)


if __name__ == '__main__':
    main()
