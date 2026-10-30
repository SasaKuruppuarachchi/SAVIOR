# P6 Report: SAVIOR-Warehouse benchmark

Date: 2026-10-16. Benchmark agent L; report saved by the coordinator.
- Detailed outputs: `tables/`, `figures/`, `scripts/`, `methods.yaml`.
- Offline perception evaluation: `offline*/`.

## Verdict
1. **Masking is decisive at L2/L3.**
   - It is the only thing that prevents the hall L3 failure: openvins fails 10/10 there.
   - Combined over warehouse + VIODE (20 sequences), the gain tracks the dynamic share with rho 0.70–0.78.
2. **Selective masking beats naive class masking when the masks are perfect, provided they carry SAVIOR's depth band.**
   - L2+L3: −51 % [−67, −31], Holm p = 0.015.
   - L0: −40 %.
   - Why: static movable objects (parked forklifts, pallets, boxes) carry 17–44 % of MSCKF-used measurements and have low chi² rejection. Naive masking throws them away, which costs +40–68 % ATE at L0.
3. **With the fine-tuned YOLO, the current selective pipelines lose to YOLO naive masking at L2/L3.**
   - Share of the ceiling's log-gain: YOLO naive 88 % (0/80 failures), P2 68 %, P4 29 % (9/10 failures on hall L3).
   - The cause is classification errors, not lost features:
     - P4's motion evidence vetoes co-moving or leading forklifts, whose motion lies along the epipolar line;
     - the motion state lags when objects start moving, which coincides with filter initialization;
     - promotion masks flicker (3–20 % of frames).

## Protocol
- **Bags:** `data/warehouse/ros2_stereoseg/<seq>`. These add the right-camera segmentation; every original topic is byte-identical.
- **Offsets:** 10 per method per sequence, 0.0–1.8 s, all inside the 3 s hover. Every run used static init (3.60–4.05 s), so no adaptation was needed.
- **Settings:** `deterministic:=true`, `dynamic_mask_upstream_compat=true`, wait policy. Rate 0.5; heavy aisles runs were rerun at 0.25 / 0.2 after mask fallbacks, and the originals kept in scratch.
- **Runs:** 1080 benchmark runs (13 methods × 8 sequences × 10 offsets, plus 40 control runs) and 64 diagnostic runs.
- **Sync:** 0 fallbacks and n_in_core = 0 in every final masked run.
- **Controls:** savior_none is md5-identical to openvins.
- **Failure criterion:** ATE > 2 m (about 2 % of the 89–96 m path). A 1 m threshold is also reported.
- **Post-hoc variant:** `yolo_p6` (P4 + `window_unveto_potential` + `gating.max_depth=2`) was selected on offline classification of these same sequences, so it is **not a held-out result**.

## Median ATE [m] over 10 offsets ([n] = failures > 2 m)

| seq | OV | orc_mov | orc_mov_warp | orc_mov_ext | orc_naive | y_naive | y_p2 | y_p4 | y_p4_noint | y_p4_noext | coco_p4 | y_p6 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| aisles L0 | 0.066 | 0.066 | 0.066 | 0.066 | 0.145 | 0.101 | 0.111 | 0.123 | 0.097 | 0.096 | 0.092 | 0.105 |
| aisles L1 | 0.102 | 0.086 | 0.105 | 0.106 | 0.121 | 0.100 | 0.191 | 0.152 | 0.094 | 0.128 | 0.097 | 0.101 |
| aisles L2 | 0.198 | 0.081[1] | 0.088 | 0.065 | 0.079[1] | 0.069 | 0.167 | 0.147 | 0.116 | 0.110[1] | 0.105 | 0.189 |
| aisles L3 | 0.156[1] | 0.140 | 0.141 | 0.119 | 0.113 | 0.118 | 0.081 | 0.097 | 0.114 | 0.126 | 0.102 | 0.141 |
| hall L0 | 0.136 | 0.136 | 0.136 | 0.136 | 0.237 | 0.216 | 0.129 | 0.129 | 0.123 | 0.137 | 0.136 | 0.182 |
| hall L1 | 0.103 | 0.168 | 0.159 | 0.132 | 0.239 | 0.208 | 0.214 | 0.203 | 0.212 | 0.178 | 0.170 | 0.195 |
| hall L2 | 0.254[1] | 0.200 | 0.249 | 0.229 | 0.200 | 0.209 | 0.348 | 0.220 | 0.195 | 0.408 | 0.295 | 0.285 |
| hall L3 | 2030[10] | 0.78[1] | 0.252 | 0.217 | 1.23[2] | 0.382 | 0.592 | 41[9] | 225[8] | 12[10] | 910[10] | 3990[6] |

