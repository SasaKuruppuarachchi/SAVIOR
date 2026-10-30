#!/usr/bin/env python3
"""mkfreeze.py : write results/review_runs/FREEZE.yaml (+ FREEZE.md5), then make both read-only. Refuses if FREEZE.yaml exists,
if any held-out review run exists, or if CHI2_BEST is unset. Every held-out / E variant is listed with its exact resolved
savior-run settings per domain (rr_args.settings) and the md5 of every config file it reads."""
import datetime, glob, hashlib, json, os, stat, subprocess, sys
import yaml
WS = '/home/sasa/workspace/savior_ws'
RR = f'{WS}/results/review_runs'
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
os.environ['RR_FREEZE_OPTIONAL'] = '1'
import rr_variants  # noqa: E402
from rr_args import settings  # noqa: E402
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
assert not os.path.exists(f'{RR}/FREEZE.yaml'), 'FREEZE.yaml exists'
assert rr_variants.CHI2_BEST is not None, 'CHI2_BEST not set'
held = [p for p in glob.glob(f'{RR}/runs/heldout/*/*/run_*') + glob.glob(f'{RR}/runs/e/*/*/run_*')]
assert not held, f'held-out / E runs already exist: {held[:3]}'
REP = {'warehouse': 'hall_t2_L2', 'viode': 'city_day_mid', 'openloris': 'openloris_cafe1-2', 'uhumans2': 'uhumans2_office_s1_06h'}


def files_of(L):
    f = {}
    cfgd = os.path.dirname(L[2])
    for p in sorted(glob.glob(f'{cfgd}/*.yaml')):
        f[os.path.relpath(p, WS)] = md5(p)
    for a in L[8:]:
        k, _, v = a.partition(':=')
        if v.startswith('/') and os.path.isfile(v):
            f[os.path.relpath(v, WS)] = md5(v)
    for kv in L[7].split():
        k, _, v = kv.partition('=')
        if v.startswith('/') and os.path.isfile(v):
            f[os.path.relpath(v, WS)] = md5(v)
    return f


VAR = {}
for name, v in rr_variants.V.items():
    if v['scope'] not in ('heldout', 'E'):
        continue
    doms = ['warehouse', 'viode'] if v['scope'] == 'heldout' else ['openloris', 'uhumans2']
    if name == 'ctl_savior_none':
        doms = ['warehouse']
    if name == 'e_oracle_person':
        doms = ['uhumans2']
    e = {'scope': v['scope'], 'label': v['label'], 'base': v['base'], 'pset_set': {k: str(x) for k, x in v.get('pset_set', {}).items()},
         'ovset_add': {k: str(x) for k, x in v.get('ovset_add', {}).items()}}
    for dom in doms:
        L = settings(REP[dom], name)
        e[dom] = {'launch': L[1], 'cfg': L[2], 'ov_set': L[5], 'pset': L[7], 'launch_args': L[8:], 'install': L[0], 'files_md5': files_of(L)}
    VAR[name] = e
chk = subprocess.run([sys.executable, f'{D}/rr_check.py', '--json', f'{RR}/tables/param_diff.json'], capture_output=True, text=True)
assert chk.returncode == 0, chk.stdout
t1 = json.load(open(f'{RR}/tables/ate_t1.json'))
sel = {f"{r['method']}": dict(gm_pct=round(r['gm'], 2), ci=[round(c, 1) for c in r['ci']], ci_cluster=[round(c, 1) for c in r['ci_cluster']],
                              holm=r['holm'], wins=r['wins'], losses=r['losses'])
       for r in t1['paired'] if r['family'] == 'B_chi2_vs_openvins' and r['group'] == 'all'}
