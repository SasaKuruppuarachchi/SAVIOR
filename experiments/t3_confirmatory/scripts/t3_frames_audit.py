#!/usr/bin/env python3
"""t3_frames_audit.py : AMENDMENT_02 section 1 validity rule (all methods) for the t3 confirmatory split:
    frames processed by the estimator == stereo pairs in the bag after the start offset, +-0.
Separate from the frozen results/m2b_heldout/scripts/m2bsync.py (which is unchanged and still applied).
Based on results/real_world/scripts/rw_analyze.py (frame counting) + rw_expected_frames.py (expected counts).

Processed frames (as rw_analyze.py, FREEZE_AMENDMENT 2 of results/real_world):
  OpenVINS family : the '[TIME]: ... seconds total' lines of run_XX/launch.log(.gz) (ROS2Visualizer prints one per stereo
                    frame fed to the filter).
  VINS family     : the 'frontend' rows of run_XX/timing.csv (vins_node writes one per synchronised stereo pair received);
                    also used for DynaVINS and DynaVINS + masks.
Expected (rw_expected_frames.py semantics: pairs whose bag time >= bag start + offset; ros2 bag play --start-offset /
rosbag play -s are relative to the earliest message of the bag):
  ros2 (OpenVINS family): data/warehouse/ros2_stereoseg/<seq> (all topics -> bag start), cam0/cam1 pairs (same header stamp).
      The warehouse bags are 20 Hz, but back-end v2 sets track_frequency 10.5 (results/backend_v2/backend_config.yaml): the
      UNCHANGED ROS2Visualizer::callback_stereo drops a pair whose stamp < last kept stamp + 1/track_frequency BEFORE the
      filter. The number of pairs the estimator must process is therefore the bag pairs after the offset passed through that
      deterministic rule (track_frequency read from the run's own config/estimator_config.yaml), and a frame is only fed
      once an IMU message newer than it has arrived (callback_inertial), so a final pair with no later IMU sample is not
      counted. The plain 'bag pairs after the offset' number is reported alongside ('pairs').
  ros1 (VINS family): the ROS 1 bag holds /cam0/image_raw /cam1/image_raw /imu0 only (run_t3.sh ros1_bag, rosbags-convert
      keeps the bag times), so its start = earliest of those three topics in the ros2 bag; every pair is received. rosbag
      play -s applies the offset as a 32-bit float (see offset_ns).
Offsets: run_info.yaml (start_offset:= in cmd, or start_offset key); else run index -> offsets file (run_XX = XX-th offset;
the P9 mask images write no run_info.yaml, a pre-existing run_one.sh COMMITS.txt bug).

AMENDMENT_05 (clarification): a run is also valid if exactly one frame is missing and it is the last expected stereo pair
(OpenVINS: last pose stamp == second-to-last expected frame; VINS: last frontend stamp == second-to-last pair). Both counts are
written: frames_invalid<TAG>.txt (clarified, used for re-runs), frames_invalid_strict<TAG>.txt, frames_tail_only<TAG>.txt.

AMENDMENT_06: every expected method dir (EXPECT: 12 OpenVINS-v2-family, 7 VINS-family, 6 DynaVINS+masks) must exist for every
sequence of the offsets file; an absent dir gives 5 'method dir missing' rows (invalid -> re-run). A paused / truncated VINS run
is caught by the frame rule itself (frontend rows == ROS 1 bag pairs after the offset, or the AMENDMENT_05 tail clause).

Usage (savior image; t3 HDD data mounted read-only):
  t3_frames_audit.py [--ov ROOT] [--vins ROOT] [--dyna ROOT] [--offsets FILE] [--runs-per-method N] [--out DIR] [--tag TAG]
  defaults: --ov results/t3_confirmatory/runs --vins results/t3_confirmatory/vins_runs --out results/t3_confirmatory/tables
  (a root that does not exist is skipped). Writes <out>/frames_audit<TAG>.md/.csv and <out>/frames_invalid<TAG>.txt
  ('<family> <seq> <method> <run>' per line). Expected counts are cached in <out>/expected_frames<TAG>.yaml."""
