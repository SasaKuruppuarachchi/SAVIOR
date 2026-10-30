# Task E: final SAVIOR (sens_fix1, COCO instantiation) and Y-Cls on OpenLORIS + uHumans2, ORIGINAL back-end (ATE)

Cells: RUN level: geometric-mean ratio - 1 [iid bootstrap CI], Holm-adjusted Wilcoxon p (within family x group), wins/losses of the paired offsets / SEQUENCE level (stats_v3): exp(mean of per-sequence mean log ratios) - 1 [two-stage cluster bootstrap CI], exact sign-flip p (sf; minimum attainable 2/2^k), LMM p, sequences better/worse. Negative = first method better. Single-sequence groups have no sequence-level statistic. P2offsets = runs 1-3 (start offsets 0.0/0.2/0.4 s, the P2 protocol).

## Median ATE [m] per sequence (n runs; [k] failures > 1 m)

| seq | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | oracle person |
|---|--:|--:|--:|--:|--:|
| openloris_cafe1-1 | 0.1730 (n=10) | 0.1718 (n=9) | 0.1690 (n=10) | 0.1795 (n=10) | - |
| openloris_cafe1-2 | 0.1588 (n=10) | 0.1484 (n=10) | 0.1643 (n=10) | 0.1576 (n=9) | - |
| openloris_office1-1 | 0.0163 (n=10) | 0.0163 (n=10) | 0.0161 (n=10) | 0.0176 (n=10) | - |
| openloris_office1-2 | 0.0279 (n=10) | 0.0259 (n=10) | 0.0259 (n=10) | 0.0245 (n=9) | - |
| openloris_office1-3 | 0.0074 (n=10) | 0.0075 (n=10) | 0.0075 (n=10) | 0.0075 (n=10) | - |
| openloris_office1-4 | 0.0247 (n=10) | 0.0267 (n=10) | 0.0238 (n=10) | 0.0199 (n=10) | - |
| openloris_office1-5 | 0.0484 (n=10) | 0.0476 (n=9) | 0.0397 (n=10) | 0.0433 (n=10) | - |
| openloris_office1-6 | 0.0290 (n=10) | 0.0290 (n=10) | 0.0258 (n=9) | 0.0256 (n=10) | - |
| openloris_office1-7 | 0.0401 (n=10) | 0.0408 (n=10) | 0.0350 (n=9) | 0.0333 (n=10) | - |
| uhumans2_office_s1_00h | 0.2767 (n=5) | - | 0.4049 (n=5) | 0.3309 (n=4) | - |
| uhumans2_office_s1_06h | 0.2571 (n=10) | 0.3000 (n=10) | 0.2751 (n=10) | 0.3272 (n=9) | 0.3276 (n=10) |
| uhumans2_office_s1_12h | 0.3642 (n=10) | 0.3045 (n=10) | 0.3996 (n=10) | 0.3756 (n=10) | 0.3657 (n=10) |

## E_vs_openvins

