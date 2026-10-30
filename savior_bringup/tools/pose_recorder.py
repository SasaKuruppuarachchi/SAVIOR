#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record a pose topic to a TUM trajectory file (replacement for ov_eval pose_to_file, which is ROS1-only).

Subscribes to geometry_msgs/PoseWithCovarianceStamped (default /ov_msckf/poseimu, OpenVINS' IMU pose in
the global frame, stamped in the IMU clock), or PoseStamped / nav_msgs/Odometry (--type), and writes
  timestamp tx ty tz qx qy qz qw
with the timestamp in seconds (header stamp). Every line is flushed so the file is usable even if the
process is killed. Duplicate / non-increasing stamps are skipped.

  ros2 run savior_bringup pose_recorder.py --ros-args -p topic:=/ov_msckf/poseimu -p output:=traj.txt
  python3 pose_recorder.py --topic /ov_msckf/poseimu --output traj.txt     (plain CLI form)
"""
import argparse
import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy


class PoseRecorder(Node):
    def __init__(self, cli):
        super().__init__('pose_recorder')
        self.declare_parameter('topic', cli.topic)
        self.declare_parameter('output', cli.output)
        self.declare_parameter('type', cli.type)
        topic = self.get_parameter('topic').value
        out = self.get_parameter('output').value
        typ = self.get_parameter('type').value
        if not out:
            raise SystemExit('pose_recorder: parameter "output" is required')
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        self.fh = open(out, 'w')
        self.fh.write('# timestamp tx ty tz qx qy qz qw\n')
        self.last = None
        self.n = 0
        if typ == 'pose_cov':
            from geometry_msgs.msg import PoseWithCovarianceStamped as T
            self.get_pose = lambda m: m.pose.pose
        elif typ == 'pose':
            from geometry_msgs.msg import PoseStamped as T
            self.get_pose = lambda m: m.pose
        elif typ == 'odom':
            from nav_msgs.msg import Odometry as T
            self.get_pose = lambda m: m.pose.pose
        else:
            raise SystemExit(f'unknown type {typ}')
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1000, reliability=ReliabilityPolicy.RELIABLE)
        self.sub = self.create_subscription(T, topic, self.cb, qos)
        self.get_logger().info(f'recording {topic} ({typ}) -> {out}')

    def cb(self, m):
        t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if self.last is not None and t <= self.last:
            return
        self.last = t
        p = self.get_pose(m)
        self.fh.write(f'{t:.9f} {p.position.x:.6f} {p.position.y:.6f} {p.position.z:.6f} '
                      f'{p.orientation.x:.9f} {p.orientation.y:.9f} {p.orientation.z:.9f} {p.orientation.w:.9f}\n')
        self.fh.flush()
        self.n += 1

    def close(self):
        self.fh.close()
        print(f"[pose_recorder] wrote {self.n} poses", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--topic', default='/ov_msckf/poseimu')
    ap.add_argument('--output', default='')
    ap.add_argument('--type', default='pose_cov', choices=['pose_cov', 'pose', 'odom'])
    cli, ros_args = ap.parse_known_args(rclpy.utilities.remove_ros_args(sys.argv)[1:])
    rclpy.init(args=sys.argv)
    node = PoseRecorder(cli)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.close()  # file is closed first: nothing is lost even if the teardown below fails
        try:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:  # context already shut down by the SIGINT handler
            pass


if __name__ == '__main__':
    main()
