# SPDX-License-Identifier: GPL-3.0-or-later
"""HELD-OUT scene A trajectory t2 ("aisles", test split): same environment and static layout as aisles t1, plus a
few extra static props in the hall (pallet / KLT stacks that people touch, a parked forklift with boxes on raised
forks). New camera path, speeds, altitude profile, actors and IMU seed.

Camera (~80 m): take-off in the south cross aisle facing west, west along y=6.0 (0.8 m/s), up aisle x=-17.9
(1.3 m/s, climbing to 1.9 m), east along the north cross aisle (0.9 m/s), down aisle x=-7.9 (1.2 m/s, down to
1.2 m), diagonally south-west into the hall (0.7 m/s) and west along the hall lane y=2.5 (1.0 m/s).
Levels (nested):
  L1 people: one standing in view during the whole hover (static person), one starting to walk across the view at
     take-off, head-on / walking-ahead people in the aisles, a picker standing at a rack, people touching the hall
     stacks (one stands against a stack, one brushes past)
  L2 + forklifts (drivers, boxes): one parked 5.5 m ahead in the hover that drives off at t=4 s (motion onset during
     filter init) and leads at 6.5-8 m, one crossing the end of aisle -17.9 slowly while the camera flies towards
     it, one parked with a driver that never moves, one parked with
     an idle driver that starts driving away only when the camera is 6 m away, one leading 9.5 m ahead down aisle
     -7.9, a perpendicular crossing in the hall, a forklift starting next to the camera in the hall and pulling
     ahead 2.4 m to its side (C3; L3 until the L2 coverage fix, its path and the L3 actor order are unchanged),
     and (L2 ONLY, not in L3, where the closer C1 takes its place) a forklift leading 7 m ahead up aisle -17.9
     that turns off into aisle -12.9 (B11)
  L3 + co-moving: a forklift leading 5.0 m -> 2.8 m ahead up aisle -17.9 at 1.3 m/s and on along the cross aisle,
     (the same forklift) 4.2 m ahead down aisle -7.9
"""
from wh.scenario import Forklift, PathBuilder, Person, Prop, Scene, crossing
from . import aisles as base
from . import full_warehouse as fw

NAME, TRAJ, SEED = 'aisles', 't2', 1117
PLAN_BOX = base.PLAN_BOX
X2, X3, X1 = -17.9, -7.9, -12.9
YS, YN, YH = 6.0, 27.4, 2.5
WPS = [[-3.5, YS], [X2, YS], [X2, YN], [X3, YN], [X3, 9.0], [-10.5, YH], [-19.5, YH]]


# Held-out hard cases per level (cumulative: level k contains those of the lower levels); used by
# tools/make_heldout_manifest.py. Keys: a leading / co-moving forklift, b motion onset at / just after take-off,
# c standing / idle people, d parked loaded forklifts + stacks (touched by people from L1), e person -> forklift -> box
# chain, f perpendicular and parallel motion; extras: static_driver, late_onset, turn_in.
HARD_CASES = {
    0: {'d': 'parked forklifts with boxes on the forks (PF2 0.05 m, PF5 0.45 m, PF4 0.9 m raised), pallet / box / KLT '
             'stacks along the hall lane'},
    1: {'b': 'A2 stands in the camera lane 4 m ahead during the hover and walks out of it at t=3.3 s',
        'c': 'A1 (whole sequence, in view during the hover), A4 picker at a rack, A5 at a rail, A6 against a stack '
             'for ~85 s; A8/A9/A10/A11/A13 stand after walking',
        'd': 'A6 stands against stack hsA, A7 brushes past hsA/hsB/hsC (0-0.3 m)',
        'f': 'A2 perpendicular; A3/A10/A13 head-on and A7/A9/A11 same-direction (parallel)'},
    2: {'a': 'B1 leads 6.5-8 m ahead (south cross aisle), B7 leads 9.5 m ahead (aisle -7.9); B11 (L2 only, replaced '
             'by the closer C1 in L3) leads 7 m ahead up aisle -17.9',
        'b': 'B1 parked 6.5 m ahead with its driver during the hover, drives off at t=4.0 s (during filter init)',
        'c': 'B2: parked forklift whose seated driver never moves',
        'e': 'every L2/L3 forklift has a seated driver and a pallet with boxes (or a pallet) on the forks',
        'f': 'B3 perpendicular crossing, B9 slow perpendicular crossing at the aisle end; B1/B7 parallel; C3 starts '
             'as the camera arrives in the hall and drives parallel 2.4 m to its side, pulling ahead (1.5 vs 1.0 m/s)',
        'late_onset': 'B5 idle in an aisle mouth until the camera is 6 m away, then drives away'},
    3: {'a': 'C1 co-moves ahead: 5.0 -> 2.8 m at 1.3 m/s up aisle -17.9, 2.8 -> 4.2 m along the cross aisle, 4.2 m '
             'at 1.2 m/s down aisle -7.9 (t1: 3.7 m at 1.0 m/s)',
        'turn_in': 'C1 turns into the camera aisle from the side just ahead of the camera'},
}

