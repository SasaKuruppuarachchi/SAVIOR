# Sequence-level re-analysis of the held-out results (2026-10-26)

Coordinator copy of the agent report. No new runs were made. Scripts are in scripts/, full tables in tables/ (key_effects, main_key_effects, failures, cap_sensitivity, holm_families, viode_diag), and the figure in figures/fig_forest_seqlevel.

## Method
- The unit of inference is the sequence: the 10 offsets are within-sequence repeats.
  - k = 6 sequences per warehouse level group, 3 for static, 12 for "all".
  - The levels of a scene share one trajectory, so a group spans only 3 independent trajectories.
- Primary analysis: a REML mixed model with a sequence random intercept and t-intervals.
- Secondary: a two-stage cluster bootstrap and an exact sign-flip test.
- Holm correction over the 31 main-text claims.
- The old run-level numbers are reproduced exactly.

## Result
- **2 of the 24 directional claims survive Holm over the 31 claims:**
  - C2, O-Dyn+B vs O-Cls+B, warehouse low-dyn: −45 % [−56, −32], 6/6 sequences.
  - C21, OV+SAVIOR vs VINS-Fusion, VIODE: −63 % [−78, −38], 12/12; −52 % on non-failed runs.
- **Unadjusted p < 0.05:** C1, C4b, C6 (SAVIOR vs Y-Cls, low-dyn, 6/6), C8a, C11, C17, C19, C23.
- **Not supported:**
  - C7 SAVIOR vs Y-Cls, high-dyn: −35 % [−70, +40]; −10 % non-failed.
  - C10 Y-Cls static cost: +46 %, driven by one of 3 sequences.
  - C15 SAVIOR vs OpenVINS, high-dyn: −55 % [−90, +113]; −17 % non-failed.
  - C16 VINS+SAVIOR vs VINS: +25 % n.s.
  - C20 OV+SAVIOR vs DynaVINS, VIODE: −58 % [−84, +11]; −18 % non-failed.
  - C25 SAVIOR-adaptive vs Y-Cls.
- **Structural limit:** with k = 6, the exact sign-flip test cannot go below p = 0.031. The between-sequence variance share is 0.3–0.9, so the run-level analysis overstated the effective n by about 3–8×.

## Failures
- Failures concentrate in a few sequences:
  - OpenVINS: 8 of 13 high-dyn failures are on dock L3;
  - Y-Cls: 9 of 10 on hall L3;
  - SAVIOR: 4, all on hall L3.
- The only clustered failure difference with p < 0.05 is O-Dyn+B vs OpenVINS (sign-flip p 0.016).
- Effects that rely on failures shrink sharply on non-failed runs and with the cap (2 → 50 m moves them by 15–30 points): C7, C15, C20, C25. The low-dyn effects and C21 are invariant to the cap.

## VIODE diagnosis
- **DynaVINS:** its failures are in-motion initialisation divergences on the parking lot at offsets ≥ 4 (p = 2e-4).
- **OpenVINS-v2:** no offset trend; failures are init-phase divergences.
- **Masking** removes most parking-lot failures (OV 11 → 5, VINS 16 → 6).
- **"Most accurate on VIODE":** holds against VINS-Fusion, but not against DynaVINS on non-failed runs (−18 % [−30, +5]; DynaVINS is better on city night).

## Wording recommendations
- Report k sequences and mixed-model CIs.
- Report failures as per-sequence counts, with non-failed accuracy next to the capped geometric mean.
- Primary claim: the oracle dynamic-outlier vs class-level result (6/6 sequences).
- Learned masks at low-dyn: supported, unadjusted (6/6 sequences).
- High-dyn learned-mask effects: "same direction, not resolved".
- hall L3: present it as a single-sequence case study.
- Per-claim wording is in the agent report, kept in the coordinator transcript.
