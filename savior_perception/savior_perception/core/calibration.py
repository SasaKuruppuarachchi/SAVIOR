# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Stereo calibration from the OpenVINS/Kalibr `kalibr_imucam_chain.yaml` + rectification.

OpenVINS tracks features on the RAW (distorted) images, so every mask SAVIOR publishes
must be in raw pixel coordinates. Stereo matching however needs a rectified pair. This
module builds both directions of the mapping once at start-up:

* ``rect_to_raw_{x,y}[i]`` (rectified-image sized): raw pixel of each rectified pixel,
  used with ``cv2.remap`` to rectify (crops of) the raw images;
* ``raw_to_rect_{x,y}[i]`` (raw-image sized): rectified coordinates of each raw pixel,
  used with ``cv2.remap`` to bring rectified quantities (disparity) back to raw pixels.

Pixels that have no valid counterpart hold ``INVALID_COORD`` (far outside any image), so a
remap with a constant border returns the border value there.

Supported camera models: pinhole + ``radtan`` (k1,k2,p1,p2) and pinhole + ``equidistant``
(Kannala-Brandt k1..k4, e.g. Intel T265). Extrinsics are read from ``T_imu_cam``
(OpenVINS convention, R_CtoI/p_CinI) or ``T_cam_imu`` (Kalibr convention), exactly as
OpenVINS does, so the yaml stays the single source of truth.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import cv2
import numpy as np
import yaml

INVALID_COORD = -1.0e5
_ITER_CRITERIA = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 100, 1e-10)


@dataclass
class CameraModel:
    K: np.ndarray            # 3x3
    D: np.ndarray            # (4,)
    model: str               # "radtan" | "equidistant"
    size: Tuple[int, int]    # (width, height)
    T_cam_imu: np.ndarray    # 4x4, X_cam = T_cam_imu * X_imu
    name: str = ""
    rostopic: str = ""

    def __post_init__(self):
        self.K = np.asarray(self.K, dtype=np.float64).reshape(3, 3)
        self.D = np.asarray(self.D, dtype=np.float64).reshape(-1)
        if self.model not in ("radtan", "equidistant"):
            raise ValueError(f"unsupported distortion_model '{self.model}' (radtan|equidistant)")
        if self.D.size != 4:
            raise ValueError(f"expected 4 distortion coefficients, got {self.D.size}")
        self.size = (int(self.size[0]), int(self.size[1]))
        self.T_cam_imu = np.asarray(self.T_cam_imu, dtype=np.float64).reshape(4, 4)

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    @property
    def is_fisheye(self) -> bool:
        return self.model == "equidistant"

    def project(self, pts_cam: np.ndarray) -> np.ndarray:
        """Project Nx3 points in the camera frame (z>0) to raw pixels (Nx2)."""
        obj = np.ascontiguousarray(np.asarray(pts_cam, dtype=np.float64).reshape(-1, 1, 3))
        rvec = np.zeros((3, 1))
        tvec = np.zeros((3, 1))
        if obj.shape[0] == 0:
            return np.zeros((0, 2))
        if self.is_fisheye:
            img, _ = cv2.fisheye.projectPoints(obj, rvec, tvec, self.K, self.D)
        else:
            img, _ = cv2.projectPoints(obj, rvec, tvec, self.K, self.D)
        return img.reshape(-1, 2)

    def undistort_normalized(self, pts: np.ndarray, tol_px: float = 0.05):
        """Raw pixels (Nx2) -> normalized undistorted coords (Nx2) and a validity flag.

        A point is valid when re-projecting the solution lands within `tol_px` of the input.
        """
        src = np.ascontiguousarray(np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2))
        if self.is_fisheye:
            try:
                xy = cv2.fisheye.undistortPoints(src, self.K, self.D, criteria=_ITER_CRITERIA)
            except TypeError:  # older OpenCV without the criteria argument
                xy = cv2.fisheye.undistortPoints(src, self.K, self.D)
        else:
            xy = cv2.undistortPointsIter(src, self.K, self.D, None, None, _ITER_CRITERIA)
        xy = xy.reshape(-1, 2)
        finite = np.isfinite(xy).all(axis=1)
        xy = np.where(finite[:, None], xy, 0.0)
        reproj = self.project(np.column_stack([xy, np.ones(len(xy))]))
        err = np.linalg.norm(reproj - src.reshape(-1, 2), axis=1)
        valid = finite & (err < tol_px)
        return xy, valid


