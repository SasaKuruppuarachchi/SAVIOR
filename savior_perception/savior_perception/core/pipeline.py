# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""SAVIOR perception core: segment -> ROI stereo depth -> promote -> track -> extend -> compose.

All stages are switchable through :class:`PipelineConfig` to run the ablations:

* ``gating.enable=false``      classification off ("cdo_off"): every potential is masked;
* ``extension.enable=false`` + ``tracker.enable=false``: post-processing off ("pp_off");
* ``gating.mode=fixed`` / ``extension.band_mode=fixed``: the paper's fixed thresholds;
* ``depth.enable=false``      no stereo (gating falls back to ``unknown_depth_policy``,
  extension to ``min_px`` dilation, no right mask).

P4: ``motion.enable=true`` runs :class:`~.motion.MotionEstimator` between depth and gating (needs the
gyro rotation between frames: ``process(..., R_imu=...)``); its decisions feed the promotion gate
(static person -> ``still``, moving potential -> root, static potential -> veto). Still instances are
unmasked (``motion.still_policy=unmask``) or written as band 192 only (``band``).

SAVIOR-SG: ``compose.movable_static_value > 0`` additionally writes the kept movable-class instances (unpromoted
potential objects, still people) with that value (e.g. 64) into the keep pixels of both masks, so the OpenVINS fork can
gate their features with a tighter chi2 test (``savior_semantic_gate``). The 0 / 192 / 255 pixels are never changed.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .calibration import StereoRectifier
from .compose import MaskItem, RightWarper, compose_left, compose_region, overlay_keep
from .config import PipelineConfig
from .extension import MaskExtender
from .gating import MotionEvidence, PromotionGate
from .motion import MotionEstimator, PrecomputedEvidence
from .roles import RoleTable
from .selective import SelectivePolicy
from .stereo_depth import StereoDepth
from .tracker import MaskTracker
from .types import (MASK_CORE, MASK_EXTENSION, ROLE_DYNAMIC, ROLE_POTENTIAL, ROLES, STATUS_CARRIED,
                    STATUS_HELD, STATUS_PROMOTED, STATUS_ROOT, STATUS_STILL, STATUS_UNCERTAIN, STATUS_UNPROMOTED, FrameResult,
                    Instance, box_slices)


def to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    if img.shape[2] == 1:
        return img[:, :, 0]
    if img.shape[2] == 4:
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


