#!/usr/bin/env python3
"""Fill the held-out numbers of the SAVIOR paper (macro file + generated tables).

Every number of the final held-out run (OpenVINS back-end v2 on SAVIOR-Warehouse t2 + VIODE, and VINS-Fusion + SAVIOR masks
on the same data) enters the manuscript ONLY through this script:

  paper/ho_values.tex          \\HOset{<key>}{<value>} for every key that could be computed (read by savior_v2.tex and
                               savior_supp.tex; a key that is not set renders as a visible magenta placeholder)
  paper/tables/*.tex           generated tables (supplement: per-sequence medians)
  paper/ho_status.txt          which keys are set / pending (copied into numbers_ledger.yaml by hand in phase 2)

Inputs (read-only; produced by the held-out pipelines, NOT by this script):
  results/backend_v2/tables/{ate,rpe}_{t2,viode}.json           (backend_v2/scripts/heldout_v2.sh analyze -> bv2analyze.py)
  results/vins_savior/heldout/tables_{t2,viode}/{ate,rpe}.json   (vins_savior/scripts/heldout/run_heldout.sh analyze)
  results/sota/tables/merge_{warehouse_t2,viode}.csv             (M3b: DynaVINS / ORB-SLAM3 per-run ATE; same protocol)
  results/m2b_heldout/tables/share_vs_gain.md                    (moving-pixel share per held-out sequence)
Statistics are those of bv2analyze.py / vs_analyze.py (paired per-offset log ratios, failures capped at 10 m, geometric-mean
ratio - 1, 95 % bootstrap CI with 20000 resamples and seed 0, Wilcoxon signed-rank). Paired effects are read from the
tables; this script only computes (i) geometric means per group for the cross-back-end table and (ii) the cross-study
paired comparison OpenVINS-v2+SAVIOR vs DynaVINS (as results/vins_savior/scripts/cross_backend_cmp.py, same offsets) and
(iii) Spearman rho of the per-sequence oracle gain vs the moving-pixel share.

Run in the savior image:
  docker run --rm --network none -u $(id -u):$(id -g) -v $WS:$WS savior:humble-cuda12.8 python3 paper/scripts/make_heldout_values.py
"""
import csv
import json
import math
import os
import re

import numpy as np
from scipy import stats

WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
P = WS + '/paper'
CAP = 10.0
TEST = os.environ.get('HO_TEST')  # developer test: point the held-out inputs at the t1 tables
B = {d: {m: f'{R}/backend_v2/tables/{m}_{d}.json' for m in ('ate', 'rpe')} for d in ('t2', 'viode')}
V = {d: {m: f'{R}/vins_savior/heldout/tables_{d}/{m}.json' for m in ('ate', 'rpe')} for d in ('t2', 'viode')}
if TEST:
    B = {d: {m: f'{R}/backend_v2/tables/{m}_t1.json' for m in ('ate', 'rpe')} for d in ('t2', 'viode')}
    V = {d: {m: f'{R}/vins_savior/tables/{m}.json' for m in ('ate', 'rpe')} for d in ('t2', 'viode')}
    P = TEST
SOTA = {'t2': f'{R}/sota/tables/merge_warehouse_t2.csv', 'viode': f'{R}/sota/tables/merge_viode.csv'}
SHARE = f'{R}/m2b_heldout/tables/share_vs_gain.md'

# short names used in the keys
MB = {'openvins': 'ov', 'yolo_naive': 'ycls', 'sens_fix1': 'savior', 'p7_nb': 'adapt', 'savior_edge': 'edge',
      'oracle_moving_ext': 'odynb', 'oracle_class_ext': 'oclsb', 'oracle_moving': 'odyn', 'oracle_class_naive': 'ocls'}
MV = {'vins_fusion': 'vins', 'vins_ycls': 'vinsycls', 'vins_savior': 'vinssavior', 'vins_edge': 'vinsedge',
      'vins_odyn': 'vinsodynb', 'vins_ocls': 'vinsoclsb', 'dynavins': 'dyna'}
GT = {'L0': 'L0', 'L1': 'L1', 'L2': 'L2', 'L3': 'L3', 'L0+L1': 'L01', 'L2+L3': 'L23', 'hall_L3': 'hallL3', 'dock_L3': 'dockL3',
      'hall+dock_L3': 'hdL3', 'all': 'all', 'none': 'N', 'low': 'Lo', 'mid': 'M', 'high': 'H', 'none+low': 'NL',
      'mid+high': 'MH', 'low+mid+high': 'LMH'}
