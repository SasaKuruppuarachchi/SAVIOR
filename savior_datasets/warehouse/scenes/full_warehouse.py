# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared pieces for scenes built on Isaac/Environments/Simple_Warehouse/full_warehouse.usd.

Geometry (world, metres): interior x in [-26.5, 5.3], y in [-23.5, 30.3]; floor z = 0.
North part: 7 rack rows along y (x centres -25.4, -20.4, -15.4, -10.4, -5.4, -0.4, 4.6; 1.1 m deep), y in
[8.6, 25.4]; aisle centres x = -22.9, -17.9, -12.9, -7.9, -2.9, 2.1 (3.9 m free); cross aisles y ~ 27.7 (north) and
the open hall south of y = 8.6 (30 x 31 m, empty in the original asset).
"""
from wh.scenario import Prop, Rail, Window

ENV = 'Isaac/Environments/Simple_Warehouse/full_warehouse.usd'
ENV_CLASSES = [
    (r'^SM_RackFrame|^SM_RackShelf|^SM_RackPile', 'rack'),
    (r'^SM_Rackshield', 'guard_rail'),
    (r'^SM_PaletteA', 'pallet'),
    (r'^Box_|^SM_CardBox|^Crate|^SM_CratePlastic', 'box'),
    (r'^forklift$', 'forklift'),
    (r'^SM_PushcartA', 'trolley'),
]
RACK_X = [-25.4, -20.4, -15.4, -10.4, -5.4, -0.4, 4.6]
AISLE_X = [-22.9, -17.9, -12.9, -7.9, -2.9, 2.1]
RACK_Y0, RACK_Y1 = 8.6, 25.4

PALLET = 'Isaac/Props/Pallet/pallet.usd'
KLT = 'Isaac/Props/KLT_Bin/small_KLT_visual.usd'
DOLLY = 'Isaac/Props/Dolly/dolly.usd'
P = 'Isaac/Environments/Simple_Warehouse/Props/'
BOXES = [P + 'SM_CardBoxA_01.usd', P + 'SM_CardBoxB_01.usd', P + 'SM_CardBoxC_01.usd', P + 'SM_CardBoxD_01.usd']
BARREL = P + 'SM_BarelPlastic_A_01.usd'
CONE = P + 'S_TrafficCone.usd'


def pallet_stack(name, x, y, yaw=0.0, layers=2, kind=0):
    """Floor pallet (1.22 x 0.8 m) with a block of cardboard boxes (each box is its own 'box' instance).
    kind 0: 0.5 m cubes (2 per layer); kind 1: 0.5 x 0.5 x 0.25 m boxes (2 per layer, twice as many layers)."""
    import math
    out = [Prop(f'{name}.pallet', PALLET, (x, y, 0.0), yaw, 'pallet')]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    usd, hz = (BOXES[1], 0.5) if kind == 0 else (BOXES[2], 0.25)
    nl = layers if kind == 0 else 2 * layers
    k = 0
    for iz in range(nl):
        for ix in (-0.3, 0.3):
            out.append(Prop(f'{name}.box{k}', usd, (x + c * ix, y + s * ix, 0.14 + hz * iz), yaw + 3.0 * (k % 3 - 1), 'box'))
            k += 1
    return out


def pallet_pile(name, x, y, n=4, yaw=0.0):
    return [Prop(f'{name}.{i}', PALLET, (x, y, 0.14 * i), yaw, 'pallet') for i in range(n)]


def klt_pallet(name, x, y, yaw=0.0):
    out = [Prop(f'{name}.pallet', PALLET, (x, y, 0.0), yaw, 'pallet')]
    import math
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    k = 0
    for iz in range(3):
        for ix in (-0.45, -0.15, 0.15, 0.45):
            for iy in (-0.22, 0.22):
                out.append(Prop(f'{name}.bin{k}', KLT, (x + c * ix - s * iy, y + s * ix + c * iy, 0.21 + 0.145 * iz),
                                yaw + 90, 'box'))
                k += 1
    return out


def rack_end_rails(rows, y, name='rail_end'):
    return [Rail(f'{name}{i}', (x - 0.6, y), (x + 0.6, y), 0.9) for i, x in enumerate(rows)]


def windows_default():
    """Windows (Office SM_Window_3m_A: 3 x 3 m, origin at its lower corner, spans +y at yaw 0) on the walls at 2.4 m;
    the asset has none and 'window' is a static class."""
    w = [Window(f'win_n{i}', (x + 1.5, 30.22, 2.4), 90.0) for i, x in enumerate((-21.0, -13.0, -5.0, 2.0))]
    w += [Window(f'win_w{i}', (-26.42, y - 1.5, 2.4), 0.0) for i, y in enumerate((-15.0, -5.0, 5.0, 16.0))]
    w += [Window(f'win_s{i}', (x - 1.5, -23.42, 2.4), -90.0) for i, x in enumerate((-18.0, -8.0, 0.0))]
    return w
