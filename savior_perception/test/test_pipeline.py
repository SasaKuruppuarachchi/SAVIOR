# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end pipeline: output contract + ablation switches."""
import json

import numpy as np
import pytest

from savior_perception.core import Instance, PipelineConfig, RoleTable, SaviorPipeline, ideal_stereo
from savior_perception.core.synthetic import Plane, ellipse_mask, rect_mask, render_stereo

W, H = 640, 480
ROLES = RoleTable(dynamic=["person"], potential=["chair", "suitcase"])
RECT = ideal_stereo(W, H, 450.0, 0.11)


def scene():
    person = Plane(ellipse_mask(H, W, (200, 240), (45, 150)), 2.0, "person")
    chair = Plane(rect_mask(H, W, (240, 300, 330, 390)), 2.3, "chair")          # touched by the person
    far = Plane(rect_mask(H, W, (100, 120, 200, 200)), 6.5, "suitcase")         # behind the person (2D overlap)
    lone = Plane(rect_mask(H, W, (480, 300, 560, 380)), 3.0, "chair")           # nobody near it
    left, right = render_stereo(W, H, RECT.fb, 8.0, [person, chair, far, lone], seed=2)
    vis_far = far.mask & ~person.mask
    vis_chair = chair.mask & ~person.mask
    masks = {"person": person.mask, "chair": vis_chair, "far": vis_far, "lone": lone.mask}
    return left, right, masks


def instances(masks, drop=()):
    cls = {"person": "person", "chair": "chair", "far": "suitcase", "lone": "chair"}
    return [Instance.from_mask(m, cls[k]) for k, m in masks.items() if k not in drop]


def core_frac(ml, m):
    return float((ml[m] == 255).mean())


def run(cfg, frames):
    pipe = SaviorPipeline(cfg, ROLES, RECT)
    out = None
    for f in frames:
        out = pipe.process(*f)
    return out


def test_output_contract():
    left, right, masks = scene()
    pipe = SaviorPipeline(PipelineConfig(), ROLES, RECT)
    stamp = 1234.5678
    ml, mr, st = pipe.process(left, right, stamp, instances(masks))
    assert ml.shape == (H, W) and mr.shape == (H, W)
    assert ml.dtype == np.uint8 and mr.dtype == np.uint8
    assert set(np.unique(ml).tolist()) <= {0, 192, 255}
    assert st["stamp"] == stamp
    json.dumps(st)  # JSON-serialisable for /savior/stats
    for k in ("depth", "gating", "tracking", "extension", "compose", "total"):
        assert st["timings_ms"][k] >= 0
    assert st["n_by_role"]["dynamic"] == 1 and st["n_by_role"]["potential"] == 3


def test_full_vs_ablations():
    left, right, masks = scene()
    full = run(PipelineConfig(), [(left, right, 0, instances(masks))])[0]
    assert core_frac(full, masks["person"]) == 1.0
    assert core_frac(full, masks["chair"]) == 1.0             # promoted through contact
    assert core_frac(full, masks["far"]) == 0.0               # 2D overlap but 4.5 m behind
    assert (full[masks["lone"]] == 0).mean() > 0.99          # untouched potential stays static
    assert (full == 192).any()

    # classification off ("cdo_off"): all potential objects are masked
    cdo = run(PipelineConfig().copy(**{"gating.enable": False}), [(left, right, 0, instances(masks))])[0]
    for k in masks:
        assert core_frac(cdo, masks[k]) == 1.0

    # post-processing off ("pp_off"): no extension band, no carry-over
    pp = PipelineConfig().copy(**{"extension.enable": False, "tracker.enable": False})
    ml = run(pp, [(left, right, 0, instances(masks))])[0]
    assert not (ml == 192).any()
    assert ((ml == 255) == (full == 255)).all()

    # fixed (paper) thresholds: dist_int=2 m still rejects the 4.5 m-behind suitcase,
    # a tighter fixed threshold rejects the contacting chair too
    fx = run(PipelineConfig().copy(**{"gating.mode": "fixed"}), [(left, right, 0, instances(masks))])[0]
    assert core_frac(fx, masks["chair"]) == 1.0 and core_frac(fx, masks["far"]) == 0.0
    fx2 = run(PipelineConfig().copy(**{"gating.mode": "fixed", "gating.fixed_threshold_m": 0.1}),
              [(left, right, 0, instances(masks))])[0]
    assert core_frac(fx2, masks["chair"]) == 0.0

    # depth off: overlap-only promotion now (wrongly) promotes the far suitcase; no right mask
    nod = run(PipelineConfig().copy(**{"depth.enable": False}), [(left, right, 0, instances(masks))])
    assert core_frac(nod[0], masks["far"]) == 1.0
    assert nod[1].max() == 0


@pytest.mark.parametrize("tracking", [True, False])
def test_dropped_detection_carry(tracking):
    left, right, masks = scene()
    cfg = PipelineConfig().copy(**{"tracker.enable": tracking})
    frames = [(left, right, i, instances(masks)) for i in range(3)] + [(left, right, 3, [])]
    ml, mr, st = run(cfg, frames)
    if tracking:
        assert core_frac(ml, masks["person"]) == 1.0 and st["n_carried"] >= 1
        assert core_frac(mr, np.roll(masks["person"], -int(round(RECT.fb / 2.0)), axis=1)) > 0.95
    else:
        assert ml.max() == 0


