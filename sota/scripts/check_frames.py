#!/usr/bin/env python3
"""check_frames.py <gt.txt> <est.txt> [...]: numeric frame check of an estimate against VIODE GT (T_world_imu, z-up).

For each estimate: associate stamps (|dt| < 20 ms), SE(3)-align positions (Kabsch/Umeyama, no scale), then
  * body_res_deg  : angle of the chordal mean of R_gt_k^T R_align R_est_k. ~0 => the estimate's body frame IS the IMU
                    frame (a camera-frame output would give ~120 deg here: VIODE R_imu_cam0 is a 120-deg permutation;
                    cam-IMU translation is 0, so only rotation can tell the frames apart);
  * body_res_spread_deg : median deviation of the per-pose residual from that mean (attitude error);
  * tilt_deg      : angle between the alignment rotation's z axis and z (0 => estimate world is gravity-aligned z-up,
                    i.e. posyaw (4-DoF) alignment is valid);
  * yaw_deg, ate_se3_m.
Pure numpy; prints one line per estimate."""
import sys
import numpy as np


def load(p):
    a = np.loadtxt(p, comments='#')
    return a[np.argsort(a[:, 0])]


def q2R(q):  # xyzw
    x, y, z, w = (q / np.linalg.norm(q, axis=1, keepdims=True)).T
    return np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                     2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                     2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], 1).reshape(-1, 3, 3)


def ang(R):
    return np.degrees(np.arccos(np.clip((np.trace(R, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))


def proj_so3(M):
    U, _, Vt = np.linalg.svd(M)
    return U @ np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))]) @ Vt


def main():
    gt = load(sys.argv[1])
    for p in sys.argv[2:]:
        try:
            est = load(p)
        except Exception as e:  # noqa
            print('%s: unreadable (%s)' % (p, e)); continue
        if est.ndim != 2 or len(est) < 10:
            print('%s: too few poses' % p); continue
        i = np.clip(np.searchsorted(gt[:, 0], est[:, 0]), 1, len(gt) - 1)
        j = np.where(np.abs(gt[i - 1, 0] - est[:, 0]) < np.abs(gt[i, 0] - est[:, 0]), i - 1, i)
        ok = np.abs(gt[j, 0] - est[:, 0]) < 0.02
        g, e = gt[j[ok]], est[ok]
        pg, pe = g[:, 1:4], e[:, 1:4]
        mg, me = pg.mean(0), pe.mean(0)
        Ra = proj_so3((pg - mg).T @ (pe - me))           # p_gt ~ Ra p_est + t
        ta = mg - Ra @ me
        ate = np.sqrt(np.mean(np.sum((pg - (pe @ Ra.T + ta)) ** 2, 1)))
        Rg, Re = q2R(g[:, 4:8]), q2R(e[:, 4:8])
        res = np.transpose(Rg, (0, 2, 1)) @ Ra @ Re      # R_gt^T R_a R_est  (= I if same body frame)
        Rm = proj_so3(res.sum(0))
        spread = np.median(ang(np.transpose(res, (0, 2, 1)) @ Rm))
        tilt = np.degrees(np.arccos(np.clip(Ra[2, 2], -1, 1)))
        yaw = np.degrees(np.arctan2(Ra[1, 0], Ra[0, 0]))
        print('%s: n=%d body_res_deg=%.2f body_res_spread_deg=%.2f tilt_deg=%.2f yaw_deg=%.1f ate_se3_m=%.3f' % (
            p, len(e), ang(Rm[None])[0], spread, tilt, yaw, ate))


if __name__ == '__main__':
    main()
