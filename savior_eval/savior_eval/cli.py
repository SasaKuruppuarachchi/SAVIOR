"""``savior-eval``: trajectory evaluation CLI (rpg_trajectory_evaluation port).

  savior-eval single  --est EST.txt --gt GT.txt --out DIR [options]
  savior-eval multi   --runs DIR_WITH_run_XX --gt GT.txt [--out DIR] [options]
  savior-eval compare --method LABEL=PATH ... --gt GT.txt --out DIR [options]
  savior-eval compare --seq-dir results/<dataset>/<seq> --gt GT.txt --out DIR
  savior-eval compare --config compare.yaml [--out DIR]
  savior-eval runstats --runs results/<dataset>/<seq>/<method> [--out FILE.md]
"""

import argparse
import os
import sys

from . import evaluation as ev


def _add_eval_args(p):
    g = p.add_argument_group('evaluation (rpg semantics)')
    g.add_argument('--align', default='posyaw', choices=ev.ALIGN_TYPES,
                   help='alignment: posyaw (4-DoF, VIO default), sim3, se3, '
                        'none (default: %(default)s)')
    g.add_argument('--align-frames', type=int, default=-1,
                   help='number of first frames used for alignment, -1 = all '
                        '(default: %(default)s)')
    g.add_argument('--max-diff', type=float, default=0.02,
                   help='max |t_est - t_gt| [s] for timestamp association '
                        '(rpg default: %(default)s)')
    g.add_argument('--t-offset', type=float, default=0.0,
                   help='time offset [s] added to GT stamps before '
                        'association (default: %(default)s)')
    x = g.add_mutually_exclusive_group()
    x.add_argument('--rpe-lengths', type=float, nargs='+', metavar='M',
                   help='explicit RPE sub-trajectory lengths in metres')
    x.add_argument('--rpe-perc', type=float, nargs='+', metavar='PCT',
                   help='RPE lengths as %% of the GT length (default: rpg '
                        '10 20 30 40 50)')
    g.add_argument('--start-time', type=float, default=None,
                   help='only evaluate GT stamps >= this [s]')
    g.add_argument('--end-time', type=float, default=None,
                   help='only evaluate GT stamps <= this [s]')
    g.add_argument('--time-unit', default='auto', choices=['auto', 's', 'ns'])
    g.add_argument('--min-matches', type=int, default=10,
                   help='runs with fewer associated poses count as failed')
    o = p.add_argument_group('output')
    o.add_argument('--no-plot', action='store_true')
    o.add_argument('--plot-format', default='pdf', choices=['pdf', 'png',
                                                            'svg'])
    o.add_argument('-v', '--verbose', action='store_true',
                   help='show the rpg log (otherwise in rpg_log.txt)')


def _cfg(a):
    return ev.EvalConfig(align=a.align, align_frames=a.align_frames,
                         max_diff=a.max_diff, t_offset=a.t_offset,
                         rpe_lengths=a.rpe_lengths, rpe_perc=a.rpe_perc,
                         start_time=a.start_time, end_time=a.end_time,
                         time_unit=a.time_unit, min_matches=a.min_matches,
                         plot=not a.no_plot, plot_format=a.plot_format,
                         verbose=a.verbose)


def _print_summary(out_dir):
    with open(os.path.join(out_dir, 'summary.md')) as f:
        print(f.read())
    print('[savior-eval] results in %s' % os.path.abspath(out_dir))


def cmd_single(a):
    ev.evaluate_trials([a.est], a.gt, a.out, _cfg(a), label=a.label)
    _print_summary(a.out)
    return 0


def cmd_multi(a):
    out = a.out or os.path.join(a.runs, 'eval')
    s = ev.evaluate_runs_dir(a.runs, a.gt, out, _cfg(a), a.pattern,
                             a.est_name, label=a.label)
    _print_summary(out)
    return 0 if s['n_success'] > 0 else 2


def _parse_method(spec):
    if '=' in spec:
        label, path = spec.split('=', 1)
    else:
        path = spec
        label = os.path.basename(os.path.normpath(spec))
    key = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in label)
    return key, label, path


