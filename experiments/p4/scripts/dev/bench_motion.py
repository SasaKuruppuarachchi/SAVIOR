"""bench_motion.py <cache.pkl> [k=v ...]: CPU (thread) time per stage on cached cafe1-1 frames (single thread)."""
import os, sys, time, pickle, math
for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import cv2
cv2.setNumThreads(1)
import numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
sys.path.insert(0, os.environ.get('PERC', '/home/sasa/workspace/savior_ws/src/savior/savior_perception'))
import perception_offline as po
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.calibration import stereo_from_kalibr
WS = '/home/sasa/workspace/savior_ws'; B = WS + '/src/savior/savior_bringup'
cache = sys.argv[1]
if not os.path.isfile(cache):
    from savior_perception.segmenters import make_segmenter
    roles = RoleTable.from_yaml(B + '/config/roles/coco_indoor.yaml')
    seg = make_segmenter('yolo', model=WS + '/models/yolo26s-seg.engine', conf=0.25, iou=0.7, imgsz=640, device='', half=False,
                         classes=roles.relevant_classes(), colormap_file='', retina_masks=True)
    fr = []
    for st, l, r in po.read_stereo(WS + '/data/openloris/ros2/cafe1-1', '/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw'):
        if len(fr) >= 400: break
        if st < 0: continue
        inst = seg.predict(l)
        fr.append((st, l, r, [(i.mask.copy(), i.cls, i.score) for i in inst]))
    g = po.read_gyro(WS + '/data/openloris/ros2/cafe1-1', '/t265/imu')
    pickle.dump((fr, g), open(cache, 'wb'))
    print('cached', len(fr)); sys.exit(0)
fr, gyro = pickle.load(open(cache, 'rb'))
P = po.load_params([WS + '/src/savior/savior_perception/config/default.yaml', B + '/config/openloris_t265/savior_perception.yaml'],
                   ['motion.static_mask_file=' + B + '/config/openloris_t265/mask_t265_cam0.png'] + sys.argv[2:])
cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
roles = RoleTable.from_yaml(B + '/config/roles/coco_indoor.yaml')
rect = stereo_from_kalibr(B + '/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=cfg.depth.rect_focal_scale)
sm = cv2.imread(cfg.motion.static_mask_file, cv2.IMREAD_UNCHANGED)[:, :, :3].max(axis=2) if cfg.motion.enable else None
pipe = SaviorPipeline(cfg, roles, rect, static_mask=sm)
from savior_perception.core.types import Instance
T = {'pipeline': [], 'motion': [], 'depth': []}
if pipe.motion is not None:
    orig = pipe.motion.update
    def upd(*a, **k):
        t = time.thread_time(); r = orig(*a, **k); T['motion'].append(time.thread_time() - t); return r
    pipe.motion.update = upd
if pipe.depth is not None:
    origd = pipe.depth.compute
    def dep(*a, **k):
        t = time.thread_time(); r = origd(*a, **k); T['depth'].append(time.thread_time() - t); return r
    pipe.depth.compute = dep
prev = None
for k, (st, l, r, insts) in enumerate(fr):
    inst = [Instance.from_mask(m, c, s) for m, c, s in insts]
    R = gyro.rotation(prev, st * 1e-9) if prev is not None else None
    prev = st * 1e-9
    t = time.thread_time()
    pipe.process(l, r, st * 1e-9, inst, R_imu=R)
    T['pipeline'].append(time.thread_time() - t)
for k, v in T.items():
    if v:
        v = np.array(v[20:]) * 1e3
        print('%-9s CPU ms/frame: median %.2f  mean %.2f  p90 %.2f' % (k, np.median(v), v.mean(), np.percentile(v, 90)))
