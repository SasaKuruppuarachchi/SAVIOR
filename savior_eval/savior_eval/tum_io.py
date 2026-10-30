"""TUM trajectory I/O (``timestamp tx ty tz qx qy qz qw [extra columns]``).

Robust reader for files written by OpenVINS' ``ov_eval pose_to_file`` (which
may append 12 covariance columns), EuRoC/rpg ``stamped_*.txt`` files and
hand-made files:

* blank lines and comment lines (``#``, ``%``, ``//``) are skipped,
* non-numeric header lines (e.g. ``timestamp tx ty ...``) are skipped,
* separators may be spaces, tabs or commas,
* only the first 8 columns are used,
* timestamps in nanoseconds are detected (``time_unit='auto'``) and converted,
* rows are sorted by time, duplicate stamps and non-finite rows are dropped
  (each with a warning recorded in the returned info).
"""

import math
import os

import numpy as np

TUM_HEADER = '# timestamp tx ty tz qx qy qz qw'
_COMMENT_PREFIXES = ('#', '%', '//')


class TumFormatError(ValueError):
    pass


def _parse_lines(path):
    rows = []
    n_header = 0
    with open(path, 'r') as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith(_COMMENT_PREFIXES):
                continue
            tokens = line.replace(',', ' ').replace('\t', ' ').split()
            try:
                vals = [float(v) for v in tokens[:8]]
            except ValueError:
                if rows:
                    raise TumFormatError(
                        '{}:{}: non-numeric line inside data: {!r}'.format(
                            path, lineno, line[:80]))
                n_header += 1
                continue
            if len(vals) < 8:
                raise TumFormatError(
                    '{}:{}: expected >= 8 columns (timestamp tx ty tz qx qy '
                    'qz qw), got {}'.format(path, lineno, len(tokens)))
            rows.append(vals)
    return rows, n_header


def load_tum(path, time_unit='auto', return_info=False):
    """Load a TUM file as an (N, 8) float64 array [t, x, y, z, qx, qy, qz, qw].

    time_unit: 's', 'ns' or 'auto' (ns if the median stamp is > 1e12).
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    rows, n_header = _parse_lines(path)
    info = {'file': os.path.abspath(path), 'n_header_lines': n_header,
            'warnings': []}
    data = np.array(rows, dtype=np.float64).reshape(-1, 8)
    info['n_rows_raw'] = int(data.shape[0])

    if data.shape[0] > 0:
        unit = time_unit
        if time_unit == 'auto':
            unit = 'ns' if np.median(np.abs(data[:, 0])) > 1e12 else 's'
            if unit == 'ns':
                info['warnings'].append(
                    'timestamps look like nanoseconds; converted to seconds')
        if unit == 'ns':
            data[:, 0] = data[:, 0] * 1e-9
        elif unit != 's':
            raise ValueError('time_unit must be s, ns or auto')
        info['time_unit'] = unit

        finite = np.all(np.isfinite(data), axis=1)
        if not np.all(finite):
            info['warnings'].append(
                'dropped {} non-finite rows'.format(int((~finite).sum())))
            data = data[finite]

        qn = np.linalg.norm(data[:, 4:8], axis=1)
        bad_q = qn < 1e-6
        if np.any(bad_q):
            info['warnings'].append(
                'dropped {} rows with zero quaternion'.format(
                    int(bad_q.sum())))
            data = data[~bad_q]

        if data.shape[0] > 1 and np.any(np.diff(data[:, 0]) < 0):
            info['warnings'].append('rows were not time-sorted; sorted')
            data = data[np.argsort(data[:, 0], kind='stable')]
        if data.shape[0] > 1:
            dup = np.concatenate(([False], np.diff(data[:, 0]) == 0))
            if np.any(dup):
                info['warnings'].append(
                    'dropped {} duplicate timestamps (kept first)'.format(
                        int(dup.sum())))
                data = data[~dup]

    info['n_rows'] = int(data.shape[0])
    if data.shape[0] > 0:
        info['t_start'] = float(data[0, 0])
        info['t_end'] = float(data[-1, 0])
    if return_info:
        return data, info
    return data


def write_tum(path, data, header=TUM_HEADER):
    """Write an (N, 8) array losslessly (repr precision)."""
    data = np.asarray(data, dtype=np.float64).reshape(-1, 8)
    d = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(d):
        os.makedirs(d)
    np.savetxt(path, data, fmt='%.17g', header=header.lstrip('# '),
               comments='# ')


def trajectory_length(positions):
    p = np.asarray(positions, dtype=np.float64).reshape(-1, 3)
    if p.shape[0] < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def quat_to_rot(q):
    """xyzw quaternion -> 3x3 rotation (same convention as rpg)."""
    x, y, z, w = [float(v) for v in q]
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
