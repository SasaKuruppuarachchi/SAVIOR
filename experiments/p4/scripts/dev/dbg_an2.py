import pickle, numpy as np, sys
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from savior_perception.core.calibration import stereo_from_kalibr
rect = stereo_from_kalibr('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
c = rect.cams[0]
D = pickle.load(open('/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/dev/dump.pkl', 'rb'))
fr = int(sys.argv[1])
for d in D:
    if d['frame'] != fr or d['out']['s_rad'] > 0.3: continue
    X, b, Y, R, t = d['X'], d['b'], d['Y'], d['R'], d['t']
    p_prev = c.project(X); p_pred = c.project(Y); p_meas = c.project(b)
    print('frame', fr, 'v_rad %.2f' % d['out']['v_rad'], 'v_lat', np.round(d['out']['v_lat'], 2), 't', np.round(t, 4))
    Yrot = X @ R.T   # rotation only
    p_rot = c.project(Yrot)
    for i in np.argsort(p_prev[:, 1]):
        print('  prev %6.1f %6.1f  meas-prev %6.2f %6.2f  pred-prev %6.2f %6.2f  (rot-only %6.2f %6.2f)  res %6.2f %6.2f  rng %.2f' % (
            *p_prev[i], *(p_meas[i] - p_prev[i]), *(p_pred[i] - p_prev[i]), *(p_rot[i] - p_prev[i]), *(p_meas[i] - p_pred[i]), np.linalg.norm(X[i])))
