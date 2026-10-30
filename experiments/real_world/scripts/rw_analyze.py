#!/usr/bin/env python3
"""rw_analyze.py : analysis of the real-world study (Monado MSD Valve Index), as pre-registered in results/real_world/PROTOCOL.yaml.

Inputs: results/real_world/runs/<seq>/<method>/{run_XX, eval/eval_summary.yaml}, share yamls (results/real_world/share/*.yaml),
reference masks data/monado/refmasks/<seq>.npz. Run in the savior image (numpy, scipy, matplotlib).
Statistics (as the addendum / bv2analyze.py): paired per-offset log ATE ratio (failures capped at 10 m), geometric-mean ratio - 1,
run-level bootstrap 95 % CI (20000, seed 0), Wilcoxon signed-rank, Holm within (group, reference); sequence-level functions copied
verbatim from results/stats_v3/scripts/stats3_core.py (two-stage cluster bootstrap, exact sign-flip, REML random intercept).
-> results/real_world/tables/*.md|json, results/real_world/figures/*.pdf|png (paper.mplstyle)."""
import csv
import glob
import gzip
import itertools
import json
import math
import os
import re

import numpy as np
import yaml
from scipy import optimize, stats

WS = '/home/sasa/workspace/savior_ws'
RW = WS + '/results/real_world'
# FREEZE_AMENDMENT 2: overridable for the disclosed rate-0.5 secondary (runs_rate05 -> tables_rate05 / figures_rate05)
RUNS = os.environ.get('RW_RUNS', RW + '/runs')
TAB, FIG = os.environ.get('RW_TAB', RW + '/tables'), os.environ.get('RW_FIG', RW + '/figures')
SHARE = os.environ.get('RW_SHARE', RW + '/share')
EXPECTED = yaml.safe_load(open(RW + '/prep/expected_frames.yaml'))   # scripts/rw_expected_frames.py
os.makedirs(TAB, exist_ok=True)
os.makedirs(FIG, exist_ok=True)
NB = 20000
CAP = 10.0
FAIL = 1.0
IDX = list(range(1, 11))
PERSON = ['MIO13', 'MIO15', 'MIO16']
STATIC = ['MIO07']
SEQS = PERSON + STATIC
OVM = ['openvins', 'savior_none', 'yolo_naive', 'sens_fix1']
SOTA = ['vins_fusion', 'dynavins']
VMETH = OVM + SOTA + ['diag_openvins']   # A5: every method is checked by the validity rule
LAB = {'openvins': 'OpenVINS', 'savior_none': 'SAVIOR-none', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR',
       'vins_fusion': 'VINS-Fusion', 'dynavins': 'DynaVINS', 'diag_openvins': 'OpenVINS (diag)'}
COL = {'openvins': 'blue', 'savior_none': '0.5', 'yolo_naive': 'green', 'sens_fix1': 'red', 'vins_fusion': 'black', 'dynavins': '0.35'}
SEQNAME = {'MIO13': 'moving person', 'MIO15': 'person + props', 'MIO16': 'person + props + screens', 'MIO07': 'static (control)'}
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


