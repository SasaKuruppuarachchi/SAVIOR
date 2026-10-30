# DynaVINS + SAVIOR masks (P10), viode, RPE (12 sequences x 10 offsets; failure = ATE > 1 m, capped at 10 m)

## Median RPE [m] ([n] = failures)

| seq | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| parking_lot_none | 0.064 [1] | 0.065 [1] | 0.064 [1] | 0.064 [1] | 0.067 [1] | 0.064 [1] | 0.064 [1] |
| parking_lot_low | 10000.000 [7] | 0.128 [4] | 0.084 [3] | 0.069 [1] | 0.072 [1] | 10000.000 [7] | 10000.000 [7] |
| parking_lot_mid | 10000.000 [7] | 0.086 [2] | 0.081 [2] | 0.064 [1] | 0.067 [1] | 10000.000 [7] | 10000.000 [7] |
| parking_lot_high | 10000.000 [8] | 0.067 [4] | 0.076 [4] | 0.055 | 0.052 | 10000.000 [8] | 10000.000 [8] |
| city_day_none | 0.143 [1] | 0.136 [1] | 0.141 [1] | 0.143 [1] | 0.113 [1] | 0.143 [1] | 0.142 [1] |
| city_day_low | 0.128 [1] | 0.103 [1] | 0.108 [1] | 0.142 | 0.104 | 0.128 [1] | 0.128 [1] |
| city_day_mid | 0.113 | 0.112 | 0.117 | 0.119 | 0.118 | 0.113 | 0.113 |
| city_day_high | 0.124 | 0.138 | 0.143 | 0.134 | 0.125 | 0.124 | 0.126 |
| city_night_none | 0.111 | 0.110 | 0.110 | 0.111 | 0.110 | 0.111 | 0.112 |
| city_night_low | 0.114 | 0.115 | 0.116 | 0.119 | 0.120 | 0.114 | 0.113 |
| city_night_mid | 0.130 | 0.125 | 0.130 | 0.120 | 0.118 | 0.130 | 0.130 |
| city_night_high | 0.118 | 0.114 | 0.112 | 0.120 | 0.124 | 0.118 | 0.119 |

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

## Paired vs DynaVINS (geometric-mean RPE ratio - 1; negative = better; Holm over 4 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+Y-Cls | -1.4 % [-4, +2] p=0.12 H=0.48 18/10<br>clu [-6, +2] p=0.54 H=1 (k=3) | -40.3 % [-66, -6] p=0.0255 H=0.051 17/8<br>clu [-78, -1] p=0.0335 H=0.101 (k=3) | -56.6 % [-77, -21] p=0.00129 H=0.00387 21/7<br>clu [-91, -1] p=0.0048 H=0.0144 (k=3) | -49.9 % [-78, +5] p=0.386 H=0.773 15/12<br>clu [-89, +11] p=0.365 H=1 (k=3) | -23.3 % [-43, -3] p=0.0104 H=0.0311 35/18<br>clu [-57, -0] p=0.0432 H=0.173 (k=6) | -53.4 % [-72, -24] p=0.00895 H=0.0179 36/19<br>clu [-84, +1] p=0.079 H=0.237 (k=6) | -49.4 % [-65, -27] p=0.000672 H=0.00202 53/27<br>clu [-77, -5] p=0.0093 H=0.0279 (k=9) | -40.2 % [-55, -21] p=0.000232 H=0.000696 71/37<br>clu [-68, -3] p=0.0114 H=0.0342 (k=12) |
| DynaVINS+SAVIOR | -0.2 % [-4, +4] p=0.678 H=1 15/13<br>clu [-6, +5] p=0.95 H=1 (k=3) | -49.4 % [-73, -17] p=0.00794 H=0.0238 18/8<br>clu [-85, -2] p=0.01 H=0.04 (k=3) | -56.0 % [-77, -19] p=0.0662 H=0.0662 16/12<br>clu [-91, +2] p=0.301 H=0.301 (k=3) | -49.0 % [-77, +7] p=0.732 H=0.773 14/13<br>clu [-89, +12] p=0.523 H=1 (k=3) | -28.9 % [-49, -8] p=0.0255 H=0.0509 33/21<br>clu [-66, +1] p=0.0879 H=0.185 (k=6) | -52.7 % [-72, -22] p=0.129 H=0.129 30/25<br>clu [-84, +4] p=0.153 H=0.237 (k=6) | -51.6 % [-67, -29] p=0.00505 H=0.00505 48/33<br>clu [-79, -4] p=0.0194 H=0.0279 (k=9) | -42.0 % [-57, -23] p=0.00798 H=0.00798 63/46<br>clu [-70, -2] p=0.0253 H=0.0342 (k=12) |
| DynaVINS+O-Dyn+B | +0.0 % [+0, +0] p=1 H=1 0/0<br>clu [+0, +0] p=1 H=1 (k=3) | -67.0 % [-85, -36] p=0.149 H=0.149 15/14<br>clu [-94, +3] p=0.172 H=0.172 (k=3) | -65.2 % [-84, -33] p=0.00215 H=0.0043 21/8<br>clu [-95, +2] p=0.0772 H=0.154 (k=3) | -74.0 % [-89, -43] p=0.177 H=0.532 18/12<br>clu [-98, +7] p=0.546 H=1 (k=3) | -42.6 % [-62, -18] p=0.149 H=0.149 15/14<br>clu [-81, +1] p=0.262 H=0.262 (k=6) | -70.0 % [-83, -49] p=0.00229 H=0.00688 39/20<br>clu [-93, +2] p=0.0942 H=0.237 (k=6) | -69.0 % [-80, -53] p=0.000675 H=0.00202 54/34<br>clu [-90, -17] p=0.0118 H=0.0279 (k=9) | -58.5 % [-71, -42] p=0.000675 H=0.00135 54/34<br>clu [-84, -7] p=0.0156 H=0.0342 (k=12) |
| DynaVINS+O-Cls+B | -3.2 % [-8, +1] p=0.274 H=0.822 16/12<br>clu [-12, +5] p=0.534 H=1 (k=3) | -68.5 % [-85, -39] p=0.00107 H=0.00427 21/8<br>clu [-94, +3] p=0.0756 H=0.151 (k=3) | -66.4 % [-84, -36] p=1.84e-05 H=7.36e-05 25/4<br>clu [-95, -7] p=0 H=0 (k=3) | -74.7 % [-89, -44] p=0.0919 H=0.368 17/13<br>clu [-98, +4] p=0.466 H=1 (k=3) | -44.8 % [-63, -21] p=0.00172 H=0.00689 37/20<br>clu [-81, +0] p=0.0617 H=0.185 (k=6) | -70.8 % [-83, -50] p=3.89e-05 H=0.000156 42/17<br>clu [-94, -3] p=0.011 H=0.044 (k=6) | -70.1 % [-81, -54] p=2.12e-07 H=8.48e-07 63/25<br>clu [-91, -21] p=0.0013 H=0.0052 (k=9) | -59.9 % [-71, -45] p=2.4e-07 H=9.6e-07 79/37<br>clu [-84, -11] p=0.0014 H=0.0056 (k=12) |

