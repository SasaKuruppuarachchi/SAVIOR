#!/usr/bin/env python3
"""offsum.py <off dir> [variants]: pooled offline metrics per variant (t1, all 8 sequences) vs main."""
import glob, json, sys, os
import numpy as np
D = sys.argv[1]
want = sys.argv[2].split(',') if len(sys.argv) > 2 else None
by = {}
for f in glob.glob(f'{D}/*_t1_*/*.json'):
    d = json.load(open(f))
    by.setdefault(d['variant'], []).append(d)
ANY = int(__import__('os').environ.get('ANY', '0'))   # 1: masked = >= 50 % of the instance on mask >= 128 (OpenVINS view)
def pool(ds, key):
    n = m = 0
    for d in ds:
        e = d['gt_centric'].get(key)
        if e:
            n += e[0]; m += e[2] if (ANY and len(e) > 2) else e[1]
    return m / n if n else float('nan')
def onset(ds):
    lat = []
    for d in ds:
        for k, v in d['onset'].items():
            if k.split(':')[0] in ('person', 'forklift'):
                lat += [3.0 if x is None else x for x in v]
    return (np.median(lat), np.percentile(lat, 90)) if lat else (np.nan, np.nan)
rows = []
for v in sorted(by, key=lambda x: (x != 'main', x)):
    if want and v not in want:
        continue
    ds = by[v]
    if len(ds) < 8:
        pass
    pix = np.sum([d['pix']['L_core_vs_moving'] for d in ds], axis=0)
    rec_px = pix[0] / max(1, pix[0] + pix[2])
    ag = {k: np.mean([d['agree'][k] for d in ds]) for k in ('Lcore_pool', 'Rcore_pool', 'same_frac')}
    ia = [d['inst_agree'] for d in ds if d['inst_agree'].get('n_rel')]
    st = {k: sum(x['status'][k] for x in ia) for k in ('mm', 'mu', 'um', 'uu')} if ia else None
    stag = (st['mm'] + st['uu']) / max(1, sum(st.values())) if st else float('nan')
    dzm = np.median([x['dz_med'] for x in ia if 'dz_med' in x]) if ia else float('nan')
    dzw10 = np.mean([x['dz_w10'] for x in ia if 'dz_w10' in x]) if ia else float('nan')
    cov = (sum(x['var_depth'] for x in ia) / max(1, sum(x['n_rel'] for x in ia)), sum(x['ref_depth'] for x in ia) / max(1, sum(x['n_rel'] for x in ia))) if ia else (np.nan, np.nan)
    cpu = np.mean([d['cpu_ms'][3] for d in ds])
    on = onset(ds)
    mov = {c: pool(ds, f'{c}:moving') for c in ('person', 'forklift')}
    rows.append((v, len(ds), mov['person'], mov['forklift'], pool(ds, 'carried_box:moving'), pool(ds, 'carried_pallet:moving'),
                 pool(ds, 'box:static'), pool(ds, 'pallet:static'), pool(ds, 'forklift:static'), rec_px, on[0], on[1],
                 ag['Lcore_pool'], ag['Rcore_pool'], stag, dzm, dzw10, cov[0], cov[1], cpu))
hdr = 'variant n mvPerson mvFork carBox carPal stBoxMasked stPalMasked stForkMasked pxRecall onsetMed onsetP90 IoU_L IoU_R statusAgree dzMed dzW10 covVar covRef cpuMeanMs'.split()
print(' | '.join(hdr))
for r in rows:
    print(' | '.join([r[0], str(r[1])] + [f'{x:.3f}' if isinstance(x, float) else str(x) for x in r[2:]]))
