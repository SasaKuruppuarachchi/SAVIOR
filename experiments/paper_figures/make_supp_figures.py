#!/usr/bin/env python3
"""Supplement figures S8 (sequence-level forest), S9 (promotion spill), S12 (real-world per-offset ATE).
docker run --rm --network none -u $(id -u):$(id -g) -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 paper/scripts/make_supp_figures.py"""
import json, csv, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
WS = '/home/sasa/workspace/savior_ws'; R = WS + '/results'; OUT = WS + '/paper/figures/supp'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')

def save(fig, n):
    for e in ('pdf', 'png'):
        fig.savefig(f'{OUT}/{n}.{e}', dpi=300)
    plt.close(fig); print('wrote', n)

# ---------------- S8 forest
K = {d['claim']: d for d in json.load(open(R + '/stats_v3/tables/key_effects.json'))}
lab = [
 ('Warehouse (held-out), OpenVINS and VINS-Fusion', None),
 ('C2', 'O-Dyn+B vs O-Cls+B, static+low'), ('C3', 'O-Dyn+B vs O-Cls+B, medium+heavy'),
 ('C4b', 'VINS+O-Dyn+B vs VINS+O-Cls+B, medium+heavy'),
 ('C6', 'SAVIOR vs Y-Cls, static+low'), ('C7', 'SAVIOR vs Y-Cls, medium+heavy'),
 ('C8a', 'VINS+SAVIOR vs VINS+Y-Cls, static+low'), ('C8b', 'VINS+SAVIOR vs VINS+Y-Cls, medium+heavy'),
 ('C11', 'O-Cls+B vs OpenVINS, static'), ('C1', 'O-Dyn+B vs OpenVINS, medium+heavy'),
 ('C15', 'SAVIOR vs OpenVINS, medium+heavy'), ('C16', 'VINS+SAVIOR vs VINS-Fusion, medium+heavy'),
 ('C17', 'VINS+Y-Cls vs VINS-Fusion, medium+heavy'), ('C22', 'OpenVINS+SAVIOR vs DynaVINS, all'),
 ('VIODE', None),
 ('C5b', 'O-Dyn+B vs O-Cls+B, mid+high'), ('C9b', 'SAVIOR vs Y-Cls, mid+high'),
 ('C19', 'VINS+SAVIOR vs VINS-Fusion, mid+high'), ('C20', 'OpenVINS+SAVIOR vs DynaVINS, all'),
 ('C21', 'OpenVINS+SAVIOR vs VINS-Fusion, all'),
]
HOLM = {'C2', 'C21'}
L = lambda e: math.log(1 + e / 100.0)
fig, ax = plt.subplots(figsize=(7.16, 5.2))
y = 0; yt = []; yl = []
for c, t in lab:
    y -= 1
    if t is None:
        ax.text(L(-97), y, c, fontsize=7.5, weight='bold', va='center'); continue
    d = K[c]
    lo, hi = d['lmm_ci']; b0, b1 = d['boot2_ci']
    lo = max(lo, -97)
    ax.plot([L(lo), L(hi)], [y, y], color='red', ls=':', lw=1.0)
    ax.plot([L(b0), L(b1)], [y, y], color='red', lw=2.2)
    ax.plot(L(d['est']), y, 'o', color='red', ms=4)
    ax.plot(L(d['nonfailed']['est']), y, 'x', color='black', ms=4)
    o0, o1 = d['old']['ci'][0], d['old']['ci'][1]
    ax.plot([L(o0), L(o1)], [y - 0.28, y - 0.28], color='black', lw=0.8)
    ax.plot(L(d['old']['est']), y - 0.28, 'o', mfc='white', mec='black', ms=3)
    yt.append(y); yl.append(t + ('  (Holm)' if c in HOLM else ''))
ax.set_ylim(y - 0.8, -0.1)
ax.axvline(0, color='0.3', ls='--', lw=0.6)
tk = [-90, -75, -50, 0, 100, 300]
ax.set_xticks([L(v) for v in tk]); ax.set_xticklabels([f'{v:+d}' if v else '0' for v in tk])
ax.set_xlim(L(-98), L(420))
ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6.5)
ax.set_xlabel('paired geometric-mean ATE change (%), log scale')
from matplotlib.lines import Line2D
h = [Line2D([], [], color='red', lw=2.2, marker='o', ms=4, label='sequence level: cluster bootstrap CI'),
     Line2D([], [], color='red', ls=':', label='sequence level: mixed-model t-interval'),
     Line2D([], [], color='black', ls='', marker='x', label='failed runs excluded'),
     Line2D([], [], color='black', lw=0.8, marker='o', mfc='white', ms=3, label='run level (repeats pooled, not independent)')]
