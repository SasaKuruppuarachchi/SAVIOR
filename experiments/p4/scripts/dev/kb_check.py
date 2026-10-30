import sys, numpy as np, cv2
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from savior_perception.core.calibration import stereo_from_kalibr
rect = stereo_from_kalibr('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
c = rect.cams[0]; K, D = c.K, c.D
def kb_proj(X):
    a, b = X[:, 0] / X[:, 2], X[:, 1] / X[:, 2]; r = np.hypot(a, b); th = np.arctan(r)
    thd = th * (1 + D[0] * th**2 + D[1] * th**4 + D[2] * th**6 + D[3] * th**8)
    s = np.where(r > 1e-12, thd / r, 1.0)
    return np.column_stack([K[0, 0] * a * s + K[0, 2], K[1, 1] * b * s + K[1, 2]])
def kb_unproj(p):
    xd, yd = (p[:, 0] - K[0, 2]) / K[0, 0], (p[:, 1] - K[1, 2]) / K[1, 1]; thd = np.hypot(xd, yd); th = thd.copy()
    for _ in range(20):
        f = th * (1 + D[0] * th**2 + D[1] * th**4 + D[2] * th**6 + D[3] * th**8) - thd
        df = 1 + 3 * D[0] * th**2 + 5 * D[1] * th**4 + 7 * D[2] * th**6 + 9 * D[3] * th**8
        th = th - f / df
    s = np.where(thd > 1e-12, np.sin(th) / thd, 1.0)
    return np.column_stack([xd * s, yd * s, np.cos(th)])
for th_deg in (30, 60, 80):
    th = np.radians(th_deg)
    X = np.array([[np.sin(th) * .7071, np.sin(th) * .7071, np.cos(th)], [np.sin(th) * .6, -np.sin(th) * .8, np.cos(th)]])
    p_cv = c.project(X); p_kb = kb_proj(X)
    print(th_deg, 'proj cv-kb px', np.round(p_cv - p_kb, 4))
    b_kb = kb_unproj(p_kb)
    xy = cv2.fisheye.undistortPoints(p_kb.reshape(-1, 1, 2), K, D).reshape(-1, 2)
    b_cv = np.column_stack([xy, np.ones(2)]); b_cv /= np.linalg.norm(b_cv, axis=1, keepdims=True)
    print('   unproj kb err deg', np.round(np.degrees(np.arccos(np.clip((b_kb * X).sum(1), -1, 1))), 6), ' cv err deg', np.round(np.degrees(np.arccos(np.clip((b_cv * X).sum(1), -1, 1))), 5))
