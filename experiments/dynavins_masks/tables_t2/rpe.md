# DynaVINS + SAVIOR masks (P10), t2, RPE (12 sequences x 10 offsets; failure = ATE > 2 m, capped at 10 m)

## Median RPE [m] ([n] = failures)

| seq | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| aisles_t2_L0 | 0.039 | 0.041 | 0.036 | 0.039 | 0.054 | 0.039 | 0.039 |
| aisles_t2_L1 | 0.031 | 0.042 | 0.035 | 0.033 | 0.056 | 0.031 | 0.032 |
| aisles_t2_L2 | 0.029 | 0.042 | 0.032 | 0.026 | 0.051 | 0.029 | 0.029 |
| aisles_t2_L3 | 0.031 | 0.036 | 0.032 | 0.022 | 0.062 | 0.031 | 0.031 |
| hall_t2_L0 | 0.041 | 0.045 | 0.039 | 0.041 | 0.035 | 0.041 | 0.041 |
| hall_t2_L1 | 0.041 | 0.045 | 0.042 | 0.041 | 0.044 | 0.041 | 0.041 |
| hall_t2_L2 | 0.064 | 0.048 | 0.043 | 0.038 | 0.043 | 0.064 | 0.064 |
| hall_t2_L3 | 0.049 | 0.051 | 0.043 | 0.038 | 0.055 | 0.049 | 0.049 |
| dock_t2_L0 | 0.027 | 0.039 | 0.030 | 0.027 | 0.060 | 0.027 | 0.027 |
| dock_t2_L1 | 0.028 | 0.043 | 0.027 | 0.025 | 0.061 | 0.028 | 0.028 |
| dock_t2_L2 | 0.039 | 0.038 | 0.038 | 0.037 | 0.067 | 0.039 | 0.039 |
| dock_t2_L3 | 0.043 | 0.045 | 0.043 | 0.032 | 0.081 | 0.043 | 0.043 |

## Failures (ATE > 2 m) per group

