#!/usr/bin/env python3
"""p7sync.py [method ...]: per-run sync check of P7 closed-loop runs (results/p7/<seq>/<method>/run_XX).
A run is VALID iff: run_info status ok + returncode 0, non-empty trajectory, fork FINAL line present with
fallback_latest=0 fallback_empty=0 late_masks=0 (savior launches only), and n_in_core = 0 in feature_stats.csv.
Writes tables/sync_check.md and tables/sync_check.csv; prints invalid runs. Host python (no ROS needed)."""
import csv, glob, gzip, os, re, sys
import yaml
P = os.environ.get('P7DIR', '/home/sasa/workspace/savior_ws/results/cpp_port/runs')   # P7DIR=.../p7/timing for stage F
only = set(sys.argv[1:])
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


rows = []
for rd in sorted(glob.glob(f'{P}/*_t1_*/*/run_*')):
    seq, m, run = rd.split('/')[-3:]
    if only and m not in only:
        continue
    r = dict(seq=seq, method=m, run=run, status='?', traj=0, final='-', meas=0, exact=0, fb_latest=0, fb_empty=0, late=0, in_core=0)
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
        r['status'] = f"{ri.get('status')}/{ri.get('returncode')}"
    except Exception:
        r['status'] = 'no_info'
    tf = f'{rd}/stamped_traj_estimate.txt'
    r['traj'] = sum(1 for _ in open(tf)) if os.path.isfile(tf) else 0
    # EDGE: complete trajectory (not cut at the bag end because the pipeline lagged): >= frozen-main run poses - 3
    rf = f'/home/sasa/workspace/savior_ws/results/p7/{seq}/sens_fix1/{run}/stamped_traj_estimate.txt'
    r['ref_traj'] = sum(1 for _ in open(rf)) if os.path.isfile(rf) else 0
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    savior = 'savior.launch.py' in open(f'{rd}/run_info.yaml').read() if os.path.isfile(f'{rd}/run_info.yaml') else True
    if lg and savior:
        last = None
        for line in opn(lg):
            if 'SAVIOR-MASK] FINAL:' in line:
                last = line
        if last:
            g = FIN.search(last)
            if g:
                r.update(final='ok', meas=int(g[1]), exact=int(g[2]), fb_latest=int(g[3]), fb_empty=int(g[4]), late=int(g[5]))
    elif not savior:
        r['final'] = 'n/a'
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            rd_ = csv.DictReader(fh)
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in rd_)
    r['valid'] = int(r['status'] == 'ok/0' and r['traj'] > 0 and r['traj'] >= r['ref_traj'] - 3 and r['final'] in ('ok', 'n/a') and
                     r['fb_latest'] + r['fb_empty'] + r['late'] == 0 and r['in_core'] == 0)
    rows.append(r)
agg = {}
for r in rows:
    a = agg.setdefault(r['method'], dict(runs=0, valid=0, fb=0, late=0, core=0, nofinal=0))
    a['runs'] += 1; a['valid'] += r['valid']; a['fb'] += r['fb_latest'] + r['fb_empty']; a['late'] += r['late']
    a['core'] += r['in_core']; a['nofinal'] += r['final'] == '-'
L = ['# P7 sync check (every closed-loop run; valid = clean exit, trajectory, FINAL fallback_latest = fallback_empty = late = 0, n_in_core = 0)\n',
     '| method | runs | valid | fallbacks | late | n_in_core | no FINAL line |', '|---|--:|--:|--:|--:|--:|--:|']
for m, a in sorted(agg.items()):
    L.append(f"| {m} | {a['runs']} | {a['valid']} | {a['fb']} | {a['late']} | {a['core']} | {a['nofinal']} |")
tot = dict(runs=sum(a['runs'] for a in agg.values()), valid=sum(a['valid'] for a in agg.values()))
L.append(f"\n**Total: {tot['valid']} / {tot['runs']} valid.**")
bad = [r for r in rows if not r['valid']]
if bad:
    L += ['\n## Invalid runs\n', '| seq | method | run | status | traj | FINAL | fb latest | fb empty | late | in core |', '|---|---|---|---|--:|---|--:|--:|--:|--:|']
    L += [f"| {r['seq']} | {r['method']} | {r['run']} | {r['status']} | {r['traj']} | {r['final']} | {r['fb_latest']} | {r['fb_empty']} | {r['late']} | {r['in_core']} |" for r in bad]
tag = os.environ.get('TAG', '')
T = '/home/sasa/workspace/savior_ws/results/cpp_port'
os.makedirs(f'{T}/tables', exist_ok=True)
open(f'{T}/tables/sync_check{tag}.md', 'w').write('\n'.join(L) + '\n')
with open(f'{T}/tables/sync_check{tag}.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
print('\n'.join(L))
