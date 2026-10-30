# AMENDMENT_04: Y1-Y4 (exploratory, own Holm family; outside P1-P5, S1-S14, X1-X3), cap 10 m, trajectory LMM

missing runs (6 methods): 0

## Parameter diff (run_info launch commands, same sequence and run)

- sf1_nis vs sens_fix1: 480 run pairs, deltas [['ov_set', 'savior_nis_gate=true', '']], install ['INSTALL=/home/sasa/workspace/savior_ws/results/semantic_gate/install'], only the FREEZE.yaml deltas: True
- ov_nis vs openvins: 480 run pairs, deltas [['ov_set', 'savior_nis_gate=true', '']], install ['INSTALL=/home/sasa/workspace/savior_ws/results/semantic_gate/install'], only the FREEZE.yaml deltas: True
- savior_sg vs sens_fix1: 480 run pairs, deltas [['ov_set', 'savior_semantic_gate=true savior_sg_keep_band=false savior_sg_mult_band=0.25 savior_sg_mult_static=0.25', ''], ['pset', 'compose.movable_static_value=64', '']], install ['INSTALL=/home/sasa/workspace/savior_ws/results/semantic_gate/install'], only the FREEZE.yaml deltas: True

| id | comparison | group | estimate [95 % CI] | 90 % CI | p (two-sided; Y4: TOST) | Holm p (Y family) | sign-flip p | traj better/worse | n traj |
|---|---|---|---|---|---|---|---|---|---|
| Y1 | SAVIOR + NIS gate vs SAVIOR | high | -24.1 % [-33.1, -13.9] | [-31.7, -15.7] | 1.5e-04 | 4.6e-04 | 1.4e-04 | 20/4 | 24 |
| Y2 | SAVIOR + NIS gate vs OpenVINS chi2 x0.25 | high | -9.1 % [-20.8, +4.4] | [-18.9, +1.9] | 0.167 | 0.334 | 0.116 | 17/7 | 24 |
| Y3 | SAVIOR + NIS gate vs OpenVINS + NIS gate | high | -84.0 % [-90.7, -72.4] | [-89.8, -74.9] | 4.5e-07 | 1.8e-06 | 0.0e+00 | 24/0 | 24 |
| Y4 | SAVIOR + NIS gate vs OpenVINS | static | -33.1 % [-39.8, -25.8] | [-38.7, -27.1] | 1.000 | 1.000 | 0.0e+00 | 23/1 | 24 |
| D1 | SAVIOR-SG vs SAVIOR | high | +2.8 % [-4.2, +10.3] | [-3.0, +9.0] | 0.419 | - | 0.439 | 14/10 | 24 |
| D1 | SAVIOR-SG vs SAVIOR | low | -4.1 % [-6.8, -1.3] | [-6.4, -1.8] | 0.007 | - | 0.007 | 19/5 | 24 |
| D1 | SAVIOR-SG vs SAVIOR | static | -3.1 % [-6.4, +0.3] | [-5.9, -0.3] | 0.074 | - | 0.074 | 17/7 | 24 |

D1 rows (savior_sg vs sens_fix1) are descriptive, not in the Y Holm family. Y4 equivalent (90 % CI inside the P5 margins): [False]

## Cap sensitivity

