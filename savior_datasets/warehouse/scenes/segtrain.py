# SPDX-License-Identifier: GPL-3.0-or-later
"""Randomised layouts for the segmentation training set (domain randomisation over layout / actors / lighting).

Each layout seed picks one base static layout (aisles or hall), then places 4..9 forklifts (driverless and parked,
or with a seated driver and a load, driving short legs) and 6..14 people (walking / standing) on the free lanes of
that layout, with a minimum separation. Everything stays in free space by construction (lanes = camera / actor lanes
of the VIO scenes)."""
import numpy as np

from wh.classes import CHARACTERS
from wh.scenario import Forklift, PathBuilder, Person, Scene
from . import aisles, hall
from . import full_warehouse as fw

# free lane segments (x0, y0, x1, y1, half width usable for actor centres)
LANES = {
    'aisles': [(x, 9.5, x, 24.5, 0.6) for x in fw.AISLE_X[1:4]] + [(-24.5, 27.9, 2.0, 27.9, 0.5),
                                                                  (-24.0, 5.6, -1.0, 5.6, 0.8), (-24.0, 2.6, -3.0, 2.6, 0.8),
                                                                  (-16.0, -5.5, -12.5, 1.0, 0.5)],
    'hall': [(-21.0, 0.0, 1.0, 0.0, 1.0), (1.0, -1.0, 1.0, -18.0, 1.2), (-22.0, -19.5, 1.0, -19.5, 1.5),
             (-22.5, -18.0, -22.5, -7.0, 1.5), (-21.0, -7.2, -4.0, -7.2, 1.2), (-12.6, 3.0, -9.4, 3.0, 0.3),
             (-11.0, -9.0, -11.0, -10.5, 0.8)],
}


def _sample_on_lanes(rng, lanes, n, min_sep, taken):
    out = []
    for _ in range(n * 40):
        if len(out) >= n:
            break
        x0, y0, x1, y1, w = lanes[rng.integers(len(lanes))]
        u = rng.uniform()
        d = np.array([x1 - x0, y1 - y0])
        L = np.linalg.norm(d)
        nrm = np.array([-d[1], d[0]]) / max(L, 1e-9)
        p = np.array([x0, y0]) + u * d + rng.uniform(-w, w) * nrm
        if all(np.linalg.norm(p - q) >= min_sep for q in taken + [o[0] for o in out]):
            out.append((p, np.arctan2(d[1], d[0])))
    return out


def build_random(seed, duration=60.0):
    rng = np.random.default_rng(seed)
    base = 'aisles' if seed % 2 == 0 else 'hall'
    mod = aisles if base == 'aisles' else hall
    props, rails, windows, parked = mod.static_layout()
    lanes = LANES[base]
    taken = [np.array(f.pose[:2]) for f in parked]
    forks, people = list(parked), []
    for i, (p, h) in enumerate(_sample_on_lanes(rng, lanes, int(rng.integers(4, 10)), 4.6, taken)):
        taken.append(p)
        hd = h + (np.pi if rng.uniform() < 0.5 else 0.0) + rng.normal(0, 0.15)
        load = ['boxes', 'pallet', 'none'][rng.integers(3)]
        driver = CHARACTERS[rng.integers(len(CHARACTERS))] if rng.uniform() < 0.7 else None
        if driver and rng.uniform() < 0.6:     # drives a short leg along its heading
            L = rng.uniform(1.5, 4.0)
            q = p + L * np.array([np.cos(hd), np.sin(hd)])
            pb = PathBuilder(p).wait_until(rng.uniform(0, 20)).leg([q], rng.uniform(0.6, 1.5))
            forks.append(Forklift(f'RF{i}', pb.build(duration, 0.45), (0, 0, 0), driver, load, rng.uniform(0.0, 0.8)))
        else:
            forks.append(Forklift(f'RF{i}', None, (p[0], p[1], np.rad2deg(hd)), driver, load, rng.uniform(0.0, 0.6)))
    for i, (p, h) in enumerate(_sample_on_lanes(rng, lanes, int(rng.integers(6, 15)), 1.6, taken)):
        taken.append(p)
        hd = h + (np.pi if rng.uniform() < 0.5 else 0.0)
        ch = CHARACTERS[rng.integers(len(CHARACTERS))]
        pb = PathBuilder(p).wait_until(rng.uniform(0, 30))
        if rng.uniform() < 0.65:   # walking a short leg (walk poses), else idle
            L = rng.uniform(1.0, 3.5)
            pb.leg([p + L * np.array([np.cos(hd), np.sin(hd)])], rng.uniform(0.8, 1.4))
        people.append(Person(f'RP{i}', ch, pb.build(duration, 0.25)))
    return Scene(f'segtrain_{seed}', fw.ENV, fw.ENV_CLASSES, [], props, rails, windows, people, forks), base
