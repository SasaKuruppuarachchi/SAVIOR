#!/usr/bin/env python3
"""SAVIOR container sanity check: prints PASS/FAIL/WARN per item, exit code 1 on any FAIL.

Installed in the image as `savior-check-env`. Run inside the container:

    savior-check-env                       # environment checks (~30 s, builds a tiny TRT engine)
    savior-check-env --yolo yolo26n-seg    # + export <model>.pt -> FP16 TensorRT engine and time it

The --yolo step downloads weights into $SAVIOR_MODELS_DIR (workspace) and caches the engine there.
"""

import argparse
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

RESULTS = []


def report(status, name, detail=""):
    RESULTS.append(status)
    print(f"[{status:4}] {name}" + (f": {detail}" if detail else ""), flush=True)


def check(name, warn_only=False):
    """Decorator: run fn, PASS with its returned detail string, FAIL (or WARN) on exception."""

    def wrap(fn):
        try:
            detail = fn()
            report("PASS", name, detail or "")
        except Exception as exc:  # noqa: BLE001
            report("WARN" if warn_only else "FAIL", name, f"{type(exc).__name__}: {exc}")
            if os.environ.get("SAVIOR_CHECK_VERBOSE"):
                traceback.print_exc()
        return fn

    return wrap


def run(cmd, timeout=120):
    proc = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"`{cmd}` exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[-400:]}")
    return proc.stdout


