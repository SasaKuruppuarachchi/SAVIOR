#!/usr/bin/env python3
"""mkfinal.py <versions.json>: write results/p7/final_config.yaml (P7 stage G, pre-registration) from methods.json
(= variants.py + sweeps, the exact psets used on t1), run_method.sh launch settings, file hashes and software versions.
Host python (yaml). Freeze: md5sum final_config.yaml > final_config.md5 (done by the caller)."""
import datetime, glob, hashlib, json, os, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
P = WS + '/results/p7'
B = 'src/savior/savior_bringup/config'
V = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
M = json.load(open(P + '/methods.json'))


def md5(rel):
    return hashlib.md5(open(f'{WS}/{rel}', 'rb').read()).hexdigest()


def tree(rel, pats):
    h = hashlib.md5()
    fs = sorted(f for p in pats for f in glob.glob(f'{WS}/{rel}/{p}', recursive=True) if '__pycache__' not in f)
    for f in fs:
        h.update(os.path.relpath(f, WS).encode()); h.update(open(f, 'rb').read())
    return {'md5': h.hexdigest(), 'n_files': len(fs), 'files': f'{rel}/' + ','.join(pats)}


def kv(pset):
    out = {}
    for t in pset.split():
        k, v = t.split('=', 1)
        out[k] = yaml.safe_load(v)
    return out


OVSET = {'deterministic_processing': True, 'dynamic_mask_upstream_compat': True, 'dynamic_mask_max_pending': 0}
YOLO = {'launch': 'savior.launch.py', 'backend': 'yolo', 'model': 'models/warehouse/yolo26s-seg-warehouse.engine',
        'perception_params': f'{B}/warehouse/savior_perception_yolo.yaml'}
meth = {
    'openvins': {'label': 'OpenVINS', 'role': 'baseline (no perception node)', 'launch': 'baseline.launch.py'},
    'savior_none': {'label': 'SAVIOR-none', 'role': 'control: empty masks; must equal openvins (md5 of trajectories)',
                    'launch': 'savior.launch.py', 'backend': 'none'},
    'oracle_moving_ext': {'label': 'O-Dyn+B', 'role': 'ceiling: GT moving-object masks + depth band', 'launch': 'savior.launch.py',
                          'backend': 'oracle_colormap', 'dataset': 'warehouse_moving', 'roles_file': f'{B}/roles/warehouse_oracle_moving.yaml',
                          'extra_topics': '/cam0/segmentation_moving',
                          'savior_node': {'extension.enable': True, 'tracker.enable': False, 'compose.right_fallback': 'median'}},
    'oracle_class_ext': {'label': 'O-Cls+B', 'role': 'like-for-like oracle naive: GT class masks (all movable classes) + depth band',
                         'launch': 'savior.launch.py', 'backend': 'oracle_colormap', 'roles_file': f'{B}/roles/warehouse_naive.yaml',
                         'extra_topics': '/cam0/segmentation',
                         'savior_node': {'extension.enable': True, 'tracker.enable': False, 'compose.right_fallback': 'median'}},
}
for name, label, role in (('yolo_naive', 'Y-Cls', 'naive YOLO class masking (all movable classes, no band)'),
                          ('sens_fix1', 'SAVIOR', 'MAIN (pre-registered primary): P7 selective, fixed interaction gate d_int = 1 m, median-depth link'),
                          ('p7_nb', 'SAVIOR-adaptive', 'SECONDARY (pre-registered): P7 selective, adaptive interaction gate (default k_sigma 3, contact link, noise cap 0.5 m)')):
    meth[name] = {'label': label, 'role': role, **YOLO, 'roles_file': f'{B}/roles/{M[name]["roles"]}.yaml', 'savior_node': kv(M[name]['pset'])}
for m in meth.values():
    if m.get('roles_file'):
        m['roles_md5'] = md5(m['roles_file'])