# ------------------------------------------------------------------ load
def load_eval(seq, m):
    fn = f'{RUNS}/{seq}/{m}/eval/eval_summary.yaml'
    ate, rpe, rot = {}, {}, {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                ate[i] = rpe[i] = rot[i] = math.inf
                continue
            ate[i] = float(t['ate']['trans_m']['rmse'])
            rot[i] = float(t['ate'].get('rot_deg', {}).get('rmse', math.nan)) if isinstance(t['ate'].get('rot_deg'), dict) else math.nan
            # FIX (FREEZE_AMENDMENT A4): savior-eval writes mean 0 with num_samples 0 for a sub-length that no sub-trajectory
            # reaches (a truncated run: MIO13 yolo_naive run_02 = 95 poses, sens_fix1 run_10 = 219 poses) -> that is "no RPE",
            # not 0 m (the 0 forced the geometric mean to 0.0000). Shortest length as before, NaN when it has no segments.
            ks = sorted(t.get('rpe', {}), key=float)
            r0 = t['rpe'][ks[0]]['trans_m'] if ks else {}
            rpe[i] = float(r0['mean']) if ks and int(r0.get('num_samples', 0)) > 0 else math.nan
    return ate, rpe, rot


def validity(seq, m):
    out = {}
    for rd in sorted(glob.glob(f'{RUNS}/{seq}/{m}/run_*')):
        i = int(rd.rsplit('_', 1)[1])
        r = dict(status='?', traj=0, final='-', fb=0, late=0, in_core=0, md5='')
        try:
            ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
            r['status'] = f"{ri.get('status')}/{ri.get('returncode', 0)}"
        except Exception:
            r['status'] = 'no_info'
        tf = f'{rd}/stamped_traj_estimate.txt'
        if os.path.isfile(tf):
            r['traj'] = sum(1 for x in open(tf) if not x.startswith('#'))
            import hashlib
            r['md5'] = hashlib.md5(open(tf, 'rb').read()).hexdigest()
        lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
        r['frames'] = 0   # A4 diagnostic: stereo frames OpenVINS processed (one '[TIME]: ... seconds total' line each)
        last = None
        if lg:
            for line in opn(lg):
                if 'FINAL:' in line:
                    last = line
                elif 'seconds total' in line:
                    r['frames'] += 1
        if m in ('yolo_naive', 'sens_fix1', 'savior_none'):
            g = FIN.search(last) if last else None
            if g:
                r.update(final='ok', fb=int(g[3]) + int(g[4]), late=int(g[5]))
        else:
            r['final'] = 'n/a'
        if m in SOTA:   # A5: stereo pairs received by vins_node (one 'frontend' row per pair in its timing.csv)
            tc = f'{rd}/timing.csv'
            r['frames'] = sum(1 for x in csv.DictReader(open(tc)) if x.get('kind') == 'frontend') if os.path.isfile(tc) else 0
            r['final'] = 'n/a'
        fs = f'{rd}/feature_stats.csv'
        if os.path.isfile(fs):
            with open(fs) as fh:
                r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
        out[i] = r
    return out


ATE, RPE, ROT, VAL = {}, {}, {}, {}
for s in SEQS:
    for m in OVM + SOTA:
        ATE.setdefault(s, {})[m], RPE.setdefault(s, {})[m], ROT.setdefault(s, {})[m] = load_eval(s, m)
        VAL.setdefault(s, {})[m] = validity(s, m)
    VAL[s]['diag_openvins'] = validity(s, 'diag_openvins')
# pose-count rule + full validity; A5 (FREEZE_AMENDMENT 2): + frames processed == bag stereo pairs after the offset (+-0)
# (ros2 27 Hz pairs for the OpenVINS family, ros1 54 Hz pairs received by vins_node for VINS-Fusion / DynaVINS)
for s in SEQS:
    for m in VMETH:
        for i, r in VAL[s][m].items():
            ref = VAL[s]['openvins'].get(i, {}).get('traj', 0)
            ok = r['status'].startswith('ok') and r['traj'] > 0 and r['final'] in ('ok', 'n/a') and r['fb'] + r['late'] == 0 and r['in_core'] == 0
            r['pose_rule'] = (r['traj'] >= ref - 1) if m in OVM else True
            r['expected'] = EXPECTED[s]['ros1_pairs' if m in SOTA else 'ros2_pairs'][f'{0.2 * (i - 1):.1f}']
            r['frames_rule'] = r['frames'] == r['expected']
            r['valid'] = int(ok and r['pose_rule'] and r['frames_rule'])


# ------------------------------------------------------------------ statistics (copied from results/stats_v3/scripts/stats3_core.py)
def boot_iid(x):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (NB, x.size)).mean(axis=1), [2.5, 97.5])


def wilcox(x):
    nz = x[np.abs(x) > 1e-12]
    return float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0


