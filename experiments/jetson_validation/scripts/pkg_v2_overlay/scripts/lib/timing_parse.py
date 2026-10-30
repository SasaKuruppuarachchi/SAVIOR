#!/usr/bin/env python3
"""timing_parse.py <timing_dir>: per-stage timing + resources of the Jetson timing runs (runs inside the image, numpy only).

<timing_dir>/<seq>/<method>/run_XX/{savior_stats.jsonl.gz, ov_timing.txt, mem.csv, t_start, t_end, run_info.yaml}
<timing_dir>/tegrastats.log  (lines '<epoch> <tegrastats line>', host side), trtbench.jsonl, power_before/after.json
Outputs:
  timing.json       {run_key: {stage: [median, p90, p99, mean], _n_runs, _n_frames}}  run_key = method and method@seq
                    (same stages / ov_timing columns / percentiles as results/p7/scripts/p7timing.py)
  resources.json    per run: tegrastats (RAM / swap peak, CPU % mean, GR3D % mean, EMC % mean, temps max, VDD_IN mean),
                    per-process peak memory (max VmHWM over the run), frames processed vs bag frames, wall time
  timing.md         human tables
"""
import glob, gzip, json, os, re, sys
from collections import defaultdict
import numpy as np

ST = ['convert', 'segment', 'depth', 'motion', 'gating', 'tracking', 'extension', 'compose', 'predict', 'total', 'node_total']
OVC = {'tracking': 'ov_tracking', 'propagation': 'ov_propagation', 'msckf update': 'ov_msckf_update', 'slam update': 'ov_slam_update',
       'slam delayed': 'ov_slam_delayed', 're-tri & marg': 'ov_retri_marg', 'total': 'ov_total'}
BAG_FRAMES = {'hall_t1_L3': 2258, 'aisles_t1_L2': 2176}
TG = dict(ram=re.compile(r'RAM (\d+)/(\d+)MB'), swap=re.compile(r'SWAP (\d+)/(\d+)MB'), cpu=re.compile(r'CPU \[([^\]]*)\]'),
          emc=re.compile(r'EMC_FREQ (\d+)%'), gr3d=re.compile(r'GR3D_FREQ (\d+)%'), temp=re.compile(r'(\w+)@(-?[\d.]+)C'),
          vin=re.compile(r'VDD_IN (\d+)mW'))


def q(v):
    v = np.asarray(v, float)
    return [round(float(np.median(v)), 3), round(float(np.percentile(v, 90)), 3), round(float(np.percentile(v, 99)), 3),
            round(float(v.mean()), 3)]


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
            r['ram_mb'] = int(m[1]); r['ram_total_mb'] = int(m[2])
        if (m := TG['swap'].search(s)):
            r['swap_mb'] = int(m[1])
        if (m := TG['cpu'].search(s)):
            loads = [int(x.split('%')[0]) for x in m[1].split(',') if '%' in x]
            r['cpu_mean'] = float(np.mean(loads)) if loads else None
            r['cpu_max_core'] = max(loads) if loads else None
            r['cpu_online'] = len(loads)
        if (m := TG['emc'].search(s)):
            r['emc'] = int(m[1])
        if (m := TG['gr3d'].search(s)):
            r['gr3d'] = int(m[1])
        if (m := TG['vin'].search(s)):
            r['vdd_in_mw'] = int(m[1])
        r['temps'] = {k: float(v) for k, v in TG['temp'].findall(s)}
        rows.append(r)
    return rows


