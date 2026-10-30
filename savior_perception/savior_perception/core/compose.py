# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Compose the layered RAW-image masks (0 keep / 192 extension / 255 core).

Left mask: extension bands first, then cores (core always wins). SAVIOR-SG (opt-in): kept movable-class objects are
written afterwards as a low value (``compose.movable_static_value``, e.g. 64) into the keep pixels only.

Right mask: the boundary of every masked left region is mapped raw-left -> rect-left
(exact map), shifted by its disparity (the per-pixel SGBM disparity when it is valid and
consistent with the instance depth band, else the instance median disparity), mapped
rect-right -> raw-right, and the warped polygons are filled (see :class:`RightWarper`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional

import cv2
import numpy as np

from .calibration import StereoRectifier
from .config import ComposeConfig
from .types import MASK_CORE, MASK_EXTENSION, MASK_KEEP, Box, Instance


@dataclass
class MaskItem:
    """One dynamic instance ready to be written into the masks."""
    box: Box                         # work box (raw left coords)
    core: np.ndarray                 # bool crop of `box`
    ext: np.ndarray                  # bool crop of `box` (disjoint from core)
    disp: Optional[np.ndarray]       # raw-domain disparity crop of `box` (0 invalid) or None
    d_med: float                     # instance median disparity (nan if unknown)
    d_lo: float = 0.0                # consistent per-pixel disparity band
    d_hi: float = math.inf
    right_band_only: bool = False    # P4 right fallback "band": write this instance into the right mask as 192 only


def compose_left(shape, items: Iterable[MaskItem]) -> np.ndarray:
    m = np.zeros(shape[:2], np.uint8)
    items = list(items)
    for it in items:
        x0, y0, x1, y1 = it.box
        m[y0:y1, x0:x1][it.ext] = MASK_EXTENSION
    for it in items:
        x0, y0, x1, y1 = it.box
        m[y0:y1, x0:x1][it.core] = MASK_CORE
    return m


def compose_region(shape, items: Iterable[MaskItem]) -> np.ndarray:
    """Boolean union of the `core` regions of `items` (SAVIOR-SG movable-static layer, left image)."""
    m = np.zeros(shape[:2], bool)
    for it in items:
        x0, y0, x1, y1 = it.box
        m[y0:y1, x0:x1] |= it.core
    return m


def overlay_keep(mask: np.ndarray, region: np.ndarray, value: int) -> None:
    """Write `value` into the keep (0) pixels of `mask` inside `region`; the 192 / 255 layers are never touched."""
    mask[region & (mask == MASK_KEEP)] = value


class RightWarper:
    """Warp layered left masks into the RAW right image.

    Each layer region (core, core+extension) of an instance is represented by its outer
    contours; every contour pixel is warped raw-left -> rect-left -> (shift by disparity)
    -> rect-right -> raw-right and the warped polygons are filled. This is exact for the
    region boundary (per-pixel disparity where valid & consistent with the instance depth
    band, else the instance median disparity) and costs O(perimeter) instead of O(area).
    Interior holes of a region are filled (conservative).
    """

    def __init__(self, rect: StereoRectifier, cfg: ComposeConfig):
        self.rect = rect
        self.cfg = cfg
        self.r2r_x, self.r2r_y = rect.raw_to_rect_x[0], rect.raw_to_rect_y[0]
        self.map_rx, self.map_ry = rect.rect_to_raw_x[1], rect.rect_to_raw_y[1]
        self.right_w, self.right_h = rect.cams[1].size
        self.rect_w, self.rect_h = rect.rect_size

    def warp_points(self, gx: np.ndarray, gy: np.ndarray, d: np.ndarray):
        """Raw-left integer pixels + disparity -> raw-right float coords (Nx2) and validity.

        Uses the rect-right -> raw-right lookup map inside the rectified frame. Points whose shifted
        rectified position falls outside that frame (or outside the valid part of the map) -- e.g. a near
        person at the fisheye periphery, beyond what the capped pinhole frame covers -- are projected
        analytically instead (rect-right ray -> cam1 -> fisheye model). Without this fallback such contours
        lost their outer points and the right mask degenerated to straight chords (P2 bug).
        """
        u = self.r2r_x[gy, gx]
        v = self.r2r_y[gy, gx]
        ur = u - d
        ui = np.rint(ur).astype(np.int32)
        vi = np.rint(v).astype(np.int32)
        base = (d > 0) & (u > -1e3)
        ok = base & (ui >= 0) & (ui < self.rect_w) & (vi >= 0) & (vi < self.rect_h)
        ui = np.where(ok, ui, 0)
        vi = np.where(ok, vi, 0)
        rx = self.map_rx[vi, ui].astype(np.float64)
        ry = self.map_ry[vi, ui].astype(np.float64)
        ok &= rx > -1e3
        miss = base & ~ok
        if miss.any():
            r = self.rect
            rays = np.column_stack([(ur[miss] - r.cx) / r.f, (v[miss] - r.cy) / r.f, np.ones(int(miss.sum()))])
            rays = rays @ r.R_rect[1]          # R1^T applied to row vectors: rect-right -> cam1
            front = rays[:, 2] > 1e-6          # in front of cam1 (projections outside the image are clipped by fillPoly)
            if front.any():
                pr = r.cams[1].project(rays[front])
                idx = np.flatnonzero(miss)[front]
                rx[idx] = pr[:, 0]
                ry[idx] = pr[:, 1]
                ok[idx] = True
        return np.column_stack([rx, ry]), ok

    def _polygons(self, it: MaskItem, region: np.ndarray):
        cs, _ = cv2.findContours(np.ascontiguousarray(region).view(np.uint8), cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_NONE)
        if not cs:
            return []
        has_med = math.isfinite(it.d_med) and it.d_med > 0
        if not has_med and it.disp is None:
            return []
        lens = [len(c) for c in cs]
        pts = np.concatenate(cs).reshape(-1, 2)
        xs, ys = pts[:, 0], pts[:, 1]
        if it.disp is not None:
            dp = it.disp[ys, xs]
            d = (np.where((dp >= it.d_lo) & (dp <= it.d_hi), dp, np.float32(it.d_med)) if has_med else dp)
        else:
            d = np.full(xs.shape, it.d_med, np.float32)
        out, ok = self.warp_points(xs + it.box[0], ys + it.box[1], d.astype(np.float32))
        polys = []
        start = 0
        for n in lens:
            sel = ok[start:start + n]
            if np.count_nonzero(sel) >= 3:
                polys.append(np.rint(out[start:start + n][sel]).astype(np.int32).reshape(-1, 1, 2))
            start += n
        return polys

    def warp(self, items: Iterable[MaskItem]) -> np.ndarray:
        m = np.zeros((self.right_h, self.right_w), np.uint8)
        ext_polys, core_polys = [], []
        for it in items:
            if it.right_band_only:
                ext_polys += self._polygons(it, it.core | it.ext)
                continue
            if it.ext.any():
                ext_polys += self._polygons(it, it.core | it.ext)
            core_polys += self._polygons(it, it.core)
        # one call per polygon: a multi-polygon fillPoly XORs overlapping polygons
        for p in ext_polys:
            cv2.fillPoly(m, [p], int(MASK_EXTENSION))
        for p in core_polys:
            cv2.fillPoly(m, [p], int(MASK_CORE))
        r = int(self.cfg.right_close_px)
        if r > 0 and (ext_polys or core_polys):
            k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
        return m

    def warp_region(self, items: Iterable[MaskItem]) -> np.ndarray:
        """Boolean right-image region of the `core` regions of `items` (same warp and closing as :meth:`warp`, on its
        own canvas so that it can not change the layered mask)."""
        m = np.zeros((self.right_h, self.right_w), np.uint8)
        polys = [p for it in items for p in self._polygons(it, it.core)]
        for p in polys:
            cv2.fillPoly(m, [p], 255)
        r = int(self.cfg.right_close_px)
        if r > 0 and polys:
            k = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
        return m > 0


_STATUS_COLORS = {"root": (0, 0, 255), "promoted": (0, 140, 255), "held": (255, 0, 255),
                  "carried": (255, 128, 0), "unpromoted": (0, 200, 0), "static": (160, 160, 160),
                  "still": (255, 255, 0)}


def render_overlay(image: np.ndarray, mask_left: np.ndarray, instances: List[Instance]) -> np.ndarray:
    """BGR debug overlay: core red, extension yellow, SAVIOR-SG movable-static (1..127) green, one label per instance."""
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image.copy() if image.shape[2] == 3 else cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    tint = bgr.copy()
    tint[mask_left == MASK_CORE] = (0, 0, 255)
    tint[mask_left == MASK_EXTENSION] = (0, 255, 255)
    tint[(mask_left > MASK_KEEP) & (mask_left < 128)] = (0, 200, 0)
    out = cv2.addWeighted(bgr, 0.55, tint, 0.45, 0)
    for inst in instances:
        x0, y0, x1, y1 = inst.bbox
        col = _STATUS_COLORS.get(inst.status, (255, 255, 255))
        cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), col, 1)
        z = f"{inst.depth:.1f}m" if math.isfinite(inst.depth) else "?m"
        tid = f"#{inst.track_id}" if inst.track_id >= 0 else ""
        mo = ""
        if inst.motion is not None:
            mo = f" l{inst.motion.get('l', 0):+.1f}"
            if "w_lat" in inst.motion:
                mo += f" w{inst.motion['w_lat']:.2f}/{inst.motion['w_rad']:+.2f}"
        cv2.putText(out, f"{inst.cls}{tid} {inst.status} {z}{mo}", (x0, max(10, y0 - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)
    return out
