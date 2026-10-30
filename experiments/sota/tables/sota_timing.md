# M3b SOTA per-frame processing time

Serial runs: one savior-sota:noetic container at a time (--cpus 4, OMP 2 threads, as the benchmark), run 1 (first offset), rate 0.5. VINS-Fusion / DynaVINS: front-end = feature tracking per stereo pair (20 Hz); back-end = sliding-window optimisation per processed frame (every 2nd pair, multiple_thread=1). ORB-SLAM3: TrackStereo per stereo pair (tracking thread only; local mapping runs in its own thread). load1 = host 1-min load average at start, containers = running docker containers on the host at start (other users' jobs included).

| dataset | seq | method | component | n | median ms | mean ms | p90 ms | max ms | load1 | containers |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| viode | city_day_high | DynaVINS | frontend | 1246 | 7.43 | 7.35 | 8.08 | 10.79 | 2.09 | 2 |
| viode | city_day_high | DynaVINS | backend | 623 | 52.49 | 47.35 | 61.68 | 96.63 | 2.09 | 2 |
| viode | city_day_high | DynaVINS | per stereo pair (fe + be amortised) | 1246 | - | 31.03 | - | - | 2.09 | 2 |
| viode | city_day_high | ORB-SLAM3 | track_all | 1246 | 16.0 | 15.76 | 17.25 | 21.0 | 4.71 | 2 |
| viode | city_day_high | ORB-SLAM3 | track_ok | 1238 | 16.01 | 15.79 | 17.26 | 21.0 | 4.71 | 2 |
| viode | city_day_high | VINS-Fusion | frontend | 1246 | 7.25 | 7.26 | 7.88 | 11.36 | 1.22 | 2 |
| viode | city_day_high | VINS-Fusion | backend | 623 | 16.96 | 16.79 | 24.09 | 30.67 | 1.22 | 2 |
| viode | city_day_high | VINS-Fusion | per stereo pair (fe + be amortised) | 1246 | - | 15.66 | - | - | 1.22 | 2 |
| viode | parking_lot_high | DynaVINS | frontend | 1082 | 6.82 | 6.66 | 7.42 | 10.17 | 2.83 | 2 |
| viode | parking_lot_high | DynaVINS | backend | 541 | 21.69 | 22.53 | 32.15 | 153.89 | 2.83 | 2 |
| viode | parking_lot_high | DynaVINS | per stereo pair (fe + be amortised) | 1082 | - | 17.92 | - | - | 2.83 | 2 |
| viode | parking_lot_high | ORB-SLAM3 | track_all | 1082 | 13.85 | 13.58 | 14.95 | 18.99 | 1.33 | 2 |
| viode | parking_lot_high | ORB-SLAM3 | track_ok | 1069 | 13.87 | 13.64 | 14.96 | 18.99 | 1.33 | 2 |
| viode | parking_lot_high | VINS-Fusion | frontend | 1082 | 6.91 | 7.01 | 7.65 | 10.74 | 4.84 | 2 |
| viode | parking_lot_high | VINS-Fusion | backend | 541 | 11.44 | 11.68 | 16.08 | 21.47 | 4.84 | 2 |
| viode | parking_lot_high | VINS-Fusion | per stereo pair (fe + be amortised) | 1082 | - | 12.85 | - | - | 4.84 | 2 |
| warehouse | hall_t2_L3 | DynaVINS | frontend | 2244 | 5.46 | 5.35 | 5.82 | 9.38 | 3.26 | 2 |
| warehouse | hall_t2_L3 | DynaVINS | backend | 1122 | 40.75 | 39.49 | 56.08 | 122.64 | 3.26 | 2 |
| warehouse | hall_t2_L3 | DynaVINS | per stereo pair (fe + be amortised) | 2244 | - | 25.09 | - | - | 3.26 | 2 |
| warehouse | hall_t2_L3 | VINS-Fusion | frontend | 2244 | 5.7 | 5.69 | 6.07 | 10.98 | 2.33 | 2 |
| warehouse | hall_t2_L3 | VINS-Fusion | backend | 1122 | 14.43 | 14.27 | 19.24 | 29.2 | 2.33 | 2 |
| warehouse | hall_t2_L3 | VINS-Fusion | per stereo pair (fe + be amortised) | 2244 | - | 12.83 | - | - | 2.33 | 2 |
