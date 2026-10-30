# Real-world (Monado) validity debug – report (debug agent a8b048a, saved by the coordinator 2026-10-27)

## 1. VINS-Fusion / DynaVINS 100 % failure (incl. static MIO07) – FIXED on MIO07 only
- A1: ROS 1 bags written with LZ4 chunks noetic roslz4 cannot decode (ROSLZ4_DATA_ERROR); no message ever reached the estimator -> 10 m cap. Bags rebuilt uncompressed (content unchanged).
- A2: Basalt IMU densities copied verbatim into VINS (50–60x too tight). Fixed with the frozen warehouse SOTA rule (upstream EuRoC value x dataset/EuRoC density): acc_n 0.8, gyr_n 0.01662, acc_w 3.333e-4, gyr_w 5.156e-4.
- MIO07 after fix: VINS-Fusion 10/10 ok (0.040–0.075 m); DynaVINS 9/10 ok (run_08 diverges). OpenVINS 0.038 m.
- Configs frozen before any person-sequence run: FREEZE_AMENDMENT.txt / FREEZE_AMENDMENT.md5; rw_args.py checks both.
- DynaVINS diverges mid-sequence on MIO15 (10/10) and MIO16 (6/10); back end 54–97 ms/frame vs 37 ms budget at rate 0.5 (possible factor, unproven).

## 2. Empty-mask control not bit-identical – NOT a mask-path bug
- At rate 0.5, whole stereo frames are dropped between bag player and the OpenVINS subscription (host load 80–180); plain OpenVINS also drops. All rate-0.25 runs received every frame.
- Complete-input pairs (21): ATE agrees to 4 digits, 8/21 md5-identical, worst 1.6 %. Incomplete pairs (19): up to 94 %.
- OpenVINS reference on MIO07 incomplete in 10/10 runs; MIO15 savior_none complete 2/10.
- Proposed fix: run reference methods at rate 0.25 + validity rule "processed frames = bag pairs after offset".

## 3. MIO13 RPE 0.0000 – FIXED
- Two interrupted runs (no run_info.yaml) had no sub-trajectory >= 5.69 m; eval wrote mean 0 and rw_analyze.py used it. RPE now NaN when there are no segments; invalid runs are listed; the two runs were re-run (valid).

## Results after fixes 1 and 3 (before the fix for 2)
ATE geometric mean m / failures > 1 m (of 10):

| sequence | OpenVINS | SAVIOR-none | Y-Cls | SAVIOR | VINS-Fusion | DynaVINS |
|---|--:|--:|--:|--:|--:|--:|
| MIO13 | 2.599 / 6 | 2.599 / 6 | 0.401 / 2 | 0.267 / 0 | 0.293 / 0 | 10.0 / 10 |
| MIO15 | 0.807 / 4 | 0.706 / 4 | 0.676 / 3 | 0.207 / 1 | 0.210 / 0 | 10.0 / 10 |
| MIO16 | 0.155 / 0 | 0.155 / 0 | 0.158 / 0 | 0.196 / 0 | 0.311 / 0 | 3.677 / 8 |
| MIO07 | 0.038 / 0 | 0.037 / 0 | 0.038 / 0 | 0.038 / 0 | 0.055 / 0 | 0.132 / 1 |

Person group: SAVIOR vs OpenVINS −67.8 % [−82.4, −43.5]; Y-Cls vs OpenVINS −49.1 %; SAVIOR vs Y-Cls −36.7 % [−62.0, −1.3];
SAVIOR vs VINS-Fusion −17.2 % [−32.9, +5.4] (per seq −9 / −1 / −37 %); SAVIOR vs DynaVINS −96.9 %.
The earlier "−98 % vs VINS-Fusion" was an integration artefact and is withdrawn.

Housekeeping: ROS 1 bags deleted; raw zips archived to /home/hdd/sasa/archive/savior/workspace/data/monado/raw/ (sha256-verified, manifest rows added).

## Amendment 2 (all methods at rate 0.25 + frame rule) – final results (2026-10-27)
- 280/280 runs valid at the first attempt (0 frames lost). Rate-0.5 results are kept as a disclosed secondary (runs_rate05/, tables_rate05/).
- Person-group ATE: SAVIOR vs OpenVINS −67.8 % [−82.4, −43.5] (Holm .014); per sequence −90 / −74 / +27 %.
  - SAVIOR vs Y-Cls −36.7 % [−62, −1] (Holm .29).
  - SAVIOR vs VINS-Fusion −13.5 % [−30, +10] (Holm .073); per sequence −0 / +0 / −35 %.
  - SAVIOR vs DynaVINS −96.5 %.
- Failures (> 1 m), person sequences: OpenVINS 10/30, Y-Cls 5/30, SAVIOR 1/30, VINS-Fusion 0/30, DynaVINS 27/30.
- Empty-mask control: max ATE difference 0.021 % (14/40 md5-identical); group effect −0.0 %. At rate 0.5 it was −4.4 %, the frame-loss effect.
- Static MIO07: SAVIOR vs OpenVINS −3.3 % [−18, +15]; R3 holds.
- MSCKF-used share on people: MIO13 26.7 %, MIO15 7.2 %, MIO16 2.5 %, MIO07 0 %.
- Sequence level: k = 3, so the minimum sign-flip p is 0.25. Supporting evidence only.
