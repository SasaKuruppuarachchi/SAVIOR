# Task E: final SAVIOR (sens_fix1, COCO instantiation) and Y-Cls on OpenLORIS + uHumans2, ORIGINAL back-end (ATE)

Cells: RUN level: geometric-mean ratio - 1 [iid bootstrap CI], Holm-adjusted Wilcoxon p (within family x group), wins/losses of the paired offsets / SEQUENCE level (stats_v3): exp(mean of per-sequence mean log ratios) - 1 [two-stage cluster bootstrap CI], exact sign-flip p (sf; minimum attainable 2/2^k), LMM p, sequences better/worse. Negative = first method better. Single-sequence groups have no sequence-level statistic. P2offsets = runs 1-3 (start offsets 0.0/0.2/0.4 s, the P2 protocol).

## Median ATE [m] per sequence (n runs; [k] failures > 1 m)

| seq | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | oracle person |
|---|--:|--:|--:|--:|--:|
| openloris_cafe1-1 | 0.1730 (n=10) | 0.1730 (n=10) | 0.1690 (n=10) | 0.1795 (n=10) | - |
| openloris_cafe1-2 | 0.1588 (n=10) | 0.1484 (n=10) | 0.1643 (n=10) | 0.1580 (n=10) | - |
| openloris_office1-1 | 0.0163 (n=10) | 0.0163 (n=10) | 0.0161 (n=10) | 0.0176 (n=10) | - |
| openloris_office1-2 | 0.0279 (n=10) | 0.0259 (n=10) | 0.0259 (n=10) | 0.0234 (n=10) | - |
| openloris_office1-3 | 0.0074 (n=10) | 0.0075 (n=10) | 0.0075 (n=10) | 0.0075 (n=10) | - |
| openloris_office1-4 | 0.0247 (n=10) | 0.0267 (n=10) | 0.0238 (n=10) | 0.0199 (n=10) | - |
| openloris_office1-5 | 0.0484 (n=10) | 0.0462 (n=10) | 0.0397 (n=10) | 0.0433 (n=10) | - |
| openloris_office1-6 | 0.0290 (n=10) | 0.0290 (n=10) | 0.0255 (n=10) | 0.0256 (n=10) | - |
| openloris_office1-7 | 0.0401 (n=10) | 0.0408 (n=10) | 0.0340 (n=10) | 0.0333 (n=10) | - |
| uhumans2_office_s1_00h | 0.2767 (n=5) | - | 0.4049 (n=5) | 0.3116 (n=5) | - |
| uhumans2_office_s1_06h | 0.2571 (n=10) | 0.3000 (n=10) | 0.2751 (n=10) | 0.3144 (n=10) | 0.3276 (n=10) |
| uhumans2_office_s1_12h | 0.3642 (n=10) | 0.3045 (n=10) | 0.3996 (n=10) | 0.3756 (n=10) | 0.3657 (n=10) |

## E_vs_openvins

