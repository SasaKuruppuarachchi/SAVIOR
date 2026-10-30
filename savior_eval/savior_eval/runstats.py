"""``savior-eval runstats``: front-end evidence of SAVIOR runs (no ROS needed).

For every ``run_XX`` directory written by ``savior-run`` + the savior_bringup launch files:

* OpenVINS mask synchronisation: the last ``[SAVIOR-MASK] FINAL`` line of
  ``launch.log`` (exact / fallback_latest / fallback_empty / late masks, hold time);
* OpenVINS feature statistics (``feature_stats.csv``, ``record_feature_stats``):
  per camera kept features per frame (tracked + new), mask rejections, relaxed
  frames, features on the extension band / dynamic core (core must be 0 when
  gating is on);
* savior_node statistics (``savior_stats.jsonl``, /savior/stats): number of
  published mask pairs vs. images received by OpenVINS (bag count without mask-sync log), per-stage timings (median / p90),
  instances per frame, promoted / carried, masked image fraction;
* md5 of the trajectory (bit-identity of repeated runs).

Writes ``runstats.yaml`` into every run directory and prints / writes a markdown
summary for the method directory.
"""

import csv
import glob
import hashlib
import json
import math
import os
import re

import numpy as np
import yaml

EST_FN = 'stamped_traj_estimate.txt'
_FINAL_RX = re.compile(
    r'\[SAVIOR-MASK\] FINAL: (\w+) policy, (\d+) measurements \((\d+) cam masks\): exact=(\d+) '
    r'fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+) \| hold avg=([\d.]+)ms max=([\d.]+)ms')
TIMING_KEYS = ('segment', 'depth', 'gating', 'tracking', 'extension', 'compose', 'total', 'node_total')


def mask_sync(log_fn):
    """Parse the last FINAL mask-sync summary of an OpenVINS log (None if absent)."""
    if not os.path.isfile(log_fn):
        return None
    last = None
    with open(log_fn, errors='replace') as f:
        for line in f:
            m = _FINAL_RX.search(line)
            if m:
                last = m
    if last is None:
        return None
    g = last.groups()
    keys = ('measurements', 'cam_masks', 'exact', 'fallback_latest', 'fallback_empty', 'late_masks')
    out = {'policy': g[0]}
    out.update({k: int(v) for k, v in zip(keys, g[1:7])})
    out['hold_avg_ms'] = float(g[7])
    out['hold_max_ms'] = float(g[8])
    return out


def feature_stats(csv_fn):
    """Per-camera summary of an OpenVINS (SAVIOR fork) record_feature_stats csv."""
    if not os.path.isfile(csv_fn):
        return None
    cols = {}
    with open(csv_fn) as f:
        for row in csv.DictReader(f):
            for k, v in row.items():
                cols.setdefault(k, []).append(float(v))
    if not cols:
        return None
    a = {k: np.asarray(v) for k, v in cols.items()}
    out = {}
    for cam in sorted(set(a['cam_id'].astype(int).tolist())):
        m = a['cam_id'] == cam
        kept = a['n_tracked'][m] + a['n_new'][m]
        out['cam%d' % cam] = {
            'frames': int(m.sum()),
            'kept_mean': round(float(kept.mean()), 2),
            'kept_p10': round(float(np.percentile(kept, 10)), 1),
            'kept_min': int(kept.min()),
            'tracked': int(a['n_tracked'][m].sum()),
            'new': int(a['n_new'][m].sum()),
            'rejected_mask': int(a['n_rejected_mask'][m].sum()),
            'relaxed_frames': int(a['relaxed'][m].sum()),
            'in_band': int(a['n_in_band'][m].sum()),
            'in_core': int(a['n_in_core'][m].sum()),
        }
    return out


def _pct(v, q):
    return round(float(np.percentile(v, q)), 3) if len(v) else None


