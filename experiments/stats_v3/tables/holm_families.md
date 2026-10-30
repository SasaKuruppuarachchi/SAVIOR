# Holm families (cap 10 m)

Families: **cell** = all key comparisons within one dataset x level group (static: only comparisons vs the unmasked back-end); **system** = one system block (OV2 / VINS / cross) within dataset x group; **all-key** = every key comparison x dataset x group in one family (n = 114); **global** = the 31 main-text claims. Adjusted p from the LMM test; old = Wilcoxon on pooled runs (original protocol), Holm in the same family for comparison.

| claim | comparison | set | group | p_LMM | H cell (size) | H system (size) | H all-key | H global | H global, p_perm | old p_W | old H global |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| C1 | O-Dyn+B vs OpenVINS | WH | L2+L3 | 0.040 | 0.60 (16) | 0.32 (8) | 1.00 | 0.99 | 0.94 | 4e-10 | 1e-8 |
| C2 | O-Dyn+B vs O-Cls+B | WH | L0+L1 | 8e-4 | 0.012 (16) | 0.006 (8) | 0.088 | 0.024 | 0.94 | 2e-11 | 7e-10 |
| C3 | O-Dyn+B vs O-Cls+B | WH | L2+L3 | 0.076 | 0.99 (16) | 0.53 (8) | 1.00 | 1.00 | 0.94 | 2e-11 | 5e-10 |
| C4a | VINS+O-Dyn+B vs VINS+O-Cls+B | WH | L0+L1 | 0.13 | 1.00 (16) | 0.38 (6) | 1.00 | 1.00 | 1.00 | 4e-6 | 8e-5 |
| C4b | VINS+O-Dyn+B vs VINS+O-Cls+B | WH | L2+L3 | 0.037 | 0.59 (16) | 0.22 (6) | 1.00 | 0.98 | 0.94 | 4e-11 | 1e-9 |
| C5a | O-Dyn+B vs O-Cls+B | VIODE | none+low | 0.43 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.33 | 1.00 |
| C5b | O-Dyn+B vs O-Cls+B | VIODE | mid+high | 0.32 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.22 | 1.00 |
| C6 | SAVIOR vs Y-Cls | WH | L0+L1 | 0.036 | 0.47 (16) | 0.26 (8) | 1.00 | 0.98 | 0.94 | 6e-7 | 1e-5 |
| C7 | SAVIOR vs Y-Cls | WH | L2+L3 | 0.20 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.001 | 0.016 |
| C8a | VINS+SAVIOR vs VINS+Y-Cls | WH | L0+L1 | 0.034 | 0.47 (16) | 0.17 (6) | 1.00 | 0.95 | 0.94 | 9e-10 | 2e-8 |
| C8b | VINS+SAVIOR vs VINS+Y-Cls | WH | L2+L3 | 0.11 | 1.00 (16) | 0.37 (6) | 1.00 | 1.00 | 1.00 | 4e-6 | 8e-5 |
| C9a | SAVIOR vs Y-Cls | VIODE | none+low | 0.60 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.63 | 1.00 |
| C9b | SAVIOR vs Y-Cls | VIODE | mid+high | 0.68 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.58 | 1.00 |
| C9c | VINS+SAVIOR vs VINS+Y-Cls | VIODE | none+low | 0.11 | 1.00 (16) | 0.63 (6) | 1.00 | 1.00 | 1.00 | 0.009 | 0.094 |
| C10 | Y-Cls vs OpenVINS | WH | L0 | 0.26 | 1.00 (9) | 0.79 (4) | 1.00 | 1.00 | 1.00 | 10e-5 | 0.002 |
| C11 | O-Cls+B vs OpenVINS | WH | L0 | 0.039 | 0.36 (9) | 0.16 (4) | 1.00 | 0.99 | 1.00 | 2e-9 | 5e-8 |
| C12 | SAVIOR vs OpenVINS | WH | L0 | 0.36 | 1.00 (9) | 0.79 (4) | 1.00 | 1.00 | 1.00 | 0.17 | 1.00 |
| C13a | VINS+Y-Cls vs VINS-Fusion | WH | L0 | 0.057 | 0.45 (9) | 0.23 (4) | 1.00 | 1.00 | 1.00 | 0.001 | 0.016 |
| C13b | VINS+SAVIOR vs VINS-Fusion | WH | L0 | 0.56 | 1.00 (9) | 1.00 (4) | 1.00 | 1.00 | 1.00 | 0.16 | 1.00 |
| C15 | SAVIOR vs OpenVINS | WH | L2+L3 | 0.24 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.005 | 0.054 |
| C15b | Y-Cls vs OpenVINS | WH | L2+L3 | 0.65 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.47 | 1.00 |
| C16 | VINS+SAVIOR vs VINS-Fusion | WH | L2+L3 | 0.14 | 1.00 (16) | 0.37 (6) | 1.00 | 1.00 | 1.00 | 1e-5 | 2e-4 |
| C17 | VINS+Y-Cls vs VINS-Fusion | WH | L2+L3 | 0.043 | 0.61 (16) | 0.22 (6) | 1.00 | 1.00 | 1.00 | 8e-9 | 2e-7 |
| C18 | VINS+O-Dyn+B vs VINS-Fusion | WH | L2+L3 | 0.65 | 1.00 (16) | 0.65 (6) | 1.00 | 1.00 | 1.00 | 0.19 | 1.00 |
| C19 | VINS+SAVIOR vs VINS-Fusion | VIODE | mid+high | 0.017 | 0.23 (16) | 0.083 (6) | 1.00 | 0.48 | 1.00 | 8e-8 | 2e-6 |
| C20 | SAVIOR vs DynaVINS | VIODE | all | 0.076 | 0.76 (16) | 0.076 (2) | 1.00 | 1.00 | 1.00 | 1e-5 | 2e-4 |
| C21 | SAVIOR vs VINS-Fusion | VIODE | all | 0.001 | 0.024 (16) | 0.003 (2) | 0.17 | 0.044 | 0.015 | 2e-14 | 6e-13 |
| C22 | SAVIOR vs DynaVINS | WH | all | 0.11 | 0.98 (16) | 0.22 (2) | 1.00 | 1.00 | 1.00 | 1e-6 | 3e-5 |
| C22b | SAVIOR vs VINS-Fusion | WH | L2+L3 | 0.38 | 1.00 (16) | 0.38 (2) | 1.00 | 1.00 | 1.00 | 0.71 | 1.00 |
| C23 | SAVIOR-edge vs SAVIOR | WH | L0+L1 | 0.076 | 0.91 (16) | 0.46 (8) | 1.00 | 1.00 | 0.94 | 0.002 | 0.026 |
| C25 | SAVIOR-adaptive vs Y-Cls | WH | L2+L3 | 0.29 | 1.00 (16) | 1.00 (8) | 1.00 | 1.00 | 1.00 | 0.003 | 0.032 |
