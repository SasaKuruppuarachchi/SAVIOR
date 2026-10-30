#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Collect the OpenVINS sanity ATE (posyaw) per sequence: python3 tools/ate_table.py [results/warehouse_sanity]"""
import glob
import os
import sys

import yaml

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))
root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WS, 'results', 'warehouse_sanity')
print('| sequence | method | runs | ATE trans per run [m] | mean [m] | ATE rot mean [deg] | RPE overall mean [%] |')
print('|---|---|--:|---|--:|--:|--:|')
for f in sorted(glob.glob(os.path.join(root, 'warehouse', '*', '*', 'eval', 'eval_summary.yaml'))):
    d = yaml.safe_load(open(f))
    tr = [t for t in d['trials'] if t.get('status') == 'ok']
    a = [t['ate']['trans_m']['rmse'] for t in tr]
    r = [t['ate']['rot_deg']['rmse'] for t in tr]
    rpe = [((d.get('rpe_overall') or {}).get('trans_perc') or {}).get('mean', float('nan'))]
    seq = f.split(os.sep)[-4]
    print(f'| {seq} | {f.split(os.sep)[-3]} | {len(a)} | {" / ".join(f"{x:.3f}" for x in a)} | {sum(a)/max(len(a),1):.3f} | '
          f'{sum(r)/max(len(r),1):.2f} | {(sum(rpe)/len(rpe)) if rpe else float("nan"):.2f} |')
