# SPDX-License-Identifier: GPL-3.0-or-later
"""P4 motion evidence: gyro integration, ego-motion fit, and synthetic stereo scenes (rotating + translating
camera) with static / moving people and objects."""
import math

import numpy as np
import pytest

from savior_perception.core import Instance, PipelineConfig, RoleTable, SaviorPipeline, ideal_stereo
from savior_perception.core.config import MotionConfig
from savior_perception.core.motion import GyroIntegrator, MotionEstimator, so3_exp, so3_log
from savior_perception.core.synthetic import fronto_plane, render_stereo_sequence
from savior_perception.core.types import MASK_CORE, MASK_EXTENSION

ROLES = RoleTable(dynamic=["person"], potential=["chair"])
FPS = 30.0
YAW = math.radians(30.0)          # 30 deg/s ego rotation (~8 px/frame at f=450)
CAM_V = (0.0, 0.0, 0.4)           # 0.4 m/s forward


def rect():
    return ideal_stereo(640, 480, 450.0, 0.11)


# ------------------------------------------------------------------------------------------ gyro
def test_gyro_constant_rate_matches_exp():
    g = GyroIntegrator()
    w = np.array([0.3, -0.2, 0.5])
    for k in range(201):
        g.add(k * 0.005, w)
    R = g.rotation(0.0123, 0.4567)
    assert np.allclose(R, so3_exp(w * (0.4567 - 0.0123)), atol=1e-9)
    assert np.allclose(g.rotation(0.4567, 0.0123), R.T, atol=1e-12)
    assert g.rotation(-0.1, 0.2) is None and g.rotation(0.5, 1.2) is None     # not covered


def test_gyro_piecewise_and_out_of_order():
    g = GyroIntegrator()
    ts = np.arange(0, 1.0001, 0.005)
    ws = [np.array([0.0, math.sin(t), 0.0]) for t in ts]
    for i in np.random.default_rng(0).permutation(len(ts)):     # arbitrary arrival order
        g.add(float(ts[i]), ws[i])
    ang = so3_log(g.rotation(0.0, 1.0))
    assert ang[1] == pytest.approx(1.0 - math.cos(1.0), abs=1e-5) and abs(ang[0]) < 1e-9


# ------------------------------------------------------------------------------------------ ego-motion
def test_ego_fit_recovers_translation_and_gyro_bias():
    r = rect()
    est = MotionEstimator(MotionConfig(enable=True), r)
    rng = np.random.default_rng(1)
    X = np.column_stack([rng.uniform(-4, 4, 120), rng.uniform(-2, 2, 120), rng.uniform(2, 9, 120)])
    R = so3_exp([0.002, 0.015, -0.001])
    t = np.array([0.004, -0.001, -0.015])
    Y = X @ R.T + t
    b = Y / np.linalg.norm(Y, axis=1, keepdims=True)
    b += rng.normal(0, 0.2 / 450.0, b.shape)            # 0.2 px noise
    b[:10] = b[:10] @ so3_exp([0, 0.02, 0]).T           # 10 outliers (independently moving)
    R_gyro = so3_exp([0.0, 0.0012, 0.0]) @ R            # biased gyro (1.2 mrad)
    ego = est.estimate_ego(X, b / np.linalg.norm(b, axis=1, keepdims=True), R_gyro, 1 / FPS)
    assert ego.t_ok and ego.n_inliers >= 100
    assert np.linalg.norm(ego.t - t) < 1.5e-3
    assert np.linalg.norm(so3_log(ego.R @ R.T)) < 3e-4


def test_ego_without_background_depth_is_rotation_only():
    est = MotionEstimator(MotionConfig(enable=True), rect())
    ego = est.estimate_ego(np.zeros((3, 3)), np.zeros((3, 3)), np.eye(3), 1 / FPS)
    assert not ego.t_ok and np.allclose(ego.t, 0) and ego.sigma_t > 0.01


