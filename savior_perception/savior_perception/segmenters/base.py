# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Segmenter interface."""

from __future__ import annotations

import abc
from typing import List

import numpy as np

from ..core.types import Instance


class Segmenter(abc.ABC):
    """Instance segmentation on the RAW left image.

    ``predict`` returns instances whose masks are full-resolution boolean arrays in the
    coordinates of the input image and whose ``cls`` are the backend's class names (the
    names used in the class-role yaml).
    """

    #: True if the backend consumes an auxiliary (e.g. ground-truth semantic) image
    needs_aux_image: bool = False

    @abc.abstractmethod
    def predict(self, image: np.ndarray) -> List[Instance]:
        ...

    def warmup(self, shape) -> None:
        """Optional: run once on a dummy image (e.g. to build TensorRT/CUDA contexts)."""


class NullSegmenter(Segmenter):
    """Backend ``none``: never detects anything (all-zero masks; pipeline/timing tests)."""

    def predict(self, image: np.ndarray) -> List[Instance]:
        return []
