# SPDX-License-Identifier: GPL-3.0-or-later
"""Smooth camera trajectories with analytic derivatives, and smooth planar paths for the moving actors.

Camera (IMU/body) trajectory
----------------------------
Position p(t) = [x, y, z] and yaw psi(t) are clamped quintic B-splines (C^4) fitted by least squares to a
reference built from a 2D polyline (constant cruise speed, slow-down at corners, smooth ramps), a smooth height
profile and a smooth yaw "look-around" offset. The first/last 5 control points of every spline are set equal, so
all derivatives up to the 4th vanish at both ends: the platform hovers exactly still before `t_start` and after
`t_end` (C^4 junction), which also gives OpenVINS a clean static initialisation window.

Attitude:
  * platform "drone": differential flatness of a quadrotor (Mellinger & Kumar 2011): body z axis along the specific
    force direction  z_b = (a + g e3) / |a + g e3|,  x_c = [cos psi, sin psi, 0],  y_b = z_b x x_c / |..|,
    x_b = y_b x z_b.  Roll/pitch therefore follow the acceleration (smooth, physically plausible).
  * platform "amr": roll = pitch = 0, R = Rz(psi), z constant.
Body angular velocity (closed form, exact):
  z_b' = (I - z_b z_b^T) j / |t|  (j = jerk);  p = -y_b . z_b',  q = x_b . z_b',
  r = (p (z_b . x_c) + psi' (y_b . y_c)) / (x_b . x_c),  y_c = [-sin psi, cos psi, 0]
  (from d/dt (y_b . x_c) = 0; for the AMR this reduces to w = [0, 0, psi']).
IMU (body frame = IMU frame, FLU):  gyro = w_B,  accel = R^T (a - g_W) with g_W = [0, 0, -g].
"""
import numpy as np
from scipy.interpolate import BSpline, make_lsq_spline

from .se3 import rotz

G = 9.81


# ----------------------------------------------------------------------------------------------- splines
class ClampedSpline:
    """Vector-valued B-spline on [t0, t1], constant outside (derivatives 0 outside)."""

    def __init__(self, spl: BSpline, t0: float, t1: float):
        self.spl, self.t0, self.t1 = spl, float(t0), float(t1)
        self.d = [spl] + [spl.derivative(k) for k in range(1, 5)]

    def __call__(self, t, nu=0):
        t = np.asarray(t, float)
        tc = np.clip(t, self.t0, self.t1)
        y = self.d[nu](tc)
        if nu > 0:
            out = (t < self.t0) | (t > self.t1)
            y = np.where(out.reshape(out.shape + (1,) * (y.ndim - out.ndim)), 0.0, y)
        return y


def fit_clamped_quintic(t, Y, knot_dt, clamp=True, end_dense=(0.0, 0.2)):
    """LSQ quintic B-spline through samples (t, Y[n, d]); first/last 5 control points pinned to Y[0] / Y[-1]
    (all derivatives up to the 4th vanish at both ends). end_dense = (duration, spacing): denser knots over the first
    and last `duration` seconds so the pinned spline can follow a quick start / stop without overshoot."""
    t = np.asarray(t, float)
    Y = np.asarray(Y, float)
    if Y.ndim == 1:
        Y = Y[:, None]
    k = 5
    t0, t1 = t[0], t[-1]
    n_int = max(int(np.floor((t1 - t0) / knot_dt)) - 1, 1)
    inner = np.linspace(t0, t1, n_int + 2)[1:-1]
    dd, ds = end_dense
    if dd > 0 and (t1 - t0) > 4 * dd:
        inner = inner[(inner > t0 + dd) & (inner < t1 - dd)]
        inner = np.sort(np.r_[np.arange(t0 + ds, t0 + dd, ds), inner, np.arange(t1 - dd + ds, t1 - ds / 2, ds)])
    knots = np.r_[[t0] * (k + 1), inner, [t1] * (k + 1)]
    spl = make_lsq_spline(t, Y, knots, k=k)
    c = spl.c.copy()
    if clamp:
        c[:k] = Y[0]
        c[-k:] = Y[-1]
    return ClampedSpline(BSpline(knots, c, k), t0, t1)


def smoothstep5(x):
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (10 - 15 * x + 6 * x * x)


