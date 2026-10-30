#!/usr/bin/env python3
"""sg_args.py <seq> <variant> : savior-run settings of one SG-study variant (back-end v2), same output format as
results/backend_v2/scripts/bv2_args.py (INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, launch args).
The base method's lines come unchanged from bv2_args.py (which asserts every frozen md5); the INSTALL line is replaced by
the SG install for install='sg' variants and the variant delta of sg_variants.py is applied to PSET / OVSET.
WAREHOUSE t1 ONLY (asserted)."""
import os, subprocess, sys
WS = '/home/sasa/workspace/savior_ws'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg_variants import V  # noqa: E402

SG_INSTALL = f'{WS}/results/semantic_gate/install'


def kvparse(s):
    out = {}
    for it in s.split():
        k, _, v = it.partition('=')
        assert k not in out, f'duplicate key {k}'
        out[k] = v
    return out


def fmt(v):
    return ('true' if v else 'false') if isinstance(v, bool) else str(v)


def settings(seq, var):
    v = V[var]
    L = subprocess.run([sys.executable, f'{WS}/results/backend_v2/scripts/bv2_args.py', seq, v['base'], 'v2'], check=True,
                       capture_output=True, text=True).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')
    assert L[0] == f'{WS}/install', L[0]
    if v['install'] == 'sg':
        assert os.path.isfile(f'{SG_INSTALL}/setup.bash'), 'SG install missing (scripts/build_sg.sh)'
        L[0] = SG_INSTALL
    if v.get('pset_set'):
        assert L[1] == 'savior.launch.py', 'pset delta on a non-savior method'
        p = kvparse(L[7])
        p.update({k: fmt(x) for k, x in v['pset_set'].items()})
        L[7] = ' '.join(f'{k}={x}' for k, x in sorted(p.items()))
    if v.get('ovset_add'):
        o = kvparse(L[5])
        for k, x in v['ovset_add'].items():
            assert k not in o, f'ov_set already has {k}'
            o[k] = fmt(x)
        L[5] = ' '.join(f'{k}={x}' for k, x in o.items())
    return L


if __name__ == '__main__':
    seq, var = sys.argv[1], sys.argv[2]
    assert '_t1_' in seq and seq.startswith(('aisles_', 'hall_')), f'{seq}: the SG study runs on warehouse t1 only'
    print('\n'.join(settings(seq, var)))
