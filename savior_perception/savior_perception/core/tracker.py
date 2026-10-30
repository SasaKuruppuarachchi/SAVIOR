# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Lightweight multi-object mask tracker with chain hysteresis.

Track states: ``tentative -> confirmed -> lost -> removed``.

* Association: greedy on IoU (bbox or mask) between the constant-velocity *predicted*
  track box/mask and each detection of the same class (or any class if class-agnostic).
* Carry-over: a confirmed track that misses its detection becomes ``lost``; while lost
  (<= ``max_lost`` frames) its last mask, translated by the predicted centroid
  displacement, is emitted as a ``carried`` instance -- only for always-dynamic tracks
  and (``carry_promoted``) potential tracks still inside their promotion hysteresis.
  Never-promoted potential objects are never hallucinated.
* Chain hysteresis: a potential track promoted at frame t stays dynamic (status ``held``)
  until t + ``hysteresis_frames`` even if this frame's gating does not promote it (root
  occluded / missed). Held instances do not refresh the hysteresis and are not used as
  promotion roots, so cycles cannot keep a chain alive forever.

Time is counted in frames (constant frame rate assumed).

P4 ``motion_model: ego``: the predicted displacement of a track is the ego-motion induced displacement of
its centroid at its depth (gyro rotation + estimated translation, accumulated frame by frame while the
track is not re-detected) plus its own, ego-compensated, pixel velocity; ``pixel_cv`` (P2) is the plain
constant pixel velocity (lags under ego-rotation). Always-dynamic tracks whose last detection was
``still`` (static person, motion evidence) are never carried.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .config import TrackerConfig
from .types import (ROLE_DYNAMIC, ROLE_POTENTIAL, STATUS_CARRIED, STATUS_HELD, STATUS_PROMOTED,
                    STATUS_ROOT, STATUS_STILL, STATUS_UNPROMOTED, Box, Instance, box_area, box_intersection,
                    box_iou)

TENTATIVE, CONFIRMED, LOST, REMOVED = "tentative", "confirmed", "lost", "removed"


@dataclass(eq=False)
class Track:
    id: int
    cls: str
    role: str
    box: Box
    mask: np.ndarray                 # bool crop of `box`
    state: str = TENTATIVE
    hits: int = 1
    last_seen: int = 0
    last_promoted: Optional[int] = None
    vel: np.ndarray = field(default_factory=lambda: np.zeros(2))
    disparity: float = math.nan
    depth: float = math.nan
    sigma_z: float = math.nan
    area: int = 0
    off_ego: np.ndarray = field(default_factory=lambda: np.zeros(2))   # ego displacement since last_seen
    still: bool = False

    @property
    def center(self) -> np.ndarray:
        return np.array([(self.box[0] + self.box[2]) * 0.5, (self.box[1] + self.box[3]) * 0.5])

    def shift(self, frame: int) -> Tuple[int, int]:
        d = self.off_ego + self.vel * float(frame - self.last_seen)
        return int(round(d[0])), int(round(d[1]))


def _shift_box(box: Box, dx: int, dy: int) -> Box:
    return box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy


