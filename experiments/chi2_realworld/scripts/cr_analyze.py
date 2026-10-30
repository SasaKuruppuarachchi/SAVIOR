#!/usr/bin/env python3
"""cr_analyze.py : analysis of the chi2-realworld check (PROTOCOL.yaml), with the real-world statistics: the functions below
(validity, boot_iid, wilcox, boot_two_stage, signflip, holm, lr, paired, analyse, fails, gmean) are copied from
results/real_world/scripts/rw_analyze.py (which copies them from results/stats_v3/scripts/stats3_core.py); only the run roots differ.
Own runs: results/chi2_realworld/runs/<seq>/{ovchi_best,sf1_chibest}; paired baselines: results/real_world/runs/<seq>/
{openvins,sens_fix1,yolo_naive,vins_fusion} (rate 0.25, Amendment 2). Primary statistics: invalid runs excluded pairwise;
include-all sensitivity. Applies DECISION_RULE.txt T1 / T2. -> tables/results.md, results.json, per_run.csv, invalid.txt.
Run in the savior image (scripts/c2py.sh python3 scripts/cr_analyze.py)."""
import csv, glob, gzip, hashlib, itertools, json, math, os, re
import numpy as np
import yaml
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
CR = WS + '/results/chi2_realworld'
RW = WS + '/results/real_world'
assert hashlib.md5(open(CR + '/DECISION_RULE.txt', 'rb').read()).hexdigest() == 'ad5789081473e4cc36909ddd6ac319f8'
assert hashlib.md5(open(CR + '/PROTOCOL.yaml', 'rb').read()).hexdigest() == open(CR + '/PROTOCOL.md5').read().split()[0]
EXPECTED = yaml.safe_load(open(RW + '/prep/expected_frames.yaml'))
TAB = CR + '/tables'
os.makedirs(TAB, exist_ok=True)
NB, CAP, FAIL = 20000, 10.0, 1.0
IDX = list(range(1, 11))
PERSON, STATIC = ['MIO13', 'MIO15', 'MIO16'], ['MIO07']
SEQS = PERSON + STATIC
OWN = ['ovchi_best', 'sf1_chibest']
BASEM = ['openvins', 'sens_fix1', 'yolo_naive', 'vins_fusion']
METH = BASEM[:2] + OWN + BASEM[2:]
ROOT = {m: CR + '/runs' for m in OWN} | {m: RW + '/runs' for m in BASEM}
SAVL = ('yolo_naive', 'sens_fix1', 'sf1_chibest')
LAB = {'openvins': 'OpenVINS', 'sens_fix1': 'SAVIOR', 'yolo_naive': 'Y-Cls', 'vins_fusion': 'VINS-Fusion',
       'ovchi_best': 'OpenVINS chi2x0.25', 'sf1_chibest': 'SAVIOR + chi2x0.25'}
SEQNAME = {'MIO13': 'moving person', 'MIO15': 'person + props', 'MIO16': 'person + props + screens', 'MIO07': 'static (control)'}
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')
CHI = re.compile(r'overriding node .*?(up_msckf_chi2_multipler|up_slam_chi2_multipler)')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


