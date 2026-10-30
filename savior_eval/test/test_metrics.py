"""Metric correctness on synthetic trajectories with known answers."""

import os

import numpy as np
import pytest

import synth
from savior_eval import evaluation as ev


def _eval(tmp_path, gt, est, name='e', **cfg):
    cfg.setdefault('plot', False)
    gfn = synth.write(str(tmp_path / (name + '_gt.txt')), gt)
    efn = synth.write(str(tmp_path / (name + '_est.txt')), est)
    return ev.evaluate_trials([efn], gfn, str(tmp_path / name),
                              ev.EvalConfig(**cfg))


@pytest.mark.parametrize('align', ['posyaw', 'sim3', 'se3', 'none'])
def test_identical_trajectories_zero_error(tmp_path, align):
    gt = synth.loop_trajectory()
    s = _eval(tmp_path, gt, gt.copy(), align=align)
    assert s['n_success'] == 1
    t = s['trials'][0]
    assert t['n_matched'] == gt.shape[0]
    assert t['ate']['trans_m']['max'] < 1e-9
    assert t['ate']['rot_deg']['max'] < 1e-5
    assert abs(t['alignment']['scale'] - 1.0) < 1e-9
    for lk, r in s['rpe'].items():
        assert r['trans_m']['num_samples'] > 0
        assert r['trans_m']['max'] < 1e-9
        assert r['rot_deg']['max'] < 1e-5
        assert r['yaw_deg']['max'] < 1e-5


def test_default_rpe_lengths_are_rpg_percentages(tmp_path):
    gt = synth.loop_trajectory()
    s = _eval(tmp_path, gt, gt.copy())
    L = s['gt_length_m']
    expected = [np.trunc(p * L * 100) / 100 for p in (0.1, 0.2, 0.3, 0.4, 0.5)]
    np.testing.assert_allclose(s['rpe_lengths_m'], expected, atol=1e-12)


@pytest.mark.parametrize('n_aligned', [-1, 1, 50])
def test_posyaw_removes_translation_and_yaw(tmp_path, n_aligned):
    gt = synth.loop_trajectory()
    yaw, t = 0.7, np.array([3.0, -2.0, 1.5])
    est = synth.transform(gt, synth.rz(yaw), t)
    s = _eval(tmp_path, gt, est, align='posyaw', align_frames=n_aligned)
    tr = s['trials'][0]
    assert tr['ate']['trans_m']['rmse'] < 1e-9
    assert tr['ate']['rot_deg']['rmse'] < 1e-5
    np.testing.assert_allclose(tr['alignment']['rotation'], synth.rz(yaw),
                               atol=1e-9)
    np.testing.assert_allclose(tr['alignment']['translation'], t, atol=1e-9)
    # without alignment the offset is fully visible
    s0 = _eval(tmp_path, gt, est, name='none', align='none')
    assert s0['trials'][0]['ate']['trans_m']['rmse'] > 1.0


def test_posyaw_does_not_remove_roll_pitch(tmp_path):
    gt = synth.loop_trajectory()
    est = synth.transform(gt, synth.rot_xyz(0.1, 0.0, 0.0))
    s = _eval(tmp_path, gt, est, align='posyaw')
    assert s['trials'][0]['ate']['rot_deg']['rmse'] > 5.0
    s3 = _eval(tmp_path, gt, est, name='se3', align='se3')
    assert s3['trials'][0]['ate']['rot_deg']['rmse'] < 1e-5


def test_sim3_recovers_scale(tmp_path):
    gt = synth.loop_trajectory()
    R = synth.rot_xyz(0.2, -0.1, 1.1)
    t = np.array([5.0, 1.0, -2.0])
    scale = 1.7
    est = synth.transform(gt, R, t, s=scale)
    s = _eval(tmp_path, gt, est, align='sim3')
    tr = s['trials'][0]
    assert abs(tr['alignment']['scale'] - scale) < 1e-9
    np.testing.assert_allclose(tr['alignment']['rotation'], R, atol=1e-9)
    assert tr['ate']['trans_m']['rmse'] < 1e-8
    # RPE uses the sim3 scale -> zero relative error as well
    for r in s['rpe'].values():
        assert r['trans_m']['max'] < 1e-8
    # se3 cannot remove a scale error
    s2 = _eval(tmp_path, gt, est, name='se3', align='se3')
    assert s2['trials'][0]['ate']['trans_m']['rmse'] > 0.5
    assert abs(s2['trials'][0]['alignment']['scale'] - 1.0) < 1e-12


def _expected_segments(D, L):
    """Independent re-derivation of the rpg segment selection on a uniform
    straight line: closest index to d+L among i >= idx, if within 0.2 L."""
    segs = []
    for idx, d in enumerate(D):
        err = np.abs(D[idx:] - (d + L))
        j = int(np.argmin(err))
        if err[j] < 0.2 * L:
            segs.append(D[idx + j] - d)
    return np.array(segs)


