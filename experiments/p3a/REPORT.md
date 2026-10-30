# P3a Report: ceiling of oracle human masking on uHumans2 (office 0/6/12 humans)

Date: 2026-10-15. Experiment agent G. The coordinator saved this from G's final report. Tables are in `tables/` and figures in `figures/`.

## Verdict
**Perfect (oracle) human masks do not measurably help OpenVINS on uHumans2.** Every masking effect is smaller than the filter's own run-to-run sensitivity.
- Pooled 06h+12h, oracle_person vs the empty-mask control:
  - ATE −0.7 % (95 % CI −29 % … +24 %, Wilcoxon p = 0.60);
  - RPE@26 m +2.5 %, which rules out an RPE gain above about 4 %.
- The extension band does not help (−8.5 %, n.s.).
- Masking only after initialization does not help.
- Local error does not change where humans are in view (circular-shift p = 0.90 / 0.13).

## Setup
- 171 runs, all with status ok. Current install used as is, `deterministic:=true`, rate 0.5.
- Start offsets: 5 (0.0 to 0.8 s) for every method; 10 (up to 1.8 s) for the key methods on 06h/12h.
- Mask sync is perfect in all 145 masked runs: 0 fallbacks, 0 late, exact == 2 × images (2.57 M masks). `n_in_core = 0` in every gated run.
- **Right mask** comes from savior_node's stereo (SGBM) warp. The converted bags have no depth topic.
- A first wave of runs was discarded and re-run, after thread oversubscription caused 4 fallbacks (bug 1). Thread caps are set in `scripts/drun.sh`.
- Methods:

| method | segmenter | roles | extension | tracker | other |
|---|---|---|---|---|---|
| openvins | – (masks off) | – | – | – | – |
| savior_none | none (all-zero masks), control | – | – | – | – |
| oracle_person | oracle | person-only | off | off | – |
| oracle_person_ext | oracle | person-only | on | off | – |
| oracle_person_after_init | oracle | person-only | off | off | masks only after VIO init |
| yolo_full | YOLO26s-seg TRT | coco_indoor | on | off | min_features 30 (P2 final) |
| yolo_naive | YOLO26s-seg TRT | person-only | off | off | – |

## 1. ATE translation RMSE [m], posyaw (`tables/methods.*`)

| seq | method | n | mean | median | std |
|---|---|--:|--:|--:|--:|
| 00h | openvins | 5 | 0.395 | 0.261 | 0.286 |
| 00h | savior_none (= oracle on 00h) | 5 | 0.418 | 0.347 | 0.266 |
| 00h | yolo_full | 5 | 0.281 | 0.309 | 0.068 |
| 00h | yolo_naive | 5 | 0.345 | 0.380 | 0.105 |
| 06h | openvins | 10 | 0.276 | 0.300 | 0.087 |
| 06h | savior_none | 10 | 0.265 | 0.263 | 0.065 |
| 06h | oracle_person | 10 | 0.306 | 0.323 | 0.070 |
| 06h | oracle_person_ext | 10 | 0.313 | 0.301 | 0.098 |
| 06h | oracle_person_after_init | 10 | 0.369 | 0.371 | 0.097 |
| 06h | yolo_full | 5 | 0.325 | 0.296 | 0.083 |
| 06h | yolo_naive | 5 | 0.421 | 0.474 | 0.143 |
| 12h | openvins | 10 | 0.319 | 0.304 | 0.103 |
| 12h | savior_none | 10 | 0.473 | 0.379 | 0.243 |
| 12h | oracle_person | 10 | 0.427 | 0.401 | 0.134 |
| 12h | oracle_person_ext | 10 | 0.362 | 0.360 | 0.097 |
| 12h | oracle_person_after_init | 10 | 0.406 | 0.335 | 0.185 |
| 12h | yolo_full | 5 | 0.434 | 0.420 | 0.130 |
| 12h | yolo_naive | 5 | 0.403 | 0.419 | 0.117 |

- **Turning the mask machinery on with all-zero masks is not a no-op.** savior_none diverges from openvins at t = 30.957 s, when cam0 makes one fewer new detection. In one 12h run the two then end 3.7 m apart before alignment.
- The likely mechanism is bug 4: `is_masked()` returns true for out-of-bounds points.
- Alternative windows (t ≥ 46 s; and 46–480 s, which excludes a late drift event that appears in all sequences, 00h included) change no conclusion.

## 2. Paired statistics over offsets (`tables/paired_*`)
Method minus reference, ATE; negative = better.

| comparison | 06h | 12h | pooled (n = 20) |
|---|---|---|---|
| oracle_person − savior_none | +15 %, p = 0.084 | −10 %, p = 0.70 | −0.7 %, p = 0.60 |
| oracle_person_ext − savior_none | +18 %, p = 0.63 | −23 %, p = 0.32 | −8.5 %, p = 0.65 |
| oracle_after_init − savior_none | +39 %, p = 0.027 | −14 %, p = 0.49 | +7 %, p = 0.28 |
| savior_none − openvins | −4 %, p = 0.85 | +48 %, p = 0.23 | +24 %, p = 0.37 |
| oracle_person − openvins | +11 %, p = 0.32 | +34 %, p = 0.084 | +23 %, p = 0.030* |

