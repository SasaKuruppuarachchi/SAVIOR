#!/usr/bin/env python3
"""m3b_analyze.py : M3b controlled SOTA benchmark analysis (VINS-Fusion, DynaVINS, ORB-SLAM3; loop closure off).

Run in the savior image after src/savior/sota/scripts/eval_sota.sh (eval_posyaw / eval_se3 / eval_sim3 per method dir).
Inputs : results/sota/<dataset>_<seq>/<method>/run_XX/{run_info.yaml,stamped_traj_estimate.txt,estimator.log,timing.csv}
         + eval_<align>/eval_summary.yaml ; OpenVINS reference = results/m2b_heldout/runs/<seq>/openvins/eval (M2b), for
         VIODE falling back to results/p5_viode/<seq>/openvins/eval (same offsets, P5).
Outputs: results/sota/tables/
   sota_viode.{md,csv,json}, sota_warehouse_t2.{md,csv,json}  (median table, failures, pooled stats vs OpenVINS)
   validity_<ds>.csv                                          (per run: status, poses, coverage, gaps, resets, tracking)
   merge_<ds>.{csv,json}                                      (long format, columns = M2b held-out conventions)
Statistics = M2b analysis_plan: paired per-offset log ATE ratio vs OpenVINS (failures capped at 10 m), geometric-mean
ratio - 1, bootstrap 95 % CI (20000, seed 0), Wilcoxon signed-rank, Holm over the 3 SOTA methods per (dataset, group).
Failure: ATE > 1 m (VIODE, P5) / > 2 m (warehouse, P6), or no / unevaluable estimate."""
import csv, glob, json, math, os, re, sys
import numpy as np, yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results/sota'
T = R + '/tables'
M2B = WS + '/results/m2b_heldout/runs'
P5 = WS + '/results/p5_viode'
METHODS = ['vins_fusion', 'dynavins', 'orbslam3']
LAB = {'openvins': 'OpenVINS', 'vins_fusion': 'VINS-Fusion', 'dynavins': 'DynaVINS', 'orbslam3': 'ORB-SLAM3'}
CAP = 10.0
IDX = list(range(1, 11))
DS = {
    'viode': dict(seqs=[f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')],
                  fail=1.0, gt=WS + '/data/viode/gt/{}.txt', bag=WS + '/data/viode/ros2/{}/metadata.yaml',
                  offs=WS + '/src/savior/sota/scripts/viode_offsets.txt', table='sota_viode',
                  lev=lambda s: s.rsplit('_', 1)[1],
                  groups=['none', 'low', 'mid', 'high', 'none+low', 'mid+high', 'low+mid+high', 'all']),
    'warehouse': dict(seqs=[f'{s}_t2_L{l}' for s in ('aisles', 'hall', 'dock') for l in range(4)],
                      fail=2.0, gt=WS + '/data/warehouse/gt/{}.txt', bag=WS + '/data/warehouse/ros2_stereoseg/{}/metadata.yaml',
                      offs=WS + '/src/savior/sota/scripts/warehouse_offsets.txt', table='sota_warehouse_t2',
                      lev=lambda s: s.rsplit('_', 1)[1],
                      groups=['L0', 'L1', 'L2', 'L3', 'L0+L1', 'L2+L3', 'hall_L3', 'dock_L3', 'hall+dock_L3', 'all']),
}


def in_group(ds, g, s):
    lev = DS[ds]['lev'](s)
    if g == 'all':
        return True
    if g.endswith('_L3'):
        return lev == 'L3' and s.split('_')[0] in g[:-3].split('+')
    return lev in g.split('+')


def eval_trials(d):
    """{run_idx: dict(ate, rpe, rot, status)} from eval_summary.yaml (posyaw / se3 / sim3)."""
    out = {}
    if not os.path.isfile(d):
        return out
    for t in yaml.safe_load(open(d)).get('trials', []):
        i = int(t['name'].split('_')[1])
        if t.get('status') != 'ok':
            out[i] = dict(ate=math.inf, rpe=math.inf, rot=math.inf, rpe_rot=math.inf, status=t.get('status')); continue
        ks = sorted(t['rpe'], key=float)
        out[i] = dict(ate=t['ate']['trans_m']['rmse'], rot=t['ate']['rot_deg']['rmse'], rpe=t['rpe'][ks[0]]['trans_m']['mean'],
                      rpe_rot=t['rpe'][ks[0]]['rot_deg']['mean'], rpe_len=float(ks[0]), status='ok')
    return out


def bag_start(ds, s):
    y = yaml.safe_load(open(DS[ds]['bag'].format(s)))
    return y['rosbag2_bagfile_information']['starting_time']['nanoseconds_since_epoch'] * 1e-9


def offsets(ds):
    o = {}
    for l in open(DS[ds]['offs']):
        if l.strip() and not l.startswith('#'):
            a, b = l.split()
            o[a] = [float(x) for x in b.split(',')]
    return o


def run_validity(ds, s, m, i, gt_t, t0bag, off):
    rd = f'{R}/{ds}_{s}/{m}/run_{i:02d}'
    v = dict(dataset=ds, seq=s, method=m, run=i, offset=off)
    if not os.path.isdir(rd):
        v['status'] = 'missing'; return v
    info = yaml.safe_load(open(rd + '/run_info.yaml')) if os.path.isfile(rd + '/run_info.yaml') else {}
    v['status'] = info.get('status', 'no_run_info')
    v['wall_time_s'] = info.get('wall_time_s')
    try:
        e = np.loadtxt(rd + '/stamped_traj_estimate.txt', comments='#', ndmin=2)
    except Exception:  # noqa
        e = np.zeros((0, 8))
    n = len(e)
    tstart = t0bag + off
    span = gt_t[-1] - tstart
    v['n_poses'] = n
    if n:
        t = np.sort(e[:, 0])
        v['first_pose_after_start_s'] = round(t[0] - tstart, 3)          # initialization latency (sensor time)
        v['last_pose_before_end_s'] = round(gt_t[-1] - t[-1], 3)
        v['coverage'] = round((t[-1] - t[0]) / span, 4)                     # time coverage of the GT span after the offset
        v['max_gap_s'] = round(float(np.max(np.diff(t))) if n > 1 else 0.0, 3)
        rate = 10.0 if m in ('vins_fusion', 'dynavins') else 20.0          # VINS: every 2nd stereo frame (multiple_thread)
        v['pose_fraction'] = round(n / (span * rate), 4)
    else:
        v.update(first_pose_after_start_s=None, last_pose_before_end_s=None, coverage=0.0, max_gap_s=None, pose_fraction=0.0)
    log = open(rd + '/estimator.log', errors='replace').read() if os.path.isfile(rd + '/estimator.log') else ''
    if m in ('vins_fusion', 'dynavins'):
        v['resets'] = log.count('system reboot!')
        v['failure_detections'] = log.count('failure detection!')
        v['lost_frames'] = None
        v['maps'] = None
    else:
        maps = re.findall(r'There are (\d+) maps in the atlas', log)
        v['maps'] = int(maps[-1]) if maps else 0
        v['resets'] = log.count('Reseting active map') + log.count('Reset map because') + log.count('RESETING FRAME')
        v['failure_detections'] = log.count('Fail to track local map!')
        st = {}
        if os.path.isfile(rd + '/timing.csv'):
            for z in csv.DictReader(open(rd + '/timing.csv')):
                st[z['state']] = st.get(z['state'], 0) + 1
        v['frames_total'] = sum(st.values())
        v['frames_not_init'] = st.get('1', 0)
        v['lost_frames'] = st.get('3', 0) + st.get('4', 0)                  # RECENTLY_LOST + LOST
    complete = v['status'] == 'ok' and n > 0 and v['last_pose_before_end_s'] is not None and v['last_pose_before_end_s'] < 2.0
    v['complete'] = bool(complete)
    return v


def lr(a, b):
    return math.log(min(a, CAP) / min(b, CAP))


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (n, x.size)).mean(axis=1), [2.5, 97.5])


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


