#!/usr/bin/env python3
"""perception_waste.py : how much savior_node work goes to frames that OpenVINS drops (track_frequency 10.5 -> every 2nd frame),
and whether the mask hold time changes, v2 vs v1. Per savior-launch run: perception frames (savior_stats.jsonl lines), filter
measurements (FINAL line), frames kept by the filter (feature_stats.csv cam0 stamps), node_total ms on kept vs dropped frames,
FINAL hold avg / max, SAVIOR-edge deferred-mask counts. -> tables/perception_waste.md / .csv"""
import csv, glob, gzip, json, os, re
import numpy as np
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
H = R + '/backend_v2'
SRC = {'v2': H + '/runs', 'v1': {'sens_fix1': R + '/p7', 'p7_nb': R + '/p7', 'oracle_class_ext': R + '/p7', 'yolo_naive': R + '/p6_warehouse',
                                 'oracle_moving_ext': R + '/p6_warehouse', 'oracle_moving': R + '/p6_warehouse',
                                 'oracle_class_naive': R + '/p6_warehouse', 'savior_none': R + '/p6_warehouse', 'savior_edge': H + '/runs_v1'}}
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?hold avg=([\d.]+)ms max=([\d.]+)ms')
EDGE = re.compile(r'EDGE\] FINAL: .*?deferred_masks=(\d+) flagged=(\d+) .*?removed_obs=(\d+) too_late=(\d+)')
rows = []
for b in ('v2', 'v1'):
    for m in SRC['v1']:
        base = SRC['v2'] if b == 'v2' else SRC['v1'][m]
        for rd in sorted(glob.glob(f'{base}/*_t1_*/{m}/run_*')):
            st = next((f for f in (f'{rd}/savior_stats.jsonl.gz', f'{rd}/savior_stats.jsonl') if os.path.isfile(f)), None)
            lg = next((f for f in (f'{rd}/launch.log.gz', f'{rd}/launch.log') if os.path.isfile(f)), None)
            fs = f'{rd}/feature_stats.csv'
            if not (st and lg and os.path.isfile(fs)):
                continue
            kept = set()
            with open(fs) as fh:
                for x in csv.DictReader(fh):
                    if x['cam_id'] == '0':
                        kept.add(round(float(x['timestamp']), 3))
            tk, td = [], []
            op = gzip.open if st.endswith('.gz') else open
            with op(st, 'rt') as fh:
                for l in fh:
                    try:
                        j = json.loads(l)
                    except Exception:
                        continue
                    t = round(j['stamp']['sec'] + j['stamp']['nanosec'] * 1e-9, 3)
                    v = j.get('timings_ms', {}).get('node_total')
                    if v is None:
                        continue
                    (tk if t in kept else td).append(v)
            fin = edge = None
            with (gzip.open(lg, 'rt', errors='replace') if lg.endswith('.gz') else open(lg, errors='replace')) as fh:
                for l in fh:
                    if 'SAVIOR-MASK] FINAL' in l:
                        fin = FIN.search(l)
                    elif 'SAVIOR-EDGE] FINAL' in l:
                        edge = EDGE.search(l)
            seq, _, run = rd.split('/')[-3:]
            rows.append(dict(backend=b, method=m, seq=seq, run=run, perception_frames=len(tk) + len(td), filter_meas=int(fin[1]) if fin else -1,
                             kept=len(tk), dropped=len(td), ms_kept=float(np.sum(tk)), ms_dropped=float(np.sum(td)),
                             med_kept=float(np.median(tk)) if tk else 0, med_dropped=float(np.median(td)) if td else 0,
                             hold_avg=float(fin[2]) if fin else -1, hold_max=float(fin[3]) if fin else -1,
                             deferred=int(edge[1]) if edge else '', flagged=int(edge[2]) if edge else '',
                             removed_obs=int(edge[3]) if edge else '', too_late=int(edge[4]) if edge else ''))
os.makedirs(H + '/tables', exist_ok=True)
if rows:
    with open(H + '/tables/perception_waste.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
L = ['# Perception work on frames the filter drops (t1, savior-launch methods)\n',
     'frames = savior_node frames (one mask pair each); meas = OpenVINS measurements (FINAL); dropped share = node_total time on frames '
     'the filter never processes / all node time; hold = FINAL mask hold time (image waits for its masks) avg / max over runs; '
     'edge: deferred masks attached, features flagged, too_late (SAVIOR-edge only)\n',
     '| method | backend | runs | frames/run | meas/run | dropped share of node time | node ms kept / dropped (median) | hold avg ms | hold max ms | edge deferred / flagged / too_late (per run) |',
     '|---|---|--:|--:|--:|--:|--:|--:|--:|---|']
for m in SRC['v1']:
    for b in ('v2', 'v1'):
        rs = [r for r in rows if r['method'] == m and r['backend'] == b]
        if not rs:
            continue
        tot = sum(r['ms_kept'] + r['ms_dropped'] for r in rs)
        e = (f"{np.mean([r['deferred'] for r in rs]):.0f} / {np.mean([r['flagged'] for r in rs]):.0f} / {sum(r['too_late'] for r in rs)}"
             if rs[0]['deferred'] != '' else '-')
        L.append(f"| {m} | {b} | {len(rs)} | {np.mean([r['perception_frames'] for r in rs]):.0f} | {np.mean([r['filter_meas'] for r in rs]):.0f} | "
                 f"{100 * sum(r['ms_dropped'] for r in rs) / tot if tot else 0:.1f} % | {np.median([r['med_kept'] for r in rs]):.1f} / "
                 f"{np.median([r['med_dropped'] for r in rs]):.1f} | {np.mean([r['hold_avg'] for r in rs]):.1f} | "
                 f"{max(r['hold_max'] for r in rs):.1f} | {e} |")
open(H + '/tables/perception_waste.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
