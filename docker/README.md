# SAVIOR Docker environment

One Dockerfile for both targets, selected automatically from the host architecture:

| `uname -m` | `PLATFORM` | Base image | Image tag | Status |
|---|---|---|---|---|
| `x86_64` | `amd64` | `nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04` | `savior:humble-cuda12.8` | tested (RTX PRO 6000 Blackwell) |
| `aarch64` | `arm64` | `nvcr.io/nvidia/l4t-jetpack:r36.4.0` (JetPack 6.1/6.2) | `savior:humble-jp6` | tested (Orin NX 8 GB, L4T R36.4.4 / JetPack 6.2, 2026-10-24) |

Contents (both targets): Ubuntu 22.04, ROS 2 Humble (ros-base, cv_bridge, image_transport,
message_filters, rosbag2 + MCAP, tf2, rviz2, Fast DDS + Cyclone DDS RMWs), colcon, rosdep,
OpenVINS build deps (Eigen 3.4, Ceres 2.0, Boost 1.74, OpenCV 4.5.4 from Ubuntu), and on the
system `python3.10`: PyTorch + torchvision, Ultralytics 8.4.177 (YOLO26), TensorRT 10 python,
ONNX/onnxslim/onnxruntime, rosbags 0.11.7, scipy, matplotlib, pytest 7.4.4. `numpy` is pinned to
1.26.4 because ROS Humble's cv_bridge is built against numpy 1.x; python OpenCV is
`opencv-python-headless` 4.11 (the last line supporting numpy 1.x) next to Ubuntu's C++ OpenCV 4.5.4.

| | amd64 (desktop) | arm64 (Jetson) |
|---|---|---|
| CUDA / cuDNN | 12.8.1 / 9.8 (base, nvcc) + torch's bundled cu128 libs (cuDNN 9.10) | 12.6 / 9.3 (JetPack) |
| PyTorch | 2.9.1+cu128 (download.pytorch.org) | 2.9.1 (jetson-ai-lab `jp6/cu126` index) |
| TensorRT | `tensorrt-cu12` 10.16 pip wheel | 10.3 from JetPack (`python3-libnvinfer`), not pip |
| onnxruntime | `onnxruntime-gpu` 1.23.2 | `onnxruntime` 1.23.2 (CPU, only used by the exporter) |
| extra | Windows-target TRT builder resources removed (-3 GB) | `libopenblas0` + cuDSS 0.6 (needed by the Jetson torch wheel) |
| size | ~24.6 GB unpacked / 13.5 GB compressed | see [Jetson notes](#jetson-orin-nx-jetpack-6) |

Exact versions are pinned in the [`Dockerfile`](Dockerfile) (build args) and
[`requirements.txt`](requirements.txt); the comments there say why.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | stages `base-amd64`/`base-arm64` -> `common` (ROS 2 + OpenVINS deps) -> `ml` (python) -> `dev` (user, entrypoint) |
| `requirements.txt` | python packages shared by both arches |
| `build.sh` | builds the image for this machine's arch and the calling user's uid/gid |
| `run.sh` | starts the long-running dev container `savior-dev` and opens a shell |
| `exec.sh` | runs one command non-interactively (in `savior-dev` if running, else a `--rm` container) |
| `common.sh` | shared settings/`docker run` arguments of the scripts |
| `entrypoint.sh` | sources ROS 2 + the workspace overlay, points caches into the workspace |
| `check_env.py` | environment self-test (`savior-check-env` in the image) |

## Prerequisites

Desktop (x86_64):
- Docker Engine >= 23 with BuildKit (default) — the user must be in the `docker` group.
- NVIDIA driver **>= 570** (CUDA 12.8 / Blackwell `sm_120`; any 570+ driver works for older GPUs too).
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html),
  configured for Docker (`sudo nvidia-ctk runtime configure --runtime=docker`). Check:
  `docker run --rm --gpus all ubuntu nvidia-smi`.
- ~45 GB free disk for the image and build cache (the CUDA devel base alone is ~12 GB unpacked).

