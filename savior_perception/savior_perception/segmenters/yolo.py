# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Ultralytics YOLO instance segmentation backend (YOLO26-seg ``.pt`` or TensorRT ``.engine``).

``ultralytics`` (and torch) are imported lazily so the rest of the package works without them.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import cv2
import numpy as np

from ..core.types import Instance, mask_bbox
from .base import Segmenter


def _import_yolo():
    try:
        from ultralytics import YOLO  # noqa: WPS433 (lazy import on purpose)
    except ImportError as exc:  # pragma: no cover - depends on the image
        raise ImportError("segmenter.backend 'yolo' needs the 'ultralytics' package (project GPU "
                          "image); it is not installed in this environment") from exc
    return YOLO


class YoloSegmenter(Segmenter):
    def __init__(self, model: str, conf: float = 0.25, iou: float = 0.7, imgsz: int = 640,
                 device: Optional[str] = None, half: bool = False,
                 classes: Optional[Sequence[str]] = None, retina_masks: bool = True,
                 mask_threshold: float = 0.5, fast_masks: bool = False):
        if not model:
            raise ValueError("segmenter.model must point to a YOLO-seg .pt/.engine file")
        YOLO = _import_yolo()
        self.model = YOLO(model, task="segment")
        names = self.model.names
        self.names = dict(names) if isinstance(names, dict) else dict(enumerate(names))
        self.conf, self.iou, self.imgsz = float(conf), float(iou), int(imgsz)
        self.device = device or None
        self.half = bool(half)
        self.retina_masks = bool(retina_masks)
        self.mask_threshold = float(mask_threshold)
        # P7: transfer only the box crops of the native-resolution masks to the CPU (one masked_select on the GPU)
        # instead of n full HxW masks; bit-identical output (the masks are zero outside their boxes)
        self.fast_masks = bool(fast_masks)
        self.class_ids = None
        if classes:
            wanted = {c.strip().lower() for c in classes}
            self.class_ids = sorted(i for i, n in self.names.items() if str(n).lower() in wanted)

    def warmup(self, shape) -> None:
        h, w = shape[:2]
        self.predict(np.zeros((h, w, 3), np.uint8))

    def predict(self, image: np.ndarray) -> List[Instance]:
        img = image if (image.ndim == 3 and image.shape[2] == 3) else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        kwargs = dict(conf=self.conf, iou=self.iou, imgsz=self.imgsz,
                      retina_masks=self.retina_masks, verbose=False)
        if self.half:
            # only when asked: ultralytics 8.4 logs a deprecation warning for every call with `half`
            # (TensorRT engines carry their own precision anyway)
            kwargs["half"] = True
        if self.device is not None:
            kwargs["device"] = self.device
        if self.class_ids is not None:
            if not self.class_ids:
                return []
            kwargs["classes"] = self.class_ids
        res = self.model.predict(img, **kwargs)[0]
        if res.masks is None or len(res.boxes) == 0:
            return []
        data = res.masks.data
        if self.fast_masks and tuple(data.shape[1:]) == (h, w):
            return self._instances_fast(data, res.boxes, h, w)
        if tuple(data.shape[1:]) != (h, w):
            # masks at letterboxed inference resolution -> undo letterbox + resize
            from ultralytics.utils import ops  # lazy
            m = ops.scale_image(data.permute(1, 2, 0).float().cpu().numpy(), (h, w))
            masks = (m > self.mask_threshold).transpose(2, 0, 1)
        else:
            masks = (data > self.mask_threshold).cpu().numpy()
        boxes = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy().astype(int)
        conf = res.boxes.conf.cpu().numpy()
        out = []
        for i in range(masks.shape[0]):
            m = np.ascontiguousarray(masks[i])
            tb = mask_bbox(m)
            if tb is None:
                continue
            x0, y0, x1, y1 = boxes[i]
            bbox = (min(tb[0], x0), min(tb[1], y0), max(tb[2], x1), max(tb[3], y1))
            out.append(Instance(mask=m, cls=str(self.names[int(cls[i])]), score=float(conf[i]), bbox=bbox))
        return out

    def _instances_fast(self, data, boxes_res, h: int, w: int) -> List[Instance]:
        """P7 fast path: masks (n x h x w, GPU, native resolution) -> instances, copying only the pixels inside each
        detection box (floor/ceil rounded, clipped). Ultralytics crops every native mask to its box, so the result
        equals the full-frame path bit for bit (same masks, same bboxes, same order, empty masks dropped)."""
        import torch  # lazy (ultralytics is loaded)
        xyxy = boxes_res.xyxy.float().cpu().numpy()
        cls = boxes_res.cls.cpu().numpy().astype(int)
        conf = boxes_res.conf.cpu().numpy()
        n = xyxy.shape[0]
        bx = np.empty((n, 4), np.int64)
        bx[:, 0] = np.clip(np.floor(xyxy[:, 0]), 0, w)
        bx[:, 1] = np.clip(np.floor(xyxy[:, 1]), 0, h)
        bx[:, 2] = np.clip(np.ceil(xyxy[:, 2]), 0, w)
        bx[:, 3] = np.clip(np.ceil(xyxy[:, 3]), 0, h)
        bx[:, 2] = np.maximum(bx[:, 2], bx[:, 0])
        bx[:, 3] = np.maximum(bx[:, 3], bx[:, 1])
        tb = torch.from_numpy(bx).to(data.device)
        cols = torch.arange(w, device=data.device)
        rows = torch.arange(h, device=data.device)
        inx = (cols[None, :] >= tb[:, 0:1]) & (cols[None, :] < tb[:, 2:3])          # n x w
        iny = (rows[None, :] >= tb[:, 1:2]) & (rows[None, :] < tb[:, 3:4])          # n x h
        inside = iny[:, :, None] & inx[:, None, :]
        flat = torch.masked_select(data > self.mask_threshold, inside).cpu().numpy()
        areas = (bx[:, 2] - bx[:, 0]) * (bx[:, 3] - bx[:, 1])
        offs = np.concatenate([[0], np.cumsum(areas)])
        out = []
        for i in range(n):
            x0, y0, x1, y1 = (int(v) for v in bx[i])
            crop = flat[offs[i]:offs[i + 1]].reshape(y1 - y0, x1 - x0)
            if not crop.any():
                continue
            m = np.zeros((h, w), bool)
            m[y0:y1, x0:x1] = crop
            out.append(Instance(mask=m, cls=str(self.names[int(cls[i])]), score=float(conf[i]), bbox=(x0, y0, x1, y1)))
        return out
