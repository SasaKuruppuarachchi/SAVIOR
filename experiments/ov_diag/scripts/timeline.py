#!/usr/bin/env python3
"""timeline.py : per-run error decomposition vs GT (warehouse t1 only).

For a TUM estimate (T_world_imu) and the 200 Hz GT:
  * init: first-pose time (s after bag start), first-pose tilt error, speed of est/GT over the first 0.5 s;
  * posyaw-aligned (full trajectory, Umeyama 4-DoF as in savior-eval) error timeline: |dp|, horizontal, vertical, yaw, tilt;
  * init-anchored (4-DoF aligned on the first 1 s of estimates) drift timeline;
  * scale: est vs GT path length over sliding 5 s windows; overall scale (sim3 fit) ;
  * jumps: max per-frame step in position error (aligned) > 5 cm.
Writes a JSON summary per run and a compressed npz timeline.
usage: timeline.py out.json run_dir1 [run_dir2 ...]   (seq inferred from path; GT data/warehouse/gt/<seq>.txt)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

T0 = 1700000000.0
GTD = Path('/home/sasa/workspace/savior_ws/data/warehouse/gt')


def load_tum(p):
    a = np.loadtxt(p, comments='#')
    return a[:, 0], a[:, 1:4], a[:, 4:8]  # t, p, q(xyzw)


def q2R(q):
    x, y, z, w = q.T
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - z * w); R[:, 0, 2] = 2 * (x * z + y * w)
    R[:, 1, 0] = 2 * (x * y + z * w); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - x * w)
    R[:, 2, 0] = 2 * (x * z - y * w); R[:, 2, 1] = 2 * (y * z + x * w); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def yaw_of(R):
    return np.arctan2(R[:, 1, 0], R[:, 0, 0])


def tilt_err(Re, Rg):
    # angle between body z axes expressed in world (both worlds gravity-aligned): roll/pitch error, yaw-independent
    ze, zg = Re[:, :, 2], Rg[:, :, 2]
    # use gravity direction in body frame: Rᵀ e3
    ge = Re[:, 2, :]; gg = Rg[:, 2, :]
    c = np.clip(np.sum(ge * gg, 1), -1, 1)
    return np.degrees(np.arccos(c))


def align_posyaw(pe, pg):
    mu_e, mu_g = pe.mean(0), pg.mean(0)
    A, B = pe - mu_e, pg - mu_g
    H = A[:, :2].T @ B[:, :2]
    # yaw-only Umeyama: maximise sum of rotated dot products
    th = np.arctan2(H[0, 1] - H[1, 0], H[0, 0] + H[1, 1])
    R = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    t = mu_g - R @ mu_e
    return R, t, th


def analyse(run):
    run = Path(run)
    seq = re.search(r'((?:aisles|hall|dock)_t1_L\d)', str(run)).group(1)
    te, pe, qe = load_tum(run / 'stamped_traj_estimate.txt')
    tg, pg, qg = load_tum(GTD / f'{seq}.txt')
    idx = np.clip(np.searchsorted(tg, te), 1, len(tg) - 1)
    idx = np.where(np.abs(tg[idx - 1] - te) < np.abs(tg[idx] - te), idx - 1, idx)
    ok = np.abs(tg[idx] - te) < 0.02
    te, pe, qe, idx = te[ok], pe[ok], qe[ok], idx[ok]
    pgm, Rg = pg[idx], q2R(qg[idx])
    Re = q2R(qe)
    out = dict(run=str(run), seq=seq, n=int(len(te)), t_first=float(te[0] - T0), t_last=float(te[-1] - T0))
    # full posyaw alignment
    R, t, th = align_posyaw(pe, pgm)
    pa = pe @ R.T + t
    Ra = np.einsum('ij,njk->nik', R, Re)
    d = pa - pgm
    dyaw = np.degrees(np.angle(np.exp(1j * (yaw_of(Ra) - yaw_of(Rg)))))
    tilt = tilt_err(Re, Rg)
    out['ate'] = float(np.sqrt(np.mean(np.sum(d ** 2, 1))))
    out['ate_h'] = float(np.sqrt(np.mean(np.sum(d[:, :2] ** 2, 1))))
    out['ate_v'] = float(np.sqrt(np.mean(d[:, 2] ** 2)))
    # rotation ATE (deg), posyaw-aligned
    Rrel = np.einsum('nji,njk->nik', Rg, Ra)
    ang = np.degrees(np.arccos(np.clip((np.trace(Rrel, axis1=1, axis2=2) - 1) / 2, -1, 1)))
    out['ate_rot'] = float(np.sqrt(np.mean(ang ** 2)))
    out['yaw_rmse'] = float(np.sqrt(np.mean(dyaw ** 2)))
    out['tilt_rmse'] = float(np.sqrt(np.mean(tilt ** 2)))
    out['tilt_first'] = float(tilt[0])
    out['tilt_max'] = float(tilt.max())
    # init-anchored (first 1 s of estimates)
    m = te < te[0] + 1.0
    R1, t1, _ = align_posyaw(pe[m], pgm[m])
    p1 = pe @ R1.T + t1
    d1 = p1 - pgm
    Ra1 = np.einsum('ij,njk->nik', R1, Re)
    dyaw1 = np.degrees(np.angle(np.exp(1j * (yaw_of(Ra1) - yaw_of(Rg)))))
    out['drift_end'] = float(np.linalg.norm(d1[-1])); out['drift_end_v'] = float(d1[-1, 2])
    out['yawdrift_end'] = float(dyaw1[-1])
    # path-length scale: est / GT over the whole trajectory and per 10 s windows
    se = np.linalg.norm(np.diff(pe, axis=0), axis=1); sg = np.linalg.norm(np.diff(pgm, axis=0), axis=1)
    out['scale_path'] = float(se.sum() / sg.sum())
    # sim3 scale (umeyama 7dof)
    mu_e, mu_g = pe.mean(0), pgm.mean(0); A, B = pe - mu_e, pgm - mu_g
    U, S, Vt = np.linalg.svd(B.T @ A / len(A)); D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0: D[2, 2] = -1
    out['scale_sim3'] = float(np.trace(np.diag(S) @ D) / (np.sum(A ** 2) / len(A)))
    # speed over first 0.5 s after the first estimate
    m5 = te < te[0] + 0.5
    if m5.sum() > 2:
        dt = te[m5][-1] - te[m5][0]
        out['v_first_est'] = float(np.linalg.norm(pe[m5][-1] - pe[m5][0]) / dt)
        out['v_first_gt'] = float(np.linalg.norm(pgm[m5][-1] - pgm[m5][0]) / dt)
    # displacement at first pose vs GT since t=2.6 (static init state time) -- for the take-off phase
    step = np.linalg.norm(np.diff(d, axis=0), axis=1)
    out['max_err_step'] = float(step.max()); out['n_jumps5cm'] = int((step > 0.05).sum())
    tl = dict(t=te - T0, err=np.linalg.norm(d, axis=1), err_h=np.linalg.norm(d[:, :2], axis=1), err_v=d[:, 2], yaw=dyaw,
              tilt=tilt, drift=np.linalg.norm(d1, axis=1), drift_v=d1[:, 2], yawdrift=dyaw1, rot=ang)
    NPZ.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(NPZ / ('__'.join(run.parts[-3:]) + '.npz'), **tl)
    return out


if __name__ == '__main__':
    NPZ = Path(sys.argv[1]).with_suffix('')
    res = []
    for r in sys.argv[2:]:
        try:
            res.append(analyse(r))
        except Exception as e:  # noqa
            res.append(dict(run=r, error=str(e)))
    json.dump(res, open(sys.argv[1], 'w'), indent=1)
