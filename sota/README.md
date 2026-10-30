# SOTA baselines (VINS-Fusion, DynaVINS, ORB-SLAM3) for SAVIOR's controlled comparison

This directory is **not** a colcon package (`COLCON_IGNORE`). It builds one Docker image, `savior-sota:noetic`
(ROS 1 Noetic, Ubuntu 20.04), that contains three stereo-inertial baselines. It also holds the VIODE configs and the
run/eval harness. The harness writes the same results layout as the SAVIOR runs.

## Contents

| path | what |
|---|---|
| `docker/Dockerfile`, `build.sh` | the image (pinned commits below; host network is used for the build only) |
| `patches/apply_patches.sh` | every source change applied at build time (list below) |
| `ros/sota_tools/` | ROS 1 package: `pose_recorder.py` (Odometry → TUM) and `orbslam3_bag_si` (ORB-SLAM3 stereo-inertial rosbag driver) |
| `config/viode/{vins_fusion,dynavins,orbslam3}/` | VIODE configs (provenance below) |
| `scripts/` | data conversion, run harness, evaluation, frame check |

## Upstream code, commits, licenses

| component | repository | commit | license |
|---|---|---|---|
| VINS-Fusion | github.com/HKUST-Aerial-Robotics/VINS-Fusion | `be55a937a57436548ddfb1bd324bc1e9a9e828e0` (2021-07-26) | GPL-3.0 |
| DynaVINS | github.com/url-kaist/dynaVINS | `0b4f492aeeb1a3752507a9b9a50124e10bfcf091` (2025-08-08) | GPL-3.0 (LICENSE file in the repo) |
| ORB-SLAM3 | github.com/UZ-SLAMLab/ORB_SLAM3 | `4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4` (v1.0, 2022-02-10) | GPL-3.0 |
| Pangolin (ORB-SLAM3 dependency) | github.com/stevenlovegrove/Pangolin | `dd801d244db3a8e27b7fe8020cd751404aa818fd` (v0.6) | MIT |
| base image | `ros:noetic-perception-focal@sha256:32370c50…` | | ROS packages: BSD and others |

The image only fetches these sources at the pinned commits. Nothing is vendored here. The code in this directory
(`sota_tools`, scripts, configs, patches) links against or modifies GPL-3.0 code, so it is GPL-3.0 as well. Ceres
1.14 (BSD), OpenCV 4.2 (BSD/Apache-2) and Eigen 3.3 (MPL-2) come from the Ubuntu 20.04 / ROS apt packages.

`/opt/sota/COMMITS.txt` in the image records the commits. Each `run_info.yaml` copies them as well.

## Build

```bash
src/savior/sota/build.sh            # JOBS=8 by default; about 15 min; image about 7 GB
```

## Patches (`patches/apply_patches.sh`)

| id | target | change | behaviour |
|---|---|---|---|
| P1 | VINS-Fusion, DynaVINS | OpenCV 4 replacements for the removed C-API constants: `CV_LOAD_IMAGE_GRAYSCALE`, `CV_AA`, `CV_GRAY2RGB`, `CV_CALIB_CB_*`, `CV_TERMCRIT_*`, … → `cv::` equivalents; adds `imgproc_c.h` where the `CV_RGB()` macro is used | none (compile fix) |
| P2 | VINS-Fusion, DynaVINS | `-std=c++11` → `-std=c++14` (Noetic headers) | none |
| P3 | VINS-Fusion | `global_fusion` (GPS) not built (`CATKIN_IGNORE`) | n/a |
| P4 | DynaVINS | copies `brief_k10L6.bin` / `brief_pattern.yml` from VINS-Fusion (README step; only loop_fusion uses them) | none |
| P5 | VINS-Fusion, DynaVINS | per-frame timing log to `$SOTA_TIMING_FILE`: front-end = `featureTracker.trackImage` for every stereo pair; back-end = `processImage` for every frame the estimator processes | none (one `fprintf` per frame, only when the variable is set) |
| P6 | ORB-SLAM3 | `find_package(OpenCV 4.4)` → `4.2` (focal) | none |
| P7 | ORB-SLAM3 + Thirdparty | drop `-march=native` (portable image) | numerically negligible |
| P8 | ORB-SLAM3 `SaveTrajectoryEuRoC` | if `$ORBSLAM3_SAVE_IN_WORLD` is set, skip the re-basing on the first keyframe's IMU pose. That pose is not gravity-aligned, while posyaw needs a z-up world. Default = upstream | output only |
| P9 | VINS-Fusion | SAVIOR dynamic masks + deterministic synchronous mode (`patches/vins_fusion_savior_mask.patch`, section "VINS-Fusion + SAVIOR masks") | none unless the optional `savior_*` keys are set |

