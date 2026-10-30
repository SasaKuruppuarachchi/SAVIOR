# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Typed configuration of the SAVIOR perception core.

Every field maps 1:1 to a ROS parameter ``<section>.<field>`` of ``savior_node`` and to an
entry of ``config/default.yaml`` (a unit test keeps the three in sync). Rationale for each
default is documented in ``config/default.yaml``.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class DepthConfig:
    enable: bool = True              # ROI stereo depth on/off (off: depth unknown everywhere)
    downsample: int = 2              # integer decimation of the rectified ROI crops before SGBM
    min_depth_m: float = 0.4         # nearest depth to resolve -> number of disparities
    max_disparity_px: int = 256      # hard cap on the (full-res) disparity search range
    matcher: str = "sgbm_3way"       # sgbm_3way | sgbm | bm
    block_size: int = 5
    uniqueness_ratio: int = 10
    speckle_window: int = 50         # 0 disables the speckle filter
    speckle_range: int = 2
    sigma_d_px: float = 1.0          # instance-level disparity std [full-res rectified px]
    min_valid_px: int = 20           # min valid disparity pixels for an instance depth
    mask_erode_px: int = 2           # erode instance mask before the median (edge fattening)
    roi_pad_px: int = 4              # extra ROI padding (rectified px) around each work box
    rect_focal_scale: float = 1.0    # rectified focal = scale * mean raw focal
    rect_size_scale: float = 0.0     # rectified size = scale * raw size; <= 0: auto (cover all raw pixels)
    rect_max_scale: float = 2.0      # auto mode: cap of the rectified size (x raw size)


@dataclass
class GatingConfig:
    enable: bool = True              # false = "classification off": every potential is masked
    mode: str = "adaptive"           # adaptive | fixed (paper: |dz| < fixed_threshold_m)
    k_sigma: float = 3.0             # threshold = size_prior + k_sigma * sigma_dz
    default_half_extent_m: float = 0.35   # half depth-extent of an object (roles yaml may override)
    fixed_threshold_m: float = 2.0   # paper's dist_int (mode=fixed)
    max_threshold_m: float = 0.0     # adaptive: cap of the link threshold [m] (<= 0: no cap)
    dilate_px: int = 4               # each mask is dilated by this before the overlap test
    min_overlap_px: int = 5          # min #pixels in the dilated-mask intersection
    unknown_depth_policy: str = "overlap"   # overlap (link on 2D overlap alone) | reject
    # --- P4 short-baseline gate (defaults = P2 behaviour) ---
    max_noise_m: float = 0.0         # adaptive: cap of the k_sigma*sigma noise term [m] (<= 0: no cap)
    link_depth: str = "median"       # median: instance medians | contact: depth along the shared boundary
    contact_px: int = 6              # contact: band (px) on each side of the shared boundary
    contact_min_px: int = 15         # contact: min valid disparity px per side, else `contact_fallback`
    contact_margin_m: float = 0.30   # contact: |dz| < margin + min(k_sigma*sigma_c, max_noise_m or inf)
    contact_fallback: str = "median"  # median | reject (contact depth unknown on either side)
    # --- P6 ablation ---
    promote_contact: bool = True     # false: no promotion through contact (interaction tree off); only roots
                                     # (always-dynamic + motion-evidence moving potential) are dynamic
    max_depth: int = 0               # max promotion hops from a root (person -> forklift -> box = 2); <= 0 = unlimited
                                     # (P6: chains otherwise spread through touching static box / pallet stacks)


@dataclass
class TrackerConfig:
    enable: bool = True
    min_hits: int = 2                # tentative -> confirmed
    max_lost: int = 5                # frames a confirmed dynamic track is carried, then removed
    hysteresis_frames: int = 5       # a promoted potential track stays dynamic this long
    iou_type: str = "bbox"           # bbox | mask
    iou_min: float = 0.3
    class_agnostic: bool = False
    velocity_alpha: float = 0.5      # EMA weight of the newest centroid displacement
    carry_promoted: bool = True      # also carry promoted potential tracks (within hysteresis)
    motion_model: str = "pixel_cv"   # pixel_cv: constant pixel velocity (P2) | ego: ego-motion compensated
                                     # (IMU rotation + estimated translation at the track depth) + own velocity


