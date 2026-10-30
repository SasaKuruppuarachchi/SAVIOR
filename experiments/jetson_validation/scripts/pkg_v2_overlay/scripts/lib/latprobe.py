#!/usr/bin/env python3
"""latprobe.py --out lat.csv : passive latency probe for the Jetson timing runs (v2). Runs in the timing container next to
savior-run (same ROS_DOMAIN_ID) and records, for every message of
    0 /cam0/image_raw      (bag player -> also what OpenVINS / savior_node receive)
    1 /savior/mask/left    (savior_node output)
    2 /ov_msckf/poseimu    (OpenVINS pose, published after each update)
the header stamp (ns) and the local receive time (CLOCK_REALTIME ns). Subscriptions are RAW (serialized CDR, only the
header stamp is decoded: no image copy into Python), BEST_EFFORT (compatible with reliable publishers, never
back-pressures them). Derived offline (timing_parse.py): mask latency = recv(mask) - recv(image) of the same stamp,
end-to-end latency = recv(pose) - recv(image) of the nearest image stamp (|d| < 25 ms).
Stops on SIGINT / SIGTERM and writes the csv (topic,stamp_ns,recv_ns)."""
import argparse, signal, struct, sys, time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseWithCovarianceStamped

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
a = ap.parse_args()
rows = []
stop = False


def _stop(*_):
    global stop
    stop = True


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def stamp(raw):
    # CDR: 4-byte encapsulation header, then std_msgs/Header: builtin_interfaces/Time {int32 sec, uint32 nanosec}
    le = raw[1] == 1
    sec, nsec = struct.unpack_from('<iI' if le else '>iI', raw, 4)
    return sec * 1_000_000_000 + nsec


def cb(tid):
    def f(raw):
        rows.append((tid, stamp(raw), time.time_ns()))
    return f


try:
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(args=None, signal_handler_options=SignalHandlerOptions.NO)
except ImportError:  # older rclpy
    rclpy.init(args=None)
signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)
node = rclpy.create_node('savior_latprobe')
qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=100, reliability=ReliabilityPolicy.BEST_EFFORT,
                 durability=DurabilityPolicy.VOLATILE)
subs = [node.create_subscription(Image, '/cam0/image_raw', cb(0), qos, raw=True),
        node.create_subscription(Image, '/savior/mask/left', cb(1), qos, raw=True),
        node.create_subscription(PoseWithCovarianceStamped, '/ov_msckf/poseimu', cb(2), qos, raw=True)]
print('latprobe up', flush=True)
while not stop and rclpy.ok():
    rclpy.spin_once(node, timeout_sec=0.2)
with open(a.out, 'w') as fh:
    fh.write('topic,stamp_ns,recv_ns\n')
    fh.writelines(f'{t},{s},{r}\n' for t, s, r in rows)
print(f'latprobe: {len(rows)} messages -> {a.out}', flush=True)
node.destroy_node()
rclpy.shutdown()
sys.exit(0)
