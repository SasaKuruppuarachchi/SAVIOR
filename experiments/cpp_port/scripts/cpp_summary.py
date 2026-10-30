#!/usr/bin/env python3
"""cpp_summary.py: per-stage CPU timing Python vs C++ (offline, same frames, same process, 1 OpenCV / BLAS thread; equiv_offline.py
--threads 1 on hall_t1_L3 + aisles_t1_L3 -> timing_offline/<seq>.json), segmenter host timing (equiv_yolo.py --ultra ->
timing_offline/yolo_<engine>_<seq>.json), node timing (tables/timing*.json from cpp_timing.py) and the updated Orin NX 8 GB
estimate with the compute model of results/edge_study/scripts/edge_summary.py:
  Orin CPU = desktop CPU per frame x K_CPU (3.5, range 3.0-4.5; Cortex-A78AE 2.0 GHz vs Zen 5 5.4 GHz single thread)
  Orin GPU = GFLOPs / 2.7 TFLOPS + 1.5 ms per keyframe; OpenVINS = desktop ov_total x K_CPU. Orin numbers are ESTIMATES.
-> tables/timing_stages.md / .json, tables/orin_estimate.md / .json. Host python (numpy)."""
import glob
import json
import os

import numpy as np

R = '/home/sasa/workspace/savior_ws/results/cpp_port'
T = R + '/tables'
K, K_LO, K_HI = 3.5, 3.0, 4.5
EFF_TFLOPS, FIXED_MS = 2.7, 1.5
GFLOPS = {'s672': 23.47, 'n672': 6.55}
OV_MS = 2.7
STAGES = ['depth', 'motion', 'gating', 'tracking', 'extension', 'compose', 'total']


def mean_of(d, k):
    return d[k]['mean'] if k in d else float('nan')


