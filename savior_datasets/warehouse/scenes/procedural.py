# SPDX-License-Identifier: GPL-3.0-or-later
"""SAVIOR-Warehouse t3 (CONFIRMATORY split): seeded procedural scenes on several Isaac Sim warehouse environments.

One seed gives one independent trajectory = (static layout, camera trajectory, IMU noise, L0-L3 actor choreography).
Everything is a pure function of (site, seed, GEN_VERSION); numpy only, no Isaac import. Use it through the renderer:

    $ISAAC isaac/render_sequence.py --scene procedural:fw01 --level 3 --plan      # a t3 trajectory (TRAJECTORIES)
    $ISAAC isaac/render_sequence.py --scene procedural:dev-ms-9002 --level 3 --preview 5 --scale 0.25   # dev seed

Sites (environment + free floor rectangle + keep-outs; see SITES):
  fw  Simple_Warehouse/full_warehouse.usd, the south hall (30 x 29 m; t1/t2 environment, new procedural layouts)
  sw  Simple_Warehouse/warehouse.usd (20 x 30 m shell, one wall rack row; NOT used in t1/t2)
  ms  Simple_Warehouse/warehouse_multiple_shelves.usd (3 rack rows with boxes / bins; NOT used in t1/t2)
  wx  warehouse_20x20_envi/warehouse_20x20_envi.usd (different asset family: white / blue hall, blue wall racks,
      its central clutter deactivated; NOT used in t1/t2)

Generator (per seed, separate RNG streams for layout / camera / actors):
  * layout: a lane grid (seeded lane count, positions and widths); the blocks between lanes are filled with pallet
    stacks (1-3 box layers, two box sizes), KLT pallets, pallet piles, dollies (trolley), barrels and cones; parked
    driverless forklifts in block bays (boxes / pallet / nothing on forks raised 0-1.1 m); guard rails on block sides.
    Only classes of the segmenter (Table I: rack, guard_rail, window, forklift, box, pallet, trolley, person).
  * camera: a random tour on the lane graph (no U-turns, unvisited lanes preferred), 80-92 m, legs at 0.7-1.3 m/s,
    1.0-1.8 m high with one 2.2-2.4 m leg, +-12-14 deg look-around, the t1/t2 quadrotor model (wh.trajectory,
    3 s hover + 0.3 m take-off climb, 2 s end hover, yaw rate <= 100 deg/s).
  * actors, nested by construction (an actor of tier k is present at every level >= k; generated L3 -> L2 -> L1 and
    each accepted only if it is clear of the camera, the static layout and all accepted actors):
      L1  people: standing at stacks (in view during the hover), one crossing DURING the hover, one starting at
          take-off, head-on and walking-ahead people, crossings at intersections, one across the final hover;
      L2  + forklifts with seated drivers and loads (crossing at take-off / at intersections, a leader 8-10 m ahead
          with late onset that turns off, a head-on one that turns off, a slow parallel one) and people pushing
          loaded carts (dolly, class trolley);
      L3  + co-moving forklifts 3-5.5 m ahead (one parked ahead during the hover that starts after take-off, one that
          turns in later and stops in front of the final hover), one alongside 1.4-1.8 m to the side, raised loads,
          two more loaded carts.
"""
import math

import numpy as np

from wh.classes import CHARACTERS
from wh.scenario import CamRef, Forklift, PathBuilder, Person, Prop, Rail, Scene, is_active
from wh.trajectory import BodyTrajectory, PlanarPath
from . import full_warehouse as fw

GEN_VERSION = 't3-gen-1'
TRAJ = 't3'

SWC = [   # Simple_Warehouse family env prims (recursive labelling: matched prims are labelled as a whole)
    (r'^SM_RackFrame|^SM_RackShelf|^SM_RackPile', 'rack'),
    (r'^SM_Rackshield', 'guard_rail'),
    (r'^SM_PaletteA', 'pallet'),
    (r'^Box_|^SM_CardBox|^Crate|^SM_CratePlastic|^SmallKLT', 'box'),
    (r'^forklift$|^Forklift', 'forklift'),
    (r'^SM_PushcartA', 'trolley'),
]
WXC = [   # warehouse_20x20_envi prims
    (r'^RackLong|^RackGroup|^Rack_', 'rack'),
    (r'^Trolly|^SM_Trolley', 'trolley'),
    (r'^SM_ExportPallet|^Pallet_|^SM_WoodDrumPallet', 'pallet'),
    (r'^Cardbox|^SM_Crate_A|^Crate_|^WoodenCrate|^sm_whitecorrugatedbox|^SM_WhiteCorrugatedBox|^sm_flatbox|'
     r'^SM_FlatBox|^sm_printersbox|^SM_PrintersBox|^sm_multidepthbox', 'box'),
]
WX_HIDE = [r'^Trolly$', r'^RackGroup$', r'^row_of_boxes$', r'^PalletGroup', r'^WarehousePile', r'^sm_packingtablecomposition',
           r'^sm_palletcomposition_a69', r'^SM_CratePacking_Table_A1_physics$', r'^SM_BoxPicking_Table']

SITES = {
    'fw': dict(env=fw.ENV, mode='children', classes=fw.ENV_CLASSES, hide=[], rect=(-25.9, -22.6, 4.8, 7.6), wall=1.3,
               plan_box=(-27.5, -24.5, 6.0, 10.0), nx=(1, 2), ny=(1, 2), lane_w=(4.6, 5.2), keepout=[],
               fixed_x=None, fixed_y=None, rack_rails=True, windows=True, n_parked=(2, 3)),
    'sw': dict(env='Isaac/Environments/Simple_Warehouse/warehouse.usd', mode='recursive', classes=SWC, hide=[],
               rect=(-8.2, -11.6, 9.3, 17.0), wall=1.3, plan_box=(-12.0, -13.0, 11.0, 19.0), nx=(0, 0), ny=(1, 2),
               lane_w=(4.4, 4.8), keepout=[(-8.8, 12.3, -4.8, 15.3)], fixed_x=None, fixed_y=None, rack_rails=False,
               windows=False, n_parked=(1, 2)),
    'ms': dict(env='Isaac/Environments/Simple_Warehouse/warehouse_multiple_shelves.usd', mode='recursive',
               classes=SWC, hide=[r'^PalletBin'], rect=(-8.0, -10.9, 8.3, 16.8), plan_box=(-12.0, -13.0, 11.0, 19.0),
               nx=None, ny=None, lane_w=(4.5, 4.7), min_block=0.85, keepout=[(-11.0, -4.6, -8.3, 12.9), (-1.3, -4.6, 1.3, 12.9),
                                                            (8.3, -4.6, 11.0, 12.9)],
               fixed_x=[(-5.0, -4.5), (4.5, 5.0)], fixed_y=[[(-8.6, -7.4), (14.6, 15.0)]],
               rack_rails=False, windows=False, n_parked=(1, 2)),
    'wx': dict(env='Isaac/Environments/warehouse_20x20_envi/warehouse_20x20_envi.usd', mode='recursive', classes=WXC,
               hide=WX_HIDE, rect=(-9.6, -18.3, 7.9, -2.0), wall=0.0, plan_box=(-11.0, -21.0, 11.0, 1.0), nx=(1, 1), ny=(0, 0),
               lane_w=(4.2, 4.5), min_block=1.7, keepout=[], fixed_x=None, fixed_y=None, rack_rails=False,
               windows=False, n_parked=(1, 1)),
}

# frozen t3 trajectories (results/t3_confirmatory/DESIGN.yaml): id -> (site, seed). Seed formula 31000 + 1000 i_site +
# 101 k (k = 1..6, spares 7..12); seeds that failed the pre-render structural check were replaced by the next spare
# (fw 31101, sw 32606, ms 33202 / 33303 / 33404; results/t3_confirmatory/scripts/make_design.py)
TRAJECTORIES = {
    'fw01': ('fw', 31202),
    'fw02': ('fw', 31303),
    'fw03': ('fw', 31404),
    'fw04': ('fw', 31505),
    'fw05': ('fw', 31606),
    'fw06': ('fw', 31707),
    'sw01': ('sw', 32101),
    'sw02': ('sw', 32202),
    'sw03': ('sw', 32303),
    'sw04': ('sw', 32404),
    'sw05': ('sw', 32505),
    'sw06': ('sw', 32707),
    'ms01': ('ms', 33101),
    'ms02': ('ms', 33505),
    'ms03': ('ms', 33606),
    'ms04': ('ms', 33707),
    'ms05': ('ms', 33808),
    'ms06': ('ms', 33909),
    'wx01': ('wx', 34101),
    'wx02': ('wx', 34202),
    'wx03': ('wx', 34303),
    'wx04': ('wx', 34404),
    'wx05': ('wx', 34505),
    'wx06': ('wx', 34606),
}

