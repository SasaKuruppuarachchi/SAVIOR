# C++ port closed-loop ATE parity vs the frozen Python main (t1 tuning set, 10 offsets 0.0-1.8 s; failure = ATE > 2 m)

## Median ATE [m] ([n] = failures; RPE: failed runs (ATE > FAIL_M) count as inf)

| seq | cpp_edge_final |
|---|--:|
| aisles_t1_L0 | 0.102 |
| aisles_t1_L1 | 0.100 |
| aisles_t1_L2 | 0.118 |
| aisles_t1_L3 | 0.115 |
| hall_t1_L0 | 0.125 |
| hall_t1_L1 | 0.163 |
| hall_t1_L2 | 0.269 |
| hall_t1_L3 | 0.160 |

| failures (all) | 0 |

## Paired vs e_c_n672_L250dfronly (geometric-mean ATE ratio - 1; negative = better; Holm over the methods within each group)

| method | L0+L1 | L2+L3 | all | hall_L3 | L2 | L3 |
|---|---|---|---|---|---|---|
| cpp_edge_final | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/40 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/40 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/80 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/10 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/20 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/20 |

## Trajectory identity vs the paired reference run (md5 of stamped_traj_estimate.txt; wins/losses/ties = paired log-ratio < 0 / > 0 / = 0)

| method | aisles_t1_L0 | aisles_t1_L1 | aisles_t1_L2 | aisles_t1_L3 | hall_t1_L0 | hall_t1_L1 | hall_t1_L2 | hall_t1_L3 | all |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| cpp_edge_final | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 80/80 |
