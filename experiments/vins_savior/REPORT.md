# Back-end-agnostic SAVIOR: SAVIOR masks in VINS-Fusion vs DynaVINS (warehouse t1)

Date: 2026-10-25. Tuning split only (`*_t1_*`: aisles/hall L0–L3, 8 sequences × 10 offsets 0.0–1.8 s, rate 0.5).
No `*_t2_*`, `*_t3_*` or VIODE data was run. Nothing in install/, frozen_edge/, ref/ or the frozen yamls was changed.
Full tables: `tables/ate.md`, `tables/rpe.md`, `tables/control.md`, `tables/backend.md` (+ .json). Figures: `figures/`
(forest_vs_vins, forest_key, ate_success, ate_strip, backend_gain; png + pdf, paper style).

## 1. What was built
| piece | where |
|---|---|
| offline mask exporter (drives the real `savior_node` from the bag, frozen parameters) | `src/savior/sota/mask_export/{export_masks.py,frozen_params.py}` |
| VINS-Fusion patch P9 (masks + deterministic mode), unified diff applied by `apply_patches.sh` | `src/savior/sota/patches/vins_fusion_savior_mask.patch` |
| incremental image `savior-sota:noetic-mask` | `src/savior/sota/docker/Dockerfile.savior_mask`, `build_mask.sh` |
| harness keys `SOTA_MASK_*`, `SOTA_DETERMINISTIC`, `SOTA_IGNORE_SOLVER_TIME`, `MDIR_NAME`, `SOTA_IMAGE` | `src/savior/sota/scripts/{run_one,run_method,drun_sota}.sh` |
| docs | `src/savior/sota/README.md`, section "VINS-Fusion + SAVIOR masks (P9)" |
| masks (PNG per left stamp, per offset; content-addressed pool + hard links; 1.1 GB) | `masks/<seq>/<method>/off_<o>/{left,right}/<ns>.png` |
| runs (720), scripts, validation | `runs/`, `scripts/`, `validation/` |

## 2. Design decisions
- **Do masks depend on the filter? No.** `savior_node` subscribes only to left/right images, `/imu0` (gyro, motion
  evidence) and, for oracles, the GT segmentation; there is no pose/odometry feedback (the selective "convergence
  proxy" is perception-internal). Masks **do** depend on the start offset (tracker / motion / selective state start at
  the first played frame; e.g. hall_t1_L3 offset 0.2 vs 0.0 differ on 466/2254 common frames), so they are exported
  **per offset**, exactly as each OpenVINS run saw them. Stateless methods (Y-Cls, oracles) were exported the same way.
- **Exporter = the node itself.** `SaviorNode` is built with the parameter list `savior.launch.py` builds (rebuilt
  from the frozen yamls, asserted identical to the logged list of the reference runs; the P6 Y-Cls/O-Dyn reference
  logs lack only the node-only keys `fast_masks`/`stats_compact`, bit-identical per the freeze notes), fed in bag order
  from `starting_time + offset` (= `ros2 bag play --start-offset`), exact-stamp synchronizer emulated, its own
  gyro-coverage hold kept, end-of-bag frames released as the online IMU time-out does. Only `_publish_masks` is
  captured.
- **Right image:** VINS-Fusion has no right-image detection; right features are LK-tracked from the left. Right
  observations are gated with SAVIOR's own right mask (the frozen stereo warp OpenVINS consumes); no extra model.
- **Band (192):** default = the frozen OpenVINS config: threshold 128 (band rejected), relaxed to 224 (core only) for a
  camera when fewer than 30 tracked features would survive (`dynamic_mask_min_features: 30`; VINS `max_cnt` 150 =
  OpenVINS `num_pts` 150). Only O-Dyn+B / O-Cls+B have a band (SAVIOR, SAVIOR-edge, Y-Cls run without extension).
  Configurable via `savior_mask_threshold/_relaxed_threshold/_min_features`. Not emulated: OpenVINS' down-scaling of
  the minimum during its init phase (VINS has no reduced init feature target).
- **Sync:** exact left header stamp in ns (from the ROS header, not the double time); PNG files read directly; wait
  policy `savior_mask_wait_ms` (0 offline = deterministic); missing mask = no masking for that frame, counted.
  Result: 0 missing / 0 bad-size masks over 560 masked runs (175 872 frames per method); 0 kept features on core
  pixels, left and right.
