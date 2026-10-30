#!/usr/bin/env python3
"""stats3_tables.py : paper-ready tables from stats3_all.json and viode_diag.json -> results/stats_v3/tables/*.md|json"""
import json
import math

T = '/home/sasa/workspace/savior_ws/results/stats_v3/tables'
J = json.load(open(T + '/stats3_all.json'))
D = json.load(open(T + '/viode_diag.json'))
LAB = J['labels']
COMP = J['comps']
IDX = {(r['comp'], r['ds'], r['group'], str(r['cap'])): r for r in J['results']}
FIDX = {(f['ds'], f['method'], f['group']): f for f in J['failures']}
DSN = {'t2': 'WH', 'viode': 'VIODE'}
GN = J['groups']


def cname(c):
    _, a, b = COMP[c]
    return f'{LAB[a]} vs {LAB[b]}'


def fp(p):
    if p is None:
        return '-'
    if p < 1e-3:
        e = int(math.floor(math.log10(p)))
        return f'{p / 10 ** e:.0f}e{e}'
    return f'{p:.3f}' if p < 0.1 else f'{p:.2f}'


def pc(v):
    return f'{v:+.0f}'


def ci(c):
    return f'[{c[0]:+.0f}, {c[1]:+.0f}]'


def verdict(r, d):
    l = r['lmm']
    hg = r['holm']['global_claims']['lmm']
    lo, hi = r['lmm_ci']
    b_lo, b_hi = r['ci2']
    if d == 0:
        if l['p'] < 0.05:
            return 'NO (a difference is detected)'
        if lo >= -10 and hi <= 10:
            return 'YES (equivalent within +/-10 %)'
        return 'YES as "no detectable difference" (CI wide; not equivalence)'
    right = (r['est'] < 0) == (d < 0)
    if not right:
        return 'NO (direction reversed)'
    if hg < 0.05:
        return 'YES (Holm-global)'
    if l['p'] < 0.05:
        return 'PARTLY (seq-level p<0.05, not after Holm)'
    if (b_hi < 0 or b_lo > 0) or r['p_perm'] <= r['p_perm_min'] + 1e-12:
        return 'WEAK (direction consistent; seq-level CI incl. 0)'
    return 'NO (not supported at sequence level)'


def fcell(ds, m, g):
    f = FIDX.get((ds, m, g))
    return '-' if f is None else f"{f['fails']}/{f['runs']}"


rows, L = [], []
L += ['# Key effects at the sequence level (stats_v3)\n',
      'Unit = sequence (k = 3 static, 6 per level group, 12 all). Effect = geometric-mean ATE ratio - 1 (%) with failures capped '
      'at 10 m; negative = first method better. **seq CI** = LMM t-interval (REML, sequence random intercept, df = k-1); '
      '**boot** = two-stage cluster bootstrap (sequences, then offsets; 20000) percentile CI. p_LMM = LMM t-test; '
      'p_perm = exact sign-flip test on the k per-sequence means (smallest attainable p: 0.25 for k=3, 0.031 for k=6, '
      '0.0005 for k=12); H_glob = Holm over the 31 main-text claims (LMM p). seq +/- = sequences favouring / against the '
      'first method. fail = failures A / B (ATE > 2 m warehouse, > 1 m VIODE). NF = paired ratio on runs where neither '
      'method failed, with two-stage bootstrap CI and n pairs.\n',
      '| claim | comparison | set | group | k | effect | seq CI (LMM) | boot CI | p_LMM | p_perm | H_glob | seq +/- | fail A / B | NF effect [boot] (n) | old run-level [iid CI] p_W | verdict |',
      '|---|---|---|---|--:|--:|---|---|--:|--:|--:|--:|--:|---|---|---|']
