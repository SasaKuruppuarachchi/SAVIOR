# SPDX-License-Identifier: GPL-3.0-or-later
"""savior_node parameters of a frozen SAVIOR method, rebuilt exactly as savior_bringup/launch/savior.launch.py builds
them for the OpenVINS runs (results/p7/final_config.yaml + final_config_addendum.yaml; the same lookups as
results/m2b_heldout/scripts/m2b_args.py).

    method_params(seq, method) -> dict(install, param_files=[...], overrides={...}, topics=[...], dataset=...)

`param_files` + `overrides` is the list savior.launch.py hands to the savior_node Node action (logged in every run's
launch.log as "[savior] savior_node parameters: [...]"); export_masks.py --check-log compares the two.
Pure python + yaml (no ROS imports)."""
import hashlib
import os

import yaml

WS = os.environ.get('SAVIOR_WS', '/home/sasa/workspace/savior_ws')
FROZEN = f'{WS}/results/p7/final_config.yaml'
ADDENDUM = f'{WS}/results/p7/final_config_addendum.yaml'
FROZEN_MD5 = '6fea24e550b7198659d8de35d19b3c67'
ADDENDUM_MD5 = 'f07c9c30'  # prefix, see results/p7/final_config_addendum.md5
CFG = f'{WS}/src/savior/savior_bringup/config'

# savior.launch.py PERCEPTION_IO (warehouse, warehouse_moving, viode)
PERCEPTION_IO = {
    'viode': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw', 'seg_topic': '/cam0/segmentation',
              'colormap': '', 'imu_topic': '/imu0'},
    'warehouse': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw', 'seg_topic': '/cam0/segmentation',
                  'colormap': 'oracle/warehouse_colormap.yaml', 'imu_topic': '/imu0'},
    'warehouse_moving': {'left_topic': '/cam0/image_raw', 'right_topic': '/cam1/image_raw',
                         'seg_topic': '/cam0/segmentation_moving', 'colormap': 'oracle/warehouse_colormap_moving.yaml',
                         'imu_topic': '/imu0'},
}


def _md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def _ab(p):
    return p if p.startswith('/') else f'{WS}/{p}'


def parse_kv(text):
    """= baseline.launch.py parse_kv: 'a=1 b.c=false' -> {'a': 1, 'b.c': False} (YAML scalars)."""
    out = {}
    for item in text.split():
        k, sep, v = item.partition('=')
        if not sep or not k:
            raise RuntimeError(f'expected key=value, got "{item}"')
        out[k] = yaml.safe_load(v) if v != '' else ''
    return out


