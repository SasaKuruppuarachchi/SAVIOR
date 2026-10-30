#!/usr/bin/env python3
"""m2bsync.py [root] : per-run validity audit of M2b runs (<root>/<seq>/<method>/run_XX, default results/m2b_heldout/runs).
VALID iff: run_info status ok + returncode 0, non-empty trajectory, fork FINAL line present with fallback_latest =
fallback_empty = late_masks = 0 (savior launches), n_in_core = 0 (feature_stats.csv), AND the pose-count rule:
poses >= same-offset openvins poses - 1. Also: savior_none vs openvins md5 agreement per run.
Writes <root>/../tables/sync_audit{TAG}.md/.csv and prints invalid runs (one 'seq method run' per line in invalid{TAG}.txt)."""
import csv, glob, gzip, hashlib, os, re, sys
import yaml
ROOT = sys.argv[1] if len(sys.argv) > 1 else '/home/sasa/workspace/savior_ws/results/m2b_heldout/runs'
TAG = os.environ.get('TAG', '')
T = os.path.join(os.path.dirname(ROOT.rstrip('/')), 'tables')
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


def stamps(f):
    if not os.path.isfile(f):
        return 0, 0.0, 0.0
    t = [float(l.split()[0]) for l in open(f) if l.strip() and not l.startswith('#')]
    return (len(t), t[0], t[-1]) if t else (0, 0.0, 0.0)


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else ''


rows = []
for rd in sorted(glob.glob(f'{ROOT}/*/*/run_*')):
    seq, m, run = rd.split('/')[-3:]
    r = dict(seq=seq, method=m, run=run, status='?', traj=0, ov_traj=0, final='-', meas=0, exact=0, fb_latest=0, fb_empty=0,
             late=0, in_core=0, md5='', edge_too_late='')
    ri = {}
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml')) or {}
        r['status'] = f"{ri.get('status')}/{ri.get('returncode')}"
    except Exception:
        r['status'] = 'no_info'
    tf = f'{rd}/stamped_traj_estimate.txt'
    r['traj'], r['t0'], r['t1'] = stamps(tf)
    r['md5'] = md5(tf)
    savior = 'savior.launch.py' in str(ri.get('cmd', '')) if ri else True
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    if savior and lg:
        last = None
        for line in opn(lg):
            if 'SAVIOR-MASK] FINAL:' in line:
                last = line
            elif 'SAVIOR-EDGE] FINAL:' in line:
                g2 = re.search(r'too_late=(\d+)', line)
                r['edge_too_late'] = int(g2[1]) if g2 else -1
        g = FIN.search(last) if last else None
        if g:
            r.update(final='ok', meas=int(g[1]), exact=int(g[2]), fb_latest=int(g[3]), fb_empty=int(g[4]), late=int(g[5]))
    elif not savior:
        r['final'] = 'n/a'
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    ovf = f'{ROOT}/{seq}/openvins/{run}/stamped_traj_estimate.txt'
    n, o0, o1 = stamps(ovf)
    r['ov_traj'] = n if os.path.isfile(ovf) else -1
    # end-complete: last pose within one camera frame (0.05 s) of openvins' last pose; init delay = first-pose delay vs openvins
    r['end_ok'] = int(n > 0 and r['traj'] > 0 and r['t1'] >= o1 - 0.051) if m != 'openvins' else int(r['traj'] > 0)
    r['init_delay_s'] = round(r['t0'] - o0, 3) if n > 0 and r['traj'] > 0 else ''
    r['missing_after_init'] = (n - sum(1 for l in open(ovf) if l.strip() and not l.startswith('#') and float(l.split()[0]) < r['t0'] - 1e-6)
                               - r['traj']) if n > 0 and r['traj'] > 0 and m != 'openvins' else ''
    r['pose_ok'] = int(r['ov_traj'] > 0 and r['traj'] >= r['ov_traj'] - 1) if m != 'openvins' else int(r['traj'] > 0)
    r['sync_ok'] = int(r['status'] == 'ok/0' and r['traj'] > 0 and r['final'] in ('ok', 'n/a') and
                       r['fb_latest'] + r['fb_empty'] + r['late'] == 0 and r['in_core'] == 0)
    r['valid'] = int(r['sync_ok'] and r['pose_ok'])
    r['valid_end'] = int(r['sync_ok'] and r['end_ok'] and (r['missing_after_init'] in ('', ) or r['missing_after_init'] <= 1))
    rows.append(r)
