"""rr_variants.py: review-run variants (reviewer request, author-approved 2026-10-26).
Every variant = one FROZEN base method (results/p7/final_config.yaml / final_config_addendum.yaml through
results/backend_v2/scripts/bv2_args.py, back-end v2) + an explicit delta:
  pset_set  : savior_node keys set (added or replaced) on top of the base pset
  ovset_add : OpenVINS keys added to ov_set (ROS parameters override the estimator yaml, logged 'overriding node <k>')
scope: 't1' (tuning only) or 'heldout' (t2 + VIODE, needs FREEZE.yaml).
The chosen chi2 value of task B (CHI2_BEST) is filled in from the t1 result BEFORE FREEZE.yaml is written."""
CHI2_GRID = (1.0, 0.5, 0.25, 0.1)          # 1.0 = current (OpenVINS-v2 itself, existing runs)
CHI2_BEST = 0.25                           # t1 sweep result (tables/ate_t1.md, B_chi2_vs_openvins, group all: -46.5 %), set before the freeze


def chi2(x):
    return {'up_msckf_chi2_multipler': x, 'up_slam_chi2_multipler': x}


def tag(x):
    return f'{int(round(x * 100)):03d}'


V = {
    # ---- A: held-out ablations of the headline method SAVIOR (sens_fix1)
    'sf1_noint': dict(base='sens_fix1', pset_set={'gating.promote_contact': False}, scope='heldout',
                      label='SAVIOR w/o interaction (class prior + motion-consistency, no association tree)'),
    'sf1_nomotion': dict(base='sens_fix1', pset_set={'motion.enable': False}, scope='heldout',
                         label='SAVIOR w/o motion evidence (class prior + interaction)'),
    # ---- reproduction controls (no delta): re-run frozen methods with this runner on held-out sequences; trajectories must be
    # md5-identical to results/backend_v2/heldout/runs (ctl_<m> vs <m>); ctl_savior_none must also equal openvins (warehouse)
    'ctl_sens_fix1': dict(base='sens_fix1', scope='heldout', label='control: SAVIOR re-run'),
    'ctl_savior_none': dict(base='savior_none', scope='heldout', label='control: SAVIOR-none re-run'),
}
# ---- B: no-semantics robust baseline, OpenVINS-v2 with a tightened chi2 gate (t1 sweep)
for x in CHI2_GRID[1:]:
    V[f'ovchi_{tag(x)}'] = dict(base='openvins', ovset_add=chi2(x), scope='t1', label=f'OpenVINS chi2 x{x:g}')
# ---- C: gate sweep under back-end v2 (t1 only); = results/p7/scripts/mksweep_e.py definitions on the base p7_nb
for d in (0, 1, 2, 3, 4):
    V[f'gate_fix{d}'] = dict(base='p7_nb', pset_set={'gating.mode': 'fixed', 'gating.fixed_threshold_m': float(d),
                                                       'gating.link_depth': 'median'}, scope='t1', label=f'fixed d_int {d} m, median link')
for k in (1, 2, 3, 4):
    V[f'gate_k{k}'] = dict(base='p7_nb', pset_set={'gating.k_sigma': float(k)}, scope='t1', label=f'adaptive k={k}, contact link')
for k in (1, 3):
    V[f'gate_kmed{k}'] = dict(base='p7_nb', pset_set={'gating.k_sigma': float(k), 'gating.link_depth': 'median'}, scope='t1',
                              label=f'adaptive k={k}, median link')
# C settings identical to existing back-end v2 t1 runs (reused, not re-run; parameter identity asserted by rr_check.py):
#   gate_fix1 == sens_fix1 (frozen pset), gate_k3 == p7_nb (k_sigma default 3.0)
REUSE_T1 = {'gate_fix1': 'sens_fix1', 'gate_k3': 'p7_nb'}
if CHI2_BEST is not None:
    V['ovchi_best'] = dict(base='openvins', ovset_add=chi2(CHI2_BEST), scope='heldout', label=f'OpenVINS chi2 x{CHI2_BEST:g} (t1-tuned)')
    V['sf1_chibest'] = dict(base='sens_fix1', ovset_add=chi2(CHI2_BEST), scope='heldout',
                            label=f'SAVIOR + OpenVINS chi2 x{CHI2_BEST:g}')

# ---- E (coordinator, approved scope): final SAVIOR (sens_fix1) and Y-Cls on OpenLORIS + uHumans2 with the ORIGINAL estimator
# configs of P2 / P3a / P4 / P7-D (src/savior/savior_bringup/config/{openloris_t265,uhumans2}/estimator_config.yaml, unchanged
# since P2) and the frozen COCO instantiation (results/p7/final_config.yaml coco_real_robot: models/yolo26s-seg.engine, roles
# coco_indoor, selective.prior_static_classes=chair,suitcase,backpack,handbag,cart; Y-Cls = person_only roles + frozen Y-Cls
# keys, exactly the P7 stage-D no-harm instantiation, results/p7/scripts/run_noharm.sh). References re-run with the same
# install: openvins, savior_none, oracle_person (P3a definition, uHumans2 only). scope 'E' (needs FREEZE.yaml).
E = {
    'e_openvins': dict(kind='openvins', label='OpenVINS (original back-end)'),
    'e_savior_none': dict(kind='savior_none', label='SAVIOR-none (empty masks)'),
    'e_yolo_naive': dict(kind='yolo_naive', label='Y-Cls (COCO person, frozen Y-Cls keys)'),
    'e_sens_fix1': dict(kind='sens_fix1', label='SAVIOR (frozen sens_fix1, COCO instantiation)'),
    'e_oracle_person': dict(kind='oracle_person', label='oracle person masks (P3a definition)'),
}
for _k, _v in E.items():
    V[_k] = dict(base=_v['kind'], scope='E', label=_v['label'])
E_SEQS = {'openloris': ['cafe1-1', 'cafe1-2', 'office1-1', 'office1-2', 'office1-3', 'office1-4', 'office1-5', 'office1-6', 'office1-7'],
          'uhumans2': ['office_s1_00h', 'office_s1_06h', 'office_s1_12h']}
