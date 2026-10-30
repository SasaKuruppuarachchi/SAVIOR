#!/usr/bin/env python3
"""Revision-2 figures: gate sensitivity re-drawn from results/review_runs (re-tuned back-end) and results/p7 (original), plain names.
Run: docker run --rm --network none -u $(id -u):$(id -g) -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 paper/scripts/make_rev2_figures.py
"""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
T = WS + '/results/review_runs/tables'
OUT = WS + '/paper/figures'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
SINGLE = 3.5


def J(p):
    return json.load(open(p))


def get(A, m, ref, g, fam=None):
    r = [x for x in A['paired'] if x['method'] == m and x['ref'] == ref and x['group'] == g and (fam is None or x.get('family') == fam)]
    return r[0] if r else None


def eb(ax, x, r, c, mk, filled=True, ms=3.4):
    lo, hi = r['ci']
    gm = r['gm']
    ax.errorbar(x, gm, yerr=[[gm - lo], [hi - gm]], fmt=mk, color=c, mfc=c if filled else 'white', ms=ms, capsize=1.5, lw=0.7, mew=0.7)


def fig_gate():
    A, A1 = J(f'{T}/ate_t1.json'), J(f'{WS}/results/p7/tables/ate_gate.json')
    G = [('fixed $d_{\\mathrm{int}}$\n(median link)', [(f'gate_fix{d}', f'sens_fix{d}', f'{d} m') for d in range(5)]),
         ('adaptive $k$\n(contact link)', [('gate_k1', 'sens_k1', '1'), ('gate_k2', 'sens_k2', '2'), ('gate_k3', 'p7_nb', '3'), ('gate_k4', 'sens_k4', '4')]),
         ('adaptive $k$\n(median link)', [('gate_kmed1', 'sens_kmed1', '1'), ('gate_kmed3', 'sens_kmed3', '3')])]
    fig, axs = plt.subplots(2, 1, figsize=(SINGLE, 3.7), sharex=True)
    for ax, (g, title) in zip(axs, (('L2+L3', '(a) high-dynamic levels'), ('L0+L1', '(b) low-dynamic levels'))):
        x0, ticks, labels, spans = 0.0, [], [], []
        for gname, ms in G:
            a = x0
            for m, m1, lab in ms:
                r = get(A, m, 'yolo_naive', g, 'C_gate_vs_ycls')
                if r:
                    eb(ax, x0 + 0.12, r, 'red' if m == 'gate_fix1' else 'black', 'o')
                r1 = get(A1, m1, 'yolo_naive', g)
                if r1:
                    eb(ax, x0 - 0.12, r1, '0.55', 's', filled=False, ms=3.0)
                ticks.append(x0); labels.append(lab); x0 += 1
            spans.append((a, x0 - 1, gname)); x0 += 0.5
        ax.axhline(0, color='green', lw=0.8)
        ax.set_title(title, fontsize=8)
        ax.set_ylabel('ATE change vs Y-Cls (%)', fontsize=7)
        ax.tick_params(axis='y', labelsize=6.5)
        lo, hi = ax.get_ylim()
        ax.set_ylim(lo, hi + 0.28 * (hi - lo))
        for a, b, gname in spans:
            ax.text((a + b) / 2, hi + 0.25 * (hi - lo), gname, ha='center', va='top', fontsize=6, linespacing=0.95)
        for (_, b, _), (c, _, _) in zip(spans[:-1], spans[1:]):
            ax.axvline((b + c) / 2, color='0.7', lw=0.5)
    axs[1].set_xticks(ticks); axs[1].set_xticklabels(labels, fontsize=6.5)
    h = [plt.Line2D([], [], marker='o', color='black', ls='', ms=3, label='re-tuned back-end'),
         plt.Line2D([], [], marker='s', color='0.55', mfc='white', ls='', ms=3, label='original back-end'),
         plt.Line2D([], [], marker='o', color='red', ls='', ms=3, label='SAVIOR (1 m), re-tuned'),
         plt.Line2D([], [], color='green', lw=0.8, label='Y-Cls')]
    axs[1].legend(handles=h, loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=6.5)
    fig.tight_layout()
    for e in ('pdf', 'png'):
        fig.savefig(f'{OUT}/fig_gate.{e}', dpi=300)


def fig_t3():
    import math
    d = J(WS + '/results/t3_confirmatory/tables/stats_t3.json')
    P = {x['id']: x for x in d['primary']}
    S = {x['id']: x for x in d['secondary']}
    rows = [(P['P1'], 'P1 O-Dyn+B vs O-Cls+B\n(high)', 'black'),
            (P['P2'], 'P2 SAVIOR vs Y-Cls\n(high)', 'red'),
            (P['P3'], 'P3 SAVIOR vs Y-Cls\n(low)', 'red'),
            (P['P4'], 'P4 SAVIOR vs OpenVINS\n(high)', 'red'),
            (P['P5'], 'P5 SAVIOR vs OpenVINS\n(static)', 'red'),
            (S['S11'], 'C11 Y-Cls vs OpenVINS\n(static)', 'green'),
            (S['S12'], 'C12 O-Dyn+B vs OpenVINS\n(high)', 'black')]
    tr = lambda p: math.log(1 + p / 100)  # noqa: E731
    fig, ax = plt.subplots(figsize=(SINGLE, 2.9))
    for y, (r, lab, c) in enumerate(rows):
        pts = list(r['per_traj'].values())
        ax.plot([tr(v) for v in pts], [y + 0.28 + 0.0 * i for i in range(len(pts))], '|', color=c, ms=3.2, alpha=0.55, mew=0.6)
        lo, hi = r['ci95']
        ax.plot([tr(lo), tr(hi)], [y] * 2, color=c, lw=1.4)
        ax.plot(tr(r['est']), y, 'o', color=c, ms=4)
        if r['id'] == 'P5':
            lo9, hi9 = r['ci90']
            ax.plot([tr(lo9), tr(hi9)], [y + 0.12] * 2, color='0.2', lw=2.2, alpha=0.8, solid_capstyle='butt')
            ax.plot([tr(-10)] * 2, [y - 0.35, y + 0.45], color='0.2', ls=':', lw=0.8)
            ax.plot([tr(10)] * 2, [y - 0.35, y + 0.45], color='0.2', ls=':', lw=0.8)
    ax.axvline(0, color='0.3', lw=0.6, ls='--')
    ticks = [-80, -50, 0, 100]
    ax.set_xticks([tr(t) for t in ticks]); ax.set_xticklabels([f'{t:+d}' if t else '0' for t in ticks], fontsize=6.5)
    ax.set_xlim(tr(-92), tr(150))
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[1] for r in rows], fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel('ATE change (%), log scale', fontsize=7)
    fig.tight_layout()
    for e in ('pdf', 'png'):
        fig.savefig(f'{OUT}/fig_t3_forest.{e}', dpi=300)


if __name__ == '__main__':
    fig_gate()
    fig_t3()
