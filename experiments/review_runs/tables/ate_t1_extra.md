# t1 (tuning split), descriptive: vs OV-chi2 x0.25 (selected on these data)

| comparison | group | run level gm [CI], Wilcoxon p, W/L | seq level [two-stage CI], sign-flip p |
|---|---|---|---|
| sens_fix1 vs ovchi_025 | L0+L1 | +31.6 % [+19, +46] p=6.9e-06 8/32 | +31.6 % [+15, +52] sf=0.12 |
| sens_fix1 vs ovchi_025 | L2+L3 | -31.9 % [-59, +2] p=0.49 16/24 | -31.9 % [-77, +30] sf=0.75 |
| sens_fix1 vs ovchi_025 | all | -5.3 % [-27, +18] p=0.00076 24/56 | -5.3 % [-49, +36] sf=0.98 |
| yolo_naive vs ovchi_025 | L0+L1 | +92.3 % [+61, +154] p=1.8e-12 0/40 | +92.3 % [+59, +186] sf=0.12 |
| yolo_naive vs ovchi_025 | L2+L3 | -1.9 % [-37, +43] p=0.0035 9/31 | -1.9 % [-57, +60] sf=1 |
| yolo_naive vs ovchi_025 | all | +37.3 % [+6, +75] p=1.9e-09 9/71 | +37.3 % [-17, +101] sf=0.17 |
| p7_nb vs ovchi_025 | L0+L1 | +42.1 % [+28, +58] p=8.7e-07 7/33 | +42.1 % [+27, +60] sf=0.12 |
| p7_nb vs ovchi_025 | L2+L3 | -31.5 % [-57, +1] p=0.88 18/22 | -31.5 % [-73, +23] sf=0.75 |
| p7_nb vs ovchi_025 | all | -1.3 % [-23, +22] p=0.0017 25/55 | -1.3 % [-44, +40] sf=1 |
