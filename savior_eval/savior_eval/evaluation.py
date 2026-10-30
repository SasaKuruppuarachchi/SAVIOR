"""Single / Monte-Carlo trajectory evaluation on top of the rpg port.

The heavy lifting (association, alignment, ATE, RPE, multi-trial pooling and
the standard plots) is done by the unmodified logic of
``third_party/rpg_trajectory_evaluation``. This module only

1. sanitises the TUM inputs (``tum_io``) and lays them out the way rpg
   expects (``stamped_groundtruth.txt`` + ``stamped_traj_estimate{i}.txt`` +
   ``eval_cfg.yaml`` in one folder),
2. fixes the sub-trajectory lengths once from the groundtruth so that all
   trials *and all methods* evaluated against the same groundtruth share them
   (rpg's analyze_trajectories.py does the same per dataset),
3. collects the results into one self-describing ``eval_summary.yaml``
   (+ ``samples.npz`` with the raw samples for comparison plots).
"""

import contextlib
import datetime
import glob
import io
import os
import re
import shutil

import numpy as np
import yaml

from . import __version__
from .tum_io import TumFormatError, load_tum, write_tum
from .third_party.rpg_trajectory_evaluation import associate_timestamps as associ
from .third_party.rpg_trajectory_evaluation import results_writer as rw
from .third_party.rpg_trajectory_evaluation import trajectory_utils as tu
from .third_party.rpg_trajectory_evaluation.trajectory import Trajectory

ALIGN_TYPES = ('posyaw', 'sim3', 'se3', 'none')
DEFAULT_RPE_PERC = [10.0, 20.0, 30.0, 40.0, 50.0]   # rpg default (0.1 .. 0.5)
SUMMARY_FN = 'eval_summary.yaml'
SAMPLES_FN = 'samples.npz'
EST_FN = 'stamped_traj_estimate.txt'

# rpg metric name -> (summary key, unit)
REL_METRICS = [('rel_trans', 'trans_m'), ('rel_trans_perc', 'trans_perc'),
               ('rel_rot', 'rot_deg'), ('rel_yaw', 'yaw_deg'),
               ('rel_gravity', 'gravity_deg'),
               ('rel_rot_deg_per_m', 'rot_deg_per_m')]
ABS_METRICS = [('rmse_trans', 'trans_m'), ('rmse_rot', 'rot_deg'),
               ('rmse_scale', 'scale_perc')]

DEFINITIONS = {
    'ATE': 'Absolute trajectory error after aligning the estimate to the '
           'groundtruth (alignment: see config.align). Per run: RMSE over all '
           'associated poses of the position error [m] and of the rotation '
           'error angle |log(R_est R_gt^T)| [deg]. "ate" gives statistics of '
           'these per-run RMSEs across the Monte-Carlo runs.',
    'RPE': 'rpg relative error (Zhang & Scaramuzza, IROS 2018): for every '
           'start pose, the sub-trajectory whose groundtruth travelled '
           'distance is closest to L (within 0.2 L) is compared; error of '
           'the relative pose expressed in the start frame. trans_m [m], '
           'rot_deg = full rotation angle [deg], yaw_deg/gravity_deg [deg], '
           'trans_perc = 100*trans_m/L [%], rot_deg_per_m = rot_deg/L. '
           '"rpe" pools all segments of all successful runs (rpg MulTrajError); '
           '"rpe_trial_means" gives statistics across runs of the per-run mean.',
    'stats': 'rmse, mean, median, std (population, ddof=0, as numpy/rpg), '
             'min, max, num_samples',
}


