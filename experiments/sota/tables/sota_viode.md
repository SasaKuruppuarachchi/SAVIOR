# M3b SOTA benchmark: VIODE (12 sequences)

VINS-Fusion, DynaVINS, ORB-SLAM3 (stereo-inertial, loop closure off), image savior-sota:noetic; 10 late-start offsets per sequence = the P5 offsets of our methods (protocol (a), no bag-start column); rate 0.5. ATE RMSE [m], posyaw alignment, full sequence (savior-eval multi). Failure = ATE > 1 m or no estimate; [n] = failures. OpenVINS = P5 runs (results/p5_viode/<seq>/openvins; the M2b re-runs reproduce them to ~1e-6 m) at the same offsets.

## Median ATE [m] over 10 offsets ([n] = failures)

| seq | OpenVINS | VINS-Fusion | DynaVINS | ORB-SLAM3 |
|---|--:|--:|--:|--:|
| parking_lot_none | 0.086 | 0.135 | 0.114 [1] | 0.060 |
| parking_lot_low | 0.084 | 0.363 [4] | 2.92e+03 [7] | 0.079 |
| parking_lot_mid | 0.105 | 0.301 [4] | 1.84e+03 [7] | 0.495 |
| parking_lot_high | 0.133 [2] | 0.579 [4] | 2.3e+03 [8] | 0.365 |
| city_day_none | 0.198 | 0.431 [3] | 0.234 [1] | 0.049 |
| city_day_low | 0.226 | 0.322 | 0.222 [1] | 0.055 |
| city_day_mid | 0.316 [2] | 0.344 [1] | 0.211 | 0.072 |
| city_day_high | 0.291 | 0.486 | 0.265 | 0.061 |
| city_night_none | 0.401 | 0.324 | 0.280 | 13.9 [10] |
| city_night_low | 0.459 | 0.609 | 0.240 | 2.599 [8] |
| city_night_mid | 0.481 | 0.566 | 0.369 | 79.1 [7] |
| city_night_high | 0.686 | 0.930 | 0.217 | 7.654 [9] |

## Failures and success rate per group

| group | OpenVINS | VINS-Fusion | DynaVINS | ORB-SLAM3 |
|---|--:|--:|--:|--:|
| none | 0/30 fail (100 % ok) | 3/30 fail (90 % ok) | 2/30 fail (93 % ok) | 10/30 fail (67 % ok) |
| low | 0/30 fail (100 % ok) | 4/30 fail (87 % ok) | 8/30 fail (73 % ok) | 8/30 fail (73 % ok) |
| mid | 2/30 fail (93 % ok) | 5/30 fail (83 % ok) | 7/30 fail (77 % ok) | 7/30 fail (77 % ok) |
| high | 2/30 fail (93 % ok) | 4/30 fail (87 % ok) | 8/30 fail (73 % ok) | 9/30 fail (70 % ok) |
| none+low | 0/60 fail (100 % ok) | 7/60 fail (88 % ok) | 10/60 fail (83 % ok) | 18/60 fail (70 % ok) |
| mid+high | 4/60 fail (93 % ok) | 9/60 fail (85 % ok) | 15/60 fail (75 % ok) | 16/60 fail (73 % ok) |
| low+mid+high | 4/90 fail (96 % ok) | 13/90 fail (86 % ok) | 23/90 fail (74 % ok) | 24/90 fail (73 % ok) |
| all | 4/120 fail (97 % ok) | 16/120 fail (87 % ok) | 25/120 fail (79 % ok) | 34/120 fail (72 % ok) |

