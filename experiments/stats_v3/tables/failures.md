# Failure rates with sequence-clustered CIs

Cell: failures/runs, rate % [95 % cluster-bootstrap CI over sequences], sequences with >= 1 failure; the per-sequence counts follow in the list below. Warehouse failure = ATE > 2 m, VIODE > 1 m.


## WH

| method | L0+L1 | L2+L3 | all | per-sequence failures (all) |
|---|---|---|---|---|
| OpenVINS | 5/60 (8 % [0, 22]; 2/6 seq) | 13/60 (22 % [7, 47]; 5/6 seq) | 18/120 (15 % [4, 29]; 7/12 seq) | aisles_L1:1, aisles_L2:1, aisles_L3:2, hall_L3:1, dock_L1:4, dock_L2:1, dock_L3:8 |
| +Y-Cls | 0/60 (0 % [0, 0]; 0/6 seq) | 10/60 (17 % [0, 47]; 2/6 seq) | 10/120 (8 % [0, 23]; 2/12 seq) | hall_L3:9, dock_L3:1 |
| +SAVIOR | 0/60 (0 % [0, 0]; 0/6 seq) | 4/60 (7 % [0, 20]; 1/6 seq) | 4/120 (3 % [0, 10]; 1/12 seq) | hall_L3:4 |
| +SAVIOR-edge | 1/60 (2 % [0, 5]; 1/6 seq) | 6/60 (10 % [0, 27]; 2/6 seq) | 7/120 (6 % [0, 15]; 3/12 seq) | hall_L3:5, dock_L1:1, dock_L3:1 |
| +O-Dyn+B | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| +O-Cls+B | 0/60 (0 % [0, 0]; 0/6 seq) | 11/60 (18 % [0, 52]; 2/6 seq) | 11/120 (9 % [0, 26]; 2/12 seq) | hall_L3:10, dock_L3:1 |
| OpenVINS v1 | 0/60 (0 % [0, 0]; 0/6 seq) | 19/60 (32 % [8, 57]; 5/6 seq) | 19/120 (16 % [2, 33]; 5/12 seq) | aisles_L2:2, aisles_L3:1, hall_L3:8, dock_L2:1, dock_L3:7 |
| +SAVIOR v1 | 0/60 (0 % [0, 0]; 0/6 seq) | 10/60 (17 % [0, 47]; 2/6 seq) | 10/120 (8 % [0, 23]; 2/12 seq) | hall_L3:9, dock_L3:1 |
| VINS-Fusion | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| VINS+Y-Cls | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| VINS+SAVIOR | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| VINS+O-Dyn+B | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| VINS+O-Cls+B | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| DynaVINS | 0/60 (0 % [0, 0]; 0/6 seq) | 0/60 (0 % [0, 0]; 0/6 seq) | 0/120 (0 % [0, 0]; 0/12 seq) |  |
| ORB-SLAM3 | 60/60 (100 % [100, 100]; 6/6 seq) | 60/60 (100 % [100, 100]; 6/6 seq) | 120/120 (100 % [100, 100]; 12/12 seq) | aisles_L0:10, aisles_L1:10, aisles_L2:10, aisles_L3:10, hall_L0:10, hall_L1:10, hall_L2:10, hall_L3:10, dock_L0:10, dock_L1:10, dock_L2:10, dock_L3:10 |

## VIODE

