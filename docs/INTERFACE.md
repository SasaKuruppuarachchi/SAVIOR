# SAVIOR: system overview and interface contract

This document is the source of truth for how the pieces of SAVIOR fit together: the repository layout, the data flow, and
the interfaces between the perception node, the OpenVINS fork and the experiment runner. If you change an interface
below, update this file in the same change.

## 0. Ground rules

- **All execution happens inside Docker** (ROS 2 Humble, Python, builds, tests, evaluation). See `docker/README.md`.
  Nothing needs to be installed on the host besides Docker and the NVIDIA container toolkit.
- The colcon workspace (`SAVIOR_WS`) is mounted in the container at the **same absolute path** as on the host, so paths in
  configs, logs and run directories are identical inside and outside the container. The container user equals the host
  user (uid/gid), so files are not root-owned.
- Design rules: stereo camera + IMU only (depth comes from stereo); the back-end is OpenVINS with its MSCKF internals
  untouched (SAVIOR acts on it only through masks); the semantic informer must run in real time on a Jetson Orin NX 8 GB.

## 1. Repository layout

This repository is the content of `<ws>/src/savior/` in a colcon workspace (self-contained: clone, `docker/build.sh`,
`colcon build`). Datasets, models and results live in the workspace next to `src/` and are never in git.

```
<ws>/                               # colcon workspace = $SAVIOR_WS (not the repository)
├── data/                           # datasets (never in git); converted outputs live next to the raw data
│   ├── uhumans2/ openloris/ viode/ monado/   # third-party datasets: raw/, ros2/ (bags), gt/ (TUM)
│   └── warehouse/                  # SAVIOR-Warehouse: ros2_stereoseg/<seq>/ (bags), gt/<seq>.txt
├── models/                         # segmenter weights / TensorRT engines (never in git)
├── results/                        # experiment outputs (trajectories, eval reports)
└── src/savior/                     # ===== REPOSITORY ROOT =====
    ├── README.md
    ├── docker/                     # Dockerfiles, run/exec scripts, README (desktop x86_64 and Jetson)
    ├── docs/INTERFACE.md           # this file
    ├── open_vins/                  # vendored OpenVINS fork (GPL-3.0; ov_core, ov_init, ov_msckf, ov_eval)
    ├── savior_perception/          # ament_python: segmenter + stereo depth + classification + tracking + mask output
    ├── savior_perception_cpp/      # C++ / TensorRT port of the perception node
    ├── savior_ov_component/        # OpenVINS as a composable component
    ├── savior_bringup/             # launch files, dataset configs, class-role YAMLs, dataset preparation tools
    ├── savior_eval/                # experiment runner (savior-run), evaluation (savior-eval; rpg_trajectory_evaluation py3 port, MIT)
    ├── savior_datasets/warehouse/  # Isaac Sim generator of SAVIOR-Warehouse
    ├── sota/                       # VINS-Fusion / DynaVINS baselines (ROS 1 Docker) and mask patches
    └── experiments/                # frozen per-study scripts, configs and reports, as run
```

## 2. Data flow

```
left/right image ──► savior_perception ──► /savior/mask/left, /savior/mask/right ──┐
       │              (segment → ROI stereo depth → promote → track → extend)       │
       └──────────────────────────────────────────────────────────────────────────┴─► OpenVINS (ov_msckf ROS 2)
IMU ─────────────────────────────────────────────────────────────────────────────────► OpenVINS
```

## 3. Interface contract

### 3.1 Dynamic mask topics

- `/savior/mask/left`, `/savior/mask/right`: `sensor_msgs/msg/Image`, encoding `mono8`,
  **same width/height as the corresponding raw camera image**.
- `header.stamp` **must equal exactly** the stamp of the source left image (the right mask uses the same stamp).
  `header.frame_id` is the camera's frame id.
- Pixel values (layered, so OpenVINS can relax the outer layer when features run short):
  - `0`   keep
  - `192` **extension band** (depth-guided mask extension; relaxable)
  - `255` **dynamic core** (always-dynamic + promoted instances + tracker-carried masks; never relaxed)
  - optional (semantic gate, `compose.movable_static_value`, default 0 = off): `64` **movable-static**, a movable-class
    object currently classified static (kept). It is written only into keep pixels and lies below every rejection
    threshold, so the binary gating masks are unchanged. It is used only by the fork's semantic chi-square gate
    (`savior_semantic_gate`).
- QoS: reliable, depth 10 (offline bag replay must not drop masks).
- Right mask: the left mask warped by per-pixel disparity where valid, else by the instance's median disparity.
  This is a boundary warp: each layer's outer contour is warped pixel by pixel (raw-left, rect-left, minus d,
  rect-right, raw-right) and filled; the per-pixel d is used when it is consistent with the instance depth band.
