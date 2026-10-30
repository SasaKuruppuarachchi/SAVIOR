#!/usr/bin/env python3
"""pose_recorder.py: nav_msgs/Odometry -> TUM file 'stamp[s] tx ty tz qx qy qz qw' (header stamp, exact ns digits).
Params: ~topic (default /vins_estimator/odometry), ~out (file). Every line is flushed."""
import rospy
from nav_msgs.msg import Odometry


def main():
    rospy.init_node('pose_recorder', anonymous=True)
    topic = rospy.get_param('~topic', '/vins_estimator/odometry')
    out = open(rospy.get_param('~out'), 'w')
    out.write('# timestamp tx ty tz qx qy qz qw\n')
    n = [0]

    def cb(m):
        p, q, s = m.pose.pose.position, m.pose.pose.orientation, m.header.stamp
        out.write('%d.%09d %.6f %.6f %.6f %.9f %.9f %.9f %.9f\n' % (s.secs, s.nsecs, p.x, p.y, p.z, q.x, q.y, q.z, q.w))
        out.flush()
        n[0] += 1
    rospy.Subscriber(topic, Odometry, cb, queue_size=100000, tcp_nodelay=True)
    rospy.spin()
    out.close()
    print('pose_recorder: %d poses from %s' % (n[0], topic))


if __name__ == '__main__':
    main()