class SaviorPipeline:
    def __init__(self, cfg: Optional[PipelineConfig] = None, roles: Optional[RoleTable] = None,
                 rect: Optional[StereoRectifier] = None,
                 motion_evidence: Optional[MotionEvidence] = None, static_mask: Optional[np.ndarray] = None):
        self.cfg = cfg or PipelineConfig()
        self.cfg.validate()
        self.roles = roles or RoleTable(dynamic=["person"])
        self.rect = rect
        c = self.cfg
        self.depth = StereoDepth(rect, c.depth) if (rect is not None and c.depth.enable) else None
        self.motion = None
        if c.motion.enable and rect is not None:
            if static_mask is None and c.motion.static_mask_file:
                static_mask = cv2.imread(c.motion.static_mask_file, cv2.IMREAD_GRAYSCALE)
            self.motion = MotionEstimator(c.motion, rect, static_mask)
            if motion_evidence is None:
                motion_evidence = PrecomputedEvidence()
        self.gate = PromotionGate(c.gating, self.roles, motion_evidence, fb=rect.fb if rect else None,
                                  sigma_d_px=c.depth.sigma_d_px)
        self.selective = SelectivePolicy(c.selective, c.motion) if c.selective.enable else None
        self.tracker = MaskTracker(c.tracker) if c.tracker.enable else None
        self.extender = MaskExtender(c.extension, rect.f if rect else None, rect.fb if rect else None,
                                     c.depth.sigma_d_px)
        self.warper = RightWarper(rect, c.compose) if (rect is not None and c.compose.right_mask) else None
        self.frame_index = 0
        self.last_result: Optional[FrameResult] = None

    def reset(self):
        if self.tracker is not None:
            self.tracker.reset()
        if self.motion is not None:
            self.motion.reset()
        if self.selective is not None:
            self.selective.reset()
        self.frame_index = 0
        self.last_result = None

    # ------------------------------------------------------------------ helpers
    def _band(self, inst: Instance) -> Tuple[float, float]:
        if self.rect is None or not (math.isfinite(inst.depth) and inst.depth > 0):
            return 0.0, math.inf
        return self.extender.disparity_band(inst.depth)

    def _region_item(self, inst: Instance) -> MaskItem:
        """Instance mask as a composable item (core = the instance mask, no extension)."""
        box = inst.bbox
        core = inst.mask[box_slices(box)]
        disp = None
        if inst.disp_crop is not None and inst.work_box is not None:
            wx0, wy0 = inst.work_box[:2]
            disp = inst.disp_crop[box[1] - wy0:box[3] - wy0, box[0] - wx0:box[2] - wx0]
        d_lo, d_hi = self._band(inst)
        return MaskItem(box=box, core=core, ext=np.zeros_like(core), disp=disp, d_med=inst.disparity, d_lo=d_lo, d_hi=d_hi)

    def _set_depth(self, inst: Instance, d: float, n: int):
        inst.disparity = d
        inst.n_depth_px = n
        if math.isfinite(d) and d > 0:
            inst.depth = self.rect.fb / d
            inst.sigma_z = inst.depth ** 2 * self.cfg.depth.sigma_d_px / self.rect.fb
        else:
            inst.depth = math.nan
            inst.sigma_z = math.nan

    # ------------------------------------------------------------------ main
    def process(self, left_raw: np.ndarray, right_raw: Optional[np.ndarray], stamp,
                instances: Sequence[Instance], R_imu: Optional[np.ndarray] = None):
        """Returns (mask_left uint8 HxW, mask_right uint8 HxW, stats dict).

        `stamp` must be in seconds when motion evidence is enabled; `R_imu` = R_{I_{k-1} I_k} (gyro rotation
        from the previous to this frame, IMU frame), only used by the motion evidence / ego tracker."""
        t0 = time.perf_counter()
        self.frame_index += 1
        h, w = left_raw.shape[:2]
        instances: List[Instance] = list(instances)
        for inst in instances:
            if inst.mask.shape[:2] != (h, w):
                raise ValueError(f"instance mask {inst.mask.shape} != image {(h, w)}")
            if inst.role is None or inst.role not in ROLES:
                inst.role = self.roles.role(inst.cls)
        relevant = [x for x in instances if x.role in (ROLE_DYNAMIC, ROLE_POTENTIAL)]
        for inst in relevant:
            inst.work_box = self.extender.work_box(inst)
            inst.depth_box = self.extender.depth_box(inst)

        # ---- ROI stereo depth
        stereo_ok = self.depth is not None and right_raw is not None
        depth_active = stereo_ok and len(relevant) > 0   # disparity computed this frame
        depth_info = {"n_rois": 0, "matched_px": 0}
        if depth_active:
            lg, rg = to_gray(left_raw), to_gray(right_raw)
            depth_info = self.depth.compute(lg, rg, [x.depth_box for x in relevant])
            for inst in relevant:
                inst.disp_crop = self.depth.raw_disparity(inst.work_box)
                d, n = self.depth.robust_disparity(inst.mask[box_slices(inst.work_box)], inst.disp_crop)
                self._set_depth(inst, d, n)
        t1 = time.perf_counter()

        # ---- motion evidence (P4)
        ctx = None
        t_m = time.perf_counter()
        if self.motion is not None:
            lg = to_gray(left_raw)
            rg = to_gray(right_raw) if right_raw is not None else None
            ctx = {"motion": self.motion.update(lg, rg, float(stamp), instances, R_imu)}
        if self.selective is not None:
            ctx = ctx or {}
            ctx["selective"] = self.selective.update(float(stamp), instances, self.motion)
            ctx["selective"]["unknown_promotes"] = self.cfg.selective.unknown_promotes
        t_m1 = time.perf_counter()

        # ---- promotion
        if self.cfg.gating.enable:
            gres = self.gate.run(instances, ctx)
            if self.selective is not None:
                self.selective.finalize(float(stamp), instances)
        else:
            gres = PromotionGate.promote_all(instances)
        t2 = time.perf_counter()

        # ---- tracking (carry-over + chain hysteresis)
        carried: List[Instance] = []
        if self.tracker is not None:
            ego = None
            if self.cfg.tracker.motion_model == "ego" and self.motion is not None:
                ego = self.motion.ego_project if self.motion.last_ego is not None else None
            carried = self.tracker.update(instances, (h, w), ego)
            for inst in carried:
                inst.work_box = self.extender.work_box(inst)
                inst.disp_crop = self.depth.raw_disparity(inst.work_box) if depth_active else None
        t3 = time.perf_counter()

        # ---- extension
        all_inst = instances + carried
        items = []
        static_items = []                       # SAVIOR-SG: kept movable-class instances (movable_static_value > 0)
        static_value = self.cfg.compose.movable_static_value
        band_still = self.cfg.motion.still_policy == "band"
        for inst in all_inst:
            if band_still and inst.status == STATUS_STILL:
                box = inst.bbox
                core = inst.mask[box_slices(box)]
                disp = None
                if inst.disp_crop is not None and inst.work_box is not None:
                    wx0, wy0 = inst.work_box[:2]
                    disp = inst.disp_crop[box[1] - wy0:box[3] - wy0, box[0] - wx0:box[2] - wx0]
                d_lo, d_hi = self._band(inst)
                items.append(MaskItem(box=box, core=np.zeros_like(core), ext=core, disp=disp,
                                      d_med=inst.disparity, d_lo=d_lo, d_hi=d_hi))
                continue
            if not inst.is_dynamic:
                if static_value and inst.status in (STATUS_UNPROMOTED, STATUS_STILL):
                    static_items.append(self._region_item(inst))
                continue
            box, core, ext, disp, _ = self.extender.extend(inst, inst.work_box, inst.disp_crop)
            d_lo, d_hi = self._band(inst)
            items.append(MaskItem(box=box, core=core, ext=ext, disp=disp,
                                  d_med=inst.disparity, d_lo=d_lo, d_hi=d_hi))
        fb_mode = self.cfg.compose.right_fallback
        if fb_mode != "none" and self.rect is not None:
            # P4: instances without stereo depth (border / textureless / missed by SGBM) got no right polygon (P2)
            no_d = [it for it in items + static_items if not (math.isfinite(it.d_med) and it.d_med > 0)]
            if no_d:
                ds = [x.disparity for x in relevant if math.isfinite(x.disparity) and x.disparity > 0]
                d_fb = float(np.median(ds)) if ds else self.rect.fb / self.cfg.compose.right_fallback_depth_m
                for it in no_d:
                    it.d_med = d_fb
                    it.d_lo = max(it.d_lo, 1e-3)        # invalid (0) per-pixel disparities -> d_fb
                    it.right_band_only = fb_mode == "band"
        t4 = time.perf_counter()

        # ---- compose
        mask_left = compose_left((h, w), items)
        if self.warper is not None and stereo_ok:
            mask_right = self.warper.warp(items)
        else:
            rshape = right_raw.shape[:2] if right_raw is not None else (h, w)
            mask_right = np.zeros(rshape, np.uint8)
        if static_items:
            overlay_keep(mask_left, compose_region((h, w), static_items), static_value)
            if self.warper is not None and stereo_ok:
                overlay_keep(mask_right, self.warper.warp_region(static_items), static_value)
        t5 = time.perf_counter()

        timings = {"depth": (t1 - t0) * 1e3, "gating": (t2 - t_m1) * 1e3, "tracking": (t3 - t2) * 1e3,
                   "extension": (t4 - t3) * 1e3, "compose": (t5 - t4) * 1e3, "total": (t5 - t0) * 1e3}
        if self.motion is not None:
            timings["motion"] = (t_m1 - t_m) * 1e3
        n_role = {r: 0 for r in ROLES}
        for inst in instances:
            n_role[inst.role] = n_role.get(inst.role, 0) + 1
        stats = {
            "stamp": stamp,
            "frame": self.frame_index,
            "image_size": [h, w],
            "timings_ms": {k: round(v, 3) for k, v in timings.items()},
            "n_instances": len(instances),
            "n_by_role": n_role,
            "n_roots": sum(1 for x in instances if x.status == STATUS_ROOT),
            "n_promoted": sum(1 for x in instances if x.status == STATUS_PROMOTED),
            "n_held": sum(1 for x in instances if x.status == STATUS_HELD),
            "n_carried": sum(1 for x in carried if x.status == STATUS_CARRIED),
            "n_tracks": len(self.tracker.tracks) if self.tracker is not None else 0,
            "tracks": self.tracker.summary() if self.tracker is not None else {},
            "links": [[c, p] for c, p in gres.links],
            "depth": depth_info,
            "core_px": int(np.count_nonzero(mask_left == MASK_CORE)),
            "ext_px": int(np.count_nonzero(mask_left == MASK_EXTENSION)),
            "instances": [x.summary() for x in all_inst],
        }
        if static_value:
            stats["static_px"] = int(np.count_nonzero(mask_left == static_value))
        if self.motion is not None:
            stats["n_still"] = sum(1 for x in instances if x.status == STATUS_STILL)
            stats["motion"] = self.motion.last_stats
        if self.selective is not None:
            stats["selective"] = dict(self.selective.last_stats,
                                      n_uncertain=sum(1 for x in instances if x.status == STATUS_UNCERTAIN))
        self.last_result = FrameResult(stamp=stamp, mask_left=mask_left, mask_right=mask_right,
                                       instances=all_inst, links=gres.links, timings_ms=timings,
                                       stats=stats)
        return mask_left, mask_right, stats
