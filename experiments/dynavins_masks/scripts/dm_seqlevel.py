#!/usr/bin/env python3
"""dm_seqlevel.py : sequence-level re-analysis of the DynaVINS + SAVIOR masks results with the statistics code of
results/stats_v3/scripts/stats3_core.py (imported, unchanged): estimate = exp(mean of per-sequence mean log ratios) - 1;
two-stage cluster bootstrap 95 % CI (sequences, then offsets; 20000, seed 0); LMM random-intercept REML t-CI (df = k-1);
exact sign-flip test on the per-sequence means; k better / worse sequences. Caps: 10 m (protocol) and 'excl' (pairs
with a failure on either side excluded). Holm over the comparisons within each (split, group, cap) family.
Post-hoc complement to the frozen dm_analyze.py (written after the held-out run; no method choice depends on it).
-> tables/seqlevel.md|json"""
import json, math, sys
import numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/stats_v3/scripts')
import stats3_core as S  # noqa: E402

V = '/home/sasa/workspace/savior_ws/results/dynavins_masks'
SPL = {'t1': ('tables', 2.0, {'L0+L1': ('L0', 'L1'), 'L2+L3': ('L2', 'L3'), 'all': ('L0', 'L1', 'L2', 'L3')}),
       't2': ('tables_t2', 2.0, {'L0+L1': ('L0', 'L1'), 'L2+L3': ('L2', 'L3'), 'all': ('L0', 'L1', 'L2', 'L3')}),
       'viode': ('tables_viode', 1.0, {'none+low': ('none', 'low'), 'mid+high': ('mid', 'high'),
                                       'all': ('none', 'low', 'mid', 'high')})}
COMP = [('dyna_ycls', 'dyna_det'), ('dyna_savior', 'dyna_det'), ('dyna_odyn', 'dyna_det'), ('dyna_ocls', 'dyna_det'),
        ('dyna_savior', 'dyna_ycls'), ('dyna_odyn', 'dyna_ocls'), ('dyna_det', 'dyna_up')]
LAB = {'dyna_det': 'DynaVINS', 'dyna_ycls': '+Y-Cls', 'dyna_savior': '+SAVIOR', 'dyna_odyn': '+O-Dyn+B',
       'dyna_ocls': '+O-Cls+B', 'dyna_up': 'DynaVINS upstream'}
pct = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731
res = []
for sp, (td, fm, groups) in SPL.items():
    W = json.load(open(f'{V}/{td}/ate.json'))['values']
    for cap in (10.0, 'excl'):
        for g, levs in groups.items():
            fam = []
            for a, b in COMP:
                X = {}
                for s in W:
                    if s.rsplit('_', 1)[1] not in levs or a not in W[s] or b not in W[s]:
                        continue
                    x = [S.lr(float(W[s][a][i]), float(W[s][b][i]), cap, fm) for i in W[s][a] if i in W[s][b]]
                    x = [v for v in x if v is not None]
                    if x:
                        X[s] = np.array(x)
                if len(X) < 2:
                    continue
                m = np.array([X[s].mean() for s in X])
                bt = S.boot_two_stage(X)
                lmm = S.reml_ri(X)
                q = S.stats.t.ppf(0.975, lmm['df'])
                p_perm, pmin = S.signflip(m)
                fam.append(dict(split=sp, cap=cap, group=g, method=a, ref=b, k=len(X), est=pct(m.mean()),
                                ci2=[pct(c) for c in np.percentile(bt, [2.5, 97.5])],
                                lmm_ci=[pct(lmm['mu'] - q * lmm['se']), pct(lmm['mu'] + q * lmm['se'])], p_lmm=lmm['p'],
                                p_perm=p_perm, p_perm_min=pmin, better=int((m < -1e-12).sum()), worse=int((m > 1e-12).sum()),
                                seq={s: pct(X[s].mean()) for s in X}))
            for r, h in zip(fam, S.holm([r['p_lmm'] for r in fam])):
                r['holm_lmm'] = float(h)
            res += fam
L = ['# Sequence-level analysis (stats_v3 code): DynaVINS + SAVIOR masks\n',
     'Estimate = mean of per-sequence mean log ratios; CI2 = two-stage cluster bootstrap; LMM = REML random intercept '
     '(t, df = k-1), Holm over the 7 comparisons per (split, group, cap); perm = exact sign-flip over sequences '
     '(minimum attainable p in brackets); b/w = sequences better/worse. cap 10 = protocol, excl = failed pairs excluded.\n']
for sp in SPL:
    for cap in (10.0, 'excl'):
        L += [f'\n## {sp}, cap {cap}\n', '| comparison | group | k | est | CI2 | LMM CI | p LMM / Holm | perm p (min) | b/w |',
              '|---|---|--:|--:|---|---|---|---|---|']
        for r in res:
            if r['split'] == sp and r['cap'] == cap:
                L.append(f"| {LAB[r['method']]} vs {LAB[r['ref']]} | {r['group']} | {r['k']} | {r['est']:+.1f} % | "
                         f"[{r['ci2'][0]:+.0f}, {r['ci2'][1]:+.0f}] | [{r['lmm_ci'][0]:+.0f}, {r['lmm_ci'][1]:+.0f}] | "
                         f"{r['p_lmm']:.3g} / {r['holm_lmm']:.3g} | {r['p_perm']:.3g} ({r['p_perm_min']:.3g}) | {r['better']}/{r['worse']} |")
open(f'{V}/tables/seqlevel.md', 'w').write('\n'.join(L) + '\n')
json.dump(res, open(f'{V}/tables/seqlevel.json', 'w'), indent=1, default=str)
print('\n'.join(L))
