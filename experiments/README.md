# experiments/: frozen per-study scripts, configurations and reports

Each folder holds the scripts, configurations, freeze/protocol files, reports (`REPORT*.md`) and result tables of one
study of the paper and its supplement (S1 to S13). The folder name is the study's name in the original workspace, where
it lived at `results/<study>/`.

**The scripts are archived exactly as they were run.** They are not cleaned up: they contain the authors' absolute
paths (`/home/sasa/workspace/savior_ws/...`, `/home/hdd/...`), internal job names and, in the reports, the working
notes of the time. Editing them would invalidate the freeze checksums, so they are kept byte-identical. For the same
reason a few source files outside this folder (the frozen configs, OpenVINS files and SOTA scripts that are listed in
the freeze md5 files) are also unchanged; their comments still refer to `docs/IMPLEMENTATION_PLAN.md`, which is now
[`docs/INTERFACE.md`](../docs/INTERFACE.md) (same section numbers).

**Raw run outputs, trajectories, masks and datasets are not in git.** They are in the Zenodo record
<https://doi.org/10.5281/zenodo.23803392> (see [`docs/DATA.md`](../docs/DATA.md) for what is where and how to use it).

## Studies

Supplement parts are numbered as in `savior_supp`: S1 configuration freezes and disclosure (S1.2 back-end diagnostic),
S2 protocol and complete held-out results (S2.2 re-tuned back-end, S2.3 original back-end), S3 SAVIOR-Warehouse and the
segmenter, S4 when masking matters, S5 dynamic-outlier vs. class-level masking (S5.4 gate sensitivities, S5.5
development history), S6 back-end-agnostic masking, S7 runtime / embedded / SAVIOR-edge, S8 sequence-level statistics,
S9 additional held-out runs, S10 tuned and self-tuned gates, S11 DynaVINS masks, S12 real-world validation, S13
confirmatory split. "t1" is the tuning split, "t2" the held-out split, "t3" the confirmatory split.

