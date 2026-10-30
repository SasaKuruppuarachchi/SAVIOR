# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene B "hall": the (originally empty) south hall of full_warehouse, populated as a block-stacking / staging
area (paper scenario 5 spirit: objects moving parallel to the camera).

Layout: north island (pallet blocks, y -4.8..-2.2) and south island (y -17..-11), both split by a 4 m crossing gap at
x = -11; staging area north of lane N (parked forklifts, pallets, KLT bins) in front of the rack rows; rails around
the islands; windows on the walls.
Camera (clockwise loop, 1 m/s, 1.4 m +- 0.25 m): lane N east (y=0) -> lane E south (x=1) -> lane S west (y=-19)
-> lane W north (x=-22.5) -> middle lane east (y=-6.3); ~96 m, ~110 s.
Levels (nested):
  L0 static layout (+ parked driverless forklifts)
  L1 + people: walking ahead / head-on along the lanes, crossing through the gap, one standing
  L2 + forklifts with drivers and boxes: opposite-direction pass on lane N, gap crossing, a slow forklift overtaken
       on lane S, head-on pass on lane E
  L3 + co-moving: a forklift leading the camera 3.7 m ahead around the whole loop, forklifts driving alongside on
       lane N, lane W and the middle lane
"""
from wh.scenario import Forklift, PathBuilder, Person, Prop, Rail, Scene, crossing
from . import full_warehouse as fw

NAME, TRAJ, SEED = 'hall', 't1', 202
PLAN_BOX = (-27.5, -24.5, 6.0, 9.0)
YN, XE, YS, XW, YM = 0.0, 1.0, -19.0, -22.5, -6.3
GAP = -11.0


def camera_cfg():
    return dict(waypoints=[[-21.0, YN], [XE, YN], [XE, YS], [XW, YS], [XW, YM], [-4.0, YM]],
                speed=1.0, height=1.4, height_amp=0.25, yaw_amp_deg=12.0, seed=SEED, platform='drone',
                hover_start_s=3.0, hover_end_s=2.0, yaw_rate_max_deg=100.0, ramp_s=1.0)


def static_layout():
    props = []
    xs_w = [-18.4, -17.0, -15.6, -14.2]
    xs_e = [-7.8, -6.4, -5.0, -3.6]
    for i, x in enumerate(xs_w + xs_e):                      # north island: one row of blocks
        if i % 3 == 2:
            props += fw.klt_pallet(f'nI{i}', x, -3.5, 0.0)
        else:
            props += fw.pallet_stack(f'nI{i}', x, -3.5, 0.0, 2 + (i % 2), kind=i % 2)
    for r, y in enumerate((-12.0, -13.4, -15.6)):            # south island: three rows
        for i, x in enumerate(xs_w + xs_e):
            k = r * 8 + i
            if r == 2 and i % 2 == 0:
                props += fw.pallet_pile(f'sI{k}', x, y, 3 + i % 3)
            elif k % 5 == 3:
                props += fw.klt_pallet(f'sI{k}', x, y, 0.0)
            else:
                props += fw.pallet_stack(f'sI{k}', x, y, 0.0, 1 + (k % 3), kind=k % 2)
    for i, x in enumerate((-20.0, -9.2, -3.0)):              # staging area (north of lane N)
        props += fw.pallet_stack(f'st{i}', x, 6.0, 90.0, 2 + i % 2, kind=i % 2)
    props += fw.pallet_pile('stP', -14.5, 6.2, 5, 90.0) + fw.klt_pallet('stK', -12.6, 6.1, 90.0)
    props += [Prop('dolly1', fw.DOLLY, (-15.8, -16.4, 0.0), 10.0, 'trolley'),
              Prop('dolly2', fw.DOLLY, (-4.6, 6.3, 0.0), 95.0, 'trolley'),
              Prop('dolly3', fw.DOLLY, (-4.5, -11.0 - 0.0, 0.0), 0.0, 'trolley'),
              Prop('barrel1', fw.BARREL, (4.4, 3.8, 0.0), 0.0, None), Prop('barrel2', fw.BARREL, (4.4, 4.8, 0.0), 20.0, None),
              Prop('barrel3', fw.BARREL, (-25.8, -22.6, 0.0), 0.0, None), Prop('cone1', fw.CONE, (-12.9, -4.6, 0.0), 0.0, None),
              Prop('cone2', fw.CONE, (-9.1, -10.6, 0.0), 0.0, None)]
    props += fw.pallet_stack('swC', 4.4, -23.0, 0.0, 3) + fw.pallet_stack('swD', -25.4, -21.0, 90.0, 2, kind=1)
    rails = [Rail('rN_w', (-19.2, -4.9), (-13.4, -4.9)), Rail('rN_e', (-8.6, -4.9), (-2.8, -4.9)),
             Rail('rS_w', (-19.2, -10.8), (-13.4, -10.8)), Rail('rS_e', (-8.6, -10.8), (-2.8, -10.8)),
             Rail('rS_ws', (-19.4, -16.6), (-19.4, -11.0)), Rail('rS_es', (-2.6, -16.6), (-2.6, -11.0)),
             Rail('rWalk', (4.6, -18.0), (4.6, -2.0))]
    parked = [Forklift('PF1', None, (-17.6, 7.0, 90.0), None, 'pallet', 0.0),
              Forklift('PF2', None, (-7.0, 7.0, 90.0), None, 'boxes', 0.1),
              Forklift('PF3', None, (-14.8, -14.4, 0.0), None, 'none', 0.0)]
    return props, rails, fw.windows_default(), parked


def build(level, cam, duration):
    props, rails, windows, parked = static_layout()
    people, forks = [], []
    T = cam.t_near

    def person(name, ch, pb, active=None):
        people.append(Person(name, ch, pb.build(duration, sigma=0.25), active=active))

    def fork(name, driver, pb, load='boxes', lift=0.25, active=None):
        forks.append(Forklift(name, pb.build(duration, sigma=0.45), (0, 0, 0), driver, load, lift, active=active))

    if level >= 1:
        # Q1 walks ahead of the camera along lane N (1.4 m to its right), then into the staging area
        person('Q1', 'male_adult_construction_01_new',
               PathBuilder((-16.5, YN - 1.4)).wait_until(4.0).leg([(-0.4, YN - 1.6)], 1.1))
        # Q3 walks north along lane E towards the camera (1.6 m to its right)
        tm = T((XE, -9.0))
        pb = PathBuilder((XE - 2.2, -18.0)).wait_until(tm - 9.0 / 1.1 - 0.8)
        person('Q3', 'male_adult_construction_03', pb.leg([(XE - 2.2, 1.2), (-0.2, 3.2)], 1.1))
        # Q4 walks east along lane S towards the camera (1.4 m to its right)
        tm = T((-8.0, YS))
        pb = PathBuilder((-21.0, YS - 1.4)).wait_until(tm - 13.0 / 1.1 - 0.8)
        person('Q4', 'F_Business_02', pb.leg([(-0.2, YS - 1.4)], 1.1))
        # Q5 crosses the middle lane through the gap (south -> north), 7 s ahead of the camera
        a, b, t0 = crossing(cam, cam.s_at(T((GAP, YM), t_min=60)), 11.5, 3.0, 1.0, side=-1)
        person('Q5', 'M_Medical_01', PathBuilder((GAP - 1.4, -12.6)).wait_until(t0 - 3.9).leg([a, b, (GAP - 0.6, -1.6)], 1.0))
        # Q6 walks north ahead of the camera along lane W (1.5 m to its right)
        pb = PathBuilder((XW + 1.5, YS + 3.0)).wait_until(T((-16.0, YS)))
        person('Q6', 'female_adult_police_03_new', pb.leg([(XW + 1.5, -10.5)], 0.95))
        # Q8 / Q9 walk ahead of the camera along lane E (1.4 m right) and lane S (1.3 m left)
        pb = PathBuilder((XE - 1.4, -3.2)).wait_until(T((-1.0, YN)))
        person('Q8', 'F_Medical_01', pb.leg([(XE - 1.4, -15.0), (-1.8, -16.6)], 1.05))
        pb = PathBuilder((-3.0, YS + 1.3)).wait_until(T((XE, -16.0)))
        person('Q9', 'female_adult_police_01_new', pb.leg([(-20.0, YS + 1.3)], 1.05))
        # Q10 walks ahead of the camera along the middle lane (1.2 m right)
        pb = PathBuilder((-17.5, YM - 1.2)).wait_until(T((XW, -9.5), t_min=60))
        person('Q10', 'male_adult_construction_05_new', pb.leg([(-5.0, YM - 1.2)], 1.0))
        # Q7 stands in the staging area (not moving)
        person('Q7', 'male_adult_police_04', PathBuilder((-13.4, 5.6)).wait(duration))
    if level >= 2:
        # G1 drives west on the far lane of lane N (4 m left of the camera, opposite direction)
        tm = T((-9.0, YN))
        pb = PathBuilder((3.0, 4.0)).wait_until(tm - 12.0 / 1.5 - 1.0)
        fork('G1', 'male_adult_construction_05_new', pb.leg([(-24.0, 4.0)], 1.5))
        # G2 crosses all three east-west lanes through the gap (north -> south), parks in the south-island gap
        pb = PathBuilder((GAP + 1.4, 3.2)).wait_until(0.0)
        fork('G2', 'male_adult_police_04', pb.leg([(GAP + 1.4, -14.8)], 1.4))
        # G3 drives west slowly on the lane south of lane S (camera overtakes it)
        tm = T((-2.0, YS))
        pb = PathBuilder((3.0, YS - 2.6)).wait_until(tm - 5.0)
        fork('G3', 'female_adult_police_01_new', pb.leg([(-24.0, YS - 2.6)], 0.65), 'boxes', 0.35)
        # G8 leads the camera 8 m ahead around the loop (own driver + load), parks east of the north island
        te = T((-16.0, YM), t_min=60)
        pb = PathBuilder(cam.follow_point(0.0, 8.6)).follow(cam, te, 8.6)
        fork('G8', 'female_adult_police_03_new', pb.leg([(-2.0, YM), (-2.0, -2.6)], 1.3, ramp=0.0, corner_radius=1.2), 'boxes', 0.3)
        # G6 drives north along lane E (2.4 m left of the camera), head-on pass
        tm = T((XE, -8.0))
        pb = PathBuilder((XE + 2.4, -17.5)).wait_until(tm - 9.5 / 1.4 - 1.0)
        fork('G6', 'male_adult_construction_01_new', pb.leg([(XE + 2.4, -1.0)], 1.4), 'pallet', 0.1)
    if level >= 3:
        # H1 leads the camera 3.7 m ahead around the whole loop, leaves at the end
        te = T((-9.0, YM), t_min=60)
        pb = PathBuilder(cam.follow_point(0.0, 3.7)).follow(cam, te, 3.7)
        fork('H1', 'male_adult_construction_03', pb.leg([(2.0, YM)], 1.0, ramp=0.0))
        # H2 alongside on lane N (2.2 m left), then parks east of the staging area
        te = T((-4.0, YN))
        pb = PathBuilder(cam.follow_point(0.0, 0.3, 2.2)).follow(cam, te, 0.3, 2.2)
        fork('H2', 'F_Medical_01', pb.leg([(3.0, 2.2)], 1.0, ramp=0.0), 'boxes', 0.25)
        # H3 alongside on lane W (2.6 m left = west), from the south-west corner
        ts, te = T((XW, -16.5)), T((XW, -8.0))
        pb = PathBuilder(cam.follow_point(ts, 0.3, 2.6)).wait_until(ts).follow(cam, te, 0.3, 2.6)
        fork('H3', 'female_adult_police_02', pb.leg([(XW - 2.6, -3.0)], 1.0, ramp=0.0), 'pallet', 0.1, active=(40.0, 1e9))
        # H4 alongside on the middle lane (2.6 m right = south)
        ts, te = T((-20.0, YM), t_min=60), T((-6.5, YM), t_min=60)
        pb = PathBuilder(cam.follow_point(ts, 0.3, -2.6)).wait_until(ts).follow(cam, te, 0.3, -2.6)
        fork('H4', 'male_adult_construction_05_new', pb.leg([(0.5, YM - 2.6)], 1.0, ramp=0.0), 'boxes', 0.25,
             active=(60.0, 1e9))
    return Scene(NAME, fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, parked + forks)
