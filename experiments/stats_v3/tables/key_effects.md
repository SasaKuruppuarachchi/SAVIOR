# Key effects at the sequence level (stats_v3)

Unit = sequence (k = 3 static, 6 per level group, 12 all). Effect = geometric-mean ATE ratio - 1 (%) with failures capped at 10 m; negative = first method better. **seq CI** = LMM t-interval (REML, sequence random intercept, df = k-1); **boot** = two-stage cluster bootstrap (sequences, then offsets; 20000) percentile CI. p_LMM = LMM t-test; p_perm = exact sign-flip test on the k per-sequence means (smallest attainable p: 0.25 for k=3, 0.031 for k=6, 0.0005 for k=12); H_glob = Holm over the 31 main-text claims (LMM p). seq +/- = sequences favouring / against the first method. fail = failures A / B (ATE > 2 m warehouse, > 1 m VIODE). NF = paired ratio on runs where neither method failed, with two-stage bootstrap CI and n pairs.

| claim | comparison | set | group | k | effect | seq CI (LMM) | boot CI | p_LMM | p_perm | H_glob | seq +/- | fail A / B | NF effect [boot] (n) | old run-level [iid CI] p_W | verdict |
|---|---|---|---|--:|--:|---|---|--:|--:|--:|--:|--:|---|---|---|
| C1 | O-Dyn+B vs OpenVINS | WH | L2+L3 | 6 | **-77** | [-94, -10] | [-93, -47] | 0.040 | 0.031 | 0.99 | 6/0 | 0/60 / 13/60 | -45 [-61, -25] (47) | -77 [-86, -65] 4e-10 | PARTLY (seq-level p<0.05, not after Holm) |
| C2 | O-Dyn+B vs O-Cls+B | WH | L0+L1 | 6 | **-45** | [-56, -32] | [-55, -37] | 8e-4 | 0.031 | 0.024 | 6/0 | 0/60 / 0/60 | -45 [-55, -37] (60) | -45 [-50, -41] 2e-11 | YES (Holm-global) |
| C3 | O-Dyn+B vs O-Cls+B | WH | L2+L3 | 6 | **-76** | [-96, +25] | [-94, -45] | 0.076 | 0.031 | 1.00 | 6/0 | 0/60 / 11/60 | -53 [-63, -43] (49) | -76 [-84, -66] 2e-11 | WEAK (direction consistent; seq-level CI incl. 0) |
| C4a | VINS+O-Dyn+B vs VINS+O-Cls+B | WH | L0+L1 | 6 | **-25** | [-50, +12] | [-43, +0] | 0.13 | 0.16 | 1.00 | 4/2 | 0/60 / 0/60 | -25 [-43, +0] (60) | -25 [-32, -17] 4e-6 | NO (not supported at sequence level) |
| C4b | VINS+O-Dyn+B vs VINS+O-Cls+B | WH | L2+L3 | 6 | **-37** | [-58, -4] | [-54, -18] | 0.037 | 0.031 | 0.98 | 6/0 | 0/60 / 0/60 | -37 [-54, -18] (60) | -37 [-43, -30] 4e-11 | PARTLY (seq-level p<0.05, not after Holm) |
| C5a | O-Dyn+B vs O-Cls+B | VIODE | none+low | 6 | **+4** | [-7, +16] | [-7, +16] | 0.43 | 0.62 | 1.00 | 4/2 | 3/60 / 3/60 | +4 [-7, +17] (57) | +4 [-4, +13] 0.33 | YES as "no detectable difference" (CI wide; not equivalence) |
| C5b | O-Dyn+B vs O-Cls+B | VIODE | mid+high | 6 | **+11** | [-13, +43] | [-5, +44] | 0.32 | 0.22 | 1.00 | 2/4 | 3/60 / 2/60 | +6 [-5, +19] (57) | +11 [-1, +29] 0.22 | YES as "no detectable difference" (CI wide; not equivalence) |
| C6 | SAVIOR vs Y-Cls | WH | L0+L1 | 6 | **-25** | [-43, -3] | [-39, -10] | 0.036 | 0.031 | 0.98 | 6/0 | 0/60 / 0/60 | -25 [-39, -10] (60) | -25 [-32, -18] 6e-7 | PARTLY (seq-level p<0.05, not after Holm) |
| C7 | SAVIOR vs Y-Cls | WH | L2+L3 | 6 | **-35** | [-70, +40] | [-66, +2] | 0.20 | 0.16 | 1.00 | 5/1 | 4/60 / 10/60 | -10 [-29, +11] (50) | -35 [-51, -18] 0.001 | NO (not supported at sequence level) |
| C8a | VINS+SAVIOR vs VINS+Y-Cls | WH | L0+L1 | 6 | **-21** | [-35, -3] | [-32, -9] | 0.034 | 0.031 | 0.95 | 6/0 | 0/60 / 0/60 | -21 [-32, -9] (60) | -21 [-25, -16] 9e-10 | PARTLY (seq-level p<0.05, not after Holm) |
| C8b | VINS+SAVIOR vs VINS+Y-Cls | WH | L2+L3 | 6 | **-16** | [-34, +6] | [-29, -1] | 0.11 | 0.12 | 1.00 | 4/2 | 0/60 / 0/60 | -16 [-29, -1] (60) | -16 [-21, -11] 4e-6 | WEAK (direction consistent; seq-level CI incl. 0) |
| C9a | SAVIOR vs Y-Cls | VIODE | none+low | 6 | **-2** | [-9, +6] | [-9, +6] | 0.60 | 0.53 | 1.00 | 3/3 | 2/60 / 2/60 | -1 [-9, +6] (58) | -2 [-7, +4] 0.63 | YES (equivalent within +/-10 %) |
| C9b | SAVIOR vs Y-Cls | VIODE | mid+high | 6 | **-2** | [-13, +10] | [-11, +9] | 0.68 | 0.69 | 1.00 | 4/2 | 3/60 / 3/60 | -3 [-13, +8] (57) | -2 [-8, +5] 0.58 | YES as "no detectable difference" (CI wide; not equivalence) |
| C9c | VINS+SAVIOR vs VINS+Y-Cls | VIODE | none+low | 6 | **+8** | [-2, +18] | [+0, +17] | 0.11 | 0.094 | 1.00 | 1/5 | 4/60 / 4/60 | +8 [+0, +17] (56) | +8 [+3, +12] 0.009 | WEAK (direction consistent; seq-level CI incl. 0) |
| C10 | Y-Cls vs OpenVINS | WH | L0 | 3 | **+46** | [-49, +321] | [+1, +128] | 0.26 | 0.50 | 1.00 | 1/2 | 0/30 / 0/30 | +46 [+1, +128] (30) | +46 [+26, +69] 10e-5 | WEAK (direction consistent; seq-level CI incl. 0) |
| C11 | O-Cls+B vs OpenVINS | WH | L0 | 3 | **+105** | [+9, +284] | [+68, +168] | 0.039 | 0.25 | 0.99 | 0/3 | 0/30 / 0/30 | +105 [+68, +168] (30) | +105 [+85, +127] 2e-9 | PARTLY (seq-level p<0.05, not after Holm) |
| C12 | SAVIOR vs OpenVINS | WH | L0 | 3 | **+8** | [-18, +42] | [-7, +22] | 0.36 | 0.50 | 1.00 | 1/2 | 0/30 / 0/30 | +8 [-7, +22] (30) | +8 [-2, +19] 0.17 | YES as "no detectable difference" (CI wide; not equivalence) |
| C13a | VINS+Y-Cls vs VINS-Fusion | WH | L0 | 3 | **+16** | [-1, +36] | [+7, +26] | 0.057 | 0.25 | 1.00 | 0/3 | 0/30 / 0/30 | +16 [+7, +26] (30) | +16 [+8, +24] 0.001 | WEAK (direction consistent; seq-level CI incl. 0) |
| C13b | VINS+SAVIOR vs VINS-Fusion | WH | L0 | 3 | **-8** | [-44, +51] | [-24, +11] | 0.56 | 0.75 | 1.00 | 2/1 | 0/30 / 0/30 | -8 [-24, +11] (30) | -8 [-15, +1] 0.16 | YES as "no detectable difference" (CI wide; not equivalence) |
| C15 | SAVIOR vs OpenVINS | WH | L2+L3 | 6 | **-55** | [-90, +113] | [-87, +26] | 0.24 | 0.22 | 1.00 | 4/2 | 4/60 / 13/60 | -17 [-41, +16] (44) | -55 [-73, -26] 0.005 | NO (not supported at sequence level) |
| C15b | Y-Cls vs OpenVINS | WH | L2+L3 | 6 | **-30** | [-90, +384] | [-83, +186] | 0.65 | 0.56 | 1.00 | 4/2 | 10/60 / 13/60 | -8 [-32, +23] (39) | -30 [-61, +22] 0.47 | YES as "no detectable difference" (CI wide; not equivalence) |
| C16 | VINS+SAVIOR vs VINS-Fusion | WH | L2+L3 | 6 | **+25** | [-10, +75] | [-0, +59] | 0.14 | 0.19 | 1.00 | 2/4 | 0/60 / 0/60 | +25 [-0, +59] (60) | +25 [+15, +37] 1e-5 | NO (not supported at sequence level) |
| C17 | VINS+Y-Cls vs VINS-Fusion | WH | L2+L3 | 6 | **+50** | [+2, +120] | [+14, +95] | 0.043 | 0.094 | 1.00 | 1/5 | 0/60 / 0/60 | +50 [+14, +95] (60) | +50 [+36, +64] 8e-9 | PARTLY (seq-level p<0.05, not after Holm) |
| C18 | VINS+O-Dyn+B vs VINS-Fusion | WH | L2+L3 | 6 | **-4** | [-23, +19] | [-18, +12] | 0.65 | 0.66 | 1.00 | 3/3 | 0/60 / 0/60 | -4 [-18, +12] (60) | -4 [-10, +3] 0.19 | YES as "no detectable difference" (CI wide; not equivalence) |
| C19 | VINS+SAVIOR vs VINS-Fusion | VIODE | mid+high | 6 | **-56** | [-76, -20] | [-74, -30] | 0.017 | 0.062 | 0.48 | 5/1 | 2/60 / 9/60 | -34 [-55, -3] (51) | -56 [-67, -42] 8e-8 | PARTLY (seq-level p<0.05, not after Holm) |
| C20 | SAVIOR vs DynaVINS | VIODE | all | 12 | **-58** | [-84, +11] | [-83, -7] | 0.076 | 0.090 | 1.00 | 7/5 | 5/120 / 25/120 | -18 [-36, +2] (92) | -58 [-70, -40] 1e-5 | WEAK (direction consistent; seq-level CI incl. 0) |
| C21 | SAVIOR vs VINS-Fusion | VIODE | all | 12 | **-63** | [-78, -38] | [-78, -42] | 0.001 | 5e-4 | 0.044 | 12/0 | 5/120 / 16/120 | -52 [-60, -40] (101) | -63 [-72, -53] 2e-14 | YES (Holm-global) |
| C22 | SAVIOR vs DynaVINS | WH | all | 12 | **+41** | [-9, +119] | [+3, +120] | 0.11 | 0.058 | 1.00 | 4/8 | 4/120 / 0/120 | +25 [+2, +53] (116) | +41 [+22, +67] 1e-6 | WEAK (direction consistent; seq-level CI incl. 0) |
| C22b | SAVIOR vs VINS-Fusion | WH | L2+L3 | 6 | **+30** | [-36, +161] | [-11, +143] | 0.38 | 0.59 | 1.00 | 3/3 | 4/60 / 0/60 | +2 [-12, +20] (56) | +30 [+3, +71] 0.71 | YES as "no detectable difference" (CI wide; not equivalence) |
| C23 | SAVIOR-edge vs SAVIOR | WH | L0+L1 | 6 | **+22** | [-3, +54] | [+5, +60] | 0.076 | 0.031 | 1.00 | 0/6 | 1/60 / 0/60 | +12 [+3, +24] (59) | +22 [+6, +49] 0.002 | WEAK (direction consistent; seq-level CI incl. 0) |
| C25 | SAVIOR-adaptive vs Y-Cls | WH | L2+L3 | 6 | **-42** | [-82, +92] | [-79, +2] | 0.29 | 0.25 | 1.00 | 4/2 | 3/60 / 10/60 | -5 [-19, +8] (50) | -42 [-59, -22] 0.003 | NO (not supported at sequence level) |

