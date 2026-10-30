"""Markdown and LaTeX (booktabs) tables from eval summaries.

Cell convention (stated in every caption):
* ATE: statistic (default mean) +- std across Monte-Carlo runs of the
  per-run RMSE; translation in m, rotation in deg.
* RPE: rpg relative error per sub-trajectory length L, statistic (default
  mean) +- std over all segments of all successful runs (rpg pooling);
  translation in m, rotation (full angle) in deg.
* "Overall": rpg's pooled normalised RPE over all lengths, translation in
  % of L and rotation in deg/m (only normalised metrics are averaged across
  lengths -- no un-normalised "average" row).
Best (lowest) value per column is bold. Missing values are shown as "--".
"""

import math

from .evaluation import length_key

DASH_MD = '–'
DASH_TEX = '--'


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _cell(stats, stat='mean', with_std=True):
    """(value, std or None) from an rpg stats dict, or None."""
    if not stats or stats.get('num_samples', 0) == 0:
        return None
    v = stats.get(stat)
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    use_std = with_std and stat == 'mean' and \
        stats.get('num_samples', 0) > 1
    s = stats.get('std') if use_std else None
    return (float(v), None if s is None else float(s))


def _fmt_md(c, prec, bold):
    if c is None:
        return DASH_MD
    v = '{:.{p}f}'.format(c[0], p=prec)
    if bold:
        v = '**' + v + '**'
    if c[1] is not None:
        v += ' ± {:.{p}f}'.format(c[1], p=prec)
    return v


def _fmt_tex(c, prec, bold):
    if c is None:
        return DASH_TEX
    v = '{:.{p}f}'.format(c[0], p=prec)
    if bold:
        v = r'\mathbf{' + v + '}'
    if c[1] is not None:
        v += r' \pm {:.{p}f}'.format(c[1], p=prec)
    return '$' + v + '$'


def tex_escape(s):
    rep = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
           '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
           '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(rep.get(ch, ch) for ch in str(s))


def _best_rows(columns):
    """columns: list of lists of cells (one per row) -> set of (row, col)."""
    best = set()
    for j, col in enumerate(columns):
        vals = [(c[0], i) for i, c in enumerate(col) if c is not None]
        if len(vals) < 2:
            continue
        m = min(v for v, _ in vals)
        for v, i in vals:
            if abs(v - m) <= 1e-12 * max(1.0, abs(m)):
                best.add((i, j))
    return best


class Table(object):
    """Generic table: row labels, grouped column headers, cells."""

    def __init__(self, caption, label, row_header, groups, rows, cells,
                 precs, bold_best=True, notes=None):
        # groups: list of (group_title or '', [sub column titles])
        self.caption = caption
        self.label = label
        self.row_header = row_header
        self.groups = groups
        self.rows = rows
        self.cells = cells          # cells[i][j] = (v, std) | None | str
        self.precs = precs          # per column precision (None for str)
        self.notes = notes or []
        ncol = sum(len(g[1]) for g in groups)
        cols = [[cells[i][j] if not isinstance(cells[i][j], str) else None
                 for i in range(len(rows))] for j in range(ncol)]
        self.best = _best_rows([c if precs[j] is not None else []
                                for j, c in enumerate(cols)]) \
            if bold_best else set()

    def _flat_headers(self, md=True):
        out = []
        for g, subs in self.groups:
            for s in subs:
                out.append((g + ' ' + s).strip() if md else s)
        return out

    def markdown(self):
        hdr = [self.row_header] + self._flat_headers()
        lines = ['**' + self.caption + '**', '',
                 '| ' + ' | '.join(hdr) + ' |',
                 '|' + '|'.join([':---'] + ['---:'] * (len(hdr) - 1)) + '|']
        for i, r in enumerate(self.rows):
            vals = []
            for j, c in enumerate(self.cells[i]):
                if isinstance(c, str):
                    vals.append(c)
                else:
                    vals.append(_fmt_md(c, self.precs[j], (i, j) in self.best))
            lines.append('| ' + ' | '.join([r] + vals) + ' |')
        for n in self.notes:
            lines += ['', n]
        return '\n'.join(lines) + '\n'

    def latex(self):
        ncol = sum(len(g[1]) for g in self.groups)
        spec = 'l' + ''.join(' ' + 'c' * len(subs) for _, subs in self.groups)
        out = [r'% requires \usepackage{booktabs}',
               r'\begin{table}[t]', r'\centering',
               r'\caption{' + tex_escape(self.caption).replace(
                   '±', r'$\pm$') + '}',
               r'\label{' + self.label + '}',
               r'\resizebox{\linewidth}{!}{%',
               r'\begin{tabular}{' + spec + '}', r'\toprule']
        if any(g for g, _ in self.groups):
            parts, rules, c0 = [''], [], 2
            for g, subs in self.groups:
                k = len(subs)
                parts.append(r'\multicolumn{%d}{c}{%s}' % (k, tex_escape(g))
                             if k > 1 else tex_escape(g))
                if g:
                    rules.append(r'\cmidrule(lr){%d-%d}' % (c0, c0 + k - 1))
                c0 += k
            out.append(' & '.join(parts) + r' \\')
            if rules:
                out.append(''.join(rules))
        out.append(' & '.join([tex_escape(self.row_header)] +
                              [tex_escape(h) for h in
                               self._flat_headers(md=False)]) + r' \\')
        out.append(r'\midrule')
        for i, r in enumerate(self.rows):
            vals = []
            for j, c in enumerate(self.cells[i]):
                if isinstance(c, str):
                    vals.append(tex_escape(c))
                else:
                    vals.append(_fmt_tex(c, self.precs[j],
                                         (i, j) in self.best))
            out.append(' & '.join([tex_escape(r)] + vals) + r' \\')
        out += [r'\bottomrule', r'\end{tabular}}', r'\end{table}']
        assert ncol >= 1
        return '\n'.join(out) + '\n'