def _strip_opencv_yaml(text: str) -> str:
    # OpenCV FileStorage files start with "%YAML:1.0", which PyYAML rejects.
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


def load_kalibr_imucam_chain(path: str) -> Dict[str, CameraModel]:
    """Parse an OpenVINS/Kalibr imu-cam chain yaml into {"cam0": CameraModel, ...}."""
    with open(path, "r") as fh:
        data = yaml.safe_load(_strip_opencv_yaml(fh.read()))
    cams = {}
    for key in sorted(k for k in data if k.startswith("cam")):
        c = data[key]
        if "T_cam_imu" in c:
            T_cam_imu = np.asarray(c["T_cam_imu"], dtype=np.float64)
        elif "T_imu_cam" in c:
            T_cam_imu = np.linalg.inv(np.asarray(c["T_imu_cam"], dtype=np.float64))
        else:
            raise ValueError(f"{path}:{key}: neither T_cam_imu nor T_imu_cam present")
        model = c.get("camera_model", "pinhole")
        if model != "pinhole":
            raise ValueError(f"{path}:{key}: camera_model '{model}' unsupported (pinhole only)")
        fx, fy, cx, cy = [float(v) for v in c["intrinsics"]]
        cams[key] = CameraModel(
            K=np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]]),
            D=np.asarray(c["distortion_coeffs"], dtype=np.float64),
            model=str(c.get("distortion_model", "radtan")),
            size=tuple(int(v) for v in c["resolution"]),
            T_cam_imu=T_cam_imu, name=key, rostopic=str(c.get("rostopic", "")))
    if not cams:
        raise ValueError(f"{path}: no cam* entries")
    return cams


