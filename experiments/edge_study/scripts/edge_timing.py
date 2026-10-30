#!/usr/bin/env python3
"""edge_timing.py (EDGE; from p7timing.py; adds mean, the asyncseg "predict" stage and TIMING_DIR):
p7timing.py: stage F timing (results/p7/timing/<seq>/<method>/run_XX, idle machine, one container, rate 1.0).
savior_node per-stage timings_ms (savior_stats) and ov_msckf per-update timing (record_timing_information file
ov_timing.txt, seconds -> ms). median / p90 / p99 per (method, seq) and pooled per method.
-> tables/timing.json {method: {stage: [med, p90, p99]}} (pooled), tables/timing_full.json (also method@seq),
   tables/timing.md. Host python (numpy only)."""
import glob, gzip, json, os
from collections import defaultdict
import numpy as np
R = '/home/sasa/workspace/savior_ws/results/edge_study'
TD = os.environ.get('TIMING_DIR', 'timing')
ST = ['convert', 'segment', 'depth', 'motion', 'gating', 'tracking', 'extension', 'compose', 'predict', 'total', 'node_total']
OV = ['ov_tracking', 'ov_propagation', 'ov_msckf_update', 'ov_slam_update', 'ov_slam_delayed', 'ov_retri_marg', 'ov_total']
acc = defaultdict(lambda: defaultdict(list))
nrun = defaultdict(int)
for rd in sorted(glob.glob(f'{R}/{TD}/*/*/run_*')):
    seq, m = rd.split('/')[-3], rd.split('/')[-2]
    keys = (f'{m}@{seq}', m)
    for k in keys:
        nrun[k] += 1
    for f in glob.glob(f'{rd}/savior_stats.jsonl*'):
        op = gzip.open if f.endswith('.gz') else open
        for ln in op(f, 'rt'):
            try:
                t = json.loads(ln).get('timings_ms', {})
            except ValueError:
                continue
            for s in ST:
                if s in t:
                    for k in keys:
                        acc[k][s].append(t[s])
            for k in keys:
                acc[k]['_frames'].append(1)
                acc[k]['_key'].append(1.0 if json.loads(ln).get('key', True) else 0.0)
    f = f'{rd}/ov_timing.txt'
    if os.path.isfile(f):
        hdr = [h.strip() for h in open(f).readline().lstrip('#').split(',')]
        cols = {'tracking': 'ov_tracking', 'propagation': 'ov_propagation', 'msckf update': 'ov_msckf_update',
                'slam update': 'ov_slam_update', 'slam delayed': 'ov_slam_delayed', 're-tri & marg': 'ov_retri_marg', 'total': 'ov_total'}
        a = np.loadtxt(f, delimiter=',', comments='#', ndmin=2)
        for j, h in enumerate(hdr):
            if h in cols and a.size:
                for k in keys:
                    acc[k][cols[h]].extend((a[:, j] * 1e3).tolist())
out = {r: {k: [float(np.median(v)), float(np.percentile(v, 90)), float(np.percentile(v, 99)), float(np.mean(v))] for k, v in d.items() if v and not k.startswith('_')}
       for r, d in acc.items()}
for r in out:
    out[r]['_n_runs'] = nrun[r]
    out[r]['_n_frames'] = len(acc[r].get('node_total', acc[r].get('ov_total', [])))
    out[r]['_key_frac'] = float(np.mean(acc[r]['_key'])) if acc[r].get('_key') else 1.0
json.dump({r: v for r, v in out.items() if '@' not in r}, open(f'{R}/tables/{TD}.json', 'w'), indent=1)
json.dump(out, open(f'{R}/tables/{TD}_full.json', 'w'), indent=1)
hw = open(f'/home/sasa/workspace/savior_ws/results/p7/tables/timing_hardware.txt').read().strip()
L = ['# EDGE timing: median / p90 / p99 / mean ms per frame (savior_node) or per update (ov_msckf)\n',
     'Idle machine, one container at a time, bag rate 1.0 (20 Hz stereo), 3 start offsets per method and sequence '
     '(hall_t1_L3, aisles_t1_L3). `_fast` / `_slow` = segmenter.fast_masks on / off (bit-identical masks).',
     'savior_node stages: segment = YOLO TensorRT predict + mask transfer; node_total = callback incl. ROS conversion and publish.',
     'ov_* = OpenVINS (ov_msckf record_timing_information): tracking = KLT front-end incl. masking, the rest = back-end.\n']
if hw:
    L += ['Hardware: ' + hw.replace('\n', '; ') + '\n']
SC = [s for s in ST if s not in ('convert', 'total')] + ['ov_tracking', 'ov_msckf_update', 'ov_slam_update', 'ov_retri_marg', 'ov_total']
for title, pick in (('Pooled over both sequences', lambda r: '@' not in r), ('Per sequence', lambda r: '@' in r)):
    L += [f'\n## {title}\n', '| run | runs | frames | ' + ' | '.join(SC) + ' |', '|---|--:|--:|' + '---|' * len(SC)]
    for r in sorted(filter(pick, out)):
        L.append(f"| {r} | {out[r]['_n_runs']} | {out[r]['_n_frames']} | " +
                 ' | '.join('{:.1f} / {:.1f} / {:.1f} / {:.1f}'.format(*out[r][k]) if k in out[r] else '-' for k in SC) + ' |')
open(f'{R}/tables/{TD}.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
