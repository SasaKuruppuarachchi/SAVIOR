# EDGE per-stage CPU per camera frame (desktop, offline profile, 1 thread; mean of hall_t1_L3 + aisles_t1_L3, 600 frames each)

Python share = 1 - (native OpenCV/numpy/C tottime attributed to the pipeline) / wall. Orin = x3.5 (estimate).

| variant | depth | motion | gating | tracking | compose | predict | glue | seg host | node I/O | pipeline+node CPU | Python share of pipeline | Orin CPU est. | Orin GPU est. |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| main | 8.07 | 8.10 | 1.10 | 1.63 | 1.34 | 0.00 | 0.48 | 2.40 | 0.60 | 23.7 | 45 % | 83 | 10.2 |
| sparse depth | 0.20 | 11.29 | 1.17 | 1.69 | 1.39 | 0.00 | 0.52 | 2.40 | 0.60 | 19.3 | 50 % | 67 | 10.2 |
| async 10 Hz | 4.12 | 3.99 | 0.56 | 0.76 | 0.59 | 2.19 | 0.00 | 1.20 | 0.60 | 14.0 | 47 % | 49 | 5.1 |
| async 5 Hz | 2.04 | 1.93 | 0.28 | 0.35 | 0.28 | 2.91 | 0.00 | 0.60 | 0.60 | 9.0 | 45 % | 31 | 2.5 |
| sparse+10 Hz | 0.09 | 5.18 | 0.56 | 0.71 | 0.57 | 2.24 | 0.00 | 1.20 | 0.60 | 11.2 | 48 % | 39 | 5.1 |
| sparse+5 Hz | 0.05 | 2.59 | 0.28 | 0.34 | 0.26 | 2.95 | 0.00 | 0.60 | 0.60 | 7.7 | 49 % | 27 | 2.5 |
| YOLO26n | 8.07 | 8.10 | 1.10 | 1.63 | 1.34 | 0.00 | 0.48 | 2.40 | 0.60 | 23.7 | 45 % | 83 | 3.9 |
