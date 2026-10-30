#!/usr/bin/env python3
"""Temporal mask stability from the online savior_stats.jsonl (run_01 of every YOLO method and sequence): share of frames
whose core (255) area changes by > 30 % w.r.t. the previous frame (frames with >= 2000 core px in either), and mean core
share. -> tables/mask_flicker.md"""
import glob
import json
R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
M = ['yolo_naive', 'yolo_p2', 'yolo_p4', 'yolo_p4_nointer', 'yolo_p4_noext', 'yolo_p6', 'yolo_coco_person_p4', 'oracle_moving', 'oracle_class_naive']
L = ['# mask flicker (run_01, offset 0.0): share of frames with a > 30 % jump of the core area (mean core share of the image)\n',
     '| seq | ' + ' | '.join(M) + ' |', '|---|' + '--:|' * len(M)]
for q in sorted({p.split('/')[-2] for p in glob.glob(f'{R}/*_t1_L*/')}):
    cells = []
    for m in M:
        f = f'{R}/{q}/{m}/run_01/savior_stats.jsonl'
        try:
            c = [json.loads(x)['core_px'] for x in open(f)]
        except OSError:
            cells.append('-')
            continue
        ch = [abs(a - b) / max(a, b) for a, b in zip(c, c[1:]) if max(a, b) > 2000]
        cells.append(f"{100 * sum(x > 0.3 for x in ch) / max(1, len(ch)):.1f} % ({100 * sum(c) / len(c) / (672 * 376):.1f} %)")
    L.append(f'| {q} | ' + ' | '.join(cells) + ' |')
open(f'{R}/tables/mask_flicker.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