# ----------------------------------------------------------------------------------------------- reference paths
def polyline_reference(waypoints, speed, dt=0.01, ramp_s=2.5, stop_dist=1.5, corner_slow=0.45,
                       corner_radius=1.5, v_min=0.04, seg_speeds=None, speed_blend=3.0):
    """Time samples (t from 0, xy) moving along a polyline: cruise `speed`, slower near corners, smooth
    start/stop. Returns (t[n], xy[n, 2], s[n]).
    seg_speeds (optional, one per polyline segment): per-segment cruise speed instead of `speed`, blended with a
    C^2 smoothstep over `speed_blend` metres centred on each inner waypoint (held-out trajectories t2+; None = t1)."""
    P = np.asarray(waypoints, float)
    seg = np.diff(P, axis=0)
    L_seg = np.linalg.norm(seg, axis=1)
    keep = L_seg > 1e-6
    if seg_speeds is not None:
        seg_speeds = np.asarray(seg_speeds, float)
        assert len(seg_speeds) == len(seg), 'seg_speeds needs one value per polyline segment'
        seg_speeds = seg_speeds[keep]
    P = np.vstack([P[0], P[1:][keep]])
    seg = np.diff(P, axis=0)
    L_seg = np.linalg.norm(seg, axis=1)
    s_v = np.r_[0, np.cumsum(L_seg)]
    L = s_v[-1]
    turn = np.zeros(len(P))
    for i in range(1, len(P) - 1):
        a, b = seg[i - 1], seg[i]
        ang = np.arctan2(a[0] * b[1] - a[1] * b[0], a @ b)
        turn[i] = min(abs(ang) / (np.pi / 2), 1.5)

    def base_speed(s):
        if seg_speeds is None:
            return speed
        v = seg_speeds[0]
        for i in range(1, len(P) - 1):
            v += (seg_speeds[i] - seg_speeds[i - 1]) * smoothstep5((s - s_v[i]) / speed_blend + 0.5)
        return v

    def v_of_s(s):
        g = 0.0
        for i in range(1, len(P) - 1):
            g = max(g, turn[i] * np.exp(-0.5 * ((s - s_v[i]) / corner_radius) ** 2))
        return base_speed(s) * (1 - corner_slow * min(g, 1.0))

    ts, ss = [0.0], [0.0]
    t, s = 0.0, 0.0
    while s < L:
        v = v_of_s(s) * smoothstep5(t / ramp_s) if ramp_s > 0 else v_of_s(s)
        rem = L - s
        if rem < stop_dist:
            v = min(v, max((speed if seg_speeds is None else seg_speeds[-1]) * np.sqrt(rem / stop_dist), v_min))
        v = max(v, v_min) if t > 0.3 * ramp_s else v
        s = min(s + v * dt, L)
        t += dt
        ts.append(t)
        ss.append(s)
    ss = np.array(ss)
    idx = np.clip(np.searchsorted(s_v, ss, side='right') - 1, 0, len(seg) - 1)
    u = (ss - s_v[idx]) / L_seg[idx]
    xy = P[idx] + seg[idx] * u[:, None]
    return np.array(ts), xy, ss


