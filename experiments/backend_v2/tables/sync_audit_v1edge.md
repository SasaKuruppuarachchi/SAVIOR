# M2b validity audit (/home/sasa/workspace/savior_ws/results/backend_v2/runs_v1)

valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 + poses >= same-offset openvins poses - 1

valid_end = sync ok + trajectory reaches the openvins end (<= 1 frame) + <= 1 pose missing after the method's own first pose (late init allowed)

| method | runs | valid (literal pose rule) | valid_end | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| savior_edge | 80 | 0 | 0 | 80 | 0 | 0 | 0 | 0 | 0 |

**Total: 0 / 80 valid (literal pose rule); 0 / 80 valid_end; 80 sync ok.**

Pose-count difference openvins - method (runs): 

Runs failing only the literal pose rule because of a later filter initialisation (end complete, sync ok): 0; init delay vs openvins [s]: median -, max -

## Invalid runs

| seq | method | run | status | poses | openvins poses | FINAL | fb latest | fb empty | late | in core |
|---|---|---|---|--:|--:|---|--:|--:|--:|--:|
| aisles_t1_L0 | savior_edge | run_01 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_02 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_03 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_04 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_05 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_06 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_07 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_08 | ok/0 | 2102 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_09 | ok/0 | 2098 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | savior_edge | run_10 | ok/0 | 2094 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_01 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_02 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_03 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_04 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_05 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_06 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_07 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_08 | ok/0 | 2102 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_09 | ok/0 | 2098 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | savior_edge | run_10 | ok/0 | 2094 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_01 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_02 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_03 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_04 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_05 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_06 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_07 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_08 | ok/0 | 2102 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_09 | ok/0 | 2098 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | savior_edge | run_10 | ok/0 | 2094 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_01 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_02 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_03 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_04 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_05 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_06 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_07 | ok/0 | 2103 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_08 | ok/0 | 2102 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_09 | ok/0 | 2098 | -1 | ok | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | savior_edge | run_10 | ok/0 | 2094 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_01 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_02 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_03 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_04 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_05 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_06 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_07 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_08 | ok/0 | 2185 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_09 | ok/0 | 2181 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L0 | savior_edge | run_10 | ok/0 | 2177 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_01 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_02 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_03 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_04 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_05 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_06 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_07 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_08 | ok/0 | 2185 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_09 | ok/0 | 2181 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L1 | savior_edge | run_10 | ok/0 | 2177 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_01 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_02 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_03 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_04 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_05 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_06 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_07 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_08 | ok/0 | 2185 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_09 | ok/0 | 2181 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L2 | savior_edge | run_10 | ok/0 | 2177 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_01 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_02 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_03 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_04 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_05 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_06 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_07 | ok/0 | 2186 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_08 | ok/0 | 2185 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_09 | ok/0 | 2181 | -1 | ok | 0 | 0 | 0 | 0 |
| hall_t1_L3 | savior_edge | run_10 | ok/0 | 2177 | -1 | ok | 0 | 0 | 0 | 0 |
