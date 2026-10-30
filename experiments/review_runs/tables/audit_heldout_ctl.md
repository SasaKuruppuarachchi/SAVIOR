# Review-run validity audit: heldout_ctl

root /home/sasa/workspace/savior_ws/results/review_runs/runs/heldout; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/backend_v2/heldout/runs

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| ctl_savior_none | 10 | 10 | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 / 10 identical |
| ctl_sens_fix1 | 20 | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 10 / 20 identical |
| ovchi_best | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| sf1_chibest | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| sf1_noint | 5 | 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | - |
| sf1_nomotion | 3 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | - |

**Total: 34 / 41 valid; 34 sync ok; 34 pass the literal pose rule.**

## Invalid runs

| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| aisles_t2_L0 | ovchi_best | run_01 | no_info | 105 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_chibest | run_01 | no_info | 704 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_chibest | run_06 | no_info | 251 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_noint | run_03 | no_info | 867 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_noint | run_07 | no_info | 142 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_nomotion | run_02 | no_info | 0 | 926 | n/a | 0 | 0 | 0 | 0 |
| aisles_t2_L0 | sf1_nomotion | run_06 | no_info | 860 | 926 | n/a | 0 | 0 | 0 | 0 |