Jetson (aarch64): see [Jetson notes](#jetson-orin-nx-jetpack-6).

Nothing is installed on the host itself; everything (builds, tests, python) runs in the container.

## Layout and paths

The scripts assume the repository is checked out inside a colcon workspace:

```
<ws>/                 # SAVIOR_WS — mounted into the container at the SAME absolute path
├── src/savior/       # this repository (docker/ is here)
├── data/             # datasets
├── models/           # SAVIOR_MODELS_DIR: .pt weights, .onnx, TensorRT .engine files
├── results/          # experiment outputs (ultralytics runs go to results/ultralytics)
├── .cache/           # SAVIOR_CACHE_DIR: ultralytics settings (YOLO_CONFIG_DIR), TORCH_HOME, matplotlib
├── build/ install/ log/   # colcon
```

`<ws>` is derived from the script location (`docker/../../..`); override with `SAVIOR_WS=/path`.
Because the path is identical inside and outside the container, paths in configs, logs and
`install/` work in both. The container user has the host user's uid/gid, so files are not
root-owned. No weights or caches are baked into the image; on first start the entrypoint creates
`models/` and `.cache/` and writes an ultralytics `settings.json` with `weights_dir=<ws>/models`,
`runs_dir=<ws>/results/ultralytics`, `datasets_dir=<ws>/data/ultralytics`.

Ultralytics auto-install is disabled in the image (`YOLO_AUTOINSTALL=false`), so it never
pip-installs packages behind your back; add missing packages to the Dockerfile instead.

## Build

```bash
cd <ws>/src/savior/docker
./build.sh                       # arch from `uname -m`, uid/gid from `id`
./build.sh --platform arm64      # override (cross-build needs QEMU binfmt; very slow, prefer building on the Jetson)
SAVIOR_BUILD_NETWORK=default ./build.sh   # Jetson: keep BuildKit's sandbox network (default there is --network host)
./build.sh --tag savior:test -- --build-arg TORCH_VERSION=2.10.0 --build-arg TORCHVISION_VERSION=0.25.0
```

Plain `docker build .` also works (PLATFORM defaults to the BuildKit target arch), but then the
user is uid/gid 1000; pass `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)`.
Rebuilding after editing only `entrypoint.sh`/`check_env.py` reuses all heavy layers.

## Run

```bash
./run.sh                 # start savior-dev (if needed) and open a shell; call again for more shells
./run.sh --devices       # + /dev, udev (RealSense/ZED/serial IMU), privileged
./run.sh --recreate      # fresh container (after rebuilding the image or changing DISPLAY/options)
./run.sh --stop          # remove the container
```

`docker run` options used (see `common.sh`): `--network host` and `--ipc host` (ROS 2 DDS
discovery and shared-memory transport with the host/other containers; `--ipc host` also means
`/dev/shm` is the host's, so no `--shm-size` is needed — set `SAVIOR_IPC=private` to use a
private `/dev/shm` of `SAVIOR_SHM_SIZE`, default 8g), workspace bind mount, GPU (`--gpus all` on
amd64), X11 when `DISPLAY` is set, and `ROS_DOMAIN_ID`/`RMW_IMPLEMENTATION`/... passed through.
Extra arguments: `SAVIOR_DOCKER_ARGS="-v /mnt/nas:/mnt/nas" ./run.sh --recreate`.

## Exec (non-interactive)

```bash
./exec.sh colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
./exec.sh colcon test && ./exec.sh colcon test-result --verbose
./exec.sh bash -c 'ros2 bag info data/uhumans2/ros2/office_00h'
./exec.sh rosbags-convert --src data/uhumans2/office.bag --dst data/uhumans2/ros2/office
```

The command runs with ROS 2 and (if built) `<ws>/install/setup.bash` sourced, in the caller's
current directory if that is inside the workspace (else `<ws>`), and its exit code is returned.

## Building the workspace

```bash
./exec.sh rosdep install --from-paths src --ignore-src -y -r   # usually nothing to do
./exec.sh colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

New shells (`./run.sh`, `./exec.sh`) source `install/setup.bash` automatically; in an already
open shell run `source install/setup.bash` after the first build.

## Sanity checks

```bash
./exec.sh savior-check-env                  # PASS/FAIL per item, exit code 1 on failure
./exec.sh savior-check-env --yolo yolo26n-seg   # + YOLO26n-seg -> FP16 TensorRT engine, latency
./exec.sh nvidia-smi
./exec.sh python3 -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.get_arch_list())"
```

Manual TensorRT export (weights are downloaded into the current directory, so run it in `models/`):

```bash
cd <ws>/models && ../src/savior/docker/exec.sh yolo export model=yolo26n-seg.pt format=engine quantize=16
../src/savior/docker/exec.sh yolo predict model=yolo26n-seg.engine \
    source=/usr/local/lib/python3.10/dist-packages/ultralytics/assets/bus.jpg project=$PWD/predict
