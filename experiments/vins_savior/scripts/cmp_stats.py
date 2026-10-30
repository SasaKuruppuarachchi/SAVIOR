"""cmp_stats.py <offline stats.jsonl.gz> <online savior_stats.jsonl.gz> : per-stamp agreement of the /savior/stats
records of an offline export and an online (OpenVINS) run. Compared: every field except timings / IMU wall wait."""
import gzip, json, sys
DROP = {'timings_ms', 'imu'}
def load(p):
    out = {}
    for l in gzip.open(p, 'rt'):
        d = json.loads(l); st = d['stamp']['sec'] * 10**9 + d['stamp']['nanosec']
        m = d.get('motion', {});
        if isinstance(m, dict): m.pop('ms', None)
        out[st] = {k: v for k, v in d.items() if k not in DROP}
    return out
a, b = load(sys.argv[1]), load(sys.argv[2])
common = sorted(set(a) & set(b))
same = lambda x, y: all(x[k] == y[k] for k in set(x) & set(y))   # non-compact (P6) online stats carry extra keys
eq = sum(same(a[s], b[s]) for s in common)
core = sum(a[s].get('core_px') == b[s].get('core_px') and a[s].get('ext_px') == b[s].get('ext_px') for s in common)
first = next((s for s in common if not same(a[s], b[s])), None)
res = dict(n_offline=len(a), n_online=len(b), n_common=len(common), records_equal=eq, core_ext_px_equal=core,
           only_offline=len(set(a) - set(b)), only_online=len(set(b) - set(a)), first_diff=first)
if first is not None:
    res['diff_keys'] = sorted(k for k in set(a[first]) & set(b[first]) if a[first][k] != b[first][k])
print(json.dumps(res))
