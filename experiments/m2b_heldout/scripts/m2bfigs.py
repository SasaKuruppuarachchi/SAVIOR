#!/usr/bin/env python3
"""m2bfigs.py: M2b held-out figures in the SAVIOR paper look (savior_eval/paper.mplstyle, docs/FIGURE_STYLE.md)
  forest_key.(png|pdf)       pre-registered head-to-head comparisons (geometric-mean ATE ratio, 95 % CI) per group, both datasets
  forest_vs_openvins.(png|pdf) every masking method vs OpenVINS per group, both datasets
  ate_success.(png|pdf)      success rate vs ATE threshold (warehouse L2+L3, warehouse L0+L1, VIODE low+mid+high)
  ate_heatmap.(png|pdf)      relative ATE change vs OpenVINS, method x sequence (blue-white-red, log2 scale)
  ate_strip.(png|pdf)        per-offset ATE per sequence and method (warehouse t2 and VIODE)
Inputs: tables/ate_warehouse.json, tables/ate_viode.json (m2banalyze.py)."""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
H = '/home/sasa/workspace/savior_ws/results/m2b_heldout'
F = H + '/figures'
os.makedirs(F, exist_ok=True)
LAB = {'openvins': 'OpenVINS', 'savior_none': 'SAVIOR-none', 'oracle_moving_ext': 'O-Dyn+B', 'oracle_class_ext': 'O-Cls+B',
       'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR-adaptive', 'savior_edge': 'SAVIOR-edge'}
COL = {'openvins': 'blue', 'sens_fix1': 'red', 'yolo_naive': 'black', 'p7_nb': 'green', 'oracle_moving_ext': 'magenta',
       'savior_edge': 'orange', 'oracle_class_ext': 'saddlebrown', 'savior_none': '0.5'}
MASK = ['oracle_moving_ext', 'oracle_class_ext', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge']
A = {d: json.load(open(f'{H}/tables/ate_{d}.json')) for d in ('warehouse', 'viode')}
GW = ['L0+L1', 'L2+L3', 'hall+dock_L3']
GV = ['none+low', 'mid+high', 'low+mid+high']
KEY = [('sens_fix1', 'yolo_naive'), ('p7_nb', 'yolo_naive'), ('p7_nb', 'sens_fix1'), ('savior_edge', 'sens_fix1'),
       ('oracle_moving_ext', 'oracle_class_ext')]


def save(fig, name):
    fig.savefig(f'{F}/{name}.png', dpi=300); fig.savefig(f'{F}/{name}.pdf'); plt.close(fig)


def get(d, ref, g, m):
    return next((x for x in A[d]['paired'] if x['ref'] == ref and x['group'] == g and x['method'] == m), None)


def forest(pairs, name, title):
    fig, axs = plt.subplots(1, 2, figsize=(7.16, 0.42 * len(pairs) * 1.6 + 1.0), sharey=True)
    for ax, d, gs in ((axs[0], 'warehouse', GW), (axs[1], 'viode', GV)):
        yt, yl = [], []
        y = 0
        for (m, ref) in pairs:
            for k, g in enumerate(gs):
                r = get(d, ref, g, m)
                yy = -(y * (len(gs) + 1) + k)
                if r:
                    q = 1 + r['gm'] / 100
                    lo, hi = 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
                    ax.errorbar(q, yy, xerr=[[q - lo], [hi - q]], fmt=['o', 's', '^'][k], color=COL[m], ms=4, capsize=2,
                                mfc=COL[m] if r['holm'] < 0.05 else 'white')
                yt.append(yy); yl.append(f"{LAB[m]} vs {LAB[ref]}  [{GW[k]} | {GV[k]}]")
            y += 1
        ax.axvline(1, color='black', lw=0.8, ls=':')
        ax.set_xscale('log')
        ticks = [0.02, 0.1, 0.25, 0.5, 1, 2, 4]
        ax.set_xticks(ticks); ax.set_xticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.minorticks_off()
        ax.set_xlim(0.015, 5)
        ax.set_xlabel('geometric-mean ATE change (%)')
        ax.set_title(f"{title}: {'Warehouse t2' if d == 'warehouse' else 'VIODE'}")
        ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6.5)
    fig.text(0.01, 0.005, 'groups: [Warehouse | VIODE]', ha='left', va='bottom', fontsize=6.5)
    fig.text(0.99, 0.005, 'filled = Holm p < 0.05', ha='right', va='bottom', fontsize=6.5)
    fig.tight_layout(); save(fig, name)


