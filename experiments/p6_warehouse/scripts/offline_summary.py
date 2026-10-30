#!/usr/bin/env python3
"""Aggregate offline/<seq>.yaml (offline_eval_wh.py) over the 8 sequences:
  tables/classification.md|csv   GT-centric masked rate per class x moving/static, carried loads, pooled (counts summed)
  tables/detection_decisions.md  detection-centric moving precision / recall / static kept per class
  tables/mask_quality.md|csv     core mask vs GT moving pixels (left / right), masked static-potential area, YOLO pixel P/R
"""
import csv
import glob

import yaml

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
POT = ['person', 'forklift', 'box', 'pallet', 'trolley']
D = {}
for f in sorted(glob.glob(f'{R}/offline/*_t1_L?.yaml')):
    d = yaml.safe_load(open(f))
    D[d['seq']] = d
seqs = sorted(D)
variants = list(D[seqs[0]]['variants']) if seqs else []
GROUPS = {'all': seqs, 'L1+L2+L3': [s for s in seqs if not s.endswith('L0')], 'L2+L3': [s for s in seqs if s[-2:] in ('L2', 'L3')],
          'L0': [s for s in seqs if s.endswith('L0')]}


def gsum(v, key, ss):
    n = m = 0
    for s in ss:
        e = D[s]['gt_centric'].get(v, {}).get(key)
        if e:
            n += e['n']
            m += e['masked']
    return n, m


L = ['# GT-centric classification (offline, deterministic, every frame): share of GT instance-frames (>= %d px in cam0) whose '
     'pixels are >= 50 %% inside the final core (255) mask; counts summed over the sequences of the group. For moving '
     'instances higher is better (recall), for static ones lower is better (1 - rate = kept unmasked). carried_* = box / pallet '
     'in a forklift actor block (load); driver = person in a forklift block.\n' % (D[seqs[0]]['min_px'] if seqs else 0)]
rows = []
keys = [f'{c}:{m}' for c in POT for m in ('moving', 'static')] + ['carried_box:moving', 'carried_box:static', 'carried_pallet:moving',
                                                                  'carried_pallet:static', 'driver:moving', 'driver:static']
for g, ss in GROUPS.items():
    L += [f'\n## {g} ({len(ss)} sequences)\n', '| variant | ' + ' | '.join(k.replace(':moving', ' mov').replace(':static', ' st') for k in keys) + ' |',
          '|---|' + '--:|' * len(keys)]
    for v in variants:
        cells = []
        for k in keys:
            n, m = gsum(v, k, ss)
            cells.append(f'{m / n:.2f}' if n else '-')
            rows.append(dict(group=g, variant=v, key=k, n=n, masked=m, rate=round(m / n, 4) if n else None))
        L.append(f'| {v} | ' + ' | '.join(cells) + ' |')
    L.append('\n(n = instance-frames: ' + ', '.join(f'{k} {gsum(variants[0], k, ss)[0]}' for k in keys) + ')')