def main():
    off = sorted(f for f in glob.glob(f'{R}/timing_offline/*_t1_*.json') if not os.path.basename(f).startswith('yolo_'))
    py, cp = {}, {}
    nfr = 0
    for f in off:
        j = json.load(open(f))
        n = j['acc']['frames']
        nfr += n
        for s in STAGES + ['m_flow_ego', 'm_assoc', 'm_points']:
            py.setdefault(s, []).append((mean_of(j['timing_ms']['py'], s), n))
            cp.setdefault(s, []).append((mean_of(j['timing_ms']['cpp'], s), n))
        py.setdefault('call', []).append((mean_of(j['timing_ms']['py'], 'call'), n))
        cp.setdefault('call', []).append((mean_of(j['timing_ms']['cpp'], 'call'), n))
    w = lambda v: sum(a * n for a, n in v) / sum(n for _, n in v) if v else float('nan')  # noqa: E731
    P = {k: w(v) for k, v in py.items()}
    C = {k: w(v) for k, v in cp.items()}
    yo = {}
    for f in glob.glob(f'{R}/timing_offline/yolo_*.json'):
        j = json.load(open(f))
        eng = os.path.basename(f).split('_')[1]
        yo.setdefault(eng, []).append(j['timing_ms'])
    Y = {}
    for eng, ts in yo.items():
        Y[eng] = {k: float(np.mean([t[k]['mean'] for t in ts if t.get(k)])) for k in ('cpp', 'cpp_infer', 'cpp_masks', 'ultra')}
    L = ['# Per-stage CPU time per frame: Python vs C++ (desktop, offline, identical frames / detections, 1 OpenCV + BLAS thread)\n',
         f'hall_t1_L3 + aisles_t1_L3, {nfr} frames, frame-weighted means [ms]; both pipelines in the same process, interleaved '
         'frame by frame (tools/equiv_offline.py --threads 1). C++ "total" = SaviorPipeline::process, Python "total" = '
         'SaviorPipeline.process (instance construction excluded in both).\n',
         '| stage | Python | C++ | C++ / Python |', '|---|--:|--:|--:|']
    for s in STAGES + ['m_flow_ego', 'm_assoc', 'm_points']:
        L.append(f'| {s} | {P[s]:.2f} | {C[s]:.2f} | {C[s] / P[s]:.2f} |' if P.get(s) == P.get(s) and P.get(s) else f'| {s} | - | - | - |')
    if Y:
        L += ['\n## Segmenter (same TensorRT engine; wall time per frame incl. pre/post-processing and mask transfer, GPU shared)\n',
              '| engine | Ultralytics predict (fast_masks) | C++ predict | of which TensorRT enqueue+sync | C++ mask stage |',
              '|---|--:|--:|--:|--:|']
        for eng, y in sorted(Y.items()):
            L.append(f"| {eng} | {y['ultra']:.2f} | {y['cpp']:.2f} | {y['cpp_infer']:.2f} | {y['cpp_masks']:.2f} |")
    # node timing
    nt = {}
    for tag in ('timing', 'timing_cpus4'):
        f = f'{T}/{tag}.json'
        if os.path.isfile(f):
            nt[tag] = json.load(open(f))
    if nt:
        L += ['\n## savior_node online (closed loop, quiet machine, rate 1.0; median / p90 / mean ms per frame)\n',
              '| run | cores | segment | depth | motion | gating | tracking | compose | node_total | ov_total |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for tag, d in nt.items():
            for m, v in sorted(d.items()):
                cells = []
                for k in ('segment', 'depth', 'motion', 'gating', 'tracking', 'compose', 'node_total', 'ov_total'):
                    cells.append('{:.1f} / {:.1f} / {:.1f}'.format(v[k][0], v[k][1], v[k][3]) if k in v else '-')
                L.append(f"| {m} | {'all 48' if tag == 'timing' else '4 (cpuset 0-3)'} | " + ' | '.join(cells) + ' |')
    open(f'{T}/timing_stages.md', 'w').write('\n'.join(L) + '\n')
    json.dump({'python': P, 'cpp': C, 'yolo': Y, 'node': nt}, open(f'{T}/timing_stages.json', 'w'), indent=1)
    print('\n'.join(L))
    # ---------------------------------------------------------------- Orin estimate
    node = nt.get('timing', {})
    def nmean(m, k, default):
        return node.get(m, {}).get(k, [None, None, None, default])[3]
    ov = nmean('cpp_main_final', 'ov_total', OV_MS)
    rows = []
    py_ovh = nmean('py_main_ctrl', 'node_total', float('nan')) - nmean('py_main_ctrl', 'total', float('nan')) - nmean('py_main_ctrl', 'segment', float('nan'))
    cp_ovh = nmean('cpp_main_final', 'node_total', float('nan')) - nmean('cpp_main_final', 'total', float('nan')) - nmean('cpp_main_final', 'segment', float('nan'))
    for eng in ('s672', 'n672'):
        y = Y.get(eng, Y.get('s672', {}))
        gpu_desk = y.get('cpp_infer', 0.0)
        for impl in ('python', 'cpp'):
            pipe = P['total'] if impl == 'python' else C['total']
            seg_host = (y.get('ultra', float('nan')) - gpu_desk) if impl == 'python' else (y.get('cpp', float('nan')) - gpu_desk)
            ovh = py_ovh if impl == 'python' else cp_ovh
            cpu = pipe + max(seg_host, 0.0) + max(ovh, 0.0)
            gpu = GFLOPS[eng] / EFF_TFLOPS + FIXED_MS
            o = ov * K
            rows.append(dict(engine=eng, impl=impl, desktop_cpu=cpu, pipe=pipe, seg_host=seg_host, node_ovh=ovh,
                             orin_cpu=cpu * K, orin_cpu_lo=cpu * K_LO, orin_cpu_hi=cpu * K_HI, orin_gpu=gpu, orin_ov=o,
                             orin_total=cpu * K + gpu + o, orin_total_lo=cpu * K_LO + gpu + ov * K_LO,
                             orin_total_hi=cpu * K_HI + gpu + ov * K_HI))
    E = ['# Orin NX 8 GB per camera frame (20 Hz budget 50 ms): Python vs C++ savior_node (ESTIMATE)\n',
         'Compute model of results/edge_study (edge_summary.py): desktop CPU per frame = pipeline (offline, 1 thread) + segmenter host '
         'side (wall predict - TensorRT enqueue/sync) + node overhead (node_total - pipeline total - segment, online timing); '
         f'Orin CPU = x {K} (range {K_LO}-{K_HI}); Orin GPU = GFLOPs / {EFF_TFLOPS} TFLOPS + {FIXED_MS} ms; OpenVINS = desktop '
         f'ov_total ({ov:.2f} ms) x K. Serial sum (no overlap of segmenter GPU time and CPU stages assumed). Not measured on a device.\n',
         '| segmenter | savior_node | desktop CPU ms (pipeline + seg host + node) | Orin CPU ms [range] | Orin GPU ms | Orin OV ms | Orin total ms [range] | vs Python |',
         '|---|---|--:|--:|--:|--:|--:|--:|']
    base = {r['engine']: r['orin_total'] for r in rows if r['impl'] == 'python'}
    for r in rows:
        E.append(f"| {r['engine']} | {r['impl']} | {r['desktop_cpu']:.1f} ({r['pipe']:.1f} + {r['seg_host']:.1f} + {r['node_ovh']:.1f}) | "
                 f"{r['orin_cpu']:.0f} [{r['orin_cpu_lo']:.0f}-{r['orin_cpu_hi']:.0f}] | {r['orin_gpu']:.1f} | {r['orin_ov']:.1f} | "
                 f"{r['orin_total']:.0f} [{r['orin_total_lo']:.0f}-{r['orin_total_hi']:.0f}] | {100 * (r['orin_total'] / base[r['engine']] - 1):+.0f} % |")
    open(f'{T}/orin_estimate.md', 'w').write('\n'.join(E) + '\n')
    json.dump(rows, open(f'{T}/orin_estimate.json', 'w'), indent=1)
    print('\n'.join(E))


if __name__ == '__main__':
    main()