- **Failures out of 80 runs:**

  | method | failures |
  |---|--:|
  | openvins | 12 |
  | oracle_moving | 2 |
  | oracle_class_naive | 3 |
  | yolo_naive | 0 |
  | yolo_p2 | 0 |
  | yolo_p4 | 9 |
  | yolo_p4_nointer | 8 |
  | yolo_p4_noext | 11 |
  | coco_p4 | 10 |
  | yolo_p6 | 6 |
  | oracle_moving_warp | 0 |
  | oracle_moving_ext | 0 |

- **Hall L1:** every masking method is worse than openvins, the oracle included (+60 %). The nocompat control rules out the code path, so this is read as filter sensitivity.

## Pooled paired statistics vs openvins
Geometric-mean ATE ratio − 1 with a bootstrap 95 % CI; Holm correction within the level family.

| method | L0 | L1 | L2 | L3 | L2+L3 [95 % CI] | Holm p | L2+L3 RPE |
|---|---|---|---|---|---|--:|--:|
| oracle_moving_ext | 0 | +0.5 % | −50 % | −89 % | **−77 % [−86, −62]** | <1e-4 | −71 % |
| oracle_moving_warp | 0 | +7 % | −39 % | −87 % | −72 % [−83, −55] | 2e-4 | −72 % |
| oracle_moving (GT right mask) | 0 | +7 % | −33 % | −77 % | −61 % [−75, −38] | 8e-4 | −61 % |
| oracle_class_naive | **+68 %** | +37 % | −29 % | −68 % | −52 % [−69, −26] | .002 | −35 % |
| yolo_naive | +40 % | +17 % | −49 % | −85 % | −72 % [−82, −57] | <1e-4 | −63 % |
| yolo_p2 | +27 % | +67 % | −9 % | −85 % | −63 % [−76, −43] | .002 | −68 % |
| yolo_p4 | +32 % | +46 % | −22 % | −45 % | −34 % [−54, −12] | .019 | −37 % |
| yolo_p4_nointer | +14 % | +20 % | −38 % | −51 % | −45 % [−62, −23] | .003 | −41 % |
| yolo_p4_noext | +20 % | +24 % | −1 % | −24 % | −14 % n.s. | .54 | −16 % |
| coco_person_p4 | +12 % | +16 % | −28 % | −38 % | −33 % [−53, −11] | .048 | −32 % |
| yolo_p6 (post-hoc) | +25 % | +21 % | −10 % | −52 % | −34 % [−56, −6] | .53 | −48 % |

**Head-to-head comparisons (L2+L3):**

| comparison | effect | p |
|---|---|---|
| oracle_moving_ext vs oracle_class_naive | **−51 %** | Holm .015 |
| oracle_moving_ext vs oracle_moving (exact) | −41 % | 5e-4 |
| yolo_naive vs oracle_class_naive | −41 % | .022 |
| yolo_naive vs ceiling | +20 % | .025 |
| yolo_p2 vs yolo_naive | +33 % | .006 |
| yolo_p4 vs yolo_naive | +135 % | Holm .004 |
| yolo_p4 vs yolo_p2 | +77 % (converged-only +1 %) | — |
| yolo_p4_noext vs yolo_p4 | +32 % | .037 |

- Mask-boundary features matter: the depth band improves perfect masks by 41 %, and removing the band from P4 costs 32 %.
- At L1/L2, P4 beats P2: −12 % / −15 %.

