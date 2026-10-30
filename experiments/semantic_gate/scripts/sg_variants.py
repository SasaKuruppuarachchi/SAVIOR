"""sg_variants.py: semantic chi2 gate (SAVIOR-SG) study variants, warehouse t1 ONLY (results/semantic_gate/GRID.yaml).

Every variant = one FROZEN base method of back-end v2 (results/backend_v2/scripts/bv2_args.py: results/p7/final_config.yaml
+ final_config_addendum.yaml + backend_config.yaml) + an explicit delta:
  pset_set  : savior_node keys set on top of the base pset
  ovset_add : OpenVINS keys added to ov_set (ROS parameters override the estimator yaml)
  install   : 'sg'     = results/semantic_gate/install (src/savior with the SG / NIS code, built by scripts/build_sg.sh)
              'frozen' = the frozen workspace install/ (unchanged code; used for the t1 run of the review-runs sf1_chibest)
"""
SG_PSET = {'compose.movable_static_value': 64}       # perception: publish the movable-static level (64)


def sg(ms, mb, kb):
    return {'savior_semantic_gate': True, 'savior_sg_mult_static': ms, 'savior_sg_mult_band': mb, 'savior_sg_keep_band': kb}


def tag(x):
    return f'{int(round(x * 100)):03d}'


V = {
    # ---- md5-identity controls (flags off, SG install): must reproduce results/backend_v2/runs/<seq>/<base>/run_XX
    'ctl_openvins': dict(base='openvins', install='sg', label='control: OpenVINS-v2, SG build, flags off'),
    'ctl_savior_none': dict(base='savior_none', install='sg', label='control: SAVIOR-none, SG build, flags off'),
    'ctl_sens_fix1': dict(base='sens_fix1', install='sg', label='control: SAVIOR, SG build, flags off'),
    # perception publishes the 64 level, fork SG off: must reproduce sens_fix1 (the 64 level is inert for the 128 / 224 gates)
    'ctl_sf1_ms64': dict(base='sens_fix1', install='sg', pset_set=SG_PSET, label='control: SAVIOR + 64 level, fork SG off'),
    # ---- non-semantic self-tuning control: NIS-adaptive gate (defaults: window 200, scale clamp [0.05, 20])
    'sf1_nis': dict(base='sens_fix1', install='sg', ovset_add={'savior_nis_gate': True}, label='SAVIOR + NIS-adaptive gate'),
    'ov_nis': dict(base='openvins', install='sg', ovset_add={'savior_nis_gate': True}, label='OpenVINS-v2 + NIS-adaptive gate'),
    # ---- review-runs t1-tuned global chi2 on SAVIOR (results/review_runs/scripts/rr_variants.py sf1_chibest), frozen code
    'sf1_chibest': dict(base='sens_fix1', install='frozen', ovset_add={'up_msckf_chi2_multipler': 0.25, 'up_slam_chi2_multipler': 0.25},
                        label='SAVIOR + OpenVINS chi2 x0.25 (review runs, t1-tuned)'),
}
# ---- SAVIOR-SG grid (pre-declared in GRID.yaml): m_s x m_b x keep_band
GRID = [(ms, mb, kb) for ms in (0.25, 0.5) for mb in (0.25, 0.5) for kb in (False, True)]
for ms, mb, kb in GRID:
    V[f'sg_s{tag(ms)}_b{tag(mb)}_kb{int(kb)}'] = dict(base='sens_fix1', install='sg', pset_set=SG_PSET, ovset_add=sg(ms, mb, kb),
                                                    label=f'SAVIOR-SG m_s={ms:g} m_b={mb:g} keep_band={kb}')
