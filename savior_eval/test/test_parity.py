"""Parity: ORIGINAL rpg_trajectory_evaluation sources vs. the py3 port.

The original (ref/rpg_trajectory_evaluation, Python 2 code) is copied to a
temporary directory and imported under Python 3. Its numerical code only
uses explicit float division (and transformations.py has
``from __future__ import division``), so Python 3 executes the same
arithmetic as Python 2 would. ``colorama`` is stubbed if missing.

Set SAVIOR_RPG_REF to point to another checkout; skipped if not present.
"""

import importlib
import os
import shutil
import sys
import types

import numpy as np
import pytest
import yaml

import synth
from savior_eval.third_party.rpg_trajectory_evaluation import \
    associate_timestamps as port_assoc
from savior_eval.third_party.rpg_trajectory_evaluation import \
    trajectory_utils as port_tu
from savior_eval.third_party.rpg_trajectory_evaluation.trajectory import \
    Trajectory as PortTrajectory
from savior_eval.third_party.rpg_trajectory_evaluation.metrics import \
    kRelMetrics

REF = os.environ.get('SAVIOR_RPG_REF', os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'ref',
    'rpg_trajectory_evaluation')))
REF_SRC = os.path.join(REF, 'src', 'rpg_trajectory_evaluation')
ORIG_MODULES = ['transformations', 'align_trajectory', 'align_utils',
                'associate_timestamps', 'compute_trajectory_errors',
                'metrics', 'multiple_traj_errors', 'results_writer',
                'trajectory', 'trajectory_loading', 'trajectory_utils']

pytestmark = pytest.mark.skipif(not os.path.isdir(REF_SRC),
                                reason='original rpg sources not found')


@pytest.fixture(scope='module')
def orig(tmp_path_factory):
    d = tmp_path_factory.mktemp('orig_rpg')
    for m in ORIG_MODULES:
        shutil.copy(os.path.join(REF_SRC, m + '.py'), str(d))
    saved = {k: sys.modules.pop(k) for k in ORIG_MODULES + ['colorama']
             if k in sys.modules}
    try:
        importlib.import_module('colorama')
    except ImportError:
        stub = types.ModuleType('colorama')
        stub.init = lambda *a, **k: None
        stub.Fore = types.SimpleNamespace(RED='', GREEN='', YELLOW='',
                                          MAGENTA='', BLUE='', CYAN='')
        sys.modules['colorama'] = stub
    sys.path.insert(0, str(d))
    sys.dont_write_bytecode = True
    mods = types.SimpleNamespace(**{m: importlib.import_module(m)
                                    for m in ORIG_MODULES})
    yield mods
    sys.path.remove(str(d))
    for m in ORIG_MODULES + ['colorama']:
        sys.modules.pop(m, None)
    sys.modules.update(saved)


def _make_dir(path, gt, est, align, n_frames=-1):
    os.makedirs(path)
    synth.write(os.path.join(path, 'stamped_groundtruth.txt'), gt)
    synth.write(os.path.join(path, 'stamped_traj_estimate.txt'), est)
    with open(os.path.join(path, 'eval_cfg.yaml'), 'w') as f:
        yaml.safe_dump({'align_type': align, 'align_num_frames': n_frames}, f)


def _run(TrajCls, path, dists=None):
    t = TrajCls(path, preset_boxplot_distances=dists or [])
    t.compute_absolute_error()
    t.compute_relative_errors()
    return t


