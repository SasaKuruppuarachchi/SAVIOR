import json, sys, numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
gt = np.loadtxt(sys.argv[2])
ts = []; tn = []
prev = None
for r in rows:
    t = r['stamp_ns'] * 1e-9
    m = r.get('motion', {})
    if m.get('t') and prev is not None and m.get('t_ok'):
        ts.append(t); tn.append(np.linalg.norm(m['t']) / (t - prev))
    prev = t
ts, tn = np.array(ts), np.array(tn)
# GT speed (smooth over 0.2 s)
g_t, g_p = gt[:, 0], gt[:, 1:4]
sp = []
for t in ts:
    i0, i1 = np.searchsorted(g_t, t - 0.1), np.searchsorted(g_t, t + 0.1)
    i1 = min(i1, len(g_t) - 1)
    sp.append(np.linalg.norm(g_p[i1] - g_p[i0]) / max(g_t[i1] - g_t[i0], 1e-3) if i1 > i0 else np.nan)
sp = np.array(sp)
ok = np.isfinite(sp) & (sp > 0.15)
print('n', ok.sum(), 'GT speed med %.3f  est med %.3f  ratio est/gt med %.3f p25 %.3f p75 %.3f' % (np.median(sp[ok]), np.median(tn[ok]), np.median(tn[ok] / sp[ok]), np.percentile(tn[ok] / sp[ok], 25), np.percentile(tn[ok] / sp[ok], 75)))
for q in range(0, len(ts), 150):
    print('%.2f gt %.3f est %.3f' % (ts[q] - ts[0], sp[q], tn[q]))
