# SPDX-License-Identifier: GPL-3.0-or-later
"""SAVIOR-Warehouse segmentation training set (domain randomised RGB + COCO instance annotations, 8 classes).

  $HOME/isaacsim/python.sh isaac/render_segtrain.py [--layouts 16] [--per-layout 170] [--val-every 8]

Per layout seed (scenes/segtrain.py): base static layout (aisles | hall) + random forklifts (driverless / driven,
loads, fork heights) and people (walking / idle, 10 characters). Domain randomisation:
  * lighting preset per layout (default / cool-bright / warm-dim) + per-frame intensity jitter of every env light;
  * textures: floor material (original or one of 4 MDLs), wood MDLs on a random subset of pallets, random
    cardboard / plastic tints on a random subset of boxes, guard-rail colour;
  * camera: random pose on the free lanes of the layout (>= 0.3 m from obstacles), aimed at a random object 1.5-15 m
    away (actors preferred), height 0.3-2.6 m, pitch -30..+10 deg, roll ~ N(0, 3 deg); focal length 470 px (ZED 2i 4 mm) or 264 px (2.1 mm), 672x376;
  * time: actors are posed at a random time of their (short) scripted motion -> walking / driving poses.
Output <data>/seg_train/: images/{train,val}/*.jpg, masks/{train,val}/*.png (uint16 instance ids),
annotations/instances_{train,val}.json (COCO polygons, iscrowd 0), meta.json.
Seeds whose index % val_every == val_every - 1 go to val (unseen layouts).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

import numpy as np  # noqa: E402

from wh.classes import CLASSES, COCO_ID, NAMES  # noqa: E402

FLOORS = [None, None, 'Natural/Asphalt', 'Stone/Slate', 'Stone/Granite_Dark', 'Stone/Porcelain_Tile_4_Linen']
WOODS = ['Wood/Oak', 'Wood/Ash_Planks', 'Wood/Walnut_Planks', 'Wood/Bamboo']
LIGHTS = {'default': (1.0, (1.0, 1.0, 1.0)), 'cool': (1.5, (0.82, 0.9, 1.0)), 'warm_dim': (0.45, (1.0, 0.82, 0.62))}
BOX_TINTS = [(0.62, 0.45, 0.28), (0.75, 0.6, 0.42), (0.9, 0.88, 0.82), (0.25, 0.4, 0.75), (0.8, 0.2, 0.15),
             (0.2, 0.55, 0.3), (0.5, 0.36, 0.22)]
RAIL_COLS = [(0.95, 0.72, 0.03), (0.85, 0.1, 0.08), (0.08, 0.08, 0.08), (0.2, 0.35, 0.8)]


def mdl_material(stage, path, rel):
    from pxr import Sdf, UsdShade
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, path + '/Shader')
    sh.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    sh.SetSourceAsset(Sdf.AssetPath(common.asset(f'Isaac/Materials/Base/{rel}.mdl')), 'mdl')
    sh.SetSourceAssetSubIdentifier(rel.split('/')[-1], 'mdl')
    mat.CreateSurfaceOutput('mdl').ConnectToSource(sh.ConnectableAPI(), 'out')
    return mat


def tint_material(stage, path, rgb, rough=0.7, metal=0.0):
    from pxr import Gf, Sdf, UsdShade
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, path + '/Shader')
    sh.CreateIdAttr('UsdPreviewSurface')
    sh.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    sh.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(rough)
    sh.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(metal)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), 'surface')
    return mat


def bind(prim, mat):
    from pxr import Usd, UsdShade
    for p in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
        if p.IsInstanceProxy():
            continue
        if p.GetTypeName() in ('Mesh', 'Cube', 'Cylinder'):
            UsdShade.MaterialBindingAPI.Apply(p).Bind(mat, UsdShade.Tokens.strongerThanDescendants)
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, UsdShade.Tokens.strongerThanDescendants)


def coco_polys(mask):
    import cv2
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cnts:
        if len(c) >= 3 and cv2.contourArea(c) >= 4:
            polys.append(c.reshape(-1).astype(float).tolist())
    return polys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--layouts', type=int, default=16)
    ap.add_argument('--per-layout', type=int, default=170)
    ap.add_argument('--val-every', type=int, default=8)
    ap.add_argument('--seed0', type=int, default=1000)
    ap.add_argument('--subframes', type=int, default=12)
    ap.add_argument('--out', default=os.path.join(common.DATA, 'seg_train'))
    ap.add_argument('--min-area', type=int, default=40)
    args = ap.parse_args()
    from scenes.segtrain import build_random
    app = common.start_app()
    common.render_settings()
    import cv2
    import omni.replicator.core as rep
    from pxr import Gf, Usd, UsdGeom, UsdLux
    from stage_builder import StageBuilder
    W, H = 672, 376
    for d in ('images/train', 'images/val', 'masks/train', 'masks/val', 'annotations'):
        os.makedirs(os.path.join(args.out, d), exist_ok=True)
    coco = {s: dict(images=[], annotations=[], categories=[dict(id=COCO_ID[n], name=n, supercategory=r)
                                                           for n, r, _, _ in CLASSES]) for s in ('train', 'val')}
    ann_id = 1
    t_all = time.time()
    stats = {s: {n: 0 for n in NAMES} for s in ('train', 'val')}
    for li in range(args.layouts):
        seed = args.seed0 + li
        split = 'val' if li % args.val_every == args.val_every - 1 else 'train'
        rng = np.random.default_rng(seed + 7)
        scene, base = build_random(seed)
        sb = StageBuilder(scene)
        st = sb.build(app)
        # ---------------- domain randomisation of the layout
        preset = list(LIGHTS)[li % 3]
        scale, col = LIGHTS[preset]
        lights = []
        for p in st.Traverse():
            if p.HasAPI(UsdLux.LightAPI) or 'Light' in p.GetTypeName():
                L = UsdLux.LightAPI(p)
                ia, ca = L.GetIntensityAttr(), L.GetColorAttr()
                if ia and ia.Get() is not None:
                    lights.append((ia, float(ia.Get())))
                    ca.Set(Gf.Vec3f(*col))
        st.DefinePrim('/World/Looks', 'Scope')
        floor = FLOORS[rng.integers(len(FLOORS))]
        if floor:
            fm = mdl_material(st, '/World/Looks/Floor', floor)
            for p in st.GetDefaultPrim().GetChildren():
                if p.GetName().startswith('SM_floor'):
                    bind(p, fm)
        woods = [mdl_material(st, f'/World/Looks/Wood{i}', w) for i, w in enumerate(WOODS)]
        tints = [tint_material(st, f'/World/Looks/Box{i}', c) for i, c in enumerate(BOX_TINTS)]
        rail_m = tint_material(st, '/World/Looks/Rail', RAIL_COLS[rng.integers(len(RAIL_COLS))], 0.4, 0.3)
        for inst in sb.instances:
            prim = st.GetPrimAtPath(inst['root'])
            if inst['actor'] is not None or not prim:
                continue
            u = rng.uniform()
            if inst['cls'] == 'pallet' and u < 0.4:
                bind(prim, woods[rng.integers(len(woods))])
            elif inst['cls'] == 'box' and u < 0.35 and inst['root'].startswith('/World'):
                bind(prim, tints[rng.integers(len(tints))])
            elif inst['cls'] == 'guard_rail' and inst['root'].startswith('/World'):
                bind(prim, rail_m)
        # targets: instance centres (static: bbox; actors: updated per frame)
        bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])
        static_t = []
        for inst in sb.instances:
            if inst['actor'] is None:
                r = bc.ComputeWorldBound(st.GetPrimAtPath(inst['root'])).ComputeAlignedRange()
                if not r.IsEmpty():
                    static_t.append((inst['cls'], np.array(r.GetMidpoint())))
        bx = (-27.0, -24.0, 5.8, 31.0)
        occ = sb.occupancy(*bx, res=0.1, zband=(0.05, 2.8), include_actors=True)
        free = cv2.erode((occ == 0).astype(np.uint8), np.ones((7, 7), np.uint8))   # >= 0.3 m from obstacles
        from scenes.segtrain import LANES
        lanes = LANES[base]
        cam = UsdGeom.Camera.Define(st, '/World/SegCam')
        px = 0.01
        cam.GetHorizontalApertureAttr().Set(W * px)
        cam.GetVerticalApertureAttr().Set(H * px)
        cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.05, 150.0))
        xf = UsdGeom.Xformable(cam.GetPrim())
        xf.ClearXformOpOrder()
        op = xf.AddTransformOp(UsdGeom.XformOp.PrecisionDouble)
        rp = rep.create.render_product(cam.GetPath(), (W, H))
        a_rgb = rep.AnnotatorRegistry.get_annotator('rgb')
        a_seg = rep.AnnotatorRegistry.get_annotator('instance_id_segmentation_fast')
        a_rgb.attach(rp)
        a_seg.attach(rp)
        for _ in range(4):
            app.update()
        cls_of = {i['id']: i['cls'] for i in sb.instances}
        n_ok, tries = 0, 0
        while n_ok < args.per_layout and tries < args.per_layout * 30:
            tries += 1
            t = float(rng.uniform(0, 45))
            sb.update(t)
            for ia, v in lights:
                ia.Set(v * scale * float(rng.uniform(0.75, 1.25)))
            # target
            if rng.uniform() < 0.65:
                acts = [a for a in sb.forklifts + sb.people]
                a = acts[rng.integers(len(acts))]
                spec = a['spec']
                if getattr(spec, 'path', None) is not None:
                    q = spec.path.at(t)['xy']
                else:
                    q = np.array(spec.pose[:2])
                tgt = np.array([q[0], q[1], rng.uniform(0.5, 1.4)])
            else:
                tgt = static_t[rng.integers(len(static_t))][1].copy()
                tgt[2] = min(max(tgt[2], 0.3), 3.0)
            # camera on a free lane (racks have open shelf decks -> occupancy alone is not enough), 1.5-15 m away
            lx0, ly0, lx1, ly1, lw = lanes[rng.integers(len(lanes))]
            d_ = np.array([lx1 - lx0, ly1 - ly0])
            n_ = np.array([-d_[1], d_[0]]) / max(np.linalg.norm(d_), 1e-9)
            pxy = np.array([lx0, ly0]) + rng.uniform() * d_ + rng.uniform(-lw - 0.6, lw + 0.6) * n_
            pos = np.array([pxy[0], pxy[1], rng.uniform(0.3, 2.6)])
            dist = np.linalg.norm(tgt[:2] - pos[:2])
            u, v = int((pos[0] - bx[0]) / 0.1), int((bx[3] - pos[1]) / 0.1)
            if not (1.5 <= dist <= 15.0) or not (0 <= u < free.shape[1] and 0 <= v < free.shape[0]) or not free[v, u]:
                continue
            f = tgt - pos
            f += rng.normal(0, 0.12, 3) * np.linalg.norm(f)
            f /= np.linalg.norm(f)
            pitch = np.arcsin(np.clip(f[2], -1, 1))
            if pitch < np.deg2rad(-30) or pitch > np.deg2rad(10):
                f[2] = np.sin(np.clip(pitch, np.deg2rad(-30), np.deg2rad(10)))
                f /= np.linalg.norm(f)
            r = np.cross(f, [0, 0, 1.0])
            r /= np.linalg.norm(r)
            up = np.cross(r, f)
            roll = rng.normal(0, np.deg2rad(3))
            r, up = np.cos(roll) * r + np.sin(roll) * up, -np.sin(roll) * r + np.cos(roll) * up
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = r, up, -f, pos
            op.Set(Gf.Matrix4d(M.T.tolist()))
            fx = 470.0 if rng.uniform() < 0.7 else 264.0
            cam.GetFocalLengthAttr().Set(fx * px)
            rep.orchestrator.step(rt_subframes=args.subframes, delta_time=0.0)
            d = a_seg.get_data()
            lut = sb.lut(d['info']['idToLabels'])
            raw = d['data']
            seg = lut[np.where(raw < len(lut), raw, 0)]
            ids, cnt = np.unique(seg, return_counts=True)
            keep = [(int(i), int(c)) for i, c in zip(ids, cnt) if i > 0 and c >= args.min_area]
            if not any(cls_of[i] in ('person', 'forklift', 'trolley') for i, _ in keep) and rng.uniform() < 0.6:
                continue   # favour frames with dynamic / potential objects
            rgb = a_rgb.get_data()[..., :3]
            name = f'L{seed}_{n_ok:04d}'
            img_id = len(coco['train']['images']) + len(coco['val']['images']) + 1
            cv2.imwrite(os.path.join(args.out, 'images', split, name + '.jpg'), rgb[..., ::-1],
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            cv2.imwrite(os.path.join(args.out, 'masks', split, name + '.png'), seg.astype(np.uint16))
            coco[split]['images'].append(dict(id=img_id, file_name=f'{split}/{name}.jpg', width=W, height=H,
                                              layout_seed=seed, base_layout=base, lighting=preset,
                                              floor=floor or 'original', fx=fx, time=t))
            for i, c in keep:
                m = seg == i
                polys = coco_polys(m)
                if not polys:
                    continue
                ys, xs = np.nonzero(m)
                coco[split]['annotations'].append(dict(
                    id=ann_id, image_id=img_id, category_id=COCO_ID[cls_of[i]], segmentation=polys, area=int(c),
                    bbox=[int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
                    iscrowd=0, instance_id=i))
                stats[split][cls_of[i]] += 1
                ann_id += 1
            n_ok += 1
        a_rgb.detach()
        a_seg.detach()
        rp.destroy()
        print(f'[segtrain] layout {seed} ({base}, {preset}, floor {floor}) -> {split}: {n_ok} images '
              f'({tries} tries), {time.time() - t_all:.0f} s total', flush=True)
        for s in ('train', 'val'):
            with open(os.path.join(args.out, 'annotations', f'instances_{s}.json'), 'w') as fh:
                json.dump(coco[s], fh)
    meta = dict(images={s: len(coco[s]['images']) for s in coco}, annotations=stats, layouts=args.layouts,
                val_every=args.val_every, seed0=args.seed0, resolution=[W, H], classes=NAMES,
                render_s=time.time() - t_all, isaac='6.0.1-rc.7')
    with open(os.path.join(args.out, 'meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    print('[segtrain] done', json.dumps(meta))
    app.close()


if __name__ == '__main__':
    main()
