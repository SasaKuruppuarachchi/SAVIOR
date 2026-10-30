#!/usr/bin/env python3
"""offline_summary.py: tables from offline_eval.py outputs (results/p5_viode/offline/<seq>.yaml + _inst.jsonl):
  tables/mask_quality.{md,csv}     YOLO vs GT, final masks of every variant vs GT dynamic / all vehicles, right masks
  tables/motion_accuracy.{md,csv}  per instance-frame and per GT vehicle: is the vehicle masked when it moves / is parked
"""
import csv
import glob
import json
import os
from collections import defaultdict

import yaml

R = '/home/sasa/workspace/savior_ws/results/p5_viode'
T = R + '/tables'
os.makedirs(T, exist_ok=True)
ORDER = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
V = ['yolo_naive', 'yolo_full_p2', 'yolo_p4_dyn', 'yolo_p4_pot', 'oracle_dynamic_warp', 'oracle_all_vehicles_warp']
files = {os.path.basename(f)[:-5]: f for f in glob.glob(f'{R}/offline/*.yaml') if not f.endswith('test.yaml')}
seqs = [s for s in ORDER if s in files]
Y = {s: yaml.safe_load(open(files[s])) for s in seqs}


def f3(x):
    return '-' if x is None else f'{x:.3f}'


L = ['# P5 mask quality vs VIODE GT segmentation (pixel level, summed over all frames). YOLO26s-seg TRT, conf 0.25.\n',
     'yolo union = all YOLO vehicle masks (car/truck/bus/motorcycle/bicycle) vs GT all vehicles / GT dynamic vehicles. '
     'Variant rows: final left core (255) vs GT dynamic (P/R/IoU), core+band vs GT dynamic (recall), core vs GT all vehicles '
     '(P), right core vs GT right dynamic (P/R), masked core share of the image.\n',
     '| seq | GT dyn px | yolo P/R (all veh) | yolo P/R (dyn) |', '|---|--:|---|---|']
rows = []
for s in seqs:
    y = Y[s]
    a, d = y['yolo_vehicle_union']['all'], y['yolo_vehicle_union']['dyn']
    L.append(f"| {s} | {100 * y['gt_dyn_share_mean']:.2f} % | {f3(a['precision'])} / {f3(a['recall'])} | {f3(d['precision'])} / {f3(d['recall'])} |")
L += ['', '| seq | variant | core P (dyn) | core R (dyn) | core IoU (dyn) | core+band R (dyn) | core P (all veh) | right P/R (dyn) | core share |',
      '|---|---|--:|--:|--:|--:|--:|---|--:|']
for s in seqs:
    for v in V:
        q = Y[s]['variants'].get(v)
        if not q:
            continue
        r = dict(seq=s, variant=v, core_P_dyn=q['L_dyn_core']['precision'], core_R_dyn=q['L_dyn_core']['recall'],
                 core_IoU_dyn=q['L_dyn_core']['iou'], any_R_dyn=q['L_dyn_any']['recall'], core_P_all=q['L_all_core']['precision'],
                 right_P_dyn=q['R_dyn_core']['precision'], right_R_dyn=q['R_dyn_core']['recall'], core_share=q['core_share'],
                 band_share=q['band_share'])
        rows.append(r)
        L.append(f"| {s} | {v} | {f3(r['core_P_dyn'])} | {f3(r['core_R_dyn'])} | {f3(r['core_IoU_dyn'])} | {f3(r['any_R_dyn'])} | "
                 f"{f3(r['core_P_all'])} | {f3(r['right_P_dyn'])} / {f3(r['right_R_dyn'])} | {100 * r['core_share']:.2f} % |")
