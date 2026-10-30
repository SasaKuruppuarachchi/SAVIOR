#!/usr/bin/env python3
"""power_t3.py : power of the pre-registered t3 analysis from the t2 variance components (results/stats_v3).

Input (read-only): results/stats_v3/tables/stats3_all.json (cap 10 m; REML random-intercept fits per comparison x group:
tau2 = between-sequence variance of the paired log ATE ratio, sigma2 = within-sequence (offset) variance; nested fit of
the 'all' group: scene (= trajectory) share of the between-sequence variance).

Unit = trajectory. A trajectory contributes k sequences to a level group (L2+L3, L0+L1: k = 2; L0: k = 1), each with m
start offsets (t3: m = 5; t2: 10). Variance of one trajectory mean:
  A (nested, from t2):   V = f tau2 + ((1 - f) tau2 + sigma2 / m) / k,   f = scene share / (scene + sequence share)
  B (conservative):      V = tau2 + sigma2 / m                          (levels of a trajectory fully correlated)
Directional hypotheses: two-sided one-sample t test on the n trajectory means, alpha 0.05 at each gate of the fixed
sequence P1 -> P4 (noncentral t). P5: TOST equivalence, margin +-10 % on the ATE ratio, 90 % CI (Monte Carlo).
Effects: the t2 point estimate and half of it on the log scale (winner's-curse shrinkage).
-> results/t3_confirmatory/tables/power.json, power.md
"""
import json
import math
import os

import numpy as np
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
J = json.load(open(f'{WS}/results/stats_v3/tables/stats3_all.json'))
OUT = f'{WS}/results/t3_confirmatory/tables'
IDX = {(r['comp'], r['ds'], r['group'], str(r['cap'])): r for r in J['results']}
H = [('P1', 'ov.odynb-oclsb', 'high', 2, 'O-Dyn+B beats O-Cls+B, high-dyn (L2+L3)'),
     ('P2', 'ov.savior-ycls', 'high', 2, 'SAVIOR beats Y-Cls, high-dyn (L2+L3)'),
     ('P3', 'ov.savior-ycls', 'low', 2, 'SAVIOR beats Y-Cls, low-dyn (L0+L1)'),
     ('P4', 'ov.savior-ov', 'high', 2, 'SAVIOR beats OpenVINS, high-dyn (L2+L3)')]
P5 = ('P5', 'ov.savior-ov', 'static', 1, 'SAVIOR equivalent to OpenVINS at L0 (+-10 %)')
NS = [8, 12, 16, 20, 24, 32]
M = 5


def comps(cid, group):
    r = IDX[(cid, 't2', group, '10.0')]
    l = r['lmm']
    nest = IDX[(cid, 't2', 'all', '10.0')].get('nested') or {}
    sc, sq = nest.get('share_scene', 0.0), nest.get('share_seq', 1.0)
    f = sc / (sc + sq) if sc + sq > 0 else 0.0
    return l['mu'], l['tau2'], l['sigma2'], f, r['n_seq']


def power_t(mu, V, n, alpha=0.05):
    df = n - 1
    nc = abs(mu) / math.sqrt(V / n)
    q = stats.t.ppf(1 - alpha / 2, df)
    return float(stats.nct.sf(q, df, nc) + stats.nct.cdf(-q, df, nc))


def power_tost(mu, V, n, lo=math.log(0.9), hi=math.log(1.1), nsim=20000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(mu, math.sqrt(V), (nsim, n))
    m, s = x.mean(1), x.std(1, ddof=1) / math.sqrt(n)
    q = stats.t.ppf(0.95, n - 1)
    return float(np.mean((m - q * s > lo) & (m + q * s < hi)))


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {'m_offsets': M, 'n_grid': NS, 'hyp': {}}
    lines = ['| hyp | t2 estimate | V_A / V_B (m=5) | power at n = ' + ' / '.join(map(str, NS)) + ' (A, t2 effect) | '
             '(B, t2 effect) | (A, half effect) |', '|---|---|---|---|---|---|']
    for name, cid, g, k, txt in H:
        mu, tau2, s2, f, nseq = comps(cid, g)
        VA = f * tau2 + ((1 - f) * tau2 + s2 / M) / k
        VB = tau2 + s2 / M
        VB10 = tau2 + s2 / 10
        pa = [power_t(mu, VA, n) for n in NS]
        pb = [power_t(mu, VB, n) for n in NS]
        ph = [power_t(mu / 2, VA, n) for n in NS]
        res['hyp'][name] = dict(text=txt, comp=cid, group=g, t2_est_pct=100 * (math.exp(mu) - 1), mu_log=mu, tau2=tau2,
                                sigma2=s2, scene_frac=f, V_A=VA, V_B=VB, V_B_10offsets=VB10, power_A=pa, power_B=pb,
                                power_A_half=ph)
        lines.append(f'| {name} {txt} | {100 * (math.exp(mu) - 1):+.0f} % | {VA:.3f} / {VB:.3f} | '
                     + ' / '.join(f'{p:.2f}' for p in pa) + ' | ' + ' / '.join(f'{p:.2f}' for p in pb) + ' | '
                     + ' / '.join(f'{p:.2f}' for p in ph) + ' |')
    # gatekeeping: probability of rejecting P1..P4 in sequence (independence approximation = product)
    seq_pow = [float(np.prod([res['hyp'][h]['power_A'][i] for h in ('P1', 'P2', 'P3', 'P4')])) for i in range(len(NS))]
    res['gate_P1_to_P4_A'] = seq_pow
    name, cid, g, k, txt = P5
    mu, tau2, s2, f, nseq = comps(cid, g)
    V = tau2 + s2 / M
    p5 = {f'{r:.2f}': [power_tost(math.log(r), V, n) for n in NS] for r in (1.00, 1.03, 1.05, math.exp(mu))}
    res['hyp']['P5'] = dict(text=txt, comp=cid, group=g, t2_est_pct=100 * (math.exp(mu) - 1), V=V, tau2=tau2, sigma2=s2,
                            power_tost_by_true_ratio=p5)
    lines.append(f'| P5 {txt} | {100 * (math.exp(mu) - 1):+.0f} % | {V:.3f} | TOST power at true ratio '
                 + '; '.join(f'{r}: ' + ' / '.join(f'{p:.2f}' for p in v) for r, v in p5.items()) + ' | | |')
    lines.append('')
    lines.append('Probability of passing the gates P1..P4 in sequence (A, t2 effects, product): '
                 + ' / '.join(f'n={n}: {p:.2f}' for n, p in zip(NS, seq_pow)))
    json.dump(res, open(f'{OUT}/power.json', 'w'), indent=1)
    open(f'{OUT}/power.md', 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
