# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Synthetic rectified stereo scenes (textured fronto-parallel planes) for tests/benchmarks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .types import Instance


def texture(h: int, w: int, rng: np.random.Generator, blur: float = 1.2) -> np.ndarray:
    t = rng.integers(0, 256, size=(h, w), dtype=np.uint8)
    if blur > 0:
        t = cv2.GaussianBlur(t, (0, 0), blur)
        t = cv2.normalize(t, None, 0, 255, cv2.NORM_MINMAX)
    return t


def shift_x(img: np.ndarray, dx: float, interp=cv2.INTER_LINEAR) -> np.ndarray:
    """out(x, y) = img(x - dx, y)."""
    h, w = img.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(img, M, (w, h), flags=interp, borderMode=cv2.BORDER_REFLECT)


def rect_mask(h: int, w: int, box) -> np.ndarray:
    m = np.zeros((h, w), bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def ellipse_mask(h: int, w: int, center, axes) -> np.ndarray:
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (int(center[0]), int(center[1])), (int(axes[0]), int(axes[1])), 0, 0, 360, 1, -1)
    return m.astype(bool)


@dataclass
class Plane:
    mask: np.ndarray     # bool, region in the LEFT image
    z: float             # depth [m]
    cls: str = ""


def render_stereo(width: int, height: int, fb: float, background_z: float, planes: Sequence[Plane],
                  seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """Render a rectified (left, right) uint8 pair. Disparity of a plane = fb / z."""
    rng = np.random.default_rng(seed)
    left = texture(height, width, rng)
    right = shift_x(left, -fb / background_z)
    for p in sorted(planes, key=lambda p: -p.z):  # far to near (painter's order)
        tex = texture(height, width, rng)
        d = fb / p.z
        left[p.mask] = tex[p.mask]
        mr = shift_x(p.mask.astype(np.uint8), -d, cv2.INTER_NEAREST).astype(bool)
        tr = shift_x(tex, -d)
        right[mr] = tr[mr]
    return left, right


def demo_scene(width: int = 640, height: int = 480, fb: float = 50.0, seed: int = 0,
               n_people: int = 2, n_objects: int = 3, f: float = 450.0):
    """Busy scene: people at 2-3 m, potential objects (some touching people), wall at 8 m.

    Positions scale with the image size, object sizes with the focal length `f` (so a
    wide-angle camera sees smaller objects, as it would in reality).
    """
    rng = np.random.default_rng(seed)
    planes: List[Plane] = []
    sx, sy = width / 640.0, height / 480.0
    k_f = f / 450.0
    for k in range(n_people):
        z = 2.0 + 1.0 * k
        cx, cy = (150 + 260 * k) * sx, 250 * sy
        planes.append(Plane(ellipse_mask(height, width, (cx, cy), (0.25 * f / z, 0.85 * f / z)), z, "person"))
    for k in range(n_objects):
        z = [2.2, 3.1, 6.5][k % 3]
        cls = ["suitcase", "chair", "suitcase"][k % 3]
        x0 = int((70 + 180 * k + rng.integers(0, 30)) * sx)
        y0 = int((300 + rng.integers(0, 40)) * sy)
        bw, bh = int(110 * k_f * 2.5 / z), int(90 * k_f * 2.5 / z)
        planes.append(Plane(rect_mask(height, width, (x0, y0, x0 + bw, y0 + bh)), z, cls))
    left, right = render_stereo(width, height, fb, 8.0, planes, seed=seed)
    return left, right, planes


def planes_to_instances(planes: Sequence[Plane], visible_only: bool = True) -> List[Instance]:
    """Instances (visible part of each plane, nearer planes occlude farther ones)."""
    out = []
    occl: Optional[np.ndarray] = None
    for p in sorted(planes, key=lambda p: p.z):
        m = p.mask.copy()
        if visible_only and occl is not None:
            m &= ~occl
        occl = p.mask.copy() if occl is None else (occl | p.mask)
        if m.any():
            out.append(Instance.from_mask(m, p.cls))
    return out


def rect_to_raw_image(rect, img_rect: np.ndarray, cam: int, interp=cv2.INTER_LINEAR) -> np.ndarray:
    """Re-distort a rectified image of camera `cam` into its RAW image (synthetic data)."""
    return cv2.remap(img_rect, rect.raw_to_rect_x[cam], rect.raw_to_rect_y[cam], interp,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def plane_right_mask_rect(rect, plane: Plane) -> np.ndarray:
    """Where a (left-rect) plane appears in the right rectified image (ignoring occlusion)."""
    return shift_x(plane.mask.astype(np.uint8), -rect.fb / plane.z, cv2.INTER_NEAREST).astype(bool)


def raw_scene(rect, planes_rect: Sequence[Plane], background_z: float = 8.0, seed: int = 0):
    """Render planes defined in the LEFT RECTIFIED image into a RAW (distorted) stereo pair.

    Returns (left_raw, right_raw, planes_raw) where planes_raw carry raw-left masks.
    """
    rw, rh = rect.rect_size
    lr, rr = render_stereo(rw, rh, rect.fb, background_z, planes_rect, seed=seed)
    left = rect_to_raw_image(rect, lr, 0)
    right = rect_to_raw_image(rect, rr, 1)
    planes_raw = [Plane(rect_to_raw_image(rect, p.mask.astype(np.uint8), 0, cv2.INTER_NEAREST).astype(bool),
                        p.z, p.cls) for p in planes_rect]
    return left, right, planes_raw


def raw_planes_to_rect(rect, planes_raw: Sequence[Plane]) -> List[Plane]:
    """Planes defined by RAW-left masks -> the same planes in the left rectified image."""
    out = []
    for p in planes_raw:
        m = cv2.remap(p.mask.astype(np.uint8), rect.rect_to_raw_x[0], rect.rect_to_raw_y[0],
                      cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out.append(Plane(m.astype(bool), p.z, p.cls))
    return out


def demo_scene_raw(rect, seed: int = 0, n_people: int = 2, n_objects: int = 3):
    """demo_scene laid out in RAW image coordinates, rendered through the real calibration."""
    w, h = rect.cams[0].size
    f = float(rect.cams[0].K[0, 0])
    _, _, planes = demo_scene(w, h, rect.fb, seed=seed, n_people=n_people, n_objects=n_objects, f=f)
    planes_rect = raw_planes_to_rect(rect, planes)
    left, right, planes_raw = raw_scene(rect, planes_rect, seed=seed)
    return left, right, planes_raw, planes_rect


# ------------------------------------------------------------------------------------------------ P4: 3D scenes
@dataclass
class TexturedPlane:
    """A textured planar patch in the world: texture pixel (u, v) is at X0 + u*e1 + v*e2 [m]."""
    tex: np.ndarray
    X0: np.ndarray
    e1: np.ndarray
    e2: np.ndarray
    cls: str = ""
    vel: Optional[np.ndarray] = None   # world velocity [m/s] (None = static)

    def at(self, t: float) -> "TexturedPlane":
        if self.vel is None:
            return self
        return TexturedPlane(self.tex, self.X0 + self.vel * t, self.e1, self.e2, self.cls, self.vel)

    @property
    def center(self) -> np.ndarray:
        h, w = self.tex.shape[:2]
        return self.X0 + 0.5 * w * self.e1 + 0.5 * h * self.e2


def fronto_plane(center, width_m: float, height_m: float, px_m: float, rng, cls: str = "", vel=None,
                 blur: float = 2.0) -> TexturedPlane:
    """Plane facing the camera (normal -z in the world = cam0 at t=0), texture of px_m metres per pixel."""
    w, h = max(4, int(round(width_m / px_m))), max(4, int(round(height_m / px_m)))
    tex = texture(h, w, rng, blur=blur)
    c = np.asarray(center, dtype=np.float64)
    X0 = c - np.array([0.5 * width_m, 0.5 * height_m, 0.0])
    return TexturedPlane(tex, X0, np.array([px_m, 0.0, 0.0]), np.array([0.0, px_m, 0.0]), cls,
                         None if vel is None else np.asarray(vel, dtype=np.float64))


def render_planes(K: np.ndarray, size, R: np.ndarray, t: np.ndarray, planes: Sequence[TexturedPlane]):
    """Render planes seen by a pinhole camera X_c = R X_w + t. Returns (gray uint8, visible masks per plane)."""
    w, h = size
    img = np.zeros((h, w), np.uint8)
    order = sorted(range(len(planes)), key=lambda i: -(R @ planes[i].center + t)[2])
    full = [None] * len(planes)
    for i in order:
        P = planes[i]
        H = K @ np.column_stack([R @ P.e1, R @ P.e2, R @ P.X0 + t])
        H = H / H[2, 2]
        wimg = cv2.warpPerspective(P.tex, H, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
        m = cv2.warpPerspective(np.ones(P.tex.shape[:2], np.uint8), H, (w, h), flags=cv2.INTER_NEAREST,
                                borderValue=0).astype(bool)
        img[m] = wimg[m]
        full[i] = m
    vis = []
    for k, i in enumerate(order):
        m = full[i].copy()
        for j in order[k + 1:]:
            m &= ~full[j]
        vis.append((i, m))
    vis = [m for _, m in sorted(vis)]
    return img, vis


def rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def render_stereo_sequence(rect, planes: Sequence[TexturedPlane], n: int, fps: float, yaw_rate: float = 0.0,
                           cam_vel=(0.0, 0.0, 0.0)):
    """Ideal (rect == raw) stereo sequence; camera yawing at `yaw_rate` [rad/s] and moving at `cam_vel` [m/s, world].

    Yields dicts: stamp, left, right, masks (visible, per plane), R_imu (= R_{I_{k-1} I_k} with IMU == cam0;
    None for the first frame), R (world->cam0), c (camera centre).
    """
    K = rect.cams[0].K
    size = rect.cams[0].size
    b = rect.baseline
    R_prev = None
    for k in range(n):
        tk = k / fps
        R = rot_y(yaw_rate * tk)
        c = np.asarray(cam_vel, dtype=np.float64) * tk
        t = -R @ c
        pl = [p.at(tk) for p in planes]
        left, masks = render_planes(K, size, R, t, pl)
        right, _ = render_planes(K, size, R, t - np.array([b, 0.0, 0.0]), pl)
        R_imu = None if R_prev is None else R_prev @ R.T
        R_prev = R
        yield {"stamp": tk, "left": left, "right": right, "masks": masks, "R_imu": R_imu, "R": R, "c": c}