def savior_stats(jsonl_fn):
    """Summary of the /savior/stats JSON lines of one run."""
    if not os.path.isfile(jsonl_fn):
        return None
    rows = []
    with open(jsonl_fn) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    if not rows:
        return {'frames': 0}
    out = {'frames': len(rows), 'timings_ms': {}}
    for k in TIMING_KEYS:
        v = [r['timings_ms'][k] for r in rows if k in r.get('timings_ms', {})]
        if v:
            out['timings_ms'][k] = {'median': _pct(v, 50), 'p90': _pct(v, 90), 'max': round(float(max(v)), 3)}
    roles = [r.get('n_by_role', {}) for r in rows]
    n_dyn = np.array([x.get('dynamic', 0) for x in roles])
    out['dynamic_per_frame'] = round(float(n_dyn.mean()), 3)
    out['frames_with_dynamic'] = round(float((n_dyn > 0).mean()), 4)
    out['potential_per_frame'] = round(float(np.mean([x.get('potential', 0) for x in roles])), 3)
    for k in ('n_promoted', 'n_held', 'n_carried'):
        out[k + '_per_frame'] = round(float(np.mean([r.get(k, 0) for r in rows])), 3)
    shape = None
    for r in rows:
        if r.get('image_size'):
            shape = r['image_size']
            break
    core = np.array([r.get('core_px', 0) for r in rows], float)
    ext = np.array([r.get('ext_px', 0) for r in rows], float)
    out['core_px_mean'] = round(float(core.mean()), 1)
    out['ext_px_mean'] = round(float(ext.mean()), 1)
    out['frames_with_mask'] = round(float((core > 0).mean()), 4)
    if shape:
        npx = float(shape[0] * shape[1])
        out['core_frac_mean'] = round(float(core.mean() / npx), 5)
        out['ext_frac_mean'] = round(float(ext.mean() / npx), 5)
    return out


def bag_image_count(bag):
    """Max message count over the sensor_msgs/msg/Image topics of a ROS 2 bag (None if unknown)."""
    meta = os.path.join(bag, 'metadata.yaml') if bag and os.path.isdir(bag) else None
    if not meta or not os.path.isfile(meta):
        return None
    with open(meta) as f:
        m = yaml.safe_load(f)
    counts = [t['message_count'] for t in m['rosbag2_bagfile_information']['topics_with_message_count']
              if t['topic_metadata']['type'] == 'sensor_msgs/msg/Image']
    return max(counts) if counts else None


def traj_md5(fn):
    if not os.path.isfile(fn):
        return None
    h = hashlib.md5()
    with open(fn, 'rb') as f:
        for line in f:
            if not line.startswith(b'#'):
                h.update(line)
    return h.hexdigest()


def run_stats(run_dir, bag=None, image_topic_count=None):
    info = {}
    ri = os.path.join(run_dir, 'run_info.yaml')
    if os.path.isfile(ri):
        with open(ri) as f:
            info = yaml.safe_load(f) or {}
    bag = bag or info.get('bag')
    n_img = image_topic_count if image_topic_count is not None else bag_image_count(bag)
    out = {'run': os.path.basename(os.path.normpath(run_dir)),
           'traj_md5': traj_md5(os.path.join(run_dir, EST_FN)),
           'bag_images': n_img,
           'mask_sync': mask_sync(os.path.join(run_dir, 'launch.log')),
           'feature_stats': feature_stats(os.path.join(run_dir, 'feature_stats.csv')),
           'savior': savior_stats(os.path.join(run_dir, 'savior_stats.jsonl'))}
    s = out['savior']
    ms = out['mask_sync']
    # images OpenVINS received = released measurements (a bag start offset skips frames, so prefer this over the bag)
    out['images_received'] = ms['measurements'] if ms else None
    # P4: bag_images is the whole bag (ignores the start offset) -> keep it as bag_images_total and report the images of
    # this replay (OpenVINS-received measurements) when the mask-sync log has them
    out['bag_images_total'] = n_img
    if out['images_received'] is not None:
        out['bag_images'] = out['images_received']
    # every image OpenVINS processed got the mask pair with its exact stamp (savior_node may publish a few more:
    # OpenVINS' track_frequency throttle drops frames whose stamps are closer than 1/track_frequency)
    if ms:
        out['all_exact'] = ms['exact'] == ms['cam_masks']
    ref = ms['measurements'] if ms else n_img
    if s is not None and ref is not None:
        out['masks_equal_images'] = (s['frames'] >= ref) if ms else (s['frames'] == ref)
    fs = out['feature_stats'] or {}
    out['core_invariant_ok'] = all(c['in_core'] == 0 for c in fs.values()) if fs else None
    return out


