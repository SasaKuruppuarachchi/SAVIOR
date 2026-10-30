# P5 motion-evidence / masking decision vs GT motion label (VIODE vehicle_ids: vehicle_dynamic_* move, vehicle_static_* are parked). Unit: YOLO vehicle instance per frame with >= 30 % of its pixels on a GT vehicle (label = majority of dynamic vs static GT pixels). "moving" = masked (core). For yolo_naive / yolo_full_p2 every vehicle is masked by construction.

| seq | variant | n dyn | n static | n no-GT (FP det) | moving precision | moving recall | static kept (unmasked) | FP det masked |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| parking_lot_none | yolo_naive | 0 | 361 | 4 | 0.000 | - | 0.000 | 1.000 |
| parking_lot_none | yolo_full_p2 | 0 | 361 | 4 | 0.000 | - | 0.000 | 1.000 |
| parking_lot_none | yolo_p4_dyn | 0 | 361 | 4 | 0.000 | - | 0.000 | 1.000 |
| parking_lot_none | yolo_p4_pot | 0 | 361 | 4 | - | - | 1.000 | 0.000 |
| parking_lot_low | yolo_naive | 109 | 359 | 3 | 0.233 | 1.000 | 0.000 | 1.000 |
| parking_lot_low | yolo_full_p2 | 109 | 359 | 3 | 0.233 | 1.000 | 0.000 | 1.000 |
| parking_lot_low | yolo_p4_dyn | 109 | 359 | 3 | 0.233 | 1.000 | 0.000 | 1.000 |
| parking_lot_low | yolo_p4_pot | 109 | 359 | 3 | 1.000 | 0.908 | 1.000 | 0.000 |
| parking_lot_mid | yolo_naive | 339 | 315 | 5 | 0.518 | 1.000 | 0.000 | 1.000 |
| parking_lot_mid | yolo_full_p2 | 339 | 315 | 5 | 0.518 | 1.000 | 0.000 | 1.000 |
| parking_lot_mid | yolo_p4_dyn | 339 | 315 | 5 | 0.518 | 1.000 | 0.000 | 1.000 |
| parking_lot_mid | yolo_p4_pot | 339 | 315 | 5 | 1.000 | 0.914 | 1.000 | 0.400 |
| parking_lot_high | yolo_naive | 921 | 312 | 7 | 0.747 | 1.000 | 0.000 | 1.000 |
| parking_lot_high | yolo_full_p2 | 921 | 312 | 7 | 0.747 | 1.000 | 0.000 | 1.000 |
| parking_lot_high | yolo_p4_dyn | 921 | 312 | 7 | 0.747 | 1.000 | 0.000 | 1.000 |
| parking_lot_high | yolo_p4_pot | 921 | 312 | 7 | 1.000 | 0.703 | 1.000 | 0.286 |
| city_day_none | yolo_naive | 0 | 684 | 115 | 0.000 | - | 0.000 | 1.000 |
| city_day_none | yolo_full_p2 | 0 | 684 | 115 | 0.000 | - | 0.000 | 1.000 |
| city_day_none | yolo_p4_dyn | 0 | 684 | 115 | 0.000 | - | 0.000 | 1.000 |
| city_day_none | yolo_p4_pot | 0 | 684 | 115 | 0.000 | - | 0.965 | 0.000 |
| city_day_low | yolo_naive | 40 | 684 | 108 | 0.055 | 1.000 | 0.000 | 1.000 |
| city_day_low | yolo_full_p2 | 40 | 684 | 108 | 0.055 | 1.000 | 0.000 | 1.000 |
| city_day_low | yolo_p4_dyn | 40 | 684 | 108 | 0.055 | 1.000 | 0.000 | 1.000 |
| city_day_low | yolo_p4_pot | 40 | 684 | 108 | 0.588 | 0.750 | 0.969 | 0.000 |
| city_day_mid | yolo_naive | 189 | 642 | 96 | 0.227 | 1.000 | 0.000 | 1.000 |
| city_day_mid | yolo_full_p2 | 189 | 642 | 96 | 0.227 | 1.000 | 0.000 | 1.000 |
| city_day_mid | yolo_p4_dyn | 189 | 642 | 96 | 0.227 | 1.000 | 0.000 | 1.000 |
| city_day_mid | yolo_p4_pot | 189 | 642 | 96 | 0.864 | 0.809 | 0.963 | 0.010 |
| city_day_high | yolo_naive | 813 | 596 | 107 | 0.577 | 1.000 | 0.000 | 1.000 |
| city_day_high | yolo_full_p2 | 813 | 596 | 107 | 0.577 | 1.000 | 0.000 | 1.000 |
| city_day_high | yolo_p4_dyn | 813 | 596 | 107 | 0.577 | 1.000 | 0.000 | 1.000 |
| city_day_high | yolo_p4_pot | 813 | 596 | 107 | 0.908 | 0.643 | 0.911 | 0.000 |
| city_night_none | yolo_naive | 0 | 158 | 12 | 0.000 | - | 0.000 | 1.000 |
| city_night_none | yolo_full_p2 | 0 | 158 | 12 | 0.000 | - | 0.000 | 1.000 |
| city_night_none | yolo_p4_dyn | 0 | 158 | 12 | 0.000 | - | 0.000 | 1.000 |
| city_night_none | yolo_p4_pot | 0 | 158 | 12 | 0.000 | - | 0.981 | 0.000 |
| city_night_low | yolo_naive | 70 | 157 | 13 | 0.308 | 1.000 | 0.000 | 1.000 |
| city_night_low | yolo_full_p2 | 70 | 157 | 13 | 0.308 | 1.000 | 0.000 | 1.000 |
| city_night_low | yolo_p4_dyn | 70 | 157 | 13 | 0.308 | 1.000 | 0.000 | 1.000 |
| city_night_low | yolo_p4_pot | 70 | 157 | 13 | 0.985 | 0.929 | 0.994 | 0.000 |
| city_night_mid | yolo_naive | 193 | 158 | 14 | 0.550 | 1.000 | 0.000 | 1.000 |
| city_night_mid | yolo_full_p2 | 193 | 158 | 14 | 0.550 | 1.000 | 0.000 | 1.000 |
| city_night_mid | yolo_p4_dyn | 193 | 158 | 14 | 0.550 | 1.000 | 0.000 | 1.000 |
| city_night_mid | yolo_p4_pot | 193 | 158 | 14 | 0.988 | 0.860 | 0.987 | 0.000 |
| city_night_high | yolo_naive | 562 | 160 | 97 | 0.778 | 1.000 | 0.000 | 1.000 |
| city_night_high | yolo_full_p2 | 562 | 160 | 97 | 0.778 | 1.000 | 0.000 | 1.000 |
| city_night_high | yolo_p4_dyn | 562 | 160 | 97 | 0.778 | 1.000 | 0.000 | 1.000 |
| city_night_high | yolo_p4_pot | 562 | 160 | 97 | 0.992 | 0.454 | 0.988 | 0.000 |

