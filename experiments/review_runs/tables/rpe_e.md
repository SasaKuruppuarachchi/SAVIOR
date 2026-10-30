# Task E: final SAVIOR (sens_fix1, COCO instantiation) and Y-Cls on OpenLORIS + uHumans2, ORIGINAL back-end (RPE)

Cells: RUN level: geometric-mean ratio - 1 [iid bootstrap CI], Holm-adjusted Wilcoxon p (within family x group), wins/losses of the paired offsets / SEQUENCE level (stats_v3): exp(mean of per-sequence mean log ratios) - 1 [two-stage cluster bootstrap CI], exact sign-flip p (sf; minimum attainable 2/2^k), LMM p, sequences better/worse. Negative = first method better. Single-sequence groups have no sequence-level statistic. P2offsets = runs 1-3 (start offsets 0.0/0.2/0.4 s, the P2 protocol).

## Median RPE [m] per sequence (n runs; [k] failures > 1 m)

| seq | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | oracle person |
|---|--:|--:|--:|--:|--:|
| openloris_cafe1-1 | 0.1726 (n=10) | 0.1717 (n=9) | 0.1729 (n=10) | 0.1788 (n=10) | - |
| openloris_cafe1-2 | 0.1856 (n=10) | 0.1841 (n=10) | 0.1896 (n=10) | 0.1869 (n=9) | - |
| openloris_office1-1 | 0.0258 (n=10) | 0.0258 (n=10) | 0.0251 (n=10) | 0.0262 (n=10) | - |
| openloris_office1-2 | 0.0262 (n=10) | 0.0254 (n=10) | 0.0254 (n=10) | 0.0256 (n=9) | - |
| openloris_office1-3 | 0.0059 (n=10) | 0.0060 (n=10) | 0.0060 (n=10) | 0.0060 (n=10) | - |
| openloris_office1-4 | 0.0249 (n=10) | 0.0255 (n=10) | 0.0260 (n=10) | 0.0249 (n=10) | - |
| openloris_office1-5 | 0.0427 (n=10) | 0.0420 (n=9) | 0.0394 (n=10) | 0.0390 (n=10) | - |
| openloris_office1-6 | 0.0245 (n=10) | 0.0245 (n=10) | 0.0243 (n=9) | 0.0242 (n=10) | - |
| openloris_office1-7 | 0.0306 (n=10) | 0.0308 (n=10) | 0.0279 (n=9) | 0.0261 (n=10) | - |
| uhumans2_office_s1_00h | 0.1400 (n=5) | - | 0.1449 (n=5) | 0.1444 (n=4) | - |
| uhumans2_office_s1_06h | 0.1408 (n=10) | 0.1346 (n=10) | 0.1545 (n=10) | 0.1302 (n=9) | 0.1450 (n=10) |
| uhumans2_office_s1_12h | 0.1602 (n=10) | 0.1595 (n=10) | 0.1526 (n=10) | 0.1550 (n=10) | 0.1645 (n=10) |

## E_vs_openvins

