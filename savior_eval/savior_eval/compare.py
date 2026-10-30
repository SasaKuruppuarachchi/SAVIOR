"""Compare several methods (e.g. OpenVINS vs SAVIOR variants) on one or
more sequences: evaluates (or loads) each method, then writes markdown +
LaTeX (booktabs) tables, a summary yaml and comparison plots."""

import glob
import os
import sys

import yaml

from . import evaluation as ev
from . import tables


def _warn(msg):
    sys.stderr.write('[savior-eval] WARNING: %s\n' % msg)


def resolve_method(path, gt, out_dir, cfg, label, pattern='run_*',
                   est_name=ev.EST_FN):
    """Return (summary, samples) for a method given a path that is
    - an eval output (dir with eval_summary.yaml, or the yaml itself),
    - a runs dir (containing run_*/stamped_traj_estimate.txt), or
    - a single TUM estimate file."""
    if path.endswith('.yaml') and os.path.isfile(path):
        return ev.load_summary(path)
    if os.path.isdir(path) and os.path.isfile(os.path.join(path, ev.SUMMARY_FN)) \
            and not glob.glob(os.path.join(path, pattern)):
        s, smp = ev.load_summary(path)
        if gt and os.path.abspath(gt) != s.get('gt_file'):
            _warn('%s was evaluated against %s, not %s' % (
                path, s.get('gt_file'), gt))
        return s, smp
    if not gt:
        raise ValueError('groundtruth needed to evaluate %s' % path)
    if os.path.isdir(path):
        ev.evaluate_runs_dir(path, gt, out_dir, cfg, pattern, est_name,
                             label=label)
    elif os.path.isfile(path):
        ev.evaluate_trials([path], gt, out_dir, cfg, label=label)
    else:
        raise FileNotFoundError(path)
    return ev.load_summary(out_dir)


def discover_methods(seq_dir, pattern='run_*'):
    out = []
    for d in sorted(os.listdir(seq_dir)):
        p = os.path.join(seq_dir, d)
        if os.path.isdir(p) and glob.glob(os.path.join(p, pattern)):
            out.append(d)
    return out