def boot_two_stage(X, seed=0):
    keys = list(X)
    k = len(keys)
    n = np.array([X[s].size for s in keys])
    nmax = n.max()
    M = np.full((k, nmax), np.nan)
    for j, s in enumerate(keys):
        M[j, :n[j]] = X[s]
    rng = np.random.default_rng(seed)
    out = np.empty(NB)
    step = 5000
    for c0 in range(0, NB, step):
        b = min(step, NB - c0)
        si = rng.integers(0, k, (b, k))
        ns = n[si]
        oi = np.floor(rng.random((b, k, nmax)) * ns[..., None]).astype(int)
        v = M[si[..., None], oi]
        valid = np.arange(nmax)[None, None, :] < ns[..., None]
        sm = np.where(valid, v, 0).sum(axis=2) / ns
        out[c0:c0 + b] = sm.mean(axis=1)
    return out


def signflip(m):
    k = m.size
    if k == 0 or np.all(np.abs(m) < 1e-12):
        return 1.0, 1.0
    S = np.array(list(itertools.product([1, -1], repeat=k)))
    st = np.abs((S * m).mean(axis=1))
    p = float(np.mean(st >= abs(m.mean()) - 1e-12))
    return p, 2.0 / 2 ** k


def reml_ri(X):
    ys = [X[s] for s in X]
    k = len(ys)
    n = np.array([y.size for y in ys], float)
    N = n.sum()
    S = np.array([y.sum() for y in ys])
    if k < 2:
        return None
    allv = np.concatenate(ys)
    if np.ptp(allv) < 1e-12:
        return dict(mu=float(allv.mean()), se=0.0, df=k - 1, t=0.0, p=1.0, tau2=0.0, sigma2=0.0, icc=float('nan'))

    def parts(g):
        w = n / (1 + n * g)
        mu = (S / (1 + n * g)).sum() / w.sum()
        Q = sum(((y - mu) ** 2).sum() - g / (1 + ni * g) * (y - mu).sum() ** 2 for y, ni in zip(ys, n))
        return mu, Q, w

    def negll(lg):
        g = math.exp(lg)
        mu, Q, w = parts(g)
        s2 = Q / (N - 1)
        return 0.5 * ((N - 1) * math.log(max(s2, 1e-300)) + np.log(1 + n * g).sum() + math.log(w.sum()))

    best = None
    for lo, hi in ((-20, -5), (-5, 0), (0, 5), (5, 12)):
        r = optimize.minimize_scalar(negll, bounds=(lo, hi), method='bounded')
        if best is None or r.fun < best.fun:
            best = r
    g = math.exp(best.x)
    mu0, Q0, w0 = parts(0.0)
    f0 = 0.5 * ((N - 1) * math.log(max(Q0 / (N - 1), 1e-300)) + math.log(w0.sum()))
    if f0 <= best.fun:
        g = 0.0
    mu, Q, w = parts(g)
    s2 = Q / (N - 1)
    se = math.sqrt(s2 / w.sum())
    df = k - 1
    t = mu / se if se > 0 else 0.0
    p = float(2 * stats.t.sf(abs(t), df)) if se > 0 else 1.0
    return dict(mu=float(mu), se=float(se), df=df, t=float(t), p=p, tau2=float(g * s2), sigma2=float(s2), icc=float(g / (1 + g)))


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


pct = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def lr(a, b, cap=CAP):
    if cap == 'excl':
        return None if (a > FAIL or b > FAIL) else math.log(a / b)
    return math.log(min(a, cap) / min(b, cap))


def paired(D, A, B, seqs, cap=CAP):
    out = {}
    for s in seqs:
        a, b = D[s].get(A, {}), D[s].get(B, {})
        x = [lr(a[i], b[i], cap) for i in IDX if i in a and i in b and not (math.isnan(a[i]) or math.isnan(b[i]))]
        x = [v for v in x if v is not None]
        if x:
            out[s] = np.array(x)
    return out