| method | none+low | mid+high | all | per-sequence failures (all) |
|---|---|---|---|---|
| OpenVINS | 6/60 (10 % [0, 23]; 2/6 seq) | 5/60 (8 % [2, 18]; 3/6 seq) | 11/120 (9 % [2, 18]; 5/12 seq) | parking_lot_low:4, parking_lot_mid:3, parking_lot_high:1, city_day_high:1, city_night_low:2 |
| +Y-Cls | 2/60 (3 % [0, 10]; 1/6 seq) | 3/60 (5 % [2, 8]; 3/6 seq) | 5/120 (4 % [1, 8]; 4/12 seq) | parking_lot_mid:1, parking_lot_high:1, city_day_high:1, city_night_low:2 |
| +SAVIOR | 2/60 (3 % [0, 10]; 1/6 seq) | 3/60 (5 % [2, 8]; 3/6 seq) | 5/120 (4 % [1, 8]; 4/12 seq) | parking_lot_mid:1, parking_lot_high:1, city_day_high:1, city_night_low:2 |
| +SAVIOR-edge | 4/60 (7 % [0, 13]; 2/6 seq) | 6/60 (10 % [2, 23]; 3/6 seq) | 10/120 (8 % [2, 16]; 5/12 seq) | parking_lot_low:2, parking_lot_mid:4, parking_lot_high:1, city_day_high:1, city_night_low:2 |
| +O-Dyn+B | 3/60 (5 % [0, 12]; 2/6 seq) | 3/60 (5 % [2, 8]; 3/6 seq) | 6/120 (5 % [2, 9]; 5/12 seq) | parking_lot_low:1, parking_lot_mid:1, parking_lot_high:1, city_day_high:1, city_night_low:2 |
| +O-Cls+B | 3/60 (5 % [0, 12]; 2/6 seq) | 2/60 (3 % [0, 7]; 2/6 seq) | 5/120 (4 % [1, 8]; 4/12 seq) | parking_lot_low:1, parking_lot_mid:1, parking_lot_high:1, city_night_low:2 |
| OpenVINS v1 | 0/60 (0 % [0, 0]; 0/6 seq) | 4/60 (7 % [0, 13]; 2/6 seq) | 4/120 (3 % [0, 8]; 2/12 seq) | parking_lot_high:2, city_day_mid:2 |
| +SAVIOR v1 | 0/60 (0 % [0, 0]; 0/6 seq) | 2/60 (3 % [0, 10]; 1/6 seq) | 2/120 (2 % [0, 5]; 1/12 seq) | city_day_mid:2 |
| VINS-Fusion | 7/60 (12 % [0, 25]; 2/6 seq) | 9/60 (15 % [2, 28]; 3/6 seq) | 16/120 (13 % [4, 23]; 5/12 seq) | parking_lot_low:4, parking_lot_mid:4, parking_lot_high:4, city_day_none:3, city_day_mid:1 |
| VINS+Y-Cls | 4/60 (7 % [0, 17]; 2/6 seq) | 2/60 (3 % [0, 7]; 2/6 seq) | 6/120 (5 % [1, 11]; 4/12 seq) | parking_lot_low:1, parking_lot_high:1, city_day_none:3, city_day_mid:1 |
| VINS+SAVIOR | 4/60 (7 % [0, 17]; 2/6 seq) | 2/60 (3 % [0, 7]; 2/6 seq) | 6/120 (5 % [1, 11]; 4/12 seq) | parking_lot_low:1, parking_lot_high:1, city_day_none:3, city_day_mid:1 |
| VINS+O-Dyn+B | 4/60 (7 % [0, 17]; 2/6 seq) | 1/60 (2 % [0, 5]; 1/6 seq) | 5/120 (4 % [0, 10]; 3/12 seq) | parking_lot_low:1, city_day_none:3, city_day_mid:1 |
| VINS+O-Cls+B | 3/60 (5 % [0, 12]; 2/6 seq) | 1/60 (2 % [0, 5]; 1/6 seq) | 4/120 (3 % [0, 8]; 3/12 seq) | parking_lot_low:1, city_day_none:2, city_day_mid:1 |
| DynaVINS | 10/60 (17 % [3, 38]; 4/6 seq) | 15/60 (25 % [0, 52]; 2/6 seq) | 25/120 (21 % [4, 39]; 6/12 seq) | parking_lot_none:1, parking_lot_low:7, parking_lot_mid:7, parking_lot_high:8, city_day_none:1, city_day_low:1 |
| ORB-SLAM3 | 18/60 (30 % [0, 63]; 2/6 seq) | 16/60 (27 % [0, 57]; 2/6 seq) | 34/120 (28 % [7, 52]; 4/12 seq) | city_night_none:10, city_night_low:8, city_night_mid:7, city_night_high:9 |

## Paired failure comparisons (key pairs)

run-level exact McNemar (iid; old view) vs exact sign-flip over the sequences whose failure counts differ (new).

