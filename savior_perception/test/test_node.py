# SPDX-License-Identifier: GPL-3.0-or-later
"""In-process ROS 2 test of savior_node's output contract (skipped without rclpy).

Verifies what the OpenVINS fork's mask subscriber relies on: RELIABLE/depth-10 QoS, one
mask pair per stereo frame (also all-zero ones and on processing errors), both stamps copied
verbatim from the left image (exact integer nanoseconds), raw size, mono8, values {0,192,255}.
"""
import os
import random
import time

import numpy as np
import pytest

rclpy = pytest.importorskip("rclpy")

from conftest import calib_path  # noqa: E402

N_FRAMES = 6


def _img(arr, stamp, frame, enc):
    from sensor_msgs.msg import Image
    m = Image()
    m.header.stamp = stamp
    m.header.frame_id = frame
    m.height, m.width = arr.shape[:2]
    m.encoding = enc
    m.step = arr.shape[1] * (1 if arr.ndim == 2 else 3)
    m.data = arr.tobytes()
    return m


@pytest.fixture
def ros_ctx():
    os.environ["ROS_DOMAIN_ID"] = str(random.randint(100, 200))
    ctx = rclpy.context.Context()
    rclpy.init(context=ctx)
    yield ctx
    rclpy.shutdown(context=ctx)