## Data feeding

`scripts/make_ros1_bag.sh <seq> <dst.bag>` runs `rosbags-convert` (ROS 2 mcap → ROS 1, typestores `ros2_humble` →
`ros1_noetic`) in the savior image. It keeps only `/cam0/image_raw`, `/cam1/image_raw` (rgb8, unchanged) and
`/imu0`. It then runs `verify_ros1_bag.py`, which checks that message counts, header stamps (exact ns) and bag
times are identical to the source. A bag is about 2.6 GB. `run_sequence.sh` deletes it after the sequence's runs.

- VINS-Fusion and DynaVINS take rgb8 and convert it to mono8 themselves (`cv_bridge`).
- The ORB-SLAM3 driver converts with the same `cv_bridge` call.

## Methods, configs and frames

All methods run stereo + IMU, with the input given by `rosbag play -r RATE -s OFFSET`. For ORB-SLAM3, the driver
reads the bag with the same offset semantics.

Every `stamped_traj_estimate.txt` is TUM, with stamps in seconds (exact image header stamps) and pose
**T_world_IMU** in a gravity-aligned z-up world. This is the GT convention: `data/viode/gt`, IMU = AirSim NED body.

### `vins_fusion`
- **Config:** `config/viode/vins_fusion/` is VIODE's own calibration files (`data/viode/meta/calibration_files`,
  VIODE commit 521bdff), already in VINS-Fusion format and used **verbatim**. The harness rewrites only
  `output_path` and `pose_graph_save_path` at run time.
  - `multiple_thread: 1`: as upstream, the estimator then processes every 2nd stereo frame (10 Hz).
- **Output:** recorded from `/vins_estimator/odometry` (`Ps/Rs[WINDOW_SIZE]` = IMU-body pose of the newest frame
  after each optimization; causal).
- **Loop closure:** VINS-Fusion's loop closure is a separate node (`loop_fusion_node`), which is not started, so
  runs are pure VIO.
  - `vins_fusion+lc` starts it and records `/loop_fusion/odometry_rect`: the causal, loop-corrected body pose.

### `dynavins`
- **Config:** `config/viode/dynavins/` is DynaVINS' own VIODE stereo config (`config/viode/calibration_stereo.yaml`
  + cams, from `launch/viode/viode_stereo.launch`), used **verbatim** except `output_path`. It differs from the
  VIODE file as follows:
  - max_cnt 150, min_dist 15, F_threshold 2;
  - max_depth 10;
  - max_solver_time 0.3, 10 iterations;
  - DynaVINS weights: λ = 2, momentum 0.2, convergence 0.9, margin threshold 0.1.
- **Output:** same as VINS-Fusion (`/vins_estimator/odometry`).
- **Loop closure:** DynaVINS' VIODE setup is BA-only. The authors validated their loop module only on their own
  dataset, and the VIODE config has no loop parameters. Loop closure is therefore off, and `+lc` is refused.

### `orbslam3`
- **Driver:** `sota_tools/orbslam3_bag_si` reads the ROS 1 bag and reproduces
  `Examples/Stereo-Inertial/stereo_inertial_euroc.cc`:
  - the same IMU association;
  - frame-locked pacing: it sleeps `dt/rate − t_track`, and frames are never dropped;
  - mono8 input.
- **Config:** `config/viode/orbslam3/viode_stereo_inertial.yaml` is upstream `EuRoC.yaml` with these changes only:
  - VIODE intrinsics, size and 20 fps;
  - `Stereo.T_c1_c2` = 5 cm along +x;
  - `IMU.T_b_c1` = VIODE `body_T_cam0`;
  - `loopClosing: 0`.
  
  Everything else stays at the upstream default: 1200 ORB features, ThDepth 60, EuRoC IMU noise.
- **Output:** `stamped_traj_estimate.txt` comes from `SaveTrajectoryEuRoC` with P8, in the IMU body frame
  (`T_wb = (T_bc · T_cw)^-1`, upstream code). It covers all tracked frames of the largest map. Frame poses are
  stored relative to their reference keyframe, so they are refined by local BA and are not strictly causal.
