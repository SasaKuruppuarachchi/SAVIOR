# SPDX-License-Identifier: GPL-3.0-or-later
"""Promotion (interaction tree) tests."""
import itertools
import math

import numpy as np
import pytest

from savior_perception.core import GatingConfig, Instance, MotionEvidence, PromotionGate, RoleTable
from savior_perception.core.gating import sigma_z
from savior_perception.core.synthetic import rect_mask

H, W = 240, 320
F, B, SD = 450.0, 0.11, 1.0
ROLES = RoleTable(dynamic=["person"], potential=["forklift", "box", "chair", "cart"],
                  half_extent_m={"forklift": 1.2})


def inst(cls, box, z):
    i = Instance.from_mask(rect_mask(H, W, box), cls)
    i.role = ROLES.role(cls)
    if z is None:
        i.depth = i.sigma_z = math.nan
    else:
        i.depth, i.sigma_z = z, sigma_z(z, F, B, SD)
    return i


def run(instances, **cfg):
    gate = PromotionGate(GatingConfig(**cfg), ROLES)
    return gate.run(instances), instances


def promoted_names(res, instances):
    return sorted(instances[i].cls + str(i) for i in res.promoted)


def test_chain_person_forklift_box():
    person = inst("person", (40, 40, 80, 200), 3.0)
    forklift = inst("forklift", (78, 80, 180, 200), 3.8)   # touches person, deeper (big object)
    box = inst("box", (178, 120, 220, 170), 4.2)           # sits on the forklift, not touching person
    res, ii = run([person, forklift, box])
    assert res.promoted == {1, 2}
    assert res.parent == {1: 0, 2: 1}
    assert forklift.status == "promoted" and box.status == "promoted" and box.parent == 1
    assert res.links == [(1, 0), (2, 1)]


def test_overlapping_but_far_box_not_promoted():
    person = inst("person", (100, 40, 140, 200), 2.0)
    far_box = inst("box", (120, 100, 200, 160), 6.0)  # overlaps in 2D, 4 m behind
    res, _ = run([person, far_box])
    assert res.promoted == set() and far_box.status == "unpromoted"


def test_two_independent_people():
    p1, c1 = inst("person", (10, 40, 50, 200), 2.0), inst("chair", (48, 120, 90, 190), 2.2)
    p2, c2 = inst("person", (200, 40, 240, 200), 4.0), inst("cart", (238, 110, 300, 190), 4.3)
    lone = inst("chair", (120, 150, 160, 200), 3.0)
    res, _ = run([p1, c1, p2, c2, lone])
    assert res.roots == [0, 2]
    assert res.promoted == {1, 3}
    assert res.parent == {1: 0, 3: 2}
    assert lone.status == "unpromoted"


def test_no_root_no_promotion():
    a, b = inst("box", (10, 10, 60, 60), 2.0), inst("chair", (58, 10, 100, 60), 2.0)
    res, _ = run([a, b])
    assert res.promoted == set() and res.roots == []


def test_paper_alg1_bug_second_root_handled():
    """Paper Alg. 1 returns after the first root; the BFS must also expand later roots."""
    p1 = inst("person", (10, 40, 50, 200), 2.0)
    p2 = inst("person", (200, 40, 240, 200), 2.0)
    box = inst("box", (238, 100, 280, 160), 2.1)
    res, _ = run([p1, p2, box])
    assert res.promoted == {2} and res.parent[2] == 1


def test_order_independence():
    def scene():
        return [inst("person", (40, 40, 80, 200), 3.0), inst("forklift", (78, 80, 180, 200), 3.8),
                inst("box", (178, 120, 220, 170), 4.2), inst("box", (60, 30, 140, 70), 8.0),
                inst("chair", (250, 100, 300, 150), 3.0), inst("person", (282, 60, 318, 220), 3.1)]
    base = scene()
    run(base)
    ref = sorted((x.cls, x.bbox, x.status) for x in base)
    for perm in itertools.permutations(range(6)):
        s = scene()
        ordered = [s[i] for i in perm]
        run(ordered)
        assert sorted((x.cls, x.bbox, x.status) for x in ordered) == ref


def test_dilation_contact_tolerance():
    person = inst("person", (40, 40, 80, 200), 2.0)
    gap = inst("box", (85, 100, 120, 150), 2.0)  # 5 px gap (x 80..84 empty)
    assert run([person, gap], dilate_px=4)[0].promoted == {1}
    gap2 = inst("box", (85, 100, 120, 150), 2.0)
    assert run([inst("person", (40, 40, 80, 200), 2.0), gap2], dilate_px=1)[0].promoted == set()


