#!/usr/bin/env python3
"""rr_args.py <seq> <variant> : savior-run settings of one review-run variant (back-end v2), same output format as
results/backend_v2/scripts/bv2_args.py (INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, launch args).
The base method's lines come unchanged from bv2_args.py (which asserts every frozen md5); only the variant delta of
rr_variants.py is applied to the PSET / OVSET lines. Held-out sequences (t2 / VIODE) require results/review_runs/FREEZE.yaml
(read-only, md5 in FREEZE.md5 verified) listing this variant with identical pset / ov_set strings.
Env RR_FREEZE_OPTIONAL=1 skips the freeze check (only used by rr_check.py to print the settings for the freeze)."""
import hashlib, os, subprocess, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
RR = f'{WS}/results/review_runs'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rr_variants import V  # noqa: E402


def kvparse(s):
    out = {}
    for it in s.split():
        k, _, v = it.partition('=')
        assert k not in out, f'duplicate key {k}'
        out[k] = v
    return out


def fmt(v):
    return ('true' if v else 'false') if isinstance(v, bool) else str(v)


def settings_e(seq, var):
    """E: OpenLORIS / uHumans2 (seq = openloris_<raw> | uhumans2_<raw>), = results/p7/scripts/run_noharm.sh instantiation."""
    F = yaml.safe_load(open(f'{WS}/results/p7/final_config.yaml'))
    assert hashlib.md5(open(f'{WS}/results/p7/final_config.yaml', 'rb').read()).hexdigest() == '6fea24e550b7198659d8de35d19b3c67'
    ds, raw = seq.split('_', 1)
    cfgd = {'openloris': 'openloris_t265', 'uhumans2': 'uhumans2'}[ds]
    Bc = f'{WS}/src/savior/savior_bringup/config'
    cfg = f'{Bc}/{cfgd}/estimator_config.yaml'
    ovset = ' '.join(f'{k}={fmt(x)}' for k, x in F['ov_set'].items())
    kind = V[var]['base']
    launch, pset, args = 'savior.launch.py', {}, []
    coco = F['coco_real_robot']
    assert hashlib.md5(open(f"{WS}/{coco['model']}", 'rb').read()).hexdigest() == coco['model_md5']
    if kind == 'openvins':
        launch = 'baseline.launch.py'
    elif kind == 'savior_none':
        args = ['backend:=none']
    elif kind == 'yolo_naive':
        pset = {k: fmt(x) for k, x in F['methods']['yolo_naive']['savior_node'].items()}
        args = ['backend:=yolo', f"model:={WS}/{coco['model']}", f'roles_file:={Bc}/roles/person_only.yaml']
    elif kind == 'sens_fix1':
        pset = {k: fmt(x) for k, x in F['methods']['sens_fix1']['savior_node'].items()}
        pset.update({k: fmt(x) for k, x in coco['savior_node_overrides'].items()})
        roles = f"{WS}/{coco['roles_file']}"
        assert hashlib.md5(open(roles, 'rb').read()).hexdigest() == coco['roles_md5']
        args = ['backend:=yolo', f"model:={WS}/{coco['model']}", f'roles_file:={roles}']
    elif kind == 'oracle_person':
        assert ds == 'uhumans2'
        pset = {'tracker.enable': 'false', 'extension.enable': 'false',
                'segmenter.colormap_file': f'{WS}/results/p3a/config/uhumans2_colormap_person.yaml'}
        args = ['backend:=oracle_colormap', f'roles_file:={Bc}/roles/person_only.yaml']
    return [f'{WS}/install', launch, cfg, f'{WS}/data/{ds}/ros2/{raw}', f'{WS}/data/{ds}/gt/{raw}.txt', ovset, '',
            ' '.join(f'{k}={x}' for k, x in sorted(pset.items()))] + args


def settings(seq, var):
    v = V[var]
    if v['scope'] == 'E':
        return settings_e(seq, var)
    L = subprocess.run([sys.executable, f'{WS}/results/backend_v2/scripts/bv2_args.py', seq, v['base'], 'v2'], check=True,
                       capture_output=True, text=True).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')
    if v.get('pset_set'):
        assert L[1] == 'savior.launch.py', 'pset delta on a non-savior method'
        p = kvparse(L[7])
        p.update({k: fmt(x) for k, x in v['pset_set'].items()})
        L[7] = ' '.join(f'{k}={x}' for k, x in sorted(p.items()))
    if v.get('ovset_add'):
        o = kvparse(L[5])
        for k, x in v['ovset_add'].items():
            assert k not in o, f'ov_set already has {k}'
            o[k] = fmt(x)
        L[5] = ' '.join(f'{k}={x}' for k, x in o.items())
    return L


if __name__ == '__main__':
    seq, var = sys.argv[1], sys.argv[2]
    heldout = '_t1_' not in seq
    assert '_t3_' not in seq, 't3 is not part of this study'
    if heldout and not os.environ.get('RR_FREEZE_OPTIONAL'):
        fz, fm = f'{RR}/FREEZE.yaml', f'{RR}/FREEZE.md5'
        assert os.path.isfile(fz) and not os.access(fz, os.W_OK), 'FREEZE.yaml missing or writable'
        h = hashlib.md5(open(fz, 'rb').read()).hexdigest()
        assert open(fm).read().split()[0] == h, 'FREEZE.yaml md5 mismatch'
        F = yaml.safe_load(open(fz))
        assert var in F['variants'] and F['variants'][var]['scope'] in ('heldout', 'E'), f'{var} not frozen'
    elif not heldout:
        assert V[var]['scope'] in ('t1', 'heldout'), var
    L = settings(seq, var)
    if heldout and not os.environ.get('RR_FREEZE_OPTIONAL'):
        dom = ('warehouse' if seq.startswith(('aisles_', 'hall_', 'dock_')) else seq.split('_')[0] if V[var]['scope'] == 'E'
               else 'viode')
        fv = F['variants'][var][dom]
        assert fv['pset'] == L[7] and fv['ov_set'] == L[5] and fv['cfg'] == L[2], f'{var}: settings differ from FREEZE.yaml'
    print('\n'.join(L))
