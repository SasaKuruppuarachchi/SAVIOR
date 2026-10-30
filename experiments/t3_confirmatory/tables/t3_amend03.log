# AMENDMENT_03: X1-X3 (exploratory, own Holm family; outside P1-P5 and S1-S14), cap 10 m, trajectory LMM

missing runs (4 methods): 0

## Parameter diff (run_info launch commands, same sequence and run)

- ovchi_best vs openvins: 480 run pairs, deltas [['ov_set', 'up_msckf_chi2_multipler=0.25 up_slam_chi2_multipler=0.25', '']], only the two chi2 multipliers: True
- sf1_chibest vs sens_fix1: 480 run pairs, deltas [['ov_set', 'up_msckf_chi2_multipler=0.25 up_slam_chi2_multipler=0.25', '']], only the two chi2 multipliers: True

| id | comparison | group | estimate [95 % CI] | p | Holm p (X family) | sign-flip p | traj better/worse | n traj |
|---|---|---|---|---|---|---|---|---|
| X1 | SAVIOR vs OpenVINS chi2 x0.25 | high | +19.8 % [+2.8, +39.7] | 0.023 | 0.045 | 0.005 | 7/17 | 24 |
| X2 | SAVIOR + chi2 x0.25 vs OpenVINS chi2 x0.25 | high | -5.1 % [-16.0, +7.3] | 0.391 | 0.391 | 0.304 | 12/12 | 24 |
| X3 | OpenVINS chi2 x0.25 vs OpenVINS | high | -56.4 % [-64.5, -46.4] | 2.1e-08 | 6.3e-08 | 0.0e+00 | 24/0 | 24 |

## Cap sensitivity

| id | cap | estimate [95 % CI] | p | n traj |
|---|---|---|---|---|
| X1 | 2.0 | +25.6 % [+10.6, +42.6] | 0.001 | 24 |
| X1 | 5.0 | +22.3 % [+6.1, +40.9] | 0.007 | 24 |
| X1 | 10.0 | +19.8 % [+2.8, +39.7] | 0.023 | 24 |
| X1 | 50.0 | +14.3 % [-4.7, +37.2] | 0.142 | 24 |
| X1 | excl | +38.2 % [+26.2, +51.4] | 1.8e-07 | 24 |
| X2 | 2.0 | -0.5 % [-10.1, +10.1] | 0.920 | 24 |
| X2 | 5.0 | -3.1 % [-13.5, +8.4] | 0.566 | 24 |
| X2 | 10.0 | -5.1 % [-16.0, +7.3] | 0.391 | 24 |
| X2 | 50.0 | -9.4 % [-22.0, +5.2] | 0.184 | 24 |
| X2 | excl | +9.9 % [-0.9, +21.8] | 0.072 | 24 |
| X3 | 2.0 | -55.2 % [-62.9, -45.9] | 7.7e-09 | 24 |
| X3 | 5.0 | -55.9 % [-63.8, -46.3] | 1.3e-08 | 24 |
| X3 | 10.0 | -56.4 % [-64.5, -46.4] | 2.1e-08 | 24 |
| X3 | 50.0 | -57.6 % [-66.3, -46.6] | 8.5e-08 | 24 |
| X3 | excl | -54.8 % [-62.6, -45.5] | 8.8e-09 | 24 |

## Per environment (descriptive)

| id | env | estimate [95 % CI] | p | traj better/worse |
|---|---|---|---|---|
| X1 | fw | +42.0 % [+10.7, +82.3] | 0.015 | 0/6 |
| X1 | sw | +20.4 % [-23.8, +90.1] | 0.345 | 3/3 |
| X1 | ms | +11.9 % [-23.2, +63.1] | 0.478 | 2/4 |
| X1 | wx | +7.8 % [-29.5, +64.8] | 0.668 | 2/4 |
| X2 | fw | +12.6 % [-10.5, +41.6] | 0.240 | 1/5 |
| X2 | sw | -6.4 % [-34.9, +34.6] | 0.662 | 3/3 |
| X2 | ms | -15.9 % [-40.0, +17.7] | 0.242 | 4/2 |
| X2 | wx | -8.4 % [-30.6, +21.1] | 0.457 | 4/2 |
| X3 | fw | -64.5 % [-81.1, -33.4] | 0.008 | 6/0 |
| X3 | sw | -56.2 % [-71.2, -33.4] | 0.004 | 6/0 |
| X3 | ms | -55.9 % [-73.6, -26.3] | 0.009 | 6/0 |
| X3 | wx | -47.4 % [-68.3, -12.9] | 0.022 | 6/0 |

## Failures (ATE > 2 m)

| method | group | failures / runs | rate [cluster 95 % CI] |
|---|---|---|---|
| OpenVINS | static | 0 / 120 | 0.0 % [0.0, 0.0] |
| OpenVINS | low | 0 / 240 | 0.0 % [0.0, 0.0] |
| OpenVINS | high | 12 / 240 | 5.0 % [2.1, 8.8] |
| OpenVINS | all | 12 / 480 | 2.5 % [1.0, 4.4] |
| SAVIOR | static | 0 / 120 | 0.0 % [0.0, 0.0] |
| SAVIOR | low | 0 / 240 | 0.0 % [0.0, 0.0] |
| SAVIOR | high | 1 / 240 | 0.4 % [0.0, 1.2] |
| SAVIOR | all | 1 / 480 | 0.2 % [0.0, 0.6] |
| OpenVINS chi2 x0.25 | static | 1 / 120 | 0.8 % [0.0, 2.5] |
| OpenVINS chi2 x0.25 | low | 1 / 240 | 0.4 % [0.0, 1.2] |
| OpenVINS chi2 x0.25 | high | 8 / 240 | 3.3 % [1.2, 5.8] |
| OpenVINS chi2 x0.25 | all | 9 / 480 | 1.9 % [0.8, 3.1] |
| SAVIOR + chi2 x0.25 | static | 1 / 120 | 0.8 % [0.0, 2.5] |
| SAVIOR + chi2 x0.25 | low | 1 / 240 | 0.4 % [0.0, 1.2] |
| SAVIOR + chi2 x0.25 | high | 1 / 240 | 0.4 % [0.0, 1.2] |
| SAVIOR + chi2 x0.25 | all | 2 / 480 | 0.4 % [0.0, 1.0] |
