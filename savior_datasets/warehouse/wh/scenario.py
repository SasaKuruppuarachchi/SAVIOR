# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene description shared by the scene definitions (scenes/*.py) and the Isaac renderer (pure data, numpy only).

A scene = environment USD + static props + procedural guard rails / windows + actors (people, forklifts). Actor
motion is fully scripted in time (PlanarPath), so the same camera trajectory can be rendered with different
dynamic levels and every pose / velocity is known exactly (moving flags, coverage).
"""
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .trajectory import PlanarPath, polyline_reference


# ----------------------------------------------------------------------------------------------- scene items
@dataclass
class Prop:
    name: str                     # unique, stable across levels (instance id is derived from the name)
    usd: str                      # path relative to the Isaac asset root ("Isaac/...") or absolute
    pos: tuple                    # (x, y, z) world
    yaw_deg: float = 0.0
    cls: Optional[str] = None     # warehouse class or None (= background, no instance id)
    scale: float = 1.0


@dataclass
class Rail:
    """Procedural yellow steel guard rail from p0 to p1 (posts every <= 1.5 m, two horizontal rails)."""
    name: str
    p0: tuple
    p1: tuple
    height: float = 1.0


@dataclass
class Window:
    """Wall window (Office SM_Window_3m_A asset), centre at pos, facing yaw."""
    name: str
    pos: tuple
    yaw_deg: float = 0.0


@dataclass
class Person:
    name: str
    character: str                # People/Characters/<character>/<character>.usd
    path: PlanarPath
    walk_speed_clip: float = 1.083   # m/s of the source walk loop (stand_walk_loop: 2.889 m in 80 frames @ 30 fps)
    active: Optional[tuple] = None   # (t_show, t_hide): visible only in this window (None = always)
    attached_to: Optional[str] = None   # t3+: name of the cart this person pushes (skipped in the pair clearance check)


@dataclass
class Forklift:
    name: str
    path: Optional[PlanarPath] = None      # None -> parked at `pose`
    pose: tuple = (0.0, 0.0, 0.0)          # (x, y, heading_deg) when parked; heading = direction the forks point
    driver: Optional[str] = None           # character name (seated) or None (driverless)
    load: str = 'boxes'                    # 'boxes' (pallet + 2x2x2 boxes), 'pallet', 'none'
    fork_lift: float = 0.25                # fork raise [m]
    active: Optional[tuple] = None         # (t_show, t_hide): visible only in this window (None = always)
    kind: str = 'forklift'                 # t3+: 'forklift' or 'cart' (pushed dolly, class trolley; load on top)


@dataclass
class Scene:
    name: str
    env: str
    env_classes: list                      # [(regex on env prim name, class)] for env prims below the env root
    env_hide: list = field(default_factory=list)   # regexes of env prims to deactivate (clear the way)
    props: List[Prop] = field(default_factory=list)
    rails: List[Rail] = field(default_factory=list)
    windows: List[Window] = field(default_factory=list)
    people: List[Person] = field(default_factory=list)
    forklifts: List[Forklift] = field(default_factory=list)
    lighting: str = 'default'
    # t3+: 'children' (t1/t2: env_classes / env_hide match the direct children of the env default prim) or
    # 'recursive' (walk the env tree: a prim whose name matches env_hide is deactivated, one matching env_classes is
    # labelled as a whole, otherwise its children are visited; for environments with nested layouts)
    env_label_mode: str = 'children'


# ----------------------------------------------------------------------------------------------- camera reference
class CamRef:
    """Planar reference of the camera (body) trajectory on a 100 Hz grid: arc length, points, normals, timing."""

    def __init__(self, body, dt=0.01):
        self.body = body
        self.t = np.arange(0.0, body.duration + dt / 2, dt)
        ev = body.eval(self.t)
        self.xy = ev['p'][:, :2]
        self.yaw = ev['yaw']
        d = np.r_[0, np.linalg.norm(np.diff(self.xy, axis=0), axis=1)]
        self.s = np.cumsum(d)
        self.L = self.s[-1]
        # unique arc-length samples for s -> xy
        self._su, iu = np.unique(self.s, return_index=True)
        self._xyu = self.xy[iu]

    def s_at(self, t):
        return np.interp(t, self.t, self.s)

    def xy_at(self, t):
        return np.stack([np.interp(t, self.t, self.xy[:, 0]), np.interp(t, self.t, self.xy[:, 1])], -1)

    def xy_at_s(self, s):
        return np.stack([np.interp(s, self._su, self._xyu[:, 0]), np.interp(s, self._su, self._xyu[:, 1])], -1)

    def tangent_at_s(self, s, h=0.3):
        d = self.xy_at_s(np.asarray(s) + h) - self.xy_at_s(np.asarray(s) - h)
        return d / np.maximum(np.linalg.norm(d, axis=-1, keepdims=True), 1e-9)

    def normal_at_s(self, s):
        tg = self.tangent_at_s(s)
        return np.stack([-tg[..., 1], tg[..., 0]], -1)   # left normal

    def t_at_s(self, s):
        """First time the camera reaches arc length s."""
        i = np.searchsorted(self.s, s)
        return float(self.t[min(i, len(self.t) - 1)])

    def t_near(self, xy, t_min=0.0, t_max=None):
        """Time of closest approach to xy within [t_min, t_max]."""
        m = (self.t >= t_min) & (self.t <= (t_max if t_max is not None else self.t[-1]))
        d = np.linalg.norm(self.xy[m] - np.asarray(xy, float), axis=1)
        return float(self.t[m][np.argmin(d)])

    def follow_point(self, t, ahead, lateral=0.0):
        s = self.s_at(t) + ahead
        return self.xy_at_s(s) + lateral * self.normal_at_s(s)


# ----------------------------------------------------------------------------------------------- path builder
class PathBuilder:
    """Compose an actor path from waits, polyline legs and camera-relative 'follow' segments, then smooth it."""

    def __init__(self, xy, t0=0.0):
        self.T, self.P, self.R = [0.0], [np.asarray(xy, float)], [False]
        if t0 > 0:
            self._push(t0, self.P[-1], False)

    def _push(self, t, xy, rev):
        self.T.append(float(t))
        self.P.append(np.asarray(xy, float))
        self.R.append(bool(rev))

    @property
    def t(self):
        return self.T[-1]

    @property
    def cur(self):
        return self.P[-1]

    def wait(self, dt):
        self._push(self.t + dt, self.cur, self.R[-1])
        return self

    def wait_until(self, t):
        if t > self.t:
            self._push(t, self.cur, self.R[-1])
        return self

    def leg(self, wps, speed, ramp=1.0, stop=True, reverse=False, corner_radius=1.0, corner_slow=0.5):
        pts = [self.cur] + [np.asarray(w, float) for w in wps]
        tr, xy, _ = polyline_reference(pts, speed, dt=0.01, ramp_s=ramp, stop_dist=(1.0 if stop else 0.0),
                                       corner_slow=corner_slow, corner_radius=corner_radius)
        t0 = self.t
        for t, p in zip(tr[1:], xy[1:]):
            self._push(t0 + t, p, reverse)
        return self

    def follow(self, cam: CamRef, t_end, ahead, lateral=0.0, ahead_end=None):
        """Camera-relative motion until t_end: point `ahead` m further along the camera path (+ `lateral` m to the
        left of it); `ahead_end` linearly changes the lead distance over the segment."""
        ts = np.arange(self.t + 0.01, t_end + 1e-9, 0.01)
        a1 = ahead if ahead_end is None else ahead_end
        for i, t in enumerate(ts):
            a = ahead + (a1 - ahead) * (i + 1) / len(ts)
            self._push(t, cam.follow_point(t, a, lateral), False)
        return self

    def build(self, duration, sigma=0.3) -> PlanarPath:
        return PlanarPath(self.T, self.P, self.R, duration, sigma=sigma)


def crossing(cam: CamRef, s_cross, lead_s, half_len, speed, side=1, t_offset=0.0):
    """Waypoints/timing for an actor crossing the camera path perpendicularly at arc length s_cross, passing the
    path `lead_s` seconds before the camera gets there. side=+1 starts on the left of the path.
    Returns (start_xy, end_xy, t_start)."""
    X = cam.xy_at_s(s_cross)
    n = cam.normal_at_s(s_cross)
    a, b = X + side * half_len * n, X - side * half_len * n
    t_x = cam.t_at_s(s_cross) - lead_s + t_offset
    # time to reach the middle from rest (ramp 1 s ~ 0.5 s lost)
    t_start = t_x - half_len / speed - 0.6
    return a, b, t_start


def is_active(actor, t):
    a = getattr(actor, 'active', None)
    return np.ones_like(np.asarray(t, float), bool) if a is None else (np.asarray(t) >= a[0]) & (np.asarray(t) <= a[1])


def min_distance(cam: CamRef, path: PlanarPath, t0=0.0, t1=None):
    t = cam.t[(cam.t >= t0) & (cam.t <= (cam.t[-1] if t1 is None else t1))]
    a = path.at(t)['xy']
    d = np.linalg.norm(a - cam.xy_at(t), axis=1)
    i = int(np.argmin(d))
    return float(d[i]), float(t[i])
