# M2b Report: pre-registered held-out benchmark (warehouse t2 + VIODE)

Date: 2026-10-24. Held-out benchmark agent; report saved by the coordinator.
- **Frozen configs:** main `results/p7/final_config.yaml` (md5 6fea24e5…) and addendum `final_config_addendum.yaml` (md5 f07c9c30…, frozen 2026-10-23 23:42).
- **Hypotheses:** H1–H5, pre-registered in the addendum.
- **Details:** `tables/` and `figures/`.

## Validity
- **Volume:** 8 methods × 24 sequences × 10 offsets = 1920 runs, all at rate 0.5. All 1920 are sync-valid.
- **Pose-count rule:** 1877/1920 pass literally. The 43 others (hall_t2_L3 ×37, parking_lot_mid ×5, dock_t2_L3 ×1) are LATER FILTER STARTS: first pose a median 1.4 s later, at most one pose missing after the start. This is not bag-end truncation. All 43 were re-run: pose counts identical 43/43, ATE agreeing to ≥ 4 digits. They are kept and flagged.
- **Control:** warehouse savior_none ≡ openvins, md5 120/120. VIODE: 114/120 within 0.1 mm, plus one diverged pair.
- **SAVIOR-edge (addendum):**
  - build: frozen_edge/ (git fdf5fe61), flags-off ≡ sens_fix1 (20/20 md5);
  - VIODE instantiations of all methods were written from the P5 settings without tuning;
  - COCO YOLO26n engine md5 86713aac….

## Warehouse t2 (held-out)
Paired geometric-mean ATE change [95 % CI], Holm-corrected p.

| comparison | L0+L1 | L2+L3 | hall+dock L3 | failures (>2 m), L3 |
|---|---|---|---|---|
| SAVIOR vs Y-Cls | **−29 %** [−40, −16] H 6e-4 | **−49 %** [−61, −35] H 3e-6 | −62 % H .010 | 10 vs 18 |
| SAVIOR-adaptive vs Y-Cls | −22 % H .008 | −43 % H 3e-6 | −53 % H .032 | 11 |
| SAVIOR-adaptive vs SAVIOR | +10 % n.s. | +12 % n.s. | +25 % n.s. | – |
| SAVIOR-edge vs SAVIOR | +6 % [−13, +32] n.s. | **−44 %** [−62, −17] H .003 | −73 % H .032 | 4 vs 10 |
| O-Dyn+B vs O-Cls+B | **−52 %** H 9e-5 (L0 −59 %) | **−82 %** H 1e-10 | −98 % | 2 vs 20 |
| SAVIOR vs OpenVINS | −8 % n.s. | **−49 %** H .005 | −61 % H .08 | 10 vs 15 |
| SAVIOR-edge vs OpenVINS | −2 % n.s. | −71 % H 5e-7 | −89 % H .001 | 4 |
| Y-Cls vs OpenVINS | +30 % H .014 | +1 % n.s. | +3 % n.s. | 18 |
| O-Dyn+B vs OpenVINS | −4 % n.s. | −76 % H 4e-6 | −96 % | 2 |

- **hall_t2_L3:** almost every method diverges. Failures out of 10: OpenVINS 8, Y-Cls 9, SAVIOR 9, SAVIOR-adaptive 9, O-Cls+B 10, SAVIOR-edge 2, O-Dyn+B 1.
- **dock_t2_L3:** SAVIOR 1/10, OpenVINS 7, Y-Cls 9.
- **RPE** agrees in direction.

## VIODE (failure > 1 m)

| comparison | none+low | mid+high | low+mid+high | high |
|---|---|---|---|---|
| SAVIOR vs OpenVINS | −3 % n.s. | **−24 %** H .032 | −19 % H .038 | −35 % H .041 |
| SAVIOR vs Y-Cls | +4.5 % n.s. | −4.5 % n.s. | −2 % n.s. | +1 % n.s. |
| SAVIOR-adaptive vs SAVIOR | 0 % | −0.7 % | −0.5 % | – |
| SAVIOR-edge vs SAVIOR | +26 % [+4, +62] H .067 | +3 % n.s. | +17 % n.s. | – |
| O-Dyn+B vs O-Cls+B | −1 % | −9 % n.s. | −7 % n.s. | – |
| O-Dyn+B vs OpenVINS | −4 % | −28 % H .013 | −21 % H .011 | – |

- **Failures out of 120:** OpenVINS 4, Y-Cls 2, SAVIOR 2, SAVIOR-adaptive 2, SAVIOR-edge 4.
- **Share vs gain** (moving-pixel share, all 24 sequences): O-Dyn+B rho +0.66 (p 4e-4); SAVIOR +0.40 (p .055); SAVIOR-edge +0.60.

## Pre-registered hypotheses
- **H1 (SAVIOR vs Y-Cls bar): PARTLY MET.** Accuracy is met and strong: −29 % at L0+L1 and −49 % at L2+L3. The "0 failures on hall/dock L3" part fails (10 vs Y-Cls 18; 9 of the 10 on hall_t2_L3).
- **H2 (SAVIOR better than OpenVINS): MET** at warehouse L2+L3 and VIODE mid+high. Not on hall L3, where all methods diverge.
- **H3 (secondary, SAVIOR-adaptive):** the same pattern as H1. It is never better than SAVIOR.
- **H4 (dynamic-outlier masking beats class-level masking, perfect masks): CONFIRMED on the warehouse** (L0 −59 %, L2+L3 −82 %). Not significant on VIODE (parked cars cover few pixels).
- **H5 (SAVIOR-edge within +10 % of SAVIOR): PASSES on the warehouse, uncertain** (CI upper bound +32 % at L0+L1; much better at L2+L3; 4 vs 10 failures). On VIODE it is worse at none+low (+26 %, H .067) with 2 more failures.
- Nothing was re-tuned, changed or dropped.
