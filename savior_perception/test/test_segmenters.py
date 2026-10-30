# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import os

import numpy as np
import pytest

from savior_perception.segmenters import NullSegmenter, make_segmenter
from savior_perception.segmenters.oracle_colormap import OracleColormapSegmenter


def test_null():
    assert make_segmenter("none").predict(np.zeros((10, 10), np.uint8)) == []
    assert isinstance(make_segmenter(""), NullSegmenter)
    with pytest.raises(ValueError):
        make_segmenter("magic")


def test_oracle_colormap(tmp_path):
    p = tmp_path / "map.yaml"
    p.write_text("encoding: rgb\ntolerance: 0\nmin_area_px: 20\nclasses:\n"
                 "  person: [[255, 0, 0]]\n  chair: [[0, 255, 0], [0, 250, 0]]\n")
    seg = make_segmenter("oracle_uhumans2", colormap_file=str(p))
    assert seg.needs_aux_image
    img = np.zeros((100, 200, 3), np.uint8)       # BGR
    img[10:50, 10:40] = (0, 0, 255)               # person (rgb 255,0,0)
    img[10:50, 100:130] = (0, 0, 255)             # second person, separate blob
    img[60:90, 10:40] = (0, 255, 0)               # chair colour 1
    img[60:90, 40:60] = (0, 250, 0)               # chair colour 2 (same component)
    img[95:97, 150:152] = (0, 0, 255)             # tiny blob -> dropped
    out = seg.predict(img)
    names = sorted(i.cls for i in out)
    assert names == ["chair", "person", "person"]
    chair = [i for i in out if i.cls == "chair"][0]
    assert chair.area == 30 * 50 and chair.bbox == (10, 60, 60, 90)
    # resize to the target (raw left) resolution
    out2 = seg.predict(img, target_shape=(200, 400))
    assert out2[0].mask.shape == (200, 400)
    # tolerance + class mode
    seg2 = OracleColormapSegmenter({"person": [[250, 0, 0]]}, tolerance=6, instance_mode="class")
    out3 = seg2.predict(img)
    assert len(out3) == 1 and out3[0].area == 2 * 40 * 30 + 4


@pytest.mark.skipif(importlib.util.find_spec("ultralytics") is not None, reason="ultralytics installed")
def test_yolo_missing_dependency_message():
    with pytest.raises(ImportError, match="ultralytics"):
        make_segmenter("yolo", model="yolo26n-seg.pt")


def test_yolo_backend():
    pytest.importorskip("ultralytics")
    model = os.environ.get("SAVIOR_YOLO_MODEL", "")
    if not model or not os.path.exists(model):
        pytest.skip("set SAVIOR_YOLO_MODEL to a YOLO-seg .pt/.engine to run")
    seg = make_segmenter("yolo", model=model, classes=["person", "chair"])
    img = np.full((480, 640, 3), 127, np.uint8)
    out = seg.predict(img)
    assert isinstance(out, list)
    for inst in out:
        assert inst.mask.shape == (480, 640) and inst.cls in ("person", "chair")


class _FakeResult:
    masks = None
    boxes = []


class _FakeYOLO:
    """Stands in for ultralytics.YOLO: records the predict() keyword arguments."""
    calls = []

    def __init__(self, model, task=None):
        self.names = {0: "person", 56: "chair"}

    def predict(self, img, **kwargs):
        _FakeYOLO.calls.append(kwargs)
        return [_FakeResult()]


def test_yolo_half_only_passed_when_requested(monkeypatch):
    # P2 bug: `half` was passed on every predict() call -> ultralytics 8.4 logs a deprecation warning per frame
    from savior_perception.segmenters import yolo
    monkeypatch.setattr(yolo, "_import_yolo", lambda: _FakeYOLO)
    _FakeYOLO.calls = []
    img = np.zeros((48, 64), np.uint8)
    assert yolo.YoloSegmenter("x.engine", classes=["person"]).predict(img) == []
    assert "half" not in _FakeYOLO.calls[-1] and _FakeYOLO.calls[-1]["classes"] == [0]
    yolo.YoloSegmenter("x.pt", half=True).predict(img)
    assert _FakeYOLO.calls[-1]["half"] is True


def test_oracle_colormap_keeps_only_role_classes(tmp_path):
    """P4: with segmenter.filter_classes the oracle only matches the classes of the role table (dynamic + potential)."""
    p = tmp_path / "cmap.yaml"
    p.write_text("encoding: rgb\nclasses:\n  person: [[255, 0, 0]]\n  chair: [[0, 255, 0]]\n  wall: [[0, 0, 255]]\n")
    img = np.zeros((60, 80, 3), np.uint8)
    img[5:25, 5:25] = (0, 0, 255)      # BGR of rgb (255, 0, 0): person
    img[30:50, 5:25] = (0, 255, 0)     # chair
    img[5:25, 40:70] = (255, 0, 0)     # wall
    all_ = make_segmenter("oracle_colormap", colormap_file=str(p)).predict(img)
    kept = make_segmenter("oracle_colormap", colormap_file=str(p), classes=["person", "chair"]).predict(img)
    assert sorted(i.cls for i in all_) == ["chair", "person", "wall"]
    assert sorted(i.cls for i in kept) == ["chair", "person"]
    assert make_segmenter("oracle_colormap", colormap_file=str(p), classes=["person"]).colors.keys() == {"person"}
