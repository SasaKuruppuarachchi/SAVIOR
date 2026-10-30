import json, sys, numpy as np
from collections import Counter, defaultdict
NPX = None
rows = [json.loads(l) for l in open(sys.argv[1])]
NPX = rows[0]["image_size"][0] * rows[0]["image_size"][1]
def pct(v, q): return np.percentile(v, q) if len(v) else float('nan')
for k in ['segment', 'depth', 'motion', 'total']:
    v = np.array([r['timings_ms'].get(k, np.nan) for r in rows], float); v = v[np.isfinite(v)]
    if len(v): print('%-9s med %.2f p90 %.2f max %.1f' % (k, np.median(v), pct(v, 90), v.max()))
ms = defaultdict(list)
for r in rows:
    for k, v in (r.get('motion', {}).get('ms') or {}).items(): ms[k].append(v)
print({k: (round(np.median(v), 3), round(pct(v, 90), 3)) for k, v in ms.items()})
c = Counter(); obs = Counter(); per = defaultdict(list); W = defaultdict(list)
for r in rows:
    for i in r['instances']:
        c[(i['cls'], i['status'])] += 1
        mo = i.get('motion')
        if mo:
            obs[(i['cls'], mo.get('obs'))] += 1
            per[mo['id']].append((r['frame'], i['cls'], i['status'], i.get('depth')))
            if 'w_lat' in mo: W[i['cls']].append((mo['w_lat'], mo['w_slat'], mo['w_rad'], mo['w_srad'], i.get('depth') or np.nan))
            if 'q' in mo: W[i['cls'] + '_q'].append((mo['q'], mo['speed']))
print(sorted(c.items(), key=lambda kv: -kv[1])[:12]); print(sorted(obs.items()))
for k, v in W.items():
    a = np.array(v)
    if k.endswith('_q'): print(k, 'q med %.2f p90 %.2f p99 %.2f  speed med %.3f p90 %.3f' % (np.median(a[:, 0]), pct(a[:, 0], 90), pct(a[:, 0], 99), np.median(a[:, 1]), pct(a[:, 1], 90)))
    else: print(k, 'n %d w_lat med %.3f p90 %.3f (s %.3f)  w_rad med %+.3f |p90| %.3f (s %.3f)' % (len(a), np.median(a[:, 0]), pct(a[:, 0], 90), np.median(a[:, 1]), np.median(a[:, 2]), pct(np.abs(a[:, 2]), 90), np.median(a[:, 3])))
print('core frac %.4f ext %.4f' % (np.mean([r['core_px'] for r in rows]) / NPX, np.mean([r['ext_px'] for r in rows]) / NPX))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for tid, L in sorted(per.items(), key=lambda kv: -len(kv[1]))[:n]:
    print('track %d %s frames %d-%d n=%d %s z %.1f' % (tid, L[0][1], L[0][0], L[-1][0], len(L), dict(Counter(x[2] for x in L)), np.median([x[3] for x in L if x[3]] or [-1])))