def _compare(t_o, t_p):
    assert t_o.preset_boxplot_distances == t_p.preset_boxplot_distances
    np.testing.assert_array_equal(t_o.p_es, t_p.p_es)
    np.testing.assert_array_equal(t_o.p_gt, t_p.p_gt)
    assert t_o.scale == pytest.approx(t_p.scale, rel=1e-13, abs=1e-13)
    np.testing.assert_allclose(t_o.rot, t_p.rot, rtol=0, atol=1e-13)
    np.testing.assert_allclose(t_o.trans, t_p.trans, rtol=0, atol=1e-11)
    for k in ['abs_e_trans', 'abs_e_rot', 'abs_e_scale_perc', 'abs_e_ypr']:
        np.testing.assert_allclose(t_o.abs_errors[k], t_p.abs_errors[k],
                                   rtol=1e-12, atol=1e-12)
    for k in ['abs_e_trans_stats', 'abs_e_rot_stats', 'abs_e_scale_stats']:
        for s in t_o.abs_errors[k]:
            assert t_o.abs_errors[k][s] == pytest.approx(
                t_p.abs_errors[k][s], rel=1e-12, abs=1e-12)
    assert sorted(t_o.rel_errors) == sorted(t_p.rel_errors)
    for d in t_o.rel_errors:
        for m in kRelMetrics:
            a, b = t_o.rel_errors[d][m], t_p.rel_errors[d][m]
            assert a.shape == b.shape and a.size > 0
            np.testing.assert_allclose(a, b, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize('align,n_frames', [('posyaw', -1), ('posyaw', 1),
                                            ('sim3', -1), ('se3', -1),
                                            ('se3', 1), ('none', -1)])
def test_trajectory_parity_synthetic(orig, tmp_path, align, n_frames):
    gt = synth.loop_trajectory(n=500)
    est = synth.drift(synth.add_noise(gt, 0.03, 0.004, seed=3),
                      k_per_m=0.01, yaw_rate_per_m=np.deg2rad(0.2))
    est = synth.transform(est, synth.rot_xyz(0.02, -0.01, 0.6),
                          np.array([1.0, 2.0, 0.3]), s=1.2)
    est = est[::2]
    est[:, 0] += 0.004      # imperfect stamps
    po, pp = str(tmp_path / 'o'), str(tmp_path / 'p')
    _make_dir(po, gt, est, align, n_frames)
    _make_dir(pp, gt, est, align, n_frames)
    _compare(_run(orig.trajectory.Trajectory, po),
             _run(PortTrajectory, pp))


def test_associate_parity(orig):
    rng = np.random.default_rng(0)
    for trial in range(20):
        a = np.sort(rng.uniform(0, 20, size=rng.integers(5, 300)))
        b = np.sort(rng.uniform(0, 20, size=rng.integers(5, 300)))
        if trial % 3 == 0:   # exact duplicates / ties
            b[:len(b) // 2] = np.round(b[:len(b) // 2], 1)
            a[:len(a) // 2] = np.round(a[:len(a) // 2], 1)
        if trial % 4 == 0:   # unsorted input
            rng.shuffle(a)
        off = [0.0, 0.013, -0.2][trial % 3]
        md = [0.02, 0.1, 0.5][trial % 3]
        ref = orig.associate_timestamps.associate(list(a), list(b), off, md)
        assert port_assoc.associate_reference(list(a), list(b), off, md) == ref
        assert port_assoc.associate(list(a), list(b), off, md) == ref


def test_comparison_indices_parity(orig):
    rng = np.random.default_rng(1)
    f = orig.trajectory_utils.compute_comparison_indices_length
    for trial in range(30):
        n = int(rng.integers(2, 400))
        steps = rng.exponential(0.1, size=n - 1)
        steps[rng.random(n - 1) < 0.2] = 0.0          # stand-still plateaus
        if trial % 5 == 0:
            steps[rng.integers(0, n - 1)] = 5.0       # gap
        D = np.concatenate(([0], np.cumsum(steps)))
        if trial % 7 == 0:
            D = rng.uniform(0, 10, size=n)            # non-monotone
        for L in [0.0, 0.5, 2.0, 0.37 * D.max() + 1e-3]:
            mdd = 0.2 * L if L > 0 else 0.05
            ref = f(D, L, mdd)
            assert port_tu.compute_comparison_indices_length_reference(
                D, L, mdd) == ref
            assert port_tu.compute_comparison_indices_length(D, L, mdd) == ref


EUROC = os.path.join(REF, 'results', 'euroc_mono_stereo', 'laptop')


@pytest.mark.skipif(not os.path.isdir(EUROC), reason='no EuRoC examples')
@pytest.mark.parametrize('case', ['vio_mono/laptop_vio_mono_MH_01',
                                  'vio_stereo/laptop_vio_stereo_V2_01'])
def test_trajectory_parity_euroc(orig, tmp_path, case):
    """Real EuRoC results shipped with rpg (posyaw, all frames).

    The original O(N*M) association is intractable on 36k GT poses, so the
    match file is precomputed (with the port, whose equality to the original
    association is tested above) and loaded by both implementations; the
    estimate is decimated x3 to keep the original O(N^2) segment search
    fast."""
    src = os.path.join(EUROC, case)
    est = np.loadtxt(os.path.join(src, 'stamped_traj_estimate.txt'))[::3]
    gt = np.loadtxt(os.path.join(src, 'stamped_groundtruth.txt'))
    matches = port_assoc.associate(list(est[:, 0]), list(gt[:, 0]), 0.0, 0.02)
    trajs = []
    for name, cls in [('o', orig.trajectory.Trajectory), ('p', PortTrajectory)]:
        d = str(tmp_path / name)
        os.makedirs(d)
        shutil.copy(os.path.join(src, 'eval_cfg.yaml'), d)
        shutil.copy(os.path.join(src, 'stamped_groundtruth.txt'), d)
        np.savetxt(os.path.join(d, 'stamped_traj_estimate.txt'), est,
                   fmt='%.18e')
        md = os.path.join(d, 'saved_results', 'traj_est')
        os.makedirs(md)
        np.savetxt(os.path.join(md, 'stamped_est_gt_matches.txt'),
                   np.array(matches, dtype=int), fmt='%d')
        trajs.append(_run(cls, d))
    assert trajs[0].align_type == 'posyaw'
    _compare(*trajs)
    # sanity: plausible VIO numbers (m, deg)
    assert 0.01 < trajs[1].abs_errors['abs_e_trans_stats']['rmse'] < 1.0
