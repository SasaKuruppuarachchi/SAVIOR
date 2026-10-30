#!/usr/bin/env python3
"""Data figures of the final SAVIOR manuscript (one main figure per claim) and of the supplement.

Run inside the SAVIOR image:
  docker run --rm --network none -u $(id -u):$(id -g) -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 \\
      python3 paper/scripts/make_final_figures.py
Inputs are read-only result tables (paths below). Held-out tables that do not exist yet are drawn as "pending":
the figure keeps its layout and states in the panel which data is missing (no number is invented).

  fig_share_gain  claim 1  oracle gain vs dynamic share: (a) mechanism (diagnostic build, tuning/benchmark data P3a/P5/P6),
                           (b) held-out sequences: O-Dyn+B vs OpenVINS per sequence, back-end v1 (M2b) and v2 (final run)
  fig_forest      claim 2  paired ATE effects (t1 tuning split, back-end v2; held-out t2 and VIODE, back-end v2)
  fig_gate        claim 2  interaction-gate sensitivity (P7 stage E, t1, back-end v1)
  fig_runtime     claim 4  Orin NX 8 GB per-stage time and end-to-end latency (results/jetson_validation)
Style: src/savior/docs/FIGURE_STYLE.md (OpenVINS blue, SAVIOR red, black box frame, no grid).
"""
import json
import math
import os
import re
import csv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
OUT = WS + '/paper/figures'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
SINGLE, DOUBLE = 3.5, 7.16
PENDING = dict(ha='center', va='center', fontsize=6.5, color='magenta', style='italic')
# one colour per method (FIGURE_STYLE.md); method order everywhere: OpenVINS, Y-Cls, SAVIOR, O-Cls(+B), O-Dyn(+B)
COL = {'openvins': 'blue', 'yolo_naive': 'green', 'sens_fix1': 'red', 'oracle_class_ext': 'magenta',
       'oracle_moving_ext': 'black'}


def load(p):
    return json.load(open(p)) if os.path.isfile(p) else None


def save(fig, name):
    for e in ('pdf', 'png'):
        fig.savefig(f'{OUT}/{name}.{e}', dpi=300)
    plt.close(fig)
    print('wrote', name)


def rows_csv(p):
    return list(csv.DictReader(open(p)))


# ------------------------------------------------------------------------------------------------ claim 1: share vs gain
def fig_share_gain():
    fig, axs = plt.subplots(1, 2, figsize=(SINGLE, 1.75), sharey=True, gridspec_kw=dict(wspace=0.10))
    # (a) gain vs MSCKF-used share on movers (logging-only diagnostic build)
    ax = axs[0]
    v = rows_csv(f'{R}/p5_viode/tables/share_vs_gain.csv')
    w = rows_csv(f'{R}/p6_warehouse/tables/share_vs_gain.csv')
    ax.scatter([max(100 * float(r['msckf_used_meas_dyn']), 0.01) for r in v], [float(r['gain_oracle_dynamic_pct']) for r in v],
               s=11, marker='o', facecolors='none', edgecolors='black', lw=0.7, label='VIODE')
    ax.scatter([max(100 * float(r['msckf_used_meas_dyn']), 0.01) for r in w], [float(r['gain_oracle_moving_pct']) for r in w],
               s=11, marker='s', color='black', label='Warehouse (tuning)')
    # uHumans2 06h / 12h (P3a): MSCKF-used share on humans = mean of the logged runs; gain = -(mean difference, % of ref.)
    uh_x = [np.mean([0.28, 0.42]), np.mean([0.76, 0.46, 0.79])]
    uh_y = [-15.39, 9.74]
    ax.scatter(uh_x, uh_y, s=14, marker='^', facecolors='none', edgecolors='0.35', lw=0.7, label='uHumans2')
    ax.set_xscale('log')
    ax.set_xlabel('MSCKF-used share, movers (%)', fontsize=6.2)
    ax.set_ylabel('oracle ATE reduction (%)', fontsize=7)
    ax.text(0.04, 0.96, '(a) tuning / benchmark\n$\\rho$ = 0.70 (n = 20)', transform=ax.transAxes, va='top', fontsize=5.8)
    ax.legend(loc='lower left', fontsize=5.2, handletextpad=0.2, borderpad=0.3, labelspacing=0.2)
    # (b) held-out sequences: gain of O-Dyn+B vs OpenVINS per sequence vs moving-pixel share
    ax = axs[1]
    share, g1 = {}, {}
    for line in open(f'{R}/m2b_heldout/tables/share_vs_gain.md'):
        m = re.match(r'\| (\w+) \| ([\d.]+) % \| ([+-]\d+) %', line)
        if m:
            share[m.group(1)] = float(m.group(2))
            g1[m.group(1)] = float(m.group(3))
    hv = load(WS + '/paper/ho_gains.json')
    g2 = (hv or {}).get('gain_pct', {}).get('oracle_moving_ext', {})
    for gains, kw, lab in ((g1, dict(facecolors='none', edgecolors='0.55', lw=0.7), 'original back-end'),
                           (g2, dict(color='black'), 're-tuned back-end')):
        for wh, mk in ((True, 's'), (False, 'o')):
            k = [s for s in gains if s in share and (('_t2_' in s) == wh)]
            if k:
                ax.scatter([max(share[s], 0.01) for s in k], [gains[s] for s in k], s=11, marker=mk, **kw,
                           label=f'{lab}' if wh else None)
    if not g2:
        ax.text(0.5, 0.82, 're-tuned back-end: pending\n(final held-out run)', transform=ax.transAxes, **PENDING)
    ax.set_xscale('log')
    ax.set_xlabel('moving-pixel share (%)', fontsize=6.2)
    ax.text(0.04, 0.96, '(b) held-out sequences', transform=ax.transAxes, va='top', fontsize=5.8)
    ax.legend(loc='lower right', fontsize=5.2, handletextpad=0.2, borderpad=0.3, labelspacing=0.2)
    for a in axs:
        a.axhline(0, color='blue', lw=0.7, ls='--')
        a.tick_params(labelsize=6.5)
        a.set_ylim(-60, 105)
    save(fig, 'fig_share_gain')