- `savior_node` publishes exactly one left+right mask pair for **every** exact-time-synced stereo frame (all zeros when
  nothing is dynamic, when there is no calibration (right mask), or when processing fails). Masks are never resampled
  with interpolation (only nearest/exact writes), so the 0/192/255 values survive.
- OpenVINS must run with `downsample_cameras: false` when SAVIOR masks are used (its pyrDown would blur the layers).

### 3.2 OpenVINS fork parameters (estimator_config.yaml)

Implemented in `open_vins/` (details, patch list and rationale: `open_vins/SAVIOR_FORK.md`). All keys are optional;
`use_dynamic_mask: false` (default) is bit-identical to upstream (verified on the KLT tracker output).

```yaml
use_dynamic_mask: true                 # subscribe to dynamic masks; gating mask = max(static > 127, dynamic >= threshold) (ROS 2 only)
dynamic_mask_topic0: "/savior/mask/left"   # topic per camera index; "" = no dynamic mask for that camera (cams >= 2 default "")
dynamic_mask_topic1: "/savior/mask/right"
dynamic_mask_policy: "wait"            # "wait": hold the image until masks with identical stamp (int64 ns) arrive (deterministic, offline eval)
                                       # "latest": use the newest mask with stamp <= image stamp (online / real-time)
dynamic_mask_timeout_ms: 100           # "wait": wall time from image arrival; then fall back to the newest mask <= stamp (max 1 s old), else empty
dynamic_mask_max_pending: 64           # "wait": more held measurements than this -> head released regardless of the timeout
                                       # (64 is about 6.4 s); <= 0 = no count cap (timeout only)
dynamic_mask_threshold: 128            # pixel >= threshold is rejected (1..256; 256 = never reject = observe-only, for baseline stats)
dynamic_mask_relaxed_threshold: 224    # used for a camera whose kept (tracked+new) features < min_features (drops the 192 band, keeps 255)
dynamic_mask_min_features: 60          # PER CAMERA, w.r.t. the post-init target num_pts/max_cameras; scaled down proportionally
                                       # while the tracker runs with the smaller init target (init_max_features/max_cameras); <=0 = off
                                       # (the savior_bringup configs use 30)
record_feature_stats: ""               # optional CSV (KLT tracker; also works with use_dynamic_mask=false), one row per frame & camera:
                                       # timestamp,cam_id,n_tracked,n_new,n_rejected_mask,relaxed,n_in_band,n_in_core
                                       # n_in_band/n_in_core = kept features on raw DYNAMIC mask pixels 128..254 / 255 (core must stay 0)
deterministic_processing: false        # offline replay independent of wall-clock timing (sync subscriber, initializer on IMU
                                       # up to the image time, lossless QoS); the savior_bringup launches set it (deterministic:=true)
dynamic_mask_after_init: false         # ignore the dynamic masks until the filter is initialized
dynamic_mask_init_policy: "normal"     # masks before init: normal | none (= after_init) | core (only 255) | relax (255 -> 192)
savior_semantic_gate: false            # per-feature chi2 multiplier from the mask label (0 bg x1 / 1..127 x mult_static /
savior_sg_mult_static: 1.0             #     >= 128 x mult_band); savior_sg_keep_band keeps band features (front-end rejects >= 224)
savior_sg_mult_band: 1.0
savior_sg_keep_band: false
savior_nis_gate: false                 # NIS-adaptive control: multiplier x median(chi2 / chi2_0.5(dof)) over savior_nis_window tests
savior_nis_window: 200
dynamic_mask_upstream_compat: false    # frames without dynamic pixels run the exact upstream front-end, out-of-bounds points
                                       # are not "masked" -> backend:=none is identical to use_dynamic_mask: false (clean control)
```

Front-end patches (ov_core, active only when `use_dynamic_mask: true`): the dynamic mask travels in
`CameraData::masks_dynamic` (separate from the static mask) and is binarized at the threshold at tracker entry; the mask
is applied to **already-tracked** features in the stereo KLT path (upstream only checks them in mono), left vs left mask and
right vs right mask; right-only detections use the right mask (upstream used the left one); relaxation re-gates the
current frame and the relaxed mask is kept for the next top-off detection. Masks must be published for every frame, with
RELIABLE QoS (a best-effort publisher does not match the reliable subscriber), with the stamp copied verbatim from the
left image header.

### 3.3 savior_perception node (`savior_node`)

