# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""ROS 2 node ``savior_node``: stereo images -> layered dynamic masks for OpenVINS.

Contract (docs/INTERFACE.md §3.1/§3.3): ``/savior/mask/left`` and
``/savior/mask/right`` are ``mono8`` images with the raw camera resolution, values
0 keep / 192 extension band / 255 dynamic core, and ``header.stamp`` equal to the stamp of
the source LEFT image (right mask too). Reliable QoS, depth 10. One mask pair is published
for every synchronized stereo frame (all zeros when nothing is dynamic or processing fails).
Masks are never resampled with interpolation (layer values must survive); OpenVINS must run
with ``downsample_cameras: false`` (its pyrDown would blur the 192/255 layers).

P4 (``motion.enable``): the node also subscribes to ``imu_topic`` (sensor_msgs/Imu, gyro only) and holds
each synced stereo frame until gyro samples cover its stamp (or ``imu_wait_ms`` of wall time passed), so
the gyro rotation between consecutive frames is independent of the message timing (deterministic replay).
"""

from __future__ import annotations

import os

# P4 (thread oversubscription): BLAS / OpenMP read their thread count when numpy is first imported, i.e. before the
# ROS parameters exist -> environment SAVIOR_NUM_THREADS (default 4; existing OMP_NUM_THREADS etc. win). OpenCV and
# torch follow the `num_threads` node parameter. With 48 cores the library defaults gave ~107 threads per node and
# fallbacks with 18+ parallel runs; the outputs do not depend on the thread count.
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    if os.environ.get("SAVIOR_NUM_THREADS", "4") not in ("", "0"):
        os.environ.setdefault(_k, os.environ.get("SAVIOR_NUM_THREADS", "4"))

import array
import json
import math
import sys
import time
from collections import deque
from typing import Optional

import numpy as np
import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import Header, String

import message_filters

from .core.calibration import stereo_from_kalibr
from .core.compose import render_overlay
from .core.config import PipelineConfig
from .core.motion import GyroIntegrator
from .core.pipeline import SaviorPipeline
from .core.roles import RoleTable
from .params import NODE_DEFAULTS
from .segmenters import make_segmenter

_CHANNELS = {"mono8": 1, "8UC1": 1, "bgr8": 3, "rgb8": 3, "8UC3": 3, "bgra8": 4, "rgba8": 4,
             "mono16": 1, "16UC1": 1}


def mask_qos() -> QoSProfile:
    """Contract QoS: RELIABLE, KEEP_LAST 10 (the OpenVINS mask subscriber is reliable)."""
    return QoSProfile(reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST, depth=10)


def image_to_numpy(msg: Image) -> np.ndarray:
    """sensor_msgs/Image -> numpy (uint8 gray, or BGR for colour encodings)."""
    enc = msg.encoding
    if enc not in _CHANNELS:
        raise ValueError(f"unsupported image encoding '{enc}'")
    ch = _CHANNELS[enc]
    is16 = enc in ("mono16", "16UC1")
    dtype = np.dtype(">u2" if (is16 and msg.is_bigendian) else ("<u2" if is16 else "u1"))
    buf = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
    row_bytes = msg.width * ch * dtype.itemsize
    arr = np.ascontiguousarray(buf[:, :row_bytes]).view(dtype)
    arr = arr.reshape(msg.height, msg.width, ch) if ch > 1 else arr.reshape(msg.height, msg.width)
    if is16:
        arr = (arr >> 8).astype(np.uint8)
    if enc == "rgb8":
        arr = arr[:, :, ::-1]
    elif enc == "rgba8":
        arr = arr[:, :, [2, 1, 0]]
    elif enc == "bgra8":
        arr = arr[:, :, :3]
    return np.ascontiguousarray(arr)


def numpy_to_image(arr: np.ndarray, header, encoding: str, frame_id: Optional[str] = None) -> Image:
    msg = Image()
    msg.header.stamp = header.stamp
    msg.header.frame_id = header.frame_id if not frame_id else frame_id
    msg.height, msg.width = int(arr.shape[0]), int(arr.shape[1])
    msg.encoding = encoding
    msg.is_bigendian = 0
    ch = 1 if arr.ndim == 2 else arr.shape[2]
    msg.step = msg.width * ch
    # array('B') skips rclpy's per-element type check of sequence<uint8> fields (tens of ms)
    msg.data = array.array("B", np.ascontiguousarray(arr, dtype=np.uint8).tobytes())
    return msg


class SaviorNode(Node):
    def __init__(self, **node_kwargs):
        super().__init__("savior_node", **node_kwargs)
        self._n_fail = 0
        dyn = ParameterDescriptor(dynamic_typing=True)
        defaults = dict(NODE_DEFAULTS)
        defaults.update(PipelineConfig().to_flat())
        for name, value in defaults.items():
            self.declare_parameter(name, value, dyn)
        P = {name: self.get_parameter(name).value for name in defaults}
        self.P = P
        self._limit_threads(int(P["num_threads"]))
        self.cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split(".")[0] in PipelineConfig.SECTIONS})

        roles_file = P["roles_file"] or self._default_roles_file()
        self.roles = RoleTable.from_yaml(roles_file)
        self.get_logger().info(f"roles from {roles_file}: {self.roles}")

        self.rect = None
        if P["calib_file"]:
            self.rect = stereo_from_kalibr(P["calib_file"], P["cam_left"], P["cam_right"],
                                           focal_scale=self.cfg.depth.rect_focal_scale,
                                           size_scale=self.cfg.depth.rect_size_scale,
                                           max_scale=self.cfg.depth.rect_max_scale)
            self.get_logger().info(
                f"stereo calib {P['calib_file']}: f={self.rect.f:.1f}px b={self.rect.baseline:.4f}m "
                f"rect={self.rect.rect_size} models=({self.rect.cams[0].model},{self.rect.cams[1].model})")
        else:
            self.get_logger().warn("no calib_file: stereo depth, depth-guided extension and right-mask "
                                   "warp disabled (right mask is all zeros)")

        backend = str(P["segmenter.backend"]).lower()
        self.segmenter = make_segmenter(
            backend, model=P["segmenter.model"], conf=P["segmenter.conf"], iou=P["segmenter.iou"],
            imgsz=P["segmenter.imgsz"], device=P["segmenter.device"], half=P["segmenter.half"],
            classes=self.roles.relevant_classes() if P["segmenter.filter_classes"] else None,
            colormap_file=P["segmenter.colormap_file"], retina_masks=P["segmenter.retina_masks"],
            fast_masks=P["segmenter.fast_masks"])
        self.uses_aux = bool(getattr(self.segmenter, "needs_aux_image", False))
        self._limit_threads(int(P["num_threads"]), torch_only=True)   # torch is imported by the YOLO backend
        if self.uses_aux and not P["seg_topic"]:
            raise ValueError(f"segmenter.backend '{backend}' requires seg_topic")
        # P5: right mask straight from the right camera's GT semantic image (oracle only; e.g. VIODE /cam1/segmentation)
        self.uses_aux_right = bool(self.uses_aux and P["seg_right_topic"])
        if P["seg_right_topic"] and not self.uses_aux:
            self.get_logger().warn("seg_right_topic is only used by the oracle backends: ignored")
        if self.uses_aux_right and (self.roles.classes_with_role("potential") or self.cfg.extension.enable
                                    or self.cfg.tracker.enable):
            self.get_logger().warn("seg_right_topic: the right mask only contains the dynamic-role instances of the "
                                   "right semantic image (no promotion, extension band or tracker on the right side)")
        self.pipeline: Optional[SaviorPipeline] = None
        self._warmed = not P["segmenter.warmup"]
        if not self._warmed and self.rect is not None:
            # warm up BEFORE subscribing: a warmup in the first image callback (TensorRT/CUDA context,
            # ~1 s) made the reliable depth-10 input queue overflow, i.e. no masks for the first frames
            self._warmup(self.rect.cams[0].size[::-1])

        qos = mask_qos()
        self.pub_left = self.create_publisher(Image, P["mask_left_topic"], qos)
        self.pub_right = self.create_publisher(Image, P["mask_right_topic"], qos)
        self.pub_stats = self.create_publisher(String, P["stats_topic"], qos)
        self.pub_debug = self.create_publisher(Image, P["debug_topic"], qos) if P["publish_debug"] else None

        # P4: gyro for the motion evidence (only subscribed when needed: P2 behaviour otherwise)
        self.gyro: Optional[GyroIntegrator] = None
        self._pending = deque()
        self._prev_img_t: Optional[float] = None
        self._imu_timeouts = 0
        self._last_imu_wall = time.monotonic()
        if self.cfg.motion.enable:
            if not P["imu_topic"]:
                raise ValueError("motion.enable requires imu_topic")
            self.gyro = GyroIntegrator()
            iqos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST,
                              depth=int(P["imu_queue_size"]))
            self._imu_sub = self.create_subscription(Imu, P["imu_topic"], self._on_imu, iqos)
            self._flush_timer = self.create_timer(0.005, self._flush)
            self.get_logger().info(f"motion evidence on: gyro from {P['imu_topic']} (wait <= {P['imu_wait_ms']} ms)")

        subs = [message_filters.Subscriber(self, Image, P["left_topic"], qos_profile=qos),
                message_filters.Subscriber(self, Image, P["right_topic"], qos_profile=qos)]
        if self.uses_aux:
            subs.append(message_filters.Subscriber(self, Image, P["seg_topic"], qos_profile=qos))
        if self.uses_aux_right:
            subs.append(message_filters.Subscriber(self, Image, P["seg_right_topic"], qos_profile=qos))
        self._subs = subs
        self.sync = message_filters.TimeSynchronizer(subs, int(P["sync_queue_size"]))
        self.sync.registerCallback(self._on_images)
        self._n = 0
        self._t_log = time.monotonic()
        self._acc = {}
        self.get_logger().info(
            f"savior_node up: backend={backend} left={P['left_topic']} right={P['right_topic']}"
            + (f" seg={P['seg_topic']}" if self.uses_aux else "")
            + (f" seg_right={P['seg_right_topic']}" if self.uses_aux_right else "")
            + f" -> {P['mask_left_topic']}, {P['mask_right_topic']}")

    def _limit_threads(self, n: int, torch_only: bool = False):
        """num_threads > 0: cv2.setNumThreads(n) and torch.set_num_threads(n) (if torch is loaded)."""
        if n <= 0:
            return
        if not torch_only:
            import cv2
            cv2.setNumThreads(n)
            self.get_logger().info(f"num_threads={n} (cv2; BLAS/OMP from env: OMP_NUM_THREADS="
                                   f"{os.environ.get('OMP_NUM_THREADS', '')})")
        if "torch" in sys.modules:
            try:
                sys.modules["torch"].set_num_threads(n)
            except Exception:  # noqa: BLE001 - best effort
                pass

    @staticmethod
    def _default_roles_file() -> str:
        try:
            from ament_index_python.packages import get_package_share_directory
            return os.path.join(get_package_share_directory("savior_perception"), "config", "roles_default.yaml")
        except Exception:  # running from source
            return os.path.join(os.path.dirname(__file__), "..", "config", "roles_default.yaml")

    def _warmup(self, shape):
        self._warmed = True
        try:
            t0 = time.perf_counter()
            self.segmenter.warmup(shape)
            self.get_logger().info(f"segmenter warmup {shape[1]}x{shape[0]}: {(time.perf_counter() - t0) * 1e3:.0f} ms")
        except Exception as exc:  # warmup is best effort
            self.get_logger().warn(f"segmenter warmup failed: {exc}")

    def _build_pipeline(self, left: np.ndarray, right: np.ndarray):
        rect = self.rect
        if rect is not None:
            exp_l, exp_r = rect.cams[0].size, rect.cams[1].size
            got_l, got_r = (left.shape[1], left.shape[0]), (right.shape[1], right.shape[0])
            if exp_l != got_l or exp_r != got_r:
                self.get_logger().error(f"image sizes {got_l}/{got_r} != calibration {exp_l}/{exp_r}: "
                                        "disabling stereo depth and right-mask warp")
                rect = None
        static_mask = None
        if self.cfg.motion.enable and self.cfg.motion.static_mask_file:
            import cv2
            static_mask = cv2.imread(self.cfg.motion.static_mask_file, cv2.IMREAD_UNCHANGED)
            if static_mask is not None and static_mask.ndim == 3:
                static_mask = static_mask[:, :, :3].max(axis=2)
            if static_mask is None or static_mask.shape[:2] != left.shape[:2]:
                self.get_logger().warn(f"motion.static_mask_file {self.cfg.motion.static_mask_file} unusable, ignored")
                static_mask = None
        self.pipeline = SaviorPipeline(self.cfg, self.roles, rect, static_mask=static_mask)

    def _publish_masks(self, left_msg: Image, right_msg: Image, mask_l: np.ndarray, mask_r: np.ndarray):
        # Both masks carry the LEFT image's header.stamp object verbatim (OpenVINS matches exact
        # integer nanoseconds; never rebuild it from float seconds). Right mask keeps the right
        # camera frame_id.
        self.pub_left.publish(numpy_to_image(mask_l, left_msg.header, "mono8", self.P["frame_id_left"]))
        hdr = Header(stamp=left_msg.header.stamp, frame_id=right_msg.header.frame_id)
        self.pub_right.publish(numpy_to_image(mask_r, hdr, "mono8", self.P["frame_id_right"]))

    # ------------------------------------------------------------------ IMU (P4)
    def _on_imu(self, msg: Imu):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        w = msg.angular_velocity
        self.gyro.add(t, (w.x, w.y, w.z))
        self._last_imu_wall = time.monotonic()
        self._flush()

    def _flush(self):
        """Process pending frames in order once the gyro covers their stamp (or after imu_wait_ms)."""
        off = self.cfg.motion.imu_time_offset_s
        wait = float(self.P["imu_wait_ms"]) * 1e-3
        while self._pending:
            left_msg, right_msg, seg_msg, segr_msg, arrival = self._pending[0]
            t_img = left_msg.header.stamp.sec + left_msg.header.stamp.nanosec * 1e-9
            covered = self.gyro.last_time >= t_img + off
            now = time.monotonic()
            # time out only if the IMU stream itself is silent: under CPU load gyro messages may queue behind the
            # image callbacks for a while (a wall-time limit on the frame alone made the replay non-deterministic)
            timed_out = (now - arrival) > wait and (now - self._last_imu_wall) > wait
            if not (covered or timed_out):
                return
            self._pending.popleft()
            if not covered:
                self._imu_timeouts += 1
                self.get_logger().warn(f"no gyro up to t={t_img:.3f} after {wait * 1e3:.0f} ms "
                                       f"({self._imu_timeouts} timeouts)", throttle_duration_sec=5.0)
            R = None
            if self._prev_img_t is not None:
                R = self.gyro.rotation(self._prev_img_t + off, t_img + off)
            self._prev_img_t = t_img
            self._run(left_msg, right_msg, seg_msg, R, {"covered": covered, "timeouts": self._imu_timeouts,
                                                        "wait_ms": round((time.monotonic() - arrival) * 1e3, 2)},
                      segr_msg=segr_msg)

    def _on_images(self, left_msg: Image, right_msg: Image, seg_msg: Optional[Image] = None,
                   segr_msg: Optional[Image] = None):
        """Every synced frame yields exactly one left + one right mask, even on failure
        (all-zero masks then), so OpenVINS never waits for dynamic_mask_timeout_ms."""
        if self.gyro is not None:
            self._pending.append((left_msg, right_msg, seg_msg, segr_msg, time.monotonic()))
            self._flush()
            return
        self._run(left_msg, right_msg, seg_msg, segr_msg=segr_msg)

    def _run(self, left_msg: Image, right_msg: Image, seg_msg: Optional[Image] = None, R_imu=None, imu_info=None,
             segr_msg: Optional[Image] = None):
        try:
            self._process(left_msg, right_msg, seg_msg, R_imu, imu_info, segr_msg)
        except Exception as exc:  # noqa: BLE001 - never drop a mask
            self._n_fail += 1
            self.get_logger().error(f"frame processing failed ({self._n_fail} so far), publishing empty "
                                    f"masks: {type(exc).__name__}: {exc}", throttle_duration_sec=5.0)
            zl = np.zeros((left_msg.height, left_msg.width), np.uint8)
            zr = np.zeros((right_msg.height, right_msg.width), np.uint8)
            self._publish_masks(left_msg, right_msg, zl, zr)

    def _process(self, left_msg: Image, right_msg: Image, seg_msg: Optional[Image], R_imu=None, imu_info=None,
                 segr_msg: Optional[Image] = None):
        t0 = time.perf_counter()
        left = image_to_numpy(left_msg)
        right = image_to_numpy(right_msg)
        if self.pipeline is None:
            self._build_pipeline(left, right)
        if not self._warmed:
            self._warmup(left.shape)
        t1 = time.perf_counter()
        if self.uses_aux:
            instances = self.segmenter.predict(image_to_numpy(seg_msg), target_shape=left.shape[:2])
        else:
            instances = self.segmenter.predict(left)
        t2 = time.perf_counter()
        stamp = left_msg.header.stamp
        stamp_f = stamp.sec + stamp.nanosec * 1e-9  # informational only (stats)
        if self.gyro is not None:
            mask_l, mask_r, stats = self.pipeline.process(left, right, stamp_f, instances, R_imu=R_imu)
            stats["imu"] = imu_info
        else:
            mask_l, mask_r, stats = self.pipeline.process(left, right, stamp_f, instances)
        if segr_msg is not None:
            # P5: GT right mask = dynamic-role instances of the right semantic image (replaces the stereo warp)
            mask_r = np.zeros((right_msg.height, right_msg.width), np.uint8)
            for inst in self.segmenter.predict(image_to_numpy(segr_msg), target_shape=mask_r.shape):
                if self.roles.role(inst.cls) == "dynamic":
                    mask_r[inst.mask] = 255
            stats["right_source"] = "seg"
        if mask_r.shape != (right_msg.height, right_msg.width):
            mask_r = np.zeros((right_msg.height, right_msg.width), np.uint8)
        self._publish_masks(left_msg, right_msg, mask_l, mask_r)
        t3 = time.perf_counter()
        if self.pub_debug is not None:
            ov = render_overlay(left, mask_l, self.pipeline.last_result.instances)
            self.pub_debug.publish(numpy_to_image(ov, left_msg.header, "bgr8"))
        stats["stamp"] = {"sec": int(stamp.sec), "nanosec": int(stamp.nanosec), "t": stamp_f}
        stats["timings_ms"]["convert"] = round((t1 - t0) * 1e3, 3)
        stats["timings_ms"]["segment"] = round((t2 - t1) * 1e3, 3)
        stats["timings_ms"]["node_total"] = round((t3 - t0) * 1e3, 3)
        if self.P["stats_compact"]:
            # P7: drop the per-instance list and the links (bulk of the log); counts, timings and core_px stay
            stats.pop("instances", None)
            stats.pop("links", None)
        self.pub_stats.publish(String(data=json.dumps(stats, default=_json_default)))
        self._log(stats)

    def _log(self, stats):
        self._n += 1
        for k, v in stats["timings_ms"].items():
            self._acc[k] = self._acc.get(k, 0.0) + v
        now = time.monotonic()
        if now - self._t_log >= 10.0:
            n = max(1, self._n)
            avg = " ".join(f"{k}={v / n:.1f}" for k, v in self._acc.items())
            self.get_logger().info(f"{n} frames, mean ms: {avg}")
            self._n, self._acc, self._t_log = 0, {}, now


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if math.isnan(v) else v
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SaviorNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