import argparse
import csv
import glob
import gzip
import os
import re
import struct
import sys

import numpy as np
import yaml

WS = '/home/sasa/workspace/savior_ws'
T = WS + '/results/t3_confirmatory'
BAGS = WS + '/data/warehouse/ros2_stereoseg'
TIME_RE = re.compile(r'\[TIME\]: .* seconds total')
OFF_RE = re.compile(r'start_offset:=([0-9.]+)')
ROS1_TOPICS = ('/cam0/image_raw', '/cam1/image_raw', '/imu0')


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


# ------------------------------------------------------------------ bag stamps
def bag_stamps(seq):
    """bag times + header stamps (ns) of cam0, cam1, imu0; ros2 start (all topics) and ros1 start (cam0/cam1/imu0)."""
    from pathlib import Path
    from rosbags.rosbag2 import Reader
    bt = {k: [] for k in ROS1_TOPICS}
    hs = {k: [] for k in ROS1_TOPICS}
    t_all = []
    with Reader(Path(f'{BAGS}/{seq}')) as r:
        for c, t, raw in r.messages():
            t_all.append(t)
            if c.topic in bt:
                bt[c.topic].append(t)
                sec, nsec = struct.unpack_from('<iI', raw, 4)   # CDR: 4-byte encapsulation, then header.stamp
                hs[c.topic].append(sec * 1000000000 + nsec)
    return ({k: np.array(v, np.int64) for k, v in bt.items()}, {k: np.array(v, np.int64) for k, v in hs.items()},
            int(min(t_all)), int(min(min(v) for v in bt.values())))


def offset_ns(kind, off):
    """start offset in ns as the player applies it. ros2 bag play --start-offset: double seconds. rosbag play -s (ROS 1):
    the C++ player parses the option as a FLOAT (32 bit) and builds ros::Duration(float) (sec = floor, nsec = round), so e.g.
    0.4 -> 0.400000006 s -> 400000006 ns: a frame exactly at bag start + 0.4 s is NOT played. Verified on the t2 VINS-Fusion /
    DynaVINS runs (one frame fewer at 0.2/0.4/0.6/0.8/1.2/1.6 s, none at 0.0/1.0/1.4/1.8 s, exactly the float32 rounding)."""
    if kind == 'ros2':
        return int(round(off * 1e9))
    d = float(np.float32(off))
    sec = int(np.floor(d))
    return sec * 1000000000 + int(round((d - sec) * 1e9))


