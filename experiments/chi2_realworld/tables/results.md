# chi2-realworld: frozen t1-tuned chi2 x0.25 gate on the real-world Monado data - results (cr_analyze.py)

## Run validity (real-world rule + Amendment-2 frame rule +-0 + chi2 delta present in launch.log)

| sequence | method | runs | valid | fallbacks | late | n_in_core | pose rule fail | frame rule fail (frames lost) | chi2 delta ok |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| MIO13 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | OpenVINS chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | SAVIOR + chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO13 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | OpenVINS chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | SAVIOR + chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO15 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | OpenVINS chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | SAVIOR + chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO16 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | OpenVINS | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | SAVIOR | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | OpenVINS chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | SAVIOR + chi2x0.25 | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | Y-Cls | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |
| MIO07 | VINS-Fusion | 10 | 10 | 0 | 0 | 0 | 0 | 0 (0) | 10 |

Invalid runs (excluded pairwise from the primary statistics): none

Trajectory md5 identical to the base method at the same offset: MIO13 ovchi_best: 0/10, MIO13 sf1_chibest: 0/10, MIO15 ovchi_best: 0/10, MIO15 sf1_chibest: 0/10, MIO16 ovchi_best: 0/10, MIO16 sf1_chibest: 0/10, MIO07 ovchi_best: 0/10, MIO07 sf1_chibest: 0/10


## ATE RMSE per sequence (posyaw, m): geometric mean over the valid runs (failures capped at 10 m) / median / failures > 1 m

| sequence | OpenVINS | SAVIOR | OpenVINS chi2x0.25 | SAVIOR + chi2x0.25 | Y-Cls | VINS-Fusion |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 moving person | 2.599 / 10.000 / 6 | 0.267 / 0.286 / 0 | 7.659 / 10.000 / 9 | 1.258 / 1.195 / 6 | 0.401 / 0.306 / 2 | 0.268 / 0.255 / 0 |
| MIO15 person + props | 0.806 / 0.381 / 4 | 0.207 / 0.172 / 1 | 6.427 / 10.000 / 9 | 1.808 / 5.414 / 5 | 0.676 / 0.254 / 3 | 0.207 / 0.200 / 0 |
| MIO16 person + props + screens | 0.155 / 0.147 / 0 | 0.196 / 0.193 / 0 | 0.398 / 0.256 / 1 | 0.154 / 0.145 / 0 | 0.158 / 0.155 / 0 | 0.302 / 0.292 / 0 |
| MIO07 static (control) | 0.039 / 0.039 / 0 | 0.038 / 0.040 / 0 | 0.055 / 0.056 / 0 | 0.053 / 0.054 / 0 | 0.038 / 0.040 / 0 | 0.056 / 0.055 / 0 |

## RPE (mean translational error, shortest savior-eval sub-length; geometric mean over valid non-failed runs)

| sequence | OpenVINS | SAVIOR | OpenVINS chi2x0.25 | SAVIOR + chi2x0.25 | Y-Cls | VINS-Fusion |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 | 0.2436 (n=4) | 0.1942 (n=10) | 0.4393 (n=1) | 0.2734 (n=4) | 0.2058 (n=8) | 0.2226 (n=10) |
| MIO15 | 0.1143 (n=6) | 0.0886 (n=9) | 0.2625 (n=1) | 0.1438 (n=5) | 0.0958 (n=7) | 0.1457 (n=10) |
| MIO16 | 0.1027 (n=10) | 0.1154 (n=10) | 0.1510 (n=9) | 0.1025 (n=10) | 0.1007 (n=10) | 0.1531 (n=10) |
| MIO07 | 0.0330 (n=10) | 0.0345 (n=10) | 0.0388 (n=10) | 0.0366 (n=10) | 0.0345 (n=10) | 0.0373 (n=10) |

## Failures (ATE > threshold), valid runs: person group / static

| method | > 0.5 m | > 1 m (protocol) | > 2 m | static > 1 m |
|---|--:|--:|--:|--:|
| OpenVINS | 11/30 | 10/30 | 9/30 | 0/10 |
| SAVIOR | 2/30 | 1/30 | 1/30 | 0/10 |
| OpenVINS chi2x0.25 | 23/30 | 19/30 | 18/30 | 0/10 |
| SAVIOR + chi2x0.25 | 14/30 | 11/30 | 6/30 | 0/10 |
| Y-Cls | 6/30 | 5/30 | 3/30 | 0/10 |
| VINS-Fusion | 0/30 | 0/30 | 0/30 | 0/10 |

