# NIS validation: validity audit (nv_audit.py)

warehouse t2 / VIODE / OpenLORIS+uHumans2: rr_audit.py rules (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0, end within 0.101 s of the same-offset OpenVINS(-v2) run, <= 1 pose missing). Monado: rw_analyze.py rules (+ pose rule, + frame rule +-0).

| dataset | method | own | runs | valid | sync ok | end ok | pose rule ok | frame rule ok | fallbacks | late | n_in_core |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| warehouse_t2 | sf1_nis | yes | 120 | 120 | 120 | 120 | 111 | - | 0 | 0 | 0 |
| warehouse_t2 | ov_nis | yes | 120 | 120 | 120 | 120 | 120 | - | 0 | 0 | 0 |
| warehouse_t2 | openvins | baseline | 120 | 120 | 120 | 120 | 120 | - | 0 | 0 | 0 |
| warehouse_t2 | sens_fix1 | baseline | 120 | 120 | 120 | 120 | 111 | - | 0 | 0 | 0 |
| warehouse_t2 | yolo_naive | baseline | 120 | 120 | 120 | 120 | 111 | - | 0 | 0 | 0 |
| warehouse_t2 | ovchi_best | baseline | 120 | 120 | 120 | 120 | 120 | - | 0 | 0 | 0 |
| warehouse_t2 | sf1_chibest | baseline | 120 | 120 | 120 | 120 | 111 | - | 0 | 0 | 0 |
| viode | sf1_nis | yes | 120 | 120 | 120 | 120 | 119 | - | 0 | 0 | 0 |
| viode | ov_nis | yes | 120 | 120 | 120 | 120 | 120 | - | 0 | 0 | 0 |
| viode | openvins | baseline | 120 | 120 | 120 | 120 | 120 | - | 0 | 0 | 0 |
| viode | sens_fix1 | baseline | 120 | 120 | 120 | 120 | 119 | - | 0 | 0 | 0 |
| viode | yolo_naive | baseline | 120 | 120 | 120 | 120 | 119 | - | 0 | 0 | 0 |
| viode | ovchi_best | baseline | 120 | 118 | 120 | 118 | 118 | - | 0 | 0 | 0 |
| viode | sf1_chibest | baseline | 120 | 120 | 120 | 120 | 119 | - | 0 | 0 | 0 |
| openloris_uhumans2 | sf1_nis | yes | 115 | 102 | 102 | 103 | 92 | - | 53840 | 0 | 0 |
| openloris_uhumans2 | ov_nis | yes | 115 | 115 | 115 | 115 | 110 | - | 0 | 0 | 0 |
| openloris_uhumans2 | openvins | baseline | 115 | 115 | 115 | 115 | 115 | - | 0 | 0 | 0 |
| openloris_uhumans2 | sens_fix1 | baseline | 115 | 111 | 111 | 112 | 99 | - | 25678 | 0 | 0 |
| openloris_uhumans2 | yolo_naive | baseline | 115 | 113 | 113 | 113 | 105 | - | 2776 | 0 | 0 |
| monado | sf1_nis | yes | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |
| monado | ov_nis | yes | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |
| monado | openvins | baseline | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |
| monado | sens_fix1 | baseline | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |
| monado | yolo_naive | baseline | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |
| monado | vins_fusion | baseline | 40 | 40 | 40 | - | 40 | 40 | 0 | 0 | 0 |

## Invalid runs

| dataset | seq | method | run | status | poses | ref poses | frames / expected | FINAL | fb | late | in core | end ok |
|---|---|---|---|---|--:|--:|---|---|--:|--:|--:|--:|
| viode | parking_lot_none | ovchi_best | run_07 | ok/0 | 499 | 502 | 526 /  | n/a | 0 | 0 | 0 | 0 |
| viode | parking_lot_none | ovchi_best | run_08 | ok/0 | 500 | 502 | 525 /  | n/a | 0 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_cafe1-1 | sf1_nis | run_01 | ok/0 | 1178 | 1629 | 1259 /  | ok | 2618 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_cafe1-2 | sf1_nis | run_01 | ok/0 | 2076 | 2539 | 2229 /  | ok | 4558 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_cafe1-2 | sens_fix1 | run_01 | ok/0 | 2070 | 2539 | 2249 /  | ok | 4598 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-1 | sf1_nis | run_01 | ok/0 | 276 | 726 | 359 /  | ok | 816 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-1 | sf1_nis | run_02 | ok/0 | 277 | 727 | 353 /  | ok | 802 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-1 | sf1_nis | run_06 | ok/0 | 264 | 714 | 328 /  | ok | 754 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-2 | sf1_nis | run_01 | ok/0 | 382 | 834 | 449 /  | ok | 998 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-2 | sens_fix1 | run_02 | ok/0 | 378 | 828 | 443 /  | ok | 982 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-3 | sf1_nis | run_01 | no_output/0 | 0 | 219 | 1 /  | ok | 0 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-4 | sf1_nis | run_01 | ok/0 | 262 | 702 | 420 /  | ok | 938 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-5 | sf1_nis | run_01 | ok/0 | 999 | 1445 | 1140 /  | ok | 2382 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-6 | sf1_nis | run_02 | ok/0 | 493 | 943 | 630 /  | ok | 1358 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-6 | yolo_naive | run_07 | ok/0 | 493 | 943 | 608 /  | ok | 1314 | 0 | 0 | 0 |
| openloris_uhumans2 | openloris_office1-7 | yolo_naive | run_05 | ok/0 | 333 | 783 | 682 /  | ok | 1462 | 0 | 0 | 0 |
| openloris_uhumans2 | uhumans2_office_s1_00h | sf1_nis | run_03 | ok/0 | 7891 | 7891 | 8301 /  | ok | 3610 | 0 | 0 | 1 |
| openloris_uhumans2 | uhumans2_office_s1_00h | sens_fix1 | run_03 | ok/0 | 7891 | 7891 | 8301 /  | ok | 3608 | 0 | 0 | 1 |
| openloris_uhumans2 | uhumans2_office_s1_06h | sf1_nis | run_03 | ok/0 | 7808 | 8106 | 8212 /  | ok | 16480 | 0 | 0 | 0 |
| openloris_uhumans2 | uhumans2_office_s1_06h | sens_fix1 | run_03 | ok/0 | 7808 | 8106 | 8218 /  | ok | 16490 | 0 | 0 | 0 |
| openloris_uhumans2 | uhumans2_office_s1_12h | sf1_nis | run_02 | ok/0 | 8820 | 9115 | 9236 /  | ok | 18526 | 0 | 0 | 0 |

## md5-identity controls (SG install, flags off, hall_t2_L3 runs 1-5 vs frozen back-end v2 held-out runs)

- ctl_sens_fix1: 1 / 5 byte-identical
- ctl_openvins: 5 / 5 byte-identical
