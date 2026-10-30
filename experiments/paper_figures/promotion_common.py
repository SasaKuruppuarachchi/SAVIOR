"""Shared helpers for find_promotion_frame.py and make_promotion_figure.py (paper-side only, no src/ changes).

The detector is replaced by the dataset's GT instance segmentation (seg0, one instance per GT id); every later
stage is savior_perception's own code (SaviorPipeline: ROI stereo depth, contact depth gate, breadth-first
association tree, IMU-compensated motion evidence, depth-guided extension, composition).
"""
import json

import cv2
import numpy as np

from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.config import PipelineConfig
from savior_perception.core.motion import GyroIntegrator
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.types import Instance

WS = "/home/sasa/workspace/savior_ws"
ROLES = f"{WS}/src/savior/savior_bringup/config/roles/warehouse.yaml"

# SAVIOR-P / SAVIOR-PM of results/p6_warehouse/methods.yaml (yolo_p2 / yolo_p4), with GT instances as detector
BASE = {"gating.link_depth": "contact", "gating.max_noise_m": 0.5, "tracker.enable": False,
        "extension.enable": True, "motion.still_policy": "unmask", "compose.right_fallback": "median"}


def make_pipeline(raw, motion=False):
    assert "_t2_" not in raw and "_t3_" not in raw, "sealed held-out split"
    roles = RoleTable.from_yaml(ROLES)
    rect = stereo_from_kalibr(f"{raw}/calib/kalibr_imucam_chain.yaml", "cam0", "cam1")
    cfg = PipelineConfig.from_flat(dict(BASE, **{"motion.enable": bool(motion)}))
    return SaviorPipeline(cfg, roles, rect)


def read_moving(raw):
    out = {}
    for line in open(f"{raw}/moving.csv"):
        if line.startswith("#"):
            continue
        r = line.strip().split(",")
        out[int(r[0])] = (r[1], {int(x) for x in r[2].split()} if len(r) > 2 and r[2] else set())
    return out


def gt_instances(raw, ts, meta, roles, min_px=30):
    seg = cv2.imread(f"{raw}/seg0/{ts}.png", cv2.IMREAD_UNCHANGED)
    out = []
    ids, cnt = np.unique(seg, return_counts=True)
    for i, c in zip(ids.tolist(), cnt.tolist()):
        if i == 0 or i not in meta or c < min_px:
            continue
        if roles.role(meta[i]["cls"]) not in ("dynamic", "potential"):
            continue
        x = Instance.from_mask(seg == i, meta[i]["cls"])
        x.gt_id = i
        out.append(x)
    return out


def gyro(raw):
    g = GyroIntegrator(max_age_s=1e9)
    for line in open(f"{raw}/imu_noisy.csv"):
        if line.startswith("#"):
            continue
        v = line.split(",")
        g.add(int(v[0]) * 1e-9, [float(x) for x in v[1:4]])
    return g
