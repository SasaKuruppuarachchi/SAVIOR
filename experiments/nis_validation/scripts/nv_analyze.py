#!/usr/bin/env python3
"""nv_analyze.py [--include-invalid] : paired statistics of the NIS validation (PROTOCOL.yaml statistics section).
Run level: paired per-offset log ATE ratio (cap 10 m), geometric-mean ratio - 1, iid bootstrap 95 % CI (20000, seed 0), Wilcoxon,
Holm within dataset x group x family (primary / secondary). Sequence level: stats_v3 boot_two_stage + signflip (imported).
Primary: pairs with an invalid run on either side (tables/invalid*.txt from nv_audit.py) are excluded; --include-invalid keeps them.
Sensitivity 'fail-excl': pairs with a failure on either side excluded. RPE: shortest sub-length mean, pairs where both runs are not
failures and have RPE segments. Lambda: tables/audit.csv columns (nv_audit.py).
-> tables/results[_inclinvalid].md / .json"""
import csv, json, math, os, sys
import numpy as np, yaml
from scipy import stats
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/stats_v3/scripts')
from stats3_core import boot_two_stage, signflip  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nv_plan import CAP, DATASETS, NV, baseline_dir, run_dir  # noqa: E402
INC = '--include-invalid' in sys.argv
TAG = '_inclinvalid' if INC else ''
LAB = {'sf1_nis': 'SAVIOR+NIS', 'ov_nis': 'OpenVINS+NIS', 'openvins': 'OpenVINS', 'sens_fix1': 'SAVIOR', 'yolo_naive': 'Y-Cls',
       'ovchi_best': 'OV-chi2x0.25', 'sf1_chibest': 'SAVIOR+chi2x0.25', 'vins_fusion': 'VINS-Fusion'}
lev = lambda s: s.rsplit('_', 1)[-1]  # noqa: E731
WG = {'all': None, 'L0': ['L0'], 'L1': ['L1'], 'L2': ['L2'], 'L3': ['L3'], 'L0+L1': ['L0', 'L1'], 'L2+L3': ['L2', 'L3'],
      'hall_L3': ['hall_t2_L3'], 'dock_L3': ['dock_t2_L3'], 'hall+dock_L3': ['hall_t2_L3', 'dock_t2_L3']}
VG = {'all': None, 'none': ['none'], 'low': ['low'], 'mid': ['mid'], 'high': ['high'], 'none+low': ['none', 'low'], 'mid+high': ['mid', 'high'],
      'low+mid+high': ['low', 'mid', 'high']}
OLH = [f'openloris_{s}' for s in ('cafe1-2', 'office1-1', 'office1-2', 'office1-3', 'office1-4', 'office1-5', 'office1-6', 'office1-7')]
UH = [f'uhumans2_office_s1_{h}' for h in ('00h', '06h', '12h')]
PRIM4 = [('sf1_nis', 'sens_fix1'), ('sf1_nis', 'ovchi_best'), ('sf1_nis', 'openvins'), ('ov_nis', 'openvins')]
PRIM3 = [('sf1_nis', 'sens_fix1'), ('sf1_nis', 'openvins'), ('ov_nis', 'openvins')]
SEC_WV = [('sf1_nis', 'yolo_naive'), ('sf1_nis', 'sf1_chibest'), ('ov_nis', 'ovchi_best')]
A = {  # analysis dataset -> (plan dataset, sequences, groups, primary, secondary)
    'warehouse_t2': ('warehouse_t2', DATASETS['warehouse_t2']['seqs'], WG, PRIM4, SEC_WV),
    'viode': ('viode', DATASETS['viode']['seqs'], VG, PRIM4, SEC_WV),
    'openloris': ('openloris_uhumans2', ['openloris_cafe1-1'] + OLH,
                  {'heldout (8)': OLH, 'cafe1-1': ['openloris_cafe1-1'], 'all (9)': ['openloris_cafe1-1'] + OLH}, PRIM3, [('sf1_nis', 'yolo_naive')]),
    'uhumans2': ('openloris_uhumans2', UH, {'all': UH, '06h+12h': UH[1:], '00h': UH[:1], '06h': UH[1:2], '12h': UH[2:]}, PRIM3,
                 [('sf1_nis', 'yolo_naive')]),
    'monado': ('monado', DATASETS['monado']['seqs'], {'person': ['MIO13', 'MIO15', 'MIO16'], 'MIO13': ['MIO13'], 'MIO15': ['MIO15'],
                                                        'MIO16': ['MIO16'], 'static MIO07': ['MIO07']}, PRIM3,
               [('sf1_nis', 'yolo_naive'), ('sf1_nis', 'vins_fusion')]),
}
inv = set()
for fn, own in (('invalid.txt', True), ('invalid_baselines.txt', False)):
    p = f'{NV}/tables/{fn}'
    for l in (open(p) if os.path.isfile(p) else []):
        a, s, m, r = l.split()
        inv.add((s, m, int(r[4:])))
