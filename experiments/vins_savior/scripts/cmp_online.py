"""cmp_online.py <online run dir (with masks_bag/)> <offline off_X dir> <reference online run dir> : md5 of every published
mask (raw mono8 pixels, ros2 bag of /savior/mask/left|right) vs the offline export (index.csv), + trajectory md5 of the
re-run vs the original frozen run. Prints one JSON line. Run in the savior image."""
import csv, glob, hashlib, json, sys
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
on, off, ref = sys.argv[1:4]
idx = {int(r['stamp_ns']): (r['md5_left'], r['md5_right']) for r in csv.DictReader(open(off + '/index.csv'))}
r = rosbag2_py.SequentialReader()
r.open(rosbag2_py.StorageOptions(uri=on + '/masks_bag', storage_id=''), rosbag2_py.ConverterOptions('', ''))
got = {'/savior/mask/left': {}, '/savior/mask/right': {}}
while r.has_next():
    t, d, _ = r.read_next()
    m = deserialize_message(d, Image)
    a = np.frombuffer(bytes(m.data), np.uint8).reshape(m.height, m.step)[:, :m.width]
    got[t][m.header.stamp.sec * 10**9 + m.header.stamp.nanosec] = hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()
res = {}
for k, t in ((0, '/savior/mask/left'), (1, '/savior/mask/right')):
    g = got[t]
    res[t.split('/')[-1]] = dict(online=len(g), offline=len(idx), common=len(set(g) & set(idx)),
                                 md5_equal=sum(g[s] == idx[s][k] for s in g if s in idx))
md5f = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()  # noqa: E731
res['traj_equal_to_reference'] = md5f(on + '/stamped_traj_estimate.txt') == md5f(ref + '/stamped_traj_estimate.txt')
res['run'] = on.split('/results/')[-1]
print(json.dumps(res))
