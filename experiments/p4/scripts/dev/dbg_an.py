import pickle, numpy as np, sys
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from savior_perception.core.calibration import stereo_from_kalibr
rect = stereo_from_kalibr('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
D = pickle.load(open('/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/dev/dump.pkl', 'rb'))
D = [d for d in D if d['out']['s_rad'] < 0.3]
D.sort(key=lambda d: d['out']['v_rad'])
for d in D[:6] + D[-2:]:
    X, b, Y, t = d['X'], d['b'], d['Y'], d['t']
    y = Y / np.linalg.norm(Y, axis=1, keepdims=True)
    m = y.mean(0); m /= np.linalg.norm(m)
    # radial (outward from m) component of residual vs offset
    off = y - m; e = b - y
    r_off = np.linalg.norm(off, axis=1); u = off / np.maximum(r_off[:, None], 1e-9)
    e_rad = np.sum(e * u, axis=1)
    rng = np.linalg.norm(Y, axis=1)
    px = rect.cams[0].project(Y)
    print('frame', d['frame'], 'v_rad %.2f s %.2f n %d rng %.2f' % (d['out']['v_rad'], d['out']['s_rad'], d['out']['n'], d['out']['rng']), 't', np.round(t, 4), 'img', np.round(px.mean(0)))
    o = np.argsort(r_off)
    print('   off(mrad)', np.round(r_off[o] * 1e3, 1)[::3])
    print('   e_rad(mrad)', np.round(e_rad[o] * 1e3, 2)[::3])
    print('   range', np.round(rng[o], 2)[::3])
