#!/usr/bin/env python3
"""sync_check.py: aggregate runstats.md of every savior method dir: masks == images, fallbacks, late, n_in_core,
and feature counts / rejections per method (tables/sync_check.md + tables/frontend.csv)."""
import csv, glob, re
R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
tot = {}
rows = []
for f in sorted(glob.glob(f'{R}/*_t1_L*/*/runstats.md')):
    seq, m = f.split('/')[-3], f.split('/')[-2]
    for line in open(f):
        if not line.startswith('| run_'):
            continue
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) < 13 or '/' not in c[2] or not c[4].isdigit():
            continue
        a, b = c[2].split('/')
        kept = [float(x) for x in c[8].split('/')]
        rej = [float(x) for x in c[9].split('/')]
        rows.append(dict(seq=seq, method=m, run=c[0], masks=int(a), images=int(b), fb_latest=int(c[4]), fb_empty=int(c[5]),
                         late=int(c[6]), kept_c0=kept[0], kept_c1=kept[1], rej_c0=rej[0], rej_c1=rej[1], in_core=int(c[12])))
for r in rows:
    t = tot.setdefault(r['method'], dict(runs=0, mismatch=0, fb=0, late=0, core=0, kept=0.0, rej=0.0))
    t['runs'] += 1; t['mismatch'] += r['masks'] != r['images']; t['fb'] += r['fb_latest'] + r['fb_empty']
    t['late'] += r['late']; t['core'] += r['in_core']; t['kept'] += r['kept_c0']; t['rej'] += r['rej_c0']
L = ['# mask sync / front-end check over all savior runs (savior-eval runstats)\n',
     '| method | runs | masks != images | fallbacks | late | n_in_core | kept/frame cam0 (mean) | rejected cam0 per run (mean) |',
     '|---|--:|--:|--:|--:|--:|--:|--:|']
for m, t in sorted(tot.items()):
    L.append(f"| {m} | {t['runs']} | {t['mismatch']} | {t['fb']} | {t['late']} | {t['core']} | {t['kept'] / t['runs']:.1f} | {t['rej'] / t['runs']:.0f} |")
open(f'{R}/tables/sync_check.md', 'w').write('\n'.join(L) + '\n')
with open(f'{R}/tables/frontend.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
print('\n'.join(L))
