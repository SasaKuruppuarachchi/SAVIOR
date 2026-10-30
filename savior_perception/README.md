# savior_perception

SAVIOR semantic front-end for OpenVINS (ROS 2 Humble, `ament_python`, GPL-3.0-or-later).
It turns a stereo pair into layered dynamic-object masks in RAW image coordinates. Depth
comes from stereo only.

```
raw left ──► segmenter ──► instances (mask, class, role)
                  │
raw L/R ──► ROI stereo depth (SGBM on rectified crops) ──► per-instance median depth + σ_z
                  │
                  ├─► motion evidence (P4, optional: gyro + KLT flow -> moving / static per instance)
                  ├─► promotion (BFS from dynamic roots, contact + noise-adaptive depth gate)
                  ├─► tracker (carry lost dynamic masks, chain hysteresis)
                  ├─► extension (depth-adaptive dilation + depth-band region growing → 192)
                  └─► compose  → /savior/mask/left (0/192/255), right mask by disparity warp
```

Interface contract: `docs/INTERFACE.md` §3.1, §3.3–3.5.

## Run

```bash
ros2 run savior_perception savior_node --ros-args \
  --params-file $(ros2 pkg prefix savior_perception)/share/savior_perception/config/default.yaml \
  -p calib_file:=/path/to/kalibr_imucam_chain.yaml \
  -p left_topic:=/cam0/image_raw -p right_topic:=/cam1/image_raw \
  -p segmenter.backend:=yolo -p segmenter.model:=/models/yolo26s-seg.engine
```

* `segmenter.backend`: `yolo` (ultralytics, `.pt` or TensorRT `.engine`), `oracle_uhumans2` /
  `oracle_colormap` (GT colour-coded semantic image on `seg_topic` + `segmenter.colormap_file`),
  `none` (no detections, all-zero masks).
* `calib_file`: the same `kalibr_imucam_chain.yaml` OpenVINS reads (pinhole-radtan or
  equidistant). Without it, stereo depth and the right mask are disabled.
* `roles_file`: class-role yaml (`dynamic` / `potential` / `static` / `default`, optional
  `half_extent_m`). Defaults to `config/roles_default.yaml`.
* All tunables, with their rationale, are listed in `config/default.yaml`.

Outputs: `/savior/mask/left`, `/savior/mask/right` (`mono8`, raw resolution,
`header.stamp` == left image stamp), `/savior/stats` (JSON: per-stage ms, counts,
interaction-tree links, per-instance depth/status), and `/savior/debug/overlay` (`bgr8`,
when `publish_debug:=true`).

## Ablations (all via parameters)

| run | parameters |
|---|---|
| full | defaults |
| cdo_off (classification off) | `gating.enable:=false` (every potential object is masked) |
| pp_off (post-processing off) | `extension.enable:=false tracker.enable:=false` |
| paper thresholds | `gating.mode:=fixed extension.band_mode:=fixed` (dist_int 2.0 m, dist_ext 0.5 m) |
| no stereo | `depth.enable:=false` (gating on 2D contact only, no right mask) |
| P4 motion evidence | `motion.enable:=true` (+ `imu_topic`, set by `savior.launch.py`) |
| P4 motion, (i) only | `motion.enable:=true motion.promote_moving:=false motion.veto_static:=false` |
| P4 short-baseline gate | `gating.link_depth:=contact gating.max_noise_m:=0.5` |
| P4 IMU-predicted tracker | `tracker.enable:=true tracker.motion_model:=ego` (needs `motion.enable`) |

## Motion evidence (P4, `core/motion.py`, off by default)

Decides per instance whether it actually moves, so static people (seated, standing) and their chairs keep
their features. Needs the gyro: `savior_node` subscribes to `imu_topic` (only when `motion.enable`) and holds
each frame until gyro samples cover its stamp (deterministic replay; released after `imu_wait_ms` only if the
IMU stream is silent).

1. Ego-motion: gyro rotation between the frame stamps (`R_c = R_CI^T R_I^T R_CI`) + a robust fit of a small
   rotation correction (prior `gyro_sigma_rad`) and the translation from ~150 background KLT points with
   left->right KLT stereo depth (no accelerometer). Gyro gap: rotation fitted to the background (`no_imu_sigma_rad`).
2. Instantaneous test: instance points (eroded mask, depth = median KLT stereo disparity of the instance) are
   tracked k-1 -> k; GLS fit of a common tangent-plane residual with per-point covariance
   `sigma_bg^2 I + depth_rel_sigma^2 pi pi^T` (pi = parallax direction): depth-robust (instances are depth
   mixtures), Mahalanobis `q` and speed `|c| r / dt`.
3. Windowed test (0.4-0.8 s): instance anchor (mask centroid x ROI-SGBM depth) vs. the chained ego-motion
   (static biases cancel); confirms "static", and flags radial (approaching) motion of people.
4. Moving probability per motion track (point-vote / IoU association): log-odds `+l_up` per moving obs,
   `-l_down` per static obs, hysteresis flags `is_moving` / `is_static`.
5. Decisions: static person -> `still` (not a promotion root, unmasked or `still_policy: band`), moving
   potential object -> root, static potential object -> never promoted.

Other P4 options: `num_threads` (default 4; OpenCV / torch; BLAS/OMP via env `SAVIOR_NUM_THREADS`, default 4 -- the
library defaults used all 48 cores per node), `compose.right_fallback` (`none` | `median` | `band`: right polygon for
instances without stereo depth), the oracle backend only matches the role-table classes (`segmenter.filter_classes`).

Stats: `/savior/stats` gains `motion` (ego fit, timings), `n_still`, per-instance `motion` (state, l, q, speed,
windowed velocities), `imu` (gyro coverage). `perception_offline.py` reads the gyro from the bag.

