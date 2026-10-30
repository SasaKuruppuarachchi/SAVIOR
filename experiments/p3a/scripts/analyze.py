"""P3a analysis: method tables, paired statistics over start offsets, density trend, timeline / local-RPE vs
human coverage, box plots. Run in the savior image after `eval_all.sh`.

python3 analyze.py   -> results/p3a/{tables,figures}/...
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
from scipy.spatial.transform import Rotation  # noqa: E402

sys.path.insert(0, '/home/sasa/workspace/savior_ws/install/savior_eval/lib/python3.10/site-packages')
from savior_eval.tum_io import load_tum  # noqa: E402
from savior_eval.third_party.rpg_trajectory_evaluation.align_trajectory import align_umeyama  # noqa: E402

WS = '/home/sasa/workspace/savior_ws'
P3 = WS + '/results/p3a'
SC = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentG'
SEQS = ['office_s1_00h', 'office_s1_06h', 'office_s1_12h']
SEQ_LAB = {'office_s1_00h': '00h', 'office_s1_06h': '06h', 'office_s1_12h': '12h'}
METHODS = ['openvins', 'savior_none', 'oracle_person', 'oracle_person_ext', 'oracle_person_after_init',
           'yolo_full', 'yolo_naive']
EXTRA = ['oracle_observe']
COL = {'openvins': '#2a78d6', 'savior_none': '#eb6834', 'oracle_person': '#1baf7a', 'oracle_person_ext': '#eda100',
       'oracle_person_after_init': '#e87ba4', 'yolo_full': '#008300', 'yolo_naive': '#6250d6',
       'oracle_observe': '#e34948'}
SHORT = {'openvins': 'openvins', 'savior_none': 'none', 'oracle_person': 'oracle', 'oracle_person_ext': 'oracle+ext',
         'oracle_person_after_init': 'oracle_afterinit', 'yolo_full': 'yolo_full', 'yolo_naive': 'yolo_naive',
         'oracle_observe': 'observe'}
NPX = 720 * 480.0
OUT_T = P3 + '/tables'
OUT_F = P3 + '/figures'
os.makedirs(OUT_T, exist_ok=True)
os.makedirs(OUT_F, exist_ok=True)


# ------------------------------------------------------------------ loading
def eval_runs(seq, m, sub='eval'):
    fn = f'{P3}/uhumans2_{seq}/{m}/{sub}/eval_summary.yaml'
    if not os.path.isfile(fn):
        return {}
    s = yaml.safe_load(open(fn))
    out = {}
    for t in s['trials']:
        if t['status'] != 'ok':
            continue
        idx = int(t['name'].split('_')[1])
        k0 = list(t['rpe'].keys())[0]
        out[idx] = dict(ate=t['ate']['trans_m']['rmse'], rot=t['ate']['rot_deg']['rmse'],
                        rpe=t['rpe'][k0]['trans_m']['mean'], rpe_yaw=t['rpe'][k0]['yaw_deg']['mean'],
                        n=t['n_matched'])
    return out


def vec(d, key, idxs):
    return np.array([d[i][key] if i in d else np.nan for i in idxs])


IDX = list(range(1, 11))
OFFS = {i: round(0.2 * (i - 1), 1) for i in IDX}


def wil(d):
    d = d[np.isfinite(d)]
    d = d[d != 0]
    if d.size < 2:
        return float('nan')
    return float(stats.wilcoxon(d, alternative='two-sided', mode='exact').pvalue)


def sign_p(d):
    d = d[np.isfinite(d)]
    n_pos, n_neg = int((d > 0).sum()), int((d < 0).sum())
    if n_pos + n_neg == 0:
        return float('nan')
    return float(stats.binomtest(n_pos, n_pos + n_neg, 0.5).pvalue)


def boot_ci(d, n=20000, seed=0):
    d = d[np.isfinite(d)]
    if d.size < 2:
        return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, (n, d.size)).mean(axis=1)
    return (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))


# ------------------------------------------------------------------ 1. method tables
def method_tables(sub='eval', tag=''):
    R = {s: {m: eval_runs(s, m, sub) for m in METHODS + EXTRA} for s in SEQS}
    lines = [f'# P3a method table {tag} (ATE trans RMSE [m], posyaw; bag start offsets 0.0, 0.2, ... s; 5 offsets (0.0-0.8) for every method, 10 (0.0-1.8) for openvins/savior_none/oracle_person/oracle_person_ext/oracle_person_after_init on 06h/12h)\n',
             '| seq | method | n | mean | median | std | min | max | per-offset (0.0/0.2/.../1.8) | rot RMSE [deg] mean | RPE@26.4m [m] mean |',
             '|---|---|--:|--:|--:|--:|--:|--:|---|--:|--:|']
    rows = []
    for s in SEQS:
        for m in METHODS + EXTRA:
            d = R[s][m]
            if not d:
                continue
            a = vec(d, 'ate', IDX)
            v = a[np.isfinite(a)]
            rows.append(dict(seq=s, method=m, n=int(v.size), mean=float(v.mean()), median=float(np.median(v)),
                             std=float(v.std(ddof=1)) if v.size > 1 else 0.0, min=float(v.min()), max=float(v.max()),
                             per=[None if not np.isfinite(x) else round(float(x), 4) for x in a],
                             rot=float(np.nanmean(vec(d, 'rot', IDX))), rpe=float(np.nanmean(vec(d, 'rpe', IDX)))))
            r = rows[-1]
            lines.append(f"| {SEQ_LAB[s]} | {m} | {r['n']} | {r['mean']:.3f} | {r['median']:.3f} | {r['std']:.3f} | "
                         f"{r['min']:.3f} | {r['max']:.3f} | " + ' / '.join('-' if x is None else f'{x:.3f}' for x in r['per'] if x is not None)
                         + f" | {r['rot']:.2f} | {r['rpe']:.3f} |")
    open(f'{OUT_T}/methods{tag}.md', 'w').write('\n'.join(lines) + '\n')
    with open(f'{OUT_T}/methods{tag}.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['seq', 'method', 'n', 'ate_mean', 'ate_median', 'ate_std', 'ate_min', 'ate_max'] +
                   [f'ate_off{OFFS[i]}' for i in IDX] + ['rot_mean', 'rpe26_mean'])
        for r in rows:
            w.writerow([r['seq'], r['method'], r['n'], r['mean'], r['median'], r['std'], r['min'], r['max']] + r['per'] +
                       [r['rot'], r['rpe']])
    # LaTeX
    tex = ['\\begin{tabular}{l' + 'r' * len(METHODS) + '}', '\\toprule',
           'seq & ' + ' & '.join(SHORT[m].replace('_', '\\_') for m in METHODS) + ' \\\\', '\\midrule']
    for s in SEQS:
        cells = []
        for m in METHODS:
            rr = [r for r in rows if r['seq'] == s and r['method'] == m]
            cells.append(f"{rr[0]['mean']:.3f}$\\pm${rr[0]['std']:.3f}" if rr else '--')
        tex.append(SEQ_LAB[s] + ' & ' + ' & '.join(cells) + ' \\\\')
    tex += ['\\bottomrule', '\\end{tabular}']
    open(f'{OUT_T}/methods{tag}.tex', 'w').write('\n'.join(tex) + '\n')
    return R, rows


# ------------------------------------------------------------------ 2. paired statistics
def paired(R, tag='', metric='ate'):
    out = []
    lines = [f'# P3a paired statistics {tag} metric={metric} (diff = method - reference per start offset; '
             'negative = method better)\n',
             'Wilcoxon signed-rank exact two-sided (smallest attainable p: n=5 0.0625, n=10 0.002); sign test (binomial). '
             'dz = mean diff / sd diff. "sens" = sd over offsets of the reference.\n',
             '| seq | method | ref | mean diff [m] | % of ref mean | median diff | sd diff | dz | 95% boot CI | wins/n | Wilcoxon p | sign p | ref sd (sens) |',
             '|---|---|---|--:|--:|--:|--:|--:|---|--:|--:|--:|--:|']
    groups = [(s,) for s in SEQS] + [('office_s1_06h', 'office_s1_12h'), tuple(SEQS)]
    for g in groups:
        for ref in ['openvins', 'savior_none']:
            for m in METHODS + EXTRA:
                if m == ref or (m == 'savior_none' and ref == 'savior_none'):
                    continue
                d, rv = [], []
                for s in g:
                    a = vec(R[s].get(m, {}), metric, IDX)
                    b = vec(R[s].get(ref, {}), metric, IDX)
                    if not R[s].get(m) or not R[s].get(ref):
                        continue
                    d += list(a - b)
                    rv += list(b)
                d, rv = np.array(d), np.array(rv)
                ok = np.isfinite(d)
                if ok.sum() < 2:
                    continue
                dd = d[ok]
                sens = float(np.nanstd(rv, ddof=1)) if len(g) == 1 else float('nan')
                rec = dict(group='+'.join(SEQ_LAB[s] for s in g), method=m, ref=ref, n=int(ok.sum()),
                           mean=float(dd.mean()), pct=float(100 * dd.mean() / np.nanmean(rv[ok])),
                           median=float(np.median(dd)), sd=float(dd.std(ddof=1)),
                           dz=float(dd.mean() / dd.std(ddof=1)) if dd.std(ddof=1) > 0 else float('nan'),
                           ci=boot_ci(dd), wins=int((dd < 0).sum()), wil=wil(dd), sign=sign_p(dd), sens=sens)
                out.append(rec)
                lines.append(f"| {rec['group']} | {m} | {ref} | {rec['mean']:+.4f} | {rec['pct']:+.1f} % | {rec['median']:+.4f} | "
                             f"{rec['sd']:.4f} | {rec['dz']:+.2f} | [{rec['ci'][0]:+.3f}, {rec['ci'][1]:+.3f}] | "
                             f"{rec['wins']}/{rec['n']} | {rec['wil']:.3f} | {rec['sign']:.3f} | "
                             + ('-' if not math.isfinite(sens) else f'{sens:.3f}') + ' |')
    open(f'{OUT_T}/paired_{metric}{tag}.md', 'w').write('\n'.join(lines) + '\n')
    json.dump(out, open(f'{OUT_T}/paired_{metric}{tag}.json', 'w'), indent=1)
    return out


# ------------------------------------------------------------------ 3. box plots
def boxplots(R, tag=''):
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), sharey=False)
    for ax, s in zip(axs, SEQS):
        ms = [m for m in METHODS + EXTRA if R[s].get(m)]
        data = [vec(R[s][m], 'ate', IDX) for m in ms]
        bp = ax.boxplot([d[np.isfinite(d)] for d in data], widths=0.55, patch_artist=True, showfliers=False,
                        medianprops=dict(color='#0b0b0b', lw=1.5))
        for patch, m in zip(bp['boxes'], ms):
            patch.set_facecolor(COL[m] + '55')
            patch.set_edgecolor(COL[m])
        for i, (d, m) in enumerate(zip(data, ms)):
            x = np.full(d.size, i + 1) + np.linspace(-0.15, 0.15, d.size)
            ax.scatter(x, d, s=22, color=COL[m], edgecolor='white', lw=0.8, zorder=3)
            # connect paired offsets to openvins? draw offset index labels lightly
        ax.set_xticks(range(1, len(ms) + 1))
        ax.set_xticklabels([SHORT[m] for m in ms], rotation=35, ha='right', fontsize=9)
        ax.set_title(f'{SEQ_LAB[s]}', fontsize=11)
        ax.grid(axis='y', alpha=0.25, lw=0.5)
        ax.spines[['top', 'right']].set_visible(False)
    axs[0].set_ylabel('ATE translation RMSE [m] (posyaw)')
    fig.suptitle('uHumans2 office_s1: ATE over bag start offsets (dots = runs; 5 or 10 offsets per method)', fontsize=11)
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/box_ate{tag}.png', dpi=130)
    plt.close(fig)
    # paired-difference plot vs openvins
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), sharey=True)
    for ax, s in zip(axs, SEQS):
        ms = [m for m in METHODS + EXTRA if R[s].get(m) and m != 'openvins']
        b = vec(R[s]['openvins'], 'ate', IDX)
        for i, m in enumerate(ms):
            d = vec(R[s][m], 'ate', IDX) - b
            x = np.full(d.size, i + 1) + np.linspace(-0.15, 0.15, d.size)
            ax.scatter(x, d, s=24, color=COL[m], edgecolor='white', lw=0.8, zorder=3)
            ax.plot([i + 0.7, i + 1.3], [np.nanmean(d)] * 2, color='#0b0b0b', lw=1.5)
        ax.axhline(0, color='#52514e', lw=0.8)
        ax.set_xticks(range(1, len(ms) + 1))
        ax.set_xticklabels([SHORT[m] for m in ms], rotation=35, ha='right', fontsize=9)
        ax.set_title(SEQ_LAB[s])
        ax.grid(axis='y', alpha=0.25, lw=0.5)
        ax.spines[['top', 'right']].set_visible(False)
    axs[0].set_ylabel('ATE(method) - ATE(openvins) [m]\nsame start offset; bar = mean')
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/paired_diff_vs_openvins{tag}.png', dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ 4. timelines / local RPE
def poses(fn):
    e = load_tum(fn)
    return e


def interp_idx(tq, t):
    i = np.searchsorted(t, tq)
    i = np.clip(i, 1, len(t) - 1)
    return np.where(np.abs(t[i - 1] - tq) < np.abs(t[i] - tq), i - 1, i)


def T_of(a):
    T = np.tile(np.eye(4), (len(a), 1, 1))
    T[:, :3, :3] = Rotation.from_quat(a[:, 4:8]).as_matrix()
    T[:, :3, 3] = a[:, 1:4]
    return T


def local_rpe(est, gt, starts, dt):
    """translation / yaw error of the relative motion over [ts, ts+dt] (no global alignment needed)."""
    te = est[:, 0]
    ok = (starts >= te[0]) & (starts + dt <= te[-1])
    out_t = np.full(starts.shape, np.nan)
    out_y = np.full(starts.shape, np.nan)
    s = starts[ok]
    i0, i1 = interp_idx(s, te), interp_idx(s + dt, te)
    g0, g1 = interp_idx(s, gt[:, 0]), interp_idx(s + dt, gt[:, 0])
    Te, Tg = T_of(est), T_of(gt)
    Re = np.linalg.inv(Te[i0]) @ Te[i1]
    Rg = np.linalg.inv(Tg[g0]) @ Tg[g1]
    E = np.linalg.inv(Rg) @ Re
    out_t[ok] = np.linalg.norm(E[:, :3, 3], axis=1)
    yaw = np.abs(np.degrees(np.arctan2(E[:, 1, 0], E[:, 0, 0])))
    out_y[ok] = yaw
    return out_t, out_y


def ate_timeline(est, gt):
    tg = gt[:, 0]
    best = interp_idx(est[:, 0], tg)
    ok = np.abs(tg[best] - est[:, 0]) < 0.02
    e, g = est[ok], gt[best[ok]]
    s, R, t = align_umeyama(g[:, 1:4], e[:, 1:4], known_scale=True, yaw_only=True)
    p = (s * (R @ e[:, 1:4].T)).T + t
    return e[:, 0], np.linalg.norm(p - g[:, 1:4], axis=1)


def coverage(seq):
    fn = f'{SC}/masks/{seq}_frames.csv'
    rows = list(csv.DictReader(open(fn)))
    t = np.array([int(r['stamp_ns']) * 1e-9 for r in rows])
    h = np.array([int(r['human_px']) for r in rows]) / NPX
    return t, h


def timeline_analysis(R):
    DT = 10.0
    res = {}
    gts = {s: load_tum(f'{WS}/data/uhumans2/gt/{s}.txt') for s in SEQS}
    t0 = gts['office_s1_00h'][0, 0]
    starts = np.arange(40.0, 505.0, 1.0)
    covs = {s: coverage(s) for s in SEQS if os.path.isfile(f'{SC}/masks/{s}_frames.csv')}
    lrpe = {}
    for s in SEQS:
        for m in METHODS + EXTRA:
            for i in IDX:
                fn = f'{P3}/uhumans2_{s}/{m}/run_0{i}/stamped_traj_estimate.txt'
                if not os.path.isfile(fn):
                    continue
                try:
                    lrpe[(s, m, i)] = local_rpe(load_tum(fn), gts[s], starts, DT)
                except Exception as exc:  # noqa
                    print('local rpe failed', fn, exc)
    # window human coverage (mean over the window), per seq
    wcov = {}
    for s, (tc, hc) in covs.items():
        cs = np.concatenate([[0], np.cumsum(hc)])
        a = np.searchsorted(tc, starts)
        b = np.searchsorted(tc, starts + DT)
        wcov[s] = (cs[b] - cs[a]) / np.maximum(1, b - a)
    lines = ['# P3a local RPE (10 s windows, 1 s grid, t >= 40 s) vs human coverage of the window\n',
             'Spearman rho / p between the window mean human-mask area fraction and the window error difference; '
             'mean over offsets of the per-window values first.\n',
             'p (naive) ignores the overlap of the 10 s windows; p_shift = circular-shift permutation test (coverage series '
             'shifted against the error series, both autocorrelations kept); rho_nov = 10 s-spaced non-overlapping windows.\n',
             '| seq | comparison | windows | rho | p (naive) | p_shift | rho_nov (p) | ref mean local RPE [m] | mean diff [m] all | mean diff top-20 % coverage | mean diff zero coverage |',
             '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']

    def mean_over(s, m):
        arr = [lrpe[(s, m, i)][0] for i in IDX if (s, m, i) in lrpe]
        return np.nanmean(np.array(arr), axis=0) if arr else None

    comps = []
    for s in ['office_s1_06h', 'office_s1_12h']:
        if s not in wcov:
            continue
        for m in METHODS + EXTRA:
            if m == 'openvins':
                continue
            comps.append((s, f'{m} - openvins ({SEQ_LAB[s]})', mean_over(s, m), mean_over(s, 'openvins')))
        comps.append((s, f'openvins {SEQ_LAB[s]} - openvins 00h', mean_over(s, 'openvins'),
                      mean_over('office_s1_00h', 'openvins')))
        comps.append((s, f'oracle_person {SEQ_LAB[s]} - savior_none {SEQ_LAB[s]}', mean_over(s, 'oracle_person'),
                      mean_over(s, 'savior_none')))
    for s, lab, a, b in comps:
        if a is None or b is None:
            continue
        d = a - b
        c = wcov[s]
        ok = np.isfinite(d)
        rho, p = stats.spearmanr(c[ok], d[ok])
        # null: circular shift of the coverage series against the error series (keeps both autocorrelations)
        cc, dd_ = c[ok], d[ok]
        null = np.array([stats.spearmanr(np.roll(cc, k), dd_)[0] for k in range(30, len(cc) - 30, 3)])
        p_shift = float((np.abs(null) >= abs(rho)).mean())
        sub = np.arange(0, len(cc), int(DT))
        rho_nov, p_nov = stats.spearmanr(cc[sub], dd_[sub])
        q = np.percentile(c[ok], 80)
        top = ok & (c >= q) & (c > 0)
        zero = ok & (c == 0)
        rec = dict(seq=s, comp=lab, n=int(ok.sum()), rho=float(rho), p=float(p), p_shift=p_shift, rho_nonoverlap=float(rho_nov),
                   p_nonoverlap=float(p_nov), n_nonoverlap=int(sub.size), ref_mean=float(np.nanmean(b[ok])), mean=float(d[ok].mean()),
                   top=float(d[top].mean()) if top.any() else float('nan'),
                   zero=float(d[zero].mean()) if zero.any() else float('nan'))
        res[lab] = rec
        lines.append(f"| {SEQ_LAB[s]} | {lab} | {rec['n']} | {rec['rho']:+.3f} | {rec['p']:.3g} | {rec['p_shift']:.3f} | "
                     f"{rec['rho_nonoverlap']:+.3f} ({rec['p_nonoverlap']:.2g}) | {rec['ref_mean']:.4f} | {rec['mean']:+.4f} | "
                     f"{rec['top']:+.4f} | {rec['zero']:+.4f} |")
    # absolute: openvins local RPE vs coverage within a sequence
    lines.append('\nOpenVINS window RPE vs coverage within a sequence (Spearman), mean over offsets:\n')
    for s in ['office_s1_06h', 'office_s1_12h']:
        a = mean_over(s, 'openvins')
        if a is None or s not in wcov:
            continue
        ok = np.isfinite(a)
        rho, p = stats.spearmanr(wcov[s][ok], a[ok])
        cc, aa = wcov[s][ok], a[ok]
        null = np.array([stats.spearmanr(np.roll(cc, k), aa)[0] for k in range(30, len(cc) - 30, 3)])
        lines.append(f'- {SEQ_LAB[s]}: rho = {rho:+.3f} (naive p = {p:.3g}, circular-shift p = {(np.abs(null) >= abs(rho)).mean():.3f}), n = {int(ok.sum())}')
    open(f'{OUT_T}/timeline_rpe.md', 'w').write('\n'.join(lines) + '\n')
    json.dump(res, open(f'{OUT_T}/timeline_rpe.json', 'w'), indent=1)

    # ---- figures: ATE timeline + local RPE + coverage, per seq
    for s in SEQS:
        fig, ax = plt.subplots(3, 1, figsize=(12, 8.5), sharex=True, gridspec_kw={'height_ratios': [2, 2, 1]})
        for m in ['openvins', 'savior_none', 'oracle_person', 'yolo_full']:
            for i in IDX:
                fn = f'{P3}/uhumans2_{s}/{m}/run_0{i}/stamped_traj_estimate.txt'
                if not os.path.isfile(fn):
                    continue
                t, e = ate_timeline(load_tum(fn), gts[s])
                ax[0].plot(t - t0, e, color=COL[m], lw=1.0, alpha=0.75, label=SHORT[m] if i == 1 else None)
            mo = mean_over(s, m)
            if mo is not None:
                ax[1].plot(starts - t0, mo, color=COL[m], lw=1.3, label=SHORT[m])
        if s in covs:
            tc, hc = covs[s]
            ax[2].fill_between(tc - t0, hc * 100, color='#52514e', alpha=0.6, lw=0)
            for a_ in ax[:2]:
                yl = a_.get_ylim()
                a_.fill_between(tc - t0, yl[0], yl[1], where=hc > 0.005, color='#888888', alpha=0.12, lw=0,
                                step='mid')
                a_.set_ylim(yl)
        ax[0].set_ylabel('ATE error [m]\n(posyaw, each run)')
        ax[1].set_ylabel(f'local RPE [m]\n({DT:.0f} s windows, mean of 5 offsets)')
        ax[2].set_ylabel('human mask\n[% of image]')
        ax[2].set_xlabel('time since GT start [s]  (grey shading: human mask > 0.5 % of the image)')
        ax[0].legend(frameon=False, fontsize=9, ncol=4)
        for a_ in ax:
            a_.grid(alpha=0.25, lw=0.5)
            a_.spines[['top', 'right']].set_visible(False)
        ax[0].set_title(f'uHumans2 office_s1_{SEQ_LAB[s]}')
        fig.tight_layout()
        fig.savefig(f'{OUT_F}/timeline_{SEQ_LAB[s]}.png', dpi=120)
        plt.close(fig)
    # scatter: window coverage vs RPE difference (oracle - openvins, openvins 12h - 00h)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
    for ax, (s, a_m, b_m, b_s, lab) in zip(axs, [
            ('office_s1_12h', 'oracle_person', 'savior_none', 'office_s1_12h', 'oracle - none (12h, 10 offsets)'),
            ('office_s1_06h', 'oracle_person', 'savior_none', 'office_s1_06h', 'oracle - none (06h, 10 offsets)'),
            ('office_s1_12h', 'openvins', 'openvins', 'office_s1_00h', 'openvins 12h - openvins 00h')]):
        if s not in wcov:
            continue
        a, b = mean_over(s, a_m), mean_over(b_s, b_m)
        if a is None or b is None:
            continue
        d = a - b
        ok = np.isfinite(d)
        ax.scatter(wcov[s][ok] * 100, d[ok], s=9, color=COL[a_m] if a_m != 'openvins' else '#2a78d6', alpha=0.6,
                   edgecolor='none')
        ax.axhline(0, color='#52514e', lw=0.8)
        rho, p = stats.spearmanr(wcov[s][ok], d[ok])
        null = np.array([stats.spearmanr(np.roll(wcov[s][ok], k), d[ok])[0] for k in range(30, int(ok.sum()) - 30, 3)])
        ps = (np.abs(null) >= abs(rho)).mean()
        ax.set_title(f'{lab}\nSpearman rho = {rho:+.2f} (circular-shift p = {ps:.2f})', fontsize=10)
        ax.set_xlabel('mean human mask area in the 10 s window [% of image]')
        ax.grid(alpha=0.25, lw=0.5)
        ax.spines[['top', 'right']].set_visible(False)
    axs[0].set_ylabel('local RPE difference [m]')
    fig.tight_layout()
    fig.savefig(f'{OUT_F}/rpe_vs_coverage.png', dpi=130)
    plt.close(fig)
    return res


def main():
    R, rows = method_tables()
    paired(R)
    paired(R, metric='rpe')
    boxplots(R)
    if os.path.isfile(f'{P3}/uhumans2_office_s1_12h/openvins/eval_w45/eval_summary.yaml'):
        Rw, _ = method_tables('eval_w45', '_w45')
        paired(Rw, '_w45')
    if os.path.isfile(f'{P3}/uhumans2_office_s1_12h/openvins/eval_mid/eval_summary.yaml'):
        Rm, _ = method_tables('eval_mid', '_mid')
        paired(Rm, '_mid')
        boxplots(Rm, '_mid')
    timeline_analysis(R)
    print(open(f'{OUT_T}/methods.md').read())
    print(open(f'{OUT_T}/paired_ate.md').read())


if __name__ == '__main__':
    main()
