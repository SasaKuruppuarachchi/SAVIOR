#!/usr/bin/env python3
"""stats3_viode_diag.py : VIODE failure diagnosis (existing runs only).

For OpenVINS-v2 (+SAVIOR), OpenVINS-v1 (M2b, +SAVIOR), VINS-Fusion (+SAVIOR), DynaVINS and ORB-SLAM3:
  - which (sequence, offset) fail (ATE posyaw > 1 m, or status != ok), per offset index;
  - start offset relative to the motion onset (from GT speed), init delay (first pose - playback start);
  - time to divergence: estimate aligned (posyaw: yaw + translation, closed form) to GT on its first 5 s of poses, then the
    first time the position error exceeds 1 m (relative to the first pose and to the playback start);
  - clustering at late offsets: stratified exact-conditional permutation test (failure labels permuted across the
    offsets within each sequence, 200000 Monte Carlo draws), statistic = sum of offset indices of failed runs (one-sided,
    late) + Spearman of per-offset failure counts.
Playback start = first GT stamp + start offset (GT /odometry starts with the bag).
-> results/stats_v3/tables/viode_diag.json|md"""
import csv
import json
import math
import os

import numpy as np
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
OUT = R + '/stats_v3/tables'
FM = 1.0
SEQS = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
OFFS = {}
for line in open(WS + '/src/savior/sota/scripts/viode_offsets.txt'):
    if line.strip() and not line.startswith('#'):
        s, o = line.split()
        OFFS[s] = [float(x) for x in o.split(',')]
B = json.load(open(f'{R}/backend_v2/tables/ate_viode.json'))['values']
V = json.load(open(f'{R}/vins_savior/heldout/tables_viode/ate.json'))['values']
ORB = {}
for r in csv.DictReader(open(f'{R}/sota/tables/merge_viode.csv')):
    if r['method'] == 'orbslam3':
        v = float(r['ate_posyaw_m']) if r['ate_posyaw_m'] not in ('', 'nan') else math.inf
        ORB.setdefault(r['seq'], {})[str(int(r['run']))] = math.inf if math.isnan(v) else v
SYS = {  # name -> (ATE dict, trajectory path pattern)
    'OpenVINS-v2': ({s: B['v2'][s]['openvins'] for s in SEQS}, R + '/backend_v2/heldout/runs/{s}/openvins/run_{i:02d}'),
    'OV-v2+SAVIOR': ({s: B['v2'][s]['sens_fix1'] for s in SEQS}, R + '/backend_v2/heldout/runs/{s}/sens_fix1/run_{i:02d}'),
    'OpenVINS-v1': ({s: B['v1'][s]['openvins'] for s in SEQS}, R + '/m2b_heldout/runs/{s}/openvins/run_{i:02d}'),
    'OV-v1+SAVIOR': ({s: B['v1'][s]['sens_fix1'] for s in SEQS}, R + '/m2b_heldout/runs/{s}/sens_fix1/run_{i:02d}'),
    'VINS-Fusion': ({s: V[s]['vins_fusion'] for s in SEQS}, R + '/vins_savior/heldout/runs_viode/viode_{s}/vins_fusion/run_{i:02d}'),
    'VINS+SAVIOR': ({s: V[s]['vins_savior'] for s in SEQS}, R + '/vins_savior/heldout/runs_viode/viode_{s}/vins_savior/run_{i:02d}'),
    'DynaVINS': ({s: V[s]['dynavins'] for s in SEQS}, R + '/sota/viode_{s}/dynavins/run_{i:02d}'),
    'ORB-SLAM3': (ORB, R + '/sota/viode_{s}/orbslam3/run_{i:02d}'),
}


def readtraj(fn):
    if not os.path.isfile(fn):
        return None
    a = np.loadtxt(fn, comments='#', ndmin=2)
    return a if a.size else None


GT = {s: readtraj(f'{WS}/data/viode/gt/{s}.txt') for s in SEQS}


def onset(g):
    t, p = g[:, 0], g[:, 1:4]
    dt = np.gradient(t)
    v = np.linalg.norm(np.gradient(p, axis=0), axis=1) / np.maximum(dt, 1e-6)
    k = np.argmax(v > 0.1)
    return t[k] - t[0]


ONSET = {s: onset(GT[s]) for s in SEQS}


