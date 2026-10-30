import json, sys, numpy as np
from collections import Counter, defaultdict
rows = [json.loads(l) for l in open(sys.argv[1])]
def pct(v, q): return np.percentile(v, q) if len(v) else float('nan')
for k in ['segment', 'depth', 'motion', 'gating', 'extension', 'compose', 'total']:
    v = np.array([r['timings_ms'].get(k, np.nan) for r in rows], float); v = v[np.isfinite(v)]
    if len(v): print('%-9s med %.2f p90 %.2f max %.1f' % (k, np.median(v), pct(v, 90), v.max()))
m = [r.get('motion', {}) for r in rows]
for k in ['n_bg', 'n_inl', 'sigma_bg_px', 'dtheta_deg', 'rot_deg']:
    v = np.array([x.get(k) for x in m if x.get(k) is not None], float)
    if len(v): print('%-12s med %.3f p10 %.3f p90 %.3f' % (k, np.median(v), pct(v, 10), pct(v, 90)))
print('t_ok frac %.3f' % np.mean([bool(x.get('t_ok')) for x in m if 'n_bg' in x]))
tn = np.array([np.linalg.norm(x['t']) for x in m if x.get('t')]); print('|t| med %.4f p90 %.4f m/frame' % (np.median(tn), pct(tn, 90)))
ms = defaultdict(list)
for x in m:
    for k, v in (x.get('ms') or {}).items(): ms[k].append(v)
print({k: (round(np.median(v), 3), round(pct(v, 90), 3)) for k, v in ms.items()})
c = Counter(); obs = Counter(); per_track = defaultdict(list)
for r in rows:
    for i in r['instances']:
        c[(i['cls'], i['status'])] += 1
        mo = i.get('motion')
        if mo:
            obs[(i['role'], mo.get('obs'))] += 1
            per_track[mo['id']].append((r['frame'], i['cls'], i['status'], mo.get('ema_lat'), mo.get('ema_rad'), mo.get('l'), i.get('depth'), mo.get('n')))
print(sorted(c.items(), key=lambda kv: -kv[1])[:16])
print(obs)
print('frames', len(rows), 'core frac %.4f ext %.4f' % (np.mean([r['core_px'] for r in rows]) / (848 * 800), np.mean([r['ext_px'] for r in rows]) / (848 * 800)))
print('person-frames: still %d root %d' % (c[('person', 'still')], c[('person', 'root')]))
if len(sys.argv) > 2:
    for tid, L in sorted(per_track.items(), key=lambda kv: -len(kv[1]))[:int(sys.argv[2])]:
        st = Counter(x[2] for x in L)
        lat = [x[3] for x in L if x[3] is not None]; rad = [x[4] for x in L if x[4] is not None]
        z = [x[6] for x in L if x[6]]
        print('track %d %s frames %d-%d n=%d %s lat med %.2f p90 %.2f rad med %.2f z %.1f' % (tid, L[0][1], L[0][0], L[-1][0], len(L), dict(st),
              np.median(lat) if lat else -1, pct(lat, 90) if lat else -1, np.median(rad) if rad else 0, np.median(z) if z else -1))
