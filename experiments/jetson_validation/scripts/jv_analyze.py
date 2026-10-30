#!/usr/bin/env python3
"""jv_analyze.py - on-device validation of SAVIOR on the Jetson Orin NX 8 GB: tables + figures for results/jetson_validation.

Inputs (pulled from the Jetson package ~/savior_jetson/savior_jetson_pkg_v1/out -> raw/device_out):
  engines/engines.json, masks/agreement.json                 on-device engine export + YOLO-level mask agreement (package v1)
  pipe_masks/device_{main,edge}_<seq>.npz                    full-pipeline masks, device engines (lib/pipe_dump.py)
  ../server_pipe_masks/server_{main,edge}_<seq>.npz          the same with the desktop engines (made on the server)
  accuracy*/compare.json + run dirs                          closed loop vs desktop (rate 0.5, frozen configs)
  timing_*/<seq>/<method>/run_XX                             rate 1.0 timing sessions (savior_stats, ov_timing, lat.csv.gz, mem.csv,
                                                             launch.log.gz, run_info.yaml), tegrastats.log, markers.txt, power_*.json
Outputs: tables/*.md + *.json, figures/*.pdf|png (paper.mplstyle).  Runs in the desktop image (numpy, matplotlib, yaml)."""
import csv, glob, gzip, hashlib, json, math, os, re, sys
from collections import defaultdict
import numpy as np
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.dirname(os.path.dirname(ROOT))
DEV = f'{ROOT}/raw/device_out'
SRVM = f'{ROOT}/raw/server_pipe_masks'
TAB, FIG = f'{ROOT}/tables', f'{ROOT}/figures'
STYLE = f'{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle'
SEQS = ['hall_t1_L3', 'aisles_t1_L2']
LABEL = {'openvins': 'OpenVINS', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR (Py)', 'savior_cpp': 'SAVIOR (C++)',
         'savior_edge': 'SAVIOR-edge (Py)', 'savior_edge_cpp': 'SAVIOR-edge (C++)'}
COLOR = {'openvins': 'blue', 'yolo_naive': 'black', 'sens_fix1': 'red', 'savior_cpp': 'red', 'savior_edge': 'green',
         'savior_edge_cpp': 'green'}
LS = {'sens_fix1': '--', 'savior_edge': '--', 'savior_cpp': '-', 'savior_edge_cpp': '-', 'openvins': '-', 'yolo_naive': ':'}
ORDER = ['openvins', 'yolo_naive', 'sens_fix1', 'savior_cpp', 'savior_edge', 'savior_edge_cpp']
os.makedirs(TAB, exist_ok=True); os.makedirs(FIG, exist_ok=True)


def q(v, ps=(50, 90, 99)):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    return [float(np.percentile(v, p)) for p in ps] + [float(v.mean()), float(v.max()), int(len(v))]


def fq(x, nd=1):
    return '-' if x is None else ' / '.join(f'{y:.{nd}f}' for y in x[:3])


def wmd(path, lines):
    open(path, 'w').write('\n'.join(lines) + '\n')
    print(f'wrote {path}')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


# ------------------------------------------------------------------------------------------------ pipeline masks
def unpack(a, n):
    return np.unpackbits(a, axis=1)[:, :n].astype(bool)


def pipe_masks():
    rows, curves = [], {}
    for cmp_, v, seq in [(c, v, q_) for c in ('device', 'serverpt') for v in ('main', 'edge') for q_ in SEQS]:
            fd = f'{DEV}/pipe_masks/device_{v}_{seq}.npz' if cmp_ == 'device' else f'{SRVM}/serverpt_{v}_{seq}.npz'
            fs = f'{SRVM}/server_{v}_{seq}.npz'
            if not (os.path.isfile(fd) and os.path.isfile(fs)):
                continue
            D, S = np.load(fd), np.load(fs)
            md, ms = json.loads(str(D['meta'])), json.loads(str(S['meta']))
            n = md['image_hw'][0] * md['image_hw'][1]
            common, idd, iss = np.intersect1d(D['stamps_ns'], S['stamps_ns'], return_indices=True)
            r = dict(compare=cmp_, variant=v, seq=seq, frames=int(len(common)), frames_device=int(len(D['stamps_ns'])), frames_server=int(len(S['stamps_ns'])),
                     engine_md5_device=md['engine_md5'], engine_md5_server=ms['engine_md5'], trt_device=md['tensorrt'], trt_server=ms['tensorrt'])
            for key in ('left_core', 'left_band', 'right_core'):
                A = unpack(D[key][idd], n); B = unpack(S[key][iss], n)
                inter = (A & B).sum(1).astype(float); uni = (A | B).sum(1).astype(float)
                both_empty = uni == 0
                iou = np.where(both_empty, np.nan, inter / np.maximum(uni, 1))
                ident = (A == B).all(1)
                x = iou[~both_empty]
                r[key] = dict(identical_frames=float(ident.mean()), nonempty_frames=int((~both_empty).sum()),
                              pooled_iou=float(inter.sum() / max(uni.sum(), 1)), px_agreement=float(1 - (A ^ B).sum() / (A.size)),
                              iou_median=float(np.median(x)) if len(x) else None, iou_p10=float(np.percentile(x, 10)) if len(x) else None,
                              iou_p1=float(np.percentile(x, 1)) if len(x) else None, iou_min=float(x.min()) if len(x) else None,
                              share_ge_099=float((x >= 0.99).mean()) if len(x) else None, share_ge_095=float((x >= 0.95).mean()) if len(x) else None,
                              core_px_ratio=float(A.sum() / max(B.sum(), 1)))
                if key == 'left_core':
                    curves[(cmp_, v, seq)] = x
            r['same_n_instances'] = float((D['n_inst'][idd] == S['n_inst'][iss]).mean())
            r['ms_median_device'] = float(np.median(D['ms'])); r['ms_median_server'] = float(np.median(S['ms']))
            rows.append(r)
    if not rows:
        return None
    json.dump(rows, open(f'{TAB}/pipe_mask_agreement.json', 'w'), indent=1)
    L = ['# Full-pipeline dynamic masks: Jetson (device FP16 engines, TensorRT 10.3) vs server (desktop FP16 engines, TensorRT 10.16)', '',
         'Offline Python SaviorPipeline on EVERY stereo frame (lib/pipe_dump.py), same bag + frozen sens_fix1 savior_node keys, only the',
         'engine/platform differs. Per-frame IoU over frames where at least one side has mask pixels; core = 255 (dynamic), band = 192.', '',
         'Rows "device vs server": Jetson FP16 engine (TensorRT 10.3) vs server FP16 engine (TensorRT 10.16). Rows "FP32 .pt vs server" = the',
         'numerics-only baseline on ONE machine: the same weights run in FP32 PyTorch vs the server FP16 engine (how much a pure',
         'arithmetic difference moves the stateful pipeline).', '',
         '| comparison | pipeline | seq | frames | identical frames (left core) | pooled IoU left core | per-frame IoU median / p10 / p1 / min | frames IoU >= 0.99 / >= 0.95 | pooled IoU right core | pooled IoU band | same #instances | core px device/server |',
         '|---|---|---|--:|--:|--:|---|---|--:|--:|--:|--:|']
    for r in rows:
        c = r['left_core']
        L.append(f"| {'device vs server' if r['compare'] == 'device' else 'FP32 .pt vs server (baseline)'} | {'SAVIOR' if r['variant'] == 'main' else 'SAVIOR-edge'} | {r['seq']} | {r['frames']} | {100 * c['identical_frames']:.1f} % | {c['pooled_iou']:.4f} | "
                 f"{c['iou_median']:.4f} / {c['iou_p10']:.4f} / {c['iou_p1']:.4f} / {c['iou_min']:.3f} | {100 * c['share_ge_099']:.1f} % / {100 * c['share_ge_095']:.1f} % | "
                 f"{r['right_core']['pooled_iou']:.4f} | {('%.4f' % r['left_band']['pooled_iou']) if r['left_band']['nonempty_frames'] else '- (band off)'} | "
                 f"{100 * r['same_n_instances']:.1f} % | {c['core_px_ratio']:.4f} |")
    wmd(f'{TAB}/pipe_mask_agreement.md', L)
    return rows, curves


