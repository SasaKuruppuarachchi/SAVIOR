#!/usr/bin/env python3
"""mkprotocol.py : writes results/chi2_realworld/PROTOCOL.yaml (+ PROTOCOL.md5, both read-only) and scripts/jobs.txt BEFORE any run.
Refuses if PROTOCOL.yaml exists. Requires cr_check.py (parameter-diff) to pass."""
import hashlib, os, subprocess, sys, time
import yaml
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
CR = R + '/chi2_realworld'
fz = CR + '/PROTOCOL.yaml'
assert not os.path.exists(fz), 'PROTOCOL.yaml exists'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
SEQS = ['MIO13', 'MIO15', 'MIO16', 'MIO07']
VARS = ['ovchi_best', 'sf1_chibest']
OFFS = [round(0.2 * k, 1) for k in range(10)]
F = yaml.safe_load(open(R + '/review_runs/FREEZE.yaml'))
inst = {}
for var in VARS:
    for seq in SEQS:
        L = subprocess.run([sys.executable, CR + '/scripts/cr_args.py', seq, var], check=True, capture_output=True, text=True,
                           env=dict(os.environ, CR_NOFREEZE='1')).stdout
        L = (L[:-1] if L.endswith('\n') else L).split('\n')
        # same ov_set string as the review_runs freeze instantiation of the variant (VIODE / warehouse)
        assert L[5] == F['variants'][var]['viode']['ov_set'] == F['variants'][var]['warehouse']['ov_set'], (var, L[5])
        assert L[0] == F['variants'][var]['viode']['install'] == WS + '/install'
        inst.setdefault(var, {})[seq] = dict(install=L[0], launch=L[1], cfg=L[2], bag=L[3], gt=L[4], ov_set=L[5], topics=L[6], pset=L[7],
                                             launch_args=L[8:], rate=0.25, offsets_s=OFFS)
chk = subprocess.run([sys.executable, CR + '/scripts/cr_check.py'], capture_output=True, text=True)
assert chk.returncode == 0, chk.stdout
scripts = {os.path.relpath(p, WS): md5(p) for p in sorted(
    [f'{CR}/scripts/{f}' for f in ('cr_args.py', 'cr_check.py', 'run_cr.sh', 'mkprotocol.py')] +
    [R + '/backend_v2/scripts/bv2queue.py', R + '/real_world/scripts/rw_args.py', R + '/real_world/scripts/rw_analyze.py',
     R + '/real_world/scripts/rw_eval.sh'])}
