#!/usr/bin/env python3
"""rr_audit.py <root> <ref root> <tag> : validity audit of review runs (<root>/<seq>/<variant>/run_XX) with the rules of
results/m2b_heldout/scripts/m2bsync.py and results/backend_v2/heldout/tables/AUDIT_NOTE.md:
  sync_ok   : run_info ok/0, non-empty trajectory, (savior launches) fork FINAL line with fallback_latest = fallback_empty =
              late_masks = 0, n_in_core = 0 (feature_stats.csv)
  pose_ok   : poses >= same-offset OpenVINS-v2 poses - 1 (reference = <ref root>/<seq>/openvins, the existing back-end v2 runs)
  end_ok    : last pose >= reference last pose - 0.101 s (one processed 10 Hz frame, AUDIT_NOTE) and <= 1 pose missing after
              the run's own first pose (later filter initialisation allowed and flagged)
  valid     = sync_ok and end_ok
md5 controls: variants named ctl_<m> are compared with <ref root>/<seq>/<m> (same offset, trajectory md5).
-> results/review_runs/tables/audit_<tag>.md / .csv"""
import csv, glob, gzip, hashlib, os, re, sys
import yaml
ROOT, REF, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
REFM = os.environ.get('REFM', 'openvins')   # reference method dir (E: e_openvins)
T = '/home/sasa/workspace/savior_ws/results/review_runs/tables'
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')


def stamps(f):
    if not os.path.isfile(f):
        return []
    return [float(l.split()[0]) for l in open(f) if l.strip() and not l.startswith('#')]


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else ''


rows = []
for rd in sorted(glob.glob(f'{ROOT}/*/*/run_*')):
    if os.path.islink(os.path.dirname(rd)):
        continue
    seq, m, run = rd.split('/')[-3:]
    r = dict(seq=seq, variant=m, run=run, status='?', final='-', fb=0, late=0, in_core=0)
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml')) or {}
        r['status'] = f"{ri.get('status')}/{ri.get('returncode')}"
    except Exception:
        ri = {}; r['status'] = 'no_info'
    t = stamps(f'{rd}/stamped_traj_estimate.txt')
    r['poses'] = len(t)
    savior = 'savior.launch.py' in str(ri.get('cmd', ''))
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    if savior and lg:
        last = None
        with (gzip.open(lg, 'rt', errors='replace') if lg.endswith('.gz') else open(lg, errors='replace')) as fh:
            for line in fh:
                if 'SAVIOR-MASK] FINAL:' in line:
                    last = line
        g = FIN.search(last) if last else None
        if g:
            r.update(final='ok', fb=int(g[3]) + int(g[4]), late=int(g[5]))
    elif not savior:
        r['final'] = 'n/a'
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    o = stamps(f'{REF}/{seq}/{REFM}/{run}/stamped_traj_estimate.txt')
    r['ref_poses'] = len(o)
    r['sync_ok'] = int(r['status'] == 'ok/0' and len(t) > 0 and r['final'] in ('ok', 'n/a') and r['fb'] + r['late'] == 0
                       and r['in_core'] == 0)
    r['pose_ok'] = int(len(o) > 0 and len(t) >= len(o) - 1)
    r['init_delay_s'] = round(t[0] - o[0], 3) if t and o else ''
    miss = (len(o) - sum(1 for x in o if x < t[0] - 1e-6) - len(t)) if t and o else 99
    r['end_ok'] = int(bool(t) and bool(o) and t[-1] >= o[-1] - 0.101 and miss <= 1)
    r['valid'] = int(r['sync_ok'] and r['end_ok'])
    r['md5'] = md5(f'{rd}/stamped_traj_estimate.txt')
    if m.startswith('ctl_'):
        r['ctl_same'] = int(r['md5'] == md5(f'{REF}/{seq}/{m[4:]}/{run}/stamped_traj_estimate.txt'))
        if m == 'ctl_savior_none':
            r['ctl_same'] &= int(r['md5'] == md5(f'{REF}/{seq}/openvins/{run}/stamped_traj_estimate.txt'))
    if m == 'e_savior_none':
        r['ctl_same'] = int(r['md5'] == md5(f'{ROOT}/{seq}/e_openvins/{run}/stamped_traj_estimate.txt'))
    rows.append(r)
agg = {}
for r in rows:
    a = agg.setdefault(r['variant'], dict(runs=0, valid=0, sync=0, pose=0, end=0, fb=0, late=0, core=0, nofinal=0, ctl=0, ctln=0))
    a['runs'] += 1; a['valid'] += r['valid']; a['sync'] += r['sync_ok']; a['pose'] += r['pose_ok']; a['end'] += r['end_ok']
    a['fb'] += r['fb']; a['late'] += r['late']; a['core'] += r['in_core']; a['nofinal'] += r['final'] == '-'
    if 'ctl_same' in r:
        a['ctl'] += r['ctl_same']; a['ctln'] += 1
L = [f'# Review-run validity audit: {TAG}\n', f'root {ROOT}; reference OpenVINS-v2 runs {REF}\n',
     'valid = sync ok (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0) + end ok (last pose within 0.101 s of '
     'the same-offset OpenVINS-v2 end, <= 1 pose missing after the own first pose). pose rule = poses >= OpenVINS-v2 - 1 '
     '(failing it with end ok = later filter initialisation, kept and flagged).\n',
     '| variant | runs | valid | sync ok | pose rule ok | end ok | fallbacks | late | n_in_core | no FINAL | md5 control |',
     '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|']
for m, a in sorted(agg.items()):
    L.append(f"| {m} | {a['runs']} | {a['valid']} | {a['sync']} | {a['pose']} | {a['end']} | {a['fb']} | {a['late']} | {a['core']} | "
             f"{a['nofinal']} | {str(a['ctl']) + ' / ' + str(a['ctln']) + ' identical' if a['ctln'] else '-'} |")
L.append(f"\n**Total: {sum(r['valid'] for r in rows)} / {len(rows)} valid; {sum(r['sync_ok'] for r in rows)} sync ok; "
         f"{sum(r['pose_ok'] for r in rows)} pass the literal pose rule.**")
late = [r for r in rows if r['valid'] and not r['pose_ok']]
if late:
    L.append(f"\nLater filter initialisation (valid, pose rule failed): {len(late)}; init delay [s] median "
             f"{sorted(r['init_delay_s'] for r in late)[len(late) // 2]}, max {max(r['init_delay_s'] for r in late)}: "
             + ', '.join(f"{r['seq']}/{r['variant']}/{r['run']}" for r in late))
bad = [r for r in rows if not r['valid']]
if bad:
    L += ['\n## Invalid runs\n', '| seq | variant | run | status | poses | ref poses | FINAL | fb | late | in core | end ok |',
          '|---|---|---|---|--:|--:|---|--:|--:|--:|--:|']
    L += [f"| {r['seq']} | {r['variant']} | {r['run']} | {r['status']} | {r['poses']} | {r['ref_poses']} | {r['final']} | {r['fb']} | "
          f"{r['late']} | {r['in_core']} | {r['end_ok']} |" for r in bad]
os.makedirs(T, exist_ok=True)
open(f'{T}/audit_{TAG}.md', 'w').write('\n'.join(L) + '\n')
with open(f'{T}/audit_{TAG}.csv', 'w') as fh:
    w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
    w.writeheader(); w.writerows(rows)
open(f'{T}/invalid_{TAG}.txt', 'w').write(''.join(f"{r['seq']} {r['variant']} {r['run']}\n" for r in bad))
print('\n'.join(L[:5 + len(agg) + 3]))
