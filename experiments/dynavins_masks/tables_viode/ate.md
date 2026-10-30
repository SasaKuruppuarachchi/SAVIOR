# DynaVINS + SAVIOR masks (P10), viode, ATE (12 sequences x 10 offsets; failure = ATE > 1 m, capped at 10 m)

## Median ATE [m] ([n] = failures)

| seq | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| parking_lot_none | 0.114 [1] | 0.113 [1] | 0.114 [1] | 0.114 [1] | 0.113 [1] | 0.114 [1] | 0.114 [1] |
| parking_lot_low | 2955.702 [7] | 0.269 [4] | 0.162 [3] | 0.122 [1] | 0.132 [1] | 2955.702 [7] | 2918.051 [7] |
| parking_lot_mid | 2203.548 [7] | 0.151 [2] | 0.138 [2] | 0.117 [1] | 0.113 [1] | 2203.548 [7] | 1839.458 [7] |
| parking_lot_high | 1663.166 [8] | 0.091 [4] | 0.105 [4] | 0.079 | 0.073 | 1663.166 [8] | 2296.226 [8] |
| city_day_none | 0.234 [1] | 0.263 [1] | 0.275 [1] | 0.234 [1] | 0.258 [1] | 0.234 [1] | 0.234 [1] |
| city_day_low | 0.220 [1] | 0.208 [1] | 0.215 [1] | 0.220 | 0.208 | 0.220 [1] | 0.222 [1] |
| city_day_mid | 0.212 | 0.202 | 0.202 | 0.207 | 0.184 | 0.212 | 0.211 |
| city_day_high | 0.262 | 0.276 | 0.312 | 0.274 | 0.255 | 0.262 | 0.265 |
| city_night_none | 0.278 | 0.258 | 0.240 | 0.278 | 0.273 | 0.278 | 0.280 |
| city_night_low | 0.240 | 0.257 | 0.241 | 0.259 | 0.231 | 0.240 | 0.240 |
| city_night_mid | 0.369 | 0.298 | 0.307 | 0.344 | 0.331 | 0.369 | 0.369 |
| city_night_high | 0.217 | 0.208 | 0.214 | 0.186 | 0.193 | 0.217 | 0.217 |

## Failures (ATE > 1 m) per group

| group | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| none | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| low | 8 | 5 | 4 | 1 | 1 | 8 | 8 |
| mid | 7 | 2 | 2 | 1 | 1 | 7 | 7 |
| high | 8 | 4 | 4 | 0 | 0 | 8 | 8 |
| none+low | 10 | 7 | 6 | 3 | 3 | 10 | 10 |
| mid+high | 15 | 6 | 6 | 1 | 1 | 15 | 15 |
| low+mid+high | 23 | 11 | 10 | 2 | 2 | 23 | 23 |
| all | 25 | 13 | 12 | 4 | 4 | 25 | 25 |