def test_adaptive_threshold_looser_at_range():
    gate = PromotionGate(GatingConfig(), ROLES)
    near = [gate.link_threshold(inst("chair", (0, 0, 2, 2), z), inst("person", (0, 0, 2, 2), z))
            for z in (1.0, 2.0, 4.0, 8.0)]
    assert all(a < b for a, b in zip(near, near[1:]))
    assert near[0] == pytest.approx(0.7, abs=0.1)  # size prior dominates up close
    # same 1.8 m depth gap: rejected at 2 m, accepted at 6 m
    for z, expect in ((2.0, set()), (6.0, {1})):
        person = inst("person", (40, 40, 80, 200), z)
        chair = inst("chair", (78, 120, 120, 190), z + 1.8)
        assert run([person, chair])[0].promoted == expect, z
    # fixed mode (paper dist_int=2 m) ignores range
    gf = PromotionGate(GatingConfig(mode="fixed", fixed_threshold_m=2.0), ROLES)
    assert gf.link_threshold(inst("chair", (0, 0, 2, 2), 1.0), inst("person", (0, 0, 2, 2), 9.0)) == 2.0


def test_unknown_depth_policy():
    mk = lambda: [inst("person", (40, 40, 80, 200), 2.0), inst("box", (78, 100, 120, 150), None)]  # noqa: E731
    assert run(mk(), unknown_depth_policy="overlap")[0].promoted == {1}
    assert run(mk(), unknown_depth_policy="reject")[0].promoted == set()


def test_motion_evidence_hook():
    class Ev(MotionEvidence):
        def __call__(self, instances, context=None):
            return {1: True, 3: False}
    a = inst("person", (0, 0, 20, 20), 2.0)
    cart = inst("cart", (100, 100, 150, 150), 3.0)      # moving on its own -> root
    box = inst("box", (148, 110, 180, 140), 3.1)        # touches the cart -> promoted
    vetoed = inst("box", (18, 0, 40, 20), 2.0)          # touches person but vetoed
    res = PromotionGate(GatingConfig(), ROLES, Ev()).run([a, cart, box, vetoed])
    assert res.roots == [0, 1] and res.promoted == {2} and vetoed.status == "unpromoted"


def test_promote_all_ablation():
    ii = [inst("person", (0, 0, 20, 20), 2.0), inst("box", (100, 100, 150, 150), 9.0),
          Instance.from_mask(rect_mask(H, W, (200, 0, 210, 10)), "tv", role="ignore")]
    res = PromotionGate.promote_all(ii)
    assert res.promoted == {1} and ii[2].status == "static"


def test_max_threshold_caps_far_noise():
    """With a short baseline sigma_z(6 m) is metres: the adaptive gate links a 1.5 m chair to a 6 m person that
    merely overlaps it in 2D (occlusion contact). gating.max_threshold_m caps the link distance."""
    fb_short = 12.8   # T265 (f*b in px*m with rect_focal_scale 0.7)
    person = inst("person", (40, 40, 80, 120), None)
    person.depth, person.sigma_z = 6.0, 6.0 ** 2 / fb_short
    chair = inst("chair", (78, 100, 160, 200), None)
    chair.depth, chair.sigma_z = 1.5, 1.5 ** 2 / fb_short
    res, xs = run([person, chair])
    assert 1 in res.promoted                       # uncapped: |dz| = 4.5 m < 0.7 + 3*2.8 m
    res, xs = run([person, chair], max_threshold_m=1.0)
    assert not res.promoted
    near = inst("chair", (78, 100, 160, 200), None)
    near.depth, near.sigma_z = 5.6, 5.6 ** 2 / fb_short
    res, _ = run([person, near], max_threshold_m=1.0)
    assert 1 in res.promoted                       # a real contact (0.4 m apart) still links


# ---------------------------------------------------------------------------------------- P4 short-baseline gate
FB_T265 = 12.8   # f*b [px m] of the T265 rectified pair (rect_focal_scale 0.7)


def disp_inst(cls, box, z_mask, extra=None):
    """Instance with a raw-domain disparity crop over its bbox (+pad): `z_mask` = depth of the mask pixels,
    `extra` = list of (box, z) sub-regions of the instance mask with a different depth."""
    i = inst(cls, box, None)
    h, w = H, W
    pad = 20
    x0, y0, x1, y1 = box
    wb = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
    d = np.zeros((wb[3] - wb[1], wb[2] - wb[0]), np.float32)
    d[y0 - wb[1]:y1 - wb[1], x0 - wb[0]:x1 - wb[0]] = FB_T265 / z_mask
    for (bx0, by0, bx1, by1), z in (extra or []):
        d[by0 - wb[1]:by1 - wb[1], bx0 - wb[0]:bx1 - wb[0]] = FB_T265 / z
    i.work_box, i.disp_crop = wb, d
    i.depth = float(np.median(FB_T265 / d[d > 0])) if extra else z_mask
    i.disparity = FB_T265 / i.depth
    i.sigma_z = i.depth ** 2 / FB_T265
    return i


def gate_t265(**cfg):
    return PromotionGate(GatingConfig(**cfg), ROLES, fb=FB_T265, sigma_d_px=1.0)


