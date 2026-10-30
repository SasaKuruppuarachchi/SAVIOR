#!/usr/bin/env python3
"""P5 VIODE analysis: method tables, failure rates, paired statistics (vs openvins and vs savior_none), dynamic-level
trend, dynamic-share vs oracle-gain, figures. Run in the savior image after eval_all.sh (and diag_p5.py / offline_eval.py).

python3 analyze.py -> results/p5_viode/{tables,figures}/
"""
import csv
import glob
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from scipy import stats  # noqa: E402

R = '/home/sasa/workspace/savior_ws/results/p5_viode'
GT = '/home/sasa/workspace/savior_ws/data/viode/gt'
OUT_T, OUT_F = R + '/tables', R + '/figures'
os.makedirs(OUT_T, exist_ok=True)
os.makedirs(OUT_F, exist_ok=True)
ENVS = ['parking_lot', 'city_day', 'city_night']
LEVELS = ['none', 'low', 'mid', 'high']
SEQS = [f'{e}_{l}' for e in ENVS for l in LEVELS]
METHODS = ['openvins', 'savior_none', 'oracle_dynamic', 'oracle_all_vehicles', 'yolo_naive', 'yolo_full_p2',
           'yolo_p4_dyn', 'yolo_p4_pot', 'openvins+fast15', 'yolo_p4_dyn+fast15', 'yolo_p4_pot+fast15']
EXTRA = ['oracle_dynamic_warp']
FAIL_M = 1.0          # ATE RMSE above this = divergence / VIO failure (good runs: 0.03-0.4 m)
IDX = list(range(1, 11))
COL = {'openvins': '#2a78d6', 'savior_none': '#7f7f7f', 'oracle_dynamic': '#1baf7a', 'oracle_all_vehicles': '#eda100',
       'yolo_naive': '#6250d6', 'yolo_full_p2': '#e87ba4', 'yolo_p4_dyn': '#e34948', 'yolo_p4_pot': '#008300',
       'openvins+fast15': '#86b6ef', 'yolo_p4_dyn+fast15': '#f2a0a0', 'yolo_p4_pot+fast15': '#8fd18f',
       'oracle_dynamic_warp': '#0b6b4a'}


def load(seq, m):
    fn = f'{R}/{seq}/{m}/eval/eval_summary.yaml'
    out = {}
    if not os.path.isfile(fn):
        return out
    s = yaml.safe_load(open(fn))
    for t in s.get('trials', []):
        idx = int(t['name'].split('_')[1])
        if t.get('status') != 'ok':
            out[idx] = dict(ate=math.inf, rot=math.inf, rpe=math.inf, rpe_yaw=math.inf, fail=True, n=0)
            continue
        ks = sorted(t['rpe'].keys(), key=lambda k: float(str(k).split('_')[0]) if str(k).split('_')[0].replace('.', '').isdigit() else 0)
        k0 = ks[0]
        ate = t['ate']['trans_m']['rmse']
        out[idx] = dict(ate=ate, rot=t['ate']['rot_deg']['rmse'], rpe=t['rpe'][k0]['trans_m']['mean'],
                        rpe_yaw=t['rpe'][k0].get('yaw_deg', t['rpe'][k0].get('rot_deg', {})).get('mean', math.nan),
                        rpe_len=k0, fail=ate > FAIL_M, n=t.get('n_matched', 0))
    # runs that produced no estimate at all (missing in the eval) = failures
    for rd in glob.glob(f'{R}/{seq}/{m}/run_*'):
        i = int(rd.rsplit('_', 1)[1])
        if i not in out:
            out[i] = dict(ate=math.inf, rot=math.inf, rpe=math.inf, rpe_yaw=math.inf, fail=True, n=0)
    return out


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
    o = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


D = {s: {m: load(s, m) for m in METHODS + EXTRA} for s in SEQS}
seqs_avail = [s for s in SEQS if D[s]['openvins']]


