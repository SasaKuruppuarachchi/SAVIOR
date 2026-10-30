#!/usr/bin/env python3
"""rr_spill_analyze.py : task D tables from results/review_runs/spill/<seq>/<variant>.json (offline replay, t1).
-> results/review_runs/tables/spill.md / spill.json"""
import glob, json
RR = '/home/sasa/workspace/savior_ws/results/review_runs'
D = {}
for f in glob.glob(f'{RR}/spill/*/*.json'):
    d = json.load(open(f)); D[(d['seq'], d['variant'])] = d
VARS = ['sens_fix1', 'p7_nb', 'sf1_nomotion', 'sf1_noint']
LAB = {'sens_fix1': 'SAVIOR', 'p7_nb': 'SAVIOR-adaptive', 'sf1_nomotion': 'SAVIOR w/o motion', 'sf1_noint': 'SAVIOR w/o interaction'}
LV = ['L0', 'L1', 'L2', 'L3', 'all']
PC = ['person_static', 'person_moving', 'moving_object', 'static_object', 'unmatched']
PCL = {'person_static': 'standing person', 'person_moving': 'walking person', 'moving_object': 'moving forklift / carried load',
       'static_object': 'GT-static object (2nd hop)', 'unmatched': 'unmatched parent'}


def pcat(par, root=False):
    q = par.split('>')[1] if root else par.split('>')[0]
    cls, gl = q.split(':')[:2]
    if gl == 'none':
        return 'unmatched'
    if cls == 'person':
        return f'person_{gl}'
    return 'moving_object' if gl == 'moving' else 'static_object'


out = {}
L = ['# Task D: promotion spill onto GT-static objects\n',
     'Offline replay of the frozen pipeline on the t1 tuning split (all 20 Hz frames from the bag start; held-out t2 logs are '
     'stats_compact and have no per-instance records). Replay validated: per-frame (n_roots, n_promoted, n_held) identical to the '
     'online back-end v2 run_01 savior_stats of SAVIOR and SAVIOR-adaptive on all 8 sequences (35472/35472 frames).\n',
     'Unit: potential-class detection-frames (a detection is matched to the GT instance covering >= 30 % of its pixels, GT moving '
     'flag of that frame from moving.csv; unmatched detections excluded from shares). promoted = linked to a dynamic chain in this '
     'frame (interaction). GT-static share = static / (static + moving), by detection-frames and by mask pixels. Parent = the '
     'instance that promoted it (its own GT state).\n']
for v in VARS:
    L += [f'\n## {LAB[v]} ({v}): promoted detections\n',
          '| level | promoted det-frames | GT-static det-frames promoted / held (of all GT-static det-frames) | GT-static share (det) | GT-static share (px) | distinct GT-static instances promoted / static movable in view | '
          + ' | '.join(f'parent: {PCL[c]}' for c in PC) + ' |', '|---|--:|--:|--:|--:|--:|' + '--:|' * len(PC)]
    for lv in LV:
        seqs = [s for (s, vv) in D if vv == v and (lv == 'all' or s.endswith(lv))]
        c = {'moving': [0, 0], 'static': [0, 0], 'none': [0, 0]}
        par = {k: 0 for k in PC}
        rt = {k: 0 for k in PC}
        hop = {}
        ids = set(); inview = 0; allstatic = 0; heldstatic = 0
        for s in seqs:
            d = D[(s, v)]
            inview += d['n_static_movable_gt_in_view']
            for k, (n, px) in d['counts'].items():
                st, gl, sc, tc, pa = k.split('|')
                if gl == 'static':
                    allstatic += n
                    heldstatic += n if st == 'held' else 0
                if st != 'promoted':
                    continue
                c[gl][0] += n; c[gl][1] += px
                if gl == 'static' and pa != '-':
                    par[pcat(pa)] += n
                    rt[pcat(pa, True)] += n
                    h = pa.rsplit(':h', 1)[1]
                    hop[h] = hop.get(h, 0) + n
            ids |= {(s, i) for i in d['instances'].get('promoted', {}).get('static', [])}
        tot = sum(x[0] for x in c.values())
        sd = c['static'][0] / max(1, c['static'][0] + c['moving'][0])
        sp = c['static'][1] / max(1, c['static'][1] + c['moving'][1])
        ns = max(1, c['static'][0])
        out[f'{v}/{lv}'] = dict(promoted=tot, moving=c['moving'], static=c['static'], none=c['none'], static_share_det=sd,
                                static_share_px=sp, distinct_static=len(ids), static_in_view=inview, static_detframes=allstatic, static_held=heldstatic, parent=par, root=rt, hops=hop)
        L.append(f"| {lv} | {tot} | {100 * c['static'][0] / max(1, allstatic):.1f} % / {100 * heldstatic / max(1, allstatic):.1f} % | {100 * sd:.1f} % | {100 * sp:.1f} % | {len(ids)} / {inview} | "
                 + ' | '.join(f'{100 * par[k] / ns:.0f} %' for k in PC) + ' |')
    L += [f'\n{LAB[v]}: GT-static promotions by the ROOT of the chain (always-dynamic person or moving root) and by hop count\n',
          '| level | ' + ' | '.join(f'root: {PCL[c]}' for c in PC if c != 'static_object') + ' | root: GT-static object | 1 hop | 2 hops | 3 hops |',
          '|---|' + '--:|' * (len(PC) + 3)]
    for lv in LV:
        o = out[f'{v}/{lv}']; ns = max(1, o['static'][0]); r = o['root']; h = o['hops']
        L.append(f'| {lv} | ' + ' | '.join(f'{100 * r[k] / ns:.0f} %' for k in PC if k != 'static_object')
                 + f" | {100 * r['static_object'] / ns:.0f} % | " + ' | '.join(f"{100 * h.get(str(i), 0) / ns:.0f} %" for i in (1, 2, 3)) + ' |')
L += ['\nNotes: the "moving forklift / carried load" parent column is the reviewer\'s case (a GT-static stack promoted through '
      'contact with a moving vehicle or its load). SAVIOR w/o interaction has no promotions by construction (sanity check).']
open(f'{RR}/tables/spill.md', 'w').write('\n'.join(L) + '\n')
json.dump(out, open(f'{RR}/tables/spill.json', 'w'), indent=1)
print('\n'.join(L))
