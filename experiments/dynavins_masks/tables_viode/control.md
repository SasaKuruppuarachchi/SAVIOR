# Empty-mask control and mask sync (runs_viode)

- dyna_zero (all-zero masks, gate mode) vs dyna_det (no masks), both deterministic: **120/120 md5-identical**

| method | runs | FINAL | frames | found | missing | bad_size | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solves | solver_time_hits |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| dyna_det | 120 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 244896 | 0 |
| dyna_ocls | 120 | 120 | 135560 | 135560 | 0 | 0 | 0 | 0 | 49928 | 38665 | 420 | 180 | 0 | 0 | 0 | 0 | 230748 | 0 |
| dyna_odyn | 120 | 120 | 135560 | 135560 | 0 | 0 | 0 | 0 | 29021 | 33109 | 410 | 160 | 0 | 0 | 0 | 0 | 230736 | 0 |
| dyna_savior | 120 | 120 | 135560 | 135560 | 0 | 0 | 0 | 0 | 79364 | 26662 | 270 | 68 | 0 | 0 | 0 | 0 | 232106 | 0 |
| dyna_ycls | 120 | 120 | 135560 | 135560 | 0 | 0 | 0 | 0 | 80492 | 25102 | 270 | 70 | 0 | 0 | 0 | 0 | 232636 | 0 |
| dyna_zero | 120 | 120 | 135560 | 135560 | 0 | 0 | 0 | 0 | 0 | 0 | 160 | 0 | 0 | 0 | 0 | 0 | 244896 | 0 |
