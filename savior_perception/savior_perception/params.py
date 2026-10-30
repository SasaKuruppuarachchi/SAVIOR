# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Parameter defaults of ``savior_node`` (kept free of rclpy so tests can import them).

Node-level parameters are below; pipeline parameters (``depth.*``, ``gating.*``,
``tracker.*``, ``extension.*``, ``compose.*``) come from :class:`PipelineConfig`.
"""

from __future__ import annotations

from typing import Any, Dict

from .core.config import PipelineConfig

NODE_DEFAULTS: Dict[str, Any] = {
    # topics (mask topics are fixed by the interface contract; overridable for tests)
    "left_topic": "/cam0/image_raw",
    "right_topic": "/cam1/image_raw",
    "seg_topic": "",                       # oracle backend: GT semantic image (exact-time synced)
    "seg_right_topic": "",                 # P5: oracle backend: GT semantic image of the RIGHT camera -> right mask =
                                           # its dynamic-role instances (255) instead of the stereo warp ("" = warp)
    "mask_left_topic": "/savior/mask/left",
    "mask_right_topic": "/savior/mask/right",
    "debug_topic": "/savior/debug/overlay",
    "stats_topic": "/savior/stats",
    "publish_debug": False,
    "sync_queue_size": 30,
    "frame_id_left": "",                   # "" = copy the left image frame_id
    "frame_id_right": "",                  # "" = copy the right image frame_id
    # calibration (the OpenVINS kalibr_imucam_chain.yaml; "" = no stereo -> depth/right mask off)
    "calib_file": "",
    "cam_left": "cam0",
    "cam_right": "cam1",
    # class roles ("" = package default config/roles_default.yaml)
    "roles_file": "",
    # segmenter
    "segmenter.backend": "none",           # yolo | oracle_uhumans2 | oracle_colormap | none
    "segmenter.model": "",                 # .pt or TensorRT .engine
    "segmenter.conf": 0.25,
    "segmenter.iou": 0.7,
    "segmenter.imgsz": 640,
    "segmenter.device": "",                # "" = ultralytics default (cuda:0 if available)
    "segmenter.half": False,
    "segmenter.retina_masks": True,        # masks at native resolution
    "segmenter.filter_classes": True,      # only run NMS/output for dynamic+potential classes
    "segmenter.colormap_file": "",         # oracle backends: colour -> class yaml
    "segmenter.warmup": True,
    "segmenter.fast_masks": False,         # P7: YOLO copies only the box crops of the native masks to the CPU (bit-identical)
    "stats_compact": False,                # P7: /savior/stats without the per-instance list / links (~25x smaller logs)
    # P4: cap of the OpenCV / torch threads (<= 0: library default = all cores); BLAS/OMP: env SAVIOR_NUM_THREADS
    "num_threads": 4,
    # P4 motion evidence: gyro input (only used with motion.enable)
    "imu_topic": "",                       # sensor_msgs/Imu (angular_velocity in the IMU frame of the kalibr yaml)
    "imu_wait_ms": 300,                    # max wall time a frame waits for gyro samples covering its stamp
    "imu_queue_size": 2000,
}


def all_defaults() -> Dict[str, Any]:
    d = dict(NODE_DEFAULTS)
    d.update(PipelineConfig().to_flat())
    return d
