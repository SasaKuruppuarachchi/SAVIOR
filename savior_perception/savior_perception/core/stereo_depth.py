# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""ROI stereo depth: SGBM only inside rectified crops around instances of interest.

Pipeline per frame:
  1. each raw work box (dilated bbox of a dynamic/potential instance) is mapped to a
     rectified box (sampling the raw->rect map on a grid that includes the box edges);
  2. the rectified box is extended to the left by the disparity search range, overlapping
     boxes are merged when that does not increase the matched area;
  3. both rectified crops are produced directly from the RAW images with ``cv2.remap`` on
     the (decimated) rect->raw sub-maps -- no full-frame rectification;
  4. SGBM disparity is written into a low-resolution rectified disparity frame, stored in
     FULL-resolution pixel units (0 = invalid / not computed);
  5. raw-domain disparity crops are sampled back with ``cv2.remap`` on the raw->rect map.

Noise model: sigma_z(z) = z^2 * sigma_d / (f * b).
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .calibration import StereoRectifier
from .config import DepthConfig
from .types import Box, box_slices


def _ceil16(x: float) -> int:
    return max(16, int(math.ceil(x / 16.0)) * 16)


class StereoDepth:
    def __init__(self, rect: StereoRectifier, cfg: DepthConfig):
        self.rect = rect
        self.cfg = cfg
        s = int(cfg.downsample)
        self.s = s
        rw, rh = rect.rect_size
        self.map_l = (np.ascontiguousarray(rect.rect_to_raw_x[0][::s, ::s]),
                      np.ascontiguousarray(rect.rect_to_raw_y[0][::s, ::s]))
        self.map_r = (np.ascontiguousarray(rect.rect_to_raw_x[1][::s, ::s]),
                      np.ascontiguousarray(rect.rect_to_raw_y[1][::s, ::s]))
        self.low_h, self.low_w = self.map_l[0].shape
        # raw (left) pixel -> low-res rectified coordinates (invalid stays hugely negative)
        self.r2r_low = (rect.raw_to_rect_x[0] / np.float32(s), rect.raw_to_rect_y[0] / np.float32(s))
        dmax_full = min(rect.fb / cfg.min_depth_m, float(cfg.max_disparity_px))
        self.num_disp = _ceil16(dmax_full / s)
        self.matcher = self._make_matcher()
        self.disp_low = np.zeros((self.low_h, self.low_w), np.float32)
        self.rois_low: List[Tuple[int, int, int, int]] = []
        self.matched_px = 0

    def _make_matcher(self):
        c = self.cfg
        bs = int(c.block_size)
        if c.matcher == "bm":
            m = cv2.StereoBM_create(numDisparities=self.num_disp, blockSize=max(5, bs))
            m.setUniquenessRatio(int(c.uniqueness_ratio))
            m.setSpeckleWindowSize(int(c.speckle_window))
            m.setSpeckleRange(int(c.speckle_range))
            m.setTextureThreshold(10)
            return m
        mode = cv2.STEREO_SGBM_MODE_SGBM_3WAY if c.matcher == "sgbm_3way" else cv2.STEREO_SGBM_MODE_SGBM
        return cv2.StereoSGBM_create(
            minDisparity=0, numDisparities=self.num_disp, blockSize=bs,
            P1=8 * bs * bs, P2=32 * bs * bs, disp12MaxDiff=1,
            uniquenessRatio=int(c.uniqueness_ratio), speckleWindowSize=int(c.speckle_window),
            speckleRange=int(c.speckle_range), mode=mode)

    # ------------------------------------------------------------------ geometry helpers
    @property
    def fb(self) -> float:
        return self.rect.fb

    def sigma_z(self, z: float) -> float:
        return float(z) ** 2 * self.cfg.sigma_d_px / self.rect.fb

    def depth_from_disparity(self, d: float) -> float:
        return self.rect.fb / d if d > 0 else math.nan

    def raw_box_to_rect_low(self, box: Box, n: int = 12) -> Optional[Tuple[int, int, int, int]]:
        x0, y0, x1, y1 = box
        if x1 <= x0 or y1 <= y0:
            return None
        xs = np.unique(np.linspace(x0, x1 - 1, n).astype(np.int32))
        ys = np.unique(np.linspace(y0, y1 - 1, n).astype(np.int32))
        u = self.r2r_low[0][np.ix_(ys, xs)]
        v = self.r2r_low[1][np.ix_(ys, xs)]
        ok = u > -1.0e3
        if not ok.any():
            return None
        pad = int(math.ceil(self.cfg.roi_pad_px / self.s))
        u0 = int(math.floor(u[ok].min())) - pad
        u1 = int(math.ceil(u[ok].max())) + 1 + pad
        v0 = int(math.floor(v[ok].min())) - pad
        v1 = int(math.ceil(v[ok].max())) + 1 + pad
        u0, u1 = max(0, u0), min(self.low_w, u1)
        v0, v1 = max(0, v0), min(self.low_h, v1)
        if u1 <= u0 or v1 <= v0:
            return None
        return u0, v0, u1, v1

    def _plan_rois(self, raw_boxes: Sequence[Box]):
        """Rectified (low-res) match regions: (x0_ext, y0, x1, y1, x0_keep)."""
        rois = []
        bs = int(self.cfg.block_size)
        for b in raw_boxes:
            rb = self.raw_box_to_rect_low(b)
            if rb is None:
                continue
            u0, v0, u1, v1 = rb
            xe = max(0, u0 - self.num_disp)
            if u1 - xe < self.num_disp + bs + 1:
                u1 = min(self.low_w, xe + self.num_disp + bs + 1)
            if v1 - v0 < bs + 2:
                continue
            rois.append([xe, v0, u1, v1, u0])
        # merge overlapping regions when that does not increase the matched area
        merged = True
        while merged and len(rois) > 1:
            merged = False
            for i in range(len(rois)):
                for j in range(i + 1, len(rois)):
                    a, b = rois[i], rois[j]
                    if a[0] >= b[2] or b[0] >= a[2] or a[1] >= b[3] or b[1] >= a[3]:
                        continue
                    u = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), min(a[4], b[4])]
                    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])  # noqa: E731
                    if area(u) <= area(a) + area(b):
                        rois[i] = u
                        del rois[j]
                        merged = True
                        break
                if merged:
                    break
        return rois

    # ------------------------------------------------------------------ per-frame
    def compute(self, left_gray: np.ndarray, right_gray: np.ndarray, raw_boxes: Sequence[Box]) -> dict:
        """Compute ROI disparity for this frame. Images: RAW uint8 grayscale."""
        self.disp_low.fill(0.0)
        rois = self._plan_rois(raw_boxes)
        self.rois_low = [tuple(r[:4]) for r in rois]
        px = 0
        for x0, y0, x1, y1, xk in rois:
            sl = (slice(y0, y1), slice(x0, x1))
            lc = cv2.remap(left_gray, self.map_l[0][sl], self.map_l[1][sl], cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            rc = cv2.remap(right_gray, self.map_r[0][sl], self.map_r[1][sl], cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            d16 = self.matcher.compute(lc, rc)
            k = xk - x0  # only keep columns that had the full disparity range available
            d = d16[:, k:].astype(np.float32) * (self.s / 16.0)
            d[d16[:, k:] <= 0] = 0.0
            self.disp_low[y0:y1, xk:x1] = d
            px += lc.size
        self.matched_px = px
        return {"n_rois": len(rois), "matched_px": px}

    def raw_disparity(self, box: Box) -> np.ndarray:
        """Disparity (full-res rectified px, 0=invalid) sampled at the RAW left pixels of `box`."""
        sl = box_slices(box)
        return cv2.remap(self.disp_low, self.r2r_low[0][sl], self.r2r_low[1][sl], cv2.INTER_NEAREST,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def robust_disparity(self, mask_crop: np.ndarray, disp_crop: np.ndarray) -> Tuple[float, int]:
        """Median valid disparity inside a (slightly eroded) mask. Returns (median, n_valid)."""
        valid = disp_crop > 0
        if self.cfg.mask_erode_px > 0:
            er = cv2.erode(mask_crop.view(np.uint8), np.ones((3, 3), np.uint8),
                           iterations=int(self.cfg.mask_erode_px)).view(bool)
            vals = disp_crop[er & valid]
            if vals.size >= self.cfg.min_valid_px:
                return float(np.median(vals)), int(vals.size)
        vals = disp_crop[mask_crop & valid]
        if vals.size < max(1, self.cfg.min_valid_px):
            return math.nan, int(vals.size)
        return float(np.median(vals)), int(vals.size)
