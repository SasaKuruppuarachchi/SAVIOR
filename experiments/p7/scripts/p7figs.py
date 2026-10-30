#!/usr/bin/env python3
"""p7figs.py: P7 figures in the SAVIOR paper look (savior_eval/paper.mplstyle, docs/FIGURE_STYLE.md) -> results/p7/figures
  forest_ate.(png|pdf)     effect size (geometric-mean ATE ratio - 1 vs yolo_naive, 95 % CI) per method, L0+L1 / L2+L3
  ate_success.(png|pdf)    success rate vs ATE threshold (all runs, L2+L3 and L0+L1)
  ate_heatmap.(png|pdf)    relative ATE change vs yolo_naive per method x sequence (blue-white-red)
  classification.(png|pdf) offline per-class decisions (moving recall / static kept) per method, L1-L3
  onset_cdf.(png|pdf)      onset latency CDF (forklift + load, transitions and appearances), L2+L3
  timing.(png|pdf)         node per-stage timing (median, p90 whisker) on the idle GPU
Inputs: tables/ate_<tag>.json (p7analyze.py), offline eval dir (p7eval.py), tables/timing.json (p7timing.py)."""
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
R = '/home/sasa/workspace/savior_ws/results/p7'
F = R + '/figures'
os.makedirs(F, exist_ok=True)
TAG = sys.argv[2] if len(sys.argv) > 2 else 'final'
OFF = os.environ.get('OFF', '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN/off_abl')
_MF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main_variant.txt')
MAIN = os.environ.get('MAIN') or (open(_MF).read().strip() if os.path.isfile(_MF) else 'p7')
# fixed colour per method (paper look: OpenVINS blue, SAVIOR red, variants black / green / magenta / orange)
COL = {'openvins': 'blue', MAIN: 'red', 'yolo_naive': 'black', 'yolo_naive_band': 'green', 'oracle_moving_ext': 'magenta',
       'yolo_naive_ring': 'orange', 'yolo_p6': 'grey', 'oracle_class_ext': 'black', 'oracle_moving': 'green', 'oracle_class_naive': 'orange',
       'sens_fix1': 'orange', 'tim_p7_nb_fast': 'red', 'tim_p7_nb_slow': 'magenta', 'tim_yolo_naive_fast': 'black', 'tim_yolo_naive_slow': 'green'}


def col(m):
    return COL.get(m, '0.45')


def save(fig, name):
    fig.savefig(f'{F}/{name}.png', dpi=300)
    fig.savefig(f'{F}/{name}.pdf')
    plt.close(fig)


def forest(A, methods, ref='yolo_naive', name='forest_ate', title='ATE vs Naive Masking', groups=('L0+L1', 'L2+L3')):
    fig, axs = plt.subplots(1, len(groups), figsize=(7.16, 0.32 * len(methods) + 1.0), sharey=True)
    for ax, g in zip(axs, groups):
        for k, m in enumerate(methods):
            r = [x for x in A['paired'] if x['ref'] == ref and x['group'] == g and x['method'] == m]
            if not r:
                continue
            r = r[0]
            y = len(methods) - 1 - k
            q = 1 + r['gm'] / 100
            ax.errorbar(q, y, xerr=[[q - (1 + r['ci'][0] / 100)], [(1 + r['ci'][1] / 100) - q]], fmt='o', color=col(m), ms=4, capsize=2)
        ax.axvline(1, color='black', lw=0.8, ls=':')
        ax.set_title(f'{title}, {g}')
        ax.set_xlabel(f'ATE change vs {ref} (%)')
        ax.set_xscale('log')
        ticks = [0.5, 0.75, 1, 1.5, 2, 4]
        ax.set_xlim(0.4, 6)
        ax.set_xticks(ticks)
        ax.set_xticklabels([f'{100 * (t - 1):+.0f} %' if t != 1 else '0' for t in ticks], rotation=30)
        ax.minorticks_off()
    axs[0].set_yticks(range(len(methods)))
    axs[0].set_yticklabels(list(reversed(methods)))
    fig.tight_layout()
    save(fig, name)