open(f'{T}/mask_quality.md', 'w').write('\n'.join(L) + '\n')
if rows:
    with open(f'{T}/mask_quality.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)

# ---- motion evidence accuracy
L = ['# P5 motion-evidence / masking decision vs GT motion label (VIODE vehicle_ids: vehicle_dynamic_* move, '
     'vehicle_static_* are parked). Unit: YOLO vehicle instance per frame with >= 30 % of its pixels on a GT vehicle '
     '(label = majority of dynamic vs static GT pixels). "moving" = masked (core). For yolo_naive / yolo_full_p2 every vehicle '
     'is masked by construction.\n',
     '| seq | variant | n dyn | n static | n no-GT (FP det) | moving precision | moving recall | static kept (unmasked) | FP det masked |',
     '|---|---|--:|--:|--:|--:|--:|--:|--:|']
rows = []
pool = defaultdict(lambda: defaultdict(int))
for s in seqs:
    for v in ('yolo_naive', 'yolo_full_p2', 'yolo_p4_dyn', 'yolo_p4_pot'):
        c = Y[s].get('instances', {}).get(v)
        if not c:
            continue
        r = dict(seq=s, variant=v, n_dyn=c['dynamic']['n'], n_static=c['static']['n'], n_none=c['none']['n'],
                 prec=c['moving_precision'], rec=c['moving_recall'], static_kept=c['static_kept_rate'],
                 none_masked=(c['none']['masked'] / c['none']['n']) if c['none']['n'] else None)
        rows.append(r)
        for k in ('dynamic', 'static', 'none'):
            pool[v][k + '_n'] += c[k]['n']
            pool[v][k + '_m'] += c[k]['masked']
        L.append(f"| {s} | {v} | {r['n_dyn']} | {r['n_static']} | {r['n_none']} | {f3(r['prec'])} | {f3(r['rec'])} | "
                 f"{f3(r['static_kept'])} | {f3(r['none_masked'])} |")
L += ['', '## pooled over sequences', '| variant | n dyn | n static | moving precision | moving recall | static kept | FP det masked |',
      '|---|--:|--:|--:|--:|--:|--:|']
for v, p in pool.items():
    tp, fp = p['dynamic_m'], p['static_m']
    fn, tn = p['dynamic_n'] - tp, p['static_n'] - fp
    L.append(f"| {v} | {p['dynamic_n']} | {p['static_n']} | {f3(tp / (tp + fp) if tp + fp else None)} | "
             f"{f3(tp / (tp + fn) if tp + fn else None)} | {f3(tn / (tn + fp) if tn + fp else None)} | "
             f"{f3(p['none_m'] / p['none_n'] if p['none_n'] else None)} |")
# per GT vehicle (track level): fraction of its detected frames that are masked
L += ['', '## per GT vehicle: share of its YOLO-detected frames that are masked (n frames)',
      '| seq | vehicle | yolo_p4_dyn | yolo_p4_pot |', '|---|---|--:|--:|']
for s in seqs:
    pv = Y[s].get('per_vehicle_masked_frac', {})
    names = sorted({k.split(':', 1)[1] for k in pv})
    for nm in names:
        a = pv.get(f'yolo_p4_dyn:{nm}')
        b = pv.get(f'yolo_p4_pot:{nm}')
        L.append(f"| {s} | {nm.split(':')[1]} | " + (f'{a[1]:.2f} ({a[0]})' if a else '-') + ' | ' + (f'{b[1]:.2f} ({b[0]})' if b else '-') + ' |')
# depth dependence of the P4 decisions (from the per-instance json lines)
L += ['', '## yolo_p4_pot / yolo_p4_dyn decisions by stereo depth (pooled; dynamic = GT moving)',
      '| variant | depth bin [m] | n dyn | dyn masked | n static | static masked |', '|---|---|--:|--:|--:|--:|']
bins = [(0, 5), (5, 10), (10, 20), (20, 1e9), (None, None)]
acc = defaultdict(lambda: [0, 0, 0, 0])
for s in seqs:
    fn = f'{R}/offline/{s}_inst.jsonl'
    if not os.path.isfile(fn):
        continue
    for line in open(fn):
        r = json.loads(line)
        if r['v'] not in ('yolo_p4_dyn', 'yolo_p4_pot') or r['lab'] == 'none':
            continue
        d = r['depth']
        b = (None, None) if d is None else next(x for x in bins[:-1] if x[0] <= d < x[1])
        k = acc[(r['v'], b)]
        if r['lab'] == 'dynamic':
            k[0] += 1; k[1] += r['masked']
        else:
            k[2] += 1; k[3] += r['masked']
for v in ('yolo_p4_dyn', 'yolo_p4_pot'):
    for b in bins:
        k = acc.get((v, b))
        if not k:
            continue
        lab = 'no depth' if b[0] is None else f'{b[0]}-{b[1] if b[1] < 1e8 else "inf"}'
        L.append(f'| {v} | {lab} | {k[0]} | {k[1] / max(1, k[0]):.2f} | {k[2]} | {k[3] / max(1, k[2]):.2f} |')
open(f'{T}/motion_accuracy.md', 'w').write('\n'.join(L) + '\n')
if rows:
    with open(f'{T}/motion_accuracy.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
print(open(f'{T}/mask_quality.md').read())
print(open(f'{T}/motion_accuracy.md').read())
