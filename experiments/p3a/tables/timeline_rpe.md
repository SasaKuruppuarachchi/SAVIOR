# P3a local RPE (10 s windows, 1 s grid, t >= 40 s) vs human coverage of the window

Spearman rho / p between the window mean human-mask area fraction and the window error difference; mean over offsets of the per-window values first.

p (naive) ignores the overlap of the 10 s windows; p_shift = circular-shift permutation test (coverage series shifted against the error series, both autocorrelations kept); rho_nov = 10 s-spaced non-overlapping windows.

| seq | comparison | windows | rho | p (naive) | p_shift | rho_nov (p) | ref mean local RPE [m] | mean diff [m] all | mean diff top-20 % coverage | mean diff zero coverage |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 06h | savior_none - openvins (06h) | 460 | -0.164 | 0.000413 | 0.082 | -0.007 (0.96) | 0.0486 | +0.0007 | -0.0015 | +0.0014 |
| 06h | oracle_person - openvins (06h) | 460 | -0.125 | 0.00729 | 0.485 | +0.049 (0.74) | 0.0486 | +0.0003 | -0.0010 | +0.0012 |
| 06h | oracle_person_ext - openvins (06h) | 460 | -0.262 | 1.2e-08 | 0.149 | -0.126 (0.4) | 0.0486 | +0.0001 | -0.0030 | +0.0032 |
| 06h | oracle_person_after_init - openvins (06h) | 460 | -0.051 | 0.272 | 0.731 | +0.165 (0.27) | 0.0486 | +0.0016 | +0.0022 | +0.0021 |
| 06h | yolo_full - openvins (06h) | 460 | -0.059 | 0.209 | 0.672 | +0.002 (0.99) | 0.0486 | +0.0007 | +0.0035 | +0.0028 |
| 06h | yolo_naive - openvins (06h) | 460 | -0.010 | 0.828 | 0.985 | -0.012 (0.94) | 0.0486 | +0.0047 | +0.0051 | +0.0052 |
| 06h | oracle_observe - openvins (06h) | 460 | -0.121 | 0.00912 | 0.172 | +0.155 (0.3) | 0.0486 | +0.0020 | +0.0006 | +0.0031 |
| 06h | openvins 06h - openvins 00h | 460 | -0.011 | 0.809 | 0.933 | -0.005 (0.97) | 0.0496 | -0.0010 | -0.0161 | +0.0035 |
| 06h | oracle_person 06h - savior_none 06h | 460 | +0.018 | 0.7 | 0.896 | +0.068 (0.65) | 0.0493 | -0.0004 | +0.0004 | -0.0001 |
| 12h | savior_none - openvins (12h) | 465 | +0.003 | 0.947 | 0.963 | +0.050 (0.74) | 0.0545 | +0.0007 | +0.0012 | +0.0010 |
| 12h | oracle_person - openvins (12h) | 465 | -0.154 | 0.000842 | 0.215 | -0.120 (0.42) | 0.0545 | -0.0006 | +0.0001 | +0.0011 |
| 12h | oracle_person_ext - openvins (12h) | 465 | -0.075 | 0.108 | 0.504 | -0.149 (0.32) | 0.0545 | -0.0018 | -0.0004 | -0.0060 |
| 12h | oracle_person_after_init - openvins (12h) | 465 | -0.190 | 3.7e-05 | 0.274 | -0.195 (0.19) | 0.0545 | -0.0017 | -0.0034 | +0.0010 |
| 12h | yolo_full - openvins (12h) | 465 | -0.036 | 0.44 | 0.667 | +0.028 (0.85) | 0.0545 | +0.0003 | +0.0030 | -0.0013 |
| 12h | yolo_naive - openvins (12h) | 465 | -0.097 | 0.0357 | 0.348 | -0.101 (0.5) | 0.0545 | +0.0006 | -0.0015 | +0.0030 |
| 12h | oracle_observe - openvins (12h) | 465 | -0.004 | 0.936 | 0.985 | +0.091 (0.54) | 0.0545 | +0.0012 | +0.0005 | +0.0003 |
| 12h | openvins 12h - openvins 00h | 465 | -0.151 | 0.0011 | 0.193 | -0.137 (0.36) | 0.0495 | +0.0051 | +0.0002 | +0.0235 |
| 12h | oracle_person 12h - savior_none 12h | 465 | -0.152 | 0.000977 | 0.133 | -0.191 (0.2) | 0.0553 | -0.0013 | -0.0011 | +0.0001 |

OpenVINS window RPE vs coverage within a sequence (Spearman), mean over offsets:

- 06h: rho = +0.246 (naive p = 8.55e-08, circular-shift p = 0.052), n = 460
- 12h: rho = -0.192 (naive p = 3.1e-05, circular-shift p = 0.067), n = 465
