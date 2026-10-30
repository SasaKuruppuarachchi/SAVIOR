#!/usr/bin/env python3
"""mkaddendum.py [verification.json] : write results/p7/final_config_addendum.yaml (M2b addendum pre-registration).
Adds SAVIOR-edge (warehouse + VIODE), the VIODE instantiation of every frozen method (P5 settings + the frozen pipeline
parameters, no tuning), the M2b validity rule and the analysis plan. Host python (yaml). The caller freezes it:
md5sum final_config_addendum.yaml > final_config_addendum.md5."""
import datetime, glob, hashlib, json, os, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
P = WS + '/results/p7'
B = 'src/savior/savior_bringup/config'
FE = 'frozen_edge'
F = yaml.safe_load(open(P + '/final_config.yaml'))
EM = json.load(open(WS + '/results/edge_study/edge_methods.json'))
VER = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}


def md5(rel):
    return hashlib.md5(open(rel if rel.startswith('/') else f'{WS}/{rel}', 'rb').read()).hexdigest()


def tree(root, rel, pats):
    h = hashlib.md5()
    fs = sorted(f for p in pats for f in glob.glob(f'{root}/{rel}/{p}', recursive=True) if '__pycache__' not in f)
    for f in fs:
        h.update(os.path.relpath(f, root).encode()); h.update(open(f, 'rb').read())
    return {'md5': h.hexdigest(), 'n_files': len(fs), 'files': f'{rel}/' + ','.join(pats)}


def kv(d):
    return ' '.join(f"{k}={('true' if v else 'false') if isinstance(v, bool) else v}" for k, v in d.items())


def install_hash(root):
    """md5 over the installed python + launch + executables of the frozen_edge install (relative paths + content)."""
    h = hashlib.md5(); n = 0
    for f in sorted(glob.glob(f'{WS}/{root}/**/*', recursive=True)):
        if os.path.isdir(f) or '__pycache__' in f or f.endswith('.pyc'):
            continue
        if not (f.endswith(('.py', '.so', '.yaml', '.xml')) or '/lib/ov_msckf/' in f or '/lib/savior_' in f):
            continue
        h.update(os.path.relpath(f, f'{WS}/{root}').encode()); h.update(open(f, 'rb').read()); n += 1
    return {'md5': h.hexdigest(), 'n_files': n,
            'files': f'{root}/**/*.py,*.so,*.yaml,*.xml + lib/ov_msckf/*, lib/savior_*/* (relative path + content)'}


