"""Synthetic trajectories for the tests (TUM arrays [t x y z qx qy qz qw])."""

import os

import numpy as np

from savior_eval.third_party.rpg_trajectory_evaluation import \
    transformations as tf
from savior_eval.tum_io import write_tum


def rot_to_quat(R):
    T = np.eye(4)
    T[:3, :3] = R
    return tf.quaternion_from_matrix(T)


def quat_to_rot(q):
    return tf.quaternion_matrix(q)[:3, :3]


def rot_xyz(roll, pitch, yaw):
    return tf.euler_matrix(roll, pitch, yaw, 'sxyz')[:3, :3]


def rz(yaw):
    return rot_xyz(0.0, 0.0, yaw)


def loop_trajectory(n=800, dt=0.05, t0=1000.0, seed=0):
    """Smooth 3D loop (~ 60 m) with heading-following yaw and small
    roll/pitch oscillation."""
    t = t0 + dt * np.arange(n)
    s = np.linspace(0, 2 * np.pi, n)
    p = np.stack([10 * np.cos(s), 6 * np.sin(2 * s),
                  1.0 + 0.5 * np.sin(3 * s)], axis=1)
    v = np.gradient(p, axis=0)
    yaw = np.arctan2(v[:, 1], v[:, 0])
    out = np.zeros((n, 8))
    out[:, 0] = t
    out[:, 1:4] = p
    for i in range(n):
        R = rot_xyz(0.05 * np.sin(5 * s[i]), 0.03 * np.cos(4 * s[i]), yaw[i])
        out[i, 4:8] = rot_to_quat(R)
    return out


def straight_line(length=100.0, step=0.1, dt=0.1, t0=0.0):
    n = int(round(length / step)) + 1
    out = np.zeros((n, 8))
    out[:, 0] = t0 + dt * np.arange(n)
    out[:, 1] = step * np.arange(n)
    out[:, 7] = 1.0
    return out


def transform(traj, R=np.eye(3), t=np.zeros(3), s=1.0):
    """Return est such that gt = s * R * est + t (rpg convention), i.e.
    est = R^T (gt - t) / s, R_est = R^T R_gt."""
    out = traj.copy()
    out[:, 1:4] = ((traj[:, 1:4] - t) @ R) / s
    for i in range(traj.shape[0]):
        out[i, 4:8] = rot_to_quat(R.T @ quat_to_rot(traj[i, 4:8]))
    return out


def add_noise(traj, sigma_p=0.02, sigma_r=0.005, seed=1):
    rng = np.random.default_rng(seed)
    out = traj.copy()
    out[:, 1:4] += rng.normal(0, sigma_p, size=(traj.shape[0], 3))
    for i in range(traj.shape[0]):
        w = rng.normal(0, sigma_r, size=3)
        dR = rot_xyz(*w)
        out[i, 4:8] = rot_to_quat(quat_to_rot(traj[i, 4:8]) @ dR)
    return out


def drift(traj, k_per_m=0.0, yaw_rate_per_m=0.0, seed=2):
    """Accumulated drift along the path: scale drift k and yaw drift per
    travelled metre applied to the *increments* (like an odometry)."""
    p = traj[:, 1:4]
    out = traj.copy()
    pos = p[0].copy()
    yaw = 0.0
    dist = 0.0
    for i in range(1, traj.shape[0]):
        d = p[i] - p[i - 1]
        step = np.linalg.norm(d)
        dist += step
        yaw = yaw_rate_per_m * dist
        pos = pos + rz(yaw) @ d * (1.0 + k_per_m)
        out[i, 1:4] = pos
        out[i, 4:8] = rot_to_quat(rz(yaw) @ quat_to_rot(traj[i, 4:8]))
    return out


def write(path, traj, header=True):
    if header:
        write_tum(path, traj)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.savetxt(path, traj, fmt='%.17g')
    return path
