#!/usr/bin/env python3
"""edge_pareto.py: accuracy-vs-compute Pareto plot (paper style, savior_eval/paper.mplstyle).
x = estimated Orin NX 8 GB compute per frame [ms] (CPU + GPU + OpenVINS; edge_summary.py model), y = ATE change vs the frozen main
(L2+L3 left panel, L0+L1 right panel; geometric mean, 95 % bootstrap CI as error bars). One marker per idea, filled = passes the
pre-registered criterion. Shaded band: spread of the P7 near-equivalent configurations (post-hoc-selection regression context)."""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = '/home/sasa/workspace/savior_ws/results/edge_study'
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
res = json.load(open(f'{R}/tables/edge_closed_loop.json'))
summ = json.load(open(f'{R}/tables/edge_compute_main.json'))
MK = {'1 sparse depth': ('s', 'green'), '2 async seg': ('o', 'magenta'), '3 deferred': ('^', 'orange'), '5 segmenter': ('D', 'black'),
      'combination': ('*', 'red')}
fig, axs = plt.subplots(1, 2, figsize=(7.16, 3.0), sharex=True)
for ax, grp, title in ((axs[0], 'L23', 'Dynamic Levels L2+L3'), (axs[1], 'L01', 'Dynamic Levels L0+L1')):
    ax.axhline(0, color='blue', lw=0.8)
    ax.axhline(10, color='gray', lw=0.8, ls='--')
    nb = summ.get('neighbors', {}).get(grp)
    if nb:
        ax.axhspan(nb[0], nb[1], color='0.9', zorder=0)
    ax.plot([summ['main_orin_ms']], [0], marker='P', color='blue', ms=8, ls='none', label='frozen main (SAVIOR)', zorder=5)
    seen = set()
    for m, r in res.items():
        c = r.get('compute')
        if not c:
            continue
        mk, col = MK.get(r['idea'], ('x', 'black'))
        g = r[grp]
        y, lo, hi = g['gm'], g['ci'][0], g['ci'][1]
        ok = r['verdict'].startswith('PASS')
        lab = r['idea'] if r['idea'] not in seen else None
        seen.add(r['idea'])
        xx = c['orin_total']
        if m.startswith('e_L'):     # idea 3 has the main's compute: spread by latency / variant for legibility
            L = int(m.split('_')[1][1:])
            xx += {100: -4, 250: 0, 500: 4}[L] + {'stale': -1, 'dfr': 0, 'dfronly': 1}[m.split('_')[2]]
        ax.errorbar([xx], [y], yerr=[[y - lo], [hi - y]], fmt=mk, color=col, mfc=col if ok else 'white', ms=6,
                    capsize=2, lw=0.8, label=lab, zorder=4)
        if not m.startswith('e_L') or m in ('e_L250_dfronly', 'e_L250_stale', 'e_L250_dfr'):
            ax.annotate(m.replace('e_', ''), (xx, y), fontsize=4.5, xytext=(3, 2), textcoords='offset points')
    ax.set_title(title)
    ax.set_xlabel('estimated Orin NX compute per frame (ms)')
    ax.text(0.99, 0.01, 'filled = passes criterion; grey band = P7 neighbour configs', transform=ax.transAxes, fontsize=5, ha='right', va='bottom')
axs[0].set_ylabel('ATE change vs main (%)')
axs[0].legend(loc='upper left', fontsize=6, frameon=True, fancybox=True, framealpha=0.8)
fig.tight_layout()
os.makedirs(f'{R}/figures', exist_ok=True)
fig.savefig(f'{R}/figures/pareto.png', dpi=300)
fig.savefig(f'{R}/figures/pareto.pdf')
print('saved', f'{R}/figures/pareto.png')