open(f'{R}/tables/classification.md', 'w').write('\n'.join(L) + '\n')
with open(f'{R}/tables/classification.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0]))
    w.writeheader()
    w.writerows(rows)

# summary metrics per variant: moving recall (instance), static-potential kept, precision (instance-frames)
L = ['# selective-masking summary (GT-centric, offline, pooled over the group): moving recall = masked share of moving '
     'potential-class instance-frames; static kept = unmasked share of static potential-class instance-frames (parked '
     'forklifts, pallets, boxes, standing people, trolleys); instance precision = moving masked / all masked; carried load on '
     'moving forklift masked / on parked forklift kept\n']
for g, ss in GROUPS.items():
    L += [f'\n## {g}\n', '| variant | moving recall | static kept | instance precision | static forklift kept | static box kept | static pallet kept | '
          'static person kept | load on moving forklift masked | load on parked forklift kept |', '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    for v in variants:
        nm = mm = ns = ms = 0
        for c in POT:
            a, b = gsum(v, f'{c}:moving', ss)
            nm += a; mm += b
            a, b = gsum(v, f'{c}:static', ss)
            ns += a; ms += b

        def kept(c):
            n, m = gsum(v, f'{c}:static', ss)
            return f'{1 - m / n:.3f}' if n else '-'
        lm = [gsum(v, f'carried_{c}:moving', ss) for c in ('box', 'pallet')]
        lsn = [gsum(v, f'carried_{c}:static', ss) for c in ('box', 'pallet')]
        lmn, lmm = sum(x[0] for x in lm), sum(x[1] for x in lm)
        lsn_, lsm = sum(x[0] for x in lsn), sum(x[1] for x in lsn)
        L.append(f"| {v} | {mm / nm if nm else float('nan'):.3f} | {1 - ms / ns if ns else float('nan'):.3f} | "
                 f"{mm / (mm + ms) if mm + ms else float('nan'):.3f} | {kept('forklift')} | {kept('box')} | {kept('pallet')} | {kept('person')} | "
                 f"{lmm / lmn if lmn else float('nan'):.3f} | {1 - lsm / lsn_ if lsn_ else float('nan'):.3f} |")
open(f'{R}/tables/selective_summary.md', 'w').write('\n'.join(L) + '\n')

# detection-centric
L = ['# detection-centric decisions (each detected instance -> GT instance with the largest overlap >= 30 % of its area; '
     'moving precision = masked moving / masked (moving + static); incl_fp = also counting masked detections without GT); '
     'pooled over all sequences by summing per-sequence counts is not possible from the ratios, so per sequence\n']
for s in seqs:
    L += [f'\n## {s}\n', '| variant | class | n det | n moving | moving precision | precision incl FP det | moving recall | static kept |',
          '|---|---|--:|--:|--:|--:|--:|--:|']
    for v, d in D[s]['detection_centric'].items():
        for c in POT + ['all']:
            e = d.get(c)
            if not e or not e['n']:
                continue
            L.append(f"| {v} | {c} | {e['n']} | {e['n_moving']} | {e['moving_precision']} | {e['moving_precision_incl_fp_det']} | "
                     f"{e['moving_recall']} | {e['static_kept']} |")
        for cm in ('moving', 'static'):
            e = d.get(f'carried_load_on_{cm}_forklift')
            if e and e['n']:
                L.append(f"| {v} | load on {cm} forklift | {e['n']} | - | masked {e['masked'] / e['n']:.3f} | - | - | {e['status']} |")
open(f'{R}/tables/detection_decisions.md', 'w').write('\n'.join(L) + '\n')

# mask quality
rows = []
L = ['# mask quality vs GT (offline): left core (255) vs GT moving pixels (precision / recall / IoU), core+band recall, right core '
     'vs GT right moving pixels (stereo warp for every variant offline), core / band / masked-static-potential share of the image\n',
     '| seq | variant | L core P | L core R | L IoU | L core+band R | R core P | R core R | core % | band % | static-potential masked % |',
     '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
for s in seqs:
    for v, o in D[s]['variants'].items():
        a, b, r = o['L_core_vs_moving'], o['L_any_vs_moving'], o['R_core_vs_moving']
        L.append(f"| {s} | {v} | {a['precision']} | {a['recall']} | {a['iou']} | {b['recall']} | {r['precision']} | {r['recall']} | "
                 f"{100 * o['core_share']:.2f} | {100 * o['band_share']:.2f} | {100 * o['static_potential_core_share']:.2f} |")
        rows.append(dict(seq=s, variant=v, Lp=a['precision'], Lr=a['recall'], Liou=a['iou'], Lany_r=b['recall'], Rp=r['precision'],
                         Rr=r['recall'], core=o['core_share'], band=o['band_share'], spot=o['static_potential_core_share']))
L += ['\n# YOLO detection pixels vs GT class pixels (all / moving instances): fine-tuned (wh) vs COCO person\n',
      '| seq | model | class | P all | R all | IoU all | R moving |', '|---|---|---|--:|--:|--:|--:|']
for s in seqs:
    for mdl, d in D[s]['yolo_pixels'].items():
        for c, e in d.items():
            if mdl == 'coco' and c != 'person':
                continue
            L.append(f"| {s} | {mdl} | {c} | {e['all']['precision']} | {e['all']['recall']} | {e['all']['iou']} | {e['moving']['recall']} |")
open(f'{R}/tables/mask_quality.md', 'w').write('\n'.join(L) + '\n')
with open(f'{R}/tables/mask_quality.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(open(f'{R}/tables/selective_summary.md').read())
