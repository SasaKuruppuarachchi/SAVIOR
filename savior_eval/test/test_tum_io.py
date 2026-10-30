import numpy as np
import pytest

from savior_eval.tum_io import TumFormatError, load_tum, write_tum


def test_openvins_style_file_with_header_and_covariance(tmp_path):
    p = tmp_path / 'ov.txt'
    lines = ['# timestamp(s) tx ty tz qx qy qz qw Pr11 Pr12 Pr13 Pr22 Pr23 '
             'Pr33 Pt11 Pt12 Pt13 Pt22 Pt23 Pt33', '']
    for i in range(5):
        lines.append('%.5f %.6f 0.000000 0.000000 0.000000 0.000000 0.000000 '
                     '1.000000 %s' % (1.0 + 0.1 * i, 0.5 * i,
                                      ' '.join(['0.0000000001'] * 12)))
    p.write_text('\n'.join(lines) + '\n')
    d, info = load_tum(str(p), return_info=True)
    assert d.shape == (5, 8)
    np.testing.assert_allclose(d[:, 1], 0.5 * np.arange(5))
    assert info['n_header_lines'] == 0 and not info['warnings']


def test_text_header_commas_tabs_comments_and_sorting(tmp_path):
    p = tmp_path / 'x.csv'
    p.write_text('timestamp,tx,ty,tz,qx,qy,qz,qw\n'
                 '% comment\n'
                 '2.0,1,2,3,0,0,0,1\n'
                 '1.0\t0\t0\t0\t0\t0\t0\t1\n'
                 '2.0,9,9,9,0,0,0,1\n'
                 '3.0,nan,0,0,0,0,0,1\n')
    d, info = load_tum(str(p), return_info=True)
    assert info['n_header_lines'] == 1
    np.testing.assert_array_equal(d[:, 0], [1.0, 2.0])
    np.testing.assert_array_equal(d[1, 1:4], [1, 2, 3])   # first dup kept
    assert len(info['warnings']) == 3


def test_nanoseconds_auto(tmp_path):
    p = tmp_path / 'ns.txt'
    p.write_text('1600000000000000000 0 0 0 0 0 0 1\n'
                 '1600000000500000000 1 0 0 0 0 0 1\n')
    d = load_tum(str(p))
    np.testing.assert_allclose(d[:, 0], [1.6e9, 1.6e9 + 0.5])
    d = load_tum(str(p), time_unit='s')
    assert d[0, 0] > 1e17


def test_errors(tmp_path):
    p = tmp_path / 'bad.txt'
    p.write_text('1 2 3\n')
    with pytest.raises(TumFormatError):
        load_tum(str(p))
    p.write_text('1 0 0 0 0 0 0 1\nfoo bar\n')
    with pytest.raises(TumFormatError):
        load_tum(str(p))


def test_roundtrip_lossless(tmp_path):
    rng = np.random.default_rng(0)
    d = rng.normal(size=(50, 8))
    d[:, 0] = 1.4e9 + np.sort(rng.uniform(0, 100, 50))
    d[:, 4:8] = np.abs(d[:, 4:8]) + 0.1
    write_tum(str(tmp_path / 'r.txt'), d)
    np.testing.assert_array_equal(load_tum(str(tmp_path / 'r.txt')), d)
    np.testing.assert_array_equal(np.loadtxt(str(tmp_path / 'r.txt')), d)