P = {
    'status': 'FROZEN - chi2-realworld protocol, written BEFORE any run (one-shot, no tuning)',
    'frozen_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'purpose': 'Run ONCE, untuned, the frozen t1-tuned chi2 x0.25 gate variants (review_runs FREEZE.yaml: ovchi_best, sf1_chibest) on the '
               'real-world Monado data, paired with the existing rate-0.25 real-world OpenVINS / SAVIOR / Y-Cls / VINS-Fusion runs, and apply '
               'the pre-registered DECISION_RULE.txt (T1 and T2).',
    'references': {
        'decision_rule': {'path': 'results/chi2_realworld/DECISION_RULE.txt', 'md5': md5(CR + '/DECISION_RULE.txt')},
        'review_runs_freeze': {'path': 'results/review_runs/FREEZE.yaml', 'md5': md5(R + '/review_runs/FREEZE.yaml')},
        'final_config': md5(R + '/p7/final_config.yaml'), 'final_config_addendum': md5(R + '/p7/final_config_addendum.yaml'),
        'real_world_protocol': {'path': 'results/real_world/PROTOCOL.yaml', 'md5': md5(R + '/real_world/PROTOCOL.yaml')},
        'real_world_amendment': {'path': 'results/real_world/FREEZE_AMENDMENT.txt', 'md5': md5(R + '/real_world/FREEZE_AMENDMENT.txt')},
        'real_world_expected_frames': {'path': 'results/real_world/prep/expected_frames.yaml', 'md5': md5(R + '/real_world/prep/expected_frames.yaml')},
        'install_run_subscribe_msckf_md5': md5(WS + '/install/ov_msckf/lib/ov_msckf/run_subscribe_msckf'),
    },
    'methods': {
        'ovchi_best': 'OpenVINS (frozen real-world openvins instantiation) + ov_set up_msckf_chi2_multipler=0.25 up_slam_chi2_multipler=0.25',
        'sf1_chibest': 'SAVIOR (frozen real-world sens_fix1 instantiation) + the same two ov_set keys',
        'install': 'workspace install/ (ORIGINAL frozen build, as the real-world baselines and the review_runs variants; NOT the SG install)',
        'delta_rule': 'review_runs FREEZE.yaml variants.<v>.ovset_add appended to the ov_set ROS-parameter string of the frozen real-world '
                      'instantiation produced by the unchanged results/real_world/scripts/rw_args.py (no yaml edit); nothing else',
        'parameter_diff': 'scripts/cr_check.py -> tables/param_diff.md: ' + chk.stdout.split('\n')[4].strip('*') +
                          ' (vs every rw_settings file and every run_info.yaml launch command of real_world/runs/<seq>/{openvins,sens_fix1})',
    },
    'runs': {
        'sequences': {'person': ['MIO13', 'MIO15', 'MIO16'], 'static_control': ['MIO07']},
        'offsets_s': OFFS, 'rate': 0.25, 'runner': 'scripts/run_cr.sh (= real_world run_rw.sh container / savior-run protocol)',
        'queue': 'results/backend_v2/scripts/bv2queue.py, RUNNER=run_cr.sh, PREFIX=cr_, GLOBAL_MAX=6 (at most 6 containers)',
        'dirs': 'results/chi2_realworld/runs/<seq>/<variant>/run_XX (run index = offset index, as the baselines)',
    },
    'validity': {
        'rule': 'results/real_world/scripts/rw_analyze.py rules: run_info status ok/0, non-empty trajectory, FINAL (savior launch) '
                'fallback_latest + fallback_empty = late_masks = 0, n_in_core = 0, pose rule poses >= same-offset real-world openvins - 1, '
                'and the Amendment-2 frame rule: processed stereo frames ("[TIME]: ... seconds total" lines) == '
                'real_world/prep/expected_frames.yaml ros2_pairs for the offset, +-0',
        'delta_applied': 'launch.log must show both chi2 keys overridden from ROS (0.25)',
        'reruns': 'an invalid run is re-run unchanged (FORCE), up to 3 attempts in total; any run still invalid is reported and excluded '
                  'pairwise from the primary statistics (include-all sensitivity reported)',
    },
    'evaluation': 'savior-eval multi --runs <dir> --gt data/monado/gt/<seq>.txt --no-plot (posyaw, full sequence; = real_world rw_eval.sh)',
    'statistics': {
        'as': 'results/real_world/scripts/rw_analyze.py (functions copied verbatim): paired per-offset log ATE ratio capped at 10 m; geometric-mean '
              'ratio - 1; run-level iid bootstrap 95 % CI (20000, seed 0); Wilcoxon; Holm within (group, reference); sequence-level two-stage '
              'cluster bootstrap + exact sign-flip; failures > 1 m; RPE (shortest sub-length, non-failed runs)',
        'pairings': 'openvins, sens_fix1, yolo_naive, vins_fusion from results/real_world/runs (rate 0.25, Amendment 2), same sequence + offset',
        'groups': 'person (MIO13+15+16), each sequence, static MIO07',
        'comparisons': ['ovchi_best vs openvins (T1)', 'ovchi_best vs sens_fix1 (T2)', 'sf1_chibest vs sens_fix1', 'sf1_chibest vs openvins',
                        'ovchi_best vs yolo_naive', 'ovchi_best vs vins_fusion', 'sf1_chibest vs ovchi_best', 'sf1_chibest vs vins_fusion'],
        'decision': 'DECISION_RULE.txt verbatim: transfers iff T1 (person group GM change < 0 with run-level 95 % CI excluding 0) AND T2 '
                    '(ovchi_best vs SAVIOR person-group GM ratio <= 1.0 and failures > 1 m <= SAVIOR failures + 2); otherwise does not transfer',
    },
    'scripts_md5': scripts,
    'instantiation': inst,
}
yaml.safe_dump(P, open(fz, 'w'), sort_keys=False, width=150)
os.chmod(fz, 0o444)
open(CR + '/PROTOCOL.md5', 'w').write(f'{md5(fz)}  PROTOCOL.yaml\n')
os.chmod(CR + '/PROTOCOL.md5', 0o444)
J = ['# chi2-realworld jobs: seq variant offsets start (bv2queue.py, RUNNER=run_cr.sh, DSN=chi2_realworld/runs, PREFIX=cr_, GLOBAL_MAX=6)']
for seq in SEQS:
    for k in range(0, 10, 2):
        for v in VARS:
            J.append(f"{seq} {v} {','.join(f'{x:.1f}' for x in OFFS[k:k + 2])} {k + 1} DSN=chi2_realworld/runs")
open(CR + '/scripts/jobs.txt', 'w').write('\n'.join(J) + '\n')
print(md5(fz), len(J) - 1, 'jobs')