AUD = list(csv.DictReader(open(f'{NV}/tables/audit.csv')))


def insel(s, sel):
    return sel is None or s in sel or lev(s) in sel


def load(pds, m, seq):
    d = run_dir(pds, m, seq) if m in ('sf1_nis', 'ov_nis') else baseline_dir(pds, m, seq)
    fn = f'{d}/eval/eval_summary.yaml'
    ate, rpe = {}, {}
    if os.path.isfile(fn):
        for t in yaml.safe_load(open(fn)).get('trials', []):
            i = int(t['name'].split('_')[1])
            if t.get('status') != 'ok':
                ate[i], rpe[i] = math.inf, math.nan; continue
            ate[i] = float(t['ate']['trans_m']['rmse'])
            ks = sorted(t.get('rpe', {}), key=float)
            r0 = t['rpe'][ks[0]]['trans_m'] if ks else {}
            rpe[i] = float(r0['mean']) if ks and int(r0.get('num_samples', 1)) > 0 and float(r0.get('mean', 0)) > 0 else math.nan
    if not INC:
        for i in list(ate):
            if (seq, m, i) in inv:
                ate.pop(i); rpe.pop(i, None)
    return ate, rpe


def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); adj = np.empty_like(ps); run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


pc = lambda v: 100 * (math.exp(v) - 1)  # noqa: E731


def summ(Dm, Dr, seqs, mode, FAIL):
    by = {}
    for s in seqs:
        a, b = Dm.get(s, {}), Dr.get(s, {})
        x = []
        for i in sorted(set(a) & set(b)):
            if mode == 'fail-excl' and (a[i] > FAIL or b[i] > FAIL):
                continue
            if mode == 'rpe':
                continue
            x.append(math.log(min(a[i], CAP) / min(b[i], CAP)))
        if x:
            by[s] = np.array(x)
    return by


def stat(by):
    if not by:
        return None
    x = np.concatenate(list(by.values()))
    if x.size < 3:
        return None
    nz = x[np.abs(x) > 1e-12]
    p = float(stats.wilcoxon(nz).pvalue) if nz.size >= 2 else 1.0
    ci = np.percentile(np.random.default_rng(0).choice(x, (20000, x.size)).mean(axis=1), [2.5, 97.5])
    out = dict(n=int(x.size), k=len(by), gm=pc(x.mean()), ci=[pc(c) for c in ci], p=p, wins=int((x < -1e-12).sum()), losses=int((x > 1e-12).sum()),
               per_seq={s: pc(v.mean()) for s, v in by.items()})
    if len(by) >= 2:
        sm = np.array([v.mean() for v in by.values()])
        bt = np.percentile(boot_two_stage(by), [2.5, 97.5])
        sf = signflip(sm)
        out['seq'] = dict(est=pc(sm.mean()), ci=[pc(c) for c in bt], p_signflip=sf[0], p_min=sf[1], wins=int((sm < -1e-12).sum()),
                          losses=int((sm > 1e-12).sum()), k=len(by))
    return out


RES, OUT = {}, {}
L = [f"# NIS validation results{' (INCLUDING invalid runs: sensitivity)' if INC else ''}\n",
     'Paired by sequence and start offset with the frozen baseline runs. Cells: run-level geometric-mean ATE ratio - 1 [iid bootstrap 95 % CI], '
     'Holm-adjusted Wilcoxon p (H; within dataset x group x family), wins/losses of paired offsets | sequence level (stats_v3): estimate '
     '[two-stage cluster bootstrap CI], exact sign-flip p (sf; min 2/2^k), sequences better/worse. Negative = first method better. '
     f"{'Invalid runs kept.' if INC else 'Pairs with an invalid run on either side excluded.'} Failures capped at 10 m.\n"]
