import sys, math, cProfile, pstats
import numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
sys.path.insert(0, '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/dev')
from savior_perception.core import PipelineConfig, SaviorPipeline, RoleTable, Instance, ideal_stereo
from savior_perception.core.synthetic import fronto_plane, render_stereo_sequence
rng = np.random.default_rng(0)
rect = ideal_stereo(640, 480, 450.0, 0.11)
pl = [fronto_plane((0, 0, 6.0), 14, 9, 0.01, rng), fronto_plane((-0.6, 0.2, 2.8), 0.5, 1.6, 0.004, rng, cls='person', vel=(0.8,0,0)),
      fronto_plane((0.9, 0.2, 3.2), 0.5, 1.6, 0.004, rng, cls='person')]
frames = list(render_stereo_sequence(rect, pl, 60, 30.0, yaw_rate=math.radians(30), cam_vel=(0.0, 0, 0.4)))
cfg = PipelineConfig().copy(**{'motion.enable': True, 'tracker.enable': False})
pipe = SaviorPipeline(cfg, RoleTable(dynamic=['person']), rect)
def run():
    for fr in frames:
        insts = [Instance.from_mask(m, 'person') for m in fr['masks'][1:] if m.sum() > 50]
        pipe.process(fr['left'], fr['right'], fr['stamp'], insts, R_imu=fr['R_imu'])
cProfile.run('run()', '/tmp/prof.out')
p = pstats.Stats('/tmp/prof.out'); p.sort_stats('tottime').print_stats(18)