# ------------------------------------------------------------------------------------------------ claim 2: forest
def fig_forest():
    T1 = load(f'{R}/backend_v2/tables/ate_t1.json')
    T2 = load(f'{R}/backend_v2/tables/ate_t2.json')
    VI = load(f'{R}/backend_v2/tables/ate_viode.json')
    comps = [('yolo_naive', 'openvins', 'Y-Cls vs OpenVINS'), ('sens_fix1', 'openvins', 'SAVIOR vs OpenVINS'),
             ('sens_fix1', 'yolo_naive', 'SAVIOR vs Y-Cls'), ('oracle_moving_ext', 'oracle_class_ext', 'O-Dyn+B vs O-Cls+B')]
    sets = [('warehouse tuning', T1, {'static': 'L0+L1', 'dynamic': 'L2+L3'}, dict(mfc='white'), 'o', -0.22),
            ('warehouse held-out', T2, {'static': 'L0+L1', 'dynamic': 'L2+L3'}, dict(), 'o', 0.0),
            ('VIODE (held-out)', VI, {'static': 'none+low', 'dynamic': 'mid+high'}, dict(), '^', 0.22)]

    def get(J, m, ref, g):
        if J is None:
            return None
        fam = 'vs_openvins_v2' if ref == 'openvins' else 'key_v2'
        r = [x for x in J['paired'] if x['family'] == fam and x['method'] == m and x['ref'] == ref and x['group'] == g]
        return r[0] if r else None

    fig, axs = plt.subplots(1, 2, figsize=(SINGLE, 2.15), sharey=True, gridspec_kw=dict(wspace=0.06))
    for ax, part, title in ((axs[0], 'static', 'low-dynamic levels'), (axs[1], 'dynamic', 'high-dynamic levels')):
        for ci, (m, ref, lab) in enumerate(comps):
            c = COL[m]
            for sname, J, gm, kw, mk, dy in sets:
                r = get(J, m, ref, gm[part])
                y = ci + dy
                if r is None:
                    ax.plot(0, y, marker='x', color='magenta', ms=2.5, mew=0.6, ls='none')
                    continue
                lo, hi = r['ci']
                ax.plot([lo, hi], [y, y], color=c, lw=0.8)
                ax.plot(r['gm'], y, marker=mk, color=c, ms=3.0, ls='none', mew=0.7, **kw)
        ax.axvline(0, color='0.3', lw=0.6, ls=':')
        ax.set_xlim(-100, 140)
        ax.set_xticks([-50, 0, 50, 100])
        ax.tick_params(labelsize=6)
        ax.set_title(title, fontsize=6.8, pad=3)
    axs[0].set_yticks(range(len(comps)))
    axs[0].set_yticklabels([c[2] for c in comps], fontsize=6)
    axs[0].invert_yaxis()
    fig.text(0.62, -0.02, 'paired geometric-mean ATE change (%), 95 % CI', ha='center', fontsize=6.8)
    h = [plt.Line2D([], [], marker='o', mfc='white', color='0.2', ls='', ms=3, label='tuning'),
         plt.Line2D([], [], marker='o', color='0.2', ls='', ms=3, label='held-out'),
         plt.Line2D([], [], marker='^', color='0.2', ls='', ms=3, label='VIODE')]
    if T2 is None or VI is None:
        h.append(plt.Line2D([], [], marker='x', color='magenta', ls='', ms=3, label='pending'))
    axs[1].legend(handles=h, loc='upper right', fontsize=5.0, handletextpad=0.1, borderpad=0.3, labelspacing=0.15)
    save(fig, 'fig_forest')