## Paired vs DynaVINS (geometric-mean ATE ratio - 1; negative = better; Holm over 4 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+Y-Cls | -3.3 % [-11, +6] p=0.164 H=0.655 16/12<br>clu [-15, +10] p=0.616 H=1 (k=3) | -38.5 % [-62, -9] p=0.011 H=0.0331 19/7<br>clu [-74, -2] p=0.0223 H=0.0892 (k=3) | -53.7 % [-74, -23] p=0.00707 H=0.00707 17/11<br>clu [-88, -1] p=0.0376 H=0.0921 (k=3) | -49.9 % [-76, +2] p=0.374 H=0.747 15/12<br>clu [-89, +5] p=0.456 H=0.912 (k=3) | -22.9 % [-40, -6] p=0.00507 H=0.0203 35/19<br>clu [-53, +1] p=0.0616 H=0.246 (k=6) | -51.8 % [-70, -25] p=0.0101 H=0.0193 32/23<br>clu [-82, -1] p=0.0385 H=0.077 (k=6) | -47.7 % [-63, -27] p=0.000343 H=0.000685 51/30<br>clu [-74, -8] p=0.0031 H=0.0062 (k=9) | -39.1 % [-53, -21] p=0.000214 H=0.000428 67/42<br>clu [-65, -6] p=0.0043 H=0.009 (k=12) |
| DynaVINS+SAVIOR | -0.6 % [-8, +9] p=0.955 H=1 14/14<br>clu [-12, +13] p=0.905 H=1 (k=3) | -43.7 % [-67, -12] p=0.116 H=0.116 17/9<br>clu [-81, +2] p=0.112 H=0.224 (k=3) | -55.5 % [-76, -24] p=0.00106 H=0.00243 19/9<br>clu [-89, -0] p=0.0482 H=0.0921 (k=3) | -47.9 % [-75, +6] p=0.679 H=0.747 13/14<br>clu [-88, +12] p=0.522 H=0.912 (k=3) | -25.2 % [-44, -5] p=0.172 H=0.172 31/23<br>clu [-60, +4] p=0.203 H=0.407 (k=6) | -51.8 % [-70, -24] p=0.00963 H=0.0193 32/23<br>clu [-82, +2] p=0.0727 H=0.077 (k=6) | -49.3 % [-65, -28] p=0.0023 H=0.0023 49/32<br>clu [-76, -6] p=0.0133 H=0.0133 (k=9) | -40.0 % [-55, -22] p=0.00613 H=0.00613 63/46<br>clu [-67, -3] p=0.0185 H=0.0185 (k=12) |
| DynaVINS+O-Dyn+B | +0.0 % [+0, +0] p=1 H=1 0/0<br>clu [+0, +0] p=1 H=1 (k=3) | -62.7 % [-81, -32] p=0.048 H=0.0961 19/10<br>clu [-92, +5] p=0.174 H=0.224 (k=3) | -60.3 % [-79, -30] p=0.000607 H=0.00243 25/4<br>clu [-92, -1] p=0.0307 H=0.0921 (k=3) | -72.0 % [-87, -42] p=0.00172 H=0.00516 23/7<br>clu [-97, -1] p=0.0263 H=0.0789 (k=3) | -39.0 % [-58, -16] p=0.048 H=0.0961 19/10<br>clu [-77, +2] p=0.266 H=0.407 (k=6) | -66.7 % [-80, -46] p=8.46e-06 H=2.54e-05 48/11<br>clu [-91, -3] p=0.001 H=0.003 (k=6) | -65.4 % [-77, -49] p=1.36e-06 H=4.08e-06 67/21<br>clu [-88, -17] p=0.0011 H=0.0033 (k=9) | -54.9 % [-67, -40] p=1.36e-06 H=4.08e-06 67/21<br>clu [-80, -8] p=0.003 H=0.009 (k=12) |
| DynaVINS+O-Cls+B | -1.4 % [-8, +5] p=0.779 H=1 15/13<br>clu [-9, +5] p=0.789 H=1 (k=3) | -64.8 % [-82, -36] p=0.00167 H=0.00667 22/7<br>clu [-92, +1] p=0.0652 H=0.196 (k=3) | -62.1 % [-80, -33] p=0.000669 H=0.00243 23/6<br>clu [-93, -5] p=0.002 H=0.008 (k=3) | -73.6 % [-88, -45] p=0.000313 H=0.00125 24/6<br>clu [-97, -6] p=0.0009 H=0.0036 (k=3) | -41.1 % [-59, -19] p=0.00787 H=0.0236 37/20<br>clu [-78, +1] p=0.0843 H=0.253 (k=6) | -68.3 % [-81, -49] p=2.06e-06 H=8.23e-06 47/12<br>clu [-92, -8] p=0 H=0 (k=6) | -67.2 % [-78, -52] p=1.72e-08 H=6.88e-08 69/19<br>clu [-88, -23] p=0 H=0 (k=9) | -56.8 % [-68, -42] p=7.1e-08 H=2.84e-07 84/32<br>clu [-81, -13] p=0.0001 H=0.0004 (k=12) |

