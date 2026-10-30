#!/usr/bin/env python3
"""dm_figs.py : figures for DynaVINS + SAVIOR masks (paper look: savior_eval/paper.mplstyle, docs/FIGURE_STYLE.md).
Inputs: tables{,_t2,_viode}/ate.json (dm_analyze.py) and, for the back-end comparison, results/vins_savior/
tables{,..heldout/tables_t2,_viode}/ate.json (same masks on VINS-Fusion). Splits without tables are skipped.
  forest_vs_dyna.(png|pdf)   every mask method vs DynaVINS, geometric-mean ATE change; thick bar = run bootstrap 95 % CI,
                             thin bar = sequence-cluster bootstrap 95 % CI; filled = Holm (Wilcoxon) < 0.05
  forest_key.(png|pdf)       DynaVINS+SAVIOR vs +Y-Cls, +O-Dyn+B vs +O-Cls+B, deterministic vs upstream DynaVINS
  ate_success.(png|pdf)      success rate vs ATE threshold per split (low vs high dynamics)
  ate_strip_<split>.(png|pdf) per-offset ATE per sequence and method
  backend_gain.(png|pdf)     same masks on VINS-Fusion (P9) vs DynaVINS (P10): change vs the plain back-end
Run in the savior image."""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
V = WS + '/results/dynavins_masks'
VS = WS + '/results/vins_savior'
F = V + '/figures'
os.makedirs(F, exist_ok=True)
SPL = {'t1': ('tables', VS + '/tables'), 't2': ('tables_t2', VS + '/heldout/tables_t2'),
       'viode': ('tables_viode', VS + '/heldout/tables_viode')}
A = {k: json.load(open(f'{V}/{d}/ate.json')) for k, (d, _) in SPL.items() if os.path.isfile(f'{V}/{d}/ate.json')}
B = {k: json.load(open(f'{d}/ate.json')) for k, (_, d) in SPL.items() if k in A and os.path.isfile(f'{d}/ate.json')}
COL = {'dyna_det': 'blue', 'dyna_savior': 'red', 'dyna_ycls': 'black', 'dyna_odyn': 'magenta', 'dyna_ocls': 'saddlebrown',
       'dyna_zero': '0.5', 'dyna_up': 'cyan'}
G = {'t1': ['L0+L1', 'L2+L3', 'hall_L3'], 't2': ['L0+L1', 'L2+L3', 'hall+dock_L3'], 'viode': ['none+low', 'mid+high', 'high']}
LOWHI = {'t1': ('L0+L1', 'L2+L3'), 't2': ('L0+L1', 'L2+L3'), 'viode': ('none+low', 'mid+high')}
TITLE = {'t1': 'Warehouse t1 (tuning)', 't2': 'Warehouse t2 (held-out)', 'viode': 'VIODE (held-out)'}
MK = ['o', 's', '^']
CAP = 10.0
lev = lambda s: s.rsplit('_', 1)[1]  # noqa: E731


def save(fig, name):
    fig.savefig(f'{F}/{name}.png', dpi=300); fig.savefig(f'{F}/{name}.pdf'); plt.close(fig)


def get(J, ref, g, m):
    return next((x for x in J['paired'] if x['ref'] == ref and x['group'] == g and x['method'] == m), None)


def sel(split, g):
    return lambda s: (g == 'all' or (lev(s) in g.split('+') if split == 'viode' or '+' in g and '_' not in g else
                      (s.split('_')[0] in g.split('_')[0].split('+') and lev(s) == g.split('_')[1]) if '_' in g else lev(s) == g))


def forest_panel(ax, J, split, pairs, short):
    yt, yl = [], []
    for y, (m, ref) in enumerate(pairs):
        for k, g in enumerate(G[split]):
            r = get(J, ref, g, m)
            yy = -(y * (len(G[split]) + 1) + k)
            if r:
                q = 1 + r['gm'] / 100
                lo, hi = 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
                clo, chi = 1 + r['cci'][0] / 100, 1 + r['cci'][1] / 100
                ax.plot([clo, chi], [yy, yy], color=COL[m], lw=0.6)
                ax.plot([lo, hi], [yy, yy], color=COL[m], lw=2.0)
                ax.plot(q, yy, MK[k], color=COL[m], ms=4, mfc=COL[m] if r['holm'] < 0.05 else 'white')
            yt.append(yy); yl.append(f'{short(m, ref)} [{g}]')
    ax.axvline(1, color='black', lw=0.8, ls=':')
    ax.set_xscale('log')
    ticks = [0.1, 0.25, 0.5, 1, 2]
    ax.set_xticks(ticks); ax.set_xticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.minorticks_off()
    ax.set_xlim(0.08, 3)
    ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6)
    ax.set_xlabel('geometric-mean ATE change (%)')
    ax.set_title(TITLE[split], fontsize=9)


LBL = {'dyna_det': 'DynaVINS', 'dyna_savior': '+SAVIOR', 'dyna_ycls': '+Y-Cls', 'dyna_odyn': '+O-Dyn+B',
       'dyna_ocls': '+O-Cls+B', 'dyna_zero': '+zero', 'dyna_up': 'upstream'}
