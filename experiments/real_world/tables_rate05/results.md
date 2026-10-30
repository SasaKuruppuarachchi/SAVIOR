# Real-world study (Monado MSD, Valve Index) - results

## Run validity (pre-registered rule + FREEZE_AMENDMENT 2 frame rule)

| sequence | method | runs | valid | fallbacks | late | n_in_core | pose rule fail | frame rule fail (frames lost) | md5 = openvins |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| MIO13 | OpenVINS | 10 | 9 | 0 | 0 | 0 | 0 | 1 (1) | 10 |
| MIO13 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 6 |
| MIO13 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO13 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO13 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO13 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO13 | OpenVINS (diag) | 3 | 0 | 0 | 0 | 0 | 0 | 3 (184) | - |
| MIO15 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | SAVIOR-none | 10 | 2 | 0 | 0 | 0 | 6 | 8 (88) | 0 |
| MIO15 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO15 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO15 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO15 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO15 | OpenVINS (diag) | 3 | 0 | 0 | 0 | 0 | 0 | 3 (117) | - |
| MIO16 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | SAVIOR-none | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 2 |
| MIO16 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO16 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO16 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO16 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO16 | OpenVINS (diag) | 3 | 0 | 0 | 0 | 0 | 0 | 3 (78) | - |
| MIO07 | OpenVINS | 10 | 0 | 0 | 0 | 0 | 0 | 10 (125) | 10 |
| MIO07 | SAVIOR-none | 10 | 3 | 0 | 0 | 0 | 1 | 7 (33) | 0 |
| MIO07 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO07 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 0 |
| MIO07 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO07 | DynaVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | - |
| MIO07 | OpenVINS (diag) | 3 | 0 | 0 | 0 | 0 | 0 | 3 (30) | - |

