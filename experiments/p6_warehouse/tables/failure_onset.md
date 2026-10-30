# failure anatomy (ATE > 2.0 m): divergence onset [s from bag start] (speed > 2.5 m/s), "drift" = failed without diverging

| seq | method | failed runs | onsets (run: ATE m @ onset s) |
|---|---|--:|---|
| aisles_t1_L2 | oracle_class_naive | 1 | 05: 1.97e+03 @ 12.5 |
| aisles_t1_L2 | oracle_moving | 1 | 09: 4.75 @ 17.8 |
| aisles_t1_L2 | yolo_p4_noext | 1 | 09: 263 @ 15.3 |
| aisles_t1_L3 | openvins | 1 | 10: 2.67e+03 @ 12.0 |
| aisles_t1_L3 | savior_none | 1 | 10: 2.67e+03 @ 12.0 |
| hall_t1_L2 | openvins | 1 | 06: 1.62e+03 @ 12.8 |
| hall_t1_L2 | savior_none | 1 | 06: 1.62e+03 @ 12.8 |
| hall_t1_L2 | savior_none+nocompat | 1 | 06: 1.76e+03 @ 12.8 |
| hall_t1_L3 | openvins | 10 | 01: 5.23 @ drift, 02: 4.93 @ drift, 03: 4.56 @ drift, 04: 3.39e+03 @ 9.5, 05: 849 @ 12.0, 06: 6.77e+03 @ 7.8, 07: 5e+03 @ 9.5, 08: 8.7e+03 @ 8.1, 09: 2.72e+03 @ 13.2, 10: 1.34e+03 @ 17.5 |
| hall_t1_L3 | oracle_class_naive | 2 | 01: 814 @ 17.0, 04: 560 @ 15.1 |
| hall_t1_L3 | oracle_moving | 1 | 09: 8.62e+03 @ 9.2 |
| hall_t1_L3 | savior_none | 10 | 01: 5.23 @ drift, 02: 4.93 @ drift, 03: 4.56 @ drift, 04: 3.39e+03 @ 9.5, 05: 849 @ 12.0, 06: 6.77e+03 @ 7.8, 07: 5e+03 @ 9.5, 08: 8.7e+03 @ 8.1, 09: 2.72e+03 @ 13.2, 10: 1.34e+03 @ 17.5 |
| hall_t1_L3 | yolo_coco_person_p4 | 10 | 01: 5.12 @ drift, 02: 5.04 @ 29.6, 03: 1.51e+03 @ 13.7, 04: 4.88 @ drift, 05: 937 @ 18.2, 06: 884 @ 14.2, 07: 2.53e+03 @ 13.3, 08: 2.16 @ drift, 09: 2.46e+03 @ 12.7, 10: 1.39e+03 @ 17.0 |
| hall_t1_L3 | yolo_p4 | 9 | 01: 4.51 @ drift, 02: 6.65e+03 @ 7.2, 03: 77.4 @ 31.0, 04: 2.07 @ drift, 05: 4.11 @ drift, 06: 1.01e+03 @ 18.2, 07: 9.51e+03 @ 7.7, 08: 4.31 @ drift, 10: 3.66e+03 @ 11.8 |
| hall_t1_L3 | yolo_p4_noext | 10 | 01: 1.17e+03 @ 17.2, 02: 181 @ 37.0, 03: 711 @ 20.5, 04: 6.63 @ 10.2, 05: 15.6 @ 83.8, 06: 7.56 @ drift, 07: 2.38 @ drift, 08: 8.46 @ drift, 09: 2.16e+03 @ 14.1, 10: 7.69 @ drift |
| hall_t1_L3 | yolo_p4_nointer | 8 | 01: 1.47e+03 @ 16.7, 02: 1.36e+03 @ 18.8, 03: 445 @ 17.6, 04: 4.04 @ drift, 05: 2.25 @ drift, 08: 4.15 @ drift, 09: 1.27e+03 @ 16.6, 10: 3.26e+03 @ 12.4 |
| hall_t1_L3 | yolo_p6 | 6 | 01: 1.01e+04 @ 6.9, 03: 9.81e+03 @ 6.9, 04: 6.83e+03 @ 9.0, 05: 6.16e+03 @ 7.2, 09: 5.08e+03 @ 9.3, 10: 2.9e+03 @ 11.5 |
