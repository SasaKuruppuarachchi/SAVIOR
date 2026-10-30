# SPDX-License-Identifier: GPL-3.0-or-later
"""Depth-guided extension: layer values, depth-adaptive margin, depth-consistent growth."""
import math

import numpy as np

from savior_perception.core import Instance, PipelineConfig, RoleTable, SaviorPipeline, ideal_stereo
from savior_perception.core.config import ExtensionConfig
from savior_perception.core.extension import MaskExtender
from savior_perception.core.synthetic import Plane, demo_scene, planes_to_instances, rect_mask, render_stereo

ROLES = RoleTable(dynamic=["person"], potential=["box", "chair", "suitcase"])


def test_margin_depth_adaptive():
    ext = MaskExtender(ExtensionConfig(margin_m=0.1, min_px=8, max_px=40), f=450.0, fb=49.5)
    assert ext.margin_px(0.5) == 40            # clamped high
    assert ext.margin_px(2.0) == round(450 * 0.1 / 2.0)
    assert ext.margin_px(10.0) == 8            # clamped to the KLT patch radius
    assert ext.margin_px(math.nan) == 8
    assert ext.margin_px(1.5) > ext.margin_px(3.0)
    # depth band (adaptive) widens with range, fixed band does not
    assert ext.band(6.0) > ext.band(2.0)
    fixed = MaskExtender(ExtensionConfig(band_mode="fixed", fixed_band_m=0.5), f=450.0, fb=49.5)
    assert fixed.band(2.0) == fixed.band(6.0) == 0.5


def test_layer_values():
    rect = ideal_stereo(640, 480, 450.0, 0.11)
    left, right, planes = demo_scene(640, 480, rect.fb)
    pipe = SaviorPipeline(PipelineConfig(), ROLES, rect)
    ml, mr, _ = pipe.process(left, right, 0, planes_to_instances(planes))
    for m in (ml, mr):
        assert m.dtype == np.uint8
        assert set(np.unique(m).tolist()) == {0, 192, 255}


def test_growth_only_where_depth_consistent():
    """Under-segmented person: the unsegmented legs (same depth) are grown into the 192 band,
    an adjacent box at a different depth inside the expanded bbox is not."""
    W, H = 640, 480
    rect = ideal_stereo(W, H, 450.0, 0.11)
    person_full = rect_mask(H, W, (250, 60, 330, 420))      # true person extent, z = 2 m
    box = rect_mask(H, W, (330, 300, 420, 420))             # adjacent box, z = 3.5 m
    left, right = render_stereo(W, H, rect.fb, 8.0, [Plane(person_full, 2.0), Plane(box, 3.5)], seed=11)
    seg = rect_mask(H, W, (250, 60, 330, 280))              # segmenter only got the upper body
    cfg = PipelineConfig()
    cfg.extension.bbox_expand = 0.6                          # generous growth region
    cfg.extension.margin_m = 0.0                             # -> min_px ring only
    cfg.extension.min_px = 6
    cfg.tracker.enable = False
    pipe = SaviorPipeline(cfg, ROLES, rect)
    inst = Instance.from_mask(seg, "person")
    ml, _, _ = pipe.process(left, right, 0, [inst])
    assert abs(inst.depth - 2.0) < 0.1
    legs = ml[300:400, 262:318]                              # beyond the 6 px ring, same depth
    assert (legs == 192).mean() > 0.9
    box_far = ml[320:410, 350:410]                           # beyond the ring, different depth
    assert (box_far == 0).mean() > 0.97
    # without growth the legs stay unmasked
    cfg2 = cfg.copy(**{"extension.grow": False})
    ml2, _, _ = SaviorPipeline(cfg2, ROLES, rect).process(left, right, 0, [Instance.from_mask(seg, "person")])
    assert (ml2[300:400, 262:318] == 0).all()
    # and the ring is exactly min_px wide around the core
    assert (ml2[60:280, 244:250] == 192).all() and (ml2[60:280, 236:242] == 0).all()