IS_JETSON = platform.machine() == "aarch64"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yolo", metavar="MODEL", help="also export MODEL (e.g. yolo26n-seg) to an FP16 TRT engine and benchmark it")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--iters", type=int, default=200, help="timed iterations for --yolo")
    args = ap.parse_args()

    print(f"== SAVIOR environment check ({platform.machine()}, python {platform.python_version()})")

    # ---------------------------------------------------------------- GPU / driver
    @check("nvidia driver", warn_only=IS_JETSON)
    def _():
        if IS_JETSON and not shutil.which("nvidia-smi"):
            with open("/etc/nv_tegra_release") as f:
                return f.readline().strip()
        out = run("nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader")
        return out.strip().replace("\n", " | ")

    # ---------------------------------------------------------------- python stack
    @check("numpy < 2 (cv_bridge ABI)")
    def _():
        import numpy

        assert numpy.__version__.startswith("1."), f"numpy {numpy.__version__}"
        return numpy.__version__

    @check("torch CUDA")
    def _():
        import torch

        assert torch.cuda.is_available(), "torch.cuda.is_available() is False"
        major, minor = torch.cuda.get_device_capability(0)
        archs = torch.cuda.get_arch_list()
        sm = f"sm_{major}{minor}"
        # Exact SASS match, or PTX (compute_XY) that the driver can JIT for this GPU.
        ptx_ok = any(a.startswith("compute_") and int(a.split("_")[1]) <= major * 10 + minor for a in archs)
        assert sm in archs or ptx_ok, f"{sm} not in {archs}"
        a = torch.randn(2048, 2048, device="cuda")
        b = torch.randn(2048, 2048, device="cuda")
        c = (a @ b).cpu()
        ref = a.cpu() @ b.cpu()
        err = (c - ref).abs().max().item() / ref.abs().max().item()
        assert err < 1e-2, f"matmul rel err {err}"
        return (f"torch {torch.__version__}, CUDA {torch.version.cuda}, cuDNN {torch.backends.cudnn.version()}, "
                f"{torch.cuda.get_device_name(0)} ({sm}), archs={','.join(archs)}, matmul rel.err {err:.1e}")

    @check("torchvision CUDA ops")
    def _():
        import torch
        import torchvision

        boxes = torch.tensor([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=torch.float, device="cuda")
        keep = torchvision.ops.nms(boxes, torch.tensor([0.9, 0.8, 0.7], device="cuda"), 0.5)
        assert keep.tolist() == [0, 2], keep
        return torchvision.__version__

    @check("cv2 + cv_bridge + torch + ultralytics in one interpreter")
    def _():
        import cv2
        import numpy as np
        import torch  # noqa: F401
        import ultralytics
        from cv_bridge import CvBridge

        img = np.random.randint(0, 255, (48, 64, 3), dtype=np.uint8)
        br = CvBridge()
        msg = br.cv2_to_imgmsg(img, encoding="bgr8")
        back = br.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        assert (back == img).all()
        mono = br.cv2_to_imgmsg(np.full((48, 64), 255, np.uint8), encoding="mono8")
        assert mono.encoding == "mono8"
        _, buf = cv2.imencode(".png", img)
        return f"cv2 {cv2.__version__} ({os.path.dirname(cv2.__file__)}), ultralytics {ultralytics.__version__}"

    @check("TensorRT engine build")
    def _():
        import numpy as np
        import tensorrt as trt

        logger = trt.Logger(trt.Logger.ERROR)
        builder = trt.Builder(logger)
        network = builder.create_network(0)
        inp = network.add_input("x", trt.float32, (1, 3, 8, 8))
        w = np.ones((4, 3, 1, 1), np.float32)
        conv = network.add_convolution_nd(inp, 4, (1, 1), trt.Weights(w), trt.Weights(np.zeros(4, np.float32)))
        network.mark_output(conv.get_output(0))
        config = builder.create_builder_config()
        config.set_flag(trt.BuilderFlag.FP16)
        plan = builder.build_serialized_network(network, config)
        assert plan is not None, "build_serialized_network returned None"
        engine = trt.Runtime(logger).deserialize_cuda_engine(plan)
        assert engine is not None
        return f"TensorRT {trt.__version__}, plan {plan.nbytes} bytes"

    @check("onnx / onnxslim / onnxruntime")
    def _():
        import onnx
        import onnxruntime
        import onnxslim

        return (f"onnx {onnx.__version__}, onnxslim {onnxslim.__version__}, onnxruntime {onnxruntime.__version__} "
                f"{onnxruntime.get_available_providers()}")

    @check("scipy / matplotlib / yaml / pytest / rosbags")
    def _():
        import matplotlib
        import pytest
        import rosbags  # noqa: F401
        import scipy
        import yaml

        return (f"scipy {scipy.__version__}, matplotlib {matplotlib.__version__}, pyyaml {yaml.__version__}, "
                f"pytest {pytest.__version__}, rosbags {importlib.metadata.version('rosbags')}")

    # ---------------------------------------------------------------- ROS
    @check("ros2 CLI + required packages")
    def _():
        run("ros2 --help")
        pkgs = set(run("ros2 pkg list").split())
        need = ["cv_bridge", "image_transport", "message_filters", "rosbag2_storage_mcap", "tf2_ros",
                "tf2_eigen", "rviz2", "rclpy", "rclcpp"]
        missing = [p for p in need if p not in pkgs]
        assert not missing, f"missing {missing}"
        return f"ROS_DISTRO={os.environ.get('ROS_DISTRO')}, {len(pkgs)} packages"

    @check("rclpy node (RMW)")
    def _():
        # Subprocess: a broken RMW makes rcl exit the interpreter instead of raising.
        run([sys.executable, "-c", "import rclpy; rclpy.init(); n = rclpy.create_node('savior_check_env'); "
             "n.destroy_node(); rclpy.shutdown()"])
        return f"RMW_IMPLEMENTATION={os.environ.get('RMW_IMPLEMENTATION', '(default rmw_fastrtps_cpp)')}"

    @check("python3 -m pytest (7.x)")
    def _():
        out = run([sys.executable, "-m", "pytest", "--version"]).strip() or "?"
        import pytest

        assert pytest.__version__.startswith("7."), f"pytest {pytest.__version__} (need 7.x)"
        return out

    @check("colcon / rosdep / rosbags-convert")
    def _():
        run("colcon --help")
        run("rosdep --version")
        run("rosbags-convert --help")
        return "ok"

    @check("OpenVINS build deps (Eigen, Ceres, Boost, OpenCV C++)")
    def _():
        eigen = run("pkg-config --modversion eigen3").strip()
        opencv = run("pkg-config --modversion opencv4").strip()
        assert opencv.startswith("4.5"), f"system OpenCV {opencv} (cv_bridge expects 4.5.x)"
        assert os.path.isdir("/usr/include/ceres"), "ceres headers missing"
        with open("/usr/include/boost/version.hpp") as f:
            boost = next(l.split('"')[1] for l in f if "BOOST_LIB_VERSION" in l and '"' in l)
        return f"Eigen {eigen}, OpenCV {opencv}, Boost {boost}, Ceres headers ok"

    # ---------------------------------------------------------------- workspace mount
    @check("workspace mount (writable, file owner = container user)")
    def _():
        ws = os.environ.get("SAVIOR_WS")
        assert ws and os.path.isdir(ws), f"SAVIOR_WS={ws!r} is not a mounted directory"
        cache = os.environ.get("SAVIOR_CACHE_DIR", os.path.join(ws, ".cache"))
        os.makedirs(cache, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache, prefix="check_env_") as f:
            st = os.stat(f.name)
            assert (st.st_uid, st.st_gid) == (os.getuid(), os.getgid()), (st.st_uid, st.st_gid)
        for var in ("SAVIOR_MODELS_DIR", "YOLO_CONFIG_DIR", "TORCH_HOME"):
            assert os.environ.get(var, "").startswith(ws), f"{var}={os.environ.get(var)!r} not inside {ws}"
        return f"{ws} (uid {os.getuid()}, gid {os.getgid()}), models -> {os.environ['SAVIOR_MODELS_DIR']}"

    @check("X11 display (optional)", warn_only=True)
    def _():
        disp = os.environ.get("DISPLAY")
        if not disp:
            return "DISPLAY not set (rviz2 unavailable, that's fine headless)"
        sock = f"/tmp/.X11-unix/X{disp.split(':')[-1].split('.')[0]}"
        if disp.startswith(":"):  # local display -> needs the X11 socket mounted
            assert os.path.exists(sock), f"DISPLAY={disp} but {sock} not mounted"
        return f"DISPLAY={disp}"

    if args.yolo:
        yolo_benchmark(args)

    n_fail = RESULTS.count("FAIL")
    print(f"== {RESULTS.count('PASS')} PASS, {RESULTS.count('WARN')} WARN, {n_fail} FAIL")
    return 1 if n_fail else 0


def yolo_benchmark(args):
    """Export <model>.pt -> FP16 engine (cached in $SAVIOR_MODELS_DIR) and time engine inference."""

    @check(f"YOLO TensorRT FP16 ({args.yolo})")
    def _():
        import cv2
        import numpy as np
        import torch
        from ultralytics import YOLO
        from ultralytics.utils import ASSETS

        models = os.environ.get("SAVIOR_MODELS_DIR") or os.getcwd()
        os.makedirs(models, exist_ok=True)
        os.chdir(models)  # ultralytics downloads bare model names into the cwd
        name = args.yolo.removesuffix(".pt")
        engine = os.path.join(models, f"{name}.engine")
        if not os.path.exists(engine):
            t0 = time.time()
            # quantize=16 == FP16 (ultralytics >= 8.4 replaces the deprecated half=True)
            YOLO(f"{name}.pt").export(format="engine", quantize=16, imgsz=args.imgsz, device=0)
            print(f"       exported {engine} in {time.time() - t0:.0f} s", flush=True)
        model = YOLO(engine, task="segment" if "seg" in name else None)
        img = cv2.imread(str(ASSETS / "bus.jpg"))  # sample image shipped with ultralytics (810x1080)
        for _ in range(20):
            model.predict(img, imgsz=args.imgsz, verbose=False)
        torch.cuda.synchronize()
        t_inf, t_e2e = [], []
        for _ in range(args.iters):
            t0 = time.perf_counter()
            r = model.predict(img, imgsz=args.imgsz, verbose=False)[0]
            t_e2e.append((time.perf_counter() - t0) * 1e3)
            t_inf.append(r.speed["inference"])
        names = [r.names[int(c)] for c in r.boxes.cls.tolist()]
        assert r.masks is not None and "person" in names, f"unexpected detections on bus.jpg: {names}"
        return (f"{os.path.basename(engine)} imgsz={args.imgsz}, bus.jpg -> {len(names)} instances "
                f"({names.count('person')} person, masks {tuple(r.masks.data.shape)}): "
                f"engine inference median {np.median(t_inf):.2f} ms, "
                f"end-to-end predict() median {np.median(t_e2e):.2f} ms (p90 {np.percentile(t_e2e, 90):.2f} ms)")


if __name__ == "__main__":
    sys.exit(main())
