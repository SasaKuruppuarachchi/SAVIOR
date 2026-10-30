# Per-environment breakdown (descriptive; cap 10 m; LMM per environment, df = n_traj - 1; no multiplicity control)

| id | comparison | group | env | estimate [95 % CI] | p | sign-flip p | traj better/worse |
|---|---|---|---|---|---|---|---|
| P1 | O-Dyn+B vs O-Cls+B | high | fw | -52.6 % [-70.3, -24.2] | 0.009 | 0.031 | 6/0 |
| P1 | O-Dyn+B vs O-Cls+B | high | sw | -68.0 % [-86.0, -26.9] | 0.016 | 0.031 | 6/0 |
| P1 | O-Dyn+B vs O-Cls+B | high | ms | -38.6 % [-57.7, -11.0] | 0.020 | 0.031 | 6/0 |
| P1 | O-Dyn+B vs O-Cls+B | high | wx | -4.7 % [-19.8, +13.2] | 0.507 | 0.375 | 4/2 |
| P2 | SAVIOR vs Y-Cls | high | fw | -42.0 % [-59.3, -17.3] | 0.011 | 0.031 | 6/0 |
| P2 | SAVIOR vs Y-Cls | high | sw | -37.6 % [-50.0, -22.1] | 0.003 | 0.031 | 6/0 |
| P2 | SAVIOR vs Y-Cls | high | ms | -19.7 % [-36.1, +0.8] | 0.056 | 0.062 | 5/1 |
| P2 | SAVIOR vs Y-Cls | high | wx | -33.8 % [-58.3, +5.1] | 0.070 | 0.062 | 5/1 |
| P3 | SAVIOR vs Y-Cls | low | fw | -28.1 % [-45.8, -4.6] | 0.030 | 0.031 | 6/0 |
| P3 | SAVIOR vs Y-Cls | low | sw | -26.4 % [-40.1, -9.6] | 0.012 | 0.062 | 5/1 |
| P3 | SAVIOR vs Y-Cls | low | ms | -24.3 % [-52.9, +21.5] | 0.191 | 0.156 | 4/2 |
| P3 | SAVIOR vs Y-Cls | low | wx | -30.5 % [-42.6, -16.0] | 0.004 | 0.031 | 6/0 |
| P4 | SAVIOR vs OpenVINS | high | fw | -49.6 % [-75.8, +5.3] | 0.062 | 0.031 | 6/0 |
| P4 | SAVIOR vs OpenVINS | high | sw | -47.3 % [-71.5, -2.5] | 0.044 | 0.031 | 6/0 |
| P4 | SAVIOR vs OpenVINS | high | ms | -50.6 % [-76.6, +3.9] | 0.059 | 0.031 | 6/0 |
| P4 | SAVIOR vs OpenVINS | high | wx | -43.3 % [-72.1, +15.1] | 0.094 | 0.031 | 6/0 |
| P5 | SAVIOR vs OpenVINS | static | fw | +0.3 % [-12.5, +14.9] | 0.963 | 0.969 | 3/3 |
| P5 | SAVIOR vs OpenVINS | static | sw | +8.9 % [-11.0, +33.2] | 0.328 | 0.344 | 2/4 |
| P5 | SAVIOR vs OpenVINS | static | ms | +11.8 % [-5.8, +32.8] | 0.156 | 0.250 | 3/3 |
| P5 | SAVIOR vs OpenVINS | static | wx | -10.1 % [-35.4, +25.1] | 0.447 | 0.469 | 3/3 |
| S1 | VINS+SAVIOR vs VINS+Y-Cls | high | fw | -15.4 % [-34.3, +8.7] | 0.147 | 0.156 | 4/2 |
| S1 | VINS+SAVIOR vs VINS+Y-Cls | high | sw | -2.2 % [-27.4, +31.7] | 0.854 | 0.844 | 2/4 |
| S1 | VINS+SAVIOR vs VINS+Y-Cls | high | ms | -2.7 % [-19.2, +17.1] | 0.720 | 0.656 | 4/2 |
| S1 | VINS+SAVIOR vs VINS+Y-Cls | high | wx | -28.4 % [-39.5, -15.3] | 0.004 | 0.031 | 6/0 |
| S2 | VINS+SAVIOR vs VINS+Y-Cls | low | fw | -16.1 % [-25.3, -5.7] | 0.012 | 0.031 | 6/0 |
| S2 | VINS+SAVIOR vs VINS+Y-Cls | low | sw | -0.1 % [-19.6, +24.1] | 0.992 | 1.000 | 3/3 |
| S2 | VINS+SAVIOR vs VINS+Y-Cls | low | ms | -6.3 % [-28.4, +22.6] | 0.562 | 0.562 | 4/2 |
| S2 | VINS+SAVIOR vs VINS+Y-Cls | low | wx | -26.1 % [-39.0, -10.3] | 0.010 | 0.031 | 6/0 |
| S3 | VINS+SAVIOR vs VINS-Fusion | high | fw | -45.9 % [-62.9, -21.0] | 0.009 | 0.031 | 6/0 |
| S3 | VINS+SAVIOR vs VINS-Fusion | high | sw | -7.9 % [-28.7, +19.1] | 0.449 | 0.500 | 4/2 |
| S3 | VINS+SAVIOR vs VINS-Fusion | high | ms | +8.3 % [-11.7, +32.8] | 0.362 | 0.312 | 2/4 |
| S3 | VINS+SAVIOR vs VINS-Fusion | high | wx | +3.7 % [-39.7, +78.1] | 0.871 | 0.844 | 2/4 |
| S4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | fw | -19.6 % [-35.3, -0.2] | 0.049 | 0.031 | 6/0 |
| S4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | sw | -30.1 % [-42.0, -15.6] | 0.004 | 0.031 | 6/0 |
| S4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | ms | -16.9 % [-38.0, +11.3] | 0.164 | 0.156 | 5/1 |
| S4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | wx | -13.2 % [-30.2, +8.0] | 0.157 | 0.156 | 5/1 |
| S5 | VINS+Y-Cls vs VINS-Fusion | static | fw | +24.8 % [+13.2, +37.5] | 0.002 | 0.031 | 0/6 |
| S5 | VINS+Y-Cls vs VINS-Fusion | static | sw | -1.8 % [-35.6, +49.8] | 0.917 | 0.969 | 4/2 |
| S5 | VINS+Y-Cls vs VINS-Fusion | static | ms | +13.2 % [-10.3, +42.7] | 0.229 | 0.219 | 2/4 |
| S5 | VINS+Y-Cls vs VINS-Fusion | static | wx | +82.2 % [+43.2, +131.8] | 0.001 | 0.031 | 0/6 |
| S6 | VINS+SAVIOR vs VINS-Fusion | static | fw | +2.3 % [-10.3, +16.7] | 0.672 | 0.781 | 3/3 |
| S6 | VINS+SAVIOR vs VINS-Fusion | static | sw | +2.8 % [-6.7, +13.2] | 0.493 | 0.562 | 2/4 |
| S6 | VINS+SAVIOR vs VINS-Fusion | static | ms | +10.0 % [-2.1, +23.6] | 0.088 | 0.125 | 2/4 |
| S6 | VINS+SAVIOR vs VINS-Fusion | static | wx | +20.1 % [-4.1, +50.5] | 0.091 | 0.156 | 1/5 |
| S7 | SAVIOR vs DynaVINS (upstream) | high | fw | +38.6 % [+1.2, +89.7] | 0.044 | 0.031 | 0/6 |
| S7 | SAVIOR vs DynaVINS (upstream) | high | sw | +37.0 % [-15.8, +123.0] | 0.157 | 0.188 | 2/4 |
| S7 | SAVIOR vs DynaVINS (upstream) | high | ms | +1.8 % [-27.4, +42.8] | 0.895 | 0.906 | 3/3 |
| S7 | SAVIOR vs DynaVINS (upstream) | high | wx | +63.8 % [+6.3, +152.5] | 0.033 | 0.062 | 1/5 |
| S8 | SAVIOR vs DynaVINS (upstream) | low | fw | +52.7 % [+12.8, +106.8] | 0.016 | 0.031 | 0/6 |
| S8 | SAVIOR vs DynaVINS (upstream) | low | sw | +72.5 % [+33.1, +123.7] | 0.003 | 0.031 | 0/6 |
| S8 | SAVIOR vs DynaVINS (upstream) | low | ms | +15.1 % [-16.8, +59.2] | 0.317 | 0.344 | 1/5 |
| S8 | SAVIOR vs DynaVINS (upstream) | low | wx | +66.8 % [+22.2, +127.6] | 0.008 | 0.031 | 0/6 |
| S9 | SAVIOR-edge vs SAVIOR | high | fw | +18.4 % [-0.4, +40.9] | 0.054 | 0.031 | 0/6 |
| S9 | SAVIOR-edge vs SAVIOR | high | sw | +5.9 % [-14.5, +31.1] | 0.524 | 0.719 | 3/3 |
| S9 | SAVIOR-edge vs SAVIOR | high | ms | +6.8 % [-7.6, +23.4] | 0.296 | 0.281 | 2/4 |
| S9 | SAVIOR-edge vs SAVIOR | high | wx | -8.9 % [-32.4, +22.7] | 0.458 | 0.250 | 4/2 |
| S10 | SAVIOR-edge vs SAVIOR | low | fw | +3.9 % [-12.1, +22.8] | 0.580 | 0.406 | 2/4 |
| S10 | SAVIOR-edge vs SAVIOR | low | sw | -5.3 % [-15.2, +5.8] | 0.262 | 0.125 | 5/1 |
| S10 | SAVIOR-edge vs SAVIOR | low | ms | +3.8 % [-14.9, +26.5] | 0.652 | 0.656 | 2/4 |
| S10 | SAVIOR-edge vs SAVIOR | low | wx | +9.2 % [-14.2, +39.1] | 0.392 | 0.406 | 3/3 |
| S11 | Y-Cls vs OpenVINS | static | fw | +43.7 % [+0.5, +105.5] | 0.048 | 0.031 | 0/6 |
| S11 | Y-Cls vs OpenVINS | static | sw | +36.9 % [-0.1, +87.6] | 0.050 | 0.062 | 1/5 |
| S11 | Y-Cls vs OpenVINS | static | ms | +57.6 % [-7.4, +168.4] | 0.079 | 0.031 | 0/6 |
| S11 | Y-Cls vs OpenVINS | static | wx | +29.5 % [-13.6, +93.9] | 0.162 | 0.188 | 1/5 |
| S12 | O-Dyn+B vs OpenVINS | high | fw | -57.3 % [-79.9, -9.5] | 0.033 | 0.031 | 6/0 |
| S12 | O-Dyn+B vs OpenVINS | high | sw | -57.5 % [-77.3, -20.6] | 0.017 | 0.031 | 6/0 |
| S12 | O-Dyn+B vs OpenVINS | high | ms | -54.0 % [-77.5, -6.2] | 0.038 | 0.031 | 6/0 |
| S12 | O-Dyn+B vs OpenVINS | high | wx | -56.0 % [-77.1, -15.6] | 0.023 | 0.031 | 6/0 |
| S13 | SAVIOR vs OpenVINS | low | fw | +5.0 % [-9.2, +21.5] | 0.428 | 0.406 | 3/3 |
| S13 | SAVIOR vs OpenVINS | low | sw | +10.9 % [-1.8, +25.1] | 0.080 | 0.125 | 2/4 |
| S13 | SAVIOR vs OpenVINS | low | ms | +5.0 % [-7.1, +18.7] | 0.353 | 0.125 | 1/5 |
| S13 | SAVIOR vs OpenVINS | low | wx | -5.1 % [-21.8, +15.3] | 0.522 | 0.656 | 3/3 |
| S14 | DynaVINS (upstream) vs VINS-Fusion | high | fw | -69.2 % [-84.1, -40.4] | 0.006 | 0.031 | 6/0 |
| S14 | DynaVINS (upstream) vs VINS-Fusion | high | sw | -51.9 % [-68.8, -25.7] | 0.008 | 0.031 | 6/0 |
| S14 | DynaVINS (upstream) vs VINS-Fusion | high | ms | -36.5 % [-63.8, +11.5] | 0.093 | 0.125 | 5/1 |
| S14 | DynaVINS (upstream) vs VINS-Fusion | high | wx | -60.0 % [-78.3, -26.4] | 0.012 | 0.031 | 6/0 |
