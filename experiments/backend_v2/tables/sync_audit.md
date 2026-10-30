# M2b validity audit (/home/sasa/workspace/savior_ws/results/backend_v2/runs)

valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 + poses >= same-offset openvins poses - 1

valid_end = sync ok + trajectory reaches the openvins end (<= 1 frame) + <= 1 pose missing after the method's own first pose (late init allowed)

| method | runs | valid (literal pose rule) | valid_end | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| openvins | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| oracle_class_ext | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| oracle_class_naive | 80 | 80 | 79 | 80 | 80 | 0 | 0 | 0 | 0 |
| oracle_moving | 80 | 80 | 79 | 80 | 80 | 0 | 0 | 0 | 0 |
| oracle_moving_ext | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| p7_nb | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| savior_edge | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| savior_none | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| sens_fix1 | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |
| yolo_naive | 80 | 80 | 80 | 80 | 80 | 0 | 0 | 0 | 0 |

**Total: 800 / 800 valid (literal pose rule); 798 / 800 valid_end; 800 sync ok.**

Pose-count difference openvins - method (runs): +0: 718, +1: 2

savior_none == openvins (trajectory md5), warehouse: 80 / 80

Runs failing only the literal pose rule because of a later filter initialisation (end complete, sync ok): 0; init delay vs openvins [s]: median -, max -

## Invalid runs

| seq | method | run | status | poses | openvins poses | FINAL | fb latest | fb empty | late | in core |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| aisles_t1_L0 | oracle_class_naive | run_04 | ok/0 | 1048 | 1049 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | oracle_moving | run_04 | ok/0 | 1048 | 1049 | ok | 0 | 0 | 0 | 0 |
