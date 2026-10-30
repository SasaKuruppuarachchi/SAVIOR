#!/usr/bin/env python3
"""vs_figs.py : figures (paper look: savior_eval/paper.mplstyle, docs/FIGURE_STYLE.md) + back-end comparison table.
  forest_vs_vins.(png|pdf)  every method vs VINS-Fusion, geometric-mean ATE change with 95 % CI (L0+L1, L2+L3, hall L3)
  forest_key.(png|pdf)      head-to-head: VINS+SAVIOR vs VINS+Y-Cls / vs DynaVINS, edge vs Y-Cls, O-Dyn+B vs O-Cls+B
  ate_success.(png|pdf)     success rate vs ATE threshold (L0+L1, L2+L3)
  ate_strip.(png|pdf)       per-offset ATE per sequence and method
  backend_gain.(png|pdf)    mask gain on OpenVINS (P6/P7/edge-study t1 runs) vs on VINS-Fusion (this study), same masks
  tables/backend.md|json    the numbers of backend_gain
Inputs: tables/ate.json (vs_analyze.py) and the OpenVINS t1 eval summaries. Run in the savior image."""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from scipy import stats  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'
plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
V = WS + '/results/vins_savior'
F = V + '/figures'
os.makedirs(F, exist_ok=True)
A = json.load(open(V + '/tables/ate.json'))
LAB = A['labels']
COL = {'vins_fusion': 'blue', 'vins_savior': 'red', 'vins_ycls': 'black', 'vins_edge': 'orange', 'vins_odyn': 'magenta',
       'vins_ocls': 'saddlebrown', 'dynavins': 'green', 'vins_zero': '0.5', 'vins_fusion_mt': 'cyan'}
SEQS = list(A['values'])
G3 = ['L0+L1', 'L2+L3', 'hall_L3']
MK = ['o', 's', '^']
FAIL, CAP = 2.0, 10.0


def save(fig, name):
    fig.savefig(f'{F}/{name}.png', dpi=300); fig.savefig(f'{F}/{name}.pdf'); plt.close(fig)


def get(ref, g, m):
    return next((x for x in A['paired'] if x['ref'] == ref and x['group'] == g and x['method'] == m), None)


def forest(pairs, name, title, w=3.5):
    fig, ax = plt.subplots(figsize=(w, 0.36 * len(pairs) * (len(G3) + 1) + 0.9))
    yt, yl = [], []
    for y, (m, ref) in enumerate(pairs):
        for k, g in enumerate(G3):
            r = get(ref, g, m)
            yy = -(y * (len(G3) + 1) + k)
            if r:
                q, lo, hi = 1 + r['gm'] / 100, 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
                ax.errorbar(q, yy, xerr=[[q - lo], [hi - q]], fmt=MK[k], color=COL[m], ms=4, capsize=2,
                            mfc=COL[m] if r['holm'] < 0.05 else 'white')
            yt.append(yy); yl.append(f'{LAB[m]} vs {LAB[ref]} [{g}]')
    ax.axvline(1, color='black', lw=0.8, ls=':')
    ax.set_xscale('log')
    ticks = [0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8]
    ax.set_xticks(ticks); ax.set_xticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.minorticks_off()
    ax.set_xlim(0.04, 10)
    ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=6)
    ax.set_xlabel('geometric-mean ATE change (%)')
    ax.set_title(title)
    save(fig, name)


ms_vs = [m for m in ('vins_ycls', 'vins_savior', 'vins_edge', 'vins_odyn', 'vins_ocls', 'dynavins') if m in LAB and get('vins_fusion', 'all', m)]
forest([(m, 'vins_fusion') for m in ms_vs], 'forest_vs_vins', 'Masking on VINS-Fusion (t1)', w=4.2)
key = [p for p in (('vins_savior', 'vins_ycls'), ('vins_savior', 'dynavins'), ('vins_edge', 'vins_ycls'), ('vins_edge', 'dynavins'),
                   ('vins_odyn', 'vins_ocls'), ('vins_edge', 'vins_savior')) if get(p[1], 'all', p[0])]
forest(key, 'forest_key', 'Head-to-Head (t1)', w=4.2)

# success-rate curves
methods = [m for m in ('vins_fusion', 'vins_ycls', 'vins_savior', 'vins_edge', 'vins_odyn', 'vins_ocls', 'dynavins') if m in A['values'][SEQS[0]]]
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), sharey=True)
th = np.logspace(-2, 1, 200)
for ax, (gn, sel) in zip(axs, (('L0+L1', ('L0', 'L1')), ('L2+L3', ('L2', 'L3')))):
    for m in methods:
        v = np.array([x for s in SEQS if s.rsplit('_', 1)[1] in sel for x in A['values'][s][m].values()], float)
        if v.size:
            ax.plot(th, [(v <= t).mean() for t in th], color=COL[m], lw=1.6 if m == 'vins_savior' else 1.0, label=LAB[m])
    ax.set_xscale('log'); ax.set_xlabel('ATE threshold (m)'); ax.set_title(f'Success Rate, {gn}')
    ax.axvline(FAIL, color='0.6', lw=0.6, ls=':')
axs[0].set_ylabel('fraction of runs')
axs[0].legend(loc='upper left', fontsize=6)
save(fig, 'ate_success')

# strip plot
fig, axs = plt.subplots(2, 4, figsize=(7.16, 4.2))
for ax, s in zip(axs.ravel(), SEQS):
    for k, m in enumerate(methods):
        v = np.minimum(np.array(list(A['values'][s][m].values()), float), CAP)
        x = k + np.linspace(-0.2, 0.2, v.size) if v.size else []
        ax.plot(x, v, 'o', ms=2.2, color=COL[m], mfc='none')
        if v.size:
            ax.plot([k - 0.3, k + 0.3], [np.median(v)] * 2, color=COL[m], lw=1.2)
    ax.set_yscale('log'); ax.set_title(s.replace('_t1_', ' '), fontsize=8)
    ax.set_xticks(range(len(methods))); ax.set_xticklabels([LAB[m].replace('VINS+', '+') for m in methods], rotation=70, fontsize=5)
