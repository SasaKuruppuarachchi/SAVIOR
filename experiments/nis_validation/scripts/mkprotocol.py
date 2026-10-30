#!/usr/bin/env python3
"""mkprotocol.py : writes results/nis_validation/PROTOCOL.yaml (+ PROTOCOL.md5, read-only) and scripts/jobs.txt BEFORE any run.
Refuses if PROTOCOL.yaml exists."""
import hashlib, os, subprocess, sys, time
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nv_plan import DATASETS, NV, R, WS, offsets  # noqa: E402
fz = NV + '/PROTOCOL.yaml'
assert not os.path.exists(fz), 'PROTOCOL.yaml exists'
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
CTL = {'ctl_sens_fix1': ['hall_t2_L3'], 'ctl_openvins': ['hall_t2_L3']}
inst = {}
for var in ('sf1_nis', 'ov_nis', 'ctl_sens_fix1', 'ctl_openvins'):
    seqs = CTL.get(var) or [s for d in DATASETS.values() for s in d['seqs']]
    for seq in seqs:
        L = subprocess.run([sys.executable, NV + '/scripts/nv_args.py', seq, var], check=True, capture_output=True, text=True,
                           env=dict(os.environ, NV_NOFREEZE='1')).stdout
        L = (L[:-1] if L.endswith('\n') else L).split('\n')
        inst.setdefault(var, {})[seq] = dict(install=L[0], launch=L[1], cfg=L[2], bag=L[3], gt=L[4], ov_set=L[5], topics=L[6], pset=L[7],
                                             launch_args=L[8:], rate=0.25 if seq.startswith('MIO') else 0.5, offsets_s=offsets(seq))
chk = subprocess.run([sys.executable, NV + '/scripts/nv_check.py'], capture_output=True, text=True)
assert chk.returncode == 0, chk.stdout
scripts = {os.path.relpath(p, WS): md5(p) for p in sorted(
    [f'{NV}/scripts/{f}' for f in ('nv_args.py', 'nv_plan.py', 'nv_check.py', 'run_nv.sh', 'mkprotocol.py')])}