def fmt(v):
    return 'fail' if not math.isfinite(v) else (f'{v:.3g}' if v >= 10 else f'{v:.3f}')


def openvins_ref(ds, s):
    # VIODE: P5 OpenVINS (complete; M2b re-runs reproduce it to ~1e-6 m); warehouse t2: M2b held-out OpenVINS
    srcs = [(f'{P5}/{s}/openvins/eval/eval_summary.yaml', 'p5')] if ds == 'viode' else [(f'{M2B}/{s}/openvins/eval/eval_summary.yaml', 'm2b')]
    for base, src in srcs:
        e = eval_trials(base)
        if e:
            return e, src
    return {}, None


def analyse(ds):
    C = DS[ds]
    FAIL = C['fail']
    offs = offsets(ds)
    seqs = [s for s in C['seqs'] if os.path.isdir(f'{R}/{ds}_{s}')]
    E, V, OV, OVSRC = {}, [], {}, {}
    for s in seqs:
        gt = np.loadtxt(C['gt'].format(s), comments='#', usecols=0)
        t0 = bag_start(ds, s)
        OV[s], OVSRC[s] = openvins_ref(ds, s)
        for m in METHODS:
            E[(s, m)] = {a: eval_trials(f'{R}/{ds}_{s}/{m}/eval_{a}/eval_summary.yaml') for a in ('posyaw', 'se3', 'sim3')}
            for i in IDX:
                V.append(run_validity(ds, s, m, i, gt, t0, offs[s][i - 1]))
    vd = {(v['seq'], v['method'], v['run']): v for v in V}

    def ate(s, m, i, a='posyaw'):
        v = vd[(s, m, i)]
        if v['status'] == 'missing':
            return None
        x = E[(s, m)][a].get(i)
        return math.inf if x is None else x['ate']

    def rpe(s, m, i):
        x = E[(s, m)]['posyaw'].get(i)
        if x is None or not x['ate'] <= FAIL:
            return math.inf
        return x['rpe']

    # ---- long-format merge table
    rows = []
    for s in seqs:
        for m in METHODS:
            for i in IDX:
                v = vd[(s, m, i)]
                a = ate(s, m, i)
                if a is None:
                    continue
                x = E[(s, m)]['posyaw'].get(i, {})
                rows.append(dict(dataset=ds if ds == 'viode' else 'warehouse_t2', seq=s, level=C['lev'](s), method=m, label=LAB[m],
                                 run=i, offset_s=v['offset'], ate_posyaw_m=a, ate_se3_m=ate(s, m, i, 'se3'), ate_sim3_m=ate(s, m, i, 'sim3'),
                                 rot_posyaw_deg=x.get('rot', math.inf), rpe_m=rpe(s, m, i), rpe_len_m=x.get('rpe_len'),
                                 fail=bool(not a <= FAIL), fail_threshold_m=FAIL, status=v['status'], n_poses=v['n_poses'],
                                 coverage=v['coverage'], resets=v['resets'], complete=v['complete']))
    os.makedirs(T, exist_ok=True)
    tag = 'viode' if ds == 'viode' else 'warehouse_t2'
    keys = list(rows[0].keys()) if rows else []
    with open(f'{T}/merge_{tag}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    vals = {s: {m: {i: ate(s, m, i) for i in IDX if ate(s, m, i) is not None} for m in METHODS} for s in seqs}
    json.dump({'dataset': tag, 'metric': 'ate_posyaw_rmse_m', 'fail_m': FAIL, 'cap_m': CAP, 'labels': LAB,
               'note': 'same shape as results/m2b_heldout/tables/ate_<ds>.json "values" ({seq: {method: {run: ate}}}); inf = failed / no estimate',
               'values': vals,
               'rpe': {s: {m: {i: rpe(s, m, i) for i in IDX if ate(s, m, i) is not None} for m in METHODS} for s in seqs}},
              open(f'{T}/merge_{tag}.json', 'w'), indent=1, default=str)
    vkeys = sorted({k for v in V for k in v}, key=lambda k: list(V[0].keys()).index(k) if k in V[0] else 99)
    with open(f'{T}/validity_{tag}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, vkeys); w.writeheader(); w.writerows(V)

    # ---- pooled paired stats vs OpenVINS
    res, res_rpe = [], []
    for metric, res in (('ate', res), ('rpe', res_rpe)):
     for g in C['groups']:
         fam = []
         for m in METHODS:
             x = []
             for s in seqs:
                 if not in_group(ds, g, s):
                     continue
                 for i in IDX:
                     if metric == 'ate':
                         a = ate(s, m, i); b = OV[s].get(i, {}).get('ate')
                     else:  # RPE (shortest rpg sub-length), failed runs = inf -> capped at 10 m, as M2b
                         a = rpe(s, m, i) if ate(s, m, i) is not None else None
                         o = OV[s].get(i)
                         b = None if o is None else (o['rpe'] if o['ate'] <= FAIL else math.inf)
                     if a is not None and b is not None:
                         x.append(lr(a, b))
             x = np.array(x)
             if x.size < 5:
                 continue
             nz = x[np.abs(x) > 1e-12]
             p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
             ci = boot(x)
             fam.append(dict(metric=metric, group=g, method=m, n=int(x.size), gm=100 * (math.exp(x.mean()) - 1), ci=[100 * (math.exp(c) - 1) for c in ci],
                             wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), p=p))
         for r, h in zip(fam, holm([r['p'] for r in fam]) if fam else []):
             r['holm'] = float(h)
         res += fam

    # ---- markdown
    L = [f'# M3b SOTA benchmark: {"VIODE (12 sequences)" if ds == "viode" else "SAVIOR-Warehouse t2 held-out (12 sequences)"}\n',
         f'VINS-Fusion, DynaVINS, ORB-SLAM3 (stereo-inertial, loop closure off), image savior-sota:noetic; 10 late-start offsets per '
         f'sequence = the {"P5" if ds == "viode" else "P6 / M2b"} offsets of our methods (protocol (a), no bag-start column); rate 0.5. '
         f'ATE RMSE [m], posyaw alignment, full sequence (savior-eval multi). Failure = ATE > {FAIL:g} m or no estimate; [n] = failures. '
         f'OpenVINS = {"P5 runs (results/p5_viode/<seq>/openvins; the M2b re-runs reproduce them to ~1e-6 m)" if ds == "viode" else "M2b held-out runs (results/m2b_heldout/runs/<seq>/openvins)"} at the same offsets'
         f'{"" if all(OVSRC.values()) else "; missing for: " + ", ".join(k for k, v in OVSRC.items() if not v)}.\n',
         '## Median ATE [m] over 10 offsets ([n] = failures)\n',
         '| seq | OpenVINS | VINS-Fusion | DynaVINS | ORB-SLAM3 |', '|---|--:|--:|--:|--:|']
    med = {}
    for s in seqs:
        cells = []
        for m in ['openvins'] + METHODS:
            if m == 'openvins':
                v = [OV[s][i]['ate'] for i in IDX if i in OV[s]]
            else:
                v = [ate(s, m, i) for i in IDX if ate(s, m, i) is not None]
            if not v:
                cells.append('-'); continue
            k = sum(not x <= FAIL for x in v)
            md = float(np.median(np.minimum(v, 1e9)))
            med[(s, m)] = (md, k, len(v))
            cells.append(('fail' if md >= 1e9 else fmt(md)) + (f' [{k}]' if k else '') + ('' if len(v) == 10 else f' (n={len(v)})'))
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    L += ['\n## Failures and success rate per group\n', '| group | ' + ' | '.join(LAB[m] for m in ['openvins'] + METHODS) + ' |',
          '|---|' + '--:|' * 4]
    succ = {}
    for g in C['groups']:
        cells = []
        for m in ['openvins'] + METHODS:
            v = [(OV[s][i]['ate'] if m == 'openvins' else ate(s, m, i)) for s in seqs if in_group(ds, g, s) for i in IDX
                 if (i in OV[s] if m == 'openvins' else ate(s, m, i) is not None)]
            if not v:
                cells.append('-'); continue
            k = sum(not x <= FAIL for x in v)
            succ[(g, m)] = (len(v) - k, len(v))
            cells.append(f'{k}/{len(v)} fail ({100 * (len(v) - k) / len(v):.0f} % ok)')
        L.append(f'| {g} | ' + ' | '.join(cells) + ' |')
    L += ['\n## Pooled paired comparison vs OpenVINS (geometric-mean ATE ratio - 1; negative = better than OpenVINS; failures capped at 10 m; '
          'bootstrap 95 % CI; Wilcoxon p; Holm over the 3 methods per group; wins/losses)\n',
          '| method | ' + ' | '.join(C['groups']) + ' |', '|---|' + '---|' * len(C['groups'])]
    for m in METHODS:
        cells = []
        for g in C['groups']:
            r = next((x for x in res if x['group'] == g and x['method'] == m), None)
            cells.append('-' if r is None else f"{r['gm']:+.0f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] H={r['holm']:.2g} {r['wins']}/{r['losses']}")
        L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
    L += ['\n## Pooled paired comparison vs OpenVINS, RPE (shortest rpg sub-length = 10 % of the GT path; failed runs = inf, capped at 10 m)\n',
          '| method | ' + ' | '.join(C['groups']) + ' |', '|---|' + '---|' * len(C['groups'])]
    for m in METHODS:
        cells = []
        for g in C['groups']:
            r = next((x for x in res_rpe if x['group'] == g and x['method'] == m), None)
            cells.append('-' if r is None else f"{r['gm']:+.0f} % [{r['ci'][0]:+.0f}, {r['ci'][1]:+.0f}] H={r['holm']:.2g} {r['wins']}/{r['losses']}")
        L.append(f'| {LAB[m]} | ' + ' | '.join(cells) + ' |')
    # converged-only medians, se3 / sim3, RPE
    L += ['\n## Secondary metrics (all 10 offsets per sequence pooled per method)\n',
          '| method | median ATE posyaw | median ATE se3 | median ATE sim3 | median RPE (converged) [m] | converged-only median ATE |', '|---|--:|--:|--:|--:|--:|']
    for m in METHODS:
        a = [ate(s, m, i) for s in seqs for i in IDX if ate(s, m, i) is not None]
        b = [ate(s, m, i, 'se3') for s in seqs for i in IDX if ate(s, m, i) is not None]
        c = [ate(s, m, i, 'sim3') for s in seqs for i in IDX if ate(s, m, i) is not None]
        rp = [rpe(s, m, i) for s in seqs for i in IDX if ate(s, m, i) is not None]
        rp = [x for x in rp if math.isfinite(x)]
        conv = [x for x in a if x <= FAIL]
        f = lambda z: (lambda q: 'fail' if q >= 1e9 else fmt(q))(float(np.median(np.minimum(z, 1e9)))) if z else '-'  # noqa: E731
        L.append(f'| {LAB[m]} | {f(a)} | {f(b)} | {f(c)} | {f(rp)} | {f(conv)} |')
    # validity
    L += ['\n## Run validity\n', '| method | runs | status ok | complete (pose within 2 s of bag end) | no poses | median coverage | '
          'median init latency [s] | median end gap [s] | runs with resets | runs with lost frames (ORB) | runs with > 1 map (ORB) |', '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    for m in METHODS:
        vv = [v for v in V if v['method'] == m and v['status'] != 'missing']
        lat = [v['first_pose_after_start_s'] for v in vv if v.get('first_pose_after_start_s') is not None]
        L.append(f"| {LAB[m]} | {len(vv)} | {sum(v['status'] == 'ok' for v in vv)} | {sum(v['complete'] for v in vv)} | "
                 f"{sum(v['n_poses'] == 0 for v in vv)} | {np.median([v['coverage'] for v in vv]) if vv else 0:.3f} | "
                 f"{(np.median(lat) if lat else float('nan')):.2f} | "
                 f"{np.median([v['last_pose_before_end_s'] for v in vv if v.get('last_pose_before_end_s') is not None] or [float('nan')]):.2f} | {sum((v['resets'] or 0) > 0 for v in vv)} | "
                 f"{'-' if m != 'orbslam3' else sum((v['lost_frames'] or 0) > 0 for v in vv)} | "
                 f"{'-' if m != 'orbslam3' else sum((v['maps'] or 0) > 1 for v in vv)} |")
    miss = [v for v in V if v['status'] == 'missing']
    if miss:
        L.append(f'\n**MISSING runs: {len(miss)}**')
    open(f'{T}/{C["table"]}.md', 'w').write('\n'.join(L) + '\n')
    with open(f'{T}/{C["table"]}.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['seq', 'method', 'label', 'n_runs', 'median_ate_posyaw_m', 'failures', 'fail_threshold_m'])
        for (s, m), (md, k, n) in med.items():
            w.writerow([s, m, LAB[m], n, md if md < 1e9 else 'inf', k, FAIL])
    json.dump({'dataset': tag, 'fail_m': FAIL, 'openvins_source': OVSRC, 'medians': {f'{s}|{m}': dict(median=md, failures=k, n=n) for (s, m), (md, k, n) in med.items()},
               'success': {f'{g}|{m}': dict(ok=a, n=b) for (g, m), (a, b) in succ.items()}, 'paired_vs_openvins': res, 'paired_vs_openvins_rpe': res_rpe},
              open(f'{T}/{C["table"]}.json', 'w'), indent=1, default=str)
    print('\n'.join(L))


if __name__ == '__main__':
    for ds in (sys.argv[1:] or ['viode', 'warehouse']):
        if any(os.path.isdir(f'{R}/{ds}_{s}') for s in DS[ds]['seqs']):
            analyse(ds)
