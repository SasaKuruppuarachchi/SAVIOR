# SPDX-License-Identifier: GPL-3.0-or-later
"""Sim-to-real photometric augmentation for YOLO26-seg fine-tuning on SAVIOR-Warehouse (numpy / OpenCV only).

The SAVIOR Docker image has no `albumentations`, so Ultralytics' built-in Albumentations stage (Blur / MedianBlur /
ToGray / CLAHE at p = 0.01) is a silent no-op there. `install()` replaces that stage (it sits after mosaic /
random_perspective / MixUp and before RandomHSV / flip in `v8_transforms`) with `SimRealAug`, which degrades the
clean Isaac Sim renders towards what a real ZED 2i stream and the SAVIOR node input look like. Image-only (no
geometry change), so labels are untouched. Every effect is drawn independently per training sample:

| effect                 | p    | parameters                    | why                                                      |
|------------------------|------|-------------------------------|----------------------------------------------------------|
| grayscale (BT.601)     | 0.50 | luma replicated to 3 ch.      | savior_node feeds YOLO the mono8 /cam0/image_raw (GRAY2BGR) |
| motion blur            | 0.20 | line kernel 3-9 px, any angle | drone: 89 deg/s yaw x ~10 ms exposure at fx 470 = ~7 px     |
| Gaussian (defocus) blur| 0.15 | sigma 0.3-1.2 px              | optics / focus, renders are perfectly sharp               |
| downscale-upscale      | 0.10 | factor 0.5-0.8                | resolution loss, debayering softness                      |
| gamma + contrast       | 0.25 | gamma 0.7-1.5, gain 0.8-1.2   | auto-exposure / tone curve (renders: fixed exposure)      |
| sensor noise           | 0.40 | sigma 2-8 DN (+ shot term), 50 % luma-correlated | renders are noise-free                 |
| JPEG re-compression    | 0.20 | quality 40-90                 | compressed camera streams                                 |

The renders already have per-frame light jitter and 3 lighting presets; RandomHSV (hsv_h/s/v) stays on top.
"""
from __future__ import annotations

import random

import cv2
import numpy as np

DEFAULT = dict(gray=0.5, motion_blur=0.2, gauss_blur=0.15, downscale=0.10, gamma=0.25, noise=0.4, jpeg=0.2)


def _motion_kernel(k: int, angle_deg: float) -> np.ndarray:
    ker = np.zeros((k, k), np.float32)
    ker[k // 2, :] = 1.0
    M = cv2.getRotationMatrix2D((k / 2 - 0.5, k / 2 - 0.5), angle_deg, 1.0)
    ker = cv2.warpAffine(ker, M, (k, k))
    return ker / max(ker.sum(), 1e-6)


def degrade(img: np.ndarray, probs: dict | None = None, rng: np.random.Generator | None = None) -> np.ndarray:
    """Apply the SimRealAug chain to one BGR uint8 image (returns a new array)."""
    p = {**DEFAULT, **(probs or {})}
    rng = rng or np.random.default_rng(random.getrandbits(63))
    im = img
    if rng.random() < p['gray']:
        im = cv2.cvtColor(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    if rng.random() < p['motion_blur']:
        k = int(rng.integers(3, 10)) | 1
        im = cv2.filter2D(im, -1, _motion_kernel(k, float(rng.uniform(0, 180))))
    if rng.random() < p['gauss_blur']:
        im = cv2.GaussianBlur(im, (0, 0), float(rng.uniform(0.3, 1.2)))
    if rng.random() < p['downscale']:
        h, w = im.shape[:2]
        f = float(rng.uniform(0.5, 0.8))
        im = cv2.resize(cv2.resize(im, (max(1, int(w * f)), max(1, int(h * f))), interpolation=cv2.INTER_AREA),
                        (w, h), interpolation=cv2.INTER_LINEAR)
    if rng.random() < p['gamma']:
        g, c = float(rng.uniform(0.7, 1.5)), float(rng.uniform(0.8, 1.2))
        lut = np.clip(((np.arange(256) / 255.0) ** g - 0.5) * c * 255.0 + 127.5, 0, 255).astype(np.uint8)
        im = cv2.LUT(im, lut)
    if rng.random() < p['noise']:
        s = float(rng.uniform(2.0, 8.0))
        f = im.astype(np.float32)
        shot = np.sqrt(np.maximum(f, 0.0) / 255.0)       # brighter pixels get a bit more (shot) noise
        if rng.random() < 0.5:   # luma-correlated (mono sensor / after debayer)
            n = rng.standard_normal(im.shape[:2], dtype=np.float32)[..., None]
        else:
            n = rng.standard_normal(im.shape, dtype=np.float32)
        im = np.clip(f + n * s * (0.5 + shot), 0, 255).astype(np.uint8)
    if rng.random() < p['jpeg']:
        ok, buf = cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(40, 91))])
        if ok:
            im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return np.ascontiguousarray(im)


class SimRealAug:
    """Drop-in for ultralytics.data.augment.Albumentations (same constructor / __call__ contract)."""

    probs = dict(DEFAULT)

    def __init__(self, p: float = 1.0, transforms=None, flip_idx=None):
        self.p = p
        self.transform = None            # attribute checked by some ultralytics code paths
        self.contains_spatial = False

    def __call__(self, labels: dict) -> dict:
        if random.random() >= self.p:
            return labels
        im = labels.get('img')
        if im is None or im.ndim != 3 or im.shape[2] != 3:
            return labels
        labels['img'] = degrade(im, self.probs)
        return labels


def install(probs: dict | None = None) -> None:
    """Replace the Albumentations stage of ultralytics' v8_transforms (call before model.train())."""
    import ultralytics.data.augment as aug
    if probs:
        SimRealAug.probs = {**DEFAULT, **probs}
    aug.Albumentations = SimRealAug
