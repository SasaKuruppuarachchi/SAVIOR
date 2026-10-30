# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""P7 selective masking policy: "conservative by default, selective when confident".

Labels every potential instance once per frame from the motion tracks of :class:`~.motion.MotionEstimator`
(``inst.motion["id"]``); :class:`~.gating.PromotionGate` turns the labels into statuses and
:meth:`SelectivePolicy.finalize` adds the temporal hysteresis.

Per motion track (potential role), with this frame's raw evidence (instantaneous GLS fit ``ev``, short window ``win``
= motion.window_min_s..window_max_s, optional long window ``win_long`` = [0.75, 1] x motion.window_long_s):

* **revoking observation** (any test): ``q_inst >= revoke_q`` and ``speed >= revoke_v`` (instantaneous), or for a window
  ``v_lat >= max(revoke_v, revoke_q s_lat)`` or ``|v_rad| >= max(revoke_v_radial, revoke_q s_rad)``. Thresholds are
  below the P4 "moving" ones (``q_move = 4``) because a revocation only masks. The static run is reset and the track
  cannot be confirmed static for ``revoke_hold_s``.
* **static observation**: no revocation, instantaneous ``q < motion.q_static`` (or no instantaneous fit), and the P4 static
  bound of the short window ``|v_lat| + 2 s_lat < v_static`` (and radial) -- or, with ``long_static``, the same bound for
  the long window (radial noise ~ 1 / window: a static forklift 4 m away can only be confirmed with the long window).
* **confirmed static** (label ``static``, provisional): an unbroken static run of ``>= confirm_s`` with ``>= confirm_min_obs``
  static observations whose newest observation is at most ``stale_s`` old. A run that is not re-confirmed for ``stale_s``
  (e.g. a leading forklift whose motion is along the epipolar line: neither static nor revoking) is reset, so the
  decision expires instead of sticking (no sticky veto).
* label ``moving`` = P4 ``is_moving`` (log-odds hysteresis; becomes a promotion root), else ``unknown``.

Gate (``gating.py``, selective branch): roots = always-dynamic instances (people) + ``moving`` potentials; a potential
instance in 2D contact with an *active* parent (root or object promoted from one; ``gating.max_depth`` hops) at a
compatible depth is promoted unless it is confirmed static AND the VIO has converged; an unpromoted instance is
unmasked if confirmed static (after convergence) or of a ``prior_static_classes`` class (boxes / pallets only move when
carried), else ``uncertain`` (masked, not a promotion parent unless ``unknown_promotes``).

Convergence proxy (deterministic, no feedback from the filter): ``converge_s`` after the motion onset (perception ego
speed ``> onset_speed_mps`` for ``onset_frames`` frames). Before it, a static confirmation neither vetoes a link nor
unmasks a non-prior class: objects that start moving at take-off together with the platform are masked from the start.

Hysteresis (:meth:`finalize`): a potential track masked at time t stays masked (status ``held``) until ``t + min_on_s``.
Held decisions do not refresh the hold (no self-sustaining masks); masking itself is immediate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence

import numpy as np

from .config import MotionConfig, SelectiveConfig
from .types import ROLE_POTENTIAL, STATUS_HELD, Instance

LABEL_MOVING, LABEL_STATIC, LABEL_HISTORY, LABEL_UNKNOWN = "moving", "static", "history", "unknown"


@dataclass
class _TrackMemory:
    run_t0: Optional[float] = None       # start of the current static run
    run_n: int = 0
    last_static_t: float = -math.inf
    revoke_t: float = -math.inf
    last_masked_t: float = -math.inf
    seen_t: float = -math.inf
    obs: str = ""
    revoke_by: str = ""
    ev_t0: Optional[float] = None        # first frame with evidence (history-static)
    ev_last_t: float = -math.inf
    rr: float = 0.0                      # EMA revocation rate over evidence frames


