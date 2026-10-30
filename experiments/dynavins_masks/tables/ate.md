# DynaVINS + SAVIOR masks (P10), t1, ATE (8 sequences x 10 offsets; failure = ATE > 2 m, capped at 10 m)

## Median ATE [m] ([n] = failures)

| seq | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| aisles_t1_L0 | 0.097 | 0.085 | 0.084 | 0.097 | 0.100 | 0.097 | 0.097 |
| aisles_t1_L1 | 0.088 | 0.114 | 0.096 | 0.082 | 0.106 | 0.088 | 0.088 |
| aisles_t1_L2 | 0.097 | 0.088 | 0.101 | 0.096 | 0.121 | 0.097 | 0.097 |
| aisles_t1_L3 | 0.113 | 0.102 | 0.085 | 0.076 | 0.135 | 0.113 | 0.114 |
| hall_t1_L0 | 0.098 | 0.083 | 0.083 | 0.098 | 0.118 | 0.098 | 0.099 |
| hall_t1_L1 | 0.177 | 0.087 | 0.062 | 0.140 | 0.120 | 0.177 | 0.178 |
| hall_t1_L2 | 0.075 | 0.076 | 0.051 | 0.072 | 0.121 | 0.075 | 0.076 |
| hall_t1_L3 | 0.096 | 0.087 | 0.068 | 0.124 | 0.083 | 0.096 | 0.096 |

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

## Paired vs DynaVINS (geometric-mean ATE ratio - 1; negative = better; Holm over 4 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+Y-Cls | -11.4 % [-20, -2] p=0.0362 H=0.0725 15/5<br>clu [-21, -2] p=0.0199 H=0.0398 (k=2) | -17.2 % [-34, +4] p=0.202 H=0.405 11/9<br>clu [-51, +35] p=0.51 H=1 (k=2) | -2.1 % [-9, +6] p=0.368 H=0.737 12/8<br>clu [-10, +9] p=0.623 H=1 (k=2) | -6.8 % [-21, +10] p=0.498 H=0.777 10/10<br>clu [-21, +11] p=0.36 H=1 (k=2) | -14.4 % [-25, -3] p=0.0548 H=0.11 26/14<br>clu [-38, +15] p=0.323 H=0.645 (k=4) | -4.5 % [-13, +5] p=0.289 H=0.577 22/18<br>clu [-14, +6] p=0.346 H=0.691 (k=4) | -5.9 % [-30, +27] p=0.625 H=0.75 5/5<br>clu [-31, +27] p=0.701 H=1 (k=1) | -9.6 % [-16, -2] p=0.0291 H=0.0408 48/32<br>clu [-25, +5] p=0.228 H=0.455 (k=8) |
| DynaVINS+SAVIOR | -12.4 % [-18, -6] p=0.00831 H=0.0332 15/5<br>clu [-18, -5] p=0.0015 H=0.006 (k=2) | -34.6 % [-49, -17] p=0.0073 H=0.0219 13/7<br>clu [-63, +12] p=0.477 H=1 (k=2) | -17.0 % [-27, -6] p=0.0266 H=0.0799 13/7<br>clu [-37, +6] p=0.399 H=1 (k=2) | -26.2 % [-36, -16] p=0.000322 H=0.00129 18/2<br>clu [-38, -16] p=0 H=0 (k=2) | -24.3 % [-34, -14] p=0.000281 H=0.00105 28/12<br>clu [-51, +1] p=0.0719 H=0.288 (k=4) | -21.8 % [-29, -14] p=1.43e-05 H=5.72e-05 31/9<br>clu [-34, -6] p=0.0064 H=0.0256 (k=4) | -28.9 % [-45, -9] p=0.0488 H=0.195 8/2<br>clu [-45, -8] p=0.0056 H=0.0168 (k=1) | -23.1 % [-29, -17] p=6.13e-08 H=2.45e-07 59/21<br>clu [-39, -7] p=0.0013 H=0.0052 (k=8) |
| DynaVINS+O-Dyn+B | +0.0 % [+0, +0] p=1 H=1 0/0<br>clu [+0, +0] p=1 H=1 (k=2) | -17.7 % [-24, -11] p=0.000261 H=0.00105 16/4<br>clu [-30, -3] p=0.0057 H=0.0228 (k=2) | +3.1 % [-8, +15] p=0.622 H=0.737 9/11<br>clu [-8, +17] p=0.625 H=1 (k=2) | -10.1 % [-23, +5] p=0.202 H=0.607 13/7<br>clu [-37, +29] p=0.516 H=1 (k=2) | -9.3 % [-14, -5] p=0.000261 H=0.00105 16/4<br>clu [-22, +0] p=0.138 H=0.413 (k=4) | -3.7 % [-13, +6] p=0.501 H=0.577 22/18<br>clu [-25, +18] p=0.793 H=0.793 (k=4) | +21.8 % [+8, +38] p=0.0488 H=0.195 3/7<br>clu [+8, +38] p=0.0015 H=0.006 (k=1) | -6.5 % [-12, -1] p=0.0204 H=0.0408 38/22<br>clu [-19, +6] p=0.332 H=0.455 (k=8) |
| DynaVINS+O-Cls+B | +14.9 % [+5, +28] p=0.0172 H=0.0515 8/12<br>clu [+3, +34] p=0.004 H=0.012 (k=2) | -4.8 % [-18, +9] p=0.756 H=0.756 9/11<br>clu [-29, +21] p=0.701 H=1 (k=2) | +38.6 % [+25, +55] p=5.72e-06 H=2.29e-05 1/19<br>clu [+20, +67] p=0 H=0 (k=2) | +7.1 % [-9, +27] p=0.388 H=0.777 7/13<br>clu [-20, +29] p=0.59 H=1 (k=2) | +4.6 % [-5, +14] p=0.179 H=0.179 17/23<br>clu [-15, +23] p=0.616 H=0.645 (k=4) | +21.9 % [+9, +35] p=0.000379 H=0.00114 8/32<br>clu [-2, +47] p=0.0738 H=0.221 (k=4) | -7.8 % [-30, +28] p=0.375 H=0.75 6/4<br>clu [-30, +27] p=0.571 H=1 (k=1) | +12.9 % [+5, +21] p=0.000393 H=0.00118 25/55<br>clu [-3, +30] p=0.117 H=0.352 (k=8) |