for cid, comp, ds, g, txt, d in J['claims']:
    r = IDX[(comp, ds, g, '10.0')]
    e = IDX.get((comp, ds, g, 'excl'))
    _, A, B = COMP[comp]
    v = verdict(r, d)
    nf = '-' if e is None else f"{pc(e['est'])} {ci(e['ci2'])} ({e['n_pairs']})"
    o = r['old']
    L.append(f"| {cid} | {cname(comp)} | {DSN[ds]} | {GN[ds][g]} | {r['n_seq']} | **{pc(r['est'])}** | {ci(r['lmm_ci'])} | "
             f"{ci(r['ci2'])} | {fp(r['lmm']['p'])} | {fp(r['p_perm'])} | {fp(r['holm']['global_claims']['lmm'])} | "
             f"{r['seq_better']}/{r['seq_worse']} | {fcell(ds, A, g)} / {fcell(ds, B, g)} | {nf} | "
             f"{pc(o['est'])} {ci(o['ci'])} {fp(o['p_wilcoxon'])} | {v} |")
    rows.append(dict(claim=cid, text=txt, comp=comp, ds=ds, group=GN[ds][g], k=r['n_seq'], n=r['n_pairs'], est=r['est'],
                     lmm_ci=r['lmm_ci'], boot2_ci=r['ci2'], boot1_ci=r['ci1'], p_lmm=r['lmm']['p'], p_perm=r['p_perm'],
                     p_sign=r['p_sign'], icc=r['lmm']['icc'], holm=r['holm'], seq_pct=r['seq_pct'], scene_pct=r['scene_pct'],
                     seq_better=r['seq_better'], seq_worse=r['seq_worse'], fails=[fcell(ds, A, g), fcell(ds, B, g)],
                     nonfailed=None if e is None else dict(est=e['est'], boot2_ci=e['ci2'], lmm_ci=e['lmm_ci'],
                                                          p_lmm=e['lmm']['p'], n=e['n_pairs'], k=e['n_seq']),
                     old=o, verdict=v, nested=r.get('nested')))
L.append('\nClaim texts:\n')
L += [f'- {c[0]}: {c[4]}' for c in J['claims']]
open(T + '/key_effects.md', 'w').write('\n'.join(L) + '\n')
json.dump(rows, open(T + '/key_effects.json', 'w'), indent=1)

# ------------------------------------------------------------------ compact main-text candidate
MAIN = ['C2', 'C3', 'C4b', 'C6', 'C7', 'C8a', 'C8b', 'C10', 'C11', 'C15', 'C16', 'C17', 'C19', 'C20', 'C21', 'C22', 'C23']
L = ['# Main-text candidate: key effects, sequence level\n',
     'Geometric-mean ATE change (%; failures capped at 10 m), sequence-level 95 % CI (LMM, df = k-1), sequences in favour, '
     'failure counts, and the same ratio on runs where neither method failed. Negative = first method better.\n',
     '| comparison | data | group | k | ATE change [95 % CI] | seq. agreeing with sign | failures A / B | non-failed change [95 % CI] |',
     '|---|---|---|--:|---|--:|--:|---|']
for x in rows:
    if x['claim'] in MAIN:
        nfx = x['nonfailed']
        better = x['seq_better'] if x['est'] < 0 else x['seq_worse']
        nfs = '-' if nfx is None else f"{pc(nfx['est'])} {ci(nfx['lmm_ci'])}"
        L.append(f"| {cname(x['comp'])} | {DSN[x['ds']]} | {x['group']} | {x['k']} | {pc(x['est'])} {ci(x['lmm_ci'])} | "
                 f"{better}/{x['k']} | {x['fails'][0]} / {x['fails'][1]} | {nfs} |")