import subprocess
commit = subprocess.run(['git', '-C', f'{WS}/{FE}/src/savior', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', '-C', f'{WS}/{FE}/src/savior', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
assert commit and not dirty, 'frozen_edge source must be committed and clean'

E = EM['e_c_n672_L250dfronly']
edge_pset = E['pset']
edge_ov = E['ov']
main_wh = F['methods']['sens_fix1']['savior_node']
# SAVIOR-edge = the frozen main + segmenter.imgsz=672 (= the main's perception_params value, redundant) ...
pe = dict(t.split('=', 1) for t in edge_pset.split())
pm = {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in main_wh.items()}
diff = {k: v for k, v in pe.items() if pm.get(k) != v}
assert diff == {'segmenter.imgsz': '672'} and set(pm) <= set(pe), diff

COCO_S = 'models/yolo26s-seg.engine'
COCO_N = f'{FE}/models/yolo26n-seg-coco640.engine'
WH_N = f'{FE}/models/yolo26n-seg-warehouse-672.engine'
ORACLE_V = 'extension.enable=true tracker.enable=false compose.right_fallback=median'
CMAP = f'segmenter.colormap_file={WS}/{B}/oracle/viode_{{env}}_colormap.yaml'
vm = {
    'openvins': {'launch': 'baseline.launch.py'},
    'savior_none': {'launch': 'savior.launch.py', 'backend': 'none'},
    'oracle_moving_ext': {'launch': 'savior.launch.py', 'backend': 'oracle_colormap', 'roles_file': f'{B}/roles/viode_oracle_dynamic.yaml',
                          'extra_topics': '/cam0/segmentation', 'pset': f'{ORACLE_V} {CMAP}',
                          'roles_md5': md5(f'{B}/roles/viode_oracle_dynamic.yaml'),
                          'note': 'P5 oracle_dynamic GT moving-vehicle masks + the frozen O-Dyn+B pipeline (band, no tracker, warped right mask)'},
    'oracle_class_ext': {'launch': 'savior.launch.py', 'backend': 'oracle_colormap', 'roles_file': f'{B}/roles/viode_oracle_all_vehicles.yaml',
                         'extra_topics': '/cam0/segmentation', 'pset': f'{ORACLE_V} {CMAP}',
                         'roles_md5': md5(f'{B}/roles/viode_oracle_all_vehicles.yaml'),
                         'note': 'P5 oracle_all_vehicles GT class masks (all vehicles) + the frozen O-Cls+B pipeline'},
    'yolo_naive': {'launch': 'savior.launch.py', 'backend': 'yolo', 'model': COCO_S, 'roles_file': f'{B}/roles/viode_vehicles_dynamic.yaml',
                   'pset': kv(F['methods']['yolo_naive']['savior_node']), 'roles_md5': md5(f'{B}/roles/viode_vehicles_dynamic.yaml'),
                   'note': 'naive class masking: person + all vehicle classes dynamic (P5 yolo_naive roles), frozen Y-Cls savior_node keys'},
    'sens_fix1': {'launch': 'savior.launch.py', 'backend': 'yolo', 'model': COCO_S, 'roles_file': f'{B}/roles/viode_vehicles_potential.yaml',
                  'pset': kv(main_wh), 'roles_md5': md5(f'{B}/roles/viode_vehicles_potential.yaml'),
                  'note': 'frozen SAVIOR savior_node keys verbatim (fixed 1 m gate, median link); roles viode_vehicles_potential (P5)'},
    'p7_nb': {'launch': 'savior.launch.py', 'backend': 'yolo', 'model': COCO_S, 'roles_file': f'{B}/roles/viode_vehicles_potential.yaml',
              'pset': kv(F['methods']['p7_nb']['savior_node']), 'roles_md5': md5(f'{B}/roles/viode_vehicles_potential.yaml'),
              'note': 'frozen SAVIOR-adaptive savior_node keys verbatim; roles viode_vehicles_potential (P5)'},
    'savior_edge': {'launch': 'savior.launch.py', 'install': f'{FE}/install', 'backend': 'yolo', 'model': COCO_N,
                    'roles_file': f'{B}/roles/viode_vehicles_potential.yaml', 'pset': kv(main_wh), 'ov_set_extra': edge_ov,
                    'roles_md5': md5(f'{B}/roles/viode_vehicles_potential.yaml'),
                    'note': 'VIODE sens_fix1 with the COCO YOLO26n engine (same 640x640 FP16 export as the COCO s engine) + deferred '
                            'invalidation 250 ms; segmenter.imgsz keeps the VIODE s-variant value (640 = engine input), as on the '
                            'warehouse where the edge imgsz=672 equals the s-variant perception_params value'},
}
now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
cfg = {
    'status': 'FROZEN-ADDENDUM - pre-registered before any held-out (warehouse t2 / VIODE) SAVIOR or YOLO run',
    'frozen_at': now,
    'frozen_by': 'M2b agent, on the author approval of 2026-10-24 (SAVIOR-edge as a pre-registered addendum)',
    'original_config': {'path': 'results/p7/final_config.yaml', 'md5': md5('results/p7/final_config.yaml'),
                        'note': 'unchanged and authoritative for the 7 original methods on the warehouse; this addendum only adds'},
    'final_methods': F['final_methods'] + ['savior_edge'],
    'paper_labels': dict(F['paper_labels'], savior_edge='SAVIOR-edge'),
    'addendum_comparisons': ['savior_edge vs sens_fix1 (edge criterion, below)', 'savior_edge vs openvins', 'savior_edge vs yolo_naive (reported)'],
    'savior_edge': {
        'label': 'SAVIOR-edge',
        'role': 'ADDENDUM: edge-study recommended combination = frozen main sens_fix1 + YOLO26n-seg 672x384 (warehouse fine-tuned, '
                'FP16) + deferred invalidation only (simulated mask latency 250 ms, no stale gating)',
        'edge_study_method': 'e_c_n672_L250dfronly (results/edge_study/edge_methods.json; the only variant passing CRITERION.txt, '
                             '"uncertain" CI on t1: L0+L1 +6.3 % [-6, +20], L2+L3 -0.3 % [-14, +16], 0 failures)',
        'install': f'{FE}/install',
        'source': {'path': f'{FE}/src/savior', 'git_commit': commit, 'parent_commit_is_frozen_baseline': True,
                   'tree_hashes': {'savior_perception': tree(f'{WS}/{FE}', 'src/savior/savior_perception/savior_perception', ['**/*.py']),
                                   'savior_bringup_launch': tree(f'{WS}/{FE}', 'src/savior/savior_bringup/launch', ['*.py']),
                                   'ov_msckf_fork': tree(f'{WS}/{FE}', 'src/savior/open_vins/ov_msckf/src', ['**/*.cpp', '**/*.h']),
                                   'ov_core': tree(f'{WS}/{FE}', 'src/savior/open_vins/ov_core/src', ['**/*.cpp', '**/*.h'])},
                   'baseline_check': 'git HEAD~1 (frozen baseline copy) == src/savior on every frozen source tree hash '
                                     '(savior_perception a0f36961, launch b1baf729, ov_msckf e3ae3a5b); edge changes are default-off flags'},
        'install_hash': install_hash(f'{FE}/install'),
        'warehouse': {'launch': 'savior.launch.py', 'backend': 'yolo', 'model': WH_N, 'model_md5': md5(WH_N),
                      'model_source': 'results/edge_study engines/n672.engine (copied, md5-identical), from models/warehouse/yolo26n-seg-warehouse.pt '
                                      f'(md5 {md5("models/warehouse/yolo26n-seg-warehouse.pt")}), TensorRT FP16 384x672',
                      'perception_params': F['methods']['sens_fix1']['perception_params'],
                      'roles_file': F['methods']['sens_fix1']['roles_file'], 'roles_md5': F['methods']['sens_fix1']['roles_md5'],
                      'pset': edge_pset, 'ov_set_extra': edge_ov,
                      'diff_vs_sens_fix1': 'model (s -> n engine), segmenter.imgsz=672 (redundant: = perception_params value), ov_set_extra'},
        'viode': {k: v for k, v in vm['savior_edge'].items()},
        'criterion_heldout': 'as results/edge_study/CRITERION.txt items 1-2 with SAVIOR (sens_fix1) as reference on warehouse t2: '
                             'geometric-mean ATE change <= +10 % in L0+L1 AND in L2+L3 (point estimate; CI upper bound > +10 % flagged '
                             '"uncertain"), and failures (ATE > 2 m) on hall_t2_L3 + dock_t2_L3 not above SAVIOR\'s. VIODE: reported.',
    },
    'viode': {
        'scope': 'VIODE instantiation of every final method (final_config.yaml defines none). P5 dataset settings + the frozen pipeline '
                 'parameters, without tuning. Note: VIODE was used in P5 (P2-P4 pipelines) but never with any P7 method.',
        'sequences': [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')],
        'estimator_config': f'{B}/viode/estimator_config.yaml', 'estimator_config_md5': md5(f'{B}/viode/estimator_config.yaml'),
        'perception_params': 'launch default: savior_perception/config/default.yaml + config/viode/savior_perception.yaml '
                             f'(md5 {md5(B + "/viode/savior_perception.yaml")}), as P5',
        'topics': '/cam0/image_raw /cam1/image_raw /imu0',
        'start_offsets_s': {'parking_lot': [5.5, 5.7, 5.9, 6.1, 6.3, 6.5, 6.7, 6.9, 7.1, 7.3],
                            'city_day': [4.1, 4.3, 4.5, 4.7, 4.9, 5.1, 5.3, 5.5, 5.7, 5.9],
                            'city_night': [6.1, 6.3, 6.5, 6.7, 6.9, 7.1, 7.3, 7.5, 7.7, 7.9]},
        'offsets_note': 'P5 late start: 10 offsets beginning 0.8 s before translation (results/p5_viode/scripts/jobs_main*.txt)',
        'failure_threshold_m': 1.0, 'failure_cap_m': 10.0,
        'gt': 'data/viode/gt/<seq>.txt', 'evaluation': 'savior-eval multi (posyaw, full sequence), as P5',
        'coco_engines': {COCO_S: md5(COCO_S), COCO_N: md5(COCO_N)},
        'coco_n_export': 'ultralytics 8.4.177 in savior:humble-cuda12.8, YOLO(models/yolo26n-seg.pt).export(format=engine, imgsz=640, '
                         'half=True, batch=1, simplify=True, device=0) = the export settings of models/yolo26s-seg.engine; '
                         f'pt md5 {md5(FE + "/models/yolo26n-seg-coco.pt")}, onnx md5 {md5(FE + "/models/yolo26n-seg-coco640.onnx")}',
        'colormaps': {e: md5(f'{B}/oracle/viode_{e}_colormap.yaml') for e in ('parking_lot', 'city_day', 'city_night')},
        'prior_static_note': 'selective.prior_static_classes kept verbatim (box,pallet,trolley): not COCO classes, so inert on VIODE',
        'methods': vm,
    },
    'warehouse_heldout': {'sequences': [f'{s}_t2_L{l}' for s in ('aisles', 'hall', 'dock') for l in range(4)],
                          'manifest': 'data/warehouse/HELDOUT_MANIFEST.yaml', 'protocol': 'final_config.yaml protocol (offsets 0.0-1.8 s, '
                          'rate 0.5, failure > 2 m, cap 10 m)'},
    'validity_m2b': ['final_config.yaml validity (clean exit, trajectory, FINAL fallback_latest = fallback_empty = late_masks = 0, n_in_core = 0)',
                     'PLUS pose-count rule: poses >= same-offset openvins pose count - 1',
                     'rate 0.5 only; deterministic_processing, dynamic_mask_upstream_compat, dynamic_mask_max_pending=0 as frozen',
                     'invalid runs are re-run, never dropped; savior_none must equal openvins (md5) on the warehouse; VIODE agreement reported'],
    'runner': 'results/m2b_heldout/scripts/run_m2b.sh + m2b_args.py (settings read only from final_config.yaml and this file)',
    'analysis_plan': {
        'metric': 'ATE RMSE (posyaw, full sequence); secondary RPE (shortest rpg sub-length, failed runs = inf); failures',
        'statistics': 'paired per-offset log ATE ratio vs reference (failures capped at 10 m); geometric-mean ratio - 1; bootstrap 95 % CI '
                      '(20000, seed 0); Wilcoxon signed-rank; Holm within each (dataset, group, reference) family over the methods',
        'groups_warehouse': ['L0', 'L1', 'L2', 'L3', 'L0+L1', 'L2+L3', 'hall_L3', 'dock_L3', 'hall+dock_L3', 'all'],
        'groups_viode': ['none', 'low', 'mid', 'high', 'none+low', 'mid+high', 'low+mid+high', 'all'],
        'references': {'openvins': ['oracle_moving_ext', 'oracle_class_ext', 'yolo_naive', 'sens_fix1', 'p7_nb', 'savior_edge'],
                       'yolo_naive': ['sens_fix1', 'p7_nb', 'savior_edge'],
                       'sens_fix1': ['p7_nb', 'savior_edge'],
                       'oracle_class_ext': ['oracle_moving_ext']},
        'hypotheses': {
            'H1 (primary, the bar)': 'SAVIOR vs Y-Cls on warehouse t2: no worse at L2+L3, better at L0+L1, 0 failures on hall/dock L3',
            'H2': 'SAVIOR better than OpenVINS (L2+L3, hall/dock L3; VIODE mid+high)',
            'H3 (secondary)': 'SAVIOR-adaptive vs Y-Cls (same bar); SAVIOR vs SAVIOR-adaptive reported',
            'H4': 'O-Dyn+B better than O-Cls+B (selective vs class-level ceiling), L0 and L2+L3',
            'H5 (addendum)': 'SAVIOR-edge within the edge criterion vs SAVIOR (above)',
            'control': 'savior_none == openvins (md5) on the warehouse',
        },
        'diagnostic_optional': 'share-vs-gain on the new sequences (optional; may be skipped)',
    },
    'verification': VER,
}
hdr = ('# ============================================================================================================\n'
       '# SAVIOR P7 FINAL CONFIGURATION ADDENDUM (M2b) - FROZEN / PRE-REGISTERED before any held-out SAVIOR / YOLO run.\n'
       '# References results/p7/final_config.yaml (md5 6fea24e550b7198659d8de35d19b3c67), which stays unchanged.\n'
       '# Do not edit. Its md5 is in results/p7/final_config_addendum.md5 and src/savior/docs/IMPLEMENTATION_PLAN.md section 6.\n'
       '# pset = savior_node "k=v ..." (launch pset:=); ov_set_extra is appended to the frozen ov_set.\n'
       '# ============================================================================================================\n')
out = os.environ.get('OUT', P + '/final_config_addendum.yaml')
open(out, 'w').write(hdr + yaml.safe_dump(cfg, sort_keys=False, width=140, allow_unicode=True))
print(out)
