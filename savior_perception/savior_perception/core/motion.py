# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Independent-motion evidence (phase P4): ego-motion compensated sparse flow per instance.

Per frame k (left camera, RAW image, any CameraModel supported by calibration.py):

1. **Ego-motion.** The gyro rotation between the two frame stamps (IMU frame, integrated by
   :class:`GyroIntegrator`) is mapped into the camera, ``R_g = R_CI^T R_{I_{k-1} I_k}^T R_CI``.
   Background KLT points (outside every dynamic/potential bbox and the static mask) carry a 3D position
   ``X_{k-1}`` from a left->right KLT stereo match at frame k-1. A robust (Huber IRLS) Gauss-Newton fit of
   a small rotation correction ``dtheta`` (prior ``N(0, gyro_sigma_rad^2)``: gyro bias / time offset) and of
   the translation ``t`` (weak prior ``N(0, (max_ego_speed*dt)^2)``) minimises the bearing residuals
   ``b_k x (R X_{k-1} + t) / |.|`` with ``R = exp(dtheta) R_g``. The accelerometer is not used: the
   translation comes from the background stereo points (fewer than ``bg_min_inliers`` inliers -> t = 0 with
   an inflated, coherent uncertainty ``max_ego_speed*dt``).
2. **Instantaneous test.** Points inside each dynamic/potential instance (mask eroded by ``inst_erode_px``;
   depth = median left->right KLT stereo disparity of the instance's points, fallback ROI-SGBM median) are
   tracked k-1 -> k. A static point would be seen at ``y = normalize(R X + t)``; the residuals ``e_j = b_j - y_j``
   (tangent plane at the instance direction) are fitted by a common 2D offset ``c`` (GLS, Huber IRLS) with
   per-point covariance ``sigma_bg^2 I + depth_rel_sigma^2 pi_j pi_j^T`` where ``pi_j = (t - (y.t) y)/|Y|`` is
   the parallax direction: the along-epipolar component is only trusted as far as the depth is (instances are
   depth mixtures: see-through chairs, people behind tables, KLT patches straddling the boundary), the
   perpendicular component is depth-free. ``sigma_bg`` = robust background residual std (floor
   ``sigma_px_min``); coherent floors (``sigma_sys_px``, translation uncertainty) are added to cov(c).
   Output: Mahalanobis ``q^2 = c^T cov^-1 c`` and speed ``|c| r / dt`` (r = median range).
3. **Windowed test.** Instance anchor ``P`` (mask-centroid bearing x ROI-SGBM depth) now vs. ``window_min_s ..
   window_max_s`` ago, moved by the ego-motion chained over the window: ``D = P_k - T_{k<-j} P_j``. Static biases
   of the anchor (segmentation, stereo) cancel in the difference; radial ``D.u_r / dt`` and lateral velocity
   with noise from ``anchor_sigma_px`` / ``anchor_sigma_d_px``. Covers motion along the epipolar line
   (approaching / receding people) that the instantaneous test down-weights.
4. **Temporal filter (moving probability).** Each instance is associated with a *motion track* by majority vote
   of its tracked points (fallback: bbox IoU >= 0.3 with the track's previous box; else a new track). Per frame:
   * moving obs: instantaneous ``q >= q_move`` and speed >= ``v_move``, or (always-dynamic classes, or
     ``window_moving_potential``) windowed lateral / radial velocity ``>= max(v_move*, q_move sigma)``;
   * static obs: instantaneous ``q < q_static`` and windowed ``|v_lat| + 2 sigma < v_static`` and
     (if ``radial_static_required``) ``|v_rad| + 2 sigma < v_static_radial``;
   * P6 ``window_unveto_potential``: for a potential object a windowed "moving" result resets ``l`` to >= 0 (cancels a
     static veto, no root);
   * log-odds ``l += l_up`` / ``-= l_down`` (clamped to +-l_max), prior by role (``prior_dynamic`` > 0: a new
     person is masked until confirmed static; ``prior_potential`` < 0).
   Hysteresis flags: ``is_moving`` on at ``l >= th_moving``, off at ``l <= 0``; ``is_static`` on at
   ``l <= th_static``, off at ``l >= 0``.
5. **Decisions** (used by the promotion gate): static always-dynamic instance -> ``False`` (STATUS_STILL:
   not a root, not masked / band only); moving potential instance -> ``True`` (root); static potential
   instance -> ``False`` (never promoted). No evidence -> no entry (P2 behaviour).

Approximations: rotation from the gyro only (no accelerometer), constant angular velocity between
gyro samples (midpoint rule), equidistant/radtan bearing model from the shared kalibr yaml, background
assumed mostly static (robust loss), background depth propagated by the ego-motion between stereo refreshes
(``stereo_refresh``), anchor noise modelled as Gaussian although real mask/depth drift is heavy-tailed (hence the
inflated ``anchor_sigma_*`` defaults and no windowed "moving" for potential objects).
"""

from __future__ import annotations

import math
import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from .calibration import StereoRectifier
from .config import MotionConfig
from .types import ROLE_DYNAMIC, ROLE_POTENTIAL, Instance, box_iou, expand_box

_UP = np.array([0.0, 1.0, 0.0])


# ---------------------------------------------------------------------------------------------- SO(3)
def skew(v) -> np.ndarray:
    x, y, z = float(v[0]), float(v[1]), float(v[2])
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def so3_exp(w) -> np.ndarray:
    w = np.asarray(w, dtype=np.float64).reshape(3)
    th = float(np.linalg.norm(w))
    K = skew(w)
    if th < 1e-9:
        return np.eye(3) + K
    return np.eye(3) + math.sin(th) / th * K + (1.0 - math.cos(th)) / (th * th) * (K @ K)


def so3_log(R) -> np.ndarray:
    c = max(-1.0, min(1.0, (np.trace(R) - 1.0) * 0.5))
    th = math.acos(c)
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    if th < 1e-7:
        return 0.5 * v
    return th / (2.0 * math.sin(th)) * v


# ---------------------------------------------------------------------------------------------- gyro
class GyroIntegrator:
    """Time-ordered gyro samples (IMU frame, rad/s) -> relative IMU rotation between two times."""

    def __init__(self, max_age_s: float = 10.0):
        self.t: List[float] = []
        self.w: List[np.ndarray] = []
        self.max_age_s = max_age_s

    def add(self, t: float, w) -> None:
        w = np.asarray(w, dtype=np.float64).reshape(3)
        if self.t and t <= self.t[-1]:
            if t == self.t[-1]:
                return
            i = bisect_left(self.t, t)          # out-of-order sample: insert in place
            if i < len(self.t) and self.t[i] == t:
                return
            self.t.insert(i, t)
            self.w.insert(i, w)
            return
        self.t.append(t)
        self.w.append(w)
        if self.t[-1] - self.t[0] > 2 * self.max_age_s:
            k = bisect_left(self.t, self.t[-1] - self.max_age_s)
            del self.t[:k]
            del self.w[:k]

    @property
    def last_time(self) -> float:
        return self.t[-1] if self.t else -math.inf

    def covers(self, t0: float, t1: float) -> bool:
        return bool(self.t) and self.t[0] <= t0 and self.t[-1] >= t1

    def _omega(self, t: float) -> np.ndarray:
        i = bisect_left(self.t, t)
        if i <= 0:
            return self.w[0]
        if i >= len(self.t):
            return self.w[-1]
        t0, t1 = self.t[i - 1], self.t[i]
        a = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
        return (1.0 - a) * self.w[i - 1] + a * self.w[i]

    def rotation(self, t0: float, t1: float) -> Optional[np.ndarray]:
        """R_{I(t0) I(t1)}: orientation of the IMU at t1 in the IMU frame at t0 (body-frame integration of the
        piecewise-linear angular velocity, midpoint rule per knot interval). None if not covered."""
        if t1 < t0:
            R = self.rotation(t1, t0)
            return None if R is None else R.T
        if not self.covers(t0, t1):
            return None
        i0, i1 = bisect_right(self.t, t0), bisect_left(self.t, t1)
        knots = [t0] + self.t[i0:i1] + [t1]
        R = np.eye(3)
        w_prev = self._omega(t0)
        for a, b in zip(knots[:-1], knots[1:]):
            w_b = self._omega(b)
            if b > a:
                R = R @ so3_exp(0.5 * (w_prev + w_b) * (b - a))
            w_prev = w_b
        return R


# ---------------------------------------------------------------------------------------------- tracks
@dataclass(eq=False)
class MotionTrack:
    id: int
    role: str
    cls: str
    l: float
    is_moving: bool = False
    is_static: bool = False
    missing: int = 0
    n_obs: int = 0
    hist: List[tuple] = field(default_factory=list)   # (frame, stamp, anchor in that camera frame)
    last: dict = field(default_factory=dict)
    box: Optional[tuple] = None
    raw: dict = field(default_factory=dict)          # P7: this frame's raw evidence {stamp, ev, win, win_long}

    @property
    def state(self) -> str:
        return "moving" if self.is_moving else ("static" if self.is_static else "unknown")


@dataclass
class EgoMotion:
    R: np.ndarray               # X_k = R X_{k-1} + t (camera frame)
    t: np.ndarray
    sigma_t: float              # std of each t component [m] (coherent uncertainty)
    sigma_bg: float             # robust background residual std [rad]
    n_bg: int = 0
    n_inliers: int = 0
    t_ok: bool = False
    dtheta: np.ndarray = field(default_factory=lambda: np.zeros(3))


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


class MotionEstimator:
    """Sparse-flow motion evidence. Call :meth:`update` once per frame (before gating)."""

    def __init__(self, cfg: MotionConfig, rect: StereoRectifier, static_mask: Optional[np.ndarray] = None):
        self.cfg = cfg
        self.rect = rect
        self.cam0, self.cam1 = rect.cams
        self.f_raw = float(np.mean([self.cam0.K[0, 0], self.cam0.K[1, 1]]))
        self.R_CI = np.linalg.inv(self.cam0.T_cam_imu)[:3, :3]      # R_CtoI
        self.s = float(cfg.image_scale)
        w, h = self.cam0.size
        self.size_s = (max(8, int(round(w * self.s))), max(8, int(round(h * self.s))))
        self.static_mask_s = None
        if static_mask is not None:
            m = (static_mask > 127).astype(np.uint8)
            self.static_mask_s = cv2.resize(m, self.size_s, interpolation=cv2.INTER_NEAREST).astype(bool)
        self.win = (int(cfg.klt_win), int(cfg.klt_win))
        self.crit = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, 0.03)
        self.reset()

    def reset(self):
        self.prev_pyr = None
        self.prev_t: Optional[float] = None
        self.bg_p = np.zeros((0, 2))            # full-res raw px at the previous frame
        self.bg_X = np.zeros((0, 3))            # 3D at the previous frame (nan = no depth)
        self.bg_age = np.zeros(0, np.int64)     # frames since the stereo depth of the point was measured
        self.in_p = np.zeros((0, 2))
        self.in_X = np.zeros((0, 3))
        self.in_tid = np.zeros(0, np.int64)
        self.tracks: Dict[int, MotionTrack] = {}
        self._next_id = 1
        self.last_ego: Optional[EgoMotion] = None
        self.last_stats: dict = {}
        self.poses: Dict[int, np.ndarray] = {}      # frame -> T_w_c (chained ego-motion, local frame)
        self.frame = 0

    # ------------------------------------------------------------------ geometry helpers
    def bearings(self, pts: np.ndarray, cam: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """Raw pixels (Nx2) -> unit bearings (Nx3) + validity (no re-projection check: fast path)."""
        if len(pts) == 0:
            return np.zeros((0, 3)), np.zeros(0, bool)
        c = self.rect.cams[cam]
        src = np.ascontiguousarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        if c.is_fisheye:
            xy = cv2.fisheye.undistortPoints(src, c.K, c.D)
        else:
            xy = cv2.undistortPointsIter(src, c.K, c.D, None, None,
                                         (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, 1e-9))
        xy = xy.reshape(-1, 2)
        ok = np.isfinite(xy).all(axis=1) & (np.abs(xy) < 20).all(axis=1)
        xy = np.where(ok[:, None], xy, 0.0)
        return _unit(np.column_stack([xy, np.ones(len(xy))])), ok

    def _rect_uv(self, b: np.ndarray, cam: int) -> Tuple[np.ndarray, np.ndarray]:
        r = b @ self.rect.R_rect[cam].T
        ok = r[:, 2] > 1e-6
        z = np.where(ok, r[:, 2], 1.0)
        return np.column_stack([self.rect.f * r[:, 0] / z + self.rect.cx, self.rect.f * r[:, 1] / z + self.rect.cy]), ok

    def point_from_disparity(self, b: np.ndarray, d: np.ndarray) -> np.ndarray:
        """Bearing (cam0) + rectified disparity -> 3D point in cam0 (nan where d <= 0)."""
        r = b @ self.rect.R_rect[0].T
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(d > 0, self.rect.fb / d, np.nan)
            lam = z / r[:, 2]
        return b * lam[:, None]

    def ego_project(self, pts: np.ndarray, depth: np.ndarray, ego: Optional[EgoMotion] = None) -> Optional[np.ndarray]:
        """Predicted raw position at frame k of static points seen at frame k-1 (rect depth; nan = infinitely far)."""
        ego = ego or self.last_ego
        if ego is None or len(pts) == 0:
            return None
        b, ok = self.bearings(pts)
        r = b @ self.rect.R_rect[0].T
        z = np.where(np.isfinite(depth) & (depth > 0), depth, 1e6)
        X = b * (z / np.maximum(r[:, 2], 1e-6))[:, None]
        Y = X @ ego.R.T + ego.t
        out = self.cam0.project(np.where(Y[:, 2:3] > 1e-6, Y, np.array([0, 0, 1.0])))
        out[~ok | (Y[:, 2] <= 1e-6)] = np.nan
        return out

    # ------------------------------------------------------------------ KLT
    def _pyr(self, gray: np.ndarray):
        # NOTE: the python binding of calcOpticalFlowPyrLK takes images only (no prebuilt pyramids)
        img = gray if self.s == 1.0 else cv2.resize(gray, self.size_s, interpolation=cv2.INTER_AREA)
        return img, img

    def _fb_ok(self, img0, img1, p0: np.ndarray, p1: np.ndarray, ok: np.ndarray) -> np.ndarray:
        """Backward KLT p1 -> img0 for the points with ok; True where the round trip is < fb_max_px."""
        res = np.zeros(len(p0), bool)
        idx = np.flatnonzero(ok)
        if len(idx) == 0:
            return res
        a = (p1[idx] * self.s).astype(np.float32).reshape(-1, 1, 2)
        b0 = (p0[idx] * self.s).astype(np.float32).reshape(-1, 1, 2)
        pb, st, _ = cv2.calcOpticalFlowPyrLK(img1, img0, a, b0.copy(), winSize=self.win,
                                             maxLevel=int(self.cfg.klt_levels), criteria=self.crit,
                                             flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
        err = np.linalg.norm((pb - b0).reshape(-1, 2), axis=1) / self.s
        res[idx] = st.reshape(-1).astype(bool) & (err < self.cfg.fb_max_px)
        return res

    def _klt(self, pyr0, pyr1, pts: np.ndarray, fb: bool = True, guess: Optional[np.ndarray] = None):
        """Full-res raw px in pyr0 -> full-res raw px in pyr1, ok mask."""
        if len(pts) == 0:
            return np.zeros((0, 2)), np.zeros(0, bool)
        p0 = (pts * self.s).astype(np.float32).reshape(-1, 1, 2)
        flags = 0
        p1 = None
        if guess is not None:
            p1 = (guess * self.s).astype(np.float32).reshape(-1, 1, 2)
            flags = cv2.OPTFLOW_USE_INITIAL_FLOW
        p1, st, _ = cv2.calcOpticalFlowPyrLK(pyr0, pyr1, p0, p1, winSize=self.win, maxLevel=int(self.cfg.klt_levels),
                                             criteria=self.crit, flags=flags)
        ok = st.reshape(-1).astype(bool)
        if fb:
            p0b, st2, _ = cv2.calcOpticalFlowPyrLK(pyr1, pyr0, p1, p0.copy(), winSize=self.win,
                                                   maxLevel=int(self.cfg.klt_levels), criteria=self.crit,
                                                   flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
            err = np.linalg.norm((p0b - p0).reshape(-1, 2), axis=1) / self.s
            ok &= st2.reshape(-1).astype(bool) & (err < self.cfg.fb_max_px)
        out = p1.reshape(-1, 2).astype(np.float64) / self.s
        w, h = self.cam0.size
        ok &= (out[:, 0] >= 0) & (out[:, 0] <= w - 1) & (out[:, 1] >= 0) & (out[:, 1] <= h - 1)
        return out, ok

    # ------------------------------------------------------------------ ego-motion
    def estimate_ego(self, X: np.ndarray, b: np.ndarray, R_g: np.ndarray, dt: float,
                     gyro_sigma: Optional[float] = None) -> EgoMotion:
        """Robust fit of (dtheta, t): b x (exp(dtheta) R_g X + t) = 0 (see module docstring)."""
        c = self.cfg
        sig_min = c.sigma_px_min / self.f_raw
        st0 = max(c.max_ego_speed_mps * max(dt, 1e-3), 1e-3)
        n = len(X)
        ego = EgoMotion(R=R_g.copy(), t=np.zeros(3), sigma_t=st0, sigma_bg=2.0 * sig_min, n_bg=n)
        if n < max(6, c.bg_min_inliers // 2):
            return ego
        Xr = X @ R_g.T
        Bx = np.zeros((n, 3, 3))
        Bx[:, 0, 1], Bx[:, 0, 2] = -b[:, 2], b[:, 1]
        Bx[:, 1, 0], Bx[:, 1, 2] = b[:, 2], -b[:, 0]
        Bx[:, 2, 0], Bx[:, 2, 1] = -b[:, 1], b[:, 0]
        x = np.zeros(6)
        sigma = 2.0 * sig_min
        w_rob = np.ones(n)
        gs = c.gyro_sigma_rad if gyro_sigma is None else gyro_sigma
        prior = np.diag([1.0 / gs ** 2] * 3 + [1.0 / st0 ** 2] * 3)
        H = prior
        for it in range(int(c.ego_iters)):
            Rc = so3_exp(x[:3])
            Yp = Xr @ Rc.T                      # rotated, before translation
            Y = Yp + x[3:]
            nY = np.linalg.norm(Y, axis=1)
            u = Y / nY[:, None]
            res = np.cross(b, u)                # ~ angular residual vector (|res| = sin angle)
            rn = np.linalg.norm(res, axis=1)
            if it >= 1:
                med = float(np.median(rn[w_rob > 0])) if np.any(w_rob > 0) else sigma
                sigma = max(sig_min, med / 1.1774)
            k = 2.0 * sigma
            w_rob = np.where(rn <= k, 1.0, k / np.maximum(rn, 1e-15))
            if it >= 2:
                w_rob[rn > 4.0 * sigma] = 0.0
            # J_i = [b]x [-[Yp]x, I] / |Y|  (3x6 per point), [b]x[Yp]x = Yp b^T - (b.Yp) I
            BP = Yp[:, :, None] * b[:, None, :]
            bp = np.einsum("ni,ni->n", b, Yp)
            BP[:, 0, 0] -= bp
            BP[:, 1, 1] -= bp
            BP[:, 2, 2] -= bp
            J = np.concatenate([-BP, Bx], axis=2) / nY[:, None, None]
            W = (w_rob / sigma ** 2)[:, None, None]
            H = prior + np.einsum("nij,nik->jk", J * W, J)
            g = prior @ x + np.einsum("nij,ni->j", J * W, res)
            try:
                dx = -np.linalg.solve(H, g)
            except np.linalg.LinAlgError:
                return ego
            x = x + dx
            if it >= 2 and np.linalg.norm(dx) < 1e-7:
                break
        Rc = so3_exp(x[:3])
        Y = Xr @ Rc.T + x[3:]
        rn = np.linalg.norm(np.cross(b, _unit(Y)), axis=1)
        inl = rn < 3.0 * sigma
        ego.n_inliers = int(inl.sum())
        ego.dtheta = x[:3]
        ego.R = Rc @ R_g
        ego.sigma_bg = sigma
        if ego.n_inliers >= c.bg_min_inliers:
            try:
                cov = np.linalg.inv(H)
                ego.sigma_t = float(math.sqrt(max(np.max(np.diag(cov)[3:]), 0.0)))
            except np.linalg.LinAlgError:
                ego.sigma_t = st0
            ego.t = x[3:].copy()
            ego.t_ok = True
        else:
            # rotation-only: keep the gyro (+ far-point) rotation, translation unknown
            ego.R = R_g.copy()
            ego.dtheta = np.zeros(3)
        return ego

    # ------------------------------------------------------------------ instance evidence
    def instance_fit(self, Xp: np.ndarray, b: np.ndarray, ego: EgoMotion, dt: float):
        """Single-instance wrapper of :meth:`instance_fits`."""
        return self.instance_fits([(0, Xp, b)], ego, dt).get(0)

    def instance_fits(self, groups, ego: EgoMotion, dt: float) -> Dict[int, dict]:
        """Instantaneous test for all instances at once: GLS fit of a common tangent-plane residual c (2D) per
        instance. `groups` = [(key, X_{k-1} (n x 3), b_k (n x 3)), ...].

        Per-point covariance ``sigma_bg^2 I + depth_rel_sigma^2 pi_j pi_j^T`` with the parallax vector
        ``pi_j = (t - (y.t) y) / |Y|`` (bearing change per unit relative inverse-depth error): the component along
        the epipolar line is only trusted as far as the point's depth is (instances are depth mixtures: see-through
        chairs, people behind tables, KLT patches on the boundary), the perpendicular component is depth-free.
        Huber IRLS (k = 2 on the Mahalanobis residual), covariance scaled by max(1, chi2/dof), plus coherent terms
        (sigma_sys_px, translation uncertainty). Returns {key: dict(v (3,) [m/s], speed, cov 2x2 [(m/s)^2], m2, n, rng)}."""
        c = self.cfg
        keys, Xs, bs, gs = [], [], [], []
        for k, Xp, b in groups:
            if len(Xp) >= c.min_points:
                gs.append(np.full(len(Xp), len(keys)))
                keys.append(k)
                Xs.append(Xp)
                bs.append(b)
        if not keys:
            return {}
        X, b, g = np.vstack(Xs), np.vstack(bs), np.concatenate(gs)
        Y = X @ ego.R.T + ego.t
        okz = Y[:, 2] > 1e-3
        Y, b, g = Y[okz], b[okz], g[okz]
        G = len(keys)
        cnt = np.bincount(g, minlength=G)
        good = cnt >= c.min_points
        if not good.any():
            return {}
        sel = good[g]
        Y, b, g = Y[sel], b[sel], g[sel]
        rngs = np.linalg.norm(Y, axis=1)
        y = Y / rngs[:, None]
        msum = np.zeros((G, 3))
        np.add.at(msum, g, y)
        mg = _unit(msum + 1e-12)
        ug = np.cross(mg, _UP)
        bad = np.linalg.norm(ug, axis=1) < 1e-6
        if bad.any():
            ug[bad] = np.cross(mg[bad], np.array([1.0, 0.0, 0.0]))
        ug = _unit(ug)
        vg = np.cross(mg, ug)
        u, v = ug[g], vg[g]
        d = b - y
        e = np.column_stack([np.sum(d * u, axis=1), np.sum(d * v, axis=1)])
        par = (ego.t[None, :] - (y @ ego.t)[:, None] * y) / rngs[:, None]
        px, py = np.sum(par * u, axis=1), np.sum(par * v, axis=1)
        s2 = ego.sigma_bg ** 2
        dr2 = c.depth_rel_sigma ** 2
        det = s2 * s2 + s2 * dr2 * (px * px + py * py)
        w00, w11, w01 = (s2 + dr2 * py * py) / det, (s2 + dr2 * px * px) / det, -dr2 * px * py / det
        wr = np.ones(len(g))
        cx = cy = None
        for it in range(4):
            a00 = np.bincount(g, wr * w00, G)
            a11 = np.bincount(g, wr * w11, G)
            a01 = np.bincount(g, wr * w01, G)
            r0 = np.bincount(g, wr * (w00 * e[:, 0] + w01 * e[:, 1]), G)
            r1 = np.bincount(g, wr * (w01 * e[:, 0] + w11 * e[:, 1]), G)
            dh = a00 * a11 - a01 * a01
            dh = np.where(np.abs(dh) > 0, dh, 1e-30)
            cx = (a11 * r0 - a01 * r1) / dh
            cy = (a00 * r1 - a01 * r0) / dh
            q0, q1 = e[:, 0] - cx[g], e[:, 1] - cy[g]
            md2 = w00 * q0 * q0 + 2 * w01 * q0 * q1 + w11 * q1 * q1
            if it < 3:
                md = np.sqrt(md2)
                wr = np.where(md <= 2.0, 1.0, 2.0 / np.maximum(md, 1e-12))
        chi2 = np.bincount(g, wr * md2, G)
        n_g = np.bincount(g, minlength=G)
        scale = np.maximum(1.0, chi2 / np.maximum(1, 2 * n_g - 2))
        cov_t = np.bincount(g, (ego.sigma_t / rngs) ** 2, G) / np.maximum(n_g, 1)
        coh = (c.sigma_sys_px / self.f_raw) ** 2 + cov_t
        out = {}
        dt = max(dt, 1e-3)
        order = np.argsort(g, kind="stable")
        bounds = np.searchsorted(g[order], np.arange(G + 1))
        for j in range(G):
            if n_g[j] < c.min_points:
                continue
            rng = float(np.median(rngs[order[bounds[j]:bounds[j + 1]]]))
            dh = a00[j] * a11[j] - a01[j] * a01[j]
            cov = np.array([[a11[j], -a01[j]], [-a01[j], a00[j]]]) / dh * scale[j] + coh[j] * np.eye(2)
            csol = np.array([cx[j], cy[j]])
            m2 = float(csol @ np.linalg.solve(cov, csol))
            k = rng / dt
            out[keys[j]] = {"n": int(n_g[j]), "rng": rng, "v": (csol[0] * ug[j] + csol[1] * vg[j]) * k,
                            "speed": float(np.hypot(cx[j], cy[j])) * k, "cov": cov * k * k, "m2": m2}
        return out

    def anchor_point(self, inst: Instance) -> Optional[np.ndarray]:
        return self.anchor_points([inst])[0]

    def anchor_points(self, insts: Sequence[Instance]) -> List[Optional[np.ndarray]]:
        """Instance anchors in cam0: mask-centroid bearing x ROI-SGBM median depth (rect z)."""
        out: List[Optional[np.ndarray]] = [None] * len(insts)
        idx, cpts = [], []
        for k, inst in enumerate(insts):
            if not (math.isfinite(inst.depth) and inst.depth > 0):
                continue
            x0, y0, x1, y1 = inst.bbox
            mom = cv2.moments(inst.mask[y0:y1, x0:x1].view(np.uint8), binaryImage=True)
            if mom["m00"] <= 0:
                continue
            idx.append(k)
            cpts.append((x0 + mom["m10"] / mom["m00"], y0 + mom["m01"] / mom["m00"]))
        if not idx:
            return out
        b, ok = self.bearings(np.array(cpts))
        rz = b @ self.rect.R_rect[0][2]
        for j, k in enumerate(idx):
            if ok[j] and rz[j] > 1e-3:
                out[k] = b[j] * (insts[k].depth / rz[j])
        return out

    def window_fit(self, trk: MotionTrack, stamp: float, wmin: Optional[float] = None,
                   wmax: Optional[float] = None) -> Optional[dict]:
        """Windowed test: anchor now vs. the anchor window_min_s..window_max_s ago moved by the chained ego-motion
        (static biases of the anchor -- segmentation, stereo -- cancel in the difference). P7: other window via wmin/wmax."""
        c = self.cfg
        wmin = c.window_min_s if wmin is None else wmin
        wmax = c.window_max_s if wmax is None else wmax
        if not trk.hist:
            return None
        fk, tk, Pk = trk.hist[-1]
        cand = [h for h in trk.hist[:-1] if wmin <= tk - h[1] <= wmax and h[0] in self.poses]
        if not cand or fk not in self.poses:
            return None
        fj, tj, Pj = cand[0]
        T = np.linalg.inv(self.poses[fk]) @ self.poses[fj]          # T_{k<-j}
        Pj_k = T[:3, :3] @ Pj + T[:3, 3]
        D = Pk - Pj_k
        r = float(np.linalg.norm(Pk))
        ur = Pk / r
        dtw = tk - tj
        v_rad = float(D @ ur) / dtw
        v_lat = float(np.linalg.norm(D - (D @ ur) * ur)) / dtw
        z = float(Pk[2])
        s_rad = math.sqrt(2.0) * r * (z * c.anchor_sigma_d_px / self.rect.fb) / dtw
        s_lat = math.sqrt(2.0) * r * (c.anchor_sigma_px / self.f_raw) / dtw
        return {"v_rad": v_rad, "s_rad": s_rad, "v_lat": v_lat, "s_lat": s_lat, "dt": dtw,
                "V": D / dtw, "ur": ur}          # P7: velocity vector (cam k) + radial unit, for the co-motion gate

    def _observe(self, trk: MotionTrack, ev: Optional[dict], win: Optional[dict]) -> None:
        c = self.cfg
        if ev is None and win is None:
            trk.last = {"obs": "none"}
            return
        moving = False
        inst_static = True
        if ev is not None:
            moving = ev["m2"] >= c.q_move ** 2 and ev["speed"] >= c.v_move_mps
            inst_static = ev["m2"] < c.q_static ** 2
        if win is not None and (trk.role == ROLE_DYNAMIC or c.window_moving_potential):
            moving = moving or (win["v_lat"] >= max(c.v_move_mps, c.q_move * win["s_lat"])
                                or abs(win["v_rad"]) >= max(c.v_move_radial_mps, c.q_move * win["s_rad"]))
        contra = False                 # P6: windowed motion contradicts "static" (potential objects, unveto option)
        if (win is not None and not moving and trk.role != ROLE_DYNAMIC and c.window_unveto_potential
                and not c.window_moving_potential):
            contra = (win["v_lat"] >= max(c.v_move_mps, c.q_move * win["s_lat"])
                      or abs(win["v_rad"]) >= max(c.v_move_radial_mps, c.q_move * win["s_rad"]))
        static = (not moving and not contra and inst_static and win is not None
                  and win["v_lat"] + 2.0 * win["s_lat"] < c.v_static_mps
                  and (not c.radial_static_required or abs(win["v_rad"]) + 2.0 * win["s_rad"] < c.v_static_radial_mps))
        trk.n_obs += 1
        if moving:
            trk.l = min(c.l_max, trk.l + c.l_up)
        elif static:
            trk.l = max(-c.l_max, trk.l - c.l_down)
        elif contra:
            trk.l = max(trk.l, 0.0)
        if trk.l >= c.th_moving:
            trk.is_moving = True
        elif trk.l <= 0.0:
            trk.is_moving = False
        if trk.l <= c.th_static:
            trk.is_static = True
        elif trk.l >= 0.0:
            trk.is_static = False
        out = {"obs": "moving" if moving else ("static" if static else ("contra" if contra else "uncertain"))}
        if ev is not None:
            out.update(speed=round(ev["speed"], 3), q=round(math.sqrt(ev["m2"]), 2), n=ev["n"], rng=round(ev["rng"], 2))
        if win is not None:
            out.update(w_lat=round(win["v_lat"], 3), w_slat=round(win["s_lat"], 3), w_rad=round(win["v_rad"], 3),
                       w_srad=round(win["s_rad"], 3))
        trk.last = out

    # ------------------------------------------------------------------ main
    def update(self, left: np.ndarray, right: Optional[np.ndarray], stamp: float, instances: Sequence[Instance],
               R_imu: Optional[np.ndarray]) -> Dict[int, bool]:
        """Process frame k. `R_imu` = R_{I_{k-1} I_k} from the gyro (None: no IMU -> no evidence, state reset).

        Instances need role, bbox, mask and (if available) depth / disparity / work_box / disp_crop.
        Returns {instance index: True (moving potential -> root) | False (static -> still / veto)}.
        Fills ``inst.motion`` (summary) and ``inst.track_id`` is NOT touched (separate id space: motion_id).
        """
        c = self.cfg
        t0 = time.perf_counter()
        self.frame += 1
        img_s, pyr = self._pyr(left)
        dt = (stamp - self.prev_t) if self.prev_t is not None else 0.0
        R_g = None
        gyro_sigma = c.gyro_sigma_rad
        if R_imu is not None:
            R_g = self.R_CI.T @ R_imu.T @ self.R_CI
        elif self.prev_pyr is not None and c.no_imu_sigma_rad > 0:
            R_g = np.eye(3)                    # gyro gap: rotation from the background points (weak prior)
            gyro_sigma = c.no_imu_sigma_rad
        relevant = [i for i, x in enumerate(instances) if x.role in (ROLE_DYNAMIC, ROLE_POTENTIAL)]
        if c.min_bbox_px > 0:          # tiny (far) instances: no evidence (prior / P2 behaviour), no cost
            relevant = [i for i in relevant if min(instances[i].bbox[2] - instances[i].bbox[0],
                                                   instances[i].bbox[3] - instances[i].bbox[1]) >= c.min_bbox_px]
        stats = {"n_bg": 0, "n_inl": 0, "t_ok": False}
        ego = None
        ev_by_tid: Dict[int, Optional[dict]] = {}
        votes: Dict[int, Dict[int, int]] = {}
        new_in_p, new_in_tid = np.zeros((0, 2)), np.zeros(0, np.int64)
        new_in_X = np.zeros((0, 3))
        bg_keep = np.zeros((0, 2))
        bg_kX = np.zeros((0, 3))
        bg_kage = np.zeros(0, np.int64)
        if self.prev_pyr is not None and R_g is not None and 0 < dt < 1.0:
            # ---- track everything k-1 -> k
            allp = np.vstack([self.bg_p, self.in_p])
            nb = len(self.bg_p)
            # forward-backward check only for the instance points (background outliers: robust ego fit)
            p1, ok = self._klt(self.prev_pyr, pyr, allp, fb=False)
            if len(self.in_p):
                ok[nb:] &= self._fb_ok(self.prev_pyr, pyr, self.in_p, p1[nb:], ok[nb:])
            b1, okb = self.bearings(p1)
            ok &= okb
            # ---- ego-motion from background points with depth
            bok = ok[:nb] & np.isfinite(self.bg_X).all(axis=1)
            ego_c = self.estimate_ego(self.bg_X[bok], b1[:nb][bok], R_g, dt, gyro_sigma)
            if R_imu is not None or ego_c.t_ok:   # gyro gap without background: no evidence this frame
                ego = ego_c
        if ego is not None:
            stats.update(n_bg=int(bok.sum()), n_inl=ego.n_inliers, t_ok=ego.t_ok,
                         sigma_bg_px=round(ego.sigma_bg * self.f_raw, 3), t=[round(float(v), 4) for v in ego.t],
                         dtheta_deg=round(float(np.degrees(np.linalg.norm(ego.dtheta))), 4),
                         rot_deg=round(float(np.degrees(np.linalg.norm(so3_log(R_g)))), 3),
                         gyro=R_imu is not None)
            bg_keep = p1[:nb][ok[:nb]]
            # background depth propagated with the ego-motion (static points); re-measured when stale
            if ego.t_ok:
                bg_kX = self.bg_X[ok[:nb]] @ ego.R.T + ego.t
                bg_kage = self.bg_age[ok[:nb]] + 1
            else:
                bg_kX = np.full((len(bg_keep), 3), np.nan)
                bg_kage = np.full(len(bg_keep), 1 << 30)
            # ---- instance points
            ip, iok = p1[nb:], ok[nb:]
            ib = b1[nb:]
            Xok = iok & np.isfinite(self.in_X).all(axis=1)
            # votes: tracked instance points landing inside current instance masks
            q = np.rint(ip).astype(np.int64)
            for i in relevant:
                inst = instances[i]
                x0, y0, x1, y1 = inst.bbox
                inside = iok & (q[:, 0] >= x0) & (q[:, 0] < x1) & (q[:, 1] >= y0) & (q[:, 1] < y1)
                if not inside.any():
                    continue
                idx = np.flatnonzero(inside)
                hit = inst.mask[q[idx, 1], q[idx, 0]]
                for tid in self.in_tid[idx[hit]]:
                    d = votes.setdefault(i, {})
                    d[int(tid)] = d.get(int(tid), 0) + 1
            new_in_p, new_in_tid = ip[iok], self.in_tid[iok]
            new_in_X = self.in_X[iok] @ ego.R.T + ego.t      # static propagation (fallback depth)
        else:
            # no IMU / first frame / time jump: drop the point and track history (no evidence)
            self.tracks = {}
        self.last_ego = ego
        # chained ego-motion for the windowed test; a frame without a translation estimate breaks the chain
        if ego is not None and ego.t_ok and (self.frame - 1) in self.poses:
            Tk = np.eye(4)
            Tk[:3, :3], Tk[:3, 3] = ego.R, ego.t                     # T_{k<-k-1}
            self.poses[self.frame] = self.poses[self.frame - 1] @ np.linalg.inv(Tk)
        else:
            self.poses = {self.frame: np.eye(4)}
            for trk in self.tracks.values():
                trk.hist = []
        keep_frames = 64 if c.window_long_s <= 0 else 200           # P7 long window: up to ~3 s of 20+ Hz poses
        for f_ in [f_ for f_ in self.poses if f_ < self.frame - keep_frames]:
            del self.poses[f_]
        t1 = time.perf_counter()

        # ---- association instance <-> motion track (greedy on votes, same role)
        assign: Dict[int, int] = {}
        pairs = sorted(((n, -i, tid) for i, d in votes.items() for tid, n in d.items()), reverse=True)
        used = set()
        for n, mi, tid in pairs:
            i = -mi
            trk = self.tracks.get(tid)
            if n < 3 or i in assign or tid in used or trk is None or trk.role != instances[i].role:
                continue
            assign[i] = tid
            used.add(tid)
        # fallback: bbox IoU with the track's previous box (few / no tracked points, e.g. small instances)
        free = [i for i in relevant if i not in assign]
        if free:
            cand = []
            tl = [(tid, trk) for tid, trk in self.tracks.items() if tid not in used and trk.box is not None]
            if tl:                       # vectorised box_iou (P7: identical candidates, ~100 x 100 pairs in the aisles)
                iou = _iou_matrix(np.array([instances[i].bbox for i in free], np.int64),
                                  np.array([trk.box for _, trk in tl], np.int64))
                frole = np.array([instances[i].role for i in free], object)
                trole = np.array([trk.role for _, trk in tl], object)
                a_, b_ = np.nonzero((iou >= 0.3) & (frole[:, None] == trole[None, :]))
                cand = [(float(iou[a, b]), -free[a], tl[b][0]) for a, b in zip(a_, b_)]
            for iou, mi, tid in sorted(cand, reverse=True):
                if -mi in assign or tid in used:
                    continue
                assign[-mi] = tid
                used.add(tid)
        if ego is not None:                          # evidence only for tracks seen in this frame
            groups = []
            for i, tid in assign.items():
                sel = (self.in_tid == tid) & Xok
                groups.append((tid, self.in_X[sel], ib[sel]))
            ev_by_tid.update(self.instance_fits(groups, ego, dt))
        pre_dup: Dict[int, int] = {}       # unmatched duplicate of a matched instance: no track of its own
        if c.dup_overlap > 0:
            inter = _box_intersects(instances)      # P7: bbox prefilter (mask_overlap is 0 without bbox intersection)
            for i in relevant:
                if i in assign:
                    continue
                for j, tj in assign.items():
                    if inter[i, j] and instances[j].role == instances[i].role and \
                            mask_overlap(instances[i], instances[j]) >= c.dup_overlap:
                        pre_dup[i] = tj
                        break
        for i in relevant:
            if i not in assign and i not in pre_dup:
                inst = instances[i]
                prior = c.prior_dynamic if inst.role == ROLE_DYNAMIC else c.prior_potential
                trk = MotionTrack(id=self._next_id, role=inst.role, cls=inst.cls, l=prior)
                trk.is_static = prior <= c.th_static
                trk.is_moving = prior >= c.th_moving
                self.tracks[trk.id] = trk
                self._next_id += 1
                assign[i] = trk.id
        inv_assign = {tid: i for i, tid in assign.items()}
        a_idx = list(assign.keys())
        anchors = dict(zip(a_idx, self.anchor_points([instances[i] for i in a_idx])))
        for tid, trk in list(self.tracks.items()):
            i = inv_assign.get(tid)
            win = None
            win_long = None
            if i is not None:
                P = anchors[i]
                if P is not None:
                    trk.hist.append((self.frame, stamp, P))
                    trk.hist = [h for h in trk.hist if stamp - h[1] <= max(c.window_max_s, c.window_long_s) + 0.05]
                    win = self.window_fit(trk, stamp)
                    if c.window_long_s > 0:
                        win_long = self.window_fit(trk, stamp, 0.75 * c.window_long_s, c.window_long_s)
            ev = ev_by_tid.get(tid)
            self._observe(trk, ev, win)
            trk.raw = {"stamp": stamp, "ev": ev, "win": win, "win_long": win_long, "matched": i is not None}
            matched = i is not None
            if matched:
                trk.missing = 0
                trk.box = instances[[i for i, t in assign.items() if t == tid][0]].bbox
            else:
                trk.missing += 1
                if trk.missing > c.max_missing:
                    del self.tracks[tid]
        # duplicate detections (YOLO: two strongly overlapping masks of one object): the instance on the younger
        # track uses the decision of the older track (occluding people have disjoint masks -> not merged)
        dup: Dict[int, int] = {}
        if c.dup_overlap > 0:
            items = sorted(assign.items(), key=lambda kv: kv[1])          # older track first
            for a_ in range(len(items)):
                i, ti = items[a_]
                for j, tj in items[:a_]:
                    if j in dup or not inter[i, j] or instances[i].role != instances[j].role:
                        continue
                    if mask_overlap(instances[i], instances[j]) >= c.dup_overlap:
                        dup[i] = tj
                        break
        dup.update(pre_dup)
        decisions: Dict[int, bool] = {}
        for i, tid in [(i, dup.get(i, t)) for i, t in assign.items()] + list(pre_dup.items()):
            trk = self.tracks.get(tid)
            if trk is None:
                continue
            inst = instances[i]
            inst.motion = {"id": tid, "state": trk.state, "l": round(trk.l, 2), **trk.last}
            if i in dup:
                inst.motion["dup"] = True
            if inst.role == ROLE_DYNAMIC:
                if c.use_still and trk.is_static:
                    decisions[i] = False
            else:
                if c.promote_moving and trk.is_moving:
                    decisions[i] = True
                elif c.veto_static and trk.is_static:
                    decisions[i] = False
        t2 = time.perf_counter()

        # ---- prepare frame k for the next step: instance points (keep + re-detect), background points
        live = set(self.tracks)
        keep = np.isin(new_in_tid, list(live)) if len(new_in_tid) else np.zeros(0, bool)
        new_in_p, new_in_tid, new_in_X = new_in_p[keep], new_in_tid[keep], new_in_X[keep]
        tid_to_inst = {tid: i for i, tid in assign.items()}
        q = np.rint(new_in_p).astype(np.int64)
        keep = np.ones(len(new_in_p), bool)
        for tid in np.unique(new_in_tid):
            i = tid_to_inst.get(int(tid))
            if i is not None:              # drop points that left their (re-detected) instance
                sel = np.flatnonzero(new_in_tid == tid)
                keep[sel] = instances[i].mask[q[sel, 1], q[sel, 0]]
        new_in_p, new_in_tid, new_in_X = new_in_p[keep], new_in_tid[keep], new_in_X[keep]
        add_p, add_t, add_X = [new_in_p], [new_in_tid], [new_in_X]
        er = int(round(c.inst_erode_px * self.s))
        for i in relevant:
            if i not in assign:                    # duplicate detection without a track: no points of its own
                continue
            inst = instances[i]
            tid = assign[i]
            have = int(np.count_nonzero(new_in_tid == tid))
            need = int(c.inst_points) - have
            if have >= c.redetect_ratio * c.inst_points or need <= 2:
                continue
            pts = self._detect_in_instance(img_s, inst, need, er, new_in_p[new_in_tid == tid])
            if len(pts):
                add_p.append(pts)
                add_t.append(np.full(len(pts), tid, np.int64))
                add_X.append(np.full((len(pts), 3), np.nan))
        in_p = np.vstack(add_p)
        in_tid = np.concatenate(add_t)
        prop = np.vstack(add_X)
        # background: drop points that entered an instance bbox, top off, stereo depth
        boxes = [expand_box(x.bbox, int(c.bg_exclude_px), 0.0, *self.cam0.size) for x in instances
                 if x.role in (ROLE_DYNAMIC, ROLE_POTENTIAL)]
        if len(bg_keep):
            out = np.zeros(len(bg_keep), bool)
            for (x0, y0, x1, y1) in boxes:
                out |= (bg_keep[:, 0] >= x0) & (bg_keep[:, 0] < x1) & (bg_keep[:, 1] >= y0) & (bg_keep[:, 1] < y1)
            bg_keep, bg_kX, bg_kage = bg_keep[~out], bg_kX[~out], bg_kage[~out]
        if len(bg_keep) < 0.8 * c.bg_points:
            add = self._detect_background(img_s, boxes, bg_keep, int(c.bg_points) - len(bg_keep))
            if len(add):
                bg_keep = np.vstack([bg_keep, add])
                bg_kX = np.vstack([bg_kX, np.full((len(add), 3), np.nan)])
                bg_kage = np.concatenate([bg_kage, np.full(len(add), 1 << 30)])
        # one left->right KLT for background + instance points: the instance depths then share the scale of the
        # background depths that fix the ego translation (ROI SGBM medians were ~20 % deeper on T265 -> biased looming)
        # stereo only for: background points without (valid propagated) depth or stale (>= stereo_refresh frames),
        # and up to stereo_inst_points points per instance (the instance depth is their median)
        bmeas = ~np.isfinite(bg_kX).all(axis=1) | (bg_kage >= c.stereo_refresh)
        imeas = np.zeros(len(in_p), bool)
        for tid in np.unique(in_tid):
            imeas[np.flatnonzero(in_tid == tid)[:int(c.stereo_inst_points)]] = True
        bidx, iidx = np.flatnonzero(bmeas), np.flatnonzero(imeas)
        bl, dl = self._stereo_disp(pyr, right, np.vstack([bg_keep[bidx], in_p[iidx]]))
        nbm = len(bidx)
        bg_X = bg_kX.copy()
        bg_age = bg_kage.copy()
        bg_X[bidx] = np.nan
        okb = np.isfinite(dl[:nbm])
        bg_X[bidx[okb]] = self.point_from_disparity(bl[:nbm][okb], np.maximum(dl[:nbm][okb], 0.25))
        bg_age[bidx] = 0
        bi = np.full((len(in_p), 3), np.nan)
        di = np.full(len(in_p), np.nan)
        bi[iidx], di[iidx] = bl[nbm:], dl[nbm:]
        need_b = ~imeas
        if need_b.any():
            bi[need_b] = self.bearings(in_p[need_b])[0]
        in_X = self._instance_depth(in_p, in_tid, tid_to_inst, instances, bi, di)
        use_prop = ~np.isfinite(in_X).all(axis=1) & np.isfinite(prop).all(axis=1)
        in_X[use_prop] = prop[use_prop]
        t3 = time.perf_counter()
        self.bg_p, self.bg_X, self.bg_age = bg_keep, bg_X, bg_age
        self.in_p, self.in_X, self.in_tid = in_p, in_X, in_tid
        self.prev_pyr, self.prev_t = pyr, stamp
        stats.update(n_tracks=len(self.tracks), n_inst_pts=int(len(in_p)),
                     ms={"flow_ego": round((t1 - t0) * 1e3, 3), "assoc": round((t2 - t1) * 1e3, 3),
                         "points": round((t3 - t2) * 1e3, 3)})
        self.last_stats = stats
        return decisions

    # ------------------------------------------------------------------ point management
    def _detect_in_instance(self, img_s, inst: Instance, n: int, er: int, existing: np.ndarray) -> np.ndarray:
        s = self.s
        x0, y0, x1, y1 = inst.bbox
        sx0, sy0 = int(math.floor(x0 * s)), int(math.floor(y0 * s))
        sx1, sy1 = min(self.size_s[0], int(math.ceil(x1 * s))), min(self.size_s[1], int(math.ceil(y1 * s)))
        if sx1 - sx0 < 4 or sy1 - sy0 < 4:
            return np.zeros((0, 2))
        crop = inst.mask[y0:y1, x0:x1].astype(np.uint8)
        m = cv2.resize(crop, (sx1 - sx0, sy1 - sy0), interpolation=cv2.INTER_NEAREST)
        if er > 0:
            m = cv2.erode(m, np.ones((2 * er + 1, 2 * er + 1), np.uint8))
        for p in existing:
            cv2.circle(m, (int(p[0] * s) - sx0, int(p[1] * s) - sy0), 3, 0, -1)
        if self.static_mask_s is not None:
            m[self.static_mask_s[sy0:sy1, sx0:sx1]] = 0
        if not m.any():
            return np.zeros((0, 2))
        c = cv2.goodFeaturesToTrack(img_s[sy0:sy1, sx0:sx1], maxCorners=int(n), qualityLevel=0.01, minDistance=3,
                                    mask=m * 255, blockSize=5)
        if c is None:
            return np.zeros((0, 2))
        c = c.reshape(-1, 2)
        return (c + np.array([sx0, sy0])) / s

    def _detect_background(self, img_s, boxes, existing: np.ndarray, n: int) -> np.ndarray:
        if n <= 0:
            return np.zeros((0, 2))
        s = self.s
        m = np.full(img_s.shape[:2], 255, np.uint8)
        if self.static_mask_s is not None:
            m[self.static_mask_s] = 0
        for (x0, y0, x1, y1) in boxes:
            m[int(y0 * s):int(math.ceil(y1 * s)), int(x0 * s):int(math.ceil(x1 * s))] = 0
        for p in existing:
            cv2.circle(m, (int(p[0] * s), int(p[1] * s)), 8, 0, -1)
        c = cv2.goodFeaturesToTrack(img_s, maxCorners=int(n), qualityLevel=0.01, minDistance=8, mask=m, blockSize=5)
        if c is None:
            return np.zeros((0, 2))
        return c.reshape(-1, 2).astype(np.float64) / s

    def _stereo_disp(self, img_l, right: Optional[np.ndarray], pts: np.ndarray):
        """Left->right KLT: (cam0 bearings, rectified disparity; nan = no valid match)."""
        bl, okl = self.bearings(pts, 0)
        d = np.full(len(pts), np.nan)
        if right is None or len(pts) == 0:
            return bl, d
        _, img_r = self._pyr(right)
        pr, ok = self._klt(img_l, img_r, pts, fb=False)
        br, okr = self.bearings(pr, 1)
        ul, vl_ok = self._rect_uv(bl, 0)
        ur, vr_ok = self._rect_uv(br, 1)
        dd = ul[:, 0] - ur[:, 0]
        ok &= okl & okr & vl_ok & vr_ok & (np.abs(ul[:, 1] - ur[:, 1]) < self.cfg.stereo_max_dy_px) & (dd > -0.5)
        d[ok] = dd[ok]
        return bl, d

    def _instance_depth(self, pts, tids, tid_to_inst, instances, b, d_klt) -> np.ndarray:
        """3D of instance points at frame k: the track's median KLT stereo disparity (per_point_depth: the point's
        own disparity when within +-max(1 px, 30 %) of that median), else the instance ROI-SGBM median."""
        X = np.full((len(pts), 3), np.nan)
        if len(pts) == 0:
            return X
        d = np.full(len(pts), np.nan)
        for tid in np.unique(tids):
            sel = tids == tid
            dk = d_klt[sel]
            v = dk[np.isfinite(dk) & (dk > 0)]
            if v.size >= 3:
                med = float(np.median(v))
                if self.cfg.per_point_depth:
                    d[sel] = np.where(np.isfinite(dk) & (np.abs(dk - med) < max(1.0, 0.3 * med)), dk, med)
                else:   # one robust depth per instance: KLT patches at the mask boundary match the background
                    d[sel] = med
            else:
                i = tid_to_inst.get(int(tid))
                dm = instances[i].disparity if i is not None else math.nan
                if math.isfinite(dm) and dm > 0:
                    d[sel] = dm
        good = np.isfinite(d) & (d > 0)
        X[good] = self.point_from_disparity(b[good], d[good])
        return X


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """box_iou of every pair (A x 4, B x 4 int boxes, x1/y1 exclusive) -> A x B (same values as types.box_iou)."""
    ix0 = np.maximum(a[:, None, 0], b[None, :, 0])
    iy0 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix1 = np.minimum(a[:, None, 2], b[None, :, 2])
    iy1 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.where((ix1 > ix0) & (iy1 > iy0), (ix1 - ix0) * (iy1 - iy0), 0)
    aa = np.maximum(0, a[:, 2] - a[:, 0]) * np.maximum(0, a[:, 3] - a[:, 1])
    ab = np.maximum(0, b[:, 2] - b[:, 0]) * np.maximum(0, b[:, 3] - b[:, 1])
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(inter > 0, inter / (aa[:, None] + ab[None, :] - inter).astype(np.float64), 0.0)


def _box_intersects(instances: Sequence[Instance]) -> np.ndarray:
    """N x N: bboxes intersect (non-empty overlap)."""
    if not instances:
        return np.zeros((0, 0), bool)
    b = np.array([x.bbox for x in instances], np.int64)
    return ((np.minimum(b[:, None, 2], b[None, :, 2]) > np.maximum(b[:, None, 0], b[None, :, 0]))
            & (np.minimum(b[:, None, 3], b[None, :, 3]) > np.maximum(b[:, None, 1], b[None, :, 1])))


def mask_overlap(a: Instance, b: Instance) -> float:
    """|mask_a & mask_b| / min(|mask_a|, |mask_b|) (0 if the bboxes do not intersect)."""
    x0, y0 = max(a.bbox[0], b.bbox[0]), max(a.bbox[1], b.bbox[1])
    x1, y1 = min(a.bbox[2], b.bbox[2]), min(a.bbox[3], b.bbox[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = int(np.count_nonzero(a.mask[y0:y1, x0:x1] & b.mask[y0:y1, x0:x1]))
    if inter == 0:
        return 0.0
    return inter / max(1, min(a.area, b.area))


class PrecomputedEvidence:
    """MotionEvidence adapter: returns the decisions stored in ``context['motion']`` (or nothing)."""

    def __call__(self, instances, context=None):
        return dict((context or {}).get("motion") or {})
