#!/usr/bin/env python3
"""verify_ros1_bag.py <ros2 bag dir> <ros1 .bag> [topics...]: message counts, header stamps (exact ns) and
bag (receive) times must be identical between the ROS 2 source and the converted ROS 1 bag. Exit 1 on mismatch.
Runs in the savior image (rosbags)."""
import sys
from rosbags.highlevel import AnyReader
from pathlib import Path

TOP = sys.argv[3:] or ['/cam0/image_raw', '/cam1/image_raw', '/imu0']


def scan(p):
    out = {t: [] for t in TOP}
    enc = {}
    with AnyReader([Path(p)]) as r:
        cons = [c for c in r.connections if c.topic in TOP]
        for c, t, raw in r.messages(connections=cons):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp
            out[c.topic].append((st.sec * 10**9 + st.nanosec, t))
            if hasattr(m, 'encoding'):
                enc[c.topic] = (m.encoding, m.width, m.height)
    return out, enc


a, ea = scan(sys.argv[1])
b, eb = scan(sys.argv[2])
ok = True
for t in TOP:
    sa, sb = sorted(a[t]), sorted(b[t])
    same = sa == sb
    ok &= same and len(sa) > 0
    d = [x[0] for x in sa]
    dt = [(y - x) * 1e-9 for x, y in zip(d, d[1:])]
    print('%-18s n=%d/%d stamps+bagtimes identical=%s first=%.9f last=%.9f dt[min,max]=[%.4f,%.4f] %s' % (
        t, len(sa), len(sb), same, d[0] * 1e-9, d[-1] * 1e-9, min(dt), max(dt), eb.get(t, '')))
print('VERIFY', 'OK' if ok else 'MISMATCH')
sys.exit(0 if ok else 1)
