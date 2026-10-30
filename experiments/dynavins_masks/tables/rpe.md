# DynaVINS + SAVIOR masks (P10), t1, RPE (8 sequences x 10 offsets; failure = ATE > 2 m, capped at 10 m)

## Median RPE [m] ([n] = failures)

| seq | DynaVINS | DynaVINS+Y-Cls | DynaVINS+SAVIOR | DynaVINS+O-Dyn+B | DynaVINS+O-Cls+B | DynaVINS+zero-masks | DynaVINS (upstream threads) |
|---|--:|--:|--:|--:|--:|--:|--:|
| aisles_t1_L0 | 0.039 | 0.043 | 0.039 | 0.039 | 0.060 | 0.039 | 0.039 |
| aisles_t1_L1 | 0.041 | 0.048 | 0.040 | 0.041 | 0.063 | 0.041 | 0.041 |
| aisles_t1_L2 | 0.038 | 0.051 | 0.043 | 0.042 | 0.067 | 0.038 | 0.038 |
| aisles_t1_L3 | 0.042 | 0.044 | 0.041 | 0.038 | 0.069 | 0.042 | 0.042 |
| hall_t1_L0 | 0.039 | 0.055 | 0.040 | 0.039 | 0.056 | 0.039 | 0.038 |
| hall_t1_L1 | 0.039 | 0.054 | 0.036 | 0.034 | 0.055 | 0.039 | 0.039 |
| hall_t1_L2 | 0.038 | 0.049 | 0.033 | 0.033 | 0.050 | 0.038 | 0.038 |
| hall_t1_L3 | 0.046 | 0.057 | 0.047 | 0.035 | 0.056 | 0.046 | 0.046 |

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

## Paired vs DynaVINS (geometric-mean RPE ratio - 1; negative = better; Holm over 4 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+Y-Cls | +24.7 % [+17, +33] p=5.72e-06 H=1.72e-05 1/19<br>clu [+8, +43] p=0 H=0 (k=2) | +27.0 % [+19, +36] p=1.91e-05 H=5.72e-05 1/19<br>clu [+14, +46] p=0 H=0 (k=2) | +30.7 % [+25, +36] p=1.91e-06 H=7.63e-06 0/20<br>clu [+23, +36] p=0 H=0 (k=2) | +12.9 % [+4, +24] p=0.00831 H=0.0166 4/16<br>clu [+3, +32] p=0.0022 H=0.0044 (k=2) | +25.8 % [+20, +32] p=2.49e-10 H=7.48e-10 2/38<br>clu [+13, +41] p=0 H=0 (k=4) | +21.5 % [+15, +28] p=2.36e-08 H=7.09e-08 4/36<br>clu [+9, +33] p=0 H=0 (k=4) | +22.5 % [+4, +44] p=0.0645 H=0.129 2/8<br>clu [+4, +44] p=0.0135 H=0.027 (k=1) | +23.6 % [+19, +28] p=4.73e-13 H=1.42e-12 6/74<br>clu [+15, +33] p=0 H=0 (k=8) |
| DynaVINS+SAVIOR | +2.5 % [-0, +6] p=0.143 H=0.286 7/13<br>clu [-1, +7] p=0.255 H=0.511 (k=2) | -5.3 % [-9, -1] p=0.0362 H=0.0725 14/6<br>clu [-11, -1] p=0.0191 H=0.0382 (k=2) | -1.6 % [-8, +5] p=0.648 H=1 8/12<br>clu [-17, +14] p=0.717 H=1 (k=2) | -0.5 % [-7, +6] p=0.841 H=0.841 11/9<br>clu [-7, +8] p=0.748 H=0.748 (k=2) | -1.4 % [-4, +1] p=0.493 H=0.493 21/19<br>clu [-7, +3] p=0.582 H=0.582 (k=4) | -1.1 % [-6, +4] p=0.963 H=0.963 19/21<br>clu [-11, +9] p=0.867 H=0.867 (k=4) | +1.1 % [-12, +14] p=0.695 H=0.695 3/7<br>clu [-12, +15] p=0.852 H=0.852 (k=1) | -1.3 % [-4, +2] p=0.741 H=0.741 40/40<br>clu [-7, +4] p=0.659 H=0.659 (k=8) |
| DynaVINS+O-Dyn+B | +0.0 % [+0, +0] p=1 H=1 0/0<br>clu [+0, +0] p=1 H=1 (k=2) | -4.6 % [-8, -1] p=0.0826 H=0.0826 12/8<br>clu [-10, -0] p=0.0492 H=0.0492 (k=2) | +1.0 % [-5, +8] p=0.784 H=1 9/11<br>clu [-13, +17] p=0.818 H=1 (k=2) | -15.5 % [-21, -9] p=0.000322 H=0.000967 18/2<br>clu [-26, -7] p=0 H=0 (k=2) | -2.3 % [-4, -0] p=0.0826 H=0.165 12/8<br>clu [-6, +0] p=0.19 H=0.381 (k=4) | -7.6 % [-13, -2] p=0.0153 H=0.0305 27/13<br>clu [-19, +7] p=0.295 H=0.59 (k=4) | -21.8 % [-30, -11] p=0.00977 H=0.0293 8/2<br>clu [-30, -11] p=0.0001 H=0.0003 (k=1) | -5.0 % [-8, -2] p=0.00294 H=0.00588 39/21<br>clu [-12, +2] p=0.166 H=0.332 (k=8) |
| DynaVINS+O-Cls+B | +47.5 % [+42, +52] p=1.91e-06 H=7.63e-06 0/20<br>clu [+39, +55] p=0 H=0 (k=2) | +47.4 % [+41, +53] p=1.91e-06 H=7.63e-06 0/20<br>clu [+40, +54] p=0 H=0 (k=2) | +51.8 % [+41, +63] p=1.91e-06 H=7.63e-06 0/20<br>clu [+27, +78] p=0 H=0 (k=2) | +42.8 % [+32, +54] p=1.91e-06 H=7.63e-06 0/20<br>clu [+19, +66] p=0 H=0 (k=2) | +47.4 % [+43, +51] p=1.82e-12 H=7.28e-12 0/40<br>clu [+42, +53] p=0 H=0 (k=4) | +47.2 % [+39, +55] p=1.82e-12 H=7.28e-12 0/40<br>clu [+27, +71] p=0 H=0 (k=4) | +23.9 % [+14, +36] p=0.00195 H=0.00781 0/10<br>clu [+14, +36] p=0 H=0 (k=1) | +47.3 % [+43, +52] p=7.85e-15 H=3.14e-14 0/80<br>clu [+37, +59] p=0 H=0 (k=8) |

