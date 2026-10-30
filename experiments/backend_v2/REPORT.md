# Back-end v2: OpenVINS re-freeze and t1 validation (warehouse t1 only)

Date: 2026-10-24, 18:20–23:40 EEST. Workstream A of the author decision of 2026-10-24. Agent report saved by the coordinator.
- **Data:** tuning split `*_t1_*` only. For VIODE, only image header stamps were read.
- **Unmodified:** src/savior, install/, frozen_edge/, ref/, the frozen yamls, and all perception, roles and pset files.

## 1. Re-freeze
- `backend_config.yaml` (md5 **10c2144bc45310d3eab3d87f7b9b638a**, read-only) was written before any v2 SAVIOR or YOLO result.
- It changes only `track_frequency` 21.0 → 10.5 and `max_clones` 11 → 15 (ov_diag trk10_clones15).
- Estimator yamls:
  - warehouse v2: 2abf884b5d4ea0ec1074c92e4fbd0952 (v1 b18ac563…); the frozen_edge copy is identical;
  - VIODE v2 (prepared, not run): edad4f259c9cac88e2334a16ec99a2f4 (v1 54b296c2…).
- Only the run scripts' CFG changes. Each v2 config directory holds the v2 estimator yaml plus md5-identical copies of the frozen kalibr and perception yamls, asserted at every launch.
- v2 OpenVINS ≡ ov_diag trk10_clones15 (md5).

## 2. VIODE
- Same 0.55 s window: 20 Hz cameras, track_frequency 21, max_clones 11.
- The drop rule keeps exactly 50 % of frames, spaced ~100 ms (`tables/stamp_spacing_viode.txt`).
- **Recommendation:** apply the identical rule, untuned.
- **Untested risks:** 10 Hz frames during dynamic init at late offsets; doubled KLT motion between frames.
- `BACKEND_VIODE=v1` keeps the frozen VIODE estimator.

## 3. Mask sync: valid
- Frames are dropped before `dynamic_mask_enqueue`, so the wait buffer holds only kept frames; dropped-frame masks are pruned.
- Over 800/800 runs: clean exit, 0 fallbacks, 0 late masks, n_in_core 0, pose-count rule passed. savior_none ≡ openvins (80/80 md5). SAVIOR-edge too_late 0.
- v1 SAVIOR-edge re-run with frozen_edge is md5-identical to the edge-study runs (80/80).
- **Perception waste:** 50 % of savior_node time goes to frames the filter drops (~2199 frames per run, 1100 used). Not changed; skipping them would need an opt-in flag and t1 validation (`tables/perception_waste.md`).

## 4–5. Results (paired geometric-mean ATE change; full tables in `tables/ate_t1.md`, `tables/rpe_t1.md`)

| comparison | back-end | L0+L1 | L2+L3 | hall L3 |
|---|---|---|---|---|
| SAVIOR vs Y-Cls | v2 | **−31.6 %** [−46, −19] H 8e-7 | **−30.5 %** [−38, −22] H 3e-6 | −57.9 % H .010 |
| | v1 | −14.1 % H .018 | −3.7 % n.s. | −63.9 % |
| SAVIOR-adaptive vs Y-Cls | v2 | −26.1 % | −30.1 % | −44.4 % |
| | v1 | −4.2 % | +32.3 % | −51.0 % |
| SAVIOR-edge vs SAVIOR | v2 | +0.5 % n.s. | +17.5 % [−3, +57] n.s. | **+31.3 %** H .010 |
| | v1 | +6.3 % | −0.3 % | +34.8 % |
| O-Dyn+B vs O-Cls+B | v2 | −32.3 % H 5e-9 | −44.7 % H 2e-11 | −57.3 % |
| | v1 | −24.4 % | −38.4 % | −68.4 % |
| O-Dyn vs O-Cls | v2 | −35.2 % | −26.9 % | −67.7 % |

**Each method vs OpenVINS under v2** (L0+L1 / L2+L3):

| method | change |
|---|---|
| SAVIOR | +5.7 % n.s. / −75.7 % |
| SAVIOR-adaptive | +14.1 % / −75.6 % |
| SAVIOR-edge | +6.2 % / −71.5 % |
| Y-Cls | +54.4 % / −65.1 % |
| O-Dyn+B | −5.7 % / −76.6 % |
| O-Cls+B | +39.3 % / −57.7 % |
| O-Dyn | −6.9 % / −72.9 % |
| O-Cls | +43.8 % / −62.9 % |

Hall L3: −96 to −99 % for every masking method.

**v2 vs v1, same method** (L0+L1 / L2+L3):

| method | change |
|---|---|
| OpenVINS | −29 % / −38 % |
| Y-Cls | −15 % / −22 % |
| SAVIOR | −32 % / −44 % |
| SAVIOR-adaptive | −34 % / −59 % |
| SAVIOR-edge | −36 % / −34 % |
| oracles | −26…−36 % / −30…−57 % |

**Change in relative gain:**
- SAVIOR vs Y-Cls becomes more favourable under v2: −24 % over all levels (H .0015), −28 % at L2+L3 (H .009).
- SAVIOR-adaptive vs Y-Cls: −47 % at L2+L3.

**Failures (> 2 m, out of 80), v2 / v1:**

| method | v2 | v1 |
|---|--:|--:|
| OpenVINS | 10 (8 on hall L3) | 12 |
| SAVIOR | 0 | 0 |
| SAVIOR-adaptive | 0 | 1 |
| SAVIOR-edge | 1 | 0 |
| Y-Cls | 1 | 0 |
| O-Dyn+B | 0 | 0 |
| O-Cls+B | 0 | 1 |
| O-Dyn | 1 | 2 |
| O-Cls | 0 | 3 |

**RPE agrees in direction.**

## Answer
- SAVIOR's relative gains survive the stronger back-end and grow on t1.
- SAVIOR ≈ OpenVINS on static scenes (+6 %, n.s.), while Y-Cls costs +54 % there.
- SAVIOR-edge would fail H5 on t1 under v2 (+17.5 % at L2+L3, +31 % on hall L3).
- **Caveats:** t1 is optimistic, because both the perception and the back-end were tuned on it; there are 2 trajectories per level.

## 6. Held-out script (prepared, not run)
- `scripts/heldout_v2.sh`, run as `CONFIRM_HELDOUT=yes … heldout_v2.sh all`.
- Scope: warehouse t2 + VIODE, 10 methods, 10 offsets. 2400 runs, about 13 h at 12 containers.
- Guarded by md5 checks; the dryrun resolves all 480 jobs.

## Files
- `backend_config.*`, `config/`, `scripts/`
- `runs/` (800 v2 runs) and `runs_v1/` (80 SAVIOR-edge v1 runs)
- `tables/`
- `figures/`: forest_effects_t1, forest_backend_t1, ate_success_t1
