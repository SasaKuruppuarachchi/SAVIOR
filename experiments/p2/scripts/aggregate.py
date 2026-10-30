"""Aggregate results/p2: ATE/RPE per method/sequence + runstats evidence -> markdown tables (stdout / files)."""
import glob
import json
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_eval')
from savior_eval import runstats  # noqa: E402

P2 = '/home/sasa/workspace/savior_ws/results/p2'
SEQS = sys.argv[1].split(',') if len(sys.argv) > 1 else None
METHODS = ['openvins', 'naive_person', 'savior_none', 'savior_cdo_off', 'savior_pp_off', 'savior_trk', 'savior_full']


def ev(method_dir):
    fn = os.path.join(method_dir, 'eval', 'eval_summary.yaml')
    if not os.path.isfile(fn):
        return None
    s = yaml.safe_load(open(fn))
    tr = [t for t in s['trials'] if t['status'] == 'ok']
    if not tr:
        return None
    at = np.array([t['ate']['trans_m']['rmse'] for t in tr])
    ar = np.array([t['ate']['rot_deg']['rmse'] for t in tr])
    L = s['rpe_lengths_m']
    k0 = '%g' % L[0] if ('%g' % L[0]) in tr[0]['rpe'] else list(tr[0]['rpe'].keys())[0]
    r0 = np.array([t['rpe'][k0]['trans_m']['mean'] for t in tr])
    r0r = np.array([t['rpe'][k0]['rot_deg']['mean'] for t in tr])
    kl = list(tr[0]['rpe'].keys())[-1]
    rl = np.array([t['rpe'][kl]['trans_perc']['mean'] for t in tr])
    return dict(n=len(tr), ate_t=at, ate_r=ar, rpe0=r0, rpe0r=r0r, L0=float(k0), rpeL=rl, LL=float(kl),
                gt_len=s['gt_length_m'], matched=[t['n_matched'] for t in tr])


def f(a, p=3):
    a = np.asarray(a)
    if a.size > 1:
        return '%.*f ± %.*f' % (p, a.mean(), p, a.std())
    return '%.*f' % (p, a.mean())


def main():
    seqs = SEQS or sorted(os.path.basename(d) for d in glob.glob(P2 + '/openloris_*') + glob.glob(P2 + '/uhumans2_*'))
    out = []
    allrows = {}
    for seq in seqs:
        out += ['', '### ' + seq, '',
                '| method | ATE [m] | ATE [deg] | ATE runs [m] | RPE@%s t [m] | RPE@%s r [deg] | RPE@longest [%%] | '
                'masks = images | exact / fb | kept/frame c0 | rejected c0+c1 | relaxed frames | in core | frames w/ person | '
                'core / band [%% px] |' % ('L0', 'L0'),
                '|:--|--:|--:|:--|--:|--:|--:|:-:|--:|--:|--:|--:|--:|--:|--:|']
        for m in METHODS:
            md = os.path.join(P2, seq, m)
            e = ev(md)
            if e is None:
                continue
            rs = runstats.runs_stats(md, write=True)
            eq = [r.get('masks_equal_images') and r.get('all_exact') for r in rs]
            ms = [r['mask_sync'] for r in rs if r['mask_sync']]
            exact = sum(x['exact'] for x in ms)
            fb = sum(x['fallback_latest'] + x['fallback_empty'] for x in ms)
            fs = [r['feature_stats'] for r in rs if r['feature_stats']]
            kept = np.mean([x['cam0']['kept_mean'] for x in fs]) if fs else float('nan')
            rej = np.mean([x['cam0']['rejected_mask'] + x['cam1']['rejected_mask'] for x in fs]) if fs else 0
            rel = np.mean([x['cam0']['relaxed_frames'] + x['cam1']['relaxed_frames'] for x in fs]) if fs else 0
            core = sum(x['cam0']['in_core'] + x['cam1']['in_core'] for x in fs)
            sv = [r['savior'] for r in rs if r['savior'] and r['savior'].get('frames')]
            fwd = np.mean([x['frames_with_dynamic'] for x in sv]) if sv else None
            cf = np.mean([x.get('core_frac_mean', x['core_px_mean'] / 678400.) for x in sv]) * 100 if sv else None
            ef = np.mean([x.get('ext_frac_mean', x['ext_px_mean'] / 678400.) for x in sv]) * 100 if sv else None
            md5 = len({r['traj_md5'] for r in rs})
            out.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %.1f | %.0f | %.0f | %d | %s | %s |' % (
                m, f(e['ate_t']), f(e['ate_r'], 2), ' '.join('%.3f' % x for x in e['ate_t']), f(e['rpe0']),
                f(e['rpe0r'], 2), f(e['rpeL'], 2),
                ('yes' if all(eq) else 'NO') if sv else '–', ('%d / %d' % (exact, fb)) if ms else '–', kept, rej, rel,
                core, ('%.2f' % fwd) if fwd is not None else '–',
                ('%.2f / %.2f' % (cf, ef)) if cf is not None else '–'))
            allrows.setdefault(m, {})[seq] = dict(ate_t=e['ate_t'].tolist(), ate_r=e['ate_r'].tolist(),
                                                  rpe0=e['rpe0'].tolist(), L0=e['L0'], fb=fb, distinct_md5=md5,
                                                  frames_with_person=fwd, core_pct=cf, kept=kept)
        out.append('')
        out.append('RPE@L0 = %.2f m (10 %% of the GT length), longest = 50 %%.' % e['L0'])
    print('\n'.join(out))
    json.dump(allrows, open(P2 + '/compare/aggregate.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
