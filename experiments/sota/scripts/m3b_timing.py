#!/usr/bin/env python3
"""m3b_timing.py : per-frame processing time of the SOTA baselines from results/sota/timing/<ds>_<seq>/<method>/run_01/timing.csv
(serial runs, one savior-sota container at a time, 4 CPUs; host load in results/sota/timing/load_*.txt).
VINS-Fusion / DynaVINS (patch P5): frontend = featureTracker.trackImage per stereo pair (20 Hz), backend = processImage per
processed frame (every 2nd pair, multiple_thread=1); 'per stereo pair' = frontend + backend/2 (amortised).
ORB-SLAM3: TrackStereo wall time per stereo pair (tracking thread; local mapping runs in parallel, not included); only
frames in state OK (2) are summarised, plus all frames. -> results/sota/tables/sota_timing.{md,csv,json}"""
import csv, glob, json, os, re
import numpy as np

R = '/home/sasa/workspace/savior_ws/results/sota'
LAB = {'vins_fusion': 'VINS-Fusion', 'dynavins': 'DynaVINS', 'orbslam3': 'ORB-SLAM3'}
rows = []
for f in sorted(glob.glob(f'{R}/timing/*_*/*/run_01/timing.csv')):
    m = f.split('/')[-3]; dsq = f.split('/')[-4]; ds, seq = dsq.split('_', 1)
    rr = list(csv.DictReader(open(f)))
    load = open(f'{R}/timing/load_{ds}_{seq}_{m}.txt').read() if os.path.isfile(f'{R}/timing/load_{ds}_{seq}_{m}.txt') else ''
    la = [float(x) for x in re.findall(r'load average: ([\d.]+)', load)]
    nc = [int(x) for x in re.findall(r'^(\d+)$', load, re.M)]
    comps = {}
    if 'kind' in rr[0]:
        for k in ('frontend', 'backend'):
            comps[k] = np.array([float(z['ms']) for z in rr if z['kind'] == k])
        comps['per_pair_amortised'] = None
    else:
        comps['track_all'] = np.array([float(z['ms']) for z in rr])
        comps['track_ok'] = np.array([float(z['ms']) for z in rr if z['state'] == '2'])
    for k, v in comps.items():
        if v is None:
            fe, be = comps['frontend'], comps['backend']
            mean = fe.mean() + be.mean() * len(be) / max(len(fe), 1)
            rows.append(dict(dataset=ds, seq=seq, method=m, label=LAB[m], component='per stereo pair (fe + be amortised)', n=len(fe),
                             median_ms=None, mean_ms=round(float(mean), 2), p90_ms=None, max_ms=None,
                             load1_start=la[0] if la else None, containers_start=nc[0] if nc else None))
            continue
        if not len(v):
            continue
        rows.append(dict(dataset=ds, seq=seq, method=m, label=LAB[m], component=k, n=len(v), median_ms=round(float(np.median(v)), 2),
                         mean_ms=round(float(v.mean()), 2), p90_ms=round(float(np.percentile(v, 90)), 2), max_ms=round(float(v.max()), 2),
                         load1_start=la[0] if la else None, containers_start=nc[0] if nc else None))
os.makedirs(R + '/tables', exist_ok=True)
with open(R + '/tables/sota_timing.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(rows, open(R + '/tables/sota_timing.json', 'w'), indent=1)
L = ['# M3b SOTA per-frame processing time\n',
     'Serial runs: one savior-sota:noetic container at a time (--cpus 4, OMP 2 threads, as the benchmark), run 1 (first offset), rate 0.5. '
     'VINS-Fusion / DynaVINS: front-end = feature tracking per stereo pair (20 Hz); back-end = sliding-window optimisation per processed '
     'frame (every 2nd pair, multiple_thread=1). ORB-SLAM3: TrackStereo per stereo pair (tracking thread only; local mapping runs in '
     'its own thread). load1 = host 1-min load average at start, containers = running docker containers on the host at start (other '
     'users\' jobs included).\n',
     '| dataset | seq | method | component | n | median ms | mean ms | p90 ms | max ms | load1 | containers |', '|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|']
for r in rows:
    g = lambda k: '-' if r[k] is None else r[k]  # noqa: E731
    L.append(f"| {r['dataset']} | {r['seq']} | {r['label']} | {r['component']} | {r['n']} | {g('median_ms')} | {g('mean_ms')} | {g('p90_ms')} | {g('max_ms')} | {g('load1_start')} | {g('containers_start')} |")
open(R + '/tables/sota_timing.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
