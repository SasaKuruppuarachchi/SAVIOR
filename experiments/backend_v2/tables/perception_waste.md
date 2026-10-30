# Perception work on frames the filter drops (t1, savior-launch methods)

frames = savior_node frames (one mask pair each); meas = OpenVINS measurements (FINAL); dropped share = node_total time on frames the filter never processes / all node time; hold = FINAL mask hold time (image waits for its masks) avg / max over runs; edge: deferred masks attached, features flagged, too_late (SAVIOR-edge only)

| method | backend | runs | frames/run | meas/run | dropped share of node time | node ms kept / dropped (median) | hold avg ms | hold max ms | edge deferred / flagged / too_late (per run) |
|---|---|--:|--:|--:|--:|--:|--:|--:|---|
| sens_fix1 | v2 | 80 | 2199 | 1100 | 50.0 % | 27.4 / 27.4 | 29.6 | 251.8 | - |
| sens_fix1 | v1 | 80 | 2199 | 2199 | 0.0 % | 22.6 / 3.0 | 25.4 | 218.8 | - |
| p7_nb | v2 | 80 | 2199 | 1100 | 50.0 % | 28.0 / 28.4 | 31.2 | 366.9 | - |
| p7_nb | v1 | 80 | 2199 | 2199 | 0.0 % | 24.3 / 3.5 | 26.8 | 227.9 | - |
| oracle_class_ext | v2 | 80 | 2199 | 1100 | 50.0 % | 13.1 / 13.1 | 13.9 | 113.8 | - |
| oracle_class_ext | v1 | 80 | 2199 | 2199 | 0.0 % | 13.0 / 1.5 | 13.2 | 64.5 | - |
| yolo_naive | v2 | 80 | 2199 | 1100 | 50.1 % | 20.0 / 20.1 | 20.2 | 186.2 | - |
| yolo_naive | v1 | 80 | 2199 | 2199 | 0.0 % | 49.3 / 32.7 | 54.2 | 1005.3 | - |
| oracle_moving_ext | v2 | 80 | 2199 | 1100 | 50.0 % | 5.3 / 5.3 | 6.6 | 102.8 | - |
| oracle_moving_ext | v1 | 80 | 2199 | 2199 | 0.0 % | 4.7 / 1.4 | 5.9 | 104.4 | - |
| oracle_moving | v2 | 80 | 2199 | 1100 | 50.0 % | 7.9 / 8.1 | 11.1 | 522.1 | - |
| oracle_moving | v1 | 80 | 2199 | 2199 | 0.0 % | 10.1 / 3.0 | 15.3 | 317.7 | - |
| oracle_class_naive | v2 | 80 | 2199 | 1100 | 49.9 % | 13.0 / 13.0 | 15.3 | 634.8 | - |
| oracle_class_naive | v1 | 80 | 2199 | 2199 | 0.0 % | 14.6 / 2.5 | 19.0 | 328.3 | - |
| savior_none | v2 | 80 | 2199 | 1100 | 50.0 % | 0.4 / 0.4 | 0.9 | 50.4 | - |
| savior_none | v1 | 80 | 2199 | 2199 | 0.0 % | 0.4 / 0.2 | 0.9 | 95.2 | - |
| savior_edge | v2 | 80 | 2199 | 1100 | 50.0 % | 27.1 / 27.0 | 28.9 | 221.9 | 2193 / 2862 / 0 |
| savior_edge | v1 | 80 | 2199 | 2199 | 0.0 % | 26.2 / 3.7 | 28.8 | 361.5 | 2194 / 3617 / 0 |
