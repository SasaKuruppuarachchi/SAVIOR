import sys, math, numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception/test'); sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
import test_motion as T
for v in [(0.8, 0, 0), (-0.8, 0, 0)]:
    h = T.run_scene(T.scene(person_vel=v))
    print(v, [(i.status, i.bbox[0], i.bbox[2]) for _, _, insts in h[::5] for i in insts])
h = T.run_scene(T.scene(person=False, chair=True, chair_vel=(-0.8, 0, 0)))
print([(i.status, i.bbox[0]) for _, _, insts in h[::4] for i in insts])