now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
F = {
    'status': 'FROZEN - review runs (reviewer request, author-approved 2026-10-26), written BEFORE any held-out (warehouse t2 / VIODE) '
              'or task-E (OpenLORIS / uHumans2) review run',
    'frozen_at': now,
    'frozen_by': 'review-runs agent (VIO evaluation engineer)',
    'references': {
        'backend_config': {'path': 'results/backend_v2/backend_config.yaml', 'md5': md5(f'{WS}/results/backend_v2/backend_config.yaml')},
        'final_config': {'path': 'results/p7/final_config.yaml', 'md5': md5(f'{WS}/results/p7/final_config.yaml')},
        'final_config_addendum': {'path': 'results/p7/final_config_addendum.yaml', 'md5': md5(f'{WS}/results/p7/final_config_addendum.yaml')},
        'estimator_v2_warehouse': md5(f'{WS}/results/backend_v2/config/warehouse/estimator_config.yaml'),
        'estimator_v2_viode': md5(f'{WS}/results/backend_v2/config/viode/estimator_config.yaml'),
        'estimator_original_openloris_t265': md5(f'{WS}/src/savior/savior_bringup/config/openloris_t265/estimator_config.yaml'),
        'estimator_original_uhumans2': md5(f'{WS}/src/savior/savior_bringup/config/uhumans2/estimator_config.yaml'),
        'install_note': 'workspace install/ (frozen build; reproduces the frozen held-out runs: ctl_* controls)'},
    'scripts_md5': {os.path.relpath(p, WS): md5(p) for p in [f'{D}/rr_variants.py', f'{D}/rr_args.py', f'{D}/run_rr.sh', f'{D}/rr_check.py',
                                                             f'{D}/rr_analyze.py', f'{D}/rr_audit.py',
                                                             f'{WS}/results/backend_v2/scripts/bv2_args.py',
                                                             f'{WS}/results/backend_v2/scripts/bv2queue.py',
                                                             f'{WS}/results/m2b_heldout/scripts/m2b_args.py']},
    'parameter_diff_check': 'scripts/rr_check.py -> tables/param_diff.json: ALL EXACT (each variant differs from its frozen base by exactly the '
                            'listed delta; E instantiation = frozen keys + coco_real_robot override; gate_fix1 == sens_fix1, gate_k3 == p7_nb)',
    'task_B_selection': {
        'rule': 'pooled paired geometric-mean ATE vs OpenVINS-v2 on warehouse t1 (8 sequences x 10 offsets, group "all"), lowest wins; '
                'both up_msckf_chi2_multipler and up_slam_chi2_multipler set to the same value; grid {1 (current), 0.5, 0.25, 0.1}',
        't1_results_vs_openvins_v2': sel,
        'chosen': rr_variants.CHI2_BEST,
        'robust_loss_note': 'the OpenVINS MSCKF / SLAM update has no robust loss (only the chi2 gate: UpdaterMSCKF.cpp:225, UpdaterSLAM.cpp:410, '
                            'StateHelper::initialize); none was implemented'},
    'variants': VAR,
    'protocol': {
        'heldout': 'warehouse t2 (12 seq) + VIODE (12 seq), offsets 0.0-1.8 s (warehouse) / P5 late-start (VIODE), rate 0.5, mask_policy wait, '
                   'timeout 30 s, feature_stats auto, back-end v2 (BACKEND_VIODE=v2); identical to results/backend_v2/scripts/run_heldout_v2.sh',
        'E': 'OpenLORIS cafe1-1 (tuning) + cafe1-2, office1-1..7 (held-out of P2/P4), offsets 0.0-1.8 s (superset of the P2 offsets 0.0/0.2/0.4); '
             'uHumans2 office_s1 00h (5 offsets 0.0-0.8 s), 06h/12h (10 offsets 0.0-1.8 s) as P3a; rate 0.5; ORIGINAL estimator configs; '
             'references re-run with the same install (openvins, savior_none, oracle_person on uHumans2)',
        'validity': 'scripts/rr_audit.py: clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0, end within 0.101 s of the '
                    'same-offset OpenVINS(-v2) run with <= 1 pose missing after the own first pose; pose rule reported; ctl_* md5 controls',
        'statistics': 'scripts/rr_analyze.py: bv2analyze.py statistics + two-stage sequence-cluster bootstrap (20000, seed 1); failures > 2 m '
                      'warehouse / > 1 m VIODE, cap 10 m; E: failures > 1 m (none expected), same paired stats',
        'comparisons': {'A': 'sf1_noint, sf1_nomotion vs sens_fix1, yolo_naive, openvins', 'B': 'ovchi_best vs openvins; sens_fix1 / yolo_naive / '
                        'sf1_chibest vs ovchi_best; sf1_chibest vs sens_fix1', 'E': 'e_sens_fix1 vs e_openvins and vs e_yolo_naive (run- and '
                        'sequence-level); e_savior_none vs e_openvins (control); e_oracle_person vs e_savior_none (uHumans2, P3a reference)'}},
    'paper_labels': {'sf1_noint': 'SAVIOR w/o interaction (class prior + motion-consistency check, no association tree)',
                     'sf1_nomotion': 'SAVIOR w/o motion evidence (class prior + interaction)', 'ovchi_best': f'OpenVINS chi2 x{rr_variants.CHI2_BEST:g}',
                     'sf1_chibest': f'SAVIOR + OpenVINS chi2 x{rr_variants.CHI2_BEST:g}'},
}
txt = ('# REVIEW RUNS FREEZE - do not edit. Written before any held-out / task-E review run; md5 in FREEZE.md5.\n'
       + yaml.safe_dump(F, sort_keys=False, width=140, allow_unicode=True))
open(f'{RR}/FREEZE.yaml', 'w').write(txt)
open(f'{RR}/FREEZE.md5', 'w').write(f"{md5(f'{RR}/FREEZE.yaml')}  FREEZE.yaml\n")
for p in (f'{RR}/FREEZE.yaml', f'{RR}/FREEZE.md5'):
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
print('frozen at', now, md5(f'{RR}/FREEZE.yaml'))