DS = {'t2': 't2', 'viode': 'vi'}

VALUES = {}


def put(k, v):
    VALUES[k] = v


def load(p):
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def fpct(x, d=0):
    s = f'{x:+.{d}f}'
    if s in ('+0', '-0', '+0.0', '-0.0'):
        s = '0' if d == 0 else '0.0'
    return f'${s.replace("-", "-")}$\\,\\%'


def fp(p):
    if p >= 0.001:
        return f'{p:.3f}'.rstrip('0').rstrip('.') if p < 0.1 else (f'{p:.2f}' if p < 0.995 else '1')
    e = int(math.floor(math.log10(p)))
    m = p / 10 ** e
    return f'{m:.0f}\\times10^{{{e}}}'


def eff(key, r, holm=True):
    """r: paired record with gm, ci, p (and holm)."""
    put(key, fpct(r['gm']))
    put(key + '.ci', f'${r["ci"][0]:+.0f}$ to ${r["ci"][1]:+.0f}$\\,\\%'.replace('+0$', '0$'))
    pv = r.get('holm', r['p']) if holm else r['p']
    put(key + '.p', f'$p_{{\\mathrm{{H}}}}={fp(pv)}$' if (holm and 'holm' in r) else f'$p={fp(pv)}$')
    put(key + '.wl', f'{r["wins"]}/{r["wins"] + r["losses"]}')
    put(key + '.b', ('\\textbf{' + fpct(r['gm']) + '}') if (holm and r.get('holm', 1) < 0.05) else fpct(r['gm']))


def gm(vals):
    v = [min(x, CAP) for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.exp(np.mean(np.log(v)))) if v else None


def fnum(x):
    return '--' if x is None else (f'{x:.3f}' if x < 1 else f'{x:.2f}')


def boot(x, n=20000):
    rng = np.random.default_rng(0)
    return np.percentile(rng.choice(x, (n, x.size)).mean(axis=1), [2.5, 97.5])


def paired(a, b):
    k = sorted(set(a) & set(b))
    x = np.array([math.log(min(a[i], CAP) / min(b[i], CAP)) for i in k])
    if x.size < 5:
        return None
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    ci = boot(x)
    return dict(gm=100 * (math.exp(x.mean()) - 1), ci=[100 * (math.exp(c) - 1) for c in ci], p=p,
                wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()), n=int(x.size))


def lev(s):
    return s.rsplit('_', 1)[1]


def groups(ds):
    if ds == 't2':
        return {'L0+L1': lambda s: lev(s) in ('L0', 'L1'), 'L2+L3': lambda s: lev(s) in ('L2', 'L3'),
                'hall+dock_L3': lambda s: s in ('hall_t2_L3', 'dock_t2_L3'), 'all': lambda s: True}
    return {'none+low': lambda s: lev(s) in ('none', 'low'), 'mid+high': lambda s: lev(s) in ('mid', 'high'),
            'all': lambda s: True}


def sota_values(ds, method):
    out = {}
    if not os.path.isfile(SOTA[ds]):
        return out
    for r in csv.DictReader(open(SOTA[ds])):
        if r['method'] != method:
            continue
        v = float(r['ate_posyaw_m']) if r['ate_posyaw_m'] not in ('', 'nan') else math.inf
        if math.isnan(v):
            v = math.inf
        out.setdefault(r['seq'], {})[str(int(r['run']))] = v
    return out