forest(KEY, 'forest_key', 'Key Comparisons')
forest([(m, 'openvins') for m in MASK], 'forest_vs_openvins', 'vs OpenVINS')

# success-rate curves
M = list(LAB)
fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.5), sharey=True)
panels = (('warehouse', ['L0', 'L1'], 'Warehouse t2 L0+L1', 4.0), ('warehouse', ['L2', 'L3'], 'Warehouse t2 L2+L3', 4.0),
          ('viode', ['low', 'mid', 'high'], 'VIODE low+mid+high', 2.0))
for ax, (d, levs, t, xmax) in zip(axs, panels):
    th = np.linspace(0, xmax, 400)
    for m in M:
        v = [x if x != 'inf' else math.inf for s, mm in A[d]['values'].items() if s.rsplit('_', 1)[1] in levs
             for x in mm[m].values()]
        v = np.array([float(x) for x in v])
        if v.size == 0:
            continue
        ax.plot(th, [(v <= x).mean() * 100 for x in th], color=COL[m], lw=1.6 if m == 'sens_fix1' else 1.0,
                ls='--' if m in ('savior_none', 'oracle_class_ext') else '-', label=LAB[m])
    ax.axvline(A[d]['fail_m'], color='0.5', lw=0.6, ls=':')
    ax.set_title(t); ax.set_xlabel('ATE threshold (m)'); ax.set_xlim(0, xmax); ax.set_ylim(0, 102)
axs[0].set_ylabel('runs with ATE below threshold (%)')
axs[2].legend(loc='lower right', fontsize=6, frameon=True, fancybox=True)
fig.tight_layout(); save(fig, 'ate_success')

# heatmap vs openvins (median over offsets of the per-offset log2 ratio, capped)
for d in ('warehouse', 'viode'):
    seqs = list(A[d]['values'])
    Z = np.full((len(MASK), len(seqs)), np.nan)
    for i, m in enumerate(MASK):
        for j, s in enumerate(seqs):
            a, b = A[d]['values'][s][m], A[d]['values'][s]['openvins']
            x = [math.log2(min(float(a[k]), 10) / min(float(b[k]), 10)) for k in a if k in b]
            if x:
                Z[i, j] = float(np.mean(x))
    fig, ax = plt.subplots(figsize=(7.16, 2.4))
    im = ax.imshow(Z, cmap='bwr', vmin=-3, vmax=3, aspect='auto')
    ax.set_xticks(range(len(seqs))); ax.set_xticklabels([s.replace('_t2', '').replace('parking_lot', 'PL').replace('city_day', 'CD')
                                                         .replace('city_night', 'CN') for s in seqs], rotation=45, ha='right', fontsize=6.5)
    ax.set_yticks(range(len(MASK))); ax.set_yticklabels([LAB[m] for m in MASK], fontsize=7)
    for i in range(len(MASK)):
        for j in range(len(seqs)):
            if not np.isnan(Z[i, j]):
                ax.text(j, i, f'{100 * (2 ** Z[i, j] - 1):+.0f}', ha='center', va='center', fontsize=5.5)
    cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label('log2 ATE ratio vs OpenVINS', fontsize=7)
    ax.set_title(f"Relative ATE vs OpenVINS ({'Warehouse t2' if d == 'warehouse' else 'VIODE'}, geometric mean over 10 offsets, %)")
    fig.tight_layout(); save(fig, f'ate_heatmap_{d}')

# strip plot
for d in ('warehouse', 'viode'):
    seqs = list(A[d]['values'])
    fig, ax = plt.subplots(figsize=(7.16, 2.8))
    w = 0.8 / len(M)
    for j, s in enumerate(seqs):
        for i, m in enumerate(M):
            v = np.array([min(float(x), 10) for x in A[d]['values'][s][m].values()])
            ax.scatter(np.full(v.size, j - 0.4 + (i + 0.5) * w), v, s=3, color=COL[m], label=LAB[m] if j == 0 else None)
    ax.axhline(A[d]['fail_m'], color='0.5', lw=0.6, ls=':')
    ax.set_yscale('log'); ax.set_ylabel('ATE RMSE (m)')
    ax.set_xticks(range(len(seqs))); ax.set_xticklabels([s.replace('_t2', '') for s in seqs], rotation=45, ha='right', fontsize=6.5)
    ax.set_title(f"Per-Offset ATE ({'Warehouse t2' if d == 'warehouse' else 'VIODE'}; capped at 10 m)")
    ax.legend(loc='upper left', ncol=4, fontsize=6, frameon=True, fancybox=True, markerscale=2)
    fig.tight_layout(); save(fig, f'ate_strip_{d}')
print('figures in', F)
