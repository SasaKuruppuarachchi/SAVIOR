"""maskhash.py <seq> <variant> <n> [start]: md5 of all left/right masks of SaviorPipeline on cached detections + timing."""
import hashlib, sys, time
import numpy as np, yaml
import p7eval as E
from variants import VARIANTS
from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.types import Instance
from savior_perception.params import all_defaults
import savior_perception
seq, var, n = sys.argv[1], sys.argv[2], int(sys.argv[3]); start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
src, roles, over = VARIANTS[var]
P = all_defaults(); P.update(E.flatten(yaml.safe_load(open(f'{E.B}/warehouse/savior_perception_yolo.yaml'))['savior_node']['ros__parameters'])); P.update(over)
cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
rect = stereo_from_kalibr(f'{E.B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1')
pipe = SaviorPipeline(cfg, RoleTable.from_yaml(f'{E.B}/roles/{roles}.yaml'), rect)
g, frames = E.load_frames(seq); dets = E.DetCache(seq)
h = hashlib.md5(); prev = None; T = []
for s in sorted(frames)[start:start + n]:
    l, r = frames[s]; t = s * 1e-9
    R = g.rotation(prev, t) if prev is not None else None; prev = t
    t0 = time.perf_counter(); ml, mr, _ = pipe.process(l, r, t, dets.get(s, Instance), R_imu=R); T.append(time.perf_counter() - t0)
    h.update(ml.tobytes()); h.update(mr.tobytes())
print(savior_perception.__file__.split('/savior_perception/')[0][-40:], var, h.hexdigest(), 'ms median %.1f' % (1e3 * np.median(T)))