| comparison | group | result |
|---|---|---|
| SAVIOR vs OpenVINS | openloris_heldout | **-8.5 % [-14, -3] H=0.016 49/31 / seq -8.5 % [-17, -0] sf=0.094 lmm=0.074 5/3** |
| SAVIOR vs OpenVINS | openloris_heldout_P2offsets | **-19.9 % [-31, -9] H=0.0022 18/6 / seq -19.9 % [-36, -4] sf=0.062 lmm=0.074 6/2** |
| SAVIOR vs OpenVINS | openloris_cafe1-1 | +3.0 % [-4, +11] H=1 4/6 |
| SAVIOR vs OpenVINS | openloris_people | **-10.2 % [-17, -4] H=0.023 25/15 / seq -10.2 % [-21, -0] sf=0.25 lmm=0.16 3/1** |
| SAVIOR vs OpenVINS | openloris_all | **-7.3 % [-12, -2] H=0.037 53/37 / seq -7.3 % [-16, +1] sf=0.098 lmm=0.092 5/4** |
| SAVIOR vs OpenVINS | uhumans2_00h | -9.0 % [-35, +31] H=1 3/2 |
| SAVIOR vs OpenVINS | uhumans2_06h | +10.3 % [-36, +75] H=1 5/5 |
| SAVIOR vs OpenVINS | uhumans2_12h | -3.6 % [-28, +28] H=1 5/5 |
| SAVIOR vs OpenVINS | uhumans2_06h+12h | +3.1 % [-23, +36] H=1 10/10 / seq +3.1 % [-23, +41] sf=1 lmm=0.87 1/1 |
| SAVIOR vs OpenVINS | uhumans2_all | +0.6 % [-22, +27] H=1 13/12 / seq -1.1 % [-22, +27] sf=1 lmm=0.97 2/1 |
| Y-Cls vs OpenVINS | openloris_heldout | **-4.7 % [-9, -1] H=0.021 49/31 / seq -4.7 % [-11, +1] sf=0.11 lmm=0.12 5/3** |
| Y-Cls vs OpenVINS | openloris_heldout_P2offsets | -6.2 % [-13, +0] H=0.092 16/8 / seq -6.2 % [-16, +3] sf=0.26 lmm=0.23 5/3 |
| Y-Cls vs OpenVINS | openloris_cafe1-1 | -2.7 % [-10, +3] H=1 5/5 |
| Y-Cls vs OpenVINS | openloris_people | **-7.3 % [-14, -1] H=0.041 27/13 / seq -7.3 % [-18, +2] sf=0.5 lmm=0.25 2/2** |
| Y-Cls vs OpenVINS | openloris_all | **-4.5 % [-8, -1] H=0.037 54/36 / seq -4.5 % [-10, +1] sf=0.066 lmm=0.095 6/3** |
| Y-Cls vs OpenVINS | uhumans2_00h | +13.3 % [-24, +57] H=1 1/4 |
| Y-Cls vs OpenVINS | uhumans2_06h | +1.7 % [-29, +36] H=1 3/7 |
| Y-Cls vs OpenVINS | uhumans2_12h | +3.0 % [-25, +39] H=1 4/6 |
| Y-Cls vs OpenVINS | uhumans2_06h+12h | +2.3 % [-19, +26] H=1 7/13 / seq +2.3 % [-19, +26] sf=0.5 lmm=0.88 0/2 |
| Y-Cls vs OpenVINS | uhumans2_all | +4.5 % [-15, +26] H=1 8/17 / seq +5.9 % [-14, +28] sf=0.25 lmm=0.71 0/3 |
| oracle person vs OpenVINS | uhumans2_06h | +10.5 % [-28, +58] H=1 5/5 |
| oracle person vs OpenVINS | uhumans2_12h | +4.6 % [-24, +43] H=1 4/6 |
| oracle person vs OpenVINS | uhumans2_06h+12h | +7.5 % [-17, +36] H=1 9/11 / seq +7.5 % [-17, +37] sf=0.5 lmm=0.68 0/2 |
| oracle person vs OpenVINS | uhumans2_all | +7.5 % [-17, +36] H=1 9/11 / seq +7.5 % [-17, +37] sf=0.5 lmm=0.68 0/2 |

## E_savior_vs_ycls

