# P7 sync check (every closed-loop run; valid = clean exit, trajectory, FINAL fallback_latest = fallback_empty = late = 0, n_in_core = 0)

| method | runs | valid | fallbacks | late | n_in_core | no FINAL line |
|---|--:|--:|--:|--:|--:|--:|
| cpp_edge_final | 80 | 0 | 0 | 0 | 0 | 80 |
| cpp_main | 80 | 80 | 0 | 0 | 0 | 0 |
| cpp_main_final | 80 | 80 | 0 | 0 | 0 | 0 |

**Total: 160 / 240 valid.**

## Invalid runs

| seq | method | run | status | traj | FINAL | fb latest | fb empty | late | in core |
|---|---|---|---|--:|---|--:|--:|--:|--:|
| aisles_t1_L0 | cpp_edge_final | run_01 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_02 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_03 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_04 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_05 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_06 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_07 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_08 | ok/0 | 2103 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_09 | ok/0 | 2099 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L0 | cpp_edge_final | run_10 | ok/0 | 2095 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_01 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_02 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_03 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_04 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_05 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_06 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_07 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_08 | ok/0 | 2103 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_09 | ok/0 | 2099 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L1 | cpp_edge_final | run_10 | ok/0 | 2095 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_01 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_02 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_03 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_04 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_05 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_06 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_07 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_08 | ok/0 | 2103 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_09 | ok/0 | 2099 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L2 | cpp_edge_final | run_10 | ok/0 | 2095 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_01 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_02 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_03 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_04 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_05 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_06 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_07 | ok/0 | 2104 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_08 | ok/0 | 2103 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_09 | ok/0 | 2099 | - | 0 | 0 | 0 | 0 |
| aisles_t1_L3 | cpp_edge_final | run_10 | ok/0 | 2095 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_01 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_02 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_03 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_04 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_05 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_06 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_07 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_08 | ok/0 | 2186 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_09 | ok/0 | 2182 | - | 0 | 0 | 0 | 0 |
| hall_t1_L0 | cpp_edge_final | run_10 | ok/0 | 2178 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_01 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_02 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_03 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_04 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_05 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_06 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_07 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_08 | ok/0 | 2186 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_09 | ok/0 | 2182 | - | 0 | 0 | 0 | 0 |
| hall_t1_L1 | cpp_edge_final | run_10 | ok/0 | 2178 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_01 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_02 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_03 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_04 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_05 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_06 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_07 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_08 | ok/0 | 2186 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_09 | ok/0 | 2182 | - | 0 | 0 | 0 | 0 |
| hall_t1_L2 | cpp_edge_final | run_10 | ok/0 | 2178 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_01 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_02 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_03 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_04 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_05 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_06 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_07 | ok/0 | 2187 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_08 | ok/0 | 2186 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_09 | ok/0 | 2182 | - | 0 | 0 | 0 | 0 |
| hall_t1_L3 | cpp_edge_final | run_10 | ok/0 | 2178 | - | 0 | 0 | 0 | 0 |
