# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Oracle backend: colour-coded ground-truth semantic image -> instances.

Colour map yaml (supplied per dataset, e.g. uHumans2 ``seg_cam``)::

    encoding: rgb          # channel order of the colours listed below (rgb | bgr)
    tolerance: 0           # max per-channel absolute difference
    min_area_px: 30        # drop smaller connected components
    connectivity: 8        # 4 | 8
    instance_mode: components   # components (one instance per connected component) | class
    classes:
      person: [[255, 0, 0]]
      chair:  [[0, 255, 0], [0, 250, 0]]

``predict`` takes the semantic image in BGR channel order (the node converts ``rgb8``).
Touching objects of one class merge into one component (semantic, not instance, GT).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import yaml

from ..core.types import Instance
from .base import Segmenter


class OracleColormapSegmenter(Segmenter):
    needs_aux_image = True

    def __init__(self, classes: Dict[str, List[List[int]]], encoding: str = "rgb", tolerance: int = 0,
                 min_area_px: int = 30, connectivity: int = 8, instance_mode: str = "components",
                 keep_classes: Optional[List[str]] = None):
        if encoding not in ("rgb", "bgr"):
            raise ValueError("colormap encoding must be rgb|bgr")
        if instance_mode not in ("components", "class"):
            raise ValueError("instance_mode must be components|class")
        self.tolerance = int(tolerance)
        self.min_area_px = int(min_area_px)
        self.connectivity = int(connectivity)
        self.instance_mode = instance_mode
        self.colors: Dict[str, np.ndarray] = {}
        for name, cols in (classes or {}).items():
            arr = np.asarray(cols, dtype=np.int32).reshape(-1, 3)
            if encoding == "rgb":
                arr = arr[:, ::-1]
            self.colors[str(name)] = arr  # BGR
        if keep_classes is not None:
            # P4: only the classes the role table uses (dynamic + potential), like the YOLO class filter: the other
            # classes are never masked, so this only saves the per-frame colour match + connected components
            keep = set(keep_classes)
            self.colors = {k: v for k, v in self.colors.items() if k in keep}

    @classmethod
    def from_yaml(cls, path: str, keep_classes: Optional[List[str]] = None) -> "OracleColormapSegmenter":
        with open(path, "r") as fh:
            d = yaml.safe_load(fh) or {}
        return cls(classes=d.get("classes", {}), encoding=d.get("encoding", "rgb"),
                   tolerance=d.get("tolerance", 0), min_area_px=d.get("min_area_px", 30),
                   connectivity=d.get("connectivity", 8),
                   instance_mode=d.get("instance_mode", "components"),
                   keep_classes=list(keep_classes) if keep_classes is not None else None)

    def class_mask(self, bgr: np.ndarray, name: str) -> np.ndarray:
        cols = self.colors[name]
        if self.tolerance <= 0:
            key = (bgr[..., 0].astype(np.int32) << 16) | (bgr[..., 1].astype(np.int32) << 8) | bgr[..., 2]
            keys = (cols[:, 0] << 16) | (cols[:, 1] << 8) | cols[:, 2]
            if keys.size == 1:
                return key == keys[0]
            return np.isin(key, keys)
        m = np.zeros(bgr.shape[:2], bool)
        for c in cols:
            lo = np.clip(c - self.tolerance, 0, 255).astype(np.uint8)
            hi = np.clip(c + self.tolerance, 0, 255).astype(np.uint8)
            m |= cv2.inRange(bgr, lo, hi) != 0
        return m

    def predict(self, image: np.ndarray, target_shape: Optional[Tuple[int, int]] = None) -> List[Instance]:
        bgr = image if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        bgr = bgr[..., :3]
        if target_shape is not None and tuple(bgr.shape[:2]) != tuple(target_shape[:2]):
            bgr = cv2.resize(bgr, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_NEAREST)
        h, w = bgr.shape[:2]
        out = []
        for name in self.colors:
            cm = self.class_mask(bgr, name)
            if not cm.any():
                continue
            if self.instance_mode == "class":
                if np.count_nonzero(cm) >= self.min_area_px:
                    out.append(Instance(mask=cm, cls=name, score=1.0))
                continue
            n, labels, stats, _ = cv2.connectedComponentsWithStats(cm.view(np.uint8), connectivity=self.connectivity)
            for k in range(1, n):
                x, y, bw, bh, area = stats[k]
                if area < self.min_area_px:
                    continue
                m = np.zeros((h, w), bool)
                m[y:y + bh, x:x + bw] = labels[y:y + bh, x:x + bw] == k
                out.append(Instance(mask=m, cls=name, score=1.0, bbox=(x, y, x + bw, y + bh)))
        return out