Invalid runs still in the statistics: MIO13 OpenVINS run_01 (ok/0, 10036 poses vs openvins 10036, frames 10121/10122); MIO13 OpenVINS (diag) run_01 (ok/0, 9998 poses vs openvins 10036, frames 10083/10122); MIO13 OpenVINS (diag) run_05 (ok/0, 9970 poses vs openvins 10037, frames 10032/10100); MIO13 OpenVINS (diag) run_10 (ok/0, 9937 poses vs openvins 10014, frames 9996/10073); MIO15 SAVIOR-none run_03 (ok/0, 6660 poses vs openvins 6662, frames 6766/6768); MIO15 SAVIOR-none run_04 (ok/0, 6644 poses vs openvins 6660, frames 6746/6762); MIO15 SAVIOR-none run_05 (ok/0, 6662 poses vs openvins 6663, frames 6756/6757); MIO15 SAVIOR-none run_06 (ok/0, 6626 poses vs openvins 6652, frames 6725/6751); MIO15 SAVIOR-none run_07 (ok/0, 6651 poses vs openvins 6661, frames 6736/6746); MIO15 SAVIOR-none run_08 (ok/0, 6646 poses vs openvins 6662, frames 6725/6741); MIO15 SAVIOR-none run_09 (ok/0, 6660 poses vs openvins 6661, frames 6734/6735); MIO15 SAVIOR-none run_10 (ok/0, 6645 poses vs openvins 6661, frames 6714/6730); MIO15 OpenVINS (diag) run_01 (ok/0, 6577 poses vs openvins 6655, frames 6733/6779); MIO15 OpenVINS (diag) run_05 (ok/0, 6628 poses vs openvins 6663, frames 6722/6757); MIO15 OpenVINS (diag) run_10 (ok/0, 6625 poses vs openvins 6661, frames 6694/6730); MIO16 OpenVINS (diag) run_01 (ok/0, 7067 poses vs openvins 7081, frames 7135/7155); MIO16 OpenVINS (diag) run_05 (ok/0, 7034 poses vs openvins 7074, frames 7093/7133); MIO16 OpenVINS (diag) run_10 (ok/0, 7029 poses vs openvins 7047, frames 7088/7106); MIO07 OpenVINS run_01 (ok/0, 1985 poses vs openvins 1985, frames 2045/2050); MIO07 OpenVINS run_02 (ok/0, 1980 poses vs openvins 1980, frames 2039/2044); MIO07 OpenVINS run_03 (ok/0, 1953 poses vs openvins 1953, frames 2017/2039); MIO07 OpenVINS run_04 (ok/0, 1967 poses vs openvins 1967, frames 2012/2033); MIO07 OpenVINS run_05 (ok/0, 1965 poses vs openvins 1965, frames 2025/2028); MIO07 OpenVINS run_06 (ok/0, 1963 poses vs openvins 1963, frames 2020/2022); MIO07 OpenVINS run_07 (ok/0, 1935 poses vs openvins 1935, frames 1998/2017); MIO07 OpenVINS run_08 (ok/0, 1924 poses vs openvins 1924, frames 1983/2012); MIO07 OpenVINS run_09 (ok/0, 1936 poses vs openvins 1936, frames 1995/2006); MIO07 OpenVINS run_10 (ok/0, 1934 poses vs openvins 1934, frames 1993/2001); MIO07 SAVIOR-none run_01 (ok/0, 1987 poses vs openvins 1985, frames 2047/2050); MIO07 SAVIOR-none run_02 (ok/0, 1980 poses vs openvins 1980, frames 2039/2044); MIO07 SAVIOR-none run_03 (ok/0, 1970 poses vs openvins 1953, frames 2034/2039); MIO07 SAVIOR-none run_06 (ok/0, 1957 poses vs openvins 1963, frames 2016/2022); MIO07 SAVIOR-none run_07 (ok/0, 1946 poses vs openvins 1935, frames 2009/2017); MIO07 SAVIOR-none run_08 (ok/0, 1948 poses vs openvins 1924, frames 2007/2012); MIO07 SAVIOR-none run_09 (ok/0, 1946 poses vs openvins 1936, frames 2005/2006); MIO07 OpenVINS (diag) run_01 (ok/0, 1984 poses vs openvins 1985, frames 2044/2050); MIO07 OpenVINS (diag) run_05 (ok/0, 1967 poses vs openvins 1965, frames 2026/2028); MIO07 OpenVINS (diag) run_10 (ok/0, 1923 poses vs openvins 1934, frames 1979/2001)


## ATE RMSE per sequence (posyaw, m): geometric mean over the 10 offsets (failures capped at 10 m), median, failures > 1 m

| sequence | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | VINS-Fusion | DynaVINS |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 moving person | 2.599 / 10.000 / 6 | 2.599 / 10.000 / 6 | 0.401 / 0.306 / 2 | 0.267 / 0.286 / 0 | 0.293 / 0.294 / 0 | 10.000 / 10.000 / 10 |
| MIO15 person + props | 0.807 / 0.381 / 4 | 0.706 / 0.381 / 4 | 0.676 / 0.254 / 3 | 0.207 / 0.172 / 1 | 0.210 / 0.199 / 0 | 10.000 / 10.000 / 10 |
| MIO16 person + props + screens | 0.155 / 0.147 / 0 | 0.155 / 0.147 / 0 | 0.158 / 0.155 / 0 | 0.196 / 0.193 / 0 | 0.311 / 0.292 / 0 | 3.677 / 6.085 / 8 |
| MIO07 static (control) | 0.038 / 0.038 / 0 | 0.037 / 0.036 / 0 | 0.038 / 0.040 / 0 | 0.038 / 0.040 / 0 | 0.055 / 0.056 / 0 | 0.132 / 0.079 / 1 |

## RPE (mean translational error, shortest savior-eval sub-length; geometric mean over non-failed runs)

