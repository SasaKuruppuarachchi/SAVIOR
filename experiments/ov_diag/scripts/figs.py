#!/usr/bin/env python3
"""figs.py : paper-style figures for the OpenVINS config diagnostic (FIGURE_STYLE.md).
 1. timelines_t1_L0.{png,pdf}: yaw error (top) and position error (bottom) vs dataset time, mean over 10 offsets (solid)
    and mean +- 2 sigma (dotted, same colour); OpenVINS frozen (blue), VINS-Fusion (black), OpenVINS fixed config (green).
 2. forest_ablation.{png,pdf}: geometric-mean ATE ratio - 1 vs base, 95 % bootstrap CI, L0 and L1 panels.
usage: figs.py <fixed_variant> <tables/ablation_runs.json>
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

WS = Path('/home/sasa/workspace/savior_ws')
D = WS / 'results/ov_diag'
plt.style.use(str(WS / 'src/savior/savior_eval/savior_eval/paper.mplstyle'))
FIX = sys.argv[1]
TAB = sys.argv[2]
(D / 'figures').mkdir(exist_ok=True)


def grid_stats(files, key, tg):
    ys = []
    for f in files:
        z = np.load(f)
        y = np.interp(tg, z['t'], np.abs(z[key]) if key == 'yaw' else z[key], left=np.nan, right=np.nan)
        ys.append(y)
    ys = np.array(ys)
    return np.nanmean(ys, 0), np.nanstd(ys, 0)


fig, axs = plt.subplots(2, 2, figsize=(7.16, 4.0), sharex='col')
for c, seq in enumerate(['hall_t1_L0', 'aisles_t1_L0']):
    tg = np.arange(1.0, 113.0, 0.1)
    sets = [('OpenVINS (frozen)', 'blue', f'runs/{seq}__base__run_*.npz'),
            ('VINS-Fusion', 'black', f'runs/warehouse_{seq}__vins_fusion__run_*.npz'),
            (f'OpenVINS ({FIX})', 'green', f'runs/{seq}__{FIX}__run_*.npz')]
    for lab, col, pat in sets:
        files = sorted(glob.glob(str(D / 'analysis' / pat)))
        if not files:
            continue
        for r, key, yl in ((0, 'yaw', 'yaw error (deg)'), (1, 'err', 'position error (m)')):
            m, s = grid_stats(files, key, tg)
            ax = axs[r, c]
            ax.plot(tg, m, color=col, lw=1.0, label=f'{lab}')
            ax.plot(tg, m + 2 * s, color=col, lw=0.7, ls=':')
            ax.plot(tg, np.clip(m - 2 * s, 0, None), color=col, lw=0.7, ls=':')
            ax.set_ylabel(yl)
    axs[0, c].set_title(f'{seq.replace("_", " ")}: Error vs Time')
    axs[1, c].set_xlabel('dataset time (s)')
    axs[0, c].axvline(3.0, color='0.5', lw=0.6, ls='--')
    axs[1, c].axvline(3.0, color='0.5', lw=0.6, ls='--')
axs[0, 0].legend(loc='upper center', ncol=1)
fig.text(0.27, -0.02, '(a) hall_t1_L0', ha='center')
fig.text(0.76, -0.02, '(b) aisles_t1_L0', ha='center')
fig.tight_layout()
for e in ('png', 'pdf'):
    fig.savefig(D / f'figures/timelines_t1_L0.{e}')

rows = json.load(open(TAB))
groups = ['L0', 'L1']
vars_ = sorted({r['variant'] for r in rows if r['variant'] not in ('base', 'clones15only', 'msckf60', 'init_nodyn')},
               key=lambda v: next((r['eff'] for r in rows if r['variant'] == v and r['group'] == 'L0+L1'), 0))
fig, axs = plt.subplots(1, 2, figsize=(7.16, 0.28 * len(vars_) + 1.2), sharey=True)
for ax, g in zip(axs, groups):
    for i, v in enumerate(vars_):
        r = next((r for r in rows if r['variant'] == v and r['group'] == g), None)
        if r is None:
            continue
        col = 'green' if v == FIX else ('red' if r['hi'] < 0 else ('black' if r['lo'] > 0 else '0.45'))
        x, lo, hi = np.log(1 + r['eff']), np.log(1 + r['lo']), np.log(1 + r['hi'])
        ax.errorbar([x], [i], xerr=[[x - lo], [hi - x]], fmt='o', color=col, ms=4, capsize=2)
        if r['fail']:
            ax.text(hi + 0.03, i, f"{r['fail']} fail", va='center', fontsize=6)
    ax.axvline(0, color='black', ls=':', lw=0.8)
    ticks = [-0.5, -0.25, 0, 0.25, 0.5, 1.0]
    ax.set_xticks(np.log(1 + np.array(ticks)))
    ax.set_xticklabels([f'{100*t:+.0f} %' if t else '0' for t in ticks], rotation=30)
    ax.set_title(f'Config Ablations vs Frozen, {g}')
    ax.set_xlabel('ATE change vs frozen config (%)')
axs[0].set_yticks(range(len(vars_)))
axs[0].set_yticklabels(vars_)
fig.tight_layout()
for e in ('png', 'pdf'):
    fig.savefig(D / f'figures/forest_ablation.{e}')
print('ok')
