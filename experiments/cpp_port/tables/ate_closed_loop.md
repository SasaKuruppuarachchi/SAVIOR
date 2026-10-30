# C++ port closed-loop ATE parity vs the frozen Python main (t1 tuning set, 10 offsets 0.0-1.8 s; failure = ATE > 2 m)

## Median ATE [m] ([n] = failures; RPE: failed runs (ATE > FAIL_M) count as inf)

| seq | cpp_main_final | cpp_main |
|---|--:|--:|
| aisles_t1_L0 | 0.098 | 0.098 |
| aisles_t1_L1 | 0.096 | 0.096 |
| aisles_t1_L2 | 0.119 | 0.119 |
| aisles_t1_L3 | 0.176 | 0.176 |
| hall_t1_L0 | 0.136 | 0.136 |
| hall_t1_L1 | 0.172 | 0.172 |
| hall_t1_L2 | 0.212 | 0.212 |
| hall_t1_L3 | 0.130 | 0.130 |

| failures (all) | 0 | 0 |

## Paired vs sens_fix1 (geometric-mean ATE ratio - 1; negative = better; Holm over the methods within each group)

| method | L0+L1 | L2+L3 | all | hall_L3 | L2 | L3 |
|---|---|---|---|---|---|---|
| cpp_main_final | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/40 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/40 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/80 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/10 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/20 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/20 |
| cpp_main | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/1/39 | +0.00 % [+0.00, +0.01] p=0.626 (H 1.000) 8/6/26 | +0.00 % [+0.00, +0.00] p=0.389 (H 0.779) 8/7/65 | +0.00 % [+0.00, +0.00] p=1.000 (H 1.000) 0/0/10 | +0.01 % [+0.00, +0.02] p=0.125 (H 0.250) 0/4/16 | +0.00 % [-0.00, +0.00] p=0.105 (H 0.211) 8/2/10 |

## Trajectory identity vs the paired reference run (md5 of stamped_traj_estimate.txt; wins/losses/ties = paired log-ratio < 0 / > 0 / = 0)

| method | aisles_t1_L0 | aisles_t1_L1 | aisles_t1_L2 | aisles_t1_L3 | hall_t1_L0 | hall_t1_L1 | hall_t1_L2 | hall_t1_L3 | all |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| cpp_main_final | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 80/80 |
| cpp_main | 10/10 | 10/10 | 10/10 | 0/10 | 10/10 | 9/10 | 6/10 | 10/10 | 65/80 |