# openvins itself: compare its pose count with the max of the other methods (reported only)
agg = {}
for r in rows:
    a = agg.setdefault(r['method'], dict(runs=0, valid=0, sync=0, pose=0, vend=0, fb=0, late=0, core=0, nofinal=0))
    a['runs'] += 1; a['valid'] += r['valid']; a['sync'] += r['sync_ok']; a['pose'] += r['pose_ok']; a['vend'] += r['valid_end']
    a['fb'] += r['fb_latest'] + r['fb_empty']; a['late'] += r['late']; a['core'] += r['in_core']; a['nofinal'] += r['final'] == '-'
L = [f'# M2b validity audit ({ROOT})\n', 'valid = clean exit + trajectory + FINAL fallback_latest = fallback_empty = late = 0 + n_in_core = 0 '
     '+ poses >= same-offset openvins poses - 1\n',
     'valid_end = sync ok + trajectory reaches the openvins end (<= 1 frame) + <= 1 pose missing after the method\'s own first pose (late init allowed)\n',
     '| method | runs | valid (literal pose rule) | valid_end | sync ok | pose rule ok | fallbacks | late | n_in_core | no FINAL |', '|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
for m, a in sorted(agg.items()):
    L.append(f"| {m} | {a['runs']} | {a['valid']} | {a['vend']} | {a['sync']} | {a['pose']} | {a['fb']} | {a['late']} | {a['core']} | {a['nofinal']} |")
L.append(f"\n**Total: {sum(r['valid'] for r in rows)} / {len(rows)} valid (literal pose rule); {sum(r['valid_end'] for r in rows)} / {len(rows)} valid_end; {sum(r['sync_ok'] for r in rows)} sync ok.**")
# pose-count deficit distribution
dd = {}
for r in rows:
    if r['method'] != 'openvins' and r['ov_traj'] > 0:
        d = r['ov_traj'] - r['traj']
        dd[d] = dd.get(d, 0) + 1
L.append('\nPose-count difference openvins - method (runs): ' + ', '.join(f'{k:+d}: {v}' for k, v in sorted(dd.items())))
# savior_none vs openvins
for dom, pat in (('warehouse', ('aisles', 'hall', 'dock')), ('viode', ('parking', 'city'))):
    same = tot = 0; diffs = []
    for r in rows:
        if r['method'] != 'savior_none' or not r['seq'].startswith(pat):
            continue
        o = next((x for x in rows if x['seq'] == r['seq'] and x['method'] == 'openvins' and x['run'] == r['run']), None)
        if o:
            tot += 1; same += r['md5'] == o['md5']
            if r['md5'] != o['md5']:
                diffs.append(f"{r['seq']}/{r['run']}")
    if tot:
        L.append(f'\nsavior_none == openvins (trajectory md5), {dom}: {same} / {tot}' + (f" (differ: {', '.join(diffs)})" if diffs else ''))
bad = [r for r in rows if not r['valid_end']]
late_init = [r for r in rows if r['sync_ok'] and r['end_ok'] and not r['pose_ok']]
L.append(f"\nRuns failing only the literal pose rule because of a later filter initialisation (end complete, sync ok): {len(late_init)}; "
         f"init delay vs openvins [s]: median {sorted(x['init_delay_s'] for x in late_init)[len(late_init) // 2] if late_init else '-'}, "
         f"max {max((x['init_delay_s'] for x in late_init), default='-')}")
if bad:
    L += ['\n## Invalid runs\n', '| seq | method | run | status | poses | openvins poses | FINAL | fb latest | fb empty | late | in core |',
          '|---|---|---|---|--:|--:|---|--:|--:|--:|--:|']
    L += [f"| {r['seq']} | {r['method']} | {r['run']} | {r['status']} | {r['traj']} | {r['ov_traj']} | {r['final']} | {r['fb_latest']} | "
          f"{r['fb_empty']} | {r['late']} | {r['in_core']} |" for r in bad]
os.makedirs(T, exist_ok=True)
open(f'{T}/sync_audit{TAG}.md', 'w').write('\n'.join(L) + '\n')
with open(f'{T}/sync_audit{TAG}.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
open(f'{T}/late_init{TAG}.txt', 'w').write(''.join(f"{r['seq']} {r['method']} {r['run']} {r['init_delay_s']} {r['ov_traj'] - r['traj']}\n" for r in late_init))
open(f'{T}/invalid{TAG}.txt', 'w').write(''.join(f"{r['seq']} {r['method']} {r['run']}\n" for r in bad))
print('\n'.join(L[:len(agg) + 12]))
print(f'{len(bad)} invalid')
