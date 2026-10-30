# M3b SOTA benchmark: SAVIOR-Warehouse t2 held-out (12 sequences)

VINS-Fusion, DynaVINS, ORB-SLAM3 (stereo-inertial, loop closure off), image savior-sota:noetic; 10 late-start offsets per sequence = the P6 / M2b offsets of our methods (protocol (a), no bag-start column); rate 0.5. ATE RMSE [m], posyaw alignment, full sequence (savior-eval multi). Failure = ATE > 2 m or no estimate; [n] = failures. OpenVINS = M2b held-out runs (results/m2b_heldout/runs/<seq>/openvins) at the same offsets.

## Median ATE [m] over 10 offsets ([n] = failures)

| seq | OpenVINS | VINS-Fusion | DynaVINS | ORB-SLAM3 |
|---|--:|--:|--:|--:|
| aisles_t2_L0 | 0.102 | 0.095 | 0.106 | fail [10] |
| aisles_t2_L1 | 0.136 | 0.081 | 0.079 | fail [10] |
| aisles_t2_L2 | 0.227 [2] | 0.094 | 0.082 | fail [10] |
| aisles_t2_L3 | 0.154 [1] | 0.094 | 0.056 | fail [10] |
| hall_t2_L0 | 0.268 | 0.085 | 0.106 | fail [10] |
| hall_t2_L1 | 0.224 | 0.127 | 0.075 | fail [10] |
| hall_t2_L2 | 0.172 | 0.103 | 0.143 | fail [10] |
| hall_t2_L3 | 1.37e+03 [8] | 0.230 | 0.108 | fail [10] |
| dock_t2_L0 | 0.153 | 0.146 | 0.062 | fail [10] |
| dock_t2_L1 | 0.254 | 0.109 | 0.043 | fail [10] |
| dock_t2_L2 | 0.363 [1] | 0.134 | 0.075 | fail [10] |
| dock_t2_L3 | 2.19e+03 [7] | 0.149 | 0.095 | fail [10] |

## Failures and success rate per group

| group | OpenVINS | VINS-Fusion | DynaVINS | ORB-SLAM3 |
|---|--:|--:|--:|--:|
| L0 | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 30/30 fail (0 % ok) |
| L1 | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 30/30 fail (0 % ok) |
| L2 | 3/30 fail (90 % ok) | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 30/30 fail (0 % ok) |
| L3 | 16/30 fail (47 % ok) | 0/30 fail (100 % ok) | 0/30 fail (100 % ok) | 30/30 fail (0 % ok) |
| L0+L1 | 0/60 fail (100 % ok) | 0/60 fail (100 % ok) | 0/60 fail (100 % ok) | 60/60 fail (0 % ok) |
| L2+L3 | 19/60 fail (68 % ok) | 0/60 fail (100 % ok) | 0/60 fail (100 % ok) | 60/60 fail (0 % ok) |
| hall_L3 | 8/10 fail (20 % ok) | 0/10 fail (100 % ok) | 0/10 fail (100 % ok) | 10/10 fail (0 % ok) |
| dock_L3 | 7/10 fail (30 % ok) | 0/10 fail (100 % ok) | 0/10 fail (100 % ok) | 10/10 fail (0 % ok) |
| hall+dock_L3 | 15/20 fail (25 % ok) | 0/20 fail (100 % ok) | 0/20 fail (100 % ok) | 20/20 fail (0 % ok) |
| all | 19/120 fail (84 % ok) | 0/120 fail (100 % ok) | 0/120 fail (100 % ok) | 120/120 fail (0 % ok) |

