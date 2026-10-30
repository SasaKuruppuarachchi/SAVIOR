# Paired failure differences (per-trajectory failure rate A - B, sign-flip on trajectories; failure = ATE > 2 m or no estimate)

| id | comparison | group | fails A / runs | fails B / runs | mean diff [pp] | sign-flip p | n traj |
|---|---|---|---|---|---|---|---|
| P1 | O-Dyn+B vs O-Cls+B | high | 0 / 240 | 10 / 240 | -4.17 | 0.125 | 24 |
| P2 | SAVIOR vs Y-Cls | high | 1 / 240 | 5 / 240 | -1.67 | 0.219 | 24 |
| P3 | SAVIOR vs Y-Cls | low | 0 / 240 | 2 / 240 | -0.83 | 1.000 | 24 |
| P4 | SAVIOR vs OpenVINS | high | 1 / 240 | 12 / 240 | -4.58 | 0.008 | 24 |
| P5 | SAVIOR vs OpenVINS | static | 0 / 120 | 0 / 120 | +0.00 | 1.000 | 24 |
| S1 | VINS+SAVIOR vs VINS+Y-Cls | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S2 | VINS+SAVIOR vs VINS+Y-Cls | low | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S3 | VINS+SAVIOR vs VINS-Fusion | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S5 | VINS+Y-Cls vs VINS-Fusion | static | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S6 | VINS+SAVIOR vs VINS-Fusion | static | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| S7 | SAVIOR vs DynaVINS (upstream) | high | 1 / 240 | 0 / 0 | +0.42 | 1.000 | 24 |
| S8 | SAVIOR vs DynaVINS (upstream) | low | 0 / 240 | 0 / 0 | +0.00 | 1.000 | 24 |
| S9 | SAVIOR-edge vs SAVIOR | high | 1 / 240 | 1 / 240 | +0.00 | 1.000 | 24 |
| S10 | SAVIOR-edge vs SAVIOR | low | 0 / 240 | 0 / 240 | +0.00 | 1.000 | 24 |
| S11 | Y-Cls vs OpenVINS | static | 1 / 120 | 0 / 120 | +0.83 | 1.000 | 24 |
| S12 | O-Dyn+B vs OpenVINS | high | 0 / 240 | 12 / 240 | -5.00 | 0.004 | 24 |
| S13 | SAVIOR vs OpenVINS | low | 0 / 240 | 0 / 240 | +0.00 | 1.000 | 24 |
| S14 | DynaVINS (upstream) vs VINS-Fusion | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM1 | DynaVINS+SAVIOR vs DynaVINS+Y-Cls | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM2 | DynaVINS+SAVIOR vs DynaVINS+Y-Cls | low | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM3 | DynaVINS+SAVIOR vs DynaVINS (det.) | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM4 | DynaVINS+SAVIOR vs DynaVINS (det.) | low | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM5 | DynaVINS+O-Dyn+B vs DynaVINS+O-Cls+B | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM6 | DynaVINS+Y-Cls vs DynaVINS (det.) | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM7 | DynaVINS+SAVIOR vs DynaVINS (det.) | static | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM8 | DynaVINS+Y-Cls vs DynaVINS (det.) | static | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
| DM9 | DynaVINS (det.) vs DynaVINS (upstream) | high | 0 / 0 | 0 / 0 | +0.00 | 1.000 | 24 |
