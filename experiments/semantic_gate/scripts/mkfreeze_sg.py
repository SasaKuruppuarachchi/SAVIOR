#!/usr/bin/env python3
"""mkfreeze_sg.py : write results/semantic_gate/FREEZE.yaml (selected SAVIOR-SG point + the NIS control) from the t1 analysis
(tables/ate_t1.json, pre-declared rule of GRID.yaml). The caller writes FREEZE.md5 and makes both read-only.
Records exact settings (sg_args.py output for warehouse), config / code / install md5s and the image id."""
import datetime, glob, hashlib, json, os, subprocess, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
SG = f'{WS}/results/semantic_gate'
sys.path.insert(0, f'{SG}/scripts')
from sg_variants import V  # noqa: E402


def md5(p):
    return hashlib.md5(open(p if p.startswith('/') else f'{WS}/{p}', 'rb').read()).hexdigest()


def tree(rel, pats):
    h = hashlib.md5()
    fs = sorted(f for p in pats for f in glob.glob(f'{WS}/{rel}/{p}', recursive=True) if '__pycache__' not in f)
    for f in fs:
        h.update(os.path.relpath(f, WS).encode())
        h.update(open(f, 'rb').read())
    return {'md5': h.hexdigest(), 'n_files': len(fs), 'files': f'{rel}/' + ','.join(pats)}


def settings(var):
    L = subprocess.run([sys.executable, f'{SG}/scripts/sg_args.py', 'hall_t1_L3', var], check=True, capture_output=True, text=True).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')   # keep an empty PSET line (OpenVINS base)
    return {'install': L[0], 'launch': L[1], 'cfg': L[2], 'ov_set': L[5], 'pset': L[7], 'launch_args': L[8:]}


def grid_rule():
    """selection_rule text of GRID.yaml, verbatim (GRID.yaml is read-only and not strictly valid YAML: an unquoted ': ' in
    method.perception, line 17; its text and md5 are unchanged)"""
    lines, out = open(f'{SG}/GRID.yaml').read().split('\n'), []
    i = next(k for k, l in enumerate(lines) if l.startswith('selection_rule:'))
    for l in lines[i + 1:]:
        if not l.startswith('  '):
            break
        out.append(l.strip())
    return ' '.join(out)


A = json.load(open(f'{SG}/tables/ate_t1.json'))
sel = A['selected']
res = {(r['family'], r['method'], r['ref'], r['group']): r for r in A['paired']}


def eff(m, ref, g):
    r = res.get(('vs_openvins' if ref == 'openvins' else 'vs_sens_fix1' if ref == 'sens_fix1' else 'vs_ovchi_best', m, ref, g))
    return None if r is None else {'gm_pct': round(r['gm'], 2), 'ci': [round(c, 1) for c in r['ci']], 'holm': r['holm'],
                                   'wins': r['wins'], 'losses': r['losses']}


def entry(var, role):
    src = A['alias'].get(var, var)
    return {'role': role, 'label': V[var]['label'], 'variant': var, 't1_result_of': src, 'base': V[var]['base'],
            'pset_set': V[var].get('pset_set', {}), 'ovset_add': V[var].get('ovset_add', {}), 'warehouse_t1_instantiation': settings(var),
            't1_failures': A['failures'][src]['all'],
            't1_vs_openvins_v2': {g: eff(src, 'openvins', g) for g in ('all', 'L0', 'L0+L1', 'L2+L3', 'hall_L3')},
            't1_vs_sens_fix1': {g: eff(src, 'sens_fix1', g) for g in ('all', 'L0', 'L0+L1', 'L2+L3', 'hall_L3')}
            if V[var]['base'] == 'sens_fix1' else None}