# ------------------------------------------------------------------ 1. method table
def method_table():
    rows = []
    for s in seqs_avail:
        for m in METHODS + EXTRA:
            d = D[s][m]
            if not d:
                continue
            a = vec(d, 'ate')
            f = np.array([d[i]['fail'] if i in d else True for i in IDX])
            ok = np.isfinite(a) & ~f
            g = a[ok]
            rows.append(dict(seq=s, method=m, n=int(np.isfinite(a).sum() + np.isinf(a).sum()), n_fail=int(f[[i in d for i in IDX]].sum()),
                             ate_mean=float(g.mean()) if g.size else math.nan, ate_median_all=float(np.nanmedian(np.where(np.isinf(a), 1e3, a))),
                             ate_std=float(g.std(ddof=1)) if g.size > 1 else math.nan,
                             rot_mean=float(np.nanmean(vec(d, 'rot')[ok])) if g.size else math.nan,
                             rpe_mean=float(np.nanmean(vec(d, 'rpe')[ok])) if g.size else math.nan,
                             rpe_yaw_mean=float(np.nanmean(vec(d, 'rpe_yaw')[ok])) if g.size else math.nan,
                             per=[None if not np.isfinite(x) else round(float(x), 4) for x in a]))
    with open(f'{OUT_T}/methods.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['seq', 'method', 'n', 'n_fail', 'ate_mean_ok', 'ate_std_ok', 'ate_median_all', 'rot_deg_mean_ok',
                    'rpe_m_mean_ok', 'rpe_yaw_deg_mean_ok'] + [f'ate_run{i:02d}' for i in IDX])
        for r in rows:
            w.writerow([r['seq'], r['method'], r['n'], r['n_fail'], r['ate_mean'], r['ate_std'], r['ate_median_all'],
                        r['rot_mean'], r['rpe_mean'], r['rpe_yaw_mean']] + r['per'])
    L = ['# P5 VIODE method table: ATE (posyaw) translation RMSE [m] over 10 start offsets; "ok" = runs with ATE <= '
         f'{FAIL_M} m (others = divergence, counted in n_fail); median over all runs (failures = +inf)\n',
         '| seq | method | n | fail | ATE mean ok | std | median all | rot [deg] | RPE [m] |', '|---|---|--:|--:|--:|--:|--:|--:|--:|']
    for r in rows:
        L.append(f"| {r['seq']} | {r['method']} | {r['n']} | {r['n_fail']} | {r['ate_mean']:.3f} | {r['ate_std']:.3f} | "
                 f"{r['ate_median_all']:.3f} | {r['rot_mean']:.2f} | {r['rpe_mean']:.3f} |")
    open(f'{OUT_T}/methods.md', 'w').write('\n'.join(L) + '\n')
    # compact matrix (median over all runs) + LaTeX
    ms = [m for m in METHODS if any(D[s][m] for s in seqs_avail)]
    hdr = '| seq | ' + ' | '.join(ms) + ' |'
    L = ['# median ATE [m] over all 10 offsets (failures count as +inf), [n_fail]\n', hdr, '|---|' + '--:|' * len(ms)]
    tex = ['\\begin{tabular}{l' + 'r' * len(ms) + '}', '\\toprule', 'seq & ' + ' & '.join(m.replace('_', '\\_') for m in ms) + ' \\\\', '\\midrule']
    for s in seqs_avail:
        cells, tcells = [], []
        for m in ms:
            rr = [r for r in rows if r['seq'] == s and r['method'] == m]
            if not rr:
                cells.append('-'); tcells.append('--')
                continue
            r = rr[0]
            cells.append(f"{r['ate_median_all']:.3f}" + (f" [{r['n_fail']}]" if r['n_fail'] else ''))
            tcells.append(f"{r['ate_median_all']:.3f}" + (f"$^{{{r['n_fail']}}}$" if r['n_fail'] else ''))
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
        tex.append(s.replace('_', '\\_') + ' & ' + ' & '.join(tcells) + ' \\\\')
    tex += ['\\bottomrule', '\\end{tabular}']
    open(f'{OUT_T}/median_matrix.md', 'w').write('\n'.join(L) + '\n')
    open(f'{OUT_T}/median_matrix.tex', 'w').write('\n'.join(tex) + '\n')
    return rows


# ------------------------------------------------------------------ 2. paired statistics
def lr(a, b):
    """log ratio method/ref per pair; failures capped at 10 m so that a divergence is a large but finite loss."""
    a = np.where(np.isinf(a), 10.0, np.minimum(a, 10.0))
    b = np.where(np.isinf(b), 10.0, np.minimum(b, 10.0))
    return np.log(a / b)