## Paired ATE comparisons (primary: invalid runs excluded pairwise). GM ratio - 1 [%], run-level bootstrap 95 % CI, Wilcoxon p (Holm within group x reference over the chi2 comparisons); sequence level: two-stage cluster bootstrap, exact sign-flip (k = 3: min p = 0.25)

| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |
|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs OpenVINS | 30 | +292.3 | [+106.9, +646.7] | 3/21 | 0.000175 (0.000351) | +292.3 | [+93, +903] | 0.25 | 0/3 | MIO13 +195, MIO15 +697, MIO16 +157 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs OpenVINS | 30 | +2.5 | [-45.9, +97.9] | 12/17 | 0.67 (0.67) | +2.5 | [-60, +164] | 1.0 | 2/3 | MIO13 -52, MIO15 +124, MIO16 -1 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs SAVIOR | 30 | +1118.2 | [+542.6, +2139.2] | 3/27 | 1.64e-07 (3.28e-07) | +1118.2 | [+122, +3934] | 0.25 | 0/3 | MIO13 +2771, MIO15 +3002, MIO16 +103 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs SAVIOR | 30 | +218.4 | [+87.8, +476.8] | 8/22 | 0.000313 (0.000313) | +218.4 | [-20, +930] | 0.5 | 1/3 | MIO13 +371, MIO15 +773, MIO16 -22 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs Y-Cls | 30 | +670.6 | [+338.7, +1248.7] | 1/26 | 4.47e-08 (4.47e-08) | +670.6 | [+157, +1977] | 0.25 | 0/3 | MIO13 +1811, MIO15 +850, MIO16 +152 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs VINS-Fusion | 30 | +953.9 | [+446.4, +1848.5] | 5/25 | 2.76e-06 (5.52e-06) | +953.9 | [+44, +3688] | 0.25 | 0/3 | MIO13 +2759, MIO15 +3005, MIO16 +32 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs VINS-Fusion | 30 | +175.4 | [+54.6, +412.7] | 12/18 | 0.0113 (0.0113) | +175.4 | [-48, +923] | 0.5 | 1/3 | MIO13 +369, MIO15 +774, MIO16 -49 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 30 | -73.9 | [-84.1, -57.1] | 23/2 | 1.01e-05 (1.01e-05) | -73.9 | [-86, -51] | 0.25 | 3/3 | MIO13 -84, MIO15 -72, MIO16 -61 |
| person (MIO13+15+16) | SAVIOR vs OpenVINS | 30 | -67.8 | [-82.4, -43.5] | 20/10 | 0.00466 (nan) | -67.8 | [-91, +24] | 0.5 | 2/3 | MIO13 -90, MIO15 -74, MIO16 +27 |
| MIO13 | OpenVINS chi2x0.25 vs OpenVINS | 10 | +194.8 | [+28.7, +667.2] | 0/4 | 0.125 (0.25) | - | - | - | - | MIO13 +195 |
| MIO13 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | -51.6 | [-85.4, +98.0] | 6/4 | 0.275 (0.275) | - | - | - | - | MIO13 -52 |
| MIO13 | OpenVINS chi2x0.25 vs SAVIOR | 10 | +2771.0 | [+1644.8, +4103.6] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO13 +2771 |
| MIO13 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | +371.5 | [+184.4, +835.6] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO13 +371 |
| MIO13 | OpenVINS chi2x0.25 vs Y-Cls | 10 | +1810.7 | [+827.8, +3552.7] | 0/10 | 0.00195 (0.00195) | - | - | - | - | MIO13 +1811 |
| MIO13 | OpenVINS chi2x0.25 vs VINS-Fusion | 10 | +2758.7 | [+1413.2, +4040.7] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO13 +2759 |
| MIO13 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | +369.4 | [+175.1, +793.3] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO13 +369 |
| MIO13 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 10 | -83.6 | [-90.0, -71.0] | 9/0 | 0.00391 (0.00391) | - | - | - | - | MIO13 -84 |
| MIO13 | SAVIOR vs OpenVINS | 10 | -89.7 | [-95.9, -72.4] | 10/0 | 0.00195 (nan) | - | - | - | - | MIO13 -90 |
| MIO15 | OpenVINS chi2x0.25 vs OpenVINS | 10 | +697.1 | [+61.7, +3063.0] | 2/8 | 0.0273 (0.0547) | - | - | - | - | MIO15 +697 |
| MIO15 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | +124.2 | [-43.0, +616.3] | 1/8 | 0.129 (0.129) | - | - | - | - | MIO15 +124 |
| MIO15 | OpenVINS chi2x0.25 vs SAVIOR | 10 | +3001.8 | [+971.4, +7224.6] | 1/9 | 0.00391 (0.00391) | - | - | - | - | MIO15 +3002 |
| MIO15 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | +772.6 | [+195.7, +2637.2] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO15 +773 |
| MIO15 | OpenVINS chi2x0.25 vs Y-Cls | 10 | +850.4 | [+234.1, +2459.6] | 0/7 | 0.0156 (0.0156) | - | - | - | - | MIO15 +850 |
| MIO15 | OpenVINS chi2x0.25 vs VINS-Fusion | 10 | +3005.2 | [+1461.1, +5141.8] | 0/10 | 0.00195 (0.00391) | - | - | - | - | MIO15 +3005 |
| MIO15 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | +773.6 | [+182.4, +2476.8] | 2/8 | 0.00977 (0.00977) | - | - | - | - | MIO15 +774 |
| MIO15 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 10 | -71.9 | [-90.9, -12.9] | 5/1 | 0.0938 (0.0938) | - | - | - | - | MIO15 -72 |
| MIO15 | SAVIOR vs OpenVINS | 10 | -74.3 | [-90.5, -37.1] | 8/2 | 0.0195 (nan) | - | - | - | - | MIO15 -74 |
| MIO16 | OpenVINS chi2x0.25 vs OpenVINS | 10 | +156.9 | [+54.5, +435.4] | 1/9 | 0.00391 (0.00781) | - | - | - | - | MIO16 +157 |
| MIO16 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | -0.7 | [-16.9, +16.6] | 5/5 | 1 (1) | - | - | - | - | MIO16 -1 |
| MIO16 | OpenVINS chi2x0.25 vs SAVIOR | 10 | +103.0 | [+16.1, +344.3] | 2/8 | 0.0371 (0.0371) | - | - | - | - | MIO16 +103 |
| MIO16 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | -21.5 | [-30.1, -11.3] | 8/2 | 0.0137 (0.0273) | - | - | - | - | MIO16 -22 |
| MIO16 | OpenVINS chi2x0.25 vs Y-Cls | 10 | +152.0 | [+43.9, +475.3] | 1/9 | 0.00586 (0.00586) | - | - | - | - | MIO16 +152 |
| MIO16 | OpenVINS chi2x0.25 vs VINS-Fusion | 10 | +31.9 | [-21.0, +182.6] | 5/5 | 1 (1) | - | - | - | - | MIO16 +32 |
| MIO16 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | -49.0 | [-54.6, -41.4] | 10/0 | 0.00195 (0.00391) | - | - | - | - | MIO16 -49 |
| MIO16 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 10 | -61.4 | [-83.1, -29.4] | 9/1 | 0.00586 (0.00586) | - | - | - | - | MIO16 -61 |
| MIO16 | SAVIOR vs OpenVINS | 10 | +26.6 | [+5.7, +50.2] | 2/8 | 0.0645 (nan) | - | - | - | - | MIO16 +27 |
| static MIO07 | OpenVINS chi2x0.25 vs OpenVINS | 10 | +38.4 | [+25.2, +50.2] | 1/9 | 0.00391 (0.00781) | - | - | - | - | MIO07 +38 |
| static MIO07 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | +34.9 | [+18.7, +50.6] | 2/8 | 0.00977 (0.00977) | - | - | - | - | MIO07 +35 |
| static MIO07 | OpenVINS chi2x0.25 vs SAVIOR | 10 | +43.2 | [+24.0, +66.5] | 1/9 | 0.00391 (0.00781) | - | - | - | - | MIO07 +43 |
| static MIO07 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | +39.5 | [+23.4, +58.2] | 1/9 | 0.00391 (0.00781) | - | - | - | - | MIO07 +40 |
| static MIO07 | OpenVINS chi2x0.25 vs Y-Cls | 10 | +43.2 | [+23.9, +66.5] | 1/9 | 0.00391 (0.00391) | - | - | - | - | MIO07 +43 |
| static MIO07 | OpenVINS chi2x0.25 vs VINS-Fusion | 10 | -2.2 | [-15.0, +11.4] | 4/6 | 0.922 (1) | - | - | - | - | MIO07 -2 |
| static MIO07 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | -4.7 | [-17.5, +9.3] | 4/6 | 0.846 (1) | - | - | - | - | MIO07 -5 |
| static MIO07 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 10 | -2.5 | [-12.4, +4.6] | 3/7 | 0.625 (0.625) | - | - | - | - | MIO07 -3 |
| static MIO07 | SAVIOR vs OpenVINS | 10 | -3.3 | [-18.0, +14.8] | 6/4 | 0.922 (nan) | - | - | - | - | MIO07 -3 |

