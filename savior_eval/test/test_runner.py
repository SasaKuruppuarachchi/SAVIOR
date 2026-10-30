"""savior-run with a fake launch command (real launch smoke-tested later)."""

import os
import sys

import yaml

import synth
from savior_eval.runner import bag_duration_s, main

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'fake_launch.py')


def _args(tmp_path, mode, n=2, extra=()):
    cfg = tmp_path / 'estimator_config.yaml'
    cfg.write_text('use_dynamic_mask: false\n')
    bag = tmp_path / 'bag'
    bag.mkdir(exist_ok=True)
    tmpl = ('%s %s --mode %s config:={config} bag:={bag} output:={output}'
            % (sys.executable, FAKE, mode))
    return ['--bag', str(bag), '--config', str(cfg), '-n', str(n),
            '--results-root', str(tmp_path / 'results'), '--dataset', 'ds',
            '--seq', 'seq', '--method', 'm_' + mode, '--cmd-template', tmpl,
            '--cooldown', '0', '--min-poses', '10'] + list(extra)


def _info(tmp_path, mode, i):
    d = tmp_path / 'results' / 'ds' / 'seq' / ('m_' + mode) / ('run_%02d' % i)
    return d, yaml.safe_load(open(str(d / 'run_info.yaml')))


def test_runner_ok_layout_and_eval(tmp_path):
    gt = synth.straight_line(length=4.9, step=0.1, dt=0.1)
    gfn = synth.write(str(tmp_path / 'gt.txt'), gt)
    assert main(_args(tmp_path, 'ok', n=3, extra=['--gt', gfn,
                                                   '--align', 'se3'])) == 0
    for i in range(3):
        d, info = _info(tmp_path, 'ok', i)
        assert info['status'] == 'ok' and info['end_reason'] == 'exited'
        assert info['n_poses'] == 50
        assert (d / 'stamped_traj_estimate.txt').is_file()
        assert (d / 'config' / 'estimator_config.yaml').is_file()
        assert 'output:=' + str(d / 'stamped_traj_estimate.txt') in \
            ' '.join(info['cmd'])
    method_dir = tmp_path / 'results' / 'ds' / 'seq' / 'm_ok'
    s = yaml.safe_load(open(str(method_dir / 'eval' / 'eval_summary.yaml')))
    assert s['n_success'] == 3
    assert s['ate']['trans_m']['max'] < 1e-9
    # skip-existing
    assert main(_args(tmp_path, 'ok', n=3, extra=['--skip-existing'])) == 0
    rs = yaml.safe_load(open(str(method_dir / 'runs_summary.yaml')))
    assert all(r['status'] == 'skipped' for r in rs['runs'])


def test_runner_timeout_sigint(tmp_path):
    assert main(_args(tmp_path, 'hang', n=1,
                      extra=['--timeout', '2', '--sigint-timeout', '5'])) == 3
    _, info = _info(tmp_path, 'hang', 0)
    assert info['end_reason'] == 'timeout' and info['status'] == 'timeout'
    assert info['shutdown'] == 'SIGINT'
    assert info['wall_time_s'] < 10


def test_runner_done_pattern(tmp_path):
    rc = main(_args(tmp_path, 'pattern', n=1, extra=[
        '--done-pattern', r'\[ros2-\d+\]: process has finished cleanly',
        '--done-grace', '0.5', '--timeout', '30']))
    assert rc == 0
    _, info = _info(tmp_path, 'pattern', 0)
    assert info['end_reason'] == 'done_pattern'
    assert info['status'] == 'ok' and info['n_poses'] == 50


def test_runner_no_output(tmp_path):
    assert main(_args(tmp_path, 'nooutput', n=1)) == 3
    _, info = _info(tmp_path, 'nooutput', 0)
    assert info['status'] == 'no_output' and info['returncode'] == 1


def test_bag_duration(tmp_path):
    (tmp_path / 'metadata.yaml').write_text(yaml.safe_dump(
        {'rosbag2_bagfile_information': {'duration': {
            'nanoseconds': 123500000000}}}))
    assert abs(bag_duration_s(str(tmp_path)) - 123.5) < 1e-9
    assert bag_duration_s(str(tmp_path / 'nope')) is None
