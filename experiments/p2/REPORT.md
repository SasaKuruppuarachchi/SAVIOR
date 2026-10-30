# P2 Report: first end-to-end SAVIOR runs (OpenLORIS T265 + uHumans2 00h check)

Date: 2026-10-15. Integration agent F; this report was saved by the coordinator from F's final report.

## Result

The integration works:
- Every OpenVINS image received its mask pair with the exact stamp, with **0 fallbacks**.
- **`n_in_core == 0`** held in every run.
- Repeated runs are **bit-identical** with the new `deterministic_processing` mode.

**SAVIOR does not improve OpenLORIS trajectories.** Mean translation ATE change against OpenVINS (positive = better):

| method | held-out mean | held-out median | cafe1-1 (tuning) |
|---|--:|--:|--:|
| savior_full | −0.3 % | −1.0 % | −0.7 % |
| naive_person | −2.7 % | | −5.0 % |
| savior_none (control: all-zero masks) | +4.0 % | | |
| savior_trk | +3.6 % | | |
| savior_pp_off | +7.4 % | | |
| savior_cdo_off | +8.4 % | | |

- Rotation ATE is within ±1.5 % for every method.
- On the held-out sequences with people (cafe1-2, office1-5/6/7): full −2.3 %, naive −0.1 %.
- The empty-mask control alone moves results by ±5–19 % per sequence. **No effect here is larger than the filter's own sensitivity.**
- On cafe1-2, the sequence with the most people, every masking method is worse than both openvins and the control.
- cdo_off's wins on office1-4/5/7 come from masking furniture. People appear in about 1 % of office1-4's frames, so these are not dynamic-object effects.

## A. Setup
- **Runs:** each method gets 3 runs, with bag start offsets of 0.0 / 0.2 / 0.4 s. Repeats are bit-identical in deterministic mode (verified for all 7 methods on cafe1-1), so plain repeats tell us nothing.
  - On office1-6/7 the static start absorbs the offset, which gives a spread of ±0.000.
- **Common settings:** bag rate 0.5, policy `wait`, timeout 1500 ms, `deterministic:=true`.
- **Methods:**
  - `openvins`: fork with masks off. It is bit-identical to stock OpenVINS (cafe1-1 md5 d624ff48).
  - `savior_full`: YOLO26s-seg plus the full pipeline.
  - `savior_cdo_off`: `gating.enable=false`.
  - `savior_pp_off`: extension off (the tracker is already off in full).
  - `naive_person`: person-only roles, no extension, no tracker. Depth is used only for the right-mask warp.
  - `savior_trk`: full pipeline with the tracker on.
  - `savior_none`: `backend:=none` control.
- **Layout:**
  - runs in `results/p2/<dataset_seq>/<method>/run_0{1,2,3}`;
  - compare tables (markdown and LaTeX) in `results/p2/compare/{openloris,uhumans2,uhumans2_preview}/`;
  - per-run evidence in `run_XX/runstats.yaml` and `compare/evidence.md`.

## B. Results
Values are ATE translation in m (mean ± std over 3 runs) / rotation in deg.