def load_eval(seq, m):
    fn = f'{ROOT[m]}/{seq}/{m}/eval/eval_summary.yaml'
    ate, rpe = {}, {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                ate[i] = rpe[i] = math.inf
                continue
            ate[i] = float(t['ate']['trans_m']['rmse'])
            ks = sorted(t.get('rpe', {}), key=float)
            r0 = t['rpe'][ks[0]]['trans_m'] if ks else {}
            rpe[i] = float(r0['mean']) if ks and int(r0.get('num_samples', 0)) > 0 else math.nan
    return ate, rpe


def validity(seq, m):
    out = {}
    for rd in sorted(glob.glob(f'{ROOT[m]}/{seq}/{m}/run_*')):
        i = int(rd.rsplit('_', 1)[1])
        r = dict(status='?', traj=0, final='-', fb=0, late=0, in_core=0, md5='', chi=set())
        try:
            ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
            r['status'] = f"{ri.get('status')}/{ri.get('returncode', 0)}"
        except Exception:
            r['status'] = 'no_info'
        tf = f'{rd}/stamped_traj_estimate.txt'
        if os.path.isfile(tf):
            r['traj'] = sum(1 for x in open(tf) if not x.startswith('#'))
            r['md5'] = hashlib.md5(open(tf, 'rb').read()).hexdigest()
        lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
        r['frames'] = 0
        last = None
        if lg:
            for line in opn(lg):
                if 'FINAL:' in line:
                    last = line
                elif 'seconds total' in line:
                    r['frames'] += 1
                elif 'overriding node' in line:
                    g = CHI.search(line)
                    if g:
                        r['chi'].add(g[1])
        if m in SAVL:
            g = FIN.search(last) if last else None
            if g:
                r.update(final='ok', fb=int(g[3]) + int(g[4]), late=int(g[5]))
        else:
            r['final'] = 'n/a'
        if m == 'vins_fusion':
            tc = f'{rd}/timing.csv'
            r['frames'] = sum(1 for x in csv.DictReader(open(tc)) if x.get('kind') == 'frontend') if os.path.isfile(tc) else 0
        fs = f'{rd}/feature_stats.csv'
        if os.path.isfile(fs):
            with open(fs) as fh:
                r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
        out[i] = r
    return out


ATE, RPE, VAL = {}, {}, {}
for s in SEQS:
    for m in METH:
        ATE.setdefault(s, {})[m], RPE.setdefault(s, {})[m] = load_eval(s, m)
        VAL.setdefault(s, {})[m] = validity(s, m)
for s in SEQS:
    for m in METH:
        for i, r in VAL[s][m].items():
            ref = VAL[s]['openvins'].get(i, {}).get('traj', 0)
            ok = r['status'].startswith('ok') and r['traj'] > 0 and r['final'] in ('ok', 'n/a') and r['fb'] + r['late'] == 0 and r['in_core'] == 0
            r['pose_rule'] = (r['traj'] >= ref - 1) if m != 'vins_fusion' else True
            r['expected'] = EXPECTED[s]['ros1_pairs' if m == 'vins_fusion' else 'ros2_pairs'][f'{0.2 * (i - 1):.1f}']
            r['frames_rule'] = r['frames'] == r['expected']
            r['delta_ok'] = (r['chi'] == {'up_msckf_chi2_multipler', 'up_slam_chi2_multipler'}) if m in OWN else (not r['chi'])
            r['valid'] = int(ok and r['pose_rule'] and r['frames_rule'] and r['delta_ok'] and i in ATE[s][m])


# ------------------------------------------------------------------ statistics (verbatim from rw_analyze.py)
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


def okpair(s, A, B, i, include_all):
    return include_all or (VAL[s][A].get(i, {}).get('valid') and VAL[s][B].get(i, {}).get('valid'))


def paired(D, A, B, seqs, cap=CAP, include_all=False, rpe=False):
    out = {}
    for s in seqs:
        a, b = D[s].get(A, {}), D[s].get(B, {})
        x = []
        for i in IDX:
            if i in a and i in b and not (math.isnan(a[i]) or math.isnan(b[i])) and okpair(s, A, B, i, include_all):
                if rpe:   # RPE: pairs where neither run is a failure
                    if ATE[s][A][i] > FAIL or ATE[s][B][i] > FAIL or not (math.isfinite(a[i]) and math.isfinite(b[i])):
                        continue
                    x.append(math.log(a[i] / b[i]))
                else:
                    x.append(lr(a[i], b[i], cap))
        x = [v for v in x if v is not None]
        if x:
            out[s] = np.array(x)
    return out


def analyse(D, A, B, seqs, cap=CAP, include_all=False, rpe=False):
    X = paired(D, A, B, seqs, cap, include_all, rpe)
    if not X:
        return None
    x = np.concatenate(list(X.values()))
    ci = boot_iid(x)
    res = dict(A=A, B=B, n=int(x.size), k=len(X), gm=pct(x.mean()), ci=[pct(c) for c in ci], p_wilcoxon=wilcox(x),
               wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), per_seq={s: pct(v.mean()) for s, v in X.items()})
    if len(X) >= 2:
        mseq = np.array([v.mean() for v in X.values()])
        bt = boot_two_stage(X)
        sf, minp = signflip(mseq)
        res.update(seq_est=pct(mseq.mean()), seq_ci=[pct(c) for c in np.percentile(bt, [2.5, 97.5])], signflip_p=sf, signflip_min_p=minp,
                   seq_dir=f"{int((mseq < 0).sum())}/{len(mseq)}")
    return res


