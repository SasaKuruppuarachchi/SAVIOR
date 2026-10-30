# Review-run validity audit: e

root /home/sasa/workspace/savior_ws/results/review_runs/runs/e; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/review_runs/runs/e

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| e_openvins | 115 | 115 | 115 | 115 | 115 | 0 | 0 | 0 | 0 | - |
| e_oracle_person | 20 | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | - |
| e_savior_none | 110 | 108 | 108 | 103 | 108 | 4781 | 0 | 0 | 0 | 34 / 110 identical |
| e_sens_fix1 | 115 | 111 | 111 | 99 | 112 | 25678 | 0 | 0 | 0 | - |
| e_yolo_naive | 115 | 113 | 113 | 105 | 113 | 2776 | 0 | 0 | 0 | - |

**Total: 467 / 475 valid; 467 sync ok; 442 pass the literal pose rule.**

Later filter initialisation (valid, pose rule failed): 26; init delay [s] median 0.3, max 4.066: openloris_cafe1-1/e_sens_fix1/run_04, openloris_cafe1-1/e_sens_fix1/run_05, openloris_cafe1-2/e_yolo_naive/run_06, openloris_office1-1/e_sens_fix1/run_08, openloris_office1-2/e_savior_none/run_01, openloris_office1-2/e_sens_fix1/run_01, openloris_office1-2/e_sens_fix1/run_04, openloris_office1-2/e_yolo_naive/run_01, openloris_office1-3/e_savior_none/run_01, openloris_office1-3/e_sens_fix1/run_01, openloris_office1-3/e_yolo_naive/run_01, openloris_office1-7/e_sens_fix1/run_01, openloris_office1-7/e_sens_fix1/run_02, openloris_office1-7/e_sens_fix1/run_03, openloris_office1-7/e_sens_fix1/run_04, openloris_office1-7/e_sens_fix1/run_05, openloris_office1-7/e_sens_fix1/run_08, openloris_office1-7/e_sens_fix1/run_10, openloris_office1-7/e_yolo_naive/run_01, openloris_office1-7/e_yolo_naive/run_02, openloris_office1-7/e_yolo_naive/run_03, openloris_office1-7/e_yolo_naive/run_04, openloris_office1-7/e_yolo_naive/run_08, uhumans2_office_s1_06h/e_savior_none/run_01, uhumans2_office_s1_06h/e_savior_none/run_02, uhumans2_office_s1_06h/e_savior_none/run_03

## Invalid runs

| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| openloris_cafe1-1 | e_savior_none | run_10 | ok/0 | 1066 | 1475 | ok | 2503 | 0 | 0 | 0 |
| openloris_cafe1-2 | e_sens_fix1 | run_01 | ok/0 | 2070 | 2539 | ok | 4598 | 0 | 0 | 0 |
| openloris_office1-2 | e_sens_fix1 | run_02 | ok/0 | 378 | 828 | ok | 982 | 0 | 0 | 0 |
| openloris_office1-5 | e_savior_none | run_09 | ok/0 | 999 | 1446 | ok | 2278 | 0 | 0 | 0 |
| openloris_office1-6 | e_yolo_naive | run_07 | ok/0 | 493 | 943 | ok | 1314 | 0 | 0 | 0 |
| openloris_office1-7 | e_yolo_naive | run_05 | ok/0 | 333 | 783 | ok | 1462 | 0 | 0 | 0 |
| uhumans2_office_s1_00h | e_sens_fix1 | run_03 | ok/0 | 7891 | 7891 | ok | 3608 | 0 | 0 | 1 |
| uhumans2_office_s1_06h | e_sens_fix1 | run_03 | ok/0 | 7808 | 8106 | ok | 16490 | 0 | 0 | 0 |
