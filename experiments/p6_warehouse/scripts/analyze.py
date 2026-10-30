#!/usr/bin/env python3
"""P6 SAVIOR-Warehouse analysis: method tables, failure rates, paired statistics (vs openvins, vs savior_none, key
comparisons), per-level / L2+L3 pooling with Holm correction, feature budget, figures. Adapted from P5 analyze.py.
Run in the savior image after eval_all.sh (and diag_p6.py / offline_eval_wh.py).

python3 analyze.py -> results/p6_warehouse/{tables,figures}/
"""
import csv
import glob
import json
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from scipy import stats  # noqa: E402

R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
W = '/home/sasa/workspace/savior_ws/data/warehouse'
OUT_T, OUT_F = R + '/tables', R + '/figures'
os.makedirs(OUT_T, exist_ok=True)
os.makedirs(OUT_F, exist_ok=True)
SCENES = ['aisles', 'hall']
LEVELS = ['L0', 'L1', 'L2', 'L3']
SEQS = [f'{s}_t1_{l}' for s in SCENES for l in LEVELS]
METHODS = ['openvins', 'savior_none', 'oracle_moving', 'oracle_class_naive', 'yolo_naive', 'yolo_p2', 'yolo_p4',
           'yolo_p4_nointer', 'yolo_coco_person_p4', 'yolo_p6']
EXTRA = ['oracle_moving_warp', 'oracle_moving_ext', 'yolo_p4_noext']
ALLM = METHODS + EXTRA
SHORT = {'openvins': 'OV', 'savior_none': 'none', 'oracle_moving': 'orc_mov', 'oracle_class_naive': 'orc_naive',
         'yolo_naive': 'y_naive', 'yolo_p2': 'y_p2', 'yolo_p4': 'y_p4', 'yolo_p4_nointer': 'y_p4_noint',
         'yolo_coco_person_p4': 'coco_p4', 'yolo_p6': 'y_p6', 'oracle_moving_warp': 'orc_mov_warp', 'oracle_moving_ext': 'orc_mov_ext', 'yolo_p4_noext': 'y_p4_noext'}
FAIL_M = float(os.environ.get('FAIL_M', '1.0'))   # ATE RMSE above this = VIO failure (see report: ~1 % of the 89-96 m path)
CAP_M = 10.0
IDX = list(range(1, 11))
COL = {'openvins': '#2a78d6', 'savior_none': '#7f7f7f', 'oracle_moving': '#1baf7a', 'oracle_class_naive': '#eda100',
       'yolo_naive': '#6250d6', 'yolo_p2': '#e87ba4', 'yolo_p4': '#e34948', 'yolo_p4_nointer': '#008300',
       'yolo_coco_person_p4': '#8c564b', 'yolo_p6': '#d62728', 'oracle_moving_warp': '#0b6b4a', 'oracle_moving_ext': '#7fd8b0', 'yolo_p4_noext': '#f2a0a0'}


def load(seq, m):
    fn = f'{R}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if os.path.isfile(fn):
        s = yaml.safe_load(open(fn))
        for t in s.get('trials', []):
            idx = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                out[idx] = dict(ate=math.inf, rot=math.inf, rpe=math.inf, rpe_rot=math.inf, fail=True)
                continue
            ks = sorted(t['rpe'].keys(), key=float)
            ate = t['ate']['trans_m']['rmse']
            out[idx] = dict(ate=ate, rot=t['ate']['rot_deg']['rmse'], rpe=t['rpe'][ks[0]]['trans_m']['mean'],
                            rpe_rot=t['rpe'][ks[0]]['rot_deg']['mean'], rpe_len=ks[0], fail=ate > FAIL_M)
    for rd in glob.glob(f'{R}/{seq}/{m}/run_*'):
        i = int(rd.rsplit('_', 1)[1])
        if i not in out and i in IDX:
            out[i] = dict(ate=math.inf, rot=math.inf, rpe=math.inf, rpe_rot=math.inf, fail=True)
    return {i: v for i, v in out.items() if i in IDX}