# ------------------------------------------------------------------------------------------------ timing runs
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)'
                 r'(?: \| hold avg=([\d.]+)ms max=([\d.]+)ms)?')
EDGE = re.compile(r'\[SAVIOR-EDGE\] FINAL: .*?too_late=(\d+)')
TG = dict(ram=re.compile(r'RAM (\d+)/(\d+)MB'), swap=re.compile(r'SWAP (\d+)/(\d+)MB'), cpu=re.compile(r'CPU \[([^\]]*)\]'),
          gr3d=re.compile(r'GR3D_FREQ (\d+)%'), temp=re.compile(r'(\w+)@(-?[\d.]+)C'),
          rail=re.compile(r'(VDD_\w+) (\d+)mW/(\d+)mW'))


def read_tegra(f):
    rows = []
    if not os.path.isfile(f):
        return rows
    for ln in open(f, errors='replace'):
        p = ln.split(' ', 1)
        try:
            t = float(p[0].replace(',', '.'))
        except (ValueError, IndexError):
            continue
        s = p[1] if len(p) > 1 else ''
        r = dict(t=t)
        if (m := TG['ram'].search(s)):
            r['ram'] = int(m[1]); r['ram_total'] = int(m[2])
        if (m := TG['swap'].search(s)):
            r['swap'] = int(m[1])
        if (m := TG['cpu'].search(s)):
            loads = [int(x.split('%')[0]) for x in m[1].split(',') if '%' in x]
            r['cpu'] = float(np.mean(loads)) if loads else None
        if (m := TG['gr3d'].search(s)):
            r['gr3d'] = int(m[1])
        for k, v, _ in TG['rail'].findall(s):
            r[k] = int(v)
        temps = {k: float(v) for k, v in TG['temp'].findall(s)}
        r['tmax'] = max(temps.values()) if temps else None
        rows.append(r)
    return rows


def twin(rows, t0, t1):
    w = [r for r in rows if t0 <= r['t'] <= t1]
    if not w:
        return None
    o = dict(samples=len(w))
    for k in ('ram', 'swap', 'cpu', 'gr3d', 'VDD_IN', 'VDD_CPU_GPU_CV', 'VDD_SOC', 'tmax'):
        v = [r[k] for r in w if r.get(k) is not None]
        if v:
            o[k] = dict(mean=float(np.mean(v)), p95=float(np.percentile(v, 95)), max=float(np.max(v)), min=float(np.min(v)))
    return o


def lat_parse(f):
    """mask latency (recv mask - recv image, same stamp), e2e (recv pose - recv image of the nearest image stamp), counts, end backlog."""
    if not os.path.isfile(f):
        return None
    a = np.loadtxt(f, delimiter=',', skiprows=1, dtype=np.int64, ndmin=2)
    if not len(a):
        return None
    img = {s: r for t, s, r in a if t == 0}
    msk = {s: r for t, s, r in a if t == 1}
    pos = [(s, r) for t, s, r in a if t == 2]
    ml = [(msk[s] - img[s]) / 1e6 for s in msk if s in img]
    ist = np.array(sorted(img))
    e2e = []
    for s, r in pos:
        j = np.searchsorted(ist, s)
        cand = [k for k in (j - 1, j) if 0 <= k < len(ist)]
        if not cand:
            continue
        k = min(cand, key=lambda k: abs(int(ist[k]) - int(s)))
        if abs(int(ist[k]) - int(s)) < 25_000_000:
            e2e.append((r - img[int(ist[k])]) / 1e6)
    last_img = max(img.values()) if img else None
    last_pose = max(r for _, r in pos) if pos else None
    return dict(n_img=len(img), n_mask=len(msk), n_pose=len(pos), mask_lat=ml, e2e=e2e,
                backlog_s=(last_pose - last_img) / 1e9 if (last_img and last_pose) else None)


def mem_peaks(f):
    peaks, minav = {}, None
    if not os.path.isfile(f):
        return peaks, None
    for ln in list(open(f))[1:]:
        p = ln.rstrip('\n').split(',')
        if len(p) < 6:
            continue
        n, hwm, av = p[2], int(p[4]), int(p[5])
        peaks[n] = max(peaks.get(n, 0), hwm)
        if av > 0:
            minav = av if minav is None else min(minav, av)
    return {k: v / 1024 for k, v in peaks.items()}, (minav / 1024 if minav else None)