| group | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| L0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L0+L1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| L2+L3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hall_L3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| all | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dock_L3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hall+dock_L3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Paired vs DynaVINS (geometric-mean RPE ratio - 1; negative = better; Holm over 4 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all | dock_L3 | hall+dock_L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| DynaVINS+Y-Cls | +17.1 % [+11, +24] p=7.99e-06 H=3.2e-05 4/26<br>clu [+4, +37] p=0.0023 H=0.0092 (k=3) | +28.8 % [+20, +39] p=4.71e-07 H=1.41e-06 2/28<br>clu [+10, +53] p=0 H=0 (k=3) | +2.6 % [-8, +13] p=0.516 H=0.954 15/15<br>clu [-23, +38] p=0.813 H=1 (k=3) | +4.0 % [-1, +8] p=0.0145 H=0.0291 11/19<br>clu [-4, +12] p=0.298 H=0.386 (k=3) | +22.8 % [+17, +29] p=1.98e-09 H=7.91e-09 6/54<br>clu [+10, +38] p=0 H=0 (k=6) | +3.3 % [-2, +9] p=0.112 H=0.167 26/34<br>clu [-11, +20] p=0.662 H=0.674 (k=6) | +1.9 % [-2, +6] p=0.432 H=0.432 5/5<br>clu [-2, +6] p=0.364 H=0.364 (k=1) | +12.6 % [+8, +17] p=2.39e-08 H=4.79e-08 32/88<br>clu [+1, +25] p=0.0314 H=0.0628 (k=12) | -1.7 % [-12, +8] p=0.846 H=1 5/5<br>clu [-12, +8] p=0.795 H=0.795 (k=1) | +0.1 % [-6, +5] p=0.409 H=0.409 10/10<br>clu [-7, +5] p=0.834 H=0.834 (k=2) |
| DynaVINS+SAVIOR | -1.7 % [-5, +2] p=0.262 H=0.524 19/11<br>clu [-8, +6] p=0.64 H=1 (k=3) | +1.3 % [-3, +6] p=0.289 H=0.579 9/21<br>clu [-6, +10] p=0.746 H=1 (k=3) | -7.2 % [-16, +2] p=0.477 H=0.954 14/16<br>clu [-30, +14] p=0.612 H=1 (k=3) | -5.9 % [-11, -1] p=0.0405 H=0.0405 18/12<br>clu [-14, +3] p=0.193 H=0.386 (k=3) | -0.2 % [-3, +3] p=0.889 H=1 28/32<br>clu [-5, +6] p=0.956 H=1 (k=6) | -6.5 % [-12, -2] p=0.0836 H=0.167 32/28<br>clu [-19, +6] p=0.337 H=0.674 (k=6) | -13.2 % [-18, -9] p=0.00195 H=0.00781 10/0<br>clu [-18, -9] p=0 H=0 (k=1) | -3.4 % [-6, -0] p=0.155 H=0.155 60/60<br>clu [-11, +3] p=0.381 H=0.381 (k=12) | -6.2 % [-16, +3] p=0.557 H=1 5/5<br>clu [-16, +3] p=0.222 H=0.443 (k=1) | -9.8 % [-15, -4] p=0.00422 H=0.00844 15/5<br>clu [-16, -2] p=0.0167 H=0.0334 (k=2) |
| DynaVINS+O-Dyn+B | +0.0 % [+0, +0] p=1 H=1 0/0<br>clu [+0, +0] p=1 H=1 (k=3) | -1.1 % [-6, +4] p=0.543 H=0.579 18/12<br>clu [-8, +6] p=0.774 H=1 (k=3) | -18.8 % [-26, -12] p=3.9e-05 H=0.000156 25/5<br>clu [-39, -1] p=0.0199 H=0.0796 (k=3) | -27.2 % [-32, -23] p=3.73e-09 H=1.49e-08 29/1<br>clu [-34, -21] p=0 H=0 (k=3) | -0.6 % [-3, +2] p=0.543 H=1 18/12<br>clu [-4, +3] p=0.807 H=1 (k=6) | -23.1 % [-27, -19] p=3.09e-10 H=1.24e-09 54/6<br>clu [-33, -12] p=0.0001 H=0.0004 (k=6) | -22.1 % [-29, -14] p=0.00391 H=0.0117 9/1<br>clu [-29, -14] p=0 H=0 (k=1) | -12.6 % [-16, -9] p=9.01e-10 H=2.7e-09 72/18<br>clu [-21, -4] p=0.0018 H=0.0054 (k=12) | -32.1 % [-43, -22] p=0.00195 H=0.00781 10/0<br>clu [-43, -22] p=0 H=0 (k=1) | -27.3 % [-34, -20] p=3.81e-06 H=1.53e-05 19/1<br>clu [-37, -18] p=0 H=0 (k=2) |
| DynaVINS+O-Cls+B | +42.3 % [+24, +64] p=6.29e-05 H=0.000189 9/21<br>clu [-9, +118] p=0.0713 H=0.214 (k=3) | +60.6 % [+43, +79] p=1.02e-07 H=4.1e-07 3/27<br>clu [+9, +115] p=0 H=0 (k=3) | +26.9 % [+7, +49] p=0.00578 H=0.0173 10/20<br>clu [-32, +79] p=0.515 H=1 (k=3) | +58.7 % [+43, +76] p=1.86e-08 H=5.59e-08 2/28<br>clu [+12, +101] p=0 H=0 (k=3) | +51.2 % [+38, +66] p=5.53e-09 H=1.66e-08 12/48<br>clu [+14, +97] p=0.0021 H=0.0063 (k=6) | +41.9 % [+28, +57] p=3.78e-07 H=1.14e-06 12/48<br>clu [+1, +85] p=0.0433 H=0.13 (k=6) | +11.0 % [+5, +17] p=0.0195 H=0.0391 2/8<br>clu [+5, +17] p=0.0008 H=0.0016 (k=1) | +46.5 % [+36, +57] p=1.89e-14 H=7.58e-14 24/96<br>clu [+18, +78] p=0.001 H=0.004 (k=12) | +79.1 % [+57, +98] p=0.00195 H=0.00781 0/10<br>clu [+57, +99] p=0 H=0 (k=1) | +41.0 % [+25, +60] p=1.91e-05 H=5.72e-05 2/18<br>clu [+8, +89] p=0 H=0 (k=2) |

## Paired vs DynaVINS+Y-Cls (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all | dock_L3 | hall+dock_L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| DynaVINS+SAVIOR | -16.1 % [-20, -13] p=3.54e-08 H=3.54e-08 28/2<br>clu [-23, -10] p=0 H=0 (k=3) | -21.3 % [-28, -15] p=6.15e-08 H=6.15e-08 27/3<br>clu [-38, -7] p=0 H=0 (k=3) | -9.5 % [-14, -5] p=0.00113 H=0.00113 22/8<br>clu [-18, -1] p=0.033 H=0.033 (k=3) | -9.5 % [-12, -7] p=1.99e-06 H=1.99e-06 28/2<br>clu [-15, -4] p=0 H=0 (k=3) | -18.7 % [-22, -15] p=6.92e-11 H=6.92e-11 55/5<br>clu [-28, -11] p=0 H=0 (k=6) | -9.5 % [-12, -7] p=2.66e-07 H=2.66e-07 50/10<br>clu [-14, -4] p=0.0002 H=0.0002 (k=6) | -14.9 % [-17, -12] p=0.00195 H=0.00195 10/0<br>clu [-18, -12] p=0 H=0 (k=1) | -14.2 % [-17, -12] p=5.64e-17 H=5.64e-17 105/15<br>clu [-21, -9] p=0 H=0 (k=12) | -4.6 % [-7, -2] p=0.0195 H=0.0195 9/1<br>clu [-7, -2] p=0.0002 H=0.0002 (k=1) | -9.9 % [-13, -7] p=1.91e-05 H=1.91e-05 19/1<br>clu [-16, -3] p=0 H=0 (k=2) |

## Paired vs DynaVINS+O-Cls+B (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all | dock_L3 | hall+dock_L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| DynaVINS+O-Dyn+B | -29.7 % [-39, -19] p=6.29e-05 H=6.29e-05 21/9<br>clu [-54, +10] p=0.0713 H=0.0713 (k=3) | -38.4 % [-46, -30] p=6.91e-07 H=6.91e-07 27/3<br>clu [-57, -8] p=0.0062 H=0.0062 (k=3) | -36.0 % [-42, -29] p=6.15e-08 H=6.15e-08 27/3<br>clu [-48, -11] p=0 H=0 (k=3) | -54.1 % [-59, -48] p=1.86e-09 H=1.86e-09 30/0<br>clu [-64, -31] p=0 H=0 (k=3) | -34.2 % [-40, -27] p=1.02e-08 H=1.02e-08 48/12<br>clu [-50, -12] p=0.0031 H=0.0031 (k=6) | -45.8 % [-50, -41] p=2.56e-11 H=2.56e-11 57/3<br>clu [-58, -30] p=0 H=0 (k=6) | -29.8 % [-34, -25] p=0.00195 H=0.00195 10/0<br>clu [-34, -25] p=0 H=0 (k=1) | -40.3 % [-44, -36] p=6.5e-19 H=6.5e-19 105/15<br>clu [-51, -27] p=0 H=0 (k=12) | -62.1 % [-65, -60] p=0.00195 H=0.00195 10/0<br>clu [-65, -60] p=0 H=0 (k=1) | -48.4 % [-55, -40] p=1.91e-06 H=1.91e-06 20/0<br>clu [-63, -28] p=0 H=0 (k=2) |

## Paired vs DynaVINS (upstream threads) (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all | dock_L3 | hall+dock_L3 |
|---|---|---|---|---|---|---|---|---|---|---|
| DynaVINS | +0.2 % [-0, +0] p=0.777 H=0.777 16/14<br>clu [-0, +1] p=0.215 H=0.215 (k=3) | -0.0 % [-0, +0] p=0.416 H=0.416 17/13<br>clu [-0, +1] p=0.888 H=0.888 (k=3) | +0.0 % [-0, +0] p=0.67 H=0.67 15/15<br>clu [-0, +0] p=0.97 H=0.97 (k=3) | -0.1 % [-0, +0] p=0.871 H=0.871 17/13<br>clu [-0, +0] p=0.755 H=0.755 (k=3) | +0.1 % [-0, +0] p=0.41 H=0.41 33/27<br>clu [-0, +0] p=0.672 H=0.672 (k=6) | -0.0 % [-0, +0] p=0.866 H=0.866 32/28<br>clu [-0, +0] p=0.978 H=0.978 (k=6) | -0.1 % [-1, +1] p=0.695 H=0.695 6/4<br>clu [-1, +1] p=0.771 H=0.771 (k=1) | +0.0 % [-0, +0] p=0.687 H=0.687 65/55<br>clu [-0, +0] p=0.722 H=0.722 (k=12) | +0.1 % [-0, +0] p=0.846 H=0.846 6/4<br>clu [-0, +0] p=0.379 H=0.379 (k=1) | -0.0 % [-0, +0] p=0.869 H=0.869 12/8<br>clu [-0, +0] p=0.879 H=0.879 (k=2) |

## Pose-count rule (poses >= same-offset DynaVINS poses - 1)

- DynaVINS+Y-Cls: 120/120 pass
- DynaVINS+SAVIOR: 120/120 pass
- DynaVINS+O-Dyn+B: 120/120 pass
- DynaVINS+O-Cls+B: 120/120 pass
- DynaVINS+zero-masks: 120/120 pass
- DynaVINS (upstream threads): 120/120 pass