## Pooled paired comparison vs OpenVINS (geometric-mean ATE ratio - 1; negative = better than OpenVINS; failures capped at 10 m; bootstrap 95 % CI; Wilcoxon p; Holm over the 3 methods per group; wins/losses)

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| VINS-Fusion | +56 % [+3, +159] H=0.35 15/15 | +96 % [+10, +291] H=0.93 13/17 | +78 % [-3, +247] H=0.29 11/18 | +78 % [+25, +184] H=8.3e-05 4/24 | +75 % [+21, +164] H=0.37 28/32 | +78 % [+24, +163] H=0.00029 15/42 | +84 % [+34, +160] H=0.00049 28/59 | +77 % [+36, +136] H=0.00056 43/74 |
| DynaVINS | -6 % [-37, +57] H=0.23 19/11 | +118 % [-5, +434] H=1 18/12 | +42 % [-44, +272] H=1 20/10 | +51 % [-30, +251] H=0.85 20/8 | +43 % [-12, +142] H=0.54 37/23 | +46 % [-21, +174] H=0.78 40/18 | +67 % [+1, +179] H=1 58/30 | +45 % [-3, +117] H=0.26 77/41 |
| ORB-SLAM3 | +65 % [-20, +249] H=0.66 20/10 | +19 % [-38, +143] H=1 22/8 | +21 % [-46, +158] H=1 14/16 | +25 % [-44, +174] H=0.85 14/16 | +40 % [-15, +136] H=0.93 42/18 | +23 % [-30, +114] H=0.78 28/32 | +21 % [-21, +89] H=1 50/40 | +31 % [-10, +91] H=0.93 70/50 |

## Pooled paired comparison vs OpenVINS, RPE (shortest rpg sub-length = 10 % of the GT path; failed runs = inf, capped at 10 m)

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| VINS-Fusion | +56 % [+3, +159] H=0.35 15/15 | +96 % [+10, +291] H=0.93 13/17 | +78 % [-3, +247] H=0.29 11/18 | +78 % [+25, +184] H=8.3e-05 4/24 | +75 % [+21, +164] H=0.37 28/32 | +78 % [+24, +163] H=0.00029 15/42 | +84 % [+34, +160] H=0.00049 28/59 | +77 % [+36, +136] H=0.00056 43/74 |
| DynaVINS | -6 % [-37, +57] H=0.23 19/11 | +118 % [-5, +434] H=1 18/12 | +42 % [-44, +272] H=1 20/10 | +51 % [-30, +251] H=0.85 20/8 | +43 % [-12, +142] H=0.54 37/23 | +46 % [-21, +174] H=0.78 40/18 | +67 % [+1, +179] H=1 58/30 | +45 % [-3, +117] H=0.26 77/41 |
| ORB-SLAM3 | +65 % [-20, +249] H=0.66 20/10 | +19 % [-38, +143] H=1 22/8 | +21 % [-46, +158] H=1 14/16 | +25 % [-44, +174] H=0.85 14/16 | +40 % [-15, +136] H=0.93 42/18 | +23 % [-30, +114] H=0.78 28/32 | +21 % [-21, +89] H=1 50/40 | +31 % [-10, +91] H=0.93 70/50 |

## Secondary metrics (all 10 offsets per sequence pooled per method)

| method | median ATE posyaw | median ATE se3 | median ATE sim3 | median RPE (converged) [m] | converged-only median ATE |
|---|--:|--:|--:|--:|--:|
| VINS-Fusion | 0.470 | 0.380 | 0.313 | 0.234 | 0.405 |
| DynaVINS | 0.257 | 0.226 | 0.203 | 0.116 | 0.232 |
| ORB-SLAM3 | 0.175 | 0.174 | 0.123 | 0.050 | 0.069 |

## Run validity

| method | runs | status ok | complete (pose within 2 s of bag end) | no poses | median coverage | median init latency [s] | median end gap [s] | runs with resets | runs with lost frames (ORB) | runs with > 1 map (ORB) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| VINS-Fusion | 120 | 120 | 120 | 0 | 0.980 | 1.09 | 0.02 | 0 | - | - |
| DynaVINS | 120 | 120 | 120 | 0 | 0.980 | 1.09 | 0.02 | 0 | - | - |
| ORB-SLAM3 | 120 | 120 | 114 | 0 | 0.977 | 1.13 | 0.01 | 29 | 40 | 8 |