- **SAVIOR-edge latency (emulates the fork's `sim_latency 250 ms, deferred, stale_gating=false`):** no current-frame
  gating; the mask of frame k arrives at the first frame j with t_j ≥ t_k + 250 ms (sensor time); every feature
  observed inside it at frame k (left or right, ≥ 128) is dropped from the tracker and removed from the estimator's
  sliding window (`FeatureManager::removeOutlier`; ids queued with the frame they travel with). Approximation inherent
  to the back-end: VINS discards the window observations of a late-flagged feature retroactively, but what is already
  marginalized stays in the prior (OpenVINS: features already used in an MSCKF update cannot be undone). 175 472
  deferred masks applied, 0 missing. (`flagged` in the logs counts flag events, one per late mask hit.)
- **Determinism:** upstream VINS-Fusion is not deterministic (processing-thread race on the tracker prediction, and
  wall-clock `max_solver_time`). P9 adds `savior_deterministic` (no processing thread; the frames the thread would
  process — every 2nd with `multiple_thread: 1`, unchanged — are processed synchronously once the IMU covers them) and
  `savior_ignore_solver_time` (iteration cap of 8 only). Measured (`validation/determinism/`, hall L0/L3, runs 1/5,
  loaded machine): upstream repeats differ on hall_L3; `deterministic` alone still diverged when the time limit bound
  (2–3 of 1110 solves); **with both keys repeats are md5-identical.** Both keys are used for every VINS method incl.
  the baseline. Accuracy effect: upstream-threaded VINS-Fusion (original image, 80 runs) vs the deterministic
  baseline: geometric mean +0.00 %, max |Δ| 0.4 %, 43/80 md5-identical. The SOTA config is unchanged (keys are only
  appended to each run's config copy). DynaVINS: upstream, original image, 80 new t1 runs.

## 3. Validation
| check | result |
|---|---|
| offline export vs online `/savior/stats` of the frozen OpenVINS runs (all fields except timings, per stamp): SAVIOR (P7), SAVIOR-edge (edge study), Y-Cls (P6), O-Dyn+B (P6), O-Cls+B (P7) | **400/400 offset-runs, every record equal**, same frame set, 0 failed frames, 0 IMU time-outs |
| online re-runs (m2b runner, frozen settings) recording `/savior/mask/{left,right}`, md5 per frame vs export | **6/6 runs, 100 % of frames md5-identical, left and right** (SAVIOR hall L3 off 0.0 + aisles L2 off 1.2; SAVIOR-edge hall L3 off 0.4 [frozen_edge]; Y-Cls aisles L2; O-Dyn+B hall L3; O-Cls+B aisles L0 off 0.8); their OpenVINS trajectories are md5-identical to the original runs (`validation/online_vs_offline.jsonl`) |
| P9 neutral without keys | patched = original image when not timing-perturbed (hall_L0 4/4 md5) |
| **empty-mask control**: VINS + all-zero masks (gate path active, every mask present) vs VINS-Fusion, both deterministic | **80/80 md5-identical** |
| pose-count rule (≥ same-offset VINS-Fusion poses − 1) | 80/80 for every method |

## 4. Results (ATE posyaw, paired geometric-mean change [95 % CI], Holm per (group, reference); 0 failures > 2 m for every method)
Median ATE over all 80 runs: VINS-Fusion 0.124 m, +Y-Cls 0.140, +SAVIOR 0.123, +SAVIOR-edge 0.113, +O-Dyn+B 0.100,
+O-Cls+B 0.150, DynaVINS 0.099.

**Each method vs VINS-Fusion**
| method | L0+L1 | L2+L3 | hall L3 |
|---|---|---|---|
| VINS+Y-Cls | +5.4 % [−6, +18] n.s. | −23.5 % [−35, −10] H .020 | −57.6 % [−62, −53] H .012 |
| **VINS+SAVIOR** | +0.3 % [−9, +11] n.s. | **−30.3 % [−37, −23] H 1e-7** | −56.2 % [−61, −51] H .012 |
| VINS+SAVIOR-edge | −8.6 % [−17, +1] n.s. | −34.1 % [−44, −23] H 9e-5 | −70.1 % [−73, −67] H .012 |
| VINS+O-Dyn+B | −10.3 % [−17, −4] H .028 | −46.6 % [−54, −38] H 5e-10 | −68.7 % [−73, −64] H .012 |
| VINS+O-Cls+B | +30.8 % [+18, +45] H 2e-4 | −24.4 % [−40, −6] H .020 | −70.9 % [−73, −68] H .012 |
| DynaVINS | −3.5 % [−15, +10] n.s. | −52.7 % [−62, −42] H 2e-7 | −76.7 % [−81, −71] H .012 |

**VINS+SAVIOR vs VINS+Y-Cls:** L0+L1 −4.9 % [−13, +5] n.s.; L2+L3 **−9.0 % [−17, −0] H .038**; hall L3 +3.4 % n.s.
(SAVIOR-edge vs Y-Cls: −13.3 % H 5e-4 / −13.9 % H .005 / −29.5 % H .004.)

**VINS+SAVIOR vs DynaVINS:** L0+L1 +4.0 % [−6, +14] n.s.; L2+L3 **+47.2 % [+29, +69] H 7e-6**; hall L3 +88.5 % H .004.
(SAVIOR-edge vs DynaVINS: −5.3 % n.s. / +39.2 % H 2e-5 / +28.5 % H .049.) DynaVINS is better on dynamic scenes.

Secondary: O-Dyn+B vs O-Cls+B −31.4 % (L0+L1, H 4e-7), −29.4 % (L2+L3, H 1e-6), +7.8 % hall L3 n.s.;
SAVIOR-edge vs SAVIOR −8.9 % n.s. / −5.4 % n.s. / −31.8 % (hall L3, H .002).

**RPE** (shortest sub-length, translation mean) agrees in direction and is harsher on class masking: vs VINS-Fusion,
SAVIOR +0.3 % n.s. / −20.8 % (H 3e-9) / −32.0 %; Y-Cls +24.1 % (H 2e-11) / −5.2 % n.s. / −36.6 %; SAVIOR vs Y-Cls
−19.2 % (H 4e-9) / −16.5 % (H 2e-5) / +7.3 % n.s. DynaVINS is −36 % RPE vs VINS-Fusion already at L0+L1 (static scenes)
and VINS+SAVIOR is +57 % / +88 % / +98 % worse than DynaVINS: much of DynaVINS' RPE edge comes from its different base
configuration (VIODE-derived: min_dist 15, F_threshold 2, 10 iterations, 0.3 s solver time), not from dynamic handling.

**Same masks, two back-ends** (`tables/backend.md`, `figures/backend_gain`): every mask helps far more on OpenVINS
(SAVIOR L2+L3 −73 %, hall L3 −98 %) than on VINS-Fusion (−30 %, −56 %): OpenVINS diverges on hall L3 without masks,
VINS-Fusion's sliding-window BA with a robust loss already tolerates movers. The ranking is preserved on both
back-ends (O-Dyn+B ≥ SAVIOR(-edge) ≥ Y-Cls at L2+L3), and class-level masking hurts static scenes on both
(O-Cls+B +31–33 % at L0+L1; Y-Cls +28 % OpenVINS, +5 % VINS).

## 5. Honest reading
- SAVIOR transfers to an optimization-based back-end without retuning: −30 % ATE / −21 % RPE at L2+L3 vs VINS-Fusion,
  no harm at L0+L1, better than naive class masking (−9 % ATE with the CI touching 0; −16…−19 % RPE, clear).
- **DynaVINS beats VINS+SAVIOR on dynamic t1 scenes** (+47 % ATE at L2+L3, Holm-significant) and in RPE everywhere;
  equal ATE at L0+L1. SAVIOR masks on VINS-Fusion do not close the gap to DynaVINS under this protocol (the
  comparison also carries DynaVINS' different base configuration).
- Mask quality matters on VINS too: perfect dynamic masks (O-Dyn+B) reach −47 % at L2+L3 (≈16 points over SAVIOR);
  perfect class masks hurt static scenes.
- t1 is the perception tuning split (sens_fix1 was selected on t1), so SAVIOR-vs-Y-Cls is optimistic here; the
  held-out run decides.

## 6. Held-out (prepared, NOT run)
`results/vins_savior/scripts/heldout/run_heldout.sh` (+ `hvrun.sh`): warehouse t2 (12 seq) + VIODE (12 seq; frozen
VIODE instantiation of the addendum, VIODE offsets, failure > 1 m). Steps `bags masks runs eval analyze clean`;
refuses unless `VS_HELDOUT_GO=1`, the p7 md5 files match and `results/vins_savior/FREEZE.md5` (patch, exporter,
harness, VINS configs, analysis, held-out scripts) matches. DynaVINS t2/VIODE runs of results/sota (same protocol)
are reused unless `RERUN_DYNAVINS=1`. ≤ 10 containers (`PAR_GPU` 6, `PAR_RUN` 9). Outputs in `results/vins_savior/heldout/`.

## 7. Reproduce (t1)
`scripts/export_job.sh <seq> <method>` (masks + stats validation) · `scripts/queue.sh scripts/jobs_{A,B}.txt N`
(runs via `scripts/vrun.sh`) · `scripts/finish_all.sh` (eval, `vs_analyze.py`, `vs_control.py`, `vs_figs.py`) ·
validation: `scripts/jobs_det.txt`, `scripts/online_record.sh` + `cmp_online.py`, `cmp_stats.py`.
