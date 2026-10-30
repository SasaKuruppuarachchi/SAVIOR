import json, sys, numpy as np
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1])]
fb = 12.8 * 1.0
seq = defaultdict(list)
for r in rows:
    for i in r['instances']:
        mo = i.get('motion')
        if mo and i.get('depth') and 'cx' in i:
            seq[mo['id']].append((r['frame'], i['depth'], i['cx'], i['cy'], i['cls'], i['area']))
out = defaultdict(list)
for tid, L in seq.items():
    L = [x for x in L]
    for a, b, c in zip(L, L[1:], L[2:]):
        if b[0] - a[0] == 1 and c[0] - b[0] == 1:
            z = b[1]
            d2z = (c[1] - 2 * b[1] + a[1]) / np.sqrt(6)
            d2x = np.hypot(c[2] - 2 * b[2] + a[2], c[3] - 2 * b[3] + a[3]) / np.sqrt(6)
            out[b[4]].append((z, d2z, d2z * fb / z ** 2, d2x, b[5]))
for cls, v in out.items():
    a = np.array(v)
    mad = lambda x: 1.4826 * np.median(np.abs(x - np.median(x)))
    print(cls, 'n', len(a), 'sigma_z(MAD) %.3f m  sigma_d(MAD) %.3f px  centroid 2nd-diff(MAD-ish) %.2f px med' % (mad(a[:, 1]), mad(a[:, 2]), np.median(a[:, 3]) / 1.18))
    for lo, hi in ((0, 1.5), (1.5, 3), (3, 6), (6, 20)):
        k = (a[:, 0] >= lo) & (a[:, 0] < hi)
        if k.sum() > 30: print('   z %.1f-%.1f n %d sigma_z %.3f sigma_d %.3f px  centroid %.2f px  p90|d2z| %.3f' % (lo, hi, k.sum(), mad(a[k, 1]), mad(a[k, 2]), np.median(a[k, 3]) / 1.18, np.percentile(np.abs(a[k, 1]), 90)))
