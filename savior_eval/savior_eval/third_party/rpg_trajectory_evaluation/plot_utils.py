#!/usr/bin/env python3
"""
@author: Christian Forster
"""

import os
import yaml
import numpy as np
import matplotlib as mpl
# [py3 port] headless backend unless the user forces one via MPLBACKEND
if not os.environ.get('MPLBACKEND'):
    mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib import rc

# [py3 port] LaTeX text rendering (and the Cardo font) only when requested via
# RPG_USETEX=1, since a TeX installation is usually not available in Docker.
USETEX = os.environ.get('RPG_USETEX', '0') == '1'
if USETEX:
    rc('font', **{'family': 'serif', 'serif': ['Cardo']})
    rc('text', usetex=True)
else:
    rc('font', **{'family': 'serif'})
# percent sign for axis labels: '\\%' is only needed with usetex
PCT = r'\%' if USETEX else '%'

FORMAT = '.pdf'


def color_box(bp, color):
    elements = ['medians', 'boxes', 'caps', 'whiskers']
    # Iterate over each of the elements changing the color
    for elem in elements:
        [plt.setp(bp[elem][idx], color=color, linestyle='-', lw=1.0)
         for idx in range(len(bp[elem]))]
    return


def boxplot_compare(ax, xlabels,
                    data, data_labels, data_colors,
                    legend=True):
    n_data = len(data)
    n_xlabel = len(xlabels)
    leg_handles = []
    leg_labels = []
    idx = 0
    for idx, d in enumerate(data):
        # print("idx and d: {0} and {1}".format(idx, d))
        w = 1 / (1.5 * n_data + 1.5)
        widths = [w for pos in np.arange(n_xlabel)]
        positions = [pos - 0.5 + 1.5 * w + idx * w
                     for pos in np.arange(n_xlabel)]
        # print("Positions: {0}".format(positions))
        # [py3 port] notch/sym passed by keyword (positional use deprecated)
        bp = ax.boxplot(d, notch=False, sym='', positions=positions,
                        widths=widths)
        color_box(bp, data_colors[idx])
        # [py3 port] proxy artist instead of an invisible line drawn into the
        # current axes: with recent matplotlib the alpha=0 line made the
        # legend entries invisible, and the point (0..1, 1) it added
        # distorted the axis autoscaling.
        tmp = mpl.lines.Line2D([], [], color=data_colors[idx])
        leg_handles.append(tmp)
        leg_labels.append(data_labels[idx])
        idx += 1

    ax.set_xticks(np.arange(n_xlabel))
    ax.set_xticklabels(xlabels)
    xlims = ax.get_xlim()
    ax.set_xlim([xlims[0]-0.1, xlims[1]-0.1])
    if legend:
        # ax.legend(leg_handles, leg_labels, bbox_to_anchor=(
            # 1.05, 1), loc=2, borderaxespad=0.)
        ax.legend(leg_handles, leg_labels)
    # [py3 port] the original hid the dummy lines here
    # (map(lambda x: x.set_visible(False), leg_handles)); not needed for
    # proxy artists, which are never drawn.


def plot_trajectory_top(ax, pos, color, name, alpha=1.0):
    ax.grid(ls='--', color='0.7')
    # pos_0 = pos - pos[0, :]
    ax.plot(pos[:, 0], pos[:, 1], color, linestyle='-', alpha=alpha, label=name)


def plot_trajectory_side(ax, pos, color, name, alpha=1.0):
    ax.grid(ls='--', color='0.7')
    # pos_0 = pos - pos[0, :]
    ax.plot(pos[:, 0], pos[:, 2], color, linestyle='-', alpha=alpha, label=name)


def plot_aligned_top(ax, p_gt, p_es, n_align_frames):
    if n_align_frames <= 0:
        n_align_frames = p_es.shape[0]
    # p_es_0 = p_es - p_gt[0, :]
    # p_gt_0 = p_gt - p_gt[0, :]
    # ax.plot(p_es[0:n_align_frames, 0], p_es[0:n_align_frames, 1],
        # 'g-', linewidth=2, label='aligned')
    for (x1, y1, z1), (x2, y2, z2) in zip(
            p_es[:n_align_frames:10, :], p_gt[:n_align_frames:10, :]):
        ax.plot([x1, x2], [y1, y2], '-', color="gray")


def plot_error_n_dim(ax, distances, errors, results_dir,
                     colors=['r', 'g', 'b'],
                     labels=['x', 'y', 'z']):
    assert len(colors) == len(labels)
    assert len(colors) == errors.shape[1]
    for i in range(len(colors)):
        ax.plot(distances, errors[:, i],
                colors[i]+'-', label=labels[i])