def parse_run(rd, tegra):
    seq, m, run = rd.rstrip('/').split('/')[-3:]
    R = dict(seq=seq, method=m, run=run, st=defaultdict(list))
    for f in glob.glob(f'{rd}/savior_stats.jsonl*'):
        for ln in opn(f):
            try:
                t = json.loads(ln).get('timings_ms', {})
            except ValueError:
                continue
            for k, v in t.items():
                R['st'][k].append(v)
            if 'node_total' in t:
                cls = sum(t.get(k, 0.0) for k in ('motion', 'gating', 'tracking', 'extension'))
                R['st']['classification'].append(cls)
                R['st']['publish'].append(max(0.0, t['node_total'] - t.get('convert', 0) - t.get('segment', 0) - t.get('total', 0)))
    R['savior_frames'] = len(R['st'].get('node_total', []))
    f = f'{rd}/ov_timing.txt'
    R['ov_updates'] = 0
    if os.path.isfile(f):
        hdr = [h.strip() for h in open(f).readline().lstrip('#').split(',')]
        a = np.loadtxt(f, delimiter=',', comments='#', ndmin=2)
        if a.size:
            R['ov_updates'] = len(a)
            col = {h: a[:, j] * 1e3 for j, h in enumerate(hdr)}
            R['st']['ov_tracking'] = col['tracking'].tolist()
            R['st']['ov_total'] = col['total'].tolist()
            R['st']['ov_update'] = (col['total'] - col['tracking']).tolist()
    lg = next((x for x in (f'{rd}/launch.log.gz', f'{rd}/launch.log') if os.path.isfile(x)), None)
    R['final'] = None; R['too_late'] = None
    if lg:
        last = edge = None
        for ln in opn(lg):
            if 'SAVIOR-MASK] FINAL:' in ln:
                last = ln
            if '[SAVIOR-EDGE] FINAL:' in ln:
                edge = ln
        if last and (g := FIN.search(last)):
            R['final'] = dict(meas=int(g[1]), exact=int(g[2]), fb_latest=int(g[3]), fb_empty=int(g[4]), late=int(g[5]),
                              hold_avg=float(g[6]) if g[6] else None, hold_max=float(g[7]) if g[7] else None)
        if edge and (e := EDGE.search(edge)):
            R['too_late'] = int(e[1])
    fs = f'{rd}/feature_stats.csv'
    R['in_core'] = 0
    if os.path.isfile(fs):
        with open(fs) as fh:
            R['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    tf = f'{rd}/stamped_traj_estimate.txt'
    R['poses'] = sum(1 for ln in open(tf) if ln.strip() and not ln.startswith('#')) if os.path.isfile(tf) else 0
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
        R['status'] = f"{ri.get('status')}/{ri.get('returncode')}"; R['wall_s'] = ri.get('wall_time_s')
    except Exception:  # noqa: BLE001
        R['status'] = 'no_info'; R['wall_s'] = None
    R['lat'] = lat_parse(next((x for x in (f'{rd}/lat.csv.gz', f'{rd}/lat.csv') if os.path.isfile(x)), ''))
    try:
        t0, t1 = float(open(f'{rd}/t_start').read()), float(open(f'{rd}/t_end').read())
    except (OSError, ValueError):
        t0 = t1 = None
    # tegrastats window: the bag-playback part only (first .. last image receive of the probe) if available
    if R['lat'] and R['lat']['n_img']:
        a = np.loadtxt(next(x for x in (f'{rd}/lat.csv.gz', f'{rd}/lat.csv') if os.path.isfile(x)), delimiter=',', skiprows=1, dtype=np.int64, ndmin=2)
        ir = a[a[:, 0] == 0, 2] / 1e9
        R['play'] = (float(ir.min()), float(ir.max()))
    else:
        R['play'] = (t0, t1) if t0 else None
    R['tegra'] = twin(tegra, *R['play']) if R['play'] else None
    R['tegra_run'] = twin(tegra, t0, t1) if t0 else None
    R['mem'], R['minavail'] = mem_peaks(f'{rd}/mem.csv')
    return R


def timing_session(td):
    tegra = read_tegra(f'{td}/tegrastats.log')
    runs = [parse_run(rd, tegra) for rd in sorted(glob.glob(f'{td}/*_t1_*/*/run_[0-9][0-9]'))]
    marks = {}
    if os.path.isfile(f'{td}/markers.txt'):
        for ln in open(f'{td}/markers.txt'):
            p = ln.split()
            if len(p) >= 2 and p[1] in ('idle_start', 'idle_end'):
                marks[p[1]] = float(p[0])
    idle = twin(tegra, marks['idle_start'], marks['idle_end']) if len(marks) == 2 else None
    pw = {k: json.load(open(f'{td}/power_{k}.json')) for k in ('before', 'after') if os.path.isfile(f'{td}/power_{k}.json')}
    trt = [json.loads(l) for l in open(f'{td}/trtbench.jsonl')] if os.path.isfile(f'{td}/trtbench.jsonl') else []
    return dict(runs=runs, idle=idle, power=pw, trt=trt, n_tegra=len(tegra))


STAGES = [('segment', 'segmentation'), ('depth', 'depth'), ('classification', 'classification (motion+gating+tracking)'),
          ('compose', 'mask compose'), ('publish', 'convert/publish'), ('node_total', 'savior_node total'),
          ('ov_tracking', 'OV front-end'), ('ov_update', 'OV update'), ('ov_total', 'OV total'),
          ('mask_lat', 'mask latency'), ('e2e', 'end-to-end latency')]


def pool(runs, m):
    rs = [r for r in runs if r['method'] == m]
    if not rs:
        return None
    P = dict(n_runs=len(rs), st={})
    for k, _ in STAGES:
        if k in ('mask_lat', 'e2e'):
            v = [x for r in rs if r['lat'] for x in r['lat'][k]]
        else:
            v = [x for r in rs for x in r['st'].get(k, [])]
        P['st'][k] = q(v) if v else None
    return P


def rt_verdict(runs, m):
    """pre-registered RT_CRITERION.txt R1-R5 for method m (pooled over its runs)."""
    rs = [r for r in runs if r['method'] == m]
    ov = {(r['seq'], r['run']): r for r in runs if r['method'] == 'openvins'}
    out = dict(method=m, runs=len(rs))
    if not rs:
        return out
    # R1
    r1 = []
    for r in rs:
        f = r['final'] or {}
        # every OpenVINS measurement got its exact-stamp mask pair (back-end v2 processes every 2nd frame: meas ~ frames / 2)
        ok = bool(f) and f['fb_latest'] + f['fb_empty'] + f['late'] == 0 and (r['too_late'] or 0) == 0 and r['in_core'] == 0 \
            and f['exact'] == 2 * f['meas'] and r['savior_frames'] >= f['meas']
        r1.append(ok)
    out['R1'] = all(r1)
    # R2
    r2 = []
    for r in rs:
        o = ov.get((r['seq'], r['run']))
        pc = (o is None) or r['poses'] >= o['poses'] - 1
        bl = r['lat']['backlog_s'] if r['lat'] else None
        r2.append(pc and bl is not None and bl < 1.0)
    out['R2'] = all(r2)
    nt = [x for r in rs for x in r['st'].get('node_total', [])]
    out['node_total_mean'] = float(np.mean(nt)) if nt else None
    out['node_total_p99'] = float(np.percentile(nt, 99)) if nt else None
    out['R3'] = bool(nt) and float(np.mean(nt)) < 50.0
    key = 'mask_lat' if 'edge' in m else 'e2e'
    lv = [x for r in rs if r['lat'] for x in r['lat'][key]]
    out['R4_metric'] = key
    out['R4_p99'] = float(np.percentile(lv, 99)) if lv else None
    out['R4'] = bool(lv) and out['R4_p99'] < 250.0
    rams = [r['tegra']['ram']['max'] for r in rs if r['tegra'] and 'ram' in r['tegra']]
    swg = [r['tegra']['swap']['max'] - r['tegra']['swap']['min'] for r in rs if r['tegra'] and 'swap' in r['tegra']]
    out['ram_max_mb'] = max(rams) if rams else None
    out['swap_growth_mb'] = max(swg) if swg else None
    out['R5'] = bool(rams) and max(rams) < 7000 and (not swg or max(swg) <= 256)
    out['REALTIME'] = all(out[k] for k in ('R1', 'R2', 'R3', 'R4', 'R5'))
    out['margin'] = out['REALTIME'] and (out['node_total_p99'] or 1e9) < 50.0
    return out


def timing_tables(name, S, desk=None):
    runs = S['runs']
    methods = [m for m in ORDER if any(r['method'] == m for r in runs)]
    P = {m: pool(runs, m) for m in methods}
    pw = S['power'].get('before', {})
    hdr = (f"power mode {pw.get('power_mode')}, jetson_clocks {pw.get('jetson_clocks_inferred')}, GPU {pw.get('gpu_hz_cur_min_max')}, "
           f"other containers: '{pw.get('other_containers', '').strip() or 'none'}'")
    L = [f'# Jetson Orin NX 8 GB timing ({name}): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)', '', hdr, '',
         'Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker '
         '(+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); '
         'OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, '
         'end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).', '',
         '| method | runs | ' + ' | '.join(lbl for _, lbl in STAGES) + ' |', '|---|--:|' + '---|' * len(STAGES)]
    for m in methods:
        p = P[m]
        L.append(f"| {LABEL[m]} | {p['n_runs']} | " + ' | '.join(fq(p['st'][k]) for k, _ in STAGES) + ' |')
    # per sequence
    L += ['', '## Per sequence (savior_node total, OV total, end-to-end)', '', '| method | seq | frames | node_total | OV total | mask latency | end-to-end |', '|---|---|--:|---|---|---|---|']
    for m in methods:
        for seq in SEQS:
            rs = [r for r in runs if r['method'] == m and r['seq'] == seq]
            if not rs:
                continue
            nt = [x for r in rs for x in r['st'].get('node_total', [])]
            ot = [x for r in rs for x in r['st'].get('ov_total', [])]
            ml = [x for r in rs if r['lat'] for x in r['lat']['mask_lat']]
            ee = [x for r in rs if r['lat'] for x in r['lat']['e2e']]
            L.append(f"| {LABEL[m]} | {seq} | {sum(r['savior_frames'] or r['ov_updates'] for r in rs)} | {fq(q(nt)) if nt else '-'} | "
                     f"{fq(q(ot)) if ot else '-'} | {fq(q(ml)) if ml else '-'} | {fq(q(ee)) if ee else '-'} |")
    # throughput / keep-up
    L += ['', '## Does the filter keep up? (per run)', '',
          '| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |',
          '|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|']
    ov = {(r['seq'], r['run']): r for r in runs if r['method'] == 'openvins'}
    for r in sorted(runs, key=lambda r: (ORDER.index(r['method']), r['seq'], r['run'])):
        f = r['final'] or {}
        la = r['lat'] or {}
        ml = np.array(la.get('mask_lat') or [np.nan])
        late = ' / '.join(f'{int((ml > t).sum())}' for t in (50, 100, 250)) if la.get('mask_lat') else '-'
        o = ov.get((r['seq'], r['run']))
        L.append(f"| {LABEL[r['method']]} | {r['seq']} | {r['run']} | {r['status']} | {la.get('n_img', '-')} | {r['savior_frames'] or '-'} | "
                 f"{la.get('n_mask', '-') if r['method'] != 'openvins' else '-'} | {f.get('meas', '-')} | {f.get('exact', '-')} | "
                 f"{(f['fb_latest'] + f['fb_empty']) if f else '-'} | {f.get('late', '-')} | {r['too_late'] if r['too_late'] is not None else '-'} | {r['in_core']} | "
                 f"{f.get('hold_avg', '-')} / {f.get('hold_max', '-')} | {r['poses']} ({o['poses'] if o else '-'}) | "
                 f"{la.get('backlog_s') if la.get('backlog_s') is None else round(la['backlog_s'], 3)} | {late} |")
    # resources
    idle = S['idle'] or {}
    L += ['', '## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)', '',
          f"Idle baseline (container up, nothing running, 30 s): RAM {idle.get('ram', {}).get('mean', float('nan')):.0f} MB, "
          f"VDD_IN {idle.get('VDD_IN', {}).get('mean', float('nan')):.0f} mW, CPU {idle.get('cpu', {}).get('mean', float('nan')):.1f} %, "
          f"GR3D {idle.get('gr3d', {}).get('mean', float('nan')):.1f} %.", '',
          '| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |',
          '|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|']
    res = {}
    for m in methods:
        rs = [r for r in runs if r['method'] == m and r['tegra']]
        if not rs:
            continue
        g = lambda k, s: [r['tegra'][k][s] for r in rs if k in r['tegra']]  # noqa: E731
        peaks = defaultdict(float)
        for r in rs:
            for k, v in r['mem'].items():
                peaks[k] = max(peaks[k], v)
        top = ', '.join(f'{k} {v:.0f}' for k, v in sorted(peaks.items(), key=lambda kv: -kv[1])[:4])
        vin = np.mean(g('VDD_IN', 'mean')) if g('VDD_IN', 'mean') else float('nan')
        vi0 = idle.get('VDD_IN', {}).get('mean', float('nan'))
        mav = [r['minavail'] for r in rs if r['minavail']]
        res[m] = dict(ram_max=max(g('ram', 'max')), swap_growth=max(a - b for a, b in zip(g('swap', 'max'), g('swap', 'min'))),
                      gr3d_mean=float(np.mean(g('gr3d', 'mean'))), gr3d_p95=float(np.max(g('gr3d', 'p95'))), cpu_mean=float(np.mean(g('cpu', 'mean'))),
                      vdd_in_mean=float(vin), vdd_in_p95=float(np.max(g('VDD_IN', 'p95'))) if g('VDD_IN', 'p95') else None,
                      vdd_cgc=float(np.mean(g('VDD_CPU_GPU_CV', 'mean'))) if g('VDD_CPU_GPU_CV', 'mean') else None,
                      vdd_soc=float(np.mean(g('VDD_SOC', 'mean'))) if g('VDD_SOC', 'mean') else None,
                      mj_frame=float(vin / 20.0), mj_frame_above_idle=float((vin - vi0) / 20.0), tmax=max(g('tmax', 'max')),
                      minavail=min(mav) if mav else None, peaks=dict(peaks))
        x = res[m]
        L.append(f"| {LABEL[m]} | {x['ram_max']:.0f} | {x['swap_growth']:.0f} | {x['minavail'] if x['minavail'] is None else round(x['minavail'])} | "
                 f"{x['gr3d_mean']:.1f} / {x['gr3d_p95']:.0f} | {x['cpu_mean']:.1f} | {x['vdd_in_mean']:.0f} / {x['vdd_in_p95']:.0f} | "
                 f"{x['vdd_cgc']:.0f} | {x['vdd_soc']:.0f} | {x['mj_frame']:.0f} | {x['mj_frame_above_idle']:.0f} | {x['tmax']:.1f} | {top} |")
    # verdict
    V = [rt_verdict(runs, m) for m in methods if m != 'openvins']
    L += ['', '## Real-time verdict (pre-registered RT_CRITERION.txt)', '',
          '| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |',
          '|---|---|---|---|---|---|---|---|']
    for v in V:
        L.append(f"| {LABEL[v['method']]} | {'yes' if v['R1'] else 'NO'} | {'yes' if v['R2'] else 'NO'} | {'yes' if v['R3'] else 'NO'} ({v['node_total_mean']:.1f} ms) | "
                 f"{'yes' if v['R4'] else 'NO'} ({v['R4_metric']} p99 {v['R4_p99'] if v['R4_p99'] is None else round(v['R4_p99'], 1)} ms) | "
                 f"{'yes' if v['R5'] else 'NO'} ({v['ram_max_mb']:.0f} MB, swap +{v['swap_growth_mb']:.0f}) | **{'YES' if v['REALTIME'] else 'NO'}** | "
                 f"{'yes' if v['margin'] else 'no'} (p99 {v['node_total_p99']:.1f} ms) |")
    if S['trt']:
        L += ['', '## TensorRT micro-benchmark (pure GPU time per inference, batch 1, trtbench.py)', '',
              '| engine | GPU ms median | p90 | min | wall ms median |', '|---|--:|--:|--:|--:|']
        L += [f"| {os.path.basename(t['engine'])} | {t['gpu_ms_med']} | {t['gpu_ms_p90']} | {t['gpu_ms_min']} | {t['wall_ms_med']} |" for t in S['trt']]
    if desk:
        L += ['', '## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)', '',
              '| run | segment | depth | node_total | OV total |', '|---|---|---|---|---|']
        L += desk
    wmd(f'{TAB}/timing_{name}.md', L)
    json.dump(dict(pooled={m: P[m] for m in methods}, verdict=V, resources=res, idle=S['idle'], power=S['power'], trt=S['trt'],
                   runs=[{k: v for k, v in r.items() if k not in ('st', 'lat')} | {'lat_summary': None if not r['lat'] else
                          {k: r['lat'][k] for k in ('n_img', 'n_mask', 'n_pose', 'backlog_s')}} for r in runs]),
              open(f'{TAB}/timing_{name}.json', 'w'), indent=1, default=float)
    return P, V, res


def desktop_ref():
    out = []
    for f, keys in ((f'{WS}/results/cpp_port/tables/timing.json', ('py_main_ctrl', 'cpp_main_final')),
                    (f'{WS}/results/edge_study/tables/timing.json', ('e_L250_dfronly', 'openvins'))):
        if not os.path.isfile(f):
            continue
        d = json.load(open(f))
        for k in keys:
            if k in d:
                x = d[k]
                g = lambda s: fq(x[s]) if s in x else '-'  # noqa: E731
                out.append(f"| {k} | {g('segment')} | {g('depth')} | {g('node_total')} | {g('ov_total')} |")
    return out


# ------------------------------------------------------------------------------------------------ figures
def figures(sessions, pm):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.style.use(STYLE)
    # (1) per-stage stacked bars (MEAN ms per frame, so the parts add up to the node mean) + desktop vs Orin panel
    name, S, P = sessions[0]
    ms = [m for m in ('yolo_naive', 'sens_fix1', 'savior_cpp', 'savior_edge', 'savior_edge_cpp') if P.get(m)]
    SHORT = {'yolo_naive': 'Y-Cls\n(Py)', 'sens_fix1': 'SAVIOR\n(Py)', 'savior_cpp': 'SAVIOR\n(C++)', 'savior_edge': 'S-edge\n(Py)',
             'savior_edge_cpp': 'S-edge\n(C++)'}
    if ms:
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.16, 2.7), gridspec_kw=dict(width_ratios=[1.35, 1]))
        parts = [('segment', 'segmentation', '////'), ('depth', 'depth', '....'), ('classification', 'classification', 'xxxx'),
                 ('compose', 'compose', '----'), ('publish', 'convert / publish', '')]
        x = np.arange(len(ms))
        bottom = np.zeros(len(ms))
        mean = lambda m, k: P[m]['st'][k][3] if P[m]['st'].get(k) else 0.0  # noqa: E731
        for k, lbl, h in parts:
            v = np.array([mean(m, k) for m in ms])
            ax.bar(x, v, 0.6, bottom=bottom, facecolor='white', edgecolor=[COLOR[m] for m in ms], hatch=h, linewidth=0.8)
            bottom += v
        ovm = np.array([mean(m, 'ov_total') for m in ms])
        ax.bar(x, ovm, 0.6, bottom=bottom, facecolor='0.85', edgecolor=[COLOR[m] for m in ms], linewidth=0.8)
        nt90 = np.array([P[m]['st']['node_total'][1] for m in ms])
        ax.plot(x, nt90, 'k_', ms=14, mew=1.2)
        ax.axhline(50, color='black', ls='--', lw=0.8)
        ax.text(len(ms) - 0.55, 52, '50 ms (20 Hz)', ha='right', va='bottom', fontsize=6)
        ax.set_xticks(x, [SHORT[m] for m in ms], fontsize=7)
        ax.set_ylabel('time per frame (ms, mean)')
        ax.set_title('Per-Stage Time on Orin NX 8 GB')
        hs = [Patch(facecolor='white', edgecolor='black', hatch=h, label=l) for _, l, h in parts] + \
             [Patch(facecolor='0.85', edgecolor='black', label='OpenVINS (per update)'), Line2D([], [], color='black', marker='_', ls='', ms=10, mew=1.2, label='savior_node p90')]
        ax.legend(handles=hs, loc='upper center', fontsize=6, ncol=3)
        ax.set_ylim(0, max(60, float(max(nt90.max(), (bottom + ovm).max())) * 1.45))
        # (b) desktop vs Orin, savior_node mean, Python vs C++ (SAVIOR main)
        dj = {}
        for f in (f'{WS}/results/cpp_port/tables/timing.json',):
            if os.path.isfile(f):
                dj = json.load(open(f))
        rows = [('Python', 'py_main_ctrl', 'sens_fix1', 92.0 - 10.6), ('C++', 'cpp_main_final', 'savior_cpp', 49.0 - 10.6)]
        xb = np.arange(len(rows))
        dv = [dj.get(k, {}).get('node_total', [np.nan] * 4)[3] for _, k, _, _ in rows]
        ov_ = [P[m]['st']['node_total'][3] if P.get(m) else np.nan for _, _, m, _ in rows]
        bx.bar(xb - 0.18, dv, 0.34, facecolor='white', edgecolor='black', hatch='////', label='desktop (RTX PRO 6000 + TR 9960X)')
        bx.bar(xb + 0.18, ov_, 0.34, facecolor='white', edgecolor='red', label='Orin NX measured')
        bx.plot(xb + 0.18, [e for *_, e in rows], 'kx', ms=6, label='Orin NX estimate (pre-device)')
        bx.axhline(50, color='black', ls='--', lw=0.8)
        for xi, v in zip(xb + 0.18, ov_):
            bx.text(xi, v + 2, f'{v:.0f}', ha='center', fontsize=6)
        for xi, v in zip(xb - 0.18, dv):
            bx.text(xi, v + 2, f'{v:.0f}', ha='center', fontsize=6)
        bx.set_xticks(xb, [r[0] + ' node' for r in rows], fontsize=7)
        bx.set_ylabel('savior_node time per frame (ms, mean)')
        bx.set_title('SAVIOR Node: Desktop vs Orin NX')
        bx.legend(loc='upper right', fontsize=6)
        bx.set_ylim(0, max(130, np.nanmax(ov_) * 1.6))
        fig.text(0.29, -0.02, '(a)', ha='center', fontsize=8); fig.text(0.79, -0.02, '(b)', ha='center', fontsize=8)
        fig.tight_layout()
        for e in ('pdf', 'png'):
            fig.savefig(f'{FIG}/stage_breakdown.{e}')
        plt.close(fig)
    # (2) latency ECDF
    fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.4))
    for m in ORDER:
        rs = [r for r in S['runs'] if r['method'] == m and r['lat']]
        if not rs:
            continue
        for ax, key in zip(axs, ('mask_lat', 'e2e')):
            v = np.sort([x for r in rs for x in r['lat'][key]])
            if len(v):
                ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=COLOR[m], ls=LS[m], label=LABEL[m])
    for ax, t in zip(axs, ('Mask Latency (image to mask)', 'End-to-End Latency (image to pose)')):
        ax.axvline(50, color='0.5', ls=':', lw=0.8); ax.axvline(250, color='0.5', ls='--', lw=0.8)
        ax.set_xscale('log'); ax.set_xlabel('latency (ms)'); ax.set_ylabel('fraction of frames'); ax.set_title(t)
    axs[1].legend(loc='lower right', fontsize=6)
    for e in ('pdf', 'png'):
        fig.savefig(f'{FIG}/latency_cdf.{e}')
    plt.close(fig)
    # (3) pipeline mask IoU ECDF (1 - IoU, log)
    if pm:
        rows, curves = pm
        fig, ax = plt.subplots(figsize=(3.5, 2.4))
        for (c, v, seq), x in curves.items():
            y = np.sort(np.maximum(1 - x, 1e-6))
            ax.plot(y, np.arange(1, len(y) + 1) / len(y), color=('red' if v == 'main' else 'green') if c == 'device' else 'black',
                    ls='-' if seq == 'hall_t1_L3' else '--', lw=1.2 if c == 'device' else 0.7,
                    label=f"{'SAVIOR' if v == 'main' else 'S-edge'} {seq.split('_')[0]}" + ('' if c == 'device' else ' (FP32 vs FP16, server)'))
        ax.set_xscale('log'); ax.set_xlabel('1 - per-frame IoU (device vs server)'); ax.set_ylabel('fraction of frames')
        ax.set_title('Dynamic-Mask Agreement'); ax.legend(loc='lower right', fontsize=6)
        for e in ('pdf', 'png'):
            fig.savefig(f'{FIG}/pipe_mask_iou_cdf.{e}')
        plt.close(fig)
    # (4) power + RAM timeline of the first session
    tg = read_tegra(f'{DEV}/{name}/tegrastats.log')
    if tg:
        t0 = tg[0]['t']
        fig, axs = plt.subplots(2, 1, figsize=(7.16, 3.2), sharex=True)
        t = np.array([r['t'] - t0 for r in tg])
        axs[0].plot(t, [r.get('VDD_IN', np.nan) / 1e3 for r in tg], color='black', lw=0.6)
        axs[1].plot(t, [r.get('ram', np.nan) / 1e3 for r in tg], color='black', lw=0.8)
        axs[1].axhline(7.4, color='0.5', ls='--', lw=0.8)
        for r in S['runs']:
            if r['play']:
                for ax in axs:
                    ax.axvspan(r['play'][0] - t0, r['play'][1] - t0, color=COLOR[r['method']], alpha=0.12, lw=0)
        axs[0].set_ylabel('VDD_IN (W)'); axs[1].set_ylabel('RAM used (GB)'); axs[1].set_xlabel('session time (s)')
        axs[0].set_title('Power and Memory During the Timing Session')
        from matplotlib.patches import Patch
        axs[0].legend(handles=[Patch(color=COLOR[m], alpha=0.3, label=LABEL[m]) for m in ORDER if any(r['method'] == m for r in S['runs'])],
                      loc='upper left', fontsize=6, ncol=6)
        for e in ('pdf', 'png'):
            fig.savefig(f'{FIG}/power_ram_timeline.{e}')
        plt.close(fig)


