# OpenVINS-baseline diagnostic (warehouse t1 L0/L1; no held-out runs)

Date: 2026-10-24. Diagnostic agent; report saved by the coordinator. Nothing was changed in src/savior, install/, frozen_edge/ or the frozen yamls.

## Verdict
- (a) Config issue for static/low-dynamic scenes: the MSCKF window is too short in time (11 clones at 21 Hz ≈ 0.55 s). VINS-Fusion uses a 10 Hz front-end with a parallax-keyframe window of several seconds.
- (b) hall L3 divergence is NOT config-related: init, ZUPT, window length and 10 Hz cloning all still fail 8–10/10. It is caused by dynamic content (a co-moving forklift right after take-off).
- On t1, frozen OpenVINS ≈ VINS-Fusion (L0+L1 −1 % [−16, +18], p = 0.75). The large t2 gap (hall_t2_L0 0.268 vs 0.085 m) does NOT reproduce on t1 and is still unexplained.

## Key findings
- **Error decomposition:** OpenVINS's loss is yaw (0.59° vs 0.39° RMSE) and jumpiness (5–7 cm per-frame steps). Scale, vertical and roll/pitch errors are better than VINS-Fusion's.
- **Init:** the static initializer is triggered by the take-off jerk. The initial state is good, but there is a 2.6–3.8° tilt transient that decays in about 1.5 s. Hover init (`try_zupt`) removes the transient but does not improve ATE (n.s.).
- **IMU noise** equals the generator's truth. Every inflation is worse (+41…+66 %). Online calibration (euroc variant) is +122 %. More features: n.s./worse. sigma_px 1 and max_slam 50 are right.
- **Fix:** `track_frequency 21 → 10.5`, optionally `max_clones 11 → 15`.
  - −29 % ATE on L0+L1 vs frozen ([−38, −20], p = 5e-6, 33/7); rotation error halved; 0 failures.
  - Vs VINS-Fusion: −30 % [−38, −20].
  - Fallback without frame dropping: clones30 at 20 Hz, −26 %.

## Full ablation table
| variant | L0+L1 vs frozen |
|---|---|
| trk10_clones15 | −29 % [−38, −20] p=5e-6 |
| trk10 | −29 % [−38, −19] |
| trk7 | −29 % |
| clones30 | −26 % |
| clones20 | −20 % |
| clones15 | −7 % n.s. |
| zupt_win1 / hoverinit_win1 / init_thr015 | +6 / +8 / +8 % n.s. |
| init_win1 | +28 % |
| zupt (2 s) | +45 % |
| imu_rw10 / imu_x2_rw10 / imu_x5 | +41 / +61 / +66 % |
| pts250 / pts300 / feat_sim / fast10 / initfeat150 | +8…+14 % n.s. |
| hist_none | +39 % (2 failures) |
| slam0 | +77 % |
| sigma_px05 | +99 % (7 failures) |
| sigma_px15 | +63 % |
| euroc | +122 % |
| VINS-Fusion | +1 % n.s. |

Detailed tables: `tables/ablation_runs.*` and `tables/ablation_vs_vins.*`.

## Proposed disclosed re-freeze (author's decision)
1. Change only `max_clones` and `track_frequency` in the shared warehouse `estimator_config.yaml`, and in the frozen_edge copy if it has one. Do not change any perception, roles or pset files.
2. Record the new md5 with a dated "OpenVINS back-end re-freeze" note citing this report.
3. Re-run all OpenVINS-based methods on t1. This checks the relative gains and the mask sync under 10 Hz processing, which drops every 2nd frame.
4. Run t2 once. Report it as a second look at the held-out data.

## Caveats
- Only 2 trajectories in t1, so per-sequence medians are noisy; the pooled paired statistics are robust.
- t2, t3 and VIODE were not run.
- The SAVIOR mask-buffer interaction at 10.5 Hz is untested.
- Not ablated: dt_slam_delay, feat_rep_*, chi² multipliers, grid.

## Files
- `figures/timelines_t1_L0`, `figures/forest_ablation`
- `configs/`, `scripts/`, `runs/`, `vins/`, `analysis/`, `tables/`
- ROS1 t1 bags in scratchpad/ovdiag/bags