| folder | what it is | protocol / freeze files | supports |
|---|---|---|---|
| `t3_confirmatory` | Confirmatory split: 24 new trajectories in four environments (96 sequences), pre-registered hypothesis chain, 8 dated amendments, analysis scripts | `DESIGN.yaml` + `DESIGN.md5`, `AMENDMENT_01..08.txt`, `AMENDMENT_0x_IMPL.md5`, `DRIVER_A0x.md5`, `ANALYSIS_*.md5`, `EXCLUSIONS.yaml`; `REPORT_DATASET.md`, `REPORT_ANALYSIS.md` | S13 |
| `real_world` | Monado SLAM dataset (Valve Index), 4 sequences (3 with a moving person, 1 static control), all methods incl. VINS-Fusion and DynaVINS | `PROTOCOL.yaml`, `FREEZE.md5`, `FREEZE_AMENDMENT.txt` + `.md5`; `DEBUG_REPORT.md` (no `REPORT.md`) | S12 |
| `dynavins_masks` | SAVIOR masks fed to DynaVINS (patch P10): determinism mode, mask manifest, tuning and held-out results | `FREEZE.md5`, `FREEZE_DATE.txt`, `FREEZE_AMENDMENT.txt`; `REPORT.md` | S11 |
| `final_heldout` | One text file with the held-out numbers of the OpenVINS-v2 family against VINS-Fusion / DynaVINS (cross-back-end comparison) | none | S11.1 (cross-back-end held-out numbers) |
| `review_runs` | Held-out ablations (without association tree / motion evidence), tightened-chi2 baseline, gate sweep under the re-tuned back-end, promotion spill, final SAVIOR on OpenLORIS and uHumans2 (tasks A to E) | `FREEZE.yaml` + `FREEZE.md5`, `FREEZE_AMENDMENT.txt`; `REPORT.md` | S9 (the tightened-chi2 baseline, task B, is also used in S10) |
| `semantic_gate` | Semantic chi2 gate and NIS-adaptive gate, tuning split only | `FREEZE.yaml` + `.md5`, `GRID.yaml` + `.md5`; `REPORT.md` | S10 |
| `nis_validation` | Cross-dataset validation of the NIS gate (warehouse t2, VIODE, OpenLORIS, uHumans2, Monado) | `PROTOCOL.yaml` + `.md5`; `REPORT.md` | S10 |
| `chi2_realworld` | One-shot test of the chi2 x0.25 gate (tuned on t1) on Monado | `PROTOCOL.yaml` + `.md5`, `DECISION_RULE.txt`, `scripts/ANALYSIS.md5`; `REPORT.md` | S10 |
| `stats_v3` | Sequence-level re-analysis of the held-out results (mixed model, cluster bootstrap, sign-flip, Holm over 31 claims); no new runs | none (`scripts/stats3_core.py` is imported by `t3_confirmatory`) | S8 |
| `edge_study` | SAVIOR-edge (efficiency variant): pre-defined acceptance criterion, closed-loop accuracy and compute | `CRITERION.txt`, `edge_methods.json` | S7 |
| `jetson_validation` | On-device validation on a Jetson Orin NX 8 GB (real-time criterion R1 to R5, timing, memory, power, device vs desktop accuracy) | `RT_CRITERION.txt`; `REPORT.md` | S7 |
| `cpp_port` | C++ / TensorRT node: equivalence with the Python node, closed-loop md5 identity, timing | none (scripts and tables only; see also `savior_perception_cpp/README.md`) | S7 |
| `vins_savior` | SAVIOR masks in VINS-Fusion (patch P9): tuning-split report; `scripts/heldout/` and `cross_backend_*.py` hold the held-out runs and the cross-back-end comparison | `FREEZE.md5`, `FREEZE_AMENDMENT.txt`; `REPORT.md` (tuning split) | S6 |
| `sota` | Controlled SOTA benchmark: VINS-Fusion, DynaVINS, ORB-SLAM3 on held-out and VIODE (720 runs) | none in the folder (the benchmark protocol is described in `REPORT.md`) | S6 (SOTA configuration and caveats), S2 (benchmark in the freeze timeline) |
| `backend_v2` | Back-end re-tune (`track_frequency` 21 to 10.5, `max_clones` 11 to 15): re-freeze, t1 validation; the folder also holds the scripts (`heldout_v2.sh`, `run_heldout_v2.sh`) and the `ate_t2` / `ate_viode` tables of the held-out run with the re-tuned back-end | `backend_config.yaml` + `.md5`, `config/estimator_v2.md5`; `REPORT.md` (covers t1 only) | S1.1, S2.2 |
| `ov_diag` | OpenVINS baseline diagnostic on the tuning split (error decomposition, init, IMU noise, window length), which led to the re-tune | none; `REPORT.md` | S1.2 |
| `m2b_heldout` | Pre-registered held-out benchmark with the original back-end (warehouse t2 + VIODE, 8 methods, 1920 runs) | the addendum is `p7/final_config_addendum.yaml` (+ `.md5`); `REPORT.md` | S2.3 |
| `p7` | Tuning-split gate sweep and ablations with the original back-end; the frozen main configuration (`final_config.yaml`) and the addendum (SAVIOR-edge, untuned VIODE instantiation, hypotheses H1 to H5) | `final_config.yaml` + `.md5`, `final_config_addendum.yaml` + `.md5`, `PLAN_approved.txt`; `REPORT.md` | S1 (freeze 1 and 3), S5.4 |
| `p6_warehouse` | First SAVIOR-Warehouse benchmark (tuning split, original back-end): oracles, class-level masking, development variants | `methods.yaml`; `REPORT.md` | S4, S5.5 (development) |
| `p5_viode` | VIODE benchmark on the tuning stage (original back-end), dataset preparation records, feature-fate logging build | `prep/`; `REPORT.md` | S4 (feature fates), development |
| `p4` | Method development: motion evidence, short-baseline gate, init policy, ego tracker | `recommended_config.yaml`; `REPORT.md` | S5.5 (development) |
| `p3a` | Ceiling of oracle human masking on uHumans2 (0/6/12 humans) | `config/`; `REPORT.md` | S4 (uHumans2) |
| `p2` | First end-to-end SAVIOR runs (OpenLORIS T265, uHumans2 00h check) | `REPORT.md` | development (not tied to a specific supplement table in the files) |
| `warehouse_sanity` | Build report and sanity runs of the first SAVIOR-Warehouse sequences | `REPORT.md` | S3 |
| `yolo_warehouse` | Fine-tuning of YOLO26-seg on SAVIOR-Warehouse: evaluation tables and recommendation | `REPORT.md` | S3 (segmenter) |
| `paper_figures` | Scripts that draw the figures and tables of the paper and supplement from the result tables | none | main paper and supplement figures |