# ------------------------------------------------------------------------------------------------ engines / accuracy
def engines_and_accuracy():
    L = []
    f = f'{DEV}/engines/engines.json'
    if os.path.isfile(f):
        E = json.load(open(f))['engines']
        L += ['# On-device TensorRT engines (FP16, built on the Orin NX)', '', '| engine | check | md5 | MB | TensorRT | first predict ms | problems |', '|---|---|---|--:|---|--:|---|']
        L += [f"| {e['name']} | {e['check']} | {e['md5']} | {e['size_mb']:.1f} | {e['trt']} | {e.get('predict_ms_first')} | {'; '.join(e.get('problems', [])) or '-'} |" for e in E]
    f = f'{DEV}/masks/agreement.json'
    if os.path.isfile(f):
        A = json.load(open(f))['results']
        L += ['', '# Offline YOLO mask agreement (device engine vs desktop engine, every 10th frame, package v1 tolerances)', '',
              '| engine x seq | verdict | worst class IoU | instance recall | precision | predict ms device (desktop) |', '|---|---|--:|--:|--:|---|']
        L += [f"| {r['label']} | {r['verdict']} | {r['worst_class_iou']} | {r['instances']['recall']} | {r['instances']['precision']} | "
              f"{r['predict_ms_median']['test']:.1f} ({r['predict_ms_median']['ref']:.1f}) |" for r in A]
    if L:
        wmd(f'{TAB}/engines_yolo_masks.md', L)
    for d in sorted(glob.glob(f'{DEV}/accuracy/compare.json')):
        C = json.load(open(d))
        tag = os.path.basename(os.path.dirname(d))
        L = [f'# Closed-loop accuracy on the Jetson vs the desktop ({tag}; rate 0.5, frozen configs, offsets 0.0 / 0.6 / 1.2 s)', '',
             f"overall {C['overall']} (accuracy {C['accuracy_verdict']}, offline masks {C['mask_verdict']}); sync {C.get('sync_summary')}", '',
             '| seq | method | verdict | ATE device m (0.0 / 0.6 / 1.2) | ATE desktop m | gm ratio device/desktop | md5 equal | valid | notes |', '|---|---|---|---|---|--:|--:|---|---|']
        for seq, R in C['per_seq'].items():
            for m, x in R.items():
                ad = ' / '.join('-' if r['ate_device'] is None else f"{r['ate_device']:.3f}" for r in x['runs'])
                ak = ' / '.join(f"{r['ate_desktop']:.3f}" for r in x['runs'])
                ok = [r for r in x['runs'] if r['ate_device'] and r['ate_device'] <= 2 and r['ate_desktop'] <= 2]
                gm = math.exp(np.mean([math.log(r['ate_device'] / r['ate_desktop']) for r in ok])) if ok else None
                L.append(f"| {seq} | {x['label']} | {x['verdict']} | {ad} | {ak} | {'-' if gm is None else f'{gm:.3f}'} | {x['md5_equal']}/3 | "
                         f"{sum(1 for r in x['runs'] if r['valid'])}/3 | {'; '.join(x['notes'])} |")
        sci = C.get('scientific_checks') or {}
        if sci:
            L += ['', '| seq | ratio | device | desktop (same 3 offsets) | same direction |', '|---|---|--:|--:|---|']
            for seq, d2 in sci.items():
                for k, v in d2.items():
                    L.append(f"| {seq} | {k} | {v['device']} | {v['desktop_same3']} | {v['same_direction']} |")
        wmd(f'{TAB}/{tag}.md', L)