for an, (pds, seqs, groups, prim, sec) in A.items():
    FAIL = DATASETS[pds]['fail']
    ms = sorted({m for c in prim + sec for m in c}, key=lambda m: list(LAB).index(m))
    ATE, RPE = {}, {}
    for m in ms:
        for s in seqs:
            ATE.setdefault(m, {})[s], RPE.setdefault(m, {})[s] = load(pds, m, s)
    res = []
    for fam, items in (('primary', prim), ('secondary', sec)):
        for g, sel in groups.items():
            gs = [s for s in seqs if insel(s, sel)]
            rs = []
            for m, ref in items:
                r = stat(summ(ATE[m], ATE[ref], gs, 'ate', FAIL))
                if r:
                    r.update(method=m, ref=ref, group=g, family=fam); rs.append(r)
            for r, h in zip(rs, holm([r['p'] for r in rs]) if rs else []):
                r['holm'] = float(h)
            res += rs
            # sensitivity (failures excluded) and RPE, same family Holm
            for mode in ('fail-excl', 'rpe'):
                rs2 = []
                for m, ref in items:
                    if mode == 'rpe':
                        by = {}
                        for s in gs:
                            a, b, aa, bb = RPE[m][s], RPE[ref][s], ATE[m][s], ATE[ref][s]
                            x = [math.log(a[i] / b[i]) for i in sorted(set(a) & set(b)) if aa[i] <= FAIL and bb[i] <= FAIL
                                 and math.isfinite(a[i]) and math.isfinite(b[i])]
                            if x:
                                by[s] = np.array(x)
                        r = stat(by)
                    else:
                        r = stat(summ(ATE[m], ATE[ref], gs, mode, FAIL))
                    if r:
                        r.update(method=m, ref=ref, group=g, family=fam, mode=mode); rs2.append(r)
                for r, h in zip(rs2, holm([r['p'] for r in rs2]) if rs2 else []):
                    r['holm'] = float(h)
                RES.setdefault(an, {}).setdefault(mode, []).extend(rs2)
    RES.setdefault(an, {})['ate'] = res

    def cell(r):
        if r is None:
            return '-'
        s = f"{r['gm']:+.1f} % [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] H={r['holm']:.2g} {r['wins']}/{r['losses']}"
        q = r.get('seq')
        if q:
            s += f" \\| seq {q['est']:+.1f} % [{q['ci'][0]:+.0f}, {q['ci'][1]:+.0f}] sf={q['p_signflip']:.2g} {q['wins']}/{q['losses']}"
        return f'**{s}**' if r['holm'] < 0.05 else s

    L += [f'\n# {an} (failure > {FAIL:g} m)\n', f'## ATE median [m] per sequence (n paired-valid runs; [k] failures)\n',
          '| seq | ' + ' | '.join(LAB[m] for m in ms) + ' |', '|---|' + '--:|' * len(ms)]
    for s in seqs:
        cs = []
        for m in ms:
            v = list(ATE[m][s].values())
            cs.append('-' if not v else f"{float(np.median(np.minimum(v, 1e4))):.3f}" + (f' [{sum(x > FAIL for x in v)}]' if any(x > FAIL for x in v) else '')
                      + ('' if len(v) == len(DATASETS[pds]['seqs']) * 0 + (5 if s.endswith('00h') else 10) else f' (n={len(v)})'))
        L.append(f'| {s} | ' + ' | '.join(cs) + ' |')
    L += [f'\n## Failures (ATE > {FAIL:g} m) / runs\n', '| group | ' + ' | '.join(LAB[m] for m in ms) + ' |', '|---|' + '--:|' * len(ms)]
    fl = {}
    for g, sel in groups.items():
        gs = [s for s in seqs if insel(s, sel)]
        row = []
        for m in ms:
            v = [x for s in gs for x in ATE[m][s].values()]
            fl[(g, m)] = (sum(x > FAIL for x in v), len(v)); row.append(f'{fl[(g, m)][0]}/{len(v)}')
        L.append(f'| {g} | ' + ' | '.join(row) + ' |')
    for mode, title in (('ate', 'ATE'), ('fail-excl', 'ATE, failures excluded (sensitivity)'), ('rpe', 'RPE (shortest sub-length, non-failed pairs)')):
        for fam, items in (('primary', prim), ('secondary', sec)):
            L += [f'\n## {title}: {fam} comparisons\n', '| comparison | ' + ' | '.join(groups) + ' |', '|---|' + '---|' * len(groups)]
            for m, ref in items:
                L.append(f'| {LAB[m]} vs {LAB[ref]} | ' + ' | '.join(cell(next((r for r in RES[an][mode] if r['family'] == fam and r['method'] == m
                                                                          and r['ref'] == ref and r['group'] == g), None)) for g in groups) + ' |')
    # per-sequence effects of the primary comparisons (all-sequence group)
    g0 = list(groups)[0]
    L += [f'\n## Per-sequence effect (run-level gm %, group {g0})\n', '| comparison | ' + ' | '.join(s for s in seqs if insel(s, groups[g0])) + ' |',
          '|---|' + '--:|' * sum(1 for s in seqs if insel(s, groups[g0]))]
    for m, ref in prim + sec:
        r = next((r for r in RES[an]['ate'] if r['method'] == m and r['ref'] == ref and r['group'] == g0), None)
        if r:
            L.append(f'| {LAB[m]} vs {LAB[ref]} | ' + ' | '.join(f"{r['per_seq'][s]:+.0f}" if s in r['per_seq'] else '-' for s in seqs if insel(s, groups[g0])) + ' |')
    # lambda
    L += ['\n## Learned NIS lambda (per run: median of the [SAVIOR-GATE] lines; clamp [0.05, 20])\n',
          '| group | variant | runs | MSCKF median [IQR] | MSCKF at 0.05 / at 20 | SLAM median [IQR] | SLAM at 0.05 / at 20 | MSCKF chi2 reject | SLAM chi2 reject |',
          '|---|---|--:|---|---|---|---|--:|--:|']
    lam = {}
    for g, sel in groups.items():
        gs = [s for s in seqs if insel(s, sel)]
        for v in ('sf1_nis', 'ov_nis'):
            rr = [r for r in AUD if r['own'] == '1' and r['method'] == v and r['seq'] in gs and r['dataset'] == pds and (INC or r['valid'] == '1')]
            if not rr:
                continue
            q = lambda k: [float(r[k]) for r in rr if r[k] != '']  # noqa: E731
            pr = lambda x: f"{np.median(x):.3f} [{np.percentile(x, 25):.3f}, {np.percentile(x, 75):.3f}]" if x else '-'  # noqa: E731
            fr = lambda a, b: f"{100 * np.mean(q(a)):.0f} % / {100 * np.mean(q(b)):.0f} %" if q(a) else '-'  # noqa: E731
            mr = lambda k: f"{100 * np.mean(q(k)):.1f} %" if q(k) else '-'  # noqa: E731
            lam[f'{g}|{v}'] = dict(n=len(rr), msckf_med=float(np.median(q('lam_med_msckf'))) if q('lam_med_msckf') else None,
                                   slam_med=float(np.median(q('lam_med_slam'))) if q('lam_med_slam') else None,
                                   msckf_lo=float(np.mean(q('lam_lo_msckf'))) if q('lam_lo_msckf') else None,
                                   msckf_hi=float(np.mean(q('lam_hi_msckf'))) if q('lam_hi_msckf') else None,
                                   slam_lo=float(np.mean(q('lam_lo_slam'))) if q('lam_lo_slam') else None,
                                   slam_hi=float(np.mean(q('lam_hi_slam'))) if q('lam_hi_slam') else None)
            L.append(f"| {g} | {LAB[v]} | {len(rr)} | {pr(q('lam_med_msckf'))} | {fr('lam_lo_msckf', 'lam_hi_msckf')} | {pr(q('lam_med_slam'))} | "
                     f"{fr('lam_lo_slam', 'lam_hi_slam')} | {mr('rej_frac_msckf')} | {mr('rej_frac_slam')} |")
    OUT[an] = dict(results=RES[an], failures={f'{g}|{m}': v for (g, m), v in fl.items()}, lam=lam,
                   values={m: {s: {str(i): x for i, x in ATE[m][s].items()} for s in seqs} for m in ms})
open(f'{NV}/tables/results{TAG}.md', 'w').write('\n'.join(L) + '\n')
json.dump(OUT, open(f'{NV}/tables/results{TAG}.json', 'w'), indent=1, default=str)
print('\n'.join(L))