def posyaw(pe, pg):
    me, mg = pe.mean(0), pg.mean(0)
    a, b = pe - me, pg - mg
    th = math.atan2((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum(), (a[:, 0] * b[:, 0] + a[:, 1] * b[:, 1]).sum())
    Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    return Rz, mg - Rz @ me


def diag_run(s, i, path):
    g = GT[s]
    t0 = g[0, 0]
    play = t0 + OFFS[s][i - 1]
    e = readtraj(path + '/stamped_traj_estimate.txt')
    d = dict(offset_s=OFFS[s][i - 1], start_rel_onset_s=round(OFFS[s][i - 1] - ONSET[s], 2))
    if e is None:
        d.update(n_poses=0)
        return d
    d['n_poses'] = int(e.shape[0])
    d['init_delay_s'] = float(e[0, 0] - play)
    j = np.clip(np.searchsorted(g[:, 0], e[:, 0]), 1, len(g) - 1)
    j = np.where(np.abs(g[j - 1, 0] - e[:, 0]) < np.abs(g[j, 0] - e[:, 0]), j - 1, j)
    ok = np.abs(g[j, 0] - e[:, 0]) < 0.02
    if ok.sum() < 10:
        return d
    te, pe, pg = e[ok, 0], e[ok, 1:4], g[j[ok], 1:4]
    d['dur_s'] = float(te[-1] - te[0])
    for W in (1.0, 5.0):
        w = te <= te[0] + W
        if w.sum() < 5:
            w = np.arange(te.size) < 5
        Rz, tr = posyaw(pe[w], pg[w])
        err = np.linalg.norm((pe @ Rz.T + tr) - pg, axis=1)
        k = np.argmax(err > FM) if (err > FM).any() else None
        d[f'err_win{W:g}s_max_m'] = float(err[w].max())
        if k is not None:
            d[f't_div_w{W:g}_s'] = float(te[k] - te[0])
    # alignment-free blow-up: estimated speed > 2 x max GT speed + 1 m/s
    ve = np.linalg.norm(np.diff(pe, axis=0), axis=1) / np.maximum(np.diff(te), 1e-3)
    vg = np.linalg.norm(np.diff(g[:, 1:4], axis=0), axis=1) / np.maximum(np.diff(g[:, 0]), 1e-3)
    lim = 2 * np.percentile(vg, 99.5) + 1.0
    kb = np.argmax(ve > lim) if (ve > lim).any() else None
    d['t_blowup_s'] = None if kb is None else float(te[kb + 1] - te[0])
    d['t_div_s'] = d.get('t_div_w1_s')
    return d


def perm_late(F, nperm=200000, seed=0):
    """F: (n_seq, 10) bool. one-sided p for 'failures at later offsets' conditional on per-sequence counts"""
    rng = np.random.default_rng(seed)
    idx = np.arange(1, 11)
    obs = (F * idx).sum()
    tot = np.zeros(nperm)
    for f in F:
        c = int(f.sum())
        if c in (0, 10):
            tot += c and idx.sum()
            continue
        r = rng.random((nperm, 10)).argsort(axis=1)[:, :c] + 1
        tot += r.sum(axis=1)
    return float(((tot >= obs - 1e-9).sum() + 1) / (nperm + 1)), float(obs), float(tot.mean())


def main():
    out = dict(onset_s=ONSET, systems={})
    for name, (ate, pat) in SYS.items():
        runs = []
        F = np.zeros((len(SEQS), 10), bool)
        for a, s in enumerate(SEQS):
            for i in range(1, 11):
                v = float(ate[s][str(i)])
                F[a, i - 1] = v > FM
                d = dict(seq=s, run=i, ate=v, fail=bool(v > FM))
                if v > FM:
                    d.update(diag_run(s, i, pat.format(s=s, i=i)))
                else:
                    d.update(offset_s=OFFS[s][i - 1], start_rel_onset_s=round(OFFS[s][i - 1] - ONSET[s], 2))
                runs.append(d)
        per_off = F.sum(axis=0).tolist()
        p_late, obs, exp = perm_late(F) if F.any() else (1.0, 0, 0)
        rho = stats.spearmanr(np.arange(1, 11), per_off) if F.any() and len(set(per_off)) > 1 else None
        early, late = int(F[:, :5].sum()), int(F[:, 5:].sum())
        fseq = {s: [i + 1 for i in np.where(F[a])[0]] for a, s in enumerate(SEQS) if F[a].any()}
        out['systems'][name] = dict(fails=int(F.sum()), per_offset=per_off, early_1_5=early, late_6_10=late,
                                    p_perm_late=p_late, sum_idx_obs=obs, sum_idx_exp=exp,
                                    spearman=None if rho is None else [float(rho.statistic), float(rho.pvalue)],
                                    fail_seq_offsets=fseq, runs=[r for r in runs if r['fail']])
        print(name, int(F.sum()), per_off, 'p_late', p_late)
    json.dump(out, open(OUT + '/viode_diag.json', 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