## Paired vs DynaVINS+Y-Cls (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+SAVIOR | -1.0 % [-8, +7] p=0.812 H=0.812 10/10<br>clu [-9, +8] p=0.777 H=0.777 (k=2) | -21.1 % [-28, -13] p=0.000168 H=0.000168 19/1<br>clu [-31, -13] p=0 H=0 (k=2) | -15.3 % [-25, -4] p=0.0441 H=0.0441 12/8<br>clu [-37, +11] p=0.507 H=0.507 (k=2) | -20.9 % [-26, -15] p=9.54e-06 H=9.54e-06 19/1<br>clu [-28, -15] p=0 H=0 (k=2) | -11.6 % [-18, -5] p=0.00186 H=0.00186 29/11<br>clu [-23, +0] p=0.0539 H=0.0539 (k=4) | -18.1 % [-24, -12] p=2.04e-06 H=2.04e-06 31/9<br>clu [-31, -0] p=0.0479 H=0.0479 (k=4) | -24.4 % [-33, -15] p=0.00391 H=0.00391 9/1<br>clu [-32, -15] p=0 H=0 (k=1) | -14.9 % [-19, -11] p=2.4e-07 H=2.4e-07 60/20<br>clu [-24, -5] p=0.0055 H=0.0055 (k=8) |

## Paired vs DynaVINS+O-Cls+B (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+O-Dyn+B | -12.9 % [-22, -4] p=0.0172 H=0.0172 12/8<br>clu [-25, -3] p=0.004 H=0.004 (k=2) | -13.5 % [-24, -2] p=0.0532 H=0.0532 15/5<br>clu [-23, +4] p=0.111 H=0.111 (k=2) | -25.6 % [-34, -17] p=0.000105 H=0.000105 17/3<br>clu [-38, -16] p=0 H=0 (k=2) | -16.1 % [-33, +6] p=0.114 H=0.114 11/9<br>clu [-48, +48] p=0.509 H=0.509 (k=2) | -13.2 % [-20, -6] p=0.0016 H=0.0016 27/13<br>clu [-22, -3] p=0.0114 H=0.0114 (k=4) | -21.0 % [-30, -10] p=0.00186 H=0.00186 28/12<br>clu [-42, +13] p=0.197 H=0.197 (k=4) | +32.1 % [-0, +65] p=0.0645 H=0.0645 1/9<br>clu [+0, +65] p=0.0499 H=0.0499 (k=1) | -17.2 % [-23, -10] p=1.97e-05 H=1.97e-05 55/25<br>clu [-31, -1] p=0.0424 H=0.0424 (k=8) |

## Paired vs DynaVINS (upstream threads) (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS | -0.3 % [-1, +0] p=0.596 H=0.596 11/9<br>clu [-1, +0] p=0.653 H=0.653 (k=2) | -0.2 % [-1, +0] p=0.189 H=0.189 12/8<br>clu [-1, +0] p=0.414 H=0.414 (k=2) | -0.4 % [-1, -0] p=0.216 H=0.216 13/7<br>clu [-1, +0] p=0.378 H=0.378 (k=2) | +0.3 % [-0, +1] p=1 H=1 11/9<br>clu [-0, +1] p=0.626 H=0.626 (k=2) | -0.2 % [-1, +0] p=0.179 H=0.179 23/17<br>clu [-1, +0] p=0.2 H=0.2 (k=4) | -0.0 % [-0, +0] p=0.347 H=0.347 24/16<br>clu [-1, +1] p=0.879 H=0.879 (k=4) | +1.0 % [-0, +2] p=0.322 H=0.322 4/6<br>clu [-0, +2] p=0.069 H=0.069 (k=1) | -0.1 % [-0, +0] p=0.0951 H=0.0951 47/33<br>clu [-1, +0] p=0.477 H=0.477 (k=8) |

## Pose-count rule (poses >= same-offset DynaVINS poses - 1)

- DynaVINS+Y-Cls: 80/80 pass
- DynaVINS+SAVIOR: 80/80 pass
- DynaVINS+O-Dyn+B: 80/80 pass
- DynaVINS+O-Cls+B: 80/80 pass
- DynaVINS+zero-masks: 80/80 pass
- DynaVINS (upstream threads): 80/80 pass
