"""End-to-end CLI tests on synthetic files: yaml + plots + tables."""

import os
import subprocess
import sys

import numpy as np
import yaml

import synth
from savior_eval.cli import main

PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _gt(tmp_path):
    gt = synth.loop_trajectory(n=600)
    return gt, synth.write(str(tmp_path / 'gt.txt'), gt)


def _runs(tmp_path, gt, method, n, sigma, k, bad=()):
    d = tmp_path / 'results' / 'synth' / 'loop' / method
    for i in range(n):
        rd = d / ('run_%02d' % i)
        rd.mkdir(parents=True)
        if i in bad:
            if i % 2:
                (rd / 'stamped_traj_estimate.txt').write_text('garbage\n')
            continue
        est = synth.drift(synth.add_noise(gt, sigma, 0.002, seed=10 * i + 1),
                          k_per_m=k, yaw_rate_per_m=np.deg2rad(0.05 * k * 100))
        est = synth.transform(est, synth.rz(0.3), np.array([1.0, -1.0, 0.0]))
        synth.write(str(rd / 'stamped_traj_estimate.txt'), est[::2])
    return str(d)


def test_single(tmp_path):
    gt, gfn = _gt(tmp_path)
    est = synth.transform(synth.add_noise(gt, 0.02, 0.003), synth.rz(-1.0))
    efn = synth.write(str(tmp_path / 'est.txt'), est, header=False)
    out = str(tmp_path / 'single')
    assert main(['single', '--est', efn, '--gt', gfn, '--out', out,
                 '--plot-format', 'png']) == 0
    s = yaml.safe_load(open(os.path.join(out, 'eval_summary.yaml')))
    assert s['n_success'] == 1 and s['config']['align'] == 'posyaw'
    assert 0.01 < s['ate']['trans_m']['mean'] < 0.06
    assert len(s['rpe_lengths_m']) == 5
    plots = os.listdir(os.path.join(out, 'plots'))
    for p in ['trajectory_top_posyaw_-1.png', 'trajectory_side_posyaw_-1.png',
              'translation_error_posyaw_-1.png', 'rotation_error_posyaw_-1.png',
              'rel_translation_error.png', 'rel_yaw_error.png',
              'trajectories_top_all_runs.png']:
        assert p in plots
    rs = os.path.join(out, 'rpg', 'saved_results', 'traj_est')
    assert os.path.isfile(os.path.join(rs, 'absolute_err_statistics_posyaw_-1'
                                           '.yaml'))
    assert os.path.isfile(os.path.join(out, 'summary.md'))
    assert os.path.isfile(os.path.join(out, 'samples.npz'))