## Pooled paired comparison vs OpenVINS (geometric-mean ATE ratio - 1; negative = better than OpenVINS; failures capped at 10 m; bootstrap 95 % CI; Wilcoxon p; Holm over the 3 methods per group; wins/losses)

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | dock_L3 | hall+dock_L3 | all |
|---|---|---|---|---|---|---|---|---|---|---|
| VINS-Fusion | -46 % [-51, -41] H=5.6e-09 30/0 | -53 % [-57, -49] H=5.6e-09 30/0 | -69 % [-82, -53] H=5.6e-09 30/0 | -93 % [-97, -87] H=5.6e-09 30/0 | -50 % [-53, -46] H=4.9e-11 60/0 | -86 % [-91, -78] H=3.3e-11 60/0 | -97 % [-98, -93] H=0.0059 10/0 | -97 % [-99, -90] H=0.0059 10/0 | -97 % [-98, -94] H=5.7e-06 20/0 | -73 % [-79, -66] H=5.9e-21 120/0 |
| DynaVINS | -67 % [-71, -64] H=5.6e-09 30/0 | -72 % [-75, -69] H=5.6e-09 30/0 | -84 % [-91, -74] H=5.6e-09 30/0 | -97 % [-99, -95] H=5.6e-09 30/0 | -70 % [-72, -67] H=4.9e-11 60/0 | -93 % [-96, -89] H=3.3e-11 60/0 | -99 % [-100, -98] H=0.0059 10/0 | -99 % [-99, -95] H=0.0059 10/0 | -99 % [-99, -98] H=5.7e-06 20/0 | -86 % [-89, -81] H=5.9e-21 120/0 |
| ORB-SLAM3 | +9316 % [+8612, +10046] H=5.6e-09 0/30 | +8341 % [+7670, +9100] H=5.6e-09 0/30 | +3871 % [+2317, +5943] H=1.5e-08 0/27 | +567 % [+221, +1298] H=0.00012 0/14 | +8815 % [+8300, +9357] H=4.9e-11 0/60 | +1527 % [+893, +2530] H=2.7e-12 0/41 | +81 % [+0, +336] H=0.5 0/2 | +219 % [+0, +925] H=0.25 0/3 | +140 % [+22, +394] H=0.062 0/5 | +3709 % [+2734, +4945] H=2.7e-18 0/101 |

## Pooled paired comparison vs OpenVINS, RPE (shortest rpg sub-length = 10 % of the GT path; failed runs = inf, capped at 10 m)

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | dock_L3 | hall+dock_L3 | all |
|---|---|---|---|---|---|---|---|---|---|---|
| VINS-Fusion | -46 % [-51, -41] H=5.6e-09 30/0 | -53 % [-57, -49] H=5.6e-09 30/0 | -69 % [-82, -53] H=5.6e-09 30/0 | -93 % [-97, -87] H=5.6e-09 30/0 | -50 % [-53, -46] H=4.9e-11 60/0 | -86 % [-91, -78] H=3.3e-11 60/0 | -97 % [-98, -93] H=0.0059 10/0 | -97 % [-99, -90] H=0.0059 10/0 | -97 % [-98, -94] H=5.7e-06 20/0 | -73 % [-79, -66] H=5.9e-21 120/0 |
| DynaVINS | -67 % [-71, -64] H=5.6e-09 30/0 | -72 % [-75, -69] H=5.6e-09 30/0 | -84 % [-91, -74] H=5.6e-09 30/0 | -97 % [-99, -95] H=5.6e-09 30/0 | -70 % [-72, -67] H=4.9e-11 60/0 | -93 % [-96, -89] H=3.3e-11 60/0 | -99 % [-100, -98] H=0.0059 10/0 | -99 % [-99, -95] H=0.0059 10/0 | -99 % [-99, -98] H=5.7e-06 20/0 | -86 % [-89, -81] H=5.9e-21 120/0 |
| ORB-SLAM3 | +9316 % [+8612, +10046] H=5.6e-09 0/30 | +8341 % [+7670, +9100] H=5.6e-09 0/30 | +3871 % [+2317, +5943] H=1.5e-08 0/27 | +567 % [+221, +1298] H=0.00012 0/14 | +8815 % [+8300, +9357] H=4.9e-11 0/60 | +1527 % [+893, +2530] H=2.7e-12 0/41 | +81 % [+0, +336] H=0.5 0/2 | +219 % [+0, +925] H=0.25 0/3 | +140 % [+22, +394] H=0.062 0/5 | +3709 % [+2734, +4945] H=2.7e-18 0/101 |

## Secondary metrics (all 10 offsets per sequence pooled per method)

| method | median ATE posyaw | median ATE se3 | median ATE sim3 | median RPE (converged) [m] | converged-only median ATE |
|---|--:|--:|--:|--:|--:|
| VINS-Fusion | 0.108 | 0.101 | 0.089 | 0.065 | 0.108 |
| DynaVINS | 0.084 | 0.083 | 0.079 | 0.037 | 0.084 |
| ORB-SLAM3 | fail | fail | fail | - | - |

## Run validity

| method | runs | status ok | complete (pose within 2 s of bag end) | no poses | median coverage | median init latency [s] | median end gap [s] | runs with resets | runs with lost frames (ORB) | runs with > 1 map (ORB) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| VINS-Fusion | 120 | 120 | 120 | 0 | 0.989 | 1.10 | 0.07 | 0 | - | - |
| DynaVINS | 120 | 120 | 120 | 0 | 0.989 | 1.10 | 0.07 | 0 | - | - |
| ORB-SLAM3 | 120 | 0 | 0 | 120 | 0.000 | nan | nan | 0 | 0 | 0 |
