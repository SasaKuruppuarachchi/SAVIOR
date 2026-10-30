"""bench_ab.py <cache.pkl> "<A k=v ...>" "<B k=v ...>" ...: interleaved CPU (thread) time of motion.update / depth / pipeline."""
import os, sys, time, pickle
for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import cv2
cv2.setNumThreads(int(os.environ.get('CVT', '1')))
import numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
import perception_offline as po
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.types import Instance
WS = '/home/sasa/workspace/savior_ws'; B = WS + '/src/savior/savior_bringup'
fr, gyro = pickle.load(open(sys.argv[1], 'rb'))
roles = RoleTable.from_yaml(B + '/config/roles/coco_indoor.yaml')
variants = []
for spec in sys.argv[2:]:
    P = po.load_params([WS + '/src/savior/savior_perception/config/default.yaml', B + '/config/openloris_t265/savior_perception.yaml'],
                       ['motion.static_mask_file=' + B + '/config/openloris_t265/mask_t265_cam0.png'] + spec.split())
    cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
    rect = stereo_from_kalibr(B + '/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=cfg.depth.rect_focal_scale)
    sm = cv2.imread(cfg.motion.static_mask_file, cv2.IMREAD_UNCHANGED)[:, :, :3].max(axis=2)
    pipe = SaviorPipeline(cfg, roles, rect, static_mask=sm)
    T = {'pipeline': [], 'motion': [], 'depth': []}
    def wrap(obj, name, key, T=T):
        f = getattr(obj, name)
        def g(*a, **k):
            t = time.thread_time(); r = f(*a, **k); T[key].append(time.thread_time() - t); return r
        setattr(obj, name, g)
    if pipe.motion is not None: wrap(pipe.motion, 'update', 'motion')
    wrap(pipe.depth, 'compute', 'depth')
    variants.append((spec, pipe, T))
prev = None
for k, (st, l, r, insts) in enumerate(fr):
    R = gyro.rotation(prev, st * 1e-9) if prev is not None else None
    prev = st * 1e-9
    for spec, pipe, T in (variants if k % 2 == 0 else variants[::-1]):
        inst = [Instance.from_mask(m, c, s) for m, c, s in insts]
        t = time.thread_time()
        pipe.process(l, r, st * 1e-9, inst, R_imu=R)
        T['pipeline'].append(time.thread_time() - t)
for spec, pipe, T in variants:
    print('[%s]' % spec)
    for key, v in T.items():
        if v:
            v = np.array(v[20:]) * 1e3
            print('   %-9s CPU ms/frame: median %.2f  mean %.2f  p90 %.2f' % (key, np.median(v), v.mean(), np.percentile(v, 90)))
