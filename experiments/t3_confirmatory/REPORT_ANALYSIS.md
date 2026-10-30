# t3 confirmatory analysis: OpenVINS-v2 family (coordinator GO, AMENDMENT_08, 2026-10-30)

Outcomes are reported exactly as computed. Nothing was tuned, dropped or re-run after seeing results.

## What was run
- Frozen analysis, unchanged files: `scripts/stats_t3.py`, `t3_extras.py`, `t3_amend03.py`, `t3_amend04.py`, `t3_strict_sens.py`; DESIGN.yaml md5 checked; `scripts/t3_run_analysis.sh` md5 checked against ANALYSIS_PREP.md5.
- Wrapper `scripts/t3_run_analysis_ov2.sh` (md5 in `ANALYSIS_OV2.md5`) = `t3_run_analysis.sh` plus one change. The analysis container sees an empty read-only directory over `vins_runs/` and `dyna_masks_runs/`, so the frozen code loads no VINS-family or DynaVINS+masks data. The VINS-family comparisons (S1-S8, S14) therefore drop out and are never computed on a partial set. Nothing in a frozen file was edited.
- Before the analysis, the OV-family audits were refreshed on the current files (OV only, VINS runs excluded because they are being written): m2bsync (`tables/invalid.txt`, `sync_audit.csv`) and the frames audit (tag "": `frames_audit.csv`, `frames_invalid.txt`, `frames_tail_only.txt`).
- The clarified invalid list (AMENDMENT_05 rule) was built by `t3_run_analysis.sh` into `tables/invalid_clarified.txt`.
- Unit of inference: the trajectory (24 trajectories, 6 per environment fw/sw/ms/wx; no exclusions). Model: REML random intercept per trajectory, t test with df = 23, 95 % t interval. Cap 10 m, failure = ATE > 2 m. Offsets are within-sequence repeats (5 per sequence).

## Validity
- OV2 family: 12 methods x 480 runs = 5760 runs; 0 missing; 0 clarified-invalid.
- m2bsync raw invalid = 309; all 309 are tail-only and sync_ok, so 0 remain under the AMENDMENT_05 rule. The frames audit gives 5451 strict-complete plus 309 tail-only = 5760/5760 pass the clarified rule; 0 mid-sequence frame loss.
- SAVIOR-none vs OpenVINS control: 480/480 identical trajectories (md5), ATE difference 0.
- Strict-complete sensitivity (309 tail-only runs dropped from pairs) is in `tables/strict_sensitivity.md`; conclusions below are unchanged.
- `tables/primary.md` prints "missing runs: 3360": these are the VINS-family runs, hidden on purpose (see above).

## Primary: P1-P5, fixed-order gatekeeping (each two-sided alpha 0.05; P5 TOST)
Estimate = exp(mu) - 1 of the ATE ratio (first vs second method); n = 24 trajectories (P1-P4: 48 sequences, P5: 24 sequences), df = 23.

| hyp | comparison (group) | estimate [95 % CI] | p (LMM) | sign-flip p | traj better/worse | rejected |
|---|---|---|---|---|---|---|
| P1 | O-Dyn+B vs O-Cls+B (L2+L3) | -45.4 % [-57.0, -30.7] | 2.5e-05 | 1.9e-06 | 22/2 | yes |
| P2 | SAVIOR vs Y-Cls (L2+L3) | -33.7 % [-42.0, -24.3] | 1.7e-06 | <1e-6 | 22/2 | yes |
| P3 | SAVIOR vs Y-Cls (L0+L1) | -27.4 % [-35.4, -18.4] | 9.1e-06 | 9.5e-07 | 21/3 | yes |
| P4 | SAVIOR vs OpenVINS (L2+L3) | -47.8 % [-60.2, -31.4] | 5.6e-05 | <1e-6 | 24/0 | yes |
| P5 | SAVIOR vs OpenVINS (L0), equivalence +-10 % | +2.4 % [-6.6, +12.1]; 90 % CI [-5.1, +10.4] | 0.602 | 0.603 | 11/13 | **NO** |

**Chain verdict.** P1, P2, P3 and P4 were each rejected in the stated direction, so the chain reached P5. P5 was tested and not rejected: the 90 % interval [-5.1, +10.4] lies inside the lower margin but its upper limit exceeds +10 % by 0.4 percentage points. Equivalence is therefore not shown. The point estimate is +2.4 % (SAVIOR slightly worse), and the 95 % interval [-6.6, +12.1] does not exclude a static cost of about +12 %. P5 is the last hypothesis, so the stop at P5 does not leave any later confirmatory hypothesis untested. The result is the same for every cap (static runs have no failures at any cap, so P5 is cap-independent) and under the strict-complete sensitivity (+6.4 % [-4.5, +18.6], 90 % CI [-2.7, +16.4], p 0.244, n 22 trajectories), which is also not equivalent. Per environment, P1 holds in 3 of 4 environments (wx -4.7 %, not significant), and P5 is within noise in each environment (fw +0.3, sw +8.9, ms +11.8, wx -10.1 %); see `tables/per_environment.md`.