def _stat_word_plain(stat):
    return {'mean': 'mean ± std', 'median': 'median', 'rmse': 'RMSE'}[stat]


def ate_table(seqs, methods, method_labels, stat='mean', prec=3):
    """seqs: list of (seq_key, seq_label, {method: summary})."""
    groups, rows, cells = [], [method_labels[m] for m in methods], []
    for _, slabel, _ in seqs:
        groups.append((slabel, ['ATE [m]', 'ATE [deg]', 'Runs']))
    precs = []
    for _ in seqs:
        precs += [prec, prec, None]
    for m in methods:
        row = []
        for _, _, summ in seqs:
            s = summ.get(m)
            if s is None:
                row += [None, None, DASH_MD]
                continue
            row.append(_cell(_get(s, 'ate', 'trans_m'), stat))
            row.append(_cell(_get(s, 'ate', 'rot_deg'), stat))
            row.append('%d/%d' % (s.get('n_success', 0), s.get('n_trials', 0)))
        cells.append(row)
    align = _common(seqs, 'config', 'align')
    cap = ('ATE: per-run RMSE of position [m] and rotation [deg] errors after '
           '{} alignment; {} across Monte-Carlo runs (Runs = successful/total).'
           ).format(align, _stat_word_plain(stat))
    return Table(cap, 'tab:ate', 'Method', groups, rows, cells, precs)


def _common(seqs, *keys):
    vals = set()
    for _, _, summ in seqs:
        for s in summ.values():
            v = _get(s, *keys)
            if v is not None:
                vals.add(str(v))
    return '/'.join(sorted(vals)) if vals else '?'


def rpe_table(seq_key, seq_label, summaries, methods, method_labels,
              stat='mean', prec=3, overall=True):
    lengths = None
    for m in methods:
        s = summaries.get(m)
        if s is None or 'rpe_lengths_m' not in s:
            continue
        if lengths is None:
            lengths = list(s['rpe_lengths_m'])
        elif [round(v, 6) for v in s['rpe_lengths_m']] != \
                [round(v, 6) for v in lengths]:
            raise ValueError(
                'RPE lengths differ between methods for %s: %s vs %s '
                '(evaluate all methods against the same groundtruth / '
                'with the same --rpe-lengths)' % (seq_key, lengths,
                                                  s['rpe_lengths_m']))
    lengths = lengths or []
    groups = [('L = %g m' % d, ['t [m]', 'r [deg]']) for d in lengths]
    precs = [prec, prec] * len(lengths)
    if overall:
        groups.append(('Overall', ['t [%]', 'r [deg/m]']))
        precs += [prec, prec + 1]
    rows, cells = [method_labels[m] for m in methods], []
    for m in methods:
        s = summaries.get(m)
        row = []
        for d in lengths:
            lk = length_key(d)
            row.append(_cell(_get(s, 'rpe', lk, 'trans_m'), stat))
            row.append(_cell(_get(s, 'rpe', lk, 'rot_deg'), stat))
        if overall:
            row.append(_cell(_get(s, 'rpe_overall', 'trans_perc'), stat))
            row.append(_cell(_get(s, 'rpe_overall', 'rot_deg_per_m'), stat))
        cells.append(row)
    cap = ('RPE on {}: rpg relative error over sub-trajectories of length L '
           '(t: translation [m], r: rotation angle [deg]); {} over all '
           'segments of all successful runs. Overall: segments of all L pooled, '
           'normalised by L (t [%], r [deg/m]).').format(
               seq_label, _stat_word_plain(stat))
    lab = 'tab:rpe_' + ''.join(ch if ch.isalnum() else '_' for ch in seq_key)
    return Table(cap, lab, 'Method', groups, rows, cells, precs)


