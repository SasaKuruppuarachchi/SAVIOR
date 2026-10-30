import json, sys, numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
R, V, S, Z, L, C, TZ = [], [], [], [], [], [], []
for r in rows:
    m = r.get('motion', {})
    for i in r['instances']:
        mo = i.get('motion')
        if not mo or mo.get('s_rad') is None or mo['s_rad'] > float(sys.argv[2]) if len(sys.argv) > 2 else 0.3: continue
        x0, y0, x1, y1 = i['bbox']
        R.append(np.hypot((x0 + x1) / 2 - 425, (y0 + y1) / 2 - 398)); V.append(mo['v_rad']); S.append(mo['s_rad']); Z.append(i['depth'] or np.nan)
        L.append(mo['v_lat']); C.append(i['cls']); TZ.append(m['t'][2] * 30 if m.get('t') else np.nan)
R, V, S, Z, L, TZ = map(np.array, (R, V, S, Z, L, TZ)); C = np.array(C)
print('n', len(R))
for cls in ('chair', 'person'):
    k = C == cls
    print(cls, 'n %d v_rad med %.3f mean %.3f  norm-med %.2f  v_lat med %.3f' % (k.sum(), np.median(V[k]), V[k].mean(), np.median(V[k] / S[k]), np.median(L[k])))
    for lo, hi in ((0, 100), (100, 200), (200, 280), (280, 340), (340, 500)):
        kk = k & (R >= lo) & (R < hi)
        if kk.sum() > 10: print('   r %3d-%3d n %4d v_rad med %+.3f  v_lat med %.3f  z med %.2f' % (lo, hi, kk.sum(), np.median(V[kk]), np.median(L[kk]), np.nanmedian(Z[kk])))
    for lo, hi in ((-1, -0.4), (-0.4, -0.1), (-0.1, 0.1), (0.1, 1)):
        kk = k & (TZ >= lo) & (TZ < hi)
        if kk.sum() > 10: print('   cam vz %+.1f..%+.1f n %4d v_rad med %+.3f' % (lo, hi, kk.sum(), np.median(V[kk])))
