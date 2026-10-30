# Review-run validity audit: t1

root /home/sasa/workspace/savior_ws/results/review_runs/runs/t1; reference OpenVINS-v2 runs /home/sasa/workspace/savior_ws/results/backend_v2/runs

valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 (failing it with end ok = later filter initialisation, kept and flagged).

| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| gate_fix0 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_fix2 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_fix3 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_fix4 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_k1 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_k2 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_k4 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_kmed1 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| gate_kmed3 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| ovchi_010 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| ovchi_025 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |
| ovchi_050 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 | - |

**Total: 960 / 960 valid; 960 sync ok; 960 pass the literal pose rule.**