def improvement_vs_baseline(seqs, methods, method_labels, baseline,
                            stat='mean'):
    """Relative change 100*(base - m)/base [%] (positive = better)."""
    res = {}
    lines = ['**Change vs. %s [%%]** (100·(baseline − method)/baseline, '
             'positive = lower error; %s values)' % (method_labels[baseline],
                                                     stat), '']
    hdr = ['Method']
    for _, slabel, _ in seqs:
        hdr += [slabel + ' ATE m', slabel + ' ATE deg',
                slabel + ' RPE %', slabel + ' RPE deg/m']
    lines += ['| ' + ' | '.join(hdr) + ' |',
              '|' + '|'.join([':---'] + ['---:'] * (len(hdr) - 1)) + '|']
    keys = [('ate', 'trans_m'), ('ate', 'rot_deg'),
            ('rpe_overall', 'trans_perc'), ('rpe_overall', 'rot_deg_per_m')]
    for m in methods:
        if m == baseline:
            continue
        row = [method_labels[m]]
        res[m] = {}
        for skey, _, summ in seqs:
            res[m][skey] = {}
            for k in keys:
                b = _cell(_get(summ.get(baseline), *k), stat, False)
                v = _cell(_get(summ.get(m), *k), stat, False)
                if b is None or v is None or b[0] == 0:
                    row.append(DASH_MD)
                    res[m][skey]['_'.join(k)] = None
                else:
                    ch = 100.0 * (b[0] - v[0]) / b[0]
                    row.append('{:+.1f}'.format(ch))
                    res[m][skey]['_'.join(k)] = float(ch)
        lines.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(lines) + '\n', res


def single_summary_markdown(summary, prec=3):
    lines = ['# Trajectory evaluation summary', '',
             '- GT: `%s` (%.2f m)' % (summary['gt_file'],
                                      summary['gt_length_m']),
             '- Alignment: %s (frames: %s), max association offset %.3f s' % (
                 summary['config']['align'],
                 summary['config']['align_num_frames'],
                 summary['config']['max_diff_s']),
             '- Runs: %d/%d successful' % (summary['n_success'],
                                            summary['n_trials']), '']
    lines += ['| Run | Status | Matched | ATE RMSE [m] | ATE RMSE [deg] |',
              '|:---|:---|---:|---:|---:|']
    for t in summary['trials']:
        a = t.get('ate')
        lines.append('| %s | %s | %s | %s | %s |' % (
            t['name'], t['status'], t.get('n_matched', DASH_MD),
            '%.*f' % (prec, a['trans_m']['rmse']) if a else DASH_MD,
            '%.*f' % (prec, a['rot_deg']['rmse']) if a else DASH_MD))
    if summary.get('ate'):
        a = summary['ate']
        lines += ['', '**ATE RMSE across runs**: %s m (median %s, std %s), '
                  '%s deg (median %s, std %s)' % tuple(
                      '%.*f' % (prec, v) for v in [
                          a['trans_m']['mean'], a['trans_m']['median'],
                          a['trans_m']['std'], a['rot_deg']['mean'],
                          a['rot_deg']['median'], a['rot_deg']['std']])]
        lines += ['', '**RPE** (pooled over all segments of all runs)', '',
                  '| L [m] | segments | t mean [m] | t median [m] | t std [m] '
                  '| r mean [deg] | r median [deg] | t mean [%] |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|']
        for d in summary['rpe_lengths_m']:
            r = summary['rpe'][length_key(d)]
            if r['trans_m']['num_samples'] == 0:
                lines.append('| %g | 0 | %s |' % (d, ' | '.join([DASH_MD] * 6)))
                continue
            lines.append('| %g | %d | %s |' % (
                d, r['trans_m']['num_samples'], ' | '.join(
                    '%.*f' % (prec, v) for v in [
                        r['trans_m']['mean'], r['trans_m']['median'],
                        r['trans_m']['std'], r['rot_deg']['mean'],
                        r['rot_deg']['median'], r['trans_perc']['mean']])))
    return '\n'.join(lines) + '\n'
