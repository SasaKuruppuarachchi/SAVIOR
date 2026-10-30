#!/usr/bin/env python3
"""sg_audit.py : validity, md5-identity and gate-counter audit of every SG-study run (results/semantic_gate/runs).

Per run (validity rule of GRID.yaml, = results/p7/scripts/p7sync.py + the back-end v2 pose rule):
  run_info status ok + returncode 0, non-empty trajectory, FINAL [SAVIOR-MASK] fallback_latest = fallback_empty =
  late_masks = 0 (savior launches), feature_stats n_in_core = 0, poses >= same-offset OpenVINS-v2 poses - 1.
Identity: ctl_<base> trajectories vs results/backend_v2/runs/<seq>/<base> (ctl_sf1_ms64 vs sens_fix1), byte md5;
inertness: sg_sXXX_bYYY_kbK (m_b != m_s) vs its twin sg_sXXX_bXXX_kbK.
Gate counters: last [SAVIOR-GATE] msckf / slam lines of launch.log (tested / rejected per label class, NIS lambda).
-> tables/audit.csv, tables/audit.md (run inside the image: scripts/sgpy.sh python3 scripts/sg_audit.py)"""
import csv, glob, gzip, hashlib, os, re
import yaml
WS = '/home/sasa/workspace/savior_ws'
SG = f'{WS}/results/semantic_gate'
BV2 = f'{WS}/results/backend_v2/runs'
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')
GATE = re.compile(r'\[SAVIOR-GATE\]: (\w+) updates=(\d+) tested bg/static/band=(\d+)/(\d+)/(\d+) rejected=(\d+)/(\d+)/(\d+) '
                  r'nis_lambda=([\d.]+)')
REF = {'ctl_openvins': 'openvins', 'ctl_savior_none': 'savior_none', 'ctl_sens_fix1': 'sens_fix1', 'ctl_sf1_ms64': 'sens_fix1'}


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


def npose(f):
    return sum(1 for _ in open(f)) if os.path.isfile(f) else 0


def twin(m):
    g = re.fullmatch(r'sg_s(\d{3})_b(\d{3})_kb(\d)', m)
    return f'sg_s{g[1]}_b{g[1]}_kb{g[3]}' if g and g[1] != g[2] else None


rows = []
for rd in sorted(glob.glob(f'{SG}/runs/*_t1_*/*/run_*')):
    seq, m, run = rd.split('/')[-3:]
    r = dict(seq=seq, method=m, run=run, status='?', poses=0, ov_poses=0, final='-', fb=0, late=0, in_core=0)
    tf = f'{rd}/stamped_traj_estimate.txt'
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml'))
        r['status'] = f"{ri.get('status')}/{ri.get('returncode')}"
        savior = 'savior.launch.py' in ' '.join(map(str, ri.get('cmd', [])))
    except Exception:
        r['status'], savior = 'no_info', True
    r['poses'] = npose(tf)
    r['ov_poses'] = npose(f'{BV2}/{seq}/openvins/{run}/stamped_traj_estimate.txt')
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    gate = {}
    if lg:
        last = None
        for line in opn(lg):
            if 'FINAL:' in line and 'SAVIOR-MASK' in line:
                last = line
            g = GATE.search(line)
            if g:
                gate[g[1]] = g
        if savior and last and FIN.search(last):
            g = FIN.search(last)
            r.update(final='ok', fb=int(g[3]) + int(g[4]), late=int(g[5]))
    if not savior:
        r['final'] = 'n/a'
    for k in ('msckf', 'slam'):
        g = gate.get(k)
        r[f'{k}_tested'] = '/'.join(g.group(3, 4, 5)) if g else ''
        r[f'{k}_rejected'] = '/'.join(g.group(6, 7, 8)) if g else ''
        r[f'{k}_lambda'] = float(g[9]) if g else ''
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    r['valid'] = int(r['status'] == 'ok/0' and r['poses'] > 0 and r['final'] in ('ok', 'n/a') and r['fb'] + r['late'] == 0
                     and r['in_core'] == 0 and r['poses'] >= r['ov_poses'] - 1)
    ref = REF.get(m)
    tw = twin(m)
    r['identity_ref'] = f'backend_v2/{ref}' if ref else (tw or '')
    other = f'{BV2}/{seq}/{ref}/{run}/stamped_traj_estimate.txt' if ref else (f'{SG}/runs/{seq}/{tw}/{run}/stamped_traj_estimate.txt' if tw else None)
    r['identical'] = '' if other is None else int(md5(tf) is not None and md5(tf) == md5(other))
    rows.append(r)

agg = {}
for r in rows:
    a = agg.setdefault(r['method'], dict(runs=0, valid=0, idn=0, idc=0, band=0))
    a['runs'] += 1
    a['valid'] += r['valid']
    if r['identical'] != '':
        a['idn'] += 1
        a['idc'] += r['identical']
    for k in ('msckf', 'slam'):
        if r[f'{k}_tested']:
            a['band'] += int(r[f'{k}_tested'].split('/')[2])
L = ['# SG study audit (t1)\n', 'valid = clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0, poses >= OpenVINS-v2 - 1. '
     'identical = byte-identical trajectory vs the reference (ctl_*: backend_v2 frozen run of the base method; '
     'sg m_b != m_s: the m_b = m_s twin). band tests = band-labelled chi2 tests (MSCKF + SLAM) over the runs.\n',
     '| variant | runs | valid | identical / compared | band-labelled chi2 tests |', '|---|--:|--:|--:|--:|']
for m, a in sorted(agg.items()):
    L.append(f"| {m} | {a['runs']} | {a['valid']} | {a['idc']} / {a['idn']} | {a['band']} |" if a['idn'] else
             f"| {m} | {a['runs']} | {a['valid']} | - | {a['band']} |")
bad = [r for r in rows if not r['valid'] or r['identical'] == 0]
if bad:
    L += ['\n## Invalid or non-identical runs\n', '| seq | variant | run | status | poses | ov poses | FINAL | fb | late | in core | identical |',
          '|---|---|---|---|--:|--:|---|--:|--:|--:|--:|']
    L += [f"| {r['seq']} | {r['method']} | {r['run']} | {r['status']} | {r['poses']} | {r['ov_poses']} | {r['final']} | {r['fb']} | "
          f"{r['late']} | {r['in_core']} | {r['identical']} |" for r in bad]
os.makedirs(f'{SG}/tables', exist_ok=True)
open(f'{SG}/tables/audit.md', 'w').write('\n'.join(L) + '\n')
if rows:
    with open(f'{SG}/tables/audit.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
print('\n'.join(L))
