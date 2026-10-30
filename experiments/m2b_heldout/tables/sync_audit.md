# M2b validity audit (/home/sasa/workspace/savior_ws/results/m2b_heldout/runs)

valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 + poses >= same-offset openvins poses - 1

valid_end = sync ok + trajectory reaches the openvins end (<= 1 frame) + <= 1 pose missing after the method's own first pose (late init allowed)

| method | runs | valid (literal pose rule) | valid_end | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| openvins | 240 | 240 | 240 | 240 | 240 | 0 | 0 | 0 | 0 |
| oracle_class_ext | 240 | 229 | 240 | 240 | 229 | 0 | 0 | 0 | 0 |
| oracle_moving_ext | 240 | 240 | 240 | 240 | 240 | 0 | 0 | 0 | 0 |
| p7_nb | 240 | 230 | 240 | 240 | 230 | 0 | 0 | 0 | 0 |
| savior_edge | 240 | 238 | 240 | 240 | 238 | 0 | 0 | 0 | 0 |
| savior_none | 240 | 240 | 240 | 240 | 240 | 0 | 0 | 0 | 0 |
| sens_fix1 | 240 | 230 | 240 | 240 | 230 | 0 | 0 | 0 | 0 |
| yolo_naive | 240 | 230 | 240 | 240 | 230 | 0 | 0 | 0 | 0 |

**Total: 1877 / 1920 valid (literal pose rule); 1920 / 1920 valid_end; 1920 sync ok.**

Pose-count difference openvins - method (runs): -34: 2, -31: 1, -29: 3, -21: 6, -20: 5, -18: 6, -16: 2, -15: 6, -14: 1, -13: 2, -8: 1, -7: 9, -5: 6, -4: 15, -3: 7, -2: 12, -1: 18, +0: 1429, +1: 106, +2: 1, +4: 3, +5: 1, +6: 1, +10: 1, +14: 1, +18: 1, +19: 6, +21: 1, +22: 2, +24: 1, +25: 1, +26: 1, +28: 1, +29: 1, +30: 7, +31: 6, +32: 1, +33: 6

savior_none == openvins (trajectory md5), warehouse: 120 / 120

savior_none == openvins (trajectory md5), viode: 0 / 120 (differ: city_day_high/run_01, city_day_high/run_02, city_day_high/run_03, city_day_high/run_04, city_day_high/run_05, city_day_high/run_06, city_day_high/run_07, city_day_high/run_08, city_day_high/run_09, city_day_high/run_10, city_day_low/run_01, city_day_low/run_02, city_day_low/run_03, city_day_low/run_04, city_day_low/run_05, city_day_low/run_06, city_day_low/run_07, city_day_low/run_08, city_day_low/run_09, city_day_low/run_10, city_day_mid/run_01, city_day_mid/run_02, city_day_mid/run_03, city_day_mid/run_04, city_day_mid/run_05, city_day_mid/run_06, city_day_mid/run_07, city_day_mid/run_08, city_day_mid/run_09, city_day_mid/run_10, city_day_none/run_01, city_day_none/run_02, city_day_none/run_03, city_day_none/run_04, city_day_none/run_05, city_day_none/run_06, city_day_none/run_07, city_day_none/run_08, city_day_none/run_09, city_day_none/run_10, city_night_high/run_01, city_night_high/run_02, city_night_high/run_03, city_night_high/run_04, city_night_high/run_05, city_night_high/run_06, city_night_high/run_07, city_night_high/run_08, city_night_high/run_09, city_night_high/run_10, city_night_low/run_01, city_night_low/run_02, city_night_low/run_03, city_night_low/run_04, city_night_low/run_05, city_night_low/run_06, city_night_low/run_07, city_night_low/run_08, city_night_low/run_09, city_night_low/run_10, city_night_mid/run_01, city_night_mid/run_02, city_night_mid/run_03, city_night_mid/run_04, city_night_mid/run_05, city_night_mid/run_06, city_night_mid/run_07, city_night_mid/run_08, city_night_mid/run_09, city_night_mid/run_10, city_night_none/run_01, city_night_none/run_02, city_night_none/run_03, city_night_none/run_04, city_night_none/run_05, city_night_none/run_06, city_night_none/run_07, city_night_none/run_08, city_night_none/run_09, city_night_none/run_10, parking_lot_high/run_01, parking_lot_high/run_02, parking_lot_high/run_03, parking_lot_high/run_04, parking_lot_high/run_05, parking_lot_high/run_06, parking_lot_high/run_07, parking_lot_high/run_08, parking_lot_high/run_09, parking_lot_high/run_10, parking_lot_low/run_01, parking_lot_low/run_02, parking_lot_low/run_03, parking_lot_low/run_04, parking_lot_low/run_05, parking_lot_low/run_06, parking_lot_low/run_07, parking_lot_low/run_08, parking_lot_low/run_09, parking_lot_low/run_10, parking_lot_mid/run_01, parking_lot_mid/run_02, parking_lot_mid/run_03, parking_lot_mid/run_04, parking_lot_mid/run_05, parking_lot_mid/run_06, parking_lot_mid/run_07, parking_lot_mid/run_08, parking_lot_mid/run_09, parking_lot_mid/run_10, parking_lot_none/run_01, parking_lot_none/run_02, parking_lot_none/run_03, parking_lot_none/run_04, parking_lot_none/run_05, parking_lot_none/run_06, parking_lot_none/run_07, parking_lot_none/run_08, parking_lot_none/run_09, parking_lot_none/run_10)

Runs failing only the literal pose rule because of a later filter initialisation (end complete, sync ok): 43; init delay vs openvins [s]: median 1.4, max 1.65