Cap sensitivity (caps 2, 5, 50 m and failures excluded; `tables/cap_sensitivity.md`): P1-P4 stay significant and negative in every variant (P4: -43.8, -46.1, -51.5 and -37.8 % for failures excluded).

## Secondary S tests
OV-family tests (Holm p as produced by the frozen code, i.e. over the 5 computed tests only):

| id | comparison (group) | estimate [95 % CI] | p | Holm p (5 tests) | traj better/worse |
|---|---|---|---|---|---|
| S9 | SAVIOR-edge vs SAVIOR (L2+L3) | +5.1 % [-3.5, +14.4] | 0.238 | 0.641 | 9/15 |
| S10 | SAVIOR-edge vs SAVIOR (L0+L1) | +2.8 % [-3.9, +9.9] | 0.405 | 0.641 | 12/12 |
| S11 | Y-Cls vs OpenVINS (L0) | +41.6 % [+21.0, +65.6] | 1.3e-04 | 5.4e-04 | 2/22 |
| S12 | O-Dyn+B vs OpenVINS (L2+L3) | -56.2 % [-66.5, -42.9] | 1.5e-06 | 7.7e-06 | 24/0 |
| S13 | SAVIOR vs OpenVINS (L0+L1) | +3.8 % [-2.3, +10.2] | 0.214 | 0.641 | 9/15 |

Caveat on multiplicity: the pre-registered Holm family is S1-S14. The frozen code applies Holm over the 5 tests that were computed. A conservative bound that treats the 14 as the family (multiplier at most 14): S12 <= 2.1e-05 and S11 <= 1.8e-03 stay below 0.05, and S9, S10 and S13 stay non-significant (Holm adjustment can only raise p). So the S9-S13 conclusions do not depend on this.
Reading: SAVIOR-edge is not distinguishable from SAVIOR (S9, S10). Naive classification costs +42 % static ATE vs OpenVINS (S11). The dynamic-oracle mask reduces ATE by 56 % at high dynamics (S12). SAVIOR at low dynamics is not distinguishable from OpenVINS, point estimate +3.8 % (S13).

**VINS-family tests S1-S8 and S14 (VINS-Fusion, VINS+masks, DynaVINS): not completed by the submission deadline.** They are not computed on a partial set. VINS-family runs are still running (see below). Note that `tables/failure_diff.md` and `tables/extras.json` still list rows for these comparisons with "0 / 0" runs; those rows are empty-data artifacts and carry no information (S7, S8 rows with SAVIOR "1 / 240 vs 0 / 0" are likewise not valid). The DynaVINS+masks secondary (DM1-DM9) is dropped per AMENDMENT_08 (`tables/dyna_masks.md` is empty).

## Exploratory X1-X3 (AMENDMENT_03; own Holm family; n = 24 trajectories, L2+L3)
| id | comparison | estimate [95 % CI] | p | Holm p | traj better/worse |
|---|---|---|---|---|---|
| X1 | SAVIOR vs OpenVINS chi2 x0.25 | +19.8 % [+2.8, +39.7] | 0.023 | 0.045 | 7/17 |
| X2 | SAVIOR + chi2 x0.25 vs OpenVINS chi2 x0.25 | -5.1 % [-16.0, +7.3] | 0.391 | 0.391 | 12/12 |
| X3 | OpenVINS chi2 x0.25 vs OpenVINS | -56.4 % [-64.5, -46.4] | 2.1e-08 | 6.3e-08 | 24/0 |

Reading: tightening the OpenVINS chi-square multipliers to 0.25 alone (X3) gives the largest gain, larger than SAVIOR masks alone; against that tuned baseline SAVIOR (default multipliers) is worse (X1, and it depends on the cap: significant at caps 2, 5, 10 and with failures excluded (+38.2 %); not at 50 m, +14.3 % [-4.7, +37.2]), and SAVIOR added to the tuned baseline is not distinguishable from it (X2; with failures excluded +9.9 % [-0.9, +21.8]). Per environment: `tables/amend03.md`.