for ax in axs[:, 0]:
    ax.set_ylabel('ATE (m)')
save(fig, 'ate_strip')

# ---------------------------------------------------------------- back-end comparison (same masks, t1, same offsets)
OV = {'baseline': ('p6_warehouse', 'openvins'), 'yolo_naive': ('p6_warehouse', 'yolo_naive'),
      'sens_fix1': ('p7', 'sens_fix1'), 'savior_edge': ('edge_study/runs', 'e_c_n672_L250dfronly'),
      'oracle_moving_ext': ('p6_warehouse', 'oracle_moving_ext'), 'oracle_class_ext': ('p7', 'oracle_class_ext')}
VI = {'baseline': 'vins_fusion', 'yolo_naive': 'vins_ycls', 'sens_fix1': 'vins_savior', 'savior_edge': 'vins_edge',
      'oracle_moving_ext': 'vins_odyn', 'oracle_class_ext': 'vins_ocls'}
NAME = {'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR', 'savior_edge': 'SAVIOR-edge', 'oracle_moving_ext': 'O-Dyn+B',
        'oracle_class_ext': 'O-Cls+B'}


def ov_load(seq, k):
    d, m = OV[k]
    fn = f'{WS}/results/{d}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    for t in yaml.safe_load(open(fn)).get('trials', []):
        i = int(t['name'].split('_')[1])
        out[i] = t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf
    return out


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (n, x.size)).mean(axis=1), [2.5, 97.5])


lr = lambda a, b: math.log(min(a, CAP) / min(b, CAP))  # noqa: E731
rows = []
GR = {'L0+L1': ('L0', 'L1'), 'L2+L3': ('L2', 'L3'), 'hall_L3': None}
for k in NAME:
    if VI[k] not in A['values'][SEQS[0]]:
        continue
    for g, sel in GR.items():
        ss = [s for s in SEQS if (s == 'hall_t1_L3' if sel is None else s.rsplit('_', 1)[1] in sel)]
        for be in ('OpenVINS', 'VINS-Fusion'):
            x = []
            for s in ss:
                if be == 'OpenVINS':
                    a, b = ov_load(s, k), ov_load(s, 'baseline')
                else:
                    a, b = A['values'][s][VI[k]], A['values'][s][VI['baseline']]
                    a = {int(i): v for i, v in a.items()}; b = {int(i): v for i, v in b.items()}
                x += [lr(a[i], b[i]) for i in range(1, 11) if i in a and i in b]
            x = np.array(x)
            nz = x[np.abs(x) > 1e-12]
            p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
            ci = boot(x)
            rows.append(dict(mask=NAME[k], group=g, backend=be, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1),
                             ci=[100 * (math.exp(c) - 1) for c in ci], p=p))
L = ['# Same masks, two back-ends (warehouse t1, 10 offsets): ATE change vs the back-end\'s own unmasked baseline\n',
     'OpenVINS numbers: frozen t1 runs (P6/P7, edge study e_c_n672_L250dfronly); VINS-Fusion: this study (deterministic).\n',
     '| mask | group | OpenVINS: change [95 % CI] p | VINS-Fusion: change [95 % CI] p |', '|---|---|---|---|']
for k in NAME:
    for g in GR:
        o = next((r for r in rows if r['mask'] == NAME[k] and r['group'] == g and r['backend'] == 'OpenVINS'), None)
        v = next((r for r in rows if r['mask'] == NAME[k] and r['group'] == g and r['backend'] == 'VINS-Fusion'), None)
        if o and v:
            f = lambda r: f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] p={r['p']:.3g}"  # noqa: E731
            L.append(f'| {NAME[k]} | {g} | {f(o)} | {f(v)} |')
open(V + '/tables/backend.md', 'w').write('\n'.join(L) + '\n')
json.dump(rows, open(V + '/tables/backend.json', 'w'), indent=1)
print('\n'.join(L))
fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.4), sharey=True)
names = [NAME[k] for k in NAME if any(r['mask'] == NAME[k] for r in rows)]
for ax, g in zip(axs, GR):
    for j, be in enumerate(('OpenVINS', 'VINS-Fusion')):
        for i, n in enumerate(names):
            r = next(r for r in rows if r['mask'] == n and r['group'] == g and r['backend'] == be)
            q, lo, hi = 1 + r['gm'] / 100, 1 + r['ci'][0] / 100, 1 + r['ci'][1] / 100
            ax.errorbar(i + (j - 0.5) * 0.3, q, yerr=[[q - lo], [hi - q]], fmt='o' if j == 0 else 's', ms=3.5, capsize=2,
                        color='blue' if j == 0 else 'black', mfc='white' if r['p'] >= 0.05 else None,
                        label=be if i == 0 else None)
    ax.axhline(1, color='black', lw=0.8, ls=':')
    ax.set_yscale('log'); ticks = [0.05, 0.1, 0.25, 0.5, 1, 2, 4]
    ax.set_yticks(ticks); ax.set_yticklabels([f'{100 * (t - 1):+.0f}' for t in ticks]); ax.minorticks_off()
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=45, fontsize=6)
    ax.set_title(g.replace('_', ' '))
axs[0].set_ylabel('ATE change vs own baseline (%)')
axs[0].legend(loc='lower left', fontsize=6)
save(fig, 'backend_gain')
print('figures in', F)
