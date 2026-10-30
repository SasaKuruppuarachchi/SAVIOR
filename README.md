# SAVIOR

SAVIOR is a semantic front-end for stereo-inertial visual-inertial odometry (VIO). From a segmenter's class prior, stereo
depth, an association tree over touching instances and IMU-compensated motion evidence, it makes a per-instance,
conservative decision about which objects are dynamic outliers, and writes the decision as an image mask. It acts on an
unmodified estimator only through these masks: the masks gate feature tracking in OpenVINS (a fork in this repository),
and an empty mask gives bit-identical behaviour to upstream OpenVINS. The same masks are also used with VINS-Fusion and
DynaVINS (see [`sota/`](sota/README.md)).

The paper is under review. This repository is the code, the frozen configurations and the evaluation artefact that go
with it. Platform: ROS 2 Humble, OpenVINS back-end, Docker.

## Repository layout

| path | content |
|---|---|
| [`docker/`](docker/README.md) | Docker environment for desktop (amd64, CUDA 12.8) and Jetson (arm64, JetPack 6) |
| [`open_vins/`](open_vins/SAVIOR_FORK.md) | OpenVINS fork (GPL-3.0) with dynamic-mask gating |
| [`savior_perception/`](savior_perception/README.md) | Python SAVIOR node and its pure-Python core, with tests |
| [`savior_perception_cpp/`](savior_perception_cpp/README.md) | C++ / TensorRT port of the node (real time on a Jetson Orin NX) |
| `savior_ov_component/` | OpenVINS as a composable component (one-process composition with the C++ node) |
| `savior_bringup/` | launch files (`savior.launch.py`, `baseline.launch.py`), dataset configs, class-role files, dataset preparation tools |
| `savior_eval/` | experiment runner `savior-run` and evaluation `savior-eval` (rpg_trajectory_evaluation port, MIT), with tests |
| [`savior_datasets/warehouse/`](savior_datasets/warehouse/README.md) | Isaac Sim generator of the SAVIOR-Warehouse dataset, segmenter training kit |
| [`sota/`](sota/README.md) | VINS-Fusion, DynaVINS (and ORB-SLAM3) baselines in a ROS 1 Docker image, plus the mask patches |
| [`experiments/`](experiments/README.md) | frozen per-study scripts, configurations, freeze files and reports, archived as run |
| [`docs/`](docs/INTERFACE.md) | [`INTERFACE.md`](docs/INTERFACE.md) (system overview and interface contract), [`DATA.md`](docs/DATA.md) (datasets and validation), [`FIGURE_STYLE.md`](docs/FIGURE_STYLE.md) |

## Requirements

- Linux with an NVIDIA GPU, a driver that supports CUDA 12.8 (570 or newer), Docker and the NVIDIA container toolkit.
  About 45 GB of disk for the image and build cache.
- For the embedded target: Jetson Orin (NX 8 GB tested) with JetPack 6; see [`docker/README.md`](docker/README.md) and
  [`savior_perception_cpp/README.md`](savior_perception_cpp/README.md).

Everything runs inside Docker; nothing is installed on the host.

## Build

The repository must be checked out as `src/savior` of a colcon workspace (`SAVIOR_WS`); the scripts derive the
workspace from their own location, or you can set `SAVIOR_WS`.

```bash
mkdir -p ~/savior_ws/src && cd ~/savior_ws/src
git clone https://github.com/SasaKuruppuarachchi/SAVIOR.git savior
export SAVIOR_WS=~/savior_ws

# 1. image (savior:humble-cuda12.8 on amd64, savior:humble-jp6 on arm64)
$SAVIOR_WS/src/savior/docker/build.sh

# 2. workspace, inside the container (the C++ node needs TensorRT headers: see savior_perception_cpp/README.md)
cd $SAVIOR_WS/src/savior/docker
./exec.sh colcon build --symlink-install --packages-skip savior_perception_cpp --cmake-args -DCMAKE_BUILD_TYPE=Release
./exec.sh colcon test --packages-select savior_perception savior_eval    # optional; or ./exec.sh pytest src/savior/savior_perception/test
```

`./run.sh` opens an interactive shell in the same container; new shells source `install/setup.bash` automatically.
For the C++ node, build the extra image and the package as described in
[`savior_perception_cpp/README.md`](savior_perception_cpp/README.md).

## Segmenter weights

Weights and TensorRT engines are not in git (`*.pt`, `*.onnx`, `*.engine` are ignored). Put them in `$SAVIOR_WS/models/`.