ax.legend(handles=h, loc='upper center', bbox_to_anchor=(0.45, -0.09), ncol=2, fontsize=6.5)
save(fig, 'seqlevel_forest')

# ---------------- S9 spill
S = json.load(open(R + '/review_runs/tables/spill.json'))
names = ['static', 'low', 'medium', 'heavy']
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), gridspec_kw=dict(wspace=0.35, width_ratios=[1, 1.15]))
ax = axs[0]
for key, col, mk, lbl in [('sens_fix1', 'red', 'o', 'SAVIOR'), ('p7_nb', 'black', 's', 'SAVIOR-adaptive')]:
    a = [100 * S[f'{key}/L{i}']['static_share_det'] for i in range(4)]
    b = [100 * S[f'{key}/L{i}']['static_share_px'] for i in range(4)]
    ax.plot(range(4), a, color=col, marker=mk, ms=4, label=f'{lbl}, by count')
    ax.plot(range(4), b, color=col, marker=mk, mfc='white', ms=4, ls=':', label=f'{lbl}, by pixels')
ax.set_xticks(range(4)); ax.set_xticklabels(names); ax.set_ylim(0, 105)
ax.set_xlabel('dynamic level'); ax.set_ylabel('static share of promoted\ninstances (%)')
ax.set_title('(a) share of promotions on static objects', fontsize=8)
ax.legend(fontsize=6, loc='lower left')
ax = axs[1]
cats = [('person_static', 'standing person', 'black', '//'), ('person_moving', 'walking person', 'green', '..'),
        ('moving_object', 'moving forklift or load', 'red', 'xx'), ('static_object', 'static object (chain)', 'orange', '--'),
        ('unmatched', 'unmatched', '0.6', '')]
bot = np.zeros(4)
for k, lb, col, ht in cats:
    v = []
    for i in range(4):
        p = S[f'sens_fix1/L{i}']['parent']; v.append(100 * p[k] / sum(p.values()))
    ax.bar(range(4), v, bottom=bot, color='white', edgecolor=col, hatch=ht, label=lb, width=0.7); bot += np.array(v)
ax.set_xticks(range(4)); ax.set_xticklabels(names); ax.set_ylim(0, 100)
ax.set_xlabel('dynamic level'); ax.set_ylabel('static promotions by\nstate of the parent (%)')
ax.set_title('(b) who promotes the static objects (SAVIOR)', fontsize=8)
ax.legend(fontsize=6, loc='center left', bbox_to_anchor=(1.0, 0.5))
save(fig, 'promotion_spill')

# ---------------- S12 per-offset ATE
rows = list(csv.DictReader(open(R + '/real_world/tables/per_run.csv')))
seqs = [('MIO13', 'MIO13 moving person'), ('MIO15', 'MIO15 person and props'), ('MIO16', 'MIO16 person, props, screens'), ('MIO07', 'MIO07 static control')]
M = [('openvins', 'OpenVINS', 'blue', 'o'), ('yolo_naive', 'Y-Cls', 'green', 's'), ('sens_fix1', 'SAVIOR', 'red', '^'), ('vins_fusion', 'VINS-Fusion', 'black', 'v')]
fig, axs = plt.subplots(1, 4, figsize=(7.16, 2.3), sharey=True, gridspec_kw=dict(wspace=0.08))
for ax, (s, t) in zip(axs, seqs):
    for m, lb, col, mk in M:
        r = sorted([x for x in rows if x['seq'] == s and x['method'] == m], key=lambda x: float(x['offset_s']))
        ax.plot([float(x['offset_s']) for x in r], [min(float(x['ate_m']), 10) for x in r], color=col, marker=mk, ms=3, lw=0.8, label=lb)
    ax.axhline(1.0, color='0.5', ls='--', lw=0.6)
    ax.set_yscale('log'); ax.set_title(t, fontsize=6.5); ax.set_xlabel('start offset (s)', fontsize=7)
    ax.tick_params(labelsize=6)
axs[0].set_ylabel('ATE (m), capped at 10 m', fontsize=7)
axs[0].legend(fontsize=5.5, loc='upper left')
save(fig, 'rw_ate_offsets')
