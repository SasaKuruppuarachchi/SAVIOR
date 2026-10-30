# Real-world study (Monado MSD, Valve Index) - results

## Run validity (pre-registered rule + FREEZE_AMENDMENT 2 frame rule)

| sequence | method | runs | valid | fallbacks | late | n_in_core | pose rule fail | frame rule fail (frames lost) | md5 = openvins |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| MIO13 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 9 |
| MIO13 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO13 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO13 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO13 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO13 | OpenVINS (diag) | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO15 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO15 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO15 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO15 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO15 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO15 | OpenVINS (diag) | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO16 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 3 |
| MIO16 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO16 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO16 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO16 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO16 | OpenVINS (diag) | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO07 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 2 |
| MIO07 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO07 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO07 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO07 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO07 | OpenVINS (diag) | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |

Invalid runs still in the statistics: none


## ATE RMSE per sequence (posyaw, m): geometric mean over the 10 offsets (failures capped at 10 m), median, failures > 1 m

| sequence | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | VINS-Fusion | DynaVINS |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 moving person | 2.599 / 10.000 / 6 | 2.599 / 10.000 / 6 | 0.401 / 0.306 / 2 | 0.267 / 0.286 / 0 | 0.268 / 0.255 / 0 | 10.000 / 10.000 / 10 |
| MIO15 person + props | 0.806 / 0.381 / 4 | 0.806 / 0.381 / 4 | 0.676 / 0.254 / 3 | 0.207 / 0.172 / 1 | 0.207 / 0.200 / 0 | 7.786 / 10.000 / 9 |
| MIO16 person + props + screens | 0.155 / 0.147 / 0 | 0.155 / 0.147 / 0 | 0.158 / 0.155 / 0 | 0.196 / 0.193 / 0 | 0.302 / 0.292 / 0 | 3.381 / 6.085 / 8 |
| MIO07 static (control) | 0.039 / 0.039 / 0 | 0.039 / 0.039 / 0 | 0.038 / 0.040 / 0 | 0.038 / 0.040 / 0 | 0.056 / 0.055 / 0 | 0.132 / 0.079 / 1 |

## RPE (mean translational error, shortest savior-eval sub-length; geometric mean over non-failed runs)

| sequence | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | VINS-Fusion | DynaVINS |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 | 0.2436 (n=4) | 0.2436 (n=4) | 0.2058 (n=8) | 0.1942 (n=10) | 0.2226 (n=10) | - |
| MIO15 | 0.1143 (n=6) | 0.1143 (n=6) | 0.0958 (n=7) | 0.0886 (n=9) | 0.1457 (n=10) | 0.4198 (n=1) |
| MIO16 | 0.1027 (n=10) | 0.1027 (n=10) | 0.1007 (n=10) | 0.1154 (n=10) | 0.1531 (n=10) | 0.2766 (n=2) |
| MIO07 | 0.0330 (n=10) | 0.0330 (n=10) | 0.0345 (n=10) | 0.0345 (n=10) | 0.0373 (n=10) | 0.0516 (n=9) |

## Paired ATE comparisons (A vs B): geometric-mean ratio - 1 [%], run-level bootstrap 95 % CI, Wilcoxon p (Holm within group x reference); sequence-level estimate (mean of per-sequence mean log ratios) with two-stage cluster-bootstrap CI and exact sign-flip p (k = 3: min p = 0.25)

| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |
|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|
| person (MIO13+15+16) | SAVIOR vs OpenVINS | 30 | -67.8 | [-82.4, -43.5] | 20/10 | 0.00466 (0.014) | -67.8 | [-91, +24] | 0.5 | 2/3 | MIO13 -90, MIO15 -74, MIO16 +27 |
| person (MIO13+15+16) | Y-Cls vs OpenVINS | 30 | -49.1 | [-74.0, +0.4] | 17/13 | 0.129 (0.259) | -49.1 | [-85, +44] | 0.5 | 2/3 | MIO13 -85, MIO15 -16, MIO16 +2 |
| person (MIO13+15+16) | SAVIOR vs Y-Cls | 30 | -36.7 | [-62.0, -1.3] | 16/14 | 0.289 (0.289) | -36.7 | [-73, +23] | 0.5 | 2/3 | MIO13 -33, MIO15 -69, MIO16 +24 |
| person (MIO13+15+16) | SAVIOR-none vs OpenVINS | 30 | -0.0 | [-0.0, +0.0] | 7/8 | 0.679 (0.679) | -0.0 | [-0, +0] | 1.0 | 1/3 | MIO13 +0, MIO15 -0, MIO16 +0 |
| person (MIO13+15+16) | SAVIOR vs VINS-Fusion | 30 | -13.5 | [-29.6, +10.3] | 21/9 | 0.0364 (0.0729) | -13.5 | [-35, +20] | 0.5 | 2/3 | MIO13 -0, MIO15 +0, MIO16 -35 |
| person (MIO13+15+16) | SAVIOR vs DynaVINS | 30 | -96.5 | [-97.6, -94.8] | 30/0 | 1.86e-09 (1.86e-09) | -96.5 | [-98, -94] | 0.25 | 3/3 | MIO13 -97, MIO15 -97, MIO16 -94 |
| person (MIO13+15+16) | OpenVINS vs VINS-Fusion | 30 | +168.7 | [+41.3, +426.8] | 12/18 | 0.119 (0.119) | +168.7 | [-48, +982] | 0.5 | 1/3 | MIO13 +870, MIO15 +290, MIO16 -49 |
| person (MIO13+15+16) | DynaVINS vs VINS-Fusion | 30 | +2405.3 | [+1656.1, +3326.1] | 0/30 | 1.86e-09 (5.59e-09) | +2405.3 | [+1068, +4152] | 0.25 | 0/3 | MIO13 +3632, MIO15 +3661, MIO16 +1020 |
| MIO13 | SAVIOR vs OpenVINS | 10 | -89.7 | [-95.9, -72.4] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO13 -90 |
| MIO13 | Y-Cls vs OpenVINS | 10 | -84.6 | [-93.7, -61.2] | 8/2 | 0.00977 (0.0195) | - | - | - | - | MIO13 -85 |
| MIO13 | SAVIOR vs Y-Cls | 10 | -33.4 | [-65.8, +20.2] | 6/4 | 0.492 (0.492) | - | - | - | - | MIO13 -33 |
| MIO13 | SAVIOR-none vs OpenVINS | 10 | +0.0 | [+0.0, +0.0] | 0/0 | 1 (1) | - | - | - | - | MIO13 +0 |
| MIO13 | SAVIOR vs VINS-Fusion | 10 | -0.4 | [-24.3, +29.7] | 5/5 | 0.922 (0.922) | - | - | - | - | MIO13 -0 |
| MIO13 | SAVIOR vs DynaVINS | 10 | -97.3 | [-97.9, -96.6] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO13 -97 |
| MIO13 | OpenVINS vs VINS-Fusion | 10 | +869.8 | [+208.0, +2726.9] | 1/9 | 0.00977 (0.0195) | - | - | - | - | MIO13 +870 |
| MIO13 | DynaVINS vs VINS-Fusion | 10 | +3632.2 | [+3210.7, +4049.7] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO13 +3632 |
| MIO15 | SAVIOR vs OpenVINS | 10 | -74.3 | [-90.5, -37.1] | 8/2 | 0.0195 (0.0586) | - | - | - | - | MIO15 -74 |
| MIO15 | Y-Cls vs OpenVINS | 10 | -16.1 | [-83.1, +295.9] | 5/5 | 1 (1) | - | - | - | - | MIO15 -16 |
| MIO15 | SAVIOR vs Y-Cls | 10 | -69.4 | [-90.0, -6.2] | 8/2 | 0.084 (0.084) | - | - | - | - | MIO15 -69 |
| MIO15 | SAVIOR-none vs OpenVINS | 10 | -0.0 | [-0.0, -0.0] | 4/4 | 0.383 (0.766) | - | - | - | - | MIO15 -0 |
| MIO15 | SAVIOR vs VINS-Fusion | 10 | +0.1 | [-39.5, +86.1] | 6/4 | 0.695 (0.695) | - | - | - | - | MIO15 +0 |
| MIO15 | SAVIOR vs DynaVINS | 10 | -97.3 | [-98.7, -94.0] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO15 -97 |
| MIO15 | OpenVINS vs VINS-Fusion | 10 | +289.6 | [+52.5, +968.2] | 1/9 | 0.0273 (0.0547) | - | - | - | - | MIO15 +290 |
| MIO15 | DynaVINS vs VINS-Fusion | 10 | +3661.5 | [+2115.7, +5086.3] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO15 +3661 |
| MIO16 | SAVIOR vs OpenVINS | 10 | +26.6 | [+5.7, +50.2] | 2/8 | 0.0645 (0.193) | - | - | - | - | MIO16 +27 |
| MIO16 | Y-Cls vs OpenVINS | 10 | +2.0 | [-14.1, +20.9] | 4/6 | 0.846 (0.938) | - | - | - | - | MIO16 +2 |
| MIO16 | SAVIOR vs Y-Cls | 10 | +24.1 | [+9.1, +41.8] | 2/8 | 0.0195 (0.0195) | - | - | - | - | MIO16 +24 |
| MIO16 | SAVIOR-none vs OpenVINS | 10 | +0.0 | [-0.0, +0.0] | 3/4 | 0.469 (0.938) | - | - | - | - | MIO16 +0 |
| MIO16 | SAVIOR vs VINS-Fusion | 10 | -35.0 | [-43.0, -26.3] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO16 -35 |
| MIO16 | SAVIOR vs DynaVINS | 10 | -94.2 | [-97.2, -87.7] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO16 -94 |
| MIO16 | OpenVINS vs VINS-Fusion | 10 | -48.7 | [-55.2, -40.7] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO16 -49 |
| MIO16 | DynaVINS vs VINS-Fusion | 10 | +1020.1 | [+488.7, +1958.6] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO16 +1020 |
| static MIO07 | SAVIOR vs OpenVINS | 10 | -3.3 | [-18.0, +14.8] | 6/4 | 0.922 (1) | - | - | - | - | MIO07 -3 |
| static MIO07 | Y-Cls vs OpenVINS | 10 | -3.3 | [-18.0, +14.8] | 6/4 | 0.922 (1) | - | - | - | - | MIO07 -3 |
| static MIO07 | SAVIOR vs Y-Cls | 10 | -0.0 | [-0.0, +0.0] | 5/3 | 0.25 (0.25) | - | - | - | - | MIO07 -0 |
| static MIO07 | SAVIOR-none vs OpenVINS | 10 | +0.0 | [-0.0, +0.0] | 3/5 | 0.383 (1) | - | - | - | - | MIO07 +0 |
| static MIO07 | SAVIOR vs VINS-Fusion | 10 | -31.7 | [-40.1, -22.4] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO07 -32 |
| static MIO07 | SAVIOR vs DynaVINS | 10 | -71.2 | [-89.0, -50.5] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO07 -71 |
| static MIO07 | OpenVINS vs VINS-Fusion | 10 | -29.4 | [-36.9, -21.2] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO07 -29 |
| static MIO07 | DynaVINS vs VINS-Fusion | 10 | +137.0 | [+29.1, +575.4] | 1/9 | 0.00391 (0.00586) | - | - | - | - | MIO07 +137 |