@dataclass
class MotionConfig:
    """Independent-motion evidence (P4, core/motion.py). enable=false = P2 behaviour (no IMU needed)."""
    enable: bool = False
    image_scale: float = 0.5         # KLT on the left image decimated by this factor
    klt_win: int = 11                # KLT window [px at image_scale]
    klt_levels: int = 2
    fb_max_px: float = 0.6           # forward-backward KLT error limit [full-res px]
    bg_points: int = 150             # background (ego-motion) points
    bg_min_inliers: int = 15         # fewer inliers -> translation unknown (rotation-only, inflated noise)
    bg_exclude_px: int = 10          # background points keep this far from instance bboxes [full-res px]
    inst_points: int = 25            # points per instance
    inst_erode_px: int = 6           # instance points stay this far inside the mask [full-res px]
    per_point_depth: bool = False    # per-point KLT stereo depth (else one robust depth per instance)
    min_points: int = 6              # fewer tracked points -> no evidence for the instance this frame
    redetect_ratio: float = 0.6      # re-detect instance points when fewer than ratio * inst_points survive
    min_bbox_px: int = 0             # instances with a smaller bbox side get no evidence (0 = all)
    stereo_max_dy_px: float = 1.5    # background stereo KLT: max rectified row difference
    stereo_refresh: int = 8          # background depth is propagated by the ego-motion, re-measured after N frames
    stereo_inst_points: int = 10     # stereo-matched points per instance (instance depth = their median)
    ego_iters: int = 4               # Gauss-Newton / IRLS iterations of the ego-motion fit
    sigma_px_min: float = 0.25       # floor of the background residual std [full-res px]
    sigma_sys_px: float = 0.25       # systematic (non-averaging) residual floor per instance [full-res px]
    sigma_d_px: float = 0.5          # per-point disparity std for the parallax term [rect px]
    gyro_sigma_rad: float = 0.002    # prior std of the per-frame gyro rotation correction
    no_imu_sigma_rad: float = 0.05   # gyro gap: rotation fitted to the background with this prior (<= 0: no evidence)
    max_ego_speed_mps: float = 1.5   # translation prior std / unknown-translation inflation [m/s]
    imu_time_offset_s: float = 0.0   # t_imu = t_cam + offset
    depth_rel_sigma: float = 0.5     # instantaneous test: relative depth uncertainty along the epipolar line
    window_min_s: float = 0.4        # windowed test: anchor displacement over window_min_s..window_max_s
    window_max_s: float = 0.8
    anchor_sigma_px: float = 4.0     # windowed test: mask-centroid jitter/drift [px] (heavy-tailed: inflated)
    anchor_sigma_d_px: float = 0.6   # windowed test: instance median disparity jitter/drift [rect px]
    window_moving_potential: bool = False  # windowed test may also flag potential objects as moving
    window_unveto_potential: bool = False  # P6: a windowed test that clearly says "moving" cancels the static state of a
                                           # potential object (log-odds reset to 0: no veto, promotable by contact) without
                                           # making it a root (co-moving / leading objects: motion along the epipolar line)
    q_move: float = 4.0              # moving obs: |v| >= q_move*sigma_v ...
    q_static: float = 3.0            # static obs needs the instantaneous Mahalanobis residual < q_static ...
    v_move_mps: float = 0.30         # ... and |v| >= v_move (lateral); radial uses v_move_radial_mps
    v_move_radial_mps: float = 0.60
    v_static_mps: float = 0.30       # static obs: windowed |v_lat| + 2 sigma < v_static ...
    v_static_radial_mps: float = 0.60  # ... and |v_rad| + 2 sigma < this (if radial_static_required)
    radial_static_required: bool = True
    l_up: float = 1.5                # log-odds increment per moving obs
    l_down: float = 0.25             # log-odds decrement per static obs
    l_max: float = 3.0
    prior_dynamic: float = 1.0       # initial log-odds (moving) of an always-dynamic instance
    prior_potential: float = -1.0
    th_moving: float = 1.5           # is_moving on at l >= th_moving, off at l <= 0
    th_static: float = -1.5          # is_static on at l <= th_static, off at l >= 0
    max_missing: int = 5             # frames a motion track survives without a matching detection
    dup_overlap: float = 0.7         # two same-role masks overlapping >= this (of the smaller one) = one object (<= 0: off)
    still_policy: str = "unmask"     # static always-dynamic instance: unmask | band (core -> 192, no extension)
    use_still: bool = True           # (i) static always-dynamic instances are not masked / not roots
    promote_moving: bool = True      # (ii) moving potential instances become roots
    veto_static: bool = True         # (iii) static potential instances are never promoted
    static_mask_file: str = ""       # optional OpenVINS static mask (png, >127 = masked) for background points
    window_long_s: float = 0.0       # P7: > 0 adds a long windowed anchor test over [0.75, 1] x window_long_s (track history
                                     # kept that long; radial sensitivity ~ 1/window), stored on the track for the selective
                                     # policy only (P4 decisions unchanged); <= 0 = off