## Semantic chi² gate (SAVIOR-SG, off by default)

SAVIOR-SG uses the semantics online to set the OpenVINS outlier gate **per feature**, instead of one global
`up_*_chi2_multipler` that has to be tuned per dataset. It has two parts that are switched on together:

* **Perception:** `compose.movable_static_value:=64` writes one extra mask level. It marks a movable-class object
  (role `dynamic` / `potential`) that is currently classified static and therefore kept (status `unpromoted` or
  `still`). The level is written only into keep (0) pixels of both masks. Every 192 / 255 pixel stays exactly where it
  was, and 64 is below every rejection threshold (128, relaxed 224), so consumers that threshold the mask see the same
  binary masks. The default `0` leaves the masks bit-identical (0 / 192 / 255 only).
* **OpenVINS fork** (`estimator_config.yaml` or `ov_set`): the KLT tracker labels each feature, frame by frame, from
  the raw mask under it: 0 background, 1..127 movable-static, >= 128 band (255 core features are removed as before).
  The MSCKF and SLAM χ² tests then use the multiplier × a factor per label:

| key | default | meaning |
|---|---|---|
| `savior_semantic_gate` | `false` | enable labelling and the per-label gate |
| `savior_sg_mult_static` | `1.0` | factor for features on movable-static objects (64) |
| `savior_sg_mult_band` | `1.0` | factor for features on the extension band (192) |
| `savior_sg_keep_band` | `false` | keep band features under the band gate: the front-end rejects only the core (>= 224) |

Background features always use the stock gate (factor 1). A multi-observation MSCKF feature, and a SLAM feature at
its delayed initialization, use the tightest label seen over its track. A SLAM update uses the label of the current
observation. With `savior_semantic_gate: false` the fork is md5-identical to the build without this code. Note that the
frozen SAVIOR configuration has `extension.enable: false`, so it publishes no 192 band and `savior_sg_mult_band` /
`savior_sg_keep_band` have no effect there.

Non-semantic control: `savior_nis_gate: true` (`savior_nis_window`, default 200) scales the MSCKF / SLAM multiplier by
a robust innovation scale, λ = median over the last W χ² tests of χ² / χ²₀.₅(dof). This is the scalar
innovation-covariance scaling of innovation-based adaptive estimation (R. K. Mehra, "On the identification of variances
and adaptive Kalman filtering", IEEE TAC 15(2), 1970; A. H. Mohamed and K. P. Schwarz, "Adaptive Kalman filtering for
INS/GPS", J. Geodesy 73, 1999) with a median window estimate. λ = 1 until the window is full; it is clamped to
[0.05, 20]. Both gates print `[SAVIOR-GATE]` counters (tested / rejected per label class, λ) every 200 updates. The
t1 development study and its freeze are in `results/semantic_gate/`.

## Offline (no ROS graph)

`savior_bringup/tools/perception_offline.py` runs exactly the node's segmenter + pipeline on a ROS 2 bag
(deterministic, frame by frame) and writes the /savior/stats JSON lines plus left/right debug overlays
(`--overlay-every N`, `--overlay-stamps`, `--overlay-status carried|promoted|held`). Used for the P2 timing,
depth-config and figure work (results/p2/REPORT.md).

## Python API (no ROS needed)

```python
from savior_perception.core import SaviorPipeline, PipelineConfig, RoleTable, stereo_from_kalibr
rect = stereo_from_kalibr("kalibr_imucam_chain.yaml")
pipe = SaviorPipeline(PipelineConfig(), RoleTable.from_yaml("roles.yaml"), rect)
mask_left, mask_right, stats = pipe.process(left_raw, right_raw, stamp, instances)
# P4 motion evidence: stamp in seconds + gyro rotation R_{I_{k-1} I_k} (core.motion.GyroIntegrator.rotation)
mask_left, mask_right, stats = pipe.process(left_raw, right_raw, t_sec, instances, R_imu=R)
```

## Tests

```bash
cd src/savior/savior_perception
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test        # add -s to print the benchmark
```

The YOLO test runs only when `ultralytics` is installed and `SAVIOR_YOLO_MODEL` names a model file.

## OpenVINS integration requirements

* OpenVINS (SAVIOR fork) must run with **`downsample_cameras: false`**: its pyrDown of the mask would blur the
  192/255 layers.
* Masks are published RELIABLE / KEEP_LAST 10, one pair for every exact-time-synced stereo frame (all zeros
  when nothing is dynamic or processing fails), with `header.stamp` copied verbatim from the left image
  (both masks), size = raw camera size, `mono8`. Feed left and right images with identical stamps, otherwise the
  exact-time synchronizer never fires and no mask is produced for that frame.
* Layers: OpenVINS rejects `>= 128`, relaxes `128..223` when features run short, never relaxes `>= 224`
  (values `1..127`, i.e. the optional SAVIOR-SG level 64, are never rejected);
  SAVIOR writes core `255`, extension band `192`. Masks are never interpolated.
* If the node cannot keep up with bag playback, the reliable depth-10 input queue drops frames (no mask for
  those) – replay slower (`ros2 bag play -r 0.5`) for deterministic offline evaluation. P2: on OpenLORIS (848x800
  fisheye, 30 Hz) the node needs ~15-18 ms median / ~25 ms p90 alone but ~22 / 35 ms with 10 parallel runs, so
  rate 0.5 was used; `savior.launch.py` starts the bag only after `savior_node up` (TensorRT load + warmup).
* With `use_dynamic_mask: true` OpenVINS is not identical to upstream even for all-zero masks (tracked stereo
  features are checked against the static mask): use `backend:=none` as the control run.