## Sensitivity: failure handling (person group, run-level GM [%])

| A vs B | cap 2 m | cap 10 m | cap 50 m | failures excluded (> 1 m) |
|---|--:|--:|--:|--:|
| SAVIOR vs OpenVINS | -49.3 (n=30) | -67.8 (n=30) | -79.0 (n=30) | -6.0 (n=20) |
| Y-Cls vs OpenVINS | -31.3 (n=30) | -49.1 (n=30) | -61.1 (n=30) | -5.4 (n=18) |
| SAVIOR vs Y-Cls | -26.1 (n=30) | -36.7 (n=30) | -46.1 (n=30) | -2.4 (n=24) |
| SAVIOR-none vs OpenVINS | -0.0 (n=30) | -0.0 (n=30) | -0.0 (n=30) | -0.0 (n=20) |

## Failures (ATE > threshold) per method, person group / static

| method | > 0.5 m | > 1 m (protocol) | > 2 m | static > 1 m |
|---|--:|--:|--:|--:|
| OpenVINS | 11/30 | 10/30 | 9/30 | 0/10 |
| SAVIOR-none | 11/30 | 10/30 | 9/30 | 0/10 |
| Y-Cls | 6/30 | 5/30 | 3/30 | 0/10 |
| SAVIOR | 2/30 | 1/30 | 1/30 | 0/10 |
| VINS-Fusion | 0/30 | 0/30 | 0/30 | 0/10 |
| DynaVINS | 30/30 | 27/30 | 25/30 | 1/10 |

## Share of the information on people (reference masks = offline YOLO26x-seg @960, person; diag_openvins post-init)

| sequence | person pixel share (mean) | frames with a person | frames > 25 % person | kept cam0 obs on person | MSCKF-used meas. on person | SLAM-update meas. on person | chi2 reject person / other |
|---|--:|--:|--:|--:|--:|--:|---|
| MIO13 | 11.05 % | 77.45 % | 11.44 % | 21.16 % | 26.73 % | 16.76 % | 0.85 / 0.78 |
| MIO15 | 5.29 % | 44.92 % | 5.96 % | 8.30 % | 7.23 % | 0.57 % | 0.87 / 0.60 |
| MIO16 | 4.81 % | 34.58 % | 4.99 % | 5.13 % | 2.54 % | 0.17 % | 0.81 / 0.46 |
| MIO07 | 0.04 % | 1.76 % | 0.00 % | 0.05 % | 0.00 % | 0.00 % | 0.94 / 0.62 |
