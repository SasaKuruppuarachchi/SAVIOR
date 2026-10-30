# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene C "dock" layout (new in the held-out split): the south hall of full_warehouse turned into a block-stacking
store with NARROW lanes (3 m) between pallet blocks, blind intersections and a staging strip in front of the rack
rows with parked forklifts carrying boxes on raised forks. Only the static layout lives here; trajectories and
actors are in dock_t<k>.py.

Lanes (centre lines, 3 m wide): east-west YA=4.0 (north lane, open to the staging strip y 5.5..8), YB=-6.0, YC=-16.0;
north-south XA=-19.5, XB=-9.0, XC=1.0. Blocks of pallet stacks (perimeter rows, mixed heights 1-3 layers, KLT pallets,
pallet piles, a few gaps) fill the rectangles between the lanes.
"""
from wh.scenario import Forklift, Prop, Rail
from . import full_warehouse as fw

YA, YB, YC = 4.0, -6.0, -16.0
XA, XB, XC = -19.5, -9.0, 1.0
PLAN_BOX = (-27.5, -24.5, 6.0, 10.0)
BLOCKS = {   # name: (x0, x1, y0, y1)
    'B11': (-25.8, -21.2, -4.3, 2.3), 'B12': (-17.8, -10.7, -4.3, 2.3), 'B13': (-7.3, -0.7, -4.3, 2.3),
    'B21': (-25.8, -21.2, -14.3, -7.7), 'B22': (-17.8, -10.7, -14.3, -7.7), 'B23': (-7.3, -0.7, -14.3, -7.7),
}
# perimeter slots left empty (x, y within 0.5 m): a forklift bay in B23's north face (E4 reverses out of it)
GAPS = [(-3.1, -8.1)]


def _stack(name, x, y, k, yaw=0.0):
    """Deterministic mix: KLT pallet, pallet pile, or a box stack of 1-3 layers."""
    if k % 6 == 4:
        return fw.klt_pallet(name, x, y, yaw)
    if k % 9 == 7:
        return fw.pallet_pile(name, x, y, 3 + k % 3, yaw)
    return fw.pallet_stack(name, x, y, yaw, 1 + (k * 7) % 3, kind=(k // 2) % 2)


def block(name, x0, x1, y0, y1, k0=0):
    """Perimeter of a block: rows of yaw-0 pallets (1.22 x 0.8 m) along the north/south faces at a 1.4 m pitch,
    columns along the west/east faces at a 1.0 m pitch."""
    props, k = [], k0
    nx = int((x1 - x0 - 1.22) // 1.4) + 1
    xs = [x0 + 0.61 + i * (x1 - x0 - 1.22) / max(nx - 1, 1) for i in range(nx)]
    ny = int((y1 - y0 - 0.8) // 1.0) + 1
    ys = [y0 + 0.4 + i * (y1 - y0 - 0.8) / max(ny - 1, 1) for i in range(ny)]
    slots = [(x, ys[-1]) for x in xs] + [(x, ys[0]) for x in xs] + \
        [(xs[0], y) for y in ys[1:-1]] + [(xs[-1], y) for y in ys[1:-1]]
    for i, (x, y) in enumerate(slots):
        if any(abs(x - gx) < 0.5 and abs(y - gy) < 0.5 for gx, gy in GAPS):
            continue
        props += _stack(f'{name}_{i}', round(x, 3), round(y, 3), k)
        k += 1
    return props, k


def static_layout():
    props, k = [], 0
    for name, (x0, x1, y0, y1) in BLOCKS.items():
        p, k = block(name, x0, x1, y0, y1, k)
        props += p
    for i, x in enumerate([-17.2 + 1.4 * j for j in range(12)]):      # south face of lane YC: one row
        if i % 4 != 3:
            props += _stack(f'sR_{i}', round(x, 3), -18.0, k)
            k += 1
    for i, y in enumerate([-13.5 + 1.45 * j for j in range(11)]):     # east strip, along the east wall
        if i % 3 != 1:
            props += _stack(f'eS_{i}', 4.1, round(y, 3), k, 90.0)
            k += 1
    # staging strip in front of the rack rows (y 6..8)
    props += fw.klt_pallet('stK1', -16.4, 7.2, 0.0) + fw.klt_pallet('stK2', -7.0, 7.1, 0.0)
    props += fw.pallet_pile('stP1', -11.8, 7.3, 4) + fw.pallet_stack('stS1', -25.0, 7.2, 0.0, 3)
    props += [Prop('dolly1', fw.DOLLY, (-13.6, 7.3, 0.0), 5.0, 'trolley'),
              Prop('dolly2', fw.DOLLY, (-0.8, -17.2, 0.0), 80.0, 'trolley'),
              Prop('barrel1', fw.BARREL, (4.4, 3.2, 0.0), 0.0, None), Prop('barrel2', fw.BARREL, (-25.9, -16.8, 0.0), 0.0, None),
              Prop('cone1', fw.CONE, (-7.45, -4.45, 0.0), 0.0, None), Prop('cone2', fw.CONE, (-0.4, -7.5, 0.0), 0.0, None),
              Prop('cone3', fw.CONE, (-10.5, -7.5, 0.0), 0.0, None)]
    rails = fw.rack_end_rails(fw.RACK_X, 8.15)
    rails += [Rail('rS_w', (-26.2, -19.0), (-21.0, -19.0)), Rail('rE_n', (4.9, 4.2), (4.9, 7.6))]
    parked = [Forklift('PF1', None, (-22.0, 7.4, 0.0), None, 'boxes', 1.1),      # boxes on raised forks
              Forklift('PF2', None, (-4.2, 6.8, 0.0), None, 'boxes', 0.6),
              Forklift('PF3', None, (-6.5, -20.6, 0.0), None, 'pallet', 0.0),
              Forklift('PF4', None, (-24.6, -20.6, 0.0), None, 'boxes', 0.35)]
    return props, rails, fw.windows_default(), parked