```

`quantize=16` is FP16; ultralytics 8.4 still accepts the older `half=True` with a deprecation
warning. Reference on the RTX PRO 6000 Blackwell (TensorRT 10.16, imgsz 640, `bus.jpg`):
engine build ~16 s, TensorRT inference ~0.5 ms, full `predict()` incl. pre/post-processing
~1.7 ms (`savior-check-env --yolo yolo26n-seg`).

TensorRT engines are specific to the GPU and TensorRT version: build them on the machine that runs
them (desktop engines do not run on the Jetson and vice versa). `savior-check-env --yolo` caches
the engine in `<ws>/models`; delete the `.engine` file to force a rebuild.

## X11 / rviz2

If `DISPLAY` is set when the container is created, the X11 socket, `XAUTHORITY` cookie and
`/dev/dri` are passed in, so `rviz2` just works (on Wayland via XWayland). If the X server
refuses the connection, allow local clients once per login with `xhost +si:localuser:$USER`
on the host. Without `DISPLAY` nothing is mounted and everything else works headless.

## Jetson Orin NX (JetPack 6)

**Status: built and run on an Orin NX 8 GB** (L4T R36.4.4 / JetPack 6.2, Docker 29.4, MAXN) on 2026-10-24: image build
~10 min on the device (base image pulled once), `savior-check-env` image items all PASS (torch 2.9.1 + CUDA 12.6 on `sm_87`,
TensorRT 10.3 engine build, cv_bridge + cv2 4.11 + ultralytics in one interpreter, OpenVINS deps with Ubuntu OpenCV
4.5.4), the colcon workspaces (OpenVINS fork, Python node, C++ node `savior_perception_cpp`) build in the image, and the
FP16 engines are exported on the device. Validation results: `results/jetson_validation/REPORT.md`.

- Requires JetPack 6.x (L4T r36.x) on the device, Docker and the NVIDIA Container Toolkit (part
  of JetPack). Build on the Jetson itself: `./build.sh` picks `PLATFORM=arm64` and the
  `l4t-jetpack:r36.4.0` base (works on an R36.4.4 BSP). If your BSP is another r36 release, pass
  `-- --build-arg BASE_IMAGE_ARM64=nvcr.io/nvidia/l4t-jetpack:r36.x.y`. Building on the device is faster and more
  reliable than a QEMU cross-build (the build is download-bound; nothing is compiled from source in the image).
- **Build network (fixed 2026-10-24):** on the Jetson, BuildKit's per-step sandbox network fails in the first `RUN`
  (`... Perhaps iptables or your kernel needs to be upgraded`, exit 3): the L4T kernel lacks netfilter / bridge
  features it needs. `build.sh` therefore passes `--network host` to `docker build` for a native arm64 build on an
  aarch64 host (`SAVIOR_BUILD_NETWORK=<mode>` overrides, `default` restores BuildKit's default; x86 is unchanged).
  With plain `docker build`, add `--network host` yourself.
- GPU access: `run.sh` uses CDI (`--device nvidia.com/gpu=all`) if a CDI spec of kind `nvidia.com/gpu` exists in
  `/etc/cdi` or `/var/run/cdi`, else `--runtime nvidia`; force with `SAVIOR_GPU=cdi|runtime`. (Fixed 2026-10-24: the
  check used to accept any `/etc/cdi/nvidia*.yaml`, but a stock JetPack 6.2 install has only `/etc/cdi/nvidia-pva.yaml`
  (kind `nvidia.com/pva`, no GPU), so auto mode picked CDI and failed; `--runtime nvidia` works out of the box.) `tegrastats` and the `jtop` socket are mounted when present. The container user is in the `video`/`render` groups.
- The base image ships NVIDIA's OpenCV 4.8 under Ubuntu's package names; the Dockerfile removes it
  and blocks it via apt pinning because ROS Humble's cv_bridge needs Ubuntu's OpenCV 4.5.4 (verified: apt resolves ROS
  Humble cleanly after the purge; C++ code in the workspace links Ubuntu's 4.5.4, the same as on the desktop).
- TensorRT 10.3 comes from JetPack (`python3-libnvinfer`); it is not pip-installed. PyTorch comes
  from NVIDIA's Jetson wheels (`https://pypi.jetson-ai-lab.io/jp6/cu126`); that wheel links
  `libcudss.so.0` and `libopenblas.so.0`, which are not in the base image, so the Dockerfile adds
  cuDSS 0.6 (Jetson redistributable, sha256-checked) and `libopenblas0`. The GPU driver libraries
  are only mounted at `docker run`, so the build-time import test is non-fatal on arm64; run
  `./exec.sh savior-check-env` on the device to validate.
