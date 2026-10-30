"""prof_pipe.py <seq> <variant> <n> [start]: cProfile of SaviorPipeline.process on cached detections (single thread)."""
import cProfile, pstats, sys, os
sys.argv += [] 
import p7eval as E
from variants import VARIANTS
seq, var, n = sys.argv[1], sys.argv[2], int(sys.argv[3]); start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
import numpy as np, yaml
from savior_perception.core.calibration import stereo_from_kalibr
from savior_perception.core.config import PipelineConfig
from savior_perception.core.pipeline import SaviorPipeline
from savior_perception.core.roles import RoleTable
from savior_perception.core.types import Instance
from savior_perception.params import all_defaults
src, roles, over = VARIANTS[var]
P = all_defaults(); P.update(E.flatten(yaml.safe_load(open(f'{E.B}/warehouse/savior_perception_yolo.yaml'))['savior_node']['ros__parameters'])); P.update(over)
cfg = PipelineConfig.from_flat({k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS})
rect = stereo_from_kalibr(f'{E.B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1')
pipe = SaviorPipeline(cfg, RoleTable.from_yaml(f'{E.B}/roles/{roles}.yaml'), rect)
g, frames = E.load_frames(seq); dets = E.DetCache(seq)
st = sorted(frames)[start:start + n]
prev = None; pr = cProfile.Profile(); T = []
import time
for s in st:
    l, r = frames[s]; t = s * 1e-9
    R = g.rotation(prev, t) if prev is not None else None; prev = t
    inp = dets.get(s, Instance)
    pr.enable(); t0 = time.perf_counter(); pipe.process(l, r, t, inp, R_imu=R); T.append((time.perf_counter() - t0) * 1e3); pr.disable()
print('total ms median %.1f p90 %.1f p99 %.1f' % tuple(np.percentile(T, [50, 90, 99])))
pstats.Stats(pr).sort_stats('cumulative').print_stats(35)