class StereoRectifier:
    """Rectified stereo geometry + raw<->rect maps for a (left=cam0, right=cam1) pair.

    The rectified camera is a shared ideal pinhole with focal ``f`` (``focal_scale`` x mean
    raw focal). Rectified frame:

    * ``size_scale > 0``: ``size_scale`` x the raw size of the left camera, principal point at
      the centre (corners of strongly distorted raw images may fall outside);
    * ``size_scale <= 0`` (auto, default): just large enough to contain every valid raw pixel of
      both cameras, each side capped at ``max_scale/2`` x the raw size from the optical axis
      (needed for fisheye lenses whose FOV a pinhole cannot represent). Stereo matching only
      runs on ROIs, so a large rectified frame costs map memory, not matching time.

    Rotations follow Bouguet (cv2.stereoRectify, zero disparity at infinity). Disparity
    ``d = u_left - u_right > 0`` and depth ``z = f * baseline / d`` in the rectified left frame.
    """

    def __init__(self, cam0: CameraModel, cam1: CameraModel, focal_scale: float = 1.0,
                 size_scale: float = 0.0, max_scale: float = 2.0):
        self.cams = (cam0, cam1)
        # X_c1 = R * X_c0 + T
        T_c1_c0 = cam1.T_cam_imu @ np.linalg.inv(cam0.T_cam_imu)
        self.T_c1_c0 = T_c1_c0
        R, T = T_c1_c0[:3, :3], T_c1_c0[:3, 3].reshape(3, 1)
        w, h = cam0.size
        R0, R1, _, P1, _, _, _ = cv2.stereoRectify(
            cam0.K, np.zeros(4), cam1.K, np.zeros(4), (w, h), R, T,
            flags=cv2.CALIB_ZERO_DISPARITY, alpha=-1)
        T_rect = R1 @ T.reshape(3)
        if abs(T_rect[0]) < 10 * max(abs(T_rect[1]), abs(T_rect[2]), 1e-9):
            raise ValueError("only horizontal stereo pairs are supported")
        if T_rect[0] >= 0:
            raise ValueError("cam1 must be to the right of cam0 (expected T_rect.x < 0)")
        self.R_rect = (R0, R1)
        self.baseline = float(np.linalg.norm(T))
        self.f = float(focal_scale * np.mean([cam0.K[0, 0], cam0.K[1, 1], cam1.K[0, 0], cam1.K[1, 1]]))
        # normalized rectified coordinates (x/z, y/z) of every raw pixel of both cameras
        norm = [self._raw_normalized(i) for i in range(2)]
        if size_scale > 0:
            self.rect_size = (int(round(w * size_scale)), int(round(h * size_scale)))
            self.cx, self.cy = (self.rect_size[0] - 1) / 2.0, (self.rect_size[1] - 1) / 2.0
        else:
            xs = np.concatenate([n[0][n[2]] for n in norm])
            ys = np.concatenate([n[1][n[2]] for n in norm])
            capx, capy = max_scale * w / (2.0 * self.f), max_scale * h / (2.0 * self.f)
            x0, x1 = max(float(xs.min()), -capx), min(float(xs.max()), capx)
            y0, y1 = max(float(ys.min()), -capy), min(float(ys.max()), capy)
            self.rect_size = (int(math.ceil((x1 - x0) * self.f - 1e-6)) + 1,
                              int(math.ceil((y1 - y0) * self.f - 1e-6)) + 1)
            self.cx, self.cy = -x0 * self.f, -y0 * self.f
        self.K_rect = np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1.0]])
        self.P_rect = (np.hstack([self.K_rect, np.zeros((3, 1))]),
                       np.hstack([self.K_rect, np.array([[-self.f * self.baseline], [0], [0]])]))
        self.raw_to_rect_x, self.raw_to_rect_y = [], []
        self.rect_to_raw_x, self.rect_to_raw_y = [], []
        for i in range(2):
            xn, yn, valid = norm[i]
            cw, ch = self.cams[i].size
            mx = np.where(valid, self.f * xn + self.cx, INVALID_COORD).reshape(ch, cw).astype(np.float32)
            my = np.where(valid, self.f * yn + self.cy, INVALID_COORD).reshape(ch, cw).astype(np.float32)
            self.raw_to_rect_x.append(mx)
            self.raw_to_rect_y.append(my)
        for i in range(2):
            mx, my = self._build_rect_to_raw(i)
            self.rect_to_raw_x.append(mx)
            self.rect_to_raw_y.append(my)

    # ------------------------------------------------------------------ geometry
    @property
    def fb(self) -> float:
        return self.f * self.baseline

    def disparity_to_depth(self, d):
        d = np.asarray(d, dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(d > 0, self.fb / d, np.nan)

    def sigma_z(self, z, sigma_d_px: float):
        """Stereo depth std: sigma_z(z) = z^2 * sigma_d / (f * b)."""
        return np.asarray(z, dtype=np.float64) ** 2 * sigma_d_px / self.fb

    def raw_to_rect_points(self, pts: np.ndarray, i: int):
        """Exact raw->rect for Nx2 points of camera i. Returns (Nx2, valid)."""
        cam = self.cams[i]
        xy, valid = cam.undistort_normalized(pts)
        rays = np.column_stack([xy, np.ones(len(xy))]) @ self.R_rect[i].T
        z = rays[:, 2]
        valid &= z > 1e-6
        zs = np.where(valid, z, 1.0)
        u = self.f * rays[:, 0] / zs + self.cx
        v = self.f * rays[:, 1] / zs + self.cy
        return np.column_stack([u, v]), valid

    def rect_to_raw_points(self, pts: np.ndarray, i: int) -> np.ndarray:
        """Exact rect->raw for Nx2 rectified points of camera i."""
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        rays = np.column_stack([(pts[:, 0] - self.cx) / self.f, (pts[:, 1] - self.cy) / self.f,
                                np.ones(len(pts))])
        rays = rays @ self.R_rect[i]  # R^T applied to row vectors
        return self.cams[i].project(rays)

    def project_cam0_point(self, X_c0: np.ndarray):
        """Helper for tests: 3D points in cam0 frame -> (raw0, raw1, rect0, rect1)."""
        X_c0 = np.asarray(X_c0, dtype=np.float64).reshape(-1, 3)
        X_c1 = X_c0 @ self.T_c1_c0[:3, :3].T + self.T_c1_c0[:3, 3]
        raw0, raw1 = self.cams[0].project(X_c0), self.cams[1].project(X_c1)
        out = []
        for X, R in ((X_c0, self.R_rect[0]), (X_c1, self.R_rect[1])):
            Xr = X @ R.T
            out.append(np.column_stack([self.f * Xr[:, 0] / Xr[:, 2] + self.cx,
                                        self.f * Xr[:, 1] / Xr[:, 2] + self.cy]))
        return raw0, raw1, out[0], out[1]

    # ------------------------------------------------------------------ maps
    def _raw_normalized(self, i: int):
        """Normalized rectified coords (flattened) of every raw pixel of camera i + validity."""
        cam = self.cams[i]
        w, h = cam.size
        xs, ys = np.meshgrid(np.arange(w, dtype=np.float64), np.arange(h, dtype=np.float64))
        xy, valid = cam.undistort_normalized(np.column_stack([xs.ravel(), ys.ravel()]))
        rays = np.column_stack([xy, np.ones(len(xy))]) @ self.R_rect[i].T
        z = rays[:, 2]
        valid &= z > 1e-6
        zs = np.where(valid, z, 1.0)
        return rays[:, 0] / zs, rays[:, 1] / zs, valid

    def _build_rect_to_raw(self, i: int, tol_rect_px: float = 1.0):
        cam = self.cams[i]
        P = self.K_rect
        if cam.is_fisheye:
            mx, my = cv2.fisheye.initUndistortRectifyMap(cam.K, cam.D, self.R_rect[i], P,
                                                         self.rect_size, cv2.CV_32FC1)
        else:
            mx, my = cv2.initUndistortRectifyMap(cam.K, cam.D, self.R_rect[i], P,
                                                 self.rect_size, cv2.CV_32FC1)
        w, h = cam.size
        rw, rh = self.rect_size
        inside = (np.isfinite(mx) & np.isfinite(my) & (mx >= -0.5) & (mx <= w - 0.5)
                  & (my >= -0.5) & (my <= h - 0.5))
        # Reject fold-backs of the distortion polynomial: the (bilinearly interpolated) exact
        # raw->rect map at the raw point must come back to the rectified pixel we started from.
        mxs = np.where(inside, mx, -1.0).astype(np.float32)
        mys = np.where(inside, my, -1.0).astype(np.float32)
        bu = cv2.remap(self.raw_to_rect_x[i], mxs, mys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        bv = cv2.remap(self.raw_to_rect_y[i], mxs, mys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        uu, vv = np.meshgrid(np.arange(rw, dtype=np.float32), np.arange(rh, dtype=np.float32))
        ok = inside & (np.abs(bu - uu) < tol_rect_px) & (np.abs(bv - vv) < tol_rect_px)
        mx = np.where(ok, mx, INVALID_COORD).astype(np.float32)
        my = np.where(ok, my, INVALID_COORD).astype(np.float32)
        return mx, my

    def rectify(self, img: np.ndarray, i: int, interpolation=cv2.INTER_LINEAR) -> np.ndarray:
        return cv2.remap(img, self.rect_to_raw_x[i], self.rect_to_raw_y[i], interpolation,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def stereo_from_kalibr(path: str, cam_left: str = "cam0", cam_right: str = "cam1",
                       focal_scale: float = 1.0, size_scale: float = 0.0,
                       max_scale: float = 2.0) -> StereoRectifier:
    cams = load_kalibr_imucam_chain(path)
    return StereoRectifier(cams[cam_left], cams[cam_right], focal_scale=focal_scale,
                           size_scale=size_scale, max_scale=max_scale)


def ideal_stereo(width: int, height: int, f: float, baseline: float) -> StereoRectifier:
    """Distortion-free, already-rectified pair (raw == rect). Used by tests / synthetic data."""
    K = np.array([[f, 0, (width - 1) / 2.0], [0, f, (height - 1) / 2.0], [0, 0, 1.0]])
    T0 = np.eye(4)
    T1 = np.eye(4)
    T1[0, 3] = -baseline  # X_c1 = X_c0 - b*x  => cam1 is `baseline` to the right
    c0 = CameraModel(K=K, D=np.zeros(4), model="radtan", size=(width, height), T_cam_imu=T0, name="cam0")
    c1 = CameraModel(K=K.copy(), D=np.zeros(4), model="radtan", size=(width, height), T_cam_imu=T1, name="cam1")
    return StereoRectifier(c0, c1)