## Paired RPE comparisons (secondary; pairs where neither run fails)

| group | A vs B | n | GM [%] | 95 % CI | wins/losses | p (Holm) | seq-level [%] | seq CI | sign-flip p | seq. direction | per sequence [%] |
|---|---|--:|--:|---|--:|---|--:|---|--:|--:|---|
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs OpenVINS | 10 | +55.6 | [+35.8, +78.3] | 0/10 | 0.00195 (0.00391) | +81.9 | [+41, +121] | 0.5 | 0/2 | MIO13 +121, MIO16 +50 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs OpenVINS | 15 | +16.5 | [+1.0, +38.4] | 5/10 | 0.0946 (0.0946) | +30.8 | [+2, +73] | 0.5 | 1/3 | MIO13 +36, MIO15 +65, MIO16 -0 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs SAVIOR | 11 | +53.2 | [+21.1, +98.5] | 0/11 | 0.000977 (0.00195) | +132.6 | [+35, +222] | 0.25 | 0/3 | MIO13 +198, MIO15 +222, MIO16 +31 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs SAVIOR | 19 | +16.2 | [-1.7, +42.2] | 10/9 | 0.515 (0.515) | +29.0 | [-10, +83] | 0.5 | 1/3 | MIO13 +45, MIO15 +66, MIO16 -11 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs Y-Cls | 11 | +69.0 | [+37.7, +117.7] | 0/11 | 0.000977 (0.000977) | +136.9 | [+51, +363] | 0.25 | 0/3 | MIO13 +93, MIO15 +363, MIO16 +49 |
| person (MIO13+15+16) | OpenVINS chi2x0.25 vs VINS-Fusion | 11 | +8.2 | [-8.2, +29.0] | 6/5 | 0.638 (0.638) | +39.1 | [+1, +79] | 0.5 | 1/3 | MIO13 +79, MIO15 +52, MIO16 -2 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs VINS-Fusion | 19 | -16.4 | [-29.4, +0.4] | 12/7 | 0.0401 (0.0803) | -7.7 | [-33, +24] | 0.75 | 2/3 | MIO13 +21, MIO15 -3, MIO16 -33 |
| person (MIO13+15+16) | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 11 | -37.0 | [-48.9, -24.0] | 11/0 | 0.000977 (0.000977) | -49.4 | [-69, -30] | 0.25 | 3/3 | MIO13 -38, MIO15 -69, MIO16 -32 |
| person (MIO13+15+16) | SAVIOR vs OpenVINS | 20 | -6.9 | [-18.6, +6.1] | 12/8 | 0.368 (nan) | -13.0 | [-30, +12] | 0.5 | 2/3 | MIO13 -27, MIO15 -20, MIO16 +12 |
| MIO13 | OpenVINS chi2x0.25 vs OpenVINS | 1 | +121.1 | [+121.1, +121.1] | 0/1 | 1 (1) | - | - | - | - | MIO13 +121 |
| MIO13 | SAVIOR + chi2x0.25 vs OpenVINS | 1 | +36.1 | [+36.1, +36.1] | 0/1 | 1 (1) | - | - | - | - | MIO13 +36 |
| MIO13 | OpenVINS chi2x0.25 vs SAVIOR | 1 | +198.1 | [+198.1, +198.1] | 0/1 | 1 (1) | - | - | - | - | MIO13 +198 |
| MIO13 | SAVIOR + chi2x0.25 vs SAVIOR | 4 | +45.2 | [+17.1, +80.1] | 0/4 | 0.125 (0.25) | - | - | - | - | MIO13 +45 |
| MIO13 | OpenVINS chi2x0.25 vs Y-Cls | 1 | +92.9 | [+92.9, +92.9] | 0/1 | 1 (1) | - | - | - | - | MIO13 +93 |
| MIO13 | OpenVINS chi2x0.25 vs VINS-Fusion | 1 | +79.3 | [+79.3, +79.3] | 0/1 | 1 (1) | - | - | - | - | MIO13 +79 |
| MIO13 | SAVIOR + chi2x0.25 vs VINS-Fusion | 4 | +20.8 | [+14.1, +27.8] | 0/4 | 0.125 (0.25) | - | - | - | - | MIO13 +21 |
| MIO13 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 1 | -38.5 | [-38.5, -38.5] | 1/0 | 1 (1) | - | - | - | - | MIO13 -38 |
| MIO13 | SAVIOR vs OpenVINS | 4 | -26.8 | [-33.5, -21.7] | 4/0 | 0.125 (nan) | - | - | - | - | MIO13 -27 |
| MIO15 | SAVIOR + chi2x0.25 vs OpenVINS | 4 | +64.7 | [+22.7, +147.3] | 0/4 | 0.125 (0.125) | - | - | - | - | MIO15 +65 |
| MIO15 | OpenVINS chi2x0.25 vs SAVIOR | 1 | +222.4 | [+222.4, +222.4] | 0/1 | 1 (1) | - | - | - | - | MIO15 +222 |
| MIO15 | SAVIOR + chi2x0.25 vs SAVIOR | 5 | +66.3 | [+7.2, +163.8] | 2/3 | 0.312 (0.625) | - | - | - | - | MIO15 +66 |
| MIO15 | OpenVINS chi2x0.25 vs Y-Cls | 1 | +363.2 | [+363.2, +363.2] | 0/1 | 1 (1) | - | - | - | - | MIO15 +363 |
| MIO15 | OpenVINS chi2x0.25 vs VINS-Fusion | 1 | +52.5 | [+52.5, +52.5] | 0/1 | 1 (1) | - | - | - | - | MIO15 +52 |
| MIO15 | SAVIOR + chi2x0.25 vs VINS-Fusion | 5 | -2.8 | [-37.0, +54.4] | 2/3 | 1 (1) | - | - | - | - | MIO15 -3 |
| MIO15 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 1 | -69.2 | [-69.2, -69.2] | 1/0 | 1 (1) | - | - | - | - | MIO15 -69 |
| MIO15 | SAVIOR vs OpenVINS | 6 | -20.0 | [-39.3, +8.8] | 5/1 | 0.219 (nan) | - | - | - | - | MIO15 -20 |
| MIO16 | OpenVINS chi2x0.25 vs OpenVINS | 9 | +49.7 | [+31.4, +70.1] | 0/9 | 0.00391 (0.00781) | - | - | - | - | MIO16 +50 |
| MIO16 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | -0.2 | [-9.2, +9.4] | 5/5 | 1 (1) | - | - | - | - | MIO16 -0 |
| MIO16 | OpenVINS chi2x0.25 vs SAVIOR | 9 | +31.0 | [+9.6, +60.4] | 0/9 | 0.00391 (0.00781) | - | - | - | - | MIO16 +31 |
| MIO16 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | -11.2 | [-16.3, -5.4] | 8/2 | 0.0195 (0.0195) | - | - | - | - | MIO16 -11 |
| MIO16 | OpenVINS chi2x0.25 vs Y-Cls | 9 | +48.9 | [+28.6, +74.4] | 0/9 | 0.00391 (0.00391) | - | - | - | - | MIO16 +49 |
| MIO16 | OpenVINS chi2x0.25 vs VINS-Fusion | 9 | -1.5 | [-14.2, +15.7] | 6/3 | 0.652 (0.652) | - | - | - | - | MIO16 -2 |
| MIO16 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | -33.0 | [-40.2, -26.2] | 10/0 | 0.00195 (0.00391) | - | - | - | - | MIO16 -33 |
| MIO16 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 9 | -31.5 | [-43.4, -18.7] | 9/0 | 0.00391 (0.00391) | - | - | - | - | MIO16 -32 |
| MIO16 | SAVIOR vs OpenVINS | 10 | +12.4 | [+1.2, +24.6] | 3/7 | 0.084 (nan) | - | - | - | - | MIO16 +12 |
| static MIO07 | OpenVINS chi2x0.25 vs OpenVINS | 10 | +17.4 | [+9.6, +26.4] | 1/9 | 0.00391 (0.00781) | - | - | - | - | MIO07 +17 |
| static MIO07 | SAVIOR + chi2x0.25 vs OpenVINS | 10 | +10.9 | [+1.8, +21.6] | 3/7 | 0.0645 (0.0645) | - | - | - | - | MIO07 +11 |
| static MIO07 | OpenVINS chi2x0.25 vs SAVIOR | 10 | +12.4 | [+4.0, +21.4] | 1/9 | 0.0273 (0.0547) | - | - | - | - | MIO07 +12 |
| static MIO07 | SAVIOR + chi2x0.25 vs SAVIOR | 10 | +6.1 | [-1.1, +12.5] | 3/7 | 0.131 (0.131) | - | - | - | - | MIO07 +6 |
| static MIO07 | OpenVINS chi2x0.25 vs Y-Cls | 10 | +12.4 | [+4.0, +21.4] | 1/9 | 0.0273 (0.0273) | - | - | - | - | MIO07 +12 |
| static MIO07 | OpenVINS chi2x0.25 vs VINS-Fusion | 10 | +4.0 | [-2.9, +11.3] | 4/6 | 0.232 (0.465) | - | - | - | - | MIO07 +4 |
| static MIO07 | SAVIOR + chi2x0.25 vs VINS-Fusion | 10 | -1.8 | [-4.9, +1.4] | 7/3 | 0.322 (0.465) | - | - | - | - | MIO07 -2 |
| static MIO07 | SAVIOR + chi2x0.25 vs OpenVINS chi2x0.25 | 10 | -5.6 | [-10.4, -0.7] | 7/3 | 0.105 (0.105) | - | - | - | - | MIO07 -6 |
| static MIO07 | SAVIOR vs OpenVINS | 10 | +4.5 | [-5.2, +14.8] | 3/7 | 0.322 (nan) | - | - | - | - | MIO07 +5 |