- **Secondary outputs:**
  - `traj_realtime.txt`: causal `TrackStereo` output, `T_wb = T_cw^-1 T_cb`. Its world frame jumps at IMU
    initialization, so it is diagnostic only.
  - `traj_upstream.txt`: the upstream re-based file.
- **Loop closure:** `loopClosing: 0` turns off place recognition, loop closing and map merging. The variant
  `orbslam3+lc` turns it back on.

### Frame verification
`scripts/check_frames.py` SE(3)-aligns positions and reports `body_res_deg`, the angle of the mean
`R_gt^T R_align R_est`, and `tilt_deg`, the tilt of the estimate's world z axis relative to gravity.
- An IMU-frame output gives ≈ 0° body residual.
- A camera-frame output would give ≈ 120°, because VIODE's `R_imu_cam0` is a 120° axis permutation and the
  translation is 0.
- `tilt_deg` ≈ 0 means posyaw alignment is valid.

## Harness

```bash
S=src/savior/sota/scripts
# one sequence, all methods, P5 offsets (run_XX <-> XX-th offset of scripts/viode_offsets.txt), temp bag deleted after
BAGDIR=/path/to/scratch RUNS="1 2 3 4 5 6 7 8 9 10" $S/run_sequence.sh parking_lot_high vins_fusion dynavins orbslam3
# + one bag-start run per method (dir <method>_fromstart/run_01)
BAGDIR=... FROMSTART_TOO=1 $S/run_sequence.sh city_night_none vins_fusion dynavins orbslam3
# full benchmark: jobs file lines "<seq> <method> <method> ...", PARSEQ sequences at a time (default 2)
BAGDIR=... LOGDIR=... PARSEQ=2 $S/run_benchmark.sh jobs.txt
# evaluation (savior image): posyaw (protocol) + se3 + sim3 -> <method dir>/eval_<align>/, frame check
$S/eval_sota.sh results/sota/viode_parking_lot_high/*
```

- **Output layout:** `results/sota/viode_<seq>/<method>/run_XX/` holds:
  - `stamped_traj_estimate.txt` and `run_info.yaml`;
  - `timing.csv`, `estimator.log`, `config/` (the exact config used), `play.log`.

  Set `ROOT=` to change the root.
- **Isolation:** each (sequence, method) pair runs in its own `--network none --ipc private --cpus 4` container
  (`SOTA_CPUS`), as the calling user (`--user`), and its offsets run in series.
- **Defaults:** `RATE=0.5`, the same playback rate as the P5 OpenVINS runs.
- **Disk guard:** `run_benchmark.sh` stops when free disk drops below `MIN_FREE_GB` (default 30).

## Validation (M3a, 2026-10-23)

Results are in `results/sota_validation/viode_<seq>/<method>/`. Regenerate the table with
`scripts/summarize.py results/sota_validation` (run it in the savior image).

- **Sequences:** parking_lot {none, high} and city_night {none, high}.
- **Runs:** runs 1/5/9 at the P5 offsets, plus one run from bag start (`*_fromstart`), plus a from-start `+lc` run.
- **Rate:** 0.5.

Summary (posyaw ATE in m; the published values are DynaVINS++ Table II):

- **VINS-Fusion:** in the published range on all 4 sequences (PL none 0.14, PL high 0.28, CN none 0.33,
  CN high 0.93).
- **DynaVINS:** in range from bag start on all 4 sequences (0.06 / 0.06 / 0.18 / 0.16) and at the P5 offsets on
  city_night.
  - On parking_lot, late starts diverge right after initialization: PL high offsets 5 and 9 fail in 6/6 repeats,
    and PL none offset 5 fails once.
  - Likely cause: the stereo-IMU init starts from zero velocity while the window is already accelerating, and the
    robust BA weights do not recover from that. VINS-Fusion, with the same init, does recover.
- **ORB-SLAM3:**
  - parking_lot: good (PL none 0.04, PL high 0.41).
  - city_night: fails (CN none 19–550 m, CN high 1.1–1.95 m with a single 517 m run). The published values are also
    poor (0.71 / 3.0 m).
  - Cause: ORB features run out on the dark frames. The tracker is RECENTLY_LOST for about 5 s, with IMU-only
    propagation over that span.
  - Diagnostic only, not adopted: FAST 12/5 instead of 20/7 brings CN none to 1.25 m. Playback rate 1.0 does not
    help.
- **Frames:** the frame check gives 0.04–0.8° body residual (IMU frame confirmed) and 0.1–3° world tilt, so posyaw
  alignment is valid.