## Paired vs DynaVINS+Y-Cls (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+SAVIOR | +2.8 % [+0, +6] p=0.0426 H=0.0426 10/18<br>clu [+0, +6] p=0.0399 H=0.0399 (k=3) | -8.4 % [-33, +11] p=0.515 H=0.515 12/15<br>clu [-41, +13] p=0.913 H=0.913 (k=3) | -3.8 % [-8, -0] p=0.15 H=0.15 16/12<br>clu [-11, +1] p=0.21 H=0.21 (k=3) | +4.0 % [-0, +9] p=0.0525 H=0.0525 8/18<br>clu [-2, +10] p=0.173 H=0.173 (k=3) | -3.0 % [-17, +7] p=0.0799 H=0.0799 22/33<br>clu [-23, +8] p=0.974 H=0.974 (k=6) | +0.0 % [-3, +3] p=0.689 H=0.689 24/30<br>clu [-5, +5] p=0.957 H=0.957 (k=6) | -2.9 % [-13, +4] p=0.433 H=0.433 36/45<br>clu [-18, +6] p=0.812 H=0.812 (k=9) | -1.5 % [-9, +4] p=0.118 H=0.118 46/63<br>clu [-13, +5] p=0.97 H=0.97 (k=12) |

## Paired vs DynaVINS+O-Cls+B (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+O-Dyn+B | +1.4 % [-5, +8] p=0.779 H=0.779 13/15<br>clu [-5, +10] p=0.789 H=0.789 (k=3) | +5.9 % [-1, +15] p=0.169 H=0.169 11/18<br>clu [-3, +20] p=0.33 H=0.33 (k=3) | +4.7 % [+1, +10] p=0.048 H=0.048 10/19<br>clu [+0, +11] p=0.028 H=0.028 (k=3) | +6.0 % [+1, +12] p=0.0636 H=0.0636 10/20<br>clu [-2, +17] p=0.167 H=0.167 (k=3) | +3.6 % [-1, +9] p=0.232 H=0.232 24/33<br>clu [-2, +12] p=0.304 H=0.304 (k=6) | +5.3 % [+2, +9] p=0.00643 H=0.00643 20/39<br>clu [+1, +11] p=0.0182 H=0.0182 (k=6) | +5.5 % [+2, +9] p=0.00259 H=0.00259 31/57<br>clu [+1, +11] p=0.0141 H=0.0141 (k=9) | +4.5 % [+1, +8] p=0.00607 H=0.00607 44/72<br>clu [+0, +9] p=0.0245 H=0.0245 (k=12) |

## Paired vs DynaVINS (upstream threads) (geometric-mean ATE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS | -0.3 % [-1, +0] p=0.438 H=0.438 12/16<br>clu [-2, +0] p=0.786 H=0.786 (k=3) | +0.4 % [-0, +1] p=0.588 H=0.588 14/8<br>clu [-0, +2] p=0.668 H=0.668 (k=3) | -0.4 % [-1, +0] p=0.601 H=0.601 14/9<br>clu [-2, +0] p=0.534 H=0.534 (k=3) | -0.1 % [-0, +0] p=0.588 H=0.588 8/14<br>clu [-0, +0] p=0.717 H=0.717 (k=3) | +0.1 % [-1, +1] p=0.992 H=0.992 26/24<br>clu [-1, +1] p=0.939 H=0.939 (k=6) | -0.2 % [-1, +0] p=0.858 H=0.858 22/23<br>clu [-1, +0] p=0.47 H=0.47 (k=6) | +0.0 % [-0, +0] p=0.783 H=0.783 36/31<br>clu [-1, +1] p=0.955 H=0.955 (k=9) | -0.1 % [-0, +0] p=0.929 H=0.929 48/47<br>clu [-1, +0] p=0.738 H=0.738 (k=12) |

## Pose-count rule (poses >= same-offset DynaVINS poses - 1)

- DynaVINS+Y-Cls: 120/120 pass
- DynaVINS+SAVIOR: 120/120 pass
- DynaVINS+O-Dyn+B: 120/120 pass
- DynaVINS+O-Cls+B: 120/120 pass
- DynaVINS+zero-masks: 120/120 pass
- DynaVINS (upstream threads): 120/120 pass