def test_no_instances_all_zero():
    left, right, _ = scene()
    pipe = SaviorPipeline(PipelineConfig(), ROLES, RECT)
    ml, mr, st = pipe.process(left, right, 7, [])
    assert ml.max() == 0 and mr.max() == 0 and st["n_instances"] == 0


def test_static_and_ignored_never_masked():
    left, right, masks = scene()
    roles = RoleTable(dynamic=["person"], static=["chair"], default="ignore")
    pipe = SaviorPipeline(PipelineConfig(), roles, RECT)
    ml, _, _ = pipe.process(left, right, 0, instances(masks))
    assert core_frac(ml, masks["chair"]) == 0.0 and core_frac(ml, masks["lone"]) == 0.0
    assert core_frac(ml, masks["far"]) == 0.0  # suitcase -> default ignore


def test_right_mask_fallback_for_instance_without_depth(monkeypatch):
    """P4 bug fix: an instance without stereo depth got no right polygon at all. right_fallback=median uses the
    frame median disparity (here: a neighbour at nearly the same depth), band writes it as 192 only."""
    from savior_perception.core import ideal_stereo
    from savior_perception.core.stereo_depth import StereoDepth
    from savior_perception.core.synthetic import Plane, ellipse_mask, plane_right_mask_rect, rect_mask, render_stereo
    r = ideal_stereo(640, 480, 450.0, 0.11)
    person = Plane(ellipse_mask(480, 640, (200, 250), (45, 150)), 2.0, "person")
    other = Plane(ellipse_mask(480, 640, (420, 250), (45, 150)), 2.1, "person")
    left, right = render_stereo(640, 480, r.fb, 8.0, [person, other], seed=3)
    truth = plane_right_mask_rect(r, person)
    orig_raw = StereoDepth.raw_disparity
    calls = {"n": 0}

    def no_disparity_for_first(self, box):           # first instance: SGBM found nothing (border / no texture)
        calls["n"] += 1
        d = orig_raw(self, box)
        return np.zeros_like(d) if calls["n"] % 2 == 1 else d
    monkeypatch.setattr(StereoDepth, "raw_disparity", no_disparity_for_first)
    out = {}
    for mode in ("none", "median", "band"):
        calls["n"] = 0
        cfg = PipelineConfig().copy(**{"compose.right_fallback": mode, "tracker.enable": False,
                                       "extension.enable": False})
        pipe = SaviorPipeline(cfg, RoleTable(dynamic=["person"]), r)
        insts = [Instance.from_mask(person.mask, "person"), Instance.from_mask(other.mask, "person")]
        _, mr, _ = pipe.process(left, right, 0.0, insts)
        out[mode] = mr
    reg = truth
    assert (out["none"][reg] == 255).mean() < 0.05                       # P2: nothing on the depth-less person
    core = out["median"] == 255
    iou = (core & reg).sum() / float((core | reg)[:, :320].sum())
    assert iou > 0.8, iou
    assert (out["band"][reg] == 192).mean() > 0.8 and (out["band"][reg] == 255).mean() < 0.05


@pytest.mark.parametrize("extension", [True, False])
def test_movable_static_layer(extension):
    """SAVIOR-SG: the movable-static value only fills keep pixels of kept movable objects; >= 128 layers are unchanged."""
    left, right, masks = scene()
    base = PipelineConfig().copy(**{"extension.enable": extension})
    ml0, mr0, st0 = run(base, [(left, right, 0, instances(masks))])
    assert set(np.unique(ml0).tolist()) <= {0, 192, 255} and set(np.unique(mr0).tolist()) <= {0, 192, 255}
    assert "static_px" not in st0
    ml, mr, st = run(base.copy(**{"compose.movable_static_value": 64}), [(left, right, 0, instances(masks))])
    for a, b in ((ml0, ml), (mr0, mr)):
        assert set(np.unique(b).tolist()) <= {0, 64, 192, 255}
        assert ((a == 0) == ((b == 0) | (b == 64))).all()      # 64 only replaces keep pixels
        assert (a[b != 64] == b[b != 64]).all()
        for thr in (128, 224):                                 # what the OpenVINS fork rejects (normal / relaxed)
            assert ((a >= thr) == (b >= thr)).all()
    lone = masks["lone"]                                       # untouched potential object: kept, labelled 64
    assert (ml[lone] == 64).mean() > 0.99 and (mr == 64).any()
    far = masks["far"]                                         # unpromoted (depth-gated) object: its keep pixels
    assert ((ml[far] == 64) == (ml0[far] == 0)).all() and (ml[far] == 64).any()
    assert st["static_px"] == int((ml == 64).sum()) > 0
    with pytest.raises(ValueError):
        PipelineConfig().copy(**{"compose.movable_static_value": 128})
