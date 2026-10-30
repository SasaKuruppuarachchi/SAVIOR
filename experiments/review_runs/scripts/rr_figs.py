#!/usr/bin/env python3
"""rr_figs.py : review-run figures in the paper style (src/savior/docs/FIGURE_STYLE.md, paper.mplstyle).
  fig_gate_v2       gate sweep under back-end v2 vs Y-Cls (t1), v1 sweep (results/p7/tables/ate_gate.json) as open grey markers
  fig_chi2_t1       chi2 sweep of OpenVINS-v2 vs OpenVINS-v2 (t1)
  fig_heldout_forest held-out A/B effects (t2 + VIODE), run-level gm [iid CI] and sequence-level [two-stage CI]
  fig_spill         task D: GT-static share of promoted detections and parent category per level
  fig_E             task E: SAVIOR / Y-Cls vs OpenVINS on OpenLORIS + uHumans2
-> results/review_runs/figures/*.pdf|png"""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
RR = WS + '/results/review_runs'
T = RR + '/tables'
OUT = RR + '/figures'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
SINGLE, DOUBLE = 3.5, 7.16
os.makedirs(OUT, exist_ok=True)


def J(p):
    return json.load(open(p)) if os.path.isfile(p) else None


def get(A, m, ref, g, fam=None):
    r = [x for x in A['paired'] if x['method'] == m and x['ref'] == ref and x['group'] == g and (fam is None or x.get('family') == fam)]
    return r[0] if r else None


def save(fig, name):
    for e in ('pdf', 'png'):
        fig.savefig(f'{OUT}/{name}.{e}', dpi=300)
    plt.close(fig)
    print('wrote', name)


def eb(ax, x, r, c, mk, filled=True, ms=3.4, key='ci'):
    lo, hi = (r[key] if key == 'ci' else r['seq']['ci'])
    gm = r['gm'] if key == 'ci' else r['seq']['est']
    ax.errorbar(x, gm, yerr=[[gm - lo], [hi - gm]], fmt=mk, color=c, mfc=c if filled else 'white', ms=ms, capsize=1.5, lw=0.7, mew=0.7)


def fig_gate_v2():
    A, A1 = J(f'{T}/ate_t1.json'), J(f'{WS}/results/p7/tables/ate_gate.json')
    if not A:
        return
    G = [('fixed $d_{\\mathrm{int}}$\n(median link)', [(f'gate_fix{d}', f'sens_fix{d}', f'{d} m') for d in range(5)]),
         ('adaptive $k$\n(contact link)', [('gate_k1', 'sens_k1', '1'), ('gate_k2', 'sens_k2', '2'), ('gate_k3', 'p7_nb', '3'), ('gate_k4', 'sens_k4', '4')]),
         ('adaptive $k$\n(median)', [('gate_kmed1', 'sens_kmed1', '1'), ('gate_kmed3', 'sens_kmed3', '3')])]
    fig, axs = plt.subplots(2, 1, figsize=(SINGLE, 3.6), sharex=True)
    for ax, (g, title) in zip(axs, (('L2+L3', '(a) high-dynamic (L2+L3)'), ('L0+L1', '(b) low-dynamic (L0+L1)'))):
        x0, ticks, labels, spans = 0.0, [], [], []
        for gname, ms in G:
            a = x0
            for m, m1, lab in ms:
                r = get(A, m, 'yolo_naive', g, 'C_gate_vs_ycls')
                if r:
                    eb(ax, x0 + 0.12, r, 'red' if m == 'gate_fix1' else 'black', 'o')
                r1 = get(A1, m1, 'yolo_naive', g) if A1 else None
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
            ax.text((a + b) / 2, hi + 0.25 * (hi - lo), gname, ha='center', va='top', fontsize=5.5, linespacing=0.95)
        for (_, b, _), (c, _, _) in zip(spans[:-1], spans[1:]):
            ax.axvline((b + c) / 2, color='0.7', lw=0.5)
    axs[1].set_xticks(ticks); axs[1].set_xticklabels(labels, fontsize=6)
    h = [plt.Line2D([], [], marker='o', color='black', ls='', ms=3, label='back-end v2 (this study)'),
         plt.Line2D([], [], marker='s', color='0.55', mfc='white', ls='', ms=3, label='back-end v1 (P7 stage E)'),
         plt.Line2D([], [], marker='o', color='red', ls='', ms=3, label='SAVIOR (1 m)'),
         plt.Line2D([], [], color='green', lw=0.8, label='Y-Cls')]
    axs[1].legend(handles=h, loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=6)
    fig.suptitle('Interaction-Gate Sensitivity (t1 tuning split)', fontsize=9)
    fig.tight_layout()
    save(fig, 'fig_gate_v2')


