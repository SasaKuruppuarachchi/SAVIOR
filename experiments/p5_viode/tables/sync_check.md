# mask sync / front-end check over all savior runs (savior-eval runstats)

| method | runs | masks != images | fallbacks | late | n_in_core | kept/frame cam0 (mean) | rejected cam0 per run (mean) |
|---|--:|--:|--:|--:|--:|--:|--:|
| oracle_all_vehicles | 120 | 0 | 0 | 0 | 0 | 60.6 | 44 |
| oracle_dynamic | 120 | 0 | 0 | 0 | 0 | 61.1 | 28 |
| oracle_dynamic_warp | 60 | 0 | 0 | 0 | 0 | 59.4 | 53 |
| savior_none | 120 | 0 | 0 | 0 | 0 | 62.7 | 0 |
| yolo_full_p2 | 120 | 0 | 0 | 0 | 0 | 60.4 | 234 |
| yolo_naive | 120 | 0 | 0 | 0 | 0 | 60.9 | 164 |
| yolo_p4_dyn | 120 | 0 | 0 | 0 | 0 | 60.4 | 234 |
| yolo_p4_dyn+fast15 | 120 | 0 | 0 | 0 | 0 | 60.7 | 235 |
| yolo_p4_pot | 120 | 0 | 0 | 0 | 0 | 61.4 | 201 |
| yolo_p4_pot+fast15 | 120 | 0 | 0 | 0 | 0 | 61.6 | 203 |