| comparison | group | result |
|---|---|---|
| SAVIOR vs Y-Cls | openloris_heldout | -4.0 % [-9, +1] H=0.088 49/31 / seq -4.0 % [-12, +3] sf=0.29 lmm=0.28 6/2 |
| SAVIOR vs Y-Cls | openloris_heldout_P2offsets | **-14.6 % [-26, -5] H=0.012 17/7 / seq -14.6 % [-30, -1] sf=0.094 lmm=0.093 5/3** |
| SAVIOR vs Y-Cls | openloris_cafe1-1 | +5.8 % [-3, +15] H=0.23 4/6 |
| SAVIOR vs Y-Cls | openloris_people | -3.1 % [-9, +3] H=0.27 23/17 / seq -3.1 % [-11, +4] sf=0.38 lmm=0.4 3/1 |
| SAVIOR vs Y-Cls | openloris_all | -2.9 % [-8, +1] H=0.22 53/37 / seq -2.9 % [-10, +4] sf=0.39 lmm=0.39 6/3 |
| SAVIOR vs Y-Cls | uhumans2_00h | -19.7 % [-35, -3] H=0.062 5/0 |
| SAVIOR vs Y-Cls | uhumans2_06h | +8.5 % [-16, +42] H=0.85 6/4 |
| SAVIOR vs Y-Cls | uhumans2_12h | -6.5 % [-20, +7] H=0.62 5/5 |
| SAVIOR vs Y-Cls | uhumans2_06h+12h | +0.7 % [-13, +18] H=0.78 11/9 / seq +0.7 % [-14, +23] sf=1 lmm=0.94 1/1 |
| SAVIOR vs Y-Cls | uhumans2_all | -3.7 % [-15, +11] H=0.34 16/9 / seq -6.6 % [-22, +13] sf=0.75 lmm=0.64 2/1 |

## E_vs_empty_mask

| comparison | group | result |
|---|---|---|
| SAVIOR vs SAVIOR-none | openloris_heldout | **-7.5 % [-13, -2] H=0.041 44/36 / seq -7.5 % [-16, +1] sf=0.13 lmm=0.12 6/2** |
| SAVIOR vs SAVIOR-none | openloris_heldout_P2offsets | **-19.1 % [-30, -9] H=0.0037 16/8 / seq -19.1 % [-34, -4] sf=0.062 lmm=0.048 6/2** |
| SAVIOR vs SAVIOR-none | openloris_cafe1-1 | +3.2 % [-3, +11] H=1 4/6 |
| SAVIOR vs SAVIOR-none | openloris_people | -7.5 % [-15, +1] H=0.12 23/17 / seq -7.5 % [-20, +5] sf=0.25 lmm=0.32 3/1 |
| SAVIOR vs SAVIOR-none | openloris_all | -6.4 % [-11, -1] H=0.079 48/42 / seq -6.4 % [-15, +2] sf=0.16 lmm=0.14 6/3 |
| SAVIOR vs SAVIOR-none | uhumans2_06h | +12.2 % [-24, +64] H=1 5/5 |
| SAVIOR vs SAVIOR-none | uhumans2_12h | +13.7 % [-8, +41] H=0.39 5/5 |
| SAVIOR vs SAVIOR-none | uhumans2_06h+12h | +13.0 % [-9, +40] H=0.34 10/10 / seq +13.0 % [-11, +41] sf=0.5 lmm=0.48 0/2 |
| SAVIOR vs SAVIOR-none | uhumans2_all | +13.0 % [-9, +40] H=0.34 10/10 / seq +13.0 % [-11, +41] sf=0.5 lmm=0.48 0/2 |
| Y-Cls vs SAVIOR-none | openloris_heldout | -3.7 % [-8, +0] H=0.072 43/37 / seq -3.7 % [-10, +2] sf=0.16 lmm=0.17 4/4 |
| Y-Cls vs SAVIOR-none | openloris_heldout_P2offsets | -5.2 % [-10, -0] H=0.1 13/11 / seq -5.2 % [-13, +3] sf=0.25 lmm=0.26 5/3 |
| Y-Cls vs SAVIOR-none | openloris_cafe1-1 | -2.4 % [-8, +3] H=1 5/5 |
| Y-Cls vs SAVIOR-none | openloris_people | -4.5 % [-12, +3] H=0.18 24/16 / seq -4.5 % [-15, +5] sf=0.5 lmm=0.42 2/2 |
| Y-Cls vs SAVIOR-none | openloris_all | -3.6 % [-7, +0] H=0.079 48/42 / seq -3.6 % [-9, +1] sf=0.11 lmm=0.13 5/4 |
| Y-Cls vs SAVIOR-none | uhumans2_06h | +3.4 % [-18, +31] H=1 4/6 |
| Y-Cls vs SAVIOR-none | uhumans2_12h | +21.6 % [-1, +48] H=0.39 3/7 |
| Y-Cls vs SAVIOR-none | uhumans2_06h+12h | +12.1 % [-4, +31] H=0.34 7/13 / seq +12.1 % [-8, +35] sf=0.5 lmm=0.4 0/2 |
| Y-Cls vs SAVIOR-none | uhumans2_all | +12.1 % [-4, +31] H=0.34 7/13 / seq +12.1 % [-8, +35] sf=0.5 lmm=0.4 0/2 |
| oracle person vs SAVIOR-none | uhumans2_06h | +12.4 % [-14, +43] H=1 4/6 |
| oracle person vs SAVIOR-none | uhumans2_12h | +23.4 % [-4, +58] H=0.39 3/7 |
| oracle person vs SAVIOR-none | uhumans2_06h+12h | +17.8 % [-2, +40] H=0.34 7/13 / seq +17.8 % [-3, +42] sf=0.5 lmm=0.33 0/2 |
| oracle person vs SAVIOR-none | uhumans2_all | +17.8 % [-2, +40] H=0.34 7/13 / seq +17.8 % [-3, +42] sf=0.5 lmm=0.33 0/2 |