- Subscribes: `left_topic`, `right_topic` (`sensor_msgs/Image`, exact-time sync) and, for the oracle backends, `seg_topic`.
  With `motion.enable` it also subscribes to `imu_topic` (`sensor_msgs/Imu`, gyro in the IMU frame of `calib_file`): each
  synced frame is then held until gyro samples cover its stamp (released after `imu_wait_ms` only if the IMU stream is
  silent), so replays stay deterministic. `savior.launch.py` sets `imu_topic` per dataset and `motion.static_mask_file`
  from the estimator yaml's `mask0` (both unused unless `motion.enable`).
- Calibration: reads the **same OpenVINS `kalibr_imucam_chain.yaml`** (single source of truth) and rectifies internally
  (pinhole-radtan and equidistant/fisheye are supported).
- Publishes: `/savior/mask/left`, `/savior/mask/right` (3.1), `/savior/debug/overlay` (bgr8, optional),
  `/savior/stats` (`std_msgs/String`, JSON: stamp, timings per stage in ms, number of instances per role, number promoted,
  number tracked).
- Optional `seg_right_topic` (oracle backends only, default ""): the ground-truth semantic image of the RIGHT camera, synced
  as a fourth input; the right mask is then its dynamic-role instances (255) instead of the stereo warp (for example VIODE
  `/cam1/segmentation`).
- Key parameters: `segmenter.backend` (`yolo` | `oracle_uhumans2` | `oracle_colormap` | `none`), `segmenter.model`
  (path to a .pt/.engine), `segmenter.conf`,
  `segmenter.colormap_file` (oracle colour-to-class yaml), `calib_file` (kalibr_imucam_chain.yaml; empty = no stereo: no
  depth, right mask all zeros), `cam_left`/`cam_right`, `roles_file` (class-role YAML; empty = package
  `config/roles_default.yaml`), `depth.*`, `gating.*`, `tracker.*`, `extension.*`, `compose.*`, `motion.*`,
  `publish_debug`. The full list with defaults and rationale is in `savior_perception/config/default.yaml` (a unit test
  keeps it equal to the code defaults).
- Ablations: cdo_off = `gating.enable:=false`; pp_off = `extension.enable:=false tracker.enable:=false`;
  paper thresholds = `gating.mode:=fixed extension.band_mode:=fixed`; no stereo = `depth.enable:=false`.

### 3.4 Class-role YAML (savior_bringup/config/roles/*.yaml)

```yaml
# role in {static, potential, dynamic, ignore}; class names as emitted by the segmenter backend
dynamic:   [person]
potential: [chair, suitcase, backpack, handbag, bicycle, car, cart]
static:    []
default: ignore            # classes not listed
half_extent_m: {car: 1.5}  # optional: per-class half depth extent [m] for the promotion size prior
```

The warehouse profile (`roles/warehouse.yaml`) uses dynamic [person]; potential [forklift, box, pallet, trolley];
static [rack, guard_rail, window].

### 3.5 Core algorithm (pure Python, no ROS imports: `savior_perception/core/`)

- `Segmenter.predict(image) -> list[Instance]`; `Instance{mask: bool HxW, cls: str, score, bbox(x0,y0,x1,y1), role}`.
- **ROI stereo depth**: SGBM only inside the (dilated) bboxes of dynamic/potential instances on rectified pairs;
  `z = f*b/d`; noise model `sigma_z(z) = z^2 * sigma_d / (f*b)`; the per-instance robust depth is the median over valid
  mask pixels. Rectified crops are remapped directly from the raw images (no full-frame rectification), optionally
  decimated (`depth.downsample`, default 2; disparity kept in full-resolution px); the rectified frame is by default
  auto-sized to contain every valid raw pixel (capped at 2x raw size for fisheye); the mask median uses a 2-px eroded
  mask (edge fattening).
- **Promotion** (association tree): fixpoint/BFS from the dynamic roots. A potential instance p is linked to a promoted or
  dynamic parent q iff the dilated 2D masks overlap AND `|z_p - z_q| < size_prior + k * sigma_z(z)`. Implemented with
  `size_prior = half_extent(p) + half_extent(q)` and `sigma = sqrt(sigma_z(z_p)^2 + sigma_z(z_q)^2)` (k = 3, half extent
  0.35 m default; optional cap `gating.max_threshold_m`). `gating.unknown_depth_policy` (overlap | reject) applies when a
  depth is missing; `gating.mode: fixed` gives the fixed distance gate (d_int). The promoted set is order-independent.
  Hook for motion evidence (`MotionEvidence`: True = extra root, False = veto; False for an always-dynamic instance gives
  status `still`: not a root, not masked or band-only).
  Short-baseline options (default off): `gating.max_noise_m` caps the `k*sigma` term; `gating.link_depth: contact`
  compares the depths of both instances in a ring along their shared boundary (an occlusion contact is a depth jump and
  is refused), with the fallback `gating.contact_fallback` (median | reject).
