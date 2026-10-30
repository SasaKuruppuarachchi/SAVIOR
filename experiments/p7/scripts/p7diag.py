"""p7diag.py <eval dir> <variant> <cls> [seq-substr] : detection-level breakdown (gt state x evidence x label x status x depth)."""
import json, sys
from pathlib import Path
D, v, cls = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sub = sys.argv[4] if len(sys.argv) > 4 else ''
agg = {}
for f in D.glob(f'*{sub}*/{v}.json'):
    for k, n in json.load(open(f)).get('diag', {}).items():
        c, gl, obs, lab, st, zb = k.split('|')
        if c != cls: continue
        for kk in [(gl, 'obs', obs), (gl, 'label', lab), (gl, 'status', st), (gl, 'depth', zb), (gl, 'obs@' + zb, obs)]:
            agg[kk] = agg.get(kk, 0) + n
for gl in ('moving', 'static', 'none'):
    tot = sum(n for (g, a, b), n in agg.items() if g == gl and a == 'status')
    if not tot: continue
    print(f'== {cls} gt={gl} n={tot}')
    for a in ('obs', 'label', 'status', 'depth', 'obs@<3', 'obs@<6', 'obs@>6'):
        row = {b: n for (g, aa, b), n in agg.items() if g == gl and aa == a}
        print('  %-8s' % a, '  '.join(f'{b}:{100*n/tot:.1f}%' for b, n in sorted(row.items(), key=lambda x: -x[1])))