| comparison | group | result |
|---|---|---|
| SAVIOR vs OpenVINS | openloris_heldout | **-3.4 % [-5, -1] H=0.0022 52/26 / seq -3.4 % [-7, -0] sf=0.13 lmm=0.11 5/3** |
| SAVIOR vs OpenVINS | openloris_heldout_P2offsets | -4.5 % [-8, -1] H=0.12 15/7 / seq -4.4 % [-10, +1] sf=0.21 lmm=0.19 4/4 |
| SAVIOR vs OpenVINS | openloris_cafe1-1 | **+3.1 % [+1, +5] H=0.027 2/8** |
| SAVIOR vs OpenVINS | openloris_people | **-5.3 % [-8, -3] H=0.0029 26/13 / seq -5.2 % [-11, -0] sf=0.25 lmm=0.19 3/1** |
| SAVIOR vs OpenVINS | openloris_all | **-2.6 % [-4, -1] H=0.035 54/34 / seq -2.7 % [-6, +1] sf=0.19 lmm=0.17 5/4** |
| SAVIOR vs OpenVINS | uhumans2_00h | +2.5 % [-10, +12] H=0.88 1/3 |
| SAVIOR vs OpenVINS | uhumans2_06h | -2.3 % [-11, +9] H=0.99 6/3 |
| SAVIOR vs OpenVINS | uhumans2_12h | -4.3 % [-11, +2] H=1 4/6 |
| SAVIOR vs OpenVINS | uhumans2_06h+12h | -3.4 % [-9, +3] H=0.68 10/9 / seq -3.3 % [-9, +3] sf=0.5 lmm=0.48 2/0 |
| SAVIOR vs OpenVINS | uhumans2_all | -2.4 % [-7, +3] H=0.6 11/12 / seq -1.4 % [-7, +6] sf=0.75 lmm=0.49 2/1 |
| Y-Cls vs OpenVINS | openloris_heldout | -1.2 % [-3, +0] H=0.35 38/40 / seq -1.2 % [-4, +1] sf=0.28 lmm=0.29 4/4 |
| Y-Cls vs OpenVINS | openloris_heldout_P2offsets | -1.8 % [-4, +1] H=0.28 13/11 / seq -1.8 % [-6, +2] sf=0.39 lmm=0.41 5/3 |
| Y-Cls vs OpenVINS | openloris_cafe1-1 | -0.2 % [-3, +2] H=0.49 3/7 |
| Y-Cls vs OpenVINS | openloris_people | -1.9 % [-4, +0] H=0.17 21/17 / seq -2.0 % [-5, +1] sf=0.5 lmm=0.31 2/2 |
| Y-Cls vs OpenVINS | openloris_all | -1.1 % [-2, +0] H=0.48 41/47 / seq -1.1 % [-3, +1] sf=0.27 lmm=0.28 5/4 |
| Y-Cls vs OpenVINS | uhumans2_00h | +3.7 % [-7, +16] H=0.88 1/4 |
| Y-Cls vs OpenVINS | uhumans2_06h | +10.1 % [+1, +21] H=0.32 4/6 |
| Y-Cls vs OpenVINS | uhumans2_12h | -1.4 % [-8, +6] H=1 5/5 |
| Y-Cls vs OpenVINS | uhumans2_06h+12h | +4.2 % [-2, +11] H=0.68 9/11 / seq +4.2 % [-5, +15] sf=1 lmm=0.59 1/1 |
| Y-Cls vs OpenVINS | uhumans2_all | +4.1 % [-1, +10] H=0.6 10/15 / seq +4.0 % [-3, +12] sf=0.5 lmm=0.39 1/2 |
| oracle person vs OpenVINS | uhumans2_06h | +4.2 % [-3, +14] H=0.99 5/5 |
| oracle person vs OpenVINS | uhumans2_12h | +3.7 % [-7, +15] H=1 4/6 |
| oracle person vs OpenVINS | uhumans2_06h+12h | +4.0 % [-3, +11] H=0.68 9/11 / seq +4.0 % [-3, +11] sf=0.5 lmm=0.46 0/2 |
| oracle person vs OpenVINS | uhumans2_all | +4.0 % [-3, +11] H=0.6 9/11 / seq +4.0 % [-3, +11] sf=0.5 lmm=0.46 0/2 |

## E_savior_vs_ycls

