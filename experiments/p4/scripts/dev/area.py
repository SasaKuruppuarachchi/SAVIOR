import json, sys, numpy as np
from collections import defaultdict
for fn in sys.argv[1:]:
    rows = [json.loads(l) for l in open(fn)]
    A = defaultdict(float); N = 0
    for r in rows:
        for i in r['instances']:
            a = i.get('area', 0)
            A[(i['cls'], i['status'])] += a
            z = i.get('depth') or 99
            A[(i['cls'], i['status'], 'near' if z < 3 else 'far')] += a
    tot = len(rows) * 848 * 800
    print(fn.split('/')[-1], 'core %.4f ext %.4f' % (np.mean([r['core_px'] for r in rows]) / (848 * 800), np.mean([r['ext_px'] for r in rows]) / (848 * 800)))
    for k in sorted(A, key=lambda k: -A[k])[:14]: print('   ', k, '%.4f' % (A[k] / tot))