# ------------------------------------------------------------------------------------------------ claim 2: gate sensitivity
def fig_gate():
    A = json.load(open(f'{R}/p7/tables/ate_gate.json'))
    MAIN = 'sens_fix1'
    G = [('fixed $d_{\\mathrm{int}}$\n(median link)', [(f'sens_fix{d}', f'{d}') for d in range(5)], 'm'),
         ('adaptive $k$\n(contact link)', [('sens_k1', '1'), ('sens_k2', '2'), ('p7_nb', '3'), ('sens_k4', '4')], ''),
         ('adaptive $k$\n(median)', [('sens_kmed1', '1'), ('sens_kmed3', '3')], '')]

    def get(m, g):
        r = [x for x in A['paired'] if x['ref'] == 'yolo_naive' and x['group'] == g and x['method'] == m]
        return r[0] if r else None

    fig, ax = plt.subplots(figsize=(SINGLE, 1.9))
    x0, ticks, labels, spans = 0.0, [], [], []
    for gname, ms, unit in G:
        a = x0
        for m, l in ms:
            for g, mk, dx in (('L2+L3', 'o', -0.15), ('L0+L1', 's', 0.15)):
                r = get(m, g)
                if r is None:
                    continue
                c = 'red' if m == MAIN else 'black'
                ax.errorbar(x0 + dx, r['gm'], yerr=[[r['gm'] - r['ci'][0]], [r['ci'][1] - r['gm']]], fmt=mk, color=c,
                            mfc=c if g == 'L2+L3' else 'white', ms=3.2, capsize=1.5, lw=0.7, mew=0.7)
            ticks.append(x0)
            labels.append(l + (' m' if unit else ''))
            x0 += 1
        spans.append((a, x0 - 1, gname))
        x0 += 0.5
    ax.axhline(0, color='green', lw=0.8)
    ax.text(-0.5, 2, 'Y-Cls', ha='left', va='bottom', fontsize=5.5, color='green')
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels, fontsize=6)
    ax.tick_params(axis='y', labelsize=6)
    ax.set_ylim(-35, 150)
    for a, b, gname in spans:
        ax.text((a + b) / 2, 147, gname, ha='center', va='top', fontsize=5.5, linespacing=0.95)
    for (_, b, _), (c, _, _) in zip(spans[:-1], spans[1:]):
        ax.axvline((b + c) / 2, color='0.7', lw=0.5)
    ax.set_xlim(-0.6, x0 - 0.9)
    ax.set_ylabel('ATE change vs Y-Cls (%)', fontsize=7)
    h = [plt.Line2D([], [], marker='o', color='black', ls='', ms=3, label='high-dynamic'),
         plt.Line2D([], [], marker='s', color='black', mfc='white', ls='', ms=3, label='low-dynamic'),
         plt.Line2D([], [], marker='o', color='red', ls='', ms=3, label='SAVIOR ($d_{\\mathrm{int}}$ = 1 m)')]
    ax.legend(handles=h, loc='upper center', bbox_to_anchor=(0.5, 0.80), ncol=3, fontsize=5.3, handletextpad=0.1,
              columnspacing=0.8, borderpad=0.3)
    save(fig, 'fig_gate')


