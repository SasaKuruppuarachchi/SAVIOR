#!/usr/bin/env python3
"""rw_args.py <seq> <method> : savior-run settings of one method x sequence of the real-world study (Monado MSD, Valve Index).

Method definitions (launch, backend, model, roles, pset, ov_set) come ONLY from the frozen files
  results/p7/final_config.yaml          (md5 6fea24e5...)  -> ov_set
  results/p7/final_config_addendum.yaml (md5 f07c9c30...)  -> section viode.methods = the frozen COCO instantiation
exactly as for VIODE (roles viode_vehicles_potential / viode_vehicles_dynamic, YOLO26s-seg COCO engine, sens_fix1 pset).
Only the dataset I/O changes: CFG = src/savior/savior_bringup/config/monado_index/estimator_config.yaml (back-end v2 rule),
BAG = data/monado/ros2/<seq>, GT = data/monado/gt/<seq>.txt, TOPICS = /cam0/image_raw /cam1/image_raw /imu0.
Every file is md5-checked against results/real_world/FREEZE.md5 (written before any evaluation run).
diag_openvins = openvins launched with the P5 diagnostic overlay (feature-fate log; same estimator).
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v'."""
import hashlib
import os
import sys

import yaml

WS = '/home/sasa/workspace/savior_ws'
RW = f'{WS}/results/real_world'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
assert md5(f'{WS}/results/p7/final_config.yaml') == '6fea24e550b7198659d8de35d19b3c67', 'frozen config changed'
assert md5(f'{WS}/results/p7/final_config_addendum.yaml') == 'f07c9c30f29a775c243d2a6ae00b9a45', 'frozen addendum changed'
if os.environ.get('RW_NOFREEZE') != '1':
    # FREEZE.md5 (pre-registration), superseded per file by FREEZE_AMENDMENT.md5 (documented in FREEZE_AMENDMENT.txt)
    FZ = {}
    for fz in (f'{RW}/FREEZE.md5', f'{RW}/FREEZE_AMENDMENT.md5'):
        for line in (open(fz) if os.path.isfile(fz) else []):
            line = line.strip()
            if line and not line.startswith('#'):
                h, p = line.split(None, 1)
                FZ[p] = h
    for p, h in FZ.items():
        assert md5(f'{WS}/{p}') == h, f'frozen file changed: {p}'
F = yaml.safe_load(open(f'{WS}/results/p7/final_config.yaml'))
A = yaml.safe_load(open(f'{WS}/results/p7/final_config_addendum.yaml'))
seq, method = sys.argv[1], sys.argv[2]
SEQS = ('MIO13', 'MIO15', 'MIO16', 'MIO07')
assert seq in SEQS, seq
METHODS = ('openvins', 'savior_none', 'yolo_naive', 'sens_fix1', 'diag_openvins')
assert method in METHODS, method


def ab(p):
    return p if p.startswith('/') else f'{WS}/{p}'


ovset = ' '.join(f"{k}={'true' if v is True else 'false' if v is False else v}" for k, v in F['ov_set'].items())
m = A['viode']['methods']['openvins' if method == 'diag_openvins' else method]
cfg = f'{WS}/src/savior/savior_bringup/config/monado_index/estimator_config.yaml'
bag, gt = f'{WS}/data/monado/ros2/{seq}', f'{WS}/data/monado/gt/{seq}.txt'
topics = '/cam0/image_raw /cam1/image_raw /imu0'
install = ab(m['install']) if m.get('install') else f'{WS}/install'
if m.get('ov_set_extra'):
    ovset += ' ' + m['ov_set_extra']
pset = m.get('pset', '')
assert '{env}' not in pset
largs = []
for k in ('backend', 'model', 'roles_file'):
    if m.get(k):
        largs.append(f"{k}:={ab(m[k]) if k != 'backend' else m[k]}")
if m.get('roles_file'):
    assert md5(ab(m['roles_file'])) == m['roles_md5'], 'roles changed'
assert not m.get('extra_topics')
print(install); print(m['launch']); print(cfg); print(bag); print(gt); print(ovset); print(topics); print(pset)
for a in largs:
    print(a)
