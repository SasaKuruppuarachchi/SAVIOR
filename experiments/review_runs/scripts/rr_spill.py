#!/usr/bin/env python3
"""rr_spill.py --out-dir D --seqs s,.. --variants v,.. [--jobs N] : promotion-spill check (task D), OFFLINE replay on t1 ONLY.

Why offline: every held-out (t2) SAVIOR run was recorded with stats_compact=true (frozen), so /savior/stats holds only
per-frame counts (n_roots / n_promoted / n_held), no per-instance list -> GT-static promoted instances cannot be identified
from existing t2 logs. The replay is exactly the node's SaviorPipeline on the cached detections of the frozen warehouse YOLO
(results/p7/scripts/p7eval.py machinery: detcache of agent N, gyro rotation between frames, all 20 Hz frames from the bag
start = online run_01 at offset 0.0). Settings = the resolved pset of the variant (rr_args.settings) on top of
all_defaults() + savior_perception_yolo.yaml (as p7eval). Per frame the counts n_roots / n_promoted / n_held are written so
they can be compared record-for-record with the online savior_stats.jsonl of the back-end v2 run_01 (validation).

Per potential detection (status promoted / held / uncertain / root...), matched GT instance = the GT id covering >= 30 % of
the detection's pixels (p7eval rule); GT label moving / static / none (moving.csv, this frame). GT-static subclasses:
  forklift_parked  static forklift body
  parked_load      static box / pallet in a forklift actor block (load of a parked forklift)
  free_static      static box / pallet / trolley not in an actor block (stacks, rack boxes)
  person_static    (person is never 'potential'; listed for completeness)
touch_mover: the detection mask dilated by 5 px overlaps GT-moving pixels of another instance in this frame (cam0).
-> D/<seq>/<variant>.json"""
import argparse, json, multiprocessing as mp, os, sys, time
from pathlib import Path
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_k] = '1'
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
cv2.setNumThreads(1)
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/p6_warehouse/scripts')
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/p7/scripts')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['RR_FREEZE_OPTIONAL'] = '1'
from wh_gt import SeqGT  # noqa: E402
from p7eval import DetCache, flatten  # noqa: E402
from rr_args import settings, kvparse  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
B = WS + '/src/savior/savior_bringup/config'
BASE = {'sens_fix1', 'p7_nb', 'yolo_naive'}


def tsec(st):
    """float seconds exactly as savior_node computes them (sec + nanosec * 1e-9), not st * 1e-9 (hysteresis boundaries)."""
    return st // 1_000_000_000 + (st % 1_000_000_000) * 1e-9


def load_frames(seq):
    """= p7eval.load_frames with the node's float time for the gyro samples."""
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
                g.add(tsec(st), (w.x, w.y, w.z))
            else:
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
    return g, frames


def pset_of(seq, var):
    if var in BASE:
        import subprocess
        out = subprocess.run([sys.executable, f'{WS}/results/backend_v2/scripts/bv2_args.py', seq, var, 'v2'], check=True,
                             capture_output=True, text=True).stdout.split('\n')
        L = out
    else:
        L = settings(seq, var)
    roles = [a.split(':=', 1)[1] for a in L[8:] if a.startswith('roles_file:=')][0]
    return {k: yaml.safe_load(v) for k, v in kvparse(L[7]).items()}, roles