| comparison | set | group | fails A / B | p McNemar (runs) | seq. differing | p sign-flip (seq) | per-sequence A-B |
|---|---|---|--:|--:|--:|--:|---|
| SAVIOR vs Y-Cls | WH | L2+L3 | 4 / 10 | 0.031 | 2 | 0.50 | hall_L3:-5, dock_L3:-1 |
| SAVIOR vs Y-Cls | WH | all | 4 / 10 | 0.031 | 2 | 0.50 | hall_L3:-5, dock_L3:-1 |
| SAVIOR-adaptive vs Y-Cls | WH | L0+L1 | 1 / 0 | 1.00 | 1 | 1.00 | dock_L1:+1 |
| SAVIOR-adaptive vs Y-Cls | WH | L2+L3 | 3 / 10 | 0.016 | 1 | 1.00 | hall_L3:-7 |
| SAVIOR-adaptive vs Y-Cls | WH | all | 4 / 10 | 0.070 | 2 | 1.00 | hall_L3:-7, dock_L1:+1 |
| O-Dyn+B vs O-Cls+B | WH | L2+L3 | 0 / 11 | 10e-4 | 2 | 0.50 | hall_L3:-10, dock_L3:-1 |
| O-Dyn+B vs O-Cls+B | WH | all | 0 / 11 | 10e-4 | 2 | 0.50 | hall_L3:-10, dock_L3:-1 |
| SAVIOR vs OpenVINS | WH | L0+L1 | 0 / 5 | 0.062 | 2 | 0.50 | aisles_L1:-1, dock_L1:-4 |
| SAVIOR vs OpenVINS | WH | L2+L3 | 4 / 13 | 0.035 | 5 | 0.50 | aisles_L2:-1, aisles_L3:-2, hall_L3:+3, dock_L2:-1, dock_L3:-8 |
| SAVIOR vs OpenVINS | WH | all | 4 / 18 | 0.003 | 7 | 0.20 | aisles_L1:-1, aisles_L2:-1, aisles_L3:-2, hall_L3:+3, dock_L1:-4, dock_L2:-1, dock_L3:-8 |
| Y-Cls vs OpenVINS | WH | L0+L1 | 0 / 5 | 0.062 | 2 | 0.50 | aisles_L1:-1, dock_L1:-4 |
| Y-Cls vs OpenVINS | WH | L2+L3 | 10 / 13 | 0.65 | 5 | 0.75 | aisles_L2:-1, aisles_L3:-2, hall_L3:+8, dock_L2:-1, dock_L3:-7 |
| Y-Cls vs OpenVINS | WH | all | 10 / 18 | 0.15 | 7 | 0.56 | aisles_L1:-1, aisles_L2:-1, aisles_L3:-2, hall_L3:+8, dock_L1:-4, dock_L2:-1, dock_L3:-7 |
| O-Cls+B vs OpenVINS | WH | L0+L1 | 0 / 5 | 0.062 | 2 | 0.50 | aisles_L1:-1, dock_L1:-4 |
| O-Cls+B vs OpenVINS | WH | L2+L3 | 11 / 13 | 0.82 | 5 | 0.88 | aisles_L2:-1, aisles_L3:-2, hall_L3:+9, dock_L2:-1, dock_L3:-7 |
| O-Cls+B vs OpenVINS | WH | all | 11 / 18 | 0.23 | 7 | 0.64 | aisles_L1:-1, aisles_L2:-1, aisles_L3:-2, hall_L3:+9, dock_L1:-4, dock_L2:-1, dock_L3:-7 |
| O-Dyn+B vs OpenVINS | WH | L0+L1 | 0 / 5 | 0.062 | 2 | 0.50 | aisles_L1:-1, dock_L1:-4 |
| O-Dyn+B vs OpenVINS | WH | L2+L3 | 0 / 13 | 2e-4 | 5 | 0.062 | aisles_L2:-1, aisles_L3:-2, hall_L3:-1, dock_L2:-1, dock_L3:-8 |
| O-Dyn+B vs OpenVINS | WH | all | 0 / 18 | 8e-6 | 7 | 0.016 | aisles_L1:-1, aisles_L2:-1, aisles_L3:-2, hall_L3:-1, dock_L1:-4, dock_L2:-1, dock_L3:-8 |
| SAVIOR-edge vs SAVIOR | WH | L0+L1 | 1 / 0 | 1.00 | 1 | 1.00 | dock_L1:+1 |
| SAVIOR-edge vs SAVIOR | WH | L2+L3 | 6 / 4 | 0.69 | 2 | 0.50 | hall_L3:+1, dock_L3:+1 |
| SAVIOR-edge vs SAVIOR | WH | all | 7 / 4 | 0.45 | 3 | 0.25 | hall_L3:+1, dock_L1:+1, dock_L3:+1 |
| SAVIOR vs DynaVINS | WH | L2+L3 | 4 / 0 | 0.12 | 1 | 1.00 | hall_L3:+4 |
| SAVIOR vs DynaVINS | WH | all | 4 / 0 | 0.12 | 1 | 1.00 | hall_L3:+4 |
| SAVIOR vs VINS-Fusion | WH | L2+L3 | 4 / 0 | 0.12 | 1 | 1.00 | hall_L3:+4 |
| SAVIOR vs VINS-Fusion | WH | all | 4 / 0 | 0.12 | 1 | 1.00 | hall_L3:+4 |
| SAVIOR vs Y-Cls | VIODE | none+low | 2 / 2 | 1.00 | 0 | 1.00 |  |
| SAVIOR vs Y-Cls | VIODE | mid+high | 3 / 3 | 1.00 | 0 | 1.00 |  |
| SAVIOR vs Y-Cls | VIODE | all | 5 / 5 | 1.00 | 0 | 1.00 |  |
| SAVIOR-adaptive vs Y-Cls | VIODE | none+low | 2 / 2 | 1.00 | 0 | 1.00 |  |
| SAVIOR-adaptive vs Y-Cls | VIODE | mid+high | 3 / 3 | 1.00 | 0 | 1.00 |  |
| SAVIOR-adaptive vs Y-Cls | VIODE | all | 5 / 5 | 1.00 | 0 | 1.00 |  |
| O-Dyn+B vs O-Cls+B | VIODE | none+low | 3 / 3 | 1.00 | 0 | 1.00 |  |
| O-Dyn+B vs O-Cls+B | VIODE | mid+high | 3 / 2 | 1.00 | 1 | 1.00 | city_day_high:+1 |
| O-Dyn+B vs O-Cls+B | VIODE | all | 6 / 5 | 1.00 | 1 | 1.00 | city_day_high:+1 |
| SAVIOR vs OpenVINS | VIODE | none+low | 2 / 6 | 0.12 | 1 | 1.00 | parking_lot_low:-4 |
| SAVIOR vs OpenVINS | VIODE | mid+high | 3 / 5 | 0.69 | 1 | 1.00 | parking_lot_mid:-2 |
| SAVIOR vs OpenVINS | VIODE | all | 5 / 11 | 0.11 | 2 | 0.50 | parking_lot_low:-4, parking_lot_mid:-2 |
| Y-Cls vs OpenVINS | VIODE | none+low | 2 / 6 | 0.12 | 1 | 1.00 | parking_lot_low:-4 |
| Y-Cls vs OpenVINS | VIODE | mid+high | 3 / 5 | 0.69 | 1 | 1.00 | parking_lot_mid:-2 |
| Y-Cls vs OpenVINS | VIODE | all | 5 / 11 | 0.11 | 2 | 0.50 | parking_lot_low:-4, parking_lot_mid:-2 |
| O-Cls+B vs OpenVINS | VIODE | none+low | 3 / 6 | 0.25 | 1 | 1.00 | parking_lot_low:-3 |
| O-Cls+B vs OpenVINS | VIODE | mid+high | 2 / 5 | 0.38 | 2 | 0.50 | parking_lot_mid:-2, city_day_high:-1 |
| O-Cls+B vs OpenVINS | VIODE | all | 5 / 11 | 0.070 | 3 | 0.25 | parking_lot_low:-3, parking_lot_mid:-2, city_day_high:-1 |
| O-Dyn+B vs OpenVINS | VIODE | none+low | 3 / 6 | 0.25 | 1 | 1.00 | parking_lot_low:-3 |
| O-Dyn+B vs OpenVINS | VIODE | mid+high | 3 / 5 | 0.62 | 1 | 1.00 | parking_lot_mid:-2 |
| O-Dyn+B vs OpenVINS | VIODE | all | 6 / 11 | 0.12 | 2 | 0.50 | parking_lot_low:-3, parking_lot_mid:-2 |
| SAVIOR-edge vs SAVIOR | VIODE | none+low | 4 / 2 | 0.50 | 1 | 1.00 | parking_lot_low:+2 |
| SAVIOR-edge vs SAVIOR | VIODE | mid+high | 6 / 3 | 0.45 | 1 | 1.00 | parking_lot_mid:+3 |
| SAVIOR-edge vs SAVIOR | VIODE | all | 10 / 5 | 0.18 | 2 | 0.50 | parking_lot_low:+2, parking_lot_mid:+3 |
| VINS+SAVIOR vs VINS+Y-Cls | VIODE | none+low | 4 / 4 | 1.00 | 0 | 1.00 |  |
| VINS+SAVIOR vs VINS+Y-Cls | VIODE | mid+high | 2 / 2 | 1.00 | 0 | 1.00 |  |
| VINS+SAVIOR vs VINS+Y-Cls | VIODE | all | 6 / 6 | 1.00 | 0 | 1.00 |  |
| VINS+SAVIOR vs VINS-Fusion | VIODE | none+low | 4 / 7 | 0.25 | 1 | 1.00 | parking_lot_low:-3 |
| VINS+SAVIOR vs VINS-Fusion | VIODE | mid+high | 2 / 9 | 0.016 | 2 | 0.50 | parking_lot_mid:-4, parking_lot_high:-3 |
| VINS+SAVIOR vs VINS-Fusion | VIODE | all | 6 / 16 | 0.002 | 3 | 0.25 | parking_lot_low:-3, parking_lot_mid:-4, parking_lot_high:-3 |
| VINS+Y-Cls vs VINS-Fusion | VIODE | none+low | 4 / 7 | 0.25 | 1 | 1.00 | parking_lot_low:-3 |
| VINS+Y-Cls vs VINS-Fusion | VIODE | mid+high | 2 / 9 | 0.016 | 2 | 0.50 | parking_lot_mid:-4, parking_lot_high:-3 |
| VINS+Y-Cls vs VINS-Fusion | VIODE | all | 6 / 16 | 0.002 | 3 | 0.25 | parking_lot_low:-3, parking_lot_mid:-4, parking_lot_high:-3 |
| VINS+O-Cls+B vs VINS-Fusion | VIODE | none+low | 3 / 7 | 0.12 | 2 | 0.50 | parking_lot_low:-3, city_day_none:-1 |
| VINS+O-Cls+B vs VINS-Fusion | VIODE | mid+high | 1 / 9 | 0.008 | 2 | 0.50 | parking_lot_mid:-4, parking_lot_high:-4 |
| VINS+O-Cls+B vs VINS-Fusion | VIODE | all | 4 / 16 | 5e-4 | 4 | 0.12 | parking_lot_low:-3, parking_lot_mid:-4, parking_lot_high:-4, city_day_none:-1 |
| VINS+O-Dyn+B vs VINS-Fusion | VIODE | none+low | 4 / 7 | 0.25 | 1 | 1.00 | parking_lot_low:-3 |
| VINS+O-Dyn+B vs VINS-Fusion | VIODE | mid+high | 1 / 9 | 0.008 | 2 | 0.50 | parking_lot_mid:-4, parking_lot_high:-4 |
| VINS+O-Dyn+B vs VINS-Fusion | VIODE | all | 5 / 16 | 10e-4 | 3 | 0.25 | parking_lot_low:-3, parking_lot_mid:-4, parking_lot_high:-4 |
| VINS+O-Dyn+B vs VINS+O-Cls+B | VIODE | none+low | 4 / 3 | 1.00 | 1 | 1.00 | city_day_none:+1 |
| VINS+O-Dyn+B vs VINS+O-Cls+B | VIODE | mid+high | 1 / 1 | 1.00 | 0 | 1.00 |  |
| VINS+O-Dyn+B vs VINS+O-Cls+B | VIODE | all | 5 / 4 | 1.00 | 1 | 1.00 | city_day_none:+1 |
| SAVIOR vs DynaVINS | VIODE | none+low | 2 / 10 | 0.039 | 5 | 0.50 | parking_lot_none:-1, parking_lot_low:-7, city_day_none:-1, city_day_low:-1, city_night_low:+2 |
| SAVIOR vs DynaVINS | VIODE | mid+high | 3 / 15 | 0.002 | 3 | 0.50 | parking_lot_mid:-6, parking_lot_high:-7, city_day_high:+1 |
| SAVIOR vs DynaVINS | VIODE | all | 5 / 25 | 9e-5 | 8 | 0.16 | parking_lot_none:-1, parking_lot_low:-7, parking_lot_mid:-6, parking_lot_high:-7, city_day_none:-1, city_day_low:-1, city_day_high:+1, city_night_low:+2 |
| SAVIOR vs VINS-Fusion | VIODE | none+low | 2 / 7 | 0.18 | 3 | 0.50 | parking_lot_low:-4, city_day_none:-3, city_night_low:+2 |
| SAVIOR vs VINS-Fusion | VIODE | mid+high | 3 / 9 | 0.070 | 4 | 0.38 | parking_lot_mid:-3, parking_lot_high:-3, city_day_mid:-1, city_day_high:+1 |
| SAVIOR vs VINS-Fusion | VIODE | all | 5 / 16 | 0.013 | 7 | 0.16 | parking_lot_low:-4, parking_lot_mid:-3, parking_lot_high:-3, city_day_none:-3, city_day_mid:-1, city_day_high:+1, city_night_low:+2 |
