#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Training-curve figure + CSV tables for results/yolo_warehouse (runs/*/results.csv, eval/*.json, latency/*).

  python3 summarize.py   -> results/yolo_warehouse/{training_curves.png, tables/*.csv}
"""
import csv
import glob
import json
import os

import numpy as np

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
R = f'{WS}/results/yolo_warehouse'
NAMES = ['rack', 'guard_rail', 'window', 'forklift', 'box', 'pallet', 'trolley', 'person']
# reference categorical palette (dataviz skill), fixed order: blue, orange, aqua, yellow
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']
TEXT, TEXT2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'


def read_results(run):
    rows = list(csv.DictReader(open(f'{R}/runs/{run}/results.csv')))
    return {k.strip(): np.array([float(r[k]) for r in rows]) for k in rows[0]}


def curves():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    runs = [r for r in ('s_auto', 's_sgd', 'n_auto', 'n_sgd') if os.path.exists(f'{R}/runs/{r}/results.csv')]
    label = {'s_auto': 'YOLO26s, auto (AdamW)', 's_sgd': 'YOLO26s, paper SGD', 'n_auto': 'YOLO26n, auto (AdamW)',
             'n_sgd': 'YOLO26n, paper SGD'}
    panels = [('metrics/mAP50-95(M)', 'val mask mAP50-95'), ('metrics/mAP50(M)', 'val mask mAP50'),
              ('val/seg_loss', 'val seg loss'), ('train/seg_loss', 'train seg loss')]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7), facecolor=SURF)
    summary = []
    for ax, (key, title) in zip(axs.ravel(), panels):
        ax.set_facecolor(SURF)
        for i, run in enumerate(runs):
            d = read_results(run)
            ax.plot(d['epoch'], d[key], color=SERIES[i], lw=2, label=label[run])
            ax.annotate(label[run].split(',')[0] + (' SGD' if 'sgd' in run else ''), (d['epoch'][-1], d[key][-1]),
                        xytext=(4, 0), textcoords='offset points', fontsize=7, color=TEXT2, va='center')
        ax.set_title(title, fontsize=10, color=TEXT, loc='left')
        ax.grid(color=GRID, lw=0.6)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=TEXT2, labelsize=8)
        ax.set_xlabel('epoch', fontsize=8, color=TEXT2)
    axs[0, 0].legend(fontsize=8, frameon=False, labelcolor=TEXT)
    for run in runs:
        d = read_results(run)
        fit = 0.1 * (d['metrics/mAP50(B)'] + d['metrics/mAP50(M)']) + 0.9 * (d['metrics/mAP50-95(B)'] + d['metrics/mAP50-95(M)'])
        b = int(np.argmax(fit))
        summary.append(dict(run=run, epochs_run=int(d['epoch'][-1]), best_epoch=int(d['epoch'][b]),
                            best_mask_mAP50=float(d['metrics/mAP50(M)'][b]),
                            best_mask_mAP50_95=float(d['metrics/mAP50-95(M)'][b]),
                            best_box_mAP50_95=float(d['metrics/mAP50-95(B)'][b]),
                            mask_mAP50_95_at_ep10=float(d['metrics/mAP50-95(M)'][min(9, len(fit) - 1)]),
                            mask_mAP50_95_at_ep30=float(d['metrics/mAP50-95(M)'][min(29, len(fit) - 1)]),
                            hours=float((sum(
                                d['time'][i - 1] for i in range(1, len(fit)) if d['time'][i] < d['time'][i - 1]) + d['time'][-1]) / 3600)))
    fig.tight_layout()
    fig.savefig(f'{R}/training_curves.png', dpi=130, facecolor=SURF)
    write_csv(f'{R}/tables/training_summary.csv', summary)
    return summary


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def eval_tables():
    for f in sorted(glob.glob(f'{R}/eval/*.json')):
        d = json.load(open(f))
        if 'per_class' not in d:
            continue
        rows = []
        for c, v in d['per_class'].items():
            rows.append(dict(cls=c, n_gt=v['n_gt'], AP50=round(v['AP50'], 3), AP50_95=round(v['AP50_95'], 3),
                             IoU=round(v['IoU'], 3), recall=v['recall'] and round(v['recall'], 3),
                             precision=round(v['precision'], 3),
                             **{f'rec_{k}': (None if r[0] is None else round(r[0], 3)) for k, r in v['recall_by_area'].items()},
                             rec_moving=v['recall_moving'][0] and round(v['recall_moving'][0], 3),
                             fp_static_per100=round(v['fp_per_100_frames'].get('static_structure', 0), 1),
                             fp_bg_per100=round(v['fp_per_100_frames'].get('background', 0), 1)))
        write_csv(f'{R}/tables/{os.path.basename(f)[:-5]}.csv', rows)


if __name__ == '__main__':
    print(json.dumps(curves(), indent=1))
    eval_tables()
