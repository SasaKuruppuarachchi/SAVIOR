# P5 Report: VIODE benchmark

Date: 2026-10-15. VIODE agent I; report saved by the coordinator.
Detailed tables are in `tables/`, figures in `figures/`, scripts in `scripts/`, and per-run directories under `<env>_<level>/<method>/run_XX`.

## Verdict
1. **Masking helps in high-dynamic scenes.** This is SAVIOR's first significant, replicated effect.
   - High level, pooled over 3 environments × 10 offsets (n = 30), ATE vs openvins:
     - oracle_dynamic: **−46 %** [−64, −26], p = 1e-4;
     - YOLO + P4 (vehicles potential): **−39 %** [−61, −15], p = 0.001.
   - Converged runs only: oracle −30 %, YOLO+P4 −18 % (p = 0.003).
   - Gain by dynamic level:

     | level | effect vs openvins |
     |---|---|
     | none | ±0 |
     | low | −2…−8 % (n.s.) |
     | mid | −3…−10 % (n.s.) |
     | high | −37…−47 % (significant) |

   - Masking prevents divergence. On parking_lot_high, openvins diverged in 2/10 runs; every masking method diverged in 0/120.
2. **SAVIOR (YOLO + P4) recovers about 60–85 % of the oracle gain but does not reach it.**
   - High level: +13 % vs oracle_dynamic (p = 0.03).
   - The gap comes from YOLO recall: vehicle pixel recall is 0.49–0.72 on the high sequences.
3. **SAVIOR is not measurably better than naive class masking on ATE.**
   - Pooled: −2.9 % [−10, +6], p = 0.40.
   - The per-instance decision is much better: moving precision 0.95 vs 0.41, 97 % of parked cars stay unmasked, and the masked area is 20–45 % smaller.
   - On VIODE, masking parked cars costs almost nothing, because they cover only 0.4–2 % of pixels. As a result, oracle_all_vehicles ≈ oracle_dynamic (+0.4 %, n.s.).
4. **Under P4, vehicles must be "potential", not "dynamic".**
   - With vehicles set to dynamic, P4 never confirms a parked car as static.
   - With vehicles set to potential:
     - moving precision 0.945, recall 0.695;
     - recall by depth: 0.90 below 5 m, 0.79 at 5–10 m, 0.29 beyond 10 m;
     - 97 % of parked cars stay unmasked.
5. **P3a's "≥ 10 %" prediction is refined.** What predicts the gain is the share of measurements the back-end actually uses, not the image or front-end share.
   - parking_lot mid/high: 11.5–13.7 % of kept features are on moving cars, but only 0.3–1.1 % of MSCKF-used measurements, because chi² rejects 83–86 % of them.
   - city_night_high: 3.5 % of kept features, but 8.2 % of used measurements (chi² rejects only 37 %). This gives the largest and most consistent gain (−46 %, 10/10 offsets).
   - The damage comes from slow, chi²-consistent movers. Large image shares hurt mainly by destabilising the filter (divergences).

## Data and calibration
- **Size:** 3 environments × 4 levels (12 sequences, 60–66 s, 76–166 m). VIODE takes 54 GB on disk.
- **Conversion:** to mcap with `savior_bringup/tools/viode_prepare.py`. Segmentation is re-encoded losslessly as mono8 object-id images, and the dynamic pixel shares match VIODE's Table II.
- **Ground truth:** /odometry is NED world / NED body. This was verified numerically: Kabsch rotation error 0.004–0.006°, no time offset, no lever arm. GT is written with z up so posyaw alignment is valid.
- **Calibration:** pinhole fx = 376 with a 5 cm baseline, converted from VINS-Fusion format to kalibr. Verified by gyro-predicted KLT: 0.28 px median residual.
- **IMU noise:** identified from the data — gyro 2.2e-4 rad/s/√Hz, accel 6e-3 m/s²/√Hz. Random walks use EuRoC values.
- **Right mask:** new node param `seg_right_topic` builds the oracle right mask from /cam1/segmentation. The stereo-warp alternative is just as good: precision/recall 0.97 / 0.98, ATE −2.8 % (n.s.).

## Protocol
- **Late start:** from the beginning of the bag, OpenVINS dynamically initializes during a rotation-only hover and diverges in about 1/3 of runs at *every* level, for every method. All methods therefore use 10 offsets starting 0.8 s before translation begins.
- **Settings:** `deterministic:=true`, `dynamic_mask_upstream_compat=true`, rate 0.5.
- **Runs:** 1320, plus 60 warp-variant and 36 diagnostic runs.
- **Sync:** 0 mask fallbacks and n_in_core = 0 in all 1260 masked runs. 10 city_day runs that had start-up mask drops were rerun.
- **Control:** savior_none equals openvins to print precision.
- **Failure criterion:** ATE > 1 m.

## Median ATE [m] over 10 offsets ([n] = failures)