def cmd_compare(a):
    from . import compare as cmp
    cfg = _cfg(a)
    baseline = a.baseline
    if a.config:
        seqs, c = cmp.sequences_from_config(a.config)
        if c.get('eval'):
            for k, v in c['eval'].items():
                setattr(a, k, v)
            cfg = _cfg(a)
        baseline = baseline or c.get('baseline')
        out = a.out or c.get('output')
        if out and not os.path.isabs(out) and not a.out:
            out = os.path.join(os.path.dirname(os.path.abspath(a.config)), out)
    else:
        methods = [_parse_method(m) for m in (a.method or [])]
        if a.seq_dir:
            keys = a.methods or cmp.discover_methods(a.seq_dir, a.pattern)
            labels = a.labels or keys
            if len(labels) != len(keys):
                sys.exit('--labels must match --methods')
            methods += [(k, l, os.path.join(a.seq_dir, k))
                        for k, l in zip(keys, labels)]
        if not methods:
            sys.exit('give --method LABEL=PATH, --seq-dir or --config')
        seq_key = a.seq or (os.path.basename(os.path.normpath(a.seq_dir))
                            if a.seq_dir else 'sequence')
        seqs = [{'key': seq_key, 'label': a.seq_label or seq_key,
                 'gt': a.gt, 'methods': methods}]
        out = a.out
    if not out:
        sys.exit('--out is required')
    if baseline:
        # allow baseline given by label
        for s in seqs:
            for k, l, _ in s['methods']:
                if baseline == l:
                    baseline = k
    cmp.run_compare(seqs, out, cfg, stat=a.stat, baseline=baseline,
                    plot=not a.no_plot, prec=a.precision, pattern=a.pattern,
                    est_name=a.est_name)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog='savior-eval',
        description='Trajectory evaluation (Python 3 port of '
                    'rpg_trajectory_evaluation, Zhang & Scaramuzza IROS 2018). '
                    'Inputs are TUM files: timestamp tx ty tz qx qy qz qw.')
    sub = p.add_subparsers(dest='cmd')
    s = sub.add_parser('single', help='evaluate one estimate')
    s.add_argument('--est', required=True, help='estimate (TUM)')
    s.add_argument('--gt', required=True, help='groundtruth (TUM)')
    s.add_argument('--out', required=True, help='output directory')
    s.add_argument('--label', default=None)
    _add_eval_args(s)
    s.set_defaults(func=cmd_single)

    m = sub.add_parser('multi', help='Monte-Carlo statistics over run_XX dirs')
    m.add_argument('--runs', required=True,
                   help='directory containing run_XX/<est-name>')
    m.add_argument('--gt', required=True)
    m.add_argument('--out', default=None,
                   help='output directory (default: <runs>/eval)')
    m.add_argument('--pattern', default='run_*')
    m.add_argument('--est-name', default=ev.EST_FN)
    m.add_argument('--label', default=None)
    _add_eval_args(m)
    m.set_defaults(func=cmd_multi)

    c = sub.add_parser('compare', help='tabulate several methods')
    c.add_argument('--method', action='append', metavar='LABEL=PATH',
                   help='method label and path (runs dir, eval dir/summary '
                        'yaml, or TUM file); repeatable, order is kept')
    c.add_argument('--seq-dir', default=None,
                   help='results/<dataset>/<seq>: methods = sub-dirs with '
                        'run_* (or those given by --methods)')
    c.add_argument('--methods', nargs='+', default=None)
    c.add_argument('--labels', nargs='+', default=None)
    c.add_argument('--config', default=None, help='compare yaml (multi-seq)')
    c.add_argument('--gt', default=None)
    c.add_argument('--seq', default=None, help='sequence key')
    c.add_argument('--seq-label', default=None)
    c.add_argument('--out', default=None)
    c.add_argument('--baseline', default=None,
                   help='method key/label for relative improvement')
    c.add_argument('--stat', default='mean', choices=['mean', 'median',
                                                      'rmse'],
                   help='table statistic (mean is shown with ± std)')
    c.add_argument('--precision', type=int, default=3)
    c.add_argument('--pattern', default='run_*')
    c.add_argument('--est-name', default=ev.EST_FN)
    _add_eval_args(c)
    c.set_defaults(func=cmd_compare)

    from . import runstats
    runstats.add_parser(sub)
    return p


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    if not getattr(a, 'func', None):
        p.print_help()
        return 1
    return a.func(a)


if __name__ == '__main__':
    sys.exit(main())
