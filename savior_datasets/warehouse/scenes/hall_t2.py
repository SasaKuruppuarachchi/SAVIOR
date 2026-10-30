# SPDX-License-Identifier: GPL-3.0-or-later
"""HELD-OUT scene B trajectory t2 ("hall", test split): same environment and static layout as hall t1, new camera
path, speeds, altitude profile, actors and IMU seed.

Camera (~90 m): take-off on the staging lane y=2.6 facing west (0.9 m/s), south through the island gap x=-11
(1.25 m/s, descending to 1.0 m), east along lane S (0.75 m/s), north along lane E (1.1 m/s, climbing), west along
the south half of the middle lane y=-8 (1.3 m/s, 2.0 m high), north on lane W (0.8 m/s) and east to x=-15 (0.7 m/s).
Levels (nested):
  L1 people: one standing against a staging stack for the whole sequence; one crossing the view during the hover
     (moving during the static init) who then stands; one walking ahead through the gap who then stands; head-on and
     walking-ahead people on lanes N / S / E / W; one standing at a rail for ~60 s who walks off when the camera comes;
     one brushing past the north-island stacks
  L2 + forklifts (drivers, boxes): one parked in view during the hover that drives off at take-off (t=3.0 s) across
     the camera lane 9 m ahead and through the gap (perpendicular, onset during init); one parked with an idle
     driver that starts when the camera is ~10 m away and passes it head-on in lane S; one leading 7 m ahead and
     1.6 m to the side in lane S that then drives parallel 2.3 m to the side up lane E; one parked on the middle
     lane that leads the camera 7 -> 10 m ahead along the middle lane and lane W; one head-on on the middle lane;
     one starting next to the camera on its final leg and overtaking it 2.3 m to its side
  L3 + co-moving: a forklift parked 4.5 m ahead during the hover that starts 0.4 s after take-off and leads 4.5 m
     ahead through the gap; one leading 5.5 m -> 3.0 m ahead along lane S, 3.0 m up lane E, 3-4 m along the middle
     lane and lane W (0.75-1.3 m/s) that finally stops in front of the camera during its end hover; one starting as
     the camera turns into the middle lane and driving alongside 1.6 m to its right, slower than the camera
"""
from wh.scenario import Forklift, PathBuilder, Person, Scene
from . import full_warehouse as fw
from . import hall as base

NAME, TRAJ, SEED = 'hall', 't2', 2213
PLAN_BOX = base.PLAN_BOX
YL, GX, YS, XE, YM, XW = 2.6, -11.0, -19.2, 0.7, -8.0, -21.3
WPS = [[-2.0, YL], [GX, YL], [GX, YS], [0.6, YS], [XE, -8.3], [-21.0, YM], [XW, 0.5], [-15.0, 0.8]]


# Held-out hard cases per level (cumulative), see scenes/aisles_t2.py.
HARD_CASES = {
    0: {'d': 'parked forklifts (PF2 with boxes, PF1 pallet, PF3 empty) and pallet / box / KLT stacks'},
    1: {'b': 'H12 starts walking 3 m ahead of the camera at t=3.3 s (just after take-off)',
        'c': 'H1 against a staging stack (whole sequence, in view during the hover), H6 at a rail for ~70 s; '
             'H2/H3/H4/H5/H8/H12 stand after walking',
        'd': 'H1 touches stack st1, H9 brushes the north-island stacks, H6 stands at a rail',
        'f': 'H2 perpendicular; H8 head-on; H3/H4/H5/H12 same direction',
        'hover_motion': 'H2 walks across the view DURING the 3 s hover (static initialisation window)'},
    2: {'a': 'K5 leads 7 -> 10 m ahead (middle lane, lane W); K9 leads 7 m ahead 1.6 m to the side (lane S)',
        'b': 'K1 parked in view during the hover drives off at take-off (t=3.0 s) and crosses the camera lane',
        'e': 'every L2/L3 forklift has a seated driver and boxes or a pallet on the forks',
        'f': 'K1 perpendicular; K2/K10 head-on; K9 parallel 2.3 m to the side in lane E; K11 parallel 2.3 m to the side, overtaking, on the final leg',
        'late_onset': 'K2 idle until the camera is ~10 m away'},
    3: {'a': 'K8 leads 4.5 m ahead from take-off; K6 leads 5.5 -> 3.0 m (lane S, 0.75 m/s), 3.0 m (lane E, 1.1 m/s), '
             '3 -> 4 m (middle lane, 1.3 m/s, camera 2 m high), 4 m (lane W) and stops in front of the camera during '
             'the final hover; K7 alongside 1.6 m to the side, slower than the camera (t1: 3.7 m at 1.0 m/s)',
        'b': 'K8 parked 4.5 m ahead during the hover starts 0.4 s after take-off (t=3.4 s)'},
}

