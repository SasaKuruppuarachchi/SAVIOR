#!/usr/bin/env python3

# adapted from 
# https://svncvpr.in.tum.de/cvpr-ros-pkg/trunk/rgbd_benchmark/rgbd_benchmark_tools/src/rgbd_benchmark_tools/associate.py
# with the following license
#
# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Juergen Sturm, TUM
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of TUM nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import numpy as np


def read_timestamps(filename):
    """
    assume the first column of the file contains timestamp in second
    """
    file = open(filename)
    data = file.read()
    lines = data.replace(",", " ").replace("\t", " ").split("\n")
    data_list = [[v.strip() for v in line.split(" ") if v.strip() != ""]
                 for line in lines if len(line) > 0 and line[0] != "#"]
    stamps = [float(v[0]) for v in data_list]
    return stamps


def associate_reference(first_stamps, second_stamps, offset, max_difference):
    """
    [py3 port] The ORIGINAL O(N*M) implementation, kept verbatim as the
    reference for `associate` below (used by the tests).

    associate timestamps

    first_stamps, second_stamps: list of timestamps to associate

    Output:
    sorted list of matches (match_first_idx, match_second_idx)
    """
    potential_matches = [(abs(a - (b + offset)), idx_a, idx_b)
                         for idx_a, a in enumerate(first_stamps)
                         for idx_b, b in enumerate(second_stamps)
                         if abs(a - (b + offset)) < max_difference]
    potential_matches.sort()  # prefer the closest
    matches = []
    first_idxes = list(range(len(first_stamps)))
    second_idxes = list(range(len(second_stamps)))
    for diff, idx_a, idx_b in potential_matches:
        if idx_a in first_idxes and idx_b in second_idxes:
            first_idxes.remove(idx_a)
            second_idxes.remove(idx_b)
            matches.append((int(idx_a), int(idx_b)))

    matches.sort()
    return matches


def associate(first_stamps, second_stamps, offset, max_difference):
    """
    associate timestamps

    first_stamps, second_stamps: list of timestamps to associate

    Output:
    sorted list of matches (match_first_idx, match_second_idx)

    [py3 port] Same result as `associate_reference` (identical candidate
    set, identical (diff, idx_a, idx_b) greedy ordering), but candidates are
    generated with a sorted search instead of all N*M pairs, which is
    intractable for long, high-rate sequences.
    """
    a = np.asarray(first_stamps, dtype=np.float64).reshape(-1)
    b_off = np.asarray(second_stamps, dtype=np.float64).reshape(-1) + offset
    if a.size == 0 or b_off.size == 0:
        return []
    order = np.argsort(b_off, kind='stable')
    b_sorted = b_off[order]
    # slightly widened window; the exact criterion is applied below
    margin = max_difference + 1e-9 * np.abs(a) + 1e-12
    lo = np.searchsorted(b_sorted, a - margin, side='left')
    hi = np.searchsorted(b_sorted, a + margin, side='right')
    counts = np.maximum(hi - lo, 0)
    total = int(counts.sum())
    if total == 0:
        return []
    idx_a = np.repeat(np.arange(a.size), counts)
    starts = np.repeat(lo, counts)
    within = np.arange(total) - np.repeat(np.cumsum(counts) - counts, counts)
    idx_b = order[starts + within]
    diff = np.abs(a[idx_a] - b_off[idx_b])
    keep = diff < max_difference
    idx_a, idx_b, diff = idx_a[keep], idx_b[keep], diff[keep]
    sort_idx = np.lexsort((idx_b, idx_a, diff))  # prefer the closest
    used_a = np.zeros(a.size, dtype=bool)
    used_b = np.zeros(b_off.size, dtype=bool)
    matches = []
    for k in sort_idx:
        ia, ib = idx_a[k], idx_b[k]
        if not used_a[ia] and not used_b[ib]:
            used_a[ia] = True
            used_b[ib] = True
            matches.append((int(ia), int(ib)))
    matches.sort()
    return matches


def read_files_and_associate(first_file, second_file, offset, max_diff):
    first_stamps = read_timestamps(first_file)
    second_stamps = read_timestamps(second_file)

    return associate(first_stamps, second_stamps, offset, max_diff)

if __name__ == '__main__':
    pass
