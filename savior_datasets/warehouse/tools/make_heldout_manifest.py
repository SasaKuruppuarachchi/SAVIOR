#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write data/warehouse/HELDOUT_MANIFEST.yaml for the held-out test split (Isaac python or any python with numpy +
yaml; no Isaac modules needed).

  $HOME/isaacsim/python.sh tools/make_heldout_manifest.py aisles_t2 hall_t2 dock_t2 [--extra extra.yaml]

Per sequence: files, duration, path, moving coverage (mean / p90 / frames > 5 %), actor counts, and the hard cases
present (cumulative HARD_CASES of the scene module up to the sequence level). --extra merges a yaml mapping
{seq: {key: value}} into the entries (e.g. IMU-check and sanity-ATE numbers).
"""
import argparse
import csv
import datetime
import importlib
import json
import os
import sys

import numpy as np
import yaml

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG)
WS = os.path.abspath(os.path.join(PKG, '..', '..', '..', '..'))
DATA = os.environ.get('SAVIOR_WAREHOUSE_DATA', os.path.join(WS, 'data', 'warehouse'))
LABELS = {'a': 'leading / co-moving forklift', 'b': 'motion onset at / just after take-off (filter init)',
          'c': 'standing / idle people', 'd': 'parked loaded forklifts, stacks touched by people',
          'e': 'person -> forklift -> box chain', 'f': 'perpendicular and parallel motion'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('modules', nargs='+')
    ap.add_argument('--extra', default='')
    ap.add_argument('--out', default=os.path.join(DATA, 'HELDOUT_MANIFEST.yaml'))
    args = ap.parse_args()
    extra = yaml.safe_load(open(args.extra)) if args.extra else {}
    seqs = []
    for mname in args.modules:
        mod = importlib.import_module(f'scenes.{mname}')
        for level in range(4):
            seq = f'{mod.NAME}_{mod.TRAJ}_L{level}'
            raw = os.path.join(DATA, 'raw', seq)
            if not os.path.isfile(os.path.join(raw, 'meta.json')):
                print(f'[manifest] skip {seq}: not rendered')
                continue
            meta = json.load(open(os.path.join(raw, 'meta.json')))
            cov = np.array([float(r['moving']) for r in csv.DictReader(open(os.path.join(raw, 'coverage.csv')))])
            inst = json.load(open(os.path.join(raw, 'instances.json')))['instances']
            actors = sorted({i['actor'] for i in inst if i['actor']})
            hard = {}
            for k in range(level + 1):
                for key, txt in mod.HARD_CASES.get(k, {}).items():
                    hard.setdefault(key, []).append(f'L{k}: {txt}')
            e = dict(sequence=seq, scene=mod.NAME, scene_module=mname, trajectory=mod.TRAJ, level=level,
                     imu_seed=int(mod.SEED), frames=int(meta['frames']), duration_s=round(meta['duration_s'], 2),
                     path_m=round(meta['path_length_m'], 1),
                     coverage_moving_mean_pct=round(100 * float(cov.mean()), 2),
                     coverage_moving_p90_pct=round(100 * float(np.percentile(cov, 90)), 2),
                     frames_moving_gt5_pct=round(100 * float(np.mean(cov > 0.05)), 1),
                     actors=len(actors), moving_instances=sum(1 for i in inst if i['moving_ever']),
                     files=dict(raw=f'data/warehouse/raw/{seq}', bag=f'data/warehouse/ros2_stereoseg/{seq}',
                                gt=f'data/warehouse/gt/{seq}.txt'),
                     hard_cases={k: hard[k] for k in sorted(hard)},
                     hard_case_keys=sorted(k for k in hard if k in LABELS))
            e.update(extra.get(seq, {}))
            seqs.append(e)
    doc = dict(
        split='heldout_test',
        created=datetime.date.today().isoformat(),
        purpose='Held-out SAVIOR-Warehouse test split for the final, honest evaluation. Do NOT tune, select or '
                'debug methods on these sequences; only the final benchmark may run on them. Tuning / development '
                'uses the t1 sequences.',
        generator='src/savior/savior_datasets/warehouse (scenes/*_t2.py, scenes/dock.py; tools/render_heldout.sh)',
        rig='configs/rig_zed2i_4mm.yaml (ZED 2i 4 mm, 672x376, 20 Hz, 200 Hz analytic IMU); 3 s hover + take-off',
        bag_launch_preset='warehouse / warehouse_moving (same topics as t1; bags include /cam1/segmentation(_moving))',
        hard_case_legend=LABELS,
        sequences=seqs)
    with open(args.out, 'w') as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, width=118, allow_unicode=True)
    print(f'[manifest] {len(seqs)} sequences -> {args.out}')


if __name__ == '__main__':
    main()
