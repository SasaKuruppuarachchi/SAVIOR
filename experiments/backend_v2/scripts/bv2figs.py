#!/usr/bin/env python3
"""bv2figs.py [--set t1] : back-end v2 figures in the SAVIOR paper look (savior_eval/paper.mplstyle, docs/FIGURE_STYLE.md)
  forest_effects_<set>   key head-to-head comparisons and every method vs OpenVINS, back-end v1 (open) vs v2 (filled), per group
  forest_backend_<set>   v2 vs v1 per method (same offset), per group
  ate_success_<set>      success rate vs ATE threshold, v2 solid / v1 dashed (L0+L1 and L2+L3 panels)
Inputs: tables/ate_<set>.json (bv2analyze.py)."""
import json, math, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
H = '/home/sasa/workspace/savior_ws/results/backend_v2'
F = H + '/figures'
os.makedirs(F, exist_ok=True)
SET = sys.argv[sys.argv.index('--set') + 1] if '--set' in sys.argv else 't1'
A = json.load(open(f'{H}/tables/ate_{SET}.json'))
LAB = A['labels']
COL = {'openvins': 'blue', 'sens_fix1': 'red', 'yolo_naive': 'black', 'p7_nb': 'green', 'oracle_moving_ext': 'magenta',
       'savior_edge': 'orange', 'oracle_class_ext': 'saddlebrown', 'oracle_moving': 'purple', 'oracle_class_naive': 'goldenrod',
       'savior_none': '0.5'}
G = ['L0+L1', 'L2+L3', 'hall_L3'] if SET == 't1' else (['L0+L1', 'L2+L3', 'hall+dock_L3'] if SET == 't2' else ['none+low', 'mid+high', 'low+mid+high'])
KEY = [('sens_fix1', 'yolo_naive'), ('p7_nb', 'yolo_naive'), ('savior_edge', 'sens_fix1'), ('oracle_moving_ext', 'oracle_class_ext'),
       ('oracle_moving', 'oracle_class_naive')]
VSOV = [('yolo_naive', 'openvins'), ('sens_fix1', 'openvins'), ('p7_nb', 'openvins'), ('savior_edge', 'openvins'),
        ('oracle_moving_ext', 'openvins'), ('oracle_class_ext', 'openvins')]
MS = ['o', 's', '^']
TICKS = [0.01, 0.05, 0.25, 0.5, 1, 2, 4]


def save(fig, name):
    fig.savefig(f'{F}/{name}_{SET}.png', dpi=300); fig.savefig(f'{F}/{name}_{SET}.pdf'); plt.close(fig)


def get(fam, m, ref, g):
    return next((x for x in A['paired'] if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g), None)


def point(ax, r, y, c, mk, filled):
    q = 1 + r['gm'] / 100
    lo, hi = 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
    ax.errorbar(q, y, xerr=[[q - lo], [hi - q]], fmt=mk, color=c, ms=4, capsize=2, lw=1,
                mfc=c if filled else 'white', ls='none')


def logx(ax, lo=0.007, hi=6, ticks=TICKS):
    ax.axvline(1, color='black', lw=0.8, ls=':')
    ax.set_xscale('log'); ax.set_xticks(ticks); ax.set_xticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.minorticks_off()
    ax.set_xlim(lo, hi)


# 1) effects v1 vs v2
fig, axs = plt.subplots(1, 2, figsize=(7.16, 4.2))
for ax, pairs, fams, title in ((axs[0], KEY, ('key_v1', 'key_v2'), 'Head-to-Head Comparisons'),
                                (axs[1], VSOV, ('vs_openvins_v1', 'vs_openvins_v2'), 'Each Method vs OpenVINS')):
    yt, yl = [], []
    for p, (m, ref) in enumerate(pairs):
        for k, g in enumerate(G):
            y0 = -(p * (len(G) * 2 + 1) + 2 * k)
            for d, fam in enumerate(fams):
                r = get(fam, m, ref, g)
                if r:
                    point(ax, r, y0 - 0.6 * d, COL[m], MS[k], d == 1)
            yt.append(y0 - 0.3); yl.append(f'{LAB[m]} vs {LAB[ref]}, {g}' if k == 0 else g)
    ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6)
    logx(ax, *((0.2, 3, [0.25, 0.5, 1, 2]) if fams[0] == 'key_v1' else (0.007, 3, [0.01, 0.05, 0.25, 1])))
    ax.set_xlabel('geometric-mean ATE change (%)')
    ax.set_title(title)
axs[0].plot([], [], 'o', color='0.3', mfc='white', label='back-end v1 (frozen)')
axs[0].plot([], [], 'o', color='0.3', label='back-end v2')
axs[0].legend(loc='lower right', fontsize=6)
fig.tight_layout(); save(fig, 'forest_effects')

# 2) v2 vs v1 per method
ms = [m for m in ['openvins', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge', 'oracle_moving_ext', 'oracle_class_ext', 'oracle_moving',
                  'oracle_class_naive'] if get('v2_vs_v1', m, m, G[0])]
fig, ax = plt.subplots(figsize=(3.5, 3.4))
yt, yl = [], []
for p, m in enumerate(ms):
    for k, g in enumerate(G):
        r = get('v2_vs_v1', m, m, g)
        y = -(p * (len(G) + 1) + k)
        if r:
            point(ax, r, y, COL[m], MS[k], r['holm'] < 0.05)
    yt.append(-(p * (len(G) + 1) + 1)); yl.append(LAB[m])
ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=7)
logx(ax, 0.04, 3); ax.set_xticks([0.05, 0.25, 0.5, 1, 2]); ax.set_xticklabels(['-95', '-75', '-50', '+0', '+100'])
for k, g in enumerate(G):
    ax.plot([], [], MS[k], color='0.3', label=g)
ax.legend(loc='upper left', fontsize=6, title='filled = Holm < 0.05', title_fontsize=6)
ax.set_xlabel('ATE change, v2 vs v1 (%)')
ax.set_title('Back-End v2 vs v1')
fig.tight_layout(); save(fig, 'forest_backend')

# 3) success rate vs threshold
LV = {'t1': (('L0+L1', ('L0', 'L1')), ('L2+L3', ('L2', 'L3'))), 't2': (('L0+L1', ('L0', 'L1')), ('L2+L3', ('L2', 'L3'))),
      'viode': (('none+low', ('none', 'low')), ('mid+high', ('mid', 'high')))}[SET]
thr = np.logspace(-2, 1, 200)
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), sharey=True)
for ax, (gname, lv) in zip(axs, LV):
    for m in ['openvins', 'yolo_naive', 'sens_fix1', 'savior_edge', 'oracle_moving_ext']:
        for b, ls in (('v2', '-'), ('v1', '--')):
            v = np.array([x for s, d in A['values'][b].items() if s.rsplit('_', 1)[1] in lv for x in d[m].values()], float)
            if v.size:
                ax.plot(thr, [(v <= t).mean() for t in thr], ls, color=COL[m], lw=1.2 if b == 'v2' else 0.9,
                        label=f'{LAB[m]} {b}' if gname == LV[0][0] else None)
    ax.set_xscale('log'); ax.set_xlim(0.03, 10); ax.set_xlabel('ATE threshold (m)'); ax.set_title(f'Success Rate, {gname}')
axs[0].set_ylabel('runs with ATE <= threshold')
h, l = axs[0].get_legend_handles_labels(); axs[1].legend(h, l, loc='lower right', fontsize=5.5, ncol=2)
fig.tight_layout(); save(fig, 'ate_success')
print('figures ->', F)
