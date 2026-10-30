# P4 Report: method improvements (motion evidence, short-baseline gate, init policy, ego tracker, bug fixes)

Date: 2026-10-15. Method agent H. The coordinator saved this from H's final report; tables and figures are in `tables/` and `figures/`, and the recommended settings in `recommended_config.yaml`.

## Summary
- Every new feature is implemented and **off by default**, so P2 and P3a stay bit-reproducible.
- **Motion evidence keeps seated people and their chairs unmasked.**
  - The masked core area on OpenLORIS drops by 48–84 %.
  - Kept features rise: cafe1-2 goes from 37.0 to 39.3 per frame (openvins: 43.5).
  - It removes P2's loss on the most crowded sequence: cafe1-2 goes from −13 % (P2 full) to +2.5 % vs openvins.
- **ATE gain is not significant, consistent with P3a.**
  - On held-out OpenLORIS (8 sequences × 5 offsets), `full+mot+gate` is +1.8 % vs openvins (p = 0.22).
  - On uHumans2 the humans walk, so 0 % are classified as still and masks barely change. Results are far below P3a's minimum detectable effect.
- **The only significant result is a front-end change for every method, not SAVIOR itself.**
  - Lowering FAST from 30 to 15 improves openvins by +9.9 % [+4.7, +15.2] held-out (33 of 40 paired runs better, p < 0.001).
  - On that front-end, `full+mot+gate+fast15` vs `none+fast15` is +2.9 % (p = 0.031). That is only a hint once multiple comparisons are accounted for.

## Components

### 1. Motion evidence (`core/motion.py`, `motion.enable`)

**Ego-motion:**
- Integrate the gyro between frames.
- Track about 150 background KLT points, with depth from left→right KLT stereo.
- Run a robust Gauss-Newton fit of a small rotation correction (absorbs gyro bias and time offset) and of the translation. No accelerometer is used.
- Estimated speed vs GT has a median ratio of 0.99 on cafe1-1 and uHumans2.

**Instantaneous test:**
- Use up to 25 points per instance, from the mask eroded by 6 px.
- Fit a common 2-D residual by generalised least squares (GLS), with per-point covariance σ_bg²·I + (0.5·π)(0.5·π)ᵀ, where π is the parallax direction. The along-epipolar component is down-weighted because instances are depth mixtures.

**Windowed test (0.4–0.8 s), people only:** compare the instance anchor (mask centroid × depth) with the same anchor earlier, moved by the ego-motion chained over the window.

**Moving probability:**
- Log-odds update: +1.5 per moving observation, −0.25 per static observation.
- Priors: +1 for people, −1 for potential objects.
- Hysteresis thresholds: ±1.5.
- Duplicate detections share one decision (+17 % more still person-frames on cafe1-1).

**Decisions:**
- A static person gets the status `still`: unmasked, and not a promotion root.
- A moving potential object becomes a root without contact.
- A static potential object is never promoted.

### 2. Short-baseline gate
- `gating.max_noise_m` caps the noise term; 0.5 m is recommended.
- `gating.link_depth: contact` compares the median depth in a ring 3–9 px outside the other mask. Two instances are linked if |Δz_c| < 0.30 m + min(3σ, cap). A depth jump means an occlusion contact, and the link is refused.

### 3. Init policy (fork)
`dynamic_mask_init_policy`: normal (default), none, core or relax.

### 4. Tracker
`tracker.motion_model: ego` predicts carried masks with the ego-motion plus the track's own ego-compensated velocity. Tracks whose last status was `still` are never carried.

### Bug fixes (from P3a)
- **Threads:** new `num_threads` param (default 4) plus the `SAVIOR_NUM_THREADS` env var. Outputs are identical for 4 threads vs all cores.
- **Oracle backend:** it now matches only the role-table classes (`filter_classes`).
- **Right mask without depth:** new `compose.right_fallback` = none | median | band. With the median fallback, the leave-one-out right-mask overlap is 0.85–0.88 (it was 0 before).
- **Clean control:** new fork option `dynamic_mask_upstream_compat`. Frames without dynamic pixels run the exact upstream front-end, and `is_masked()` no longer treats out-of-bounds points as masked. With it, `none` is bit-identical to openvins on cafe1-1 (5/5 offsets, same md5) and agrees within ≤1.2e-5 m on uHumans2.
- **runstats:** `bag_images` is now offset-aware.