def success(A, methods):
    th = np.logspace(-1.3, 1, 200)
    fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), sharey=True)
    for ax, (g, lv) in zip(axs, [('L0+L1', ('L0', 'L1')), ('L2+L3', ('L2', 'L3'))]):
        for m in methods:
            v = [x for s, d in A['median'].items() if s.endswith(lv) for x in d.get(m, {}).values()]
            v = np.array([x if x is not None and np.isfinite(float(x)) else np.inf for x in map(float, v)])
            if v.size == 0:
                continue
            ax.plot(th, [(v <= t).mean() for t in th], color=col(m), label=m, lw=1.6 if m == MAIN else 1.0)
        ax.set_xscale('log')
        ax.set_title(f'Success Rate, {g}')
        ax.set_xlabel('ATE threshold (m)')
    axs[0].set_ylabel('success rate')
    axs[1].legend(loc='lower right')
    fig.tight_layout()
    save(fig, 'ate_success')


def heatmap(A, methods):
    seqs = list(A['median'])
    M = np.full((len(methods), len(seqs)), np.nan)
    for i, m in enumerate(methods):
        for j, s in enumerate(seqs):
            a, b = A['median'][s].get(m, {}), A['median'][s].get('yolo_naive', {})
            x = [math.log(min(float(a[k]), 10) / min(float(b[k]), 10)) for k in a if k in b]
            if x:
                M[i, j] = 100 * (math.exp(np.mean(x)) - 1)
    fig, ax = plt.subplots(figsize=(7.16, 0.3 * len(methods) + 1.2))
    lim = 100
    im = ax.imshow(np.clip(M, -lim, lim), cmap='bwr', vmin=-lim, vmax=lim, aspect='auto')
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f'{M[i, j]:+.0f}', ha='center', va='center', fontsize=6)
    ax.set_xticks(range(len(seqs)))
    ax.set_xticklabels([s.replace('_t1_', ' ') for s in seqs], rotation=30, ha='right')
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods)
    ax.set_title('Relative ATE Change vs Naive Masking (%)')
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout()
    save(fig, 'ate_heatmap')


def offline_load(methods):
    out = {}
    for m in methods:
        for f in __import__('glob').glob(f'{OFF}/*/{m}.json'):
            d = json.load(open(f))
            out.setdefault(m, []).append(d)
    return out


def classification(methods):
    O = offline_load(methods)
    keys = [('person:moving', 'person mov', 1), ('forklift:moving', 'forklift mov', 1), ('carried_box:moving', 'load mov', 1),
            ('forklift:static', 'forklift st kept', 0), ('box:static', 'box st kept', 0), ('pallet:static', 'pallet st kept', 0)]
    fig, ax = plt.subplots(figsize=(7.16, 2.6))
    w = 0.8 / max(1, len(methods))
    for i, m in enumerate(methods):
        ds = [d for d in O.get(m, []) if not d['seq'].endswith('L0')]
        vals = []
        for k, _, pos in keys:
            n = sum(d['gt_centric'].get(k, [0, 0])[0] for d in ds)
            r = sum(d['gt_centric'].get(k, [0, 0])[1] for d in ds) / n if n else np.nan
            vals.append(r if pos else 1 - r)
        ax.bar(np.arange(len(keys)) + (i - (len(methods) - 1) / 2) * w, vals, w, color='none', edgecolor=col(m), label=m, lw=1.2)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([k[1] for k in keys])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel('rate (instance-frames)')
    ax.set_title('Offline Classification vs GT Moving Flags (L1-L3)')
    ax.legend(loc='upper center', ncol=len(methods), fontsize=7)
    fig.tight_layout()
    save(fig, 'classification')


