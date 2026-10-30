#!/usr/bin/env python3
"""summarize.py <root> : ATE table (posyaw / se3 / sim3) from eval_<align>/eval_summary.yaml of every
<root>/<dataset>_<seq>/<method>/ plus per-frame timing from run_XX/timing.csv. Failure = ATE > 1 m or no estimate.
Prints markdown to stdout (no files written)."""
import csv, glob, math, os, statistics as st, sys
import yaml

ROOT = sys.argv[1]
PUB = {  # DynaVINS++ (RA-L 2024) Table II, ATE RMSE [m], stereo-inertial; None = diverged
    'vins_fusion': {'city_day': [.150, .203, .234, .373], 'city_night': [.317, .507, .494, .828], 'parking_lot': [.121, .121, .212, .300]},
    'dynavins': {'city_day': [.171, .178, .206, .285], 'city_night': [.266, .295, .321, .275], 'parking_lot': [.079, .123, .095, .148]},
    'orbslam3': {'city_day': [.302, .419, .217, None], 'city_night': [.709, .895, 1.693, 3.006], 'parking_lot': [.148, .067, None, None]},
}
LV = ['none', 'low', 'mid', 'high']


def ate(d, a):
    f = os.path.join(d, 'eval_%s' % a, 'eval_summary.yaml')
    if not os.path.isfile(f):
        return {}
    y = yaml.safe_load(open(f))
    return {t['name']: (t['ate']['trans_m']['rmse'] if t.get('status') == 'ok' else math.inf) for t in y['trials']}


def fmt(v):
    return 'fail' if v is None or not math.isfinite(v) else ('%.3f*' % v if v > 1 else '%.3f' % v)


def pub(m, seq):
    base = m.split('+')[0].replace('_fromstart', '')
    env, lv = seq.rsplit('_', 1)
    v = PUB.get(base, {}).get(env)
    if not v:
        return ''
    x = v[LV.index(lv)]
    return 'div.' if x is None else '%.3f' % x


rows, tim = [], {}
for d in sorted(glob.glob(os.path.join(ROOT, '*_*', '*'))):
    if not os.path.isdir(d):
        continue
    seq = os.path.basename(os.path.dirname(d)).split('_', 1)[1]
    m = os.path.basename(d)
    runs = sorted(glob.glob(os.path.join(d, 'run_*')))
    r = {a: ate(d, a) for a in ('posyaw', 'se3', 'sim3')}
    names = [os.path.basename(x) for x in runs]
    vals = {a: [r[a].get(n, math.inf) for n in names] for a in r}
    nf = sum(1 for v in vals['posyaw'] if not v <= 1.0)
    med = {a: (st.median(v) if v else math.nan) for a, v in vals.items()}
    rows.append((seq, m, len(names), nf, med, vals, pub(m, seq)))
    for x in runs:  # timing
        f = os.path.join(x, 'timing.csv')
        if not os.path.isfile(f):
            continue
        rr = [z for z in csv.DictReader(open(f)) if z.get('ms') not in (None, '')]
        key = m.split('+')[0].replace('_fromstart', '')
        t = tim.setdefault(key, {})
        if not rr:
            continue
        if 'kind' in rr[0]:
            for k in ('frontend', 'backend'):
                t.setdefault(k, []).extend(float(z['ms']) for z in rr if z['kind'] == k)
        else:
            t.setdefault('track', []).extend(float(z['ms']) for z in rr)

print('| seq | method | runs | fail(posyaw>1m) | posyaw median | se3 median | sim3 median | posyaw per run | published |')
print('|---|---|--:|--:|--:|--:|--:|---|--:|')
for seq, m, n, nf, med, vals, p in rows:
    print('| %s | %s | %d | %d | %s | %s | %s | %s | %s |' % (seq, m, n, nf, fmt(med['posyaw']), fmt(med['se3']), fmt(med['sim3']),
          ' '.join(fmt(v) for v in vals['posyaw']), p))
print('\n| method | component | n frames | median ms | mean ms | p90 ms |')
print('|---|---|--:|--:|--:|--:|')
for m, t in sorted(tim.items()):
    for k, v in t.items():
        v = sorted(v)
        print('| %s | %s | %d | %.1f | %.1f | %.1f |' % (m, k, len(v), st.median(v), st.mean(v), v[int(.9 * len(v))]))
