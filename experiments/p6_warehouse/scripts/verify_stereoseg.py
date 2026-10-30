#!/usr/bin/env python3
"""verify_stereoseg.py seq...: the ros2_stereoseg bags must carry byte-identical messages (and bag times) on every topic
of the original data/warehouse/ros2 bags, plus /cam1/segmentation(_moving) with one message per left image stamp."""
import hashlib
import sys
from pathlib import Path

from rosbags.rosbag2 import Reader

W = Path('/home/sasa/workspace/savior_ws/data/warehouse')


def digest(p):
    h, n = {}, {}
    with Reader(p) as r:
        for c, t, raw in r.messages():
            h.setdefault(c.topic, hashlib.sha1())
            h[c.topic].update(t.to_bytes(8, 'little', signed=True) + bytes(raw))
            n[c.topic] = n.get(c.topic, 0) + 1
    return {k: v.hexdigest() for k, v in h.items()}, n


ok = True
for q in sys.argv[1:]:
    a, na = digest(W / 'ros2' / q)
    b, nb = digest(W / 'ros2_stereoseg' / q)
    bad = [k for k in a if a[k] != b.get(k)]
    extra = sorted(set(b) - set(a))
    good = not bad and extra == ['/cam1/segmentation', '/cam1/segmentation_moving'] and \
        nb['/cam1/segmentation'] == nb['/cam0/image_raw'] == nb['/cam1/segmentation_moving']
    ok &= good
    print(q, 'OK' if good else 'MISMATCH', 'differing:', bad, 'extra:', extra, {k: nb[k] for k in extra})
sys.exit(0 if ok else 1)