def smooth_noise(t, amp, periods, seed, n=3):
    """Sum of n sinusoids with random phases / periods in [periods] (deterministic for a seed)."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(t)
    for _ in range(n):
        T = rng.uniform(*periods)
        out += np.sin(2 * np.pi * t / T + rng.uniform(0, 2 * np.pi))
    return amp * out / np.sqrt(n / 2.0)


# ----------------------------------------------------------------------------------------------- camera / body
class BodyTrajectory:
    """IMU(body) trajectory in the world frame (Z up). Times are relative seconds from the sequence start."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.platform = cfg.get('platform', 'drone')
        self.g = float(cfg.get('gravity', G))
        hover0 = float(cfg.get('hover_start_s', 3.0))
        hover1 = float(cfg.get('hover_end_s', 2.0))
        speed = float(cfg.get('speed', 1.0))
        extra = {}
        if cfg.get('seg_speeds') is not None:     # held-out t2+: per-segment cruise speed (absent in t1)
            extra = dict(seg_speeds=cfg['seg_speeds'], speed_blend=float(cfg.get('speed_blend', 3.0)))
        tr, xy, s_ref = polyline_reference(cfg['waypoints'], speed, ramp_s=float(cfg.get('ramp_s', 2.5)),
                                           corner_slow=float(cfg.get('corner_slow', 0.45)),
                                           corner_radius=float(cfg.get('corner_radius', 1.5)), **extra)
        tr = tr + hover0
        self.t_start, self.t_end = tr[0], tr[-1]
        self.duration = self.t_end + hover1
        tm = tr - tr[0]
        win = smoothstep5((tm - 1.5) / 4.0) * smoothstep5((tm[-1] - tm) / 4.0)   # height / yaw offsets fade in / out
        z0 = float(cfg.get('height', 1.4))
        if self.platform == 'drone':
            climb = float(cfg.get('takeoff_climb', 0.3))      # vertical climb at the start of the motion (take-off)
            ct = float(cfg.get('takeoff_climb_s', 1.5))
            z = z0 - climb * (1.0 - smoothstep5(tm / ct)) + \
                win * smooth_noise(tm, float(cfg.get('height_amp', 0.25)), (6.0, 14.0), cfg.get('seed', 0) + 11)
            if cfg.get('wp_heights') is not None:
                # held-out t2+: altitude profile, one height per waypoint, linear in arc length, Gaussian-smoothed in
                # time (sigma height_smooth_s); replaces the constant `height` (absent in t1)
                hw = np.asarray(cfg['wp_heights'], float)
                Pw = np.asarray(cfg['waypoints'], float)
                s_w = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Pw, axis=0), axis=1))]
                assert len(hw) == len(Pw), 'wp_heights needs one value per waypoint'
                h = np.interp(s_ref, s_w, hw)
                sg = float(cfg.get('height_smooth_s', 1.5))
                kk = int(round(3 * sg / 0.01))
                ker = np.exp(-0.5 * (np.arange(-kk, kk + 1) * 0.01 / sg) ** 2)
                ker /= ker.sum()
                h = np.convolve(np.r_[np.full(kk, h[0]), h, np.full(kk, h[-1])], ker, mode='valid')
                z = z + (h - z0)
        else:
            z = np.full_like(tm, z0)
        dense = (float(cfg.get('end_dense_s', 3.0)), float(cfg.get('end_dense_dt', 0.2)))
        self.pos = fit_clamped_quintic(tr, np.c_[xy, z], float(cfg.get('knot_dt', 0.6)), end_dense=dense)
        # yaw reference: heading of the fitted velocity (held where slow) + look-around offset
        v = self.pos(tr, 1)
        sp = np.linalg.norm(v[:, :2], axis=1)
        d0 = np.asarray(cfg['waypoints'][1], float) - np.asarray(cfg['waypoints'][0], float)
        hd = np.empty_like(tm)
        last = np.arctan2(d0[1], d0[0])
        for i in range(len(tm)):
            if sp[i] > 0.15:
                last = np.arctan2(v[i, 1], v[i, 0])
            hd[i] = last
        hd = np.unwrap(hd)
        yaw_amp = np.deg2rad(float(cfg.get('yaw_amp_deg', 15.0)))
        yaw = hd + win * smooth_noise(tm, yaw_amp, (4.0, 9.0), cfg.get('seed', 0) + 23)
        lim = np.deg2rad(float(cfg.get('yaw_rate_max_deg', 100.0)))
        kdt = float(cfg.get('yaw_knot_dt', 0.8))
        for _ in range(12):  # widen the yaw knot spacing until the yaw rate limit holds
            self.yaw = fit_clamped_quintic(tr, yaw, kdt, end_dense=dense)
            if np.abs(self.yaw(np.arange(tr[0], tr[-1], 0.01), 1)).max() <= lim:
                break
            kdt *= 1.15
        self.yaw_knot_dt = kdt

    # -- evaluation
    def eval(self, t):
        """Dict with p, v, a, j [n,3], yaw, yaw_d [n], R [n,3,3] (body->world), w_b [n,3] (body rates),
        f_b [n,3] (specific force in body = accelerometer)."""
        t = np.atleast_1d(np.asarray(t, float))
        p, v, a, j = (self.pos(t, k) for k in range(4))
        psi = self.yaw(t)[:, 0]
        psid = self.yaw(t, 1)[:, 0]
        n = len(t)
        xc = np.c_[np.cos(psi), np.sin(psi), np.zeros(n)]
        yc = np.c_[-np.sin(psi), np.cos(psi), np.zeros(n)]
        e3 = np.array([0, 0, 1.0])
        if self.platform == 'drone':
            th = a + self.g * e3
            tn = np.linalg.norm(th, axis=1, keepdims=True)
            zb = th / tn
            yb = np.cross(zb, xc)
            yb /= np.linalg.norm(yb, axis=1, keepdims=True)
            xb = np.cross(yb, zb)
            zbd = (j - np.sum(zb * j, 1, keepdims=True) * zb) / tn
            wp = -np.sum(yb * zbd, 1)
            wq = np.sum(xb * zbd, 1)
            wr = (wp * np.sum(zb * xc, 1) + psid * np.sum(yb * yc, 1)) / np.sum(xb * xc, 1)
            R = np.stack([xb, yb, zb], axis=2)
            w_b = np.c_[wp, wq, wr]
        else:
            R = np.stack([rotz(x) for x in psi])
            w_b = np.c_[np.zeros(n), np.zeros(n), psid]
        f_w = a + self.g * e3
        f_b = np.einsum('nji,nj->ni', R, f_w)
        return dict(t=t, p=p, v=v, a=a, j=j, yaw=psi, yaw_d=psid, R=R, w_b=w_b, f_b=f_b)