def main():
    status = []
    # ------------------------------------------------------------------ back-end v2 held-out (OpenVINS-based methods)
    for ds in ('t2', 'viode'):
        for met in ('ate', 'rpe'):
            J = load(B[ds][met])
            if J is None:
                status.append(f'missing {B[ds][met]}')
                if met == 'ate':
                    os.makedirs(P + '/tables', exist_ok=True)
                    with open(f'{P}/tables/ho_medians_{ds}.tex', 'w') as f:
                        f.write('% placeholder: held-out table not yet available\n\\HOmissing{table ho-medians-' + ds + '}\n')
                continue
            pre = DS[ds] + ('' if met == 'ate' else 'rpe')
            for r in J['paired']:
                if r['family'] not in ('vs_openvins_v2', 'key_v2', 'v2_vs_v1', 'gain_change'):
                    continue
                if r['group'] not in GT or r['method'] not in MB or r['ref'] not in MB:
                    continue
                fam = {'vs_openvins_v2': '', 'key_v2': '', 'v2_vs_v1': 'v2v1.', 'gain_change': 'dd.'}[r['family']]
                name = MB[r['method']] if r['family'] == 'v2_vs_v1' else f'{MB[r["method"]]}-{MB[r["ref"]]}'
                eff(f'{pre}.{fam}{name}.{GT[r["group"]]}', r)
            if met == 'ate':
                for b in ('v2', 'v1'):
                    for m, gs in J['failures'][b].items():
                        if m in MB:
                            for g, n in gs.items():
                                if g in GT:
                                    put(f'{pre}.fail{"" if b == "v2" else "v1"}.{MB[m]}.{GT[g]}', str(n))
                write_median_table(ds, J)
    # ------------------------------------------------------------------ VINS-Fusion + SAVIOR held-out
    for ds in ('t2', 'viode'):
        for met in ('ate', 'rpe'):
            J = load(V[ds][met])
            if J is None:
                status.append(f'missing {V[ds][met]}')
                continue
            pre = DS[ds] + ('' if met == 'ate' else 'rpe')
            for r in J['paired']:
                if r['group'] in GT and r['method'] in MV and r['ref'] in MV:
                    eff(f'{pre}.{MV[r["method"]]}-{MV[r["ref"]]}.{GT[r["group"]]}', r)
            if met == 'ate':
                for m, gs in J['failures'].items():
                    if m in MV:
                        for g, n in gs.items():
                            if g in GT:
                                put(f'{pre}.fail.{MV[m]}.{GT[g]}', str(n))
    # ------------------------------------------------------------------ cross-back-end table (Table: back-end agnostic)
    for ds in ('t2', 'viode'):
        JB, JV = load(B[ds]['ate']), load(V[ds]['ate'])
        vals = {}
        if JB:
            for m in ('openvins', 'yolo_naive', 'sens_fix1'):
                vals['ov' if m == 'openvins' else 'ov' + MB[m]] = {s: d[m] for s, d in JB['values']['v2'].items()}
        if JV:
            for m in ('vins_fusion', 'vins_ycls', 'vins_savior', 'dynavins'):
                if all(m in d for d in JV['values'].values()):
                    vals[MV[m]] = {s: d[m] for s, d in JV['values'].items()}
        if 'dyna' not in vals:   # DynaVINS held-out runs of M3b (the VINS held-out analysis reuses exactly these runs)
            sv = sota_values(ds, 'dynavins')
            if sv:
                vals['dyna'] = sv
        so = sota_values(ds, 'orbslam3')
        if so:
            vals['orb'] = so
        fail_m = 2.0 if ds == 't2' else 1.0
        for name, per in vals.items():
            for g, sel in groups(ds).items():
                xs = [v for s, d in per.items() if sel(s) for v in d.values()]
                if not xs:
                    continue
                put(f'bt.{DS[ds]}.{name}.{GT[g]}', fnum(gm(xs)))
                put(f'bt.{DS[ds]}.{name}.{GT[g]}.fail', f'{sum(x > fail_m for x in xs)}/{len(xs)}')
        # cross-study paired: OpenVINS v2 + SAVIOR vs DynaVINS; OpenVINS v2 vs VINS-Fusion; OV+SAVIOR vs VINS+SAVIOR
        for a, b in (('ovsavior', 'dyna'), ('ov', 'vins'), ('ovsavior', 'vinssavior'), ('ovsavior', 'vins')):
            if a in vals and b in vals:
                for g, sel in groups(ds).items():
                    A = {(s, i): v for s, d in vals[a].items() if sel(s) for i, v in d.items()}
                    Bv = {(s, i): v for s, d in vals[b].items() if sel(s) for i, v in d.items()}
                    r = paired(A, Bv)
                    if r:
                        eff(f'x.{DS[ds]}.{a}-{b}.{GT[g]}', r, holm=False)
    # ------------------------------------------------------------------ held-out share vs gain (O-Dyn+B and SAVIOR vs OpenVINS, v2)
    share = {}
    if os.path.isfile(SHARE):
        for line in open(SHARE):
            m = re.match(r'\| (\w+) \| ([\d.]+) % \|', line)
            if m:
                share[m.group(1)] = float(m.group(2))
    gains = {}
    for ds in ('t2', 'viode'):
        J = load(B[ds]['ate'])
        if not J:
            continue
        for s, d in J['values']['v2'].items():
            for m in ('oracle_moving_ext', 'sens_fix1'):
                r = paired(d[m], d['openvins'])
                if r:
                    gains.setdefault(m, {})[s] = -r['gm']
    for m, gg in gains.items():
        k = [s for s in gg if s in share]
        if len(k) >= 10:
            rho, p = stats.spearmanr([share[s] for s in k], [gg[s] for s in k])
            put(f'ho.rho.{MB[m]}', f'{rho:.2f}')
            put(f'ho.rho.{MB[m]}.p', f'$p={fp(p)}$')
            put(f'ho.rho.{MB[m]}.n', str(len(k)))
    os.makedirs(P + '/tables', exist_ok=True)
    with open(P + '/ho_gains.json', 'w') as f:
        json.dump({'share_pct': share, 'gain_pct': gains}, f, indent=1)
    # ------------------------------------------------------------------ write
    with open(P + '/ho_values.tex', 'w') as f:
        f.write('% GENERATED by paper/scripts/make_heldout_values.py -- do not edit by hand.\n')
        for k in sorted(VALUES):
            f.write(f'\\HOset{{{k}}}{{{VALUES[k]}}}\n')
    used = set()
    for fn in ('savior_v2.tex', 'savior_supp.tex'):
        if os.path.isfile(f'{P}/{fn}'):
            txt = '\n'.join(re.sub(r'(?<!\\)%.*', '', l) for l in open(f'{P}/{fn}'))  # drop LaTeX comments, keep \\%
            used |= set(re.findall(r'\\HO(?:eff|t|p)?\{([^}]+)\}', txt))
    base = {k for k in VALUES}
    PROSE = {'h1.v2', 'h2.v2', 'h4.v2', 'h5.v2', 'supp.ho2.analysis', 'supp.v1v2.agreement'}  # written by hand in phase 2
    pending = sorted(k for k in used if k not in base and k not in PROSE)
    prose = sorted(k for k in used if k in PROSE and k not in base)
    with open(P + '/ho_status.txt', 'w') as f:
        f.write('\n'.join(status) + '\n')
        f.write(f'# keys used in the manuscript: {len(used)}; set: {len(used) - len(pending)}; pending: {len(pending)}\n')
        f.write('\n'.join(pending) + '\n')
        f.write('# prose items (hand-written in phase 2, from the held-out tables): ' + ' '.join(prose) + '\n')
    print('\n'.join(status))
    print(f'keys set: {len(VALUES)}; used in tex: {len(used)}; pending: {len(pending)}')