| sequence | openvins | naive_person | savior_none | cdo_off | pp_off | trk | full |
|:--|--:|--:|--:|--:|--:|--:|--:|
| cafe1-1 (tuning) | 0.164±0.002 / 2.18 | 0.172±0.002 / 2.23 | 0.164±0.002 / 2.11 | 0.169±0.007 / 1.91 | 0.187±0.004 / 2.14 | 0.178±0.018 / 2.00 | 0.165±0.010 / 2.01 |
| cafe1-2 | 0.154±0.009 / 1.91 | 0.155±0.004 / 1.88 | 0.145±0.014 / 1.89 | 0.163±0.002 / 1.92 | 0.162±0.015 / 1.90 | 0.164±0.017 / 1.97 | 0.178±0.011 / 1.95 |
| office1-1 | 0.018±0.003 / 2.36 | 0.018±0.000 / 2.42 | 0.017±0.003 / 2.34 | 0.017±0.001 / 2.33 | 0.014±0.002 / 2.34 | 0.016±0.002 / 2.42 | 0.015±0.001 / 2.36 |
| office1-2 | 0.028±0.009 / 2.47 | 0.025±0.006 / 2.46 | 0.025±0.006 / 2.46 | 0.030±0.004 / 2.40 | 0.025±0.006 / 2.46 | 0.028±0.002 / 2.47 | 0.028±0.002 / 2.47 |
| office1-3 | 0.008±0.001 / 1.79 | 0.009±0.001 / 1.83 | 0.009±0.001 / 1.83 | 0.011±0.001 / 2.33 | 0.009±0.001 / 1.83 | 0.009±0.001 / 1.83 | 0.009±0.001 / 1.83 |
| office1-4 | 0.029±0.002 / 1.94 | 0.035±0.005 / 1.96 | 0.031±0.005 / 1.93 | 0.017±0.003 / 1.87 | 0.032±0.004 / 1.97 | 0.028±0.003 / 1.95 | 0.028±0.003 / 1.92 |
| office1-5 | 0.061±0.017 / 2.57 | 0.054±0.017 / 2.55 | 0.049±0.007 / 2.57 | 0.038±0.008 / 2.20 | 0.052±0.011 / 2.56 | 0.061±0.010 / 2.61 | 0.052±0.004 / 2.50 |
| office1-6 | 0.029 / 2.15 | 0.032 / 2.26 | 0.027 / 2.17 | 0.029 / 2.02 | 0.029 / 2.25 | 0.031 / 2.11 | 0.030 / 2.11 |
| office1-7 | 0.041 / 2.27 | 0.041 / 2.27 | 0.040 / 2.27 | 0.028 / 2.00 | 0.025 / 2.39 | 0.023 / 2.37 | 0.044 / 2.35 |
| uHumans2 00h (0 humans) | 0.294±0.089 / 0.98 | – | – | – | – | – | 0.289±0.070 / 0.91 |
| RPE@10 % cafe1-1 / cafe1-2 [m] | 0.169 / 0.183 | 0.173 / 0.190 | 0.172 / 0.181 | 0.177 / 0.200 | 0.180 / 0.194 | 0.177 / 0.199 | 0.169 / 0.201 |

- **uHumans2 00h: no degradation.**
  - YOLO false positives occur in 0.45 % of frames, the core mask covers 0.001 % of pixels, and only 27 features were rejected.
  - RPE@10 % is 0.151 (openvins) vs 0.144 m (savior).
  - OpenVINS alone spans 0.206–0.415 m across the start offsets.
- **Office:** RPE@10 % is identical within about 0.003 m across all methods.

**uHumans2 preview** (YOLO backend, 3 runs, ATE m / deg; `compare/uhumans2_preview/`):

| sequence | openvins | naive_person | savior_full |
|---|--:|--:|--:|
| 06h | 0.338±0.021 / 1.17 | 0.360±0.131 / 1.12 | 0.292±0.045 / 1.04 |
| 12h | 0.307±0.041 / 1.08 | 0.394±0.090 / 1.65 | 0.381±0.067 / 1.29 |

- People are detected in 42 % (06h) and 61 % (12h) of frames, and the core mask covers 0.6–1 % of the image.
- Full is better on 06h and worse on 12h, both within the large spread.

## C. Evidence

### Mask sync
- Every run has exact == cam_masks, with fallback_latest, fallback_empty and late all 0.
- Total exact masks per method over 3 runs: cafe1-1 10228, cafe1-2 16168, uHumans2 00h 49828.
- Average hold time is about 20 ms (max about 170 ms).

### Features
Kept features per frame, cam0, openvins → full:

| sequence | openvins | full | note |
|---|--:|--:|---|
| cafe1-1 | 45.5 | 36.7 | relaxed on 438 of 3418 camera-frames |
| cafe1-2 | 43.5 | 37.1 | |
| office1-7 | 35.0 | 31.5 | |
| office1-1..6 | – | – | unchanged |

Masked area (full, core / band): cafe1-1 3.7 % / 5.2 %, office1-7 4.3 % / 3.9 %.

Observe-only runs (threshold 256, `results/p2/extra/`) give the share of baseline features that fall on SAVIOR masks:

| sequence | core | band |
|---|--:|--:|
| cafe1-1 | 9.3 % | 9.2 % |
| cafe1-2 | 9.8 % | 7.9 % |
| office1-7 | 10.0 % | 7.9 % |
| office1-5 | 0.9 % | 0.6 % |

