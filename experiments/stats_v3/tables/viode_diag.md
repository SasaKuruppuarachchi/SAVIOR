# VIODE failure diagnosis (failure = ATE > 1 m)

Offsets: run k starts at offset_1 + 0.2 (k-1) s; GT motion onset (speed > 0.1 m/s) is city_day: 4.53, city_night: 6.53, parking_lot: 6.18 s after the GT start. p_late = stratified permutation test (failure labels permuted across offsets within each sequence; one-sided, later offsets). t_div = time from the first estimated pose until the position error exceeds 1 m after a posyaw alignment on the first 1 s of the estimate; init = first pose - playback start.

| system | failures | per offset 1..10 | offsets 1-5 / 6-10 | p_late | failing (sequence: offsets) | init delay (s) | t_div median [range] (s) |
|---|--:|---|--:|--:|---|--:|---|
| OpenVINS-v2 | 11 | 1 1 0 2 1 0 2 2 1 1 | 5 / 6 | 0.32 | parking_lot_low: 2,7,8,9; parking_lot_mid: 4,5,7; parking_lot_high: 8; city_day_high: 10; city_night_low: 1,4 | 2.5 | 1.4 [0.9, 2.6] |
| OV-v2+SAVIOR | 5 | 1 0 0 1 0 1 0 0 0 2 | 2 / 3 | 0.32 | parking_lot_mid: 6; parking_lot_high: 10; city_day_high: 10; city_night_low: 1,4 | 2.5 | 1.5 [0.0, 2.7] |
| OpenVINS-v1 | 4 | 0 0 0 1 1 2 0 0 0 0 | 2 / 2 | 0.60 | parking_lot_high: 4,6; city_day_mid: 5,6 | 3.1 | 2.3 [1.2, 2.4] |
| OV-v1+SAVIOR | 2 | 0 0 0 0 1 1 0 0 0 0 | 1 / 1 | 0.56 | city_day_mid: 5,6 | 2.6 | 2.4 [2.3, 2.4] |
| VINS-Fusion | 16 | 0 0 3 3 1 3 1 1 3 1 | 7 / 9 | 0.22 | parking_lot_low: 3,4,8,9; parking_lot_mid: 3,4,6,9; parking_lot_high: 3,4,6,10; city_day_none: 5,7,9; city_day_mid: 6 | 1.1 | 3.3 [0.0, 12.1] |
| VINS+SAVIOR | 6 | 0 0 2 0 1 1 1 0 1 0 | 3 / 3 | 0.53 | parking_lot_low: 3; parking_lot_high: 3; city_day_none: 5,7,9; city_day_mid: 6 | 1.1 | 4.5 [3.9, 12.1] |
| DynaVINS | 25 | 0 1 0 3 4 4 3 4 3 3 | 8 / 17 | 2e-4 | parking_lot_none: 5; parking_lot_low: 4,5,6,7,8,9,10; parking_lot_mid: 4,5,6,7,8,9,10; parking_lot_high: 2,4,5,6,7,8,9,10; city_day_none: 8; city_day_low: 6 | 1.1 | 1.2 [0.0, 10.8] |
| ORB-SLAM3 | 34 | 3 3 4 3 4 3 3 4 4 3 | 17 / 17 | 0.35 | city_night_none: 1,2,3,4,5,6,7,8,9,10; city_night_low: 1,2,3,4,5,6,8,9; city_night_mid: 3,4,5,7,8,9,10; city_night_high: 1,2,3,5,6,7,8,9,10 | 1.1 | 8.9 [0.9, 22.3] |
