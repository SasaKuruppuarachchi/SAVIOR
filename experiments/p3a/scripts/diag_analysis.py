"""P3a feature-fate analysis from the diagnostic OpenVINS build log (diag_updates.csv) + oracle human masks.

diag rows:  T,t,init,cam,id,u,v           every kept feature of every frame (after the tracker)
            M,t,featid,status,n,chi2,thr  MSCKF update: few | trifail | chi2 | used
            SD,...                        SLAM delayed init: few | trifail | chi2 | init
            SU,...                        SLAM landmark update (per frame): chi2 | used
            C,t,featid,n                  dropped by max_msckf_in_update (may be retried later)
A track is "human" if >= 50 % of its observations lie on the oracle human mask (cam0: GT seg, cam1: the
oracle mask warped to the right camera by savior_node's stereo warp). Writes a YAML summary.

python3 diag_analysis.py --diag run_dir/diag_updates.csv --masks masks/<seq>_masks.npz --out out.yaml
"""
import argparse
import collections
import json

import cv2
import numpy as np
import yaml


def load_masks(fn, dilate=0):
    zf = np.load(fn)
    z = {k: zf[k] for k in zf.files}   # load once (NpzFile decompresses on every access)
    h, w = z['shape']
    st = z['stamp_ns']
    key = {int(round(s / 1000.0)): i for i, s in enumerate(st)}   # us -> index
    k = np.ones((2 * dilate + 1, 2 * dilate + 1), np.uint8) if dilate else None

    def get(arr, i):
        m = np.unpackbits(arr[i])[:h * w].reshape(h, w).astype(bool)
        if k is not None:
            m = cv2.dilate(m.view(np.uint8), k).astype(bool)
        return m
    return key, z, get


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--diag', required=True)
    ap.add_argument('--masks', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dilate', type=int, default=0)
    ap.add_argument('--init-time', type=float, default=None)
    a = ap.parse_args()

    obs = collections.defaultdict(list)          # id -> [(t, cam, u, v, init)]
    frames = collections.defaultdict(list)       # (t, cam) -> [(id, u, v)]
    M = collections.defaultdict(list)            # id -> [(t, status, n, chi2, thr)]
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
                t, ini, cam, fid, u, v = float(p[1]), int(p[2]), int(p[3]), int(p[4]), float(p[5]), float(p[6])
                obs[fid].append((t, cam, u, v, ini))
                frames[(t, cam)].append((fid, u, v))
            elif k in ('M', 'SD', 'SU'):
                rec = (float(p[1]), p[3], int(p[4]), float(p[5]) if p[5] else None, float(p[6]) if p[6] else None)
                {'M': M, 'SD': SD, 'SU': SU}[k][int(p[2])].append(rec)
            elif k == 'C':
                C[int(p[2])].append((float(p[1]), int(p[3])))

    key, z, get = load_masks(a.masks, a.dilate)
    on = {}                                      # (id, t, cam) -> bool
    frame_stats = []                             # per (t, cam): n kept, n on human
    for (t, cam), lst in sorted(frames.items()):
        i = key.get(int(round(t * 1e6)))
        if i is None:
            hits = [False] * len(lst)
        else:
            m = get(z['human'] if cam == 0 else z['right'], i)
            hits = []
            for fid, u, v in lst:
                x, y = int(round(u)), int(round(v))
                hits.append(bool(0 <= y < m.shape[0] and 0 <= x < m.shape[1] and m[y, x]))
        for (fid, _, _), hh in zip(lst, hits):
            on[(fid, t, cam)] = hh
        frame_stats.append((t, cam, len(lst), sum(hits)))
    fs = np.array([(t, c, n, h) for t, c, n, h in frame_stats])
    t_init = a.init_time
    if t_init is None:
        inits = [o[0] for ol in obs.values() for o in ol if o[4]]
        t_init = min(inits) if inits else None

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
        nh = sum(on[(fid, t, c)] for t, c, *_ in ol)
        frames_ = sorted({t for t, *_ in ol})
        post = any(o[4] for o in ol)
        su = SU.get(fid, [])
        tracks.append(dict(id=fid, n_obs=n, n_frames=len(frames_), n_human=nh, human=nh >= 0.5 * n, any_human=nh > 0,
                           post_init=post, fate=fate(fid), su_used=sum(1 for x in su if x[1] == 'used'),
                           su_chi2=sum(1 for x in su if x[1] == 'chi2'),
                           m_used_meas=sum(x[2] for x in M.get(fid, []) if x[1] == 'used'),
                           m_chi2=[x[3] / x[4] for x in M.get(fid, []) if x[3] is not None and x[4]]))

    def summarize(sel):
        out = {'n_tracks': len(sel)}
        if not sel:
            return out
        L = np.array([x['n_frames'] for x in sel])
        out.update(len_frames_mean=round(float(L.mean()), 2), len_frames_median=float(np.median(L)),
                   len_frames_p90=float(np.percentile(L, 90)), n_obs_total=int(sum(x['n_obs'] for x in sel)))
        cnt = collections.Counter(x['fate'] for x in sel)
        out['fate'] = {k: int(v) for k, v in sorted(cnt.items())}
        out['fate_frac'] = {k: round(v / len(sel), 4) for k, v in sorted(cnt.items())}
        nu, nr = cnt.get('used', 0), cnt.get('chi2', 0)
        out['msckf_chi2_reject_rate'] = round(nr / (nu + nr), 4) if nu + nr else None
        sl = [x for x in sel if x['fate'] == 'slam']
        su_u = sum(x['su_used'] for x in sl)
        su_r = sum(x['su_chi2'] for x in sl)
        out['slam_landmarks'] = len(sl)
        out['slam_update_meas'] = su_u + su_r
        out['slam_update_chi2_reject_rate'] = round(su_r / (su_u + su_r), 4) if su_u + su_r else None
        out['msckf_used_meas'] = int(sum(x['m_used_meas'] for x in sel))
        r = np.array([v for x in sel for v in x['m_chi2']])
        if r.size:
            out['msckf_chi2_over_thr_median'] = round(float(np.median(r)), 3)
        return out

    post = [x for x in tracks if x['post_init']]
    res = {
        'diag': a.diag, 'masks': a.masks, 'dilate_px': a.dilate, 'init_time': t_init,
        'frames_cam0': int((fs[:, 1] == 0).sum()),
        'kept_per_frame_cam0': round(float(fs[fs[:, 1] == 0, 2].mean()), 2),
        'kept_on_human_per_frame_cam0': round(float(fs[fs[:, 1] == 0, 3].mean()), 3),
        'frac_kept_obs_on_human_cam0': round(float(fs[fs[:, 1] == 0, 3].sum() / fs[fs[:, 1] == 0, 2].sum()), 5),
        'frac_kept_obs_on_human_cam1': round(float(fs[fs[:, 1] == 1, 3].sum() / max(1, fs[fs[:, 1] == 1, 2].sum())), 5),
        'frames_with_feature_on_human_cam0': round(float((fs[fs[:, 1] == 0, 3] > 0).mean()), 4),
        'max_kept_on_human_cam0': int(fs[fs[:, 1] == 0, 3].max()),
        'post_init': {'all': summarize(post), 'human': summarize([x for x in post if x['human']]),
                      'non_human': summarize([x for x in post if not x['human']]),
                      'any_human_obs': summarize([x for x in post if x['any_human']])},
        'pre_init_only': {'all': summarize([x for x in tracks if not x['post_init']]),
                          'human': summarize([x for x in tracks if not x['post_init'] and x['human']])},
    }
    # share of the information actually used: MSCKF-used features and SLAM-update measurements that are human
    used = [x for x in post if x['fate'] == 'used']
    res['post_init']['frac_msckf_used_tracks_human'] = round(sum(x['human'] for x in used) / max(1, len(used)), 5)
    res['post_init']['frac_msckf_used_meas_human'] = round(sum(x['m_used_meas'] for x in used if x['human']) /
                                                          max(1, sum(x['m_used_meas'] for x in used)), 5)
    su_all = sum(x['su_used'] for x in post)
    res['post_init']['frac_slam_update_meas_human'] = round(sum(x['su_used'] for x in post if x['human']) / max(1, su_all), 5)
    # per-frame timeline (cam0) for figures
    tl = fs[fs[:, 1] == 0]
    np.savez_compressed(a.out.replace('.yaml', '_timeline.npz'), t=tl[:, 0], kept=tl[:, 2], on_human=tl[:, 3])
    with open(a.out, 'w') as fh:
        yaml.safe_dump(json.loads(json.dumps(res)), fh, sort_keys=False)
    print(yaml.safe_dump(json.loads(json.dumps(res)), sort_keys=False))


if __name__ == '__main__':
    main()
