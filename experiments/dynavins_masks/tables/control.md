# Empty-mask control and mask sync (runs)

- dyna_zero (all-zero masks, gate mode) vs dyna_det (no masks), both deterministic: **80/80 md5-identical**

| method | runs | FINAL | frames | found | missing | bad_size | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solves | solver_time_hits |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| dyna_det | 80 | 80 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 260732 | 0 |
| dyna_ocls | 80 | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 217290 | 403699 | 90 | 382 | 0 | 0 | 0 | 0 | 265346 | 0 |
| dyna_odyn | 80 | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 62337 | 105730 | 80 | 0 | 0 | 0 | 0 | 0 | 256020 | 0 |
| dyna_savior | 80 | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 540347 | 526970 | 80 | 0 | 0 | 0 | 0 | 0 | 255268 | 0 |
| dyna_ycls | 80 | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 1174712 | 1069720 | 80 | 0 | 0 | 0 | 0 | 0 | 257190 | 0 |
| dyna_zero | 80 | 80 | 175872 | 175872 | 0 | 0 | 0 | 0 | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 | 260732 | 0 |
