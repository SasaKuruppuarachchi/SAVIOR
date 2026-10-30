#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record a std_msgs/String topic (default /savior/stats, one JSON document per frame) to a JSON-lines file.

Every line is flushed, so the file is complete even if the process is killed. The QoS is RELIABLE with a
deep history (offline evaluation must not lose stats lines; savior_node publishes them reliable).

  ros2 run savior_bringup stats_recorder.py --ros-args -p topic:=/savior/stats -p output:=savior_stats.jsonl
"""
import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class StatsRecorder(Node):
    def __init__(self):
        super().__init__('stats_recorder')
        self.declare_parameter('topic', '/savior/stats')
        self.declare_parameter('output', '')
        topic = self.get_parameter('topic').value
        out = self.get_parameter('output').value
        if not out:
            raise SystemExit('stats_recorder: parameter "output" is required')
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        self.fh = open(out, 'w')
        self.n = 0
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1000, reliability=ReliabilityPolicy.RELIABLE)
        self.sub = self.create_subscription(String, topic, self.cb, qos)
        self.get_logger().info(f'recording {topic} -> {out}')

    def cb(self, msg):
        self.fh.write(msg.data.replace('\n', ' ') + '\n')
        self.fh.flush()
        self.n += 1

    def close(self):
        self.fh.close()
        print(f'[stats_recorder] wrote {self.n} lines', flush=True)


def main():
    rclpy.init(args=sys.argv)
    node = StatsRecorder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.close()
        try:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:  # context already shut down by the SIGINT handler
            pass


if __name__ == '__main__':
    main()
