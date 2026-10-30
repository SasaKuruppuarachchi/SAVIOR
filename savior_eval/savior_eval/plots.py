"""Additional plots (multi-run overlay, method comparison).

The standard per-estimate plots are produced by the rpg port
(``analyze_trajectory_single.plot_single_results``); comparison boxplots use
the port's ``plot_utils.boxplot_compare`` exactly as rpg's
analyze_trajectories.py does.
"""

import os

import numpy as np

from .third_party.rpg_trajectory_evaluation import plot_utils as pu  # Agg
import matplotlib.pyplot as plt  # noqa: E402

# Categorical slots in fixed order (validated light-mode palette).
SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4',
                 '#008300', '#6250d6', '#e34948']
GT_COLOR = '#52514e'
RUN_COLOR = '#2a78d6'


def method_color(i):
    # beyond 8 methods colours would repeat; tables remain the reference
    return SERIES_COLORS[i % len(SERIES_COLORS)]


def _finish(fig, path):
    fig.tight_layout()
    fig.savefig(path, bbox_inches='tight', dpi=200)
    plt.close(fig)


def plot_trials_overlay(traj_list, success_indices, run_names, plots_dir,
                        fmt='pdf'):
    """Top view of all successful runs (aligned) over the groundtruth, plus
    per-run ATE RMSE."""
    if not traj_list:
        return
    fig = plt.figure(figsize=(6, 5.5))
    ax = fig.add_subplot(111, aspect='equal', xlabel='x [m]', ylabel='y [m]')
    ax.grid(ls='--', color='0.85', lw=0.5)
    alpha = 1.0 if len(traj_list) == 1 else max(0.25, 1.0 / len(traj_list) ** 0.5)
    for k, traj in enumerate(traj_list):
        ax.plot(traj.p_es_aligned[:, 0], traj.p_es_aligned[:, 1], '-',
                color=RUN_COLOR, lw=1.0, alpha=alpha,
                label='Estimate (%d runs)' % len(traj_list) if k == 0 else None)
    p_gt = traj_list[0].p_gt
    ax.plot(p_gt[:, 0], p_gt[:, 1], '-', color=GT_COLOR, lw=1.5,
            label='Groundtruth')
    ax.legend(loc='best', frameon=False)
    _finish(fig, os.path.join(plots_dir, 'trajectories_top_all_runs.' + fmt))

    if len(traj_list) > 1:
        rmse = [t.abs_errors['abs_e_trans_stats']['rmse'] for t in traj_list]
        names = [run_names[i] for i in success_indices]
        fig = plt.figure(figsize=(max(4, 0.45 * len(rmse) + 1.5), 2.6))
        ax = fig.add_subplot(111, ylabel='ATE RMSE [m]')
        ax.bar(np.arange(len(rmse)), rmse, width=0.6, color=RUN_COLOR)
        ax.axhline(np.mean(rmse), color=GT_COLOR, lw=1, ls='--',
                   label='mean %.3f m' % np.mean(rmse))
        ax.set_xticks(np.arange(len(rmse)))
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
        ax.legend(frameon=False, fontsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        _finish(fig, os.path.join(plots_dir, 'ate_rmse_per_run.' + fmt))


def plot_compare_rpe(seq_name, methods, labels, samples_by_method, lengths,
                     out_dir, fmt='pdf'):
    """Boxplots of RPE (translation m, rotation deg) per sub-trajectory
    length, one colour per method (rpg boxplot_compare)."""
    from .evaluation import length_key
    colors = [method_color(i) for i in range(len(methods))]
    xl = ['%g' % d for d in lengths]
    for key, ylabel, fn in [('trans_m', 'Translation error [m]', 'rpe_trans'),
                            ('rot_deg', 'Rotation error [deg]', 'rpe_rot'),
                            ('trans_perc', 'Translation error [' + pu.PCT + ']',
                             'rpe_trans_perc')]:
        data = []
        for m in methods:
            s = samples_by_method[m]
            data.append([np.asarray(s.get('rpe_%s_%s' % (key, length_key(d)),
                                          np.array([])))
                         for d in lengths])
        fig = plt.figure(figsize=(max(6, 1.2 * len(lengths) + 2), 2.8))
        ax = fig.add_subplot(111, xlabel='Distance traveled [m]',
                             ylabel=ylabel)
        pu.boxplot_compare(ax, xl, data, labels, colors, legend=True)
        ax.set_title(seq_name, fontsize=10)
        _finish(fig, os.path.join(out_dir, '%s_%s.%s' % (seq_name, fn, fmt)))


def plot_compare_ate(seq_labels, methods, labels, ate_by_seq_method, out_dir,
                     fmt='pdf'):
    """Boxplot of per-run ATE RMSE (m and deg), sequences on the x axis
    (rpg plot_rmse_per_dataset)."""
    colors = [method_color(i) for i in range(len(methods))]
    for key, ylabel, fn in [('trans_m', 'Translation RMSE [m]', 'ate_trans'),
                            ('rot_deg', 'Rotation RMSE [deg]', 'ate_rot')]:
        data = []
        for m in methods:
            data.append([np.asarray(ate_by_seq_method[s].get(m, {}).get(
                key, []), dtype=float) for s in range(len(seq_labels))])
        fig = plt.figure(figsize=(max(5, 1.6 * len(seq_labels) + 2), 3))
        ax = fig.add_subplot(111, xlabel='Sequence', ylabel=ylabel)
        pu.boxplot_compare(ax, seq_labels, data, labels, colors, legend=True)
        _finish(fig, os.path.join(out_dir, 'all_%s_rmse.%s' % (fn, fmt)))


def plot_compare_trajectories(seq_name, methods, labels, samples_by_method,
                              out_dir, fmt='pdf'):
    """Top view of the first successful run of each method + groundtruth."""
    fig = plt.figure(figsize=(6, 5.5))
    ax = fig.add_subplot(111, aspect='equal', xlabel='x [m]', ylabel='y [m]')
    ax.grid(ls='--', color='0.85', lw=0.5)
    gt_done = False
    for i, m in enumerate(methods):
        s = samples_by_method[m]
        keys = sorted([k for k in s if k.endswith('_p_es_aligned')],
                      key=lambda k: int(k[4:].split('_')[0]))
        if not keys:
            continue
        p = s[keys[0]]
        if not gt_done:
            g = s[keys[0].replace('_p_es_aligned', '_p_gt')]
            ax.plot(g[:, 0], g[:, 1], '-', color=GT_COLOR, lw=1.5,
                    label='Groundtruth')
            gt_done = True
        ax.plot(p[:, 0], p[:, 1], '-', color=method_color(i), lw=1.0,
                label=labels[i])
    ax.legend(loc='best', frameon=False)
    ax.set_title(seq_name, fontsize=10)
    _finish(fig, os.path.join(out_dir, '%s_trajectory_top.%s' % (seq_name, fmt)))
