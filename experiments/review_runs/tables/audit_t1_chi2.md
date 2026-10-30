# Review-run validity audit: t1_chi2

root /home/sasa/workspace/savior_ws/results/review_runs/runs/t1; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/backend_v2/runs

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| gate_fix0 | 4 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | - |
| gate_fix2 | 4 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | - |
| gate_fix3 | 4 | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | - |
| gate_fix4 | 3 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | - |
| gate_k1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| gate_k2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| ovchi_010 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| ovchi_025 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| ovchi_050 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |

**Total: 247 / 259 valid; 247 sync ok; 247 pass the literal pose rule.**

## Invalid runs

| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| aisles_t1_L3 | gate_fix0 | run_02 | no_info | 641 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix0 | run_07 | no_info | 556 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix2 | run_02 | no_info | 412 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix2 | run_07 | no_info | 328 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix3 | run_02 | no_info | 197 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix3 | run_07 | no_info | 113 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix4 | run_02 | no_info | 0 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_fix4 | run_06 | no_info | 1026 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_k1 | run_01 | no_info | 908 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_k1 | run_06 | no_info | 810 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_k2 | run_01 | no_info | 694 | 1049 | n/a | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | gate_k2 | run_06 | no_info | 595 | 1049 | n/a | 0 | 0 | 0 | 0 |