def window(rows, t0, t1):
    w = [r for r in rows if t0 <= r['t'] <= t1]
    if not w:
        return None
    out = dict(samples=len(w))
    for k in ('ram_mb', 'swap_mb'):
        v = [r[k] for r in w if k in r]
        if v:
            out[k + '_max'] = max(v); out[k + '_mean'] = round(float(np.mean(v)), 1)
    for k in ('cpu_mean', 'cpu_max_core', 'emc', 'gr3d', 'vdd_in_mw'):
        v = [r[k] for r in w if r.get(k) is not None]
        if v:
            out[k + '_avg'] = round(float(np.mean(v)), 1); out[k + '_p95'] = round(float(np.percentile(v, 95)), 1)
    temps = defaultdict(list)
    for r in w:
        for k, v in r['temps'].items():
            temps[k].append(v)
    out['temp_max_c'] = {k: max(v) for k, v in temps.items()}
    out['ram_total_mb'] = next((r['ram_total_mb'] for r in w if 'ram_total_mb' in r), None)
    return out


def mem_peaks(f):
    peaks = {}
    if not os.path.isfile(f):
        return peaks, None
    minavail = None
    for ln in list(open(f))[1:]:
        p = ln.rstrip('\n').split(',')
        if len(p) < 6:
            continue
        n, hwm, av = p[2], int(p[4]), int(p[5])
        peaks[n] = max(peaks.get(n, 0), hwm)
        if av > 0:
            minavail = av if minavail is None else min(minavail, av)
    return {k: round(v / 1024, 1) for k, v in sorted(peaks.items(), key=lambda kv: -kv[1])}, (round(minavail / 1024, 1) if minavail else None)


