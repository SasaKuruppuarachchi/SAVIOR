#!/usr/bin/env python3
"""stats3_fig.py : forest plot, old run-level CI vs new sequence-level CIs, per key claim.
Style: src/savior/savior_eval/savior_eval/paper.mplstyle (docs/FIGURE_STYLE.md). -> results/stats_v3/figures/fig_forest_seqlevel.{pdf,png}"""
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
T = WS + '/results/stats_v3/tables'
K = {r['claim']: r for r in json.load(open(T + '/key_effects.json'))}
LAB = {'ov.odynb-ov': 'O-Dyn+B vs OV', 'ov.odynb-oclsb': 'O-Dyn+B vs O-Cls+B', 'vins.odynb-oclsb': 'V: O-Dyn+B vs O-Cls+B',
       'ov.savior-ycls': 'SAVIOR vs Y-Cls', 'vins.savior-ycls': 'V: SAVIOR vs Y-Cls', 'ov.ycls-ov': 'Y-Cls vs OV',
       'ov.oclsb-ov': 'O-Cls+B vs OV', 'ov.savior-ov': 'SAVIOR vs OV', 'vins.savior-vins': 'V: SAVIOR vs VINS',
       'vins.ycls-vins': 'V: Y-Cls vs VINS', 'x.ovsavior-dyna': 'OV+SAVIOR vs DynaVINS', 'x.ovsavior-vins': 'OV+SAVIOR vs VINS',
       'ov.edge-savior': 'SAVIOR-edge vs SAVIOR'}
PANELS = [('(a) SAVIOR-Warehouse held-out', ['C2', 'C3', 'C4b', 'C6', 'C7', 'C8a', 'C8b', 'C10', 'C11', 'C1', 'C15', 'C16', 'C17',
                                             'C22', 'C23']),
          ('(b) VIODE', ['C5b', 'C9b', 'C19', 'C20', 'C21'])]
tr = lambda p: math.log(1 + p / 100)  # noqa: E731
fig, axs = plt.subplots(2, 1, figsize=(4.6, 5.4), sharex=True, gridspec_kw=dict(height_ratios=[15, 5.6], hspace=0.22))
for ax, (title, cl) in zip(axs, PANELS):
    for y, c in enumerate(cl):
        r = K[c]
        o = r['old']
        ax.plot([tr(o['ci'][0]), tr(o['ci'][1])], [y - 0.2] * 2, color='black', lw=0.9)
        ax.plot(tr(o['est']), y - 0.2, marker='o', mfc='white', color='black', ms=3.6, mew=0.8, ls='none')
        ax.plot([tr(r['lmm_ci'][0]), tr(r['lmm_ci'][1])], [y + 0.2] * 2, color='red', lw=0.8, ls=':')
        ax.plot([tr(r['boot2_ci'][0]), tr(r['boot2_ci'][1])], [y + 0.2] * 2, color='red', lw=1.6)
        ax.plot(tr(r['est']), y + 0.2, marker='o', color='red', ms=3.6, ls='none')
        if r['nonfailed'] and abs(r['nonfailed']['est'] - r['est']) > 3:
            ax.plot(tr(r['nonfailed']['est']), y + 0.2, marker='x', color='red', ms=3.6, mew=0.9, ls='none')
    ax.axvline(0, color='0.3', lw=0.6, ls='--')
    ticks = [-90, -75, -50, 0, 100, 300]
    ax.tick_params(axis='x', labelbottom=ax is axs[1])
    ax.set_xticks([tr(t) for t in ticks])
    ax.set_xticklabels([f'{t:+d}' if t else '0' for t in ticks])
    ax.set_xlim(tr(-97), tr(400))
    ax.set_yticks(range(len(cl)))
    ax.set_yticklabels([f"{c} {LAB[K[c]['comp']]}, {K[c]['group']}" for c in cl], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=9)
axs[1].set_xlabel('paired geometric-mean ATE change (%), log scale')
h = [plt.Line2D([], [], marker='o', mfc='white', color='black', lw=0.9, ms=3.6, label='old: runs pooled, iid bootstrap'),
     plt.Line2D([], [], marker='o', color='red', lw=1.6, ms=3.6, label='new: two-stage cluster bootstrap'),
     plt.Line2D([], [], color='red', lw=0.8, ls=':', label='new: LMM t-interval (df = k-1)'),
     plt.Line2D([], [], marker='x', color='red', ls='none', ms=3.6, label='new: failures excluded')]
axs[1].legend(handles=h, loc='upper center', bbox_to_anchor=(0.35, -0.42), fontsize=6.5, ncol=2)
for ext in ('pdf', 'png'):
    fig.savefig(f'{WS}/results/stats_v3/figures/fig_forest_seqlevel.{ext}')
print('ok')
