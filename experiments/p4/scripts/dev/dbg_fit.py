"""Run the pipeline on cafe1-1 frames [a,b) and dump per-point data of instance fits."""
import sys, json, math, numpy as np, pickle
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
import perception_offline as po
from savior_perception.core import motion as M
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.segmenters import make_segmenter
WS = '/home/sasa/workspace/savior_ws'; B = WS + '/src/savior/savior_bringup'
P = po.load_params([WS + '/src/savior/savior_perception/config/default.yaml', B + '/config/openloris_t265/savior_perception.yaml'],
                   ['motion.enable=true'] + sys.argv[3:])
cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
roles = RoleTable.from_yaml(B + '/config/roles/coco_indoor.yaml')
rect = stereo_from_kalibr(B + '/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
seg = make_segmenter('yolo', model=WS + '/models/yolo26s-seg.engine', conf=0.25, iou=0.7, imgsz=640, device='', half=False,
                     classes=roles.relevant_classes(), colormap_file='', retina_masks=True)
pipe = SaviorPipeline(cfg, roles, rect)
gyro = po.read_gyro(WS + '/data/openloris/ros2/cafe1-1', '/t265/imu')
dump = []
orig = pipe.motion.instance_fit
def hook(Xp, b, ego, dt):
    out = orig(Xp, b, ego, dt)
    if out is not None:
        Y = Xp @ ego.R.T + ego.t
        dump.append(dict(frame=pipe.frame_index, X=Xp.copy(), b=b.copy(), Y=Y, R=ego.R, t=ego.t, out={k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in out.items()}))
    return out
pipe.motion.instance_fit = hook
a, bnd = int(sys.argv[1]), int(sys.argv[2]); prev = None; n = 0
for st, l, r in po.read_stereo(WS + '/data/openloris/ros2/cafe1-1', '/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw'):
    n += 1
    if n >= bnd: break
    inst = seg.predict(l)
    R = gyro.rotation(prev, st * 1e-9) if prev is not None else None
    prev = st * 1e-9
    pipe.process(l, r, st * 1e-9, inst, R_imu=R)
dump = [d for d in dump if d['frame'] >= a]
pickle.dump(dump, open('/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/dev/dump.pkl', 'wb'))
print(len(dump))