def main():
    T = sys.argv[1]
    tegra = read_tegra(f'{T}/tegrastats.log')
    acc = defaultdict(lambda: defaultdict(list))
    nrun = defaultdict(int)
    res = {}
    for rd in sorted(glob.glob(f'{T}/*_t1_*/*/run_[0-9][0-9]')):
        seq, m, run = rd.split('/')[-3:]
        keys = (f'{m}@{seq}', m)
        for k in keys:
            nrun[k] += 1
        nframes = 0
        for f in glob.glob(f'{rd}/savior_stats.jsonl*'):
            op = gzip.open if f.endswith('.gz') else open
            for ln in op(f, 'rt'):
                try:
                    t = json.loads(ln).get('timings_ms', {})
                except ValueError:
                    continue
                nframes += 1
                for s in ST:
                    if s in t:
                        for k in keys:
                            acc[k][s].append(t[s])
        f = f'{rd}/ov_timing.txt'
        n_ov = 0
        if os.path.isfile(f):
            hdr = [h.strip() for h in open(f).readline().lstrip('#').split(',')]
            a = np.loadtxt(f, delimiter=',', comments='#', ndmin=2)
            n_ov = len(a)
            for j, h in enumerate(hdr):
                if h in OVC and a.size:
                    for k in keys:
                        acc[k][OVC[h]].extend((a[:, j] * 1e3).tolist())
        try:
            t0, t1 = float(open(f'{rd}/t_start').read()), float(open(f'{rd}/t_end').read())
        except (OSError, ValueError):
            t0 = t1 = None
        peaks, minavail = mem_peaks(f'{rd}/mem.csv')
        res[f'{m}@{seq}/{run}'] = dict(seq=seq, method=m, run=run, wall_s=None if t0 is None else round(t1 - t0, 1),
                                       savior_frames=nframes, ov_updates=n_ov, bag_frames=BAG_FRAMES.get(seq),
                                       tegrastats=window(tegra, t0, t1) if t0 else None, mem_peak_mb=peaks,
                                       mem_available_min_mb=minavail)
    out = {r: {k: q(v) for k, v in d.items() if v} for r, d in acc.items()}
    for r in out:
        out[r]['_n_runs'] = nrun[r]
        out[r]['_n_frames'] = len(acc[r].get('node_total', acc[r].get('ov_total', [])))
    # per method: worst-case resources over its runs
    per_m = defaultdict(lambda: dict(mem_peak_mb={}, ram_mb_max=0, temp_max_c={}))
    for x in res.values():
        pm = per_m[x['method']]
        for k, v in x['mem_peak_mb'].items():
            pm['mem_peak_mb'][k] = max(pm['mem_peak_mb'].get(k, 0), v)
        tg = x['tegrastats'] or {}
        pm['ram_mb_max'] = max(pm['ram_mb_max'], tg.get('ram_mb_max', 0))
        for k in ('gr3d_avg', 'cpu_mean_avg', 'emc_avg', 'vdd_in_mw_avg'):
            if k in tg:
                pm.setdefault(k, []).append(tg[k])
        for k, v in (tg.get('temp_max_c') or {}).items():
            pm['temp_max_c'][k] = max(pm['temp_max_c'].get(k, -99), v)
    for pm in per_m.values():
        for k in ('gr3d_avg', 'cpu_mean_avg', 'emc_avg', 'vdd_in_mw_avg'):
            if k in pm:
                pm[k] = round(float(np.mean(pm[k])), 1)
    trt = [json.loads(l) for l in open(f'{T}/trtbench.jsonl')] if os.path.isfile(f'{T}/trtbench.jsonl') else []
    json.dump(out, open(f'{T}/timing.json', 'w'), indent=1)
    json.dump(dict(runs=res, per_method=per_m, trtbench=trt, tegrastats_samples=len(tegra)), open(f'{T}/resources.json', 'w'), indent=1)
    SC = ['segment', 'depth', 'motion', 'gating', 'tracking', 'extension', 'compose', 'predict', 'node_total', 'ov_tracking',
          'ov_msckf_update', 'ov_retri_marg', 'ov_total']
    L = ['# Jetson timing: median / p90 / p99 ms per frame (savior_node) or per update (ov_msckf); rate 1.0, one container\n']
    for f in ('power_before.json', 'power_after.json'):
        if os.path.isfile(f'{T}/{f}'):
            p = json.load(open(f'{T}/{f}'))
            L.append(f"{f}: power mode {p.get('power_mode')}, jetson_clocks {p.get('jetson_clocks_inferred')}, temps {p.get('thermal')}")
    for title, pick in (('Pooled over both sequences', lambda r: '@' not in r), ('Per sequence', lambda r: '@' in r)):
        L += [f'\n## {title}\n', '| run | runs | frames | ' + ' | '.join(SC) + ' |', '|---|--:|--:|' + '---|' * len(SC)]
        for r in sorted(filter(pick, out)):
            L.append(f"| {r} | {out[r]['_n_runs']} | {out[r]['_n_frames']} | " +
                     ' | '.join('{:.1f} / {:.1f} / {:.1f}'.format(*out[r][k][:3]) if k in out[r] else '-' for k in SC) + ' |')
    L += ['\n## Resources per method (worst run)\n', '| method | RAM used max (MB, tegrastats) | GR3D avg % | CPU avg % | EMC avg % | VDD_IN avg mW | peak RSS per process (MB) |',
          '|---|--:|--:|--:|--:|--:|---|']
    for m, pm in sorted(per_m.items()):
        top = ', '.join(f'{k} {v:.0f}' for k, v in list(pm['mem_peak_mb'].items())[:5])
        L.append(f"| {m} | {pm['ram_mb_max'] or '-'} | {pm.get('gr3d_avg', '-')} | {pm.get('cpu_mean_avg', '-')} | {pm.get('emc_avg', '-')} | "
                 f"{pm.get('vdd_in_mw_avg', '-')} | {top} |")
    L += ['\n## Throughput per run\n', '| run | wall s | savior frames | ov updates | min MemAvailable MB |', '|---|--:|--:|--:|--:|']
    for k, x in sorted(res.items()):
        L.append(f"| {k} | {x['wall_s']} | {x['savior_frames']} | {x['ov_updates']} | {x['mem_available_min_mb']} |")
    if trt:
        L += ['\n## TensorRT micro-benchmark (pure GPU time per inference, batch 1)\n', '| engine | gpu ms median | p90 | min | wall ms median |', '|---|--:|--:|--:|--:|']
        L += [f"| {t['engine']} | {t['gpu_ms_med']} | {t['gpu_ms_p90']} | {t['gpu_ms_min']} | {t['wall_ms_med']} |" for t in trt]
    open(f'{T}/timing.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