P = {
    'status': 'FROZEN - NIS validation protocol, written BEFORE any NIS-validation run (one-shot, no tuning)',
    'frozen_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'purpose': 'Evaluate ONCE, untuned, the frozen self-tuning (NIS-adaptive chi2) gate controls of the semantic-gate study on every '
               'non-t3 dataset: warehouse held-out t2, VIODE held-out, OpenLORIS (cafe1-1 + 8 held-out) / uHumans2 (task-E setup), '
               'real-world Monado. t3 is excluded (confirmatory study running separately).',
    'references': {
        'semantic_gate_freeze': {'path': 'results/semantic_gate/FREEZE.yaml', 'md5': md5(R + '/semantic_gate/FREEZE.yaml')},
        'review_runs_freeze': {'path': 'results/review_runs/FREEZE.yaml', 'md5': md5(R + '/review_runs/FREEZE.yaml')},
        'review_runs_amendment': {'path': 'results/review_runs/FREEZE_AMENDMENT.txt', 'md5': md5(R + '/review_runs/FREEZE_AMENDMENT.txt')},
        'backend_config': {'path': 'results/backend_v2/backend_config.yaml', 'md5': md5(R + '/backend_v2/backend_config.yaml')},
        'final_config': md5(R + '/p7/final_config.yaml'), 'final_config_addendum': md5(R + '/p7/final_config_addendum.yaml'),
        'real_world_protocol': {'path': 'results/real_world/PROTOCOL.yaml', 'md5': md5(R + '/real_world/PROTOCOL.yaml')},
        'real_world_amendment': {'path': 'results/real_world/FREEZE_AMENDMENT.txt', 'md5': md5(R + '/real_world/FREEZE_AMENDMENT.txt')},
        'stats3_core': {'path': 'results/stats_v3/scripts/stats3_core.py', 'md5': md5(R + '/stats_v3/scripts/stats3_core.py')},
        'sg_install_run_subscribe_msckf_md5': md5(R + '/semantic_gate/install/ov_msckf/lib/ov_msckf/run_subscribe_msckf'),
    },
    'methods': {
        'sf1_nis': 'SAVIOR (frozen sens_fix1 instantiation of each dataset) + NIS-adaptive gate: INSTALL results/semantic_gate/install, '
                   'ov_set + savior_nis_gate=true (code defaults window 200, scale clamp [0.05, 20]); nothing else',
        'ov_nis': 'OpenVINS (frozen openvins instantiation of each dataset) + NIS-adaptive gate, same delta',
        'ctl_sens_fix1 / ctl_openvins': 'md5-identity control (SG install, NO delta) on warehouse hall_t2_L3 runs 1-5 only (the held-out warehouse '
                                        'is bit-deterministic): trajectories must equal the frozen sens_fix1 / openvins runs. Check only, not in statistics.',
        'delta_rule': 'held-out instantiation = the freeze delta (semantic_gate FREEZE.yaml methods.<v>.ovset_add) applied to the frozen '
                      'instantiation of the base method on that dataset; for Monado the key is added to the ov_set ROS-parameter string '
                      'of the frozen real-world OpenVINS config exactly as the freeze applies it (no yaml edit)',
        'parameter_diff': 'scripts/nv_check.py -> tables/param_diff.md: ' + chk.stdout.split('\n')[4].strip('*'),
    },
    'datasets': {
        'warehouse_t2': {'sequences': DATASETS['warehouse_t2']['seqs'], 'offsets_s': '0.0..1.8 (10)', 'rate': 0.5, 'backend': 'v2',
                         'runner': 'run_nv.sh = review_runs run_rr.sh protocol', 'failure_m': 2.0},
        'viode': {'sequences': DATASETS['viode']['seqs'], 'offsets_s': 'P5 late-start (parking_lot 5.5.., city_day 4.1.., city_night 6.1.., 10 each)',
                  'rate': 0.5, 'backend': 'v2 (BACKEND_VIODE=v2)', 'failure_m': 1.0},
        'openloris': {'sequences': DATASETS['openloris_uhumans2']['seqs'][:9], 'offsets_s': '0.0..1.8 (10)', 'rate': 0.5,
                      'config': 'ORIGINAL estimator config (task E)', 'failure_m': 1.0, 'note': 'cafe1-1 = P2 tuning sequence, reported separately'},
        'uhumans2': {'sequences': DATASETS['openloris_uhumans2']['seqs'][9:], 'offsets_s': '00h 0.0..0.8 (5); 06h / 12h 0.0..1.8 (10)', 'rate': 0.5,
                     'config': 'ORIGINAL estimator config (task E)', 'failure_m': 1.0},
        'monado': {'sequences': ['MIO13', 'MIO15', 'MIO16', 'MIO07 (static control)'], 'offsets_s': '0.0..1.8 (10)', 'rate': 0.25,
                   'config': 'frozen real-world configs (FREEZE.md5 + FREEZE_AMENDMENT.md5, asserted by rw_args.py)', 'failure_m': 1.0},
        'cap_m': 10.0,
        'runs': 'results/nis_validation/runs/{t2,viode,e,rw,ctl}/<seq>/<variant>/run_XX (run index = offset index, as the baselines)',
    },
    'pairings': {
        'warehouse_t2 / viode': 'openvins, sens_fix1, yolo_naive (results/backend_v2/heldout/runs); ovchi_best, sf1_chibest (results/review_runs/runs/heldout)',
        'openloris / uhumans2': 'e_openvins, e_sens_fix1, e_yolo_naive (results/review_runs/runs/e)',
        'monado': 'openvins, sens_fix1, yolo_naive, vins_fusion at rate 0.25 (results/real_world/runs; Amendment 2)',
        'unit': 'same sequence and same start offset (run_XX index); existing baseline runs are reused, never re-run',
    },
    'validity': {
        'warehouse_t2 / viode': 'results/review_runs/scripts/rr_audit.py rules (= m2bsync + AUDIT_NOTE 0.101 s end tolerance for back-end v2): '
                                'run_info ok/0, non-empty trajectory, FINAL fallback_latest = fallback_empty = late_masks = 0 (savior launches), '
                                'n_in_core = 0, last pose >= same-offset openvins(-v2) last pose - 0.101 s and <= 1 pose missing after the own '
                                'first pose; pose rule (>= openvins - 1) reported',
        'openloris / uhumans2': 'the same rr_audit.py rules with the reference e_openvins (review_runs/runs/e)',
        'monado': 'results/real_world/scripts/rw_analyze.py rules: status ok, trajectory, FINAL (savior launch) fallbacks = late = 0, n_in_core = 0, '
                  'pose rule poses >= same-offset openvins - 1, and the Amendment-2 frame rule: processed stereo frames ("[TIME]: ... seconds '
                  'total" lines) == prep/expected_frames.yaml ros2_pairs for the offset, +-0',
        'reruns': 'an invalid run is re-run unchanged (FORCE), up to 3 attempts in total; any run still invalid is reported, kept in the '
                  'include-all sensitivity and excluded pairwise from the primary statistics (as task E did for its baselines). Baseline '
                  'runs are audited with the same rule; pairs with an invalid baseline run are excluded pairwise in the primary statistics.',
    },
    'statistics': {
        'metric': 'ATE RMSE (savior-eval multi, posyaw, full sequence); failures = ATE > failure_m (warehouse 2 m, others 1 m), log ratios capped at 10 m',
        'run_level': 'paired per-offset log ATE ratio; geometric-mean ratio - 1; iid bootstrap 95 % CI over the pooled pairs (20000, seed 0); '
                     'Wilcoxon signed-rank (zero differences dropped); Holm within each dataset x group over the PRIMARY comparisons '
                     '(secondary comparisons: own Holm family)',
        'sequence_level': 'results/stats_v3/scripts/stats3_core.py (imported): exp(mean of per-sequence mean log ratios) - 1, two-stage '
                          'cluster bootstrap CI (boot_two_stage, 20000, seed 0), exact sign-flip p (signflip; min p = 2/2^k reported)',
        'rpe': 'savior-eval RPE, mean translational error at the shortest sub-length; paired log ratio over pairs where both runs are not '
               'failures and have RPE segments; same run-level statistics (secondary)',
        'lambda': 'per run, from the [SAVIOR-GATE] msckf / slam log lines (one every 200 update calls): median nis_lambda over the run, and the '
                  'fraction of lines at the lower clamp (<= 0.0500) and at the upper clamp (>= 20.0); reported per dataset (median over runs '
                  'of the run medians, IQR, mean clamp fractions)',
        'sensitivity': 'include-all (invalid runs kept), failures excluded instead of capped',
    },
    'primary_comparisons': {
        'warehouse_t2': ['sf1_nis vs sens_fix1', 'sf1_nis vs ovchi_best', 'sf1_nis vs openvins', 'ov_nis vs openvins'],
        'viode': ['sf1_nis vs sens_fix1', 'sf1_nis vs ovchi_best', 'sf1_nis vs openvins', 'ov_nis vs openvins'],
        'openloris': ['sf1_nis vs sens_fix1', 'sf1_nis vs openvins', 'ov_nis vs openvins'],
        'uhumans2': ['sf1_nis vs sens_fix1', 'sf1_nis vs openvins', 'ov_nis vs openvins'],
        'monado': ['sf1_nis vs sens_fix1', 'sf1_nis vs openvins', 'ov_nis vs openvins'],
    },
    'secondary_comparisons': {
        'warehouse_t2 / viode': ['sf1_nis vs yolo_naive', 'sf1_nis vs sf1_chibest', 'ov_nis vs ovchi_best'],
        'openloris / uhumans2': ['sf1_nis vs yolo_naive'],
        'monado': ['sf1_nis vs yolo_naive', 'sf1_nis vs vins_fusion'],
    },
    'primary_groups': {'warehouse_t2': 'all (12 seq); also L0, L1, L2, L3, L0+L1, L2+L3, hall_L3, dock_L3, hall+dock_L3',
                       'viode': 'all (12 seq); also none, low, mid, high, none+low, mid+high, low+mid+high',
                       'openloris': 'held-out 8 sequences (cafe1-1 reported separately; also all 9)',
                       'uhumans2': 'all 3 (also 06h+12h, each)', 'monado': 'person MIO13+15+16 (also each, and static MIO07)'},
    'scripts_md5': scripts,
    'instantiation': inst,
}
yaml.safe_dump(P, open(fz, 'w'), sort_keys=False, width=150)
os.chmod(fz, 0o444)
open(NV + '/PROTOCOL.md5', 'w').write(f'{md5(fz)}  PROTOCOL.yaml\n')
os.chmod(NV + '/PROTOCOL.md5', 0o444)
# jobs: Monado first (longest, 2-offset chunks as real_world jobs_a2_r025), then the rest in two 5-offset halves; controls last
J = ['# NIS validation jobs: seq variant offsets start DSN=...']
for seq in DATASETS['monado']['seqs']:
    for v in ('sf1_nis', 'ov_nis'):
        for k in range(0, 10, 2):
            J.append(f"{seq} {v} {','.join(f'{x:.1f}' for x in offsets(seq)[k:k + 2])} {k + 1} DSN={DATASETS['monado']['dsn']}")
for ds in ('warehouse_t2', 'viode', 'openloris_uhumans2'):
    for seq in DATASETS[ds]['seqs']:
        for v in ('sf1_nis', 'ov_nis'):
            o = offsets(seq)
            for k in range(0, len(o), 5):
                J.append(f"{seq} {v} {','.join(f'{x:.1f}' for x in o[k:k + 5])} {k + 1} DSN={DATASETS[ds]['dsn']}")
for v in CTL:
    J.append(f'hall_t2_L3 {v} 0.0,0.2,0.4,0.6,0.8 1 DSN=nis_validation/runs/ctl')
open(NV + '/scripts/jobs.txt', 'w').write('\n'.join(J) + '\n')
print(md5(fz), len(J) - 1, 'jobs')