- **Loop closure:** VINS-Fusion `loop_fusion` detected no loop on these trajectories, so `+lc` equals VIO.
  ORB-SLAM3 `+lc` changes ATE by −0.2…+0.04 m (thread non-determinism and BA).

Per-frame time on this desktop, with 6 containers in parallel and 4 CPUs each:

| method | timing |
|---|---|
| VINS-Fusion | front-end 7.9 ms per stereo pair, back-end 15.8 ms per processed frame (every 2nd) |
| DynaVINS | front-end 8.1 ms, back-end 39 ms (p90 71 ms) |
| ORB-SLAM3 | `TrackStereo` 15.0 ms (p90 17.5 ms); local mapping runs in its own thread |

## SAVIOR-Warehouse configs (M3b, evaluation-only baselines on the t2 held-out split)

`config/warehouse/{vins_fusion,dynavins,orbslam3}/`, derived from `savior_bringup/config/warehouse/kalibr_imucam_chain.yaml`
and `kalibr_imu_chain.yaml`. Each file's header lists its derivation. Every other parameter is the method's default.

| value | source | VINS-Fusion | DynaVINS | ORB-SLAM3 |
|---|---|---|---|---|
| intrinsics | kalibr cam0/cam1 `[470, 470, 336, 188]`, radtan 0 | cam*_pinhole.yaml | same | Camera1/2 fx, fy, cx, cy, k = 0 |
| image size, rate | 672x376, 20 Hz | image_width/height | same | Camera.width/height, fps 20 |
| cam0 extrinsic | T_imu_cam0 = R[[0,0,1],[-1,0,0],[0,-1,0]], p (0, +0.06, 0); T_i_b = I | body_T_cam0 | same | IMU.T_b_c1 |
| cam1 extrinsic | T_imu_cam1, p (0, -0.06, 0) | body_T_cam1 | same | Stereo.T_c1_c2 = inv(T0) T1 = I, +0.12 m x |
| time offset | timeshift_cam_imu 0 | td 0, estimate_td 0 | same | n/a |
| IMU noise | kalibr: acc 1.6e-3, gyro 2.44e-4, acc RW 3e-4, gyro RW 2e-5, 200 Hz | upstream EuRoC values x (warehouse / EuRoC kalibr density): acc_n 0.08, gyr_n 0.0144, acc_w 1.0e-4, gyr_w 1.03e-4 | same as VINS-Fusion | kalibr values verbatim (same convention as EuRoC.yaml), Frequency 200 |
| gravity | simulator G = 9.81 | g_norm 9.81 | same | built-in 9.81 |
| other parameters | | upstream `euroc_stereo_imu_config.yaml` | DynaVINS ships no EuRoC config, so its own stereo-IMU VIODE setting is used | upstream `Stereo-Inertial/EuRoC.yaml`, loopClosing 0 |

- **Frame check (all 240 VINS-family warehouse runs):** body residual ≤ 0.57°, world tilt ≤ 0.73°. Output is IMU frame,
  posyaw valid.
- **Dev check before held-out:** one run each on t1 hall_L0 / aisles_L2 (`results/sota/dev_t1_configcheck`). It verified
  the configs and frames; nothing was tuned.
- **ORB-SLAM3 on the warehouse never initializes with upstream defaults.** `Tracking::StereoInitialization` needs more
  than 500 keypoints *and* an inter-frame mean-acceleration change of at least 0.5 m/s². The smooth simulated
  trajectories never meet the second condition, so every frame stays NOT_INITIALIZED and there are 0 poses.
  - The upstream escape `IMU.fastInit` is parsed only by the legacy (non-`File.version 1.0`) settings path, so it cannot
    be enabled without a code patch. It was not changed.

**Harness changes (M3b):**
- `DATASET=viode|warehouse` selects the source bag (`make_ros1_bag.sh`), the config dir (`run_one.sh`), the offsets file
  (`<dataset>_offsets.txt`) and the GT (`eval_sota.sh`).
- `run_benchmark.sh` now feeds `run_sequence.sh` from `/dev/null`. Before this fix, `docker run -i` consumed the jobs
  file, so only the first PARSEQ+1 sequences ran.

## Known issues
- With the P5 late-start offsets, DynaVINS diverges systematically on parking_lot. The protocol choice (P5 offsets
  vs bag start) changes its ranking.
- ORB-SLAM3 with the upstream FAST thresholds fails on city_night. Upstream's EuRoC.yaml comment suggests lowering
  them for low-contrast images, but that has not been adopted, so the defaults stay.