@dataclass
class SelectiveConfig:
    """P7 "conservative by default, selective when confident" decisions for potential objects (core/selective.py).
    enable=false = P2-P6 behaviour. Needs motion.enable for any static confirmation (else class prior only)."""
    enable: bool = False
    prior_static_classes: str = "box,pallet"   # potential classes whose UNKNOWN state is "static" when no root is in
                                     # contact (static class prior: they only move when carried); every other potential
                                     # class (forklift, trolley, vehicles ...) is masked until confirmed static
    confirm_s: float = 1.0           # static confirmation: an unbroken run of static observations this long ...
    confirm_min_obs: int = 8         # ... with at least this many static observations
    stale_s: float = 0.5             # ... and the newest static observation at most this old (provisional: a static
                                     # decision that is no longer re-confirmed expires -> unknown -> masked)
    revoke_q: float = 3.0            # revocation (any of instantaneous / short / long window): |v| >= max(v_revoke, q*sigma)
    revoke_v_mps: float = 0.25       # lateral (and instantaneous speed) floor of a revoking observation
    revoke_v_radial_mps: float = 0.40
    revoke_hold_s: float = 1.0       # after a revocation the object cannot be confirmed static for this long
    long_static: bool = True         # a long-window (motion.window_long_s) static bound also counts as static observation
    converge_s: float = 5.0          # VIO convergence proxy: this long after motion onset (perception ego speed); before,
                                     # static confirmations neither veto links nor unmask non-prior classes
    onset_speed_mps: float = 0.2     # motion onset: ego speed above this ...
    onset_frames: int = 3            # ... for this many consecutive frames (with a translation estimate)
    min_on_s: float = 0.5            # hysteresis: a masked potential track stays masked (status held) this long after its
                                     # last masked decision (off-delay; masking itself is immediate)
    history_s: float = 2.0           # history-static (weaker than confirmed; unmasks an unlinked object, never vetoes a link):
                                     # evidence history >= history_s ...
    history_max_revoke: float = 0.3  # ... with an EMA revocation rate (time constant history_tau_s) below this
    history_tau_s: float = 1.0       # (radial motion is unobservable beyond ~5 m: far parked forklifts never confirm)
    comotion_gate: bool = True       # link p <- q from a moving parent only if p co-moves: refused when p's windowed velocity
                                     # is consistent with 0 but differs from q's by >= comotion_q sigma (static stack passed by
                                     # a forklift / person); carried loads and drivers co-move. No window -> contact rule only
    comotion_q: float = 3.0
    comotion_v_min_mps: float = 0.3  # parent windowed speed needed to apply the co-motion test
    unknown_promotes: bool = False   # an uncertain (unknown-state, masked) object also promotes its contacts (default:
                                     # links only from active parents = people, moving roots and objects promoted from
                                     # them; never from uncertain / held ones -> no spreading through static stacks)


@dataclass
class ExtensionConfig:
    enable: bool = True
    dilate: bool = True              # depth-adaptive dilation ring
    margin_m: float = 0.10           # metric margin -> px = f * margin_m / z
    min_px: int = 8                  # >= KLT patch radius (OpenVINS 15x15 window -> 7..8 px)
    max_px: int = 40
    grow: bool = True                # depth-band region growing inside the expanded bbox
    band_mode: str = "adaptive"      # adaptive | fixed (paper: dist_ext)
    band_m: float = 0.25             # adaptive band = band_m + k_sigma * sigma_z(z)
    k_sigma: float = 2.0
    fixed_band_m: float = 0.5        # paper's dist_ext (band_mode=fixed)
    bbox_expand: float = 0.10        # growth region = bbox expanded by this ratio (+ max_px)


@dataclass
class ComposeConfig:
    right_mask: bool = True          # warp the left mask into the right image
    right_close_px: int = 0          # optional grayscale closing radius on the right mask (0 = off)
    right_fallback: str = "none"     # instance without stereo depth: none (no right polygon, P2) | median (frame median
                                     # disparity of the instances with depth, else fb / right_fallback_depth_m) | band
                                     # (same disparity, written as relaxable band 192 only)
    right_fallback_depth_m: float = 3.0
    movable_static_value: int = 0    # SAVIOR-SG: value written where a movable-class object (role dynamic / potential) is
                                     # currently classified static and kept (unpromoted, still): 0 = off (0/192/255 only),
                                     # else 1..127 (64 for the semantic chi2 gate; the >= 128 layers never change)


