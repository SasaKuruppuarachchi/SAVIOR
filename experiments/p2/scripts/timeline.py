"""Per-time ATE error (posyaw, full alignment) of several runs + front-end evidence, one PNG.

python3 timeline.py --gt GT --run label=RUN_DIR ... --out fig.png [--savior RUN_DIR]
"""
import argparse
import csv
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_eval')
from savior_eval.tum_io import load_tum  # noqa: E402
from savior_eval.third_party.rpg_trajectory_evaluation.align_trajectory import align_umeyama  # noqa: E402

COLS = ['#2a78d6', '#eb6834', '#1baf7a', '#6250d6', '#e34948']


def errors(est_fn, gt):
    est = load_tum(est_fn)
    tg = gt[:, 0]
    idx = np.searchsorted(tg, est[:, 0])
    idx = np.clip(idx, 1, len(tg) - 1)
    best = np.where(np.abs(tg[idx - 1] - est[:, 0]) < np.abs(tg[idx] - est[:, 0]), idx - 1, idx)
    ok = np.abs(tg[best] - est[:, 0]) < 0.02
    e, g = est[ok], gt[best[ok]]
    s, R, t = align_umeyama(g[:, 1:4], e[:, 1:4], known_scale=True, yaw_only=True)
    p = (s * (R @ e[:, 1:4].T)).T + t
    return e[:, 0], np.linalg.norm(p - g[:, 1:4], axis=1)


def feat(run):
    rows = list(csv.DictReader(open(run + '/feature_stats.csv')))
    t = np.array([float(r['timestamp']) for r in rows])
    c = np.array([int(r['cam_id']) for r in rows])
    kept = np.array([int(r['n_tracked']) + int(r['n_new']) for r in rows])
    m = c == 0
    return t[m], kept[m]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gt', required=True)
    ap.add_argument('--run', action='append', required=True)
    ap.add_argument('--savior', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    gt = load_tum(a.gt)
    t0 = gt[0, 0]
    fig, ax = plt.subplots(3, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
    for i, spec in enumerate(a.run):
        lab, run = spec.split('=', 1)
        t, e = errors(run + '/stamped_traj_estimate.txt', gt)
        ax[0].plot(t - t0, e, color=COLS[i], lw=1.5, label=f'{lab} (RMSE {np.sqrt(np.mean(e ** 2)):.3f} m)')
        tf, k = feat(run)
        k_s = np.convolve(k, np.ones(15) / 15, mode='same')
        ax[1].plot(tf - t0, k_s, color=COLS[i], lw=1.5, label=lab)
    ax[0].set_ylabel('ATE error [m]\n(posyaw, full traj.)')
    ax[0].legend(frameon=False, fontsize=9)
    ax[1].set_ylabel('kept features\ncam0 (0.5 s mean)')
    if a.savior:
        rows = [json.loads(line) for line in open(a.savior + '/savior_stats.jsonl')]
        ts = np.array([r['stamp']['t'] for r in rows]) - t0
        npx = 848 * 800.0
        ax[2].plot(ts, [r['core_px'] / npx * 100 for r in rows], color=COLS[1], lw=1.2, label='core 255 [% px]')
        ax[2].plot(ts, [r['ext_px'] / npx * 100 for r in rows], color='#888888', lw=1.0, label='band 192 [% px]')
        ax2 = ax[2]
        ax2.set_ylabel('masked image [%]')
        ax2.legend(frameon=False, fontsize=9, loc='upper left')
    ax[2].set_xlabel('time since GT start [s]')
    for x in ax:
        x.grid(alpha=0.25, lw=0.5)
        x.spines[['top', 'right']].set_visible(False)
    if a.title:
        ax[0].set_title(a.title)
    fig.tight_layout()
    fig.savefig(a.out, dpi=110)


if __name__ == '__main__':
    main()