- None of the methods is bit-deterministic (multi-threaded). VINS-Fusion is close: repeated runs differ by 0–0.1 m.

## VINS-Fusion + SAVIOR masks (back-end-agnostic SAVIOR, P9)

SAVIOR's perception output (layered per-frame masks, mono8: 0 keep, 192 extension band, 255 dynamic core;
`docs/INTERFACE.md` §3.1) is back-end independent. Two pieces make it usable by VINS-Fusion:

**1. Offline mask export (`mask_export/`).** `export_masks.py` instantiates the real `savior_node`
(`savior_perception.node.SaviorNode`) with exactly the parameter list `savior_bringup/launch/savior.launch.py` builds for
the frozen methods (`frozen_params.py` reads `results/p7/final_config.yaml` + `final_config_addendum.yaml`;
`--check-log <launch.log>` asserts equality with an online run) and drives it with the bag messages in bag order from
`starting_time + start_offset` (= `ros2 bag play --start-offset`), emulating the exact-time synchronizer. The node's own
gyro-coverage hold makes this deterministic. Perception inputs are images, IMU and (oracles) the GT segmentation only —
there is no filter feedback — but the tracker / motion / selective state starts at the first played frame, so masks are
exported **per start offset**:

```
<out>/<seq>/<method>/off_<offset>/{left,right}/<left stamp ns>.png   (+ index.csv, stats.jsonl.gz, export_info.yaml)
<out>/<seq>/<method>/pool/<md5>.png                                   (content-addressed; the per-offset files are hard links)
# run in the savior image with the method's install sourced (frozen_edge/install for savior_edge), GPU for YOLO:
python3 mask_export/export_masks.py --seq hall_t1_L3 --method sens_fix1 --offsets 0.0 0.2 --out masks
python3 mask_export/export_masks.py --seq hall_t1_L3 --method zero --out masks       # all-zero control masks
```

**2. VINS-Fusion patch P9 (`patches/vins_fusion_savior_mask.patch`, applied by `apply_patches.sh`;
`build_mask.sh` builds `savior-sota:noetic-mask` incrementally on an existing `savior-sota:noetic`).** Optional yaml keys
(documented in `vins_estimator/src/featureTracker/savior_mask.h`); without them VINS-Fusion is unchanged:

| key | default | meaning |
|---|---|---|
| `savior_mask_dir` | "" | mask directory (`left/`, `right/`, `<stamp ns>.png`); enables masking |
| `savior_mask_mode` | gate | `gate`: tracked features whose current pixel is masked are dropped (left; right observations on the right mask), no detection on masked pixels. `deferred`: SAVIOR-edge latency emulation (below) |
| `savior_mask_threshold` / `_relaxed_threshold` / `_min_features` | 128 / 224 / 30 | as the OpenVINS fork (`dynamic_mask_threshold`, `_relaxed_threshold`, `_min_features` of the warehouse config): band 192 rejected unless fewer than 30 tracked features of that camera would survive, then core only |
| `savior_mask_latency_ms` | 250 | `deferred` only |
| `savior_mask_wait_ms` | 0 | wait for a missing mask file (online producers); 0 = offline. A missing mask = no masking for that frame (counted) |
| `savior_mask_stats` | "" | per-frame CSV (kept / dropped / relaxed / features left on core = sanity 0) |
| `savior_deterministic` | 0 | no estimator thread: each frame the upstream thread would process (`multiple_thread: 1`: every 2nd) is processed synchronously as soon as the IMU covers it, so the tracker prediction from `processImage` is always in place for the next frame |
| `savior_ignore_solver_time` | 0 | `max_solver_time` not applied (iteration cap `max_num_iterations` only), removes the wall-clock dependence |

- Masks are synced by the **exact** left header stamp (ns, taken from the ROS header, not the double time).
- Right image: VINS-Fusion has no right-image detection (right features are LK-tracked from the left); right
  observations are gated with SAVIOR's own right mask (the frozen stereo warp OpenVINS consumes).
- `deferred` (= OpenVINS fork `dynamic_mask_sim_latency_ms=250, dynamic_mask_deferred=true,
  dynamic_mask_stale_gating=false`): no current-frame gating; the mask of frame k arrives at the first frame j with
  t_j ≥ t_k + latency; every feature observed inside it at frame k (left or right) is removed from the tracker and from
  the estimator's sliding window (`FeatureManager::removeOutlier`). Observations already marginalized stay in the prior
  (the MSCKF analogue: features already used in an update cannot be undone).
