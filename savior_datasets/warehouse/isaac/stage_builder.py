# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a wh.scenario.Scene on the Isaac stage and pose its actors at any time t (import after SimulationApp)."""
import os
import re

import numpy as np
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdSkel, Vt

import common
from wh.classes import MOVING_SPEED

FORKLIFT_USD = 'Isaac/Props/Forklift/forklift.usd'
PALLET_USD = 'Isaac/Props/Pallet/pallet.usd'
BOX_USD = 'Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxA_01.usd'
WINDOW_USD = 'Isaac/Environments/Office/Props/SM_Window_3m_A.usd'
CART_USD = 'Isaac/Props/Dolly/dolly.usd'                                   # t3+ carts (class trolley)
CART_BOX_USD = 'Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxB_01.usd'   # 0.5 m cube
CART_DECK = 0.441
FORK_TOP = 0.10          # fork blade top above the floor at zero lift [m]
SEAT = (0.0, 0.62, 1.02)   # forklift-local seat point (driver hips rest here), forklift faces -y
HIP_SIT = (0.0, 0.408, 0.626)   # hip joint offset of the retargeted Sit pose (character faces -y)
YAW_OFFSET = 90.0        # forklift.usd and the characters face local -y: usd yaw = heading + 90 deg

# instance id ranges (uint16): env 1..2999, static props 3000..4999, actors 5000..
ID_PROP0, ID_ACTOR0 = 3000, 5000


def _xf(prim, pos=(0, 0, 0), yaw_deg=0.0, scale=None):
    x = UsdGeom.Xformable(prim)
    x.ClearXformOpOrder()
    t = x.AddTranslateOp()
    t.Set(Gf.Vec3d(*map(float, pos)))
    r = x.AddRotateZOp()
    r.Set(float(yaw_deg))
    if scale is not None and scale != 1.0:
        x.AddScaleOp().Set(Gf.Vec3f(float(scale), float(scale), float(scale)))
    return t, r


def _ref(stage, path, usd, pos=(0, 0, 0), yaw=0.0, scale=None):
    p = stage.DefinePrim(path, 'Xform')
    p.GetReferences().AddReference(common.asset(usd))
    ops = _xf(p, pos, yaw, scale)
    return p, ops


class Anim:
    """Baked retargeted clips of one character: per-frame local joint translations / rotations / scales."""

    def __init__(self, character):
        st = Usd.Stage.Open(os.path.join(common.ANIM_CACHE, f'{character}.usda'))
        self.clips = {}
        for k in ('walk', 'idle', 'sit'):
            a = UsdSkel.Animation(st.GetPrimAtPath(f'/Out/{k}'))
            ts = a.GetTranslationsAttr().GetTimeSamples()
            T = np.array([np.array(a.GetTranslationsAttr().Get(t), np.float32) for t in ts])
            R = np.array([np.array([[q.GetReal(), *q.GetImaginary()] for q in a.GetRotationsAttr().Get(t)], np.float32)
                          for t in ts])
            S = np.array([np.array(a.GetScalesAttr().Get(t), np.float32) for t in ts]) \
                if a.GetScalesAttr().GetTimeSamples() else np.ones_like(T)
            self.clips[k] = (T, R, S)
            self.joints = list(a.GetJointsAttr().Get())

    def sample(self, clip, frame, loop=True):
        T, R, S = self.clips[clip]
        n = len(T) - 1 if loop else len(T)   # loops: last frame == first frame
        f = frame % n if loop else min(max(frame, 0), n - 1)
        i0 = int(np.floor(f))
        i1 = (i0 + 1) % n if loop else min(i0 + 1, n - 1)
        a = f - i0
        return T[i0] * (1 - a) + T[i1] * a, _nlerp(R[i0], R[i1], a), S[i0] * (1 - a) + S[i1] * a


def _nlerp(q0, q1, a):
    d = np.sum(q0 * q1, axis=-1, keepdims=True)
    q1 = np.where(d < 0, -q1, q1)
    q = q0 * (1 - a) + q1 * a
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def _set_pose(drv, T, R, S):
    drv.GetTranslationsAttr().Set(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(T, np.float32)))
    # NOTE: Gf.Quatf memory layout is (x, y, z, w); our arrays are (w, x, y, z)
    drv.GetRotationsAttr().Set(Vt.QuatfArray.FromNumpy(np.ascontiguousarray(R[:, [1, 2, 3, 0]], np.float32)))
    drv.GetScalesAttr().Set(Vt.Vec3hArray.FromNumpy(np.ascontiguousarray(S, np.float16)))


