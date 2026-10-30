#!/usr/bin/env python3
"""make_design.py : write and FREEZE results/t3_confirmatory/DESIGN.yaml (run once, before any t3 rendering).

1. structural pre-render check of every frozen seed with the numpy generator (scenes/procedural.py; no Isaac, no
   rendering, no VIO): the seed must yield a camera tour, >= 1 L3 co-mover, >= 3 L2 forklifts / carts and >= 6 moving
   L1 walkers; a failing seed is replaced by the next spare seed of its site (rule written in the design itself).
2. md5 of the generator / renderer code, the rig and the frozen configs the analysis depends on.
3. DESIGN.yaml (read-only) + DESIGN.md5. Refuses to overwrite an existing DESIGN.yaml.
"""
import datetime
import hashlib
import json
import os
import stat
import sys

import numpy as np
import yaml

WS = '/home/sasa/workspace/savior_ws'
PKG = f'{WS}/src/savior/savior_datasets/warehouse'
T = f'{WS}/results/t3_confirmatory'
sys.path.insert(0, PKG)
from scenes import procedural as pr  # noqa: E402
from wh.scenario import CamRef, Forklift, Person  # noqa: E402
from wh.trajectory import BodyTrajectory  # noqa: E402

md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
N_PER_SITE = 6
SITES = ['fw', 'sw', 'ms', 'wx']


def seeds(i, k):
    return 31000 + 1000 * i + 101 * (k + 1)


def structural(site, seed):
    try:
        return _structural(site, seed)
    except Exception as e:   # generator failure -> spare seed (pre-render rule)
        return False, dict(error=repr(e))


def _structural(site, seed):
    sc = pr.ProceduralScene(f'chk{site}{seed}', site, seed)
    body = BodyTrajectory(sc.camera_cfg())
    cam = CamRef(body)
    C = sc.choreo(cam, body)
    moving = lambda a: a.path is not None and float(np.max(a.path.speed)) > 0.05  # noqa: E731
    n3 = sum(1 for a, t, _ in C.acc if t == 3 and isinstance(a, Forklift) and a.kind == 'forklift' and a.name in ('Q1', 'Q2'))
    n2 = sum(1 for a, t, _ in C.acc if t == 2 and isinstance(a, Forklift) and moving(a))
    n1 = sum(1 for a, t, _ in C.acc if t == 1 and isinstance(a, Person) and moving(a))
    ok = n3 >= 1 and n2 >= 3 and n1 >= 6
    sm = sc.summary(cam, body)
    sm.pop('log')
    return ok, dict(co_movers=n3, l2_moving_vehicles=n2, l1_moving_people=n1, **sm)