def _run(ctx, overrides, w, h, seg=False, break_segmenter=False, seg_right=False):
    from builtin_interfaces.msg import Time
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.parameter import Parameter
    from rclpy.qos import HistoryPolicy, ReliabilityPolicy
    from sensor_msgs.msg import Image

    from savior_perception.node import SaviorNode, mask_qos

    params = [Parameter(k, value=v) for k, v in overrides.items()]
    node = SaviorNode(context=ctx, parameter_overrides=params)
    if break_segmenter:
        def boom(*a, **k):
            raise RuntimeError("segmenter exploded")
        node.segmenter.predict = boom
    peer = rclpy.create_node("savior_test_peer", context=ctx)
    q = mask_qos()
    pl = peer.create_publisher(Image, "/cam0/image_raw", q)
    pr = peer.create_publisher(Image, "/cam1/image_raw", q)
    ps = peer.create_publisher(Image, "/seg", q)
    psr = peer.create_publisher(Image, "/seg_right", q)
    got = {"left": [], "right": []}
    peer.create_subscription(Image, "/savior/mask/left", lambda m: got["left"].append(m), q)
    peer.create_subscription(Image, "/savior/mask/right", lambda m: got["right"].append(m), q)
    ex = SingleThreadedExecutor(context=ctx)
    ex.add_node(node)
    ex.add_node(peer)
    try:
        t0 = time.time()
        while (pl.get_subscription_count() == 0 or len(peer.get_publishers_info_by_topic("/savior/mask/left")) == 0) \
                and time.time() - t0 < 10:
            ex.spin_once(timeout_sec=0.05)
        # QoS of the mask publishers as seen on the graph
        for topic in ("/savior/mask/left", "/savior/mask/right"):
            info = node.get_publishers_info_by_topic(topic)
            assert len(info) == 1
            assert info[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE
        # history depth is not advertised on the graph -> check the publishers themselves
        for pub in (node.pub_left, node.pub_right):
            assert pub.qos_profile.reliability == ReliabilityPolicy.RELIABLE
            assert pub.qos_profile.history == HistoryPolicy.KEEP_LAST and pub.qos_profile.depth == 10
        rng = np.random.default_rng(0)
        tex = rng.integers(0, 255, (h, w + 40), dtype=np.uint8)
        sent = []
        for i in range(N_FRAMES):
            st = Time(sec=1_700_000_000 + i, nanosec=999_999_999 - 7 * i)  # not float-representable
            pl.publish(_img(np.ascontiguousarray(tex[:, 20:20 + w]), st, "cam0", "mono8"))
            pr.publish(_img(np.ascontiguousarray(tex[:, 30:30 + w]), st, "cam1", "mono8"))
            if seg:
                s = np.zeros((h, w, 3), np.uint8)
                s[100:300, 200:280] = (255, 0, 0)
                ps.publish(_img(s, st, "cam0", "rgb8"))
            if seg_right:
                s = np.zeros((h, w, 3), np.uint8)
                s[50:150, 400:500] = (255, 0, 0)
                psr.publish(_img(s, st, "cam1", "rgb8"))
            sent.append((st.sec, st.nanosec))
            for _ in range(5):
                ex.spin_once(timeout_sec=0.01)
        t0 = time.time()
        while (len(got["left"]) < N_FRAMES or len(got["right"]) < N_FRAMES) and time.time() - t0 < 10:
            ex.spin_once(timeout_sec=0.05)
    finally:
        ex.shutdown()
        node.destroy_node()
        peer.destroy_node()
    for side, frame in (("left", "cam0"), ("right", "cam1")):
        msgs = got[side]
        assert [(m.header.stamp.sec, m.header.stamp.nanosec) for m in msgs] == sent, side
        for m in msgs:
            assert m.encoding == "mono8" and (m.width, m.height) == (w, h) and m.step == w
            assert m.header.frame_id == frame
            a = np.frombuffer(bytes(m.data), np.uint8)
            assert set(np.unique(a).tolist()) <= {0, 192, 255}
    return got


def test_node_none_backend_all_zero(ros_ctx):
    got = _run(ros_ctx, {"segmenter.backend": "none"}, 640, 480)
    for m in got["left"] + got["right"]:
        assert max(m.data) == 0


def test_node_oracle_with_calib(ros_ctx, tmp_path):
    cmap = tmp_path / "cmap.yaml"
    cmap.write_text("encoding: rgb\nclasses:\n  person: [[255, 0, 0]]\n")
    got = _run(ros_ctx, {"segmenter.backend": "oracle_uhumans2", "seg_topic": "/seg",
                         "segmenter.colormap_file": str(cmap), "calib_file": calib_path("euroc")},
               752, 480, seg=True)
    for side in ("left", "right"):
        a = np.frombuffer(bytes(got[side][-1].data), np.uint8)
        assert (a == 255).sum() > 10000 and (a == 192).sum() > 0


def test_node_oracle_right_seg(ros_ctx, tmp_path):
    """P5: seg_right_topic -> the right mask is the right semantic image's dynamic instances (no stereo warp)."""
    cmap = tmp_path / "cmap.yaml"
    cmap.write_text("encoding: rgb\nclasses:\n  person: [[255, 0, 0]]\n")
    got = _run(ros_ctx, {"segmenter.backend": "oracle_colormap", "seg_topic": "/seg", "seg_right_topic": "/seg_right",
                         "segmenter.colormap_file": str(cmap), "calib_file": calib_path("euroc"),
                         "extension.enable": False, "tracker.enable": False},
               752, 480, seg=True, seg_right=True)
    left = np.frombuffer(bytes(got["left"][-1].data), np.uint8).reshape(480, 752)
    right = np.frombuffer(bytes(got["right"][-1].data), np.uint8).reshape(480, 752)
    assert (left == 255).sum() == 200 * 80 and (left[100:300, 200:280] == 255).all()
    assert (right == 255).sum() == 100 * 100 and (right[50:150, 400:500] == 255).all()


def test_node_publishes_zero_masks_on_failure(ros_ctx):
    got = _run(ros_ctx, {"segmenter.backend": "none"}, 320, 240, break_segmenter=True)
    for m in got["left"] + got["right"]:
        assert max(m.data) == 0


def test_node_warmup_before_first_frame(ros_ctx, monkeypatch):
    """P2 bug: the segmenter warmup (TensorRT context, ~1 s) ran in the first image callback, so the reliable
    depth-10 input queue overflowed and the first frames got no mask. With a calibration the warmup must run in
    the constructor, with the calibrated image size."""
    from rclpy.parameter import Parameter

    from savior_perception import node as node_mod
    from savior_perception.segmenters import NullSegmenter

    shapes = []

    class Recording(NullSegmenter):
        def warmup(self, shape):
            shapes.append(tuple(shape[:2]))

    monkeypatch.setattr(node_mod, "make_segmenter", lambda *a, **k: Recording())
    n = node_mod.SaviorNode(context=ros_ctx, parameter_overrides=[
        Parameter("calib_file", value=calib_path("t265")), Parameter("segmenter.backend", value="none")])
    try:
        assert shapes == [(800, 848)] and n._warmed
    finally:
        n.destroy_node()


def test_node_motion_waits_for_gyro(ros_ctx):
    """P4: with motion.enable the node holds each frame until gyro samples cover its stamp (deterministic replay),
    then publishes the masks in frame order; IMU stalls longer than imu_wait_ms release the frame anyway."""
    from builtin_interfaces.msg import Time
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.parameter import Parameter
    from sensor_msgs.msg import Image, Imu

    from savior_perception.node import SaviorNode, mask_qos

    node = SaviorNode(context=ros_ctx, parameter_overrides=[
        Parameter("segmenter.backend", value="none"), Parameter("calib_file", value=calib_path("euroc")),
        Parameter("motion.enable", value=True), Parameter("imu_topic", value="/imu"),
        Parameter("imu_wait_ms", value=1500)])
    peer = rclpy.create_node("savior_test_peer_imu", context=ros_ctx)
    q = mask_qos()
    pl = peer.create_publisher(Image, "/cam0/image_raw", q)
    pr = peer.create_publisher(Image, "/cam1/image_raw", q)
    pi = peer.create_publisher(Imu, "/imu", q)
    got = []
    peer.create_subscription(Image, "/savior/mask/left", lambda m: got.append(m.header.stamp.nanosec), q)
    ex = SingleThreadedExecutor(context=ros_ctx)
    ex.add_node(node)
    ex.add_node(peer)

    def spin(sec):
        t0 = time.time()
        while time.time() - t0 < sec:
            ex.spin_once(timeout_sec=0.01)

    def imu(t_ns):
        m = Imu()
        m.header.stamp = Time(sec=100, nanosec=t_ns)
        m.angular_velocity.y = 0.1
        pi.publish(m)
    try:
        t0 = time.time()
        while (pl.get_subscription_count() == 0 or pi.get_subscription_count() == 0) and time.time() - t0 < 10:
            ex.spin_once(timeout_sec=0.05)
        img = np.random.default_rng(0).integers(0, 255, (480, 752), dtype=np.uint8)
        for t_ns in range(0, 110_000_000, 5_000_000):       # gyro up to 0.105 s
            imu(t_ns)
        for k in range(4):                                   # frames at 0, 50, 100, 150 ms
            st = Time(sec=100, nanosec=k * 50_000_000)
            pl.publish(_img(img, st, "cam0", "mono8"))
            pr.publish(_img(img, st, "cam1", "mono8"))
        spin(0.6)
        assert got == [0, 50_000_000, 100_000_000]           # frame at 150 ms waits for the gyro
        imu(155_000_000)
        spin(0.4)
        assert got == [0, 50_000_000, 100_000_000, 150_000_000]
        st = Time(sec=100, nanosec=200_000_000)              # IMU stalls: released after imu_wait_ms
        pl.publish(_img(img, st, "cam0", "mono8"))
        pr.publish(_img(img, st, "cam1", "mono8"))
        spin(0.5)
        assert len(got) == 4
        spin(2.0)
        assert got[-1] == 200_000_000 and node._imu_timeouts == 1
    finally:
        ex.shutdown()
        node.destroy_node()
        peer.destroy_node()


def test_node_limits_threads(ros_ctx):
    """P4 bug fix: OpenCV defaulted to all 48 cores per node (load ~290 with 18 parallel runs)."""
    import cv2
    from rclpy.parameter import Parameter

    from savior_perception.node import SaviorNode
    before = cv2.getNumThreads()
    try:
        n = SaviorNode(context=ros_ctx, parameter_overrides=[Parameter("segmenter.backend", value="none"),
                                                             Parameter("num_threads", value=3)])
        assert cv2.getNumThreads() == 3
        n.destroy_node()
        assert os.environ.get("OMP_NUM_THREADS")              # BLAS/OMP capped from SAVIOR_NUM_THREADS at import
    finally:
        cv2.setNumThreads(before)