# ------------------------------------------------------------------------------------------ scenes
def run_scene(planes, n=36, motion=True, imu=True, **over):
    r = rect()
    flat = {"motion.enable": motion, "tracker.enable": False}
    flat.update(over)
    pipe = SaviorPipeline(PipelineConfig().copy(**flat), ROLES, r)
    hist = []
    for fr in render_stereo_sequence(r, planes, n, FPS, yaw_rate=YAW, cam_vel=CAM_V):
        inst = [Instance.from_mask(m, p.cls) for p, m in zip(planes, fr["masks"]) if p.cls and m.sum() > 50]
        ml, mr, st = pipe.process(fr["left"], fr["right"], fr["stamp"], inst, R_imu=fr["R_imu"] if imu else None)
        hist.append((st, ml, pipe.last_result.instances))
    return hist


def scene(person_vel=None, chair=False, chair_vel=None, person=True, seed=0):
    rng = np.random.default_rng(seed)
    out = [fronto_plane((0, 0, 6.0), 14, 9, 0.01, rng)]
    if person:
        out.append(fronto_plane((-0.6, 0.2, 2.8), 0.5, 1.6, 0.004, rng, cls="person", vel=person_vel))
    if chair:
        out.append(fronto_plane((-0.1, 0.55, 2.85), 0.5, 0.6, 0.004, rng, cls="chair", vel=chair_vel))
    return out


def statuses(hist, cls):
    return [[i.status for i in insts if i.cls == cls] for _, _, insts in hist]


def test_static_person_becomes_still_and_unmasked():
    hist = run_scene(scene())
    st = statuses(hist, "person")
    assert all(s == ["root"] for s in st[:10])               # prior: masked until confident (>= window_min_s)
    assert st[-1] == ["still"] and hist[-1][0]["n_still"] == 1
    assert hist[-1][0]["core_px"] == 0 and hist[-1][0]["ext_px"] == 0
    first = next(k for k, s in enumerate(st) if s == ["still"])
    assert all(s == ["still"] for s in st[first:])           # hysteresis: no flicker
    # band policy: the still person becomes relaxable band only
    hist_b = run_scene(scene(), **{"motion.still_policy": "band"})
    ml = hist_b[-1][1]
    assert not (ml == MASK_CORE).any() and (ml == MASK_EXTENSION).sum() > 1000


@pytest.mark.parametrize("vel", [(-0.8, 0.0, 0.0), (0.0, 0.0, -1.0)], ids=["lateral", "approaching"])
def test_moving_person_stays_masked(vel):
    hist = run_scene(scene(person_vel=vel))
    st = [s for s in statuses(hist, "person") if s]          # (the person may leave the view)
    assert len(st) > 20 and all(s == ["root"] for s in st)
    moving = [i.motion["state"] for _, _, insts in hist[12:] for i in insts if i.cls == "person"]
    assert moving and all(m == "moving" for m in moving)
    assert all(h[0]["core_px"] > 0 for h, s in zip(hist, statuses(hist, "person")) if s)


def test_moving_potential_object_promoted_without_contact():
    hist = run_scene(scene(person=False, chair=True, chair_vel=(-0.8, 0.0, 0.0)))
    st = statuses(hist, "chair")
    assert st[0] == ["unpromoted"] and st[-1] == ["root"]
    off = run_scene(scene(person=False, chair=True, chair_vel=(-0.8, 0.0, 0.0)), motion=False)
    assert statuses(off, "chair")[-1] == ["unpromoted"]      # P2: no person, no promotion


def test_still_person_does_not_promote_its_chair():
    off = run_scene(scene(chair=True), motion=False)
    assert statuses(off, "chair")[-1] == ["promoted"]        # P2: contact + depth gate -> promoted
    hist = run_scene(scene(chair=True))
    assert statuses(hist, "person")[-1] == ["still"]
    assert statuses(hist, "chair")[-1] == ["unpromoted"]
    assert hist[-1][0]["core_px"] == 0


def test_no_imu_no_evidence():
    hist = run_scene(scene(), n=20, imu=False, **{"motion.no_imu_sigma_rad": 0.0})
    assert all(s == ["root"] for s in statuses(hist, "person"))
    assert all(h[0]["motion"]["n_bg"] == 0 for h in hist)
    # default: without any gyro the rotation is fitted to the background points (vision-only fallback)
    hist = run_scene(scene(), n=8, imu=False)
    assert all(h[0]["motion"]["t_ok"] and not h[0]["motion"]["gyro"] for h in hist[1:])