PALLET_L, PALLET_W = 1.22, 0.80
DUR_RANGE = (92.0, 112.0)        # accepted sequence duration [s] (t1/t2: 96-113 s)
CAM_R, CAM_CLR, PAIR_CLR = 0.35, 0.25, 0.25
HFOV_HALF = math.radians(35.5 + 15.0)   # cam0 half field of view + margin (out-of-view test for visibility windows)


# ============================================================================================== layout
def _sample_lanes(rng, lo, hi, n, w, min_block, wall=0.0):
    """Lane centres in [lo, hi] (corridor width w): one ring lane along each wall (perimeter aisle; `wall` m of
    storage strip between it and the wall) plus n inner lanes; blocks between corridors are >= min_block wide."""
    a, b = lo + wall + w / 2, hi - wall - w / 2
    if n == 0:
        return [round(a, 2), round(b, 2)]
    if b - a < (n + 1) * (w + min_block) - min_block + w * 0.0 or a + w + min_block > b - w - min_block:
        return _sample_lanes(rng, lo, hi, n - 1, w, min_block, wall)     # does not fit: one inner lane fewer
    for _ in range(4000):
        c = np.sort(rng.uniform(a + w + min_block, b - w - min_block, n))
        g = np.diff(np.r_[a, c, b]) - w
        if np.all(g >= min_block):
            return [round(float(v), 2) for v in np.r_[a, c, b]]
    return _sample_lanes(rng, lo, hi, n - 1, w, min_block, wall)


def _intervals(lo, hi, lanes, w, min_block, wall=0.0):
    out, a = [], lo
    for i, c in enumerate(lanes):
        lim = min(min_block, wall - 0.05) if (i == 0 and wall > 0) else min_block
        if c - w / 2 - a >= lim:
            out.append((a, c - w / 2))
        a = c + w / 2
    if hi - a >= (min(min_block, wall - 0.05) if wall > 0 else min_block):
        out.append((a, hi))
    return out


def _in_box(x, y, b, m=0.0):
    return b[0] - m <= x <= b[2] + m and b[1] - m <= y <= b[3] + m


