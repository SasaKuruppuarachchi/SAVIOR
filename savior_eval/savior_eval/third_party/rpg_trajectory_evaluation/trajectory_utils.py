#!/usr/bin/env python3
"""
@author: Christian Forster
"""

import os
import numpy as np
from . import transformations as tf


def get_rigid_body_trafo(quat, trans):
    T = tf.quaternion_matrix(quat)
    T[0:3, 3] = trans
    return T


def get_distance_from_start(gt_translation):
    distances = np.diff(gt_translation[:, 0:3], axis=0)
    distances = np.sqrt(np.sum(np.multiply(distances, distances), 1))
    distances = np.cumsum(distances)
    distances = np.concatenate(([0], distances))
    return distances


def compute_comparison_indices_length_reference(distances, dist,
                                                max_dist_diff):
    """[py3 port] ORIGINAL O(N^2) pure-python implementation, kept verbatim
    as the reference for `compute_comparison_indices_length` (tests)."""
    max_idx = len(distances)
    comparisons = []
    for idx, d in enumerate(distances):
        best_idx = -1
        error = max_dist_diff
        for i in range(idx, max_idx):
            if np.abs(distances[i]-(d+dist)) < error:
                best_idx = i
                error = np.abs(distances[i] - (d+dist))
        if best_idx != -1:
            comparisons.append(best_idx)
    return comparisons


def compute_comparison_indices_length(distances, dist, max_dist_diff):
    """
    For every start index idx, the index i >= idx whose distance from start
    is closest to distances[idx] + dist (first one on ties), if the gap is
    < max_dist_diff. Indices without a match are skipped (as in the original,
    the returned list is therefore compacted -- see PORTING.md).

    [py3 port] Same output as `compute_comparison_indices_length_reference`,
    vectorised with a sorted search (distances from start are monotone).
    Falls back to a per-index argmin for non-monotone input.
    """
    D = np.asarray(distances, dtype=np.float64).reshape(-1)
    n = D.size
    if n == 0:
        return []
    targets = D + dist
    if not np.all(np.diff(D) >= 0):
        comparisons = []
        for idx in range(n):
            err = np.abs(D[idx:] - targets[idx])
            j = int(np.argmin(err))
            if err[j] < max_dist_diff:
                comparisons.append(idx + j)
        return comparisons
    idxs = np.arange(n)
    # first index >= idx with D >= target ("above" candidate)
    k = np.maximum(np.searchsorted(D, targets, side='left'), idxs)
    best = np.full(n, -1, dtype=np.int64)
    best_err = np.full(n, np.inf)
    # "below" candidate: first index of the plateau holding D[k-1], >= idx
    has_below = k - 1 >= idxs
    kb = np.where(has_below, k - 1, 0)
    below = np.maximum(np.searchsorted(D, D[kb], side='left'), idxs)
    err_below = np.where(has_below, np.abs(D[below] - targets), np.inf)
    has_above = k < n
    ka = np.where(has_above, k, 0)
    # first index of the plateau holding D[k] (>= idx)
    above = np.maximum(np.searchsorted(D, D[ka], side='left'), idxs)
    err_above = np.where(has_above, np.abs(D[above] - targets), np.inf)
    # earlier index wins on ties (strict '<' update in the original loop)
    use_below = err_below <= err_above
    best = np.where(use_below, below, above)
    best_err = np.where(use_below, err_below, err_above)
    ok = best_err < max_dist_diff
    return [int(v) for v in best[ok]]


def compute_angle(transform):
    """
    Compute the rotation angle from a 4x4 homogeneous matrix.
    """
    # an invitation to 3-d vision, p 27
    return np.arccos(
        min(1, max(-1, (np.trace(transform[0:3, 0:3]) - 1)/2)))*180.0/np.pi
