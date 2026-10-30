# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic stereo: textured fronto-parallel planes at known depths."""
import math

import numpy as np
import pytest

from conftest import calib_path
from savior_perception.core import (DepthConfig, Instance, PipelineConfig, RoleTable, SaviorPipeline,
                                    ideal_stereo, stereo_from_kalibr)
from savior_perception.core.stereo_depth import StereoDepth
from savior_perception.core.synthetic import (Plane, ellipse_mask, plane_right_mask_rect, raw_planes_to_rect,
                                              raw_scene, rect_mask, rect_to_raw_image, render_stereo)

ROLES = RoleTable(dynamic=["person"], potential=["box", "chair"])


def _scene(rect):
    """Person + box laid out in RAW-left coordinates, returned as LEFT-RECTIFIED planes."""
    w, h = rect.cams[0].size
    sx, sy = w / 640.0, h / 480.0
    person = Plane(ellipse_mask(h, w, (220 * sx, 230 * sy), (50 * sx, 130 * sy)), 2.0, "person")
    box = Plane(rect_mask(h, w, (int(380 * sx), int(220 * sy), int(470 * sx), int(310 * sy))), 4.0, "box")
    return raw_planes_to_rect(rect, [person, box])


@pytest.mark.parametrize("downsample", [1, 2])
def test_roi_depth_ideal(downsample):
    rect = ideal_stereo(640, 480, 450.0, 0.11)
    planes = _scene(rect)
    left, right = render_stereo(640, 480, rect.fb, 8.0, planes, seed=3)
    sd = StereoDepth(rect, DepthConfig(downsample=downsample))
    insts = [Instance.from_mask(p.mask, p.cls) for p in planes]
    sd.compute(left, right, [i.bbox for i in insts])
    for inst, p in zip(insts, planes):
        disp = sd.raw_disparity(inst.bbox)
        d, n = sd.robust_disparity(inst.crop(), disp)
        z = rect.fb / d
        sz = sd.sigma_z(p.z)
        assert n > 500
        assert abs(z - p.z) < max(3 * sz, 0.02 * p.z), (p.cls, z, p.z, sz)
    # only ROI pixels were matched
    assert sd.matched_px < 0.8 * (640 * 480) / downsample ** 2


def test_noise_model():
    rect = ideal_stereo(640, 480, 450.0, 0.11)
    sd = StereoDepth(rect, DepthConfig(sigma_d_px=1.0))
    assert math.isclose(sd.sigma_z(2.0), 4.0 / rect.fb)
    assert sd.sigma_z(6.0) / sd.sigma_z(2.0) == pytest.approx(9.0)


@pytest.mark.parametrize("name", ["euroc", "t265"])
def test_roi_depth_distorted(name):
    """Full raw -> rect -> SGBM -> raw chain on re-distorted synthetic images."""
    rect = stereo_from_kalibr(calib_path(name))
    planes_rect = _scene(rect)
    left, right, planes_raw = raw_scene(rect, planes_rect, seed=5)
    cfg = PipelineConfig()
    cfg.depth.downsample = 1 if name == "t265" else 2
    pipe = SaviorPipeline(cfg, ROLES, rect)
    insts = [Instance.from_mask(p.mask, p.cls) for p in planes_raw]
    ml, mr, st = pipe.process(left, right, 0.0, insts)
    for inst, p in zip(insts, planes_raw):
        sz = rect.sigma_z(p.z, cfg.depth.sigma_d_px)
        assert abs(inst.depth - p.z) < max(3 * sz, 0.03 * p.z), (name, p.cls, inst.depth, p.z)


@pytest.mark.parametrize("name", ["ideal", "euroc", "t265"])
def test_right_mask_lands_on_object(name):
    rect = ideal_stereo(640, 480, 450.0, 0.11) if name == "ideal" else stereo_from_kalibr(calib_path(name))
    planes_rect = _scene(rect)
    left, right, planes_raw = raw_scene(rect, planes_rect, seed=7)
    cfg = PipelineConfig()
    cfg.extension.enable = False
    cfg.tracker.enable = False
    cfg.depth.downsample = 1 if name == "t265" else 2
    pipe = SaviorPipeline(cfg, ROLES, rect)
    person = planes_raw[0]
    ml, mr, st = pipe.process(left, right, 0.0, [Instance.from_mask(person.mask, "person")])
    assert mr.shape == right.shape[:2] and mr.dtype == np.uint8
    gt_right_rect = plane_right_mask_rect(rect, planes_rect[0]).astype(np.uint8)
    gt_right_raw = rect_to_raw_image(rect, gt_right_rect, 1, interp=0).astype(bool)
    pred = mr == 255
    iou = (pred & gt_right_raw).sum() / float((pred | gt_right_raw).sum())
    # the naive "copy the left mask" would be far off (disparity ~ f*b/2m)
    naive = person.mask
    iou_naive = (naive & gt_right_raw).sum() / float((naive | gt_right_raw).sum())
    assert iou > 0.93, (name, iou)
    assert iou > iou_naive + 0.05


def test_right_mask_median_fallback():
    """Without per-pixel disparity the right mask is the left mask shifted by the median."""
    from savior_perception.core.compose import MaskItem, RightWarper
    from savior_perception.core.config import ComposeConfig
    rect = ideal_stereo(200, 100, 100.0, 0.1)
    w = RightWarper(rect, ComposeConfig())
    core = np.zeros((100, 200), bool)
    core[20:60, 100:140] = True
    item = MaskItem(box=(0, 0, 200, 100), core=core, ext=np.zeros_like(core), disp=None, d_med=10.0)
    m = w.warp([item])
    assert (m[20:60, 90:130] == 255).all() and m.sum() == 255 * 40 * 40


def test_right_mask_fisheye_periphery_near_object():
    """P2 bug: a near object at the T265 fisheye periphery lies (partly) outside the capped rectified frame;
    its warped contour lost those points and the right mask degenerated to straight chords. The analytic
    rect-right -> cam1 projection must reproduce the true right-image footprint."""
    import cv2
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.compose import MaskItem, RightWarper
    from savior_perception.core.config import ComposeConfig
    rect = stereo_from_kalibr(calib_path("t265"), focal_scale=0.7)
    z = 0.6
    # 1.4 x 0.6 m fronto-parallel patch 73..80 deg off-axis: beyond the capped (2x raw) rectified frame
    xs, ys = np.meshgrid(np.linspace(2.0, 3.4, 80), np.linspace(-0.3, 0.3, 40))
    X = np.column_stack([xs.ravel(), ys.ravel(), np.full(xs.size, z)])
    raw0, raw1, _, _ = rect.project_cam0_point(X)
    (w0, h0), (w1, h1) = rect.cams[0].size, rect.cams[1].size

    def footprint(pts, w, h):
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [cv2.convexHull(np.rint(pts).astype(np.int32))], 1)
        return m.astype(bool)
    left, gt = footprint(raw0, w0, h0), footprint(raw1, w1, h1)
    assert left.sum() > 2000 and gt.sum() > 2000
    # most of the shifted footprint must be outside the rectified frame for this test to be meaningful
    u = rect.raw_to_rect_x[0][left]
    assert ((u - rect.fb / z) >= rect.rect_size[0]).mean() > 0.3
    d = rect.fb / z
    item = MaskItem(box=(0, 0, w0, h0), core=left, ext=np.zeros_like(left), disp=None, d_med=d)
    pred = RightWarper(rect, ComposeConfig()).warp([item]) == 255
    iou = (pred & gt).sum() / float((pred | gt).sum())
    assert iou > 0.85, iou