@pytest.mark.parametrize('k', [0.01, 0.05])
def test_rpe_scale_drift_expected_value(tmp_path, k):
    gt = synth.straight_line(length=100.0, step=0.1)
    est = synth.drift(gt, k_per_m=k)
    lengths = [10.0, 20.0, 40.0]
    s = _eval(tmp_path, gt, est, align='se3', rpe_lengths=lengths)
    D = np.cumsum(np.r_[0, np.linalg.norm(np.diff(gt[:, 1:4], axis=0),
                                          axis=1)])
    for L in lengths:
        r = s['rpe'][ev.length_key(L)]
        segs = _expected_segments(D, L)
        assert r['trans_m']['num_samples'] == segs.size
        np.testing.assert_allclose(r['trans_m']['mean'], k * segs.mean(),
                                   rtol=1e-9)
        # the bulk of the segments is exactly L long -> median = k L
        np.testing.assert_allclose(r['trans_m']['median'], k * L, rtol=1e-9)
        np.testing.assert_allclose(r['trans_perc']['median'], 100 * k,
                                   rtol=1e-9)
        assert r['rot_deg']['max'] < 1e-5


def test_rpe_yaw_drift_expected_value(tmp_path):
    gt = synth.straight_line(length=60.0, step=0.1)
    c = np.deg2rad(0.5)       # 0.5 deg of yaw drift per metre
    est = synth.drift(gt, yaw_rate_per_m=c)
    lengths = [5.0, 10.0]
    s = _eval(tmp_path, gt, est, align='posyaw', align_frames=1,
              rpe_lengths=lengths)
    D = np.cumsum(np.r_[0, np.linalg.norm(np.diff(gt[:, 1:4], axis=0),
                                          axis=1)])
    for L in lengths:
        r = s['rpe'][ev.length_key(L)]
        segs = _expected_segments(D, L)
        np.testing.assert_allclose(r['rot_deg']['mean'],
                                   np.rad2deg(c * segs).mean(), rtol=1e-6)
        np.testing.assert_allclose(r['yaw_deg']['median'], 0.5 * L,
                                   rtol=1e-6)
        assert r['gravity_deg']['max'] < 1e-6
        np.testing.assert_allclose(r['rot_deg_per_m']['median'], 0.5,
                                   rtol=1e-6)


def test_monte_carlo_statistics(tmp_path):
    gt = synth.loop_trajectory(n=400)
    gfn = synth.write(str(tmp_path / 'gt.txt'), gt)
    files = []
    for i, sig in enumerate([0.01, 0.02, 0.03, 0.04]):
        est = synth.add_noise(gt, sigma_p=sig, sigma_r=0.002, seed=i)
        files.append(synth.write(str(tmp_path / ('est%d.txt' % i)), est))
    files.insert(2, str(tmp_path / 'missing.txt'))     # failed run
    s = ev.evaluate_trials(files, gfn, str(tmp_path / 'mc'),
                           ev.EvalConfig(align='se3', plot=False))
    assert s['n_trials'] == 5 and s['n_success'] == 4
    assert s['trials'][2]['status'] == 'missing'
    per = [t['ate']['trans_m']['rmse'] for t in s['trials']
           if t['status'] == 'ok']
    assert s['ate_per_trial']['trans_m'] == pytest.approx(per)
    a = s['ate']['trans_m']
    assert a['num_samples'] == 4
    assert a['mean'] == pytest.approx(np.mean(per))
    assert a['median'] == pytest.approx(np.median(per))
    assert a['std'] == pytest.approx(np.std(per))
    assert per == sorted(per)          # noise level ordering preserved
    # pooled RPE = concatenation of the per-trial samples (rpg MulTrajError)
    for lk, r in s['rpe'].items():
        n = sum(t['rpe'][lk]['trans_m']['num_samples'] for t in s['trials']
                if t['status'] == 'ok')
        assert r['trans_m']['num_samples'] == n
        means = [t['rpe'][lk]['trans_m']['mean'] for t in s['trials']
                 if t['status'] == 'ok']
        assert s['rpe_trial_means'][lk]['trans_m']['mean'] == \
            pytest.approx(np.mean(means))
    assert os.path.isfile(str(tmp_path / 'mc' / 'rpg' / 'saved_results' /
                              'traj_est' / 'mt_abs_err_se3_-1.yaml'))


def test_association_max_diff_and_offset(tmp_path):
    gt = synth.loop_trajectory(n=400, dt=0.05)
    est = gt[::2].copy()
    est[:, 0] += 0.015                  # 15 ms stamp offset
    s = _eval(tmp_path, gt, est, name='a', max_diff=0.01)
    assert s['trials'][0]['status'] == 'too_few_matches'
    s = _eval(tmp_path, gt, est, name='b', max_diff=0.02)
    assert s['trials'][0]['n_matched'] == est.shape[0]
    s = _eval(tmp_path, gt, est, name='c', max_diff=0.002, t_offset=0.015)
    assert s['trials'][0]['n_matched'] == est.shape[0]
    assert s['trials'][0]['ate']['trans_m']['rmse'] < 1e-9