| sequence | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | VINS-Fusion | DynaVINS |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 | 0.2436 (n=4) | 0.2436 (n=4) | 0.2058 (n=8) | 0.1942 (n=10) | 0.2309 (n=10) | - |
| MIO15 | 0.1145 (n=6) | 0.1005 (n=6) | 0.0958 (n=7) | 0.0886 (n=9) | 0.1473 (n=10) | - |
| MIO16 | 0.1027 (n=10) | 0.1027 (n=10) | 0.1007 (n=10) | 0.1154 (n=10) | 0.1602 (n=10) | 0.3274 (n=2) |
| MIO07 | 0.0343 (n=10) | 0.0341 (n=10) | 0.0345 (n=10) | 0.0345 (n=10) | 0.0368 (n=10) | 0.0517 (n=9) |

## Paired ATE comparisons (A vs B): geometric-mean ratio - 1 [%], run-level bootstrap 95 % CI, Wilcoxon p (Holm within group x reference); sequence-level estimate (mean of per-sequence mean log ratios) with two-stage cluster-bootstrap CI and exact sign-flip p (k = 3: min p = 0.25)

| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |
|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|
| person (MIO13+15+16) | SAVIOR vs OpenVINS | 30 | -67.8 | [-82.4, -43.5] | 20/10 | 0.00466 (0.014) | -67.8 | [-91, +24] | 0.5 | 2/3 | MIO13 -90, MIO15 -74, MIO16 +27 |
| person (MIO13+15+16) | Y-Cls vs OpenVINS | 30 | -49.1 | [-74.0, +0.3] | 17/13 | 0.129 (0.259) | -49.1 | [-85, +44] | 0.5 | 2/3 | MIO13 -85, MIO15 -16, MIO16 +2 |
| person (MIO13+15+16) | SAVIOR vs Y-Cls | 30 | -36.7 | [-62.0, -1.3] | 16/14 | 0.289 (0.289) | -36.7 | [-73, +23] | 0.5 | 2/3 | MIO13 -33, MIO15 -69, MIO16 +24 |
| person (MIO13+15+16) | SAVIOR-none vs OpenVINS | 30 | -4.4 | [-9.9, +0.3] | 9/9 | 0.734 (0.734) | -4.4 | [-14, +0] | 0.75 | 2/3 | MIO13 +0, MIO15 -13, MIO16 -0 |
| person (MIO13+15+16) | SAVIOR vs VINS-Fusion | 30 | -17.2 | [-32.9, +5.4] | 21/9 | 0.0234 (0.0468) | -17.2 | [-37, +15] | 0.25 | 3/3 | MIO13 -9, MIO15 -1, MIO16 -37 |
| person (MIO13+15+16) | SAVIOR vs DynaVINS | 30 | -96.9 | [-97.8, -95.6] | 30/0 | 1.86e-09 (1.86e-09) | -96.9 | [-98, -94] | 0.25 | 3/3 | MIO13 -97, MIO15 -98, MIO16 -95 |
| person (MIO13+15+16) | OpenVINS vs VINS-Fusion | 30 | +157.2 | [+36.4, +398.8] | 13/17 | 0.124 (0.124) | +157.2 | [-49, +902] | 0.5 | 1/3 | MIO13 +788, MIO15 +284, MIO16 -50 |
| person (MIO13+15+16) | DynaVINS vs VINS-Fusion | 30 | +2579.8 | [+1861.5, +3405.1] | 0/30 | 1.86e-09 (5.59e-09) | +2579.8 | [+1151, +4605] | 0.25 | 0/3 | MIO13 +3317, MIO15 +4661, MIO16 +1083 |
| MIO13 | SAVIOR vs OpenVINS | 10 | -89.7 | [-95.9, -72.4] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO13 -90 |
| MIO13 | Y-Cls vs OpenVINS | 10 | -84.6 | [-93.7, -61.2] | 8/2 | 0.00977 (0.0195) | - | - | - | - | MIO13 -85 |
| MIO13 | SAVIOR vs Y-Cls | 10 | -33.4 | [-65.8, +20.2] | 6/4 | 0.492 (0.492) | - | - | - | - | MIO13 -33 |
| MIO13 | SAVIOR-none vs OpenVINS | 10 | +0.0 | [-0.0, +0.0] | 1/1 | 1 (1) | - | - | - | - | MIO13 +0 |
| MIO13 | SAVIOR vs VINS-Fusion | 10 | -8.8 | [-31.9, +21.4] | 5/5 | 0.625 (0.625) | - | - | - | - | MIO13 -9 |
| MIO13 | SAVIOR vs DynaVINS | 10 | -97.3 | [-97.9, -96.6] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO13 -97 |
| MIO13 | OpenVINS vs VINS-Fusion | 10 | +787.9 | [+185.8, +2334.0] | 2/8 | 0.0195 (0.0391) | - | - | - | - | MIO13 +788 |
| MIO13 | DynaVINS vs VINS-Fusion | 10 | +3316.8 | [+2938.4, +3741.6] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO13 +3317 |
| MIO15 | SAVIOR vs OpenVINS | 10 | -74.3 | [-90.5, -37.3] | 8/2 | 0.0195 (0.0586) | - | - | - | - | MIO15 -74 |
| MIO15 | Y-Cls vs OpenVINS | 10 | -16.2 | [-83.1, +295.1] | 5/5 | 1 (1) | - | - | - | - | MIO15 -16 |
| MIO15 | SAVIOR vs Y-Cls | 10 | -69.4 | [-90.0, -6.2] | 8/2 | 0.084 (0.084) | - | - | - | - | MIO15 -69 |
| MIO15 | SAVIOR-none vs OpenVINS | 10 | -12.6 | [-25.3, +0.1] | 3/5 | 0.742 (1) | - | - | - | - | MIO15 -13 |
| MIO15 | SAVIOR vs VINS-Fusion | 10 | -1.3 | [-40.6, +80.7] | 6/4 | 0.695 (0.695) | - | - | - | - | MIO15 -1 |
| MIO15 | SAVIOR vs DynaVINS | 10 | -97.9 | [-98.8, -95.9] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO15 -98 |
| MIO15 | OpenVINS vs VINS-Fusion | 10 | +284.4 | [+52.3, +943.5] | 1/9 | 0.0273 (0.0547) | - | - | - | - | MIO15 +284 |
| MIO15 | DynaVINS vs VINS-Fusion | 10 | +4661.1 | [+4224.4, +5089.2] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO15 +4661 |
| MIO16 | SAVIOR vs OpenVINS | 10 | +26.6 | [+5.7, +50.2] | 2/8 | 0.0645 (0.193) | - | - | - | - | MIO16 +27 |
| MIO16 | Y-Cls vs OpenVINS | 10 | +2.0 | [-14.1, +20.9] | 4/6 | 0.846 (0.846) | - | - | - | - | MIO16 +2 |
| MIO16 | SAVIOR vs Y-Cls | 10 | +24.1 | [+9.1, +41.8] | 2/8 | 0.0195 (0.0195) | - | - | - | - | MIO16 +24 |
| MIO16 | SAVIOR-none vs OpenVINS | 10 | -0.0 | [-0.0, +0.0] | 5/3 | 0.195 (0.391) | - | - | - | - | MIO16 -0 |
| MIO16 | SAVIOR vs VINS-Fusion | 10 | -36.9 | [-46.4, -27.1] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO16 -37 |
| MIO16 | SAVIOR vs DynaVINS | 10 | -94.7 | [-97.3, -89.1] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO16 -95 |
| MIO16 | OpenVINS vs VINS-Fusion | 10 | -50.2 | [-57.8, -41.6] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO16 -50 |
| MIO16 | DynaVINS vs VINS-Fusion | 10 | +1083.0 | [+555.0, +1958.1] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO16 +1083 |
| static MIO07 | SAVIOR vs OpenVINS | 10 | -0.1 | [-12.7, +14.4] | 6/4 | 1 (1) | - | - | - | - | MIO07 -0 |
| static MIO07 | Y-Cls vs OpenVINS | 10 | -0.1 | [-12.7, +14.4] | 6/4 | 1 (1) | - | - | - | - | MIO07 -0 |
| static MIO07 | SAVIOR vs Y-Cls | 10 | -0.0 | [-0.0, +0.0] | 5/3 | 0.25 (0.25) | - | - | - | - | MIO07 -0 |
| static MIO07 | SAVIOR-none vs OpenVINS | 10 | -3.7 | [-18.2, +9.5] | 6/4 | 0.922 (1) | - | - | - | - | MIO07 -4 |
| static MIO07 | SAVIOR vs VINS-Fusion | 10 | -31.2 | [-42.3, -19.6] | 10/0 | 0.00195 (0.00586) | - | - | - | - | MIO07 -31 |
| static MIO07 | SAVIOR vs DynaVINS | 10 | -71.3 | [-89.0, -50.6] | 10/0 | 0.00195 (0.00195) | - | - | - | - | MIO07 -71 |
| static MIO07 | OpenVINS vs VINS-Fusion | 10 | -31.2 | [-42.1, -18.5] | 9/1 | 0.00586 (0.00586) | - | - | - | - | MIO07 -31 |
| static MIO07 | DynaVINS vs VINS-Fusion | 10 | +139.3 | [+27.5, +585.2] | 0/10 | 0.00195 (0.00586) | - | - | - | - | MIO07 +139 |