Claim texts:

- C1: Perfect masks reduce high-dyn. warehouse ATE of OpenVINS (-77 %)
- C2: O-Dyn+B beats O-Cls+B, warehouse low-dyn. (-45 %)
- C3: O-Dyn+B beats O-Cls+B, warehouse high-dyn. (-76 %)
- C4a: "same holds with VINS-Fusion" (low-dyn.)
- C4b: "same holds with VINS-Fusion" (high-dyn.)
- C5a: VIODE: the two oracles do not differ (low-dyn.)
- C5b: VIODE: the two oracles do not differ (high-dyn.)
- C6: SAVIOR beats Y-Cls (OpenVINS), warehouse low-dyn. (-25 %)
- C7: SAVIOR beats Y-Cls (OpenVINS), warehouse high-dyn. (-35 %)
- C8a: SAVIOR beats Y-Cls with VINS-Fusion, warehouse low-dyn. ("significantly better")
- C8b: SAVIOR beats Y-Cls with VINS-Fusion, warehouse high-dyn. (-16 %, conclusion)
- C9a: VIODE: SAVIOR and Y-Cls equivalent with OpenVINS (low-dyn.)
- C9b: VIODE: SAVIOR and Y-Cls equivalent with OpenVINS (high-dyn.)
- C9c: VIODE: VINS+SAVIOR slightly worse than VINS+Y-Cls (low-dyn.)
- C10: Static cost: Y-Cls raises OpenVINS ATE at L0 (+46 %)
- C11: Static cost: O-Cls+B raises OpenVINS ATE at L0 (+105 %)
- C12: SAVIOR change at L0 not significant (+8 %)
- C13a: "VINS-Fusion shows the same pattern" (Y-Cls, L0)
- C13b: "VINS-Fusion shows the same pattern" (SAVIOR, L0)
- C15: SAVIOR reduces OpenVINS ATE, warehouse high-dyn. (-55 %)
- C15b: change with Y-Cls (vs OpenVINS) not significant, high-dyn.
- C16: SAVIOR raises VINS-Fusion ATE, warehouse high-dyn. (+25 %)
- C17: Y-Cls raises VINS-Fusion ATE even more, warehouse high-dyn. (+50 %)
- C18: perfect masks give VINS-Fusion no gain, warehouse high-dyn.
- C19: SAVIOR improves VINS-Fusion on VIODE high-dyn. (-56 %)
- C20: VIODE: OV+SAVIOR most accurate, below DynaVINS (-58 %)
- C21: VIODE: OV+SAVIOR below VINS-Fusion (-63 %)
- C22: Warehouse: OV+SAVIOR worse than DynaVINS (+41 %)
- C22b: Warehouse high-dyn.: VINS-Fusion lower than OV+SAVIOR (n.s.)
- C23: SAVIOR-edge worse than SAVIOR, warehouse low-dyn. (+22 %)
- C25: SAVIOR-adaptive beats Y-Cls, warehouse high-dyn. (-42 %)
