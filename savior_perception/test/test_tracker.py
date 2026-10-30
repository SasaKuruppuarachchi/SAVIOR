# SPDX-License-Identifier: GPL-3.0-or-later
"""Tracker: carry-over, ID stability, chain hysteresis, no hallucinated potentials."""
import numpy as np

from savior_perception.core import Instance, PipelineConfig, RoleTable, SaviorPipeline
from savior_perception.core.config import TrackerConfig
from savior_perception.core.synthetic import rect_mask
from savior_perception.core.tracker import MaskTracker

H, W = 240, 320
ROLES = RoleTable(dynamic=["person"], potential=["cart", "box"])


def det(cls, box, status):
    i = Instance.from_mask(rect_mask(H, W, box), cls)
    i.role = ROLES.role(cls)
    i.status = status
    return i


def test_carry_dropped_person_then_drop():
    trk = MaskTracker(TrackerConfig(max_lost=3, min_hits=2))
    vx = 4
    for f in range(5):
        d = det("person", (50 + vx * f, 40, 90 + vx * f, 200), "root")
        assert trk.update([d], (H, W)) == []
        tid = d.track_id
    assert tid == 1
    for k in range(1, 4):  # lost frames carried with constant velocity
        carried = trk.update([], (H, W))
        assert len(carried) == 1
        c = carried[0]
        assert c.status == "carried" and c.track_id == tid
        expected_x0 = 50 + vx * (4 + k)
        assert abs(c.bbox[0] - expected_x0) <= 1
        assert c.mask.sum() == 40 * 160
    assert trk.update([], (H, W)) == []          # max_lost exceeded
    assert trk.tracks == []
    # re-detection after removal gets a new id
    d = det("person", (90, 40, 130, 200), "root")
    trk.update([d], (H, W))
    assert d.track_id == 2


def test_reacquire_keeps_id():
    trk = MaskTracker(TrackerConfig(max_lost=5))
    for f in range(3):
        d = det("person", (50 + 5 * f, 40, 90 + 5 * f, 200), "root")
        trk.update([d], (H, W))
    trk.update([], (H, W))
    trk.update([], (H, W))
    d = det("person", (75, 40, 115, 200), "root")   # where constant velocity predicts it
    trk.update([d], (H, W))
    assert d.track_id == 1


def test_ids_stable_two_people():
    trk = MaskTracker(TrackerConfig())
    ids = None
    for f in range(10):
        a = det("person", (20 + 3 * f, 40, 60 + 3 * f, 200), "root")
        b = det("person", (250 - 3 * f, 40, 290 - 3 * f, 200), "root")
        dets = [b, a] if f % 2 else [a, b]          # detection order must not matter
        trk.update(dets, (H, W))
        cur = (a.track_id, b.track_id)
        ids = ids or cur
        assert cur == ids and cur[0] != cur[1]


def test_tentative_not_carried():
    trk = MaskTracker(TrackerConfig(min_hits=2))
    trk.update([det("person", (50, 40, 90, 200), "root")], (H, W))
    assert trk.update([], (H, W)) == []


def test_never_promoted_potential_not_hallucinated():
    trk = MaskTracker(TrackerConfig())
    for _ in range(5):
        trk.update([det("cart", (50, 40, 90, 200), "unpromoted")], (H, W))
    for _ in range(5):
        assert trk.update([], (H, W)) == []


def test_promoted_potential_carry_switch():
    for carry in (True, False):
        trk = MaskTracker(TrackerConfig(carry_promoted=carry, hysteresis_frames=3))
        for _ in range(4):
            trk.update([det("cart", (50, 40, 90, 200), "promoted")], (H, W))
        out = [len(trk.update([], (H, W))) for _ in range(5)]
        assert out == ([1, 1, 1, 0, 0] if carry else [0] * 5)


def _pipe(**over):
    cfg = PipelineConfig()
    cfg.extension.enable = False
    for k, v in over.items():
        sec, name = k.split("__")
        setattr(getattr(cfg, sec), name, v)
    return SaviorPipeline(cfg, ROLES, rect=None)  # no stereo: overlap-only promotion


def test_chain_hysteresis_during_root_occlusion():
    pipe = _pipe(tracker__hysteresis_frames=4, tracker__max_lost=2)
    img = np.zeros((H, W), np.uint8)
    cart_box = (100, 120, 180, 200)
    person_box = (60, 40, 102, 200)
    cart_px = lambda m: m[130:190, 110:170]  # noqa: E731  cart interior (never under the person)
    for _ in range(3):  # person pushes the cart
        ml, _, st = pipe.process(img, None, 0, [det("person", person_box, ""), det("cart", cart_box, "")])
        assert (cart_px(ml) == 255).all() and st["n_promoted"] == 1
    statuses = []
    for _ in range(6):  # person fully occluded / missed by the segmenter; cart still detected
        ml, _, st = pipe.process(img, None, 0, [det("cart", cart_box, "")])
        statuses.append([x["status"] for x in st["instances"] if x["cls"] == "cart"][0])
        if statuses[-1] == "held":
            assert (cart_px(ml) == 255).all()
        else:
            assert (cart_px(ml) == 0).all()
    assert statuses == ["held"] * 4 + ["unpromoted"] * 2
    # the occluded person itself was carried for max_lost frames (then dropped)


