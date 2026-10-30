# Empty-mask control and mask sync (runs)

- vins_zero (all-zero masks, gate mode) vs vins_fusion (no masks), both deterministic: **80/80 md5-identical**

| method | runs | frames | found | missing | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solver_time_hits |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| vins_edge | 80 | 175872 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 175472 | 0 | 2715516 | 448288 | 0 |
| vins_ocls | 80 | 175872 | 175872 | 0 | 0 | 0 | 171904 | 374293 | 6847 | 8070 | 0 | 0 | 0 | 0 | 0 |
| vins_odyn | 80 | 175872 | 175872 | 0 | 0 | 0 | 56853 | 80066 | 280 | 332 | 0 | 0 | 0 | 0 | 0 |
| vins_savior | 80 | 175872 | 175872 | 0 | 0 | 0 | 364295 | 377748 | 80 | 431 | 0 | 0 | 0 | 0 | 0 |
| vins_ycls | 80 | 175872 | 175872 | 0 | 0 | 0 | 746411 | 709192 | 80 | 368 | 0 | 0 | 0 | 0 | 0 |
| vins_zero | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 | 0 |