class EvalConfig(object):
    def __init__(self, align='posyaw', align_frames=-1, max_diff=0.02,
                 t_offset=0.0, rpe_lengths=None, rpe_perc=None,
                 start_time=None, end_time=None, time_unit='auto',
                 min_matches=10, plot=True, plot_format='pdf',
                 verbose=False):
        if align not in ALIGN_TYPES:
            raise ValueError('align must be one of {}'.format(ALIGN_TYPES))
        if align == 'sim3' and 0 <= align_frames < 2:
            raise ValueError('sim3 alignment needs >= 2 frames (or -1)')
        self.align = align
        self.align_frames = int(align_frames)
        self.max_diff = float(max_diff)
        self.t_offset = float(t_offset)
        self.rpe_lengths = [float(v) for v in rpe_lengths] if rpe_lengths \
            else None
        self.rpe_perc = [float(v) for v in rpe_perc] if rpe_perc else None
        if self.rpe_lengths and self.rpe_perc:
            raise ValueError('give either rpe_lengths or rpe_perc, not both')
        self.start_time = start_time
        self.end_time = end_time
        self.time_unit = time_unit
        self.min_matches = int(min_matches)
        self.plot = plot
        self.plot_format = plot_format.lstrip('.')
        self.verbose = verbose

    def as_dict(self):
        d = {'align': self.align, 'align_num_frames': self.align_frames,
             'max_diff_s': self.max_diff, 't_offset_s': self.t_offset,
             'start_time': self.start_time, 'end_time': self.end_time,
             'time_unit': self.time_unit, 'min_matches': self.min_matches}
        if self.rpe_lengths:
            d['rpe_mode'] = 'explicit_lengths'
            d['rpe_lengths_m'] = list(self.rpe_lengths)
        else:
            d['rpe_mode'] = 'percent_of_gt_length'
            d['rpe_perc'] = list(self.rpe_perc or DEFAULT_RPE_PERC)
        return d


def length_key(d):
    return '{:g}'.format(d)


def _time_window(cfg):
    lo = -float('inf') if cfg.start_time is None else float(cfg.start_time)
    hi = float('inf') if cfg.end_time is None else float(cfg.end_time)
    return lo, hi


def gt_length(gt, cfg):
    lo, hi = _time_window(cfg)
    sel = gt[(gt[:, 0] >= lo) & (gt[:, 0] <= hi)]
    if sel.shape[0] < 2:
        return 0.0
    return float(tu.get_distance_from_start(sel[:, 1:4])[-1])


def compute_rpe_lengths(gt, cfg):
    """Sub-trajectory lengths [m]: explicit, or rpg's percentage rule
    (truncate(pct * GT length, 2), GT restricted to the time window)."""
    if cfg.rpe_lengths:
        return list(cfg.rpe_lengths)
    L = gt_length(gt, cfg)
    perc = cfg.rpe_perc or DEFAULT_RPE_PERC
    lengths = [Trajectory.truncate(p / 100.0 * L, 2) for p in perc]
    if any(v <= 0 for v in lengths):
        raise ValueError('groundtruth too short (%.3f m) for RPE lengths' % L)
    return lengths


def _stats(v):
    return rw.compute_statistics(np.asarray(v, dtype=np.float64).reshape(-1))