| id | cap | estimate [95 % CI] | p | n traj |
|---|---|---|---|---|
| Y1 | 2.0 | -24.3 % [-33.3, -14.2] | 1.3e-04 | 24 |
| Y1 | 5.0 | -24.0 % [-33.1, -13.8] | 1.7e-04 | 24 |
| Y1 | 10.0 | -24.1 % [-33.1, -13.9] | 1.5e-04 | 24 |
| Y1 | 50.0 | -24.6 % [-33.4, -14.7] | 8.9e-05 | 24 |
| Y1 | excl | -24.6 % [-33.5, -14.5] | 1.2e-04 | 24 |
| Y2 | 2.0 | -5.0 % [-15.0, +6.3] | 0.354 | 24 |
| Y2 | 5.0 | -7.1 % [-18.2, +5.5] | 0.242 | 24 |
| Y2 | 10.0 | -9.1 % [-20.8, +4.4] | 0.167 | 24 |
| Y2 | 50.0 | -13.8 % [-27.1, +1.9] | 0.079 | 24 |
| Y2 | excl | +3.7 % [-5.4, +13.7] | 0.417 | 24 |
| Y3 | 2.0 | -77.8 % [-85.7, -65.6] | 3.1e-07 | 24 |
| Y3 | 5.0 | -82.5 % [-89.6, -70.7] | 4.1e-07 | 24 |
| Y3 | 10.0 | -84.0 % [-90.7, -72.4] | 4.5e-07 | 24 |
| Y3 | 50.0 | -86.1 % [-92.4, -74.8] | 5.7e-07 | 24 |
| Y3 | excl | -63.8 % [-76.3, -44.8] | 5.0e-05 | 24 |
| Y4 | 2.0 | -33.1 % [-39.8, -25.8] | 4.7e-08 | 24 |
| Y4 | 5.0 | -33.1 % [-39.8, -25.8] | 4.7e-08 | 24 |
| Y4 | 10.0 | -33.1 % [-39.8, -25.8] | 4.7e-08 | 24 |
| Y4 | 50.0 | -33.1 % [-39.8, -25.8] | 4.7e-08 | 24 |
| Y4 | excl | -33.1 % [-39.8, -25.8] | 4.7e-08 | 24 |
| D1 | 2.0 | +1.5 % [-3.9, +7.1] | 0.583 | 24 |
| D1 | 5.0 | +2.3 % [-4.0, +8.9] | 0.474 | 24 |
| D1 | 10.0 | +2.8 % [-4.2, +10.3] | 0.419 | 24 |
| D1 | 50.0 | +4.2 % [-4.5, +13.8] | 0.340 | 24 |
| D1 | excl | -0.2 % [-4.1, +3.8] | 0.908 | 24 |
| D1 | 2.0 | -4.1 % [-6.8, -1.3] | 0.007 | 24 |
| D1 | 5.0 | -4.1 % [-6.8, -1.3] | 0.007 | 24 |
| D1 | 10.0 | -4.1 % [-6.8, -1.3] | 0.007 | 24 |
| D1 | 50.0 | -4.1 % [-6.8, -1.3] | 0.007 | 24 |
| D1 | excl | -4.1 % [-6.8, -1.3] | 0.007 | 24 |
| D1 | 2.0 | -3.1 % [-6.4, +0.3] | 0.074 | 24 |
| D1 | 5.0 | -3.1 % [-6.4, +0.3] | 0.074 | 24 |
| D1 | 10.0 | -3.1 % [-6.4, +0.3] | 0.074 | 24 |
| D1 | 50.0 | -3.1 % [-6.4, +0.3] | 0.074 | 24 |
| D1 | excl | -3.1 % [-6.4, +0.3] | 0.074 | 24 |

## Per environment (descriptive)

| id | env | estimate [95 % CI] | p | traj better/worse |
|---|---|---|---|---|
| Y1 | fw | -35.9 % [-56.3, -5.9] | 0.031 | 5/1 |
| Y1 | sw | -27.7 % [-46.7, -2.0] | 0.041 | 5/1 |
| Y1 | ms | -15.5 % [-39.3, +17.7] | 0.249 | 5/1 |
| Y1 | wx | -15.4 % [-40.7, +20.5] | 0.278 | 5/1 |
| Y2 | fw | -8.9 % [-38.1, +34.0] | 0.561 | 3/3 |
| Y2 | sw | -13.0 % [-36.8, +19.8] | 0.314 | 5/1 |
| Y2 | ms | -5.4 % [-33.2, +34.1] | 0.699 | 4/2 |
| Y2 | wx | -8.8 % [-41.4, +41.8] | 0.613 | 5/1 |
| Y3 | fw | -84.5 % [-96.0, -40.3] | 0.016 | 6/0 |
| Y3 | sw | -85.6 % [-96.8, -34.5] | 0.022 | 6/0 |
| Y3 | ms | -85.7 % [-96.6, -39.7] | 0.018 | 6/0 |
| Y3 | wx | -79.5 % [-94.4, -25.7] | 0.025 | 6/0 |
| Y4 | fw | -35.5 % [-51.7, -13.8] | 0.012 | 6/0 |
| Y4 | sw | -36.3 % [-45.2, -26.0] | 5.8e-04 | 6/0 |
| Y4 | ms | -24.8 % [-34.6, -13.5] | 0.003 | 6/0 |
| Y4 | wx | -35.4 % [-56.7, -3.6] | 0.038 | 5/1 |

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
| SAVIOR + NIS gate | static | 0 / 120 | 0.0 % [0.0, 0.0] |
| SAVIOR + NIS gate | low | 0 / 240 | 0.0 % [0.0, 0.0] |
| SAVIOR + NIS gate | high | 2 / 240 | 0.8 % [0.0, 2.1] |
| SAVIOR + NIS gate | all | 2 / 480 | 0.4 % [0.0, 1.0] |
| OpenVINS + NIS gate | static | 0 / 120 | 0.0 % [0.0, 0.0] |
| OpenVINS + NIS gate | low | 0 / 240 | 0.0 % [0.0, 0.0] |
| OpenVINS + NIS gate | high | 84 / 240 | 35.0 % [27.9, 41.7] |
| OpenVINS + NIS gate | all | 84 / 480 | 17.5 % [14.0, 20.8] |
| SAVIOR-SG | static | 0 / 120 | 0.0 % [0.0, 0.0] |
| SAVIOR-SG | low | 0 / 240 | 0.0 % [0.0, 0.0] |
| SAVIOR-SG | high | 3 / 240 | 1.2 % [0.0, 3.3] |
| SAVIOR-SG | all | 3 / 480 | 0.6 % [0.0, 1.7] |
