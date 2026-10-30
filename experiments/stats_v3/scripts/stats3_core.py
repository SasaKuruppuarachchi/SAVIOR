#!/usr/bin/env python3
"""stats3_core.py : sequence-level (hierarchical) re-analysis of the SAVIOR held-out results (existing runs only).

Inputs (read-only, produced by the frozen held-out pipelines):
  results/backend_v2/tables/ate_{t2,viode}.json         OpenVINS back-end v2 (and v1 = M2b) per-run ATE (posyaw, rpg)
  results/vins_savior/heldout/tables_{t2,viode}/ate.json VINS-Fusion family + DynaVINS (M3b runs reused), posyaw
  results/sota/tables/merge_{warehouse_t2,viode}.csv     ORB-SLAM3 per-run ATE (failure table only)
Definitions copied from bv2analyze.py / vs_analyze.py: ATE = posyaw RMSE; failure = ATE > 2 m (warehouse) / 1 m (VIODE);
status != ok -> inf; paired log ratio log(min(a,cap)/min(b,cap)), cap 10 m (sensitivity: 2, 5, 50 m, failures excluded).

Unit of inference = sequence (12 per dataset; 3 static, 6 per level group). Offsets (0.2 s start shifts) are treated as
within-sequence replicates. Per comparison x dataset x group x cap:
  old   : pooled run-level geometric-mean ratio, iid bootstrap CI (20000, seed 0), Wilcoxon (= original protocol)
  new   : estimate = exp(mean of per-sequence mean log ratios) - 1
          two-stage cluster bootstrap (sequences, then offsets within sequence; 20000, seed 0, percentile CI)
          one-stage cluster bootstrap (sequence means only) as a sensitivity
          exact sign-flip permutation test on the per-sequence means (2^k), exact sign test
          LMM  y = mu + b_seq + e  (REML, own implementation; statsmodels is not in the image), t-test on mu, df = k-1
Holm families: cell (dataset x group), system (OV2 / VINS / cross x dataset x group), global (all main-text claims).
-> results/stats_v3/tables/*.json|md
"""
import csv
import itertools
import json
import math
import os

import numpy as np
from scipy import optimize, stats

WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
OUT = R + '/stats_v3/tables'
NB = 20000
CAPS = [2.0, 5.0, 10.0, 50.0, 'excl']
FAIL = {'t2': 2.0, 'viode': 1.0}
IDX = [str(i) for i in range(1, 11)]