## Timing
Single-thread CPU, cafe1-1 with about 13 instances per frame, excluding segmentation.

| configuration | CPU ms/frame |
|---|--:|
| P2 full | 16.5 |
| + contact gate | +0.5 |
| + motion evidence | +2.7 (module alone ≈ 3.9) |
| + motion + gate + ego tracker | +4.1 |

Expect about 12–20 ms for the motion module on the Orin NX. A C++ port would roughly halve it.

## Results
ATE posyaw, paired over 5 offsets; positive = better.

### Held-out OpenLORIS (8 sequences, n = 40 pairs)

| method | vs openvins [95 % CI], p | vs full |
|---|---|--:|
| none | +1.1 % | |
| full | +0.8 % [−5.0, +6.3], p = 0.84 | |
| full+gate | +0.5 % | −0.4 % |
| full+mot | +2.7 % [−2.8, +8.0], p = 0.13 | +0.8 % |
| still-only | +2.7 % | +1.5 % [−0.4, +3.6] |
| full+mot+gate | +1.8 % [−3.8, +7.1], p = 0.22 | −0.2 % |
| openvins+fast15 | **+9.9 % [+4.7, +15.2], p < 0.001** | |
| full+mot+gate+fast15 | +11.7 % [+5.5, +17.7], p = 0.002 | |

### Per sequence
- **cafe1-2:** full −13.2 %; full+mot+gate +2.5 %.
- **office1-7:** full −1.9 %; full+mot +11.4 %; full+mot+gate +4.5 %.

### Tuning (cafe1-1)
All variants fall inside a ±8 % sensitivity band. The same configuration scored −5.1 / +3.8 / −6.9 % across code versions with nearly identical masks.

### Classification (offline)
- **Masked core area** drops on every sequence:

  | sequence | P2 full | P4 |
  |---|--:|--:|
  | cafe1-1 | 3.73 % | 1.93 % |
  | cafe1-2 | 3.49 % | 1.73 % |
  | office1-7 | 4.27 % | 1.33 % |
  | office1-6 | 1.04 % | 0.17 % |

- **Person area classified still:** 33–78 %.
- **Chair area:** chair promotions fall by 60–90 %, and the contact gate removes a further 10–20 %.

## What helps
- **Helps:** motion evidence (less over-masking, more features, no harm; fixes cafe1-2); the compat control and the thread cap; FAST 15 (for all methods).
- **Neutral:** contact gate and noise cap; right-mask fallback.
- **Does not help:** init policies; still-as-band; removing the extension band; the tracker in either motion model.

## Recommended configuration (`recommended_config.yaml`)
- **savior_node:** `motion.enable=true gating.link_depth=contact gating.max_noise_m=0.5 tracker.enable=false compose.right_fallback=median`.
- **OpenVINS:** `dynamic_mask_upstream_compat=true`. Make it the default from P5 on.
- **Front-end:** `fast_threshold=15` for the baseline and SAVIOR alike.

## Open problems
- **Radial motion:** the T265's 6.4 cm baseline cannot confirm people beyond about 4 m as static.
- **Slow static confirmation:** anchor drift is heavy-tailed, so confirming a person as static takes about 1 s, and the init window is still starved of features.
- **Cost:** the motion module needs a C++ port for the Orin.
- **Statistical power:** single sequences cannot resolve effects below about 10–25 %. A real benefit needs scenes where dynamic features are at least about 10 % of the update measurements.

Note: H's code changes are in `src/savior` but were built only in H's scratch directory. The workspace `install/` still holds the P2/P3a build and must be rebuilt before the next phase.
