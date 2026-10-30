# Parameter-diff check (cr_check.py)

Each chi2-realworld setting vs (a) the rw_settings files and (b) the run_info.yaml launch commands recorded in the paired frozen real-world baseline (ovchi_best vs openvins, sf1_chibest vs sens_fix1). Allowed: OVSET + up_msckf_chi2_multipler=0.25 + up_slam_chi2_multipler=0.25 only (INSTALL identical: workspace install/).

**115 / 115 recorded settings: exactly the chi2 delta. Errors: 0.**

| sequence | variant | rw_settings files (exact) | run_info cmds (exact) |
|---|---|--:|--:|
| MIO13 | ovchi_best | 5 (5) | 10 (10) |
| MIO13 | sf1_chibest | 6 (6) | 10 (10) |
| MIO15 | ovchi_best | 5 (5) | 10 (10) |
| MIO15 | sf1_chibest | 5 (5) | 10 (10) |
| MIO16 | ovchi_best | 5 (5) | 10 (10) |
| MIO16 | sf1_chibest | 5 (5) | 10 (10) |
| MIO07 | ovchi_best | 2 (2) | 10 (10) |
| MIO07 | sf1_chibest | 2 (2) | 10 (10) |

