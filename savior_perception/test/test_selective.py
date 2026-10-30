# SPDX-License-Identifier: GPL-3.0-or-later
"""P7 selective policy: static confirmation / revocation / expiry, convergence proxy, gate branch, hysteresis,
default-off reproducibility, YOLO fast mask path."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from savior_perception.core import GatingConfig, Instance, PromotionGate, RoleTable
from savior_perception.core.config import MotionConfig, PipelineConfig, SelectiveConfig
from savior_perception.core.gating import sigma_z
from savior_perception.core.motion import MotionTrack
from savior_perception.core.selective import SelectivePolicy, _TrackMemory
from savior_perception.core.synthetic import rect_mask

H, W = 240, 320
ROLES = RoleTable(dynamic=["person"], potential=["forklift", "box", "pallet"], half_extent_m={"forklift": 1.5})
STATIC_WIN = {"v_lat": 0.02, "s_lat": 0.02, "v_rad": 0.02, "s_rad": 0.05}
STATIC_EV = {"m2": 0.5, "speed": 0.01}


def inst(cls, box, z, tid=None):
    i = Instance.from_mask(rect_mask(H, W, box), cls)
    i.role = ROLES.role(cls)
    i.depth, i.sigma_z = z, sigma_z(z, 470.0, 0.12, 1.0)
    if tid is not None:
        i.motion = {"id": tid}
    return i


def policy(**kw):
    return SelectivePolicy(SelectiveConfig(enable=True, **kw), MotionConfig())


def feed(pol, mem, raw, t0, n, dt=0.05):
    for k in range(n):
        pol.observe(mem, raw, t0 + k * dt)
    return t0 + (n - 1) * dt


def test_static_confirmation_needs_time_and_count():
    pol = policy(confirm_s=1.0, confirm_min_obs=8)
    m = _TrackMemory()
    t = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, 0.0, 10)       # 0.45 s
    assert not pol.confirmed(m, t)
    t = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, t + 0.05, 12)  # > 1 s
    assert pol.confirmed(m, t)


def test_revocation_resets_and_holds():
    pol = policy(confirm_s=0.5, confirm_min_obs=3, revoke_hold_s=1.0)
    m = _TrackMemory()
    t = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, 0.0, 20)
    assert pol.confirmed(m, t)
    # leading object: radial motion seen only by the window (instantaneous fit blind) -> immediate revoke
    assert pol.observe(m, {"ev": STATIC_EV, "win": {**STATIC_WIN, "v_rad": 1.0, "s_rad": 0.25}}, t + 0.05) == "revoke"
    assert not pol.confirmed(m, t + 0.05)
    t2 = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, t + 0.1, 15)   # within the hold: no new run
    assert not pol.confirmed(m, t2)
    t3 = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, t + 1.2, 15)
    assert pol.confirmed(m, t3)


def test_decision_expires_without_reconfirmation():
    pol = policy(confirm_s=0.5, confirm_min_obs=3, stale_s=0.5)
    m = _TrackMemory()
    t = feed(pol, m, {"ev": STATIC_EV, "win": STATIC_WIN}, 0.0, 20)
    assert pol.confirmed(m, t)
    # along-epipolar motion at range: neither static nor revoking -> expires after stale_s (no sticky veto)
    unc = {"ev": STATIC_EV, "win": {**STATIC_WIN, "v_rad": 0.3, "s_rad": 0.3}}
    assert pol.observe(m, unc, t + 0.3) == "uncertain"
    assert pol.confirmed(m, t + 0.3)
    pol.observe(m, unc, t + 0.6)
    assert not pol.confirmed(m, t + 0.6) and m.run_t0 is None


def test_long_window_confirms_far_object():
    far = {**STATIC_WIN, "s_rad": 0.35}          # short window: radial noise too large for a static bound
    pol = policy(confirm_s=0.3, confirm_min_obs=3)
    m = _TrackMemory()
    t = feed(pol, m, {"ev": STATIC_EV, "win": far}, 0.0, 10)
    assert not pol.confirmed(m, t)
    t = feed(pol, m, {"ev": STATIC_EV, "win": far, "win_long": STATIC_WIN}, t + 0.05, 10)
    assert pol.confirmed(m, t)
    pol2 = policy(confirm_s=0.3, confirm_min_obs=3, long_static=False)
    m2 = _TrackMemory()
    t = feed(pol2, m2, {"ev": STATIC_EV, "win": far, "win_long": STATIC_WIN}, 0.0, 20)
    assert not pol2.confirmed(m2, t)


def test_convergence_proxy():
    pol = policy(converge_s=1.0, onset_speed_mps=0.2, onset_frames=3)
    ego_still = SimpleNamespace(t_ok=True, t=np.zeros(3))
    ego_move = SimpleNamespace(t_ok=True, t=np.array([0.0, 0.0, 0.05]))       # 1 m/s at 20 Hz
    mo = SimpleNamespace(last_ego=ego_still, tracks={})
    for k in range(10):
        pol.update(k * 0.05, [], mo)
    assert pol.onset_t is None and not pol.converged
    mo.last_ego = ego_move
    for k in range(10, 14):
        pol.update(k * 0.05, [], mo)
    assert pol.onset_t == pytest.approx(12 * 0.05)
    pol.update(12 * 0.05 + 0.99, [], mo)
    assert not pol.converged
    pol.update(12 * 0.05 + 1.01, [], mo)
    assert pol.converged


def sel_run(instances, labels, converged=True, prior=("box", "pallet"), **gcfg):
    gate = PromotionGate(GatingConfig(**gcfg), ROLES)
    ctx = {"selective": {"labels": labels, "converged": converged, "prior": set(prior)}}
    return gate.run(instances, ctx)


def test_gate_conservative_defaults():
    lone_box = inst("box", (250, 20, 280, 50), 6.0)
    lone_forklift = inst("forklift", (10, 10, 80, 80), 6.0)
    st_forklift = inst("forklift", (100, 10, 170, 80), 6.0)
    ii = [lone_box, lone_forklift, st_forklift]
    sel_run(ii, {0: "unknown", 1: "unknown", 2: "static"})
    assert lone_box.status == "unpromoted" and not lone_box.is_dynamic        # class prior: static
    assert lone_forklift.status == "uncertain" and lone_forklift.is_dynamic   # unknown -> masked
    assert st_forklift.status == "unpromoted"                                 # confirmed static -> unmasked
    sel_run(ii, {0: "unknown", 1: "unknown", 2: "static"}, converged=False)
    assert st_forklift.status == "uncertain"                                  # before convergence: masked


def test_gate_provisional_veto_and_chain():
    person = inst("person", (40, 40, 80, 200), 3.0)
    forklift = inst("forklift", (78, 80, 180, 200), 3.8)
    load = inst("pallet", (178, 120, 220, 170), 4.2)
    ii = [person, forklift, load]
    res = sel_run(ii, {1: "unknown", 2: "unknown"})
    assert res.promoted == {1, 2}
    # confirmed static forklift next to a person: vetoed after convergence, its load is not reached
    res = sel_run(ii, {1: "static", 2: "unknown"})
    assert forklift.status == "unpromoted" and load.status == "unpromoted"
    # ... but not before convergence (init: objects near people stay masked)
    res = sel_run(ii, {1: "static", 2: "unknown"}, converged=False)
    assert res.promoted == {1, 2}
    # chain depth limit
    res = sel_run(ii, {1: "unknown", 2: "unknown"}, max_depth=1)
    assert res.promoted == {1} and load.status == "unpromoted"


def test_gate_moving_root_and_inactive_parents():
    forklift = inst("forklift", (78, 80, 180, 200), 3.8)
    box = inst("box", (178, 120, 220, 170), 4.2)
    ii = [forklift, box]
    sel_run(ii, {0: "moving", 1: "unknown"})
    assert forklift.status == "root" and box.status == "promoted"
    # an uncertain (masked, unknown) forklift does not spread to its contacts by default
    sel_run(ii, {0: "unknown", 1: "unknown"})
    assert forklift.status == "uncertain" and box.status == "unpromoted"
    gate = PromotionGate(GatingConfig(), ROLES)
    gate.run(ii, {"selective": {"labels": {0: "unknown", 1: "unknown"}, "converged": True, "prior": {"box"},
                                "unknown_promotes": True}})
    assert box.status == "promoted"


def test_hysteresis_off_delay():
    pol = policy(min_on_s=0.5)
    pol.mem[7] = _TrackMemory()
    f = inst("forklift", (10, 10, 80, 80), 4.0, tid=7)
    f.status = "promoted"
    pol.finalize(1.0, [f])
    f.status = "unpromoted"
    pol.finalize(1.3, [f])
    assert f.status == "held" and f.is_dynamic
    f.status = "unpromoted"
    pol.finalize(1.45, [f])                    # held does not refresh the hold
    assert f.status == "held"
    f.status = "unpromoted"
    pol.finalize(1.55, [f])
    assert f.status == "unpromoted"


def test_policy_labels_from_tracks():
    pol = policy(confirm_s=0.2, confirm_min_obs=3)
    trk = MotionTrack(id=3, role="potential", cls="forklift", l=-1.0)
    mo = SimpleNamespace(last_ego=None, tracks={3: trk})
    f = inst("forklift", (10, 10, 80, 80), 4.0, tid=3)
    for k in range(8):
        t = k * 0.05
        trk.raw = {"stamp": t, "ev": STATIC_EV, "win": STATIC_WIN}
        ctx = pol.update(t, [f], mo)
    assert ctx["labels"] == {0: "static"} and f.motion["sel"] == "static"
    trk.is_moving = True
    assert pol.update(0.45, [f], mo)["labels"] == {0: "moving"}
    # the motion estimator dropped the track -> memory forgotten, no evidence -> unknown
    mo.tracks = {}
    f.motion = {"id": 3}
    assert pol.update(0.5, [f], mo)["labels"] == {0: "unknown"} and 3 not in pol.mem


def test_defaults_off():
    c = PipelineConfig()
    assert c.selective.enable is False and c.motion.window_long_s == 0.0
    with pytest.raises(ValueError):
        PipelineConfig.from_flat({"motion.window_long_s": 0.5})        # < window_max_s


def test_yolo_fast_masks_equivalent():
    torch = pytest.importorskip("torch")
    from savior_perception.segmenters.yolo import YoloSegmenter
    rng = np.random.default_rng(0)
    h, w = 60, 90
    seg = YoloSegmenter.__new__(YoloSegmenter)
    seg.mask_threshold, seg.names = 0.5, {0: "person", 1: "box"}
    xyxy = np.array([[3.2, 4.7, 40.1, 30.0], [50.0, 10.5, 89.9, 59.2], [10.0, 10.0, 12.0, 12.0], [0, 0, 0.5, 0.5]], np.float32)
    data = torch.zeros((4, h, w))
    for i, (x0, y0, x1, y1) in enumerate(xyxy):
        r = torch.arange(h)[:, None].float()
        c = torch.arange(w)[None, :].float()
        inside = (c >= x0) & (c < x1) & (r >= y0) & (r < y1)       # ultralytics crop_mask semantics
        data[i] = torch.from_numpy(rng.random((h, w)).astype(np.float32)) * inside
    data[3] = 0.0                                                    # empty mask -> dropped by both paths
    boxes = SimpleNamespace(xyxy=torch.from_numpy(xyxy), cls=torch.tensor([0.0, 1.0, 1.0, 0.0]),
                            conf=torch.tensor([0.9, 0.8, 0.7, 0.6]))
    fast = seg._instances_fast(data, boxes, h, w)
    masks = (data > 0.5).numpy()
    ref = []
    from savior_perception.core.types import mask_bbox
    for i in range(4):
        tb = mask_bbox(masks[i])
        if tb is None:
            continue
        x0, y0, x1, y1 = xyxy[i]
        ref.append(Instance(mask=masks[i], cls=seg.names[int(boxes.cls[i])], score=float(boxes.conf[i]),
                            bbox=(min(tb[0], x0), min(tb[1], y0), max(tb[2], x1), max(tb[3], y1))))
    assert len(fast) == len(ref) == 3
    for a, b in zip(fast, ref):
        assert a.cls == b.cls and a.score == b.score and a.bbox == b.bbox and np.array_equal(a.mask, b.mask)
    assert not math.isnan(fast[0].score)
