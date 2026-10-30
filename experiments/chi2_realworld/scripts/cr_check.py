#!/usr/bin/env python3
"""cr_check.py : parameter-diff check (adapted from results/nis_validation/scripts/nv_check.py).
For every (sequence, variant) the settings produced by cr_args.py are compared field by field with
  (a) every rw_settings_*.txt RECORDED in the paired frozen real-world baseline method dir (ovchi_best vs openvins, sf1_chibest vs
      sens_fix1; results/real_world/runs/<seq>/<base>), and
  (b) the launch command recorded in every baseline run_XX/run_info.yaml (cmd: launch file, config, bag, rate, ov_set, pset, topics,
      backend / model / roles_file, feature_stats, mask_policy, mask_timeout_ms, start_offset = 0.2 (i-1)).
The ONLY allowed difference: OVSET + up_msckf_chi2_multipler=0.25 + up_slam_chi2_multipler=0.25 (INSTALL must be identical =
workspace install/). -> tables/param_diff.json, tables/param_diff.md ; exit 1 on any unexpected difference."""
import glob, json, os, subprocess, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
CR = WS + '/results/chi2_realworld'
RWR = WS + '/results/real_world/runs'
SEQS = ['MIO13', 'MIO15', 'MIO16', 'MIO07']
BASE = {'ovchi_best': 'openvins', 'sf1_chibest': 'sens_fix1'}
ALLOWED = {'up_msckf_chi2_multipler': (None, '0.25'), 'up_slam_chi2_multipler': (None, '0.25')}
FIELDS = ['INSTALL', 'LAUNCH', 'CFG', 'BAG', 'OVSET', 'TOPICS', 'PSET', 'ARGS', 'RATE']
errs, rows = [], []


def mine(seq, var):
    L = subprocess.run([sys.executable, CR + '/scripts/cr_args.py', seq, var], check=True, capture_output=True, text=True,
                       env=dict(os.environ, CR_NOFREEZE='1')).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')
    return dict(INSTALL=L[0], LAUNCH=L[1], CFG=L[2], BAG=L[3], OVSET=L[5], TOPICS=L[6], PSET=L[7], ARGS=' '.join(L[8:]), RATE='0.25')


def kv(s):
    return dict(t.split('=', 1) for t in s.split())


def ovdiff(a, b):
    A, B = kv(a), kv(b)
    return {k: (A.get(k), B.get(k)) for k in sorted(set(A) | set(B)) if A.get(k) != B.get(k)}


for seq in SEQS:
    for var, base in BASE.items():
        M = mine(seq, var)
        bdir = f'{RWR}/{seq}/{base}'
        sfs = sorted(glob.glob(f'{bdir}/rw_settings_*.txt'))
        if not sfs:
            errs.append(f'{seq} {var}: no rw_settings in {bdir}')
        for sf in sfs:
            rec = {}
            for line in open(sf):
                k, _, x = line.rstrip('\n').partition('=')
                rec.setdefault(k, x)
            diff = {}
            for k in FIELDS:
                a, b = rec.get(k, ''), M[k]
                if k == 'OVSET':
                    d = ovdiff(a, b)
                    if d:
                        diff[k] = d
                elif a.split() != b.split():
                    diff[k] = (a, b)
            if rec.get('OVERLAY', ''):
                diff['OVERLAY'] = rec['OVERLAY']
            ok = set(diff) == {'OVSET'} and diff['OVSET'] == ALLOWED
            if not ok:
                errs.append(f'{seq} {var} vs {sf}: {diff}')
            rows.append(dict(kind='rw_settings', seq=seq, variant=var, baseline=os.path.relpath(sf, WS), exact=ok, diff=diff))
        ris = sorted(glob.glob(f'{bdir}/run_*/run_info.yaml'))
        if len(ris) != 10:
            errs.append(f'{seq} {var}: {len(ris)} baseline run_info.yaml (expected 10)')
        for ri in ris:
            i = int(os.path.basename(os.path.dirname(ri)).split('_')[1])
            cmd = yaml.safe_load(open(ri))['cmd']
            assert cmd[:3] == ['ros2', 'launch', 'savior_bringup'], cmd[:3]
            launch = cmd[3]
            C = dict(c.split(':=', 1) for c in cmd[4:])
            exp = dict(config=M['CFG'], bag=M['BAG'], start_offset=f'{0.2 * (i - 1):.1f}', rate='0.25', feature_stats='auto',
                       topics=M['TOPICS'])
            for a in M['ARGS'].split():
                k, _, v = a.partition(':=')
                exp[k] = v
            if M['LAUNCH'] == 'savior.launch.py':
                exp.update(mask_policy='wait', mask_timeout_ms='30000')
                if M['PSET'].strip():
                    exp['pset'] = M['PSET']
            diff = {}
            if launch != M['LAUNCH']:
                diff['launch'] = (launch, M['LAUNCH'])
            for k in sorted(set(C) | set(exp) | {'ov_set'}):
                if k == 'output':
                    if not C[k].endswith(f'/{seq}/{base}/run_{i:02d}/stamped_traj_estimate.txt'):
                        diff[k] = C[k]
                    continue
                if k == 'ov_set':
                    d = ovdiff(C.get('ov_set', ''), M['OVSET'])
                    if d:
                        diff['ov_set'] = d
                    continue
                if C.get(k) != exp.get(k):
                    diff[k] = (C.get(k), exp.get(k))
            ok = set(diff) == {'ov_set'} and diff['ov_set'] == ALLOWED
            if not ok:
                errs.append(f'{seq} {var} vs {ri}: {diff}')
            rows.append(dict(kind='run_info_cmd', seq=seq, variant=var, baseline=os.path.relpath(ri, WS), exact=ok, diff=diff))
os.makedirs(CR + '/tables', exist_ok=True)
json.dump(dict(errors=errs, rows=rows), open(CR + '/tables/param_diff.json', 'w'), indent=1)
L = ['# Parameter-diff check (cr_check.py)\n',
     'Each chi2-realworld setting vs (a) the rw_settings files and (b) the run_info.yaml launch commands recorded in the paired frozen '
     'real-world baseline (ovchi_best vs openvins, sf1_chibest vs sens_fix1). Allowed: OVSET + up_msckf_chi2_multipler=0.25 + '
     'up_slam_chi2_multipler=0.25 only (INSTALL identical: workspace install/).\n',
     f'**{sum(r["exact"] for r in rows)} / {len(rows)} recorded settings: exactly the chi2 delta. Errors: {len(errs)}.**\n',
     '| sequence | variant | rw_settings files (exact) | run_info cmds (exact) |', '|---|---|--:|--:|']
for seq in SEQS:
    for v in BASE:
        a = [r for r in rows if r['seq'] == seq and r['variant'] == v and r['kind'] == 'rw_settings']
        b = [r for r in rows if r['seq'] == seq and r['variant'] == v and r['kind'] == 'run_info_cmd']
        L.append(f"| {seq} | {v} | {len(a)} ({sum(r['exact'] for r in a)}) | {len(b)} ({sum(r['exact'] for r in b)}) |")
L += [''] + [f'- ERROR {e}' for e in errs]
open(CR + '/tables/param_diff.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
sys.exit(1 if errs else 0)
