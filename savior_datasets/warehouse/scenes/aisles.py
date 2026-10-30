# SPDX-License-Identifier: GPL-3.0-or-later
"""Scene A "aisles": the rack aisles of full_warehouse (paper scenario 4 spirit: objects crossing the camera path).

Camera: starts in the hall, flies up aisle x=-12.9, west along the north cross aisle, down aisle x=-17.9, east
along the south cross aisle and up aisle x=-7.9 (~89 m, ~105 s, 1 m/s cruise, 1.4 m +- 0.25 m height).
Levels (nested: every level contains the actors of the lower ones):
  L0 static: env racks/boxes/pallets + parked driverless forklifts, pallets, boxes, KLT bins, trolleys, rails, windows
  L1 + people crossing in front of the camera / walking head-on in the aisles, one standing still
  L2 + forklifts driven by people, carrying pallets with boxes: crossing the hall and both cross aisles, one
       overtaking in parallel along the south cross aisle
  L3 + co-moving: a forklift driving 4 m ahead of the camera up both long aisles, one alongside in the hall,
       a person walking ahead down aisle -17.9, a person alongside in the cross aisle, more crossings
"""
import numpy as np

from wh.scenario import Forklift, PathBuilder, Person, Prop, Rail, Scene, crossing
from . import full_warehouse as fw

NAME, TRAJ, SEED = 'aisles', 't1', 101
PLAN_BOX = (-27.5, -6.0, 6.0, 31.0)
X1, X2, X3 = -12.9, -17.9, -7.9           # aisles used by the camera
YN, YS, YH = 27.6, 5.8, 3.0                # north cross aisle, south cross aisle, hall lane


def camera_cfg():
    return dict(waypoints=[[-21.5, YH], [X1, YH], [X1, YN], [X2, YN], [X2, YS], [X3, YS], [X3, 25.0]],
                speed=1.0, height=1.4, height_amp=0.25, yaw_amp_deg=12.0, seed=SEED, platform='drone',
                hover_start_s=3.0, hover_end_s=2.0, yaw_rate_max_deg=100.0, ramp_s=1.0)


def static_layout():
    props = []
    props += fw.pallet_stack('stackA', -24.6, -1.2, 0.0, 3)
    props += fw.pallet_stack('stackB', -23.2, -1.2, 0.0, 2, kind=1)
    props += fw.pallet_pile('pileA', -21.8, -1.3, 5)
    props += fw.klt_pallet('kltA', -20.4, -1.2)
    props += fw.pallet_stack('stackC', -9.0, -1.5, 90.0, 3)
    props += fw.pallet_stack('stackD', -9.0, -3.0, 90.0, 2, kind=1)
    props += fw.klt_pallet('kltB', -3.5, 1.4, 90.0)
    props += fw.pallet_stack('stackE', -20.4, 29.85, 0.0, 3)
    props += fw.pallet_pile('pileB', -4.0, 29.85, 4, 0.0)
    props += [Prop('dolly1', fw.DOLLY, (-12.0, -2.6, 0.0), 15.0, 'trolley'),
              Prop('dolly2', fw.DOLLY, (4.0, 26.3, 0.0), 80.0, 'trolley'),
              Prop('barrel1', fw.BARREL, (-3.0, -3.0, 0.0), 0.0, None),
              Prop('barrel2', fw.BARREL, (-2.2, -3.3, 0.0), 30.0, None),
              Prop('cone1', fw.CONE, (-21.5, 4.6, 0.0), 0.0, None),
              Prop('cone2', fw.CONE, (-24.0, 4.8, 0.0), 0.0, None)]
    rails = fw.rack_end_rails(fw.RACK_X[:6], 8.15) + fw.rack_end_rails(fw.RACK_X[1:4], 25.85, 'rail_n')
    rails += [Rail('rail_walk', (-25.6, -4.0), (-25.6, 2.2), 1.0), Rail('rail_hall', (-12.0, -4.6), (-4.0, -4.6), 1.0)]
    parked = [Forklift('PF1', None, (-24.0, -3.4, 90.0), None, 'pallet', 0.0),
              Forklift('PF2', None, (-6.0, 0.2, 0.0), None, 'boxes', 0.05),
              Forklift('PF3', None, (-22.9, 18.0, -90.0), None, 'none', 0.0)]
    return props, rails, fw.windows_default(), parked


