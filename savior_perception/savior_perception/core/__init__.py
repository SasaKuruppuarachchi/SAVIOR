# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Pure-python SAVIOR perception core (no rclpy imports; unit-testable)."""

from .calibration import (CameraModel, StereoRectifier, ideal_stereo, load_kalibr_imucam_chain,
                          stereo_from_kalibr)
from .config import (ComposeConfig, DepthConfig, ExtensionConfig, GatingConfig, PipelineConfig,
                     TrackerConfig)
from .gating import GatingResult, MotionEvidence, PromotionGate
from .pipeline import SaviorPipeline
from .roles import RoleTable
from .types import MASK_CORE, MASK_EXTENSION, MASK_KEEP, FrameResult, Instance

__all__ = [
    "CameraModel", "StereoRectifier", "ideal_stereo", "load_kalibr_imucam_chain", "stereo_from_kalibr",
    "ComposeConfig", "DepthConfig", "ExtensionConfig", "GatingConfig", "PipelineConfig", "TrackerConfig",
    "GatingResult", "MotionEvidence", "PromotionGate", "SaviorPipeline", "RoleTable",
    "MASK_CORE", "MASK_EXTENSION", "MASK_KEEP", "FrameResult", "Instance",
]