def run_compare(sequences, out_dir, cfg, stat='mean', baseline=None,
                plot=True, prec=3, pattern='run_*', est_name=ev.EST_FN):
    """sequences: list of dicts
         {key, label, gt, methods: [(method_key, method_label, path), ...]}
    """
    os.makedirs(out_dir, exist_ok=True)
    methods, mlabels = [], {}
    seq_rows = []          # (key, label, {method: summary})
    seq_samples = {}
    for seq in sequences:
        summ, smp = {}, {}
        for mkey, mlabel, path in seq['methods']:
            if mkey not in mlabels:
                methods.append(mkey)
                mlabels[mkey] = mlabel
            m_out = os.path.join(out_dir, seq['key'], mkey)
            print('[savior-eval] %s / %s <- %s' % (seq['key'], mkey, path))
            s, sm = resolve_method(path, seq.get('gt'), m_out, cfg, mlabel,
                                   pattern, est_name)
            summ[mkey], smp[mkey] = s, sm
            if s.get('n_success', 0) < s.get('n_trials', 0):
                _warn('%s / %s: only %d/%d runs succeeded' % (
                    seq['key'], mkey, s.get('n_success', 0),
                    s.get('n_trials', 0)))
        seq_rows.append((seq['key'], seq.get('label', seq['key']), summ))
        seq_samples[seq['key']] = smp

    md_parts, result = [], {'methods': [{'key': m, 'label': mlabels[m]}
                                        for m in methods],
                            'stat': stat, 'sequences': {}}
    t = tables.ate_table(seq_rows, methods, mlabels, stat, prec)
    _write(out_dir, 'ate', t)
    md_parts.append(t.markdown())
    for skey, slabel, summ in seq_rows:
        present = [m for m in methods if m in summ]
        t = tables.rpe_table(skey, slabel, summ, present, mlabels, stat, prec)
        _write(out_dir, 'rpe_' + skey, t)
        md_parts.append(t.markdown())
        result['sequences'][skey] = {
            'label': slabel,
            'gt_file': next(iter(summ.values())).get('gt_file'),
            'rpe_lengths_m': next(iter(summ.values())).get('rpe_lengths_m'),
            'methods': {m: {
                'n_trials': summ[m].get('n_trials'),
                'n_success': summ[m].get('n_success'),
                'align': summ[m].get('config', {}).get('align'),
                'ate': summ[m].get('ate'),
                'rpe': summ[m].get('rpe'),
                'rpe_overall': summ[m].get('rpe_overall'),
            } for m in present}}
    if baseline:
        if baseline not in mlabels:
            raise ValueError('baseline %r not among methods %s' % (
                baseline, methods))
        md, imp = tables.improvement_vs_baseline(seq_rows, methods, mlabels,
                                                 baseline, stat)
        md_parts.append(md)
        result['improvement_vs_baseline_perc'] = {'baseline': baseline,
                                                  'values': imp}
    with open(os.path.join(out_dir, 'compare.md'), 'w') as f:
        f.write('\n'.join(md_parts))
    with open(os.path.join(out_dir, 'compare.tex'), 'w') as f:
        for name in ['ate'] + ['rpe_' + k for k, _, _ in seq_rows]:
            with open(os.path.join(out_dir, name + '.tex')) as g:
                f.write(g.read() + '\n')
    with open(os.path.join(out_dir, 'compare_summary.yaml'), 'w') as f:
        yaml.safe_dump(ev._clean(result), f, sort_keys=False, width=100)

    if plot:
        from . import plots
        pdir = os.path.join(out_dir, 'plots')
        os.makedirs(pdir, exist_ok=True)
        fmt = cfg.plot_format
        ate = []
        for skey, _, summ in seq_rows:
            ate.append({m: summ[m].get('ate_per_trial', {}) for m in summ})
            present = [m for m in methods if m in summ]
            smp = seq_samples[skey]
            lengths = next(iter(summ.values())).get('rpe_lengths_m') or []
            plots.plot_compare_rpe(skey, present, [mlabels[m] for m in present],
                                   smp, lengths, pdir, fmt)
            plots.plot_compare_trajectories(
                skey, present, [mlabels[m] for m in present], smp, pdir, fmt)
        plots.plot_compare_ate([lab for _, lab, _ in seq_rows], methods,
                               [mlabels[m] for m in methods], ate, pdir, fmt)
    print('[savior-eval] tables written to %s' % out_dir)
    print('\n'.join(md_parts))
    return result


def _write(out_dir, name, table):
    with open(os.path.join(out_dir, name + '.md'), 'w') as f:
        f.write(table.markdown())
    with open(os.path.join(out_dir, name + '.tex'), 'w') as f:
        f.write(table.latex())


def sequences_from_config(path):
    """Parse a compare yaml:

    results_root: results/uhumans2        # optional, prefix for 'dir'
    sequences:
      - key: office_00h
        label: Office 00h                 # optional
        gt: data/uhumans2/gt/office_00h.txt
        dir: office_00h                   # methods = <dir>/<method_key>
    methods:                              # ordered; optional (auto-discover)
      - {key: openvins, label: OpenVINS}
      - {key: savior_full, label: SAVIOR}
    baseline: openvins                    # optional
    eval: {align: posyaw, rpe_lengths: [..], ...}   # optional EvalConfig args
    """
    with open(path) as f:
        c = yaml.safe_load(f)
    root = c.get('results_root', '')
    base = os.path.dirname(os.path.abspath(path))

    def absp(p):
        return p if os.path.isabs(p) else os.path.join(base, p)
    seqs = []
    for s in c['sequences']:
        d = absp(os.path.join(root, s.get('dir', s['key'])))
        if c.get('methods'):
            ms = [(m['key'], m.get('label', m['key']),
                   os.path.join(d, m['key'])) for m in c['methods']]
        else:
            ms = [(m, m, os.path.join(d, m)) for m in discover_methods(d)]
        seqs.append({'key': s['key'], 'label': s.get('label', s['key']),
                     'gt': absp(s['gt']) if s.get('gt') else None,
                     'methods': ms})
    return seqs, c