## Paired vs DynaVINS+Y-Cls (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+SAVIOR | +1.2 % [-1, +4] p=0.522 H=0.522 12/16<br>clu [-2, +5] p=0.453 H=0.453 (k=3) | -15.2 % [-39, +1] p=0.34 H=0.34 16/10<br>clu [-47, +1] p=0.2 H=0.2 (k=3) | +1.2 % [-1, +4] p=0.194 H=0.194 9/19<br>clu [-3, +5] p=0.578 H=0.578 (k=3) | +1.8 % [-1, +5] p=0.19 H=0.19 9/17<br>clu [-2, +5] p=0.276 H=0.276 (k=3) | -7.3 % [-22, +2] p=0.793 H=0.793 28/26<br>clu [-28, +2] p=0.55 H=0.55 (k=6) | +1.5 % [-0, +4] p=0.0648 H=0.0648 18/36<br>clu [-1, +4] p=0.264 H=0.264 (k=6) | -4.4 % [-15, +2] p=0.426 H=0.426 34/46<br>clu [-21, +3] p=0.776 H=0.776 (k=9) | -3.0 % [-11, +2] p=0.316 H=0.316 46/62<br>clu [-16, +2] p=0.859 H=0.859 (k=12) |

## Paired vs DynaVINS+O-Cls+B (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+O-Dyn+B | +3.3 % [-1, +9] p=0.274 H=0.274 12/16<br>clu [-5, +14] p=0.534 H=0.534 (k=3) | +4.8 % [+0, +10] p=0.176 H=0.176 11/18<br>clu [-3, +18] p=0.582 H=0.582 (k=3) | +3.4 % [-0, +7] p=0.495 H=0.495 16/13<br>clu [-3, +12] p=0.466 H=0.466 (k=3) | +2.5 % [-0, +5] p=0.158 H=0.158 11/19<br>clu [-2, +7] p=0.272 H=0.272 (k=3) | +4.0 % [+1, +8] p=0.0913 H=0.0913 23/34<br>clu [-3, +12] p=0.289 H=0.289 (k=6) | +2.9 % [+1, +5] p=0.0953 H=0.0953 27/32<br>clu [-1, +8] p=0.178 H=0.178 (k=6) | +3.5 % [+1, +6] p=0.0338 H=0.0338 38/50<br>clu [-1, +9] p=0.127 H=0.127 (k=9) | +3.5 % [+1, +6] p=0.0191 H=0.0191 50/66<br>clu [-0, +8] p=0.0901 H=0.0901 (k=12) |

## Paired vs DynaVINS (upstream threads) (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | none | low | mid | high | none+low | mid+high | low+mid+high | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS | -0.1 % [-0, +0] p=0.412 H=0.412 14/14<br>clu [-0, +0] p=0.51 H=0.51 (k=3) | +0.2 % [+0, +0] p=0.0587 H=0.0587 7/15<br>clu [+0, +1] p=0.0427 H=0.0427 (k=3) | -0.3 % [-1, +0] p=0.8 H=0.8 13/10<br>clu [-2, +0] p=0.799 H=0.799 (k=3) | -0.4 % [-1, +0] p=0.0391 H=0.0391 15/7<br>clu [-1, +0] p=0.0797 H=0.0797 (k=3) | +0.1 % [-0, +0] p=0.421 H=0.421 21/29<br>clu [-0, +0] p=0.614 H=0.614 (k=6) | -0.4 % [-1, +0] p=0.0973 H=0.0973 28/17<br>clu [-1, +0] p=0.203 H=0.203 (k=6) | -0.2 % [-1, +0] p=0.583 H=0.583 35/32<br>clu [-1, +0] p=0.462 H=0.462 (k=9) | -0.2 % [-0, +0] p=0.385 H=0.385 49/46<br>clu [-1, +0] p=0.378 H=0.378 (k=12) |

## Pose-count rule (poses >= same-offset DynaVINS poses - 1)

- DynaVINS+Y-Cls: 120/120 pass
- DynaVINS+SAVIOR: 120/120 pass
- DynaVINS+O-Dyn+B: 120/120 pass
- DynaVINS+O-Cls+B: 120/120 pass
- DynaVINS+zero-masks: 120/120 pass
- DynaVINS (upstream threads): 120/120 pass
