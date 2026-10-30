# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
import pytest
import yaml
import cv2

from conftest import calib_path
from savior_perception.core.calibration import (INVALID_COORD, StereoRectifier, ideal_stereo,
                                                load_kalibr_imucam_chain, stereo_from_kalibr)

_CACHE = {}


def rect_for(name):
    if name not in _CACHE:
        _CACHE[name] = stereo_from_kalibr(calib_path(name))
    return _CACHE[name]


@pytest.mark.parametrize("name,model,size", [("euroc", "radtan", (752, 480)), ("t265", "equidistant", (848, 800))])
def test_parse(name, model, size):
    cams = load_kalibr_imucam_chain(calib_path(name))
    assert set(cams) == {"cam0", "cam1"}
    for c in cams.values():
        assert c.model == model and c.size == size
        assert np.allclose(c.T_cam_imu[3], [0, 0, 0, 1])
    r = rect_for(name)
    expected_b = {"euroc": 0.110, "t265": 0.0627}[name]
    assert abs(r.baseline - expected_b) < 2e-3


def test_T_imu_cam_vs_T_cam_imu(tmp_path):
    """OpenVINS T_imu_cam and Kalibr T_cam_imu spellings give the same geometry."""
    src = calib_path("euroc")
    with open(src) as fh:
        d = yaml.safe_load("\n".join(l for l in fh.read().splitlines() if not l.startswith("%")))
    for k in ("cam0", "cam1"):
        d[k]["T_cam_imu"] = np.linalg.inv(np.array(d[k].pop("T_imu_cam"))).tolist()
    p = tmp_path / "kalibr.yaml"
    p.write_text(yaml.safe_dump(d))
    a, b = stereo_from_kalibr(src), stereo_from_kalibr(str(p))
    assert np.allclose(a.T_c1_c0, b.T_c1_c0, atol=1e-9)
    assert abs(a.f - b.f) < 1e-9


@pytest.mark.parametrize("name", ["euroc", "t265"])
@pytest.mark.parametrize("cam", [0, 1])
def test_roundtrip_raw_rect_raw(name, cam):
    """raw -> rect (raw_to_rect map) -> raw (bilinear on rect_to_raw map): < 0.5 px."""
    r = rect_for(name)
    w, h = r.cams[cam].size
    rw, rh = r.rect_size
    xs, ys = np.meshgrid(np.arange(0, w, 5), np.arange(0, h, 5))
    xs, ys = xs.ravel(), ys.ravel()
    u = r.raw_to_rect_x[cam][ys, xs]
    v = r.raw_to_rect_y[cam][ys, xs]
    inside = (u > 1) & (u < rw - 2) & (v > 1) & (v < rh - 2)
    assert inside.mean() > (0.99 if name == "euroc" else 0.5)
    u, v, xs, ys = u[inside], v[inside], xs[inside], ys[inside]
    mx = cv2.remap(r.rect_to_raw_x[cam], u.reshape(1, -1), v.reshape(1, -1), cv2.INTER_LINEAR).ravel()
    my = cv2.remap(r.rect_to_raw_y[cam], u.reshape(1, -1), v.reshape(1, -1), cv2.INTER_LINEAR).ravel()
    # exclude points whose bilinear footprint touches an INVALID map entry
    okmap = (r.rect_to_raw_x[cam] > -1e3).astype(np.float32)
    valid = cv2.remap(okmap, u.reshape(1, -1), v.reshape(1, -1), cv2.INTER_LINEAR).ravel() > 0.9999
    assert valid.mean() > 0.97
    err = np.hypot(mx[valid] - xs[valid], my[valid] - ys[valid])
    assert err.max() < 0.5, f"max round-trip error {err.max():.3f}px"
    # exact point functions agree with the maps
    pts = np.column_stack([xs[::50], ys[::50]]).astype(float)
    uv, ok = r.raw_to_rect_points(pts, cam)
    back = r.rect_to_raw_points(uv[ok], cam)
    assert np.abs(back - pts[ok]).max() < 1e-3


@pytest.mark.parametrize("name", ["euroc", "t265"])
def test_rectified_epipolar_geometry(name):
    """A 3D point lands on the same rectified row in both cameras with d = f*b/z."""
    r = rect_for(name)
    rng = np.random.default_rng(1)
    X = np.column_stack([rng.uniform(-0.6, 0.6, 50), rng.uniform(-0.4, 0.4, 50), rng.uniform(1.0, 8.0, 50)])
    raw0, raw1, rc0, rc1 = r.project_cam0_point(X)
    assert np.abs(rc0[:, 1] - rc1[:, 1]).max() < 1e-6
    z_rect = (X @ r.R_rect[0].T)[:, 2]
    assert np.allclose(rc0[:, 0] - rc1[:, 0], r.fb / z_rect, rtol=1e-6)
    # the maps reproduce the projection: bilinear-sampled raw_to_rect at raw0 ~ rc0
    u = cv2.remap(r.raw_to_rect_x[0], raw0[:, 0:1].T.astype(np.float32), raw0[:, 1:2].T.astype(np.float32),
                  cv2.INTER_LINEAR).ravel()
    v = cv2.remap(r.raw_to_rect_y[0], raw0[:, 0:1].T.astype(np.float32), raw0[:, 1:2].T.astype(np.float32),
                  cv2.INTER_LINEAR).ravel()
    ok = u > -1e3
    assert ok.mean() > 0.9
    assert np.abs(u[ok] - rc0[ok, 0]).max() < 0.2 and np.abs(v[ok] - rc0[ok, 1]).max() < 0.2


def test_invalid_regions_marked():
    r = rect_for("t265")
    # fisheye: corners of the raw image are outside the pinhole-representable FOV or the image circle
    inv = r.raw_to_rect_x[0] <= INVALID_COORD / 2
    assert 0.05 < inv.mean() < 0.5
    assert (r.rect_to_raw_x[0] > -1e3).mean() > 0.75


def test_ideal_stereo_is_identity():
    r = ideal_stereo(320, 240, 300.0, 0.1)
    xs, ys = np.meshgrid(np.arange(320), np.arange(240))
    assert np.abs(r.raw_to_rect_x[0] - xs).max() < 1e-3
    assert np.abs(r.rect_to_raw_y[1] - ys).max() < 1e-3
    assert abs(r.baseline - 0.1) < 1e-12 and abs(r.f - 300.0) < 1e-12


def test_vertical_or_flipped_rig_rejected():
    r = ideal_stereo(64, 48, 50.0, 0.1)
    c0, c1 = r.cams
    c1.T_cam_imu = np.eye(4)
    c1.T_cam_imu[0, 3] = +0.1  # cam1 left of cam0
    with pytest.raises(ValueError):
        StereoRectifier(c0, c1)
