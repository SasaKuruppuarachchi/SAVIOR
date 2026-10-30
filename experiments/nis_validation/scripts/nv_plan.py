"""nv_plan.py: the NIS-validation plan (datasets, sequences, offsets, run directories, pairings). Imported by every script."""
WS = '/home/sasa/workspace/savior_ws'
R = WS + '/results'
NV = R + '/nis_validation'
VARIANTS = ['sf1_nis', 'ov_nis']
WH = [f'{s}_t2_{l}' for s in ('aisles', 'hall', 'dock') for l in ('L0', 'L1', 'L2', 'L3')]
VI = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
OL = ['cafe1-1', 'cafe1-2', 'office1-1', 'office1-2', 'office1-3', 'office1-4', 'office1-5', 'office1-6', 'office1-7']
EQ = [f'openloris_{s}' for s in OL] + [f'uhumans2_office_s1_{h}' for h in ('00h', '06h', '12h')]
RW = ['MIO13', 'MIO15', 'MIO16', 'MIO07']
W10 = [round(0.2 * k, 1) for k in range(10)]
VOFF = {'parking_lot': [5.5, 5.7, 5.9, 6.1, 6.3, 6.5, 6.7, 6.9, 7.1, 7.3], 'city_day': [4.1, 4.3, 4.5, 4.7, 4.9, 5.1, 5.3, 5.5, 5.7, 5.9],
        'city_night': [6.1, 6.3, 6.5, 6.7, 6.9, 7.1, 7.3, 7.5, 7.7, 7.9]}
DATASETS = {
    'warehouse_t2': dict(seqs=WH, dsn='nis_validation/runs/t2', rate=0.5, fail=2.0,
                         ref_root=R + '/backend_v2/heldout/runs', ref_openvins='openvins',
                         baselines={'openvins': R + '/backend_v2/heldout/runs', 'sens_fix1': R + '/backend_v2/heldout/runs',
                                    'yolo_naive': R + '/backend_v2/heldout/runs', 'ovchi_best': R + '/review_runs/runs/heldout',
                                    'sf1_chibest': R + '/review_runs/runs/heldout'},
                         base_dir={'sf1_nis': 'sens_fix1', 'ov_nis': 'openvins'}, settings_glob='bv2_settings_*.txt'),
    'viode': dict(seqs=VI, dsn='nis_validation/runs/viode', rate=0.5, fail=1.0,
                  ref_root=R + '/backend_v2/heldout/runs', ref_openvins='openvins',
                  baselines={'openvins': R + '/backend_v2/heldout/runs', 'sens_fix1': R + '/backend_v2/heldout/runs',
                             'yolo_naive': R + '/backend_v2/heldout/runs', 'ovchi_best': R + '/review_runs/runs/heldout',
                             'sf1_chibest': R + '/review_runs/runs/heldout'},
                  base_dir={'sf1_nis': 'sens_fix1', 'ov_nis': 'openvins'}, settings_glob='bv2_settings_*.txt'),
    'openloris_uhumans2': dict(seqs=EQ, dsn='nis_validation/runs/e', rate=0.5, fail=1.0,
                               ref_root=R + '/review_runs/runs/e', ref_openvins='e_openvins',
                               baselines={'openvins': (R + '/review_runs/runs/e', 'e_openvins'),
                                          'sens_fix1': (R + '/review_runs/runs/e', 'e_sens_fix1'),
                                          'yolo_naive': (R + '/review_runs/runs/e', 'e_yolo_naive')},
                               base_dir={'sf1_nis': 'e_sens_fix1', 'ov_nis': 'e_openvins'}, settings_glob='rr_settings_*.txt'),
    'monado': dict(seqs=RW, dsn='nis_validation/runs/rw', rate=0.25, fail=1.0,
                   ref_root=R + '/real_world/runs', ref_openvins='openvins',
                   baselines={'openvins': R + '/real_world/runs', 'sens_fix1': R + '/real_world/runs',
                              'yolo_naive': R + '/real_world/runs', 'vins_fusion': R + '/real_world/runs'},
                   base_dir={'sf1_nis': 'sens_fix1', 'ov_nis': 'openvins'}, settings_glob='rw_settings_*.txt'),
}
CAP = 10.0


def dataset_of(seq):
    for k, d in DATASETS.items():
        if seq in d['seqs']:
            return k
    raise KeyError(seq)


def offsets(seq):
    if seq.startswith(tuple(VOFF)):
        return VOFF[next(e for e in VOFF if seq.startswith(e))]
    if seq == 'uhumans2_office_s1_00h':
        return W10[:5]      # task E / P3a: 5 offsets 0.0-0.8 s
    return W10


def baseline_dir(ds, m, seq):
    b = DATASETS[ds]['baselines'][m]
    root, name = (b if isinstance(b, tuple) else (b, m))
    return f'{root}/{seq}/{name}'


def run_dir(ds, var, seq):
    return f"{R}/{DATASETS[ds]['dsn']}/{seq}/{var}"
