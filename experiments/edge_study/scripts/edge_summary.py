#!/usr/bin/env python3
"""edge_summary.py: EDGE study tables + Pareto figure.

Inputs: closed-loop paired ATE (tables/ate_<tag>.json from edge_analyze.py, ref sens_fix1), offline metrics (scratch off/,
edgeeval.py, 8 t1 sequences), offline CPU per frame, quiet-machine timing (tables/timing*.json, if present), engine GFLOPs.
Outputs: tables/edge_offline.md, tables/edge_closed_loop.md (+ .json), tables/edge_compute.md, figures/pareto.{png,pdf}.

Compute model (per camera frame, 20 Hz):
  desktop CPU  = pipeline CPU (offline edgeeval cpu_ms mean, 1 thread, keyframes + prediction)
                 + node overhead (ROS conversion / publish, timing runs) + segmenter host side (ultralytics pre/post) x key_frac
  desktop GPU  = TensorRT kernel time (trtbench.py) x key_frac
  Orin NX 8 GB (ESTIMATE): CPU x K_CPU (Cortex-A78AE 2.0 GHz vs Zen 5 5.4 GHz, single-thread Python/OpenCV: 3.5, range 3-4.5);
                 GPU = GFLOPs / EFF_TFLOPS + FIXED_MS per keyframe (FP16 TensorRT, 2.7 effective TFLOPS, 1.5 ms launch / NMS
                 floor; Orin NX 8 GB: 1024 CUDA cores / 32 tensor cores @ 765 MHz); OpenVINS x K_CPU.
"""
import glob, json, math, os, sys
import numpy as np

R = '/home/sasa/workspace/savior_ws/results/edge_study'
SCR = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge'
sys.path.insert(0, SCR + '/scripts')
from edge_variants import VARIANTS  # noqa: E402
K_CPU, K_CPU_LO, K_CPU_HI = 3.5, 3.0, 4.5
EFF_TFLOPS, FIXED_MS = 2.7, 1.5
GFLOPS = {'s672': 23.47, 's512': 13.39, 's416': 8.45, 'n672': 6.55, 'n512': 3.73, 'n416': 2.35}
# desktop measured constants (filled from the timing runs when present, else P7 stage F values)
NODE_OVH_MS = 0.6        # convert + publish + stats (node_total - pipeline total - segment), P7 stage F
SEG_HOST_MS = 2.4        # segment stage (3.2 ms median, fast masks) - TensorRT kernel (0.77 ms)
GPU_MS = {'s672': 0.77, 'n672': 0.71, 's512': 0.72, 'n512': 0.67, 's416': 0.67, 'n416': 0.63}   # trtbench (latency-bound)
OV_MS = 2.7              # OpenVINS ov_total median per update, P7 stage F

# ------------------------------------------------------------------ offline metrics
by = {}
for f in glob.glob(f'{SCR}/off/*_t1_*/*.json'):
    d = json.load(open(f))
    by.setdefault(d['variant'], []).append(d)


def pool(ds, key, any_=True):
    n = m = 0
    for d in ds:
        e = d['gt_centric'].get(key)
        if e:
            n += e[0]
            m += e[2] if (any_ and len(e) > 2) else e[1]
    return m / n if n else float('nan')


def onset(ds):
    lat = []
    for d in ds:
        for k, v in d['onset'].items():
            if k.split(':')[0] in ('person', 'forklift'):
                lat += [3.0 if x is None else x for x in v]
    return float(np.median(lat)), float(np.percentile(lat, 90))