| comparison | group | result |
|---|---|---|
| SAVIOR vs OpenVINS | openloris_heldout | **-7.3 % [-12, -3] H=0.017 48/30 / seq -7.2 % [-15, +1] sf=0.12 lmm=0.1 6/2** |
| SAVIOR vs OpenVINS | openloris_heldout_P2offsets | **-16.9 % [-25, -9] H=0.0014 17/5 / seq -17.0 % [-30, -4] sf=0.055 lmm=0.053 6/2** |
| SAVIOR vs OpenVINS | openloris_cafe1-1 | +3.0 % [-4, +11] H=1 4/6 |
| SAVIOR vs OpenVINS | openloris_people | **-10.8 % [-17, -4] H=0.015 25/14 / seq -10.5 % [-21, -1] sf=0.12 lmm=0.14 4/0** |
| SAVIOR vs OpenVINS | openloris_all | **-6.2 % [-10, -2] H=0.039 52/36 / seq -6.1 % [-14, +1] sf=0.14 lmm=0.12 6/3** |
| SAVIOR vs OpenVINS | uhumans2_00h | +3.6 % [-22, +50] H=1 2/2 |
| SAVIOR vs OpenVINS | uhumans2_06h | +18.3 % [-34, +90] H=1 4/5 |
| SAVIOR vs OpenVINS | uhumans2_12h | -3.6 % [-28, +28] H=1 5/5 |
| SAVIOR vs OpenVINS | uhumans2_06h+12h | +6.2 % [-22, +42] H=1 9/10 / seq +6.8 % [-22, +52] sf=1 lmm=0.77 1/1 |
| SAVIOR vs OpenVINS | uhumans2_all | +5.7 % [-18, +35] H=1 11/12 / seq +5.7 % [-17, +38] sf=0.75 lmm=0.71 1/2 |
| Y-Cls vs OpenVINS | openloris_heldout | **-3.7 % [-8, +0] H=0.044 47/31 / seq -3.7 % [-10, +2] sf=0.17 lmm=0.16 5/3** |
| Y-Cls vs OpenVINS | openloris_heldout_P2offsets | -6.2 % [-13, +0] H=0.092 16/8 / seq -6.2 % [-16, +3] sf=0.26 lmm=0.23 5/3 |
| Y-Cls vs OpenVINS | openloris_cafe1-1 | -2.7 % [-10, +3] H=1 5/5 |
| Y-Cls vs OpenVINS | openloris_people | -5.5 % [-11, +1] H=0.094 25/13 / seq -5.4 % [-15, +4] sf=0.5 lmm=0.35 2/2 |
| Y-Cls vs OpenVINS | openloris_all | -3.6 % [-7, +0] H=0.05 52/36 / seq -3.6 % [-9, +1] sf=0.11 lmm=0.13 6/3 |
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
| SAVIOR vs Y-Cls | openloris_heldout | **-3.5 % [-7, +0] H=0.046 48/28 / seq -3.7 % [-10, +3] sf=0.27 lmm=0.3 6/2** |
| SAVIOR vs Y-Cls | openloris_heldout_P2offsets | **-11.1 % [-18, -5] H=0.011 16/6 / seq -10.2 % [-21, -0] sf=0.12 lmm=0.12 5/3** |
| SAVIOR vs Y-Cls | openloris_cafe1-1 | +5.8 % [-3, +15] H=0.23 4/6 |
| SAVIOR vs Y-Cls | openloris_people | -5.4 % [-11, -0] H=0.093 23/14 / seq -5.6 % [-14, +1] sf=0.25 lmm=0.25 3/1 |
| SAVIOR vs Y-Cls | openloris_all | -2.4 % [-6, +1] H=0.14 52/34 / seq -2.7 % [-9, +4] sf=0.39 lmm=0.42 6/3 |
| SAVIOR vs Y-Cls | uhumans2_00h | -24.0 % [-38, -7] H=0.12 4/0 |
| SAVIOR vs Y-Cls | uhumans2_06h | +10.9 % [-16, +48] H=0.73 5/4 |
| SAVIOR vs Y-Cls | uhumans2_12h | -6.5 % [-20, +7] H=0.62 5/5 |
| SAVIOR vs Y-Cls | uhumans2_06h+12h | +1.4 % [-13, +19] H=0.89 10/9 / seq +1.9 % [-14, +27] sf=1 lmm=0.89 1/1 |
| SAVIOR vs Y-Cls | uhumans2_all | -3.6 % [-16, +12] H=0.43 14/9 / seq -7.6 % [-25, +15] sf=0.75 lmm=0.67 2/1 |

## E_vs_empty_mask