def paired(metric='ate', okonly=False):
    out = []
    groups = [(s,) for s in seqs_avail]
    for lev in LEVELS:
        g = tuple(s for s in seqs_avail if s.endswith('_' + lev))
        if g:
            groups.append(g)
    dyn = tuple(s for s in seqs_avail if not s.endswith('_none'))
    groups.append(dyn)
    groups.append(tuple(s for s in seqs_avail if s.endswith('_mid') or s.endswith('_high')))
    names = {g: (g[0] if len(g) == 1 else ('all_' + g[0].split('_')[-1] if all(x.split('_')[-1] == g[0].split('_')[-1] for x in g)
                                           else ('dynamic(low+mid+high)' if g == dyn else 'mid+high'))) for g in groups}
    pairs = [(m, 'openvins') for m in METHODS + EXTRA if m != 'openvins'] + \
            [(m, 'savior_none') for m in METHODS + EXTRA if m not in ('openvins', 'savior_none', 'openvins+fast15')] + \
            [('yolo_p4_dyn+fast15', 'openvins+fast15'), ('yolo_p4_pot+fast15', 'openvins+fast15'),
             ('yolo_p4_dyn', 'yolo_naive'), ('yolo_p4_pot', 'yolo_naive'), ('yolo_p4_dyn', 'oracle_all_vehicles'),
             ('yolo_p4_pot', 'oracle_all_vehicles'), ('oracle_dynamic', 'oracle_all_vehicles'),
             ('yolo_p4_dyn', 'oracle_dynamic'), ('yolo_p4_pot', 'oracle_dynamic'), ('yolo_full_p2', 'yolo_naive'),
             ('oracle_dynamic_warp', 'oracle_dynamic')]
    for g in groups:
        for m, ref in pairs:
            x, fa, fb, av, bv = [], 0, 0, [], []
            for s in g:
                if not D[s].get(m) or not D[s].get(ref):
                    continue
                a, b = vec(D[s][m], metric), vec(D[s][ref], metric)
                ok = ~(np.isnan(a) | np.isnan(b))
                if okonly:   # accuracy when both converged: drop pairs where either run diverged
                    fa_ = np.array([D[s][m].get(i, {}).get('fail', True) for i in IDX])
                    fb_ = np.array([D[s][ref].get(i, {}).get('fail', True) for i in IDX])
                    ok &= ~fa_ & ~fb_
                x += list(lr(a[ok], b[ok]))
                av += list(a[ok]); bv += list(b[ok])
                fa += int(np.sum(a[ok] > FAIL_M)); fb += int(np.sum(b[ok] > FAIL_M))
            x = np.array(x)
            if x.size < 2:
                continue
            ci = boot(x)
            rec = dict(group=names[g], method=m, ref=ref, n=int(x.size), gm_ratio_pct=float(100 * (math.exp(x.mean()) - 1)),
                       ci_pct=[float(100 * (math.exp(ci[0]) - 1)), float(100 * (math.exp(ci[1]) - 1))],
                       median_ratio_pct=float(100 * (math.exp(np.median(x)) - 1)), wins=int((x < 0).sum()),
                       losses=int((x > 0).sum()), wil=wil(x), sign=sign_p(x), fail_m=fa, fail_ref=fb)
            out.append(rec)
    # Holm over the main family: pooled dynamic group, every method vs openvins
    fam = [r for r in out if r['group'] == 'dynamic(low+mid+high)' and r['ref'] == 'openvins']
    for r, p in zip(fam, holm([r['wil'] for r in fam])):
        r['holm'] = float(p)
    L = [f'# P5 paired statistics, metric={metric}: per start offset log(method/ref) (failures capped at 10 m); '
         'gm = geometric-mean ratio - 1 (negative = method better), 95 % bootstrap CI, Wilcoxon signed-rank (exact for n <= 25), '
         'sign test; holm = Holm-adjusted p over the family "every method vs openvins on the pooled dynamic sequences"\n',
         '| group | method | ref | n | gm ratio | 95% CI | median ratio | wins/losses | Wilcoxon p | sign p | holm | fails m/ref |',
         '|---|---|---|--:|--:|---|--:|--:|--:|--:|--:|--:|']
    for r in out:
        L.append(f"| {r['group']} | {r['method']} | {r['ref']} | {r['n']} | {r['gm_ratio_pct']:+.1f} % | "
                 f"[{r['ci_pct'][0]:+.1f}, {r['ci_pct'][1]:+.1f}] | {r['median_ratio_pct']:+.1f} % | {r['wins']}/{r['losses']} | "
                 f"{r['wil']:.4f} | {r['sign']:.4f} | " + (f"{r['holm']:.4f}" if 'holm' in r else '-') + f" | {r['fail_m']}/{r['fail_ref']} |")
    tag = '_okonly' if okonly else ''
    if okonly:
        L[0] = L[0].replace('(failures capped at 10 m)', '(ONLY pairs where neither run diverged)')
    open(f'{OUT_T}/paired_{metric}{tag}.md', 'w').write('\n'.join(L) + '\n')
    json.dump(out, open(f'{OUT_T}/paired_{metric}{tag}.json', 'w'), indent=1)
    return out