## Exploratory Y1-Y4 (AMENDMENT_04; own Holm family; n = 24 trajectories)
| id | comparison (group) | estimate [95 % CI] | p | Holm p | traj better/worse |
|---|---|---|---|---|---|
| Y1 | SAVIOR + NIS gate vs SAVIOR (L2+L3) | -24.1 % [-33.1, -13.9] | 1.5e-04 | 4.6e-04 | 20/4 |
| Y2 | SAVIOR + NIS gate vs OpenVINS chi2 x0.25 (L2+L3) | -9.1 % [-20.8, +4.4] | 0.167 | 0.334 | 17/7 |
| Y3 | SAVIOR + NIS gate vs OpenVINS + NIS gate (L2+L3) | -84.0 % [-90.7, -72.4] | 4.5e-07 | 1.8e-06 | 24/0 |
| Y4 | SAVIOR + NIS gate vs OpenVINS (L0), equivalence | -33.1 % [-39.8, -25.8]; 90 % CI [-38.7, -27.1] | TOST 1.000 | 1.000 | 23/1 |

Y4 is not equivalent: the NIS-gate variant is 33 % better than OpenVINS at L0 (the interval is entirely below the -10 % margin), not equivalent in the TOST sense. Descriptive D1 (SAVIOR-SG vs SAVIOR): high +2.8 % [-4.2, +10.3], low -4.1 % [-6.8, -1.3], static -3.1 % [-6.4, +0.3]. Y3 reflects that OpenVINS + NIS gate alone fails often (below). Per environment: `tables/amend04.md`.

## Failures (ATE > 2 m or no estimate), trajectory-cluster bootstrap 95 % CI (high = L2+L3)
| method | high | all levels |
|---|---|---|
| OpenVINS | 12/240 = 5.0 % [2.1, 8.8], 9 trajectories | 12/480 = 2.5 % [1.0, 4.4] |
| SAVIOR-none (control) | 12/240 (identical to OpenVINS) | 12/480 |
| Y-Cls | 5/240 = 2.1 % [0.4, 3.8] | 7/480 = 1.5 % [0.4, 2.7] |
| SAVIOR | 1/240 = 0.4 % [0.0, 1.2] | 1/480 = 0.2 % [0.0, 0.6] |
| O-Dyn+B | 0/240 = 0.0 % | 0/480 |
| O-Cls+B | 10/240 = 4.2 % [0.8, 8.3] | 14/480 = 2.9 % [0.4, 6.2] |
| SAVIOR-edge | 1/240 = 0.4 % [0.0, 1.2] | 1/480 = 0.2 % [0.0, 0.6] |
| OpenVINS chi2 x0.25 | 8/240 = 3.3 % [1.2, 5.8] | 9/480 = 1.9 % [0.8, 3.1] |
| SAVIOR + chi2 x0.25 | 1/240 = 0.4 % | 2/480 = 0.4 % [0.0, 1.0] |
| SAVIOR + NIS gate | 2/240 = 0.8 % [0.0, 2.1] | 2/480 = 0.4 % [0.0, 1.0] |
| OpenVINS + NIS gate | 84/240 = 35.0 % [27.9, 41.7] | 84/480 = 17.5 % [14.0, 20.8] |
| SAVIOR-SG | 3/240 = 1.2 % [0.0, 3.3] | 3/480 = 0.6 % [0.0, 1.7] |

At static and low dynamics, failures are 0 for OpenVINS and SAVIOR; Y-Cls has 1 static and 2 low-level failures, O-Cls+B 2 and 4. Paired failure differences (trajectory sign-flip, `tables/failure_diff.md`): SAVIOR vs OpenVINS high -4.58 pp, p 0.008; O-Dyn+B vs OpenVINS high -5.00 pp, p 0.004; SAVIOR vs Y-Cls high -1.67 pp, p 0.219 (not significant); O-Dyn+B vs O-Cls+B high -4.17 pp, p 0.125 (not significant).

## Accuracy on non-failed runs (ATE <= 2 m; median ATE in m; `tables/nonfailed.md`)
| method | static | low | high |
|---|---|---|---|
| OpenVINS | 0.076 | 0.077 | 0.129 |
| SAVIOR | 0.079 | 0.080 | 0.092 |
| Y-Cls | 0.106 | 0.112 | 0.130 |
| O-Dyn+B | 0.076 | 0.077 | 0.080 |
| O-Cls+B | 0.113 | 0.112 | 0.122 |
| SAVIOR-edge | 0.088 | 0.082 | 0.097 |

The accuracy gain at high dynamics is therefore not only a failure-rate effect; the P4 estimate with failures excluded is still -37.8 % [-50.6, -21.8].

## Per-environment breakdown (descriptive, no multiplicity control; `tables/per_environment.md`)
- P4 (SAVIOR vs OpenVINS, L2+L3): 6/0 trajectories better in all four environments (fw -49.6, sw -47.3, ms -50.6, wx -43.3 %; 95 % CIs include 0 in fw, ms and wx because n = 6 per environment; sign-flip p 0.031 = the minimum possible with 6 trajectories).
- P2 (SAVIOR vs Y-Cls, L2+L3): negative in all four (fw -42.0, sw -37.6, ms -19.7, wx -33.8 %).
- P3: negative in all four (fw -28.1, sw -26.4, ms -24.3, wx -30.5 %).
- P1: negative in fw, sw, ms (-52.6, -68.0, -38.6 %); wx -4.7 % [-19.8, +13.2] (4/2), not different from zero.
- P5 (static): fw +0.3, sw +8.9, ms +11.8, wx -10.1 %, none different from zero.