open(T + '/main_key_effects.md', 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ cap sensitivity
L = ['# Cap sensitivity (sequence-level estimate, LMM 95 % CI, LMM p)\n',
     'Cap = value substituted for failed / diverged runs before the log ratio (warehouse: failure > 2 m, so cap 2 m = '
     '"failure counts as 2 m"); excl = pairs where either run failed are dropped.\n',
     '| claim | comparison | set | group | cap 2 m | cap 5 m | cap 10 m | cap 50 m | failures excluded |',
     '|---|---|---|---|---|---|---|---|---|']
cap_rows = []
for cid, comp, ds, g, txt, d in J['claims']:
    cells = []
    cr = {}
    for c in ('2.0', '5.0', '10.0', '50.0', 'excl'):
        r = IDX.get((comp, ds, g, c))
        if r is None:
            cells.append('-'); continue
        cells.append(f"{pc(r['est'])} {ci(r['lmm_ci'])} p={fp(r['lmm']['p'])}" + ('' if c != 'excl' else f" n={r['n_pairs']}"))
        cr[c] = dict(est=r['est'], lmm_ci=r['lmm_ci'], boot2_ci=r['ci2'], p_lmm=r['lmm']['p'], n=r['n_pairs'])
    cap_rows.append(dict(claim=cid, comp=comp, ds=ds, group=GN[ds][g], caps=cr))
    L.append(f'| {cid} | {cname(comp)} | {DSN[ds]} | {GN[ds][g]} | ' + ' | '.join(cells) + ' |')
open(T + '/cap_sensitivity.md', 'w').write('\n'.join(L) + '\n')
json.dump(cap_rows, open(T + '/cap_sensitivity.json', 'w'), indent=1)

# ------------------------------------------------------------------ Holm families
L = ['# Holm families (cap 10 m)\n',
     'Families: **cell** = all key comparisons within one dataset x level group (static: only comparisons vs the unmasked '
     'back-end); **system** = one system block (OV2 / VINS / cross) within dataset x group; **all-key** = every key comparison '
     'x dataset x group in one family (n = %d); **global** = the 31 main-text claims. Adjusted p from the LMM test; '
     'old = Wilcoxon on pooled runs (original protocol), Holm in the same family for comparison.\n' %
     rows[0]['holm']['all_key']['size'],
     '| claim | comparison | set | group | p_LMM | H cell (size) | H system (size) | H all-key | H global | H global, p_perm | old p_W | old H global |',
     '|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|']
for x in rows:
    h = x['holm']
    L.append(f"| {x['claim']} | {cname(x['comp'])} | {DSN[x['ds']]} | {x['group']} | {fp(x['p_lmm'])} | "
             f"{fp(h['cell']['lmm'])} ({h['cell']['size']}) | {fp(h['system']['lmm'])} ({h['system']['size']}) | "
             f"{fp(h['all_key']['lmm'])} | {fp(h['global_claims']['lmm'])} | {fp(h['global_claims']['perm'])} | "
             f"{fp(x['old']['p_wilcoxon'])} | {fp(h['global_claims']['old'])} |")
open(T + '/holm_families.md', 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ failures
FM = [('ov2:openvins', 'OpenVINS'), ('ov2:yolo_naive', '+Y-Cls'), ('ov2:sens_fix1', '+SAVIOR'), ('ov2:savior_edge', '+SAVIOR-edge'),
      ('ov2:oracle_moving_ext', '+O-Dyn+B'), ('ov2:oracle_class_ext', '+O-Cls+B'), ('ov1:openvins', 'OpenVINS v1'),
      ('ov1:sens_fix1', '+SAVIOR v1'), ('vins_fusion', 'VINS-Fusion'), ('vins_ycls', 'VINS+Y-Cls'), ('vins_savior', 'VINS+SAVIOR'),
      ('vins_odyn', 'VINS+O-Dyn+B'), ('vins_ocls', 'VINS+O-Cls+B'), ('dynavins', 'DynaVINS'), ('orbslam3', 'ORB-SLAM3')]
L = ['# Failure rates with sequence-clustered CIs\n',
     'Cell: failures/runs, rate % [95 % cluster-bootstrap CI over sequences], sequences with >= 1 failure; the per-sequence '
     'counts follow in the list below. Warehouse failure = ATE > 2 m, VIODE > 1 m.\n']
for ds in ('t2', 'viode'):
    L += [f'\n## {DSN[ds]}\n', '| method | ' + ' | '.join(GN[ds][g] for g in ('low', 'high', 'all')) + ' | per-sequence failures (all) |',
          '|---|---|---|---|---|']
    for m, n in FM:
        cs = []
        for g in ('low', 'high', 'all'):
            f = FIDX.get((ds, m, g))
            cs.append('-' if f is None else f"{f['fails']}/{f['runs']} ({100 * f['rate']:.0f} % [{100 * f['ci_cluster'][0]:.0f}, "
                      f"{100 * f['ci_cluster'][1]:.0f}]; {f['n_seq_with_fail']}/{f['n_seq']} seq)")
        f = FIDX.get((ds, m, 'all'))
        ps = ', '.join(f'{s.replace("_t2", "")}:{c}' for s, c in f['per_seq'].items()) if f else ''
        L.append(f'| {n} | ' + ' | '.join(cs) + f' | {ps} |')
L += ['\n## Paired failure comparisons (key pairs)\n',
      'run-level exact McNemar (iid; old view) vs exact sign-flip over the sequences whose failure counts differ (new).\n',
      '| comparison | set | group | fails A / B | p McNemar (runs) | seq. differing | p sign-flip (seq) | per-sequence A-B |',
      '|---|---|---|--:|--:|--:|--:|---|']
for f in J['failure_pairs']:
    if f['fails_A'] + f['fails_B'] == 0 or f['group'] == 'static':
        continue
    L.append(f"| {cname(f['comp'])} | {DSN[f['ds']]} | {GN[f['ds']][f['group']]} | {f['fails_A']} / {f['fails_B']} | "
             f"{fp(f['p_mcnemar_run'])} | {f['n_seq_diff']} | {fp(f['p_signflip_seq'])} | "
             + ', '.join(f'{s.replace("_t2", "")}:{v:+d}' for s, v in f['seq_diff'].items()) + ' |')
open(T + '/failures.md', 'w').write('\n'.join(L) + '\n')

# ------------------------------------------------------------------ VIODE diagnosis
L = ['# VIODE failure diagnosis (failure = ATE > 1 m)\n',
     'Offsets: run k starts at offset_1 + 0.2 (k-1) s; GT motion onset (speed > 0.1 m/s) is %s s after the GT start. '
     'p_late = stratified permutation test (failure labels permuted across offsets within each sequence; one-sided, '
     'later offsets). t_div = time from the first estimated pose until the position error exceeds 1 m after a posyaw '
     'alignment on the first 1 s of the estimate; init = first pose - playback start.\n' %
     ', '.join(f'{k}: {v:.2f}' for k, v in sorted({s.rsplit("_", 1)[0]: D['onset_s'][s] for s in D['onset_s']}.items())),
     '| system | failures | per offset 1..10 | offsets 1-5 / 6-10 | p_late | failing (sequence: offsets) | init delay (s) | t_div median [range] (s) |',
     '|---|--:|---|--:|--:|---|--:|---|']
for n, S in D['systems'].items():
    td = sorted(r['t_div_s'] for r in S['runs'] if r.get('t_div_s') is not None)
    ini = sorted(r['init_delay_s'] for r in S['runs'] if r.get('init_delay_s') is not None)
    tds = '-' if not td else f'{td[len(td) // 2]:.1f} [{td[0]:.1f}, {td[-1]:.1f}]'
    inis = '-' if not ini else f'{ini[len(ini) // 2]:.1f}'
    fs = '; '.join(f'{s}: {",".join(map(str, o))}' for s, o in S['fail_seq_offsets'].items())
    L.append(f"| {n} | {S['fails']} | {' '.join(map(str, S['per_offset']))} | {S['early_1_5']} / {S['late_6_10']} | "
             f"{fp(S['p_perm_late'])} | {fs} | {inis} | {tds} |")
open(T + '/viode_diag.md', 'w').write('\n'.join(L) + '\n')
print('ok')