# ------------------------------------------------------------------ 3. figures
def fig_box():
    ms = [m for m in METHODS if any(D[s][m] for s in seqs_avail)]
    envs = [e for e in ENVS if any(s.startswith(e) for s in seqs_avail)]
    fig, axs = plt.subplots(len(envs), 4, figsize=(18, 3.6 * len(envs)), squeeze=False)
    for i, e in enumerate(envs):
        for j, lev in enumerate(LEVELS):
            ax = axs[i][j]
            s = f'{e}_{lev}'
            if s not in seqs_avail:
                ax.axis('off')
                continue
            data = [np.clip(vec(D[s][m], 'ate'), 0, 2.0) for m in ms]
            for k, (d, m) in enumerate(zip(data, ms)):
                d = d[np.isfinite(d)]
                ax.boxplot([d], positions=[k], widths=0.6, showfliers=False, patch_artist=True,
                           boxprops=dict(facecolor=COL[m] + '44', edgecolor=COL[m]), medianprops=dict(color='#111'))
                ax.scatter(np.full(d.size, k) + np.linspace(-0.2, 0.2, d.size), d, s=10, color=COL[m], zorder=3)
            ax.set_xticks(range(len(ms)))
            ax.set_xticklabels([m.replace('_', '\n', 1) for m in ms], fontsize=6, rotation=90)
            ax.set_title(s, fontsize=10)
            ax.set_ylabel('ATE [m] (clipped at 2)')
            ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/ate_boxplots.png', dpi=130)
    plt.close(fig)


def fig_trend(P):
    ms = ['savior_none', 'oracle_dynamic', 'oracle_all_vehicles', 'yolo_naive', 'yolo_full_p2', 'yolo_p4_dyn', 'yolo_p4_pot']
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for m in ms:
        ys, lo, hi = [], [], []
        for lev in LEVELS:
            r = [x for x in P if x['group'] == f'all_{lev}' and x['method'] == m and x['ref'] == 'openvins']
            ys.append(r[0]['gm_ratio_pct'] if r else np.nan)
            lo.append(r[0]['ci_pct'][0] if r else np.nan)
            hi.append(r[0]['ci_pct'][1] if r else np.nan)
        x = np.arange(4) + 0.06 * (ms.index(m) - 3)
        ax.errorbar(x, ys, yerr=[np.array(ys) - lo, np.array(hi) - ys], marker='o', ms=4, capsize=2, color=COL[m], label=m)
    ax.axhline(0, color='k', lw=0.8)
    ax.set_xticks(range(4)); ax.set_xticklabels(LEVELS)
    ax.set_ylabel('ATE vs openvins: geometric-mean ratio - 1 [%]\n(negative = better), 95 % CI')
    ax.set_xlabel('VIODE dynamic level (pooled over environments)')
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/trend_levels.png', dpi=140)
    plt.close(fig)