# ----------------------------------------------------------------------------------------------- actors
class PlanarPath:
    """Ground actor path (people, forklifts) on a fixed 100 Hz grid: xy(t), heading(t), speed(t), dist(t).
    Built from raw time samples (see wh.scenario.PathBuilder), Gaussian-smoothed in time (C-infinity; stops stay
    exactly still). Heading = direction of travel (+pi on reverse samples), held while (almost) stopped."""

    DT = 0.01

    def __init__(self, T, P, REV, duration, sigma=0.3, heading0=None):
        T, P, REV = np.asarray(T, float), np.asarray(P, float), np.asarray(REV, bool)
        grid = np.arange(0.0, max(duration, T[-1]) + 2.0 + self.DT / 2, self.DT)
        gx, gy = np.interp(grid, T, P[:, 0]), np.interp(grid, T, P[:, 1])
        grv = REV[np.clip(np.searchsorted(T, grid, side='right') - 1, 0, len(REV) - 1)]
        k = max(int(round(3 * sigma / self.DT)), 1)
        ker = np.exp(-0.5 * (np.arange(-k, k + 1) * self.DT / sigma) ** 2)
        ker /= ker.sum()

        def sm(x):
            return np.convolve(np.r_[np.full(k, x[0]), x, np.full(k, x[-1])], ker, mode='valid')

        gx, gy = sm(gx), sm(gy)
        vx, vy = np.gradient(gx, self.DT), np.gradient(gy, self.DT)
        sp = np.hypot(vx, vy)
        mv = np.nonzero(sp > 0.03)[0]
        if heading0 is None:
            heading0 = np.arctan2(vy[mv[0]], vx[mv[0]]) + (np.pi if grv[mv[0]] else 0.0) if len(mv) else 0.0
        hd = np.empty_like(sp)
        last = heading0
        for i in range(len(sp)):
            if sp[i] > 0.03:
                last = np.arctan2(vy[i], vx[i]) + (np.pi if grv[i] else 0.0)
                last = hd[i - 1] + np.angle(np.exp(1j * (last - hd[i - 1]))) if i else last
            hd[i] = last
        hd = sm(hd)
        self.grid, self.x, self.y, self.heading, self.speed = grid, gx, gy, hd, sp
        self.dist = np.r_[0, np.cumsum(sp[1:] * self.DT)]

    def at(self, t):
        t = np.asarray(t, float)
        return dict(xy=np.stack([np.interp(t, self.grid, self.x), np.interp(t, self.grid, self.y)], -1),
                    heading=np.interp(t, self.grid, self.heading), speed=np.interp(t, self.grid, self.speed),
                    dist=np.interp(t, self.grid, self.dist))