- **COCO-pretrained YOLO26-seg** (for VIODE, OpenLORIS, uHumans2, Monado): downloaded from Ultralytics and exported to a
  TensorRT FP16 engine inside the container. The archived studies used
  `YOLO('yolo26s-seg.pt').export(format='engine', imgsz=640, half=True, batch=1, simplify=True, device=0)`:

  ```bash
  cd $SAVIOR_WS/models && ../src/savior/docker/exec.sh yolo export model=yolo26s-seg.pt format=engine imgsz=640 half=True batch=1 simplify=True
  ```

- **SAVIOR-Warehouse segmenter** (`yolo26s-seg-warehouse`, `yolo26n-seg-warehouse`): the fine-tuned `.pt` and `.onnx` are in
  the Zenodo record ([`docs/DATA.md`](docs/DATA.md), archive `models_warehouse.tar.gz`; extracts to `models/warehouse/`).
  Build the engine for your GPU with
  `python3 savior_datasets/warehouse/train/export.py --weights models/warehouse/yolo26s-seg-warehouse.pt`
  (static input 384x672, FP16). Training kit and settings: [`savior_datasets/warehouse/train/`](savior_datasets/warehouse/train/README.md).
- **Jetson**: engines are specific to the GPU and TensorRT version, so build them on the device
  (`yolo export ... format=engine half=True`, or `trtexec` plus `tools/add_engine_metadata.py`); see
  [`savior_perception_cpp/README.md`](savior_perception_cpp/README.md) and [`docker/README.md`](docker/README.md).

The model path in `savior_bringup/config/warehouse/savior_perception_yolo.yaml` is the authors' absolute path; always
pass `model:=$SAVIOR_WS/models/warehouse/yolo26s-seg-warehouse.engine` to the launch file (the launch argument overrides
the YAML value).

## Quick start

SAVIOR with OpenVINS on a ROS 2 bag (`config:=` is a directory name in `savior_bringup/config/` or the path of an
`estimator_config.yaml`; `bag:=` a bag directory; `output:=` receives the estimated trajectory in TUM format):

```bash
cd $SAVIOR_WS/src/savior/docker
./exec.sh ros2 launch savior_bringup savior.launch.py \
    config:=viode bag:=$SAVIOR_WS/data/viode/ros2/parking_lot_high \
    output:=$SAVIOR_WS/results/demo/savior/run_01/stamped_traj_estimate.txt \
    backend:=yolo model:=$SAVIOR_WS/models/yolo26s-seg.engine \
    roles_file:=$SAVIOR_WS/src/savior/savior_bringup/config/roles/viode_vehicles_potential.yaml rate:=0.5
```

Arguments of `savior.launch.py` (see the docstring of the file): `config`, `bag`, `output`, `dataset`, `topics`, `rate`,
`start_offset`, `deterministic`, `feature_stats`, `ov_set`, `perception_params`, `roles_file`, `backend`
(`yolo | oracle_colormap | none`), `model`, `mask_policy` (`wait | latest`), `mask_timeout_ms`, `pset`
(`"gating.mode=fixed gating.fixed_threshold_m=1.0"`: savior_node overrides), `stats_file`, `perception_impl`
(`python | cpp | cpp_composed`). Use a bag rate below 1 for offline runs (`rate:=0.5`), so the node keeps up.

Baseline (stock OpenVINS path of the same fork, no masks):

```bash
./exec.sh ros2 launch savior_bringup baseline.launch.py config:=viode \
    bag:=$SAVIOR_WS/data/viode/ros2/parking_lot_high \
    output:=$SAVIOR_WS/results/demo/openvins/run_01/stamped_traj_estimate.txt rate:=0.5
```

Evaluation against ground truth (TUM files), single run or Monte-Carlo over `run_XX` directories, and comparison tables:

```bash
./exec.sh savior-eval single --est results/demo/savior/run_01/stamped_traj_estimate.txt \
    --gt data/viode/gt/parking_lot_high.txt --out results/demo/savior/run_01/eval
./exec.sh savior-eval multi --runs results/demo/savior --gt data/viode/gt/parking_lot_high.txt
./exec.sh savior-eval compare --help
```

`savior-run` runs repeated trials of a launch file and writes the layout `results/<dataset>/<seq>/<method>/run_XX/`;
`savior-eval runstats` summarises mask synchronisation, feature statistics and timing per run.

## Datasets

