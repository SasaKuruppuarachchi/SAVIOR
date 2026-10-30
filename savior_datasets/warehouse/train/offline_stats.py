#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-stage latency (median / p90 / mean, ms) and instance counts from perception_offline --stats JSON lines.
Node pipeline = segment + SaviorPipeline total (depth, gating, tracking, extension, compose).

  python3 offline_stats.py <stats.jsonl> [...]
"""
import json
import sys

import numpy as np

out = {}
for f in sys.argv[1:]:
    L = [json.loads(line) for line in open(f)]
    T = {k: np.array([x['timings_ms'].get(k, np.nan) for x in L], float) for k in L[0]['timings_ms']}
    T['node_total'] = T['segment'] + T['total']
    r = {k: dict(median=round(float(np.nanmedian(v)), 2), p90=round(float(np.nanpercentile(v, 90)), 2),
                 mean=round(float(np.nanmean(v)), 2)) for k, v in T.items()}
    roles = {}
    for x in L:
        for k, v in x['n_by_role'].items():
            roles.setdefault(k, []).append(v)
    r['frames'] = len(L)
    r['mean_instances_by_role'] = {k: round(float(np.mean(v)), 2) for k, v in roles.items()}
    r['frames_with_core_mask'] = int(sum(x['core_px'] > 0 for x in L))
    r['mean_core_px_frac'] = round(float(np.mean([x['core_px'] for x in L])) / (672 * 376), 4)
    r['mean_ext_px_frac'] = round(float(np.mean([x['ext_px'] for x in L])) / (672 * 376), 4)
    out[f] = r
    print(f, json.dumps(r))