def analyse(D, A, B, seqs, cap=CAP):
    X = paired(D, A, B, seqs, cap)
    if not X:
        return None
    x = np.concatenate(list(X.values()))
    ci = boot_iid(x)
    res = dict(A=A, B=B, n=int(x.size), k=len(X), gm=pct(x.mean()), ci=[pct(c) for c in ci], p_wilcoxon=wilcox(x),
               wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()),
               per_seq={s: pct(v.mean()) for s, v in X.items()})
    if len(X) >= 2:
        mseq = np.array([v.mean() for v in X.values()])
        bt = boot_two_stage(X)
        sf, minp = signflip(mseq)
        rm = reml_ri(X)
        res.update(seq_est=pct(mseq.mean()), seq_ci=[pct(c) for c in np.percentile(bt, [2.5, 97.5])], signflip_p=sf, signflip_min_p=minp,
                   reml_p=rm['p'] if rm else None, reml_icc=rm['icc'] if rm else None,
                   seq_dir=f"{int((mseq < 0).sum())}/{len(mseq)}")
    return res


def fails(D, m, seqs, thr=FAIL):
    v = [D[s][m][i] for s in seqs for i in IDX if i in D[s][m]]
    return sum(1 for x in v if x > thr), len(v)


def gmean(v):
    v = [min(x, CAP) for x in v]
    return math.exp(np.mean(np.log(v))) if v else math.nan


def fmt(v, d=1):
    return '-' if v is None or (isinstance(v, float) and math.isnan(v)) else f'{v:+.{d}f}'


