# Data: what is released, where it goes, and how to check it

Everything below uses `$SAVIOR_WS`, the colcon workspace that contains this repository as `src/savior/` (see
[`docker/README.md`](../docker/README.md)). Commands that run ROS or Python go through `docker/exec.sh` (or `docker run`
with the `savior:humble-cuda12.8` image); nothing is installed on the host.

## 1. SAVIOR-Warehouse and the study artefacts (Zenodo)

Only ROS 2 bags (MCAP), ground truth and metadata are released. The raw Isaac Sim renders (camera, depth and
segmentation images) are not; they can be regenerated with `savior_datasets/warehouse/` (see its README).

Every archive extracts with

```bash
tar -xf <archive> -C "$SAVIOR_WS"
```

and produces the workspace layout directly. Check the downloads first: `md5sum -c MANIFEST.md5` in the directory that
holds the archives and the manifest of the same record.

### Record A, DOI [10.5281/zenodo.23803392](https://doi.org/10.5281/zenodo.23803392)

| archive | content | extracts to |
|---|---|---|
| `savior-<version>.zip` | code snapshot of this repository | (unpack anywhere; the git repository is the maintained copy) |
| `experiments.tar.gz` | the same content as `experiments/` in the repository | (list with `tar -tf`; the commands below use the repository's `experiments/`) |
| `runs_<study>.tar.gz` (one per `experiments/<study>`, including `runs_t3_confirmatory.tar.gz`) | run outputs: trajectories (`stamped_traj_estimate.txt`), eval yaml/txt, `run_info`, configs, stats csv/jsonl. No images, logs, pickle caches or masks | `results/<study>/...` |
| `warehouse_dev_bags_{aisles,hall,dock}.tar` | development sequences of SAVIOR-Warehouse: 20 sequences. `aisles_t1` and `hall_t1` are the tuning split; `aisles_t2`, `hall_t2` and `dock_t2` are held out; each has levels L0 to L3 | `data/warehouse/ros2_stereoseg/<seq>/<seq>.mcap` + `metadata.yaml` |
| `warehouse_dev_gt_meta.tar.gz` | ground truth and metadata of these sequences | `data/warehouse/gt/<seq>.txt`, `HELDOUT_MANIFEST.yaml`, `coverage_table*.csv`, and `data/warehouse/raw/<seq>/` with the non-image files only: `calib/`, `actors.csv`, `frames.csv`, `coverage.csv`, `gt_cam0_tum.txt`, `gt_imu_tum.txt`, `gt_imu_vel.csv`, `imu_*.csv`, `instances.json`, `meta.json`, `moving.csv` |
| `models_warehouse.tar.gz` | segmenter weights fine-tuned on SAVIOR-Warehouse (AGPL-3.0, see the README licence note): `yolo26n` and `yolo26s` `-seg-warehouse` as `.pt` and `.onnx`, plus `*_export.json`. TensorRT engines are not included (they are specific to the GPU and TensorRT version) | `models/warehouse/` |
| `MANIFEST.md5` | md5 of all archives of the record | |

The COCO-pretrained `yolo26*-seg.pt` used for the COCO-based methods are not redistributed; they come from Ultralytics
(`yolo export model=yolo26s-seg.pt ...`, see the README, section "Segmenter weights").

### Record B (`<DOI-B>`): "SAVIOR-Warehouse confirmatory split, part 1"

| archive | content | extracts to |
|---|---|---|
| `warehouse_t3_bags_fw.tar`, `warehouse_t3_bags_sw.tar` | confirmatory bags of environments `fw` and `sw` (about 15 GB each) | `data/warehouse/ros2_stereoseg/<env><nn>_t3_L<k>/` |
| `warehouse_t3_gt_meta.tar.gz` | ground truth and metadata for all 96 confirmatory sequences | `data/warehouse/raw/<seq>/` (non-image files only) and `data/warehouse/logs/` |
| `MANIFEST.md5` | | |

### Record C (`<DOI-C>`): "part 2"

`warehouse_t3_bags_ms.tar` and `warehouse_t3_bags_wx.tar` (environments `ms` and `wx`, extract as in record B), the same
`warehouse_t3_gt_meta.tar.gz`, and `MANIFEST.md5`.

(`<DOI-B>` and `<DOI-C>` are assigned when records B and C are published.)

### Where the code looks for the files

- Bags: `data/warehouse/ros2_stereoseg/<seq>/` (the run scripts, `experiments/*/scripts/*args*.py` and the t3 scripts all
  use this path). Sequences are named `<scene>_t<split>_L<level>`, for example `hall_t1_L3`, `dock_t2_L2`,
  `fw01_t3_L0`.
- Ground truth for `savior-eval --gt`: `data/warehouse/gt/<seq>.txt` (TUM format, IMU frame). The development archive
  ships these files. For the confirmatory sequences the metadata archive contains `raw/<seq>/gt_imu_tum.txt`; the
  converter `savior_datasets/warehouse/tools/to_ros2.py` writes `gt/<seq>.txt` as a copy of that file with only the
  comment line replaced, so for t3 do

  ```bash
  mkdir -p "$SAVIOR_WS/data/warehouse/gt"
  for d in "$SAVIOR_WS"/data/warehouse/raw/*_t3_L*; do cp "$d/gt_imu_tum.txt" "$SAVIOR_WS/data/warehouse/gt/$(basename "$d").txt"; done
  ```

- t3 root. The archived t3 drivers (`experiments/t3_confirmatory/scripts/run_t3.sh`, `run_t3_ov2.sh`) and
  `savior_datasets/warehouse/tools/render_t3.sh` use `T3_ROOT` only as the disk on which the large raw renders and the
  bags were stored (the workspace paths are symlinks into it) and mount it read-only into the container. With the
  extracted layout the bags are ordinary directories under `data/warehouse/ros2_stereoseg/`, so set
  `T3_ROOT="$SAVIOR_WS/data/warehouse"` (it only has to exist). `render_t3.sh`, which regenerates the raw renders
  (needs Isaac Sim), defaults to `$SAVIOR_WS/data/warehouse/t3`.

## 2. Third-party datasets (not re-hosted)

VIODE, OpenLORIS-Scene, uHumans2 and the Monado SLAM dataset are not redistributed here or on Zenodo, because of their
licences and because the originals are the authoritative copies (OpenLORIS-Scene is CC BY-ND 4.0, so converted data must
not be redistributed; the VIODE and Monado licences are CC BY 4.0 as stated in the prepare tools). Download them from the
authors and convert them with the tools in `savior_bringup/tools/` (they read the original archives and bags directly,
never run anything shipped with a dataset).

| dataset | source | sequences used | tools |
|---|---|---|---|
| VIODE (Minoda et al., RA-L 2021) | <https://github.com/kminoda/VIODE> (the segmentation metadata `rgb_ids.txt` and `vehicle_ids_<env>.txt` also come from this repository; the oracle colour maps were generated from commit 521bdff) | `parking_lot`, `city_day`, `city_night`, each at levels `none`, `low`, `mid`, `high` (12 sequences) | `viode_prepare.py`, `bag1_to_ros2.py` |
| OpenLORIS-Scene (T265 fisheye stereo + IMU only) | https://lifelong-robotic-vision.github.io/dataset/scene | `cafe1-1` (tuning), `cafe1-2`, `office1-1` to `office1-7`, and `market1-1` (own config) | `openloris_prepare.py`, `bag1_to_ros2.py` |
| uHumans2 (TESSE), office scene | https://web.mit.edu/sparklab/datasets/uHumans2/ | `office_s1_00h`, `office_s1_06h`, `office_s1_12h` | `uhumans2_prepare.py`, `bag1_to_ros2.py` |
| Monado SLAM dataset (MSD), Valve Index (de Mayo et al., arXiv 2508.00088) | <https://huggingface.co/datasets/collabora/monado-slam-datasets> | `MIO13_moving_person`, `MIO15_moving_person_props`, `MIO16_moving_screens_person_props` (person-dynamic), `MIO07_mapping_easy` (static control), plus `MI_valve_index/extras/calibration.json` | `monado_prepare.py` |

The sequence lists come from `experiments/real_world/PROTOCOL.yaml` (Monado), `experiments/review_runs/FREEZE.yaml`
(OpenLORIS, uHumans2), `experiments/p5_viode/prep/` (VIODE) and the roles and config directories in
`savior_bringup/config/` (`viode/`, `openloris_t265/`, `uhumans2/`, `monado_index/`).

### uHumans2 and OpenLORIS: `prepare_datasets.sh`

Run inside the container. Put the downloads at the locations below, then:

```bash
cd "$SAVIOR_WS"
EXEC=src/savior/docker/exec.sh          # runs in the current directory inside the workspace
$EXEC bash src/savior/savior_bringup/tools/prepare_datasets.sh uhumans2  "$SAVIOR_WS"
$EXEC bash src/savior/savior_bringup/tools/prepare_datasets.sh openloris "$SAVIOR_WS"
```

Input layout:

```
data/uhumans2/uHumans2_office_s1_00h.bag  (and _06h, _12h)
data/openloris/raw/{cafe1-1_2-rosbag.tar, office1-1_7-rosbag.tar, groundtruth.zip, market1-1.bag}
```

Output layout (override the sequence list for uHumans2 with `UH_SEQS="..."`):

```
data/uhumans2/ros2/<seq>/   data/uhumans2/gt/<seq>.txt   data/uhumans2/imu_noise_<seq>.yaml   data/uhumans2/inspect_<seq>.yaml
data/openloris/extracted/   data/openloris/ros2/<seq>/    data/openloris/gt/<seq>.txt          data/openloris/gt/base_link/<seq>.txt
```

The OpenLORIS calibration step prints the `kalibr_imucam_chain*.yaml` that is already stored in
`savior_bringup/config/openloris_t265/`.

### VIODE

Download the per-environment zips and the VIODE segmentation metadata, then convert each bag (run from `$SAVIOR_WS`). The archived scripts that
did this are `experiments/p5_viode/scripts/prepare_env.sh` and `prep_bag.sh` (they carry the authors' paths); the
commands they run are:

```
data/viode/raw/<env>.zip                          # parking_lot, city_day, city_night
data/viode/meta/segmentation/{rgb_ids.txt,vehicle_ids_<env>.txt}
unzip data/viode/raw/<env>.zip -d data/viode/extracted/<env>
src/savior/docker/exec.sh bash -c '
  T=src/savior/savior_bringup/tools; V=data/viode
  python3 -I $T/viode_prepare.py gt      --bag $V/extracted/<env>/<n>_<level>.bag --out $V/gt/<env>_<level>.txt
  python3 -I $T/viode_prepare.py convert --bag $V/extracted/<env>/<n>_<level>.bag --dst $V/ros2/<env>_<level> \
                                         --rgb-ids $V/meta/segmentation/rgb_ids.txt'
```

(`<n>_<level>` is the bag name inside the zip, for example `0_none`, `3_high`.) `viode_prepare.py inspect`, `imunoise` and
`segcolors` produce the checks recorded in `experiments/p5_viode/prep/`. Result: `data/viode/ros2/<env>_<level>/`
(ROS 2 bag with `/cam{0,1}/image_raw`, `/imu0`, `/odometry` and the segmentation as mono8 object ids) and
`data/viode/gt/<env>_<level>.txt`. The VIODE oracle methods additionally need `data/viode/gt/masks/<env>_<level>.npz`
(`experiments/p5_viode/scripts/gt_masks.py`).

### Monado SLAM dataset

Download the four sequence zips and `calibration.json` of the Valve Index headset to `data/monado/raw/`, then per
sequence, from `$SAVIOR_WS` (`experiments/real_world/scripts/prep_seq.sh MIO13 MIO13_moving_person` is the archived version):

```bash
src/savior/docker/exec.sh bash -c '
  T=src/savior/savior_bringup/tools/monado_prepare.py; D=data/monado
  python3 -I $T gt      --zip $D/raw/MIO13_moving_person.zip --out $D/gt/MIO13.txt
  python3 -I $T convert --zip $D/raw/MIO13_moving_person.zip --dst $D/ros2/MIO13 --zstd --track-hz 28.35'
```

`--track-hz 28.35` keeps the stereo pairs that OpenVINS tracks at `track_frequency 28.35` (as in the real-world
protocol). `monado_prepare.py calib --json calibration.json --out-dir <dir>` regenerates the calibration files already
stored in `savior_bringup/config/monado_index/`.

## 3. Validating the artefact

### Level 1: integrity

```bash
md5sum -c MANIFEST.md5                      # in the directory with the downloaded archives (each record)
cd experiments/t3_confirmatory && md5sum -c DESIGN.md5     # freeze files; see experiments/README.md for all of them
```

`experiments/README.md` lists which freeze files are folder-relative and which are workspace-relative, and which entries
are superseded by amendments.

### Level 2: re-analysis without re-running anything

The analysis scripts compute the paper tables from the run outputs. They have the original workspace path
`/home/sasa/workspace/savior_ws` hard-coded, and they read `results/<study>/...`, so recreate that layout and make the
path exist inside a container:

```bash
# 1. runs + scripts + frozen tables in one tree (run from the repository root)
tar -xf runs_<study>.tar.gz -C "$SAVIOR_WS"           # every study you need (a script may read the runs of another study)
mkdir -p "$SAVIOR_WS/results" && cp -rn experiments/. "$SAVIOR_WS/results/"   # scripts, DESIGN.yaml, shipped tables (-n: do not overwrite)
cp -r "$SAVIOR_WS/results/t3_confirmatory/tables" /tmp/t3_tables_shipped         # keep the shipped tables to diff against

# 2. run a frozen script in the image with the workspace mounted at the hard-coded path
W=/home/sasa/workspace/savior_ws
docker run --rm --network none -u "$(id -u):$(id -g)" -e MPLCONFIGDIR=/tmp \
  -v "$SAVIOR_WS":$W -v "$SAVIOR_WS/src/savior":$W/src/savior:ro \
  savior:humble-cuda12.8 python3 -I $W/results/t3_confirmatory/scripts/stats_t3.py
diff -r /tmp/t3_tables_shipped "$SAVIOR_WS/results/t3_confirmatory/tables"
```

`stats_t3.py` reads `results/t3_confirmatory/runs/<seq>/<method>/eval/eval_summary.yaml` (OpenVINS family),
`vins_runs/warehouse_<seq>/<method>/eval_posyaw/eval_summary.yaml` (VINS family), `DESIGN.yaml`, `EXCLUSIONS.yaml`, and
imports `results/stats_v3/scripts/stats3_core.py`; it writes `primary.md`, `secondary.md`, `failures.md`,
`cap_sensitivity.md` and `stats_t3.json` to `results/t3_confirmatory/tables/`. The final t3 tables were produced by the
wrappers `t3_run_analysis.sh` and `t3_run_analysis_ov2.sh`, which first build a "clarified" invalid-run list and mount it
over `tables/invalid.txt` (this is described in the header of the wrapper and in `AMENDMENT_05.txt`); the wrappers
require `T3_ANALYSIS_GO=yes` and call `docker` themselves with the hard-coded path, so on another machine run their
steps as in the example above, with `-v .../tables/invalid_clarified.txt:$W/results/t3_confirmatory/tables/invalid.txt:ro`
for `stats_t3.py`, and then `t3_extras.py`, `t3_amend03.py`, `t3_amend04.py` and `t3_strict_sens.py`.

The entry points of the other studies follow the same pattern (`python3 -I $W/results/<study>/scripts/<script>`; the
docstring of each lists its inputs):

| study | analysis entry point |
|---|---|
| `stats_v3` | `stats3_tables.py`, `stats3_fig.py`, `stats3_viode_diag.py` (shared code: `stats3_core.py`) |
| `m2b_heldout` | `m2banalyze.py` |
| `backend_v2` | `bv2analyze.py` |
| `p7` | `p7analyze.py` |
| `review_runs` | `rr_analyze.py`, `rr_analyze_e.py`, `rr_spill_analyze.py` |
| `semantic_gate`, `nis_validation`, `chi2_realworld` | `sg_analyze.py`, `nv_analyze.py`, `cr_analyze.py` |
| `dynavins_masks`, `vins_savior`, `sota` | `dm_analyze.py`, `vs_analyze.py` + `cmp_stats.py`, `m3b_analyze.py` |
| `real_world` | `rw_analyze.py` |
| `edge_study`, `jetson_validation`, `cpp_port` | `edge_analyze.py`, `jv_analyze.py`, `cpp_analyze.py` |

Some scripts are shell wrappers that start their own Docker containers with `-v $WS:$WS` (for example `*py.sh`,
`drun*.sh`); run the Python entry point directly as above instead.

### Level 3: re-running one sequence end to end

Build the workspace and a TensorRT engine (README, "Quick start" and "Segmenter weights"), extract
`warehouse_dev_bags_hall.tar`, `warehouse_dev_gt_meta.tar.gz` and `models_warehouse.tar.gz`, and then run SAVIOR with the
frozen main configuration on `hall_t1_L3` at start offset 1.0 s. The settings are those of `sens_fix1` in
`experiments/p7/final_config.yaml` with the re-tuned back-end of `experiments/backend_v2/` (rate 0.5, deterministic
replay, mask policy `wait`):

```bash
cd "$SAVIOR_WS"
S=$SAVIOR_WS/src/savior; B=$S/savior_bringup/config; EXEC=$S/docker/exec.sh
$EXEC ros2 launch savior_bringup savior.launch.py \
  config:=$S/experiments/backend_v2/config/warehouse/estimator_config.yaml dataset:=warehouse \
  bag:=$SAVIOR_WS/data/warehouse/ros2_stereoseg/hall_t1_L3 \
  output:=$SAVIOR_WS/results/repro/hall_t1_L3/sens_fix1/run_06/stamped_traj_estimate.txt \
  topics:="/cam0/image_raw /cam1/image_raw /imu0 /tf_static" rate:=0.5 start_offset:=1.0 \
  backend:=yolo model:=$SAVIOR_WS/models/warehouse/yolo26s-seg-warehouse.engine \
  perception_params:=$B/warehouse/savior_perception_yolo.yaml roles_file:=$B/roles/warehouse.yaml \
  mask_policy:=wait mask_timeout_ms:=30000 feature_stats:=auto \
  ov_set:="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0" \
  pset:="compose.right_fallback=median extension.enable=false gating.fixed_threshold_m=1.0 gating.link_depth=median gating.max_depth=3 gating.max_noise_m=0.5 gating.mode=fixed motion.enable=true motion.still_policy=unmask motion.use_still=false motion.window_long_s=2.0 segmenter.fast_masks=true selective.enable=true selective.prior_static_classes=box,pallet,trolley stats_compact=true tracker.enable=true tracker.motion_model=ego"
$EXEC savior-eval single --est $SAVIOR_WS/results/repro/hall_t1_L3/sens_fix1/run_06/stamped_traj_estimate.txt \
  --gt $SAVIOR_WS/data/warehouse/gt/hall_t1_L3.txt --out $SAVIOR_WS/results/repro/hall_t1_L3/sens_fix1/run_06/eval
```

Compare the ATE with the archived run `results/backend_v2/runs/hall_t1_L3/sens_fix1/run_06/` (extract
`runs_backend_v2.tar.gz`; run `NN` corresponds to the `NN`-th start offset 0.0, 0.2, ..., 1.8 s). The exact argument
lists of the archived runs are printed by `experiments/backend_v2/scripts/bv2_args.py <seq> <method> v2` (run it in the
container at the hard-coded workspace path as in level 2); `savior-run` (`savior_eval`) wraps the same launch file for
repeated trials and result layout.

What to expect, from the studies' own records:

- With `deterministic:=true` (the default of the launch files), repeats of warehouse runs with the same configuration,
  rate and engine were md5-identical in the studies (for example the 80 SAVIOR-edge re-runs in
  `experiments/backend_v2/REPORT.md`, and the empty-mask control equal to OpenVINS in 120 of 120 warehouse t2 runs in
  `experiments/m2b_heldout/REPORT.md`). The segmenter engine is built per GPU and TensorRT version, so on different
  hardware the masks, and hence the trajectory, can differ slightly (the Jetson validation measures a pooled mask IoU of
  0.968 to 0.993 between device and server); compare the ATE, not the md5, unless you use the same hardware and engine.
- VIODE and the real data are not always bit-identical: `m2b_heldout/REPORT.md` records 114 of 120 VIODE control pairs
  within 0.1 mm plus one diverged pair, and `real_world/DEBUG_REPORT.md` records 8 of 21 complete-input pairs
  md5-identical (ATE agreeing to four digits) for the empty-mask control.