def test_noise_cap_limits_only_the_noise_term():
    p, q = inst("chair", (0, 0, 2, 2), 6.0), inst("person", (0, 0, 2, 2), 6.0)
    p.sigma_z = q.sigma_z = 36.0 / FB_T265
    assert gate_t265().link_threshold(p, q) > 10.0                     # P2: ~12.6 m at 6 m
    assert gate_t265(max_noise_m=0.5).link_threshold(p, q) == pytest.approx(0.7 + 0.5)



def test_contact_depth_refuses_occlusion_contact():
    """Person at 2 m standing in front of (2D-overlapping) a chair at 5 m: the P2 median gate links them through
    the short-baseline noise term; the contact gate sees the depth jump along the shared boundary."""
    person = disp_inst("person", (100, 40, 140, 200), 2.0)
    chair = disp_inst("chair", (135, 120, 200, 190), 5.0)
    assert gate_t265().run([person, chair]).promoted == {1}                       # P2 (no cap)
    assert gate_t265(link_depth="contact", max_noise_m=0.5).run([person, chair]).promoted == set()


def test_contact_depth_accepts_support_contact_despite_median_gap():
    """Seated person (median 2.0 m) on a chair whose back reaches 2.9 m: median gap 0.75 m > the capped
    median threshold, but along the contact (seat) both are at ~2.1 m -> linked."""
    person = disp_inst("person", (100, 40, 140, 160), 2.0, extra=[((100, 140, 140, 160), 2.1)])
    chair = disp_inst("chair", (95, 158, 150, 220), 2.9, extra=[((95, 158, 150, 168), 2.1)])
    capped = gate_t265(max_noise_m=0.05, default_half_extent_m=0.3)
    assert capped.run([person, chair]).promoted == set()                       # medians too far apart
    contact = gate_t265(link_depth="contact", max_noise_m=0.05, default_half_extent_m=0.3)
    assert contact.run([person, chair]).promoted == {1}
    assert contact.contact_log and contact.contact_log[0]["ok"]


def test_contact_fallback_when_no_disparity():
    person = inst("person", (40, 40, 80, 200), 2.0)
    chair = inst("chair", (78, 100, 120, 150), 2.2)            # no disp crops -> fallback
    assert gate_t265(link_depth="contact").run([person, chair]).promoted == {1}
    person2, chair2 = inst("person", (40, 40, 80, 200), 2.0), inst("chair", (78, 100, 120, 150), 2.2)
    assert gate_t265(link_depth="contact", contact_fallback="reject").run([person2, chair2]).promoted == set()


def test_still_person_is_not_a_root():
    class Ev(MotionEvidence):
        def __call__(self, instances, context=None):
            return {0: False}
    person = inst("person", (40, 40, 80, 200), 2.0)
    chair = inst("chair", (78, 100, 120, 150), 2.1)
    res = PromotionGate(GatingConfig(), ROLES, Ev()).run([person, chair])
    assert person.status == "still" and res.roots == [] and res.promoted == set()


def test_promote_contact_off_keeps_only_roots():
    """P6 ablation gating.promote_contact=false: no interaction promotion, motion-evidence roots stay roots."""
    class Ev(MotionEvidence):
        def __call__(self, instances, context=None):
            return {2: True}
    mk = lambda: [inst("person", (40, 40, 80, 200), 2.0), inst("chair", (78, 100, 120, 150), 2.1),  # noqa: E731
                  inst("chair", (200, 40, 240, 100), 3.0), inst("chair", (238, 60, 280, 100), 3.1)]
    on = PromotionGate(GatingConfig(), ROLES, Ev()).run(mk())
    assert on.roots == [0, 2] and on.promoted == {1, 3}
    a = mk()
    off = PromotionGate(GatingConfig(promote_contact=False), ROLES, Ev()).run(a)
    assert off.roots == [0, 2] and off.promoted == set() and off.parent == {}
    assert [x.status for x in a] == ["root", "unpromoted", "root", "unpromoted"]


def test_max_depth_limits_chain_hops():
    """P6 gating.max_depth: person -> chair1 -> chair2 -> chair3 (touching, same depth); 0 = unlimited."""
    mk = lambda: [inst("person", (40, 40, 80, 200), 2.0), inst("chair", (78, 100, 120, 150), 2.0),  # noqa: E731
                  inst("chair", (118, 100, 160, 150), 2.0), inst("chair", (158, 100, 200, 150), 2.0)]
    assert PromotionGate(GatingConfig(), ROLES).run(mk()).promoted == {1, 2, 3}
    assert PromotionGate(GatingConfig(max_depth=2), ROLES).run(mk()).promoted == {1, 2}
    assert PromotionGate(GatingConfig(max_depth=1), ROLES).run(mk()).promoted == {1}
    a = mk()[::-1]                     # order independence of the BFS-depth limit
    assert PromotionGate(GatingConfig(max_depth=2), ROLES).run(a).promoted == {1, 2}