# ------------------------------------------------------------------ tables
def main():
    out = {}
    L = ['# Real-world study (Monado MSD, Valve Index) - results\n']
    # validity
    L += ['## Run validity (pre-registered rule + FREEZE_AMENDMENT 2 frame rule)\n', '| sequence | method | runs | valid | fallbacks | late | n_in_core | pose rule fail | frame rule fail (frames lost) | md5 = openvins |',
          '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|']
    vt = {}
    for s in SEQS:
        for m in VMETH:
            V = VAL[s][m]
            eq = sum(1 for i, r in V.items() if r['md5'] and r['md5'] == VAL[s]['openvins'].get(i, {}).get('md5'))
            vt[(s, m)] = dict(runs=len(V), valid=sum(r['valid'] for r in V.values()))
            L.append(f"| {s} | {LAB[m]} | {len(V)} | {sum(r['valid'] for r in V.values())} | {sum(r['fb'] for r in V.values())} | "
                     f"{sum(r['late'] for r in V.values())} | {sum(r['in_core'] for r in V.values())} | "
                     f"{sum(1 for r in V.values() if not r['pose_rule'])} | {sum(1 for r in V.values() if not r['frames_rule'])} "
                     f"({sum(r['expected'] - r['frames'] for r in V.values())}) | {eq if m in OVM else '-'} |")
    # A4: list every run that is still invalid (the protocol re-runs invalid runs; any listed here is IN the statistics below)
    bad = [f"{s} {LAB[m]} run_{i:02d} ({r['status']}, {r['traj']} poses vs openvins {VAL[s]['openvins'].get(i, {}).get('traj', 0)}, frames {r['frames']}/{r['expected']})"
           for s in SEQS for m in VMETH for i, r in sorted(VAL[s][m].items()) if not r['valid']]
    L.append('\nInvalid runs still in the statistics: ' + ('; '.join(bad) if bad else 'none') + '\n')
    out['invalid_runs'] = bad
    out['input_missing_frames'] = {f'{s}:{m}': [VAL[s][m][i]['expected'] - VAL[s][m][i]['frames'] for i in sorted(VAL[s][m])]
                                   for s in SEQS for m in VMETH}
    # per-sequence ATE summary
    L += ['\n## ATE RMSE per sequence (posyaw, m): geometric mean over the 10 offsets (failures capped at 10 m), median, failures > 1 m\n',
          '| sequence | ' + ' | '.join(LAB[m] for m in OVM + SOTA) + ' |', '|---|' + '--:|' * len(OVM + SOTA)]
    summ = {}
    for s in SEQS:
        cells = []
        for m in OVM + SOTA:
            v = [ATE[s][m][i] for i in IDX if i in ATE[s][m]]
            if not v:
                cells.append('-')
                continue
            f = sum(1 for x in v if x > FAIL)
            summ[(s, m)] = dict(gm=gmean(v), med=float(np.median([min(x, CAP) for x in v])), fails=f, n=len(v),
                                min=float(min(v)), max=float(max(v)))
            cells.append(f"{gmean(v):.3f} / {np.median([min(x, CAP) for x in v]):.3f} / {f}" + (f' (n={len(v)})' if len(v) != 10 else ''))
        L.append(f'| {s} {SEQNAME[s]} | ' + ' | '.join(cells) + ' |')
    out['summary'] = {f'{s}:{m}': v for (s, m), v in summ.items()}
    # RPE
    L += ['\n## RPE (mean translational error, shortest savior-eval sub-length; geometric mean over non-failed runs)\n',
          '| sequence | ' + ' | '.join(LAB[m] for m in OVM + SOTA) + ' |', '|---|' + '--:|' * len(OVM + SOTA)]
    for s in SEQS:
        cells = []
        for m in OVM + SOTA:
            v = [RPE[s][m][i] for i in IDX if i in RPE[s][m] and ATE[s][m][i] <= FAIL and math.isfinite(RPE[s][m][i])]
            cells.append(f'{math.exp(np.mean(np.log(v))):.4f} (n={len(v)})' if v else '-')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    # paired comparisons
    comps = [('sens_fix1', 'openvins'), ('yolo_naive', 'openvins'), ('sens_fix1', 'yolo_naive'), ('savior_none', 'openvins'),
             ('sens_fix1', 'vins_fusion'), ('sens_fix1', 'dynavins'), ('openvins', 'vins_fusion'), ('dynavins', 'vins_fusion')]
    groups = {'person (MIO13+15+16)': PERSON, 'MIO13': ['MIO13'], 'MIO15': ['MIO15'], 'MIO16': ['MIO16'], 'static MIO07': STATIC}
    res = {}
    for g, ss in groups.items():
        for A, B in comps:
            r = analyse(ATE, A, B, ss)
            if r:
                res[(g, A, B)] = r
    # Holm within (group, reference) over the methods
    for g in groups:
        for ref in {B for _, _, B in res if True}:
            keys = [k for k in res if k[0] == g and k[2] == ref]
            if keys:
                adj = holm([res[k]['p_wilcoxon'] for k in keys])
                for k, a in zip(keys, adj):
                    res[k]['p_holm'] = float(a)
    L += ['\n## Paired ATE comparisons (A vs B): geometric-mean ratio - 1 [%], run-level bootstrap 95 % CI, Wilcoxon p (Holm within group x reference); '
          'sequence-level estimate (mean of per-sequence mean log ratios) with two-stage cluster-bootstrap CI and exact sign-flip p (k = 3: min p = 0.25)\n',
          '| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |',
          '|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|']
    for (g, A, B), r in res.items():
        ps = ', '.join(f'{s} {v:+.0f}' for s, v in r['per_seq'].items())
        L.append(f"| {g} | {LAB[A]} vs {LAB[B]} | {r['n']} | {r['gm']:+.1f} | [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] | {r['wins']}/{r['losses']} | "
                 f"{r['p_wilcoxon']:.3g} ({r.get('p_holm', float('nan')):.3g}) | {fmt(r.get('seq_est'))} | "
                 + (f"[{r['seq_ci'][0]:+.0f}, {r['seq_ci'][1]:+.0f}]" if 'seq_ci' in r else '-') +
                 f" | {r.get('signflip_p', '-') if 'signflip_p' not in r else round(r['signflip_p'], 3)} | {r.get('seq_dir', '-')} | {ps} |")
    out['paired'] = {f'{g}|{A}|{B}': r for (g, A, B), r in res.items()}
    # cap / failure sensitivity for the key comparisons
    L += ['\n## Sensitivity: failure handling (person group, run-level GM [%])\n', '| A vs B | cap 2 m | cap 10 m | cap 50 m | failures excluded (> 1 m) |',
          '|---|--:|--:|--:|--:|']
    for A, B in comps[:4]:
        cells = []
        for cap in (2.0, 10.0, 50.0, 'excl'):
            r = analyse(ATE, A, B, PERSON, cap)
            cells.append(f"{r['gm']:+.1f} (n={r['n']})" if r else '-')
        L.append(f'| {LAB[A]} vs {LAB[B]} | ' + ' | '.join(cells) + ' |')
    L += ['\n## Failures (ATE > threshold) per method, person group / static\n', '| method | > 0.5 m | > 1 m (protocol) | > 2 m | static > 1 m |', '|---|--:|--:|--:|--:|']
    for m in OVM + SOTA:
        c = [fails(ATE, m, PERSON, t) for t in (0.5, 1.0, 2.0)] + [fails(ATE, m, STATIC, 1.0)]
        L.append(f'| {LAB[m]} | ' + ' | '.join(f'{a}/{n}' for a, n in c) + ' |')
    # measurement share
    sh = {}
    for s in SEQS:
        ys = sorted(glob.glob(f'{SHARE}/{s}_run_*.yaml'))
        if ys:
            Y = [yaml.safe_load(open(y)) for y in ys]
            sh[s] = dict(n=len(Y), msckf_used_meas=float(np.mean([y['post_init']['frac_msckf_used_meas_human'] for y in Y])),
                         msckf_used_tracks=float(np.mean([y['post_init']['frac_msckf_used_tracks_human'] for y in Y])),
                         slam_update=float(np.mean([y['post_init']['frac_slam_update_meas_human'] for y in Y])),
                         kept_obs_cam0=float(np.mean([y['frac_kept_obs_on_human_cam0'] for y in Y])),
                         frames_with_feat=float(np.mean([y['frames_with_feature_on_human_cam0'] for y in Y])),
                         chi2_rej_human=[y['post_init']['human'].get('msckf_chi2_reject_rate') for y in Y],
                         chi2_rej_other=[y['post_init']['non_human'].get('msckf_chi2_reject_rate') for y in Y])
        mk = f'{WS}/data/monado/refmasks/{s}.npz'
        if os.path.isfile(mk):
            z = np.load(mk)
            pl = z['px_left']
            sh.setdefault(s, {}).update(px_mean=float(pl.mean()), px_frames_with_person=float((pl > 0).mean()), px_p90=float(np.percentile(pl, 90)),
                                        px_frames_over_25=float((pl > 0.25).mean()), px_max=float(pl.max()))
    out['share'] = sh
    L += ['\n## Share of the information on people (reference masks = offline YOLO26x-seg @960, person; diag_openvins post-init)\n',
          '| sequence | person pixel share (mean) | frames with a person | frames > 25 % person | kept cam0 obs on person | MSCKF-used meas. on person | SLAM-update meas. on person | chi2 reject person / other |',
          '|---|--:|--:|--:|--:|--:|--:|---|']
    for s in SEQS:
        d = sh.get(s, {})
        f = lambda k: f"{100 * d[k]:.2f} %" if k in d else '-'  # noqa: E731
        cr = (f"{np.nanmean([x for x in d['chi2_rej_human'] if x is not None]):.2f} / {np.nanmean([x for x in d['chi2_rej_other'] if x is not None]):.2f}"
              if d.get('chi2_rej_human') and any(x is not None for x in d['chi2_rej_human']) else '-')
        L.append(f"| {s} | {f('px_mean')} | {f('px_frames_with_person')} | {f('px_frames_over_25')} | {f('kept_obs_cam0')} | {f('msckf_used_meas')} | "
                 f"{f('slam_update')} | {cr} |")
    open(f'{TAB}/results.md', 'w').write('\n'.join(L) + '\n')
    json.dump(json.loads(json.dumps(out, default=float)), open(f'{TAB}/results.json', 'w'), indent=1)
    # per-run table
    with open(f'{TAB}/per_run.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['seq', 'method', 'run', 'offset_s', 'ate_m', 'rpe_m', 'valid', 'poses'])
        for s in SEQS:
            for m in OVM + SOTA:
                for i in IDX:
                    if i in ATE[s][m]:
                        v = VAL[s].get(m, {}).get(i, {})
                        w.writerow([s, m, i, f'{0.2 * (i - 1):.1f}', ATE[s][m][i], RPE[s][m].get(i), v.get('valid', ''), v.get('traj', '')])
    print('\n'.join(L))
    figures(sh, summ)


# ------------------------------------------------------------------ figures (src/savior/docs/FIGURE_STYLE.md)
def figures(sh, summ):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.style.use(WS + '/src/savior/savior_eval/savior_eval/paper.mplstyle')
    SINGLE, DOUBLE = 3.5, 7.16

    def save(fig, name):
        for e in ('pdf', 'png'):
            fig.savefig(f'{FIG}/{name}.{e}', dpi=300)
        plt.close(fig)

    # (1) per-sequence ATE strip plot, all methods
    ms = [m for m in OVM + SOTA if any(ATE[s][m] for s in SEQS)]
    fig, axs = plt.subplots(1, len(SEQS), figsize=(DOUBLE, 2.0), gridspec_kw=dict(wspace=0.32))
    for ax, s in zip(axs, SEQS):
        for j, m in enumerate(ms):
            v = [min(ATE[s][m][i], CAP) for i in IDX if i in ATE[s][m]]
            if not v:
                continue
            x = j + np.linspace(-0.18, 0.18, len(v))
            ax.scatter(x, v, s=7, facecolors='none', edgecolors=COL[m], lw=0.6)
            ax.plot([j - 0.3, j + 0.3], [gmean(v)] * 2, color=COL[m], lw=1.2)
        ax.axhline(FAIL, color='0.6', lw=0.6, ls=':')
        ax.set_yscale('log')
        ax.set_xticks(range(len(ms)))
        ax.set_xticklabels([LAB[m] for m in ms], rotation=60, ha='right', fontsize=5.5)
        ax.tick_params(labelsize=6)
        ax.set_title(f'({chr(97 + SEQS.index(s))}) {s}: {SEQNAME[s]}', fontsize=6.5)
    axs[0].set_ylabel('ATE RMSE (m), 10 start offsets', fontsize=6.5)
    save(fig, 'fig_rw_ate')

    # (2) share vs gain: the paper's panel (a) points (oracle gain, simulated) + the real-world points (learned masks)
    def rows_csv(p):
        return list(csv.DictReader(open(p))) if os.path.isfile(p) else []
    fig, ax = plt.subplots(figsize=(SINGLE, 2.2))
    v = rows_csv(f'{WS}/results/p5_viode/tables/share_vs_gain.csv')
    w = rows_csv(f'{WS}/results/p6_warehouse/tables/share_vs_gain.csv')
    if v:
        ax.scatter([max(100 * float(r['msckf_used_meas_dyn']), 0.01) for r in v], [float(r['gain_oracle_dynamic_pct']) for r in v],
                   s=10, marker='o', facecolors='none', edgecolors='0.6', lw=0.6, label='VIODE, oracle (sim.)')
        ax.scatter([max(100 * float(r['msckf_used_meas_dyn']), 0.01) for r in v], [float(r['gain_yolo_p4_pot_pct']) for r in v],
                   s=8, marker='x', color='0.6', lw=0.6, label='VIODE, learned masks (sim.)')
    if w:
        ax.scatter([max(100 * float(r['msckf_used_meas_dyn']), 0.01) for r in w], [float(r['gain_oracle_moving_pct']) for r in w],
                   s=10, marker='s', color='0.6', label='Warehouse, oracle (sim.)')
    ax.scatter([np.mean([0.28, 0.42]), np.mean([0.76, 0.46, 0.79])], [-15.39, 9.74], s=12, marker='^', facecolors='none', edgecolors='0.6', lw=0.6,
               label='uHumans2, oracle (sim.)')
    for m, mk in (('sens_fix1', 'D'), ('yolo_naive', 'v')):
        xs, ys, ls_ = [], [], []
        for s in SEQS:
            if s in sh and 'msckf_used_meas' in sh[s]:
                X = paired(ATE, m, 'openvins', [s])
                if s in X:
                    xs.append(max(100 * sh[s]['msckf_used_meas'], 0.01))
                    ys.append(-pct(X[s].mean()))
                    ls_.append(s)
        if xs:
            ax.scatter(xs, ys, s=22, marker=mk, color=COL[m], label=f'Monado (real), {LAB[m]}', zorder=5)
            if m == 'sens_fix1':
                for x_, y_, l_ in zip(xs, ys, ls_):
                    ax.annotate(l_, (x_, y_), fontsize=5, xytext=(3, 3), textcoords='offset points')
    ax.axhline(0, color='blue', lw=0.7, ls='--')
    ax.set_xscale('log')
    ax.set_xlabel('MSCKF-used share on movers / people (%)', fontsize=6.5)
    ax.set_ylabel('ATE reduction vs OpenVINS (%)', fontsize=6.5)
    ax.tick_params(labelsize=6)
    ax.legend(loc='upper left', fontsize=4.8, handletextpad=0.2, borderpad=0.3, labelspacing=0.2)
    save(fig, 'fig_rw_share_gain')

    # (3) person pixel share over time (reference masks), per person sequence
    fig, ax = plt.subplots(figsize=(SINGLE, 1.6))
    for s, c in zip(SEQS, ('black', 'red', 'blue', '0.6')):
        mk = f'{WS}/data/monado/refmasks/{s}.npz'
        if os.path.isfile(mk):
            z = np.load(mk)
            t = (z['stamp_ns'] - z['stamp_ns'][0]) * 1e-9
            k = max(1, int(round(27 / 2)))   # 0.5 s moving average at 27 Hz
            y = np.convolve(z['px_left'], np.ones(k) / k, mode='same')
            ax.plot(t, 100 * y, color=c, lw=0.7, label=s)
    ax.set_xlabel('time (s)', fontsize=6.5)
    ax.set_ylabel('person pixels, cam0 (%)', fontsize=6.5)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=5, loc='upper right')
    save(fig, 'fig_rw_person_share')

    # (4) per-offset paired log ratio SAVIOR / Y-Cls vs OpenVINS (offset sensitivity view)
    fig, axs = plt.subplots(1, 2, figsize=(SINGLE, 1.7), sharey=True, gridspec_kw=dict(wspace=0.08))
    for ax, m in zip(axs, ('yolo_naive', 'sens_fix1')):
        for s, c in zip(SEQS, ('black', 'red', 'blue', '0.6')):
            a, b = ATE[s][m], ATE[s]['openvins']
            ii = [i for i in IDX if i in a and i in b]
            if ii:
                ax.plot([0.2 * (i - 1) for i in ii], [100 * (min(a[i], CAP) / min(b[i], CAP) - 1) for i in ii], marker='o', ms=2.5, lw=0.6, color=c, label=s)
        ax.axhline(0, color='blue', lw=0.7, ls='--')
        ax.set_title(f'({"ab"[m == "sens_fix1"]}) {LAB[m]} vs OpenVINS', fontsize=6.5)
        ax.set_xlabel('start offset (s)', fontsize=6.5)
        ax.tick_params(labelsize=6)
    axs[0].set_ylabel('ATE change (%)', fontsize=6.5)
    axs[1].legend(fontsize=5)
    save(fig, 'fig_rw_offsets')


if __name__ == '__main__':
    main()