def write_median_table(ds, J):
    """Supplement: median ATE per sequence and method, back-end v2 held-out ([n] = failures)."""
    M = ['openvins', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge', 'oracle_class_naive', 'oracle_class_ext',
         'oracle_moving', 'oracle_moving_ext']
    lab = {'openvins': 'OpenVINS', 'yolo_naive': 'Y-Cls', 'sens_fix1': 'SAVIOR', 'p7_nb': 'S-adapt.', 'savior_edge': 'S-edge',
           'oracle_class_naive': 'O-Cls', 'oracle_class_ext': 'O-Cls+B', 'oracle_moving': 'O-Dyn', 'oracle_moving_ext': 'O-Dyn+B'}
    fm = J['fail_m']
    L = ['% GENERATED by paper/scripts/make_heldout_values.py', '\\begin{tabular}{l' + 'r' * len(M) + '}', '\\toprule',
         'Sequence & ' + ' & '.join(lab[m] for m in M) + ' \\\\', '\\midrule']
    for s, d in J['values']['v2'].items():
        cells = []
        for m in M:
            v = list(d.get(m, {}).values())
            if not v:
                cells.append('--')
                continue
            med = float(np.median(np.minimum(v, 1e4)))
            k = sum(x > fm for x in v)
            cells.append((f'{med:.3f}' if med < 10 else f'{med:.0f}') + (f'\\,[{k}]' if k else ''))
        L.append(s.replace('_', ' ') + ' & ' + ' & '.join(cells) + ' \\\\')
    L += ['\\bottomrule', '\\end{tabular}']
    os.makedirs(P + '/tables', exist_ok=True)
    with open(f'{P}/tables/ho_medians_{ds}.tex', 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