## E_control

| comparison | group | result |
|---|---|---|
| SAVIOR-none vs OpenVINS | openloris_heldout | -1.1 % [-5, +2] H=0.47 27/23 / seq -1.1 % [-6, +3] sf=0.73 lmm=0.59 3/5 |
| SAVIOR-none vs OpenVINS | openloris_heldout_P2offsets | -1.0 % [-7, +4] H=0.98 9/6 / seq -1.0 % [-10, +5] sf=0.95 lmm=0.77 2/5 |
| SAVIOR-none vs OpenVINS | openloris_cafe1-1 | -0.3 % [-2, +1] H=0.69 4/2 |
| SAVIOR-none vs OpenVINS | openloris_people | -2.9 % [-9, +1] H=0.93 7/8 / seq -2.9 % [-11, +1] sf=0.5 lmm=0.38 2/2 |
| SAVIOR-none vs OpenVINS | openloris_all | -1.0 % [-5, +2] H=0.4 31/25 / seq -1.0 % [-6, +2] sf=0.71 lmm=0.58 4/5 |
| SAVIOR-none vs OpenVINS | uhumans2_06h | -1.7 % [-19, +20] H=1 5/5 |
| SAVIOR-none vs OpenVINS | uhumans2_12h | -15.2 % [-30, +1] H=0.28 7/3 |
| SAVIOR-none vs OpenVINS | uhumans2_06h+12h | -8.7 % [-20, +5] H=0.43 12/8 / seq -8.7 % [-23, +8] sf=0.5 lmm=0.43 2/0 |
| SAVIOR-none vs OpenVINS | uhumans2_all | -8.7 % [-20, +5] H=0.43 12/8 / seq -8.7 % [-23, +8] sf=0.5 lmm=0.43 2/0 |

Invalid runs excluded pairwise (no): openloris_cafe1-1/e_savior_none/run_10, openloris_cafe1-2/e_sens_fix1/run_01, openloris_office1-2/e_sens_fix1/run_02, openloris_office1-5/e_savior_none/run_09, openloris_office1-6/e_yolo_naive/run_07, openloris_office1-7/e_yolo_naive/run_05, uhumans2_office_s1_00h/e_sens_fix1/run_03, uhumans2_office_s1_06h/e_sens_fix1/run_03

Reproduction of earlier OpenVINS runs (same original estimator config, same start offset, trajectory md5): p2: 11/36 identical, p4: 19/60 identical, p7/noharm: 4/20 identical, p3a: 0/25 identical