class StageBuilder:
    def __init__(self, scene, actor_names_all=None):
        self.scene = scene
        self.stage = None
        self.instances = []          # dicts: id, name, cls, root, actor
        self._roots = {}             # prim path -> instance id
        self._path_cache = {}
        self.people, self.forklifts = [], []
        names = actor_names_all or sorted([p.name for p in scene.people] + [f.name for f in scene.forklifts])
        order = sorted(names)
        # actors of this level that are not in the reference (level-3) list get ids after all reference actors,
        # so the ids of the reference actors do not change (only the held-out aisles_t2 L2 has such an actor)
        order += sorted(({p.name for p in scene.people} | {f.name for f in scene.forklifts}) - set(order))
        self._actor_order = {n: i for i, n in enumerate(order)}
        self._anims = {}

    # ------------------------------------------------------------------------------------------- build
    def build(self, app):
        sc = self.scene
        omni.usd.get_context().open_stage(common.asset(sc.env))
        for _ in range(5):
            app.update()
        st = self.stage = omni.usd.get_context().get_stage()
        root = st.GetDefaultPrim()
        hide = [re.compile(h) for h in sc.env_hide]
        envc = [(re.compile(r), c) for r, c in sc.env_classes]
        kids = sorted(root.GetChildren(), key=lambda p: str(p.GetPath()))
        nid = 1
        if getattr(sc, 'env_label_mode', 'children') == 'recursive':   # t3+: nested env layouts
            nid = self._label_recursive(kids, hide, envc, nid)
            kids = []
        for p in kids:
            n = p.GetName()
            if any(h.search(n) for h in hide):
                p.SetActive(False)
                continue
            for rx, c in envc:
                if rx.search(n):
                    self._add_instance(nid, n, c, str(p.GetPath()), None)
                    nid += 1
                    break
        st.DefinePrim('/World', 'Xform')
        st.DefinePrim('/World/Static', 'Xform')
        st.DefinePrim('/World/Actors', 'Xform')
        pid = ID_PROP0
        for pr in sc.props:
            path = f'/World/Static/{_clean(pr.name)}'
            _ref(st, path, pr.usd, pr.pos, pr.yaw_deg, pr.scale)
            if pr.cls:
                self._add_instance(pid, pr.name, pr.cls, path, None)
            pid += 1
        mat = self._rail_material()
        for r in sc.rails:
            path = f'/World/Static/{_clean(r.name)}'
            self._make_rail(path, r, mat)
            self._add_instance(pid, r.name, 'guard_rail', path, None)
            pid += 1
        for w in sc.windows:
            path = f'/World/Static/{_clean(w.name)}'
            _ref(st, path, WINDOW_USD, w.pos, w.yaw_deg)
            self._add_instance(pid, w.name, 'window', path, None)
            pid += 1
        for fk in sc.forklifts:
            self._add_forklift(fk)
        for pe in sc.people:
            self._add_person(pe)
        for _ in range(3):
            app.update()
        # driver skeleton animation sources (skeleton prims exist only after the references composed)
        for f in self.forklifts:
            if f['driver_prim'] is not None:
                drv = self._bind_driver(f['driver_prim'], f['driver_char'])
                _set_pose(drv, *self._anim(f['driver_char']).sample('sit', 10 ** 6, loop=False))
        for p in self.people:
            p['drv'] = self._bind_driver(p['prim'], p['spec'].character)
        return st

    def _label_recursive(self, prims, hide, envc, nid):
        """Depth-first over the env tree (children sorted by path): deactivate prims whose name matches env_hide,
        label a prim matching env_classes as one instance (its subtree included), else descend."""
        for p in prims:
            n = p.GetName()
            if any(h.search(n) for h in hide):
                p.SetActive(False)
                continue
            c = next((c for rx, c in envc if rx.search(n)), None)
            if c is not None:
                self._add_instance(nid, n, c, str(p.GetPath()), None)
                nid += 1
                continue
            if not p.IsInstance():
                nid = self._label_recursive(sorted(p.GetChildren(), key=lambda q: str(q.GetPath())), hide, envc, nid)
        return nid

    def _anim(self, ch):
        if ch not in self._anims:
            self._anims[ch] = Anim(ch)
        return self._anims[ch]

    def _bind_driver(self, char_prim, ch):
        skel = [p for p in Usd.PrimRange(char_prim) if p.GetTypeName() == 'Skeleton'][0]
        drv = UsdSkel.Animation.Define(self.stage, skel.GetPath().AppendChild('SaviorPose'))
        drv.GetJointsAttr().Set(Vt.TokenArray(self._anim(ch).joints))
        UsdSkel.BindingAPI.Apply(skel).CreateAnimationSourceRel().SetTargets([drv.GetPath()])
        return drv

    def _add_instance(self, iid, name, cls, root, actor):
        self.instances.append(dict(id=int(iid), name=name, cls=cls, root=root, actor=actor))
        self._roots[root] = int(iid)

    def actor_base_id(self, name):
        return ID_ACTOR0 + 16 * self._actor_order[name]

    def _add_forklift(self, fk):
        st = self.stage
        base = self.actor_base_id(fk.name)
        root = f'/World/Actors/{_clean(fk.name)}'
        rp = st.DefinePrim(root, 'Xform')
        x, y, h = fk.pose
        if fk.path is not None:
            a = fk.path.at(0.0)
            x, y, h = a['xy'][0], a['xy'][1], np.rad2deg(a['heading'])
        ops = _xf(rp, (x, y, 0.0), h + YAW_OFFSET)
        if getattr(fk, 'kind', 'forklift') == 'cart':     # t3+: pushed dolly (trolley) with boxes on top
            self._add_cart(fk, root, base)
            self.forklifts.append(dict(spec=fk, ops=ops, driver_prim=None, driver_char=None, root=root))
            return
        body, _ = _ref(st, root + '/body', FORKLIFT_USD)
        self._add_instance(base, fk.name, 'forklift', root + '/body', fk.name)
        fork = st.GetPrimAtPath(root + '/body/S_ForkliftFork')
        fx = UsdGeom.Xformable(fork)
        tops = [o for o in fx.GetOrderedXformOps() if o.GetOpType() == UsdGeom.XformOp.TypeTranslate]
        if tops:
            v = tops[0].Get()
            tops[0].Set(type(v)(v[0], v[1], v[2] + fk.fork_lift))
        else:
            fx.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble, 'savior').Set(Gf.Vec3d(0, 0, fk.fork_lift))
        z0 = FORK_TOP + fk.fork_lift
        lp = root + '/load'
        st.DefinePrim(lp, 'Xform')
        if fk.load in ('pallet', 'boxes'):
            _ref(st, lp + '/pallet', PALLET_USD, (0.0, -1.12, z0), 90.0)
            self._add_instance(base + 1, fk.name + '.pallet', 'pallet', lp + '/pallet', fk.name)
        if fk.load == 'boxes':
            k = 0
            for iz in range(2):
                for iy in range(2):
                    _ref(st, lp + f'/box{k}', BOX_USD, (0.0, -1.12 + (iy - 0.5) * 0.52, z0 + 0.145 + iz * 0.5), 0.0)
                    self._add_instance(base + 2 + k, fk.name + f'.box{k}', 'box', lp + f'/box{k}', fk.name)
                    k += 1
        drv = None
        if fk.driver:
            pos = (SEAT[0] - HIP_SIT[0], SEAT[1] - HIP_SIT[1], SEAT[2] - HIP_SIT[2])
            drv, _ = _ref(st, root + '/driver', common.char_usd(fk.driver).replace(common.ASSET_ROOT + '/', ''), pos, 0.0)
            self._add_instance(base + 10, fk.name + '.driver', 'person', root + '/driver', fk.name)
        self.forklifts.append(dict(spec=fk, ops=ops, driver_prim=drv, driver_char=fk.driver, root=root))

    def _add_cart(self, fk, root, base):
        """Dolly (0.85 x 1.26 m, deck 0.44 m; long axis = local y = direction of travel) + boxes on the deck."""
        st = self.stage
        _ref(st, root + '/body', CART_USD)
        self._add_instance(base, fk.name, 'trolley', root + '/body', fk.name)
        if fk.load == 'boxes':
            st.DefinePrim(root + '/load', 'Xform')
            n = 3 if fk.fork_lift > 0.5 else 2          # fork_lift > 0.5 = one more box on top (taller load)
            for k in range(n):
                pos = (0.0, (-0.28, 0.28, 0.0)[k], CART_DECK + (0.0, 0.0, 0.5)[k])
                _ref(st, root + f'/load/box{k}', CART_BOX_USD, pos, 3.0 * (k - 1))
                self._add_instance(base + 2 + k, fk.name + f'.box{k}', 'box', root + f'/load/box{k}', fk.name)

    def _add_person(self, pe):
        st = self.stage
        base = self.actor_base_id(pe.name)
        root = f'/World/Actors/{_clean(pe.name)}'
        rp = st.DefinePrim(root, 'Xform')
        a = pe.path.at(0.0)
        ops = _xf(rp, (a['xy'][0], a['xy'][1], 0.0), np.rad2deg(a['heading']) + YAW_OFFSET)
        cp, _ = _ref(st, root + '/char', common.char_usd(pe.character).replace(common.ASSET_ROOT + '/', ''))
        self._add_instance(base, pe.name, 'person', root, pe.name)
        self.people.append(dict(spec=pe, ops=ops, prim=cp, drv=None, idle_phase=float(base % 97), root=root))

    def _rail_material(self):
        st = self.stage
        mp = '/World/Static/Looks/RailYellow'
        mat = UsdShade.Material.Define(st, mp)
        sh = UsdShade.Shader.Define(st, mp + '/Shader')
        sh.CreateIdAttr('UsdPreviewSurface')
        sh.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.95, 0.72, 0.03))
        sh.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.45)
        sh.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.2)
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), 'surface')
        return mat

    def _make_rail(self, path, r, mat):
        st = self.stage
        p0, p1 = np.asarray(r.p0, float), np.asarray(r.p1, float)
        L = float(np.linalg.norm(p1 - p0))
        yaw = float(np.rad2deg(np.arctan2(*(p1 - p0)[::-1])))
        g = st.DefinePrim(path, 'Xform')
        _xf(g, (p0[0], p0[1], 0.0), yaw)
        n = max(int(np.ceil(L / 1.5)), 1)
        for i in range(n + 1):
            c = UsdGeom.Cylinder.Define(st, f'{path}/post{i}')
            c.CreateRadiusAttr(0.045)
            c.CreateHeightAttr(r.height)
            c.CreateAxisAttr('Z')
            _xf(c.GetPrim(), (L * i / n, 0.0, r.height / 2))
        for j, z in enumerate((0.35 * r.height, 0.9 * r.height)):
            b = UsdGeom.Cube.Define(st, f'{path}/rail{j}')
            b.CreateSizeAttr(1.0)
            xf = UsdGeom.Xformable(b.GetPrim())
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(L / 2, 0.0, z))
            xf.AddScaleOp().Set(Gf.Vec3f(L + 0.1, 0.07, 0.12))
        UsdShade.MaterialBindingAPI.Apply(g).Bind(mat)

    # ------------------------------------------------------------------------------------------- per frame
    def update(self, t):
        """Pose all actors at time t; returns {actor_name: speed [m/s]}."""
        speeds = {}
        for a in self.forklifts + self.people:
            act = a['spec'].active
            vis = act is None or (act[0] <= t <= act[1])
            if a.get('vis', True) != vis:
                im = UsdGeom.Imageable(self.stage.GetPrimAtPath(a['root']))
                im.MakeVisible() if vis else im.MakeInvisible()
                a['vis'] = vis
        for f in self.forklifts:
            fk = f['spec']
            if not f.get('vis', True):
                speeds[fk.name] = 0.0
                continue
            if fk.path is None:
                speeds[fk.name] = 0.0
                continue
            a = fk.path.at(t)
            f['ops'][0].Set(Gf.Vec3d(float(a['xy'][0]), float(a['xy'][1]), 0.0))
            f['ops'][1].Set(float(np.rad2deg(a['heading']) + YAW_OFFSET))
            speeds[fk.name] = float(a['speed'])
        for p in self.people:
            pe = p['spec']
            if not p.get('vis', True):
                speeds[pe.name] = 0.0
                continue
            a = pe.path.at(t)
            p['ops'][0].Set(Gf.Vec3d(float(a['xy'][0]), float(a['xy'][1]), 0.0))
            p['ops'][1].Set(float(np.rad2deg(a['heading']) + YAW_OFFSET))
            sp = float(a['speed'])
            speeds[pe.name] = sp
            an = self._anim(pe.character)
            nw = len(an.clips['walk'][0]) - 1
            fw = float(a['dist']) / (pe.walk_speed_clip * nw / 30.0) * nw   # foot-locked walk phase
            Tw, Rw, Sw = an.sample('walk', fw)
            w = float(np.clip(sp / 0.45, 0.0, 1.0))
            w = w * w * (3 - 2 * w)
            if w < 1.0:
                Ti, Ri, Si = an.sample('idle', t * 30.0 + p['idle_phase'])
                Tw, Rw, Sw = Ti * (1 - w) + Tw * w, _nlerp(Ri, Rw, w), Si * (1 - w) + Sw * w
            _set_pose(p['drv'], Tw, Rw, Sw)
        return speeds

    def moving_ids(self, speeds):
        return {i['id'] for i in self.instances if i['actor'] is not None and speeds.get(i['actor'], 0.0) > MOVING_SPEED}

    # ------------------------------------------------------------------------------------------- segmentation
    def lut(self, id_to_labels):
        """Annotator id -> our uint16 instance id (0 = background)."""
        mx = max(int(k) for k in id_to_labels) if id_to_labels else 0
        lut = np.zeros(mx + 1, np.uint16)
        for k, path in id_to_labels.items():
            lut[int(k)] = self._resolve(str(path))
        return lut

    def _resolve(self, path):
        if path in self._path_cache:
            return self._path_cache[path]
        q = path
        iid = 0
        while q and q != '/':
            if q in self._roots:
                iid = self._roots[q]
                break
            q = q.rsplit('/', 1)[0]
        self._path_cache[path] = iid
        return iid

    # ------------------------------------------------------------------------------------------- occupancy
    def occupancy(self, x0, y0, x1, y1, res=0.05, zband=(0.12, 2.0), include_actors=False):
        import cv2
        st = self.stage
        W, H = int(np.ceil((x1 - x0) / res)), int(np.ceil((y1 - y0) / res))
        occ = np.zeros((H, W), np.uint8)
        cache = UsdGeom.XformCache()
        polys = []
        for p in Usd.PrimRange(st.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
            if not p.IsA(UsdGeom.Mesh) and not p.IsA(UsdGeom.Gprim):
                continue
            sp = str(p.GetPath())
            if (not include_actors and sp.startswith('/World/Actors')) or sp.startswith('/World/Rig'):
                continue
            if UsdGeom.Imageable(p).ComputeVisibility() == UsdGeom.Tokens.invisible:
                continue
            M = np.array(cache.GetLocalToWorldTransform(p)).T
            if p.IsA(UsdGeom.Mesh):
                m = UsdGeom.Mesh(p)
                pts = m.GetPointsAttr().Get()
                cnt = m.GetFaceVertexCountsAttr().Get()
                idx = m.GetFaceVertexIndicesAttr().Get()
                if pts is None or cnt is None or idx is None or len(pts) == 0:
                    continue
                P = np.asarray(pts, float) @ M[:3, :3].T + M[:3, 3]
                cnt, idx = np.asarray(cnt), np.asarray(idx)
                starts = np.r_[0, np.cumsum(cnt)[:-1]]
                tris = []
                for k in range(1, int(cnt.max()) - 1 if len(cnt) else 0):   # fan triangulation
                    s = starts[cnt > k + 1]
                    tris.append(np.c_[idx[s], idx[s + k], idx[s + k + 1]])
                if not tris:
                    continue
                T = P[np.concatenate(tris)]
            else:   # procedural gprims (rails): bounding box
                r = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render']).ComputeWorldBound(p).ComputeAlignedRange()
                lo, hi = np.array(r.GetMin()), np.array(r.GetMax())
                T = np.array([[[lo[0], lo[1], lo[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]]],
                              [[lo[0], lo[1], lo[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], lo[2]]]])
            zl, zh = T[..., 2].min(1), T[..., 2].max(1)
            keep = (zh >= zband[0]) & (zl <= zband[1])
            if not keep.any():
                continue
            uv = np.stack([(T[keep, :, 0] - x0) / res, (y1 - T[keep, :, 1]) / res], -1)
            polys.append(np.round(uv).astype(np.int32))
        for P in polys:
            cv2.fillPoly(occ, list(P), 255)
            cv2.polylines(occ, list(P), True, 255, 1)
        return occ


def _clean(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)