def bv2_table():
    """device back-end v2 closed loop (accuracy_bv2) vs the desktop back-end v2 runs (results/backend_v2/runs, evaluated into
    raw/desktop_bv2_eval). C++ node runs are compared with the desktop Python run of the same pipeline."""
    root = f'{DEV}/accuracy_bv2'
    if not os.path.isdir(root):
        return
    ref = {'openvins': 'openvins', 'savior_cpp': 'sens_fix1', 'savior_edge_cpp': 'savior_edge', 'sens_fix1': 'sens_fix1', 'savior_edge': 'savior_edge'}
    def ate(f):
        if not os.path.isfile(f):
            return {}
        return {t['name']: (t['ate']['trans_m']['rmse'] if t.get('ate') else None) for t in yaml.safe_load(open(f))['trials']}
    L = ['# Closed loop with the re-frozen OpenVINS back-end v2 (results/backend_v2/backend_config.yaml md5 10c2144b: track_frequency 10.5, max_clones 15)', '',
         'Jetson (C++ node for SAVIOR / SAVIOR-edge, rate 0.5, offsets 0.0 / 0.6 / 1.2 s) vs the desktop back-end v2 runs of the same pipeline',
         '(Python node, results/backend_v2/runs, same offsets = run_01 / 04 / 07). Failure = ATE > 2 m.', '',
         '| seq | method | ATE device m (0.0 / 0.6 / 1.2) | ATE desktop m | gm ratio (both < 2 m) | failures device / desktop (3) | desktop 10-offset range (non-failed) |', '|---|---|---|---|--:|---|---|']
    rows = []
    for seq in SEQS:
        for m in ('openvins', 'savior_cpp', 'savior_edge_cpp', 'sens_fix1', 'savior_edge'):
            dv = ate(f'{root}/{seq}/{m}/eval/eval_summary.yaml')
            if not dv:
                continue
            dk = ate(f'{ROOT}/raw/desktop_bv2_eval/{seq}/{ref[m]}/eval_summary.yaml')
            rr = ['run_01', 'run_04', 'run_07']
            a = [dv.get(r) for r in rr]; b = [dk.get(r) for r in rr]
            ok = [(x, y) for x, y in zip(a, b) if x is not None and y is not None and x <= 2 and y <= 2]
            gm = math.exp(np.mean([math.log(x / y) for x, y in ok])) if ok else None
            d10 = [v for v in dk.values() if v is not None and v <= 2]
            f = lambda v: '-' if v is None else (f'{v:.3f}' if v <= 2 else f'FAIL ({v:.0f})')  # noqa: E731
            L.append(f"| {seq} | {LABEL[m]} | {' / '.join(f(v) for v in a)} | {' / '.join(f(v) for v in b)} | {'-' if gm is None else f'{gm:.3f}'} | "
                     f"{sum(v is not None and v > 2 for v in a)} / {sum(v is not None and v > 2 for v in b)} | "
                     f"{(f'{min(d10):.3f}-{max(d10):.3f} ({len(d10)}/10)') if d10 else '-'} |")
            rows.append(dict(seq=seq, method=m, device=a, desktop=b, gm=gm))
    json.dump(rows, open(f'{TAB}/accuracy_bv2.json', 'w'), indent=1)
    wmd(f'{TAB}/accuracy_bv2.md', L)


