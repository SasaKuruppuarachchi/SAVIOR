#!/usr/bin/env python3
"""p7timefig.py: stage F timing figure (paper look). (a) savior_node per-stage median time per frame, stacked, for
SAVIOR (sens_fix1), SAVIOR-adaptive (p7_nb), Y-Cls (yolo_naive) with fast_masks on / off; p90 / p99 of node_total
as markers; 50 ms frame budget (20 Hz). (b) OpenVINS per-update median time (front-end tracking / back-end) alone and
with each method's masks. Input tables/timing.json (p7timing.py) -> figures/timing.{pdf,png}"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.style.use('/home/sasa/workspace/savior_ws/src/savior/savior_eval/savior_eval/paper.mplstyle')
R = '/home/sasa/workspace/savior_ws/results/p7'
T = json.load(open(f'{R}/tables/timing.json'))
LAB = {'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR\nadaptive', 'yolo_naive': 'Y-Cls'}
ST = [('convert', 'convert'), ('segment', 'segment (YOLO)'), ('depth', 'depth'), ('motion', 'motion'), ('tracking', 'tracking'),
      ('gating', 'gating'), ('extension', 'extension'), ('compose', 'compose')]
SC = ['0.55', 'orange', 'green', 'magenta', 'cyan', 'blue', 'gold', 'black']
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.16, 2.9), gridspec_kw={'width_ratios': [2.1, 1]})
runs = [(f'tim_{m}_{f}', (LAB[m] if f == 'fast' else LAB[m].replace('\nadaptive', '-ad.') + '\nslow masks')) for f in ('fast', 'slow') for m in LAB]
runs = [(r, l) for r, l in runs if r in T]
for i, (r, l) in enumerate(runs):
    b = 0
    for (s, sl), c in zip(ST, SC):
        v = T[r].get(s, [0])[0]
        a1.bar(i, v, 0.65, bottom=b, color=c, edgecolor='black', lw=0.4, label=sl if i == 0 else None)
        b += v
    nt = T[r]['node_total']
    a1.bar(i, max(nt[0] - b, 0), 0.65, bottom=b, color='white', edgecolor='black', lw=0.4, hatch='///',
           label='other (ROS, publish)' if i == 0 else None)
    a1.plot(i, nt[1], 'v', color='red', ms=4, label='node total p90' if i == 0 else None)
    a1.plot(i, nt[2], 'x', color='red', ms=4, label='node total p99' if i == 0 else None)
a1.axhline(50, color='black', ls=':', lw=0.8)
a1.text(len(runs) - 0.6, 51, '50 ms (20 Hz)', ha='right', va='bottom', fontsize=7)
a1.set_xticks(range(len(runs)))
a1.set_xticklabels([l for _, l in runs], fontsize=7)
a1.set_ylabel('time per frame (ms)')
a1.set_title('(a) Perception Node, Median per Stage')
a1.legend(loc='upper left', fontsize=6.5, ncol=3)
a1.set_ylim(0, max(T[r]['node_total'][2] for r, _ in runs) * 1.75)
OVR = [('openvins', 'OpenVINS\nalone')] + [(f'tim_{m}_fast', LAB[m]) for m in LAB]
OVR = [(r, l) for r, l in OVR if r in T and 'ov_total' in T[r]]
OS = [('ov_tracking', 'front-end', 'orange'), ('ov_propagation', 'propagation', '0.55'),
      ('ov_msckf_update', 'MSCKF upd.', 'blue'), ('ov_slam_update', 'SLAM upd.', 'green'),
      ('ov_slam_delayed', 'SLAM init', 'cyan'), ('ov_retri_marg', 're-tri./marg.', 'magenta')]
for i, (r, l) in enumerate(OVR):
    b = 0
    for s, sl, c in OS:
        v = T[r].get(s, [0])[0]
        a2.bar(i, v, 0.65, bottom=b, color=c, edgecolor='black', lw=0.4, label=sl if i == 0 else None)
        b += v
    a2.plot(i, T[r]['ov_total'][1], 'v', color='red', ms=4, label='total p90' if i == 0 else None)
a2.set_xticks(range(len(OVR)))
a2.set_xticklabels([l for _, l in OVR], fontsize=6.5)
a2.set_ylabel('time per update (ms)')
a2.set_title('(b) OpenVINS, Median per Stage')
a2.set_ylim(0, max(T[r]['ov_total'][1] for r, _ in OVR) * 2.3)
a2.legend(loc='upper left', fontsize=6.2, ncol=2, columnspacing=0.8, handlelength=1.4)
fig.tight_layout()
for e in ('png', 'pdf'):
    fig.savefig(f'{R}/figures/timing.{e}', dpi=300)
print('->', f'{R}/figures/timing.pdf')
