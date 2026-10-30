# P7 Report: stages A–E (conservative-by-default classification)

Date: 2026-10-23, 02:00–08:40. Method agent N; report saved by the coordinator.
Tuning set: t1 only; held-out data untouched.
Detailed outputs: tables in `tables/`, figures in `figures/`. `final_config.yaml` is a DRAFT (not frozen).
Stages F (timing) and G (freeze and pre-register) are pending the author's go-ahead.

## Headline
- **No planned variant meets the bar on t1.** The bar: no worse than yolo_naive at L2/L3, better at L0/L1, 0 failures on hall L3.
- **Main variant so far: p7_nb** (P7 without the depth band).
- **The sensitivity sweep found one setting that meets the bar:** `sens_fix1`, a fixed interaction threshold dist_int = 1 m with the median-depth link. It was selected post hoc from 9 settings on the tuning set, so it is optimistic. The choice between the two is for the author.

## Validity
- 1640/1640 warehouse runs and 80/80 no-harm runs are sync-valid: 0 fallbacks, 0 late masks, n_in_core = 0.
- `dynamic_mask_max_pending=0` was active in every run.
- openvins ≡ savior_none ≡ P6 (md5) on the warehouse. yolo_naive matches P6.
- Re-run hall p7 equals the earlier b1 runs (md5 10/10).
- **On the no-harm sequences** (uHumans2 06h, OpenLORIS cafe1-1), the filter itself is not bit-deterministic. openvins vs openvins differs by micrometres, and one savior_none run differs from openvins by up to 0.23 m. This is not caused by the mask code.

## A: vs yolo_naive (geometric-mean ATE change; Holm within level group)

| variant | L0+L1 | L2+L3 | hall L3 | failures |
|---|---|---|---|---|
| p7 (band) | +14 % n.s. | +42 % [+23, +66], H < 1e-3 | +75 % | 0/80 |
| **p7_nb** | −4 % n.s. (L0 −15 %, p = .07) | +32 % [+2, +77], H .09 | **−51 %** | 1/80 |
| p7_ring | +2 % | +65 %, H < 1e-3 | – | 1/80 |
| yolo_naive_ring | +28 % | +90 %, H < 1e-3 | – | 1/80 |

- **ATE vs RPE:** p7_nb is better on RPE everywhere: L0+L1 −18 %, L2+L3 −8 % (34/6 wins, Holm < 1e-3), hall L3 −31 %. It is locally more accurate but drifts more at L2.
- **Remaining loss is at L2** (hall +54 %, aisles +90 %). The cause is classification: carried loads are masked 0.87 vs 0.95 for naive, and 34 % more moving pixels are missed. Relaxation churn is ruled out.
- **The depth band hurts with YOLO masks.**

## B: like-for-like oracle check

| comparison | L0 | L2+L3 | hall L3 |
|---|---|---|---|
| O-Dyn+B vs O-Cls+B | −25 % (H .033) | **−38 % [−51, −25]** (H < 1e-3) | −68 % |
| O-Cls+B vs O-Cls | −21 % (H < 1e-3) | −20 % n.s. | |
| O-Dyn vs O-Cls (no band) | −40 % | −17 % n.s. | |

- O-Cls+B has 1/80 failures.
- **For the paper:** restate "−51 %" as "−38 % like for like". The band helps perfect masks and hurts YOLO masks.

## C: ablations rebased on p7_nb (880 runs)

| ablation | L2+L3 vs main | hall L3 vs main | other |
|---|---|---|---|
| sticky (static decisions never expire) | +107 % | 10/10 failures, Holm .021 | the only clearly harmful component to remove |
| addband | +7 % | +256 % (Holm .021) | |
| noint | – | +72 % (Holm .035) | |
| nohold | −16 % n.s. | +50 % | L0+L1 −13 % (Holm .035) |
| noprior | −17 % n.s. | +52 % | |
| nocomo, noconv, notrk, optimistic, nolong | n.s. | – | |

On ATE, several components have no measurable benefit at this sample size.

## Classification (offline, L1–L3)

| method | moving-forklift recall | load on moving forklift masked | static boxes kept | load on parked forklift kept | flicker |
|---|--:|--:|--:|--:|--:|
| p7_nb | 0.99 | 0.88 | 0.78 | 0.33 | 2.1 % |
| yolo_naive | 0.99 | 0.92 | 0.02 | 0.02 | 0.5 % |

- Onset latency: median 0.00 s, p90 0.40 s.
- Effect of removing components: sticky → forklift recall 0.61; noint → loads 0.32; noprior → static boxes kept 0.11.

## D: no-harm (COCO YOLO, 10 offsets)
- **ATE vs openvins** (all n.s.):

  | sequence | yolo_naive | p7_nb |
  |---|---|---|
  | uHumans2 06h | +2.9 % | +12.2 % [−23, +59] |
  | cafe1-1 | −3.0 % | +0.7 % |

- **RPE:** n.s. for both methods.

## E: sensitivity (interaction gate)
- **Offline:** the adaptive k sweep (1–4) is nearly inert (core area changes by 0.1 %). dist_int = 0 (no interaction) differs; 1–4 m is flat.
- **Closed loop, L2+L3, vs main:**

  | setting | vs main |
  |---|---|
  | k = 1 | −4 % n.s. |
  | k = 2, 4 | identical |
  | dist_int 0 m | +27 % |
  | **dist_int 1 m** | **−27 % (Holm < 1e-3)** |
  | dist_int 2 m | −9 % |
  | dist_int 3 m | +6 % |
  | dist_int 4 m | −6 % |

  The curve is not monotone.
- **`sens_fix1` (dist_int 1 m) vs yolo_naive:**

  | | effect |
  |---|---|
  | L0+L1 | −14 % (Holm .012) |
  | L2+L3 | −4 % [−23, +18] n.s. |
  | hall L3 | −64 % (Holm .006) |
  | failures | 0/80 |

  **This meets the bar.** Caveats: it was selected post hoc on the tuning set, and its offline load recall is 0.83.

## Disk
About 3.9 GB of new data; 81 GB free.

## Pending
- **F (timing):** needs an idle-GPU slot (`scripts/run_timing.sh`).
- **G:** choose the main variant, freeze `final_config.yaml`, and record its md5 in IMPLEMENTATION_PLAN §6 before any held-out run.
