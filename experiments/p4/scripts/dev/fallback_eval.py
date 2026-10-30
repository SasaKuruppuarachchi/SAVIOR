import json, sys, numpy as np
fb = float(sys.argv[2]); W = None
rows = [json.loads(l) for l in open(sys.argv[1])]
W = rows[0]['image_size'][1]
nod = n = border = 0; ov_med, ov_fix = [], []
for r in rows:
    rel = [i for i in r['instances'] if i['role'] in ('dynamic', 'potential')]
    for k, i in enumerate(rel):
        if i['cls'] != 'person': continue
        n += 1
        x0, y0, x1, y1 = i['bbox']
        if not i.get('disparity'):
            nod += 1; border += (x0 <= 2 or x1 >= W - 2); continue
        others = [j['disparity'] for m, j in enumerate(rel) if m != k and j.get('disparity')]
        d = i['disparity']; w = max(1, x1 - x0)
        for lst, dfb in ((ov_med, np.median(others) if others else fb / 3.0), (ov_fix, fb / 3.0)):
            lst.append(max(0.0, 1 - abs(dfb - d) / w))
print('person instances %d, without depth %d (%.1f %%), of those at the image border %.0f %%' % (n, nod, 100 * nod / max(n, 1), 100 * border / max(nod, 1)))
print('leave-one-out horizontal overlap of the right mask (instances with depth): median-fallback mean %.2f (p10 %.2f), fixed %.1f m mean %.2f (p10 %.2f)' % (
    np.mean(ov_med), np.percentile(ov_med, 10), 3.0, np.mean(ov_fix), np.percentile(ov_fix, 10)))
