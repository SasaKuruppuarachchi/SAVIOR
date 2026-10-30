# SPDX-License-Identifier: GPL-3.0-or-later
"""Render one SAVIOR-Warehouse sequence <scene>_<traj>_L<level> with Isaac Sim (headless).

  /home/sasa/isaacsim/python.sh isaac/render_sequence.py --scene aisles --level 2            # full render
  ... --plan                       # top-view occupancy + all paths + clearance report (no frames)
  ... --preview 5 --scale 0.25     # every 5th frame, cam0 segmentation only, low-res -> coverage estimate

Writes <data>/raw/<seq>/: cam0/ cam1/ (RGB png, <stamp_ns>.png), seg0/ seg1/ (uint16 instance ids png),
depth0/ (uint16 png, millimetres, 0 = invalid, 65535 = >= 65.535 m), imu_clean.csv, imu_noisy.csv, imu_bias.csv,
gt_imu_tum.txt (200 Hz), gt_cam0_tum.txt (frame rate), frames.csv, instances.json, moving.csv, coverage.csv,
actors.csv, calib/ (kalibr yaml + rig yaml), meta.json.
"""
import argparse
import importlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

import numpy as np  # noqa: E402

from wh import rig as whrig  # noqa: E402
from wh.classes import COLOR, NAMES, ROLE  # noqa: E402
from wh.scenario import CamRef, is_active, min_distance  # noqa: E402
from wh.se3 import rot_to_quat  # noqa: E402
from wh.trajectory import BodyTrajectory  # noqa: E402

FLIP = np.diag([1.0, -1.0, -1.0])   # OpenCV camera -> USD camera axes


def load_scene_module(name):
    """'aisles_t2' -> module scenes.aisles_t2; t3+: 'procedural:<traj id>' -> scenes.procedural.get('<traj id>'),
    an object with the same attributes as a scene module (NAME, TRAJ, SEED, PLAN_BOX, camera_cfg(), build())."""
    if ':' in name:
        mod, arg = name.split(':', 1)
        return importlib.import_module(f'scenes.{mod}').get(arg)
    return importlib.import_module(f'scenes.{name}')


def precompute(mod, rig, level):
    body = BodyTrajectory(mod.camera_cfg())
    t_imu, t_cam = whrig.time_grids(rig, body.duration)
    cam = CamRef(body)
    scene = mod.build(level, cam, body.duration)
    all_names = sorted(p.name for p in mod.build(3, cam, body.duration).people) + \
        sorted(f.name for f in mod.build(3, cam, body.duration).forklifts)
    return body, t_imu, t_cam, cam, scene, all_names