### Timing
Quiet machine, offline tool, cafe1-1, 848×800; median / p90 in ms.

| stage | yolo26n-seg 640 | yolo26s-seg 640 |
|---|--:|--:|
| segment | 3.6 / 4.1 | 4.2 / 4.8 |
| ROI stereo depth (downsample 2) | 9.6 / 18.5 | 10.9 / 19.2 |
| gating | 0.26 / 0.42 | 0.34 / 0.53 |
| extension | 0.6 / 1.3 | 0.8 / 1.5 |
| compose (incl. right warp) | 1.1 / 2.0 | 1.6 / 2.6 |
| pipeline total excl. segment | 11.6 / 21.7 | 13.7 / 23.3 |
| segment + pipeline | ≈15 / 26 | ≈18 / 28 |

- The tracker, when on, costs 0.3 / 0.6 ms.
- During the experiments 10 runs ran in parallel. The node total was then 21.8 / 34.8 ms for full and 8.8 / 18.9 ms for naive, which is why the bags were played at rate 0.5.
- Depth at full resolution (downsample 1) takes 41 / 73 ms.

### YOLO on raw fisheye
171 frames from cafe1-1. Pseudo ground truth: yolo26x@1280 on the raw image plus two wide pinhole views. Data: `results/p2/yolo_fisheye_study_cafe1-1.json`.

| variant | recall | person-pixel coverage | ms |
|---|--:|--:|--:|
| n 640 raw | 0.48 | 0.73 | 3.5 |
| s 640 raw | 0.75 | 0.89 | 3.5 |
| n 960 raw | 0.69 | 0.81 | 3.9 |
| s 960 raw | 0.88 | 0.92 | 4.5 |
| n 640 pinhole f×0.5 → raw | 0.16 | 0.41 | 6.7 |
| s 640 pinhole f×0.5 → raw | 0.31 | 0.59 | 9.4 |

- Most misses are small, distant people near the image centre.
- Segmenting a rectified view was clearly worse and was rejected.
- **Chosen: s640.** s960 has about 2.25× the pixels for +3 points of coverage, which is likely over the Jetson budget.

## D. Bugs found and fixed

1. **`segmenters/yolo.py`:** `half` was passed on every predict call, causing a deprecation warning each frame. It is now passed only when requested. Test added.
2. **`node.py`:** segmenter warm-up (~0.7 s) ran in the first image callback, overflowing the input queue so the first frames got no mask. Warm-up now happens in the constructor. Test added.
3. **`core/compose.py`:** the right-mask warp dropped contour points that fell outside the capped rectified frame. For near people at the fisheye periphery the right mask turned into chords; synthetic IoU went from 0.63 to above 0.85 after the fix, which uses an analytic rect-right → cam1 projection. Test added.
4. **Fork, static + dynamic masks:** the two masks were max-combined before thresholding. Three consequences:
   - relaxation unmasked the static mask's edges;
   - observe-only mode dropped the static mask;
   - static pixels were counted as core.

   Now `CameraData::masks_dynamic` is separate, and gating uses max(static > 127, dynamic ≥ thr).
5. **Fork, `perform_detection_*`:** `n_in_core > 0` occurred because grider sub-pixel refinement ran after the mask test, and the right KLT match of a new stereo detection was not mask-checked. Both are now re-checked when gating is on. All gated methods were rerun after this fix.
6. **Fork, non-determinism (stock behaviour):** detached processing and init threads, with the initializer pruning against the newest IMU sample. The new opt-in `deterministic_processing`:
   - uses a synchronous subscriber;
   - clips the initializer to IMU data up to the image time;
   - removes the wall-time limit on the dynamic-init MLE;
   - uses lossless QoS.

   It reproduces the unloaded stock md5 exactly and stays bit-identical under heavy CPU load.
7. **Bringup launch files:** a fixed `start_delay` raced savior_node start-up, leaving up to 20 frames without masks. The bag now starts after savior_node logs `savior_node up`. New launch args: `deterministic` (default true), `feature_stats`, `ov_set`, `pset`, `stats_file`.
8. **New tools:**
   - `savior_bringup/tools/stats_recorder.py`
   - `savior_bringup/tools/perception_offline.py`
   - `savior-eval runstats`

   New options (default off): `gating.max_threshold_m`, `dynamic_mask_after_init`. `/savior/stats` now includes `image_size`.