def fails(D, m, seqs, thr=FAIL, include_all=False):
    v = [D[s][m][i] for s in seqs for i in IDX if i in D[s][m] and (include_all or VAL[s][m].get(i, {}).get('valid'))]
    return sum(1 for x in v if x > thr), len(v)


def gmean(v):
    v = [min(x, CAP) for x in v]
    return math.exp(np.mean(np.log(v))) if v else math.nan


def fmt(v, d=1):
    return '-' if v is None or (isinstance(v, float) and math.isnan(v)) else f'{v:+.{d}f}'


COMPS = [('ovchi_best', 'openvins'), ('sf1_chibest', 'openvins'), ('ovchi_best', 'sens_fix1'), ('sf1_chibest', 'sens_fix1'),
         ('ovchi_best', 'yolo_naive'), ('ovchi_best', 'vins_fusion'), ('sf1_chibest', 'vins_fusion'), ('sf1_chibest', 'ovchi_best'),
         ('sens_fix1', 'openvins')]   # last row = the published real-world SAVIOR vs OpenVINS, recomputed here as a consistency check
GROUPS = {'person (MIO13+15+16)': PERSON, 'MIO13': ['MIO13'], 'MIO15': ['MIO15'], 'MIO16': ['MIO16'], 'static MIO07': STATIC}


def run_comps(include_all, D=None, rpe=False):
    D = D or ATE
    res = {}
    for g, ss in GROUPS.items():
        for A, B in COMPS:
            r = analyse(D, A, B, ss, include_all=include_all, rpe=rpe)
            if r:
                res[(g, A, B)] = r
    for g in GROUPS:
        for ref in {B for _, _, B in res}:
            keys = [k for k in res if k[0] == g and k[2] == ref and k[1] != 'sens_fix1']
            if keys:
                for k, a in zip(keys, holm([res[k]['p_wilcoxon'] for k in keys])):
                    res[k]['p_holm'] = float(a)
    return res


def table(res, title):
    L = [f'\n## {title}\n',
         '| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |',
         '|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|']
    for (g, A, B), r in res.items():
        ps = ', '.join(f'{s} {v:+.0f}' for s, v in r['per_seq'].items())
        L.append(f"| {g} | {LAB[A]} vs {LAB[B]} | {r['n']} | {r['gm']:+.1f} | [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] | {r['wins']}/{r['losses']} | "
                 f"{r['p_wilcoxon']:.3g} ({r.get('p_holm', float('nan')):.3g}) | {fmt(r.get('seq_est'))} | "
                 + (f"[{r['seq_ci'][0]:+.0f}, {r['seq_ci'][1]:+.0f}]" if 'seq_ci' in r else '-') +
                 f" | {round(r['signflip_p'], 3) if 'signflip_p' in r else '-'} | {r.get('seq_dir', '-')} | {ps} |")
    return L