def write_motion_files(out, body, rig, t_imu, t_cam, seed):
    imu = whrig.synth_imu(body, rig, t_imu, seed)
    t0 = int(rig['time']['t0_ns'])
    ns = t0 + np.round(t_imu * 1e9).astype(np.int64)
    hdr_imu = '#timestamp [ns],w_RS_S_x [rad s^-1],w_RS_S_y [rad s^-1],w_RS_S_z [rad s^-1],' \
              'a_RS_S_x [m s^-2],a_RS_S_y [m s^-2],a_RS_S_z [m s^-2]'
    for name, g, a in (('imu_clean.csv', imu['gyro'], imu['acc']), ('imu_noisy.csv', imu['gyro_noisy'], imu['acc_noisy'])):
        with open(os.path.join(out, name), 'w') as fh:
            fh.write(hdr_imu + '\n')
            for k in range(len(ns)):
                fh.write(f'{ns[k]},{g[k,0]:.9e},{g[k,1]:.9e},{g[k,2]:.9e},{a[k,0]:.9e},{a[k,1]:.9e},{a[k,2]:.9e}\n')
    with open(os.path.join(out, 'imu_bias.csv'), 'w') as fh:
        fh.write('#timestamp [ns],bg_x [rad s^-1],bg_y,bg_z,ba_x [m s^-2],ba_y,ba_z\n')
        for k in range(len(ns)):
            b, c = imu['bg'][k], imu['ba'][k]
            fh.write(f'{ns[k]},{b[0]:.9e},{b[1]:.9e},{b[2]:.9e},{c[0]:.9e},{c[1]:.9e},{c[2]:.9e}\n')
    ev = imu['ev']
    q = rot_to_quat(ev['R'])
    with open(os.path.join(out, 'gt_imu_tum.txt'), 'w') as fh:
        fh.write('# timestamp[s] tx ty tz qx qy qz qw  (T_world_imu, IMU = body FLU, world Z up)\n')
        for k in range(len(ns)):
            p = ev['p'][k]
            fh.write(f'{ns[k] // 10**9}.{ns[k] % 10**9:09d} {p[0]:.9f} {p[1]:.9f} {p[2]:.9f} '
                     f'{q[k,1]:.9f} {q[k,2]:.9f} {q[k,3]:.9f} {q[k,0]:.9f}\n')
    with open(os.path.join(out, 'gt_imu_vel.csv'), 'w') as fh:
        fh.write('#timestamp [ns],v_x,v_y,v_z [m/s, world],w_x,w_y,w_z [rad/s, body]\n')
        for k in range(len(ns)):
            v, w = ev['v'][k], ev['w_b'][k]
            fh.write(f'{ns[k]},{v[0]:.9e},{v[1]:.9e},{v[2]:.9e},{w[0]:.9e},{w[1]:.9e},{w[2]:.9e}\n')
    # camera poses at frame times
    T_IC = whrig.cam_extrinsics(rig)
    evc = body.eval(t_cam)
    Tw = []
    for k in range(len(t_cam)):
        T_WI = np.eye(4)
        T_WI[:3, :3] = evc['R'][k]
        T_WI[:3, 3] = evc['p'][k]
        Tw.append([T_WI @ T_IC[0], T_WI @ T_IC[1]])
    nsc = t0 + np.round(t_cam * 1e9).astype(np.int64)
    qc = rot_to_quat(np.array([T[0][:3, :3] for T in Tw]))
    with open(os.path.join(out, 'gt_cam0_tum.txt'), 'w') as fh:
        fh.write('# timestamp[s] tx ty tz qx qy qz qw  (T_world_cam0, OpenCV camera axes)\n')
        for k in range(len(nsc)):
            p = Tw[k][0][:3, 3]
            fh.write(f'{nsc[k] // 10**9}.{nsc[k] % 10**9:09d} {p[0]:.9f} {p[1]:.9f} {p[2]:.9f} '
                     f'{qc[k,1]:.9f} {qc[k,2]:.9f} {qc[k,3]:.9f} {qc[k,0]:.9f}\n')
    with open(os.path.join(out, 'frames.csv'), 'w') as fh:
        fh.write('#frame,timestamp [ns]\n')
        for k in range(len(nsc)):
            fh.write(f'{k},{nsc[k]}\n')
    return Tw, nsc, imu


def _discs(actor, path, t):
    """Footprint discs (centres [n, k, 2], radii [k]) of an actor at times t: forklift = 3 discs along its axis."""
    a = path.at(t)
    xy = a['xy']
    if actor.__class__.__name__ == 'Forklift':
        h = a['heading'] if 'heading' in a else np.full(len(t), np.deg2rad(actor.pose[2]))
        u = np.stack([np.cos(h), np.sin(h)], -1)
        if getattr(actor, 'kind', 'forklift') == 'cart':      # t3+: dolly 0.85 x 1.26 m -> 2 discs r 0.45
            off = np.array([-0.2, 0.2])
            return xy[:, None, :] + off[None, :, None] * u[:, None, :], np.array([0.45, 0.45])
        off = np.array([-1.15, 0.0, 1.15])
        return xy[:, None, :] + off[None, :, None] * u[:, None, :], np.array([0.68, 0.68, 0.68])
    return xy[:, None, :], np.array([0.3])


def check_paths(scene, cam, duration):
    """Min clearances camera <-> actors and actor <-> actor (planar footprints: person disc r 0.3, forklift 3 discs
    r 0.68, camera/drone disc r 0.35)."""
    rep = []
    tt = np.arange(0, duration, 0.05)
    actors = [(p.name, p.path, p) for p in scene.people] + \
             [(f.name, f.path if f.path is not None else _parked_path(f), f) for f in scene.forklifts]
    camxy = cam.xy_at(tt)
    disc = {n: _discs(ac, pth, tt) for n, pth, ac in actors}
    for n, pth, ac in actors:
        c, r = disc[n]
        d = np.min(np.linalg.norm(c - camxy[:, None, :], axis=2) - r[None], axis=1) - 0.35
        d = np.where(is_active(ac, tt), d, 1e9)
        k = int(np.argmin(d))
        rep.append((f'cam-{n}', float(np.linalg.norm(pth.at(tt[k:k+1])['xy'][0] - camxy[k])), float(tt[k]), float(d[k])))
    for i in range(len(actors)):
        for j in range(i + 1, len(actors)):
            a, b = actors[i], actors[j]
            if getattr(a[2], 'path', 1) is None and getattr(b[2], 'path', 1) is None:
                continue
            if getattr(a[2], 'attached_to', None) == b[0] or getattr(b[2], 'attached_to', None) == a[0]:
                continue   # t3+: a person pushing this cart
            (ca, ra), (cb, rb) = disc[a[0]], disc[b[0]]
            d = np.linalg.norm(ca[:, :, None, :] - cb[:, None, :, :], axis=3) - ra[None, :, None] - rb[None, None, :]
            d = d.reshape(len(tt), -1).min(1)
            d = np.where(is_active(a[2], tt) & is_active(b[2], tt), d, 1e9)
            k = int(np.argmin(d))
            cd = float(np.linalg.norm(a[1].at(tt[k:k+1])['xy'][0] - b[1].at(tt[k:k+1])['xy'][0]))
            rep.append((f'{a[0]}-{b[0]}', cd, float(tt[k]), float(d[k])))
    return rep