img = os.environ['SAVIOR_IMAGE_ID']   # docker image inspect --format '{{.Id}}' savior:humble-cuda12.8 (host)
F = {
    'status': 'FROZEN - SAVIOR-SG t1 selection (pre-declared rule, GRID.yaml) and the NIS control; NO held-out run was made. '
              'Any held-out evaluation is the coordinator\'s decision and must use exactly these settings.',
    'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'frozen_by': 'semantic-gate agent',
    'grid': {'path': 'results/semantic_gate/GRID.yaml', 'md5': md5(f'{SG}/GRID.yaml')},
    'selection': {'rule': grid_rule(), 'table': A['selection'], 'selected': sel,
                  'tie_note': 'All 8 points pass the constraints and are within 0.011 pp of each other (m_s = 0.25: -49.183 %, m_s = 0.5: '
                              '-49.172 %), i.e. the rule picks m_s = 0.25 on a negligible margin. m_b is inert (GRID run_plan check passed: '
                              '80/80 md5-identical, 0 band-labelled chi2 tests). keep_band true and false are md5-identical in 80/80 t1 runs; '
                              'this tie between two m_b = m_s points is not covered by the pre-declared tie-break; it is resolved post hoc to '
                              'keep_band = false (the default, first in the declared grid order), which cannot change any t1 number.'},
    'methods': ({'savior_sg': entry(sel, 'selected SAVIOR-SG configuration')} if sel else {}) |
               {'sf1_nis': entry('sf1_nis', 'non-semantic self-tuning control on SAVIOR (NIS-adaptive gate)'),
                'ov_nis': entry('ov_nis', 'non-semantic self-tuning control on OpenVINS-v2 (NIS-adaptive gate)')},
    'caveat': 'Selected on warehouse t1, the split on which SAVIOR (sens_fix1), the back-end v2 and the chi2 x0.25 value were also '
              'tuned: every t1 number is optimistic. m_b / keep_band act only on 192 band pixels, which the frozen SAVIOR pset never '
              'produces (extension.enable=false).',
    'references': {
        'backend_config': {'path': 'results/backend_v2/backend_config.yaml', 'md5': md5('results/backend_v2/backend_config.yaml')},
        'final_config': {'path': 'results/p7/final_config.yaml', 'md5': md5('results/p7/final_config.yaml')},
        'final_config_addendum': {'path': 'results/p7/final_config_addendum.yaml', 'md5': md5('results/p7/final_config_addendum.yaml')},
        'estimator_v2_warehouse': md5('results/backend_v2/config/warehouse/estimator_config.yaml'),
        'estimator_v2_viode': md5('results/backend_v2/config/viode/estimator_config.yaml'),
    },
    'install': {'path': 'results/semantic_gate/install', 'built_by': 'results/semantic_gate/scripts/build_sg.sh (Release, no symlink-install)',
                'run_subscribe_msckf_md5': md5(f'{SG}/install/ov_msckf/lib/ov_msckf/run_subscribe_msckf'),
                'libov_msckf_lib_md5': md5(f'{SG}/install/ov_msckf/lib/libov_msckf_lib.so'),
                'libov_core_lib_md5': md5(f'{SG}/install/ov_core/lib/libov_core_lib.so'),
                'note': 'the frozen workspace install/ (pre-SG code) is untouched; pre-SG source snapshot in source/src_savior_pre_sg.tgz'},
    'code': {
        'savior_perception': tree('src/savior/savior_perception/savior_perception', ['**/*.py']),
        'savior_perception_default_yaml': md5('src/savior/savior_perception/config/default.yaml'),
        'savior_bringup_launch': tree('src/savior/savior_bringup/launch', ['*.py']),
        'ov_msckf_fork': tree('src/savior/open_vins/ov_msckf/src', ['**/*.cpp', '**/*.h']),
        'ov_core_fork': tree('src/savior/open_vins/ov_core/src', ['**/*.cpp', '**/*.h']),
        'changed_files': {f: md5(f) for f in [
            'src/savior/savior_perception/savior_perception/core/types.py', 'src/savior/savior_perception/savior_perception/core/config.py',
            'src/savior/savior_perception/savior_perception/core/compose.py', 'src/savior/savior_perception/savior_perception/core/pipeline.py',
            'src/savior/savior_perception/config/default.yaml', 'src/savior/open_vins/ov_core/src/feat/Feature.h',
            'src/savior/open_vins/ov_core/src/feat/FeatureDatabase.h', 'src/savior/open_vins/ov_core/src/feat/FeatureDatabase.cpp',
            'src/savior/open_vins/ov_core/src/track/TrackBase.h', 'src/savior/open_vins/ov_core/src/track/TrackBase.cpp',
            'src/savior/open_vins/ov_core/src/track/TrackKLT.cpp', 'src/savior/open_vins/ov_msckf/src/update/SaviorGate.h',
            'src/savior/open_vins/ov_msckf/src/update/UpdaterOptions.h', 'src/savior/open_vins/ov_msckf/src/update/UpdaterMSCKF.h',
            'src/savior/open_vins/ov_msckf/src/update/UpdaterMSCKF.cpp', 'src/savior/open_vins/ov_msckf/src/update/UpdaterSLAM.h',
            'src/savior/open_vins/ov_msckf/src/update/UpdaterSLAM.cpp', 'src/savior/open_vins/ov_msckf/src/core/VioManagerOptions.h',
            'src/savior/open_vins/ov_msckf/src/core/VioManager.cpp']},
        'scripts': {os.path.relpath(f, WS): md5(f) for f in sorted(glob.glob(f'{SG}/scripts/*.py') + glob.glob(f'{SG}/scripts/*.sh'))},
    },
    'image': {'tag': 'savior:humble-cuda12.8', 'id': img},
    'protocol': 'rate 0.5, 10 start offsets 0.0..1.8 s, mask_policy wait (30 s), feature_stats auto, ov_set deterministic_processing=true '
                'dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0 (+ the method delta), failure > 2 m, cap 10 m '
                '(scripts/run_sg.sh; held-out instantiation = the same delta on the frozen held-out instantiation of the base method)',
}
yaml.safe_dump(F, open(f'{SG}/FREEZE.yaml', 'w'), sort_keys=False, width=140, allow_unicode=True)
print(open(f'{SG}/FREEZE.yaml').read())
