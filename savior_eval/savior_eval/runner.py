"""``savior-run``: run N trials of a launch file on a bag and store the
trajectories as results/<dataset>/<seq>/<method>/run_XX/stamped_traj_estimate.txt

Decoupled from ROS on purpose (no rclpy import): every trial is a
``ros2 launch <pkg> <file> config:=... bag:=... output:=...`` subprocess in its
own process group. A trial ends when

1. the launch process exits by itself (preferred: the launch file emits
   Shutdown when the bag player exits), or
2. a line of the launch output matches ``--done-pattern`` (then we wait
   ``--done-grace`` s and shut down), or
3. ``--timeout`` expires (auto: bag duration / rate * factor + margin).

Shutdown = SIGINT to the process group (like Ctrl-C, lets pose_to_file
flush), then SIGTERM, then SIGKILL.
"""

import argparse
import datetime
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

import yaml

DEFAULT_TEMPLATE = ('ros2 launch {launch_pkg} {launch_file} config:={config} '
                    'bag:={bag} output:={output}')
EST_FN = 'stamped_traj_estimate.txt'


def bag_duration_s(bag):
    """Duration of a ROS 2 bag from its metadata.yaml (None if unknown)."""
    if os.path.isdir(bag):
        meta = os.path.join(bag, 'metadata.yaml')
    elif os.path.isfile(bag):      # path to the .db3/.mcap inside the bag dir
        meta = os.path.join(os.path.dirname(bag), 'metadata.yaml')
    else:
        return None
    if not os.path.isfile(meta):
        return None
    try:
        with open(meta) as f:
            m = yaml.safe_load(f)
        return m['rosbag2_bagfile_information']['duration']['nanoseconds'] \
            * 1e-9
    except Exception:
        return None


def count_poses(path):
    if not os.path.isfile(path):
        return 0
    n = 0
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith('#'):
                n += 1
    return n


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def shutdown_group(proc, sigint_timeout=20.0, sigterm_timeout=10.0, log=None):
    """SIGINT -> SIGTERM -> SIGKILL the process group of proc (the group
    leader is proc itself: it was started with start_new_session=True)."""
    pgid = proc.pid
    for sig, tmo in [(signal.SIGINT, sigint_timeout),
                     (signal.SIGTERM, sigterm_timeout),
                     (signal.SIGKILL, 5.0)]:
        if proc.poll() is not None and not _group_alive(pgid):
            return 'exited'
        if log:
            log('sending %s to process group %d' % (sig.name, pgid))
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return 'exited'
        t0 = time.time()
        while time.time() - t0 < tmo:
            if proc.poll() is not None and not _group_alive(pgid):
                return sig.name
            time.sleep(0.2)
    return 'SIGKILL'


def run_trial(cmd, out_dir, timeout, env=None, done_pattern=None,
              done_grace=5.0, sigint_timeout=20.0, poll=0.5, echo=False):
    """Run one trial. Returns an info dict."""
    log_fn = os.path.join(out_dir, 'launch.log')
    info = {'cmd': cmd, 'log': log_fn,
            'start': datetime.datetime.now().isoformat(timespec='seconds')}
    rx = re.compile(done_pattern) if done_pattern else None
    t0 = time.time()
    end_reason = None
    with open(log_fn, 'wb') as logf:
        proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env,
                                start_new_session=True)
        info['pid'] = proc.pid
        done_at = None
        read_pos = 0
        try:
            while True:
                if proc.poll() is not None:
                    end_reason = 'exited'
                    break
                el = time.time() - t0
                if timeout and el > timeout:
                    end_reason = 'timeout'
                    break
                if rx is not None and done_at is None:
                    logf.flush()
                    with open(log_fn, 'rb') as r:
                        r.seek(read_pos)
                        chunk = r.read()
                    if chunk:
                        if echo:
                            sys.stdout.write(chunk.decode('utf-8', 'replace'))
                        # keep a tail so matches spanning chunks are found
                        text = chunk.decode('utf-8', 'replace')
                        if rx.search(text):
                            done_at = time.time()
                        read_pos += max(0, len(chunk) - 512)
                if done_at is not None and time.time() - done_at > done_grace:
                    end_reason = 'done_pattern'
                    break
                time.sleep(poll)
        except KeyboardInterrupt:
            end_reason = 'interrupted'
        if end_reason != 'exited':
            info['shutdown'] = shutdown_group(proc, sigint_timeout)
        else:
            # launch returned; make sure no orphaned children survive
            if _group_alive(proc.pid):
                info['shutdown'] = shutdown_group(proc, 5.0)
        proc.wait()
    info['end_reason'] = end_reason
    info['returncode'] = proc.returncode
    info['wall_time_s'] = round(time.time() - t0, 3)
    info['end'] = datetime.datetime.now().isoformat(timespec='seconds')
    return info


