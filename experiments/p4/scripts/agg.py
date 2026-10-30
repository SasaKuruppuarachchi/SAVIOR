#!/usr/bin/env python3
"""P4 aggregation: ATE per run (paired by bag start offset = run index) + run evidence + paired statistics.

agg.py --seqs openloris_cafe1-1,uhumans2_office_s1_06h --methods openvins,none,full,full+mot --refs openvins,none,full
       [--md out.md] [--json out.json] [--title T]
Relative change rel = (ATE_ref - ATE_m) / ATE_ref (positive = method better), paired per (sequence, offset).
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_eval')
from savior_eval import runstats  # noqa: E402

P4 = '/home/sasa/workspace/savior_ws/results/p4'


def run_evidence(run_dir):
    """Cached per-run evidence: mask sync, features, savior stats (still, motion ms, core/ext)."""
    cache = os.path.join(run_dir, 'p4_evidence.json')
    traj = os.path.join(run_dir, 'stamped_traj_estimate.txt')
    if os.path.isfile(cache) and os.path.getmtime(cache) >= os.path.getmtime(traj):
        return json.load(open(cache))
    ev = {}
    ms = runstats.mask_sync(os.path.join(run_dir, 'launch.log'))
    if ms:
        ev['exact'] = ms.get('exact')
        ev['fallback'] = ms.get('fallback_latest', 0) + ms.get('fallback_empty', 0)
    fs = runstats.feature_stats(os.path.join(run_dir, 'feature_stats.csv'))
    if fs:
        ev['kept_c0'] = fs['cam0']['kept_mean']
        ev['kept_c1'] = fs.get('cam1', {}).get('kept_mean')
        ev['relaxed'] = fs['cam0']['relaxed_frames'] + fs.get('cam1', {}).get('relaxed_frames', 0)
        ev['rejected'] = fs['cam0']['rejected_mask'] + fs.get('cam1', {}).get('rejected_mask', 0)
        ev['in_core'] = fs['cam0']['in_core'] + fs.get('cam1', {}).get('in_core', 0)
    # init: kept features over the first 60 frames of cam0
    fn = os.path.join(run_dir, 'feature_stats.csv')
    if os.path.isfile(fn):
        try:
            a = np.genfromtxt(fn, delimiter=',', names=True)
            c0 = a[a['cam_id'] == 0]
            ev['kept_c0_first60'] = round(float(np.mean(c0['n_tracked'][:60] + c0['n_new'][:60])), 2)
        except Exception:
            pass
    sj = os.path.join(run_dir, 'savior_stats.jsonl')
    if os.path.isfile(sj):
        rows = []
        for line in open(sj):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
        if rows:
            hw = rows[0].get('image_size', [1, 1])
            npx = float(hw[0] * hw[1])
            ev['frames'] = len(rows)
            ev['core'] = round(float(np.mean([r['core_px'] for r in rows])) / npx * 100, 3)
            ev['ext'] = round(float(np.mean([r['ext_px'] for r in rows])) / npx * 100, 3)
            ev['still'] = round(float(np.mean([r.get('n_still', 0) for r in rows])), 3)
            ev['roots'] = round(float(np.mean([r.get('n_roots', 0) for r in rows])), 3)
            ev['promoted'] = round(float(np.mean([r.get('n_promoted', 0) for r in rows])), 3)
            for k in ('motion', 'total', 'depth', 'segment', 'node_total'):
                v = [r['timings_ms'][k] for r in rows if k in r.get('timings_ms', {})]
                if v:
                    ev['ms_' + k] = round(float(np.median(v)), 2)
            to = [r.get('imu', {}) or {} for r in rows]
            ev['imu_timeouts'] = max([x.get('timeouts', 0) for x in to] or [0])
    json.dump(ev, open(cache, 'w'))
    return ev


def load(seq, method):
    md = os.path.join(P4, seq, method)
    fn = os.path.join(md, 'eval', 'eval_summary.yaml')
    if not os.path.isfile(fn):
        return None
    s = yaml.safe_load(open(fn))
    runs = {}
    for t in s['trials']:
        if t['status'] != 'ok':
            continue
        idx = int(t['name'].split('_')[-1])
        k0 = list(t['rpe'].keys())[0]
        ev = run_evidence(os.path.join(md, t['name']))
        runs[idx] = dict(ate=t['ate']['trans_m']['rmse'], rot=t['ate']['rot_deg']['rmse'],
                         rpe=t['rpe'][k0]['trans_m']['mean'], **ev)
    return runs


def paired(data, seqs, m, ref):
    rels, diffs, per_seq = [], [], {}
    for sq in seqs:
        a, b = data.get((sq, m)), data.get((sq, ref))
        if not a or not b:
            continue
        common = sorted(set(a) & set(b))
        r = [(b[i]['ate'] - a[i]['ate']) / b[i]['ate'] for i in common]
        d = [a[i]['ate'] - b[i]['ate'] for i in common]
        if r:
            per_seq[sq] = (float(np.mean(r)), len(r))
            rels += r
            diffs += d
    if not rels:
        return None
    out = {'n': len(rels), 'mean_rel': float(np.mean(rels)), 'median_rel': float(np.median(rels)),
           'seq_mean_rel': float(np.mean([v[0] for v in per_seq.values()])), 'per_seq': per_seq,
           'wins': int(sum(1 for x in diffs if x < -1e-6)), 'losses': int(sum(1 for x in diffs if x > 1e-6))}
    try:
        from scipy.stats import wilcoxon
        nz = [x for x in diffs if abs(x) > 1e-6]
        out['p_wilcoxon'] = float(wilcoxon(nz).pvalue) if len(nz) >= 5 else float('nan')
    except Exception:
        out['p_wilcoxon'] = float('nan')
    rng = np.random.default_rng(0)
    rels_a = np.array(rels)
    bs = [rels_a[rng.integers(0, len(rels_a), len(rels_a))].mean() for _ in range(2000)]
    out['ci95'] = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    return out


def fmt(v, p=3):
    return '–' if v is None or (isinstance(v, float) and math.isnan(v)) else ('%.*f' % (p, v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seqs', required=True)
    ap.add_argument('--methods', required=True)
    ap.add_argument('--refs', default='openvins,none,full')
    ap.add_argument('--md', default='')
    ap.add_argument('--json', default='')
    ap.add_argument('--title', default='')
    ap.add_argument('--evidence', action='store_true', help='per-sequence evidence columns')
    a = ap.parse_args()
    seqs = a.seqs.split(',')
    if seqs == ['all']:
        seqs = sorted(os.path.basename(d) for d in glob.glob(P4 + '/*_*'))
    methods = a.methods.split(',')
    refs = [r for r in a.refs.split(',') if r]
    data = {}
    for sq in seqs:
        for m in set(methods + refs):
            r = load(sq, m)
            if r:
                data[(sq, m)] = r
    L = ['# ' + a.title if a.title else '', '']
    # per-sequence ATE table
    L += ['## ATE translation RMSE [m] (mean ± std over offsets; n runs)', '',
          '| sequence | ' + ' | '.join(methods) + ' |', '|:--|' + '--:|' * len(methods)]
    for sq in seqs:
        row = []
        for m in methods:
            r = data.get((sq, m))
            if not r:
                row.append('–')
                continue
            v = np.array([x['ate'] for x in r.values()])
            row.append('%.3f ± %.3f (%d)' % (v.mean(), v.std(), len(v)))
        L.append('| %s | %s |' % (sq.replace('openloris_', '').replace('uhumans2_office_s1_', 'uH2 '), ' | '.join(row)))
    for ref in refs:
        L += ['', '## Paired vs `%s`: mean relative ATE change [%%] per sequence (positive = better)' % ref, '',
              '| method | ' + ' | '.join(s.replace('openloris_', '').replace('uhumans2_office_s1_', 'uH2 ') for s in seqs)
              + ' | seq-mean | pooled mean [95% CI] | median | W/L | p (Wilcoxon) |',
              '|:--|' + '--:|' * (len(seqs) + 5)]
        for m in methods:
            if m == ref:
                continue
            st = paired(data, seqs, m, ref)
            if not st:
                continue
            cells = [('%+.1f' % (100 * st['per_seq'][s][0])) if s in st['per_seq'] else '–' for s in seqs]
            L.append('| %s | %s | %+.1f | %+.1f [%+.1f, %+.1f] | %+.1f | %d/%d | %s |' % (
                m, ' | '.join(cells), 100 * st['seq_mean_rel'], 100 * st['mean_rel'], 100 * st['ci95'][0],
                100 * st['ci95'][1], 100 * st['median_rel'], st['wins'], st['losses'], fmt(st['p_wilcoxon'], 3)))
    if a.evidence:
        L += ['', '## Evidence (means over runs)', '',
              '| sequence | method | ATE rot [deg] | RPE@10%% [m] | kept/frame c0 | kept c0 first 60 | relaxed | core %% | band %% | '
              'still/frame | promoted/frame | motion ms | node ms | fallbacks | imu timeouts |',
              '|:--|:--|' + '--:|' * 13]
        for sq in seqs:
            for m in methods:
                r = data.get((sq, m))
                if not r:
                    continue
                g = lambda k, p=2: fmt(np.mean([x[k] for x in r.values() if x.get(k) is not None]) if any(x.get(k) is not None for x in r.values()) else None, p)  # noqa: E731
                L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                    sq.replace('openloris_', '').replace('uhumans2_office_s1_', 'uH2 '), m, g('rot'), g('rpe', 3),
                    g('kept_c0', 1), g('kept_c0_first60', 1), g('relaxed', 0), g('core'), g('ext'), g('still'),
                    g('promoted'), g('ms_motion'), g('ms_node_total', 1), g('fallback', 0), g('imu_timeouts', 0)))
    text = '\n'.join(L)
    print(text)
    if a.md:
        open(a.md, 'w').write(text + '\n')
    if a.json:
        out = {'%s|%s' % k: v for k, v in data.items()}
        json.dump(out, open(a.json, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