class SelectivePolicy:
    def __init__(self, cfg: SelectiveConfig, motion_cfg: MotionConfig):
        self.cfg = cfg
        self.mcfg = motion_cfg
        self.prior = {c.strip().lower() for c in cfg.prior_static_classes.split(",") if c.strip()}
        self.reset()

    def reset(self):
        self.mem: Dict[int, _TrackMemory] = {}
        self.prev_t: Optional[float] = None
        self.onset_count = 0
        self.onset_t: Optional[float] = None
        self.converged = False
        self.last_stats: dict = {}

    # ------------------------------------------------------------------ observations
    def _revokes(self, ev: Optional[dict], wins) -> str:
        """'' (no revocation) or which test revokes: i (instantaneous), wl / wr (short window lateral / radial),
        ll / lr (long window)."""
        c = self.cfg
        if ev is not None and ev["m2"] >= c.revoke_q ** 2 and ev["speed"] >= c.revoke_v_mps:
            return "i"
        for tag, w in zip(("w", "l"), wins):
            if w is None:
                continue
            if w["v_lat"] >= max(c.revoke_v_mps, c.revoke_q * w["s_lat"]):
                return tag + "l"
            if abs(w["v_rad"]) >= max(c.revoke_v_radial_mps, c.revoke_q * w["s_rad"]):
                return tag + "r"
        return ""

    def _static_bound(self, w: Optional[dict]) -> bool:
        m = self.mcfg
        if w is None:
            return False
        return (w["v_lat"] + 2.0 * w["s_lat"] < m.v_static_mps
                and (not m.radial_static_required or abs(w["v_rad"]) + 2.0 * w["s_rad"] < m.v_static_radial_mps))

    def observe(self, mem: _TrackMemory, raw: dict, stamp: float) -> str:
        """Update one track's static run from this frame's raw evidence; returns the observation kind."""
        c = self.cfg
        ev, win, wl = raw.get("ev"), raw.get("win"), raw.get("win_long")
        if ev is None and win is None and wl is None:
            obs = "none"
        elif self._revokes(ev, (win, wl)):
            obs = "revoke"
            mem.revoke_by = self._revokes(ev, (win, wl))
        elif (ev is None or ev["m2"] < self.mcfg.q_static ** 2) and \
                (self._static_bound(win) or (c.long_static and self._static_bound(wl))):
            obs = "static"
        else:
            obs = "uncertain"
        if obs != "none":
            if mem.ev_t0 is None:
                mem.ev_t0, mem.rr = stamp, (1.0 if obs == "revoke" else 0.0)
            else:
                a = 1.0 - math.exp(-max(stamp - mem.ev_last_t, 0.0) / c.history_tau_s)
                mem.rr += a * ((1.0 if obs == "revoke" else 0.0) - mem.rr)
            mem.ev_last_t = stamp
        if obs == "revoke":
            mem.run_t0, mem.run_n, mem.revoke_t = None, 0, stamp
        elif obs == "static" and stamp - mem.revoke_t >= c.revoke_hold_s:
            if mem.run_t0 is None:
                mem.run_t0 = stamp
            mem.run_n += 1
            mem.last_static_t = stamp
        if mem.run_t0 is not None and stamp - mem.last_static_t > c.stale_s:
            mem.run_t0, mem.run_n = None, 0          # not re-confirmed: provisional decision expires
        mem.obs = obs
        return obs

    def confirmed(self, mem: _TrackMemory, stamp: float) -> bool:
        c = self.cfg
        return (mem.run_t0 is not None and stamp - mem.run_t0 >= c.confirm_s and mem.run_n >= c.confirm_min_obs
                and stamp - mem.last_static_t <= c.stale_s)

    def history_static(self, mem: _TrackMemory, stamp: float) -> bool:
        c = self.cfg
        return (c.history_s > 0 and mem.ev_t0 is not None and stamp - mem.ev_t0 >= c.history_s
                and mem.rr < c.history_max_revoke and stamp - mem.revoke_t >= min(c.revoke_hold_s, c.history_s))

    # ------------------------------------------------------------------ convergence proxy
    def _update_convergence(self, stamp: float, motion) -> None:
        c = self.cfg
        ego = getattr(motion, "last_ego", None) if motion is not None else None
        dt = (stamp - self.prev_t) if self.prev_t is not None else 0.0
        self.prev_t = stamp
        if self.onset_t is None:
            if ego is not None and ego.t_ok and dt > 0 and float(np.linalg.norm(ego.t)) / dt > c.onset_speed_mps:
                self.onset_count += 1
                if self.onset_count >= c.onset_frames:
                    self.onset_t = stamp
            else:
                self.onset_count = 0
        self.converged = self.onset_t is not None and stamp - self.onset_t >= c.converge_s

    # ------------------------------------------------------------------ main
    def update(self, stamp: float, instances: Sequence[Instance], motion=None) -> dict:
        """Labels for this frame -> gate context ``{"labels": {i: label}, "converged": bool, "prior": set}``."""
        self._update_convergence(stamp, motion)
        tracks = getattr(motion, "tracks", {}) if motion is not None else {}
        # forget tracks the motion estimator dropped
        for tid in [t for t in self.mem if t not in tracks]:
            del self.mem[tid]
        labels: Dict[int, str] = {}
        seen = set()
        n_conf = 0
        for i, inst in enumerate(instances):
            if inst.role != ROLE_POTENTIAL:
                continue
            mo = inst.motion or {}
            tid = mo.get("id")
            trk = tracks.get(tid) if tid is not None else None
            if trk is None:
                labels[i] = LABEL_UNKNOWN
                continue
            mem = self.mem.setdefault(tid, _TrackMemory())
            if tid not in seen:                      # duplicates share the older track: observe it once
                seen.add(tid)
                raw = trk.raw if trk.raw.get("stamp") == stamp else {}
                self.observe(mem, raw, stamp)
                mem.seen_t = stamp
            conf = self.confirmed(mem, stamp)
            raw_now = trk.raw if trk.raw.get("stamp") == stamp else {}
            inst.win = raw_now.get("win") or raw_now.get("win_long")
            if trk.is_moving:
                labels[i] = LABEL_MOVING
            elif conf:
                labels[i] = LABEL_STATIC
                n_conf += 1
            elif self.history_static(mem, stamp):
                labels[i] = LABEL_HISTORY
            else:
                labels[i] = LABEL_UNKNOWN
            inst.motion = {**mo, "sel": labels[i], "sel_obs": mem.obs + ("_" + mem.revoke_by if mem.obs == "revoke" else "")}
        self.last_stats = {"converged": self.converged, "onset_t": self.onset_t, "n_static": n_conf,
                           "n_labels": len(labels)}
        # people: windowed velocity for the co-motion gate (they are parents only)
        for inst in instances:
            if inst.role != ROLE_POTENTIAL and inst.motion and inst.motion.get("id") in tracks:
                raw = tracks[inst.motion["id"]].raw
                if raw.get("stamp") == stamp:
                    inst.win = raw.get("win") or raw.get("win_long")
        return {"labels": labels, "converged": self.converged, "prior": self.prior,
                "comotion": (self.cfg.comotion_q, self.cfg.comotion_v_min_mps) if self.cfg.comotion_gate else None}

    def finalize(self, stamp: float, instances: Sequence[Instance]) -> int:
        """Off-delay hysteresis after gating: returns the number of instances held masked."""
        n_held = 0
        hold = self.cfg.min_on_s
        for inst in instances:
            if inst.role != ROLE_POTENTIAL or not inst.motion or inst.motion.get("id") not in self.mem:
                continue
            mem = self.mem[inst.motion["id"]]
            if inst.is_dynamic and inst.status != STATUS_HELD:
                mem.last_masked_t = stamp
            elif not inst.is_dynamic and hold > 0 and stamp - mem.last_masked_t < hold:
                inst.status = STATUS_HELD
                n_held += 1
        self.last_stats["n_held"] = n_held
        return n_held