- **SAVIOR-Warehouse** (the synthetic stereo-inertial dataset generated for this work): ROS 2 bags, ground truth and
  metadata on Zenodo, DOI [10.5281/zenodo.23803392](https://doi.org/10.5281/zenodo.23803392); the confirmatory split is in
  two further records. Extraction layout and validation: [`docs/DATA.md`](docs/DATA.md). The generator is in
  [`savior_datasets/warehouse/`](savior_datasets/warehouse/README.md).
- **Third-party datasets** (VIODE, OpenLORIS-Scene, uHumans2, Monado SLAM dataset) are not re-hosted. Download them from
  their authors and convert them with `savior_bringup/tools/prepare_datasets.sh` (uHumans2, OpenLORIS) and the
  `viode_prepare.py` / `monado_prepare.py` tools; sources, sequences and commands are in [`docs/DATA.md`](docs/DATA.md).

## C++ node and Jetson

The C++ / TensorRT node reproduces the Python node (masks bit-identical in the equivalence study) and is the one that
meets the real-time criterion on a Jetson Orin NX 8 GB. Select it with `perception_impl:=cpp` (or `cpp_composed` for
one-process composition with OpenVINS). Build instructions for desktop and Jetson, engine building and the equivalence
tools: [`savior_perception_cpp/README.md`](savior_perception_cpp/README.md); Jetson image and notes:
[`docker/README.md`](docker/README.md). The on-device study is in
[`experiments/jetson_validation/`](experiments/jetson_validation/REPORT.md).

## Baselines

VINS-Fusion, DynaVINS and ORB-SLAM3 run in a ROS 1 Docker image, with patches that let VINS-Fusion and DynaVINS take the
SAVIOR masks: [`sota/README.md`](sota/README.md).

## Key configuration

- **Mask contract** (`/savior/mask/left`, `/savior/mask/right`, `mono8`, raw image size, stamp of the left image):
  `0` keep, `192` extension band (relaxable), `255` dynamic core (never relaxed). OpenVINS needs
  `downsample_cameras: false` with masks. Full contract and all OpenVINS-fork keys: [`docs/INTERFACE.md`](docs/INTERFACE.md).
- **`use_dynamic_mask`** (key of the OpenVINS `estimator_config.yaml`): `false` (default) is bit-identical to upstream;
  the SAVIOR launch sets it to `true` and the topics to `/savior/mask/left|right`. The dataset estimator configs are
  shared between baseline and SAVIOR.
- **Class roles**: `savior_bringup/config/roles/*.yaml` map the segmenter's class names to `dynamic`, `potential`,
  `static` or `ignore` (`coco_indoor.yaml`, `person_only.yaml`, `viode_vehicles_potential.yaml`, `warehouse.yaml`, ...).
- **Interaction gate**: the paper's SAVIOR uses the fixed depth gate `d_int = 1 m` (`gating.mode=fixed
  gating.fixed_threshold_m=1.0`). The built-in default of `savior_perception/config/default.yaml` is the adaptive gate; the
  full parameter set of the main method (`sens_fix1`) is in `experiments/p7/final_config.yaml` and, for the re-tuned
  back-end, `experiments/backend_v2/`. Pass overrides with `pset:="key=value ..."`.
- **Ablations**: `gating.enable=false` (no association tree), `extension.enable=false tracker.enable=false`,
  `depth.enable=false` (no stereo); see [`docs/INTERFACE.md`](docs/INTERFACE.md) section 3.3.

## Reproducing the paper

[`experiments/README.md`](experiments/README.md) maps every study folder to the part of the paper or supplement that it
supports and explains how to verify the freeze files. The scripts there are archived exactly as run (with the authors'
absolute paths); raw outputs, trajectories and datasets are in the Zenodo record. [`docs/DATA.md`](docs/DATA.md) describes
three levels of validation: integrity checks, re-analysis of the released run outputs, and re-running a sequence.

## Licence

GPL-3.0 (see [`LICENSE`](LICENSE)): the OpenVINS fork and the VINS-Fusion / DynaVINS patches are GPL-3.0, so the
repository is released under the same licence. `savior_eval` includes a port of rpg_trajectory_evaluation (MIT; see its
sources). Segmenter weights fine-tuned from Ultralytics YOLO fall under AGPL-3.0; they are not part of this repository
and are distributed separately (Zenodo). Third-party datasets keep their own licences.

## Citation

The paper is under review. Until it is published, please cite the software record (see also
[`CITATION.cff`](CITATION.cff)):

```bibtex
@software{savior_code,
  title        = {{SAVIOR}: code, frozen configurations and evaluation artefact},
  author       = {Kuruppu Arachchige, Sasanka and Lee, Kyuman},
  version      = {1.0.0},
  year         = {2026},
  month        = oct,
  doi          = {10.5281/zenodo.23803392},
  url          = {https://github.com/SasaKuruppuarachchi/SAVIOR},
  license      = {GPL-3.0-or-later},
  note         = {Paper under review}
}
```