def fig_chi2_t1():
    A = J(f'{T}/ate_t1.json')
    if not A:
        return
    xs = [('ovchi_050', '0.5'), ('ovchi_025', '0.25'), ('ovchi_010', '0.1')]
    fig, ax = plt.subplots(figsize=(SINGLE, 1.9))
    for gi, (g, mk, c) in enumerate((('all', 'D', 'blue'), ('L0+L1', 's', 'black'), ('L2+L3', 'o', 'black'))):
        for i, (m, _) in enumerate(xs):
            r = get(A, m, 'openvins', g, 'B_chi2_vs_openvins')
            if r:
                eb(ax, i + (gi - 1) * 0.18, r, c, mk, filled=g != 'L0+L1')
    ax.axhline(0, color='blue', lw=0.8, ls='--')
    ax.set_xticks(range(len(xs))); ax.set_xticklabels([f'$\\times${l}' for _, l in xs])
    ax.set_xlabel('chi$^2$ multiplier (MSCKF and SLAM)')
    ax.set_ylabel('ATE change vs OpenVINS (%)', fontsize=7)
    ax.set_title('Tightened chi$^2$ Gate (t1 tuning split)', fontsize=9)
    h = [plt.Line2D([], [], marker='D', color='blue', ls='', ms=3, label='all (selection)'),
         plt.Line2D([], [], marker='s', color='black', mfc='white', ls='', ms=3, label='L0+L1'),
         plt.Line2D([], [], marker='o', color='black', ls='', ms=3, label='L2+L3')]
    ax.legend(handles=h, loc='upper left', fontsize=6)
    save(fig, 'fig_chi2_t1')


def fig_heldout_forest():
    P = [('t2', 'L0+L1', 'warehouse t2, L0+L1'), ('t2', 'L2+L3', 'warehouse t2, L2+L3'), ('viode', 'none+low', 'VIODE none+low'),
         ('viode', 'mid+high', 'VIODE mid+high')]
    C = [('sf1_noint', 'sens_fix1', 'w/o interaction vs SAVIOR', 'black'), ('sf1_nomotion', 'sens_fix1', 'w/o motion vs SAVIOR', 'green'),
         ('sens_fix1', 'ovchi_best', 'SAVIOR vs OV-chi2', 'red'), ('yolo_naive', 'ovchi_best', 'Y-Cls vs OV-chi2', 'magenta'),
         ('ovchi_best', 'openvins', 'OV-chi2 vs OpenVINS', 'blue'), ('sf1_chibest', 'sens_fix1', 'SAVIOR+chi2 vs SAVIOR', 'orange')]
    D = {s: J(f'{T}/ate_{s}.json') for s in ('t2', 'viode')}
    if not all(D.values()):
        return
    fig, axs = plt.subplots(1, len(P), figsize=(DOUBLE, 2.5), sharey=True)
    tr = lambda p: math.log(1 + p / 100)  # noqa: E731
    for ax, (s, g, title) in zip(axs, P):
        for y, (m, ref, lab, c) in enumerate(C):
            r = get(D[s], m, ref, g)
            if not r:
                continue
            ax.plot([tr(r['ci'][0]), tr(r['ci'][1])], [y - 0.15] * 2, color=c, lw=0.9)
            ax.plot(tr(r['gm']), y - 0.15, 'o', color=c, mfc='white', ms=3.2, mew=0.8)
            if r['seq']:
                ax.plot([tr(r['seq']['ci'][0]), tr(r['seq']['ci'][1])], [y + 0.15] * 2, color=c, lw=1.6)
                ax.plot(tr(r['seq']['est']), y + 0.15, 'o', color=c, ms=3.2)
        ax.axvline(0, color='0.3', lw=0.6, ls='--')
        ticks = [-90, -50, 0, 100, 300]
        ax.set_xticks([tr(t) for t in ticks]); ax.set_xticklabels([f'{t:+d}' if t else '0' for t in ticks], fontsize=6)
        ax.set_xlim(tr(-95), tr(400))
        ax.set_title(title, fontsize=7.5)
    axs[0].set_yticks(range(len(C))); axs[0].set_yticklabels([c[2] for c in C], fontsize=6.5); axs[0].invert_yaxis()
    fig.supxlabel('paired geometric-mean ATE change (%), log scale; open: runs pooled, filled: sequence level', fontsize=7)
    fig.tight_layout()
    save(fig, 'fig_heldout_forest')