def test_motion_disabled_is_p2_behaviour():
    pipe = SaviorPipeline(PipelineConfig(), ROLES, rect())
    assert pipe.motion is None
    hist = run_scene(scene(), n=8, motion=False)
    assert all("motion" not in h[0] and "n_still" not in h[0] for h in hist)
    assert all(i.motion is None for _, _, insts in hist for i in insts)


def test_gyro_gap_falls_back_to_background_rotation():
    """A frame without gyro coverage keeps the evidence (rotation fitted to the background points) instead of
    resetting every motion track; the static person still becomes 'still'."""
    r = rect()
    pipe = SaviorPipeline(PipelineConfig().copy(**{"motion.enable": True, "tracker.enable": False}), ROLES, r)
    planes = scene()
    last = None
    for k, fr in enumerate(render_stereo_sequence(r, planes, 36, FPS, yaw_rate=YAW, cam_vel=CAM_V)):
        inst = [Instance.from_mask(m, p.cls) for p, m in zip(planes, fr["masks"]) if p.cls and m.sum() > 50]
        R = None if k % 7 == 3 else fr["R_imu"]
        _, _, st = pipe.process(fr["left"], fr["right"], fr["stamp"], inst, R_imu=R)
        if k % 7 == 3:
            assert st["motion"]["gyro"] is False and st["motion"]["t_ok"]
        last = pipe.last_result.instances
    assert [i.status for i in last if i.cls == "person"] == ["still"]


def test_duplicate_detection_shares_the_still_decision():
    """YOLO sometimes returns two overlapping masks of one person; the duplicate must not restart at the
    'masked' prior once the person is confirmed still."""
    r = rect()
    pipe = SaviorPipeline(PipelineConfig().copy(**{"motion.enable": True, "tracker.enable": False}), ROLES, r)
    planes = scene()
    for k, fr in enumerate(render_stereo_sequence(r, planes, 36, FPS, yaw_rate=YAW, cam_vel=CAM_V)):
        m = fr["masks"][1]
        inst = [Instance.from_mask(m, "person")]
        if k >= 30:                                         # duplicate: the same mask minus its lower quarter
            ys = np.flatnonzero(m.any(axis=1))
            m2 = m.copy()
            m2[ys[0] + 3 * (ys[-1] - ys[0]) // 4:] = False
            inst.append(Instance.from_mask(m2, "person"))
        _, _, st = pipe.process(fr["left"], fr["right"], fr["stamp"], inst, R_imu=fr["R_imu"])
    assert [i.status for i in pipe.last_result.instances] == ["still", "still"]
    assert st["core_px"] == 0


def test_window_unveto_potential_cancels_static_state():
    """P6 motion.window_unveto_potential: a potential object confirmed static whose windowed test then clearly says
    'moving' radially (co-moving forklift ahead: instantaneous test blind along the epipolar line) is un-vetoed
    (log-odds reset to 0 -> state unknown, promotable by contact) but does not become a root; default unchanged."""
    from savior_perception.core.motion import MotionTrack
    ev = {"m2": 0.2, "speed": 0.02, "n": 20, "rng": 3.0}
    win = {"v_lat": 0.10, "s_lat": 0.04, "v_rad": 1.0, "s_rad": 0.13}
    for flag, l_exp, state in ((False, -2.0, "static"), (True, 0.0, "unknown")):
        est = MotionEstimator(MotionConfig(window_unveto_potential=flag), rect())
        trk = MotionTrack(id=1, role="potential", cls="chair", l=-2.0, is_static=True)
        est._observe(trk, ev, win)
        assert trk.l == pytest.approx(l_exp) and trk.state == state and not trk.is_moving
    est = MotionEstimator(MotionConfig(window_unveto_potential=True), rect())
    trk = MotionTrack(id=2, role="potential", cls="chair", l=-2.0, is_static=True)
    est._observe(trk, ev, {"v_lat": 0.05, "s_lat": 0.04, "v_rad": 0.1, "s_rad": 0.1})   # truly static: stays vetoed
    assert trk.state == "static" and trk.l < -2.0