def share_vs_gain(P):
    """GT dynamic pixel share + diag feature / MSCKF-used share (openvins diag runs) vs oracle gain per sequence."""
    rows = []
    for s in seqs_avail:
        z = np.load(f'{GT}/masks/{s}.npz')
        rec = dict(seq=s, px_dyn=float(z['dyn_share'].mean()), px_static=float(z['static_share'].mean()))
        ds = sorted(glob.glob(f'{R}/{s}/diag_openvins/run_*/diag_dyn.yaml'))
        if ds:
            v = [yaml.safe_load(open(f)) for f in ds]
            rec['kept_dyn_cam0'] = float(np.mean([x['frac_kept_obs_on_human_cam0'] for x in v]))
            rec['msckf_used_meas_dyn'] = float(np.mean([x['post_init']['frac_msckf_used_meas_human'] for x in v]))
            rec['slam_update_meas_dyn'] = float(np.mean([x['post_init']['frac_slam_update_meas_human'] for x in v]))
            rec['chi2_reject_dyn'] = float(np.nanmean([x['post_init']['human'].get('msckf_chi2_reject_rate') or np.nan for x in v]))
            rec['chi2_reject_other'] = float(np.nanmean([x['post_init']['non_human'].get('msckf_chi2_reject_rate') or np.nan for x in v]))
        for m in ('oracle_dynamic', 'oracle_all_vehicles', 'yolo_p4_dyn', 'yolo_p4_pot', 'yolo_naive'):
            r = [x for x in P if x['group'] == s and x['method'] == m and x['ref'] == 'openvins']
            if r:
                rec[f'gain_{m}_pct'] = -r[0]['gm_ratio_pct']
                rec[f'p_{m}'] = r[0]['wil']
        rows.append(rec)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k != 'seq', k))
    with open(f'{OUT_T}/share_vs_gain.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, keys)
        w.writeheader()
        w.writerows(rows)
    out = {}
    for xk in ('px_dyn', 'kept_dyn_cam0', 'msckf_used_meas_dyn'):
        for yk in ('gain_oracle_dynamic_pct', 'gain_yolo_p4_dyn_pct', 'gain_yolo_p4_pot_pct'):
            pts = [(r[xk], r[yk]) for r in rows if xk in r and yk in r]
            if len(pts) >= 4:
                x, y = np.array(pts).T
                rho, p = stats.spearmanr(x, y)
                out[f'{yk} ~ {xk}'] = dict(n=len(pts), spearman_rho=float(rho), p=float(p))
    yaml.safe_dump(out, open(f'{OUT_T}/share_vs_gain_corr.yaml', 'w'), sort_keys=False)
    xk = 'msckf_used_meas_dyn' if any('msckf_used_meas_dyn' in r for r in rows) else 'px_dyn'
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, xkk in zip(axs, ('px_dyn', xk)):
        for m, mk in (('oracle_dynamic', 'o'), ('yolo_p4_dyn', 's'), ('yolo_p4_pot', '^')):
            pts = [(r[xkk] * 100, r[f'gain_{m}_pct'], r['seq']) for r in rows if xkk in r and f'gain_{m}_pct' in r]
            if not pts:
                continue
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], marker=mk, color=COL[m], label=m, s=36)
            if m == 'oracle_dynamic':
                for p in pts:
                    ax.annotate(p[2].replace('parking_lot', 'PL').replace('city_day', 'CD').replace('city_night', 'CN'),
                                (p[0], p[1]), fontsize=6, xytext=(3, 3), textcoords='offset points')
        ax.axhline(0, color='k', lw=0.8)
        ax.set_xlabel({'px_dyn': 'GT dynamic-vehicle pixel share [%]', 'msckf_used_meas_dyn':
                       'share of MSCKF-used measurements on dynamic vehicles [%] (openvins)'}[xkk])
        ax.set_ylabel('ATE gain vs openvins [%] (geometric mean, + = better)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/share_vs_gain.png', dpi=140)
    plt.close(fig)
    return rows, out


def fail_table():
    L = ['# divergence / failure rate (ATE > %.1f m or no estimate) per sequence and method [failed/n]\n' % FAIL_M]
    ms = [m for m in METHODS + EXTRA if any(D[s][m] for s in seqs_avail)]
    L += ['| seq | ' + ' | '.join(ms) + ' |', '|---|' + '--:|' * len(ms)]
    tot = {m: [0, 0] for m in ms}
    for s in seqs_avail:
        cells = []
        for m in ms:
            d = D[s][m]
            if not d:
                cells.append('-')
                continue
            f = sum(1 for v in d.values() if v['fail'])
            tot[m][0] += f; tot[m][1] += len(d)
            cells.append(f'{f}/{len(d)}')
        L.append(f'| {s} | ' + ' | '.join(cells) + ' |')
    L.append('| total | ' + ' | '.join(f'{tot[m][0]}/{tot[m][1]}' for m in ms) + ' |')
    open(f'{OUT_T}/failures.md', 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    rows = method_table()
    fail_table()
    P = paired('ate')
    P_ok = paired('ate', okonly=True)
    paired('rpe')
    paired('rot')
    fig_box()
    fig_trend(P)
    sg = share_vs_gain(P)
    print('sequences:', seqs_avail)
    print(open(f'{OUT_T}/median_matrix.md').read())
    print(open(f'{OUT_T}/failures.md').read())
