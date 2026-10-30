import sys, time, math, json
import numpy as np
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from savior_perception.core import PipelineConfig, SaviorPipeline, RoleTable, Instance, ideal_stereo
from savior_perception.core.synthetic import fronto_plane, render_stereo_sequence

def scene(kind, seed=0):
    rng = np.random.default_rng(seed)
    wall = fronto_plane((0, 0, 6.0), 14, 9, 0.01, rng)
    box = fronto_plane((1.6, 0.6, 3.5), 1.5, 1.5, 0.006, rng)
    pv = {'static': None, 'lateral': (0.8, 0, 0), 'slow': (0.3, 0, 0), 'radial': (0, 0, -1.0)}[kind]
    person = fronto_plane((-0.6, 0.2, 2.8), 0.5, 1.6, 0.004, rng, cls='person', vel=pv)
    return [wall, box, person]

rect = ideal_stereo(640, 480, 450.0, 0.11)
roles = RoleTable(dynamic=['person'], potential=['chair'])
for kind in sys.argv[1:] or ['static', 'lateral', 'slow', 'radial']:
    cfg = PipelineConfig().copy(**{'motion.enable': True, 'tracker.enable': False})
    pipe = SaviorPipeline(cfg, roles, rect)
    pl = scene(kind)
    for fr in render_stereo_sequence(rect, pl, 30, 30.0, yaw_rate=math.radians(30), cam_vel=(0.0, 0, 0.4)):
        insts = [Instance.from_mask(fr['masks'][2], 'person')] if fr['masks'][2].sum() > 50 else []
        ml, mr, st = pipe.process(fr['left'], fr['right'], fr['stamp'], insts, R_imu=fr['R_imu'])
        m = st['motion']
        i = st['instances'][0] if st['instances'] else {}
        print(kind, st['frame'], i.get('status'), json.dumps(i.get('motion')), 'bg', m.get('n_bg'), m.get('n_inl'), m.get('sigma_bg_px'), m.get('t'), m.get('dtheta_deg'), m.get('ms'), 'core', st['core_px'])
