#!/usr/bin/env python3
"""pkg_args.py <seq> <method> : savior-run settings of one method x sequence, read ONLY from the packaged frozen files
  ws/results/p7/final_config.yaml          (md5 6fea24e550b7198659d8de35d19b3c67): openvins, yolo_naive, sens_fix1
  ws/results/p7/final_config_addendum.yaml (md5 f07c9c30f29a775c243d2a6ae00b9a45): savior_edge (warehouse)
Same resolution as results/m2b_heldout/scripts/m2b_args.py (warehouse branch), with WS = this package's ws/.
Refuses anything but the two packaged t1 tuning sequences.
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v' (one per line).
Env (x86 smoke test only): SJ_INSTALL_MAIN, SJ_INSTALL_EDGE, SJ_MODEL_S, SJ_MODEL_N replace the install / engine paths."""
import hashlib, os, sys
import yaml
WS = os.environ.get('SAVIOR_WS') or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ws')
FROZEN = f'{WS}/results/p7/final_config.yaml'
ADD = f'{WS}/results/p7/final_config_addendum.yaml'
assert hashlib.md5(open(FROZEN, 'rb').read()).hexdigest() == '6fea24e550b7198659d8de35d19b3c67', 'frozen config changed'
assert hashlib.md5(open(ADD, 'rb').read()).hexdigest() == 'f07c9c30f29a775c243d2a6ae00b9a45', 'frozen addendum changed'
F = yaml.safe_load(open(FROZEN))
A = yaml.safe_load(open(ADD))
seq, method = sys.argv[1], sys.argv[2]
if seq not in ('hall_t1_L3', 'aisles_t1_L2'):
    sys.exit(f'refusing {seq}: this package only contains hall_t1_L3 and aisles_t1_L2 (t1 tuning split)')
# v2 (on-device validation 2026-10-24): C++ savior_node (savior_perception_cpp, results/cpp_port, md5-identical to the Python
# node on the desktop) for the two frozen pipelines: same frozen settings + perception_impl:=cpp, overlay ws/cpp_port/install
# (savior_perception_cpp + the perception_impl savior_bringup of results/cpp_port/source_git 237640ee) on top of the method's install.
CPP = {'savior_cpp': 'sens_fix1', 'savior_edge_cpp': 'savior_edge'}
if method not in ('openvins', 'yolo_naive', 'sens_fix1', 'savior_edge') + tuple(CPP):
    sys.exit(f'unknown method {method}')
cpp = method in CPP
method = CPP.get(method, method)


def kv(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        out.append(f'{k}={v}')
    return ' '.join(out)


def ab(p):
    p = p if p.startswith('/') else f'{WS}/{p}'
    over = {f'{WS}/models/warehouse/yolo26s-seg-warehouse.engine': os.environ.get('SJ_MODEL_S'),
            f'{WS}/frozen_edge/models/yolo26n-seg-warehouse-672.engine': os.environ.get('SJ_MODEL_N'),
            f'{WS}/install': os.environ.get('SJ_INSTALL_MAIN'), f'{WS}/frozen_edge/install': os.environ.get('SJ_INSTALL_EDGE')}
    return over.get(p) or p


install = ab('install')
ovset = kv(F['ov_set'])
largs = []
cfg = ab(F['protocol']['estimator_config'])
# v2: SJ_BACKEND=v2 -> the re-frozen OpenVINS back-end (results/backend_v2/backend_config.yaml md5 10c2144b...: track_frequency
# 10.5, max_clones 15; the v2 directory = v2 estimator yaml + verbatim copies of the frozen warehouse files; same for SAVIOR-edge)
if os.environ.get('SJ_BACKEND', 'v1') == 'v2':
    cfg = ab('results/backend_v2/config/warehouse/estimator_config.yaml')
    assert hashlib.md5(open(cfg, 'rb').read()).hexdigest() == '2abf884b5d4ea0ec1074c92e4fbd0952', 'backend v2 estimator changed'
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
if cpp:
    install = install + '+' + ab('cpp_port/install')
    largs.append('perception_impl:=cpp')
print(install); print(launch); print(cfg); print(bag); print(gt); print(ovset); print(topics); print(pset)
for a in largs:
    print(a)