Corrections to the mapping suggested in the task description, from what the files say:

- `review_runs` is S9 (held-out ablations, gate sweep, promotion spill, OpenLORIS/uHumans2); only its task B (tightened
  chi2 baseline) is used again in S10. The S10 studies are `semantic_gate`, `nis_validation` and `chi2_realworld`.
- `backend_v2` is S1.1 plus the held-out evaluation with the re-tuned back-end (S2.2), not S1 alone.
- `sota` has a `REPORT.md` but no separate protocol or freeze file; the freeze of the VINS-Fusion mask runs is in
  `vins_savior`.
- `final_heldout` is a single text file (cross-back-end numbers), not a study with scripts.

## Verifying the freezes

The freeze and protocol files record md5 checksums of the configurations, scripts and patches that were fixed before the
data that test them were opened. There are two kinds of `.md5` files.

1. Folder-relative: `PROTOCOL.md5`, `FREEZE.md5` (review_runs, semantic_gate), `GRID.md5`, `final_config*.md5`,
   `backend_config.md5`, `DESIGN.md5`, `ANALYSIS_*.md5`, `scripts/ANALYSIS.md5`. Check from inside the folder:

   ```bash
   cd experiments/t3_confirmatory && md5sum -c DESIGN.md5
   cd experiments/semantic_gate   && md5sum -c FREEZE.md5 && md5sum -c GRID.md5
   ```

2. Workspace-relative: `dynavins_masks/FREEZE.md5`, `real_world/FREEZE*.md5`, `vins_savior/FREEZE.md5`,
   `t3_confirmatory/AMENDMENT_*_IMPL.md5`, `DRIVER_A0*.md5`. Their paths start with `results/<study>/...` and
   `src/savior/...`. Recreate the original layout and run them from its root (lines starting with `#` are comments):

   ```bash
   mkdir -p ws/src && ln -s "$PWD" ws/src/savior && ln -s "$PWD/experiments" ws/results   # from the repository root
   cd ws && grep -v '^#' results/vins_savior/FREEZE.md5 | md5sum -c --quiet
   ```

   Entries that refer to `data/` or `models/` need the datasets and weights (Zenodo). Some entries are superseded by a
   later amendment and differ from the original file by design; each study states this in its amendment file
   (`real_world/FREEZE_AMENDMENT.*`, `t3_confirmatory/AMENDMENT_0x.txt`, `vins_savior/FREEZE_AMENDMENT.txt`,
   `dynavins_masks/FREEZE_AMENDMENT.txt`). Checked on the repository as released:

   - pass: `vins_savior/FREEZE.md5`, `real_world/FREEZE_AMENDMENT.md5`, `t3_confirmatory/AMENDMENT_03_IMPL.md5`,
     `AMENDMENT_04_IMPL.md5`, `AMENDMENT_06_IMPL.md5`, `DRIVER_A06.md5`, `DRIVER_A07.md5`, `DRIVER_A08.md5`;
   - `real_world/FREEZE.md5`: all existing files match except `rw_args.py`, `run_rw.sh`, `make_sota_configs.py` and the
     two SOTA calibration files under `sota/config/monado/`, which `FREEZE_AMENDMENT.md5` supersedes; the entries under
     `data/` and `models/` need the Zenodo data;
   - `dynavins_masks/FREEZE.md5`: `scripts/dm_figs.py` differs (figure-layout amendment; the frozen version is kept as `scripts/dm_figs.frozen.py`), and `validation/heldout_masks_manifest.txt` is not in
     this folder;
   - `t3_confirmatory/AMENDMENT_02_IMPL.md5` and `AMENDMENT_05_IMPL.md5`: `t3_frames_audit.py` differs; each of the
     three amendment files (02, 05, 06) lists a different checksum for it.

## Re-running the analyses

The analysis scripts read the run outputs under `results/<study>/runs/` (Zenodo archives `runs_<study>.tar.gz`) and have
the workspace path hard-coded. [`docs/DATA.md`](../docs/DATA.md) describes how to point them at the extracted runs.