## Feature budget
- **Kept features at L3:** naive masking −33 to −40 %; yolo_p4 −17 to −20 %; oracle_moving −12 to −19 %. At L0 the selective variants lose 0 %.
- **Static movable objects:** they hold 23.5–26 % of kept features (aisles) and 11–14 % (hall), and carry **38–44 % / 17–28 % of MSCKF-used measurements**.
  - Their chi² rejection is lower than other background (0.09–0.22 vs 0.19–0.37).
  - Their tracks are as long as background tracks.
  - Naive masking cuts their used share to about 1–4 %.

## Classification vs GT moving flags (offline, pooled L1–L3)

| variant | moving recall | static kept | moving-forklift recall | load on moving forklift masked | load on parked forklift kept |
|---|--:|--:|--:|--:|--:|
| yolo_naive | 0.97 | 0.02 | — | 0.92 | 0.02 |
| yolo_p2 | 0.87 | 0.76 | 0.86 | 0.69 | 0.43 |
| yolo_p4 | 0.75 | 0.78 | 0.46 | 0.69 | 0.45 |
| yolo_p4_nointer | 0.58 | 0.96 | 0.26 | 0.27 | 0.98 |
| yolo_p6 | 0.89 | 0.87 | 0.88 | 0.73 | 0.63 |
| coco_person_p4 | 0.34 | 0.97 | — | 0.00 | 1.00 |

- **Static people stay masked** 91–95 % of the time: the still test rarely confirms standing people from a drone moving at 1 m/s.
- **Root cause of the P4 forklift misses:** the lead forklift 3.7 m ahead is confirmed "static" during the hover. Afterwards the instantaneous test is blind to its along-epipolar motion, and the windowed "moving" result is disabled for potential objects, so the veto sticks for 1837 frames.
- **P6** fixes the veto (forklift recall 0.26 → 0.95 on hall L3) but still diverges, because the lead forklift stays unmasked from 3.0 to 4.25 s, just after init.
- **Flicker** (share of frames with > 30 % core-area jumps): naive 0.3–0.9 %; nointer 1.6–2.9 %; P2 / P4 / P6 3–20 %.
- **Fine-tuned vs COCO person** (sim): IoU 0.877 vs 0.817. COCO cannot detect forklifts, so it fails hall L3 10/10.

## Share vs gain
- **Warehouse** (n = 8): rho 0.93 (pixel share), 0.86 (kept share), 0.83 (MSCKF-used share). On hall L3, 30 % of MSCKF-used and 52 % of SLAM-update measurements are on movers.
- **Combined with VIODE** (n = 20, identical definitions): rho 0.78 / 0.75 / 0.70 (p ≤ 6e-4).

## Timing
GPU 93–95 % busy with other users' jobs, about 22 parallel runs.
- **Node total, median (p90):** naive 49 (79), P2 52 (85), P4 60 (112), COCO 36 (51) ms.
- **Segment step:** 39–41 ms, with about 65 instances per frame (up to 300 in the aisles).
- **This is over the 50 ms budget at p90.**

## Code changes
All default off or backward compatible; 99 perception tests pass.
- `gating.promote_contact`
- `gating.max_depth`
- `motion.window_unveto_potential`
- `to_ros2.py --seg-right`
- `roles/warehouse_naive.yaml`

## Open issues
1. Motion evidence must handle leading and co-moving objects and the static→moving onset at init. Options: provisional vetoes, conservative masking until the filter has converged, a windowed test for large instances.
2. Contact promotion flickers. Re-evaluate temporal smoothing (tracker / chain hysteresis).
3. Static people are almost never confirmed still from a moving drone.
4. Apply a boundary band to oracle and naive masks too.
5. yolo_p6 was tuned on these sequences. **Held-out warehouse trajectories are needed** for an honest evaluation.
6. The node is over the frame budget under load.
7. Bug: the fork's wait policy releases images after about 6.4 s (pending buffer of 64 frames) regardless of the timeout.
8. The results folder is 26 GB (`savior_stats.jsonl`, about 27 MB per YOLO run).
9. Forklift wheels don't turn (sim realism).