def offline(v):
    ds = by.get(v, [])
    if len(ds) < 8:
        return None
    nmv = sum(d['gt_centric'].get(f'{c}:moving', [0, 0, 0])[0] for d in ds for c in ('person', 'forklift'))
    mmv = sum((lambda e: e[2] if len(e) > 2 else e[1])(d['gt_centric'].get(f'{c}:moving', [0, 0, 0])) for d in ds for c in ('person', 'forklift'))
    st_n = sum(d['gt_centric'].get(f'{c}:static', [0, 0, 0])[0] for d in ds for c in ('box', 'pallet', 'forklift'))
    st_m = sum((lambda e: e[2] if len(e) > 2 else e[1])(d['gt_centric'].get(f'{c}:static', [0, 0, 0])) for d in ds for c in ('box', 'pallet', 'forklift'))
    pix = np.sum([d['pix']['L_any_vs_moving'] for d in ds], axis=0)
    o = onset(ds)
    nk = sum(d['n_key'] for d in ds) / max(1, sum(d['frames'] for d in ds))
    cpu = float(np.sum([d['cpu_ms'][3] * d['frames'] for d in ds]) / max(1, sum(d['frames'] for d in ds)))
    return {'recall_moving': mmv / max(1, nmv), 'recall_person': pool(ds, 'person:moving'), 'recall_forklift': pool(ds, 'forklift:moving'),
            'carried': (pool(ds, 'carried_box:moving') + pool(ds, 'carried_pallet:moving')) / 2,
            'static_kept': 1.0 - st_m / max(1, st_n), 'px_recall': pix[0] / max(1, pix[0] + pix[2]),
            'onset_med': o[0], 'onset_p90': o[1], 'iou_l': float(np.mean([d['agree']['Lany_pool'] for d in ds])),
            'key_frac': nk, 'cpu_ms': cpu}


# ------------------------------------------------------------------ closed loop
def closed():
    out = {}
    for f in [f'{R}/tables/ate_final.json']:
        d = json.load(open(f))
        for r in d['paired']:
            if r['ref'] != 'sens_fix1':
                continue
            out.setdefault(r['method'], {})[r['group']] = r
        for s, ms in d['median'].items():
            for m, runs in ms.items():
                e = out.setdefault(m, {})
                e.setdefault('_fail', {})[s] = sum(1 for x in runs.values() if (x if isinstance(x, (int, float)) else float(x)) > 2.0)
                e.setdefault('_n', {})[s] = len(runs)
    return out


CL = closed()
MAIN_OFF = offline('main')


def det_of(var):
    return VARIANTS.get(var, {}).get('det', 's672')


def compute(var):
    o = offline(var)
    if o is None:
        return None
    kf = o['key_frac']
    det = det_of(var)
    cpu = o['cpu_ms'] + NODE_OVH_MS + SEG_HOST_MS * kf
    gpu = GPU_MS[det] * kf
    orin_cpu = cpu * K_CPU
    orin_gpu = (GFLOPS[det] / EFF_TFLOPS + FIXED_MS) * kf
    return {'cpu': cpu, 'gpu': gpu, 'desk_total': cpu + gpu + OV_MS, 'orin_cpu': orin_cpu, 'orin_gpu': orin_gpu,
            'orin_ov': OV_MS * K_CPU, 'orin_total': orin_cpu + orin_gpu + OV_MS * K_CPU,
            'orin_cpu_lo': cpu * K_CPU_LO, 'orin_cpu_hi': cpu * K_CPU_HI, 'key_frac': kf}


def var_of(method):
    if method.startswith('e_c_sp_r10_L50_dfr') or method == 'e_c_sp_r10_L50_dfr100':
        return 'c_sp_r10_L50'
    if method.startswith('e_c_sp_r10_dfr'):
        return 'c_sp_r10'
    if method.startswith('e_L'):
        return 'main'
    if method.startswith('e_c_n672_L'):
        return 'seg_n672'
    return method[2:]


IDEA = lambda v: ('1 sparse depth' if v.startswith('sp') else '2 async seg' if v.startswith('as') else '3 deferred' if v.startswith('L')
                  else '5 segmenter' if v.startswith('seg') else 'combination' if v.startswith('c_') else 'main')

