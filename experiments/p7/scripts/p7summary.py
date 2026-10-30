#!/usr/bin/env python3
"""p7summary.py <eval dir> [variants comma] [--md out.md]: pooled classification table of p7eval.py outputs.
Groups: L0, L1, L2+L3, L1-L3; counts summed over sequences (instance-frames)."""
import json
import sys
from pathlib import Path

import numpy as np

D = Path(sys.argv[1])
want = sys.argv[2].split(',') if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
md = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
R = {}
for f in sorted(D.glob('*/*.json')):
    d = json.load(open(f))
    R.setdefault(d['variant'], {})[d['seq']] = d
order = want or sorted(R)
GROUPS = {'L0': ['_L0'], 'L1': ['_L1'], 'L2+L3': ['_L2', '_L3'], 'hall_L3': ['hall_t1_L3'], 'L1-L3': ['_L1', '_L2', '_L3']}


def rate(ds, key, kind='gt_centric'):
    n = sum(d[kind].get(key, [0, 0])[0] for d in ds)
    m = sum(d[kind].get(key, [0, 0])[1] for d in ds)
    return (m / n if n else None), n


def onset(ds, cls_list, kinds=('transition', 'appear')):
    v = []
    for d in ds:
        for c in cls_list:
            for k in kinds:
                v += d['onset'].get(f'{c}:{k}', [])
    if not v:
        return None
    lat = np.array([x if x is not None else np.inf for x in v])
    return len(v), float(np.median(lat)), float(np.percentile(lat, 90)), float(np.mean(np.isinf(lat))), float(np.mean(lat <= 0.25))


def fl(ds, key):
    n = sum(d['flicker_inst'].get(key, [0, 0])[0] for d in ds)
    m = sum(d['flicker_inst'].get(key, [0, 0])[1] for d in ds)
    return 100 * m / n if n else None


def f2(x, p=2):
    return '-' if x is None else f'{x:.{p}f}'


lines = []
for g, pats in GROUPS.items():
    lines.append(f'\n## {g}\n')
    lines.append('| variant | person mov | forklift mov | forklift st kept | box mov | box st kept | pallet mov | pallet st kept | trolley st kept '
                 '| load on moving fl masked | load on parked fl kept | driver mov | init-window mov recall '
                 '| onset fl+load: median s / p90 s / never / <=0.25 s | flicker toggles /100 fr mov / st | core-jump flicker | static-pot px masked | core share |')
    lines.append('|---|' + '--:|' * 18)
    for v in order:
        ds = [d for s, d in R.get(v, {}).items() if any(p in s for p in pats)]
        if not ds:
            continue
        r = lambda k: rate(ds, k)[0]  # noqa: E731
        kept = lambda k: None if r(k) is None else 1 - r(k)  # noqa: E731
        lm_n = sum(rate(ds, f'carried_{c}:moving')[1] for c in ('box', 'pallet'))
        lm = sum((rate(ds, f'carried_{c}:moving')[0] or 0) * rate(ds, f'carried_{c}:moving')[1] for c in ('box', 'pallet')) / lm_n if lm_n else None
        ls_n = sum(rate(ds, f'carried_{c}:static')[1] for c in ('box', 'pallet'))
        ls = 1 - sum((rate(ds, f'carried_{c}:static')[0] or 0) * rate(ds, f'carried_{c}:static')[1] for c in ('box', 'pallet')) / ls_n if ls_n else None
        n_i = sum(sum(e[0] for e in d['init_window'].values()) for d in ds)
        m_i = sum(sum(e[1] for e in d['init_window'].values()) for d in ds)
        o = onset(ds, ('forklift', 'box', 'pallet'))
        os_ = '-' if o is None else f'{o[1]:.2f} / {o[2]:.2f} / {o[3]:.2f} / {o[4]:.2f} (n={o[0]})'
        fm = [fl(ds, f'{c}:moving') for c in ('person', 'forklift', 'box', 'pallet')]
        fs = [fl(ds, f'{c}:static') for c in ('forklift', 'box', 'pallet', 'trolley')]
        fmv = np.nanmean([x for x in fm if x is not None]) if any(x is not None for x in fm) else None
        fsv = np.nanmean([x for x in fs if x is not None]) if any(x is not None for x in fs) else None
        cj = np.mean([d['flicker_core_jump'] for d in ds])
        spm = np.mean([d['static_pot_core_share_of_static_pot'] for d in ds])
        cs = np.mean([d['core_share'] for d in ds])
        lines.append(f'| {v} | {f2(r("person:moving"))} | {f2(r("forklift:moving"))} | {f2(kept("forklift:static"))} | {f2(r("box:moving"))} '
                     f'| {f2(kept("box:static"))} | {f2(r("pallet:moving"))} | {f2(kept("pallet:static"))} | {f2(kept("trolley:static"))} '
                     f'| {f2(lm)} | {f2(ls)} | {f2(r("driver:moving"))} | {f2(m_i / n_i if n_i else None)} | {os_} '
                     f'| {f2(fmv, 1)} / {f2(fsv, 1)} | {100 * cj:.1f} % | {100 * spm:.1f} % | {100 * cs:.1f} % |')
txt = '\n'.join(lines)
print(txt)
if md:
    Path(md).write_text('# P7 offline classification (tuning set t1, GT moving flags; see scripts/p7eval.py)\n' + txt + '\n')