# ------------------------------------------------------------------ data
VAL = {}   # VAL[ds][method][seq][run] = ATE (inf = status != ok)
for ds in ('t2', 'viode'):
    B = json.load(open(f'{R}/backend_v2/tables/ate_{ds}.json'))['values']
    Vj = json.load(open(f'{R}/vins_savior/heldout/tables_{ds}/ate.json'))['values']
    d = {}
    for m in ('openvins', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge', 'oracle_moving_ext', 'oracle_class_ext'):
        d['ov2:' + m] = {s: {i: float(v) for i, v in B['v2'][s][m].items()} for s in B['v2']}
        d['ov1:' + m] = {s: {i: float(v) for i, v in B['v1'][s][m].items()} for s in B['v1']}
    for m in ('vins_fusion', 'vins_ycls', 'vins_savior', 'vins_odyn', 'vins_ocls', 'dynavins'):
        d[m] = {s: {i: float(v) for i, v in Vj[s][m].items()} for s in Vj}
    sf = f'{R}/sota/tables/merge_{"warehouse_t2" if ds == "t2" else "viode"}.csv'
    orb = {}
    for r in csv.DictReader(open(sf)):
        if r['method'] == 'orbslam3':
            v = r['ate_posyaw_m']
            v = float(v) if v not in ('', 'nan') else math.inf
            orb.setdefault(r['seq'], {})[str(int(r['run']))] = math.inf if math.isnan(v) else v
    d['orbslam3'] = orb
    VAL[ds] = d
SEQS = {ds: list(VAL[ds]['ov2:openvins']) for ds in VAL}
SCENE = lambda s: s.rsplit('_', 1)[0].replace('_t2', '')  # noqa: E731
LEV = lambda s: s.rsplit('_', 1)[1]  # noqa: E731
GROUPS = {'t2': {'static': ['L0'], 'low': ['L0', 'L1'], 'high': ['L2', 'L3'], 'all': ['L0', 'L1', 'L2', 'L3']},
          'viode': {'static': ['none'], 'low': ['none', 'low'], 'high': ['mid', 'high'], 'all': ['none', 'low', 'mid', 'high']}}
GNAME = {'t2': {'static': 'L0', 'low': 'L0+L1', 'high': 'L2+L3', 'all': 'all'},
         'viode': {'static': 'none', 'low': 'none+low', 'high': 'mid+high', 'all': 'all'}}

LAB = {'ov2:openvins': 'OpenVINS', 'ov2:yolo_naive': 'Y-Cls', 'ov2:sens_fix1': 'SAVIOR', 'ov2:p7_nb': 'SAVIOR-adaptive',
       'ov2:savior_edge': 'SAVIOR-edge', 'ov2:oracle_moving_ext': 'O-Dyn+B', 'ov2:oracle_class_ext': 'O-Cls+B',
       'ov1:openvins': 'OpenVINS (v1)', 'ov1:sens_fix1': 'SAVIOR (v1)', 'ov1:yolo_naive': 'Y-Cls (v1)',
       'vins_fusion': 'VINS-Fusion', 'vins_ycls': 'VINS+Y-Cls', 'vins_savior': 'VINS+SAVIOR', 'vins_odyn': 'VINS+O-Dyn+B',
       'vins_ocls': 'VINS+O-Cls+B', 'dynavins': 'DynaVINS', 'orbslam3': 'ORB-SLAM3'}
# comparisons: id -> (system block, method A, method B)
COMP = {
    'ov.savior-ycls': ('OV2', 'ov2:sens_fix1', 'ov2:yolo_naive'),
    'ov.adapt-ycls': ('OV2', 'ov2:p7_nb', 'ov2:yolo_naive'),
    'ov.odynb-oclsb': ('OV2', 'ov2:oracle_moving_ext', 'ov2:oracle_class_ext'),
    'ov.savior-ov': ('OV2', 'ov2:sens_fix1', 'ov2:openvins'),
    'ov.ycls-ov': ('OV2', 'ov2:yolo_naive', 'ov2:openvins'),
    'ov.oclsb-ov': ('OV2', 'ov2:oracle_class_ext', 'ov2:openvins'),
    'ov.odynb-ov': ('OV2', 'ov2:oracle_moving_ext', 'ov2:openvins'),
    'ov.edge-savior': ('OV2', 'ov2:savior_edge', 'ov2:sens_fix1'),
    'vins.savior-ycls': ('VINS', 'vins_savior', 'vins_ycls'),
    'vins.savior-vins': ('VINS', 'vins_savior', 'vins_fusion'),
    'vins.ycls-vins': ('VINS', 'vins_ycls', 'vins_fusion'),
    'vins.oclsb-vins': ('VINS', 'vins_ocls', 'vins_fusion'),
    'vins.odynb-vins': ('VINS', 'vins_odyn', 'vins_fusion'),
    'vins.odynb-oclsb': ('VINS', 'vins_odyn', 'vins_ocls'),
    'x.ovsavior-dyna': ('cross', 'ov2:sens_fix1', 'dynavins'),
    'x.ovsavior-vins': ('cross', 'ov2:sens_fix1', 'vins_fusion'),
}
# main-text claims: (claim id, comparison, dataset, group, text, old macro value, expected direction: -1 better, +1 worse, 0 'no difference')
CLAIMS = [
    ('C1', 'ov.odynb-ov', 't2', 'high', 'Perfect masks reduce high-dyn. warehouse ATE of OpenVINS (-77 %)', -1),
    ('C2', 'ov.odynb-oclsb', 't2', 'low', 'O-Dyn+B beats O-Cls+B, warehouse low-dyn. (-45 %)', -1),
    ('C3', 'ov.odynb-oclsb', 't2', 'high', 'O-Dyn+B beats O-Cls+B, warehouse high-dyn. (-76 %)', -1),
    ('C4a', 'vins.odynb-oclsb', 't2', 'low', '"same holds with VINS-Fusion" (low-dyn.)', -1),
    ('C4b', 'vins.odynb-oclsb', 't2', 'high', '"same holds with VINS-Fusion" (high-dyn.)', -1),
    ('C5a', 'ov.odynb-oclsb', 'viode', 'low', 'VIODE: the two oracles do not differ (low-dyn.)', 0),
    ('C5b', 'ov.odynb-oclsb', 'viode', 'high', 'VIODE: the two oracles do not differ (high-dyn.)', 0),
    ('C6', 'ov.savior-ycls', 't2', 'low', 'SAVIOR beats Y-Cls (OpenVINS), warehouse low-dyn. (-25 %)', -1),
    ('C7', 'ov.savior-ycls', 't2', 'high', 'SAVIOR beats Y-Cls (OpenVINS), warehouse high-dyn. (-35 %)', -1),
    ('C8a', 'vins.savior-ycls', 't2', 'low', 'SAVIOR beats Y-Cls with VINS-Fusion, warehouse low-dyn. ("significantly better")', -1),
    ('C8b', 'vins.savior-ycls', 't2', 'high', 'SAVIOR beats Y-Cls with VINS-Fusion, warehouse high-dyn. (-16 %, conclusion)', -1),
    ('C9a', 'ov.savior-ycls', 'viode', 'low', 'VIODE: SAVIOR and Y-Cls equivalent with OpenVINS (low-dyn.)', 0),
    ('C9b', 'ov.savior-ycls', 'viode', 'high', 'VIODE: SAVIOR and Y-Cls equivalent with OpenVINS (high-dyn.)', 0),
    ('C9c', 'vins.savior-ycls', 'viode', 'low', 'VIODE: VINS+SAVIOR slightly worse than VINS+Y-Cls (low-dyn.)', 1),
    ('C10', 'ov.ycls-ov', 't2', 'static', 'Static cost: Y-Cls raises OpenVINS ATE at L0 (+46 %)', 1),
    ('C11', 'ov.oclsb-ov', 't2', 'static', 'Static cost: O-Cls+B raises OpenVINS ATE at L0 (+105 %)', 1),
    ('C12', 'ov.savior-ov', 't2', 'static', 'SAVIOR change at L0 not significant (+8 %)', 0),
    ('C13a', 'vins.ycls-vins', 't2', 'static', '"VINS-Fusion shows the same pattern" (Y-Cls, L0)', 1),
    ('C13b', 'vins.savior-vins', 't2', 'static', '"VINS-Fusion shows the same pattern" (SAVIOR, L0)', 0),
    ('C15', 'ov.savior-ov', 't2', 'high', 'SAVIOR reduces OpenVINS ATE, warehouse high-dyn. (-55 %)', -1),
    ('C15b', 'ov.ycls-ov', 't2', 'high', 'change with Y-Cls (vs OpenVINS) not significant, high-dyn.', 0),
    ('C16', 'vins.savior-vins', 't2', 'high', 'SAVIOR raises VINS-Fusion ATE, warehouse high-dyn. (+25 %)', 1),
    ('C17', 'vins.ycls-vins', 't2', 'high', 'Y-Cls raises VINS-Fusion ATE even more, warehouse high-dyn. (+50 %)', 1),
    ('C18', 'vins.odynb-vins', 't2', 'high', 'perfect masks give VINS-Fusion no gain, warehouse high-dyn.', 0),
    ('C19', 'vins.savior-vins', 'viode', 'high', 'SAVIOR improves VINS-Fusion on VIODE high-dyn. (-56 %)', -1),
    ('C20', 'x.ovsavior-dyna', 'viode', 'all', 'VIODE: OV+SAVIOR most accurate, below DynaVINS (-58 %)', -1),
    ('C21', 'x.ovsavior-vins', 'viode', 'all', 'VIODE: OV+SAVIOR below VINS-Fusion (-63 %)', -1),
    ('C22', 'x.ovsavior-dyna', 't2', 'all', 'Warehouse: OV+SAVIOR worse than DynaVINS (+41 %)', 1),
    ('C22b', 'x.ovsavior-vins', 't2', 'high', 'Warehouse high-dyn.: VINS-Fusion lower than OV+SAVIOR (n.s.)', 0),
    ('C23', 'ov.edge-savior', 't2', 'low', 'SAVIOR-edge worse than SAVIOR, warehouse low-dyn. (+22 %)', 1),
    ('C25', 'ov.adapt-ycls', 't2', 'high', 'SAVIOR-adaptive beats Y-Cls, warehouse high-dyn. (-42 %)', -1),
]


# ------------------------------------------------------------------ statistics
def lr(a, b, cap, fm):
    if cap == 'excl':
        return None if (a > fm or b > fm) else math.log(a / b)
    return math.log(min(a, cap) / min(b, cap))


def paired(ds, A, B, group, cap):
    """{seq: np.array of paired log ratios} for the sequences of the group"""
    out = {}
    for s in SEQS[ds]:
        if LEV(s) not in GROUPS[ds][group]:
            continue
        a, b = VAL[ds][A].get(s, {}), VAL[ds][B].get(s, {})
        x = [lr(a[i], b[i], cap, FAIL[ds]) for i in IDX if i in a and i in b]
        x = [v for v in x if v is not None]
        if x:
            out[s] = np.array(x)
    return out


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


def boot_one_stage(m, seed=0):
    rng = np.random.default_rng(seed)
    return rng.choice(m, (NB, m.size)).mean(axis=1)


def signflip(m):
    k = m.size
    if k == 0 or np.all(np.abs(m) < 1e-12):
        return 1.0, 1.0
    S = np.array(list(itertools.product([1, -1], repeat=k)))
    st = np.abs((S * m).mean(axis=1))
    p = float(np.mean(st >= abs(m.mean()) - 1e-12))
    minp = 2.0 / 2 ** k
    return p, minp


def signtest(m):
    nz = m[np.abs(m) > 1e-12]
    if nz.size == 0:
        return 1.0
    return float(stats.binomtest(int((nz < 0).sum()), nz.size, 0.5).pvalue)


def reml_ri(X):
    """REML random-intercept model y_sj = mu + b_s + e_sj; returns mu, se, df, p, tau2, sigma2"""
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
    # boundary gamma = 0
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
    return dict(mu=float(mu), se=float(se), df=df, t=float(t), p=p, tau2=float(g * s2), sigma2=float(s2),
                icc=float(g / (1 + g)))


def reml_nested(ds, X):
    """sensitivity: scene + sequence-within-scene random intercepts (dense REML); returns variance shares, mu, se"""
    keys = list(X)
    y = np.concatenate([X[s] for s in keys])
    seq = np.concatenate([[j] * X[s].size for j, s in enumerate(keys)])
    scs = sorted({SCENE(s) for s in keys})
    sc = np.concatenate([[scs.index(SCENE(s))] * X[s].size for s in keys])
    if len(scs) < 2 or np.ptp(y) < 1e-12:
        return None
    N = y.size
    Z1 = (sc[:, None] == np.arange(len(scs))[None]).astype(float)
    Z2 = (seq[:, None] == np.arange(len(keys))[None]).astype(float)
    Xd = np.ones((N, 1))

    def f(th):
        g1, g2 = np.exp(th)
        V = np.eye(N) + g1 * Z1 @ Z1.T + g2 * Z2 @ Z2.T
        L = np.linalg.cholesky(V)
        Vi = np.linalg.inv(V)
        XtVX = Xd.T @ Vi @ Xd
        beta = np.linalg.solve(XtVX, Xd.T @ Vi @ y)
        r = y - Xd @ beta
        Q = float(r @ Vi @ r)
        s2 = Q / (N - 1)
        return 0.5 * ((N - 1) * math.log(s2) + 2 * np.log(np.diag(L)).sum() + math.log(XtVX[0, 0])), beta[0], s2, XtVX[0, 0]

    best = None
    for st in itertools.product([-6, -1, 2], repeat=2):
        r = optimize.minimize(lambda th: f(np.clip(th, -20, 12))[0], np.array(st, float), method='Nelder-Mead',
                              options=dict(xatol=1e-4, fatol=1e-8, maxiter=2000))
        if best is None or r.fun < best.fun:
            best = r
    th = np.clip(best.x, -20, 12)
    _, mu, s2, xvx = f(th)
    g1, g2 = np.exp(th)
    se = math.sqrt(s2 / xvx)
    tot = s2 * (1 + g1 + g2)
    t = mu / se
    return dict(mu=float(mu), se=float(se), n_scene=len(scs), share_scene=float(s2 * g1 / tot),
                share_seq=float(s2 * g2 / tot), share_resid=float(s2 / tot),
                p_df_seq=float(2 * stats.t.sf(abs(t), len(keys) - 1)), p_df_scene=float(2 * stats.t.sf(abs(t), len(scs) - 1)))


pct = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def analyse(ds, cid, group, cap, full=True):
    _, A, B = COMP[cid]
    X = paired(ds, A, B, group, cap)
    if not X:
        return None
    allx = np.concatenate(list(X.values()))
    m = np.array([X[s].mean() for s in X])
    r = dict(comp=cid, ds=ds, group=group, gname=GNAME[ds][group], cap=cap, n_seq=len(X), n_pairs=int(allx.size))
    # old (run-level, original protocol)
    r['old'] = dict(est=pct(allx.mean()), ci=[pct(c) for c in boot_iid(allx)], p_wilcoxon=wilcox(allx),
                    wins=int((allx < -1e-12).sum()), losses=int((allx > 1e-12).sum()))
    est = m.mean()
    r['est'] = pct(est)
    r['seq_pct'] = {s: pct(X[s].mean()) for s in X}
    r['seq_better'] = int((m < -1e-12).sum())
    r['seq_worse'] = int((m > 1e-12).sum())
    r['scene_pct'] = {}
    for sc in sorted({SCENE(s) for s in X}):
        r['scene_pct'][sc] = pct(np.mean([X[s].mean() for s in X if SCENE(s) == sc]))
    if full:
        bt = boot_two_stage(X)
        r['ci2'] = [pct(c) for c in np.percentile(bt, [2.5, 97.5])]
        b1 = boot_one_stage(m)
        r['ci1'] = [pct(c) for c in np.percentile(b1, [2.5, 97.5])]
    else:
        bt = boot_two_stage(X)
        r['ci2'] = [pct(c) for c in np.percentile(bt, [2.5, 97.5])]
    r['p_perm'], r['p_perm_min'] = signflip(m)
    r['p_sign'] = signtest(m)
    lmm = reml_ri(X)
    r['lmm'] = lmm
    if lmm:
        r['lmm_est'] = pct(lmm['mu'])
        q = stats.t.ppf(0.975, lmm['df'])
        r['lmm_ci'] = [pct(lmm['mu'] - q * lmm['se']), pct(lmm['mu'] + q * lmm['se'])]
    if full and group == 'all':
        r['nested'] = reml_nested(ds, X)
    return r


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0
    for rk, i in enumerate(o):
        run = max(run, min(1, (len(ps) - rk) * ps[i]))
        adj[i] = run
    return adj


# ------------------------------------------------------------------ failures
def fail_counts(ds, m, group, fm=None):
    fm = FAIL[ds] if fm is None else fm
    out = {}
    for s in SEQS[ds]:
        if LEV(s) in GROUPS[ds][group] and s in VAL[ds][m]:
            v = VAL[ds][m][s]
            out[s] = (sum(v[i] > fm for i in IDX if i in v), sum(i in v for i in IDX))
    return out


def fail_summary(ds, m, group):
    fc = fail_counts(ds, m, group)
    if not fc:
        return None
    f = np.array([a for a, _ in fc.values()], float)
    n = np.array([b for _, b in fc.values()], float)
    rng = np.random.default_rng(0)
    si = rng.integers(0, f.size, (NB, f.size))
    rates = f[si].sum(1) / n[si].sum(1)
    tot, N = int(f.sum()), int(n.sum())
    cp = stats.binomtest(tot, N).proportion_ci(method='exact') if N else None
    return dict(method=m, ds=ds, group=group, fails=tot, runs=N, rate=tot / N,
                ci_cluster=[float(x) for x in np.percentile(rates, [2.5, 97.5])],
                ci_cp_iid=[cp.low, cp.high], n_seq_with_fail=int((f > 0).sum()), n_seq=int(f.size),
                per_seq={s: a for s, (a, _) in fc.items() if a})


def fail_paired(ds, cid, group):
    _, A, B = COMP[cid]
    fa, fb = fail_counts(ds, A, group), fail_counts(ds, B, group)
    ks = [s for s in fa if s in fb]
    d = np.array([fa[s][0] - fb[s][0] for s in ks], float)
    # run-level exact McNemar (old style, iid)
    b10 = c01 = 0
    for s in ks:
        a, b = VAL[ds][A][s], VAL[ds][B][s]
        for i in IDX:
            if i in a and i in b:
                fa_i, fb_i = a[i] > FAIL[ds], b[i] > FAIL[ds]
                b10 += fa_i and not fb_i
                c01 += fb_i and not fa_i
    p_mc = float(stats.binomtest(b10, b10 + c01).pvalue) if b10 + c01 else 1.0
    nz = d[np.abs(d) > 0]
    p_seq = signflip(nz)[0] if nz.size else 1.0
    return dict(comp=cid, ds=ds, group=group, fails_A=int(sum(fa[s][0] for s in ks)), fails_B=int(sum(fb[s][0] for s in ks)),
                runs=int(sum(fa[s][1] for s in ks)), discordant_A_only=int(b10), discordant_B_only=int(c01),
                p_mcnemar_run=p_mc, n_seq_diff=int(nz.size), p_signflip_seq=p_seq,
                seq_diff={s: int(fa[s][0] - fb[s][0]) for s in ks if fa[s][0] != fb[s][0]})


# ------------------------------------------------------------------ run everything
def main():
    os.makedirs(OUT, exist_ok=True)
    res = []
    for ds in ('t2', 'viode'):
        for cid in COMP:
            for g in GROUPS[ds]:
                for cap in CAPS:
                    r = analyse(ds, cid, g, cap, full=(cap == 10.0 or cap == 'excl'))
                    if r:
                        res.append(r)
    main10 = [r for r in res if r['cap'] == 10.0]
    # Holm families (on LMM p and on sign-flip p), cap 10
    claim_keys = {(c[1], c[2], c[3]) for c in CLAIMS}
    fams = {}
    for r in main10:
        if r['group'] == 'static' and COMP[r['comp']][2] not in ('ov2:openvins', 'vins_fusion'):
            continue   # static cost family: only comparisons vs the unmasked back-end
        fams.setdefault(('cell', r['ds'], r['group']), []).append(r)
        fams.setdefault(('system', COMP[r['comp']][0], r['ds'], r['group']), []).append(r)
        fams.setdefault(('all_key',), []).append(r)
        if (r['comp'], r['ds'], r['group']) in claim_keys:
            fams.setdefault(('global_claims',), []).append(r)
    for fk, rs in fams.items():
        name = fk[0]
        for which in ('lmm', 'perm', 'old'):
            ps = [(x['lmm']['p'] if x['lmm'] else 1.0) if which == 'lmm' else x['p_perm'] if which == 'perm'
                  else x['old']['p_wilcoxon'] for x in rs]
            for x, h in zip(rs, holm(ps)):
                x.setdefault('holm', {}).setdefault(name, {})[which] = float(h)
                x['holm'][name]['size'] = len(rs)
    # failures
    FMETH = ['ov2:openvins', 'ov2:yolo_naive', 'ov2:sens_fix1', 'ov2:p7_nb', 'ov2:savior_edge', 'ov2:oracle_moving_ext',
             'ov2:oracle_class_ext', 'ov1:openvins', 'ov1:yolo_naive', 'ov1:sens_fix1', 'vins_fusion', 'vins_ycls',
             'vins_savior', 'vins_odyn', 'vins_ocls', 'dynavins', 'orbslam3']
    fres = [fail_summary(ds, m, g) for ds in ('t2', 'viode') for m in FMETH for g in GROUPS[ds]]
    fres = [f for f in fres if f]
    fpair = [fail_paired(ds, cid, g) for ds in ('t2', 'viode') for cid in COMP for g in GROUPS[ds]]
    json.dump(dict(results=res, failures=fres, failure_pairs=fpair, claims=CLAIMS, comps=COMP, labels=LAB,
                   groups=GNAME, fail_m=FAIL, caps=[str(c) for c in CAPS]),
              open(OUT + '/stats3_all.json', 'w'), indent=1, default=str)
    print('results', len(res), 'failures', len(fres))


if __name__ == '__main__':
    main()
