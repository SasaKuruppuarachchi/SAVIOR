# Empty-mask control and mask sync (runs_t2)

- dyna_zero (all-zero masks, gate mode) vs dyna_det (no masks), both deterministic: **120/120 md5-identical**

| method | runs | FINAL | frames | found | missing | bad_size | in_core_l | in_core_r | drop_tracked_l | drop_tracked_r | relaxed_l | relaxed_r | deferred_masks | deferred_missing | flagged | flagged_tracked | solves | solver_time_hits |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| dyna_det | 120 | 120 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 372280 | 0 |
| dyna_ocls | 120 | 120 | 250848 | 250848 | 0 | 0 | 0 | 0 | 320201 | 601484 | 718 | 1161 | 0 | 0 | 0 | 0 | 370204 | 0 |
| dyna_odyn | 120 | 120 | 250848 | 250848 | 0 | 0 | 0 | 0 | 108767 | 196598 | 120 | 10 | 0 | 0 | 0 | 0 | 347920 | 0 |
| dyna_savior | 120 | 120 | 250848 | 250848 | 0 | 0 | 0 | 0 | 1085614 | 1086219 | 120 | 330 | 0 | 0 | 0 | 0 | 352084 | 0 |
| dyna_ycls | 120 | 120 | 250848 | 250848 | 0 | 0 | 0 | 0 | 2380972 | 2171774 | 120 | 450 | 0 | 0 | 0 | 0 | 357626 | 0 |
| dyna_zero | 120 | 120 | 250848 | 250848 | 0 | 0 | 0 | 0 | 0 | 0 | 120 | 0 | 0 | 0 | 0 | 0 | 372280 | 0 |