## Sensitivity (person group, run-level GM [%])

| A vs B | cap 2 m | cap 10 m | cap 50 m | failures excluded (> 1 m) | include-all (10 m) |
|---|--:|--:|--:|--:|--:|
| OpenVINS chi2x0.25 vs OpenVINS | +136.6 (n=30) | +292.3 (n=30) | +490.2 (n=30) | +97.2 (n=10) | +292.3 (n=30) |
| SAVIOR + chi2x0.25 vs OpenVINS | +17.7 (n=30) | +2.5 (n=30) | -7.9 (n=30) | +25.0 (n=15) | +2.5 (n=30) |
| OpenVINS chi2x0.25 vs SAVIOR | +366.3 (n=30) | +1118.2 (n=30) | +2715.1 (n=30) | +78.9 (n=11) | +1118.2 (n=30) |
| SAVIOR + chi2x0.25 vs SAVIOR | +132.0 (n=30) | +218.4 (n=30) | +339.3 (n=30) | +27.4 (n=19) | +218.4 (n=30) |

## DECISION_RULE.txt (pre-registered, md5 ad578908...)

- T1 ovchi_best vs OpenVINS, person group: GM +292.3 % [+106.9, +646.7] (n=30) -> FAILS (needs GM < 0 and CI excluding 0)
- T2 ovchi_best vs SAVIOR, person group: GM ratio 12.182 (+1118.2 % [+542.6, +2139.2]); failures > 1 m 19/30 vs SAVIOR 1/30 (limit 3) -> FAILS (needs ratio <= 1.0 and failures <= SAVIOR + 2)
- **Verdict: the tuned-threshold result DOES NOT TRANSFER to real data.**