def build(level, cam, duration):
    """Choreography (camera time line, see the module doc): every actor waits at a free spot (or is hidden while it
    cannot be seen) and starts relative to the camera passage."""
    props, rails, windows, parked = static_layout()
    people, forks = [], []
    T = cam.t_near

    def person(name, ch, pb, active=None):
        people.append(Person(name, ch, pb.build(duration, sigma=0.25), active=active))

    def fork(name, driver, pb, load='boxes', lift=0.25, active=None):
        forks.append(Forklift(name, pb.build(duration, sigma=0.45), (0, 0, 0), driver, load, lift, active=active))

    t_x1n = T((X1, 21.5))                       # camera in aisle X1, 6 m before its north end
    t_x3 = T((X3, 11.0), t_min=60)
    if level >= 1:
        # P1 crosses the hall lane 2.5 s ahead of the camera (north -> south) and stops near the pallets
        a, b, t0 = crossing(cam, cam.s_at(T((-16.6, YH))), 2.5, 4.0, 1.2, side=+1)
        person('P1', 'male_adult_construction_01_new',
               PathBuilder((-16.6, 7.0)).wait_until(t0).leg([(-16.6, 0.5), (-13.6, -3.4)], 1.2))
        # P2 walks south down aisle X1 towards the camera (1.5 m to its right), then east along the cross aisle
        tm = T((X1, 17.0))
        pb = PathBuilder((X1 + 1.65, 25.0)).wait_until(tm - 8.0 / 1.15 - 0.8)
        person('P2', 'female_adult_police_02', pb.leg([(X1 + 1.65, 9.3), (X1 + 1.65, 7.3), (-2.0, 7.4)], 1.15))
        # P3 walks east along the north cross aisle, meets the camera head-on (1.3 m to its left)
        tm = T((-17.0, YN))
        pb = PathBuilder((-25.6, YN + 1.2)).wait_until(tm - 8.6 / 1.1 - 0.8)
        person('P3', 'male_adult_construction_03', pb.leg([(-11.8, YN + 1.2)], 1.1))
        # P4 crosses the south cross aisle 3 s ahead of the camera (hall -> aisle X1)
        tm = T((-12.3, YS), t_min=60) - 3.0
        pb = PathBuilder((-12.3, -0.5)).wait_until(tm - 6.3 / 1.1 - 0.8)
        person('P4', 'F_Business_02', pb.leg([(-12.3, 12.5)], 1.1))
        # P5 stands still (idle) in aisle X3: a person that is NOT moving
        person('P5', 'M_Medical_01', PathBuilder((X3 - 1.55, 17.5)).wait(duration))
        # P6 walks down aisle X3 before the camera gets there, then east along the cross aisle (seen walking away)
        pb = PathBuilder((X3 + 1.3, 26.0)).wait_until(T((-15.0, YN)) - 2.0)
        person('P6', 'female_adult_police_03_new', pb.leg([(X3 + 1.3, 7.0), (-2.5, 5.0)], 1.2))
        # P12..P15 walk ahead of the camera (same direction, slightly faster) -> long, coherent visibility
        pb = PathBuilder((-16.0, 3.4)).wait_until(1.5)
        person('P12', 'male_adult_police_04', pb.leg([(-12.1, 3.6), (-12.1, 6.0), (-12.1, 25.0), (-11.6, 25.6)], 1.05))
        pb = PathBuilder((-19.0, 26.0)).wait_until(T((-15.0, YN)))
        person('P13', 'F_Medical_01', pb.leg([(-19.0, 7.3), (-22.0, 7.6), (-22.9, 9.8)], 1.0))
        pb = PathBuilder((-13.6, 9.6)).wait_until(T((X2, 10.0)))
        person('P14', 'male_adult_construction_05_new', pb.leg([(-13.6, 6.8), (-5.0, 6.6)], 1.05), active=(58.0, 1e9))
        pb = PathBuilder((-8.9, 20.0)).wait_until(T((-9.0, YS), t_min=60))
        person('P15', 'female_adult_police_01_new', pb.leg([(-8.9, 23.0)], 0.8))
    if level >= 2:
        # F1 crosses the hall lane 4 s ahead of the camera (south -> north), parks west along the cross aisle
        a, b, t0 = crossing(cam, cam.s_at(T((-14.6, YH))), 4.0, 8.5, 1.6, side=-1)
        pb = PathBuilder((-14.6, -5.5)).wait_until(t0 - 0.3)
        fork('F1', 'male_adult_construction_05_new', pb.leg([(-14.6, 6.6), (-24.5, 6.6)], 1.6, corner_radius=1.5))
        # F2 crosses the north cross aisle (east -> west) ahead of the camera, parks in the westmost aisle
        tm = T((X1, YN)) - 8.5
        pb = PathBuilder((1.0, 28.0)).wait_until(tm - 13.9 / 1.8 - 1.0)
        fork('F2', 'male_adult_police_04', pb.leg([(-22.9, 28.0), (-22.9, 22.3)], 1.8, corner_radius=1.5))
        # F3 overtakes the camera on its right along the south cross aisle (parallel, 1.7 m/s)
        tm = T((X2, 9.0)) + 2.0
        pb = PathBuilder((-24.5, 3.4)).wait_until(tm)
        fork('F3', 'male_adult_construction_01_new', pb.leg([(1.5, 3.4)], 1.3), 'pallet', 0.1)
        # F9 leads the camera down aisle X2 at ~9 m (0.4 m left), then drives on into the hall and parks
        ts, te = T((X2, 25.5)), T((X2, 15.5))   # same start as F8 (L3), 4.6 m further ahead
        pb = PathBuilder(cam.follow_point(ts - 2.0, 8.3, 0.4)).wait_until(ts - 2.0).follow(cam, te, 8.3, 0.4)
        fork('F9', 'female_adult_police_02', pb.leg([(X2 + 0.4, 3.0), (-16.0, 0.5), (-16.0, -0.5)], 1.0, ramp=0.0,
                                                   corner_radius=1.5), active=(30.0, 1e9))
        # F7 leads the camera up aisle X3 at ~9 m (0.4 m right), turns east and parks in aisle -2.9
        s7 = cam.s_at(T((X3, 17.0), t_min=60))
        ts, te = cam.t_at_s(s7 - 11.0), T((X3, 15.0), t_min=60)
        pb = PathBuilder(cam.follow_point(ts, 11.0, -0.4)).wait_until(ts).follow(cam, te, 11.0, -0.4)
        fork('F7', 'male_adult_construction_03', pb.leg([(X3 + 0.4, 26.6), (-5.0, 28.0), (-2.9, 26.5), (-2.9, 22.0)], 1.0,
                                                       ramp=0.0, corner_radius=1.2), active=(62.0, 1e9))
    if level >= 3:
        # F6 alongside the camera in the hall (2.7 m to its right), then turns south and parks
        te = T((-19.8, YH))
        pb = PathBuilder(cam.follow_point(0.0, 0.8, -2.7)).follow(cam, te, 0.8, -2.7)
        fork('F6', 'male_adult_police_04', pb.leg([(-18.6, -0.6), (-18.6, -2.4)], 0.9, ramp=0.0), 'pallet', 0.1)
        # F4 waits in aisle X1, then drives ahead of the camera (4.3 m, 0.5 m left), turns east at the north end
        s_w = cam.s_at(T((X1, 12.0)))
        ts = cam.t_at_s(s_w - 8.0)
        tmid = cam.t_at_s(s_w - 2.0)
        pb = PathBuilder(cam.follow_point(ts, s_w - cam.s_at(ts), 0.5)).wait_until(ts)
        pb.follow(cam, tmid, s_w - cam.s_at(ts), 0.5, ahead_end=3.7).follow(cam, t_x1n, 3.7, 0.5)
        fork('F4', 'female_adult_police_01_new',
             pb.leg([(X1 - 0.5, 27.0), (-11.5, 28.0), (0.0, 28.0)], 1.2, ramp=0.0, corner_radius=1.2))
        # F5 appears in aisle X3 (out of sight), waits, then leads the camera (4.3 m, 0.4 m right) and turns east
        s_w = cam.s_at(t_x3)
        ts = cam.t_at_s(s_w - 8.0)
        tmid = cam.t_at_s(s_w - 2.0)
        te = T((X3, 21.0), t_min=60)
        pb = PathBuilder(cam.follow_point(ts, s_w - cam.s_at(ts), -0.4)).wait_until(ts)
        pb.follow(cam, tmid, s_w - cam.s_at(ts), -0.4, ahead_end=3.7).follow(cam, te, 3.7, -0.4)
        fork('F5', 'male_adult_construction_03',
             pb.leg([(X3 + 0.4, 26.8), (-6.0, 28.0), (-5.0, 28.0)], 1.0, ramp=0.0, corner_radius=1.0), active=(60.0, 1e9))
        # F8 drives 3.7 m ahead of the camera down aisle X2 (0.4 m left), turns west at the south end and parks
        ts, te = T((X2, 25.5)), T((X2, 14.5))
        pb = PathBuilder(cam.follow_point(ts - 2.0, 3.7, 0.4)).wait_until(ts - 2.0).follow(cam, te, 3.7, 0.4)
        fork('F8', 'male_adult_construction_05_new', pb.leg([(X2 + 0.4, 6.9), (-20.4, 6.9)], 1.4, ramp=0.0,
                                                           corner_radius=1.2), active=(30.0, 1e9))
        # P9 steps out of aisle X2 and walks alongside the camera (1.7 m left) along the cross aisle into aisle X1
        ts, te = T((X2, 7.5)), T((-11.9, YS), t_min=60)
        pb = PathBuilder((-15.3, 7.3)).wait_until(ts - 1.0).leg([cam.follow_point(ts, 0.5, 1.7)], 1.0, stop=False)
        person('P9', 'female_adult_police_01_new',
               pb.follow(cam, te, 0.5, 1.7).leg([(-11.5, 8.6), (-11.5, 9.6)], 1.0, ramp=0.0), active=(40.0, 1e9))
        # P10 picks at the rack in aisle X2 (standing, not moving)
        person('P10', 'male_adult_police_04', PathBuilder((X2 + 1.65, 15.0)).wait(duration))
    return Scene(NAME, fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, parked + forks)
