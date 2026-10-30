# Review-run validity audit: heldout

root /home/sasa/workspace/savior_ws/results/review_runs/runs/heldout; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/backend_v2/heldout/runs

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| ctl_savior_none | 10 | 10 | 10 | 10 | 10 | 0 | 0 | 0 | 0 | 10 / 10 identical |
| ctl_sens_fix1 | 20 | 20 | 20 | 20 | 20 | 0 | 0 | 0 | 0 | 10 / 20 identical |
| ovchi_best | 240 | 238 | 240 | 238 | 238 | 0 | 0 | 0 | 0 | - |
| sf1_chibest | 240 | 240 | 240 | 230 | 240 | 0 | 0 | 0 | 0 | - |
| sf1_noint | 240 | 239 | 240 | 232 | 239 | 0 | 0 | 0 | 0 | - |
| sf1_nomotion | 240 | 240 | 240 | 230 | 240 | 0 | 0 | 0 | 0 | - |

**Total: 987 / 990 valid; 990 sync ok; 960 pass the literal pose rule.**

Later filter initialisation (valid, pose rule failed): 27; init delay [s] median 1.6, max 1.8: hall_t2_L3/sf1_chibest/run_02, hall_t2_L3/sf1_chibest/run_03, hall_t2_L3/sf1_chibest/run_04, hall_t2_L3/sf1_chibest/run_05, hall_t2_L3/sf1_chibest/run_06, hall_t2_L3/sf1_chibest/run_07, hall_t2_L3/sf1_chibest/run_08, hall_t2_L3/sf1_chibest/run_09, hall_t2_L3/sf1_chibest/run_10, hall_t2_L3/sf1_noint/run_05, hall_t2_L3/sf1_noint/run_06, hall_t2_L3/sf1_noint/run_07, hall_t2_L3/sf1_noint/run_08, hall_t2_L3/sf1_noint/run_09, hall_t2_L3/sf1_noint/run_10, hall_t2_L3/sf1_nomotion/run_02, hall_t2_L3/sf1_nomotion/run_03, hall_t2_L3/sf1_nomotion/run_04, hall_t2_L3/sf1_nomotion/run_05, hall_t2_L3/sf1_nomotion/run_06, hall_t2_L3/sf1_nomotion/run_07, hall_t2_L3/sf1_nomotion/run_08, hall_t2_L3/sf1_nomotion/run_09, hall_t2_L3/sf1_nomotion/run_10, parking_lot_low/sf1_chibest/run_08, parking_lot_low/sf1_noint/run_08, parking_lot_low/sf1_nomotion/run_08

## Invalid runs

| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| city_night_low | sf1_noint | run_08 | ok/0 | 516 | 518 | ok | 0 | 0 | 0 | 0 |
| parking_lot_none | ovchi_best | run_07 | ok/0 | 499 | 502 | n/a | 0 | 0 | 0 | 0 |
| parking_lot_none | ovchi_best | run_08 | ok/0 | 500 | 502 | n/a | 0 | 0 | 0 | 0 |
