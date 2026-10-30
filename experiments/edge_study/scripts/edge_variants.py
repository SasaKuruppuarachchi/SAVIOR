"""EDGE study variants (offline edgeeval.py and online edge_run.sh share these). MAIN = frozen sens_fix1 overrides
(results/p7/final_config.yaml); every variant = MAIN + its overrides. det = detection cache key (CACHES)."""
MAIN = {'motion.enable': True, 'gating.link_depth': 'median', 'gating.max_noise_m': 0.5, 'tracker.enable': True,
        'extension.enable': False, 'motion.still_policy': 'unmask', 'compose.right_fallback': 'median', 'motion.use_still': False,
        'motion.window_long_s': 2.0, 'gating.max_depth': 3, 'selective.enable': True,
        'selective.prior_static_classes': 'box,pallet,trolley', 'tracker.motion_model': 'ego', 'segmenter.fast_masks': True,
        'gating.mode': 'fixed', 'gating.fixed_threshold_m': 1.0}
S = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad'
CACHES = {'s672': S + '/agentN/detcache'}
for _m in ('n672', 's512', 'n512', 's416', 'n416', 's672i8', 'n672i8', 's512i8', 'n512i8'):
    CACHES[_m] = f'{S}/edge/detcache/{_m}'

VARIANTS = {'main': {}}
# idea 1: sparse instance depth (no ROI SGBM)
VARIANTS['sp'] = {'over': {'depth.mode': 'sparse'}}
VARIANTS['sp5'] = {'over': {'depth.mode': 'sparse', 'depth.sparse_min_px': 5}}
VARIANTS['sp_n20'] = {'over': {'depth.mode': 'sparse', 'motion.stereo_inst_points': 20}}
# idea 2: async segmentation
A = {'asyncseg.enable': True}
VARIANTS['as20'] = {'over': {**A, 'asyncseg.rate_hz': 20.0}}          # control: must equal main
for _r, _t in ((10.0, '10'), (5.0, '5'), (2.5, '2')):
    for _m in ('hold', 'rot', 'full'):
        VARIANTS[f'as{_t}_{_m}'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': _m}}
        VARIANTS[f'as{_t}_{_m}_m1'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': _m, 'asyncseg.margin_v_mps': 1.0}}
for _L in (50, 150):
    for _m in ('hold', 'rot', 'full'):
        VARIANTS[f'as20_{_m}_L{_L}'] = {'over': {**A, 'asyncseg.rate_hz': 20.0, 'asyncseg.mode': _m, 'asyncseg.latency_ms': float(_L)}}
        VARIANTS[f'as20_{_m}_L{_L}_m1'] = {'over': {**A, 'asyncseg.rate_hz': 20.0, 'asyncseg.mode': _m,
                                                    'asyncseg.latency_ms': float(_L), 'asyncseg.margin_v_mps': 1.0}}
        for _r, _t in ((10.0, '10'), (5.0, '5')):
            VARIANTS[f'as{_t}_{_m}_L{_L}_m1'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': _m,
                                                          'asyncseg.latency_ms': float(_L), 'asyncseg.margin_v_mps': 1.0}}
# idea 5: cheaper segmentation (detection caches of other engines)
for _m in ('n672', 's512', 'n512', 's416', 'n416', 's672i8', 'n672i8', 's512i8', 'n512i8'):
    VARIANTS[f'seg_{_m}'] = {'det': _m}
VARIANTS['sp_nofb'] = {'over': {'depth.mode': 'sparse', 'depth.sparse_fallback': 'none'}}
VARIANTS['sp_tmpl'] = {'over': {'depth.mode': 'sparse', 'depth.sparse_source': 'template'}}
VARIANTS['sp_klt'] = {'over': {'depth.mode': 'sparse', 'depth.sparse_fallback': 'klt'}}
for _r, _t in ((10.0, '10'), (5.0, '5')):
    VARIANTS[f'as{_t}_egot'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'full', 'asyncseg.use_velocity': False}}
    VARIANTS[f'as{_t}_vel'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'full', 'asyncseg.use_ego_t': False}}
    VARIANTS[f'as{_t}_rot_m05'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'rot', 'asyncseg.margin_v_mps': 0.5}}
    VARIANTS[f'as{_t}_rot_m1c'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'rot', 'asyncseg.margin_v_mps': 1.0,
                                            'asyncseg.margin_value': 255}}
    VARIANTS[f'as{_t}_rot_k3'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'rot', 'asyncseg.klt_levels': 3}}
    VARIANTS[f'as{_t}_rot_noscale'] = {'over': {**A, 'asyncseg.rate_hz': _r, 'asyncseg.mode': 'rot', 'asyncseg.scale_frame_params': False}}
# combinations
SPK = {'depth.mode': 'sparse', 'depth.sparse_fallback': 'klt'}
R10 = {**A, 'asyncseg.rate_hz': 10.0, 'asyncseg.mode': 'rot', 'asyncseg.margin_v_mps': 1.0}
R5 = {**A, 'asyncseg.rate_hz': 5.0, 'asyncseg.mode': 'rot', 'asyncseg.margin_v_mps': 1.0}
VARIANTS['c_sp_r10'] = {'over': {**SPK, **R10}}
VARIANTS['c_sp_r5'] = {'over': {**SPK, **R5}}
VARIANTS['c_sp_r10_n672'] = {'over': {**SPK, **R10}, 'det': 'n672'}
VARIANTS['c_sp_r10_s512'] = {'over': {**SPK, **R10}, 'det': 's512'}
VARIANTS['c_sp_r5_s512'] = {'over': {**SPK, **R5}, 'det': 's512'}
VARIANTS['c_sp_r10_L50'] = {'over': {**SPK, **R10, 'asyncseg.latency_ms': 50.0}}
VARIANTS['c_sp_n672'] = {'over': {**SPK}, 'det': 'n672'}
VARIANTS['c_sp_s512'] = {'over': {**SPK}, 'det': 's512'}
# transfer check on the pre-registered SECONDARY configuration p7_nb (adaptive gate, contact link): base = P7NB
P7NB = {**{k: v for k, v in MAIN.items() if k not in ('gating.mode', 'gating.fixed_threshold_m')}, 'gating.link_depth': 'contact'}
BASES = {'main': MAIN, 'p7nb': P7NB}
VARIANTS['nb'] = {'base': 'p7nb'}
VARIANTS['nb_sp_klt'] = {'base': 'p7nb', 'over': dict(SPK)}
VARIANTS['nb_c_sp_r10'] = {'base': 'p7nb', 'over': {**SPK, **R10}}
VARIANTS['nb_as10_rot_m1'] = {'base': 'p7nb', 'over': dict(R10)}
VARIANTS['nb_seg_n672'] = {'base': 'p7nb', 'det': 'n672'}
VARIANTS['c_n672_L100'] = {'det': 'n672'}