def run_one(args):
    seq, var, out_path = args
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.config import PipelineConfig
    from savior_perception.core.pipeline import SaviorPipeline
    from savior_perception.core.roles import RoleTable
    from savior_perception.core.types import Instance
    from savior_perception.params import all_defaults
    t_start = time.time()
    over, roles = pset_of(seq, var)
    P = all_defaults()
    y = yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))
    P.update(flatten(y['savior_node']['ros__parameters']))
    P.update(over)
    cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(f'{B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    pipe = SaviorPipeline(cfg, RoleTable.from_yaml(roles), rect)
    gt = SeqGT(seq)
    g, frames = load_frames(seq)
    dets = DetCache(seq)
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    counts = {}       # status|gtlabel|subclass|touch -> [n det-frames, n px]
    inst = {}         # status -> {gt label -> set of gt ids}
    per_frame = []
    static_in_view = set()
    prev_t = None
    ker = np.ones((11, 11), np.uint8)
    for st in stamps:
        left, right = frames.pop(st)
        t = tsec(st)
        R_imu = g.rotation(prev_t, t) if prev_t is not None else None
        prev_t = t
        ml, mr, stats = pipe.process(left, right, t, dets.get(st, Instance), R_imu=R_imu)
        per_frame.append([round(t, 3), stats['n_roots'], stats['n_promoted'], stats['n_held']])
        ids0 = gt.seg(0, st)
        mv = gt.moving.get(st, set())
        mvarr = np.fromiter(mv, np.int64) if mv else np.zeros(0, np.int64)
        mov0 = np.isin(ids0, mvarr) & (ids0 > 0)
        cnt = np.bincount(ids0.ravel(), minlength=gt.max_id + 1)
        for i in np.flatnonzero(cnt >= 200):
            i = int(i)
            if i and gt.code[i] in (2, 3, 4, 5) and i not in mv:
                static_in_view.add(i)
        insts = pipe.last_result.instances
        lab = []
        for x in insts:                      # GT match of EVERY instance (also roots = people), p7eval 30 % rule
            if x.status == 'carried':
                lab.append((0, 'none')); continue
            x0, y0, x1, y1 = x.bbox
            sub = ids0[y0:y1, x0:x1][x.mask[y0:y1, x0:x1]]
            if sub.size == 0:
                lab.append((0, 'none')); continue
            ii, cc = np.unique(sub, return_counts=True)
            j = int(np.argmax(cc))
            gid = int(ii[j]) if cc[j] >= 0.3 * sub.size else 0
            gl = 'none' if gid == 0 or gt.code[gid] not in (1, 2, 3, 4, 5) else ('moving' if gid in mv else 'static')
            lab.append((gid, gl))
        for xi, x in enumerate(insts):
            if x.role != 'potential' or x.status == 'carried':
                continue
            gid, gl = lab[xi]
            if gl == 'none':
                sc = '-'
            elif gl == 'moving':
                sc = gt.cls[gid]
            else:
                c = gt.cls[gid]
                sc = ('forklift_parked' if c == 'forklift' else 'parked_load' if (c in ('box', 'pallet') and gt.carried_by(gid) is not None)
                      else 'person_static' if c == 'person' else 'free_static')
            touch = '-'
            par = '-'
            if gl == 'static' and x.status in ('promoted', 'held'):
                x0, y0, x1, y1 = x.bbox
                X0, Y0, X1, Y1 = max(0, x0 - 6), max(0, y0 - 6), min(ids0.shape[1], x1 + 6), min(ids0.shape[0], y1 + 6)
                dm = cv2.dilate(x.mask[Y0:Y1, X0:X1].astype(np.uint8), ker) > 0
                near = mov0[Y0:Y1, X0:X1] & dm & (ids0[Y0:Y1, X0:X1] != gid)
                touch = 'touch' if near.any() else 'notouch'
            if x.status == 'promoted' and 0 <= x.parent < len(insts):
                q = insts[x.parent]
                r, hop = x.parent, 1
                while 0 <= insts[r].parent < len(insts) and insts[r].status == 'promoted' and hop < 10:
                    r, hop = insts[r].parent, hop + 1
                par = f'{q.cls}:{lab[x.parent][1]}>{insts[r].cls}:{lab[r][1]}:{insts[r].status}:h{hop}'
            key = f'{x.status}|{gl}|{sc}|{touch}|{par}'
            e = counts.setdefault(key, [0, 0])
            e[0] += 1
            e[1] += int(x.mask.sum())
            if gid:
                inst.setdefault(x.status, {}).setdefault(gl, set()).add(gid)
    out = {'seq': seq, 'variant': var, 'pset': over, 'roles': roles, 'frames': len(stamps), 'counts': counts,
           'instances': {s: {k: sorted(v) for k, v in d.items()} for s, d in inst.items()},
           'n_static_movable_gt_in_view': len(static_in_view), 'per_frame': per_frame, 'runtime_s': round(time.time() - t_start, 1)}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, 'w'))
    return seq, var, out['runtime_s']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--seqs', required=True)
    ap.add_argument('--variants', required=True)
    ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    seqs = a.seqs.split(',')
    assert all('_t1_' in s for s in seqs), 'tuning set (t1) only'
    tasks = [(s, v, f'{a.out_dir}/{s}/{v}.json') for s in seqs for v in a.variants.split(',')
             if not os.path.isfile(f'{a.out_dir}/{s}/{v}.json')]
    print(len(tasks), 'tasks', flush=True)
    t0 = time.time()
    with mp.get_context('spawn').Pool(a.jobs, maxtasksperchild=1) as pool:
        for s, v, rt in pool.imap_unordered(run_one, tasks):
            print(f'{time.time() - t0:7.0f}s done {s} {v} ({rt}s)', flush=True)


if __name__ == '__main__':
    main()
