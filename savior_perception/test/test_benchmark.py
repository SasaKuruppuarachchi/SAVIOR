# SPDX-License-Identifier: GPL-3.0-or-later
"""Micro-benchmark of the pipeline core (segmenter excluded). Run with `pytest -s` to see numbers.

Target: < 8 ms per frame with ~5 instances on the desktop CPU.
"""
import os
import time

import cv2
import numpy as np
import pytest

from conftest import calib_path
from savior_perception.core import PipelineConfig, RoleTable, SaviorPipeline, ideal_stereo, stereo_from_kalibr
from savior_perception.core.synthetic import demo_scene_raw, planes_to_instances

ROLES = RoleTable(dynamic=["person"], potential=["chair", "suitcase"])
N = int(os.environ.get("SAVIOR_BENCH_FRAMES", "60"))
LIMIT_MS = float(os.environ.get("SAVIOR_BENCH_LIMIT_MS", "25"))  # loose CI bound; target is 8 ms


def _bench(rect, downsample, threads):
    left, right, planes_raw, _ = demo_scene_raw(rect, seed=1, n_people=2, n_objects=3)
    cfg = PipelineConfig()
    cfg.depth.downsample = downsample
    pipe = SaviorPipeline(cfg, ROLES, rect)
    old = cv2.getNumThreads()
    cv2.setNumThreads(threads)
    try:
        frames = [planes_to_instances(planes_raw) for _ in range(N + 5)]
        per_stage, totals = {}, []
        for i, inst in enumerate(frames):
            t = time.perf_counter()
            _, _, st = pipe.process(left, right, i, inst)
            dt = (time.perf_counter() - t) * 1e3
            if i >= 5:
                totals.append(dt)
                for k, v in st["timings_ms"].items():
                    per_stage.setdefault(k, []).append(v)
    finally:
        cv2.setNumThreads(old)
    med = {k: float(np.median(v)) for k, v in per_stage.items()}
    return float(np.median(totals)), med, len(frames[0])


CASES = [("ideal640x480", 2), ("euroc752x480", 2), ("t265_848x800", 2), ("t265_848x800", 1)]


@pytest.mark.parametrize("name,ds", CASES)
@pytest.mark.parametrize("threads", [0, 1], ids=["mt", "1thread"])
def test_benchmark(name, ds, threads):
    if name.startswith("ideal"):
        rect = ideal_stereo(640, 480, 450.0, 0.11)
    else:
        rect = stereo_from_kalibr(calib_path("euroc" if name.startswith("euroc") else "t265"))
    total, med, n_inst = _bench(rect, ds, threads if threads else cv2.getNumThreads())
    stages = " ".join(f"{k}={v:.2f}" for k, v in med.items() if k != "total")
    print(f"\n[bench] {name} downsample={ds} threads={'all' if threads == 0 else threads} "
          f"instances={n_inst}: median total {total:.2f} ms ({stages})")
    if ds == 2:  # default configuration; downsample=1 on the fisheye is reported only
        assert total < LIMIT_MS