- **Motion evidence** (`core/motion.py`, `motion.enable`): gyro rotation between frames + ego translation from background
  KLT points with KLT stereo depth (robust fit, no accelerometer). Per instance, an instantaneous GLS test of the
  ego-compensated flow (depth-robust: along-epipolar residuals weighted by the parallax uncertainty) and a windowed
  (0.4-0.8 s) anchor-displacement test against the chained ego-motion; a log-odds moving probability with hysteresis per
  motion track. A static person gives `still`; a moving potential becomes a root; a static potential is vetoed.
  `tracker.motion_model: ego` predicts carried masks with the ego-motion at the track depth (plus the track's own velocity).
- **Further options (all default off):** `gating.promote_contact: false` (no interaction promotion, roots only: ablation),
  `gating.max_depth: N` (maximum number of promotion hops from a root, BFS depth; person, forklift, box = 2; stops chains
  spreading through touching static box/pallet stacks), `motion.window_unveto_potential: true` (a windowed "moving" result
  cancels a potential object's static veto: log-odds reset to 0, promotable by contact, not a root; co-moving or leading
  objects move along the epipolar line where the instantaneous test is blind). Warehouse bags with ground-truth right
  masks: `savior_datasets/warehouse/tools/to_ros2.py --seg-right` (`/cam1/segmentation(_moving)`).
- **Selective policy** (`core/selective.py`, `selective.enable`, default off): "conservative by default, selective when
  confident". Per potential motion track: revoking observation (instantaneous or short / long window, `selective.revoke_q`
  < `motion.q_move`), static observation (the short-window bound or the long window `motion.window_long_s`), provisional
  static confirmation (unbroken run >= `confirm_s`, re-confirmed within `stale_s`, none for `revoke_hold_s` after a
  revocation), history-static (evidence history >= `history_s`, EMA revocation rate < `history_max_revoke`), convergence
  proxy (`converge_s` after the perception's motion onset; deterministic, no filter feedback). Gate (selective branch):
  roots = people (+ still if `motion.use_still`) and moving potentials; links only from active parents (roots and objects
  promoted from them, `gating.max_depth` hops), a co-motion gate (`selective.comotion_gate`: refused when the child's
  windowed velocity is about 0 but differs from the moving parent's), a provisional veto by confirmed static after
  convergence; unlinked objects: `prior_static_classes` and (after convergence) confirmed / history-static objects are
  unmasked, every other potential instance is `uncertain` (masked, status 255, not a parent unless `unknown_promotes`).
  Hysteresis: masked potential tracks stay `held` for `min_on_s`. The status `uncertain` is part of DYNAMIC_STATUSES.
  Node options: `segmenter.fast_masks` (YOLO copies only box crops of the native masks, bit-identical), `stats_compact`
  (no per-instance list in `/savior/stats`). Tracker and motion association are vectorised (bit-identical masks).
- **Tracker**: track-state machine (tentative, confirmed, lost, removed), IoU association, constant-velocity mask
  carry-over for up to `max_lost` frames; chain hysteresis uses the same state machine.
- **Extension**: depth-adaptive dilation (margin px about f*m/z, at least the KLT patch radius) + depth-band region growing
  inside the expanded bbox, written as layer 192.

### 3.6 Experiment runner and launch contract (savior_eval `savior-run` and the savior_bringup launch files)

- `ros2 launch savior_bringup <baseline|savior>.launch.py config:=<abs yaml> bag:=<abs bag dir> output:=<abs run_XX/stamped_traj_estimate.txt> [rate:=1.0] [k:=v ...]`
  Further arguments: `deterministic:=true` (default), `feature_stats:=auto` (writes run_XX/feature_stats.csv),
  `ov_set:="k=v ..."` (OpenVINS overrides); savior only: `pset:="k=v ..."` (savior_node overrides), `stats_file:=auto`
  (writes run_XX/savior_stats.jsonl). `savior-eval runstats --runs <method dir>` summarises mask sync, feature stats,
  timings and md5 per run.
- The launch plays the bag once, runs ov_msckf and `ov_eval pose_to_file`, and writes TUM poses exactly to `output`;
  when the bag player exits it waits a few seconds and then emits Shutdown, so `ros2 launch` returns by itself; SIGINT is
  handled cleanly.
- Runner layout: `results/<dataset>/<seq>/<method>/run_XX/{stamped_traj_estimate.txt, launch.log, run_info.yaml, config/}`,
  `runs_summary.yaml`, and `eval/` (from `savior-eval multi`) when ground truth is given.
- Evaluation: `savior-eval single|multi|compare` (rpg_trajectory_evaluation py3 port; RPE per sub-trajectory length in
  m/deg; only the normalised "Overall" (%, deg/m) aggregates across lengths).
