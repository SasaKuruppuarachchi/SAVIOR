# Same masks, two back-ends (warehouse t1, 10 offsets): ATE change vs the back-end's own unmasked baseline

OpenVINS numbers: frozen t1 runs (P6/P7, edge study e_c_n672_L250dfronly); VINS-Fusion: this study (deterministic).

| mask | group | OpenVINS: change [95 % CI] p | VINS-Fusion: change [95 % CI] p |
|---|---|---|---|
| Y-Cls | L0+L1 | +27.7 % [+10, +47] p=0.00405 | +5.4 % [-6, +18] p=0.301 |
| Y-Cls | L2+L3 | -72.1 % [-82, -57] p=1.46e-07 | -23.5 % [-35, -10] p=0.0102 |
| Y-Cls | hall_L3 | -95.5 % [-97, -94] p=0.00195 | -57.6 % [-62, -53] p=0.00195 |
| SAVIOR | L0+L1 | +9.7 % [-6, +28] p=0.132 | +0.3 % [-9, +11] p=0.806 |
| SAVIOR | L2+L3 | -73.1 % [-85, -53] p=0.000233 | -30.3 % [-37, -23] p=2.36e-08 |
| SAVIOR | hall_L3 | -98.4 % [-99, -98] p=0.00195 | -56.2 % [-61, -51] p=0.00195 |
| SAVIOR-edge | L0+L1 | +16.6 % [-2, +39] p=0.0622 | -8.6 % [-17, +1] p=0.139 |
| SAVIOR-edge | L2+L3 | -73.2 % [-85, -54] p=1.67e-05 | -34.1 % [-44, -23] p=3.06e-05 |
| SAVIOR-edge | hall_L3 | -97.8 % [-98, -97] p=0.00195 | -70.1 % [-73, -67] p=0.00195 |
| O-Dyn+B | L0+L1 | +0.3 % [-11, +13] p=0.956 | -10.3 % [-17, -4] p=0.00558 |
| O-Dyn+B | L2+L3 | -76.6 % [-86, -62] p=5.06e-08 | -46.6 % [-54, -38] p=7.82e-11 |
| O-Dyn+B | hall_L3 | -97.4 % [-98, -96] p=0.00195 | -68.7 % [-73, -64] p=0.00195 |
| O-Cls+B | L0+L1 | +32.6 % [+14, +54] p=0.000844 | +30.8 % [+18, +45] p=2.64e-05 |
| O-Cls+B | L2+L3 | -62.1 % [-76, -42] p=0.000233 | -24.4 % [-40, -6] p=0.0178 |
| O-Cls+B | hall_L3 | -91.6 % [-96, -80] p=0.00391 | -70.9 % [-73, -68] p=0.00195 |