| comparison | group | result |
|---|---|---|
| SAVIOR vs Y-Cls | openloris_heldout | **-2.0 % [-4, -1] H=0.0015 52/24 / seq -2.1 % [-4, +0] sf=0.055 lmm=0.075 7/1** |
| SAVIOR vs Y-Cls | openloris_heldout_P2offsets | **-2.9 % [-5, -1] H=0.02 16/6 / seq -2.7 % [-6, +0] sf=0.07 lmm=0.12 7/1** |
| SAVIOR vs Y-Cls | openloris_cafe1-1 | **+3.4 % [+1, +6] H=0.0039 1/9** |
| SAVIOR vs Y-Cls | openloris_people | **-3.3 % [-5, -2] H=0.0056 25/12 / seq -3.3 % [-7, -1] sf=0.12 lmm=0.13 4/0** |
| SAVIOR vs Y-Cls | openloris_all | **-1.4 % [-3, -0] H=0.028 53/33 / seq -1.5 % [-4, +1] sf=0.18 lmm=0.2 7/2** |
| SAVIOR vs Y-Cls | uhumans2_00h | -1.9 % [-6, +2] H=0.62 3/1 |
| SAVIOR vs Y-Cls | uhumans2_06h | **-13.2 % [-20, -5] H=0.039 7/2** |
| SAVIOR vs Y-Cls | uhumans2_12h | -3.0 % [-12, +6] H=0.62 6/4 |
| SAVIOR vs Y-Cls | uhumans2_06h+12h | **-8.0 % [-14, -1] H=0.045 13/6 / seq -8.2 % [-17, +1] sf=0.5 lmm=0.37 2/0** |
| SAVIOR vs Y-Cls | uhumans2_all | **-6.9 % [-12, -1] H=0.033 16/7 / seq -6.2 % [-13, +0] sf=0.25 lmm=0.24 3/0** |

## E_vs_empty_mask

| comparison | group | result |
|---|---|---|
| SAVIOR vs SAVIOR-none | openloris_heldout | **-2.9 % [-5, -1] H=0.0068 47/30 / seq -2.9 % [-7, +0] sf=0.094 lmm=0.15 5/3** |
| SAVIOR vs SAVIOR-none | openloris_heldout_P2offsets | -4.1 % [-7, -1] H=0.14 13/9 / seq -3.7 % [-9, +1] sf=0.24 lmm=0.22 6/2 |
| SAVIOR vs SAVIOR-none | openloris_cafe1-1 | **+3.6 % [+2, +5] H=0.016 1/8** |
| SAVIOR vs SAVIOR-none | openloris_people | **-5.1 % [-8, -3] H=0.0045 25/13 / seq -5.0 % [-11, +0] sf=0.25 lmm=0.22 3/1** |
| SAVIOR vs SAVIOR-none | openloris_all | -2.2 % [-4, -1] H=0.1 48/38 / seq -2.2 % [-6, +1] sf=0.28 lmm=0.24 5/4 |
| SAVIOR vs SAVIOR-none | uhumans2_06h | +0.4 % [-9, +11] H=1 4/5 |
| SAVIOR vs SAVIOR-none | uhumans2_12h | -2.2 % [-7, +2] H=1 5/5 |
| SAVIOR vs SAVIOR-none | uhumans2_06h+12h | -1.0 % [-6, +5] H=0.71 9/10 / seq -0.9 % [-6, +6] sf=1 lmm=0.79 1/1 |
| SAVIOR vs SAVIOR-none | uhumans2_all | -1.0 % [-6, +5] H=0.71 9/10 / seq -0.9 % [-6, +6] sf=1 lmm=0.79 1/1 |
| Y-Cls vs SAVIOR-none | openloris_heldout | -0.7 % [-2, +0] H=0.6 38/39 / seq -0.8 % [-3, +1] sf=0.53 lmm=0.45 3/5 |
| Y-Cls vs SAVIOR-none | openloris_heldout_P2offsets | -1.3 % [-3, +1] H=0.28 12/12 / seq -1.3 % [-4, +2] sf=0.5 lmm=0.42 3/5 |
| Y-Cls vs SAVIOR-none | openloris_cafe1-1 | +0.7 % [-1, +2] H=0.16 2/7 |
| Y-Cls vs SAVIOR-none | openloris_people | -1.7 % [-4, +0] H=0.24 20/17 / seq -1.7 % [-5, +1] sf=0.5 lmm=0.41 2/2 |
| Y-Cls vs SAVIOR-none | openloris_all | -0.5 % [-2, +0] H=0.91 40/46 / seq -0.6 % [-3, +1] sf=0.59 lmm=0.51 3/6 |
| Y-Cls vs SAVIOR-none | uhumans2_06h | +13.6 % [+3, +26] H=0.48 4/6 |
| Y-Cls vs SAVIOR-none | uhumans2_12h | +0.8 % [-7, +9] H=1 4/6 |
| Y-Cls vs SAVIOR-none | uhumans2_06h+12h | +7.0 % [+0, +15] H=0.27 8/12 / seq +7.0 % [-3, +19] sf=0.5 lmm=0.46 0/2 |
| Y-Cls vs SAVIOR-none | uhumans2_all | +7.0 % [+0, +15] H=0.27 8/12 / seq +7.0 % [-3, +19] sf=0.5 lmm=0.46 0/2 |
| oracle person vs SAVIOR-none | uhumans2_06h | +7.6 % [-1, +17] H=0.48 3/7 |
| oracle person vs SAVIOR-none | uhumans2_12h | +5.9 % [-5, +17] H=0.83 4/6 |
| oracle person vs SAVIOR-none | uhumans2_06h+12h | +6.8 % [-0, +14] H=0.23 7/13 / seq +6.8 % [-0, +14] sf=0.5 lmm=0.31 0/2 |
| oracle person vs SAVIOR-none | uhumans2_all | +6.8 % [-0, +14] H=0.23 7/13 / seq +6.8 % [-0, +14] sf=0.5 lmm=0.31 0/2 |

