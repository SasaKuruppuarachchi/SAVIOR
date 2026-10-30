#!/usr/bin/env python3
"""fig_t3_forest.py : forest plot of P1-P5, X1-X3, Y1-Y4 (t3 confirmatory, OV2 family). Estimates and 95 % trajectory-level
(REML random-intercept, t, df = 23) CIs read from tables/stats_t3.json, amend03.json, amend04.json. Style: paper.mplstyle."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
WS = '/home/sasa/workspace/savior_ws'; T = f'{WS}/results/t3_confirmatory'
plt.style.use(f'{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle')
s = json.load(open(f'{T}/tables/stats_t3.json')); a3 = json.load(open(f'{T}/tables/amend03.json')); a4 = json.load(open(f'{T}/tables/amend04.json'))
LAB = {'P1': 'P1  O-Dyn+B vs O-Cls+B (L2+L3)', 'P2': 'P2  SAVIOR vs Y-Cls (L2+L3)', 'P3': 'P3  SAVIOR vs Y-Cls (L0+L1)',
       'P4': 'P4  SAVIOR vs OpenVINS (L2+L3)', 'P5': 'P5  SAVIOR vs OpenVINS (L0)',
       'X1': 'X1  SAVIOR vs OpenVINS chi2 x0.25 (L2+L3)', 'X2': 'X2  SAVIOR+chi2 x0.25 vs OpenVINS chi2 x0.25 (L2+L3)',
       'X3': 'X3  OpenVINS chi2 x0.25 vs OpenVINS (L2+L3)', 'Y1': 'Y1  SAVIOR+NIS vs SAVIOR (L2+L3)',
       'Y2': 'Y2  SAVIOR+NIS vs OpenVINS chi2 x0.25 (L2+L3)', 'Y3': 'Y3  SAVIOR+NIS vs OpenVINS+NIS (L2+L3)',
       'Y4': 'Y4  SAVIOR+NIS vs OpenVINS (L0)'}
rows = [(r['id'], r) for r in s['primary']] + [(r['id'], r) for r in a3['X']] + [(r['id'], r) for r in a4['X'] if r['id'] in ('Y1', 'Y2', 'Y3', 'Y4')]
fig, ax = plt.subplots(figsize=(7.16, 5.0))
n = len(rows)
for i, (k, r) in enumerate(rows):
    y = n - 1 - i - (0.6 if k.startswith('X') else 0) - (1.2 if k.startswith('Y') else 0)
    col = 'red' if k.startswith('P') else ('blue' if k.startswith('X') else 'black')
    est, (lo, hi) = r['est'], r['ci95']
    ax.plot([lo, hi], [y, y], color=col, lw=1.5)
    ax.plot([est], [y], 's', color=col, ms=5)
    ax.text(1.02, y, f"{est:+.1f} % [{lo:+.1f}, {hi:+.1f}]", transform=ax.get_yaxis_transform(), va='center', fontsize=7.5)
    ax.text(-0.01, y, LAB[k], transform=ax.get_yaxis_transform(), va='center', ha='right', fontsize=7.5)
ys = [n - 1 - i - (0.6 if k.startswith('X') else 0) - (1.2 if k.startswith('Y') else 0) for i, (k, _) in enumerate(rows)]
ax.axvline(0, color='black', lw=0.8)
p5 = dict(rows)['P5']
ax.axvspan(-10, 10, ymin=0, ymax=1, color='0.9', zorder=0)   # P5 equivalence margin
ax.set_yticks([]); ax.set_ylim(min(ys) - 0.8, max(ys) + 0.8)
ax.set_xlim(-100, 50); ax.set_xticks([-100, -80, -60, -40, -20, 0, 20, 40])
ax.set_xlabel('ATE change, first method vs second (%); negative = first method better')
ax.set_title('t3 Confirmatory Effects (24 Trajectories, 95 % Trajectory-Level CI)')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color='red', marker='s', label='P1-P5 confirmatory chain (grey band: P5 margin, +-10 %; P5 tests the 90 % CI)'),
                   Line2D([], [], color='blue', marker='s', label='X1-X3 exploratory (AMENDMENT_03)'),
                   Line2D([], [], color='black', marker='s', label='Y1-Y4 exploratory (AMENDMENT_04)')], loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=7, ncol=1)
fig.subplots_adjust(left=0.42, right=0.80, bottom=0.22, top=0.92)
for ext in ('pdf', 'png'):
    fig.savefig(f'{T}/figures/fig_t3_forest.{ext}', bbox_inches='tight')
