# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Promotion of potentially-dynamic instances through interaction with dynamic chains.

Replaces Algorithm 1 of the JSEN paper (which returns after the first root and mutates
the list it iterates over) with a breadth-first fixpoint:

* roots = every always-dynamic instance (+ potential instances with positive independent
  motion evidence, see :class:`MotionEvidence`);
* a potential instance ``p`` is linked to an already dynamic/promoted instance ``q`` iff
  their dilated 2D masks overlap (>= ``min_overlap_px``) AND
  ``|z_p - z_q| < size_prior(p, q) + k_sigma * sqrt(sigma_z(z_p)^2 + sigma_z(z_q)^2)``
  with ``size_prior = half_extent(p) + half_extent(q)`` (mode ``adaptive``), or
  ``|z_p - z_q| < fixed_threshold_m`` (mode ``fixed``, the paper's ``dist_int``);
* promotion repeats until no new instance is linked (fixpoint).

P4 options (defaults reproduce P2):

* motion evidence ``False`` for an always-dynamic instance -> status ``still``: not a root (a seated person
  does not promote its chair) and not masked by the pipeline (or band-only);
* ``max_noise_m``: cap of the noise term ``k_sigma * sigma`` alone (short baselines: sigma_z ~ z^2);
* ``link_depth: contact``: compare the depths of the two instances along their shared boundary (pixels of
  each mask in a ring ``contact_gap_px .. contact_gap_px + contact_px`` from the other mask, gap = SGBM edge
  fattening) instead of the instance medians: a support/carry contact is depth-continuous, an occlusion
  contact (person in front of a far chair) is a depth discontinuity and is refused:
  ``|z_c,p - z_c,q| < contact_margin_m + min(k_sigma * sigma_c, max_noise_m)``.

P6 ablation: ``promote_contact: false`` skips the BFS (no interaction promotion; roots only);
``max_depth`` > 0 limits the chain length in hops from a root (BFS depth, so the promoted set stays order-independent).

The promoted SET is the union of the connected components (in the link graph restricted to
dynamic + potential nodes) that contain a root, hence independent of input order. The
parent links (interaction tree) are the BFS tree and are returned for debugging/eval.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

import cv2
import numpy as np

from .config import GatingConfig
from .roles import RoleTable
from .types import (ROLE_DYNAMIC, ROLE_POTENTIAL, STATUS_PROMOTED, STATUS_ROOT, STATUS_STATIC,
                    STATUS_STILL, STATUS_UNCERTAIN, STATUS_UNPROMOTED, Instance, box_intersection, expand_box)


class MotionEvidence:
    """Hook for independent-motion evidence (phase 4: IMU-rotation-compensated flow residual).

    Return ``{instance_index: True|False}``: True turns a potential instance into a root
    (it moves on its own), False vetoes its promotion; missing indices mean "no evidence".
    The default implementation provides no evidence.
    """

    def __call__(self, instances: Sequence[Instance], context: Optional[dict] = None) -> Dict[int, bool]:
        return {}


@dataclass
class GatingResult:
    roots: List[int] = field(default_factory=list)
    promoted: Set[int] = field(default_factory=set)
    parent: Dict[int, int] = field(default_factory=dict)

    @property
    def links(self) -> List[Tuple[int, int]]:
        return sorted(self.parent.items())

    @property
    def dynamic(self) -> Set[int]:
        return set(self.roots) | self.promoted


def sigma_z(z: float, f: float, baseline: float, sigma_d_px: float) -> float:
    """sigma_z(z) = z^2 * sigma_d / (f * b)."""
    return z * z * sigma_d_px / (f * baseline)


class PromotionGate:
    def __init__(self, cfg: GatingConfig, roles: Optional[RoleTable] = None,
                 motion_evidence: Optional[MotionEvidence] = None, fb: Optional[float] = None,
                 sigma_d_px: float = 1.0):
        self.cfg = cfg
        self.roles = roles
        self.motion_evidence = motion_evidence or MotionEvidence()
        self.fb = fb                    # f*b of the rectified pair (contact depth); None = no stereo
        self.sigma_d_px = sigma_d_px
        self.contact_log: List[dict] = []

    # ------------------------------------------------------------------ predicates
    def _half_extent(self, cls_name: str) -> float:
        if self.roles is None:
            return self.cfg.default_half_extent_m
        return self.roles.half_extent(cls_name, self.cfg.default_half_extent_m)

    def link_threshold(self, p: Instance, q: Instance) -> float:
        """Max allowed |z_p - z_q| for a link (meters)."""
        if self.cfg.mode == "fixed":
            return self.cfg.fixed_threshold_m
        size = self._half_extent(p.cls) + self._half_extent(q.cls)
        sp = p.sigma_z if math.isfinite(p.sigma_z) else 0.0
        sq = q.sigma_z if math.isfinite(q.sigma_z) else 0.0
        noise = self.cfg.k_sigma * math.hypot(sp, sq)
        if self.cfg.max_noise_m > 0:
            noise = min(noise, self.cfg.max_noise_m)
        thr = size + noise
        # NOTE: sigma_z grows with z^2; with a short baseline (T265: f*b = 12.8 px m) the noise term alone exceeds
        # several metres at 4-6 m and the gate degenerates to 2D contact (chains through occlusion contacts)
        if self.cfg.max_threshold_m > 0:
            thr = min(thr, self.cfg.max_threshold_m)
        return thr

    def depth_compatible(self, p: Instance, q: Instance) -> bool:
        if not (math.isfinite(p.depth) and math.isfinite(q.depth)):
            return self.cfg.unknown_depth_policy == "overlap"
        if self.cfg.link_depth == "contact" and self.fb:
            zc = self.contact_depths(p, q)
            if zc is not None:
                zp, zq = zc
                sp, sq = (zp * zp * self.sigma_d_px / self.fb, zq * zq * self.sigma_d_px / self.fb)
                noise = self.cfg.k_sigma * math.hypot(sp, sq)
                if self.cfg.max_noise_m > 0:
                    noise = min(noise, self.cfg.max_noise_m)
                ok = abs(zp - zq) < self.cfg.contact_margin_m + noise
                self.contact_log.append({"zp": round(zp, 3), "zq": round(zq, 3), "ok": bool(ok)})
                return ok
            if self.cfg.contact_fallback == "reject":
                return False
        return abs(p.depth - q.depth) < self.link_threshold(p, q)

    def contact_depths(self, p: Instance, q: Instance) -> Optional[Tuple[float, float]]:
        """Median depth of each instance along the shared boundary (ring gap..gap+contact_px from the other mask)."""
        if p.disp_crop is None or q.disp_crop is None or p.work_box is None or q.work_box is None:
            return None
        gap, band = 3, int(self.cfg.contact_px)
        r = gap + band
        h, w = p.shape
        a = expand_box(p.bbox, r + 1, 0.0, w, h)
        b = expand_box(q.bbox, r + 1, 0.0, w, h)
        reg = box_intersection(a, b)
        if reg is None:
            return None
        x0, y0, x1, y1 = reg
        mp = np.ascontiguousarray(p.mask[y0:y1, x0:x1]).view(np.uint8)
        mq = np.ascontiguousarray(q.mask[y0:y1, x0:x1]).view(np.uint8)
        k_out = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        k_in = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * gap + 1, 2 * gap + 1))
        out = []
        for m_self, m_other, inst in ((mp, mq, p), (mq, mp, q)):
            ring = cv2.dilate(m_other, k_out) & ~cv2.dilate(m_other, k_in) & m_self
            ys, xs = np.nonzero(ring)
            if xs.size == 0:
                return None
            wx0, wy0, wx1, wy1 = inst.work_box
            gx, gy = xs + x0, ys + y0
            inb = (gx >= wx0) & (gx < wx1) & (gy >= wy0) & (gy < wy1)
            d = inst.disp_crop[gy[inb] - wy0, gx[inb] - wx0]
            d = d[d > 0]
            if d.size < self.cfg.contact_min_px:
                return None
            out.append(self.fb / float(np.median(d)))
        return out[0], out[1]

    def _dilated(self, inst: Instance):
        r = int(self.cfg.dilate_px)
        h, w = inst.shape
        box = expand_box(inst.bbox, r, 0.0, w, h)
        crop = np.ascontiguousarray(inst.crop(box)).view(np.uint8)
        if r > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
            crop = cv2.dilate(crop, k)
        return box, crop

    def overlap_px(self, a: Tuple, b: Tuple) -> int:
        inter = box_intersection(a[0], b[0])
        if inter is None:
            return 0
        (ax0, ay0), (bx0, by0) = a[0][:2], b[0][:2]
        x0, y0, x1, y1 = inter
        ca = a[1][y0 - ay0:y1 - ay0, x0 - ax0:x1 - ax0]
        cb = b[1][y0 - by0:y1 - by0, x0 - bx0:x1 - bx0]
        return int(np.count_nonzero(ca & cb))

    # ------------------------------------------------------------------ main
    def run(self, instances: Sequence[Instance], context: Optional[dict] = None) -> GatingResult:
        """Classify instances in place (status/parent) and return the interaction tree."""
        res = GatingResult()
        evidence = self.motion_evidence(instances, context) or {}
        self.contact_log = []
        if context and context.get("selective") is not None:
            return self._run_selective(instances, evidence, context["selective"])
        potential = []
        for i, inst in enumerate(instances):
            inst.parent = -1
            if inst.role == ROLE_DYNAMIC:
                if evidence.get(i) is False:     # P4: confidently not moving ("still"): no root, not masked
                    inst.status = STATUS_STILL
                    continue
                inst.status = STATUS_ROOT
                res.roots.append(i)
            elif inst.role == ROLE_POTENTIAL:
                if evidence.get(i) is True:
                    inst.status = STATUS_ROOT
                    res.roots.append(i)
                else:
                    inst.status = STATUS_UNPROMOTED
                    if evidence.get(i) is not False:
                        potential.append(i)
            else:
                inst.status = STATUS_STATIC
        if not res.roots or not potential or not self.cfg.promote_contact:
            return res
        dil = {i: self._dilated(instances[i]) for i in res.roots + potential}
        queue = deque(res.roots)
        done = set(res.roots)
        hops = {i: 0 for i in res.roots}
        max_depth = int(self.cfg.max_depth)
        while queue:
            q = queue.popleft()
            if max_depth > 0 and hops[q] >= max_depth:
                continue
            for p in potential:
                if p in done:
                    continue
                if (self.overlap_px(dil[p], dil[q]) >= self.cfg.min_overlap_px
                        and self.depth_compatible(instances[p], instances[q])):
                    done.add(p)
                    res.promoted.add(p)
                    res.parent[p] = q
                    instances[p].status = STATUS_PROMOTED
                    instances[p].parent = q
                    hops[p] = hops[q] + 1
                    queue.append(p)
        return res

    @staticmethod
    def comotion_refuses(p: Instance, q: Instance, comotion) -> bool:
        """P7 co-motion gate: True if parent q moves (windowed speed >= v_min and >= q sigma) while child p is consistent
        with being static (< 2 sigma) and inconsistent with q's velocity (>= q sigma). Missing windows -> False."""
        if comotion is None or p.win is None or q.win is None:
            return False
        qs, v_min = comotion
        wp, wq = p.win, q.win
        ur = wp["ur"]

        def m2(V, s_rad, s_lat):
            vr = float(V @ ur)
            vl = V - vr * ur
            return (vr / max(s_rad, 1e-6)) ** 2 + float(vl @ vl) / max(s_lat, 1e-6) ** 2

        Vq = wq["V"]
        if float(np.linalg.norm(Vq)) < v_min or m2(Vq, wq["s_rad"], wq["s_lat"]) < qs * qs:
            return False                                   # parent not clearly moving: contact rule
        if m2(wp["V"], wp["s_rad"], wp["s_lat"]) >= 4.0:
            return False                                   # child moves itself
        d = m2(wp["V"] - Vq, math.hypot(wp["s_rad"], wq["s_rad"]), math.hypot(wp["s_lat"], wq["s_lat"]))
        return d >= qs * qs

    def _bfs(self, instances, res: GatingResult, sources, candidates, hops, comotion=None) -> None:
        """Promote candidates reachable from `sources` (contact + depth gate, gating.max_depth hops from a root)."""
        if not sources or not candidates or not self.cfg.promote_contact:
            return
        dil = {i: self._dilated(instances[i]) for i in list(sources) + list(candidates)}
        queue = deque(sources)
        done = set(sources)
        max_depth = int(self.cfg.max_depth)
        while queue:
            q = queue.popleft()
            if max_depth > 0 and hops[q] >= max_depth:
                continue
            for p in candidates:
                if p in done or p in res.promoted:
                    continue
                if (self.overlap_px(dil[p], dil[q]) >= self.cfg.min_overlap_px
                        and self.depth_compatible(instances[p], instances[q])
                        and not self.comotion_refuses(instances[p], instances[q], comotion)):
                    done.add(p)
                    res.promoted.add(p)
                    res.parent[p] = q
                    instances[p].status = STATUS_PROMOTED
                    instances[p].parent = q
                    hops[p] = hops[q] + 1
                    queue.append(p)

    def _run_selective(self, instances, evidence, sel: dict) -> GatingResult:
        """P7 (core/selective.py): conservative by default, selective when confident."""
        res = GatingResult()
        labels = sel.get("labels", {})
        converged = bool(sel.get("converged", False))
        prior = sel.get("prior", set())
        unknown_promotes = bool(sel.get("unknown_promotes", False))
        candidates = []
        for i, inst in enumerate(instances):
            inst.parent = -1
            if inst.role == ROLE_DYNAMIC:
                if evidence.get(i) is False:     # still person (only if motion.use_still)
                    inst.status = STATUS_STILL
                    continue
                inst.status = STATUS_ROOT
                res.roots.append(i)
            elif inst.role == ROLE_POTENTIAL:
                lab = labels.get(i, "unknown")
                if lab == "moving":
                    inst.status = STATUS_ROOT
                    res.roots.append(i)
                    continue
                inst.status = STATUS_UNPROMOTED
                if not (lab == "static" and converged):     # provisional veto only after convergence
                    candidates.append(i)
            else:
                inst.status = STATUS_STATIC
        hops = {i: 0 for i in res.roots}
        comotion = sel.get("comotion")
        self._bfs(instances, res, res.roots, candidates, hops, comotion)
        uncertain = []
        for i, inst in enumerate(instances):
            if inst.role != ROLE_POTENTIAL or inst.status != STATUS_UNPROMOTED:
                continue
            lab = labels.get(i, "unknown")
            is_prior = inst.cls.strip().lower() in prior
            if is_prior or (lab in ("static", "history") and converged):
                continue                                     # unmasked
            inst.status = STATUS_UNCERTAIN
            uncertain.append(i)
        if unknown_promotes and uncertain:
            for i in uncertain:
                hops[i] = 0
            rest = [i for i in candidates if instances[i].status == STATUS_UNPROMOTED]
            self._bfs(instances, res, uncertain, rest, hops, comotion)
        return res

    @staticmethod
    def promote_all(instances: Sequence[Instance]) -> GatingResult:
        """Classification disabled (ablation 'cdo_off'): every potential instance is dynamic."""
        res = GatingResult()
        for i, inst in enumerate(instances):
            inst.parent = -1
            if inst.role == ROLE_DYNAMIC:
                inst.status = STATUS_ROOT
                res.roots.append(i)
            elif inst.role == ROLE_POTENTIAL:
                inst.status = STATUS_PROMOTED
                res.promoted.add(i)
            else:
                inst.status = STATUS_STATIC
        return res