def main():
    out = {}
    L = ['# chi2-realworld: frozen t1-tuned chi2 x0.25 gate on the real-world Monado data - results (cr_analyze.py)\n']
    L += ['## Run validity (real-world rule + Amendment-2 frame rule +-0 + chi2 delta present in launch.log)\n',
          '| sequence | method | runs | valid | fallbacks | late | n_in_core | pose rule fail | frame rule fail (frames lost) | chi2 delta ok |',
          '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|']
    for s in SEQS:
        for m in METH:
            V = VAL[s][m]
            L.append(f"| {s} | {LAB[m]} | {len(V)} | {sum(r['valid'] for r in V.values())} | {sum(r['fb'] for r in V.values())} | "
                     f"{sum(r['late'] for r in V.values())} | {sum(r['in_core'] for r in V.values())} | {sum(1 for r in V.values() if not r['pose_rule'])} | "
                     f"{sum(1 for r in V.values() if not r['frames_rule'])} ({sum(r['expected'] - r['frames'] for r in V.values())}) | "
                     f"{sum(1 for r in V.values() if r['delta_ok'])} |")
    bad = [f"{s} {m} run_{i:02d}" for s in SEQS for m in METH for i in IDX if not VAL[s][m].get(i, {}).get('valid')]
    badd = [f"{s} {LAB[m]} run_{i:02d} ({VAL[s][m].get(i, {}).get('status', 'missing')}, {VAL[s][m].get(i, {}).get('traj', 0)} poses, frames "
            f"{VAL[s][m].get(i, {}).get('frames', 0)}/{VAL[s][m].get(i, {}).get('expected', '?')})" for s in SEQS for m in METH for i in IDX
            if not VAL[s][m].get(i, {}).get('valid')]
    open(TAB + '/invalid.txt', 'w').write('\n'.join(bad) + ('\n' if bad else ''))
    L.append('\nInvalid runs (excluded pairwise from the primary statistics): ' + ('; '.join(badd) if badd else 'none') + '\n')
    out['invalid_runs'] = badd
    # md5 identity: own variants vs their base (expected to differ: the gate changes the filter)
    L.append('Trajectory md5 identical to the base method at the same offset: ' + ', '.join(
        f"{s} {v}: {sum(1 for i in IDX if VAL[s][v].get(i, {}).get('md5') and VAL[s][v][i]['md5'] == VAL[s][b].get(i, {}).get('md5'))}/10"
        for s in SEQS for v, b in (('ovchi_best', 'openvins'), ('sf1_chibest', 'sens_fix1'))) + '\n')
    # per-sequence ATE
    L += ['\n## ATE RMSE per sequence (posyaw, m): geometric mean over the valid runs (failures capped at 10 m) / median / failures > 1 m\n',
          '| sequence | ' + ' | '.join(LAB[m] for m in METH) + ' |', '|---|' + '--:|' * len(METH)]
    summ = {}
    for s in SEQS:
        cells = []
        for m in METH:
            v = [ATE[s][m][i] for i in IDX if i in ATE[s][m] and VAL[s][m].get(i, {}).get('valid')]
            if not v:
                cells.append('-'); continue
            f = sum(1 for x in v if x > FAIL)
            summ[f'{s}:{m}'] = dict(gm=gmean(v), med=float(np.median([min(x, CAP) for x in v])), fails=f, n=len(v), min=float(min(v)), max=float(max(v)))
            cells.append(f"{gmean(v):.3f} / {np.median([min(x, CAP) for x in v]):.3f} / {f}" + (f' (n={len(v)})' if len(v) != 10 else ''))
        L.append(f'| {s} {SEQNAME[s]} | ' + ' | '.join(cells) + ' |')
    out['summary'] = summ
    # RPE
    L += ['\n## RPE (mean translational error, shortest savior-eval sub-length; geometric mean over valid non-failed runs)\n',
          '| sequence | ' + ' | '.join(LAB[m] for m in METH) + ' |', '|---|' + '--:|' * len(METH)]
    for s in SEQS:
        cells = []
        for m in METH:
            v = [RPE[s][m][i] for i in IDX if i in RPE[s][m] and VAL[s][m].get(i, {}).get('valid') and ATE[s][m][i] <= FAIL and math.isfinite(RPE[s][m][i])]
            cells.append(f'{math.exp(np.mean(np.log(v))):.4f} (n={len(v)})' if v else '-')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    # failures
    L += ['\n## Failures (ATE > threshold), valid runs: person group / static\n', '| method | > 0.5 m | > 1 m (protocol) | > 2 m | static > 1 m |', '|---|--:|--:|--:|--:|']
    for m in METH:
        c = [fails(ATE, m, PERSON, t) for t in (0.5, 1.0, 2.0)] + [fails(ATE, m, STATIC, 1.0)]
        L.append(f'| {LAB[m]} | ' + ' | '.join(f'{a}/{n}' for a, n in c) + ' |')
    # paired
    res = run_comps(False)
    L += table(res, 'Paired ATE comparisons (primary: invalid runs excluded pairwise). GM ratio - 1 [%], run-level bootstrap 95 % CI, Wilcoxon p '
                    '(Holm within group x reference over the chi2 comparisons); sequence level: two-stage cluster bootstrap, exact sign-flip (k = 3: min p = 0.25)')
    out['paired'] = {f'{g}|{A}|{B}': r for (g, A, B), r in res.items()}
    resall = run_comps(True)
    out['paired_include_all'] = {f'{g}|{A}|{B}': r for (g, A, B), r in resall.items()}
    rr = run_comps(False, RPE, rpe=True)
    L += table(rr, 'Paired RPE comparisons (secondary; pairs where neither run fails)')
    out['paired_rpe'] = {f'{g}|{A}|{B}': r for (g, A, B), r in rr.items()}
    # sensitivity
    L += ['\n## Sensitivity (person group, run-level GM [%])\n', '| A vs B | cap 2 m | cap 10 m | cap 50 m | failures excluded (> 1 m) | include-all (10 m) |',
          '|---|--:|--:|--:|--:|--:|']
    for A, B in COMPS[:4]:
        cells = []
        for cap in (2.0, 10.0, 50.0, 'excl'):
            r = analyse(ATE, A, B, PERSON, cap)
            cells.append(f"{r['gm']:+.1f} (n={r['n']})" if r else '-')
        r = analyse(ATE, A, B, PERSON, include_all=True)
        cells.append(f"{r['gm']:+.1f} (n={r['n']})" if r else '-')
        L.append(f'| {LAB[A]} vs {LAB[B]} | ' + ' | '.join(cells) + ' |')
    # decision rule
    t1r = res.get(('person (MIO13+15+16)', 'ovchi_best', 'openvins'))
    t2r = res.get(('person (MIO13+15+16)', 'ovchi_best', 'sens_fix1'))
    if not (t1r and t2r):
        open(TAB + '/results.md', 'w').write('\n'.join(L) + '\n'); print('\n'.join(L)); print('NO DECISION: own runs missing'); return
    fo, no = fails(ATE, 'ovchi_best', PERSON)
    fs_, ns = fails(ATE, 'sens_fix1', PERSON)
    T1 = bool(t1r and t1r['gm'] < 0 and t1r['ci'][1] < 0)
    T2 = bool(t2r and (t2r['gm'] / 100 + 1) <= 1.0 and fo <= fs_ + 2)
    verdict = 'transfers' if (T1 and T2) else 'does not transfer'
    dec = dict(T1=dict(gm_pct=t1r['gm'], ci=t1r['ci'], n=t1r['n'], holds=T1),
               T2=dict(gm_ratio=t2r['gm'] / 100 + 1, gm_pct=t2r['gm'], ci=t2r['ci'], fails_ovchi=f'{fo}/{no}', fails_savior=f'{fs_}/{ns}',
                       fails_ok=fo <= fs_ + 2, holds=T2), verdict=verdict)
    out['decision'] = dec
    L += ['\n## DECISION_RULE.txt (pre-registered, md5 ad578908...)\n',
          f"- T1 ovchi_best vs OpenVINS, person group: GM {t1r['gm']:+.1f} % [{t1r['ci'][0]:+.1f}, {t1r['ci'][1]:+.1f}] (n={t1r['n']}) -> "
          f"{'HOLDS' if T1 else 'FAILS'} (needs GM < 0 and CI excluding 0)",
          f"- T2 ovchi_best vs SAVIOR, person group: GM ratio {t2r['gm'] / 100 + 1:.3f} ({t2r['gm']:+.1f} % [{t2r['ci'][0]:+.1f}, {t2r['ci'][1]:+.1f}]); "
          f"failures > 1 m {fo}/{no} vs SAVIOR {fs_}/{ns} (limit {fs_ + 2}) -> {'HOLDS' if T2 else 'FAILS'} (needs ratio <= 1.0 and failures <= SAVIOR + 2)",
          f'- **Verdict: the tuned-threshold result {verdict.upper()} to real data.**']
    open(TAB + '/results.md', 'w').write('\n'.join(L) + '\n')
    json.dump(json.loads(json.dumps(out, default=lambda o: sorted(o) if isinstance(o, set) else float(o))), open(TAB + '/results.json', 'w'), indent=1)
    with open(TAB + '/per_run.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['seq', 'method', 'run', 'offset_s', 'ate_m', 'rpe_m', 'valid', 'poses', 'frames', 'expected'])
        for s in SEQS:
            for m in METH:
                for i in IDX:
                    v = VAL[s][m].get(i, {})
                    w.writerow([s, m, i, f'{0.2 * (i - 1):.1f}', ATE[s][m].get(i, ''), RPE[s][m].get(i, ''), v.get('valid', 0), v.get('traj', ''),
                                v.get('frames', ''), v.get('expected', '')])
    print('\n'.join(L))


if __name__ == '__main__':
    main()
