# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Depth-guided mask extension (layer 192 = relaxable extension band).

Two complementary parts, both evaluated inside the instance *work box*
(bbox expanded by ``bbox_expand`` x size + ``max_px``):

1. depth-adaptive dilation ring: ``margin_px = clamp(f * margin_m / z, min_px, max_px)``
   (an object at range needs fewer pixels for the same metric margin; ``min_px`` keeps at
   least a KLT patch radius so no feature patch straddles the object boundary);
2. depth-band region growing: pixels inside the bbox expanded by ``bbox_expand`` whose
   disparity lies in the band ``z +- delta`` (``delta = band_m + k_sigma*sigma_z(z)`` or the
   paper's fixed ``dist_ext``) and that are 8-connected to the core mask.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import cv2
import numpy as np

from .config import ExtensionConfig
from .types import Box, Instance, expand_box


class MaskExtender:
    def __init__(self, cfg: ExtensionConfig, f: Optional[float] = None, fb: Optional[float] = None,
                 sigma_d_px: float = 1.0):
        self.cfg = cfg
        self.f = f
        self.fb = fb
        self.sigma_d_px = sigma_d_px

    def work_box(self, inst: Instance) -> Box:
        h, w = inst.shape
        pad = int(self.cfg.max_px) if (self.cfg.enable and self.cfg.dilate) else 0
        ratio = self.cfg.bbox_expand if (self.cfg.enable and self.cfg.grow) else 0.0
        return expand_box(inst.bbox, pad + 1, ratio, w, h)

    def depth_box(self, inst: Instance) -> Box:
        """Region needing disparity: the bbox (instance depth) + the growth region."""
        h, w = inst.shape
        ratio = self.cfg.bbox_expand if (self.cfg.enable and self.cfg.grow) else 0.0
        return expand_box(inst.bbox, 0, ratio, w, h)

    def margin_px(self, z: float) -> int:
        c = self.cfg
        if self.f is None or not math.isfinite(z) or z <= 0:
            return int(c.min_px)
        return int(round(min(max(self.f * c.margin_m / z, c.min_px), c.max_px)))

    def band(self, z: float) -> float:
        c = self.cfg
        if c.band_mode == "fixed":
            return c.fixed_band_m
        sz = (z * z * self.sigma_d_px / self.fb) if self.fb else 0.0
        return c.band_m + c.k_sigma * sz

    def disparity_band(self, z: float) -> Tuple[float, float]:
        delta = self.band(z)
        d_lo = self.fb / (z + delta)
        zn = z - delta
        d_hi = self.fb / zn if zn > 1e-3 else np.inf
        return d_lo, d_hi

    def extend(self, inst: Instance, box: Box, disp_crop: Optional[np.ndarray]):
        """Compute the extension band of `inst`.

        `box` is the instance work box and `disp_crop` its raw-domain disparity crop (or None).
        Returns ``(ext_box, core, ext, disp, margin)`` where ``ext_box`` is the (smaller or equal)
        sub-box of `box` actually touched, ``core``/``ext`` are bool crops of it (disjoint),
        ``disp`` the matching disparity view (or None) and ``margin`` the dilation used [px].
        """
        c = self.cfg
        h, w = inst.shape
        margin = self.margin_px(inst.depth) if (c.enable and c.dilate) else 0
        can_grow = (c.enable and c.grow and disp_crop is not None and bool(self.fb)
                    and math.isfinite(inst.depth) and inst.depth > 0)
        gbox = expand_box(inst.bbox, 0, c.bbox_expand, w, h) if can_grow else inst.bbox
        rbox = expand_box(inst.bbox, margin + 1, 0.0, w, h) if margin > 0 else inst.bbox
        ub = (min(gbox[0], rbox[0]), min(gbox[1], rbox[1]), max(gbox[2], rbox[2]), max(gbox[3], rbox[3]))
        ub = (max(ub[0], box[0]), max(ub[1], box[1]), min(ub[2], box[2]), min(ub[3], box[3]))
        core = inst.mask[ub[1]:ub[3], ub[0]:ub[2]]
        disp = None
        if disp_crop is not None:
            disp = disp_crop[ub[1] - box[1]:ub[3] - box[1], ub[0] - box[0]:ub[2] - box[0]]
        ext = np.zeros(core.shape, bool)
        if not c.enable:
            return ub, core, ext, disp, 0
        if margin > 0:
            notcore = np.ascontiguousarray(~core).view(np.uint8)
            dist = cv2.distanceTransform(notcore, cv2.DIST_L2, 3)
            ext |= dist <= margin
        if can_grow:
            d_lo, d_hi = self.disparity_band(inst.depth)
            cand = (disp >= d_lo) & (disp <= d_hi)
            if gbox != ub:  # restrict growth to the bbox expanded by `bbox_expand`
                region = np.zeros_like(cand)
                region[gbox[1] - ub[1]:gbox[3] - ub[1], gbox[0] - ub[0]:gbox[2] - ub[0]] = True
                cand &= region
            if cand.any():
                seeds = np.ascontiguousarray(cand | core)
                n, labels = cv2.connectedComponents(seeds.view(np.uint8), connectivity=8)
                lut = np.zeros(n, bool)
                lut[labels[core]] = True
                lut[0] = False
                ext |= lut[labels] & cand
        ext &= ~core
        return ub, core, ext, disp, margin
