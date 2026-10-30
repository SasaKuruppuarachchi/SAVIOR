#!/usr/bin/env python3
"""m2b_args.py <seq> <method> : print the savior-run settings of one M2b method x sequence, read ONLY from the frozen files
  results/p7/final_config.yaml (md5 6fea24e5...) - warehouse instantiation of the 7 frozen methods, and
  results/p7/final_config_addendum.yaml        - SAVIOR-edge (warehouse + VIODE) and the VIODE instantiation of all methods.
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v' (one per line).
Host python (yaml). Env ADDENDUM= overrides the addendum path (only for the pre-freeze verification runs)."""
import hashlib, os, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
FROZEN = f'{WS}/results/p7/final_config.yaml'
ADD = os.environ.get('ADDENDUM', f'{WS}/results/p7/final_config_addendum.yaml')
B = f'{WS}/src/savior/savior_bringup/config'
assert hashlib.md5(open(FROZEN, 'rb').read()).hexdigest() == '6fea24e550b7198659d8de35d19b3c67', 'frozen config changed'
F = yaml.safe_load(open(FROZEN))
seq, method = sys.argv[1], sys.argv[2]
viode = not any(seq.startswith(s) for s in ('aisles_', 'hall_', 'dock_'))
A = yaml.safe_load(open(ADD)) if (viode or method == 'savior_edge') else {}


def kv(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        out.append(f'{k}={v}')
    return ' '.join(out)


def ab(p):
    return p if p.startswith('/') else f'{WS}/{p}'


install = f'{WS}/install'
ovset = kv(F['ov_set'])
largs = []
if not viode:
    cfg = ab(F['protocol']['estimator_config'])
    bag, gt = f'{WS}/data/warehouse/ros2_stereoseg/{seq}', f'{WS}/data/warehouse/gt/{seq}.txt'
    topics = '/cam0/image_raw /cam1/image_raw /imu0 /tf_static'
    if method == 'savior_edge':
        m = A['savior_edge']['warehouse']
        install = ab(A['savior_edge']['install'])
        ovset += ' ' + m['ov_set_extra']
        pset = m['pset']
        largs += ['backend:=yolo', f"perception_params:={ab(m['perception_params'])}", f"model:={ab(m['model'])}",
                  f"roles_file:={ab(m['roles_file'])}"]
        launch = 'savior.launch.py'
    else:
        m = F['methods'][method]
        launch = m['launch']
        pset = kv(m.get('savior_node', {}))
        if m.get('backend'):
            largs.append(f"backend:={m['backend']}")
        if m.get('dataset'):
            largs.append(f"dataset:={m['dataset']}")
        if m.get('perception_params'):
            largs.append(f"perception_params:={ab(m['perception_params'])}")
        if m.get('model'):
            largs.append(f"model:={ab(m['model'])}")
        if m.get('roles_file'):
            largs.append(f"roles_file:={ab(m['roles_file'])}")
        if m.get('extra_topics'):
            topics += ' ' + m['extra_topics']
else:
    V = A['viode']
    env = seq.rsplit('_', 1)[0]
    cfg = ab(V['estimator_config'])
    bag, gt = f'{WS}/data/viode/ros2/{seq}', f'{WS}/data/viode/gt/{seq}.txt'
    topics = V['topics']
    m = V['methods'][method]
    launch = m['launch']
    if m.get('install'):
        install = ab(m['install'])
    if m.get('ov_set_extra'):
        ovset += ' ' + m['ov_set_extra']
    pset = m.get('pset', '').replace('{env}', env)
    for k in ('backend', 'model', 'roles_file'):
        if m.get(k):
            largs.append(f"{k}:={ab(m[k]) if k != 'backend' else m[k]}")
    if m.get('extra_topics'):
        topics += ' ' + m['extra_topics']
print(install); print(launch); print(cfg); print(bag); print(gt); print(ovset); print(topics); print(pset)
for a in largs:
    print(a)