| seq | openvins | none | oracle_dyn | oracle_all | yolo_naive | yolo_p2 | yolo_p4_dyn | yolo_p4_pot | ov+fast15 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| PL none | 0.086 | 0.086 | 0.086 | 0.081 | 0.079 | 0.085 | 0.086 | 0.083 | 0.086 |
| PL low | 0.084 | 0.084 | 0.096 | 0.095 | 0.082 | 0.074 | 0.074 | 0.088 | 0.104 [3] |
| PL mid | 0.105 | 0.105 | 0.092 | 0.089 | 0.167 | 0.141 | 0.145 | 0.098 | 0.125 [1] |
| PL high | 0.133 [2] | 0.133 [2] | 0.118 | 0.095 | 0.142 | 0.119 | 0.112 | 0.100 | 0.144 [3] |
| CD none | 0.198 | 0.198 | 0.198 | 0.166 | 0.210 | 0.175 | 0.170 | 0.200 | 0.183 |
| CD low | 0.226 | 0.226 | 0.219 | 0.217 | 0.231 | 0.241 | 0.247 | 0.206 | 0.250 [2] |
| CD mid | 0.316 [2] | 0.316 [2] | 0.344 [2] | 0.314 [2] | 0.316 [2] | 0.290 [2] | 0.304 [2] | 0.389 [2] | 0.282 [1] |
| CD high | 0.291 | 0.291 | 0.207 | 0.243 | 0.235 | 0.220 | 0.251 | 0.243 | 0.251 |
| CN none | 0.401 | 0.401 | 0.401 | 0.346 | 0.354 | 0.387 | 0.398 | 0.370 | 0.379 |
| CN low | 0.459 | 0.459 | 0.372 | 0.394 | 0.345 | 0.382 | 0.405 | 0.386 | 0.479 |
| CN mid | 0.481 | 0.481 | 0.432 | 0.437 | 0.375 | 0.439 | 0.466 | 0.410 | 0.452 |
| CN high | 0.686 | 0.686 | 0.351 | 0.335 | 0.419 | 0.431 | 0.456 | 0.486 | 0.665 |

- The CD-mid failures happen for every method, including the oracle: an initialization window at take-off, not dynamics.
- Failure totals: openvins 4/120, every masking method 2/120, openvins+fast15 10/120.

**Published numbers, for context only** (DynaVINS Table II; a SLAM system, full sequence, different alignment):
- VINS-Fusion: PL 0.121/0.121/0.212/0.278; CD 0.150/0.203/0.234/0.373; CN 0.317/0.507/0.494/0.828.
- DynaVINS: PL 0.049/0.042/0.064/0.042; CD 0.171/0.178/0.091/0.148; CN 0.213/0.182/0.201/0.198.

## Pooled statistics
Dynamic sequences (low+mid+high, n = 90); log-ratio per offset with failures capped at 10 m, bootstrap CI, Holm correction over 11 tests.

| method vs openvins | all runs | Holm p | converged only | RPE |
|---|---|--:|---|---|
| oracle_dynamic | −21.8 % [−33, −11] | 0.014 | −13.7 % (0.04) | −22.9 % |
| oracle_all_vehicles | −22.1 % | 0.014 | −14.4 % (0.03) | −19.7 % |
| yolo_naive | −16.3 % | 0.17 | −6.7 % | −20.5 % |
| yolo_full_p2 | −18.5 % | 0.06 | −8.1 % | −19.2 % |
| yolo_p4_dyn | −16.7 % | 0.17 | −6.3 % | −19.5 % |
| yolo_p4_pot | −18.8 % | 0.066 | −10.9 % (p = 0.018) | −19.7 % |
| openvins+fast15 | +29 % | n.s. | −3 % | |

- **FAST 15 does not transfer from P4.** It adds divergences (10/120 vs 4/120).
- About 150 tests were run per metric. Only the high-level and pooled effects (p ≤ 0.002) survive correction.

## Dynamic share vs gain (diagnostic build, `tables/feature_fates.txt`)

| seq | kept on moving cars | MSCKF-used meas | chi² rejected (dyn vs other) | oracle gain |
|---|--:|--:|---|--:|
| PL mid | 11.5 % | 0.30 % | 0.86 vs 0.27 | 18 % |
| PL high | 13.7 % | 1.11 % | 0.83 vs 0.29 | 63 % (divergences) |
| CD high | 5.6 % | 2.25 % | 0.81 vs 0.21 | 21 % |
| CN low | 1.2 % | 3.0 % | 0.43 vs 0.26 | 13 % |
| CN mid | 1.8 % | 2.8 % | 0.54 vs 0.25 | 14 % |
| CN high | 3.5 % | 8.2 % | 0.37 vs 0.25 | 46 % |

- Spearman correlation of oracle gain over 12 sequences:

  | oracle gain vs | rho | p |
  |---|--:|--:|
  | pixel share | 0.72 | 0.009 |
  | kept share | 0.75 | 0.005 |
  | MSCKF-used share | 0.68 | 0.016 |

- The YOLO+P4 gain correlates similarly (rho 0.61–0.68).

## Mask quality and motion evidence
- **YOLO26s-seg vehicle masks vs GT:**
  - precision 0.87–0.94;
  - recall 0.55–0.92, lowest when cars fill the frame;
  - the single moving car in city_day_low is detected 5 % of the time.
- **Per instance-frame decisions** (3236 moving, 4586 parked):

  | variant | moving precision | moving recall | parked kept unmasked |
  |---|--:|--:|--:|
  | naive / p2 / p4_dyn | 0.41 | 1.00 | 0.00 |
  | p4_pot | 0.945 | 0.695 | 0.972 |

- **Timing** (desktop, median per frame): segment 4.9 ms, motion 2.5 ms, node total 12.2 ms (p90 20 ms).

## Bugs, changes and open issues
- **Added:**
  - `seg_right_topic` (perception, default off), with a test; perception tests now 97 pass;
  - additive `viode` launch presets;
  - configs in `config/viode/`, `config/oracle/viode_*`, `config/roles/viode_*`.
- **Open issues:**
  - OpenVINS dynamic init during a rotation-only hover diverges about 1/3 of the time. It needs an init guard (e.g. minimum translation or parallax).
  - The oracle 4-topic sync drops masks when about 25 containers start at once.
  - The P4 still-test is tuned for people: it cannot confirm parked cars as static from a moving UAV with a 5 cm baseline.
  - YOLO recall on large, near and truncated cars is the main gap to the oracle.
  - z-axis accel noise is probably under-modelled on the city sequences.