- **C++ node** (`savior_perception_cpp`, TensorRT C++ API): JetPack keeps the TensorRT headers / libs in the system
  directories and nvcc in `/usr/local/cuda/bin`, so build with
  `--cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=87 -DTENSORRT_ROOT=/usr`
  (`TENSORRT_ROOT` only produces a harmless "unused variable" CMake warning). It links `libnvinfer.so.10` (10.3),
  `libcudart.so.12` (12.6) and Ubuntu OpenCV 4.5.4.
- **Engines** are GPU + TensorRT-version specific: export them on the device (Ultralytics
  `format=engine half=True imgsz=(384,672) opset=17`, ~400 s each for YOLO26s / YOLO26n-seg on the Orin NX with
  `workspace=2`), never copy desktop engines.
- `savior-check-env`'s "workspace mount" item fails if `YOLO_CONFIG_DIR` points outside the mounted workspace (as the
  Jetson validation package does on purpose); that is a check of the run setup, not of the image.
- Orin NX 8 GB memory tips:
  - Deploy with the **TensorRT engine only**; do not import PyTorch in the runtime node (torch +
    CUDA context alone costs ~1-2 GB of the shared 8 GB). Use PyTorch only for export.
  - Build engines **on the device** (`yolo export ... format=engine half=True device=0`), with a
    small builder workspace (`workspace=1`-`2` GB) and nothing else running; consider adding swap
    for the build step only.
  - `sudo nvpmodel -m 0 && sudo jetson_clocks` for timing runs; record `tegrastats` (`VDD_IN` = board input power).
  - Disable the desktop (`sudo systemctl set-default multi-user.target`) to free ~0.8 GB.

## Troubleshooting

- **`could not select device driver "" with capabilities: [[gpu]]`** — NVIDIA Container
  Toolkit missing or not configured for Docker: `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.
  Alternatively use CDI: `SAVIOR_GPU=cdi ./run.sh --recreate` (needs `nvidia-ctk cdi generate`).
- **`no kernel image is available for execution on the device`** — the torch build lacks your
  GPU's arch; check `torch.cuda.get_arch_list()` (cu128 wheels include `sm_120`).
- **Files in the workspace owned by the wrong user** — the image was built for another uid/gid
  (`run.sh` warns); rebuild with `./build.sh` as your user.
- **`numpy.core.multiarray failed to import` / cv_bridge errors** — something installed numpy 2;
  numpy must stay 1.26.x (`pip list | grep numpy`).
- **rviz2: `could not connect to display`** — see X11 above; recreate the container after
  `DISPLAY` changed (`./run.sh --recreate`).
- **ROS 2 nodes on host and container do not see each other** — same `ROS_DOMAIN_ID` and RMW on
  both sides; host networking + `--ipc host` are required for the shared-memory transport.
- **Stale container after rebuild** — `./run.sh --recreate`.
- **pytest errors (`No module named _pytest.scope`, launch_testing plugin failures)** — the image
  pins pytest 7.4.4 on purpose: Ubuntu's 6.2.5 is too old, pytest >= 8 breaks ROS Humble's
  launch_testing plugin (workaround there: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`).
- **Why no compose.yaml?** The `docker run` arguments depend on the architecture and host state
  (GPU mode, X11, Jetson tools); `common.sh` computes them, the scripts are the supported entry.
