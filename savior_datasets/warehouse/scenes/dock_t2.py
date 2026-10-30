# SPDX-License-Identifier: GPL-3.0-or-later
"""HELD-OUT scene C trajectory t2 ("dock", test split): new block-stacking layout with narrow lanes (scenes/dock.py).

Camera (~88 m): take-off in the north lane facing east (1.0 m/s), south down lane XB (1.2 m/s), west along lane YC
(0.7 m/s, 1.0-1.1 m high), north up lane XA (0.9 m/s), east along lane YB (1.3 m/s, climbing to 2.4 m: it looks
down over the blocks), north up lane XC (0.9 m/s) and diagonally into the staging strip (0.7 m/s).
Levels (nested):
  L1 people: one standing against a KLT pallet in view during the whole hover; one starting to walk at take-off who
     crosses the camera lane and then stands touching a block; a picker standing at a block face; head-on people in
     lanes YC and YB (the latter then stands); walking-ahead people in the north lane and lane XA who then stand; one brushing along a block face ahead of the camera in lane XC; one
     crossing lane YB at a blind intersection (perpendicular); one crossing the north lane DURING the hover; one
     walking across the view of the final approach and hover
  L2 + forklifts (drivers, boxes): one coming out of a side lane and turning away ahead of the camera
     (perpendicular), one crossing a blind intersection 3.5 s ahead, one parked in a lane that starts when the camera
     is 9 m away and leads it 9 -> 8 m, one REVERSING out of a block bay and then leading the camera 10-15 m ahead,
     one starting when the camera is 4 m away and leading it 4 -> 10 m up lane XA and along lane YB, one creeping
     north 1.8 m to the side of the camera in lane XC (overtaken)
     (L2 coverage fix: E9, E10 and the people D11, D12 were added, E2 / E7 / E4 / D5 / D8 / D10 retimed)
  L3 + co-moving: a forklift 2.5 m ahead and 1.8 m to the left in the north lane from take-off (static during the hover,
     starts with the camera); one parked in a lane ahead that starts when the camera is 5 m away and leads it
     5.0 -> 2.6 m (1.2 m/s) and 2.6 -> 4.0 m (0.7 m/s); one coming out of a side lane, turning in 3.5 m ahead and
     leading 3.5 -> 3.0 m at 1.3 m/s (seen from above) and up lane XC, parking in front of the final hover
"""
from wh.scenario import PathBuilder, Person, Forklift, Scene
from . import dock as base
from . import full_warehouse as fw

NAME, TRAJ, SEED = 'dock', 't2', 3301
PLAN_BOX = base.PLAN_BOX
YA, YB, YC, XA, XB, XC = base.YA, base.YB, base.YC, base.XA, base.XB, base.XC
WPS = [[-24.0, YA], [XB, YA], [XB, YC], [XA, YC], [XA, YB], [XC, YB], [XC, 2.6], [2.6, 4.2]]


# Held-out hard cases per level (cumulative), see scenes/aisles_t2.py.
HARD_CASES = {
    0: {'d': 'new block-stacking layout (narrow 3 m lanes); parked forklifts with boxes on raised forks (PF1 1.1 m, '
             'PF2 0.6 m, PF4 0.35 m), PF3 with a pallet'},
    1: {'b': 'D2 and D9 start walking at t=3.3 s (just after take-off), D2 crossing the camera lane 8 m ahead',
        'c': 'D1 against a KLT pallet (whole sequence, in view during the hover), D3 picker at a block; '
             'D2/D5/D6/D8/D9/D10 stand after walking',
        'd': 'D1 / D2 touch stacks, D3 at a block face, D4/D5/D6 brush along block faces',
        'hover_motion': 'D12 walks across the north lane 5 m ahead DURING the 3 s hover (static initialisation window)',
        'f': 'D2/D8/D11/D12 perpendicular (D8 at a blind intersection, D11 across the final hover); D4/D5 head-on; '
             'D6/D9/D10 same direction'},
    2: {'a': 'E7 parked in the lane starts when the camera is 9 m away and leads it 9 -> 8 m; E4 leads 10-15 m; '
             'E10 starts when the camera is 4 m away and leads it 4 -> 10 m up lane XA and along lane YB',
        'e': 'every L2/L3 forklift has a seated driver and boxes or a pallet on the forks',
        'f': 'E1 out of a side lane and E2 across a blind intersection (perpendicular); E7/E4 parallel; E9 parallel '
             '1.8 m to the side in lane XC, slower than the camera',
        'reverse': 'E4 reverses out of a block bay into the lane, then drives forward'},
    3: {'a': 'F0 2.5 m ahead / 1.8 m to the side from take-off; F1 5.0 -> 2.6 m at 1.2 m/s and 2.6 -> 4.0 m at 0.7 m/s; '
             'F2 turns in 3.5 m ahead and leads 3.5 -> 3.0 m at 1.3 m/s seen from 2.4 m altitude (t1: 3.7 m at 1.0 m/s)',
        'b': 'F0 is static next to the camera during the hover and starts with it at take-off; F1 starts when the '
             'camera is 5 m away',
        'turn_in': 'F2 drives out of a side lane and turns in just ahead of the camera'},
}

