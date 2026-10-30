#!/usr/bin/env python3
"""equiv_offline.py --seq <t1 seq> --method sens_fix1|p7_nb --out <json> [--cache DIR] [--max-frames N] [--threads 4]

Offline Python <-> C++ equivalence of the SAVIOR perception pipeline on identical inputs: the raw stereo frames + gyro of a
t1 warehouse bag and the cached YOLO detections (detcache.py: deployed engine, fast_masks; identical to the node's), the
same flat configuration (built-in defaults + savior_perception_yolo.yaml + the frozen method overrides of
results/p7/final_config.yaml) and the same gyro rotation (Python GyroIntegrator) are fed frame by frame to
savior_perception.core.pipeline.SaviorPipeline (reference) and to the C++ port (pybind11 module savior_cpp), each keeping its
own state (closed offline loop, no re-synchronisation). Per frame and per stage it records:
  depth (disparity / n_depth_px per detection), motion (track id, state, log-odds, observation, selective label),
  gating (status, parent, links), tracker (track ids, carried instances), masks (left/right pixel agreement, core IoU),
  counters, and the per-stage CPU time of both implementations.
TUNING SET (t1) ONLY.
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import cv2  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
B = WS + '/src/savior/savior_bringup/config'
SCR = os.environ.get('SAVIOR_SCRATCH', '/tmp/savior')   # scratch dir (detection cache etc.)
FINAL = WS + '/results/p7/final_config.yaml'


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flatten(v, f'{prefix}{k}.'))
        else:
            out[f'{prefix}{k}'] = v
    return out


def method_params(method):
    from savior_perception.params import all_defaults
    P = all_defaults()
    y = yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))
    P.update(flatten(y['savior_node']['ros__parameters']))
    m = yaml.safe_load(open(FINAL))['methods'][method]
    P.update(m.get('savior_node', {}))
    roles = m['roles_file'].split('/')[-1].replace('.yaml', '')
    return P, roles


def load_frames(seq):
    from rosbags.highlevel import AnyReader
    from savior_perception.core.motion import GyroIntegrator
    g = GyroIntegrator(max_age_s=1e9)
    frames, imu_t, imu_w = {}, [], []
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
        conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw', '/cam1/image_raw')]
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            if c.topic == '/imu0':
                w = m.angular_velocity
                g.add(st * 1e-9, (w.x, w.y, w.z))
                imu_t.append(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)
                imu_w.append((w.x, w.y, w.z))
            else:
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
    return g, frames, imu_t, imu_w


class DetCache:
    def __init__(self, path):
        z = np.load(path)
        self.h, self.w = (int(v) for v in z['shape'])
        self.cls, self.score, self.bbox, self.bits = z['cls'], z['score'], z['bbox'], z['bits']
        self.offs = np.concatenate([[0], np.cumsum(z['lens'])])
        first = np.concatenate([[0], np.cumsum(z['nper'])])
        self.idx = {int(st): (int(first[j]), int(first[j + 1])) for j, st in enumerate(z['stamps'])}

    def get(self, st):
        a, b = self.idx.get(int(st), (0, 0))
        out = []
        for j in range(a, b):
            x0, y0, x1, y1 = (int(v) for v in self.bbox[j])
            n = (y1 - y0) * (x1 - x0)
            crop = np.unpackbits(self.bits[self.offs[j]:self.offs[j + 1]])[:n].reshape(y1 - y0, x1 - x0)
            out.append((crop, str(self.cls[j]), float(self.score[j]), (x0, y0, x1, y1)))
        return out


def fz(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def motion_key(mo):
    if not mo:
        return None
    return (mo.get('id'), mo.get('state'), mo.get('l'), mo.get('obs'), mo.get('sel'), mo.get('sel_obs'), bool(mo.get('dup')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True)
    ap.add_argument('--method', default='sens_fix1')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cache', default=SCR + '/detcache')
    ap.add_argument('--max-frames', type=int, default=0)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--dump-masks', default='', help='npz of the per-frame differing mask pixels (debug)')
    a = ap.parse_args()
    assert '_t1_' in a.seq, 'tuning set (t1) only'
    cv2.setNumThreads(a.threads)
    import savior_cpp
    savior_cpp.set_num_threads(a.threads)
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.config import PipelineConfig
    from savior_perception.core.pipeline import SaviorPipeline
    from savior_perception.core.roles import RoleTable
    from savior_perception.core.types import Instance
    P, roles = method_params(a.method)
    flat = {k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS}
    cfg = PipelineConfig.from_flat(flat)
    calib = f'{B}/warehouse/kalibr_imucam_chain.yaml'
    rect = stereo_from_kalibr(calib, 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    roles_file = f'{B}/roles/{roles}.yaml'
    py = SaviorPipeline(cfg, RoleTable.from_yaml(roles_file), rect)
    cp = savior_cpp.Pipeline(flat, roles_file, calib)
    ri = cp.rect_info()
    rect_same = (abs(ri['f'] - rect.f) == 0 and tuple(ri['rect_size']) == tuple(rect.rect_size)
                 and ri['cx'] == rect.cx and ri['cy'] == rect.cy and ri['baseline'] == rect.baseline)
    g, frames, imu_t, imu_w = load_frames(a.seq)
    dets = DetCache(f'{a.cache}/{a.seq}.npz')
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    if a.max_frames:
        stamps = stamps[:a.max_frames]
    # node path: C++ gyro integration of the same sample stream vs the Python GyroIntegrator
    ft = [s * 1e-9 for s in stamps]
    Rc = savior_cpp.gyro_rotations(imu_t, imu_w, ft)
    gyro_maxdiff = 0.0
    R_py = [None]
    for k in range(1, len(ft)):
        R = g.rotation(ft[k - 1], ft[k])
        R_py.append(R)
        if R is not None and Rc[k] is not None:
            gyro_maxdiff = max(gyro_maxdiff, float(np.abs(np.asarray(Rc[k]) - R).max()))
        elif (R is None) != (Rc[k] is None):
            gyro_maxdiff = float('inf')
    acc = {'frames': 0, 'px_total': 0, 'L_eq_px': 0, 'R_eq_px': 0, 'L_core_inter': 0, 'L_core_union': 0,
           'R_core_inter': 0, 'R_core_union': 0, 'L_frames_identical': 0, 'R_frames_identical': 0,
           'inst_frames': 0, 'inst_count_mismatch_frames': 0, 'disp_equal': 0, 'disp_both_nan': 0, 'disp_absdiff_max': 0.0,
           'ndepth_equal': 0, 'status_equal': 0, 'parent_equal': 0, 'track_equal': 0, 'motion_equal': 0,
           'motion_frames_identical': 0, 'links_frames_identical': 0, 'status_frames_identical': 0,
           'counts_frames_identical': 0, 'decision_frames_identical': 0, 'egostats_frames_identical': 0,
           'first_div': {}, 'n_links_py': 0, 'n_links_cpp': 0}
    tim = {'py': {}, 'cpp': {}}
    diffs = []
    t_start = time.time()
    prev_t = None
    for k, st in enumerate(stamps):
        left, right = frames[st]
        t = st * 1e-9
        R_imu = R_py[k] if k > 0 else None
        prev_t = t
        dl = dets.get(st)
        insts = []
        for crop, c, s, bb in dl:
            m = np.zeros((dets.h, dets.w), bool)
            m[bb[1]:bb[3], bb[0]:bb[2]] = crop.astype(bool)
            insts.append(Instance(mask=m, cls=c, score=s, bbox=bb))
        tp0 = time.perf_counter()
        ml_p, mr_p, st_p = py.process(left, right, t, insts, R_imu=R_imu)
        tp1 = time.perf_counter()
        out = cp.process(left, right, t, dl, R_imu)
        tp2 = time.perf_counter()
        for kk, v in st_p['timings_ms'].items():
            tim['py'].setdefault(kk, []).append(v)
        tim['py'].setdefault('call', []).append((tp1 - tp0) * 1e3)
        for kk, v in out['timings'].items():
            tim['cpp'].setdefault(kk, []).append(v)
        tim['cpp'].setdefault('call', []).append((tp2 - tp1) * 1e3)
        tim['py'].setdefault('m_flow_ego', []).append(st_p.get('motion', {}).get('ms', {}).get('flow_ego', 0.0))
        tim['py'].setdefault('m_assoc', []).append(st_p.get('motion', {}).get('ms', {}).get('assoc', 0.0))
        tim['py'].setdefault('m_points', []).append(st_p.get('motion', {}).get('ms', {}).get('points', 0.0))
        ml_c, mr_c = out['mask_left'], out['mask_right']
        acc['frames'] += 1
        npx = ml_p.size
        acc['px_total'] += npx
        eqL = int(np.count_nonzero(ml_p == ml_c))
        eqR = int(np.count_nonzero(mr_p == mr_c))
        acc['L_eq_px'] += eqL
        acc['R_eq_px'] += eqR
        acc['L_frames_identical'] += int(eqL == npx)
        acc['R_frames_identical'] += int(eqR == npx)
        for side, mp_, mc_ in (('L', ml_p, ml_c), ('R', mr_p, mr_c)):
            a_, b_ = mp_ == 255, mc_ == 255
            acc[f'{side}_core_inter'] += int(np.count_nonzero(a_ & b_))
            acc[f'{side}_core_union'] += int(np.count_nonzero(a_ | b_))
        res = py.last_result
        pi, ci = res.instances, out['instances']
        frame_diff = []
        if len(pi) != len(ci):
            acc['inst_count_mismatch_frames'] += 1
            frame_diff.append(f'n_inst {len(pi)} vs {len(ci)}')
        same_status = same_motion = True
        for x, y in zip(pi, ci):
            acc['inst_frames'] += 1
            dp, dc = fz(x.disparity), y['disparity']
            if dp is None and dc is None:
                acc['disp_both_nan'] += 1
                acc['disp_equal'] += 1
            elif dp is not None and dc is not None:
                acc['disp_equal'] += int(dp == dc)
                acc['disp_absdiff_max'] = max(acc['disp_absdiff_max'], abs(dp - dc))
                if dp != dc:
                    frame_diff.append(f'disp {x.cls} {dp} vs {dc}')
            else:
                frame_diff.append(f'disp nan-mismatch {x.cls} {dp} vs {dc}')
            acc['ndepth_equal'] += int(x.n_depth_px == y['n_depth_px'] or x.status == 'carried')
            s_eq = x.status == y['status']
            acc['status_equal'] += int(s_eq)
            same_status &= s_eq and tuple(x.bbox) == tuple(y['bbox'])
            acc['parent_equal'] += int(x.parent == y['parent'])
            acc['track_equal'] += int(x.track_id == y['track_id'])
            mk_p, mk_c = motion_key(x.motion), motion_key(y['motion'])
            m_eq = mk_p == mk_c
            acc['motion_equal'] += int(m_eq)
            same_motion &= m_eq
            if not s_eq:
                frame_diff.append(f'status {x.cls} {x.status} vs {y["status"]}')
            if not m_eq:
                frame_diff.append(f'motion {x.cls} {mk_p} vs {mk_c}')
        same_status &= len(pi) == len(ci)
        same_motion &= len(pi) == len(ci)
        links_eq = [tuple(l) for l in res.links] == [tuple(l) for l in out['links']]
        acc['n_links_py'] += len(res.links)
        acc['n_links_cpp'] += len(out['links'])
        acc['links_frames_identical'] += int(links_eq)
        acc['status_frames_identical'] += int(same_status)
        acc['motion_frames_identical'] += int(same_motion)
        counts_eq = all(st_p[kk] == v for kk, v in (('n_roots', sum(1 for y in ci[:st_p['n_instances']] if y['status'] == 'root')),))
        cnt_p = (st_p['n_roots'], st_p['n_promoted'], st_p['n_held'], st_p['n_carried'], st_p['n_tracks'], st_p['core_px'],
                 st_p['ext_px'], st_p.get('selective', {}).get('n_uncertain'), st_p.get('selective', {}).get('converged'))
        n_det = st_p['n_instances']
        cnt_c = (sum(1 for y in ci[:n_det] if y['status'] == 'root'), sum(1 for y in ci[:n_det] if y['status'] == 'promoted'),
                 sum(1 for y in ci[:n_det] if y['status'] == 'held'), sum(1 for y in ci[n_det:] if y['status'] == 'carried'),
                 out['n_tracks'], out['core_px'], out['ext_px'], sum(1 for y in ci[:n_det] if y['status'] == 'uncertain'),
                 out['selective'].get('converged'))
        counts_eq = cnt_p == cnt_c
        acc['counts_frames_identical'] += int(counts_eq)
        acc['decision_frames_identical'] += int(same_status and links_eq and same_motion)
        mp = st_p.get('motion', {})
        mc = out['motion']
        ego_eq = (mp.get('n_bg') == mc.get('n_bg') and mp.get('n_inl') == mc.get('n_inl') and mp.get('t_ok') == mc.get('t_ok')
                  and mp.get('n_tracks') == mc.get('n_tracks') and mp.get('n_inst_pts') == mc.get('n_inst_pts'))
        acc['egostats_frames_identical'] += int(ego_eq)
        if not ego_eq:
            frame_diff.append(f'ego {mp.get("n_bg")},{mp.get("n_inl")},{mp.get("n_tracks")},{mp.get("n_inst_pts")} vs '
                              f'{mc.get("n_bg")},{mc.get("n_inl")},{mc.get("n_tracks")},{mc.get("n_inst_pts")}')
        for key, ok in (('masks_L', eqL == npx), ('masks_R', eqR == npx), ('status', same_status), ('motion', same_motion),
                        ('links', links_eq), ('ego_stats', ego_eq), ('counts', counts_eq)):
            if not ok and key not in acc['first_div']:
                acc['first_div'][key] = k
        if frame_diff or eqL != npx or eqR != npx:
            diffs.append({'k': k, 'stamp': st, 'L_diff_px': npx - eqL, 'R_diff_px': npx - eqR, 'items': frame_diff[:12]})
    def pct(v):
        v = np.asarray(v, float)
        return {'mean': round(float(v.mean()), 4), 'p50': round(float(np.percentile(v, 50)), 4),
                'p90': round(float(np.percentile(v, 90)), 4), 'p99': round(float(np.percentile(v, 99)), 4)}
    out = {'seq': a.seq, 'method': a.method, 'threads': a.threads, 'opencv_py': cv2.__version__,
           'opencv_cpp': savior_cpp.opencv_version, 'rect_identical': bool(rect_same), 'gyro_maxabs_diff': gyro_maxdiff,
           'acc': acc, 'timing_ms': {s: {kk: pct(v) for kk, v in d.items()} for s, d in tim.items()},
           'n_diff_frames': len(diffs), 'diffs': diffs[:400], 'runtime_s': round(time.time() - t_start, 1)}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    A = acc
    print(f"{a.seq} {a.method}: frames {A['frames']} L px agree {A['L_eq_px'] / A['px_total']:.6f} R {A['R_eq_px'] / A['px_total']:.6f}"
          f" L identical frames {A['L_frames_identical']} decisions identical {A['decision_frames_identical']} "
          f"first_div {A['first_div']} ({out['runtime_s']} s)", flush=True)


if __name__ == '__main__':
    main()
