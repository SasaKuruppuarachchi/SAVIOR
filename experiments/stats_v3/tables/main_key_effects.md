# Main-text candidate: key effects, sequence level

Geometric-mean ATE change (%; failures capped at 10 m), sequence-level 95 % CI (LMM, df = k-1), sequences in favour, failure counts, and the same ratio on runs where neither method failed. Negative = first method better.

| comparison | data | group | k | ATE change [95 % CI] | seq. agreeing with sign | failures A / B | non-failed change [95 % CI] |
|---|---|---|--:|---|--:|--:|---|
| O-Dyn+B vs O-Cls+B | WH | L0+L1 | 6 | -45 [-56, -32] | 6/6 | 0/60 / 0/60 | -45 [-56, -32] |
| O-Dyn+B vs O-Cls+B | WH | L2+L3 | 6 | -76 [-96, +25] | 6/6 | 0/60 / 11/60 | -53 [-67, -33] |
| VINS+O-Dyn+B vs VINS+O-Cls+B | WH | L2+L3 | 6 | -37 [-58, -4] | 6/6 | 0/60 / 0/60 | -37 [-58, -4] |
| SAVIOR vs Y-Cls | WH | L0+L1 | 6 | -25 [-43, -3] | 6/6 | 0/60 / 0/60 | -25 [-43, -3] |
| SAVIOR vs Y-Cls | WH | L2+L3 | 6 | -35 [-70, +40] | 5/6 | 4/60 / 10/60 | -10 [-36, +24] |
| VINS+SAVIOR vs VINS+Y-Cls | WH | L0+L1 | 6 | -21 [-35, -3] | 6/6 | 0/60 / 0/60 | -21 [-35, -3] |
| VINS+SAVIOR vs VINS+Y-Cls | WH | L2+L3 | 6 | -16 [-34, +6] | 4/6 | 0/60 / 0/60 | -16 [-34, +6] |
| Y-Cls vs OpenVINS | WH | L0 | 3 | +46 [-49, +321] | 2/3 | 0/30 / 0/30 | +46 [-49, +321] |
| O-Cls+B vs OpenVINS | WH | L0 | 3 | +105 [+9, +284] | 3/3 | 0/30 / 0/30 | +105 [+9, +284] |
| SAVIOR vs OpenVINS | WH | L2+L3 | 6 | -55 [-90, +113] | 4/6 | 4/60 / 13/60 | -17 [-44, +28] |
| VINS+SAVIOR vs VINS-Fusion | WH | L2+L3 | 6 | +25 [-10, +75] | 4/6 | 0/60 / 0/60 | +25 [-10, +75] |
| VINS+Y-Cls vs VINS-Fusion | WH | L2+L3 | 6 | +50 [+2, +120] | 5/6 | 0/60 / 0/60 | +50 [+2, +120] |
| VINS+SAVIOR vs VINS-Fusion | VIODE | mid+high | 6 | -56 [-76, -20] | 5/6 | 2/60 / 9/60 | -34 [-61, +11] |
| SAVIOR vs DynaVINS | VIODE | all | 12 | -58 [-84, +11] | 7/12 | 5/120 / 25/120 | -18 [-30, +5] |
| SAVIOR vs VINS-Fusion | VIODE | all | 12 | -63 [-78, -38] | 12/12 | 5/120 / 16/120 | -52 [-60, -40] |
| SAVIOR vs DynaVINS | WH | all | 12 | +41 [-9, +119] | 8/12 | 4/120 / 0/120 | +25 [-1, +57] |
| SAVIOR-edge vs SAVIOR | WH | L0+L1 | 6 | +22 [-3, +54] | 6/6 | 1/60 / 0/60 | +12 [+2, +24] |