## E_control

| comparison | group | result |
|---|---|---|
| SAVIOR-none vs OpenVINS | openloris_heldout | -0.5 % [-2, +0] H=0.17 28/21 / seq -0.5 % [-2, +1] sf=0.59 lmm=0.48 4/4 |
| SAVIOR-none vs OpenVINS | openloris_heldout_P2offsets | -0.5 % [-3, +2] H=0.28 10/5 / seq -0.5 % [-3, +2] sf=0.7 lmm=0.7 4/3 |
| SAVIOR-none vs OpenVINS | openloris_cafe1-1 | +0.1 % [-0, +0] H=0.31 1/4 |
| SAVIOR-none vs OpenVINS | openloris_people | -0.3 % [-1, +0] H=0.81 8/6 / seq -0.3 % [-2, +1] sf=0.75 lmm=0.59 2/2 |
| SAVIOR-none vs OpenVINS | openloris_all | -0.4 % [-1, +0] H=0.35 29/25 / seq -0.4 % [-2, +1] sf=0.59 lmm=0.48 4/5 |
| SAVIOR-none vs OpenVINS | uhumans2_06h | -3.1 % [-7, +1] H=0.49 6/4 |
| SAVIOR-none vs OpenVINS | uhumans2_12h | -2.1 % [-6, +2] H=0.28 6/4 |
| SAVIOR-none vs OpenVINS | uhumans2_06h+12h | -2.6 % [-5, +0] H=0.18 12/8 / seq -2.6 % [-6, +0] sf=0.5 lmm=0.32 2/0 |
| SAVIOR-none vs OpenVINS | uhumans2_all | -2.6 % [-5, +0] H=0.18 12/8 / seq -2.6 % [-6, +0] sf=0.5 lmm=0.32 2/0 |

Invalid runs excluded pairwise (8): openloris_cafe1-1/e_savior_none/run_10, openloris_cafe1-2/e_sens_fix1/run_01, openloris_office1-2/e_sens_fix1/run_02, openloris_office1-5/e_savior_none/run_09, openloris_office1-6/e_yolo_naive/run_07, openloris_office1-7/e_yolo_naive/run_05, uhumans2_office_s1_00h/e_sens_fix1/run_03, uhumans2_office_s1_06h/e_sens_fix1/run_03

Reproduction of earlier OpenVINS runs (same original estimator config, same start offset, trajectory md5): p2: 11/36 identical, p4: 19/60 identical, p7/noharm: 4/20 identical, p3a: 0/25 identical