class Layout:
    """Static layout of one seed: lanes, blocks, props, rails, parked forklifts + footprints for the clearance raster."""

    def __init__(self, site, seed):
        S = SITES[site]
        self.site, self.S = site, S
        rng = np.random.default_rng([seed, 1])
        x0, y0, x1, y1 = S['rect']
        self.rect = S['rect']
        self.w = w = round(float(rng.uniform(*S['lane_w'])), 2)
        mb = S.get('min_block', 2.5)
        if S['fixed_x'] is not None:
            self.xl = [round(float(rng.uniform(*iv)), 2) for iv in S['fixed_x']]
            fy = S['fixed_y'][int(rng.integers(len(S['fixed_y'])))]
            self.yl = [round(float(rng.uniform(*iv)), 2) for iv in fy]
        else:
            nx = int(rng.integers(S['nx'][0], S['nx'][1] + 1))
            ny = int(rng.integers(S['ny'][0], S['ny'][1] + 1))
            if S.get('one_inner'):            # exactly one inner lane, on a random axis
                nx, ny = (1, 0) if rng.random() < 0.5 else (0, 1)
            self.xl = _sample_lanes(rng, x0, x1, nx, w, mb, S.get('wall', 0.0))
            self.yl = _sample_lanes(rng, y0, y1, ny, w, mb, S.get('wall', 0.0))
        self.foot = []      # (cx, cy, half_l, half_w, yaw_rad) rectangles; discs as (cx, cy, r)
        self.discs = []
        self.props, self.rails, self.parked = [], [], []
        self.keepout = [tuple(k) for k in S['keepout']]
        bx = _intervals(x0, x1, self.xl, w, mb, S.get('wall', 0.0))
        by = _intervals(y0, y1, self.yl, w, mb, S.get('wall', 0.0))
        self.blocks = [(a[0], b[0], a[1], b[1]) for a in bx for b in by]     # (x0, y0, x1, y1)
        npark = int(rng.integers(S['n_parked'][0], S['n_parked'][1] + 1))
        bays = self._choose_bays(rng, npark)
        k = 0
        for bi, b in enumerate(self.blocks):
            k = self._fill_block(rng, f'b{bi}', b, k, [bb for bb in bays if bb[0] == bi])
            if rng.random() < 0.5:
                self._block_rail(rng, f'r{bi}', b)
        if len(bays) < npark:            # no block bay: park at the side of a lane (parallel, 0.68 m from its edge)
            nodes, adj = self.graph()
            edges = [(a, b, d) for a in adj for b, d, _ in adj[a] if a < b and np.linalg.norm(nodes[b] - nodes[a]) >= 6.5]
            for i in rng.permutation(len(edges)):
                a, b, d = edges[int(i)]
                n_ = np.array([-d[1], d[0]]) * (1 if rng.random() < 0.5 else -1)
                c = 0.5 * (nodes[a] + nodes[b]) + n_ * (w / 2 - 0.68)
                if all(math.hypot(c[0] - o[1], c[1] - o[2]) > 6.0 for o in bays):
                    bays.append((-1, float(c[0]), float(c[1]), float(np.rad2deg(np.arctan2(d[1], d[0])) + rng.choice([0.0, 180.0]))))
                if len(bays) >= npark:
                    break
        for j, (bi, x, y, hd) in enumerate(bays):
            load = ['boxes', 'pallet', 'none'][int(rng.integers(3))]
            lift = round(float(rng.choice([0.0, 0.35, 0.6, 1.1])), 2) if load != 'none' else 0.0
            self.parked.append(Forklift(f'PF{j + 1}', None, (round(x, 3), round(y, 3), round(hd, 1)), None, load, lift))
            u = (math.cos(math.radians(hd)), math.sin(math.radians(hd)))
            for o in (-1.15, 0.0, 1.15):
                self.discs.append((x + o * u[0], y + o * u[1], 0.68))
        if S['rack_rails']:
            self.rails += fw.rack_end_rails(fw.RACK_X, 8.15)
            for r in self.rails:
                self.foot.append(((r.p0[0] + r.p1[0]) / 2, r.p0[1], abs(r.p1[0] - r.p0[0]) / 2, 0.08, 0.0))
        self.windows = fw.windows_default() if S['windows'] else []

    # -- bays for parked forklifts: along a block side (parallel to the lane), inset 0.7 m, sides >= 4.4 m long
    def _choose_bays(self, rng, n):
        cand = []
        for bi, (bx0, by0, bx1, by1) in enumerate(self.blocks):
            if bx1 - bx0 >= 4.4 and by1 - by0 >= 1.3:
                for x in np.arange(bx0 + 2.0, bx1 - 2.0 + 1e-6, 1.4):
                    for y in (by0 + 0.7, by1 - 0.7):
                        cand.append((bi, float(x), float(y), float(rng.choice([0.0, 180.0]))))
            if by1 - by0 >= 4.4 and bx1 - bx0 >= 1.3:
                for y in np.arange(by0 + 2.0, by1 - 2.0 + 1e-6, 1.4):
                    for x in (bx0 + 0.7, bx1 - 0.7):
                        cand.append((bi, float(x), float(y), float(rng.choice([90.0, -90.0]))))
        cand = [c for c in cand if not any(_in_box(c[1], c[2], ko, 2.2) for ko in self.keepout)]
        out = []
        for i in rng.permutation(len(cand)):
            c = cand[i]
            if all(math.hypot(c[1] - o[1], c[2] - o[2]) > 6.0 for o in out):
                out.append(c)
            if len(out) >= n:
                break
        return out

    def _fill_block(self, rng, name, b, k, bays):
        bx0, by0, bx1, by1 = b
        yaw = 0.0
        if bx1 - bx0 < PALLET_L + 0.02:               # narrow strip in x: one column of pallets turned by 90 deg
            if by1 - by0 < PALLET_L + 0.02 or bx1 - bx0 < PALLET_W + 0.02:
                return k
            yaw = 90.0
            xs = [0.5 * (bx0 + bx1)]
            ny = int((by1 - by0 - PALLET_L) // 1.4) + 1
            ys = [by0 + PALLET_L / 2 + i * (by1 - by0 - PALLET_L) / max(ny - 1, 1) for i in range(ny)]
        elif by1 - by0 < PALLET_W + 0.02:
            return k
        else:
            nx = int((bx1 - bx0 - PALLET_L) // 1.4) + 1
            xs = [bx0 + PALLET_L / 2 + i * (bx1 - bx0 - PALLET_L) / max(nx - 1, 1) for i in range(nx)]
            ny = int((by1 - by0 - PALLET_W) // 1.0) + 1
            ys = [by0 + PALLET_W / 2 + i * (by1 - by0 - PALLET_W) / max(ny - 1, 1) for i in range(ny)]
        perim = list(dict.fromkeys([(x, ys[-1]) for x in xs] + [(x, ys[0]) for x in xs] +
                                   [(xs[0], y) for y in ys[1:-1]] + [(xs[-1], y) for y in ys[1:-1]]))
        inner = [(x, y) for x in xs[1:-1] for y in ys[1:-1]]
        slots = [(p, True) for p in perim] + [(p, False) for p in inner if rng.random() < 0.35]
        for i, ((x, y), outer) in enumerate(slots):
            if any(abs((x - bb[1]) * math.cos(math.radians(bb[3])) + (y - bb[2]) * math.sin(math.radians(bb[3]))) < 1.9 + 0.65
                   and abs(-(x - bb[1]) * math.sin(math.radians(bb[3])) + (y - bb[2]) * math.cos(math.radians(bb[3]))) < 0.7 + 0.65
                   for bb in bays):
                continue
            if any(_in_box(x, y, ko, 0.75) for ko in self.keepout):
                continue
            r = rng.random()
            nm = f'{name}_{i}'
            x, y = round(x, 3), round(y, 3)
            if r < 0.06:
                continue                                        # gap
            if r < 0.51:
                self.props += fw.pallet_stack(nm, x, y, yaw, int(rng.integers(1, 4)), kind=0)
            elif r < 0.71:
                self.props += fw.pallet_stack(nm, x, y, yaw, int(rng.integers(1, 3)), kind=1)
            elif r < 0.83:
                self.props += fw.klt_pallet(nm, x, y, yaw)
            elif r < 0.93:
                self.props += fw.pallet_pile(nm, x, y, int(rng.integers(2, 6)), yaw)
            elif r < 0.97:
                self.props.append(Prop(nm, fw.DOLLY, (x, y, 0.0), 90.0 + yaw + float(rng.uniform(-8, 8)), 'trolley'))
            elif r < 0.985:
                self.props.append(Prop(nm, fw.BARREL, (x, y, 0.0), 0.0, None))
                self.discs.append((x, y, 0.32))
                continue
            else:
                self.props.append(Prop(nm, fw.CONE, (x, y, 0.0), 0.0, None))
                self.discs.append((x, y, 0.22))
                continue
            self.foot.append((x, y, PALLET_L / 2 + 0.03, PALLET_W / 2 + 0.03, math.radians(yaw)))
            k += 1
        return k

    def _block_rail(self, rng, name, b):
        bx0, by0, bx1, by1 = b
        side = int(rng.integers(4))
        if side < 2:
            y = by0 - 0.12 if side == 0 else by1 + 0.12
            a, c = bx0 + 0.2 * (bx1 - bx0), bx1 - 0.2 * (bx1 - bx0)
            self.rails.append(Rail(name, (round(a, 2), round(y, 2)), (round(c, 2), round(y, 2)), 0.9))
            self.foot.append(((a + c) / 2, y, (c - a) / 2 + 0.05, 0.08, 0.0))
        else:
            x = bx0 - 0.12 if side == 2 else bx1 + 0.12
            a, c = by0 + 0.2 * (by1 - by0), by1 - 0.2 * (by1 - by0)
            self.rails.append(Rail(name, (round(x, 2), round(a, 2)), (round(x, 2), round(c, 2)), 0.9))
            self.foot.append((x, (a + c) / 2, (c - a) / 2 + 0.05, 0.08, math.pi / 2))

    # -- lane graph
    def graph(self):
        """nodes: intersections + lane ends; adjacency {node: [(nbr, dir unit, axis)]}"""
        x0, y0, x1, y1 = self.rect
        e = 1.3
        nodes, adj = [], {}

        def nid(p):
            for i, q in enumerate(nodes):
                if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6:
                    return i
            nodes.append(p)
            return len(nodes) - 1

        lanes = [('x', c, [(c, y) for y in [y0 + e] + self.yl + [y1 - e]]) for c in self.xl] + \
                [('y', c, [(x, c) for x in [x0 + e] + self.xl + [x1 - e]]) for c in self.yl]
        for ax, c, pts in lanes:
            pts = sorted(set(pts), key=lambda p: p[1] if ax == 'x' else p[0])
            ids = [nid(p) for p in pts]
            for a, b in zip(ids, ids[1:]):
                pa, pb = np.array(nodes[a]), np.array(nodes[b])
                if np.linalg.norm(pb - pa) < 1.0 or self._lane_blocked(pa, pb):
                    continue
                d = (pb - pa) / np.linalg.norm(pb - pa)
                adj.setdefault(a, []).append((b, d, ax))
                adj.setdefault(b, []).append((a, -d, ax))
        return [np.array(p) for p in nodes], adj

    def _lane_blocked(self, pa, pb):
        for t in np.linspace(0, 1, 40):
            p = pa + t * (pb - pa)
            if any(_in_box(p[0], p[1], ko, 1.0) for ko in self.keepout):
                return True
        return False

    def raster(self, res=0.1):
        """distance [m] to the nearest static obstacle on a grid over PLAN_BOX (walls = outside the env interior)."""
        from scipy import ndimage
        X0, Y0, X1, Y1 = self.S['plan_box']
        W, H = int(math.ceil((X1 - X0) / res)), int(math.ceil((Y1 - Y0) / res))
        gx = X0 + (np.arange(W) + 0.5) * res
        gy = Y1 - (np.arange(H) + 0.5) * res
        XX, YY = np.meshgrid(gx, gy)
        occ = np.zeros((H, W), bool)
        r0 = self.rect
        occ |= (XX < r0[0] - 0.6) | (XX > r0[2] + 0.6) | (YY < r0[1] - 0.6) | (YY > r0[3] + 0.6)
        for cx, cy, hl, hw, yaw in self.foot:
            c, s = math.cos(yaw), math.sin(yaw)
            dx, dy = XX - cx, YY - cy
            occ |= (np.abs(dx * c + dy * s) <= hl) & (np.abs(-dx * s + dy * c) <= hw)
        for cx, cy, r in self.discs:
            occ |= (XX - cx) ** 2 + (YY - cy) ** 2 <= r * r
        for ko in self.keepout:
            occ |= (XX >= ko[0]) & (XX <= ko[2]) & (YY >= ko[1]) & (YY <= ko[3])
        d = ndimage.distance_transform_edt(~occ) * res
        return d, (X0, Y1, res)


def _dist_at(D, xy):
    d, (X0, Y1, res) = D
    j = np.clip(((xy[..., 0] - X0) / res).astype(int), 0, d.shape[1] - 1)
    i = np.clip(((Y1 - xy[..., 1]) / res).astype(int), 0, d.shape[0] - 1)
    return d[i, j]


# ============================================================================================== camera
def camera_tour(L, seed):
    """Random tour on the lane graph -> camera cfg (waypoints, seg_speeds, wp_heights) + leg list."""
    rng = np.random.default_rng([seed, 2])
    nodes, adj = L.graph()
    for attempt in range(400):
        L_t = float(rng.uniform(80.0, 92.0))
        a = int(rng.choice([q for q in adj if len(adj[q]) >= 2]))
        b, d, _ = adj[a][int(rng.integers(len(adj[a])))]
        if len(adj.get(b, [])) < 2:
            continue
        # first leg: >= 12 m straight (hover view + the L3 forklift parked ahead)
        path = [a, b]
        straight = np.linalg.norm(nodes[b] - nodes[a])
        dcur = d
        ok = True
        while straight < 12.0:
            nxt = [(n, dd) for n, dd, _ in adj.get(path[-1], []) if dd @ dcur > 0.99 and len(adj.get(n, [])) >= 2]
            if not nxt:
                ok = False
                break
            path.append(nxt[0][0])
            straight += np.linalg.norm(nodes[nxt[0][0]] - nodes[path[-2]])
        if not ok:
            continue
        visits = {}
        length = sum(np.linalg.norm(nodes[q] - nodes[p]) for p, q in zip(path, path[1:]))
        for p, q in zip(path, path[1:]):
            visits[frozenset((p, q))] = visits.get(frozenset((p, q)), 0) + 1
        while length < L_t + 10.0:
            cur, prev = path[-1], path[-2]
            dprev = nodes[cur] - nodes[prev]
            dprev /= np.linalg.norm(dprev)
            opts = [(n, dd) for n, dd, _ in adj.get(cur, []) if dd @ dprev > -0.5 and len(adj.get(n, [])) >= 2]
            if not opts:
                break
            wgt = np.array([(2.0 if dd @ dprev > 0.99 else 1.0) / (1 + 3 * visits.get(frozenset((cur, n)), 0))
                            for n, dd in opts])
            n = opts[int(rng.choice(len(opts), p=wgt / wgt.sum()))][0]
            length += np.linalg.norm(nodes[n] - nodes[cur])
            visits[frozenset((cur, n))] = visits.get(frozenset((cur, n)), 0) + 1
            path.append(n)
        if length < L_t + 4.0:
            continue
        # truncate at L_t; the lane must continue >= 8 m beyond the end point (the L3 co-mover drives on and parks)
        P = [nodes[i] for i in path]
        s = np.r_[0, np.cumsum([np.linalg.norm(q - p) for p, q in zip(P, P[1:])])]
        j = int(np.searchsorted(s, L_t)) - 1
        u = (L_t - s[j]) / (s[j + 1] - s[j])
        end = P[j] + u * (P[j + 1] - P[j])
        dend = (P[j + 1] - P[j]) / np.linalg.norm(P[j + 1] - P[j])
        beyond = np.linalg.norm(P[j + 1] - end)
        k2 = j + 1
        while k2 + 1 < len(P) and (P[k2 + 1] - P[k2]) @ dend / np.linalg.norm(P[k2 + 1] - P[k2]) > 0.99:
            beyond += np.linalg.norm(P[k2 + 1] - P[k2])
            k2 += 1
        if beyond < 8.0:
            # extend straight along the lane graph beyond the last node
            q, dd, ext = path[min(k2, len(path) - 1)], dend, 0.0
            while True:
                nx = [(n, d2) for n, d2, _ in adj.get(q, []) if d2 @ dd > 0.99]
                if not nx:
                    break
                ext += np.linalg.norm(nodes[nx[0][0]] - nodes[q])
                q = nx[0][0]
            if beyond + ext < 8.0:
                continue
        wps = [P[i] for i in range(j + 1)] + [end]
        if np.linalg.norm(wps[-1] - wps[-2]) < 2.0:
            continue
        # merge collinear waypoints into legs
        legs, cur = [], [0]
        for i in range(1, len(wps) - 1):
            d1 = wps[i] - wps[i - 1]
            d2 = wps[i + 1] - wps[i]
            if d1 @ d2 / (np.linalg.norm(d1) * np.linalg.norm(d2)) > 0.99:
                cur.append(i)
            else:
                cur.append(i)
                legs.append(cur)
                cur = [i]
        cur.append(len(wps) - 1)
        legs.append(cur)
        sp_leg = [round(float(rng.choice(np.arange(0.70, 1.31, 0.05))), 2) for _ in legs]
        h_leg = [round(float(rng.uniform(1.0, 1.8)), 2) for _ in legs]
        long_ = [i for i, lg in enumerate(legs) if np.linalg.norm(wps[lg[-1]] - wps[lg[0]]) >= 8.0 and i > 0]
        if long_:
            h_leg[int(rng.choice(long_))] = round(float(rng.uniform(2.2, 2.4)), 2)
        seg_speeds, wp_h = [], [1.3]
        for li, lg in enumerate(legs):
            for _ in range(len(lg) - 1):
                seg_speeds.append(sp_leg[li])
            for _ in lg[1:]:
                wp_h.append(h_leg[li])
        cfg = dict(waypoints=[[round(float(p[0]), 3), round(float(p[1]), 3)] for p in wps], seg_speeds=seg_speeds,
                   wp_heights=wp_h, height_smooth_s=1.5, speed=1.0, height=1.4,
                   height_amp=round(float(rng.uniform(0.10, 0.12)), 3), yaw_amp_deg=round(float(rng.uniform(12, 14)), 2),
                   seed=int(seed), platform='drone', hover_start_s=3.0, hover_end_s=2.0, yaw_rate_max_deg=100.0,
                   ramp_s=1.0)
        dur = BodyTrajectory(cfg).duration
        if not DUR_RANGE[0] <= dur <= DUR_RANGE[1]:
            continue
        return cfg, dict(path=path, nodes=nodes, adj=adj, legs=legs, wps=wps, end_dir=dend)
    raise RuntimeError(f'no camera tour for seed {seed}')


# ============================================================================================== actors
def _discs(actor, t):
    path = actor.path
    a = path.at(t) if path is not None else dict(xy=np.tile(np.array(actor.pose[:2], float), (len(t), 1)),
                                                 heading=np.full(len(t), math.radians(actor.pose[2])))
    xy = a['xy']
    if isinstance(actor, Forklift):
        u = np.stack([np.cos(a['heading']), np.sin(a['heading'])], -1)
        if actor.kind == 'cart':
            off, r = np.array([-0.2, 0.2]), np.array([0.45, 0.45])
        else:
            off, r = np.array([-1.15, 0.0, 1.15]), np.array([0.68, 0.68, 0.68])
        return xy[:, None, :] + off[None, :, None] * u[:, None, :], r
    return xy[:, None, :], np.array([0.3])


class Choreo:
    """Actor generator with rejection sampling against the camera, the static layout and all accepted actors."""

    def __init__(self, L, cam, body, tour, seed):
        self.L, self.cam, self.body, self.tour = L, cam, body, tour
        self.rng = np.random.default_rng([seed, 3])
        self.tt = np.arange(0.0, body.duration, 0.05)
        self.camxy = cam.xy_at(self.tt)
        self.camyaw = np.interp(self.tt, cam.t, cam.yaw)
        self.D = L.raster()
        self.dur = body.duration
        self.acc = []           # (actor, tier, discs)
        self.log = []
        self.chars = list(self.rng.permutation(CHARACTERS))
        self._ci = 0
        self.t0 = body.t_start   # take-off
        # camera legs with times / arc lengths
        wps, legs = tour['wps'], tour['legs']
        # camera arc length at each waypoint: closest approach in a window after the previous waypoint (the tour
        # may pass a node twice)
        s_w = [0.0]
        tprev = 0.0
        for p, q in zip(wps, wps[1:]):
            seg = float(np.linalg.norm(np.asarray(q) - np.asarray(p)))
            t = cam.t_near(q, t_min=tprev + 0.2, t_max=min(tprev + seg / 0.4 + 6.0, cam.t[-1]))
            s_w.append(cam.s_at(t))
            tprev = t
        self.s_w = np.array(s_w)
        self.legs = []
        for lg in legs:
            p0, p1 = np.asarray(wps[lg[0]], float), np.asarray(wps[lg[-1]], float)
            d = (p1 - p0) / np.linalg.norm(p1 - p0)
            self.legs.append(dict(p0=p0, p1=p1, d=d, n=np.array([-d[1], d[0]]), len=float(np.linalg.norm(p1 - p0)),
                                  s0=float(self.s_w[lg[0]]), s1=float(self.s_w[lg[-1]]),
                                  t0=cam.t_at_s(self.s_w[lg[0]]), t1=cam.t_at_s(self.s_w[lg[-1]]),
                                  nodes=[wps[i] for i in lg]))
        # intersection passages: (node xy, camera time, camera dir in, cross-lane arm directions + lengths)
        nodes, adj = tour['nodes'], tour['adj']
        self.passes = []
        for i in range(1, len(tour['path'])):
            q = tour['path'][i]
            if i >= len(wps) - 1 or len(adj.get(q, [])) < 3:
                continue
            X = nodes[q]
            t = cam.t_at_s(self.s_w[i])
            if np.linalg.norm(cam.xy_at(t) - X) > 0.8:
                continue
            din = X - nodes[tour['path'][i - 1]]
            din /= np.linalg.norm(din)
            dout = np.asarray(wps[i + 1], float) - X
            dout /= np.linalg.norm(dout)
            # exits: lanes at the node that the camera neither comes from nor takes next (direction, length)
            arms = [(dd, self._arm_len(q, dd)) for n, dd, _ in adj[q] if dd @ din > -0.9 and dd @ dout < 0.9]
            self.passes.append(dict(X=X, t=t, s=cam.s_at(t), din=din, dout=dout, arms=arms,
                                    straight=self._arm_len(q, dout)))
        self.lat_fork = L.w / 2 - 0.80
        self.lat_person = L.w / 2 - 0.45
        self.side = 1.0                                           # set by make_actors: free side (away from co-movers)

    def plat(self):
        """lateral offset of a walker: 1.1 m .. lane edge - 0.45 m, on the free side with probability 0.75"""
        v = float(self.rng.uniform(1.1, max(self.lat_person, 1.15)))
        return v * self.side * (1 if self.rng.random() < 0.75 else -1)

    def _arm_len(self, q, dd):
        nodes, adj = self.tour['nodes'], self.tour['adj']
        ln, cur = 0.0, q
        while True:
            nx = [n for n, d2, _ in adj.get(cur, []) if d2 @ dd > 0.99]
            if not nx:
                return ln
            ln += np.linalg.norm(nodes[nx[0]] - nodes[cur])
            cur = nx[0]

    def arrive(self, start, wps, speed, t_arr, stop=False):
        """PathBuilder waiting at `start`, then driving the legs through `wps` so that it reaches wps[-1] at t_arr"""
        probe = PathBuilder(start).leg(wps, speed, stop=stop, corner_radius=1.2)
        t_go = t_arr - probe.t
        if t_go < 0.3:
            raise ValueError('cannot arrive in time')
        return PathBuilder(start).wait_until(t_go).leg(wps, speed, stop=stop, corner_radius=1.2)

    def char(self):
        c = self.chars[self._ci % len(self.chars)]
        self._ci += 1
        return str(c)

    # -- acceptance
    def ok(self, actor, static_tol=0.0):
        tt = self.tt
        c, r = _discs(actor, tt)
        act = is_active(actor, tt)
        dcam = np.min(np.linalg.norm(c - self.camxy[:, None, :], axis=2) - r[None], axis=1) - CAM_R
        if np.any(dcam[act] < CAM_CLR):
            return False, f'camera {dcam[act].min():.2f}'
        ds = _dist_at(self.D, c) - r[None]
        if np.any(ds[act] < static_tol):
            return False, f'static {ds[act].min():.2f}'
        for b, _, (cb, rb) in self.acc:
            if getattr(actor, 'attached_to', None) == b.name or getattr(b, 'attached_to', None) == actor.name:
                continue
            both = act & is_active(b, tt)
            if not both.any():
                continue
            d = np.linalg.norm(c[:, :, None, :] - cb[:, None, :, :], axis=3) - r[None, :, None] - rb[None, None, :]
            d = d.reshape(len(tt), -1).min(1)
            if np.any(d[both] < PAIR_CLR):
                return False, f'{b.name} {d[both].min():.2f}'
        return True, ''

    def out_of_view(self, xy):
        """[n] bool over self.tt: point xy outside the cam0 field of view (+margin) or > 30 m away"""
        v = np.asarray(xy, float) - self.camxy
        bearing = np.arctan2(v[:, 1], v[:, 0]) - self.camyaw
        bearing = np.abs(np.angle(np.exp(1j * bearing)))
        return (bearing > HFOV_HALF) | (np.linalg.norm(v, axis=1) > 30.0)

    def auto_active(self, actor):
        """Visibility window of a moving actor: it appears at its start pose at the last out-of-view instant >= 1.5 s
        before it starts moving (t=0 if it is in view since the start) and disappears at the first out-of-view instant
        >= 1 s after it has stopped (never, if it stays in view). Static actors are always present."""
        if actor.path is None:
            return None
        q = actor.path.at(self.tt)
        mv = np.nonzero(q['speed'] > 0.05)[0]
        if not len(mv):
            return None
        t0m, t1m = self.tt[mv[0]], self.tt[mv[-1]]
        oov0 = self.out_of_view(q['xy'][0])
        cand = np.nonzero(oov0 & (self.tt <= t0m - 1.5))[0]
        t_show = float(self.tt[cand[-1]]) if len(cand) else 0.0
        if not np.all(~oov0[(self.tt >= t_show + 0.05) & (self.tt <= t0m)]) and len(cand):
            pass
        oov1 = self.out_of_view(q['xy'][-1])
        cand = np.nonzero(oov1 & (self.tt >= t1m + 1.0))[0]
        t_hide = float(self.tt[cand[0]]) if len(cand) else 1e9
        return (round(t_show, 2), round(t_hide, 2)) if (t_show > 0 or t_hide < 1e9) else None

    def add(self, actor, tier, static_tol=0.0, partner=None):
        actor.active = self.auto_active(actor)
        if partner is not None:
            partner.active = actor.active
        ok, why = self.ok(actor, static_tol)
        if ok and partner is not None:
            ok, why = self.ok(partner, static_tol)
        if not ok:
            return False, why
        for a in ([actor] + ([partner] if partner is not None else [])):
            self.acc.append((a, tier, _discs(a, self.tt)))
        return True, ''

    def try_(self, name, tier, fn, n=40, static_tol=0.0):
        why = ''
        for _ in range(n):
            try:
                out = fn()
            except (ValueError, IndexError, RuntimeError) as e:   # infeasible sample
                why = str(e)
                continue
            if out is None:
                continue
            a, partner = (out if isinstance(out, tuple) else (out, None))
            ok, why = self.add(a, tier, static_tol, partner)
            if ok:
                self.log.append((name, tier, 'ok'))
                return a
        self.log.append((name, tier, f'dropped ({why})'))
        return None

    # -- helpers
    def pb_build(self, pb, sigma):
        return pb.build(self.dur, sigma=sigma)

    def fork(self, name, pb, load, lift, driver=True, kind='forklift'):
        return Forklift(name, self.pb_build(pb, 0.45 if kind == 'forklift' else 0.3), (0, 0, 0),
                        self.char() if driver else None, load, lift, kind=kind)

    def person(self, name, pb, attached=None):
        return Person(name, self.char(), self.pb_build(pb, 0.25), attached_to=attached)

    def cart_pair(self, name, pb, load_lift=0.25):
        """person path pb pushing a dolly 0.95 m ahead of it"""
        pe = Person(name + 'p', self.char(), self.pb_build(pb, 0.25), attached_to=name)
        pp = pe.path
        u = np.stack([np.cos(pp.heading), np.sin(pp.heading)], -1)
        P = np.stack([pp.x, pp.y], -1) + 0.95 * u
        cp = PlanarPath(pp.grid, P, np.zeros(len(pp.grid), bool), self.dur, sigma=0.02,
                        heading0=float(pp.heading[0]))
        cart = Forklift(name, cp, (0, 0, 0), None, 'boxes', load_lift, kind='cart')
        return cart, pe

    def frac_time(self, f):
        return self.cam.t_at_s(f * self.cam.L)

    def pass_in(self, f0, f1):
        return [p for p in self.passes if f0 * self.cam.L <= p['s'] <= f1 * self.cam.L]

    def leg_at(self, f):
        s = f * self.cam.L
        for lg in self.legs:
            if lg['s0'] <= s <= lg['s1']:
                return lg
        return self.legs[-1]


def make_actors(L, cam, body, tour, seed):
    C = Choreo(L, cam, body, tour, seed)
    rng = C.rng
    T = cam.L
    dur = C.dur
    t_take = C.t0
    side_co = 1.0 if rng.random() < 0.5 else -1.0          # co-movers drive 0.25 m to the -side_co side of the centre
    lat_co = -0.25 * side_co
    C.side = side_co

    # ------------------------------------------------------------------ L3: co-movers, alongside, loaded carts
    fa_end = float(rng.uniform(0.35, 0.48))

    def co_a():
        a0 = float(rng.uniform(4.5, 5.5))
        a1 = float(rng.uniform(2.8, 3.6))
        ps = C.pass_in(fa_end - 0.12, fa_end + 0.12)
        if not ps:
            raise ValueError('no exit node')
        P = ps[int(rng.integers(len(ps)))]
        arms = [(d, ln) for d, ln in P['arms'] if ln >= 7.0]
        if not arms:
            raise ValueError('no exit arm')
        d, ln = arms[int(rng.integers(len(arms)))]
        t_f = cam.t_at_s(P['s'] - a1)
        pb = PathBuilder(cam.follow_point(0.0, a0, lat_co)).wait_until(t_take + float(rng.uniform(0.3, 0.6)))
        t_mid = cam.t_at_s(0.25 * T)
        pb.follow(cam, t_mid, a0, lat_co, ahead_end=a1).follow(cam, t_f, a1, lat_co)
        stop = P['X'] + d * min(ln - 1.8, float(rng.uniform(6.0, 10.0)))
        return C.fork('Q1', pb.leg([P['X'] + 0.0 * d, stop], 1.0, ramp=0.0, corner_radius=1.2), 'boxes',
                      round(float(rng.uniform(0.5, 1.0)), 2))

    def co_full():
        a0 = float(rng.uniform(4.5, 5.5))
        a1 = float(rng.uniform(3.0, 3.8))
        pb = PathBuilder(cam.follow_point(0.0, a0, lat_co)).wait_until(t_take + float(rng.uniform(0.3, 0.6)))
        t_mid = cam.t_at_s(0.25 * T)
        t_e = cam.t_at_s(T - a1 - 0.5)
        pb.follow(cam, t_mid, a0, lat_co, ahead_end=a1).follow(cam, t_e, a1, lat_co, ahead_end=a1 + 0.3)
        end = cam.follow_point(t_e, a1 + 0.3, lat_co) + tour['end_dir'] * float(rng.uniform(5.0, 6.5))
        return C.fork('Q1', pb.leg([end], 0.9, ramp=0.0), 'boxes', round(float(rng.uniform(0.5, 1.0)), 2))

    if C.try_('Q1 co-mover from take-off, exits', 3, co_a) is None:
        C.try_('Q1 co-mover from take-off to the end', 3, co_full)
    fb_start = float(rng.uniform(0.58, 0.68))

    def co_b():
        ps = C.pass_in(fb_start - 0.08, fb_start + 0.08)
        if not ps:
            raise ValueError('no entry node')
        P = ps[int(rng.integers(len(ps)))]
        arms = [(d, ln) for d, ln in P['arms'] if ln >= 7.0]
        if not arms:
            raise ValueError('no entry arm')
        d, ln = arms[int(rng.integers(len(arms)))]
        a = float(rng.uniform(3.2, 4.0))
        wait = P['X'] + d * min(ln - 1.8, float(rng.uniform(6.0, 8.0)))
        t_arr = cam.t_at_s(P['s'] - a)
        pb = C.arrive(wait, [P['X'] - 0.3 * P['din']], 1.2, t_arr)
        t_e = cam.t_at_s(T - a - 0.5)
        pb.follow(cam, t_e, a, lat_co, ahead_end=a + 0.3)
        end = cam.follow_point(t_e, a + 0.3, lat_co) + tour['end_dir'] * float(rng.uniform(5.0, 6.5))
        return C.fork('Q2', pb.leg([end], 0.9, ramp=0.0), 'boxes', round(float(rng.uniform(0.5, 1.0)), 2))

    C.try_('Q2 co-mover turn-in to the end', 3, co_b)

    # ------------------------------------------------------------------ L2: forklifts + carts
    def takeoff_cross():
        ps = [p for p in C.passes if 6.0 <= p['s'] <= 22.0]
        if not ps:
            raise ValueError('no node ahead')
        P = ps[0]
        arms = [(d, ln) for d, ln in P['arms'] if ln >= 6.0]
        if len(arms) < 2:
            raise ValueError('need two exits')
        i = int(rng.integers(2))
        d, ln = arms[i]
        oth = arms[1 - i]
        st = P['X'] + d * min(ln - 1.8, 6.0)
        en = P['X'] - d * min(oth[1] - 1.8, float(rng.uniform(5.0, 8.0)))
        pb = PathBuilder(st).wait_until(t_take + float(rng.uniform(-0.5, 1.5)))
        return C.fork('V1', pb.leg([en], float(rng.uniform(1.1, 1.4))), 'boxes', round(float(rng.uniform(0.2, 0.5)), 2))

    C.try_('V1 crossing at take-off', 2, takeoff_cross)

    def leader(nm, fr):
        f = float(rng.uniform(*fr))
        ps = C.pass_in(f + 0.15, f + 0.40)
        if not ps:
            raise ValueError('no exit')
        P = ps[int(rng.integers(len(ps)))]
        arms = [(d, ln) for d, ln in P['arms'] if ln >= 7.0]
        if not arms:
            raise ValueError('no exit arm')
        d, ln = arms[int(rng.integers(len(arms)))]
        a = float(rng.uniform(5.5, 8.0))
        ts = cam.t_at_s(f * T)
        t_f = cam.t_at_s(P['s'] - a + 0.5)
        pb = PathBuilder(cam.follow_point(ts, a, -lat_co)).wait_until(ts).follow(cam, t_f, a, -lat_co, ahead_end=a - 0.5)
        stop = P['X'] + d * min(ln - 1.8, float(rng.uniform(5.0, 9.0)))
        return C.fork(nm, pb.leg([P['X'], stop], 1.1, ramp=0.0, corner_radius=1.2),
                      ['boxes', 'pallet'][int(rng.integers(2))], round(float(rng.uniform(0.2, 0.5)), 2))

    C.try_('V2 leader 5.5-8 m (late onset)', 2, lambda: leader('V2', (0.08, 0.35)))
    C.try_('V7 leader 5.5-8 m (late onset)', 2, lambda: leader('V7', (0.40, 0.65)))
    for vn in ('V3', 'V4', 'V8', 'V9'):
        def crosser(vn=vn):
            ps = [p for p in C.passes if p['s'] > 15.0 and len(p['arms']) == 2]
            if not ps:
                raise ValueError('no node with two exits')
            P = ps[int(rng.integers(len(ps)))]
            i = int(rng.integers(2))
            d, ln = P['arms'][i]
            oth = [P['arms'][1 - i]]
            if ln < 6.0 or oth[0][1] < 6.0:
                raise ValueError('short arms')
            lead = float(rng.uniform(5.5, 10.0))
            sp = float(rng.uniform(1.0, 1.5))
            h = min(ln - 1.8, 7.0)
            st = P['X'] + d * h
            en = P['X'] - d * min(oth[0][1] - 1.8, float(rng.uniform(6.0, 9.0)))
            pb = PathBuilder(st).wait_until(max(P['t'] - lead - h / sp - 0.8, 0.5))
            return C.fork(vn, pb.leg([en], sp), ['boxes', 'pallet', 'none'][int(rng.integers(3))],
                          round(float(rng.uniform(0.1, 0.5)), 2))
        C.try_(f'{vn} crossing at an intersection', 2, crosser)

    def headon_turnoff():
        ps = [p for p in C.passes if p['s'] > 20.0 and p['arms'] and p['straight'] >= 10.0]
        if not ps:
            raise ValueError('no node with a lane beyond')
        P = ps[int(rng.integers(len(ps)))]
        # comes towards the camera along the lane beyond the node and turns off into an arm 4-7 s before the camera
        d, ln = P['arms'][int(rng.integers(len(P['arms'])))]
        if ln < 7.0:
            raise ValueError('short arm')
        far = P['X'] + P['dout'] * min(P['straight'] - 1.8, 9.0)
        lead = float(rng.uniform(4.0, 7.0))
        stop = P['X'] + d * min(ln - 1.8, float(rng.uniform(6.0, 9.0)))
        pb = C.arrive(far, [P['X'] + 0.5 * P['dout']], 1.1, P['t'] - lead)
        return C.fork('V5', pb.leg([P['X'], stop], 1.1, ramp=0.0, corner_radius=1.3), 'boxes',
                      round(float(rng.uniform(0.2, 0.6)), 2))

    C.try_('V5 head-on, turns off', 2, headon_turnoff)

    def overtaker(vn='V10'):
        lg = C.legs[int(rng.integers(len(C.legs)))]
        if lg['len'] < 12.0:
            raise ValueError('short leg')
        lat = C.lat_fork * side_co
        st = lg['p0'] - lg['d'] * 1.0 + lg['n'] * lat
        en = lg['p1'] - lg['d'] * 2.0 + lg['n'] * lat
        pb = PathBuilder(st).wait_until(max(lg['t0'] - 0.5, 0.5))
        return C.fork(vn, pb.leg([en], float(rng.uniform(1.5, 1.8))), 'boxes', round(float(rng.uniform(0.2, 0.6)), 2))

    C.try_('V10 overtaking the camera, parallel', 2, overtaker)
    C.try_('V15 overtaking the camera, parallel', 2, lambda: overtaker('V15'))
    for vn in ('V11', 'V12', 'V13', 'V14'):
        def headon_pass(vn=vn):
            lg = C.legs[int(rng.integers(len(C.legs)))]
            if lg['len'] < 12.0:
                raise ValueError('short leg')
            lat = C.lat_fork * side_co
            st = lg['p1'] - lg['d'] * 2.0 + lg['n'] * lat
            en = lg['p0'] + lg['d'] * 2.0 + lg['n'] * lat
            sp = float(rng.uniform(1.0, 1.4))
            t_meet = cam.t_at_s(lg['s0'] + float(rng.uniform(0.45, 0.7)) * lg['len'])
            dist_ = float(np.linalg.norm(cam.xy_at(t_meet) - st))
            pb = PathBuilder(st).wait_until(max(t_meet - dist_ / (sp + 1.0) - 0.8, 0.5))
            return C.fork(vn, pb.leg([en], sp), ['boxes', 'pallet'][int(rng.integers(2))], round(float(rng.uniform(0.2, 0.6)), 2))
        C.try_(f'{vn} head-on, passing on the free side', 2, headon_pass)

    def slow_parallel():
        lg = C.legs[int(rng.integers(len(C.legs)))]
        if lg['len'] < 12.0:
            raise ValueError('short leg')
        lat = C.lat_fork * side_co
        st = lg['p0'] + lg['d'] * float(rng.uniform(4.0, 7.0)) + lg['n'] * lat
        en = lg['p1'] - lg['d'] * 2.2 + lg['n'] * lat
        pb = PathBuilder(st).wait_until(max(lg['t0'] - 2.0, 0.5))
        return C.fork('V6', pb.leg([en], float(rng.uniform(0.3, 0.5))), 'pallet', round(float(rng.uniform(0.1, 0.4)), 2))

    C.try_('V6 slow parallel (overtaken)', 2, slow_parallel)
    for cn in ('C1', 'C2', 'C3'):
        def cart(cn=cn):
            if rng.random() < 0.5 and C.passes:      # crossing at an intersection
                P = C.passes[int(rng.integers(len(C.passes)))]
                if len(P['arms']) < 2:
                    raise ValueError('no 4-way')
                d, ln = P['arms'][0]
                oth = P['arms'][1]
                if ln < 5.0 or oth[1] < 5.0:
                    raise ValueError('short arms')
                st, en = P['X'] + d * min(ln - 1.5, 5.0), P['X'] + oth[0] * min(oth[1] - 1.5, 5.0)
                lead = float(rng.uniform(4.0, 9.0))
                sp = 0.8
                pb = PathBuilder(st - d * 0.95).wait_until(max(P['t'] - lead - 5.0 / sp - 0.6, 0.5))
                return C.cart_pair(cn, pb.leg([en + d * 0.95], sp), 0.25)
            lg = C.legs[int(rng.integers(len(C.legs)))]       # head-on along a leg
            if lg['len'] < 10.0:
                raise ValueError('short leg')
            lat = C.lat_person * (1 if rng.random() < 0.5 else -1)
            st = lg['p1'] - lg['d'] * 1.5 + lg['n'] * lat
            en = lg['p0'] + lg['d'] * 1.5 + lg['n'] * lat
            sp = 0.8
            t_meet = cam.t_at_s(lg['s0'] + 0.5 * lg['len'])
            pb = PathBuilder(st + lg['d'] * 0.95).wait_until(max(t_meet - (0.5 * lg['len'] - 1.5) / sp - 0.6, 0.5))
            return C.cart_pair(cn, pb.leg([en + lg['d'] * 0.95], sp), 0.25)
        C.try_(f'{cn} cart', 2, cart)

    # ------------------------------------------------------------------ L1: people
    lg0 = C.legs[0]

    def standing_hover():
        lat = C.lat_person + 0.12
        lat *= (1 if rng.random() < 0.5 else -1)
        p = lg0['p0'] + lg0['d'] * float(rng.uniform(6.0, min(14.0, lg0['len'] - 1.0))) + lg0['n'] * lat
        return C.person('P01', PathBuilder(p).wait(dur))

    C.try_('P01 standing at a stack, in view during the hover', 1, standing_hover, static_tol=-0.1)

    def hover_mover():
        dist_ = float(rng.uniform(7.0, 11.0))
        X = lg0['p0'] + lg0['d'] * dist_
        lat = C.plat()
        if rng.random() < 0.5:     # walk diagonally across the lane during the hover, then stand at the far side
            st, en = X + lg0['n'] * lat, X + lg0['d'] * 2.5 - lg0['n'] * lat
        else:                      # walk towards the camera during the hover, then stand
            st, en = X + lg0['d'] * 3.0 + lg0['n'] * lat, X + lg0['n'] * lat
        return C.person('P02', PathBuilder(st).wait_until(float(rng.uniform(0.2, 0.8))).leg([en], 1.0))

    C.try_('P02 walking DURING the hover', 1, hover_mover, static_tol=-0.1)

    def onset():
        lat = C.plat()
        st = lg0['p0'] + lg0['d'] * float(rng.uniform(3.5, 6.0)) + lg0['n'] * lat
        en = lg0['p1'] - lg0['d'] * 1.0 + lg0['n'] * lat
        return C.person('P03', PathBuilder(st).wait_until(t_take + 0.3).leg([en], float(rng.uniform(0.7, 0.9))))

    C.try_('P03 starts walking at take-off', 1, onset, static_tol=-0.1)
    k = 4
    for kind in ('headon',) * 8 + ('ahead',) * 8 + ('cross',) * 9 + ('stand',) * 3:
        nm = f'P{k:02d}'
        k += 1

        def walker(kind=kind, nm=nm):
            if kind == 'cross' and (not C.passes or rng.random() < 0.35):    # across the lane, mid-leg, ahead of the camera
                lg = C.legs[int(rng.integers(len(C.legs)))]
                if lg['len'] < 7.0:
                    raise ValueError('short leg')
                u = float(rng.uniform(0.3, 0.8))
                X = lg['p0'] + lg['d'] * u * lg['len']
                sg = 1 if rng.random() < 0.5 else -1
                st = X + lg['n'] * sg * C.lat_person
                en = X - lg['n'] * sg * (C.lat_person + 0.1) + lg['d'] * float(rng.uniform(-1.5, 1.5))
                sp = float(rng.uniform(0.9, 1.3))
                t_x = cam.t_at_s(lg['s0'] + u * lg['len']) - float(rng.uniform(2.5, 6.0))
                return C.person(nm, PathBuilder(st).wait_until(max(t_x - C.lat_person / sp - 0.6, 0.3)).leg([en], sp))
            if kind == 'cross':
                P = C.passes[int(rng.integers(len(C.passes)))]
                if not P['arms'] or max(a[1] for a in P['arms']) < 4.0:
                    raise ValueError('short arm')
                arms = [a for a in P['arms'] if a[1] >= 4.0] + [a for a in P['arms'] if a[1] < 4.0]
                if len(arms) == 2 and rng.random() < 0.5:
                    arms = arms[::-1]
                d, ln = arms[0]
                if ln < 4.0:
                    raise ValueError('short arm')
                lead = float(rng.uniform(2.5, 8.0))
                sp = float(rng.uniform(1.0, 1.3))
                h = min(ln - 1.0, 4.5)
                st = P['X'] + d * h
                if len(arms) == 2 and arms[1][1] >= 4.0:      # 4-way: cross to the other arm
                    en = P['X'] + arms[1][0] * min(arms[1][1] - 1.0, float(rng.uniform(3.0, 4.5)))
                else:                                         # T: cross the camera lane, stand at its far edge
                    en = P['X'] - d * (C.lat_person + 0.12) + P['din'] * float(rng.uniform(-1.0, 1.0))
                return C.person(nm, PathBuilder(st).wait_until(max(P['t'] - lead - h / sp - 0.6, 0.3)).leg([en], sp))
            lg = C.legs[int(rng.integers(len(C.legs)))]
            if lg['len'] < 7.0:
                raise ValueError('short leg')
            lat = C.plat()
            if kind == 'headon':
                st, en = lg['p1'] - lg['d'] * 1.0 + lg['n'] * lat, lg['p0'] + lg['d'] * 1.0 + lg['n'] * lat
                sp = float(rng.uniform(0.9, 1.2))
                t_meet = cam.t_at_s(lg['s0'] + float(rng.uniform(0.4, 0.7)) * lg['len'])
                dist_ = float(np.linalg.norm(cam.xy_at(t_meet) - st))
                return C.person(nm, PathBuilder(st).wait_until(max(t_meet - dist_ / (sp + 1.0) - 0.5, 0.3)).leg([en], sp))
            if kind == 'ahead':
                st = lg['p0'] + lg['d'] * float(rng.uniform(4.0, 7.0)) + lg['n'] * lat
                en = lg['p1'] - lg['d'] * 0.8 + lg['n'] * lat
                return C.person(nm, PathBuilder(st).wait_until(max(lg['t0'] - 1.0, 0.3)).leg([en], float(rng.uniform(0.4, 0.7))))
            p = lg['p0'] + lg['d'] * float(rng.uniform(0.2, 0.8)) * lg['len'] + lg['n'] * (lat + 0.12 * np.sign(lat))
            return C.person(nm, PathBuilder(p).wait(dur))

        C.try_(f'{nm} {kind}', 1, walker, static_tol=-0.1)

    def end_cross():
        end = np.asarray(tour['wps'][-1], float)
        d = tour['end_dir']
        n = np.array([-d[1], d[0]])
        X = end + d * float(rng.uniform(2.5, 4.0))
        lat = C.lat_person
        sgn = 1 if rng.random() < 0.5 else -1
        st, en = X + n * lat * sgn, X - n * lat * sgn
        return C.person('P99', PathBuilder(st).wait_until(body.t_end + float(rng.uniform(-1.0, 0.5))).leg([en], 0.9))

    C.try_('P99 across the final hover', 1, end_cross, static_tol=-0.1)

    # ------------------------------------------------------------------ L3 extras (after L1/L2: lower priority)
    def alongside():
        f = float(rng.uniform(fa_end + 0.02, fb_start - 0.04))
        lg = C.leg_at(f)
        if lg['len'] < 9.0:
            raise ValueError('short leg')
        t0, t1 = lg['t0'] + 0.5, lg['t1'] - 1.5
        lat = C.lat_fork * (1 if rng.random() < 0.5 else -1)
        ahead = float(rng.uniform(-0.8, 0.8))
        p_start = cam.follow_point(t0, ahead, lat)
        pb = PathBuilder(p_start).wait_until(t0).follow(cam, t1, ahead, lat, ahead_end=ahead - 1.5)
        stop = cam.follow_point(t1, ahead - 1.5, lat) + lg['d'] * 0.8
        return C.fork('Q3', pb.leg([stop], 0.6, ramp=0.0), 'pallet', round(float(rng.uniform(0.3, 0.8)), 2))

    C.try_('Q3 alongside', 3, alongside)
    for qn in ('Q4', 'Q5'):
        def loaded_cart(qn=qn):
            lg = C.legs[int(rng.integers(len(C.legs)))]
            if lg['len'] < 9.0:
                raise ValueError('short leg')
            lat = C.lat_person * (1 if rng.random() < 0.5 else -1)
            st = lg['p0'] + lg['d'] * float(rng.uniform(3.0, 6.0)) + lg['n'] * lat
            en = lg['p1'] - lg['d'] * 1.2 + lg['n'] * lat
            pb = PathBuilder(st - lg['d'] * 0.95).wait_until(max(lg['t0'] - 1.0, 0.1))
            return C.cart_pair(qn, pb.leg([en - lg['d'] * 0.95], float(rng.uniform(0.6, 0.8))), 0.7)
        C.try_(f'{qn} loaded cart ahead', 3, loaded_cart)

    return C


# ============================================================================================== scene object
class ProceduralScene:
    """Module-like object for isaac/render_sequence.py (NAME, TRAJ, SEED, PLAN_BOX, camera_cfg(), build())."""

    def __init__(self, name, site, seed):
        self.NAME, self.TRAJ, self.SEED, self.SITE = name, TRAJ, int(seed), site
        S = SITES[site]
        self.PLAN_BOX = S['plan_box']
        self.layout = Layout(site, seed)
        self._cfg, self.tour = camera_tour(self.layout, seed)
        self._choreo = None

    def camera_cfg(self):
        return dict(self._cfg)

    def choreo(self, cam, body):
        if self._choreo is None:
            self._choreo = make_actors(self.layout, cam, body, self.tour, self.SEED)
        return self._choreo

    def build(self, level, cam, duration):
        L = self.layout
        S = SITES[self.SITE]
        C = self.choreo(cam, cam.body)
        people = [a for a, tier, _ in C.acc if tier <= level and isinstance(a, Person)]
        forks = [a for a, tier, _ in C.acc if tier <= level and isinstance(a, Forklift)]
        return Scene(self.NAME, S['env'], S['classes'], list(S['hide']), list(L.props), list(L.rails),
                     list(L.windows), people, list(L.parked) + forks, env_label_mode=S['mode'])

    def summary(self, cam, body):
        C = self.choreo(cam, body)
        L = self.layout
        return dict(name=self.NAME, site=self.SITE, seed=self.SEED, env=SITES[self.SITE]['env'], lane_w=L.w,
                    x_lanes=L.xl, y_lanes=L.yl, blocks=len(L.blocks), props=len(L.props), rails=len(L.rails),
                    parked=len(L.parked), path_m=round(float(cam.L), 1), duration_s=round(float(body.duration), 2),
                    actors={lvl: sum(1 for _, t, _ in C.acc if t == lvl) for lvl in (1, 2, 3)}, log=C.log)


_CACHE = {}


def get(arg):
    """'fw01' (frozen t3 trajectory) or 'dev-<site>-<seed>' (generator development seeds; never t3 seeds)."""
    if arg in _CACHE:
        return _CACHE[arg]
    if arg in TRAJECTORIES:
        site, seed = TRAJECTORIES[arg]
        sc = ProceduralScene(arg, site, seed)
    elif arg.startswith('dev-'):
        _, site, seed = arg.split('-')
        assert int(seed) not in [s for _, s in TRAJECTORIES.values()], 'dev seeds must not be t3 seeds'
        sc = ProceduralScene(f'dev{site}{seed}', site, int(seed))
        sc.TRAJ = 'dev'
    else:
        raise KeyError(arg)
    _CACHE[arg] = sc
    return sc


def plan_numpy(arg):
    """Numpy-only plan check (no Isaac): body, cam, scene at L3, summary."""
    sc = get(arg)
    body = BodyTrajectory(sc.camera_cfg())
    cam = CamRef(body)
    scene = sc.build(3, cam, body.duration)
    return sc, body, cam, scene, sc.summary(cam, body)
