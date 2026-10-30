#!/usr/bin/env python3
"""Search the SAVIOR-Warehouse *t1* L2/L3 sequences for a frame that illustrates promotion and motion evidence (Fig. 2).

Stage 1 (GT only): a driven forklift (driver -> forklift -> carried box/pallet, all moving and visible) and a
static potentially dynamic object that touches the chain in 2D (masks dilated by 4 px overlap by >= 5 px, the
gating.dilate_px / min_overlap_px defaults).
Stage 2 (SAVIOR code): the candidate frame is run through savior_perception's SaviorPipeline with the SAVIOR-P
configuration (contact depth gate, noise cap 0.5 m, extension band, no motion evidence, no tracker) on GT
instance masks. Kept: the driver is a root, the forklift and a carried load are promoted (load at >= 2 hops),
no static object of >= 200 px is promoted, and at least one static object in 2D contact is refused by the depth gate.
Stage 3 (SAVIOR code, motion evidence): one continuous SAVIOR-PM pass (same configuration + IMU-compensated
motion evidence, gyro of imu_noisy.csv) from the first frame of the sequence, so every candidate frame has the
full history. Kept: at least one potentially dynamic object that is static in the ground truth has the motion
state "static" (confirmed by SAVIOR-PM, never promoted), and every moving chain member is still a dynamic outlier.
Only *_t1_* sequences are read (t2/t3 are the sealed held-out split).
Result (step 5, all four sequences): stage 2 keeps aisles L2 125/130, hall L2 770/1615/1620, aisles L3 2095; none of
them has a static decision in stage 3 (static confirmation needs objects within about 4 m). Fig. 2 keeps the
aisles L2 scene and uses frame 127 for all panels; panel (5) shows moving vs undecided (see make_promotion_figure.py
for the choice of frame 127 among 126-132).

Usage (inside the savior image):  python3 paper/scripts/find_promotion_frame.py [step] [seq ...]
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promotion_common import WS, gt_instances, gyro, make_pipeline, read_moving  # noqa: E402

SEQS = ["aisles_t1_L2", "hall_t1_L2", "aisles_t1_L3", "hall_t1_L3"]
K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))


def stage1(raw, meta, moving, step):
    out = []
    for f, (ts, mov) in sorted(moving.items())[::step]:
        seg = cv2.imread(f"{raw}/seg0/{ts}.png", cv2.IMREAD_UNCHANGED)
        ids, cnt = np.unique(seg, return_counts=True)
        area = dict(zip(ids.tolist(), cnt.tolist()))
        for d in [i for i in mov if i in area and meta[i]["name"].endswith(".driver") and area[i] > 400]:
            actor = meta[d]["actor"]
            chain = [i for i in area if i in meta and meta[i]["actor"] == actor and i in mov]
            if not any(meta[i]["cls"] == "forklift" and area[i] > 2000 for i in chain):
                continue
            if not any(meta[i]["cls"] in ("box", "pallet") and area[i] > 300 for i in chain):
                continue
            cd = cv2.dilate(np.isin(seg, chain).astype(np.uint8), K)
            touch = [j for j in area if j in meta and j not in mov and meta[j]["role"] == "potential"
                     and area[j] >= 400 and np.count_nonzero(cv2.dilate((seg == j).astype(np.uint8), K) & cd) >= 5]
            if touch:
                out.append((f, ts, d))
    return out


def stage2(raw, meta, mov, ts, d):
    """SAVIOR-P checks on one frame; returns (score, loads, refused) or None."""
    pipe = make_pipeline(raw, motion=False)
    left = cv2.imread(f"{raw}/cam0/{ts}.png", cv2.IMREAD_GRAYSCALE)
    right = cv2.imread(f"{raw}/cam1/{ts}.png", cv2.IMREAD_GRAYSCALE)
    insts = gt_instances(raw, ts, meta, pipe.roles)
    pipe.process(left, right, int(ts) * 1e-9, insts)
    byid = {x.gt_id: (k, x) for k, x in enumerate(insts)}
    if d not in byid or byid[d][1].status != "root":
        return None

    def hop(k):
        x = insts[k]
        return 0 if x.parent < 0 else 1 + hop(x.parent)
    actor = meta[d]["actor"]
    chain = [(k, x) for k, x in enumerate(insts) if meta[x.gt_id]["actor"] == actor]
    fork_ok = any(x.cls == "forklift" and x.status == "promoted" and x.area > 2000 for _, x in chain)
    load_ok = [x for k, x in chain if x.cls in ("box", "pallet") and x.status == "promoted" and hop(k) >= 2
               and x.area > 300]
    false_prom = [x for x in insts if x.role == "potential" and x.gt_id not in mov and x.is_dynamic
                  and x.area >= 200]          # tiny objects seen through the cab take the cab depth
    dyn = [k for k, x in enumerate(insts) if x.is_dynamic]
    refused = []
    for k, x in enumerate(insts):
        if x.role != "potential" or x.is_dynamic or x.area < 400 or x.gt_id in mov:
            continue
        dx = pipe.gate._dilated(x)
        if any(pipe.gate.overlap_px(dx, pipe.gate._dilated(insts[q])) >= 5 for q in dyn):
            refused.append(x)
    if not (fork_ok and load_ok and not false_prom and refused):
        return None
    score = sum(min(x.area, 6000) for x in refused) + sum(min(x.area, 3000) for x in load_ok)
    return score, [meta[x.gt_id]["name"] for x in load_ok], [(meta[x.gt_id]["name"], x.area, round(x.depth, 1))
                                                           for x in refused]


def stage3(raw, meta, moving, cands):
    """One continuous SAVIOR-PM pass; at each candidate frame: statically confirmed potential objects."""
    want = {f: d for f, _, d in cands}
    last = max(want)
    rows = [l.strip().split(",") for l in open(f"{raw}/frames.csv") if not l.startswith("#")]
    pipe = make_pipeline(raw, motion=True)
    g = gyro(raw)
    prev = None
    out = {}
    for f, ts in ((int(a), b) for a, b in rows):
        if f > last:
            break
        left = cv2.imread(f"{raw}/cam0/{ts}.png", cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(f"{raw}/cam1/{ts}.png", cv2.IMREAD_GRAYSCALE)
        insts = gt_instances(raw, ts, meta, pipe.roles)
        t = int(ts) * 1e-9
        R = g.rotation(prev, t) if prev is not None else None
        prev = t
        pipe.process(left, right, t, insts, R_imu=R)
        if f not in want:
            continue
        mov = moving[f][1]
        st = lambda x: (x.motion or {}).get("state", "none")  # noqa: E731
        static_ok = [(meta[x.gt_id]["name"], x.area, round(x.depth, 1)) for x in insts
                     if x.role == "potential" and st(x) == "static" and x.gt_id not in mov and not x.is_dynamic
                     and x.area >= 800]
        static_wrong = [meta[x.gt_id]["name"] for x in insts if x.role == "potential" and st(x) == "static"
                        and x.gt_id in mov]
        actor = meta[want[f]]["actor"]
        chain_missed = [meta[x.gt_id]["name"] for x in insts if meta[x.gt_id]["actor"] == actor and x.gt_id in mov
                        and x.area > 300 and not x.is_dynamic]
        moving_st = [meta[x.gt_id]["name"] for x in insts if st(x) == "moving" and x.area > 1500]
        out[f] = (static_ok, static_wrong, chain_missed, moving_st)
    return out


def main(step=5, seqs=SEQS):
    res = []
    for seq in seqs:
        assert "_t1_" in seq
        raw = f"{WS}/data/warehouse/raw/{seq}"
        meta = {i["id"]: i for i in json.load(open(f"{raw}/instances.json"))["instances"]}
        moving = read_moving(raw)
        cands = stage1(raw, meta, moving, step)
        print(seq, "stage-1 candidates:", len(cands), file=sys.stderr, flush=True)
        ok = []
        for f, ts, d in cands:
            r = stage2(raw, meta, moving[f][1], ts, d)
            if r is not None:
                ok.append((f, ts, d, r))
        print(seq, "stage-2 candidates:", len(ok), [c[0] for c in ok], file=sys.stderr, flush=True)
        if not ok:
            continue
        s3 = stage3(raw, meta, moving, [(f, ts, d) for f, ts, d, _ in ok])
        for f, ts, d, (score, loads, refused) in ok:
            static_ok, static_wrong, chain_missed, moving_st = s3[f]
            print(seq, f, "static:", static_ok[:4], "wrong:", static_wrong, "missed:", chain_missed,
                  file=sys.stderr, flush=True)
            if static_ok:
                res.append((score + sum(min(a, 6000) for _, a, _ in static_ok), seq, f, ts, meta[d]["name"], loads,
                            refused, static_ok, static_wrong, chain_missed, moving_st))
    res.sort(key=lambda r: -r[0])
    for r in res[:30]:
        print(r, flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5, sys.argv[2:] or SEQS)
