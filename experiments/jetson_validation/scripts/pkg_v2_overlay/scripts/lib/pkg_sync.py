#!/usr/bin/env python3
"""pkg_sync.py <runs_root> [--json OUT] [--timing]: per-run validity of closed-loop runs <runs_root>/<seq>/<method>/run_XX.

VALID iff (= results/p7/scripts/p7sync.py + the M2b pose-count rule, final_config_addendum.yaml validity_m2b):
  run_info status ok and returncode 0; non-empty trajectory; for SAVIOR launches the fork FINAL line with
  fallback_latest = fallback_empty = late_masks = 0 (SAVIOR-edge also: [SAVIOR-EDGE] FINAL too_late = 0);
  n_in_core = 0 in feature_stats.csv; POSE COUNT: poses >= same-offset OpenVINS poses - 1 (this device's OpenVINS run
  if present, and the desktop OpenVINS run from reference/desktop_ate.json).
With --timing the sync / pose-count rules are reported but not required (rate 1.0 runs on a slower device can drop or
wait for frames; timing validity = clean exit + trajectory).
Prints one line per run and writes the json (list of rows + summary). Exit 0 if all valid."""
import csv, glob, gzip, json, os, re, sys
import yaml

FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')
EDGE = re.compile(r'\[SAVIOR-EDGE\] FINAL: .*?too_late=(\d+)')
PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def poses(f):
    if not os.path.isfile(f):
        return 0
    return sum(1 for ln in open(f) if ln.strip() and not ln.startswith('#'))


def check_run(rd):
    seq, m, run = rd.rstrip('/').split('/')[-3:]
    r = dict(seq=seq, method=m, run=run, status='?', poses=0, final='-', meas=0, fb_latest=0, fb_empty=0, late=0,
             too_late=0, in_core=0, rate=None, wall_s=None, fake=os.path.isfile(f'{rd}/FAKE'))
    savior = True
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
        r['status'] = f"{ri.get('status')}/{ri.get('returncode')}"
        r['wall_s'] = ri.get('wall_time_s')
        cmd = ri.get('cmd') or []
        savior = any('savior.launch.py' in c for c in cmd)
        r['rate'] = next((float(c.split(':=')[1]) for c in cmd if c.startswith('rate:=')), None)
    except Exception:  # noqa: BLE001
        r['status'] = 'no_info'
    r['poses'] = poses(f'{rd}/stamped_traj_estimate.txt')
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    if not savior:
        r['final'] = 'n/a'
    elif lg:
        last = edge = None
        op = gzip.open if lg.endswith('.gz') else open
        for line in op(lg, 'rt', errors='replace'):
            if 'SAVIOR-MASK] FINAL:' in line or ('FINAL:' in line and 'measurements' in line):
                last = line
            if '[SAVIOR-EDGE] FINAL:' in line:
                edge = line
        g = FIN.search(last or '')
        if g:
            r.update(final='ok', meas=int(g[1]), fb_latest=int(g[3]), fb_empty=int(g[4]), late=int(g[5]))
        e = EDGE.search(edge or '')
        if e:
            r['too_late'] = int(e[1])
        elif m.startswith('savior_edge'):
            r['final'] = 'no_edge_final' if r['final'] == 'ok' else r['final']
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    r['sync_ok'] = int(r['final'] in ('ok', 'n/a') and r['fb_latest'] + r['fb_empty'] + r['late'] + r['too_late'] == 0
                       and r['in_core'] == 0)
    r['exit_ok'] = int(r['status'] == 'ok/0' and r['poses'] > 0)
    return r


def main():
    root = sys.argv[1]
    out = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    timing = '--timing' in sys.argv
    ref = json.load(open(f'{PKG}/reference/desktop_ate.json'))['runs']
    rows = [check_run(rd) for rd in sorted(glob.glob(f'{root}/*_t1_*/*/run_[0-9][0-9]'))]
    ov = {(r['seq'], r['run']): r['poses'] for r in rows if r['method'] == 'openvins' and r['exit_ok']}
    for r in rows:
        dref = ref.get(r['seq'], {}).get('openvins', {}).get('trials', {}).get(r['run'], {}).get('n_poses')
        if os.environ.get('SJ_BACKEND', 'v1') != 'v1':
            dref = None   # v2: the desktop reference pose counts are back-end v1 (20 Hz poses); only this device's openvins applies
        r['ov_poses_device'] = ov.get((r['seq'], r['run'])) if r['method'] != 'openvins' else None
        r['ov_poses_desktop'] = dref
        refs = [x for x in (r['ov_poses_device'], dref) if x]
        r['pose_ok'] = int(not refs or r['poses'] >= max(refs) - 1)
        r['valid'] = int(r['exit_ok'] and (timing or (r['sync_ok'] and r['pose_ok'])))
        flag = 'VALID  ' if r['valid'] else 'INVALID'
        print(f"{flag} {r['seq']:13s} {r['method']:12s} {r['run']} status={r['status']} poses={r['poses']} "
              f"(ov dev {r['ov_poses_device']}, desk {r['ov_poses_desktop']}) final={r['final']} fb={r['fb_latest']}+{r['fb_empty']} "
              f"late={r['late']} too_late={r['too_late']} in_core={r['in_core']} rate={r['rate']}{' FAKE' if r['fake'] else ''}")
    summ = dict(runs=len(rows), valid=sum(r['valid'] for r in rows), sync_ok=sum(r['sync_ok'] for r in rows),
                pose_ok=sum(r['pose_ok'] for r in rows), mode='timing' if timing else 'accuracy')
    print(f"SYNC SUMMARY: {summ['valid']}/{summ['runs']} valid ({summ['mode']})")
    if out:
        json.dump(dict(summary=summ, rows=rows), open(out, 'w'), indent=1)
    sys.exit(0 if summ['valid'] == summ['runs'] and rows else 1)


if __name__ == '__main__':
    main()