def camera_cfg():
    return dict(waypoints=WPS, seg_speeds=[0.8, 1.3, 0.9, 1.2, 0.7, 1.0],
                wp_heights=[1.3, 1.3, 1.9, 1.9, 1.2, 1.1, 1.6], height_smooth_s=1.5,
                speed=1.0, height=1.4, height_amp=0.12, yaw_amp_deg=14.0, seed=SEED, platform='drone',
                hover_start_s=3.0, hover_end_s=2.0, yaw_rate_max_deg=100.0, ramp_s=1.0)


def static_layout():
    props, rails, windows, parked = base.static_layout()
    props = list(props)
    props += fw.pallet_stack('hsA', -15.0, 0.8, 0.0, 3)            # hall stacks the people touch / brush past
    props += fw.klt_pallet('hsB', -16.6, 0.8, 0.0)
    props += fw.pallet_stack('hsC', -21.0, 0.7, 0.0, 2, kind=1)
    parked = list(parked) + [Forklift('PF4', None, (-24.6, 2.0, 90.0), None, 'boxes', 0.9),   # boxes on raised forks
                             Forklift('PF5', None, (-5.0, 3.4, 180.0), None, 'boxes', 0.45)]
    return props, rails, windows, parked


def build(level, cam, duration):
    props, rails, windows, parked = static_layout()
    people, forks = [], []
    T = cam.t_near

    def person(name, ch, pb, active=None):
        people.append(Person(name, ch, pb.build(duration, sigma=0.25), active=active))

    def fork(name, driver, pb, load='boxes', lift=0.25, active=None):
        forks.append(Forklift(name, pb.build(duration, sigma=0.45), (0, 0, 0), driver, load, lift, active=active))

    t_x2n = T((X2, 25.0))
    if level >= 1:
        # A1 stands in the south cross aisle, in view during the whole hover (never moves)
        person('A1', 'male_adult_police_04', PathBuilder((-11.5, 7.4)).wait(duration))
        # A2 stands in the camera lane 4 m ahead during the hover and walks out of it at take-off (t=3.3 s)
        person('A2', 'F_Business_02', PathBuilder((-7.6, 5.6)).wait_until(3.3).leg([(-6.6, 7.4)], 0.9))
        # A3 walks south down aisle -17.9 head-on (1.35 m to the camera's left), then east along the cross aisle
        tm = T((X2, 18.0))
        pb = PathBuilder((X2 - 1.35, 26.0)).wait_until(tm - 8.0 / 1.1 - 0.8)
        person('A3', 'male_adult_construction_03', pb.leg([(X2 - 1.35, 7.6), (-13.5, 7.5)], 1.1))
        # A4 picks at the rack in aisle -17.9 (standing next to the rack, whole sequence)
        person('A4', 'F_Medical_01', PathBuilder((X2 + 1.5, 13.0)).wait(duration))
        # A9 walks up aisle -17.9 ahead of the camera (overtaken), stops next to A4 and stands there
        pb = PathBuilder((X2 + 1.35, 9.6)).wait_until(T((X2 + 4.0, YS)))
        person('A9', 'male_adult_construction_01_new', pb.leg([(X2 + 1.35, 11.9)], 0.9))
        # A10 walks west along the north cross aisle, head-on (1.35 m to the camera's left), then stands
        tm = T((-12.0, YN))
        pb = PathBuilder((-7.5, YN + 1.35)).wait_until(tm - 4.5 / 1.0 - 0.8)
        person('A10', 'female_adult_police_02', pb.leg([(-16.0, YN + 1.35)], 1.0))
        # A11 walks down aisle -7.9 ahead of the camera (1.35 m to its right, overtaken), stops near the aisle end
        pb = PathBuilder((X3 - 1.35, 25.0)).wait_until(T((-11.0, YN)))
        person('A11', 'F_Business_02', pb.leg([(X3 - 1.35, 10.5)], 0.8))
        # A13 walks east along the south cross aisle, head-on (1.3 m to the camera's left)
        tm = T((-12.0, YS))
        pb = PathBuilder((-19.5, YS - 1.3)).wait_until(tm - 7.5 / 1.1 - 0.8)
        person('A13', 'female_adult_police_03_new', pb.leg([(-9.6, YS - 1.3), (-9.0, 3.3)], 1.1))
        # A5 stands at the rack-end rail in the north cross aisle (touching it)
        person('A5', 'female_adult_police_03_new', PathBuilder((-15.4, 26.15)).wait(duration))
        # A6 stands against the east face of stack hsA (touching it) until the camera has passed, then walks off
        tw = T((-12.0, YH), t_min=60)
        person('A6', 'male_adult_construction_05_new',
               PathBuilder((-14.1, 0.8)).wait_until(tw + 6.0).leg([(-14.0, -1.0), (-13.8, -3.6)], 0.9))
        # A7 walks west along the hall stacks, brushing past them (0.0-0.3 m), ahead of the camera (overtaken)
        tm = T((-12.5, YH), t_min=60)
        pb = PathBuilder((-15.3, 1.5)).wait_until(tm - 1.0)
        person('A7', 'female_adult_police_01_new', pb.leg([(-21.8, 1.5), (-22.6, 0.3)], 0.75))
        # A8 walks up aisle -7.9 towards the camera before it gets there, then stands (1.35 m to its left)
        tm = T((X3, 20.0), t_min=40)
        pb = PathBuilder((X3 + 1.35, 9.5)).wait_until(tm - 10.0)
        person('A8', 'M_Medical_01', pb.leg([(X3 + 1.35, 17.0)], 1.0))
    if level >= 2:
        # B1 parked 6.5 m ahead (driver seated) during the hover; drives off at t=4.0 s (onset during init), leads
        # the camera west at 1.0 m/s (6.5-8 m ahead), turns north into aisle -12.9 and parks there
        pb = PathBuilder((-10.0, YS)).wait_until(4.0)
        fork('B1', 'male_adult_construction_01_new',
             pb.leg([(X1 + 0.1, YS), (X1 + 0.1, 15.0)], 1.0, corner_radius=1.6), 'boxes', 0.3)
        # B2 parked in the east part of the cross aisle with a seated driver who never moves
        fork('B2', 'female_adult_police_02', PathBuilder((-4.9, 28.9)).leg([(-5.0, 28.9)], 0.05).wait(duration),
             'boxes', 0.25)
        # B9 crosses the north end of aisle -17.9 slowly (east -> west, 0.6 m/s) while the camera flies up the
        # aisle towards it, and parks at the west end of the cross aisle
        pb = PathBuilder((-12.5, 28.9)).wait_until(T((X2, 9.0)) - 5.0)
        fork('B9', 'male_adult_construction_03', pb.leg([(-21.6, 28.9)], 0.6), 'pallet', 0.6)
        # B3 crosses the hall lane perpendicularly (south -> north) 9 s ahead of the camera, parks in aisle -17.9
        a, b, t0 = crossing(cam, cam.s_at(T((-18.3, YH), t_min=60)), 9.0, 5.0, 1.5, side=-1)
        pb = PathBuilder((-18.3, -3.0)).wait_until(t0)
        fork('B3', 'male_adult_police_04', pb.leg([(-18.3, 6.4), (X2, 8.0), (X2, 11.0)], 1.5, corner_radius=1.4),
             'pallet', 0.15)
        # B5 parked (idle driver) in the mouth of aisle -2.9, facing south; starts when the camera is ~6 m away
        # and drives down the aisle, away from the camera
        tst = T((-9.0, YN))
        pb = PathBuilder((-2.9, 26.3)).wait_until(tst)
        fork('B5', 'male_adult_construction_05_new', pb.leg([(-2.9, 17.5)], 1.0), 'boxes', 0.35)
        # B7 waits inside aisle -7.9 (out of sight), leads the camera down the aisle 9.5 m ahead, then parks east
        ts, te = T((-11.0, YN)), T((X3, 19.5))
        pb = PathBuilder(cam.follow_point(ts, 9.5)).wait_until(ts).follow(cam, te, 9.5)
        fork('B7', 'male_adult_police_04', pb.leg([(X3, 5.9), (0.8, 5.9)], 1.6, ramp=0.0, corner_radius=1.4),
             'boxes', 0.3)
    if level >= 3:
        # C1 turns into aisle -17.9 from the west just ahead of the camera and leads it: up aisle -17.9 5.0 m ahead at 1.3 m/s closing to 2.8 m, along the cross aisle
        # opening to 4.2 m, down aisle -7.9 at 4.2 m, then into the hall where it parks
        ts = T((X2 + 3.0, YS)) - 1.0
        te2, te3 = T((-10.0, YN)), T((X3, 13.0))
        pb = PathBuilder((-21.6, 6.6)).wait_until(ts - 3.5).leg([cam.follow_point(ts, 5.0)], 1.2, stop=False)
        pb.follow(cam, t_x2n, 5.0, ahead_end=2.8)
        pb.follow(cam, te2, 2.8, ahead_end=4.2).follow(cam, te3, 4.2)
        fork('C1', 'female_adult_police_03_new', pb.leg([(X3, 5.5), (-4.0, 5.5)], 1.2, ramp=0.0,
                                                       corner_radius=1.4), 'boxes', 0.3, active=(8.0, 1e9))
    if level >= 2:
        # (L2 coverage fix, after L3 was rendered: C3 is part of L2 and L3; placed after C1 so the L3 actor list and
        # order are unchanged)
        # C3 waits in the hall and starts as the camera arrives, then drives parallel to it 2.4 m to its right
        # (north), pulling ahead (1.5 m/s vs 1.0)
        ts = T((-11.0, YH), t_min=60)
        pb = PathBuilder((-12.5, YH + 2.4)).wait_until(ts + 0.5)
        fork('C3', 'female_adult_police_01_new', pb.leg([(-19.3, YH + 2.4)], 1.5), 'boxes', 0.25,
             active=(60.0, 1e9))
    if level == 2:
        # (L2 coverage fix, L2 ONLY: L3 was rendered before the fix and stays unchanged, so L3 contains every L2
        # actor except B11; in L3 the closer co-moving C1 takes its place in aisle -17.9) B11 waits (driver seated)
        # in aisle -17.9, leads the camera 7 m ahead up the aisle as soon as it turns in, turns east at the top
        # ahead of it and then south into aisle -12.9, where it parks
        ts, te = T((X2, 6.5)), T((X2, 21.0))
        pb = PathBuilder(cam.follow_point(ts, 7.0)).wait_until(ts).follow(cam, te, 7.0)
        fork('B11', 'male_adult_construction_03', pb.leg([(X1, YN), (X1, 21.0)], 1.2, ramp=0.0, corner_radius=1.4),
             'boxes', 0.3)
    return Scene(NAME, fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, parked + forks)
