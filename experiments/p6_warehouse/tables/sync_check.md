# mask sync / front-end check over all savior runs (savior-eval runstats)

| method | runs | masks != images | fallbacks | late | n_in_core | kept/frame cam0 (mean) | rejected cam0 per run (mean) |
|---|--:|--:|--:|--:|--:|--:|--:|
| diag_oracle_class_naive | 8 | 0 | 0 | 0 | 0 | 50.1 | 536 |
| diag_oracle_moving | 8 | 0 | 0 | 0 | 0 | 58.5 | 277 |
| diag_yolo_naive | 8 | 0 | 0 | 0 | 0 | 50.2 | 953 |
| diag_yolo_p4 | 7 | 0 | 0 | 0 | 0 | 55.3 | 1210 |
| diag_yolo_p6 | 7 | 0 | 0 | 0 | 0 | 52.9 | 864 |
| oracle_class_naive | 80 | 0 | 0 | 0 | 0 | 50.4 | 540 |
| oracle_moving | 80 | 0 | 0 | 0 | 0 | 58.6 | 278 |
| oracle_moving_ext | 80 | 0 | 0 | 0 | 0 | 56.4 | 256 |
| oracle_moving_warp | 80 | 0 | 0 | 0 | 0 | 58.6 | 279 |
| savior_none | 80 | 0 | 0 | 0 | 0 | 62.1 | 0 |
| savior_none+nocompat | 40 | 0 | 0 | 0 | 0 | 61.6 | 0 |
| yolo_coco_person_p4 | 80 | 0 | 0 | 0 | 0 | 60.4 | 220 |
| yolo_naive | 80 | 0 | 0 | 0 | 0 | 50.4 | 960 |
| yolo_p2 | 80 | 0 | 0 | 0 | 0 | 53.2 | 1294 |
| yolo_p4 | 80 | 0 | 0 | 0 | 0 | 56.2 | 1076 |
| yolo_p4_noext | 80 | 0 | 0 | 0 | 0 | 58.2 | 779 |
| yolo_p4_nointer | 80 | 0 | 0 | 0 | 0 | 58.9 | 318 |
| yolo_p6 | 80 | 0 | 0 | 0 | 0 | 54.2 | 769 |