\* This is the machinery perturbation, not an effect of masking: the control differs from openvins by just as much, and oracle vs control gives p = 0.60.

- **Sensitivity:** the openvins SD over offsets is 32–72 % of its mean. The minimum detectable effect at 80 % power with 10 offsets is about 25 % ATE on 06h and about 70 % on 12h.
- **yolo_naive:** pooled RPE is +15 % vs openvins (p = 0.010). It is nominally worse, but this does not survive correction across about 70 tests.

## 3. Density trend
- There is no monotonic gain from 00h to 06h to 12h.
- Humans do not hurt the baseline either: openvins scores 0.395 / 0.276 / 0.319 m.
- On 12h, the excess local RPE over 00h sits in windows with *no* humans in view.
- Confounds:
  - the camera frame count differs (8307 / 8522 / 9535 frames in 506 s);
  - 06h initializes at about 44 s for every method, against about 31 s for the others.

## 4. Where the human information goes (observe-only + diagnostic logging build; `tables/feature_fates.md`)

| | 06h | 12h |
|---|--:|--:|
| kept cam0 features on humans | 0.6 % | 1.0–1.2 % |
| frames with ≥ 1 human feature | 21 % | 35–40 % |
| median track length, human vs other [frames] | 3 vs 10 | 3 vs 11 |
| human-track fate: used / chi²-rejected / triangulation failed / < 2 measurements | ≈ 10 / 28 / 38 / 20 % | ≈ 9 / 27 / 40 / 21 % |
| MSCKF chi² reject rate, human vs other | 69–77 % vs 35 % | 72–78 % vs 38 % |
| share of MSCKF-used measurements on humans | 0.3–0.4 % | 0.5–0.8 % |
| share of SLAM-update measurements on humans | ≤ 0.02 % | ≤ 0.11 % |

- Even in frames with more than 5 % human coverage (1.5 % / 4.1 % of frames), only 3–5 % of features are on humans.
- Masking does not cost features here: 61.8 vs 62.0 kept per frame, and 27.2 vs 27.2 before init.
- The diagnostic build is logging-only (`scripts/diag_logging.patch`), and its trajectories match the install to within 3e-6 m.

## 5. YOLO vs oracle masks (`tables/mask_quality.*`)
- Person pixel recall / precision is 0.95 / 0.84 on 06h and 0.96 / 0.86 on 12h.
- Per-frame IoU: median 0.72.
- Instances of 300 px or more have recall ≥ 0.91, and those of 1000 px or more ≥ 0.98. Recall on tiny instances (under 100 px) is only 0.17–0.20.
- yolo_full's total masked area is 2.4–3.1× the oracle's, because of extension and other classes.
- False positives on 00h: 0.45 % of frames.

## Why masking doesn't matter here
1. **Too little dynamic information reaches the filter.** Humans cover 0.4–0.8 % of the image on average and carry under 1 % of the measurements the MSCKF uses.
2. **The back-end already filters what does arrive.** Human tracks are short, and about 90 % never contribute: they fail chi², fail triangulation, or have too few measurements.
3. **Neither initialization nor feature starvation is the issue.**
4. **What remains is chaotic filter sensitivity.** A 0.2 s start shift, or one fewer detection, moves ATE by 30–70 %.

## What scene properties masking would need to matter
- Dynamic features need to make up roughly **≥ 10 % of the update measurements**. That means sustained dynamic coverage of about **10–30 % of the image** for seconds at a time.
- The dynamic tracks need to be long and coherent enough to survive chi² and triangulation. Large or near objects moving slowly qualify, as do vehicles, crowds and objects that move with the camera.
- Masking can also matter where the filter's gate is weak: feature-starved scenes, and dynamic content during static initialization or standstill.
- Any such test needs ≥ 10 perturbations plus the empty-mask control.

## Bugs found (not fixed by G; forwarded to the P4 agent)
1. **Thread oversubscription in savior_node.** Each node runs about 107 threads, because OpenCV/BLAS default to all cores. With 18 or more parallel runs the load average hits about 290, causing mask holds over 1.5 s and fallbacks. Fix: cap the threads in the node (`cv2.setNumThreads`, BLAS environment variables).
2. **The oracle backend runs connected components for all 20 classes,** even when the roles use only person.
3. **The right mask has no fallback for instances without stereo depth.** These are 9–16 % of person instances, and about a third of them touch the image border. As a result, right-core area is 87–95 % of the left.
4. **`TrackBase::is_masked()` treats out-of-bounds points as masked.** This is the probable reason savior_none differs from openvins.
5. Minor: `runstats` `bag_images` ignores the start offset. Use `images_received`.