Tests after the fixes: perception 71 passed / 2 skipped (the YOLO engine test also passes with a model set); eval 42 passed.

Note: in the current image cafe1-2 gives 0.154 m, against 0.166 m in P1, which was built in an older image. cafe1-1 reproduces (0.164–0.165 m).

## E. Final parameters (tuned on cafe1-1 only; see `tuning/TUNING_LOG.md`)

savior_node (`config/openloris_t265/savior_perception.yaml`):
- `yolo26s-seg.engine` (TRT FP16, 640).
- `depth.downsample` 1 → 2 (41 → 10 ms, with the same promotion decisions); `rect_focal_scale` 0.7.
- `tracker.enable` false. With constant pixel velocity, carried masks lag under ego-rotation: every tracker-on variant gave 0.183–0.199 m vs 0.160–0.164 m with it off. This choice is fragile, since on held-out data trk was +3.6 % vs full −0.3 %.

OpenVINS:
- `dynamic_mask_min_features` 60 → 30. At 60, relaxation fired on 1706 of 1709 frames, because the baseline keeps only about 45 features per camera.
- `deterministic_processing` true.

Tried and not adopted:
- gating cap of 1.0 / 1.5 m (0.179 / 0.169 vs 0.155 m);
- masking only after initialization (0.168 vs 0.155 m).

The two late bug fixes moved cafe1-1 full from 0.160 m (tuned) to 0.165 ± 0.010 m, which is itself a measure of the sensitivity.

## F. Figures (`results/p2/figures/`)
- Raw-fisheye mask alignment (left and right).
- Right-warp fix, before and after.
- People at the fisheye border.
- Walker with a promoted backpack and promoted chairs.
- **Over-promotion failure:** an empty chair promoted through a chain from a person 6.4 m away. With the T265's 6.4 cm baseline, σ_z(6.4 m) ≈ 3.2 m, so the adaptive gate degenerates to 2D contact.
- YOLO n vs s vs x@1280.
- Error, feature and mask timelines for cafe1-1 and cafe1-2.

## G. Why SAVIOR doesn't win here
1. **Little to gain.** About 10 % of baseline features lie on masked objects, and these are mostly seated people and their chairs. Walking people produce short tracks that the MSCKF chi² test already rejects. RPE is identical across methods; T265 scale/drift and the GT tilt bias dominate the error.
2. **Feature starvation.** About 45 of the 75 target features survive per camera, and masking removes a further 15–20 %. Initialization is hit hardest: on cafe1-2, masked methods initialize on about 10 features per camera instead of 23, start at 0.4 m error instead of 0.27 m, and never recover.
3. **Over-masking.** 52–65 % of chairs get promoted because the depth gate blows up with the short baseline, and the extension band adds about 5 % of the image.
4. **Latency is not the issue offline** (0 fallbacks). Online at 30 Hz, the p90 of 26–35 ms is borderline.
5. **Evaluation sensitivity.** The deterministic filter shifts ±10–20 % when the start moves by 0.2 s, which is too coarse to resolve few-percent effects on 9 short sequences.

## H. Recommended next steps
- **Motion evidence before masking:** an IMU-rotation-compensated flow residual or a per-track 3D velocity, so that seated people stay usable. The `MotionEvidence` hook is ready.
- **Promotion gate for short baselines:**
  - cap the noise term;
  - use boundary-depth contact rather than median vs median;
  - reject occlusion contacts.
- **Initialization:** relax or skip masks during init. Evaluate on uHumans2 06h/12h with the oracle backend.
- **Tracker:** if kept, predict carried masks with the IMU rotation.
- **Evaluation protocol:** keep `deterministic:=true`, always report the empty-mask control, and use more perturbations and sequences.
- **Jetson:** check s640 vs s960 against the time budget.
- **Front-end budget:** a lower FAST threshold or a finer grid would make masking cost less.

Operational note: experiments ran in isolated containers (`results/p2/scripts/drun.sh`, `--network none --ipc private`), because `exec.sh` uses host networking and another ROS container is running on the host. CycloneDDS needs `ROS_DOMAIN_ID` ≤ 232.