def test_hysteresis_disabled_without_tracker():
    pipe = _pipe(tracker__enable=False)
    img = np.zeros((H, W), np.uint8)
    pipe.process(img, None, 0, [det("person", (60, 40, 102, 200), ""), det("cart", (100, 120, 180, 200), "")])
    ml, _, st = pipe.process(img, None, 0, [det("cart", (100, 120, 180, 200), "")])
    assert ml.max() == 0 and st["n_held"] == 0


def test_ego_motion_model_carries_mask_with_the_camera():
    """P4 motion_model=ego: under ego-rotation (every static point shifts +12 px/frame) a lost person's mask is
    carried along with the image motion; pixel_cv (P2) keeps its stale pixel velocity."""
    from savior_perception.core.config import TrackerConfig
    from savior_perception.core.tracker import MaskTracker
    from savior_perception.core.synthetic import rect_mask
    from savior_perception.core.types import Instance
    ego = lambda pts, z: pts + np.array([12.0, 0.0])          # noqa: E731
    out = {}
    for model in ("pixel_cv", "ego"):
        trk = MaskTracker(TrackerConfig(motion_model=model, min_hits=1, max_lost=3))
        x = 100
        for f in range(4):                                      # person static in the world: moves +12 px/frame
            d = Instance.from_mask(rect_mask(240, 320, (x, 50, x + 30, 150)), "person", role="dynamic")
            d.status = "root"
            trk.update([d], (240, 320), ego if model == "ego" else None)
            x += 12
        carried = trk.update([], (240, 320), ego if model == "ego" else None)
        out[model] = carried[0].bbox[0]
    assert out["ego"] == x                                       # exactly where the person is (ego + own vel 0)
    assert out["pixel_cv"] == x                                  # constant velocity also right here ...
    # ... but when the camera starts rotating only after the person was lost, only ego follows
    for model in ("pixel_cv", "ego"):
        trk = MaskTracker(TrackerConfig(motion_model=model, min_hits=1, max_lost=3))
        for f in range(3):
            d = Instance.from_mask(rect_mask(240, 320, (100, 50, 130, 150)), "person", role="dynamic")
            d.status = "root"
            trk.update([d], (240, 320), (lambda p, z: p) if model == "ego" else None)
        c1 = trk.update([], (240, 320), ego if model == "ego" else None)
        c2 = trk.update([], (240, 320), ego if model == "ego" else None)
        out[model] = (c1[0].bbox[0], c2[0].bbox[0])
    assert out["ego"] == (112, 124) and out["pixel_cv"] == (100, 100)


def test_still_tracks_are_not_carried():
    from savior_perception.core.config import TrackerConfig
    from savior_perception.core.tracker import MaskTracker
    from savior_perception.core.synthetic import rect_mask
    from savior_perception.core.types import Instance
    trk = MaskTracker(TrackerConfig(min_hits=1, max_lost=3))
    for st in ("root", "still"):
        d = Instance.from_mask(rect_mask(240, 320, (100, 50, 130, 150)), "person", role="dynamic")
        d.status = st
        trk.update([d], (240, 320))
    assert trk.update([], (240, 320)) == []


def test_vectorised_bbox_pairs_equal_loop():
    """P7: the vectorised bbox association yields exactly the per-pair loop's candidates."""
    import random
    from savior_perception.core.config import TrackerConfig
    from savior_perception.core.tracker import MaskTracker
    from savior_perception.core.types import Instance
    rng = random.Random(1)
    H, W = 120, 160

    def rnd():
        x0, y0 = rng.randrange(0, W - 10), rng.randrange(0, H - 10)
        m = np.zeros((H, W), bool)
        m[y0:y0 + rng.randrange(3, 30), x0:x0 + rng.randrange(3, 30)] = True
        i = Instance(mask=m, cls=rng.choice(["person", "box"]))
        i.role, i.status = ("dynamic", "root") if i.cls == "person" else ("potential", "promoted")
        return i

    for iou_min in (0.3, 0.0):
        tr = MaskTracker(TrackerConfig(iou_min=iou_min, min_hits=1))
        for _ in range(3):
            tr.update([rnd() for _ in range(25)], (H, W))
        dets = [rnd() for _ in range(25)]
        tr.frame += 1
        idx = list(range(len(dets)))
        loop = []
        for ti, trk in enumerate(tr.tracks):
            for di in idx:
                if tr._compatible(trk, dets[di]):
                    v = tr._iou(trk, dets[di])
                    if v >= iou_min:
                        loop.append((v, -trk.id, ti, di))
        assert sorted(loop) == sorted(tr._pairs_bbox(dets, idx))
