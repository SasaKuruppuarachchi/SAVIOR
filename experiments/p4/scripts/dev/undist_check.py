import sys, numpy as np, cv2
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from savior_perception.core.calibration import stereo_from_kalibr
rect = stereo_from_kalibr('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
c = rect.cams[0]
for th_deg in (10, 30, 50, 60, 65, 70, 75, 80, 85):
    th = np.radians(th_deg)
    X = np.array([[np.sin(th), 0.0, np.cos(th)], [0, np.sin(th), np.cos(th)], [np.sin(th) * .7071, np.sin(th) * .7071, np.cos(th)]])
    p = c.project(X)
    for crit in (None, (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 100, 1e-12)):
        if crit is None:
            xy = cv2.fisheye.undistortPoints(p.reshape(-1, 1, 2), c.K, c.D).reshape(-1, 2)
        else:
            xy = cv2.fisheye.undistortPoints(p.reshape(-1, 1, 2), c.K, c.D, criteria=crit).reshape(-1, 2)
        b = np.column_stack([xy, np.ones(3)]); b /= np.linalg.norm(b, axis=1, keepdims=True)
        err = np.degrees(np.arccos(np.clip(np.sum(b * X, axis=1), -1, 1)))
        print(th_deg, 'px', np.round(p[0], 1), 'crit' if crit else 'dflt', 'err deg', np.round(err, 5), 'err px ~', np.round(np.radians(err) * 285, 3))
