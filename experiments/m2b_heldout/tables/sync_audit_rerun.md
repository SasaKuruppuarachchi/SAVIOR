# M2b validity audit (runs_rerun)

valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 + poses >= same-offset openvins poses - 1

valid_end = sync ok + trajectory reaches the openvins end (<= 1 frame) + <= 1 pose missing after the method's own first pose (late init allowed)

| method | runs | valid (literal pose rule) | valid_end | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| oracle_class_ext | 11 | 0 | 0 | 11 | 0 | 0 | 0 | 0 | 0 |
| p7_nb | 10 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |
| savior_edge | 2 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| sens_fix1 | 10 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |
| yolo_naive | 10 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |

**Total: 0 / 43 valid (literal pose rule); 0 / 43 valid_end; 43 sync ok.**

Pose-count difference openvins - method (runs): 

Runs failing only the literal pose rule because of a later filter initialisation (end complete, sync ok): 0; init delay vs openvins [s]: median -, max -

## Invalid runs

| seq | method | run | status | poses | openvins poses | FINAL | fb latest | fb empty | late | in core |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| dock_t2_L3 | oracle_class_ext | run_10 | ok/0 | 2071 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_01 | ok/0 | 2150 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_02 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_03 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_04 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_05 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_06 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_07 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_08 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_09 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | oracle_class_ext | run_10 | ok/0 | 2153 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_02 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_03 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_04 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_05 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_06 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_07 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_08 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_09 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | p7_nb | run_10 | ok/0 | 2141 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_02 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_03 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_04 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_05 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_06 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_07 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_08 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_09 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | sens_fix1 | run_10 | ok/0 | 2139 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_02 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_03 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_04 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_05 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_06 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_07 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_08 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_09 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t2_L3 | yolo_naive | run_10 | ok/0 | 2142 | -1 | ok | 0 | 0 | 0 | 0 |
| parking_lot_mid | p7_nb | run_01 | ok/0 | 1033 | -1 | ok | 0 | 0 | 0 | 0 |
| parking_lot_mid | savior_edge | run_06 | ok/0 | 1003 | -1 | ok | 0 | 0 | 0 | 0 |
| parking_lot_mid | savior_edge | run_09 | ok/0 | 979 | -1 | ok | 0 | 0 | 0 | 0 |
| parking_lot_mid | sens_fix1 | run_01 | ok/0 | 1033 | -1 | ok | 0 | 0 | 0 | 0 |
| parking_lot_mid | yolo_naive | run_01 | ok/0 | 1033 | -1 | ok | 0 | 0 | 0 | 0 |
