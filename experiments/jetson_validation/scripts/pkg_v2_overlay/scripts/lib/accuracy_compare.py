#!/usr/bin/env python3
"""accuracy_compare.py <runs_root> <out_dir>: Jetson closed-loop accuracy vs the desktop reference (runs inside the image).

Inputs : <runs_root>/<seq>/<method>/eval/eval_summary.yaml (savior-eval multi), run dirs, <out_dir>/sync.json (pkg_sync.py),
         <out_dir>/../masks/agreement.json (optional), reference/desktop_ate.json, reference/tolerances.json,
         reference/desktop_runs/ (per-frame savior_stats for the closed-loop mask comparison).
Outputs: <out_dir>/compare.json, <out_dir>/compare.txt (human summary with PASS / WARN / FAIL)."""
import glob, gzip, hashlib, json, math, os, sys
import numpy as np
import yaml

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LABEL = {'openvins': 'OpenVINS', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR', 'savior_edge': 'SAVIOR-edge', 'savior_cpp': 'SAVIOR (C++)', 'savior_edge_cpp': 'SAVIOR-edge (C++)'}
RUNS = ['run_01', 'run_04', 'run_07']
ORDER = {'PASS': 0, 'WARN': 1, 'FAIL': 2}


def worst(vs):
    return max(vs, key=lambda v: ORDER[v]) if vs else 'FAIL'


def stats_by_stamp(f):
    out = {}
    if not os.path.isfile(f):
        return out
    op = gzip.open if f.endswith('.gz') else open
    for ln in op(f, 'rt'):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        st = d.get('stamp', {})
        key = st.get('sec', 0) * 10**9 + st.get('nanosec', 0)
        out[key] = (d.get('n_instances', 0), d.get('n_roots', 0), d.get('core_px', 0))
    return out


def closed_loop_masks(jrd, drd):
    J, D = stats_by_stamp(f'{jrd}/savior_stats.jsonl.gz'), stats_by_stamp(f'{drd}/savior_stats.jsonl.gz')
    common = sorted(set(J) & set(D))
    if not common:
        return None
    a = np.array([J[k] for k in common], float); b = np.array([D[k] for k in common], float)
    rel = np.abs(a[:, 2] - b[:, 2]) / np.maximum(b[:, 2], 1.0)
    return dict(frames=len(common), frames_device=len(J), frames_desktop=len(D),
                same_n_instances=round(float(np.mean(a[:, 0] == b[:, 0])), 4), same_n_roots=round(float(np.mean(a[:, 1] == b[:, 1])), 4),
                core_px_reldiff_median=round(float(np.median(rel)), 4), core_px_reldiff_p90=round(float(np.percentile(rel, 90)), 4),
                core_px_ratio_pooled=round(float(a[:, 2].sum() / max(b[:, 2].sum(), 1)), 4))


def main():
    root, outd = sys.argv[1], sys.argv[2]
    ref = json.load(open(f'{PKG}/reference/desktop_ate.json'))['runs']
    tol = json.load(open(f'{PKG}/reference/tolerances.json'))['ate']
    sync = json.load(open(f'{outd}/sync.json')) if os.path.isfile(f'{outd}/sync.json') else {'rows': [], 'summary': {}}
    srow = {(r['seq'], r['method'], r['run']): r for r in sync['rows']}
    FM, PR, WR, EF = tol['failure_m'], tol['pass_ratio'], tol['warn_ratio'], tol['envelope_factor']
    res, lines = {}, []
    for seq in ('hall_t1_L3', 'aisles_t1_L2'):
        # v2: the C++ node runs (savior_cpp / savior_edge_cpp) are compared with the desktop PYTHON reference of the same
        # pipeline (on the desktop the C++ node is md5-identical to it: results/cpp_port/tables/ate_closed_loop*.md)
        for m in ('openvins', 'yolo_naive', 'sens_fix1', 'savior_edge') + tuple(x for x in ('savior_cpp', 'savior_edge_cpp') if os.path.isdir(f'{root}/{seq}/{x}')):
            rm = {'savior_cpp': 'sens_fix1', 'savior_edge_cpp': 'savior_edge'}.get(m, m)
            d = ref[seq][rm]['trials']
            ev = f'{root}/{seq}/{m}/eval/eval_summary.yaml'
            jt = {}
            if os.path.isfile(ev):
                for t in yaml.safe_load(open(ev))['trials']:
                    jt[t['name']] = t['ate']['trans_m']['rmse'] if t.get('ate') else None
            rows, notes = [], []
            for run in RUNS:
                tf = f'{root}/{seq}/{m}/{run}/stamped_traj_estimate.txt'
                md5 = hashlib.md5(open(tf, 'rb').read()).hexdigest() if os.path.isfile(tf) else None
                s = srow.get((seq, m, run), {})
                row = dict(run=run, offset=d[run]['offset'], ate_device=jt.get(run), ate_desktop=d[run]['ate_m'], md5_device=md5,
                           md5_desktop=d[run]['md5'], md5_equal=md5 == d[run]['md5'], valid=s.get('valid'), poses=s.get('poses'),
                           poses_desktop=d[run]['n_poses'], rate=s.get('rate'))
                if m != 'openvins':
                    row['closed_loop_masks'] = closed_loop_masks(f'{root}/{seq}/{m}/{run}', f'{PKG}/reference/desktop_runs/{seq}/{rm}/{run}')
                rows.append(row)
            d10 = [t['ate_m'] for t in d.values() if t['ate_m'] is not None]
            d10_fail = sum(a > FM for a in d10)
            verdicts = []
            if any(r['ate_device'] is None for r in rows):
                verdicts.append('FAIL'); notes.append('missing Jetson ATE (run or eval failed)')
            else:
                mism = [r['run'] for r in rows if (r['ate_device'] > FM) != (r['ate_desktop'] > FM)]
                if mism:
                    v = 'WARN' if d10_fail else 'FAIL'
                    verdicts.append(v); notes.append(f'failure class (> {FM} m) differs at {mism} (desktop fails {d10_fail}/10 offsets) -> {v}')
                ok = [r for r in rows if r['ate_device'] <= FM and r['ate_desktop'] <= FM]
                if ok:
                    lr = [math.log(r['ate_device'] / r['ate_desktop']) for r in ok]
                    gm = math.exp(sum(lr) / len(lr))
                    env = max(a for a in d10 if a <= FM) if any(a <= FM for a in d10) else None
                    jmax = max(r['ate_device'] for r in ok)
                    if 1 / PR <= gm <= PR and (env is None or jmax <= EF * env):
                        v = 'PASS'
                    elif 1 / WR <= gm <= WR:
                        v = 'WARN'
                    else:
                        v = 'FAIL'
                    verdicts.append(v)
                    notes.append(f'gm ratio device/desktop {gm:.3f} over {len(ok)} offsets; max device {jmax:.3f} m vs desktop '
                                 f'10-offset envelope {env if env is None else round(env, 3)} m -> {v}')
                elif not mism:
                    verdicts.append('PASS'); notes.append(f'diverges (> {FM} m) at every offset on both device and desktop -> PASS')
            if any(r['valid'] == 0 for r in rows):
                verdicts.append('FAIL'); notes.append('invalid run(s) (sync / pose count)')
            v = worst(verdicts)
            gmj = [r['ate_device'] for r in rows if r['ate_device']]
            res.setdefault(seq, {})[m] = dict(label=LABEL.get(m, m), verdict=v, notes=notes, runs=rows,
                                              gm_ate_device=float(np.exp(np.mean(np.log(np.minimum(gmj, 10.0))))) if gmj else None,
                                              gm_ate_desktop_same3=float(np.exp(np.mean(np.log(np.minimum([r['ate_desktop'] for r in rows], 10.0))))),
                                              gm_ate_desktop_10=float(np.exp(np.mean(np.log(np.minimum(d10, 10.0))))),
                                              desktop_fail_10=d10_fail, md5_equal=sum(r['md5_equal'] for r in rows))
    # scientific consistency (informational): SAVIOR vs Y-Cls / OpenVINS and SAVIOR-edge vs SAVIOR, geometric means capped at 10 m
    sci = {}
    for seq, R in res.items():
        def g(m, k):
            return R[m][k]
        sci[seq] = {}
        for a_, b_ in (('sens_fix1', 'yolo_naive'), ('sens_fix1', 'openvins'), ('savior_edge', 'sens_fix1')):
            if g(a_, 'gm_ate_device') and g(b_, 'gm_ate_device'):
                sci[seq][f'{a_}/{b_}'] = dict(device=round(g(a_, 'gm_ate_device') / g(b_, 'gm_ate_device'), 3),
                                              desktop_same3=round(g(a_, 'gm_ate_desktop_same3') / g(b_, 'gm_ate_desktop_same3'), 3))
                sci[seq][f'{a_}/{b_}']['same_direction'] = (sci[seq][f'{a_}/{b_}']['device'] < 1) == (sci[seq][f'{a_}/{b_}']['desktop_same3'] < 1)
    masks = None
    mf = os.path.join(os.path.dirname(outd), 'masks', 'agreement.json')
    if os.path.isfile(mf):
        masks = json.load(open(mf))
    acc_v = worst([x['verdict'] for R in res.values() for x in R.values()])
    mask_v = worst([x['verdict'] for x in masks['results'] if not x.get('informational')]) if masks and masks.get('results') else 'n/a'
    overall = worst([acc_v] + ([mask_v] if mask_v != 'n/a' else []))
    out = dict(overall=overall, accuracy_verdict=acc_v, mask_verdict=mask_v, sync_summary=sync.get('summary'), per_seq=res,
               scientific_checks=sci, tolerances=tol, md5_note='trajectory md5 equality is NOT expected across architectures / TensorRT builds')
    json.dump(out, open(f'{outd}/compare.json', 'w'), indent=1)
    lines.append(f'SAVIOR Jetson accuracy vs desktop  (overall {overall}: accuracy {acc_v}, offline masks {mask_v})')
    lines.append(f"sync: {sync.get('summary')}")
    lines.append(f"{'seq':13s} {'method':12s} {'verdict':7s} {'ATE device (m) 0.0/0.6/1.2':30s} {'ATE desktop':24s} md5=  notes")
    for seq, R in res.items():
        for m, x in R.items():
            dv = '/'.join('-' if r['ate_device'] is None else f"{r['ate_device']:.3f}" for r in x['runs'])
            dd = '/'.join(f"{r['ate_desktop']:.3f}" for r in x['runs'])
            lines.append(f"{seq:13s} {x['label']:12s} {x['verdict']:7s} {dv:30s} {dd:24s} {x['md5_equal']}/3  {' | '.join(x['notes'])}")
    lines.append('scientific checks (geometric-mean ATE ratios, informational): ' + json.dumps(sci))
    if masks:
        for r in masks.get('results', []):
            lines.append(f"masks {r['label']:28s} {r['verdict']}{' (info)' if r.get('informational') else ''}  worst class IoU {r['worst_class_iou']}"
                         f"  inst recall {r['instances']['recall']} precision {r['instances']['precision']}  frames {r['frames']}")
    open(f'{outd}/compare.txt', 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