def kv(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        out.append(f'{k}={v}')
    return ' '.join(out)


def is_viode(seq):
    return not any(seq.startswith(s) for s in ('aisles_', 'hall_', 'dock_'))


def static_mask0(config_path):
    """= savior.launch.py static_mask0 (OpenVINS mask0 when use_mask: true; used only with motion.enable)."""
    import re
    try:
        text = open(config_path).read()
    except OSError:
        return ''
    if not re.search(r'^use_mask:\s*true', text, re.M):
        return ''
    m = re.search(r'^mask0:\s*"?([^"#\s]+)"?', text, re.M)
    if not m:
        return ''
    path = os.path.join(os.path.dirname(config_path), m.group(1))
    return path if os.path.isfile(path) else ''


def method_settings(seq, method):
    """Frozen launch settings of one method (subset of m2b_args.py): install, cfg, bag, backend, dataset,
    perception_params, model, roles_file, pset, topics."""
    assert _md5(FROZEN) == FROZEN_MD5, 'frozen config changed'
    assert _md5(ADDENDUM).startswith(ADDENDUM_MD5), 'frozen addendum changed'
    F = yaml.safe_load(open(FROZEN))
    A = yaml.safe_load(open(ADDENDUM))
    s = dict(install=f'{WS}/install', backend='', dataset='', perception_params='', model='', roles_file='')
    if not is_viode(seq):
        s['cfg'] = _ab(F['protocol']['estimator_config'])
        s['bag'] = f'{WS}/data/warehouse/ros2_stereoseg/{seq}'
        topics = '/cam0/image_raw /cam1/image_raw /imu0 /tf_static'
        if method == 'savior_edge':
            m = A['savior_edge']['warehouse']
            s['install'] = _ab(A['savior_edge']['install'])
            s.update(backend='yolo', perception_params=_ab(m['perception_params']), model=_ab(m['model']),
                     roles_file=_ab(m['roles_file']))
            s['pset'] = m['pset']
            s['ov_set_extra'] = m['ov_set_extra']
        else:
            m = F['methods'][method]
            s['pset'] = kv(m.get('savior_node', {}))
            for k in ('backend', 'dataset'):
                s[k] = m.get(k, '')
            for k in ('perception_params', 'model', 'roles_file'):
                s[k] = _ab(m[k]) if m.get(k) else ''
            if m.get('extra_topics'):
                topics += ' ' + m['extra_topics']
    else:
        V = A['viode']
        env = seq.rsplit('_', 1)[0]
        s['cfg'] = _ab(V['estimator_config'])
        s['bag'] = f'{WS}/data/viode/ros2/{seq}'
        topics = V['topics']
        m = V['methods'][method]
        if m.get('install'):
            s['install'] = _ab(m['install'])
        s['pset'] = m.get('pset', '').replace('{env}', env)
        s['backend'] = m.get('backend', '')
        for k in ('model', 'roles_file'):
            s[k] = _ab(m[k]) if m.get(k) else ''
        if m.get('ov_set_extra'):
            s['ov_set_extra'] = m['ov_set_extra']
        if m.get('extra_topics'):
            topics += ' ' + m['extra_topics']
    s['topics'] = topics.split()
    return s


def method_params(seq, method):
    """savior_node parameter list exactly as savior.launch.py builds it (function build())."""
    s = method_settings(seq, method)
    install = s['install']
    share_bringup = f'{install}/savior_bringup/share/savior_bringup'
    share_perc = f'{install}/savior_perception/share/savior_perception'
    config_path = s['cfg']
    cfg_name = os.path.basename(os.path.dirname(os.path.abspath(config_path)))   # resolve_config(file)
    dataset = s['dataset'] or cfg_name
    io = PERCEPTION_IO.get(dataset, {})
    calib = os.path.join(os.path.dirname(config_path), 'kalibr_imucam_chain.yaml')
    files = []
    pp = s['perception_params'] or os.path.join(share_perc, 'config', 'default.yaml')
    files.append(pp)
    ds_pp = os.path.join(os.path.dirname(config_path), 'savior_perception.yaml')
    if not s['perception_params'] and os.path.isfile(ds_pp):
        files.append(ds_pp)
    over = {'calib_file': calib, 'cam_left': 'cam0', 'cam_right': 'cam1',
            'roles_file': s['roles_file'] or os.path.join(share_bringup, 'config', 'roles', 'coco_indoor.yaml'),
            'mask_left_topic': '/savior/mask/left', 'mask_right_topic': '/savior/mask/right',
            'publish_debug': False, 'use_sim_time': False}
    for k in ('left_topic', 'right_topic', 'imu_topic'):
        if io.get(k):
            over[k] = io[k]
    sm = static_mask0(config_path)
    if sm:
        over['motion.static_mask_file'] = sm
    backend = s['backend']
    if backend:
        over['segmenter.backend'] = backend
    if io.get('colormap'):
        over['segmenter.colormap_file'] = os.path.join(share_bringup, 'config', io['colormap'])
    if backend.startswith('oracle') and io.get('seg_topic'):
        over['seg_topic'] = io['seg_topic']
    if s['model']:
        over['segmenter.model'] = s['model']
    over.update(parse_kv(s['pset']))
    if not backend and os.path.isfile(ds_pp):   # backend from the dataset params file (launch does the same)
        backend = ((yaml.safe_load(open(ds_pp)) or {}).get('savior_node', {}).get('ros__parameters', {})
                   .get('segmenter', {}).get('backend', ''))
    return dict(install=install, param_files=files, overrides=over, topics=s['topics'], dataset=dataset,
                backend=backend, bag=s['bag'], settings=s)


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(method_params(sys.argv[1], sys.argv[2]), indent=1, default=str))