class Expected:
    def __init__(self, cache):
        self.cache_f = cache
        self.cache = yaml.safe_load(open(cache)) if os.path.isfile(cache) else {}
        self.st = {}
        self.dirty = False

    def _stamps(self, seq):
        if seq not in self.st:
            self.st[seq] = bag_stamps(seq)
        return self.st[seq]

    def get(self, seq, kind, off, trk=None):
        key = f'{kind}:{off:.1f}' + (f':trk{trk:g}' if trk else '') + ':v2'   # v2: + last2 (AMENDMENT_05)
        c = self.cache.setdefault(seq, {})
        if key not in c:
            bt, hs, s2, s1 = self._stamps(seq)
            t0 = (s2 if kind == 'ros2' else s1) + offset_ns(kind, off)
            c0 = set(hs['/cam0/image_raw'][bt['/cam0/image_raw'] >= t0].tolist())
            c1 = set(hs['/cam1/image_raw'][bt['/cam1/image_raw'] >= t0].tolist())
            pairs = sorted(c0 & c1)
            out = {'pairs': len(pairs), 'last2': [int(x) for x in pairs[-2:]]}
            if kind == 'ros2':
                imu = hs['/imu0'][bt['/imu0'] >= t0]
                imu_last = int(imu.max()) if imu.size else -1
                dt = 1.0 / float(trk)
                last, kept = None, []
                for s in pairs:   # ROS2Visualizer::callback_stereo drop rule, in double seconds as in the C++ code
                    ts = (s // 1000000000) + (s % 1000000000) * 1e-9
                    if last is not None and ts < last + dt:
                        continue
                    last = ts
                    kept.append(s)
                out['kept'] = len(kept)
                fed = [s for s in kept if s < imu_last]   # needs an IMU sample newer than the frame
                out['fed'] = len(fed)
                out['last2'] = [int(x) for x in fed[-2:]]   # the last two frames the estimator must process
            c[key] = out
            self.dirty = True
        return c[key]

    def save(self):
        if self.dirty:
            yaml.safe_dump(self.cache, open(self.cache_f, 'w'), sort_keys=True)


# ------------------------------------------------------------------ runs
def offsets_map(f):
    m = {}
    if f and os.path.isfile(f):
        for l in open(f):
            p = l.split()
            if len(p) >= 2 and not l.startswith('#'):
                m[p[0]] = [float(x) for x in p[1].split(',')]
    return m


def run_offset(rd, seq, offs):
    ri = {}
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml')) or {}
    except Exception:
        pass
    if 'start_offset' in ri:
        return float(ri['start_offset']), 'run_info'
    g = OFF_RE.search(' '.join(map(str, ri.get('cmd', []))))
    if g:
        return float(g[1]), 'run_info'
    i = int(rd.rsplit('_', 1)[1])
    if seq in offs and i <= len(offs[seq]):
        return offs[seq][i - 1], 'offsets_file'
    return None, 'unknown'


def track_frequency(rd):
    f = f'{rd}/config/estimator_config.yaml'
    if os.path.isfile(f):
        for l in open(f):
            g = re.match(r'\s*track_frequency:\s*([0-9.eE+-]+)', l)
            if g:
                return float(g[1])
    return None


def ov_frames(rd):
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    return sum(1 for line in opn(lg) if TIME_RE.search(line)) if lg else 0


def vins_frames(rd):
    tc = f'{rd}/timing.csv'
    if not os.path.isfile(tc):
        return 0
    with open(tc) as fh:
        return sum(1 for x in csv.DictReader(fh) if x.get('kind') == 'frontend')


def last_stamp_ov(rd):
    """stamp (ns) of the last pose OpenVINS wrote (one pose per processed frame after initialisation), None if none"""
    f = f'{rd}/stamped_traj_estimate.txt'
    last = None
    if os.path.isfile(f):
        for l in open(f):
            if l.strip() and not l.startswith('#'):
                last = l.split()[0]
    if last is None:
        return None
    a, _, b = last.partition('.')
    return int(a) * 1000000000 + int((b + '000000000')[:9])


def last_stamp_vins(rd):
    tc = f'{rd}/timing.csv'
    last = None
    if os.path.isfile(tc):
        with open(tc) as fh:
            for x in csv.DictReader(fh):
                if x.get('kind') == 'frontend':
                    last = x['stamp']
    if last is None:
        return None
    a, _, b = last.partition('.')
    return int(a) * 1000000000 + int((b + '000000000')[:9])


def tail_only(r, e, last):
    """AMENDMENT_05: exactly one frame short and it is the last expected stereo pair (the last processed frame is the
    second-to-last expected one; 1 ms tolerance on the printed stamp)"""
    return int(r['diff'] == -1 and last is not None and len(e['last2']) == 2 and abs(last - e['last2'][0]) < 1000000)


EXPECT_ON = True
EXPECT = {'ov': 'openvins savior_none yolo_naive sens_fix1 oracle_moving_ext oracle_class_ext savior_edge ovchi_best sf1_chibest '
                 'sf1_nis ov_nis savior_sg'.split(),
          'vins': 'vins_fusion vins_zero vins_savior vins_ycls vins_odyn vins_ocls dynavins'.split(),
          'dyna': 'dyna_det dyna_zero dyna_savior dyna_ycls dyna_odyn dyna_ocls'.split()}


def missing_methods(fam, root, offs, nruns, rows):
    """AMENDMENT_06 check: every expected method dir exists for every sequence of the offsets file (else nruns 'run missing'
    rows per absent method dir, which the re-run step then runs)"""
    for seq in sorted(offs):
        for m in EXPECT[fam]:
            md = f'{root}/{seq}/{m}' if fam == 'ov' else f'{root}/warehouse_{seq}/{m}'
            if not os.path.isdir(md):
                for i in range(1, (nruns or 0) + 1):
                    rows.append(dict(family=fam, seq=seq, method=m, run=f'run_{i:02d}', offset='', off_src='missing', frames=0,
                                     expected=-1, pairs=-1, trk='', diff='', ok_strict=0, tail_only=0, ok=0, note='method dir missing'))


def audit(fam, root, exp, offs, nruns, rows):
    if not root or not os.path.isdir(root):
        return
    if EXPECT_ON:
        missing_methods(fam, root, offs, nruns, rows)
    for md in sorted(glob.glob(f'{root}/*/*/')):
        md = md.rstrip('/')
        m = os.path.basename(md)
        sd = os.path.basename(os.path.dirname(md))
        seq = sd[len('warehouse_'):] if fam != 'ov' and sd.startswith('warehouse_') else sd
        if not os.path.isdir(f'{BAGS}/{seq}'):
            continue   # not a warehouse sequence (e.g. VIODE in the held-out smoke roots)
        rds = sorted(glob.glob(f'{md}/run_[0-9][0-9]'))
        have = {int(r.rsplit('_', 1)[1]) for r in rds}
        for i in range(1, (nruns or 0) + 1):
            if i not in have:
                rows.append(dict(family=fam, seq=seq, method=m, run=f'run_{i:02d}', offset='', off_src='missing', frames=0,
                                 expected=-1, pairs=-1, trk='', diff='', ok_strict=0, tail_only=0, ok=0, note='run missing'))
        for rd in rds:
            off, src = run_offset(rd, seq, offs)
            r = dict(family=fam, seq=seq, method=m, run=os.path.basename(rd), offset=off, off_src=src, note='')
            if off is None:
                r.update(frames=-1, expected=-1, pairs=-1, trk='', diff='', ok_strict=0, tail_only=0, ok=0, note='no offset')
                rows.append(r)
                continue
            if fam == 'ov':
                trk = track_frequency(rd)
                if trk is None:
                    r.update(frames=ov_frames(rd), expected=-1, pairs=-1, trk='', diff='', ok_strict=0, tail_only=0, ok=0, note='no run config')
                    rows.append(r)
                    continue
                e = exp.get(seq, 'ros2', off, trk)
                r.update(frames=ov_frames(rd), expected=e['fed'], pairs=e['pairs'], trk=trk)
            else:
                e = exp.get(seq, 'ros1', off)
                r.update(frames=vins_frames(rd), expected=e['pairs'], pairs=e['pairs'], trk='')
            r['diff'] = r['frames'] - r['expected']
            r['ok_strict'] = int(r['diff'] == 0)
            r['tail_only'] = tail_only(r, e, last_stamp_ov(rd) if fam == 'ov' else last_stamp_vins(rd))
            r['ok'] = int(r['ok_strict'] or r['tail_only'])   # AMENDMENT_05 clarified rule
            if r['tail_only']:
                r['note'] = 'tail only (last stereo pair not processed)'
            rows.append(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ov', default=T + '/runs')
    ap.add_argument('--vins', default=T + '/vins_runs')
    ap.add_argument('--dyna', default=None)
    ap.add_argument('--offsets', default=T + '/config/t3_offsets.txt')
    ap.add_argument('--runs-per-method', type=int, default=5)
    ap.add_argument('--out', default=T + '/tables')
    ap.add_argument('--tag', default='')
    ap.add_argument('--no-expect', action='store_true', help='skip the AMENDMENT_06 method-dir completeness check (t2 smoke roots)')
    a = ap.parse_args()
    global EXPECT_ON
    EXPECT_ON = not a.no_expect
    os.makedirs(a.out, exist_ok=True)
    exp = Expected(f'{a.out}/expected_frames{a.tag}.yaml')
    offs = offsets_map(a.offsets)
    rows = []
    for fam, root in (('ov', a.ov), ('vins', a.vins), ('dyna', a.dyna)):
        audit(fam, root, exp, offs, a.runs_per_method, rows)
        exp.save()
    if not rows:
        print('no runs found')
        return 1
    with open(f'{a.out}/frames_audit{a.tag}.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    agg = {}
    for r in rows:
        g = agg.setdefault((r['family'], r['method']), dict(runs=0, ok=0, strict=0, tail=0, lost=0, extra=0, missing=0, offsrc=set()))
        g['runs'] += 1
        g['ok'] += r['ok']
        g['strict'] += r['ok_strict']
        g['tail'] += r['tail_only']
        g['offsrc'].add(r['off_src'])
        if r['note'] in ('run missing', 'method dir missing'):
            g['missing'] += 1
        elif isinstance(r['diff'], int):
            g['lost'] += max(0, -r['diff'])
            g['extra'] += max(0, r['diff'])
    L = [f'# t3 frames audit (AMENDMENT_02 section 1, clarified by AMENDMENT_05) {a.tag}\n',
         'clarified rule (used): strict OR tail only = exactly one frame short and it is the last expected stereo pair '
         '(the last processed frame is the second-to-last expected one); any other shortfall is invalid and re-run.\n',
         'valid iff frames processed by the estimator == expected stereo pairs after the start offset (+-0). OpenVINS family: '
         "'[TIME] ... seconds total' lines vs bag pairs after the offset passed through the track_frequency drop rule "
         '(fed = with a later IMU sample); VINS family: timing.csv frontend rows vs ROS 1 bag pairs after the offset.\n',
         f'roots: ov={a.ov} vins={a.vins} dyna={a.dyna}; offsets file {a.offsets}\n',
         '| family | method | runs | strict ok (+-0) | tail only | clarified ok | invalid (clarified) | frames lost (sum) | frames extra (sum) | runs missing | offset source |',
         '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|']
    for (f, m), g in sorted(agg.items()):
        L.append(f"| {f} | {m} | {g['runs']} | {g['strict']} | {g['tail']} | {g['ok']} | {g['runs'] - g['ok']} | {g['lost']} | {g['extra']} | {g['missing']} | "
                 f"{','.join(sorted(g['offsrc']))} |")
    tot, ok = len(rows), sum(r['ok'] for r in rows)
    st, tl = sum(r['ok_strict'] for r in rows), sum(r['tail_only'] for r in rows)
    L.append(f'\n**Total: {ok} / {tot} runs pass the clarified frame rule ({st} strict, {tl} tail only); {tot - ok} invalid.**')
    bad = [r for r in rows if not r['ok']]
    if bad:
        L += ['\n## Runs failing the frame rule\n', '| family | seq | method | run | offset | frames | expected | bag pairs | diff | note |',
              '|---|---|---|---|--:|--:|--:|--:|--:|---|']
        L += [f"| {r['family']} | {r['seq']} | {r['method']} | {r['run']} | {r['offset']} | {r['frames']} | {r['expected']} | {r['pairs']} | "
              f"{r['diff']} | {r['note']} |" for r in bad]
    open(f'{a.out}/frames_audit{a.tag}.md', 'w').write('\n'.join(L) + '\n')
    open(f'{a.out}/frames_invalid{a.tag}.txt', 'w').write(''.join(f"{r['family']} {r['seq']} {r['method']} {r['run']}\n" for r in bad))
    open(f'{a.out}/frames_invalid_strict{a.tag}.txt', 'w').write(''.join(f"{r['family']} {r['seq']} {r['method']} {r['run']}\n" for r in rows if not r['ok_strict']))
    open(f'{a.out}/frames_tail_only{a.tag}.txt', 'w').write(''.join(f"{r['family']} {r['seq']} {r['method']} {r['run']}\n" for r in rows if r['tail_only']))
    print('\n'.join(L[:len(agg) + 8]))
    print(f'{len(bad)} invalid')
    return 0


if __name__ == '__main__':
    sys.exit(main())