if __name__ == '__main__':
    os.makedirs(f'{R}/tables', exist_ok=True)
    # offline table
    L = ['# EDGE offline metrics (t1, 8 sequences, cached YOLO detections; masks as OpenVINS sees them: >= 128)\n',
         'recall = GT moving person/forklift instance-frames with >= 50 % of their pixels masked; static kept = static box/pallet/forklift',
         'instance-frames NOT masked; carried = mean of carried box / pallet on moving forklifts masked; IoU = left mask (>= 128) IoU vs the',
         'frozen main (pooled); CPU = pipeline CPU ms per frame (1 thread, offline, mean; keyframes + prediction).\n',
         '| variant | idea | key frac | recall moving | person | forklift | carried | static kept | px recall | onset med / p90 [s] | IoU vs main | CPU ms/frame | CPU vs main |',
         '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    rows = []
    for v in sorted(by, key=lambda x: (x != 'main', IDEA(x), x)):
        o = offline(v)
        if o is None:
            continue
        rows.append(v)
        L.append(f"| {v} | {IDEA(v)} | {o['key_frac']:.2f} | {o['recall_moving']:.3f} ({100 * (o['recall_moving'] - MAIN_OFF['recall_moving']):+.1f}) | "
                 f"{o['recall_person']:.3f} | {o['recall_forklift']:.3f} | {o['carried']:.3f} | {o['static_kept']:.3f} | {o['px_recall']:.3f} | "
                 f"{o['onset_med']:.2f} / {o['onset_p90']:.2f} | {o['iou_l']:.3f} | {o['cpu_ms']:.1f} | {100 * (o['cpu_ms'] / MAIN_OFF['cpu_ms'] - 1):+.0f} % |")
    open(f'{R}/tables/edge_offline.md', 'w').write('\n'.join(L) + '\n')
    # closed-loop + pass/fail + compute
    L = ['# EDGE closed loop vs the frozen main sens_fix1 (t1, 8 seq x 10 offsets; paired geometric-mean ATE change, bootstrap 95 % CI, '
         'Wilcoxon, Holm over the methods within each group)\n',
         'Criterion (CRITERION.txt, written before the runs): L0+L1 and L2+L3 change <= +10 %, 0 failures on hall L3, offline moving recall',
         'within 3 points of the main. "uncertain" = point estimate passes but the CI upper bound exceeds +10 %.\n',
         '| method | idea | L0+L1 | L2+L3 | all | hall L3 | failures all / hall L3 | recall diff [pt] | Orin est. ms/frame (CPU+GPU+OV) | saving vs main | verdict |',
         '|---|---|---|---|---|---|---|--:|--:|--:|---|']
    cm = compute('main')
    res = {}
    for m in sorted(CL, key=lambda x: (IDEA(var_of(x)), x)):
        if not m.startswith('e_') or m == 'e_main' or m.startswith('e_nb'):
            continue
        g = CL[m]
        if 'L0+L1' not in g or 'L2+L3' not in g:
            continue
        v = var_of(m)
        o = offline(v)
        c = compute(v)
        nf = sum(g['_fail'].values())
        nh = g['_fail'].get('hall_t1_L3', 0)
        cell = lambda r: f"{r['gm']:+.1f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] H {r.get('holm', 1):.2f}"
        rd = 100 * (o['recall_moving'] - MAIN_OFF['recall_moving']) if o else float('nan')
        ok = g['L0+L1']['gm'] <= 10 and g['L2+L3']['gm'] <= 10 and nh == 0 and (o is None or rd >= -3)
        unc = ok and (g['L0+L1']['ci'][1] > 10 or g['L2+L3']['ci'][1] > 10)
        verdict = ('PASS (uncertain)' if unc else 'PASS') if ok else 'FAIL'
        if o is None:
            verdict += ' (no offline recall)'
        sav = 100 * (1 - c['orin_total'] / cm['orin_total']) if c else float('nan')
        res[m] = {'var': v, 'idea': 'combination' if m.startswith('e_c_') else IDEA(v if not m.startswith('e_L') else 'L'), 'L01': g['L0+L1'], 'L23': g['L2+L3'], 'all': g.get('all'),
                  'hall_L3': g.get('hall_L3'), 'fail': nf, 'fail_hall_L3': nh, 'recall_diff_pt': rd, 'compute': c, 'saving_pct': sav,
                  'verdict': verdict}
        L.append(f"| {m} | {res[m]['idea']} | {cell(g['L0+L1'])} | {cell(g['L2+L3'])} | {cell(g['all']) if 'all' in g else '-'} | "
                 f"{cell(g['hall_L3']) if 'hall_L3' in g else '-'} | {nf} / {nh} | {rd:+.1f} | "
                 f"{c['orin_total']:.1f} | {sav:+.0f} % | {verdict} |" if c else
                 f"| {m} | {res[m]['idea']} | {cell(g['L0+L1'])} | {cell(g['L2+L3'])} | - | - | {nf} / {nh} | - | - | - | {verdict} |")
    open(f'{R}/tables/edge_closed_loop.md', 'w').write('\n'.join(L) + '\n')
    json.dump(res, open(f'{R}/tables/edge_closed_loop.json', 'w'), indent=1, default=str)
    # compute table
    L = ['# EDGE compute per camera frame (20 Hz): desktop measured / modelled, Orin NX 8 GB ESTIMATE (see edge_summary.py docstring)\n',
         f'K_CPU = {K_CPU} (range {K_CPU_LO}-{K_CPU_HI}), GPU = GFLOPs / {EFF_TFLOPS} TFLOPS + {FIXED_MS} ms per keyframe, OpenVINS {OV_MS} ms x K_CPU.\n',
         'measured = quiet-machine online timing (tables/timing.md): savior_node node_total mean per frame (incl. segment), OpenVINS ov_total mean; '
         'cpus4 = same with docker --cpuset-cpus 0-3 (tables/timing_cpus4.md).\n',
         '| variant | key frac | segmenter (GFLOPs) | desktop CPU ms (model) | desktop node_total measured mean [p90] | cpus4 node_total mean [p90] | OV measured mean | desktop GPU ms | Orin CPU ms [range] | Orin GPU ms | Orin OV ms | Orin total ms | vs main |',
         '|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    TM = json.load(open(f'{R}/tables/timing.json')) if os.path.isfile(f'{R}/tables/timing.json') else {}
    T4 = json.load(open(f'{R}/tables/timing_cpus4.json')) if os.path.isfile(f'{R}/tables/timing_cpus4.json') else {}
    def meas(D, v, k='node_total'):
        e = D.get('e_' + v, {}).get(k)
        return f'{e[3]:.1f} [{e[1]:.1f}]' if e else '-'
    for v in rows:
        c = compute(v)
        d = det_of(v)
        L.append(f"| {v} | {c['key_frac']:.2f} | {d} ({GFLOPS[d]:.1f}) | {c['cpu']:.1f} | {meas(TM, v)} | {meas(T4, v)} | {meas(TM, v, 'ov_total')} | {c['gpu']:.2f} | {c['orin_cpu']:.0f} [{c['orin_cpu_lo']:.0f}-{c['orin_cpu_hi']:.0f}] | "
                 f"{c['orin_gpu']:.1f} | {c['orin_ov']:.1f} | {c['orin_total']:.0f} | {100 * (c['orin_total'] / cm['orin_total'] - 1):+.0f} % |")
    open(f'{R}/tables/edge_compute.md', 'w').write('\n'.join(L) + '\n')
    # context: ATE change of the P7 near-equivalent configurations vs sens_fix1 (regression after post-hoc selection)
    nb = {}
    fn = f'{R}/tables/ate_p7neighbors.json'
    if os.path.isfile(fn):
        d = json.load(open(fn))
        for grp, key in (('L2+L3', 'L23'), ('L0+L1', 'L01')):
            v = [r['gm'] for r in d['paired'] if r['ref'] == 'sens_fix1' and r['group'] == grp and r['method'] != 'yolo_naive']
            if v:
                nb[key] = [min(v), max(v)]
    json.dump({'main_orin_ms': cm['orin_total'], 'main': cm, 'neighbors': nb}, open(f'{R}/tables/edge_compute_main.json', 'w'), indent=1)
    print(open(f'{R}/tables/edge_closed_loop.md').read())