short = lambda m, ref: LBL[m] if ref == 'dyna_det' else f'{LBL[m]} vs {LBL[ref]}'  # noqa: E731
if A:
    fig, axs = plt.subplots(1, len(A), figsize=(3.3 * len(A), 3.8), squeeze=False)
    fig.subplots_adjust(wspace=0.95)
    for ax, (sp, J) in zip(axs[0], A.items()):
        forest_panel(ax, J, sp, [(m, 'dyna_det') for m in ('dyna_ycls', 'dyna_savior', 'dyna_odyn', 'dyna_ocls')], short)
    save(fig, 'forest_vs_dyna')
    fig, axs = plt.subplots(1, len(A), figsize=(3.3 * len(A), 3.0), squeeze=False)
    fig.subplots_adjust(wspace=1.1)
    for ax, (sp, J) in zip(axs[0], A.items()):
        forest_panel(ax, J, sp, [p for p in (('dyna_savior', 'dyna_ycls'), ('dyna_odyn', 'dyna_ocls'), ('dyna_det', 'dyna_up'))
                                 if get(J, p[1], 'all', p[0])], short)
    save(fig, 'forest_key')

    # success-rate curves
    th = np.logspace(-2.3, 1, 200)
    meths = ['dyna_det', 'dyna_ycls', 'dyna_savior', 'dyna_odyn', 'dyna_ocls']
    fig, axs = plt.subplots(len(A), 2, figsize=(7.16, 2.2 * len(A)), squeeze=False, sharey=True)
    for row, (sp, J) in zip(axs, A.items()):
        seqs = list(J['values'])
        for ax, g in zip(row, LOWHI[sp]):
            for m in meths:
                v = np.array([x for s in seqs if lev(s) in g.split('+') for x in J['values'][s].get(m, {}).values()], float)
                if v.size:
                    ax.plot(th, [(v <= t).mean() for t in th], color=COL[m], lw=1.6 if m == 'dyna_savior' else 1.0,
                            label=('DynaVINS' if m == 'dyna_det' else 'DynaVINS' + LBL[m]))
            ax.set_xscale('log'); ax.set_title(f'Success Rate, {TITLE[sp]}, {g}', fontsize=8)
            ax.axvline(J['fail_m'], color='0.6', lw=0.6, ls=':')
        row[0].set_ylabel('fraction of runs')
    for ax in axs[-1]:
        ax.set_xlabel('ATE threshold (m)')
    axs[0][0].legend(loc='upper left', fontsize=6)
    save(fig, 'ate_success')

    # strip plots
    for sp, J in A.items():
        seqs = list(J['values'])
        nc = 4
        fig, axs = plt.subplots(int(np.ceil(len(seqs) / nc)), nc, figsize=(7.16, 1.9 * np.ceil(len(seqs) / nc)), squeeze=False)
        for ax, s in zip(axs.ravel(), seqs):
            for k, m in enumerate(meths):
                v = np.minimum(np.array(list(J['values'][s].get(m, {}).values()), float), CAP)
                if v.size:
                    ax.plot(k + np.linspace(-0.2, 0.2, v.size), v, 'o', ms=2.0, color=COL[m], mfc='none')
                    ax.plot([k - 0.3, k + 0.3], [np.median(v)] * 2, color=COL[m], lw=1.2)
            ax.set_yscale('log'); ax.set_title(s.replace('_', ' '), fontsize=7)
            ax.set_xticks(range(len(meths))); ax.set_xticklabels([LBL[m] for m in meths], rotation=70, fontsize=5)
        for ax in axs[:, 0]:
            ax.set_ylabel('ATE (m)')
        save(fig, f'ate_strip_{sp}')

# back-end comparison (same masks): change vs the plain back-end at the high-dynamic group
VM = {'dyna_ycls': 'vins_ycls', 'dyna_savior': 'vins_savior', 'dyna_odyn': 'vins_odyn', 'dyna_ocls': 'vins_ocls'}
rows = []
if B:
    fig, axs = plt.subplots(1, len(B), figsize=(2.4 * len(B) + 0.4, 2.4), squeeze=False, sharey=True)
    for ax, (sp, Jv) in zip(axs[0], B.items()):
        g = LOWHI[sp][1]
        for k, (dm, vm) in enumerate(VM.items()):
            for off, (J, ref, m, mk) in zip((-0.15, 0.15), ((Jv, 'vins_fusion', vm, 's'), (A[sp], 'dyna_det', dm, 'o'))):
                r = get(J, ref, g, m)
                if not r:
                    continue
                q, lo, hi = 1 + r['gm'] / 100, 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
                ax.plot([k + off] * 2, [lo, hi], color=COL[dm], lw=1.2)
                ax.plot(k + off, q, mk, color=COL[dm], ms=4, mfc=COL[dm] if r['holm'] < 0.05 else 'white')
                rows.append(dict(split=sp, group=g, mask=dm, backend=ref, gm=r['gm'], ci=r['ci'], holm=r['holm']))
        ax.axhline(1, color='black', lw=0.8, ls=':')
        ax.set_yscale('log'); ax.minorticks_off()
        ticks = [0.25, 0.5, 1, 2]
        ax.set_yticks(ticks); ax.set_yticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.set_ylim(0.2, 2.5)
        ax.set_xticks(range(len(VM))); ax.set_xticklabels([LBL[m] for m in VM], rotation=45, fontsize=7)
        ax.set_title(f'{TITLE[sp]}, {g}', fontsize=8)
    axs[0][0].set_ylabel('ATE change vs plain back-end (%)')
    axs[0][0].plot([], [], 's', color='0.3', mfc='none', label='VINS-Fusion'); axs[0][0].plot([], [], 'o', color='0.3', mfc='none', label='DynaVINS')
    axs[0][0].legend(loc='lower left', fontsize=6)
    save(fig, 'backend_gain')
json.dump(rows, open(F + '/backend_gain.json', 'w'), indent=1)
print('figures:', sorted(os.listdir(F)))