def main():
    dry = '--dry-run' in sys.argv
    if os.path.exists(f'{T}/DESIGN.yaml') and not dry:
        sys.exit('DESIGN.yaml exists (frozen); refusing to overwrite')
    trajs, replaced, struct = [], [], {}
    for i, site in enumerate(SITES):
        cand = [seeds(i, k) for k in range(N_PER_SITE + 6)]        # 6 frozen + 6 spare seeds per site, in order
        used = []
        for sd in cand:
            ok, info = structural(site, sd)
            struct[f'{site}:{sd}'] = dict(ok=ok, **info)
            if ok:
                used.append(sd)
            else:
                replaced.append(dict(site=site, seed=sd, reason=info))
            if len(used) == N_PER_SITE:
                break
        assert len(used) == N_PER_SITE, f'not enough valid seeds for {site}'
        for k, sd in enumerate(used):
            trajs.append(dict(id=f'{site}{k + 1:02d}', site=site, seed=int(sd)))
    table = {t['id']: (t['site'], t['seed']) for t in trajs}
    print('trajectories:', table, 'replaced:', [(r['site'], r['seed']) for r in replaced])
    if dry:
        return
    assert table == pr.TRAJECTORIES, 'scenes/procedural.py TRAJECTORIES must equal the checked seed table'
    files = ['scenes/procedural.py', 'scenes/full_warehouse.py', 'isaac/render_sequence.py', 'isaac/stage_builder.py',
             'isaac/common.py', 'wh/scenario.py', 'wh/trajectory.py', 'wh/rig.py', 'wh/classes.py', 'wh/se3.py',
             'configs/rig_zed2i_4mm.yaml', 'tools/to_ros2.py', 'tools/render_t3.sh', 'tools/check_imu.py',
             'tools/check_geometry.py', 'tools/coverage_report.py']
    frozen = ['results/backend_v2/backend_config.yaml', 'results/backend_v2/config/warehouse/estimator_config.yaml',
              'results/p7/final_config.yaml', 'results/p7/final_config_addendum.yaml', 'results/vins_savior/FREEZE.md5',
              'results/stats_v3/scripts/stats3_core.py', 'results/t3_confirmatory/scripts/power_t3.py',
              'results/t3_confirmatory/scripts/stats_t3.py', 'results/t3_confirmatory/scripts/t3_checks.py',
              'results/t3_confirmatory/scripts/run_t3.sh', 'results/t3_confirmatory/scripts/run_t3_ov2.sh',
              'results/t3_confirmatory/scripts/export_masks_t3.py', 'results/t3_confirmatory/scripts/sanity_t3.sh',
              'models/warehouse/yolo26s-seg-warehouse.engine']
    P = json.load(open(f'{T}/tables/power.json'))
    D = yaml.safe_load(open(f'{T}/scripts/design_template.yaml'))
    now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    D['frozen_at'] = now
    D['dataset']['trajectories'] = trajs
    D['dataset']['seed_replacements_pre_render'] = replaced
    D['dataset']['structural_check'] = {k: {kk: vv for kk, vv in v.items() if kk in (
        'ok', 'co_movers', 'l2_moving_vehicles', 'l1_moving_people', 'path_m', 'duration_s', 'lane_w', 'props', 'parked')}
        for k, v in struct.items()}
    D['code_md5'] = {f: md5(f'{PKG}/{f}') for f in files}
    D['frozen_inputs_md5'] = {f: md5(f'{WS}/{f}') for f in frozen if os.path.isfile(f'{WS}/{f}')}
    D['analysis_plan']['power']['table'] = {h: dict(power_A=[round(x, 3) for x in v.get('power_A', [])],
                                                     power_B=[round(x, 3) for x in v.get('power_B', [])],
                                                     power_A_half_effect=[round(x, 3) for x in v.get('power_A_half', [])])
                                            if h != 'P5' else dict(tost_by_true_ratio={r: [round(x, 3) for x in p] for r, p in
                                                                                       v['power_tost_by_true_ratio'].items()})
                                            for h, v in P['hyp'].items()}
    D['analysis_plan']['power']['n_grid'] = P['n_grid']
    D['analysis_plan']['power']['gate_P1_to_P4_A'] = [round(x, 3) for x in P['gate_P1_to_P4_A']]
    head = ('# SAVIOR-Warehouse t3 CONFIRMATORY split: PRE-REGISTERED DESIGN. FROZEN at ' + now + ' before any t3\n'
            '# rendering (only numpy generator checks and dev-seed previews existed). Do not edit: its md5 is in DESIGN.md5\n'
            '# and src/savior/docs/IMPLEMENTATION_PLAN.md section 6. A change needs a new, dated, disclosed amendment file.\n')
    with open(f'{T}/DESIGN.yaml', 'w') as fh:
        fh.write(head)
        yaml.safe_dump(D, fh, sort_keys=False, width=120, allow_unicode=True)
    os.chmod(f'{T}/DESIGN.yaml', stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    h = md5(f'{T}/DESIGN.yaml')
    open(f'{T}/DESIGN.md5', 'w').write(f'{h}  DESIGN.yaml\n')
    print('DESIGN.yaml', h, len(trajs), 'trajectories; replaced', [(r['site'], r['seed']) for r in replaced])


if __name__ == '__main__':
    main()