def snapshot_config(config, out_dir):
    if not config or not os.path.exists(config):
        return None
    dst = os.path.join(out_dir, 'config')
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    if os.path.isdir(config):
        shutil.copytree(config, dst, ignore=shutil.ignore_patterns(
            '*.pt', '*.engine', '*.onnx', '*.bag', '*.db3', '*.mcap'))
    else:
        os.makedirs(dst)
        shutil.copy2(config, dst)
    return dst


def build_cmd(a, output, run_dir):
    fields = dict(launch_pkg=a.launch_pkg, launch_file=a.launch_file,
                  config=os.path.abspath(a.config) if a.config else '',
                  bag=os.path.abspath(a.bag) if a.bag else '',
                  output=output, run_dir=run_dir)
    cmd = shlex.split(a.cmd_template.format(**fields))
    for la in a.launch_arg or []:
        cmd.append(la.format(**fields))
    return cmd


def main(argv=None):
    p = argparse.ArgumentParser(
        prog='savior-run',
        description='Run N trials of a ROS 2 launch file on a bag and store '
                    'results/<dataset>/<seq>/<method>/run_XX/'
                    'stamped_traj_estimate.txt')
    p.add_argument('--launch-pkg', default='savior_bringup')
    p.add_argument('--launch-file', default='baseline.launch.py')
    p.add_argument('--bag', required=True, help='ROS 2 bag (directory)')
    p.add_argument('--config', required=True,
                   help='estimator config (file or directory) -> config:=')
    p.add_argument('-n', '--trials', type=int, default=10)
    p.add_argument('--start-index', type=int, default=0)
    p.add_argument('--results-root', default='results')
    p.add_argument('--dataset', required=True)
    p.add_argument('--seq', required=True)
    p.add_argument('--method', required=True)
    p.add_argument('--launch-arg', action='append', metavar='KEY:=VALUE',
                   help='extra launch argument (repeatable); {run_dir} and '
                        '{output} are substituted')
    p.add_argument('--output-mode', choices=['file', 'dir'], default='file',
                   help='output:= gets the TUM file path (default) or the '
                        'run directory')
    p.add_argument('--cmd-template', default=DEFAULT_TEMPLATE,
                   help='command template (default: %(default)r)')
    p.add_argument('--timeout', type=float, default=None,
                   help='per-trial timeout [s]; default: bag duration / '
                        '--rate * --timeout-factor + --timeout-margin, or '
                        '3600 if the duration is unknown')
    p.add_argument('--rate', type=float, default=1.0,
                   help='bag playback rate used only for the auto timeout')
    p.add_argument('--timeout-factor', type=float, default=1.5)
    p.add_argument('--timeout-margin', type=float, default=120.0)
    p.add_argument('--done-pattern', default=None,
                   help='regex on the launch output that marks the end of '
                        'the run (e.g. the bag player finishing)')
    p.add_argument('--done-grace', type=float, default=5.0)
    p.add_argument('--sigint-timeout', type=float, default=20.0)
    p.add_argument('--cooldown', type=float, default=3.0,
                   help='pause between trials [s]')
    p.add_argument('--domain-id', type=int, default=None,
                   help='ROS_DOMAIN_ID for the trials (isolation)')
    p.add_argument('--skip-existing', action='store_true',
                   help='skip runs that already have a non-empty estimate')
    p.add_argument('--min-poses', type=int, default=10,
                   help='fewer poses in the output => run marked failed')
    p.add_argument('--gt', default=None,
                   help='if given, run savior-eval multi on the runs after')
    p.add_argument('--align', default='posyaw')
    p.add_argument('--echo', action='store_true',
                   help='echo the launch output (needs --done-pattern)')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(argv)

    method_dir = os.path.abspath(os.path.join(a.results_root, a.dataset,
                                              a.seq, a.method))
    timeout = a.timeout
    if timeout is None:
        dur = bag_duration_s(a.bag)
        timeout = 3600.0 if dur is None else \
            dur / a.rate * a.timeout_factor + a.timeout_margin
    env = os.environ.copy()
    if a.domain_id is not None:
        env['ROS_DOMAIN_ID'] = str(a.domain_id)

    def log(msg):
        print('[savior-run] ' + msg, flush=True)

    log('method dir: %s, trials %d..%d, timeout %.0f s' % (
        method_dir, a.start_index, a.start_index + a.trials - 1, timeout))
    if not a.dry_run:
        os.makedirs(method_dir, exist_ok=True)
    results = []
    interrupted = False
    for i in range(a.start_index, a.start_index + a.trials):
        run_dir = os.path.join(method_dir, 'run_%02d' % i)
        est = os.path.join(run_dir, EST_FN)
        if a.skip_existing and count_poses(est) >= a.min_poses:
            log('run_%02d exists, skipping' % i)
            results.append({'run': 'run_%02d' % i, 'status': 'skipped'})
            continue
        output = est if a.output_mode == 'file' else run_dir
        cmd = build_cmd(a, output, run_dir)
        log('run_%02d: %s' % (i, ' '.join(shlex.quote(c) for c in cmd)))
        if a.dry_run:
            continue
        os.makedirs(run_dir, exist_ok=True)
        if os.path.exists(est):
            os.remove(est)
        snapshot_config(a.config, run_dir)
        env['SAVIOR_RUN_INDEX'] = str(i)
        env['SAVIOR_RUN_DIR'] = run_dir
        info = run_trial(cmd, run_dir, timeout, env, a.done_pattern,
                         a.done_grace, a.sigint_timeout, echo=a.echo)
        n = count_poses(est)
        info.update({'run': 'run_%02d' % i, 'index': i, 'n_poses': n,
                     'bag': os.path.abspath(a.bag),
                     'config': os.path.abspath(a.config),
                     'dataset': a.dataset, 'seq': a.seq, 'method': a.method,
                     'timeout_s': timeout,
                     'domain_id': env.get('ROS_DOMAIN_ID')})
        if info['end_reason'] == 'interrupted':
            info['status'] = 'interrupted'
        elif n < a.min_poses:
            info['status'] = 'no_output'
        elif info['end_reason'] == 'timeout':
            info['status'] = 'timeout'   # output kept, but flagged
        else:
            info['status'] = 'ok'
        with open(os.path.join(run_dir, 'run_info.yaml'), 'w') as f:
            yaml.safe_dump(info, f, sort_keys=False)
        log('run_%02d: %s (%d poses, %.0f s, %s)' % (
            i, info['status'], n, info['wall_time_s'], info['end_reason']))
        results.append({k: info[k] for k in ('run', 'status', 'n_poses',
                                             'wall_time_s', 'end_reason')})
        if info['status'] == 'interrupted':
            interrupted = True
            break
        if i < a.start_index + a.trials - 1:
            time.sleep(a.cooldown)

    if not a.dry_run:
        with open(os.path.join(method_dir, 'runs_summary.yaml'), 'w') as f:
            yaml.safe_dump({'updated': datetime.datetime.now().isoformat(
                timespec='seconds'), 'runs': results}, f, sort_keys=False)
    if a.gt and not a.dry_run and not interrupted:
        from . import evaluation as ev
        log('evaluating against %s' % a.gt)
        s = ev.evaluate_runs_dir(method_dir, a.gt,
                                 os.path.join(method_dir, 'eval'),
                                 ev.EvalConfig(align=a.align),
                                 label=a.method)
        log('ATE RMSE: %s' % (s.get('ate', {}).get('trans_m')))
    n_ok = sum(1 for r in results if r.get('status') in ('ok', 'skipped'))
    return 130 if interrupted else (0 if n_ok == len(results) else 3)


if __name__ == '__main__':
    sys.exit(main())
