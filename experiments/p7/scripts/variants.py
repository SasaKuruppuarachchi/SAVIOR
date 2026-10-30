"""P7 perception variants (offline evaluator p7eval.py and run_method.sh share these definitions).
name -> (detections: wh | gt_moving | gt_all, roles yaml stem, savior_node overrides)."""
P4 = {'motion.enable': True, 'gating.link_depth': 'contact', 'gating.max_noise_m': 0.5, 'tracker.enable': False,
      'extension.enable': True, 'motion.still_policy': 'unmask', 'compose.right_fallback': 'median'}
P2 = {'motion.enable': False, 'gating.link_depth': 'contact', 'gating.max_noise_m': 0.5, 'tracker.enable': False,
      'extension.enable': True, 'compose.right_fallback': 'median'}
NAIVE = {'extension.enable': False, 'tracker.enable': False, 'compose.right_fallback': 'median'}
# P7 base: P4 motion evidence + selective policy, people always dynamic, long window, chain depth 3
# (person -> forklift -> pallet -> box), fast YOLO mask transfer (bit-identical)
P7 = {**P4, 'motion.use_still': False, 'motion.window_long_s': 2.0, 'gating.max_depth': 3,
      'selective.enable': True, 'selective.prior_static_classes': 'box,pallet,trolley',
      'tracker.enable': True, 'tracker.motion_model': 'ego', 'segmenter.fast_masks': True}

VARIANTS = {
    'yolo_naive': ('wh', 'warehouse_naive', NAIVE),
    'yolo_naive_band': ('wh', 'warehouse_naive', {**NAIVE, 'extension.enable': True}),
    'yolo_p2': ('wh', 'warehouse', P2),
    'yolo_p4': ('wh', 'warehouse', P4),
    'yolo_p6': ('wh', 'warehouse', {**P4, 'motion.window_unveto_potential': True, 'gating.max_depth': 2}),
    'p7': ('wh', 'warehouse', P7),
    'p7_v0': ('wh', 'warehouse', {**P7, 'selective.prior_static_classes': 'box,pallet', 'tracker.enable': False,
                                  'tracker.motion_model': 'pixel_cv'}),   # first sweep base (p7b)
}
# P7 band variants (closed loop b1: the depth-band region growing hurts with YOLO masks)
VARIANTS['yolo_naive_ring'] = ('wh', 'warehouse_naive', {**NAIVE, 'extension.enable': True, 'extension.grow': False})
VARIANTS['p7_nb'] = ('wh', 'warehouse', {**P7, 'extension.enable': False})
VARIANTS['p7_ring'] = ('wh', 'warehouse', {**P7, 'extension.grow': False})
# P7 component ablations (each removes one component from p7)
ABLATIONS = {
    'p7_abl_noconv': {'selective.converge_s': 0.0},                      # no init / convergence conservatism
    'p7_abl_nohold': {'selective.min_on_s': 0.0},                        # no mask hysteresis (off-delay)
    'p7_abl_notrk': {'tracker.enable': False, 'tracker.motion_model': 'pixel_cv'},   # no tracker carry
    'p7_abl_sticky': {'selective.stale_s': 1e6, 'selective.revoke_q': 1e6},          # static decisions never expire / revoked
    'p7_abl_optimistic': {'selective.prior_static_classes': 'box,pallet,trolley,forklift'},  # unknown forklifts unmasked
    'p7_abl_noband': {'extension.enable': False},                        # no depth band (192)
    'p7_abl_nocomo': {'selective.comotion_gate': False},                 # links by contact only
    'p7_abl_noint': {'gating.promote_contact': False},                   # no interaction promotion (roots only)
    'p7_abl_nolong': {'motion.window_long_s': 0.0},                      # no long window
    'p7_abl_noprior': {'selective.prior_static_classes': 'none'},       # resume: no class prior (unlinked boxes/pallets/trolleys uncertain -> masked until confirmed static)
}
for _k, _v in ABLATIONS.items():
    VARIANTS[_k] = ('wh', 'warehouse', {**P7, **_v})


def p7(**over):
    """P7 base + overrides given as section__field=value (double underscore = dot)."""
    return {**P7, **{k.replace('__', '.'): v for k, v in over.items()}}

# P7 stage C (resume 2026-10-23): component ablations REBASED on the chosen main variant (CHECKPOINT 1 decision).
# Each <main>_abl_<x> = main + one component removed. For a no-band main, the band ablation is the reverse (+band).
def rebased_ablations(main):
    src, roles, base = VARIANTS[main]
    out = {}
    for k, v in ABLATIONS.items():
        name = k.replace('p7_abl_', f'{main}_abl_')
        over = dict(v)
        if k == 'p7_abl_noband' and not base.get('extension.enable', True):
            name, over = f'{main}_abl_addband', {'extension.enable': True}
        out[name] = (src, roles, {**base, **over})
    return out


import os as _os
_MF = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'main_variant.txt')   # written at CHECKPOINT 1
MAIN = open(_MF).read().strip() if _os.path.isfile(_MF) else None
if MAIN:
    VARIANTS.update(rebased_ablations(MAIN))
