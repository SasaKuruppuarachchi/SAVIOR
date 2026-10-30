#!/usr/bin/env python3
"""print a compact classification summary of offline_eval_wh yaml files (GT-centric masked rates)."""
import sys
import yaml
K = ['person:moving', 'person:static', 'forklift:moving', 'forklift:static', 'box:moving', 'box:static',
     'carried_box:moving', 'carried_box:static', 'pallet:static', 'trolley:static']
for f in sys.argv[1:]:
    d = yaml.safe_load(open(f))
    print('==', d['seq'])
    print('variant'.ljust(24), 'Lcore P/R vs moving'.ljust(20), 'core%  spot%', ' '.join(k.replace(':moving', ':mov').replace(':static', ':st')[:13].rjust(13) for k in K))
    for v, o in d['variants'].items():
        g = d['gt_centric'][v]
        m = o['L_core_vs_moving']
        print(v.ljust(24), f"{m['precision']}/{m['recall']}".ljust(20), f"{100 * o['core_share']:5.1f} {100 * o['static_potential_core_share']:5.1f}",
              ' '.join((f"{g[k]['rate']:.2f}/{g[k]['n']}" if k in g else '-').rjust(13) for k in K))