class MaskTracker:
    def __init__(self, cfg: TrackerConfig):
        self.cfg = cfg
        self.tracks: List[Track] = []
        self.frame = 0
        self._next_id = 1

    def reset(self):
        self.tracks = []
        self.frame = 0
        self._next_id = 1

    # ------------------------------------------------------------------ association
    def _iou(self, trk: Track, det: Instance) -> float:
        dx, dy = trk.shift(self.frame)
        pbox = _shift_box(trk.box, dx, dy)
        if self.cfg.iou_type == "bbox":
            return box_iou(pbox, det.bbox)
        inter = box_intersection(pbox, det.bbox)
        if inter is None:
            return 0.0
        x0, y0, x1, y1 = inter
        tm = trk.mask[y0 - pbox[1]:y1 - pbox[1], x0 - pbox[0]:x1 - pbox[0]]
        dm = det.mask[y0:y1, x0:x1]
        i = int(np.count_nonzero(tm & dm))
        u = trk.area + det.area - i
        return i / u if u > 0 else 0.0

    def _compatible(self, trk: Track, det: Instance) -> bool:
        if self.cfg.class_agnostic:
            return trk.role == det.role or (trk.role in (ROLE_DYNAMIC, ROLE_POTENTIAL)
                                            and det.role in (ROLE_DYNAMIC, ROLE_POTENTIAL))
        return trk.cls == det.cls

    def _pairs_bbox(self, instances, dets):
        """Vectorised bbox IoU of every (predicted track box, detection) pair; same values and candidate list as the
        per-pair loop (P7: ~100 x 100 pairs per frame in the warehouse aisles took ~15 ms in Python)."""
        f = self.frame
        tb = np.array([_shift_box(t.box, *t.shift(f)) for t in self.tracks], np.int64)          # T x 4
        db = np.array([instances[i].bbox for i in dets], np.int64)                             # D x 4
        ix0 = np.maximum(tb[:, None, 0], db[None, :, 0])
        iy0 = np.maximum(tb[:, None, 1], db[None, :, 1])
        ix1 = np.minimum(tb[:, None, 2], db[None, :, 2])
        iy1 = np.minimum(tb[:, None, 3], db[None, :, 3])
        inter = np.where((ix1 > ix0) & (iy1 > iy0), (ix1 - ix0) * (iy1 - iy0), 0)
        at = np.maximum(0, tb[:, 2] - tb[:, 0]) * np.maximum(0, tb[:, 3] - tb[:, 1])
        ad = np.maximum(0, db[:, 2] - db[:, 0]) * np.maximum(0, db[:, 3] - db[:, 1])
        with np.errstate(divide="ignore", invalid="ignore"):
            iou = np.where(inter > 0, inter / (at[:, None] + ad[None, :] - inter).astype(np.float64), 0.0)
        if self.cfg.class_agnostic:
            comp = np.array([[self._compatible(t, instances[i]) for i in dets] for t in self.tracks], bool)
        else:
            tc = np.array([t.cls for t in self.tracks], object)
            dc = np.array([instances[i].cls for i in dets], object)
            comp = tc[:, None] == dc[None, :]
        ok = comp & (iou >= self.cfg.iou_min)
        ti, dj = np.nonzero(ok)
        return [(float(iou[a, b]), -self.tracks[a].id, int(a), dets[b]) for a, b in zip(ti, dj)]

    # ------------------------------------------------------------------ main
    def update(self, instances: Sequence[Instance], image_shape: Tuple[int, int], ego=None) -> List[Instance]:
        """Associate this frame's classified detections; return carried instances.

        `ego` (motion_model ego): callable(points Nx2 raw px, rect depth N) -> predicted raw px at this frame of
        static points seen at the previous frame (MotionEstimator.ego_project), or None.

        Detections must already carry ``role`` and ``status`` (from gating). Status of a
        matched unpromoted potential detection may be changed to ``held`` in place, and
        ``track_id`` is set on every tracked detection.
        """
        self.frame += 1
        f = self.frame
        cfg = self.cfg
        if ego is not None and cfg.motion_model == "ego" and self.tracks:
            c_prev = np.array([t.center + t.off_ego + t.vel * float(f - 1 - t.last_seen) for t in self.tracks])
            z = np.array([t.depth for t in self.tracks], dtype=np.float64)
            pred = ego(c_prev, z)
            if pred is not None:
                for t, c0, c1 in zip(self.tracks, c_prev, pred):
                    if np.all(np.isfinite(c1)):
                        t.off_ego = t.off_ego + (c1 - c0)
        dets = [i for i, d in enumerate(instances) if d.role in (ROLE_DYNAMIC, ROLE_POTENTIAL)]
        if cfg.iou_type == "bbox" and self.tracks and dets:
            pairs = self._pairs_bbox(instances, dets)
        else:
            pairs = []
            for ti, trk in enumerate(self.tracks):
                for di in dets:
                    det = instances[di]
                    if not self._compatible(trk, det):
                        continue
                    iou = self._iou(trk, det)
                    if iou >= cfg.iou_min:
                        pairs.append((iou, -trk.id, ti, di))
        pairs.sort(reverse=True)
        t_used, d_used = set(), set()
        for _, _, ti, di in pairs:
            if ti in t_used or di in d_used:
                continue
            t_used.add(ti)
            d_used.add(di)
            self._update_track(self.tracks[ti], instances[di])
        for di in dets:
            if di not in d_used:
                self._new_track(instances[di])
        carried = []
        for ti, trk in enumerate(self.tracks):
            if ti in t_used or trk.last_seen == f:
                continue
            if trk.state == TENTATIVE:
                trk.state = REMOVED
                continue
            if f - trk.last_seen > cfg.max_lost:
                trk.state = REMOVED
                continue
            trk.state = LOST
            if self._carry_eligible(trk):
                inst = self._carry(trk, image_shape)
                if inst is not None:
                    carried.append(inst)
        self.tracks = [t for t in self.tracks if t.state != REMOVED]
        return carried

    def _in_hysteresis(self, trk: Track) -> bool:
        return trk.last_promoted is not None and self.frame - trk.last_promoted <= self.cfg.hysteresis_frames

    def _carry_eligible(self, trk: Track) -> bool:
        if trk.still:
            return False
        if trk.role == ROLE_DYNAMIC:
            return True
        return bool(self.cfg.carry_promoted) and self._in_hysteresis(trk)

    def _update_track(self, trk: Track, det: Instance):
        f = self.frame
        dt = max(1, f - trk.last_seen)
        c_old = trk.center
        trk.box = det.bbox
        trk.mask = np.array(det.crop(), copy=True)
        trk.area = int(np.count_nonzero(trk.mask))
        meas = (trk.center - c_old - trk.off_ego) / dt
        trk.off_ego = np.zeros(2)
        a = self.cfg.velocity_alpha
        trk.vel = meas if trk.hits == 1 else a * meas + (1.0 - a) * trk.vel
        trk.hits += 1
        trk.last_seen = f
        trk.cls, trk.role = det.cls, det.role
        if trk.state == TENTATIVE and trk.hits >= self.cfg.min_hits:
            trk.state = CONFIRMED
        elif trk.state == LOST:
            trk.state = CONFIRMED
        self._absorb_det(trk, det)

    def _new_track(self, det: Instance):
        trk = Track(id=self._next_id, cls=det.cls, role=det.role, box=det.bbox,
                    mask=np.array(det.crop(), copy=True), last_seen=self.frame)
        trk.area = int(np.count_nonzero(trk.mask))
        self._next_id += 1
        if self.cfg.min_hits <= 1:
            trk.state = CONFIRMED
        self.tracks.append(trk)
        self._absorb_det(trk, det)

    def _absorb_det(self, trk: Track, det: Instance):
        det.track_id = trk.id
        trk.still = det.status == STATUS_STILL
        if math.isfinite(det.disparity):
            trk.disparity, trk.depth, trk.sigma_z = det.disparity, det.depth, det.sigma_z
        if det.status in (STATUS_ROOT, STATUS_PROMOTED):
            trk.last_promoted = self.frame
        elif det.status == STATUS_UNPROMOTED and self._in_hysteresis(trk):
            det.status = STATUS_HELD

    def _carry(self, trk: Track, image_shape) -> Optional[Instance]:
        h, w = image_shape[:2]
        dx, dy = trk.shift(self.frame)
        x0, y0, x1, y1 = _shift_box(trk.box, dx, dy)
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            return None
        mask = np.zeros((h, w), bool)
        mask[cy0:cy1, cx0:cx1] = trk.mask[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        if box_area((cx0, cy0, cx1, cy1)) == 0 or not mask[cy0:cy1, cx0:cx1].any():
            return None
        return Instance(mask=mask, cls=trk.cls, score=0.0, bbox=(cx0, cy0, cx1, cy1), role=trk.role,
                        disparity=trk.disparity, depth=trk.depth, sigma_z=trk.sigma_z,
                        status=STATUS_CARRIED, track_id=trk.id)

    def summary(self) -> dict:
        out = {TENTATIVE: 0, CONFIRMED: 0, LOST: 0}
        for t in self.tracks:
            out[t.state] = out.get(t.state, 0) + 1
        return out
