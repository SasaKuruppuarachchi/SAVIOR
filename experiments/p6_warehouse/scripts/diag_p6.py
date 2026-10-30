#!/usr/bin/env python3
"""P6 feature-fate analysis from the diagnostic OpenVINS build log (diag_updates.csv, P3a/P5 patch) + the
SAVIOR-Warehouse GT instance images (scripts/wh_gt.py, cam0 = seg0, cam1 = seg1, per-frame moving flags).

Every kept feature observation (T line: t, init, cam, id, u, v) gets the GT category of its pixel in that frame
(moving_<cls> / static_<cls> / struct / bg, wh_gt.CAT_NAMES). A track is "on a moving object" (P5 "human" key) if
>= 50 % of its observations are on moving pixels; the same definitions as diag_p5.py (P5 VIODE), so the P5 and P6
share-vs-gain points can be combined: kept share = share of kept cam0 observations (whole run) on moving objects,
MSCKF-used share = share of the measurements of post-init MSCKF-used tracks that belong to moving tracks.
Additionally: the kept / used share on STATIC potentially-dynamic objects (parked forklifts, pallets, boxes, standing
people, trolleys) = what naive class masking throws away.

python3 diag_p6.py --diag run_dir/diag_updates.csv --seq <seq> --out out.yaml
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wh_gt import CAT_NAMES, SeqGT  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diag', required=True)
    ap.add_argument('--seq', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    gt = SeqGT(a.seq)
    obs = collections.defaultdict(list)          # id -> [(t, cam, cat, init)]
    frames = collections.defaultdict(list)       # (t, cam) -> [(id, u, v, init)]
    M = collections.defaultdict(list)
    SD = collections.defaultdict(list)
    SU = collections.defaultdict(list)
    C = collections.defaultdict(list)
    with open(a.diag) as fh:
        for line in fh:
            if line.startswith('#'):
                continue
            p = line.rstrip('\n').split(',')
            k = p[0]
            if k == 'T':
                frames[(float(p[1]), int(p[3]))].append((int(p[4]), float(p[5]), float(p[6]), int(p[2])))
            elif k in ('M', 'SD', 'SU'):
                rec = (float(p[1]), p[3], int(p[4]), float(p[5]) if p[5] else None, float(p[6]) if p[6] else None)
                {'M': M, 'SD': SD, 'SU': SU}[k][int(p[2])].append(rec)
            elif k == 'C':
                C[int(p[2])].append((float(p[1]), int(p[3])))
    cnt = {0: collections.Counter(), 1: collections.Counter()}
    cnt_post = {0: collections.Counter(), 1: collections.Counter()}
    nmiss = 0
    for (t, cam), lst in sorted(frames.items()):
        ns = gt.stamp_from_sec(t)
        if ns is None:
            nmiss += len(lst)
            continue
        cat = gt.category_image(cam, ns)
        h, w = cat.shape
        for fid, u, v, ini in lst:
            x, y = int(round(u)), int(round(v))
            c = int(cat[y, x]) if (0 <= y < h and 0 <= x < w) else 0
            obs[fid].append((t, cam, c, ini))
            cnt[cam][c] += 1
            if ini:
                cnt_post[cam][c] += 1

    def is_mov(c):
        return c >= 11

    def is_spot(c):
        return 1 <= c <= 5

    def fate(fid):
        if SD.get(fid) and SD[fid][-1][1] == 'init':
            return 'slam'
        if M.get(fid):
            return M[fid][-1][1]
        if SD.get(fid):
            return 'slam_' + SD[fid][-1][1]
        if C.get(fid):
            return 'cap_dropped'
        return 'no_update'

    tracks = []
    for fid, ol in obs.items():
        n = len(ol)
        nm = sum(is_mov(o[2]) for o in ol)
        ns_ = sum(is_spot(o[2]) for o in ol)
        su = SU.get(fid, [])
        tracks.append(dict(id=fid, n=n, frames=len({o[0] for o in ol}), mov=nm >= 0.5 * n, spot=ns_ >= 0.5 * n,
                           post=any(o[3] for o in ol), fate=fate(fid),
                           su_used=sum(1 for x in su if x[1] == 'used'), su_chi2=sum(1 for x in su if x[1] == 'chi2'),
                           m_used_meas=sum(x[2] for x in M.get(fid, []) if x[1] == 'used')))

    def summ(sel):
        out = {'n_tracks': len(sel)}
        if not sel:
            return out
        L = np.array([x['frames'] for x in sel])
        c = collections.Counter(x['fate'] for x in sel)
        nu, nr = c.get('used', 0), c.get('chi2', 0)
        out.update(len_frames_median=float(np.median(L)), len_frames_mean=round(float(L.mean()), 2),
                   fate_frac={k: round(v / len(sel), 4) for k, v in sorted(c.items())},
                   msckf_chi2_reject_rate=round(nr / (nu + nr), 4) if nu + nr else None,
                   msckf_used_meas=int(sum(x['m_used_meas'] for x in sel)),
                   slam_update_meas=int(sum(x['su_used'] for x in sel)),
                   slam_chi2_reject_rate=(round(sum(x['su_chi2'] for x in sel) / max(1, sum(x['su_used'] + x['su_chi2'] for x in sel)), 4)))
        return out

    post = [x for x in tracks if x['post']]
    used = [x for x in post if x['fate'] == 'used']
    tot_used = max(1, sum(x['m_used_meas'] for x in used))
    su_all = max(1, sum(x['su_used'] for x in post))

    def share(counter, pred):
        n = sum(counter.values())
        return round(sum(v for k, v in counter.items() if pred(k)) / max(1, n), 5)
    res = {
        'diag': a.diag, 'seq': a.seq, 'obs_without_gt_frame': nmiss,
        'kept_obs_cam0': int(sum(cnt[0].values())), 'kept_obs_cam1': int(sum(cnt[1].values())),
        'frames_cam0': int(sum(1 for (t, c) in frames if c == 0)),
        'kept_per_frame_cam0': round(sum(cnt[0].values()) / max(1, sum(1 for (t, c) in frames if c == 0)), 2),
        # P5-compatible keys ("human" = on a MOVING object)
        'frac_kept_obs_on_human_cam0': share(cnt[0], is_mov),
        'frac_kept_obs_on_human_cam1': share(cnt[1], is_mov),
        'frac_kept_obs_on_static_potential_cam0': share(cnt[0], is_spot),
        'frac_kept_obs_on_static_potential_cam1': share(cnt[1], is_spot),
        'frac_kept_obs_on_static_potential_cam0_post_init': share(cnt_post[0], is_spot),
        'kept_obs_by_category_cam0': {CAT_NAMES.get(k, str(k)): round(v / max(1, sum(cnt[0].values())), 5) for k, v in sorted(cnt[0].items())},
        'post_init': {
            'all': summ(post), 'human': summ([x for x in post if x['mov']]),
            'non_human': summ([x for x in post if not x['mov']]),
            'static_potential': summ([x for x in post if x['spot']]),
            'frac_msckf_used_meas_human': round(sum(x['m_used_meas'] for x in used if x['mov']) / tot_used, 5),
            'frac_msckf_used_meas_static_potential': round(sum(x['m_used_meas'] for x in used if x['spot']) / tot_used, 5),
            'frac_slam_update_meas_human': round(sum(x['su_used'] for x in post if x['mov']) / su_all, 5),
            'frac_slam_update_meas_static_potential': round(sum(x['su_used'] for x in post if x['spot']) / su_all, 5),
        },
    }
    with open(a.out, 'w') as fh:
        yaml.safe_dump(json.loads(json.dumps(res)), fh, sort_keys=False)
    print(json.dumps({k: res[k] for k in ('seq', 'frac_kept_obs_on_human_cam0', 'frac_kept_obs_on_static_potential_cam0')}))


if __name__ == '__main__':
    main()
