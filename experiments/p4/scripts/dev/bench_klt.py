import sys, time, numpy as np, cv2
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_perception')
from perception_offline import read_stereo
from savior_perception.core.calibration import stereo_from_kalibr
cv2.setNumThreads(int(sys.argv[1]) if len(sys.argv) > 1 else -1)
fr = []
for st, l, r in read_stereo('/home/sasa/workspace/savior_ws/data/openloris/ros2/cafe1-1', '/t265/fisheye1/image_raw', '/t265/fisheye2/image_raw'):
    fr.append((l, r))
    if len(fr) > 300: break
rect = stereo_from_kalibr('/home/sasa/workspace/savior_ws/src/savior/savior_bringup/config/openloris_t265/kalibr_imucam_chain.yaml', focal_scale=0.7)
l0, l1 = fr[299][0], fr[300][0]
def T(f, n=50):
    t = time.perf_counter()
    for _ in range(n): f()
    return (time.perf_counter() - t) / n * 1e3
for s in (0.5, 0.35):
    a = cv2.resize(l0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA); b = cv2.resize(l1, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    print('resize ms %.3f' % T(lambda: cv2.resize(l0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)))
    p = cv2.goodFeaturesToTrack(a, 250, 0.01, 4).astype(np.float32)
    print('gftt ms %.3f' % T(lambda: cv2.goodFeaturesToTrack(a, 150, 0.01, 8)))
    for win, lev in ((15, 3), (15, 2), (11, 2), (9, 2), (11, 1)):
        crit = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, 0.03)
        f = lambda: cv2.calcOpticalFlowPyrLK(a, b, p, None, winSize=(win, win), maxLevel=lev, criteria=crit)
        q, stt, _ = f()
        crit2 = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 10, 0.03)
        f2 = lambda: cv2.calcOpticalFlowPyrLK(a, b, p, None, winSize=(win, win), maxLevel=lev, criteria=crit2)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, q, None, winSize=(win, win), maxLevel=lev, criteria=crit)
        fb = np.linalg.norm(pb - p, axis=2).ravel()[stt.ravel() == 1] / s
        print('s %.2f win %d lev %d: %.3f ms (10it %.3f) n=%d ok %.2f fb<0.6 %.2f' % (s, win, lev, T(f), T(f2), len(p), stt.mean(), (fb < 0.6).mean()))
pts = np.random.default_rng(0).uniform([100, 100], [748, 700], (250, 2))
c = rect.cams[0]
src = pts.reshape(-1, 1, 2)
print('fisheye.undistortPoints 250: %.3f ms' % T(lambda: cv2.fisheye.undistortPoints(src, c.K, c.D)))
print('fisheye.projectPoints 250: %.3f ms' % T(lambda: c.project(np.column_stack([pts / 800, np.ones(250)]))))
