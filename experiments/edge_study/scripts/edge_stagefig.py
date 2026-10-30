#!/usr/bin/env python3
"""edge_stagefig.py: per-stage compute per camera frame (stacked bars), desktop measured (offline profile, 1 thread, mean over
hall_t1_L3 + aisles_t1_L3, 600 frames each) and the Orin NX 8 GB ESTIMATE (edge_summary.py model), plus the Python-glue share
per variant (cProfile native vs Python attribution). -> figures/stages.{png,pdf}, tables/edge_stages.md"""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R = '/home/sasa/workspace/savior_ws/results/edge_study'
SCR = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge'
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
V = [('main', 'main', 1.0, 's672'), ('sp_klt', 'sparse depth', 1.0, 's672'), ('as10_rot_m1', 'async 10 Hz', 0.5, 's672'),
     ('as5_rot_m1', 'async 5 Hz', 0.25, 's672'), ('c_sp_r10', 'sparse+10 Hz', 0.5, 's672'), ('c_sp_r5', 'sparse+5 Hz', 0.25, 's672'),
     ('main', 'YOLO26n', 1.0, 'n672')]
GF = {'s672': 23.47, 'n672': 6.55}
K_CPU, EFF, FIX, OV, SEGHOST, OVH = 3.5, 2.7, 1.5, 2.7, 2.4, 0.6
ST = ['depth', 'motion', 'gating', 'tracking', 'compose', 'predict']
rows, pyshare = [], []
for v, lab, kf, det in V:
    acc = {s: [] for s in ST + ['frame']}
    nat, fr = [], []
    for q in ('hall_t1_L3', 'aisles_t1_L3'):
        d = json.load(open(f'{SCR}/prof/{v}_{q}.json'))
        w = d['wall_ms']
        for s in ST:
            acc[s].append(w[s][2] * kf if s in w else 0.0)
        fr.append(w['frame'][2])
        nat.append(sum(d['native_by_stage_ms_per_frame'].values()))
    st = {s: float(np.mean(acc[s])) for s in ST}
    frame = float(np.mean(fr))
    st['predict'] = max(0.0, frame - sum(st[s] for s in ST if s != 'predict')) if kf < 1 else 0.0
    st['glue'] = max(0.0, frame - sum(st.values()))
    st['seg host'] = SEGHOST * kf
    st['node I/O'] = OVH
    gpu = (GF[det] / EFF + FIX) * kf
    rows.append((lab, st, gpu))
    pyshare.append((lab, 1 - float(np.mean(nat)) / frame, frame))
cols = {'depth': 'blue', 'motion': 'red', 'gating': 'green', 'tracking': 'magenta', 'compose': 'orange', 'predict': 'cyan',
        'glue': '0.6', 'seg host': 'black', 'node I/O': '0.85'}
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.9))
x = np.arange(len(rows))
for ax, scale, title in ((axs[0], 1.0, 'Desktop CPU (measured, 1 thread)'), (axs[1], K_CPU, 'Orin NX 8 GB (estimate)')):
    bot = np.zeros(len(rows))
    for k in cols:
        h = np.array([r[1][k] * scale for r in rows])
        ax.bar(x, h, bottom=bot, color=cols[k], edgecolor='black', lw=0.3, label=k if ax is axs[0] else None)
        bot += h
    if scale > 1:
        g = np.array([r[2] for r in rows])
        ax.bar(x + 0.42, g, width=0.3, color='white', edgecolor='black', hatch='///', lw=0.5, label='GPU (YOLO)')
        ax.bar(x + 0.42, OV * K_CPU, bottom=g, width=0.3, color='yellow', edgecolor='black', lw=0.5, label='OpenVINS (other core)')
        ax.axhline(50, color='black', ls='--', lw=0.8)
        ax.text(len(rows) - 0.6, 51, '20 Hz budget', fontsize=6, ha='right')
        ax.legend(loc='upper right', fontsize=5.5, frameon=True, fancybox=True)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], rotation=35, ha='right', fontsize=6.5)
    ax.set_title(title)
    ax.set_ylabel('time per camera frame (ms)')
axs[0].legend(loc='upper right', fontsize=5.5, ncol=2, frameon=True, fancybox=True)
fig.tight_layout()
fig.savefig(f'{R}/figures/stages.png', dpi=300)
fig.savefig(f'{R}/figures/stages.pdf')
L = ['# EDGE per-stage CPU per camera frame (desktop, offline profile, 1 thread; mean of hall_t1_L3 + aisles_t1_L3, 600 frames each)\n',
     'Python share = 1 - (native OpenCV/numpy/C tottime attributed to the pipeline) / wall. Orin = x3.5 (estimate).\n',
     '| variant | ' + ' | '.join(cols) + ' | pipeline+node CPU | Python share of pipeline | Orin CPU est. | Orin GPU est. |', '|---|' + '--:|' * (len(cols) + 5)]
for (lab, st, gpu), (_, ps, fr) in zip(rows, pyshare):
    tot = sum(st.values())
    L.append(f'| {lab} | ' + ' | '.join(f'{st[k]:.2f}' for k in cols) + f' | {tot:.1f} | {100 * ps:.0f} % | {tot * K_CPU:.0f} | {gpu:.1f} |')
open(f'{R}/tables/edge_stages.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
