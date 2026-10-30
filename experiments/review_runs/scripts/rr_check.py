#!/usr/bin/env python3
"""rr_check.py [--json out] : parameter diff of every review variant vs its frozen base (and the A ablations vs sens_fix1),
per domain (warehouse: hall_t1_L2 / hall_t2_L2, VIODE: city_day_mid), from the resolved savior-run settings (rr_args.settings).
Asserts that each diff is EXACTLY the intended delta (no other pset / ov_set / CFG / launch / args change), and that the C
reuse settings (gate_fix1 == sens_fix1, gate_k3 == p7_nb up to the explicit default gating.k_sigma=3.0) hold."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['RR_FREEZE_OPTIONAL'] = '1'
from rr_args import settings, kvparse, fmt  # noqa: E402
from rr_variants import V, REUSE_T1  # noqa: E402
WS = '/home/sasa/workspace/savior_ws'


def base_lines(seq, m):
    out = subprocess.run([sys.executable, f'{WS}/results/backend_v2/scripts/bv2_args.py', seq, m, 'v2'], check=True,
                         capture_output=True, text=True, env={**os.environ, 'BACKEND_VIODE': 'v2'}).stdout
    return (out[:-1] if out.endswith('\n') else out).split('\n')


def diff(a, b):
    """a, b: settings line lists -> dict of differences."""
    d = {}
    for i, name in enumerate(('install', 'launch', 'cfg', 'bag', 'gt')):
        if a[i] != b[i]:
            d[name] = (a[i], b[i])
    for i, name in ((5, 'ov_set'), (7, 'pset')):
        pa, pb = kvparse(a[i]), kvparse(b[i])
        for k in sorted(set(pa) | set(pb)):
            if pa.get(k) != pb.get(k):
                d[f'{name}.{k}'] = (pa.get(k), pb.get(k))
    if a[6] != b[6]:
        d['topics'] = (a[6], b[6])
    if a[8:] != b[8:]:
        d['args'] = (a[8:], b[8:])
    return d


res = {}
ok = True
for var, v in V.items():
    if v['scope'] == 'E':
        continue
    seqs = {'warehouse': 'hall_t1_L2'} if v['scope'] == 't1' else {'warehouse': 'hall_t2_L2', 'viode': 'city_day_mid'}
    for dom, seq in seqs.items():
        L, B = settings(seq, var), base_lines(seq, v['base'])
        d = diff(B, L)
        want = {f'pset.{k}': fmt(x) for k, x in v.get('pset_set', {}).items()}
        want.update({f'ov_set.{k}': fmt(x) for k, x in v.get('ovset_add', {}).items()})
        got = {k: b for k, (a, b) in d.items()}
        # keys that are set to the value they already had produce no diff (e.g. gate_k3 k_sigma=3.0 explicit)
        exact = all(k in want and want[k] == g for k, g in got.items()) and all(
            got.get(k) == w or kvparse(B[7 if k.startswith('pset') else 5]).get(k.split('.', 1)[1]) == w for k, w in want.items())
        ok &= exact
        res[f'{var}/{dom}'] = {'base': v['base'], 'diff_vs_base': {k: list(x) for k, x in d.items()}, 'exact_intended': exact}
        print(f"{var:14s} {dom:9s} vs {v['base']:9s}: {'OK ' if exact else 'BAD'} {d}")
# C reuse identity (warehouse t1)
for var, m in REUSE_T1.items():
    d = diff(base_lines('hall_t1_L2', m), settings('hall_t1_L2', var))
    same = all(k == 'pset.gating.k_sigma' and x == (None, '3.0') for k, x in d.items())
    ok &= same
    res[f'reuse/{var}=={m}'] = {'diff': {k: list(x) for k, x in d.items()}, 'parameter_identical': same}
    print(f'reuse {var} == {m}: {"OK" if same else "BAD"} {d}')
# E: COCO instantiation vs the frozen warehouse keys (only the coco_real_robot override may differ) and vs P7 stage-D runs
for var, m in (('e_sens_fix1', 'sens_fix1'), ('e_yolo_naive', 'yolo_naive')):
    pe, pw = kvparse(settings('openloris_cafe1-2', var)[7]), kvparse(base_lines('hall_t2_L2', m)[7])
    d = {k: (pw.get(k), pe.get(k)) for k in set(pe) | set(pw) if pe.get(k) != pw.get(k)}
    want = {'selective.prior_static_classes': ('box,pallet,trolley', 'chair,suitcase,backpack,handbag,cart')} if m == 'sens_fix1' else {}
    ok &= d == want
    res[f'E/{var}'] = {'diff_vs_frozen_warehouse': {k: list(x) for k, x in d.items()}, 'exact_intended': d == want}
    print(f'{var} vs frozen warehouse {m}: {"OK" if d == want else "BAD"} {d}')
import yaml as _y
ri = _y.safe_load(open(f'{WS}/results/p7/noharm/openloris_cafe1-1/yolo_naive/run_01/run_info.yaml'))
pn = kvparse(next(a for a in ri['cmd'] if a.startswith('pset:='))[6:])
pe = kvparse(settings('openloris_cafe1-1', 'e_yolo_naive')[7])
print('e_yolo_naive == P7 stage-D yolo_naive pset:', pn == pe)
ok &= pn == pe
if '--json' in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
print('ALL EXACT' if ok else 'SOME DIFF NOT AS INTENDED')
sys.exit(0 if ok else 1)