def fig_spill():
    S = J(f'{T}/spill.json')
    if not S:
        return
    LV = ['L0', 'L1', 'L2', 'L3']
    PC = [('person_static', 'standing person', 'black'), ('person_moving', 'walking person', 'green'),
          ('moving_object', 'moving forklift / load', 'red'), ('static_object', 'static object (chain)', 'orange'), ('unmatched', 'unmatched', '0.7')]
    fig, axs = plt.subplots(1, 2, figsize=(DOUBLE * 0.75, 2.1))
    ax = axs[0]
    for v, c, mk in (('sens_fix1', 'red', 'o'), ('p7_nb', 'black', 's')):
        ax.plot(range(4), [100 * S[f'{v}/{l}']['static_share_det'] for l in LV], marker=mk, color=c, ms=3.5,
                label={'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR-adaptive'}[v] + ', detections')
        ax.plot(range(4), [100 * S[f'{v}/{l}']['static_share_px'] for l in LV], marker=mk, color=c, ms=3.5, ls=':', mfc='white',
                label={'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR-adaptive'}[v] + ', pixels')
    ax.set_xticks(range(4)); ax.set_xticklabels(LV); ax.set_ylim(0, 105)
    ax.set_ylabel('GT-static share of\npromoted instances (%)', fontsize=7)
    ax.set_title('(a) Promotion Precision', fontsize=8)
    ax.legend(fontsize=5.3, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)
    ax = axs[1]
    b = [0.0] * 4
    for k, lab, c in PC:
        v = [100 * S[f'sens_fix1/{l}']['parent'][k] / max(1, S[f'sens_fix1/{l}']['static'][0]) for l in LV]
        ax.bar(range(4), v, bottom=b, color='white', edgecolor=c, hatch={'black': '////', 'green': '....', 'red': 'xxxx',
                                                                         'orange': '----', '0.7': ''}[c], lw=0.8, label=lab)
        b = [x + y for x, y in zip(b, v)]
    ax.set_xticks(range(4)); ax.set_xticklabels(LV); ax.set_ylim(0, 100)
    ax.set_ylabel('GT-static promotions (%)', fontsize=7)
    ax.set_title('(b) SAVIOR: Promoting Parent', fontsize=8)
    ax.legend(fontsize=5.3, loc='upper left', bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    save(fig, 'fig_spill')


def fig_E():
    D = J(f'{T}/ate_e.json')
    if not D:
        return
    C = [('e_sens_fix1', 'e_openvins', 'SAVIOR vs OpenVINS', 'red'), ('e_yolo_naive', 'e_openvins', 'Y-Cls vs OpenVINS', 'green'),
         ('e_sens_fix1', 'e_yolo_naive', 'SAVIOR vs Y-Cls', 'black'), ('e_savior_none', 'e_openvins', 'empty masks vs OpenVINS', 'blue')]
    G = [g for g in ('openloris_heldout', 'openloris_cafe1-1', 'uhumans2_00h', 'uhumans2_06h', 'uhumans2_12h', 'uhumans2_06h+12h')
         if any(get(D, m, r, g) for m, r, _, _ in C)]
    fig, ax = plt.subplots(figsize=(SINGLE, 2.6))
    for gi, g in enumerate(G):
        for ci, (m, ref, lab, c) in enumerate(C):
            r = get(D, m, ref, g)
            if r:
                y = gi + (ci - 1.5) * 0.18
                ax.plot([r['ci'][0], r['ci'][1]], [y, y], color=c, lw=0.9)
                ax.plot(r['gm'], y, 'o', color=c, ms=3, label=lab if gi == 0 else None)
    ax.axvline(0, color='0.3', lw=0.6, ls='--')
    ax.set_yticks(range(len(G))); ax.set_yticklabels(G, fontsize=6.5); ax.invert_yaxis()
    ax.set_xlabel('paired geometric-mean ATE change (%)')
    ax.set_title('Low-Dynamic Real / Sim Data', fontsize=9)
    ax.legend(fontsize=5.5, loc='upper center', bbox_to_anchor=(0.4, -0.22), ncol=2)
    save(fig, 'fig_E')


if __name__ == '__main__':
    for f in (fig_gate_v2, fig_chi2_t1, fig_heldout_forest, fig_spill, fig_E):
        f()