- Harness: `run_one.sh` appends the keys to the run's config copy from `SOTA_MASK_DIR` (may contain `{off}`),
  `SOTA_MASK_MODE`, `SOTA_MASK_LATENCY_MS`, `SOTA_MASK_THRESHOLD`, `SOTA_MASK_RELAXED`, `SOTA_MASK_MIN_FEATURES`,
  `SOTA_DETERMINISTIC`, `SOTA_IGNORE_SOLVER_TIME`; `SOTA_IMAGE=savior-sota:noetic-mask`, `MDIR_NAME=<method dir>`.
- Determinism (warehouse t1, 4 CPUs per container, loaded machine): upstream multi-threaded VINS-Fusion repeats differ;
  `savior_deterministic` alone still diverges whenever `max_solver_time` binds (2–3 of ~1100 solves under load); with
  both keys repeated runs are md5-identical, and all-zero masks give md5-identical trajectories
  (`results/vins_savior/REPORT.md`).

## DynaVINS + SAVIOR masks (P10, port of P9)

Answers "does DynaVINS improve with SAVIOR masks?" (`results/dynavins_masks/REPORT.md`). DynaVINS is VINS-Fusion-based,
so P10 (`patches/dynavins_savior_mask.patch`, unified diff on top of P1-P5) is P9 ported hunk by hunk: the same
`savior_mask.{h,cpp}` (mask source, counters, per-frame CSV), the same feature-tracker gating (exact left header stamp
in ns; tracked features whose current pixel is masked are dropped, left and right observations on their own masks;
detection blocked on masked pixels; band 192 rejected unless fewer than 30 tracked features of a camera would survive,
then core only = defaults 128 / 224 / 30), the same `deferred` SAVIOR-edge latency mode (250 ms, invalidated ids removed
from the tracker and from the sliding window via `FeatureManager::removeOutlier`), and the same
`savior_deterministic` / `savior_ignore_solver_time` estimator hooks (adapted to DynaVINS' `processMeasurements`,
`optimizeVIO` and its 2-space layout). One key is new:

| key | default | meaning |
|---|---|---|
| `savior_solver_threads` | 0 (= upstream `num_threads = 2`) | Ceres threads of `optimizeVIO`. DynaVINS (unlike VINS-Fusion) runs Ceres with 2 threads, whose parallel cost / Schur-complement sums are thread-order dependent; 1 makes them reproducible |

- **Image:** `build_mask_dyna.sh` builds `savior-sota:noetic-mask-dyna` from `savior-sota:noetic`
  (`docker/Dockerfile.savior_mask_dyna`, no network; only DynaVINS + camera_models are rebuilt; COMMITS.txt gets a
  `P10 dynavins_savior_mask.patch <md5>` line). `apply_patches.sh` is not changed (it is frozen with the P9 study).
- **Harness:** `scripts/run_method_dm.sh` -> `drun_sota_dm.sh` -> `run_one_dm.sh` are copies of the frozen
  `run_method.sh` / `drun_sota.sh` / `run_one.sh` that also append the `SOTA_MASK_*`, `SOTA_DETERMINISTIC`,
  `SOTA_IGNORE_SOLVER_TIME` keys for `dynavins`, plus `SOTA_SOLVER_THREADS` -> `savior_solver_threads`; default image
  `savior-sota:noetic-mask-dyna`. `run_one_dm.sh` also fixes a latent `run_one.sh` bug: the 3-field P9/P10 line in
  COMMITS.txt made the `run_info.yaml` writer fail in the mask images (trajectories were unaffected).
- **Deterministic mode used for every DynaVINS method incl. the plain baseline:** `savior_deterministic 1`,
  `savior_ignore_solver_time 1`, `savior_solver_threads 1`. Measured on warehouse hall t1 L0/L3, runs 1/5: upstream
  repeats differ (ATE up to 3 %); `deterministic + ignore_solver_time` with 2 Ceres threads still differs between
  repeats; with 1 thread repeats are md5-identical, and all-zero masks are md5-identical to no masks.
- The DynaVINS configs (`config/<warehouse|viode>/dynavins`) are used unchanged (not retuned).
- Study: `results/dynavins_masks/` (t1 tuning, then held-out t2 + VIODE after `FREEZE.md5`). Empty-mask control
  80/80 (t1), 120/120 (t2), 120/120 (VIODE) md5-identical; 0 missing masks; deterministic vs upstream DynaVINS ATE
  −0.1 % on every split.
