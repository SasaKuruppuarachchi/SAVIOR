# Review-run validity audit: e_partial

root /home/sasa/workspace/savior_ws/results/review_runs/runs/e; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/review_runs/runs/e

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| e_openvins | 94 | 90 | 90 | 94 | 94 | 0 | 0 | 0 | 0 | - |
| e_oracle_person | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| e_savior_none | 92 | 88 | 88 | 86 | 88 | 4754 | 0 | 0 | 0 | 34 / 92 identical |
| e_sens_fix1 | 92 | 87 | 87 | 74 | 87 | 8196 | 0 | 0 | 0 | - |
| e_yolo_naive | 92 | 87 | 87 | 79 | 87 | 7338 | 0 | 0 | 0 | - |

**Total: 352 / 372 valid; 352 sync ok; 333 pass the literal pose rule.**

Later filter initialisation (valid, pose rule failed): 23; init delay [s] median 0.3, max 4.066: openloris_cafe1-1/e_sens_fix1/run_04, openloris_cafe1-1/e_sens_fix1/run_05, openloris_cafe1-2/e_yolo_naive/run_06, openloris_office1-1/e_sens_fix1/run_08, openloris_office1-2/e_savior_none/run_01, openloris_office1-2/e_sens_fix1/run_01, openloris_office1-2/e_sens_fix1/run_04, openloris_office1-2/e_yolo_naive/run_01, openloris_office1-3/e_savior_none/run_01, openloris_office1-3/e_sens_fix1/run_01, openloris_office1-3/e_yolo_naive/run_01, openloris_office1-7/e_sens_fix1/run_01, openloris_office1-7/e_sens_fix1/run_02, openloris_office1-7/e_sens_fix1/run_03, openloris_office1-7/e_sens_fix1/run_04, openloris_office1-7/e_sens_fix1/run_05, openloris_office1-7/e_sens_fix1/run_08, openloris_office1-7/e_sens_fix1/run_10, openloris_office1-7/e_yolo_naive/run_01, openloris_office1-7/e_yolo_naive/run_02, openloris_office1-7/e_yolo_naive/run_03, openloris_office1-7/e_yolo_naive/run_04, openloris_office1-7/e_yolo_naive/run_08

## Invalid runs

| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| openloris_cafe1-1 | e_savior_none | run_10 | ok/0 | 1037 | 1475 | ok | 2477 | 0 | 0 | 0 |
| openloris_cafe1-1 | e_sens_fix1 | run_01 | ok/0 | 1178 | 1629 | ok | 2618 | 0 | 0 | 0 |
| openloris_cafe1-2 | e_sens_fix1 | run_01 | ok/0 | 2090 | 2539 | ok | 4596 | 0 | 0 | 0 |
| openloris_cafe1-2 | e_yolo_naive | run_04 | ok/0 | 2090 | 2540 | ok | 4560 | 0 | 0 | 0 |
| openloris_office1-2 | e_sens_fix1 | run_02 | ok/0 | 378 | 828 | ok | 982 | 0 | 0 | 0 |
| openloris_office1-5 | e_savior_none | run_09 | ok/0 | 1000 | 1446 | ok | 2277 | 0 | 0 | 0 |
| openloris_office1-6 | e_yolo_naive | run_07 | ok/0 | 493 | 943 | ok | 1314 | 0 | 0 | 0 |
| openloris_office1-7 | e_yolo_naive | run_05 | ok/0 | 333 | 783 | ok | 1464 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_openvins | run_01 | no_info | 3388 | 3388 | n/a | 0 | 0 | 0 | 1 |
| uhumans2_office_s1_06h | e_openvins | run_06 | no_info | 3232 | 3233 | n/a | 0 | 0 | 0 | 1 |
| uhumans2_office_s1_06h | e_oracle_person | run_01 | no_info | 1556 | 3388 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_oracle_person | run_06 | no_info | 1402 | 3233 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_savior_none | run_01 | no_info | 1898 | 3388 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_savior_none | run_06 | no_info | 1744 | 3233 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_sens_fix1 | run_01 | no_info | 2971 | 3389 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_sens_fix1 | run_06 | no_info | 2808 | 3233 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_yolo_naive | run_01 | no_info | 2207 | 3389 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_06h | e_yolo_naive | run_06 | no_info | 2043 | 3233 | n/a | 0 | 0 | 0 | 0 |
| uhumans2_office_s1_12h | e_openvins | run_01 | no_info | 1352 | 1352 | n/a | 0 | 0 | 0 | 1 |
| uhumans2_office_s1_12h | e_openvins | run_06 | no_info | 1160 | 1160 | n/a | 0 | 0 | 0 | 1 |
