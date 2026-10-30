#!/usr/bin/env python3
"""bv2_args.py <seq> <method> [v1|v2] : savior-run settings of one method x sequence for the OpenVINS back-end v1 or v2.

Perception / savior_node / ov_set settings come ONLY from the frozen files (results/p7/final_config.yaml md5 6fea24e5...,
final_config_addendum.yaml md5 f07c9c30...) through the unchanged results/m2b_heldout/scripts/m2b_args.py; the two no-band
oracles (oracle_moving = O-Dyn, oracle_class_naive = O-Cls) from results/backend_v2/backend_config.yaml (P6 / P5 definitions).
Back-end v2 replaces ONLY the CFG line by results/backend_v2/config/<warehouse|viode>/estimator_config.yaml (md5 asserted).
Back-end for VIODE: env BACKEND_VIODE (default = the requested back-end).
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v'."""
import hashlib, os, subprocess, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
BV2 = f'{WS}/results/backend_v2'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
assert md5(f'{WS}/results/p7/final_config.yaml') == '6fea24e550b7198659d8de35d19b3c67', 'frozen config changed'
assert md5(f'{WS}/results/p7/final_config_addendum.yaml') == 'f07c9c30f29a775c243d2a6ae00b9a45', 'frozen addendum changed'
C = yaml.safe_load(open(f'{BV2}/backend_config.yaml'))
seq, method = sys.argv[1], sys.argv[2]
backend = sys.argv[3] if len(sys.argv) > 3 else 'v2'
viode = not any(seq.startswith(s) for s in ('aisles_', 'hall_', 'dock_'))
dom = 'viode' if viode else 'warehouse'
if viode:
    backend = os.environ.get('BACKEND_VIODE', backend)
assert backend in ('v1', 'v2'), backend
F = C['files'][dom]


def ab(p):
    return p if p.startswith('/') else f'{WS}/{p}'


if method in C['methods']['extra_oracles_no_band']:
    m = C['methods']['extra_oracles_no_band'][method][dom]
    assert md5(ab(m['roles_file'])) == m['roles_md5'], 'roles changed'
    env = seq.rsplit('_', 1)[0]
    if viode:
        bag, gt, topics = f'{WS}/data/viode/ros2/{seq}', f'{WS}/data/viode/gt/{seq}.txt', '/cam0/image_raw /cam1/image_raw /imu0'
    else:
        bag, gt = f'{WS}/data/warehouse/ros2_stereoseg/{seq}', f'{WS}/data/warehouse/gt/{seq}.txt'
        topics = '/cam0/image_raw /cam1/image_raw /imu0 /tf_static'
    F7 = yaml.safe_load(open(f'{WS}/results/p7/final_config.yaml'))
    ovset = ' '.join(f"{k}={'true' if v is True else 'false' if v is False else v}" for k, v in F7['ov_set'].items())
    L = [f'{WS}/install', m['launch'], ab(F['estimator_config_v1']['path']), bag, gt, ovset, topics + ' ' + m['extra_topics'],
         m['pset'].replace('{env}', env)]
    L += [f"backend:={m['backend']}"] + ([f"dataset:={m['dataset']}"] if m.get('dataset') else []) + [f"roles_file:={ab(m['roles_file'])}"]
else:
    L = subprocess.run([sys.executable, f'{WS}/results/m2b_heldout/scripts/m2b_args.py', seq, method], check=True,
                       capture_output=True, text=True).stdout
    L = L[:-1].split('\n') if L.endswith('\n') else L.split('\n')
assert L[2] == ab(F['estimator_config_v1']['path']), f'unexpected v1 CFG {L[2]}'
assert md5(L[2]) == F['estimator_config_v1']['md5']
if backend == 'v2':
    L[2] = ab(F['estimator_config_v2']['path'])
    assert md5(L[2]) == F['estimator_config_v2']['md5'], 'v2 estimator changed'
    d = os.path.dirname(L[2])
    for fn, h in F.get('verbatim_copies', {}).items():
        assert md5(f'{d}/{fn}') == h, f'{fn} copy changed'
print('\n'.join(L))
