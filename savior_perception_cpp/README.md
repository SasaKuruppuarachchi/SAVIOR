# savior_perception_cpp

C++ port of the SAVIOR perception hot path (`savior_perception` `savior_node`, Python) for edge deployment
(Jetson Orin NX 8 GB). Same algorithms, parameters, topics and mask contract; the Python node stays the reference.

* `savior_core` (no ROS): calibration / rectification maps, ROI SGBM stereo depth, promotion gate (fixed / adaptive
  threshold, median / contact link, P7 selective branch with co-motion gate), motion evidence (gyro integration, KLT,
  robust ego-motion fit, instantaneous GLS test, short / long windowed anchor test, log-odds tracks, duplicate handling),
  P7 selective policy (provisional static, revocation, history-static, convergence gate, off-delay hysteresis), mask
  tracker (ego-motion carry, chain hysteresis), depth-band extension (192), left compose + right boundary warp.
* `savior_yolo`: YOLO26-seg through the TensorRT C++ API from the **same Ultralytics `.engine` files**, with the
  Ultralytics 8.4 pre/post-processing re-implemented (letterbox, `x * (1/255)`, class-offset NMS with stable score order,
  `scale_boxes`, `process_mask_native` with PyTorch's bilinear kernel, `crop_mask`, empty-mask drop, integer box crops) and
  the mask stage on the GPU (only the box crops are copied back).
* `savior_node_component` (`savior_perception_cpp::SaviorNode`, rclcpp component) + executable `savior_node_cpp`.
  Node name `savior_node`, every parameter of `savior_perception/params.py` + `config/default.yaml`
  (`<section>.<field>`, same coercion rules), same topics, `/savior/stats` JSON with the same keys.
  Mask contract (docs/INTERFACE.md 3.1): `mono8`, raw size, 0 / 192 / 255, `header.stamp` = left image stamp for
  both masks, RELIABLE KEEP_LAST 10, one mask pair per exact-time stereo pair (zeros on failure), gyro wait logic of the
  Python node (deterministic replay). Masks / stats are published as `unique_ptr`: zero-copy intra-process delivery
  when composed with OpenVINS (`savior_ov_component`, launch `perception_impl:=cpp_composed`).
* Segmenter backends: `yolo` (TensorRT `.engine`) and `none`. The oracle backends stay Python-only.
* `src/fillpoly411.cpp`: OpenCV 4.11's polygon fill (Apache-2.0), so the right-mask warp is bit-identical to the Python
  node (cv2 4.11) with any linked OpenCV (OpenCV <= 4.9 clips border-crossing polygons differently).

## Build (desktop, Docker)

The host is not used directly: build inside the project image derived with the C++ build/test deps
(`docker/Dockerfile.dev`: TensorRT 10.16 headers for the runtime shipped with the image's tensorrt wheel, pybind11,
OpenCV 4.11.0 in `/opt/opencv-4.11` for the matched-OpenCV equivalence build):

```bash
docker build -t savior-cpp:humble-cuda12.8 -f docker/Dockerfile.dev docker/
# colcon overlay on top of the workspace install (OpenVINS fork for savior_ov_component)
docker run --rm -v $WS:$WS -w $WS savior-cpp:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; \
  source install/setup.bash; colcon build --packages-select savior_perception_cpp savior_ov_component savior_bringup \
  --cmake-args -DCMAKE_BUILD_TYPE=Release [-DSAVIOR_BUILD_PYTHON=ON] [-DSAVIOR_OPENCV_DIR=/opt/opencv-4.11/lib/cmake/opencv4]"
```

CMake options: `SAVIOR_WITH_TRT` (ON; off automatically without `NvInfer.h`), `SAVIOR_BUILD_ROS` (ON),
`SAVIOR_BUILD_PYTHON` (OFF; pybind11 module `savior_cpp` for the harness), `SAVIOR_OPENCV_DIR`, `TENSORRT_ROOT`,
`CMAKE_CUDA_ARCHITECTURES` (default `86;89;120` on x86_64, `87` on aarch64). The C++ core is compiled with
`-ffp-contract=off` (same results on x86_64 and aarch64).

## Build (Jetson Orin, JetPack 6.1 / 6.2, L4T r36.4, arm64)

`docker/Dockerfile.jetson` (build on the device): L4T JetPack base (CUDA 12.6, TensorRT 10.3, OpenCV 4.8.0) + ROS 2
Humble arm64 apt packages, `colcon build --packages-up-to savior_perception_cpp savior_bringup ov_msckf savior_ov_component`
with `-DCMAKE_CUDA_ARCHITECTURES=87 -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DTENSORRT_ROOT=/usr` (TensorRT
headers / libs in `/usr/include|lib/aarch64-linux-gnu`). Native build without Docker: the same colcon line in a sourced
Humble workspace. Validated natively on a Jetson Orin NX 8 GB (JetPack 6.2, `savior:humble-jp6`; see `experiments/jetson_validation/REPORT.md`). Before that, on x86_64 stand-ins, the code was shown to compile
against the TensorRT 10.3 headers for `sm_87` (`docker/Dockerfile.jpcheck`) and gives bit-identical results with
OpenCV 4.8.0 built without IPP (the JetPack OpenCV version). Engines are GPU / TensorRT-version specific: rebuild on
the device from the ONNX and add the Ultralytics metadata header (class names, input size):

```bash
/usr/src/tensorrt/bin/trtexec --onnx=models/warehouse/yolo26n-seg-warehouse.onnx --fp16 --saveEngine=/tmp/raw.engine
python3 tools/add_engine_metadata.py config/engines/yolo26n-seg-warehouse.meta.json /tmp/raw.engine \
    models/warehouse/yolo26n-seg-warehouse.orin.engine
```

For one-process composition build `savior_perception_cpp` against the same OpenCV as OpenVINS / cv_bridge.

## Run

```bash
ros2 run savior_perception_cpp savior_node_cpp --ros-args --params-file <params.yaml> -p ...        # standalone
ros2 launch savior_bringup savior.launch.py ... perception_impl:=cpp            # instead of the Python savior_node
ros2 launch savior_bringup savior.launch.py ... perception_impl:=cpp_composed   # + ov_msckf in one container (intra-process)
```

`perception_impl` (`savior_bringup`): `python` (default, unchanged) | `cpp` | `cpp_composed`.

## Equivalence and parity (t1 tuning set only)

* `tools/equiv_offline.py`: identical inputs (raw frames + gyro of the t1 bags, cached YOLO detections) to the Python
  `SaviorPipeline` and to the C++ pipeline (pybind11), each with its own state over the whole sequence; per stage
  (depth, motion state, gating status / links, tracker, masks, counters) and per-stage timing.
* `tools/equiv_yolo.py`: C++ TensorRT segmenter vs Ultralytics on every t1 frame (same engine).
* `tools/cv_version_diff.py`, `tools/test_fillpoly.py`: OpenCV primitives of the pipeline, C++ build vs cv2.
* `tools/equiv_tables.py`: tables (results/cpp_port/tables/equivalence.md).

Results (results/cpp_port/tables):

* offline (equivalence.md): bit-identical to the Python node on all 8 t1 sequences (17 736 frames: every left and right
  mask pixel, every instance disparity, status, parent link, track id and motion / selective state) for SAVIOR main
  (sens_fix1), SAVIOR-adaptive (p7_nb) and SAVIOR-edge (YOLO26n detections), linked with OpenCV 4.11.0, 4.8.0 (no IPP)
  or 4.5.4; the TensorRT segmenter reproduces Ultralytics exactly (2.3 M detections over the t1 frames, s and n engines:
  same classes, boxes, scores and masks).
* the only OpenCV-version-dependent primitive of the pipeline is the polygon fill (opencv_versions.md); without the
  vendored 4.11 fill, OpenCV 4.5.4 / 4.8.0 change 1295 right-mask pixels in 17 736 frames (decisions unchanged).
* closed loop (ate_closed_loop*.md; 8 sequences x 10 offsets, rate 0.5, deterministic OpenVINS, frozen run protocol):
  SAVIOR main C++ 80 / 80 trajectories md5-identical to the frozen Python main, SAVIOR-edge C++ 80 / 80 md5-identical to
  the Python edge reference (e_c_n672_L250dfronly), the pre-vendoring build (cpp_main) 65 / 80 identical and
  +0.00 % geometric-mean ATE (Wilcoxon p = 0.39); one-process composition (intra-process masks) md5-identical as well.
* timing: timing_stages.md (per stage, Python vs C++), timing*.md (online node), orin_estimate.md (Orin NX 8 GB estimate).

## Layout

```
include/savior_cpp/*.hpp  src/*.cpp  cuda/yolo_kernels.cu   core, segmenter, node
python/bindings.cpp (+ cvops.inc)                             pybind11 module savior_cpp (harness only)
tools/                                                        equivalence / timing / engine tools
docker/Dockerfile.dev | Dockerfile.jpcheck | Dockerfile.jetson
config/roles_default.yaml  config/engines/*.meta.json
```