def hall10_table():
    """hall_t1_L3, all 10 desktop offsets on the device for the C++ nodes (accuracy run_01/04/07 + accuracy_hall10 runs 02/03/05/06/08/09/10,
    evaluated on the server into raw/device_eval_hall10) vs the 10 desktop offsets of the same pipeline (reference/desktop_ate.json)."""
    ref = json.load(open(f'{WS}/results/jetson_pkg/savior_jetson_pkg_v1/reference/desktop_ate.json'))['runs']['hall_t1_L3']
    def ate(f):
        return {t['name']: (t['ate']['trans_m']['rmse'] if t.get('ate') else None) for t in yaml.safe_load(open(f))['trials']} if os.path.isfile(f) else {}
    L = ['# hall_t1_L3, 10 start offsets (0.0-1.8 s), back-end v1, rate 0.5: Jetson C++ node vs desktop (Python = C++ md5-identical there)', '',
         '| method | device ATE per offset 0.0 ... 1.8 s (m) | desktop ATE per offset (m) | device median [min-max] | desktop median [min-max] | failures > 2 m device / desktop | runs > 0.5 m device / desktop | gm ratio device/desktop (paired, non-failed) |',
         '|---|---|---|---|---|---|---|--:|']
    rows = {}
    for m, rm in (('savior_cpp', 'sens_fix1'), ('savior_edge_cpp', 'savior_edge')):
        a = ate(f'{DEV}/accuracy/hall_t1_L3/{m}/eval/eval_summary.yaml')
        a.update({k: v for k, v in ate(f'{ROOT}/raw/device_eval_hall10/{m}/eval_summary.yaml').items()})
        runs = [f'run_{i:02d}' for i in range(1, 11)]
        if not all(r in a for r in runs):
            continue
        dv = [a[r] for r in runs]; dk = [ref[rm]['trials'][r]['ate_m'] for r in runs]
        ok = [(x, y) for x, y in zip(dv, dk) if x <= 2 and y <= 2]
        gm = math.exp(np.mean([math.log(x / y) for x, y in ok]))
        f = lambda v: f'{v:.3f}' if v <= 2 else f'FAIL({v:.0f})'  # noqa: E731
        L.append(f"| {LABEL[m]} | {' '.join(f(v) for v in dv)} | {' '.join(f(v) for v in dk)} | {np.median(dv):.3f} [{min(dv):.3f}-{max(dv):.3f}] | "
                 f"{np.median(dk):.3f} [{min(dk):.3f}-{max(dk):.3f}] | {sum(v > 2 for v in dv)} / {sum(v > 2 for v in dk)} | {sum(v > 0.5 for v in dv)} / {sum(v > 0.5 for v in dk)} | {gm:.3f} |")
        rows[m] = dict(device=dv, desktop=dk, gm=gm)
    if rows:
        json.dump(rows, open(f'{TAB}/accuracy_hall10.json', 'w'), indent=1)
        wmd(f'{TAB}/accuracy_hall10.md', L)


def main():
    engines_and_accuracy()
    hall10_table()
    bv2_table()
    pm = pipe_masks()
    sessions = []
    desk = desktop_ref()
    for td in sorted(glob.glob(f'{DEV}/timing*')):
        if not os.path.isdir(td) or not glob.glob(f'{td}/*_t1_*'):
            continue
        name = os.path.basename(td)
        S = timing_session(td)
        P, V, res = timing_tables(name, S, desk)
        sessions.append((name, S, P))
    if sessions:
        main_s = [s for s in sessions if s[0] == os.environ.get('JV_MAIN_SESSION', 'timing_main')] or sessions
        figures(main_s, pm)


if __name__ == '__main__':
    main()