@dataclass
class PipelineConfig:
    depth: DepthConfig = field(default_factory=DepthConfig)
    gating: GatingConfig = field(default_factory=GatingConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    extension: ExtensionConfig = field(default_factory=ExtensionConfig)
    compose: ComposeConfig = field(default_factory=ComposeConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    selective: SelectiveConfig = field(default_factory=SelectiveConfig)

    SECTIONS = ("depth", "gating", "tracker", "extension", "compose", "motion", "selective")

    def to_flat(self) -> Dict[str, Any]:
        out = {}
        for sec in self.SECTIONS:
            for f in dataclasses.fields(getattr(self, sec)):
                out[f"{sec}.{f.name}"] = getattr(getattr(self, sec), f.name)
        return out

    @classmethod
    def from_flat(cls, flat: Dict[str, Any], strict: bool = True) -> "PipelineConfig":
        cfg = cls()
        for key, value in flat.items():
            sec, _, name = key.partition(".")
            if sec not in cls.SECTIONS:
                if strict:
                    raise KeyError(f"unknown config section in '{key}'")
                continue
            obj = getattr(cfg, sec)
            names = {f.name: f for f in dataclasses.fields(obj)}
            if name not in names:
                if strict:
                    raise KeyError(f"unknown config key '{key}'")
                continue
            setattr(obj, name, _coerce(getattr(obj, name), value, key))
        cfg.validate()
        return cfg

    @classmethod
    def from_nested(cls, d: Dict[str, Any], strict: bool = True) -> "PipelineConfig":
        flat = {}
        for sec, vals in (d or {}).items():
            if isinstance(vals, dict):
                for k, v in vals.items():
                    flat[f"{sec}.{k}"] = v
            else:
                flat[sec] = vals
        return cls.from_flat(flat, strict=strict)

    def copy(self, **overrides) -> "PipelineConfig":
        flat = self.to_flat()
        flat.update(overrides)
        return PipelineConfig.from_flat(flat)

    def validate(self):
        d, g, t, e = self.depth, self.gating, self.tracker, self.extension
        _check(d.downsample >= 1, "depth.downsample must be >= 1")
        _check(d.matcher in ("sgbm_3way", "sgbm", "bm"), "depth.matcher: sgbm_3way|sgbm|bm")
        _check(d.block_size % 2 == 1 and d.block_size >= 1, "depth.block_size must be odd")
        _check(d.min_depth_m > 0, "depth.min_depth_m must be > 0")
        _check(g.mode in ("adaptive", "fixed"), "gating.mode: adaptive|fixed")
        _check(g.unknown_depth_policy in ("overlap", "reject"), "gating.unknown_depth_policy: overlap|reject")
        _check(t.iou_type in ("bbox", "mask"), "tracker.iou_type: bbox|mask")
        _check(t.min_hits >= 1 and t.max_lost >= 0 and t.hysteresis_frames >= 0, "tracker counters")
        _check(e.band_mode in ("adaptive", "fixed"), "extension.band_mode: adaptive|fixed")
        _check(g.link_depth in ("median", "contact"), "gating.link_depth: median|contact")
        _check(self.compose.right_fallback in ("none", "median", "band"), "compose.right_fallback: none|median|band")
        _check(0 <= self.compose.movable_static_value < 128, "compose.movable_static_value must be in 0..127")
        _check(g.contact_fallback in ("median", "reject"), "gating.contact_fallback: median|reject")
        _check(t.motion_model in ("pixel_cv", "ego"), "tracker.motion_model: pixel_cv|ego")
        m = self.motion
        _check(0 < m.image_scale <= 1.0, "motion.image_scale must be in (0, 1]")
        _check(m.still_policy in ("unmask", "band"), "motion.still_policy: unmask|band")
        _check(0 < m.window_min_s <= m.window_max_s, "motion: 0 < window_min_s <= window_max_s")
        _check(m.th_static < 0 < m.th_moving, "motion: th_static < 0 < th_moving")
        _check(0 <= e.min_px <= e.max_px, "extension: 0 <= min_px <= max_px")
        sv = self.selective
        _check(0 < sv.history_max_revoke <= 1 and sv.history_tau_s > 0, "selective: 0 < history_max_revoke <= 1, history_tau_s > 0")
        _check(sv.confirm_s >= 0 and sv.stale_s > 0 and sv.min_on_s >= 0 and sv.converge_s >= 0,
               "selective: confirm_s, min_on_s, converge_s >= 0 and stale_s > 0")
        _check(m.window_long_s <= 0 or m.window_long_s >= m.window_max_s, "motion.window_long_s: <= 0 or >= window_max_s")


def _check(cond, msg):
    if not cond:
        raise ValueError(msg)


def _coerce(default, value, key):
    if isinstance(default, bool):
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            if value.lower() in ("false", "0", "no", "off"):
                return False
            raise ValueError(f"{key}: expected bool, got '{value}'")
        return bool(value)
    if isinstance(default, int):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"{key}: expected int, got {value}")
        return int(value)
    if isinstance(default, float):
        return float(value)
    return str(value)