def _clean(obj):
    """numpy -> plain python for yaml."""
    if isinstance(obj, dict):
        return {str(k) if not isinstance(k, str) else k: _clean(v)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def evaluate_trials(est_files, gt_file, out_dir, cfg=None, run_names=None,
                    label=None):
    """Evaluate one or several (Monte-Carlo) estimates against one GT.

    est_files: list of paths (None / missing files count as failed runs).
    Returns the summary dict (also written to out_dir/eval_summary.yaml).
    """
    cfg = cfg or EvalConfig()
    est_files = list(est_files)
    n = len(est_files)
    if n == 0:
        raise ValueError('no estimate files given')
    if run_names is None:
        run_names = ['run_%02d' % i for i in range(n)] if n > 1 else ['single']
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, 'rpg')
    if os.path.isdir(work):
        shutil.rmtree(work)       # never reuse rpg caches (matches/rel errors)
    os.makedirs(work)

    gt, gt_info = load_tum(gt_file, cfg.time_unit, return_info=True)
    if gt.shape[0] < 2:
        raise ValueError('groundtruth has < 2 poses: %s' % gt_file)
    write_tum(os.path.join(work, 'stamped_groundtruth.txt'), gt)
    with open(os.path.join(work, 'eval_cfg.yaml'), 'w') as f:
        yaml.safe_dump({'align_type': cfg.align,
                        'align_num_frames': cfg.align_frames}, f)
    if cfg.start_time is not None or cfg.end_time is not None:
        se = {}
        if cfg.start_time is not None:
            se['start_time_sec'] = float(cfg.start_time)
        if cfg.end_time is not None:
            se['end_time_sec'] = float(cfg.end_time)
        with open(os.path.join(work, 'start_end_time.yaml'), 'w') as f:
            yaml.safe_dump(se, f)

    lengths = compute_rpe_lengths(gt, cfg)
    lo, hi = _time_window(cfg)

    trials = []
    for i, fn in enumerate(est_files):
        suffix = '' if n == 1 else str(i)
        t = {'index': i, 'name': run_names[i],
             'est_file': os.path.abspath(fn) if fn else None}
        trials.append(t)
        if not fn or not os.path.isfile(fn):
            t['status'] = 'missing'
            continue
        try:
            est, est_info = load_tum(fn, cfg.time_unit, return_info=True)
        except TumFormatError as e:
            t['status'] = 'bad_format'
            t['error'] = str(e)
            continue
        t['n_est_poses'] = est_info['n_rows']
        if est_info['warnings']:
            t['load_warnings'] = est_info['warnings']
        if est.shape[0] == 0:
            t['status'] = 'empty'
            continue
        matches = associ.associate(est[:, 0], gt[:, 0], cfg.t_offset,
                                   cfg.max_diff)
        n_m = sum(1 for _, ig in matches if lo <= gt[ig, 0] <= hi)
        t['n_matched'] = int(n_m)
        if n_m < max(cfg.min_matches, 2):
            t['status'] = 'too_few_matches'
            continue
        write_tum(os.path.join(work, 'stamped_traj_estimate%s.txt' % suffix),
                  est)
        t['status'] = 'pending'

    # ---- rpg evaluation (port, unchanged logic) ----
    from .third_party.rpg_trajectory_evaluation.analyze_trajectory_single \
        import analyze_multiple_trials, plot_single_results
    log = io.StringIO()
    ctx = contextlib.nullcontext() if cfg.verbose else \
        contextlib.redirect_stdout(log)
    # errstate: rpg's "scale" metric divides by the distance from the origin
    # (upstream quirk, see PORTING.md) -> inf/nan when the GT starts at 0.
    with ctx, np.errstate(divide='ignore', invalid='ignore'):
        traj_list, mt = analyze_multiple_trials(
            work, 'traj_est', n, recalculate_errors=False,
            preset_boxplot_distances=list(lengths),
            compute_odometry_error=True,
            max_diff=cfg.max_diff, t_offset=cfg.t_offset,
            align_type=cfg.align, align_num_frames=cfg.align_frames)
        if mt.n_traj > 0:
            mt.saveErrors()
    with open(os.path.join(out_dir, 'rpg_log.txt'), 'w') as f:
        f.write(log.getvalue())

    samples = {}
    for idx, traj in zip(mt.success_indices, traj_list):
        t = trials[idx]
        t['status'] = 'ok'
        t['n_matched'] = int(traj.p_es.shape[0])
        t['ate'] = {'trans_m': traj.abs_errors['abs_e_trans_stats'],
                    'rot_deg': traj.abs_errors['abs_e_rot_stats'],
                    'scale_perc': traj.abs_errors['abs_e_scale_stats']}
        t['alignment'] = {'scale': float(traj.scale),
                          'rotation': np.asarray(traj.rot).tolist(),
                          'translation': np.asarray(traj.trans).tolist()}
        t['rpe'] = {}
        for d in lengths:
            e = traj.rel_errors[d]
            t['rpe'][length_key(d)] = {k: e[m + '_stats']
                                       for m, k in REL_METRICS}
        t['duration_s'] = float(traj.t_es[-1] - traj.t_es[0])
        samples['traj%d_t' % idx] = traj.t_es
        samples['traj%d_p_es_aligned' % idx] = traj.p_es_aligned
        samples['traj%d_p_gt' % idx] = traj.p_gt
        samples['traj%d_ate_trans' % idx] = traj.abs_errors['abs_e_trans']
        samples['traj%d_ate_rot' % idx] = traj.abs_errors['abs_e_rot']
    for t in trials:
        if t['status'] == 'pending':
            t['status'] = 'rpg_failed'

    summary = {
        'tool': 'savior_eval %s (rpg_trajectory_evaluation py3 port)'
                % __version__,
        'created': datetime.datetime.now().isoformat(timespec='seconds'),
        'label': label,
        'gt_file': os.path.abspath(gt_file),
        'gt_n_poses': int(gt.shape[0]),
        'gt_length_m': gt_length(gt, cfg),
        'config': cfg.as_dict(),
        'rpe_lengths_m': [float(v) for v in lengths],
        'n_trials': n,
        'n_success': int(mt.n_traj),
        'trials': trials,
        'definitions': DEFINITIONS,
    }
    if gt_info['warnings']:
        summary['gt_load_warnings'] = gt_info['warnings']
    if mt.n_traj > 0:
        summary['ate'] = {k: mt.abs_errors[m + '_stats']
                          for m, k in ABS_METRICS}
        summary['ate_per_trial'] = {k: list(mt.abs_errors[m])
                                    for m, k in ABS_METRICS}
        summary['rpe'] = {}
        summary['rpe_trial_means'] = {}
        for d in lengths:
            lk = length_key(d)
            summary['rpe'][lk] = {k: mt.rel_errors[d][m + '_stats']
                                  for m, k in REL_METRICS}
            tm = {}
            for m, k in REL_METRICS:
                per = [trials[i]['rpe'][lk][k]['mean']
                       for i in mt.success_indices
                       if trials[i]['rpe'][lk][k]['num_samples'] > 0]
                tm[k] = _stats(per)
            summary['rpe_trial_means'][lk] = tm
            for m, k in REL_METRICS:
                samples['rpe_%s_%s' % (k, lk)] = mt.rel_errors[d][m]
        summary['rpe_overall'] = {k: mt.overall_rel_errors[m]
                                  for m, k in REL_METRICS}
        for m, k in ABS_METRICS:
            samples['ate_%s_rmse' % k] = np.asarray(mt.abs_errors[m])
    summary = _clean(summary)
    np.savez_compressed(os.path.join(out_dir, SAMPLES_FN), **samples)

    with open(os.path.join(out_dir, SUMMARY_FN), 'w') as f:
        yaml.safe_dump(summary, f, sort_keys=False, default_flow_style=None,
                       width=100)

    if cfg.plot and traj_list:
        plots_dir = os.path.join(out_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        with ctx:
            plot_single_results(traj_list[0], mt, plots_dir, n,
                                fmt='.' + cfg.plot_format)
        from . import plots
        plots.plot_trials_overlay(traj_list, mt.success_indices, run_names,
                                  plots_dir, cfg.plot_format)
        summary_plots = sorted(os.listdir(plots_dir))
        summary['plots'] = summary_plots
        with open(os.path.join(out_dir, SUMMARY_FN), 'w') as f:
            yaml.safe_dump(summary, f, sort_keys=False,
                           default_flow_style=None, width=100)

    from . import tables
    with open(os.path.join(out_dir, 'summary.md'), 'w') as f:
        f.write(tables.single_summary_markdown(summary))
    return summary


_RUN_RE = re.compile(r'(\d+)$')


def discover_runs(runs_dir, pattern='run_*', est_name=EST_FN):
    """Sorted list of (run_name, est_path_or_None) under runs_dir."""
    dirs = [d for d in glob.glob(os.path.join(runs_dir, pattern))
            if os.path.isdir(d)]

    def key(d):
        m = _RUN_RE.search(os.path.basename(d))
        return (int(m.group(1)) if m else float('inf'), os.path.basename(d))
    out = []
    for d in sorted(dirs, key=key):
        p = os.path.join(d, est_name)
        out.append((os.path.basename(d), p if os.path.isfile(p) else None))
    return out


def evaluate_runs_dir(runs_dir, gt_file, out_dir=None, cfg=None,
                      pattern='run_*', est_name=EST_FN, label=None):
    runs = discover_runs(runs_dir, pattern, est_name)
    if not runs:
        raise FileNotFoundError('no %s directories in %s' % (pattern, runs_dir))
    out_dir = out_dir or os.path.join(runs_dir, 'eval')
    return evaluate_trials([p for _, p in runs], gt_file, out_dir, cfg,
                           run_names=[r for r, _ in runs], label=label)


def load_summary(path):
    """Load eval_summary.yaml (+ samples.npz if present) from a dir/file."""
    if os.path.isdir(path):
        path = os.path.join(path, SUMMARY_FN)
    with open(path) as f:
        summary = yaml.safe_load(f)
    sp = os.path.join(os.path.dirname(path), SAMPLES_FN)
    samples = {}
    if os.path.isfile(sp):
        with np.load(sp) as z:
            samples = {k: z[k] for k in z.files}
    return summary, samples