class _Static:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def at(self, t):
        t = np.asarray(t, float)
        return dict(xy=np.stack([np.full(t.shape, self.x), np.full(t.shape, self.y)], -1))


def _parked_path(f):
    return _Static(f.pose[0], f.pose[1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scene', required=True)
    ap.add_argument('--level', type=int, default=0)
    ap.add_argument('--rig', default=os.path.join(common.PKG, 'configs', 'rig_zed2i_4mm.yaml'))
    ap.add_argument('--out', default='')
    ap.add_argument('--plan', action='store_true', help='only write the plan view + clearance report')
    ap.add_argument('--preview', type=int, default=0, help='>0: render every N-th frame, cam0 seg only')
    ap.add_argument('--scale', type=float, default=1.0, help='resolution scale (preview)')
    ap.add_argument('--frames', default='', help='a:b frame range, or a comma separated frame list (debug)')
    ap.add_argument('--subframes', type=int, default=4, help='RTX subframes per frame (temporal convergence)')
    ap.add_argument('--no-depth', action='store_true')
    ap.add_argument('--png-level', type=int, default=3)
    ap.add_argument('--plan-dir', default='', help='directory of the --plan image (default <data>/preview)')
    args = ap.parse_args()

    mod = load_scene_module(args.scene)
    rig = whrig.load_rig(args.rig)
    seq = f'{mod.NAME}_{mod.TRAJ}_L{args.level}'
    body, t_imu, t_cam, cam, scene, all_names = precompute(mod, rig, args.level)
    print(f'[render] {seq}: duration {body.duration:.2f} s, {len(t_cam)} frames, path {cam.L:.1f} m, '
          f'yaw knot dt {body.yaw_knot_dt:.2f}, people {len(scene.people)}, forklifts {len(scene.forklifts)}', flush=True)
    for name, d, t, clr in check_paths(scene, cam, body.duration):
        if clr < 0.25:
            print(f'[render]   WARNING clearance {name}: centre distance {d:.2f} m at t={t:.1f} s (clearance {clr:.2f})')

    out = args.out or os.path.join(common.DATA, 'raw' if not (args.preview or args.plan) else 'preview_runs', seq)
    os.makedirs(out, exist_ok=True)
    full = not (args.preview or args.plan)
    if full:
        Tw, nsc, imu = write_motion_files(out, body, rig, t_imu, t_cam, mod.SEED)
        whrig.write_kalibr(rig, os.path.join(out, 'calib'))
        import shutil
        shutil.copy(args.rig, os.path.join(out, 'calib', 'rig.yaml'))
    else:
        T_IC = whrig.cam_extrinsics(rig)
        evc = body.eval(t_cam)
        Tw = []
        for k in range(len(t_cam)):
            T_WI = np.eye(4)
            T_WI[:3, :3], T_WI[:3, 3] = evc['R'][k], evc['p'][k]
            Tw.append([T_WI @ T_IC[0], T_WI @ T_IC[1]])
        nsc = int(rig['time']['t0_ns']) + np.round(t_cam * 1e9).astype(np.int64)

    app = common.start_app()
    common.render_settings()
    import cv2
    import omni.replicator.core as rep
    from pxr import Gf, UsdGeom
    from stage_builder import StageBuilder
    sb = StageBuilder(scene, all_names)
    st = sb.build(app)

    if args.plan:
        write_plan(sb, mod, scene, cam, body, out, seq, args.plan_dir)
        app.close()
        return

    K, (W, H) = whrig.intrinsics(rig)
    W, H = int(round(W * args.scale)), int(round(H * args.scale))
    px = 0.01
    cams, ops = [], []
    st.DefinePrim('/World/Rig', 'Xform')
    for i in range(1 if args.preview else 2):
        c = UsdGeom.Camera.Define(st, f'/World/Rig/cam{i}')
        c.GetHorizontalApertureAttr().Set(W * px)
        c.GetVerticalApertureAttr().Set(H * px)
        c.GetFocalLengthAttr().Set(K[0] * args.scale * px)
        c.GetClippingRangeAttr().Set(Gf.Vec2f(float(rig['camera']['clip_near']), float(rig['camera']['clip_far'])))
        x = UsdGeom.Xformable(c.GetPrim())
        x.ClearXformOpOrder()
        ops.append(x.AddTransformOp(UsdGeom.XformOp.PrecisionDouble))
        cams.append(c)
    rps = [rep.create.render_product(c.GetPath(), (W, H)) for c in cams]
    an = {}
    for i, rp in enumerate(rps):
        if not args.preview:
            an[f'rgb{i}'] = rep.AnnotatorRegistry.get_annotator('rgb')
            an[f'rgb{i}'].attach(rp)
        an[f'seg{i}'] = rep.AnnotatorRegistry.get_annotator('instance_id_segmentation_fast')
        an[f'seg{i}'].attach(rp)
    if not args.preview and not args.no_depth:
        an['depth0'] = rep.AnnotatorRegistry.get_annotator('distance_to_image_plane')
        an['depth0'].attach(rps[0])
    for _ in range(5):
        app.update()

    for d in (['cam0', 'cam1', 'seg0', 'seg1'] + ([] if args.no_depth else ['depth0'])) if full else []:
        os.makedirs(os.path.join(out, d), exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(8)
    futs = []
    png = [cv2.IMWRITE_PNG_COMPRESSION, args.png_level]

    idx = np.arange(len(t_cam))
    if args.frames and ',' in args.frames:
        idx = np.array([int(v) for v in args.frames.split(',')])
    elif args.frames:
        a, b = args.frames.split(':')
        idx = idx[int(a or 0):int(b) if b else None]
    if args.preview:
        idx = idx[::args.preview]
    cls_of = {i['id']: i['cls'] for i in sb.instances}
    max_id = max([i['id'] for i in sb.instances] + [1])
    cls_idx = np.zeros(max_id + 1, np.int16) - 1
    for i in sb.instances:
        cls_idx[i['id']] = NAMES.index(i['cls'])
    cov_rows, mov_rows, act_rows = [], [], []
    seen = {}
    moving_ever = set()
    t_start = time.time()
    for n, k in enumerate(idx):
        t = float(t_cam[k])
        speeds = sb.update(t)
        mov = sb.moving_ids(speeds)
        moving_ever |= mov
        for i, T in enumerate(Tw[k][:len(cams)]):
            M = np.eye(4)
            M[:3, :3] = T[:3, :3] @ FLIP
            M[:3, 3] = T[:3, 3]
            ops[i].Set(Gf.Matrix4d(M.T.tolist()))
        rep.orchestrator.step(rt_subframes=1 if args.preview else args.subframes, delta_time=0.0)
        segs = []
        for i in range(len(cams)):
            d = an[f'seg{i}'].get_data()
            lut = sb.lut(d['info']['idToLabels'])
            raw = d['data']
            raw = np.where(raw < len(lut), raw, 0)
            segs.append(lut[raw])
        s0 = segs[0]
        cnt = np.bincount(s0.ravel(), minlength=max_id + 1)
        npx = s0.size
        vis = np.nonzero(cnt[1:])[0] + 1
        for v in vis:
            seen[int(v)] = seen.get(int(v), 0) + 1
        movm = np.zeros(max_id + 1, bool)
        if mov:
            movm[list(mov)] = True
        frac = lambda m: float(cnt[m].sum()) / npx  # noqa: E731
        per_cls = {c: frac((cls_idx == j) & movm) for j, c in enumerate(NAMES)}
        all_cls = {c: frac(cls_idx == j) for j, c in enumerate(NAMES)}
        row = dict(frame=int(k), t=t, moving=frac(movm),
                   moving_inst=int(np.count_nonzero(cnt[movm])),
                   person=all_cls['person'], potential=sum(all_cls[c] for c in NAMES if ROLE[c] == 'potential'),
                   **{f'mov_{c}': per_cls[c] for c in ('person', 'forklift', 'box', 'pallet', 'trolley')})
        cov_rows.append(row)
        mov_rows.append((int(k), int(nsc[k]), sorted(int(m) for m in mov)))
        for f in scene.forklifts + scene.people:
            if getattr(f, 'path', None) is not None:
                a = f.path.at(t)
                act_rows.append((int(k), int(nsc[k]), f.name, a['xy'][0], a['xy'][1], a['heading'], a['speed']))
        if full:
            stamp = int(nsc[k])
            for i in range(2):
                rgb = an[f'rgb{i}'].get_data()[..., :3]
                futs.append(pool.submit(cv2.imwrite, os.path.join(out, f'cam{i}', f'{stamp}.png'),
                                        np.ascontiguousarray(rgb[..., ::-1]), png))
                futs.append(pool.submit(cv2.imwrite, os.path.join(out, f'seg{i}', f'{stamp}.png'),
                                        segs[i].astype(np.uint16), png))
            if 'depth0' in an:
                dep = an['depth0'].get_data()
                dmm = np.where(np.isfinite(dep) & (dep > 0), np.minimum(dep * 1000.0 + 0.5, 65535), 0).astype(np.uint16)
                futs.append(pool.submit(cv2.imwrite, os.path.join(out, 'depth0', f'{stamp}.png'), dmm, png))
            if len(futs) > 400:
                for f_ in futs:
                    f_.result()
                futs = []
        if n % 50 == 0:
            el = time.time() - t_start
            print(f'[render] {seq} frame {n}/{len(idx)} t={t:.2f} moving={row["moving"]*100:.1f}% '
                  f'{(n + 1) / max(el, 1e-6):.2f} fps', flush=True)
    for f_ in futs:
        f_.result()
    el = time.time() - t_start
    # ---- summaries
    import csv
    keys = list(cov_rows[0].keys())
    with open(os.path.join(out, 'coverage.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in cov_rows:
            w.writerow({k_: (f'{v:.6f}' if isinstance(v, float) else v) for k_, v in r.items()})
    with open(os.path.join(out, 'moving.csv'), 'w') as fh:
        fh.write('#frame,timestamp [ns],moving instance ids (space separated)\n')
        for k, s, m in mov_rows:
            fh.write(f'{k},{s},{" ".join(map(str, m))}\n')
    with open(os.path.join(out, 'actors.csv'), 'w') as fh:
        fh.write('#frame,timestamp [ns],actor,x,y,heading [rad],speed [m/s]\n')
        for r in act_rows:
            fh.write(f'{r[0]},{r[1]},{r[2]},{r[3]:.5f},{r[4]:.5f},{r[5]:.5f},{r[6]:.5f}\n')
    # moving intervals per instance
    intervals = {}
    for i in sb.instances:
        if i['actor'] is None:
            continue
        flags = [i['id'] in set(m) for _, _, m in mov_rows]
        iv, st_ = [], None
        for (k, s, _), f in zip(mov_rows, flags):
            if f and st_ is None:
                st_ = s
            if not f and st_ is not None:
                iv.append([st_, prev])
                st_ = None
            prev = s
        if st_ is not None:
            iv.append([st_, prev])
        intervals[i['id']] = iv
    inst = [dict(id=i['id'], name=i['name'], cls=i['cls'], role=ROLE[i['cls']], prim=i['root'], actor=i['actor'],
                 moving_ever=i['id'] in moving_ever, moving_intervals_ns=intervals.get(i['id'], []),
                 frames_visible_cam0=seen.get(i['id'], 0), color=COLOR[i['cls']]) for i in sb.instances]
    with open(os.path.join(out, 'instances.json'), 'w') as fh:
        json.dump(dict(sequence=seq, moving_speed_threshold=0.05, classes=NAMES, instances=inst), fh, indent=1)
    cov = np.array([r['moving'] for r in cov_rows])
    meta = dict(sequence=seq, scene=mod.NAME, traj=mod.TRAJ, level=args.level, frames=len(idx),
                duration_s=float(body.duration), path_length_m=float(cam.L), render_s=el, fps=len(idx) / el,
                subframes=args.subframes, scale=args.scale, preview=args.preview,
                coverage_moving_mean=float(cov.mean()), coverage_moving_p90=float(np.percentile(cov, 90)),
                frames_moving_gt_5pct=float(np.mean(cov > 0.05)), isaac='6.0.1-rc.7', renderer='RaytracedLighting')
    with open(os.path.join(out, 'meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    print(f'[render] {seq} done: {len(idx)} frames in {el:.0f} s ({len(idx)/el:.2f} fps); moving coverage mean '
          f'{cov.mean()*100:.2f} % p90 {np.percentile(cov, 90)*100:.2f} %, frames>5%: {np.mean(cov > 0.05)*100:.0f} %',
          flush=True)
    app.close()


def write_plan(sb, mod, scene, cam, body, out, seq, plan_dir=''):
    import cv2
    x0, y0, x1, y1 = mod.PLAN_BOX
    res = 0.05
    occ = sb.occupancy(x0, y0, x1, y1, res)
    img = cv2.cvtColor(255 - occ, cv2.COLOR_GRAY2BGR)
    H, W = occ.shape

    def uv(xy):
        xy = np.atleast_2d(xy)
        return np.c_[(xy[:, 0] - x0) / res, (y1 - xy[:, 1]) / res].astype(np.int32)

    for gx in range(int(np.ceil(x0)), int(x1) + 1):
        if gx % 5 == 0:
            cv2.line(img, (int((gx - x0) / res), 0), (int((gx - x0) / res), H - 1), (230, 200, 200), 1)
            cv2.putText(img, str(gx), (int((gx - x0) / res) + 2, 12), 0, 0.4, (200, 0, 0), 1)
    for gy in range(int(np.ceil(y0)), int(y1) + 1):
        if gy % 5 == 0:
            cv2.line(img, (0, int((y1 - gy) / res)), (W - 1, int((y1 - gy) / res)), (200, 200, 230), 1)
            cv2.putText(img, str(gy), (2, int((y1 - gy) / res) - 2), 0, 0.4, (0, 0, 200), 1)
    # clearance of the camera path
    free = (occ == 0).astype(np.uint8)
    dist = cv2.distanceTransform(free, cv2.DIST_L2, 5) * res
    p = uv(cam.xy)
    ok = (p[:, 0] >= 0) & (p[:, 0] < W) & (p[:, 1] >= 0) & (p[:, 1] < H)
    clr = dist[p[ok, 1], p[ok, 0]]
    cv2.polylines(img, [p], False, (0, 0, 0), 2)
    for tt in range(0, int(body.duration), 10):
        q = uv(cam.xy_at(tt))[0]
        cv2.circle(img, tuple(int(v) for v in q), 4, (0, 0, 0), -1)
        cv2.putText(img, f'{tt}', (int(q[0]) + 4, int(q[1]) - 4), 0, 0.4, (0, 0, 0), 1)
    rng = np.random.default_rng(3)
    lines = [f'{seq}: camera path {cam.L:.1f} m, duration {body.duration:.1f} s, '
             f'min static clearance {clr.min():.2f} m at t={cam.t[ok][np.argmin(clr)]:.1f} s']
    for a in scene.people + scene.forklifts:
        pth = getattr(a, 'path', None)
        col = tuple(int(c) for c in rng.integers(0, 200, 3))
        if pth is None:
            continue
        tt = np.arange(0, body.duration, 0.1)
        xy = pth.at(tt)['xy']
        cv2.polylines(img, [uv(xy)], False, col, 1)
        q = uv(xy[0])[0]
        cv2.putText(img, a.name, (int(q[0]) + 3, int(q[1]) + 10), 0, 0.35, col, 1)
        for t10 in range(0, int(body.duration), 10):
            q = uv(pth.at(t10)['xy'])[0]
            cv2.circle(img, tuple(int(v) for v in q), 2, col, -1)
        pp = uv(xy)
        okk = (pp[:, 0] >= 0) & (pp[:, 0] < W) & (pp[:, 1] >= 0) & (pp[:, 1] < H)
        dmin = dist[pp[okk, 1], pp[okk, 0]].min() if okk.any() else -1
        lines.append(f'  {a.name}: min static clearance (centre) {dmin:.2f} m')
    for name, d, t, c in check_paths(scene, cam, body.duration):
        if c < 0.5:
            lines.append(f'  close: {name} {d:.2f} m at t={t:.1f} s (clearance {c:.2f})')
    path = os.path.join(plan_dir or os.path.join(common.DATA, 'preview'), f'plan_{seq}.png')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img)
    np.savez_compressed(os.path.join(out, 'occupancy.npz'), occ=occ, x0=x0, y0=y0, x1=x1, y1=y1, res=res)
    print('\n'.join('[plan] ' + s for s in lines))
    print(f'[plan] wrote {path}')


if __name__ == '__main__':
    main()