## pooled over sequences
| variant | n dyn | n static | moving precision | moving recall | static kept | FP det masked |
|---|--:|--:|--:|--:|--:|--:|
| yolo_naive | 3236 | 4586 | 0.414 | 1.000 | 0.000 | 1.000 |
| yolo_full_p2 | 3236 | 4586 | 0.414 | 1.000 | 0.000 | 1.000 |
| yolo_p4_dyn | 3236 | 4586 | 0.414 | 1.000 | 0.000 | 1.000 |
| yolo_p4_pot | 3236 | 4586 | 0.945 | 0.695 | 0.972 | 0.009 |

## per GT vehicle: share of its YOLO-detected frames that are masked (n frames)
| seq | vehicle | yolo_p4_dyn | yolo_p4_pot |
|---|---|--:|--:|
| parking_lot_none | vehicle_static_0 | 1.00 (247) | 0.00 (247) |
| parking_lot_none | vehicle_static_1 | 1.00 (114) | 0.00 (114) |
| parking_lot_low | vehicle_dynamic_5 | 1.00 (109) | 0.91 (109) |
| parking_lot_low | vehicle_static_0 | 1.00 (246) | 0.00 (246) |
| parking_lot_low | vehicle_static_1 | 1.00 (113) | 0.00 (113) |
| parking_lot_mid | vehicle_dynamic_4 | 1.00 (235) | 0.91 (235) |
| parking_lot_mid | vehicle_dynamic_5 | 1.00 (104) | 0.93 (104) |
| parking_lot_mid | vehicle_static_0 | 1.00 (248) | 0.00 (248) |
| parking_lot_mid | vehicle_static_1 | 1.00 (67) | 0.00 (67) |
| parking_lot_high | vehicle_dynamic_0 | 1.00 (141) | 0.96 (141) |
| parking_lot_high | vehicle_dynamic_1 | 1.00 (56) | 0.77 (56) |
| parking_lot_high | vehicle_dynamic_2 | 1.00 (274) | 0.43 (274) |
| parking_lot_high | vehicle_dynamic_3 | 1.00 (85) | 0.05 (85) |
| parking_lot_high | vehicle_dynamic_4 | 1.00 (239) | 0.93 (239) |
| parking_lot_high | vehicle_dynamic_5 | 1.00 (126) | 0.97 (126) |
| parking_lot_high | vehicle_static_0 | 1.00 (226) | 0.00 (226) |
| parking_lot_high | vehicle_static_1 | 1.00 (86) | 0.00 (86) |
| city_day_none | vehicle_static_0 | 1.00 (391) | 0.06 (391) |
| city_day_none | vehicle_static_1 | 1.00 (293) | 0.00 (293) |
| city_day_low | vehicle_dynamic_9 | 1.00 (40) | 0.75 (40) |
| city_day_low | vehicle_static_0 | 1.00 (390) | 0.05 (390) |
| city_day_low | vehicle_static_1 | 1.00 (294) | 0.01 (294) |
| city_day_mid | vehicle_dynamic_4 | 1.00 (120) | 0.95 (120) |
| city_day_mid | vehicle_dynamic_9 | 1.00 (34) | 0.73 (34) |
| city_day_mid | vehicle_dynamic_10 | 1.00 (35) | 0.40 (35) |
| city_day_mid | vehicle_static_0 | 1.00 (389) | 0.05 (389) |
| city_day_mid | vehicle_static_1 | 1.00 (253) | 0.02 (253) |
| city_day_high | vehicle_dynamic_2 | 1.00 (238) | 0.24 (238) |
| city_day_high | vehicle_dynamic_3 | 1.00 (40) | 0.65 (40) |
| city_day_high | vehicle_dynamic_4 | 1.00 (136) | 0.76 (136) |
| city_day_high | vehicle_dynamic_5 | 1.00 (172) | 0.95 (172) |
| city_day_high | vehicle_dynamic_6 | 1.00 (109) | 0.82 (109) |
| city_day_high | vehicle_dynamic_7 | 1.00 (46) | 0.41 (46) |
| city_day_high | vehicle_dynamic_9 | 1.00 (50) | 0.96 (50) |
| city_day_high | vehicle_dynamic_10 | 1.00 (22) | 0.77 (22) |
| city_day_high | vehicle_static_0 | 1.00 (362) | 0.15 (362) |
| city_day_high | vehicle_static_1 | 1.00 (234) | 0.00 (234) |
| city_night_none | vehicle_static_0 | 1.00 (158) | 0.02 (158) |
| city_night_low | vehicle_dynamic_6 | 1.00 (70) | 0.93 (70) |
| city_night_low | vehicle_static_0 | 1.00 (157) | 0.01 (157) |
| city_night_mid | vehicle_dynamic_2 | 1.00 (46) | 0.91 (46) |
| city_night_mid | vehicle_dynamic_4 | 1.00 (77) | 0.83 (77) |
| city_night_mid | vehicle_dynamic_6 | 1.00 (70) | 0.86 (70) |
| city_night_mid | vehicle_static_0 | 1.00 (158) | 0.01 (158) |
| city_night_high | vehicle_dynamic_0 | 1.00 (71) | 0.01 (71) |
| city_night_high | vehicle_dynamic_1 | 1.00 (176) | 0.11 (176) |
| city_night_high | vehicle_dynamic_2 | 1.00 (53) | 0.93 (53) |
| city_night_high | vehicle_dynamic_3 | 1.00 (32) | 0.00 (32) |
| city_night_high | vehicle_dynamic_4 | 1.00 (83) | 0.71 (83) |
| city_night_high | vehicle_dynamic_6 | 1.00 (64) | 0.92 (64) |
| city_night_high | vehicle_dynamic_7 | 1.00 (75) | 0.89 (75) |
| city_night_high | vehicle_dynamic_10 | 1.00 (8) | 0.00 (8) |
| city_night_high | vehicle_static_0 | 1.00 (160) | 0.01 (160) |

## yolo_p4_pot / yolo_p4_dyn decisions by stereo depth (pooled; dynamic = GT moving)
| variant | depth bin [m] | n dyn | dyn masked | n static | static masked |
|---|---|--:|--:|--:|--:|
| yolo_p4_dyn | 0-5 | 1172 | 1.00 | 282 | 1.00 |
| yolo_p4_dyn | 5-10 | 1178 | 1.00 | 2846 | 1.00 |
| yolo_p4_dyn | 10-20 | 672 | 1.00 | 1038 | 1.00 |
| yolo_p4_dyn | no depth | 214 | 1.00 | 420 | 1.00 |
| yolo_p4_pot | 0-5 | 1172 | 0.90 | 282 | 0.01 |
| yolo_p4_pot | 5-10 | 1178 | 0.79 | 2846 | 0.03 |
| yolo_p4_pot | 10-20 | 672 | 0.29 | 1038 | 0.02 |
| yolo_p4_pot | no depth | 214 | 0.30 | 420 | 0.04 |
