#!/usr/bin/env python3
"""m2bsharegain.py: share-vs-gain on the M2b sequences WITHOUT the diagnostic build (only the moving-pixel share is
available): per sequence moving-pixel share (warehouse: HELDOUT_MANIFEST coverage_moving_mean_pct; VIODE: P5
tables/share_vs_gain.csv px_dyn) vs gain = -(geometric-mean ATE ratio - 1) vs OpenVINS (per-offset, capped at 10 m),
Spearman rho per method over the 24 sequences and per dataset. -> tables/share_vs_gain.(md|json), figures/share_vs_gain."""
import csv, json, math
import numpy as np, yaml
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
WS = '/home/sasa/workspace/savior_ws'
H = WS + '/results/m2b_heldout'
man = yaml.safe_load(open(WS + '/data/warehouse/HELDOUT_MANIFEST.yaml'))
share = {s['sequence']: s['coverage_moving_mean_pct'] / 100 for s in man['sequences']}
for r in csv.DictReader(open(WS + '/results/p5_viode/tables/share_vs_gain.csv')):
    share[r['seq']] = float(r['px_dyn'])
MS = ['oracle_moving_ext', 'oracle_class_ext', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge']
LAB = {'oracle_moving_ext': 'O-Dyn+B', 'oracle_class_ext': 'O-Cls+B', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR',
       'p7_nb': 'SAVIOR-adaptive', 'savior_edge': 'SAVIOR-edge'}
COL = {'sens_fix1': 'red', 'yolo_naive': 'black', 'p7_nb': 'green', 'oracle_moving_ext': 'magenta', 'savior_edge': 'orange',
       'oracle_class_ext': 'saddlebrown'}
rows, out = [], {}
for d in ('warehouse', 'viode'):
    A = json.load(open(f'{H}/tables/ate_{d}.json'))
    for s, mm in A['values'].items():
        r = {'dataset': d, 'seq': s, 'px_moving': share[s]}
        for m in MS:
            x = [math.log(min(float(mm[m][k]), 10) / min(float(mm['openvins'][k]), 10)) for k in mm[m] if k in mm['openvins']]
            r[m] = -100 * (math.exp(np.mean(x)) - 1) if x else float('nan')
        rows.append(r)
L = ['# Share vs gain on the M2b sequences (moving-pixel share only; the diagnostic build was skipped)\n',
     'gain = -(geometric-mean ATE ratio - 1) vs OpenVINS per sequence (10 offsets, capped at 10 m); Spearman rho\n',
     '| method | all 24 (rho, p) | warehouse 12 | VIODE 12 |', '|---|---|---|---|']
for m in MS:
    cells = []
    for sel in (lambda r: True, lambda r: r['dataset'] == 'warehouse', lambda r: r['dataset'] == 'viode'):
        rr = [r for r in rows if sel(r)]
        rho, p = stats.spearmanr([r['px_moving'] for r in rr], [r[m] for r in rr])
        cells.append(f'{rho:+.2f} ({p:.3g})')
        out.setdefault(m, []).append({'rho': float(rho), 'p': float(p), 'n': len(rr)})
    L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
L += ['\n| seq | moving px share | ' + ' | '.join(LAB[m] for m in MS) + ' |', '|---|--:|' + '--:|' * len(MS)]
for r in rows:
    L.append(f"| {r['seq']} | {100 * r['px_moving']:.2f} % | " + ' | '.join(f"{r[m]:+.0f} %" for m in MS) + ' |')
open(f'{H}/tables/share_vs_gain.md', 'w').write('\n'.join(L) + '\n')
json.dump({'rows': rows, 'spearman': out}, open(f'{H}/tables/share_vs_gain.json', 'w'), indent=1)
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.6), sharey=True)
for ax, m in zip(axs, ('oracle_moving_ext', 'sens_fix1')):
    for d, mk in (('warehouse', 'o'), ('viode', 's')):
        rr = [r for r in rows if r['dataset'] == d]
        ax.scatter([100 * r['px_moving'] for r in rr], [max(r[m], -145) for r in rr], marker=mk, s=14, color=COL[m],
                   facecolors=COL[m] if d == 'warehouse' else 'white', label='Warehouse t2' if d == 'warehouse' else 'VIODE')
    ax.axhline(0, color='black', lw=0.6, ls=':')
    ax.set_xscale('symlog', linthresh=0.5)
    ax.set_xlabel('moving-pixel share (%)')
    ax.set_title(f"{LAB[m]}: rho = {out[m][0]['rho']:+.2f} (p = {out[m][0]['p']:.2g})")
    ax.set_ylim(-150, 105)  # losses below -145 % drawn at -145 %
axs[0].set_ylabel('ATE gain vs OpenVINS (%)')
axs[0].legend(loc='lower right', fontsize=6.5, frameon=True, fancybox=True)
fig.tight_layout(); fig.savefig(f'{H}/figures/share_vs_gain.png', dpi=300); fig.savefig(f'{H}/figures/share_vs_gain.pdf')
print('\n'.join(L))
