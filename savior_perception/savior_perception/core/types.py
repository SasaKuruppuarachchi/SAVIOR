# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Plain data types shared by the SAVIOR perception core (no ROS imports)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# Mask layer values (see docs/IMPLEMENTATION_PLAN.md §3.1).
MASK_KEEP = 0
MASK_EXTENSION = 192
MASK_CORE = 255
# SAVIOR-SG (semantic chi2 gate, opt-in via compose.movable_static_value): movable-class object currently classified
# static, i.e. kept. Below every rejection threshold (128 / 224), so consumers that threshold the mask are unaffected.
MASK_MOVABLE_STATIC = 64

# Class roles (§3.4).
ROLE_DYNAMIC = "dynamic"
ROLE_POTENTIAL = "potential"
ROLE_STATIC = "static"
ROLE_IGNORE = "ignore"
ROLES = (ROLE_DYNAMIC, ROLE_POTENTIAL, ROLE_STATIC, ROLE_IGNORE)

# Per-frame instance status after classification / tracking.
STATUS_ROOT = "root"            # always-dynamic instance detected this frame
STATUS_PROMOTED = "promoted"    # potential instance linked to a dynamic chain this frame
STATUS_HELD = "held"            # potential instance kept dynamic by chain hysteresis
STATUS_CARRIED = "carried"      # mask predicted by the tracker (no detection this frame)
STATUS_UNPROMOTED = "unpromoted"  # potential instance classified static this frame
STATUS_STATIC = "static"        # static / ignored class, never masked
STATUS_STILL = "still"          # always-dynamic instance with confident "not moving" motion evidence (P4):
                                # not a promotion root, unmasked (motion.still_policy=unmask) or band-only (band)
STATUS_UNCERTAIN = "uncertain"  # P7 selective policy: potential instance whose motion state is unknown / not confirmed
                                # static (conservative default): masked, but not a promotion parent
DYNAMIC_STATUSES = (STATUS_ROOT, STATUS_PROMOTED, STATUS_HELD, STATUS_CARRIED, STATUS_UNCERTAIN)

Box = Tuple[int, int, int, int]  # (x0, y0, x1, y1), integer pixels, x1/y1 exclusive


def mask_bbox(mask: np.ndarray) -> Optional[Box]:
    """Tight integer bbox (x1/y1 exclusive) of a boolean mask, or None if empty."""
    cols = np.flatnonzero(mask.any(axis=0))
    if cols.size == 0:
        return None
    rows = np.flatnonzero(mask.any(axis=1))
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def clip_box(box, width: int, height: int) -> Box:
    """Round a (possibly float) box outwards and clip it to the image."""
    x0, y0, x1, y1 = box
    x0 = max(0, min(width, int(math.floor(x0))))
    y0 = max(0, min(height, int(math.floor(y0))))
    x1 = max(x0, min(width, int(math.ceil(x1))))
    y1 = max(y0, min(height, int(math.ceil(y1))))
    return x0, y0, x1, y1


def expand_box(box: Box, pad: int, ratio: float, width: int, height: int) -> Box:
    """Expand a box by `ratio` of its size plus `pad` pixels on every side (clipped)."""
    x0, y0, x1, y1 = box
    px = pad + int(math.ceil(ratio * (x1 - x0)))
    py = pad + int(math.ceil(ratio * (y1 - y0)))
    return clip_box((x0 - px, y0 - py, x1 + px, y1 + py), width, height)


def box_area(box: Box) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def box_intersection(a: Box, b: Box) -> Optional[Box]:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def box_iou(a: Box, b: Box) -> float:
    inter = box_intersection(a, b)
    if inter is None:
        return 0.0
    ia = box_area(inter)
    return ia / float(box_area(a) + box_area(b) - ia)


def box_slices(box: Box):
    return slice(box[1], box[3]), slice(box[0], box[2])


@dataclass(eq=False)
class Instance:
    """One segmented object in the RAW left image.

    `mask` is a full-frame boolean HxW array; `bbox` must contain every True pixel
    (it is computed from the mask when not given). Fields below `role` are filled
    by the pipeline.
    """

    mask: np.ndarray
    cls: str
    score: float = 1.0
    bbox: Optional[Box] = None
    role: Optional[str] = None
    # --- filled by the pipeline ---
    disparity: float = math.nan     # robust (median) rectified disparity [px, full-res]
    depth: float = math.nan         # z = f*b/disparity [m]
    sigma_z: float = math.nan       # stereo depth std at `depth` [m]
    n_depth_px: int = 0             # number of valid disparity pixels used
    status: str = ""                # one of STATUS_*
    parent: int = -1                # index (in the frame's instance list) of the promoting parent
    track_id: int = -1
    motion: Optional[dict] = field(default=None, repr=False)   # P4 motion evidence summary (core/motion.py)
    # internal per-frame scratch (work box and its raw-domain disparity crop)
    work_box: Optional[Box] = field(default=None, repr=False)
    depth_box: Optional[Box] = field(default=None, repr=False)
    disp_crop: Optional[np.ndarray] = field(default=None, repr=False)
    win: Optional[dict] = field(default=None, repr=False)     # P7: windowed anchor velocity (co-motion gate)

    def __post_init__(self):
        if self.mask.dtype != np.bool_:
            self.mask = self.mask.astype(bool)
        h, w = self.mask.shape[:2]
        if self.bbox is None:
            bb = mask_bbox(self.mask)
            self.bbox = bb if bb is not None else (0, 0, 0, 0)
        else:
            self.bbox = clip_box(self.bbox, w, h)

    @classmethod
    def from_mask(cls, mask: np.ndarray, cls_name: str, score: float = 1.0,
                  role: Optional[str] = None) -> "Instance":
        return cls(mask=mask.astype(bool), cls=cls_name, score=score, role=role)

    @property
    def shape(self) -> Tuple[int, int]:
        return self.mask.shape[:2]

    @property
    def area(self) -> int:
        return int(self.mask[box_slices(self.bbox)].sum())

    def crop(self, box: Optional[Box] = None) -> np.ndarray:
        """Mask restricted to `box` (default: own bbox); a view, do not modify."""
        return self.mask[box_slices(self.bbox if box is None else box)]

    @property
    def is_dynamic(self) -> bool:
        return self.status in DYNAMIC_STATUSES

    def summary(self) -> dict:
        def f(v):
            return None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 4)
        return {
            "cls": self.cls, "score": f(self.score), "role": self.role, "status": self.status,
            "bbox": list(self.bbox), "depth": f(self.depth), "sigma_z": f(self.sigma_z),
            "disparity": f(self.disparity), "parent": self.parent, "track_id": self.track_id,
            **({"motion": self.motion} if self.motion is not None else {}),
        }


@dataclass
class FrameResult:
    """Everything the pipeline produced for one frame (for debug overlay / eval)."""

    stamp: object
    mask_left: np.ndarray
    mask_right: Optional[np.ndarray]
    instances: List[Instance]                    # detections (with status) + carried instances
    links: List[Tuple[int, int]]                 # (child_idx, parent_idx) interaction-tree edges
    timings_ms: Dict[str, float]
    stats: Dict[str, object]