## Paired vs DynaVINS+Y-Cls (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+SAVIOR | -17.8 % [-22, -14] p=1.91e-06 H=1.91e-06 20/0<br>clu [-27, -8] p=0 H=0 (k=2) | -25.4 % [-30, -20] p=1.91e-06 H=1.91e-06 20/0<br>clu [-36, -16] p=0 H=0 (k=2) | -24.7 % [-29, -20] p=1.91e-06 H=1.91e-06 20/0<br>clu [-34, -15] p=0 H=0 (k=2) | -11.9 % [-18, -7] p=0.000134 H=0.000134 18/2<br>clu [-21, -5] p=0 H=0 (k=2) | -21.7 % [-25, -18] p=1.82e-12 H=1.82e-12 40/0<br>clu [-31, -13] p=0 H=0 (k=4) | -18.6 % [-23, -15] p=1.6e-10 H=1.6e-10 38/2<br>clu [-28, -9] p=0 H=0 (k=4) | -17.5 % [-26, -9] p=0.00586 H=0.00586 9/1<br>clu [-26, -9] p=0.0001 H=0.0001 (k=1) | -20.1 % [-23, -17] p=1.67e-14 H=1.67e-14 78/2<br>clu [-27, -13] p=0 H=0 (k=8) |

## Paired vs DynaVINS+O-Cls+B (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS+O-Dyn+B | -32.2 % [-34, -30] p=1.91e-06 H=1.91e-06 20/0<br>clu [-35, -28] p=0 H=0 (k=2) | -35.3 % [-38, -32] p=1.91e-06 H=1.91e-06 20/0<br>clu [-38, -32] p=0 H=0 (k=2) | -33.5 % [-36, -31] p=1.91e-06 H=1.91e-06 20/0<br>clu [-36, -30] p=0 H=0 (k=2) | -40.8 % [-44, -37] p=1.91e-06 H=1.91e-06 20/0<br>clu [-45, -34] p=0 H=0 (k=2) | -33.7 % [-36, -32] p=1.82e-12 H=1.82e-12 40/0<br>clu [-36, -31] p=0 H=0 (k=4) | -37.2 % [-40, -35] p=1.82e-12 H=1.82e-12 40/0<br>clu [-42, -33] p=0 H=0 (k=4) | -36.9 % [-43, -30] p=0.00195 H=0.00195 10/0<br>clu [-43, -30] p=0 H=0 (k=1) | -35.5 % [-37, -34] p=7.85e-15 H=7.85e-15 80/0<br>clu [-39, -33] p=0 H=0 (k=8) |

## Paired vs DynaVINS (upstream threads) (geometric-mean RPE ratio - 1; negative = better; Holm over 1 method(s) per group)

Cells: change [run-bootstrap 95 % CI] Wilcoxon p / Holm, wins/losses; second line: sequence-cluster bootstrap 95 % CI, bootstrap p / Holm (n_seq sequences).

| method | L0 | L1 | L2 | L3 | L0+L1 | L2+L3 | hall_L3 | all |
|---|---|---|---|---|---|---|---|---|
| DynaVINS | +0.2 % [-0, +1] p=0.571 H=0.571 10/10<br>clu [-0, +1] p=0.418 H=0.418 (k=2) | -0.3 % [-1, +0] p=0.571 H=0.571 13/7<br>clu [-1, +0] p=0.389 H=0.389 (k=2) | -0.5 % [-1, -0] p=0.368 H=0.368 12/8<br>clu [-2, +0] p=0.192 H=0.192 (k=2) | -0.2 % [-1, +0] p=0.409 H=0.409 11/9<br>clu [-1, +0] p=0.44 H=0.44 (k=2) | -0.0 % [-1, +0] p=0.931 H=0.931 23/17<br>clu [-1, +1] p=0.856 H=0.856 (k=4) | -0.3 % [-1, -0] p=0.206 H=0.206 23/17<br>clu [-1, +0] p=0.142 H=0.142 (k=4) | -0.1 % [-1, +1] p=0.625 H=0.625 6/4<br>clu [-1, +1] p=0.813 H=0.813 (k=1) | -0.2 % [-1, +0] p=0.345 H=0.345 46/34<br>clu [-1, +0] p=0.344 H=0.344 (k=8) |

## Pose-count rule (poses >= same-offset DynaVINS poses - 1)

- DynaVINS+Y-Cls: 80/80 pass
- DynaVINS+SAVIOR: 80/80 pass
- DynaVINS+O-Dyn+B: 80/80 pass
- DynaVINS+O-Cls+B: 80/80 pass
- DynaVINS+zero-masks: 80/80 pass
- DynaVINS (upstream threads): 80/80 pass