def test_single_explicit_lengths_module_entry(tmp_path):
    gt, gfn = _gt(tmp_path)
    efn = synth.write(str(tmp_path / 'est.txt'), synth.add_noise(gt))
    out = str(tmp_path / 'o')
    env = dict(os.environ, PYTHONPATH=PKG_ROOT + os.pathsep +
               os.environ.get('PYTHONPATH', ''))
    r = subprocess.run([sys.executable, '-m', 'savior_eval', 'single',
                        '--est', efn, '--gt', gfn, '--out', out,
                        '--rpe-lengths', '3', '28', '--align', 'se3',
                        '--no-plot'], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    s = yaml.safe_load(open(os.path.join(out, 'eval_summary.yaml')))
    assert s['rpe_lengths_m'] == [3.0, 28.0]
    assert set(s['rpe']) == {'3', '28'}
    assert not os.path.isdir(os.path.join(out, 'plots'))


def test_multi_and_compare(tmp_path):
    gt, gfn = _gt(tmp_path)
    ov = _runs(tmp_path, gt, 'openvins', 5, 0.03, 0.02, bad=(1, 2))
    _runs(tmp_path, gt, 'savior_full', 4, 0.01, 0.005)

    assert main(['multi', '--runs', ov, '--gt', gfn, '--no-plot']) == 0
    s = yaml.safe_load(open(os.path.join(ov, 'eval', 'eval_summary.yaml')))
    assert s['n_trials'] == 5 and s['n_success'] == 3
    st = {t['name']: t['status'] for t in s['trials']}
    assert st == {'run_00': 'ok', 'run_01': 'empty', 'run_02': 'missing',
                  'run_03': 'ok', 'run_04': 'ok'}
    assert s['ate']['trans_m']['num_samples'] == 3
    assert os.path.isfile(os.path.join(ov, 'eval', 'rpg', 'saved_results',
                                       'traj_est', 'mt_rel_err_overall.yaml'))

    out = str(tmp_path / 'cmp')
    seq_dir = os.path.dirname(ov)
    assert main(['compare', '--seq-dir', seq_dir, '--gt', gfn, '--out', out,
                 '--methods', 'openvins', 'savior_full',
                 '--labels', 'OpenVINS', 'SAVIOR', '--baseline', 'OpenVINS',
                 '--plot-format', 'png']) == 0
    for f in ['ate.md', 'ate.tex', 'rpe_loop.md', 'rpe_loop.tex',
              'compare.md', 'compare.tex', 'compare_summary.yaml']:
        assert os.path.isfile(os.path.join(out, f)), f
    tex = open(os.path.join(out, 'rpe_loop.tex')).read()
    for k in [r'\toprule', r'\midrule', r'\bottomrule', r'\cmidrule(lr)',
              r'\pm', r'\mathbf{', 'OpenVINS', 'SAVIOR']:
        assert k in tex, k
    md = open(os.path.join(out, 'compare.md')).read()
    assert '**' in md and '± ' in md and 'Change vs. OpenVINS' in md
    cs = yaml.safe_load(open(os.path.join(out, 'compare_summary.yaml')))
    seq = cs['sequences']['loop']
    ov_m, sv_m = seq['methods']['openvins'], seq['methods']['savior_full']
    assert ov_m['n_success'] == 3 and sv_m['n_success'] == 4
    assert sv_m['ate']['trans_m']['mean'] < ov_m['ate']['trans_m']['mean']
    imp = cs['improvement_vs_baseline_perc']['values']['savior_full']['loop']
    assert imp['ate_trans_m'] > 0
    # table cell == summary statistic
    v = '%.3f' % sv_m['ate']['trans_m']['mean']
    ate_md = open(os.path.join(out, 'ate.md')).read()
    assert '**%s**' % v in ate_md
    plots = os.listdir(os.path.join(out, 'plots'))
    for p in ['loop_rpe_trans.png', 'loop_rpe_rot.png',
              'loop_trajectory_top.png', 'all_ate_trans_rmse.png']:
        assert p in plots

    # compare can also consume existing eval outputs
    out2 = str(tmp_path / 'cmp2')
    assert main(['compare', '--method',
                 'OpenVINS=' + os.path.join(ov, 'eval'),
                 '--method', 'SAVIOR=' + os.path.join(out, 'loop',
                                                      'savior_full'),
                 '--out', out2, '--seq', 'loop', '--no-plot']) == 0
    assert open(os.path.join(out2, 'ate.md')).read() == ate_md


def test_compare_config_multi_sequence(tmp_path):
    gt, gfn = _gt(tmp_path)
    _runs(tmp_path, gt, 'openvins', 2, 0.03, 0.02)
    _runs(tmp_path, gt, 'savior_full', 2, 0.01, 0.005)
    cfg = {'results_root': str(tmp_path / 'results' / 'synth'),
           'output': str(tmp_path / 'cmp_cfg'),
           'baseline': 'openvins',
           'eval': {'align': 'se3', 'rpe_lengths': [5.0, 10.0]},
           'sequences': [{'key': 'loop', 'label': 'Loop A', 'gt': gfn},
                         {'key': 'loop_b', 'dir': 'loop', 'label': 'Loop B',
                          'gt': gfn}],
           'methods': [{'key': 'openvins', 'label': 'OpenVINS'},
                       {'key': 'savior_full', 'label': 'SAVIOR (full)'}]}
    cf = tmp_path / 'cmp.yaml'
    cf.write_text(yaml.safe_dump(cfg))
    assert main(['compare', '--config', str(cf), '--no-plot']) == 0
    out = str(tmp_path / 'cmp_cfg')
    ate = open(os.path.join(out, 'ate.tex')).read()
    assert 'Loop A' in ate and 'Loop B' in ate and 'se3' in ate
    assert os.path.isfile(os.path.join(out, 'rpe_loop_b.md'))
    s = yaml.safe_load(open(os.path.join(out, 'compare_summary.yaml')))
    assert s['sequences']['loop']['rpe_lengths_m'] == [5.0, 10.0]


def test_ported_rpg_scripts(tmp_path):
    """The ported original scripts still work on rpg-style folders."""
    from savior_eval.third_party.rpg_trajectory_evaluation import \
        analyze_trajectories, analyze_trajectory_single
    gt = synth.loop_trajectory(n=400)
    res = tmp_path / 'results'
    for alg in ['vio_a', 'vio_b']:
        for ds in ['loop']:
            d = res / 'laptop' / alg / ('laptop_%s_%s' % (alg, ds))
            d.mkdir(parents=True)
            synth.write(str(d / 'stamped_groundtruth.txt'), gt)
            for i in range(3):
                est = synth.add_noise(gt, 0.01 if alg == 'vio_a' else 0.03,
                                      0.002, seed=i)
                synth.write(str(d / ('stamped_traj_estimate%d.txt' % i)), est)
            (d / 'eval_cfg.yaml').write_text(
                'align_type: posyaw\nalign_num_frames: -1\n')
    one = res / 'laptop' / 'vio_a' / 'laptop_vio_a_loop'
    analyze_trajectory_single.main([str(one), '--mul_trials', '3', '--png'])
    assert (one / 'plots' / 'traj_est' / 'rel_translation_error_mt.png').is_file()
    assert (one / 'saved_results' / 'traj_est' /
            'mt_abs_err_posyaw_-1.yaml').is_file()
    cfg = tmp_path / 'cfg.yaml'
    cfg.write_text(yaml.safe_dump({
        'Datasets': {'loop': {'label': 'Loop'}},
        'Algorithms': {'vio_a': {'fn': 'traj_est', 'label': 'A'},
                       'vio_b': {'fn': 'traj_est', 'label': 'B'}},
        'RelDistances': [5.0, 10.0]}))
    out = tmp_path / 'out'
    out.mkdir()
    analyze_trajectories.main([str(cfg), '--results_dir', str(res),
                               '--output_dir', str(out), '--mul_trials', '3',
                               '--rmse_table', '--rmse_boxplot',
                               '--overall_odometry_error',
                               '--odometry_error_per_dataset',
                               '--plot_trajectories', '--png'])
    files = os.listdir(str(out))
    assert any(f.startswith('laptop_translation_rmse_') for f in files)
    assert 'overall_rel_trans_perc.png' in files
    assert os.path.isfile(str(out / 'laptop_loop_results' /
                              'loop_trans_rot_error.png'))