| comparison | group | result |
|---|---|---|
| SAVIOR vs SAVIOR-none | openloris_heldout | **-7.4 % [-12, -3] H=0.022 43/34 / seq -7.4 % [-15, +0] sf=0.12 lmm=0.11 6/2** |
| SAVIOR vs SAVIOR-none | openloris_heldout_P2offsets | **-16.1 % [-23, -9] H=0.0028 15/7 / seq -15.0 % [-27, -3] sf=0.031 lmm=0.068 6/2** |
| SAVIOR vs SAVIOR-none | openloris_cafe1-1 | +4.9 % [-2, +12] H=0.72 3/6 |
| SAVIOR vs SAVIOR-none | openloris_people | **-10.4 % [-17, -4] H=0.033 23/15 / seq -10.2 % [-22, +0] sf=0.25 lmm=0.18 3/1** |
| SAVIOR vs SAVIOR-none | openloris_all | -6.2 % [-10, -2] H=0.062 46/40 / seq -6.1 % [-14, +1] sf=0.17 lmm=0.15 6/3 |
| SAVIOR vs SAVIOR-none | uhumans2_06h | +17.9 % [-23, +75] H=1 4/5 |
| SAVIOR vs SAVIOR-none | uhumans2_12h | +13.7 % [-8, +41] H=0.39 5/5 |
| SAVIOR vs SAVIOR-none | uhumans2_06h+12h | +15.7 % [-8, +45] H=0.34 9/10 / seq +15.8 % [-9, +47] sf=0.5 lmm=0.43 0/2 |
| SAVIOR vs SAVIOR-none | uhumans2_all | +15.7 % [-8, +45] H=0.34 9/10 / seq +15.8 % [-9, +47] sf=0.5 lmm=0.43 0/2 |
| Y-Cls vs SAVIOR-none | openloris_heldout | -3.6 % [-7, -0] H=0.086 41/36 / seq -3.8 % [-9, +1] sf=0.19 lmm=0.17 4/4 |
| Y-Cls vs SAVIOR-none | openloris_heldout_P2offsets | -5.2 % [-10, -0] H=0.1 13/11 / seq -5.2 % [-13, +3] sf=0.25 lmm=0.26 5/3 |
| Y-Cls vs SAVIOR-none | openloris_cafe1-1 | -0.0 % [-4, +3] H=1 4/5 |
| Y-Cls vs SAVIOR-none | openloris_people | -4.4 % [-10, +2] H=0.21 22/15 / seq -4.6 % [-14, +5] sf=0.5 lmm=0.42 2/2 |
| Y-Cls vs SAVIOR-none | openloris_all | -3.2 % [-6, -0] H=0.11 45/41 / seq -3.3 % [-8, +1] sf=0.17 lmm=0.17 5/4 |
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
| SAVIOR-none vs OpenVINS | openloris_heldout | +0.4 % [-2, +3] H=0.61 26/23 / seq +0.4 % [-2, +3] sf=0.49 lmm=0.78 2/6 |
| SAVIOR-none vs OpenVINS | openloris_heldout_P2offsets | -1.0 % [-7, +4] H=0.98 9/6 / seq -1.0 % [-10, +5] sf=0.95 lmm=0.77 2/5 |
| SAVIOR-none vs OpenVINS | openloris_cafe1-1 | +0.3 % [-0, +1] H=1 3/2 |
| SAVIOR-none vs OpenVINS | openloris_people | -0.1 % [-1, +1] H=0.76 6/8 / seq -0.1 % [-2, +1] sf=1 lmm=0.9 1/3 |
| SAVIOR-none vs OpenVINS | openloris_all | +0.4 % [-2, +3] H=0.65 29/25 / seq +0.4 % [-2, +3] sf=0.43 lmm=0.76 2/7 |
| SAVIOR-none vs OpenVINS | uhumans2_06h | -1.7 % [-19, +20] H=1 5/5 |
| SAVIOR-none vs OpenVINS | uhumans2_12h | -15.2 % [-30, +1] H=0.28 7/3 |
| SAVIOR-none vs OpenVINS | uhumans2_06h+12h | -8.7 % [-20, +5] H=0.43 12/8 / seq -8.7 % [-23, +8] sf=0.5 lmm=0.43 2/0 |
| SAVIOR-none vs OpenVINS | uhumans2_all | -8.7 % [-20, +5] H=0.43 12/8 / seq -8.7 % [-23, +8] sf=0.5 lmm=0.43 2/0 |

Invalid runs excluded pairwise (8): openloris_cafe1-1/e_savior_none/run_10, openloris_cafe1-2/e_sens_fix1/run_01, openloris_office1-2/e_sens_fix1/run_02, openloris_office1-5/e_savior_none/run_09, openloris_office1-6/e_yolo_naive/run_07, openloris_office1-7/e_yolo_naive/run_05, uhumans2_office_s1_00h/e_sens_fix1/run_03, uhumans2_office_s1_06h/e_sens_fix1/run_03

Reproduction of earlier OpenVINS runs (same original estimator config, same start offset, trajectory md5): p2: 11/36 identical, p4: 19/60 identical, p7/noharm: 4/20 identical, p3a: 0/25 identical