def onset(methods):
    O = offline_load(methods)
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    t = np.linspace(0, 3, 301)
    for m in methods:
        v = [x for d in O.get(m, []) if d['seq'][-2:] in ('L2', 'L3') for c in ('forklift', 'box', 'pallet')
             for kind in ('transition', 'appear') for x in d['onset'].get(f'{c}:{kind}', [])]
        if not v:
            continue
        lat = np.array([x if x is not None else np.inf for x in v])
        ax.plot(t, [(lat <= x).mean() for x in t], color=col(m), label=m, lw=1.6 if m == MAIN else 1.0)
    ax.set_xlabel('latency to first masked frame (s)')
    ax.set_ylabel('share of onsets')
    ax.set_title('Motion-Onset Latency')
    ax.legend(loc='lower right')
    fig.tight_layout()
    save(fig, 'onset_cdf')


def timing():
    fn = f'{R}/tables/timing.json'
    if not os.path.isfile(fn):
        return
    T = json.load(open(fn))
    stages = ['segment', 'depth', 'motion', 'gating', 'tracking', 'extension', 'compose']
    runs = list(T)
    fig, ax = plt.subplots(figsize=(7.16, 2.6))
    w = 0.8 / len(runs)
    for i, r in enumerate(runs):
        med = [T[r].get(s, [np.nan] * 3)[0] for s in stages + ['node_total']]
        p90 = [T[r].get(s, [np.nan] * 3)[1] for s in stages + ['node_total']]
        x = np.arange(len(stages) + 1) + (i - (len(runs) - 1) / 2) * w
        ax.bar(x, med, w, color='none', edgecolor=col(r.split('@')[0]), label=r, lw=1.2)
        ax.errorbar(x, med, yerr=[np.zeros(len(med)), np.array(p90) - np.array(med)], fmt='none', ecolor=col(r.split('@')[0]), lw=0.8)
    ax.axhline(50, color='black', ls=':', lw=0.8)
    ax.set_xticks(range(len(stages) + 1))
    ax.set_xticklabels(stages + ['node total'])
    ax.set_ylabel('time per frame (ms), median (bar) / p90')
    ax.set_title('savior_node Timing on the Idle GPU (budget 50 ms)')
    ax.legend(loc='upper left', fontsize=7)
    fig.tight_layout()
    save(fig, 'timing')


def extra():
    """stage B (like-for-like oracle), C (ablations vs main), E (sensitivity vs main) forest plots, if their tables exist."""
    for tag, ms, ref, name, title, groups in [
            ('stageAB', ['oracle_moving_ext', 'oracle_moving', 'oracle_class_naive'], 'oracle_class_ext', 'forest_oracle_b',
             'Oracle Masks vs O-Cls+B', ('L0', 'L0+L1', 'L2+L3')),
            ('stageC', None, MAIN, 'forest_ablation', 'Ablations vs Main', ('L0+L1', 'L2+L3')),
            ('stageE', None, MAIN, 'forest_sensitivity', 'Sensitivity vs Main', ('L2', 'L3', 'L2+L3')),
            ('stageE_fix1', ['openvins', MAIN, 'sens_fix1'], 'yolo_naive', 'forest_fix1', 'ATE vs Naive Masking', ('L0+L1', 'L2+L3', 'hall_L3'))]:
        fn = f'{R}/tables/ate_{tag}.json'
        if not os.path.isfile(fn):
            continue
        A = json.load(open(fn))
        if ms is None:
            ms = sorted({x['method'] for x in A['paired'] if x['ref'] == ref})
        forest(A, ms, ref=ref, name=name, title=title, groups=groups)


if __name__ == '__main__':
    methods = sys.argv[1].split(',') if len(sys.argv) > 1 else [MAIN, 'yolo_naive', 'yolo_naive_band', 'openvins', 'oracle_moving_ext']
    A = json.load(open(f'{R}/tables/ate_{TAG}.json'))
    forest(A, [m for m in methods if m != 'yolo_naive'])
    success(A, methods)
    heatmap(A, [m for m in methods if m != 'yolo_naive'])
    offm = [m for m in methods if m.startswith(('p7', 'yolo'))][:5]
    classification(offm)
    onset(offm)
    timing()
    extra()
    print('figures ->', F)