def camera_cfg():
    return dict(waypoints=WPS, seg_speeds=[0.9, 1.25, 0.75, 1.1, 1.3, 0.8, 0.7],
                wp_heights=[1.3, 1.2, 1.0, 1.5, 2.0, 1.6, 1.2, 1.3], height_smooth_s=1.5,
                speed=1.0, height=1.4, height_amp=0.12, yaw_amp_deg=14.0, seed=SEED, platform='drone',
                hover_start_s=3.0, hover_end_s=2.0, yaw_rate_max_deg=100.0, ramp_s=1.0)


def static_layout():
    return base.static_layout()


def build(level, cam, duration):
    props, rails, windows, parked = static_layout()
    people, forks = [], []
    T = cam.t_near

    def person(name, ch, pb, active=None):
        people.append(Person(name, ch, pb.build(duration, sigma=0.25), active=active))

    def fork(name, driver, pb, load='boxes', lift=0.25, active=None):
        forks.append(Forklift(name, pb.build(duration, sigma=0.45), (0, 0, 0), driver, load, lift, active=active))

    t_gap = T((GX, -8.0))
    t_mid = T((-11.0, YM), t_min=50)
    if level >= 1:
        # H1 stands against the south face of staging stack st1 for the whole sequence (in view at take-off)
        person('H1', 'male_adult_police_04', PathBuilder((-9.2, 5.05)).wait(duration))
        # H2 walks across the camera lane DURING the hover (t=0-4 s, south -> north, 7.5 m ahead), then stands
        person('H2', 'F_Business_02', PathBuilder((-9.5, -0.4)).leg([(-9.5, 3.6), (-8.4, 4.3)], 1.1))
        # H3 walks south through the gap ahead of the camera (1.4 m left, overtaken), then stands there
        pb = PathBuilder((GX + 1.4, -2.2)).wait_until(T((-8.5, YL)))
        person('H3', 'male_adult_construction_03', pb.leg([(GX + 1.4, -12.4)], 0.8))
        # H4 walks east along lane S ahead of the camera (1.2 m to its right, 0.65 m/s), then stands
        pb = PathBuilder((-8.6, YS - 1.2)).wait_until(T((GX, -17.0)))
        person('H4', 'female_adult_police_01_new', pb.leg([(-3.0, YS - 1.2)], 0.65))
        # H12 walks west along the staging lane ahead of the camera from take-off (1.2 m to its left), then stands
        pb = PathBuilder((-4.6, YL - 1.2)).wait_until(3.3)
        person('H12', 'male_adult_construction_01_new', pb.leg([(-9.4, YL - 1.2)], 0.8))
        # H5 walks north along lane E ahead of the camera (1.4 m left, overtaken), then stands
        pb = PathBuilder((XE - 1.4, -15.5)).wait_until(T((-3.0, YS)))
        person('H5', 'F_Medical_01', pb.leg([(XE - 1.4, -11.0)], 0.85))
        # H6 stands at the north rail of the middle lane for ~70 s, walks off west ahead of the camera when it comes
        pb = PathBuilder((-15.0, -5.2)).wait_until(t_mid - 3.0)
        person('H6', 'male_adult_construction_05_new', pb.leg([(-19.8, -5.3)], 1.0))
        # H8 walks south along lane W, head-on (1.4 m left of the camera)
        tm = T((XW, -3.0), t_min=60)
        pb = PathBuilder((XW - 1.4, 2.5)).wait_until(tm - 5.5 / 1.0 - 0.8)
        person('H8', 'M_Medical_01', pb.leg([(XW - 1.4, -5.8)], 1.0))
        # H9 walks east along the north face of the north-island stacks (brushing them), ahead of the camera
        pb = PathBuilder((-19.6, -2.75)).wait_until(T((XW, -1.5), t_min=60))
        person('H9', 'female_adult_police_03_new', pb.leg([(-13.0, -2.75), (-12.0, -1.0)], 0.7))
    if level >= 2:
        # K1 parked in the staging area facing south (driver seated) in view during the hover; drives off at
        # t=3.0 s (take-off, 1.6 then 1.25 m/s), crosses the camera lane 9 m ahead, goes through the gap and west along the middle lane
        pb = PathBuilder((GX, 4.6)).wait_until(3.0)
        fork('K1', 'male_adult_construction_01_new',
             pb.leg([(GX, -1.0)], 1.6, stop=False).leg([(GX, -7.0), (-24.4, -7.0)], 1.25, ramp=0.5,
                    corner_radius=1.6), 'boxes', 0.3)
        # K2 parked with an idle driver at the east end of lane S; starts when the camera is ~10 m away and drives
        # west, passing it head-on 2.4 m to its right
        tst = T((-9.0, YS))
        pb = PathBuilder((2.8, YS - 2.4)).wait_until(tst)
        fork('K2', 'female_adult_police_02', pb.leg([(-21.5, YS - 2.4)], 1.4), 'boxes', 0.35)
        # K5 waits on the middle lane (driver seated), leads the camera 7 -> 10 m ahead along it, turns north on lane W
        # ahead of it and parks at the west wall
        ts, te = T((XE, -10.5), t_min=40), T((-15.0, YM), t_min=50)
        pb = PathBuilder(cam.follow_point(ts, 7.0)).wait_until(ts).follow(cam, te, 7.0, ahead_end=10.0)
        fork('K5', 'male_adult_police_04', pb.leg([(XW, 3.6), (-24.6, 3.6)], 1.1, ramp=0.0, corner_radius=1.3),
             'boxes', 0.25)
        # K9 drives east along lane S 7 m ahead of the camera, 1.6 m to its left (parallel), turns north east of
        # lane E (2.3 m to the camera's right) and parks there
        ts = T((GX, -17.0))
        pb = PathBuilder((-4.0, YS + 1.6)).wait_until(ts).leg([(3.1, YS + 1.6), (3.1, -4.6)], 0.8, corner_radius=1.6)
        fork('K9', 'male_adult_construction_03', pb, 'boxes', 0.5)
        # K10 drives east on the south side of the middle lane, passing the camera head-on 1.6 m to its left
        tm = T((-9.0, YM), t_min=50)
        pb = PathBuilder((-20.4, YM - 1.6)).wait_until(tm - 11.4 / 1.3 - 1.0)
        fork('K10', 'female_adult_police_01_new', pb.leg([(-1.5, YM - 1.6)], 1.3), 'pallet', 0.2)
        # K11 (L2 coverage fix) waits (driver seated) at the west end of the staging area; starts as the camera
        # comes on its final eastward leg and drives east parallel to it, 2.3 m to its left, slowly pulling ahead
        # (0.85 vs 0.7 m/s)
        ts = T((-19.0, 0.6), t_min=95)
        pb = PathBuilder((-16.8, 3.0)).wait_until(ts)
        fork('K11', 'M_Medical_01', pb.leg([(-7.5, 3.0)], 0.85), 'boxes', 0.4)
    if level >= 3:
        # K8 parked 4.5 m ahead (driver, boxes) during the hover, starts 0.4 s after take-off and leads the camera
        # 4.5 m ahead through the gap; turns west before lane S and parks
        ts, te = 3.4, T((GX, -11.0))
        pb = PathBuilder(cam.follow_point(0.0, 4.5)).wait_until(ts).follow(cam, te, 4.5)
        fork('K8', 'female_adult_police_03_new', pb.leg([(GX, -17.7), (-18.5, -17.9)], 1.6, ramp=0.0, corner_radius=1.4),
             'boxes', 0.3)
        # K6 waits in lane S; leads the camera 5.5 m -> 3.0 m ahead along lane S, 3.0 m up lane E, 3.0 -> 4.0 m
        # along the middle lane and 4.0 m up lane W (0.75-1.3 m/s), then drives on east and stops in front of the
        # camera during its final hover
        ts = T((GX, -17.5))
        t1, t2, t3 = T((0.6, YS)), T((XE, -9.5), t_min=40), T((-15.0, YM), t_min=50)
        t4 = T((XW, -1.0), t_min=60)
        pb = PathBuilder(cam.follow_point(ts, 5.5)).wait_until(ts).follow(cam, t1, 5.5, ahead_end=3.0)
        pb.follow(cam, t2, 3.0).follow(cam, t3, 3.0, ahead_end=4.0).follow(cam, t4, 4.0)
        fork('K6', 'male_adult_construction_03', pb.leg([(-12.3, 0.8)], 1.0, ramp=0.0), 'pallet', 0.1,
             active=(12.0, 1e9))
        # K7 waits at the east end of the middle lane, starts as the camera turns in and drives alongside it 1.7 m
        # to its right (north), slower (1.15 m/s)
        tst = T((XE, -10.0), t_min=40)
        pb = PathBuilder((-2.2, YM + 1.6)).wait_until(tst)
        fork('K7', 'F_Medical_01', pb.leg([(-17.0, YM + 1.6)], 1.15), 'boxes', 0.25)
    return Scene(NAME, fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, parked + forks)