def vec(d, key):
    return np.array([d[i][key] if i in d else np.nan for i in IDX], float)


def wil(x):
    x = x[np.isfinite(x)]
    x = x[x != 0]
    if x.size < 2:
        return math.nan
    return float(stats.wilcoxon(x, alternative='two-sided', mode='exact' if x.size <= 25 else 'approx').pvalue)


def sign_p(x):
    x = x[np.isfinite(x)]
    p, n = int((x > 0).sum()), int((x < 0).sum())
    return float(stats.binomtest(p, p + n, 0.5).pvalue) if p + n else math.nan


def boot(x, n=20000, seed=0, f=np.mean):
    x = x[np.isfinite(x)]
    if x.size < 2:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    b = f(rng.choice(x, (n, x.size)), axis=1)
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(np.where(np.isnan(ps), 2, ps))
    adj = np.full_like(ps, np.nan)
    run = 0.0
    m = int(np.isfinite(ps).sum())
    for r, i in enumerate(o):
        if not np.isfinite(ps[i]):
            continue
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


D = {s: {m: load(s, m) for m in ALLM} for s in SEQS}
seqs_avail = [s for s in SEQS if D[s]['openvins']]


def fmt(x, nd=3):
    return '-' if x is None or (isinstance(x, float) and not np.isfinite(x)) else f'{x:.{nd}f}'


