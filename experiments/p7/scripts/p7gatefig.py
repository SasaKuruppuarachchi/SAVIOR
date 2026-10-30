#!/usr/bin/env python3
"""p7gatefig.py [tag]: threshold-story figure. ATE change vs yolo_naive (Y-Cls) across interaction-gate settings,
geometric-mean ratio - 1 with 95 % bootstrap CI (tables/ate_<tag>.json from p7analyze.py --refs yolo_naive).
Groups: fixed dist_int {0..4} m (median link), adaptive k (contact link; k = 2 is p7_nb), adaptive k (median link).
Markers: L2+L3 circle, L0+L1 square. Reference lines: 0 (= Y-Cls) and the main (sens_fix1) per level group.
-> figures/gate_sensitivity.{pdf,png}"""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
R = '/home/sasa/workspace/savior_ws/results/p7'
tag = sys.argv[1] if len(sys.argv) > 1 else 'gate'
A = json.load(open(f'{R}/tables/ate_{tag}.json'))
MAIN = 'sens_fix1'
GROUPS = [('fixed $d_{int}$, median link', [(f'sens_fix{d}', f'{d} m') for d in range(5)]),
          ('adaptive $k$, contact link', [('sens_k1', 'k=1'), ('sens_k2', 'k=2'), ('p7_nb', 'k=3'), ('sens_k4', 'k=4')]),
          ('adaptive $k$,\nmedian link', [('sens_kmed1', 'k=1'), ('sens_kmed3', 'k=3')])]
LV = [('L2+L3', 'o', -0.13), ('L0+L1', 's', 0.13)]


def get(m, g):
    r = [x for x in A['paired'] if x['ref'] == 'yolo_naive' and x['group'] == g and x['method'] == m]
    return r[0] if r else None


fig, ax = plt.subplots(figsize=(7.16, 3.0))
x0, ticks, labels, spans = 0, [], [], []
for gname, ms in GROUPS:
    ms = [(m, l) for m, l in ms if get(m, 'L2+L3')]
    if not ms:
        continue
    spans.append((x0, x0 + len(ms) - 1, gname))
    for m, l in ms:
        for g, mk, dx in LV:
            r = get(m, g)
            if not r:
                continue
            c = 'red' if m == MAIN else ('black' if g == 'L2+L3' else '0.45')
            ax.errorbar(x0 + dx, r['gm'], yerr=[[r['gm'] - r['ci'][0]], [r['ci'][1] - r['gm']]], fmt=mk, color=c,
                        mfc=c if g == 'L2+L3' else 'white', ms=4.5, capsize=2, lw=0.9)
        ticks.append(x0); labels.append(l + ('\n(main)' if m == MAIN else '\n(p7_nb)' if m == 'p7_nb' else ''))
        x0 += 1
    x0 += 0.6
ax.axhline(0, color='black', lw=0.8)
ax.text(x0 - 0.75, 1.5, 'Y-Cls', ha='right', va='bottom', fontsize=7)
for g, ls in (('L2+L3', '--'), ('L0+L1', ':')):
    r = get(MAIN, g)
    if r:
        ax.axhline(r['gm'], color='red', lw=0.8, ls=ls)
ax.set_xticks(ticks)
ax.set_xticklabels(labels, fontsize=7)
lo, hi = ax.get_ylim()
for a, b, gname in spans:
    ax.text((a + b) / 2, hi * 0.97, gname, ha='center', va='top', fontsize=7.5)
for (a, b, _), (c, d, _) in zip(spans[:-1], spans[1:]):
    ax.axvline((b + c) / 2, color='0.7', lw=0.6)
ax.set_ylim(lo, hi * 1.12)
ax.set_xlim(-0.6, x0 - 0.9)
ax.set_ylabel('ATE change vs Y-Cls (%)')
ax.set_title('Interaction-Gate Sensitivity (t1 tuning set)')
h = [plt.Line2D([], [], marker='o', color='black', ls='', ms=4.5, label='L2+L3'),
     plt.Line2D([], [], marker='s', color='0.45', mfc='white', ls='', ms=4.5, label='L0+L1'),
     plt.Line2D([], [], color='red', ls='--', lw=0.8, label='main, L2+L3'),
     plt.Line2D([], [], color='red', ls=':', lw=0.8, label='main, L0+L1')]
ax.legend(handles=h, loc='upper center', ncol=4, bbox_to_anchor=(0.5, -0.2))
fig.tight_layout()
for e in ('png', 'pdf'):
    fig.savefig(f'{R}/figures/gate_sensitivity.{e}', dpi=300)
print('->', f'{R}/figures/gate_sensitivity.pdf')
