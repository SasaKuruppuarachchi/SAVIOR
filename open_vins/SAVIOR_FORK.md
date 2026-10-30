# SAVIOR fork of OpenVINS

This directory is a vendored fork of [OpenVINS](https://github.com/rpng/open_vins) (GPL-3.0, see `LICENSE`),
used as the back-end of SAVIOR. The MSCKF internals are untouched; the fork only adds external dynamic-mask
input (ROS 2) and dynamic-mask gating in the visual front-end.

- Upstream: `https://github.com/rpng/open_vins`, branch `master`, commit `69488123ed9362dd44b6f28e7f4680abbff1442b`
- Interface contract (mask topics, pixel values, stamps): `../docs/INTERFACE.md` §3.1 / §3.2
- Every code change is marked with a `// SAVIOR:` comment.

## What was vendored

Kept: `LICENSE`, `ReadMe.md`, `.clang-format`, `.gitignore`, `run_*.sh`, `config/`, `ov_core`, `ov_init`, `ov_msckf`, `ov_eval`,
`ov_data` (only `ov_data/sim`, the simulation trajectories, 11 MB).

Dropped: `.git`, `.github`, `docs/`, `Doxyfile*`, `Dockerfile_*`, and the ground-truth folders of `ov_data`
(`euroc_mav`, `kaist`, `kaist_vio`, `rpng_*`, `tum_vi`, `uzhfpv_*`, ~365 MB). These are only referenced by the ROS 1
`.launch` files (`path_gt`); SAVIOR extracts its own ground truth with `savior_eval`.

## Behaviour with the default configuration

`use_dynamic_mask: false` (the default, also when the key is absent) is **bit-identical to upstream**: no mask
subscription, masks are passed to the trackers untouched, and every new front-end branch is guarded by the gating flag.
This was checked by feeding the same synthetic stereo sequence (100 frames, with and without an upstream-style static mask)
to the upstream and the patched `TrackKLT` and comparing every tracked feature id and position: they are identical.
`record_feature_stats` only writes a file and also does not change the tracking.

## Patches

| File | Purpose |
|---|---|
| `ov_core/src/track/TrackBase.h/.cpp` | `set_mask_gating()` (threshold, relaxed threshold, min features), `set_feature_stats_file()`; helpers `threshold_mask()` (binarize: 255 iff value >= threshold), `apply_mask_threshold()`, `is_masked()`, `mask_relax_min_features()`, `write_feature_stats()`; storage of the raw (layered) masks of the current frame. |
| `ov_core/src/track/TrackKLT.cpp` | Masks are binarized at the configured threshold at entry (so every downstream upstream test, `> 127`, `!= 255`, the FAST/GRID griders and the visualization, stays consistent). **Stereo path: already-tracked left features are checked against the left mask, right features against the right mask** (upstream only does this in the mono path). A stereo pair whose right observation is masked is kept as a left mono track. Right-only detections use the right mask (upstream used the left mask, `mask1_updated = mask0.clone()`). Layered relaxation and feature statistics (mono and stereo). |
| `ov_core/src/track/TrackDescriptor.cpp` | Masks are binarized at the configured threshold (features are re-detected on every frame with its mask, so nothing else is needed). No relaxation, no statistics. |
| `ov_core/src/track/TrackAruco.cpp` | Masks are binarized at the configured threshold. |
| `ov_core/src/utils/sensor_data.h` | `CameraData::masks_dynamic`: raw layered dynamic masks, kept separate from the static `masks` (P2). |
| `ov_msckf/src/core/VioManagerOptions.h` | New parameters (below), parsed as optional, validated and printed. `deterministic_processing` (P2). |
| `ov_msckf/src/core/VioManager.cpp` | Configures gating / statistics on the feature tracker (and the threshold on the ArUco tracker); downsamples `masks_dynamic` with the images; deterministic mode: no IMU pruning relative to the newest IMU before initialization (P2); `dynamic_mask_after_init` (P2) and `dynamic_mask_init_policy` (P4) before initialization. |
| `ov_msckf/src/ros/ROS2Visualizer.h/.cpp` | Mask subscribers, stamp-keyed mask buffer, "wait" / "latest" policies, pending-image buffer + 5 ms wall timer, attaching the dynamic mask next to the static mask, logging; deterministic mode: reliable deep IMU / image / mask queues (P2). |
| `ov_msckf/src/run_subscribe_msckf.cpp` | Keeps the upstream multi-threaded subscriber unless `deterministic_processing` (P2). |
| `ov_init/src/init/InertialInitializerOptions.h`, `InertialInitializer.cpp` | `init_imu_until_camera`: the initializers only see IMU up to the newest image (+1 sample), set by `deterministic_processing` (P2). |
| `config/euroc_mav/estimator_config.yaml`, `config/rs_t265/estimator_config.yaml` | New keys (default off). |
| `ov_core/src/feat/Feature.h`, `FeatureDatabase.h/.cpp` | (SG) Semantic label bits per feature (`sem_seen` over the track, `sem_last` of the newest frame), `update_feature_semantics()`. |
| `ov_core/src/track/TrackBase.h/.cpp`, `TrackKLT.cpp` | (SG) `set_semantic_labels()`: every feature entering the database is labelled from the raw dynamic mask under it (mono and stereo, left and right). |
| `ov_msckf/src/update/SaviorGate.h` (new), `UpdaterOptions.h`, `UpdaterMSCKF.h/.cpp`, `UpdaterSLAM.h/.cpp` | (SG / NIS) Per-feature χ² multiplier: semantic factor and NIS-adaptive scale, `[SAVIOR-GATE]` counters. With both off the test is the upstream expression. |
| `ov_msckf/src/core/VioManagerOptions.h`, `VioManager.cpp` | (SG / NIS) Parameters below; SG keep-band sets the front-end threshold to the relaxed (core) threshold. |

The ROS 1 visualizer is not patched (`use_dynamic_mask` has no effect there besides the tracker thresholding).

## New parameters (`estimator_config.yaml`, can be overridden by ROS 2 parameters)

| Key | Default | Meaning |
|---|---|---|
| `use_dynamic_mask` | `false` | Subscribe to the dynamic masks and enable gating. |
| `dynamic_mask_topic<i>` | `/savior/mask/left` (0), `/savior/mask/right` (1), `""` (>= 2) | Mask topic of camera `i`; `""` disables the dynamic mask of that camera. |
| `dynamic_mask_policy` | `"wait"` | `"wait"`: hold each image until the masks with the identical stamp arrive. `"latest"`: use the newest mask with stamp <= image stamp immediately. |
| `dynamic_mask_timeout_ms` | `100` | `"wait"`: wall time after image arrival after which we fall back to the newest mask with stamp <= image stamp (at most 1 s older), else an empty mask. |
| `dynamic_mask_max_pending` | `64` | (P7) `"wait"`: cap on held measurements; when more are pending, the head is released (with the fallback mask) regardless of `dynamic_mask_timeout_ms` (protects against a dead mask publisher). `64` = P2-P6 behaviour (about 6.4 s of 10 Hz stereo measurements: this capped long timeouts, e.g. 30 s, in heavy offline replays); `<= 0` = no count cap, only the timeout releases. |
| `dynamic_mask_threshold` | `128` | Mask pixel values >= threshold are rejected (1..256, 256 = never reject: observe-only mode for baseline statistics). |
| `dynamic_mask_relaxed_threshold` | `224` | Threshold used for a camera whose kept features would drop below `dynamic_mask_min_features` (drops the 192 band, keeps the 255 core). Must be >= `dynamic_mask_threshold`. |
| `dynamic_mask_min_features` | `60` | Per camera. Refers to the post-initialization per-camera target `num_pts / max_cameras`; while the tracker runs with a smaller target (before initialization: `init_max_features / max_cameras`) it is scaled proportionally (e.g. 60 of 100 -> 15 of 25). `<= 0` disables relaxation. |
| `record_feature_stats` | `""` | CSV path (KLT tracker only, works also without dynamic masks). |
| `deterministic_processing` | `false` | Offline bag replay: synchronous subscriber (`multi_threading_subs` off), initializer on IMU up to the image time, no wall-time limit on the dynamic-init MLE, lossless QoS. Upstream results depend on the wall-clock timing of IMU vs image processing (CPU load, mask waiting). `savior_bringup` launch files set it by default (`deterministic:=true`). |
| `init_imu_until_camera` | `false` | (ov_init) see above; implied by `deterministic_processing`. |
| `dynamic_mask_after_init` | `false` | (P2) Ignore the dynamic masks until the filter is initialized. |
| `dynamic_mask_init_policy` | `"normal"` | (P4) Dynamic masks before initialization: `normal` (unchanged), `none` (= `dynamic_mask_after_init`), `core` (only the 255 core is rejected: pixels < 224 are cleared), `relax` (255 -> 192: everything relaxable when the init tracker runs short). Implemented in `VioManager::track_image_and_update` on a new buffer (the message copy shares the mask data). |
| `dynamic_mask_upstream_compat` | `false` | (P4) Upstream-compatible gating for clean controls: frames whose dynamic masks (this and the previous frame, any camera) have no pixel >= `dynamic_mask_threshold` run the exact upstream front-end (raw static masks, no SAVIOR re-checks, right detections with upstream's mask0), and `TrackBase::is_masked()` never treats out-of-bounds points as masked (also tracked left points at x == cols are kept, as upstream does). With all-zero masks (`backend:=none`) the run is identical to `use_dynamic_mask: false`. Default `false` keeps the P2/P3a/P4 behaviour (out-of-bounds = masked; with all-zero masks one fewer detection at t = 30.957 s on uHumans2 12h, P3a). |

### Feature statistics CSV

One row per processed frame and camera, flushed per row:
`timestamp,cam_id,n_tracked,n_new,n_rejected_mask,relaxed,n_in_band,n_in_core`

- `n_tracked` / `n_new`: kept features of this frame that existed before / were detected during this frame's top-off
  (`n_tracked + n_new` = features that enter the feature database for this camera; for the very first frame after a
  tracker (re)initialization nothing enters the database).
- `n_rejected_mask`: successfully KLT-tracked features rejected by the mask in this frame.
- `relaxed`: 1 if the relaxed threshold was used for this camera in this frame.
- `n_in_band` / `n_in_core`: kept features lying on raw DYNAMIC mask pixels 128..254 / 255 (the static mask is not
  counted since P2). With gating enabled
  `n_in_core` must always be 0. With `dynamic_mask_threshold: 256` (observe-only) it counts the features a baseline puts on
  dynamic objects.

### Semantic χ² gate (SAVIOR-SG) and NIS-adaptive gate

| Key | Default | Meaning |
|---|---|---|
| `savior_semantic_gate` | `false` | Label features from the raw dynamic mask (0 background, 1..127 movable-static, >= 128 band) and scale the MSCKF / SLAM χ² multiplier per label (background: x1, the stock gate). MSCKF and SLAM delayed initialization: tightest label over the track; SLAM update: label of the current observation. KLT tracker only. |
| `savior_sg_mult_static` | `1.0` | Factor for movable-static features (SAVIOR level 64, `compose.movable_static_value`). |
| `savior_sg_mult_band` | `1.0` | Factor for band features (192). |
| `savior_sg_keep_band` | `false` | Front-end threshold = `dynamic_mask_relaxed_threshold` (only the core is removed), band features are kept under `savior_sg_mult_band`. |
| `savior_nis_gate` | `false` | Non-semantic self-tuning control: multiplier x λ, λ = median of χ² / χ²₀.₅(dof) over the last `savior_nis_window` tests of that updater (robust innovation scale of innovation-based adaptive estimation; Mehra 1970, Mohamed & Schwarz 1999), 1 until the window is full, clamped to [0.05, 20]. |
| `savior_nis_window` | `200` | NIS window (χ² tests per updater, >= 10). |

**Default-off contract.** With `savior_semantic_gate: false` and `savior_nis_gate: false` no label is written, the
tracker threshold is unchanged and the gate is the upstream `chi2 > chi2_multipler * chi2_0.95(dof)`. This was verified
end to end: trajectories md5-identical to the frozen build for OpenVINS-v2, SAVIOR-none, SAVIOR, and SAVIOR publishing the
64 level with the fork gate off (results/semantic_gate/tables/audit.md). ArUco tags never use either gate.

## Static vs dynamic mask (P2 change)

Until P1 the dynamic mask was max-combined with the static mask in the visualizer and the combination was binarized at
`dynamic_mask_threshold`. That (a) unmasked the anti-aliased static-mask edge pixels (values 128..223) whenever the
relaxed threshold was used, (b) dropped the static mask entirely in observe-only mode (threshold 256), and (c) counted
static-mask pixels as "core" in the statistics. Now the dynamic mask travels in `CameraData::masks_dynamic`; the tracker
gates with `max(static > 127, dynamic >= threshold)` (relaxed: `dynamic >= relaxed_threshold`), so the static mask keeps
its upstream meaning for every threshold. Observe-only (`dynamic_mask_threshold: 256`) now gives exactly the trajectory
of gating with all-zero masks (verified on cafe1-1, identical md5).

Note that with `use_dynamic_mask: true` the front-end is not identical to upstream even with all-zero masks: tracked stereo
features are checked against the (static) mask, right-only detections use the right static mask and out-of-bounds points
count as masked (cafe1-1: ATE 0.164 vs 0.165 m). Use SAVIOR with empty masks (`backend:=none`) as the control for mask
effects, or (P4) `dynamic_mask_upstream_compat: true`, which makes the empty-mask control identical to upstream.

## Determinism (P2)

Upstream processes images and runs the initializer in detached threads, and the initializers use every IMU reading
received so far (and prune relative to the newest one). The result therefore depends on CPU load and on how long images
are held for their masks: cafe1-1 stock OpenVINS gave ATE 0.165 m unloaded and 0.154 m with a parallel build (init one
frame later). With `deterministic_processing: true` the fork reproduces the unloaded stock result bit-identically and
stays bit-identical under a 46-process CPU load; with SAVIOR masks and the "wait" policy repeated runs are bit-identical
too (rare 1e-9 floating-point differences were seen once).

## Design notes

**Mask input (ROS 2).** Mask topics are subscribed with reliable QoS, depth 10. Masks are stored per camera keyed by
their stamp in integer nanoseconds (exact comparison, no float rounding) and pruned to the last second before the most recent
released image (max 200 per camera). The dynamic mask is combined with the upstream static mask by per-pixel max; a mask
whose size differs from the image is resized (nearest) with a warning. Encodings `mono8` and `8UC1` are accepted.

**"wait" policy.** Every camera measurement that passed the upstream `track_frequency` throttle goes into a small pending
buffer sorted by stamp. Measurements are released strictly in stamp order (head of line) when all of their masks with the
identical stamp are present, or when the head has waited `dynamic_mask_timeout_ms` (or, P7, more than
`dynamic_mask_max_pending` measurements are held; default 64) (wall time, checked on every image /
mask callback and by a 5 ms wall timer), or when more than 64 measurements are pending. Released measurements go into the
upstream camera queue, so the order into the `VioManager` is preserved. All state is protected by one mutex (lock order:
mask mutex, then the upstream camera-queue mutex). Fallbacks are logged with running counts
(`[SAVIOR-MASK]: cam0 t=... no mask with identical stamp after 100.1 ms -> latest(dt=50.0ms) (exact=120 latest=1 empty=0)`),
masks arriving after their image was released are logged as late, a summary is printed every 200 measurements and at the
end, and each release is printed at DEBUG verbosity with the hold time.

**Gating and relaxation (KLT).** OpenVINS detects (tops off) on the *previous* frame with the previous mask and then tracks
into the current frame; only the features of the current frame enter the database. Gating is applied to all features of the
current frame with the current mask (mono and stereo, left and right). If a camera keeps fewer than the (scaled)
`dynamic_mask_min_features`, the gating of that frame is re-run with the relaxed mask (cheap: no new KLT), and the relaxed mask is
stored as the "last" mask so the next top-off detection may also use the extension band. On a tracker (re)initialization frame
a top-off detection with the relaxed mask is run. Nothing is done twice unless relaxation is needed.

## Known limitations

- `downsample_cameras: true` downsamples the masks with `pyrDown` (as upstream), which blurs the layers at their borders.
- Relaxation and statistics are implemented for the KLT tracker only (`use_klt: true`, the default).
- The upstream ROS 2 node does not exit on SIGINT (it hangs after `visualize_final()`; same with the unmodified upstream build),
  so runners have to SIGKILL it after a grace period. The statistics CSV is flushed per row, and the final mask summary is
  printed before the hang (use line-buffered stdout, e.g. `stdbuf -oL`, when redirecting to a file).