## Sensitivity: failure handling (person group, run-level GM [%])

| A vs B | cap 2 m | cap 10 m | cap 50 m | failures excluded (> 1 m) |
|---|--:|--:|--:|--:|
| SAVIOR vs OpenVINS | -49.3 (n=30) | -67.8 (n=30) | -79.0 (n=30) | -6.1 (n=20) |
| Y-Cls vs OpenVINS | -31.4 (n=30) | -49.1 (n=30) | -61.1 (n=30) | -5.5 (n=18) |
| SAVIOR vs Y-Cls | -26.1 (n=30) | -36.7 (n=30) | -46.1 (n=30) | -2.4 (n=24) |
| SAVIOR-none vs OpenVINS | -3.2 (n=30) | -4.4 (n=30) | -4.4 (n=30) | -4.8 (n=20) |

## Failures (ATE > threshold) per method, person group / static

| method | > 0.5 m | > 1 m (protocol) | > 2 m | static > 1 m |
|---|--:|--:|--:|--:|
| OpenVINS | 11/30 | 10/30 | 9/30 | 0/10 |
| SAVIOR-none | 11/30 | 10/30 | 9/30 | 0/10 |
| Y-Cls | 6/30 | 5/30 | 3/30 | 0/10 |
| SAVIOR | 2/30 | 1/30 | 1/30 | 0/10 |
| VINS-Fusion | 0/30 | 0/30 | 0/30 | 0/10 |
| DynaVINS | 30/30 | 28/30 | 26/30 | 1/10 |

## Share of the information on people (reference masks = offline YOLO26x-seg @960, person; diag_openvins post-init)

| sequence | person pixel share (mean) | frames with a person | frames > 25 % person | kept cam0 obs on person | MSCKF-used meas. on person | SLAM-update meas. on person | chi2 reject person / other |
|---|--:|--:|--:|--:|--:|--:|---|
| MIO13 | 11.05 % | 77.45 % | 11.44 % | 21.20 % | 28.99 % | 20.17 % | 0.86 / 0.81 |
| MIO15 | 5.29 % | 44.92 % | 5.96 % | 8.44 % | 5.51 % | 0.62 % | 0.86 / 0.52 |
| MIO16 | 4.81 % | 34.58 % | 4.99 % | 5.13 % | 2.47 % | 0.17 % | 0.82 / 0.46 |
| MIO07 | 0.04 % | 1.76 % | 0.00 % | 0.05 % | 0.00 % | 0.00 % | 1.00 / 0.60 |