## Figure
Forest plot of P1-P5, X1-X3 and Y1-Y4 with 95 % trajectory-level CIs (paper.mplstyle): `figures/fig_t3_forest.pdf`, `figures/fig_t3_forest.png` (script `scripts/fig_t3_forest.py`). The P5 grey band is the +-10 % margin; the plotted P5 bar is the 95 % CI, while the test uses the 90 % CI.

## VINS family status
Restarted at full capacity under AMENDMENT_08 by `scripts/t3_drive_a08.sh` (md5 in `DRIVER_A08.md5`): cap 36 containers, PAR_VINS 30, mask exports 10 concurrent, ros1_bag container name now uses `$BASHPID` + random suffix, DynaVINS+masks off. The frames audit and the completeness check still apply at the end of the driver; no analysis runs in it. Status at report time is in the hand-off message.

## Files
`tables/primary.md secondary.md failures.md cap_sensitivity.md per_environment.md controls.md failure_diff.md nonfailed.md amend03.md amend04.md strict_sensitivity.md stats_t3.json extras.json amend03.json amend04.json invalid_clarified.txt frames_audit.md`. Logs of the run are in `/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval/logs/analysis_ov2.log`.

## VINS-family secondary tests (AMENDMENT_09, computed 2026-10-30 ~14:00, after submission)
- **Set:** complete. 3360/3360 VINS-family runs are valid; the final combined audit has 9120/9120 valid (8811 strict, 309 tail only), 0 failures (> 2 m) in any VINS-family method.
- **Runner:** the frozen scripts, unedited (t3_run_analysis_vins.sh = the OV2 runner with vins_runs visible). The submitted tables are kept in tables_submission_ov2/.
- **OV2 family:** P1–P5, amend03 and amend04 are identical to the submitted ones.
  - Only the Holm-adjusted p of the OV2 secondary tests changes, because the Holm family is now the full pre-registered S1–S14 family instead of the subset available at submission.
  - S11 goes from 5.4e-04 to 0.001 and S12 from 7.7e-06 to 2.0e-05. S9, S10 and S13 stay at 0.641.
  - No conclusion changes.
- **Empty-mask control for VINS-Fusion:** 480/480 runs identical (ATE difference 0).

| id (paper C#) | comparison | group | estimate [95 % CI] | Holm p | better/worse |
|---|---|---|---|---|---|
| C1 | VINS+SAVIOR vs VINS+Y-Cls | high | -12.9 % [-21.4, -3.5] | 0.064 | 16/8 |
| C2 | VINS+SAVIOR vs VINS+Y-Cls | low | -12.7 % [-20.1, -4.6] | 0.030 | 19/5 |
| C3 | VINS+SAVIOR vs VINS-Fusion | high | -13.5 % [-27.9, +3.8] | 0.454 | 14/10 |
| C4 | VINS+O-Dyn+B vs VINS+O-Cls+B | high | -20.2 % [-26.9, -12.9] | 2.4e-04 | 22/2 |
| C5 | VINS+Y-Cls vs VINS-Fusion | static | +26.1 % [+9.3, +45.4] | 0.021 | 6/18 |
| C6 | VINS+SAVIOR vs VINS-Fusion | static | +8.6 % [+1.9, +15.7] | 0.064 | 8/16 |
| C7 | SAVIOR (OpenVINS) vs DynaVINS | high | +33.4 % [+12.9, +57.7] | 0.015 | 6/18 |
| C8 | SAVIOR (OpenVINS) vs DynaVINS | low | +49.9 % [+31.4, +71.1] | 2.1e-05 | 1/23 |
| C14 | DynaVINS vs VINS-Fusion | high | -56.0 % [-65.5, -43.8] | 5.9e-06 | 23/1 |

**Reading:**
- With VINS-Fusion as well, perfect dynamic-outlier masks beat class-level masks (C4, 22/24). The back-end-agnostic oracle result therefore replicates on the confirmatory split.
- SAVIOR masks beat Y-Cls masks for VINS-Fusion at both traffic groups (point estimates -13 %; significant after Holm at low traffic).
- Class masks cost VINS-Fusion +26 % in static scenes. SAVIOR's static cost for VINS-Fusion, +8.6 %, is smaller but not excluded.
- Against unmasked VINS-Fusion, SAVIOR masks give no detectable gain in heavy traffic (C3, n.s.). This matches the paper's statement that optimization-based back-ends gain little.
- DynaVINS is more accurate than OpenVINS+SAVIOR in simulation (C7/C8), as on the held-out split.
