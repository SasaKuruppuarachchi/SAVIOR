# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Segmentation backends and factory."""

from __future__ import annotations

from typing import Optional, Sequence

from .base import NullSegmenter, Segmenter

BACKENDS = ("none", "yolo", "oracle_uhumans2", "oracle_colormap")


def make_segmenter(backend: str, model: str = "", conf: float = 0.25, iou: float = 0.7,
                   imgsz: int = 640, device: str = "", half: bool = False,
                   classes: Optional[Sequence[str]] = None, colormap_file: str = "",
                   retina_masks: bool = True, fast_masks: bool = False) -> Segmenter:
    backend = (backend or "none").strip().lower()
    if backend == "none":
        return NullSegmenter()
    if backend == "yolo":
        from .yolo import YoloSegmenter
        return YoloSegmenter(model, conf=conf, iou=iou, imgsz=imgsz, device=device or None,
                             half=half, classes=classes, retina_masks=retina_masks,
                             fast_masks=fast_masks)
    if backend in ("oracle_uhumans2", "oracle_colormap"):
        if not colormap_file:
            raise ValueError(f"backend '{backend}' needs segmenter.colormap_file")
        from .oracle_colormap import OracleColormapSegmenter
        return OracleColormapSegmenter.from_yaml(colormap_file, keep_classes=classes)
    raise ValueError(f"unknown segmenter.backend '{backend}' (one of {BACKENDS})")


__all__ = ["BACKENDS", "NullSegmenter", "Segmenter", "make_segmenter"]
