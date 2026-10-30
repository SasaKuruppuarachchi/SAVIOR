#!/usr/bin/env python3
"""nv_check.py : parameter-diff check. For every (dataset, sequence, variant) the settings produced by nv_args.py are compared
field by field with the settings file RECORDED in the paired frozen baseline run directory (bv2_settings_* / rr_settings_* /
rw_settings_*: sf1_nis vs sens_fix1, ov_nis vs openvins). The only allowed differences: INSTALL (frozen install/ -> the read-only
SG install) and OVSET (+ savior_nis_gate=true). Also checks that the semantic_gate FREEZE.yaml delta of sf1_nis / ov_nis is exactly
ovset_add {savior_nis_gate: true}, pset_set {} and that its warehouse t1 instantiation has the same pset / ov_set as produced here.
-> tables/param_diff.json, tables/param_diff.md ; exit 1 on any unexpected difference."""
import glob, json, os, subprocess, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nv_plan import DATASETS, NV, WS, R, VARIANTS  # noqa: E402
F = yaml.safe_load(open(R + '/semantic_gate/FREEZE.yaml'))
errs, rows = [], []
for v in VARIANTS:
    fm = F['methods'][v]
    if not (fm['ovset_add'] == {'savior_nis_gate': True} and fm['pset_set'] == {} and fm['warehouse_t1_instantiation']['install'] == R + '/semantic_gate/install'):
        errs.append(f'freeze delta of {v} is not exactly savior_nis_gate=true: {fm}')
FIELDS = ['INSTALL', 'LAUNCH', 'CFG', 'BAG', 'OVSET', 'TOPICS', 'PSET', 'ARGS']


def nv(seq, var):
    L = subprocess.run([sys.executable, NV + '/scripts/nv_args.py', seq, var], check=True, capture_output=True, text=True,
                       env=dict(os.environ, NV_NOFREEZE='1')).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')
    return dict(INSTALL=L[0], LAUNCH=L[1], CFG=L[2], BAG=L[3], OVSET=L[5], TOPICS=L[6], PSET=L[7], ARGS=' '.join(L[8:]))


for ds, D in DATASETS.items():
    for seq in D['seqs']:
        for var in VARIANTS:
            mine = nv(seq, var)
            bdir = f"{D['ref_root']}/{seq}/{D['base_dir'][var]}"
            sfs = sorted(glob.glob(f"{bdir}/{D['settings_glob']}"))
            if not sfs:
                errs.append(f'{ds} {seq} {var}: no recorded settings in {bdir}'); continue
            for sf in sfs:
                rec = {}
                for line in open(sf):
                    k, _, x = line.rstrip('\n').partition('=')
                    rec.setdefault(k, x)
                diff = {}
                for k in FIELDS:
                    a, b = rec.get(k, ''), mine[k]
                    if k == 'OVSET':
                        A = dict(t.split('=', 1) for t in a.split()); B = dict(t.split('=', 1) for t in b.split())
                        d = {kk: (A.get(kk), B.get(kk)) for kk in set(A) | set(B) if A.get(kk) != B.get(kk)}
                        if d:
                            diff[k] = d
                    elif a.split() != b.split():
                        diff[k] = (a, b)
                ok = (set(diff) == {'INSTALL', 'OVSET'} and diff['INSTALL'] == (WS + '/install', R + '/semantic_gate/install')
                      and diff['OVSET'] == {'savior_nis_gate': (None, 'true')})
                if not ok:
                    errs.append(f'{ds} {seq} {var} vs {sf}: {diff}')
                rows.append(dict(dataset=ds, seq=seq, variant=var, baseline_settings=os.path.relpath(sf, WS), exact=ok, diff=diff))
            if ds == 'warehouse_t2':
                t1 = F['methods'][var]['warehouse_t1_instantiation']
                if not (t1['ov_set'] == mine['OVSET'] and t1['pset'] == mine['PSET'] and t1['cfg'] == mine['CFG'] and t1['launch'] == mine['LAUNCH']
                        and ' '.join(t1['launch_args']) == mine['ARGS']):
                    errs.append(f'{seq} {var}: differs from the semantic_gate freeze warehouse t1 instantiation')
os.makedirs(NV + '/tables', exist_ok=True)
json.dump(dict(errors=errs, rows=rows), open(NV + '/tables/param_diff.json', 'w'), indent=1)
L = ['# Parameter-diff check (nv_check.py)\n',
     'Each NIS-validation setting vs the settings file recorded in the paired frozen baseline run directory. Allowed: INSTALL '
     f'install/ -> results/semantic_gate/install, OVSET + savior_nis_gate=true.\n',
     f'**{sum(r["exact"] for r in rows)} / {len(rows)} settings files: exactly the NIS delta. Errors: {len(errs)}.**\n',
     '| dataset | variant | baseline settings files | exact |', '|---|---|--:|--:|']
for ds in DATASETS:
    for v in VARIANTS:
        rr = [r for r in rows if r['dataset'] == ds and r['variant'] == v]
        L.append(f"| {ds} | {v} | {len(rr)} | {sum(r['exact'] for r in rr)} |")
L += [''] + [f'- ERROR {e}' for e in errs]
open(NV + '/tables/param_diff.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
sys.exit(1 if errs else 0)