# ------------------------------------------------------------------ 1. method table
def method_table():
    rows = []
    for s in seqs_avail:
        for m in ALLM:
            d = D[s][m]
            if not d:
                continue
            a = vec(d, 'ate')
            f = np.array([d[i]['fail'] if i in d else False for i in IDX])
            have = np.array([i in d for i in IDX])
            ok = have & ~f
            g = a[ok]
            rows.append(dict(seq=s, method=m, n=int(have.sum()), n_fail=int(f.sum()),
                             ate_mean=float(g.mean()) if g.size else math.nan,
                             ate_median_all=float(np.median(np.where(np.isinf(a[have]), 1e3, a[have]))),
                             ate_median_ok=float(np.median(g)) if g.size else math.nan,
                             ate_std=float(g.std(ddof=1)) if g.size > 1 else math.nan,
                             rot_median=float(np.median(vec(d, 'rot')[ok])) if g.size else math.nan,
                             rpe_median=float(np.median(vec(d, 'rpe')[ok])) if g.size else math.nan,
                             rpe_rot_median=float(np.median(vec(d, 'rpe_rot')[ok])) if g.size else math.nan,
                             per=[None if not np.isfinite(x) else round(float(x), 4) for x in a]))
    with open(f'{OUT_T}/methods.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['seq', 'method', 'n', 'n_fail', 'ate_mean_ok', 'ate_std_ok', 'ate_median_all', 'ate_median_ok',
                    'rot_deg_median_ok', 'rpe10m_m_median_ok', 'rpe10m_deg_median_ok'] + [f'ate_run{i:02d}' for i in IDX])
        for r in rows:
            w.writerow([r['seq'], r['method'], r['n'], r['n_fail'], r['ate_mean'], r['ate_std'], r['ate_median_all'],
                        r['ate_median_ok'], r['rot_median'], r['rpe_median'], r['rpe_rot_median']] + r['per'])
    L = [f'# P6 method table: ATE (posyaw, full sequence) translation RMSE [m] over 10 start offsets; failure = ATE > {FAIL_M} m '
         '(or no estimate). "ok" columns over converged runs only. RPE = mean over ~9.6 m sub-trajectories (shortest rpg length).\n',
         '| seq | method | n | fail | ATE median all | ATE median ok | mean ok | std ok | rot [deg] med ok | RPE [m] med ok | RPE [deg] med ok |',
         '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    for r in rows:
        L.append(f"| {r['seq']} | {r['method']} | {r['n']} | {r['n_fail']} | {fmt(r['ate_median_all'])} | {fmt(r['ate_median_ok'])} | "
                 f"{fmt(r['ate_mean'])} | {fmt(r['ate_std'])} | {fmt(r['rot_median'], 2)} | {fmt(r['rpe_median'])} | {fmt(r['rpe_rot_median'], 2)} |")
    open(f'{OUT_T}/methods.md', 'w').write('\n'.join(L) + '\n')
    for key, title, nd in (('ate_median_all', 'median ATE [m] over all 10 offsets (failures = +inf), [n_fail]', 3),
                           ('rot_median', 'median ATE rotation [deg] over converged runs', 2),
                           ('rpe_median', 'median RPE (9.6 m) [m] over converged runs', 3)):
        ms = [m for m in ALLM if any(D[s][m] for s in seqs_avail)]
        L = [f'# {title}\n', '| seq | ' + ' | '.join(SHORT[m] for m in ms) + ' |', '|---|' + '--:|' * len(ms)]
        tex = ['\\begin{tabular}{l' + 'r' * len(ms) + '}', '\\toprule',
               'seq & ' + ' & '.join(SHORT[m].replace('_', '\\_') for m in ms) + ' \\\\', '\\midrule']
        for s in seqs_avail:
            cells, tcells = [], []
            for m in ms:
                rr = [r for r in rows if r['seq'] == s and r['method'] == m]
                if not rr:
                    cells.append('-'); tcells.append('--')
                    continue
                r = rr[0]
                v = r[key]
                cells.append(fmt(v, nd) + (f" [{r['n_fail']}]" if r['n_fail'] and key == 'ate_median_all' else ''))
                tcells.append(fmt(v, nd) + (f"$^{{{r['n_fail']}}}$" if r['n_fail'] and key == 'ate_median_all' else ''))
            L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
            tex.append(s.replace('_', '\\_') + ' & ' + ' & '.join(tcells) + ' \\\\')
        tex += ['\\bottomrule', '\\end{tabular}']
        nm = {'ate_median_all': 'median_matrix', 'rot_median': 'median_rot_matrix', 'rpe_median': 'median_rpe_matrix'}[key]
        open(f'{OUT_T}/{nm}.md', 'w').write('\n'.join(L) + '\n')
        open(f'{OUT_T}/{nm}.tex', 'w').write('\n'.join(tex) + '\n')
    return rows


def fail_table():
    ms = [m for m in ALLM if any(D[s][m] for s in seqs_avail)]
    L = [f'# failure rate (ATE > {FAIL_M} m or no estimate) [failed/n]\n', '| seq | ' + ' | '.join(SHORT[m] for m in ms) + ' |',
         '|---|' + '--:|' * len(ms)]
    tot = {m: [0, 0] for m in ms}
    for s in seqs_avail:
        cells = []
        for m in ms:
            d = D[s][m]
            if not d:
                cells.append('-')
                continue
            f = sum(1 for v in d.values() if v['fail'])
            tot[m][0] += f
            tot[m][1] += len(d)
            cells.append(f'{f}/{len(d)}')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    L.append('| total | ' + ' | '.join(f'{tot[m][0]}/{tot[m][1]}' for m in ms) + ' |')
    open(f'{OUT_T}/failures.md', 'w').write('\n'.join(L) + '\n')


# ------------------------------------------------------------------ 2. paired statistics
def lr(a, b):
    a = np.where(np.isinf(a), CAP_M, np.minimum(a, CAP_M))
    b = np.where(np.isinf(b), CAP_M, np.minimum(b, CAP_M))
    return np.log(a / b)


KEY_PAIRS = [('oracle_moving', 'oracle_class_naive'), ('yolo_p4', 'yolo_naive'), ('yolo_p2', 'yolo_naive'),
             ('yolo_p4', 'yolo_p2'), ('yolo_p4', 'yolo_p4_nointer'), ('yolo_p4', 'oracle_moving'),
             ('yolo_naive', 'oracle_class_naive'), ('yolo_coco_person_p4', 'yolo_p4'), ('yolo_p4_noext', 'yolo_p4'),
             ('oracle_moving_warp', 'oracle_moving'), ('yolo_p4_nointer', 'yolo_naive'), ('yolo_p2', 'oracle_moving'),
             ('yolo_p6', 'yolo_naive'), ('yolo_p6', 'yolo_p4'), ('yolo_p6', 'yolo_p2'), ('yolo_p6', 'oracle_moving'),
             ('yolo_p6', 'yolo_p4_nointer'), ('oracle_moving_ext', 'oracle_moving_warp'), ('oracle_moving_ext', 'oracle_moving'),
             ('oracle_moving_ext', 'oracle_class_naive'), ('yolo_naive', 'oracle_moving'), ('yolo_naive', 'oracle_moving_ext'),
             ('yolo_p2', 'oracle_moving_ext'), ('yolo_p4', 'oracle_moving_ext')]


def groups():
    g = [(s,) for s in seqs_avail]
    for lev in LEVELS:
        x = tuple(s for s in seqs_avail if s.endswith(lev))
        if x:
            g.append(x)
    g.append(tuple(s for s in seqs_avail if s.endswith('L2') or s.endswith('L3')))
    g.append(tuple(s for s in seqs_avail if not s.endswith('L0')))
    return g


def gname(g):
    if len(g) == 1:
        return g[0]
    levs = sorted({s[-2:] for s in g})
    return 'all_' + '+'.join(levs)


def paired(metric='ate', okonly=False):
    out = []
    pairs = [(m, 'openvins') for m in ALLM if m != 'openvins'] + \
            [(m, 'savior_none') for m in ALLM if m not in ('openvins', 'savior_none')] + KEY_PAIRS
    for g in groups():
        for m, ref in pairs:
            x, fa, fb = [], 0, 0
            for s in g:
                if not D[s].get(m) or not D[s].get(ref):
                    continue
                a, b = vec(D[s][m], metric), vec(D[s][ref], metric)
                ok = ~(np.isnan(a) | np.isnan(b))
                fa_ = np.array([D[s][m].get(i, {}).get('fail', False) for i in IDX])
                fb_ = np.array([D[s][ref].get(i, {}).get('fail', False) for i in IDX])
                if okonly:
                    ok &= ~fa_ & ~fb_
                x += list(lr(a[ok], b[ok]))
                fa += int(fa_[ok].sum())
                fb += int(fb_[ok].sum())
            x = np.array(x)
            if x.size < 2:
                continue
            ci = boot(x)
            out.append(dict(group=gname(g), method=m, ref=ref, n=int(x.size), gm_ratio_pct=float(100 * (math.exp(x.mean()) - 1)),
                            ci_pct=[float(100 * (math.exp(ci[0]) - 1)), float(100 * (math.exp(ci[1]) - 1))],
                            median_ratio_pct=float(100 * (math.exp(np.median(x)) - 1)), wins=int((x < 0).sum()),
                            losses=int((x > 0).sum()), wil=wil(x), sign=sign_p(x), fail_m=fa, fail_ref=fb))
    # Holm families on the pooled L2+L3 group: (A) every method vs openvins, (B) key comparisons; and per level (A)
    for grp in ('all_L2+L3', 'all_L0', 'all_L1', 'all_L2', 'all_L3', 'all_L1+L2+L3'):
        fam = [r for r in out if r['group'] == grp and r['ref'] == 'openvins']
        for r, p in zip(fam, holm([r['wil'] for r in fam])):
            r['holm'] = float(p)
        fam = [r for r in out if r['group'] == grp and (r['method'], r['ref']) in KEY_PAIRS]
        for r, p in zip(fam, holm([r['wil'] for r in fam])):
            r['holm'] = float(p)
    L = [f'# P6 paired statistics, metric={metric}: per start offset log(method/ref) (failures / >{CAP_M:.0f} m capped at {CAP_M:.0f} m); '
         'gm = geometric-mean ratio - 1 (negative = method better), 95 % bootstrap CI, Wilcoxon signed-rank (exact n <= 25), '
         'sign test; holm = Holm-adjusted Wilcoxon p within the pooled group over the family "every method vs openvins" or the '
         'family "key comparisons"\n',
         '| group | method | ref | n | gm ratio | 95% CI | median ratio | wins/losses | Wilcoxon p | sign p | holm | fails m/ref |',
         '|---|---|---|--:|--:|---|--:|--:|--:|--:|--:|--:|']
    for r in out:
        L.append(f"| {r['group']} | {r['method']} | {r['ref']} | {r['n']} | {r['gm_ratio_pct']:+.1f} % | "
                 f"[{r['ci_pct'][0]:+.1f}, {r['ci_pct'][1]:+.1f}] | {r['median_ratio_pct']:+.1f} % | {r['wins']}/{r['losses']} | "
                 f"{r['wil']:.4f} | {r['sign']:.4f} | " + (f"{r['holm']:.4f}" if 'holm' in r else '-') + f" | {r['fail_m']}/{r['fail_ref']} |")
    tag = '_okonly' if okonly else ''
    open(f'{OUT_T}/paired_{metric}{tag}.md', 'w').write('\n'.join(L) + '\n')
    json.dump(out, open(f'{OUT_T}/paired_{metric}{tag}.json', 'w'), indent=1)
    return out


def pooled_table(P, Pok):
    """compact: pooled groups x (method vs openvins) and key comparisons."""
    L = ['# pooled ATE effects (geometric-mean ratio - 1, 95 % bootstrap CI, Wilcoxon p, Holm p); converged-only in the last column\n']
    for grp in ('all_L0', 'all_L1', 'all_L2', 'all_L3', 'all_L2+L3'):
        L += [f'\n## {grp}\n', '| method | ref | n | ATE ratio | 95% CI | wins/losses | p | Holm p | fails m/ref | converged-only ratio (p) |',
              '|---|---|--:|--:|---|--:|--:|--:|--:|--:|']
        for r in P:
            if r['group'] != grp or not (r['ref'] == 'openvins' or (r['method'], r['ref']) in KEY_PAIRS):
                continue
            q = [x for x in Pok if x['group'] == grp and x['method'] == r['method'] and x['ref'] == r['ref']]
            qs = f"{q[0]['gm_ratio_pct']:+.1f} % ({q[0]['wil']:.3f})" if q else '-'
            L.append(f"| {r['method']} | {r['ref']} | {r['n']} | {r['gm_ratio_pct']:+.1f} % | [{r['ci_pct'][0]:+.1f}, {r['ci_pct'][1]:+.1f}] | "
                     f"{r['wins']}/{r['losses']} | {r['wil']:.4f} | " + (f"{r['holm']:.4f}" if 'holm' in r else '-') +
                     f" | {r['fail_m']}/{r['fail_ref']} | {qs} |")
    open(f'{OUT_T}/pooled.md', 'w').write('\n'.join(L) + '\n')


# ------------------------------------------------------------------ 3. feature budget
def feature_budget():
    rows = []
    for s in seqs_avail:
        for m in ALLM:
            vals = []
            for rd in sorted(glob.glob(f'{R}/{s}/{m}/run_*')):
                fn = f'{rd}/feature_stats.csv'
                if not os.path.isfile(fn):
                    continue
                a = np.genfromtxt(fn, delimiter=',', names=True)
                if a.size == 0:
                    continue
                kept = a['n_tracked'] + a['n_new']
                c0 = a['cam_id'] == 0
                nfr = max(1, int(c0.sum()))
                vals.append((kept.sum(), kept[c0].sum() / nfr, kept[~c0].sum() / nfr, a['n_rejected_mask'].sum(),
                             float((a['relaxed'] > 0).mean())))
            if not vals:
                continue
            v = np.array(vals)
            rows.append(dict(seq=s, method=m, runs=len(vals), kept_total=float(np.mean(v[:, 0])), kept_c0=float(np.mean(v[:, 1])),
                             kept_c1=float(np.mean(v[:, 2])), rejected_total=float(np.mean(v[:, 3])), relaxed_frac=float(np.mean(v[:, 4]))))
    base = {r['seq']: r['kept_total'] for r in rows if r['method'] == 'openvins'}
    for r in rows:
        r['kept_vs_openvins_pct'] = 100 * (r['kept_total'] / base[r['seq']] - 1) if r['seq'] in base else math.nan
    with open(f'{OUT_T}/feature_budget.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ms = [m for m in ALLM if any(r['method'] == m for r in rows)]
    L = ['# feature budget: cumulative kept features (tracked + new, both cameras, whole run, mean over runs) relative to openvins [%], '
         '(kept cam0 per frame)\n', '| seq | ' + ' | '.join(SHORT[m] for m in ms) + ' |', '|---|' + '--:|' * len(ms)]
    for s in seqs_avail:
        cells = []
        for m in ms:
            rr = [r for r in rows if r['seq'] == s and r['method'] == m]
            cells.append(f"{rr[0]['kept_vs_openvins_pct']:+.1f} % ({rr[0]['kept_c0']:.1f})" if rr else '-')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    open(f'{OUT_T}/feature_budget.md', 'w').write('\n'.join(L) + '\n')
    return rows


# ------------------------------------------------------------------ 4. figures
def fig_box():
    ms = [m for m in ALLM if any(D[s][m] for s in seqs_avail)]
    fig, axs = plt.subplots(2, 4, figsize=(19, 8), squeeze=False)
    for i, sc in enumerate(SCENES):
        for j, lev in enumerate(LEVELS):
            ax = axs[i][j]
            s = f'{sc}_t1_{lev}'
            if s not in seqs_avail:
                ax.axis('off')
                continue
            for k, m in enumerate(ms):
                d = vec(D[s][m], 'ate') if D[s][m] else np.array([])
                d = d[~np.isnan(d)] if d.size else d
                if not d.size:
                    continue
                dc = np.clip(np.where(np.isinf(d), 50, d), 0.02, 50)
                ax.boxplot([dc], positions=[k], widths=0.6, showfliers=False, patch_artist=True,
                           boxprops=dict(facecolor=COL[m] + '44', edgecolor=COL[m]), medianprops=dict(color='#111'))
                ax.scatter(np.full(dc.size, k) + np.linspace(-0.2, 0.2, dc.size), dc, s=9, color=COL[m], zorder=3)
            ax.set_yscale('log')
            ax.axhline(FAIL_M, color='k', ls=':', lw=0.8)
            ax.set_xticks(range(len(ms)))
            ax.set_xticklabels([SHORT[m] for m in ms], fontsize=7, rotation=90)
            ax.set_title(s, fontsize=10)
            ax.set_ylabel('ATE RMSE [m] (log; failure line dotted)')
            ax.grid(axis='y', alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/ate_boxplots.png', dpi=130)
    plt.close(fig)


def fig_trend(P):
    ms = [m for m in ALLM if m != 'openvins' and any(D[s][m] for s in seqs_avail)]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for j, m in enumerate(ms):
        ys, lo, hi = [], [], []
        for lev in LEVELS:
            r = [x for x in P if x['group'] == f'all_{lev}' and x['method'] == m and x['ref'] == 'openvins']
            ys.append(r[0]['gm_ratio_pct'] if r else np.nan)
            lo.append(r[0]['ci_pct'][0] if r else np.nan)
            hi.append(r[0]['ci_pct'][1] if r else np.nan)
        ys, lo, hi = np.array(ys), np.array(lo), np.array(hi)
        x = np.arange(4) + 0.05 * (j - len(ms) / 2)
        ax.errorbar(x, ys, yerr=[ys - lo, hi - ys], marker='o', ms=4, capsize=2, color=COL[m], label=m)
    ax.axhline(0, color='k', lw=0.8)
    ax.set_xticks(range(4))
    ax.set_xticklabels(LEVELS)
    ax.set_ylabel('ATE vs openvins: geometric-mean ratio - 1 [%]\n(negative = better; failures capped at 10 m), 95 % CI')
    ax.set_xlabel('SAVIOR-Warehouse dynamic level (aisles + hall pooled, n = 20 per point)')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/trend_levels.png', dpi=140)
    plt.close(fig)


def fig_budget(rows, mt):
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, levs in zip(axs, (('L0', 'L1'), ('L2', 'L3'))):
        for r in rows:
            if r['seq'][-2:] not in levs:
                continue
            q = [x for x in mt if x['seq'] == r['seq'] and x['method'] == r['method']]
            if not q:
                continue
            y = min(q[0]['ate_median_all'], 50)
            ax.scatter(r['kept_vs_openvins_pct'], y, color=COL[r['method']], marker='o' if r['seq'].startswith('hall') else 's', s=30,
                       label=r['method'])
        h, lab = ax.get_legend_handles_labels()
        u = dict(zip(lab, h))
        ax.legend(u.values(), u.keys(), fontsize=6)
        ax.set_yscale('log')
        ax.set_xlabel('cumulative kept features vs openvins [%]')
        ax.set_ylabel('median ATE [m] (log; o hall, s aisles)')
        ax.set_title('levels ' + '+'.join(levs))
        ax.grid(alpha=0.3, which='both')
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/feature_budget_vs_ate.png', dpi=140)
    plt.close(fig)


# ------------------------------------------------------------------ 5. share vs gain (+ P5 points)
def share_vs_gain(P):
    rows = []
    for s in seqs_avail:
        cov = np.genfromtxt(f'{W}/raw/{s}/coverage.csv', delimiter=',', names=True)
        rec = dict(dataset='warehouse', seq=s, px_dyn=float(cov['moving'].mean()), px_potential=float(cov['potential'].mean()))
        ds = sorted(glob.glob(f'{R}/{s}/diag_openvins/run_*/diag_p6.yaml'))
        if ds:
            v = [yaml.safe_load(open(f)) for f in ds]
            rec['n_diag_runs'] = len(v)
            rec['kept_dyn_cam0'] = float(np.mean([x['frac_kept_obs_on_human_cam0'] for x in v]))
            rec['kept_static_potential_cam0'] = float(np.mean([x['frac_kept_obs_on_static_potential_cam0'] for x in v]))
            rec['msckf_used_meas_dyn'] = float(np.mean([x['post_init']['frac_msckf_used_meas_human'] for x in v]))
            rec['msckf_used_meas_static_potential'] = float(np.mean([x['post_init']['frac_msckf_used_meas_static_potential'] for x in v]))
            rec['slam_update_meas_dyn'] = float(np.mean([x['post_init']['frac_slam_update_meas_human'] for x in v]))
            rec['chi2_reject_dyn'] = float(np.nanmean([x['post_init']['human'].get('msckf_chi2_reject_rate') or np.nan for x in v]))
            rec['chi2_reject_other'] = float(np.nanmean([x['post_init']['non_human'].get('msckf_chi2_reject_rate') or np.nan for x in v]))
            rec['chi2_reject_static_potential'] = float(np.nanmean([x['post_init']['static_potential'].get('msckf_chi2_reject_rate') or np.nan for x in v]))
        for m in ('oracle_moving', 'oracle_class_naive', 'yolo_p4', 'yolo_naive', 'yolo_p2', 'yolo_p6'):
            r = [x for x in P if x['group'] == s and x['method'] == m and x['ref'] == 'openvins']
            if r:
                rec[f'gain_{m}_pct'] = -r[0]['gm_ratio_pct']
                rec[f'p_{m}'] = r[0]['wil']
        rows.append(rec)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ('dataset', 'seq'), k))
    with open(f'{OUT_T}/share_vs_gain.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, keys)
        w.writeheader()
        w.writerows(rows)
    # P5 VIODE points (same definitions: diag_p5.py "human" = dynamic vehicle; oracle_dynamic = oracle moving)
    p5 = []
    fn = '/home/sasa/workspace/savior_ws/results/p5_viode/tables/share_vs_gain.csv'
    if os.path.isfile(fn):
        for r in csv.DictReader(open(fn)):
            if r.get('msckf_used_meas_dyn') and r.get('gain_oracle_dynamic_pct'):
                p5.append(dict(dataset='viode', seq=r['seq'], px_dyn=float(r['px_dyn']), kept_dyn_cam0=float(r['kept_dyn_cam0']),
                               msckf_used_meas_dyn=float(r['msckf_used_meas_dyn']), gain_oracle_moving_pct=float(r['gain_oracle_dynamic_pct']),
                               gain_yolo_p4_pct=float(r['gain_yolo_p4_pot_pct']) if r.get('gain_yolo_p4_pot_pct') else math.nan))
    out = {}
    for name, pts_rows in (('warehouse', rows), ('viode_p5', p5), ('combined', rows + p5)):
        for xk in ('px_dyn', 'kept_dyn_cam0', 'msckf_used_meas_dyn'):
            for yk in ('gain_oracle_moving_pct', 'gain_yolo_p4_pct'):
                pts = [(r[xk], r[yk]) for r in pts_rows if xk in r and yk in r and np.isfinite(r[yk])]
                if len(pts) >= 4:
                    x, y = np.array(pts).T
                    rho, p = stats.spearmanr(x, y)
                    out[f'{name}: {yk} ~ {xk}'] = dict(n=len(pts), spearman_rho=float(rho), p=float(p))
    yaml.safe_dump(out, open(f'{OUT_T}/share_vs_gain_corr.yaml', 'w'), sort_keys=False)
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
    for ax, xk, lab in zip(axs, ('px_dyn', 'kept_dyn_cam0', 'msckf_used_meas_dyn'),
                           ('GT moving-object pixel share [%]', 'kept cam0 features on moving objects [%] (openvins diag)',
                            'MSCKF-used measurements on moving objects [%] (openvins diag)')):
        for dset, mk, rr in (('warehouse', 'o', rows), ('viode', '^', p5)):
            for m, c in (('oracle_moving', COL['oracle_moving']), ('yolo_p4', COL['yolo_p4'])):
                pts = [(r[xk] * 100, r[f'gain_{m}_pct'], r['seq']) for r in rr if xk in r and f'gain_{m}_pct' in r and np.isfinite(r[f'gain_{m}_pct'])]
                if not pts:
                    continue
                ax.scatter([p[0] for p in pts], [p[1] for p in pts], marker=mk, color=c, s=34, alpha=0.85,
                           facecolors=c if dset == 'warehouse' else 'none', label=f'{m} ({dset})')
                if m == 'oracle_moving':
                    for p in pts:
                        ax.annotate(p[2].replace('_t1_', ' ').replace('parking_lot', 'PL').replace('city_day', 'CD').replace('city_night', 'CN'),
                                    (p[0], p[1]), fontsize=6, xytext=(3, 3), textcoords='offset points')
        ax.axhline(0, color='k', lw=0.8)
        ax.set_xscale('symlog', linthresh=1)
        ax.set_xlabel(lab)
        ax.set_ylabel('ATE gain vs openvins [%] (geometric mean, + = better)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/share_vs_gain.png', dpi=140)
    plt.close(fig)
    return rows, out


if __name__ == '__main__':
    rows = method_table()
    fail_table()
    P = paired('ate')
    Pok = paired('ate', okonly=True)
    paired('rpe')
    paired('rot')
    paired('rpe', okonly=True)
    pooled_table(P, Pok)
    fb = feature_budget()
    fig_box()
    fig_trend(P)
    fig_budget(fb, rows)
    share_vs_gain(P)
    print('sequences:', seqs_avail)
    print(open(f'{OUT_T}/median_matrix.md').read())
    print(open(f'{OUT_T}/failures.md').read())