cfg = {
    'status': 'FROZEN - pre-registered before any held-out evaluation',
    'frozen_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
    'frozen_by': 'agent N (P7 stage G) on the author\'s decisions of 2026-10-23 11:25',
    'tuned_on': 'SAVIOR-Warehouse *_t1_* only (aisles/hall L0-L3). Held-out: warehouse *_t2_*, *_t3_* (and VIODE) never opened.',
    'main_method': 'sens_fix1',
    'secondary_method': 'p7_nb',
    'final_methods': ['openvins', 'savior_none', 'oracle_moving_ext', 'oracle_class_ext', 'yolo_naive', 'sens_fix1', 'p7_nb'],
    'paper_labels': {k: v['label'] for k, v in meth.items()},
    'primary_comparisons': ['sens_fix1 vs yolo_naive', 'sens_fix1 vs openvins', 'p7_nb vs yolo_naive (secondary)',
                            'oracle_moving_ext vs oracle_class_ext (like-for-like oracle)', 'savior_none == openvins (md5 control)'],
    'protocol': {
        'runner': 'savior-run (savior_eval), one isolated container per method x sequence (results/p7/scripts/run_method.sh, drun.sh)',
        'bag_rate': 0.5, 'start_offsets_s': [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8],
        'mask_policy': 'wait', 'mask_timeout_ms': 30000, 'feature_stats': 'auto',
        'topics': '/cam0/image_raw /cam1/image_raw /imu0 /tf_static (+ the oracle segmentation topic for oracle methods)',
        'estimator_config': f'{B}/warehouse/estimator_config.yaml',
        'validity': 'every run: clean exit, non-empty trajectory, fork FINAL line with fallback_latest = fallback_empty = late_masks = 0, '
                    'n_in_core = 0 (results/p7/scripts/p7sync.py); invalid runs are re-run, never dropped silently',
        'evaluation': 'savior-eval multi --runs <dir> --gt data/warehouse/gt/<seq>.txt (posyaw alignment, full sequence)',
        'failure_threshold_m': 2.0, 'failure_cap_m': 10.0,
        'statistics': 'paired per-offset log ATE ratio vs reference; geometric-mean ratio - 1; bootstrap 95 % CI (20000, seed 0); '
                      'Wilcoxon signed-rank; Holm within each (level group, reference) family; groups L0, L1, L2, L3, L0+L1, L2+L3, hall_L3 '
                      '(results/p7/scripts/p7analyze.py); secondary metric RPE (shortest rpg sub-length)'},
    'ov_set': OVSET,
    'methods': meth,
    'coco_real_robot': {'role': 'no-harm profile (uHumans2, OpenLORIS; COCO person detector)', 'model': 'models/yolo26s-seg.engine',
                        'model_md5': md5('models/yolo26s-seg.engine'), 'roles_file': f'{B}/roles/coco_indoor.yaml',
                        'roles_md5': md5(f'{B}/roles/coco_indoor.yaml'),
                        'savior_node_overrides': {'selective.prior_static_classes': 'chair,suitcase,backpack,handbag,cart'}},
    'files': {
        'model_engine': {'path': 'models/warehouse/yolo26s-seg-warehouse.engine', 'md5': md5('models/warehouse/yolo26s-seg-warehouse.engine'),
                         'note': 'TensorRT FP16 384x672, built for this GPU / TRT version; rebuild elsewhere from the .onnx'},
        'model_onnx': {'path': 'models/warehouse/yolo26s-seg-warehouse.onnx', 'md5': md5('models/warehouse/yolo26s-seg-warehouse.onnx')},
        'model_pt': {'path': 'models/warehouse/yolo26s-seg-warehouse.pt', 'md5': md5('models/warehouse/yolo26s-seg-warehouse.pt')},
        'perception_params': {'path': f'{B}/warehouse/savior_perception_yolo.yaml', 'md5': md5(f'{B}/warehouse/savior_perception_yolo.yaml')},
        'perception_defaults': {'path': 'src/savior/savior_perception/config/default.yaml', 'md5': md5('src/savior/savior_perception/config/default.yaml')},
        'estimator_config': {'path': f'{B}/warehouse/estimator_config.yaml', 'md5': md5(f'{B}/warehouse/estimator_config.yaml')},
        'roles': {f: md5(f'{B}/roles/{f}') for f in ('warehouse.yaml', 'warehouse_naive.yaml', 'warehouse_oracle_moving.yaml', 'coco_indoor.yaml')},
        'source_trees': {
            'savior_perception': tree('src/savior/savior_perception/savior_perception', ['**/*.py']),
            'savior_bringup_launch': tree('src/savior/savior_bringup/launch', ['*.py']),
            'ov_msckf_fork': tree('src/savior/open_vins/ov_msckf/src', ['**/*.cpp', '**/*.h']),
            'p7_scripts': tree('results/p7/scripts', ['variants.py', 'mkmethods.py', 'mksweep_e.py', 'run_method.sh', 'drun.sh',
                                                       'p7sync.py', 'p7analyze.py', 'eval_all.sh'])}},
    'software': V,
    'notes': ['t1 reference runs of openvins, savior_none, oracle_moving_ext and yolo_naive were reused from P6 (md5-identical poses after '
              'the P7 rebuild; 0 fallbacks so dynamic_mask_max_pending had no effect); on held-out data ALL methods are run with this file.',
              'segmenter.fast_masks and stats_compact are node-only (bit-identical masks / trajectories, verified in stage F).',
              'Interaction-gate check (sens_kmed1/3: adaptive gate + median link) was run on t1 before freezing and did not change the choice.'],
    'stage_F_timing': 'results/p7/tables/timing.md (idle machine, rate 1.0)',
}
hdr = ('# ============================================================================================================\n'
       '# SAVIOR P7 FINAL CONFIGURATION - FROZEN / PRE-REGISTERED before any held-out evaluation.\n'
       '# Do not edit. Its md5 is recorded in results/p7/final_config.md5 and src/savior/docs/IMPLEMENTATION_PLAN.md section 6.\n'
       '# savior_node keys are pset:="k=v ..." on top of savior_perception/config/default.yaml + perception_params; ov_set:="k=v ...".\n'
       '# Main (sens_fix1) was selected on the t1 tuning set (stage E, post hoc among 9 gate settings): t1 numbers are optimistic.\n'
       '# ============================================================================================================\n')
open(P + '/final_config.yaml', 'w').write(hdr + yaml.safe_dump(cfg, sort_keys=False, width=140, allow_unicode=True))
print(open(P + '/final_config.yaml').read())
