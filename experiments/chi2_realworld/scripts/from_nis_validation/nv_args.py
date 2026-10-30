#!/usr/bin/env python3
"""nv_args.py <seq> <variant> : savior-run settings of one NIS-validation run (one-shot evaluation of the FROZEN self-tuning gate
controls of results/semantic_gate/FREEZE.yaml, md5 0457d646d61995b1de656cdd86ecb5bc: sf1_nis, ov_nis).

Every variant = the FROZEN instantiation of its base method on that dataset, produced by the unchanged frozen argument scripts
(which assert every frozen md5), with exactly the semantic_gate freeze delta:
  INSTALL -> results/semantic_gate/install (read-only SG build)
  OVSET   += savior_nis_gate=true        (sf1_nis, ov_nis; ctl_* = no OVSET delta, md5-identity control)
Base instantiations:
  warehouse t2 / VIODE : results/backend_v2/scripts/bv2_args.py <seq> <base> v2  (BACKEND_VIODE=v2), = review_runs held-out
  OpenLORIS / uHumans2 : results/review_runs/scripts/rr_args.py <seq> e_<base>     (task E, original configs; asserts review FREEZE)
  Monado (MIOxx)       : results/real_world/scripts/rw_args.py <seq> <base>        (asserts real_world FREEZE(+AMENDMENT).md5)
Bases: sf1_nis / ctl_sens_fix1 -> sens_fix1, ov_nis / ctl_openvins -> openvins.
Unless NV_NOFREEZE=1 (only used to write PROTOCOL.yaml), PROTOCOL.yaml must be read-only, match PROTOCOL.md5, and list
identical INSTALL / LAUNCH / CFG / OVSET / PSET / args for this (seq, variant).
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v'."""
import hashlib, os, subprocess, sys
WS = '/home/sasa/workspace/savior_ws'
NV = f'{WS}/results/nis_validation'
SG_INSTALL = f'{WS}/results/semantic_gate/install'
SG_FREEZE_MD5 = '0457d646d61995b1de656cdd86ecb5bc'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
BASE = {'sf1_nis': 'sens_fix1', 'ov_nis': 'openvins', 'ctl_sens_fix1': 'sens_fix1', 'ctl_openvins': 'openvins'}
DELTA = {'sf1_nis': {'savior_nis_gate': 'true'}, 'ov_nis': {'savior_nis_gate': 'true'}, 'ctl_sens_fix1': {}, 'ctl_openvins': {}}


def domain(seq):
    if seq.startswith(('aisles_t2_', 'hall_t2_', 'dock_t2_')):
        return 'warehouse'
    if seq.startswith(('parking_lot_', 'city_day_', 'city_night_')):
        return 'viode'
    if seq.startswith(('openloris_', 'uhumans2_')):
        return 'e'
    if seq in ('MIO13', 'MIO15', 'MIO16', 'MIO07'):
        return 'rw'
    raise SystemExit(f'{seq}: not part of the NIS validation (t1 / t3 excluded)')


def kvparse(s):
    out = {}
    for it in s.split():
        k, _, v = it.partition('=')
        assert k not in out, f'duplicate key {k}'
        out[k] = v
    return out


def base_lines(seq, var):
    d, b = domain(seq), BASE[var]
    env = dict(os.environ, BACKEND_VIODE='v2')
    if d in ('warehouse', 'viode'):
        cmd = [sys.executable, f'{WS}/results/backend_v2/scripts/bv2_args.py', seq, b, 'v2']
    elif d == 'e':
        cmd = [sys.executable, f'{WS}/results/review_runs/scripts/rr_args.py', seq, f'e_{b}']
    else:
        cmd = [sys.executable, f'{WS}/results/real_world/scripts/rw_args.py', seq, b]
    L = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env).stdout
    return (L[:-1] if L.endswith('\n') else L).split('\n')


def settings(seq, var):
    assert var in BASE, var
    if var.startswith('ctl_'):
        assert domain(seq) == 'warehouse', 'md5 controls: warehouse t2 only (bit-deterministic there)'
    assert md5(f'{WS}/results/semantic_gate/FREEZE.yaml') == SG_FREEZE_MD5, 'semantic_gate FREEZE.yaml changed'
    L = base_lines(seq, var)
    assert L[0] == f'{WS}/install', f'unexpected base install {L[0]}'
    assert os.path.isfile(f'{SG_INSTALL}/setup.bash') and not os.access(SG_INSTALL, os.W_OK), 'SG install missing or writable'
    L[0] = SG_INSTALL
    o = kvparse(L[5])
    for k, x in DELTA[var].items():
        assert k not in o, f'ov_set already has {k}'
        o[k] = x
    L[5] = ' '.join(f'{k}={x}' for k, x in o.items())
    return L


if __name__ == '__main__':
    seq, var = sys.argv[1], sys.argv[2]
    L = settings(seq, var)
    if os.environ.get('NV_NOFREEZE') != '1':
        import yaml
        fz = f'{NV}/PROTOCOL.yaml'
        assert os.path.isfile(fz) and not os.access(fz, os.W_OK), 'PROTOCOL.yaml missing or writable'
        assert open(f'{NV}/PROTOCOL.md5').read().split()[0] == md5(fz), 'PROTOCOL.yaml md5 mismatch'
        P = yaml.safe_load(open(fz))
        fv = P['instantiation'][var][seq]
        assert [fv['install'], fv['launch'], fv['cfg'], fv['ov_set'], fv['pset'], fv['launch_args']] == \
            [L[0], L[1], L[2], L[5], L[7], L[8:]], f'{seq} {var}: settings differ from PROTOCOL.yaml'
    print('\n'.join(L))
