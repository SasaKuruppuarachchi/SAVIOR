#!/usr/bin/env python3
"""cr_args.py <seq> <variant> : savior-run settings of one chi2-realworld run (one-shot, untuned real-world check of the FROZEN
t1-tuned chi2 x0.25 gate variants of results/review_runs/FREEZE.yaml, md5 d00e1421c1291253bfcd3bb464029ebb: ovchi_best, sf1_chibest).

Adapted from results/nis_validation/scripts/nv_args.py (copy in scripts/from_nis_validation/). Each variant = the FROZEN real-world
instantiation of its base method, produced by the unchanged results/real_world/scripts/rw_args.py (asserts the real-world
FREEZE.md5 + FREEZE_AMENDMENT.md5 and the frozen final_config / addendum), with exactly the review_runs freeze delta:
  OVSET += up_msckf_chi2_multipler=0.25 up_slam_chi2_multipler=0.25   (FREEZE.yaml variants.<v>.ovset_add)
  INSTALL unchanged = the ORIGINAL workspace install/ (as the real-world baselines and the review_runs variants; NOT the SG install)
Bases: ovchi_best -> openvins, sf1_chibest -> sens_fix1.
Unless CR_NOFREEZE=1 (only used to write PROTOCOL.yaml), PROTOCOL.yaml must be read-only, match PROTOCOL.md5, and list identical
INSTALL / LAUNCH / CFG / OVSET / PSET / args for this (seq, variant).
Output (one per line): INSTALL, LAUNCH, CFG, BAG, GT, OVSET, TOPICS, PSET, then launch args 'k:=v'."""
import hashlib, os, subprocess, sys
WS = '/home/sasa/workspace/savior_ws'
CR = f'{WS}/results/chi2_realworld'
RR_FREEZE_MD5 = 'd00e1421c1291253bfcd3bb464029ebb'
DECISION_MD5 = 'ad5789081473e4cc36909ddd6ac319f8'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
BASE = {'ovchi_best': 'openvins', 'sf1_chibest': 'sens_fix1'}
SEQS = ('MIO13', 'MIO15', 'MIO16', 'MIO07')


def delta(var):
    import yaml
    F = yaml.safe_load(open(f'{WS}/results/review_runs/FREEZE.yaml'))
    m = F['variants'][var]
    assert m['base'] == BASE[var] and m['pset_set'] == {}, f'freeze base/pset of {var}'
    d = {k: str(v) for k, v in m['ovset_add'].items()}
    assert d == {'up_msckf_chi2_multipler': '0.25', 'up_slam_chi2_multipler': '0.25'}, f'freeze delta of {var}: {d}'
    return d


def kvparse(s):
    out = {}
    for it in s.split():
        k, _, v = it.partition('=')
        assert k not in out, f'duplicate key {k}'
        out[k] = v
    return out


def settings(seq, var):
    assert seq in SEQS and var in BASE, (seq, var)
    assert md5(f'{WS}/results/review_runs/FREEZE.yaml') == RR_FREEZE_MD5, 'review_runs FREEZE.yaml changed'
    assert md5(f'{CR}/DECISION_RULE.txt') == DECISION_MD5, 'DECISION_RULE.txt changed'
    L = subprocess.run([sys.executable, f'{WS}/results/real_world/scripts/rw_args.py', seq, BASE[var]], check=True,
                       capture_output=True, text=True).stdout
    L = (L[:-1] if L.endswith('\n') else L).split('\n')
    assert L[0] == f'{WS}/install', f'unexpected base install {L[0]}'
    o = kvparse(L[5])
    for k, x in delta(var).items():
        assert k not in o, f'ov_set already has {k}'
        o[k] = x
    L[5] = ' '.join(f'{k}={x}' for k, x in o.items())
    return L


if __name__ == '__main__':
    seq, var = sys.argv[1], sys.argv[2]
    L = settings(seq, var)
    if os.environ.get('CR_NOFREEZE') != '1':
        import yaml
        fz = f'{CR}/PROTOCOL.yaml'
        assert os.path.isfile(fz) and not os.access(fz, os.W_OK), 'PROTOCOL.yaml missing or writable'
        assert open(f'{CR}/PROTOCOL.md5').read().split()[0] == md5(fz), 'PROTOCOL.yaml md5 mismatch'
        P = yaml.safe_load(open(fz))
        fv = P['instantiation'][var][seq]
        assert [fv['install'], fv['launch'], fv['cfg'], fv['ov_set'], fv['pset'], fv['launch_args']] == \
            [L[0], L[1], L[2], L[5], L[7], L[8:]], f'{seq} {var}: settings differ from PROTOCOL.yaml'
    print('\n'.join(L))