def camera_cfg():
    return dict(waypoints=WPS, seg_speeds=[1.0, 1.2, 0.7, 0.9, 1.3, 0.9, 0.7],
                wp_heights=[1.3, 1.5, 1.1, 1.0, 1.4, 2.4, 1.6, 1.4], height_smooth_s=1.5,
                speed=1.0, height=1.4, height_amp=0.10, yaw_amp_deg=12.0, seed=SEED, platform='drone',
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

    t_yb = T((-9.0, YB), t_min=55)          # camera at the XB/YB intersection on lane YB
    if level >= 1:
        # D1 stands against KLT pallet stK1 in the staging strip, in view during the hover (never moves)
        person('D1', 'male_adult_police_04', PathBuilder((-17.4, 7.2)).wait(duration))
        # D2 starts walking at take-off (3.3 s), crosses the north lane 8 m ahead and stands touching block B12
        person('D2', 'F_Business_02', PathBuilder((-15.4, 7.4)).wait_until(3.3).leg([(-15.5, 2.75)], 1.1))
        # D9 walks east ahead of the camera from take-off (1.0 m to its right), stops next to D2 and stands
        pb = PathBuilder((-21.2, YA - 1.0)).wait_until(3.3)
        person('D9', 'male_adult_construction_01_new', pb.leg([(-16.6, YA - 1.0)], 0.85))
        # D10 walks north up lane XA ahead of the camera (1.0 m to its left, overtaken), then stands (south of YB)
        pb = PathBuilder((XA - 1.0, -13.4)).wait_until(T((-17.0, YC)))
        person('D10', 'female_adult_police_02', pb.leg([(XA - 1.1, -10.4)], 0.7))
        # D3 picks at the west face of block B22 (lane XA, standing)
        person('D3', 'F_Medical_01', PathBuilder((XA + 1.4, -11.0)).wait(duration))
        # D4 walks east along lane YC, head-on (1.2 m to the camera's left), brushing the south row
        tm = T((-14.0, YC))
        pb = PathBuilder((-21.5, YC - 1.2)).wait_until(tm - 7.5 / 1.0 - 0.8)
        person('D4', 'male_adult_construction_03', pb.leg([(-2.0, YC - 1.2)], 1.0))
        # D5 walks west along lane YB, head-on (1.3 m to the camera's left, brushing the block face), then stands there
        tm = T((-8.0, YB), t_min=55)
        pb = PathBuilder((0.6, YB + 1.3)).wait_until(tm - 8.6 / 1.0 - 0.8)
        person('D5', 'female_adult_police_03_new', pb.leg([(-15.0, YB + 1.3)], 1.0))
        # D6 walks north in lane XC ahead of the camera, brushing along block B13 (overtaken)
        pb = PathBuilder((XC - 1.35, -3.9)).wait_until(T((-2.0, YB), t_min=55))
        person('D6', 'male_adult_construction_05_new', pb.leg([(XC - 1.35, 2.4)], 0.75))
        # D8 crosses lane YB at the blind XB intersection (north -> south), 14 s ahead of the camera, then stands
        pb = PathBuilder((XB + 0.3, -2.4)).wait_until(t_yb - 14.0 - 3.5)
        person('D8', 'female_adult_police_01_new', pb.leg([(XB + 0.3, -10.4)], 1.1), active=(40.0, 1e9))
        # D12 (L2 coverage fix) walks out of the staging strip across the north lane 5 m ahead DURING the hover
        # (static initialisation window) into the mouth of lane XA, where it stands at the block corner
        person('D12', 'female_adult_police_02', PathBuilder((-18.8, 7.2)).leg([(-18.8, 4.0), (-18.6, 1.0)], 1.0))
        # D11 (L2 coverage fix) walks west along the staging strip across the view of the final approach and hover
        # (1 m in front of the camera's end point), from the east rail
        ts = T((XC, 1.1), t_min=80)
        person('D11', 'M_Medical_01', PathBuilder((4.3, 5.2)).wait_until(ts + 2.5).leg([(-0.3, 5.2)], 0.8))
    if level >= 2:
        # E1 comes north out of lane XB 8 s ahead of the camera, turns east (away) and parks
        tc = T((XB, YA)) - 8.0
        pb = PathBuilder((XB, -3.0)).wait_until(tc - 7.0 / 1.4 - 1.0)
        fork('E1', 'male_adult_construction_01_new', pb.leg([(XB, YA + 0.4), (-2.5, YA + 0.4)], 1.4, corner_radius=1.4),
             'boxes', 0.3)
        # E2 crosses lane XB along lane YB (east -> west) 3.5 s ahead of the camera and parks at the west end
        tc = T((XB, YB)) - 3.5
        pb = PathBuilder((-2.0, YB)).wait_until(tc - 7.0 / 1.5 - 1.0)
        fork('E2', 'female_adult_police_02', pb.leg([(-24.5, YB)], 1.5), 'boxes', 0.35)
        # E4 parked nose-in in the bay of block B23 (driver seated); reverses out into lane YB when the camera is
        # 19 m away, then drives east 10-15 m ahead of it and parks in lane XC (south part)
        ts = T((XA, -12.5), t_min=40)
        pb = PathBuilder((-3.1, -9.7)).wait_until(ts).leg([(-3.1, -6.1)], 0.7, reverse=True)
        fork('E4', 'male_adult_police_04', pb.leg([(XC, YB), (XC, -14.2)], 1.3, corner_radius=1.3), 'boxes', 0.4)
        # E7 parked deep in lane XB (driver seated); starts when the camera is 9 m away and leads it 9 -> 8 m ahead
        # down lane XB and along lane YC, then turns south at lane XA and parks
        ts = T((XB, -4.0))
        t1 = T((-10.6, YC))
        pb = PathBuilder(cam.follow_point(ts, 9.0)).wait_until(ts).follow(cam, t1, 9.0, ahead_end=8.0)
        fork('E7', 'male_adult_construction_03', pb.leg([(XA, YC), (XA, -21.6)], 1.2, ramp=0.0, corner_radius=1.2),
             'boxes', 0.3)
        # E10 (L2 coverage fix) waits (driver seated) in lane XA (shown from t=45 s, after E2 has passed); starts
        # when the camera is 4 m away and leads it 4 -> 9 m ahead up lane XA and 9 -> 10 m ahead along lane YB
        # (behind E4), then turns south into lane XC and parks there north of E4
        ts, ts2 = T((XA, -13.0), t_min=40), T((XA, -8.5), t_min=40)
        te = T((XC - 11.0, YB), t_min=60)
        pb = PathBuilder(cam.follow_point(ts, 4.0)).wait_until(ts).follow(cam, ts2, 4.0, ahead_end=9.0)
        pb.follow(cam, te, 9.0, ahead_end=10.0)
        fork('E10', 'female_adult_police_03_new', pb.leg([(XC, YB), (XC, -10.0)], 1.3, ramp=0.0, corner_radius=1.3),
             'pallet', 0.3, active=(45.0, 1e9))
        # E9 (L2 coverage fix) waits (driver seated) on the east side of lane XC; starts as the camera turns into
        # lane XC and creeps north parallel to it (0.25 m/s), 1.8 m to its right (overtaken), then parks at the east
        # side of the lane's north end
        ts = T((-2.0, YB), t_min=60)
        pb = PathBuilder((XC + 1.8, -2.4)).wait_until(ts)
        fork('E9', 'F_Business_02', pb.leg([(XC + 1.8, 1.6)], 0.25), 'boxes', 0.45)
    if level >= 3:
        # F0 co-moves with the camera in the north lane, 2.5 m ahead and 1.8 m to its left, from take-off; parks in the
        # staging strip
        te = T((-11.5, YA))
        pb = PathBuilder(cam.follow_point(0.0, 2.5, 1.8)).follow(cam, te, 2.5, 1.8)
        fork('F0', 'male_adult_construction_05_new', pb.leg([(-8.6, YA + 1.85)], 1.0, ramp=0.0), 'boxes', 0.3)
        # F1 parked in lane XB (driver seated); starts when the camera is 5 m away, leads it 5.0 -> 2.6 m down lane
        # XB and 2.6 -> 4.0 m along lane YC, then drives on west and parks
        ts = T((XB, -4.0))
        t1, t2 = T((XB, YC)), T((-14.5, YC))
        pb = PathBuilder(cam.follow_point(ts, 5.0)).wait_until(ts).follow(cam, t1, 5.0, ahead_end=2.6)
        pb.follow(cam, t2, 2.6, ahead_end=4.0)
        fork('F1', 'female_adult_police_03_new', pb.leg([(-23.5, YC)], 0.8, ramp=0.0), 'pallet', 0.2)
        # F2 parked in lane XA (north part) facing south; drives out, turns into lane YB 3.5 m ahead of the camera
        # and leads it 3.5 -> 3.0 m along lane YB (1.3 m/s) and up lane XC; parks in front of the final hover
        ts2 = T((XA, -8.5), t_min=40)
        t3, t4 = T((XC, YB), t_min=60), T((XC, -0.5), t_min=60)
        pb = PathBuilder((XA, -1.0)).wait_until(ts2 - 5.0)
        pb.leg([(XA, -3.6), cam.follow_point(ts2, 3.5, -0.2)], 1.2, stop=False)
        pb.follow(cam, t3, 3.5, -0.2, ahead_end=3.0).follow(cam, t4, 3.0)
        fork('F2', 'female_adult_police_01_new', pb.leg([(XC, 5.8), (1.6, 7.4)], 0.9, ramp=0.0, corner_radius=1.0),
             'boxes', 0.25)
    return Scene(NAME, fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, parked + forks)