def runs_stats(method_dir, pattern='run_*', write=True):
    runs = sorted(d for d in glob.glob(os.path.join(method_dir, pattern)) if os.path.isdir(d))
    res = []
    n_img = None
    for d in runs:
        r = run_stats(d, image_topic_count=n_img)
        n_img = r['bag_images_total'] if n_img is None else n_img   # bag count is shared by the runs
        res.append(r)
        if write:
            with open(os.path.join(d, 'runstats.yaml'), 'w') as f:
                yaml.safe_dump(r, f, sort_keys=False)
    return res


def _fmt(v, prec=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return '–'
    if isinstance(v, float):
        return '{:.{p}f}'.format(v, p=prec)
    return str(v)


def markdown(res, title=''):
    lines = []
    if title:
        lines += ['### ' + title, '']
    lines += ['| run | md5 | masks/images | exact | fb latest | fb empty | late | hold avg/max ms | '
              'kept/frame c0 / c1 | rejected c0 / c1 | relaxed frames c0 / c1 | in band | in core |',
              '|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
    for r in res:
        ms, fs, s = r['mask_sync'] or {}, r['feature_stats'] or {}, r['savior'] or {}
        c0, c1 = fs.get('cam0', {}), fs.get('cam1', {})
        lines.append('| %s | %s | %s/%s | %s | %s | %s | %s | %s/%s | %s / %s | %s / %s | %s / %s | %s | %s |' % (
            r['run'], (r['traj_md5'] or '–')[:8], _fmt(s.get('frames')),
            _fmt(r['images_received'] if r.get('images_received') is not None else r['bag_images']),
            _fmt(ms.get('exact')), _fmt(ms.get('fallback_latest')), _fmt(ms.get('fallback_empty')),
            _fmt(ms.get('late_masks')), _fmt(ms.get('hold_avg_ms')), _fmt(ms.get('hold_max_ms')),
            _fmt(c0.get('kept_mean')), _fmt(c1.get('kept_mean')), _fmt(c0.get('rejected_mask')),
            _fmt(c1.get('rejected_mask')), _fmt(c0.get('relaxed_frames')), _fmt(c1.get('relaxed_frames')),
            _fmt(c0.get('in_band', 0) + c1.get('in_band', 0) if fs else None),
            _fmt(c0.get('in_core', 0) + c1.get('in_core', 0) if fs else None)))
    md5s = {r['traj_md5'] for r in res if r['traj_md5']}
    if len(res) > 1:
        lines += ['', 'Trajectories bit-identical across runs: **%s**' % ('yes' if len(md5s) == 1 else 'no (%d distinct)'
                                                                          % len(md5s))]
    t = [r['savior']['timings_ms'] for r in res if r['savior'] and r['savior'].get('timings_ms')]
    if t:
        lines += ['', '| stage | median ms | p90 ms |', '|:--|--:|--:|']
        for k in TIMING_KEYS:
            med = [x[k]['median'] for x in t if k in x]
            p90 = [x[k]['p90'] for x in t if k in x]
            if med:
                lines.append('| %s | %.2f | %.2f |' % (k, float(np.mean(med)), float(np.mean(p90))))
    return '\n'.join(lines) + '\n'


def cmd_runstats(a):
    res = runs_stats(a.runs, a.pattern, write=not a.no_write)
    md = markdown(res, a.title or os.path.basename(os.path.normpath(a.runs)))
    print(md)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w') as f:
            f.write(md)
    return 0


def add_parser(sub):
    r = sub.add_parser('runstats', help='mask-sync / feature / timing evidence of run_XX dirs')
    r.add_argument('--runs', required=True, help='method directory containing run_XX/')
    r.add_argument('--pattern', default='run_*')
    r.add_argument('--out', default=None, help='markdown summary file')
    r.add_argument('--title', default=None)
    r.add_argument('--no-write', action='store_true', help='do not write run_XX/runstats.yaml')
    r.set_defaults(func=cmd_runstats)
    return r