# ------------------------------------------------------------------------------------------------ claim 4: runtime
def fig_runtime():
    J = json.load(open(f'{R}/jetson_validation/tables/timing_timing_main.json'))['pooled']
    D = json.load(open(f'{R}/jetson_validation/tables/timing_timing_deploy.json'))['pooled']
    fig, axs = plt.subplots(1, 2, figsize=(SINGLE, 1.95), gridspec_kw=dict(width_ratios=[1.15, 1.1], wspace=0.42))
    ax = axs[0]
    M = [('yolo_naive', 'Y-Cls\n(Py)', 'green'), ('sens_fix1', 'SAVIOR\n(Py)', 'red'), ('savior_cpp', 'SAVIOR\n(C++)', 'red')]
    stages = [('segment', 'segmentation', '////'), ('depth', 'ROI depth', '....'), ('classification', 'classification', 'xxxx'),
              ('compose', 'compose', '----'), ('publish', 'convert/publish', '')]
    for i, (m, lab, c) in enumerate(M):
        st = J[m]['st']
        b = 0.0
        for k, sl, hatch in stages:
            v = st[k][3] if st.get(k) else 0.0
            ax.bar(i, v, bottom=b, width=0.62, color='white', edgecolor=c, hatch=hatch, lw=0.7)
            b += v
        ax.plot([i - 0.31, i + 0.31], [st['node_total'][2]] * 2, color='black', lw=1.0)
    ax.axhline(50, color='0.3', ls='--', lw=0.7)
    ax.text(2.45, 52, '50 ms', ha='right', va='bottom', fontsize=5.5)
    ax.set_xticks(range(len(M)))
    ax.set_xticklabels([x[1] for x in M], fontsize=5.8)
    ax.set_ylabel('time per frame (ms)', fontsize=7)
    ax.set_ylim(0, 430)
    ax.tick_params(axis='y', labelsize=6)
    import matplotlib.patches as mp
    hh = [mp.Patch(facecolor='white', edgecolor='0.2', hatch=h_, lw=0.6, label=sl) for _, sl, h_ in stages]
    hh.append(plt.Line2D([], [], color='black', lw=1.0, label='node p99'))
    ax.legend(handles=hh, loc='upper center', ncol=2, fontsize=4.5, handlelength=1.4, borderpad=0.3, labelspacing=0.15,
              columnspacing=0.6)
    ax.set_title('(a) perception node on Orin NX', fontsize=6.5, pad=3)
    # (b) end-to-end latency image -> pose: median / p90 / p99
    ax = axs[1]
    L = [('OpenVINS\nalone', J['openvins']['st']['e2e'], 'blue'), ('SAVIOR\nwait', J['savior_cpp']['st']['e2e'], 'red'),
         ('SAVIOR\n100 ms', D['savior_cpp']['st']['e2e'], 'red')]
    for i, (lab, e, c) in enumerate(L):
        ax.plot([i, i], [e[0], e[2]], color=c, lw=0.8)
        ax.plot(i, e[0], 'o', color=c, ms=3.2)
        ax.plot(i, e[1], 'o', color=c, mfc='white', ms=3.2)
        ax.plot(i, e[2], '_', color=c, ms=7, mew=1.2)
    ax.axhline(250, color='0.3', ls='--', lw=0.7)
    ax.text(2.4, 240, '250 ms limit', ha='right', va='top', fontsize=5.5)
    ax.set_xticks(range(len(L)))
    ax.set_xticklabels([x[0] for x in L], fontsize=5.4)
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylim(0, 280)
    ax.set_ylabel('end-to-end latency (ms)', fontsize=7)
    ax.tick_params(axis='y', labelsize=6)
    h = [plt.Line2D([], [], marker='o', color='0.2', ls='', ms=3, label='median'),
         plt.Line2D([], [], marker='o', mfc='white', color='0.2', ls='', ms=3, label='p90'),
         plt.Line2D([], [], marker='_', color='0.2', ls='', ms=6, mew=1.2, label='p99')]
    ax.legend(handles=h, loc='upper left', fontsize=4.8, handletextpad=0.1, borderpad=0.3, labelspacing=0.15)
    ax.set_title('(b) image $\\to$ pose', fontsize=6.5, pad=3)
    save(fig, 'fig_runtime')


if __name__ == '__main__':
    fig_share_gain()
    fig_forest()
    fig_gate()
    fig_runtime()
