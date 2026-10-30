#!/usr/bin/env python3
"""Fig. fig:qual of the SAVIOR paper: dynamic-outlier masking vs class-level masking, on real offline masks.

Columns: input | class-level masking (Y-Cls = yolo_naive) | SAVIOR-PM (yolo_p4_pot on VIODE, yolo_p4 on the warehouse).
Row (a) VIODE parking_lot_high (public data), the idea working. Masks regenerated deterministically with
        paper/scripts/regen_qual_viode.py (the P5 offline_eval.py pipeline: YOLO26s models/yolo26s-seg.engine,
        config/viode/savior_perception.yaml, roles viode_vehicles_dynamic / viode_vehicles_potential), stored in
        results/p5_viode/offline/qual/. The frame is chosen by select_viode_frame() from the stored P5 per-instance
        decisions (offline/parking_lot_high_inst.jsonl) and the GT masks: among frames in which YOLO detects both a
        moving and a parked car, keep those where EVERY SAVIOR-PM decision equals the majority outcome of its class
        in the report (parked -> kept, 97 %; moving below 10 m -> masked, 0.90 / 0.79 recall; moving beyond 10 m ->
        missed, 0.29 recall) and at least one moving car is masked; take the one with the most GT-labelled
        instances, then the largest visible parked-car area (visibility only).
Row (b) SAVIOR-Warehouse hall_t1_L3 (tuning split t1 only), t = 61.45 s, the co-moving failure. Masks are the
        stored P6 offline outputs (results/p6_warehouse/offline/qual/, offline_eval_wh.py --save-stamps); image in
        colour from data/warehouse/raw/hall_t1_L3/cam0.
Overlays: red = core (255, dynamic outlier), light red = extension band (192), green = static potentially dynamic
object (GT) left unmasked (kept as inlier), white dashed = GT moving object outline. Features: FAST threshold 20,
the strongest corner per 32 px grid cell (OpenVINS-like); green dot = kept, red x = removed (mask >= 128, the
OpenVINS fork's rejection rule).

Usage (savior image):  python3 paper/scripts/make_qual_figure.py
Output: paper/figures/fig_qual.pdf / fig_qual.png
"""
import json
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

WS = "/home/sasa/workspace/savior_ws"
sys.path.insert(0, f"{WS}/results/p6_warehouse/scripts")
from wh_gt import SeqGT  # noqa: E402

OUT = f"{WS}/paper/figures"
plt.style.use(f"{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle")

VIODE_SEQ = "parking_lot_high"
VIODE_STAMP = 1597195521283433592
WH_SEQ = "hall_t1_L3"
WH_STAMP = 1700000061450000000

RED = np.array([225, 20, 20]) / 255
LRED = np.array([255, 150, 150]) / 255
GREEN = np.array([30, 200, 60]) / 255
CELL = 32
MIN_OUTLINE_PX = 200


def select_viode_frame():
    z = np.load(f"{WS}/data/viode/gt/masks/{VIODE_SEQ}.npz")
    key = {round(s * 1e-9, 3): i for i, s in enumerate(z["stamp_ns"])}
    fr = {}
    for line in open(f"{WS}/results/p5_viode/offline/{VIODE_SEQ}_inst.jsonl"):
        r = json.loads(line)
        if r["v"] == "yolo_p4_pot" and r["lab"] != "none":
            fr.setdefault(r["t"], {}).setdefault((r["lab"], r["gid"]), []).append(r)

    def typical(lab, depth, masked):
        if lab == "static":
            return not masked
        return depth is not None and (masked if depth < 10 else not masked)

    best, n_both, n_typ = None, 0, 0
    for t, g in fr.items():
        labs = {k[0] for k in g}
        if labs != {"dynamic", "static"}:
            continue
        n_both += 1
        dec = {k: any(x["masked"] for x in v) for k, v in g.items()}
        if not all(typical(k[0], g[k][0]["depth"], dec[k]) for k in g):
            continue
        if not any(dec[k] for k in g if k[0] == "dynamic"):
            continue
        n_typ += 1
        i = key[t]
        score = (len(g), int(np.isin(z["left"][i], z["static_ids"]).sum()))
        if best is None or score > best[0]:
            best = (score, int(z["stamp_ns"][i]), t, g, dec)
    print(f"VIODE: {n_both} frames with a detected moving and parked car, {n_typ} typical; chosen t={best[2]} "
          f"stamp {best[1]} decisions " + str({f'{k[0]}:{k[1]}@{best[3][k][0]["depth"]}m': best[4][k] for k in best[3]}))
    return best[1]


def fast_grid(gray):
    fast = cv2.FastFeatureDetector_create(threshold=20, nonmaxSuppression=True)
    h, w = gray.shape
    best = {}
    for k in fast.detect(gray):
        c = (int(k.pt[0]) // CELL, int(k.pt[1]) // CELL)
        if c not in best or k.response > best[c].response:
            best[c] = k
    return np.array([k.pt for k in best.values()])


def overlay(rgb, ml, static_pot):
    out = rgb.astype(float) / 255
    out = 0.85 * out + 0.15 * out.mean(axis=2, keepdims=True)   # slight desaturation so overlays stand out
    kept = static_pot & (ml < 128)
    for m, c, a in ((kept, GREEN, 0.45), (ml == 192, LRED, 0.55), (ml == 255, RED, 0.55)):
        out[m] = (1 - a) * out[m] + a * c
    return np.clip(out, 0, 1)


def contours(mask):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [c[:, 0, :] for c in cs if cv2.contourArea(c) >= MIN_OUTLINE_PX]


def load_viode(stamp):
    q = f"{WS}/results/p5_viode/offline/qual/{VIODE_SEQ}_{stamp}"
    zc, zp = np.load(f"{q}_yolo_naive.npz"), np.load(f"{q}_yolo_p4_pot.npz")
    assert bool(zc["match"]) and bool(zp["match"]), "regenerated decisions differ from the stored P5 decisions"
    gl = zp["gt_left"]
    return dict(rgb=zp["left_rgb"], ml_cls=zc["ml"], ml_pm=zp["ml"], moving=np.isin(gl, zp["dyn_ids"]),
                static_pot=np.isin(gl, zp["static_ids"]))


def load_wh():
    q = f"{WS}/results/p6_warehouse/offline/qual/{WH_SEQ}_{WH_STAMP}"
    zc, zp = np.load(f"{q}_yolo_naive.npz"), np.load(f"{q}_yolo_p4.npz")
    bgr = cv2.imread(f"{WS}/data/warehouse/raw/{WH_SEQ}/cam0/{WH_STAMP}.png", cv2.IMREAD_COLOR)
    assert np.array_equal(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), zp["left"]), "colour frame != stored mono8 frame"
    cat = SeqGT(WH_SEQ).category_image(0, WH_STAMP)
    return dict(rgb=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), ml_cls=zc["ml"], ml_pm=zp["ml"],
                moving=(cat >= 11) & (cat <= 15), static_pot=(cat >= 1) & (cat <= 5))


def report(name, d):
    gray = cv2.cvtColor(d["rgb"], cv2.COLOR_RGB2GRAY)
    pts = fast_grid(gray)
    d["pts"] = pts
    xi, yi = pts[:, 0].astype(int), pts[:, 1].astype(int)
    for v in ("ml_cls", "ml_pm"):
        ml = d[v]
        rem = ml[yi, xi] >= 128
        sp = d["static_pot"] & (ml < 128)
        print(f"{name} {v}: core {100 * (ml == 255).mean():.1f} % band {100 * (ml == 192).mean():.1f} %, "
              f"moving px masked {(ml[d['moving']] >= 128).mean():.2f}, static-pot px masked "
              f"{(ml[d['static_pot']] >= 128).mean():.2f} (kept px {sp.sum()}), features {len(pts)} removed {rem.sum()}")


def main():
    stamp = select_viode_frame()
    assert stamp == VIODE_STAMP, f"frame selection changed: {stamp}"
    rows = [load_viode(VIODE_STAMP), load_wh()]
    for n, d in zip(("viode", "warehouse"), rows):
        report(n, d)

    W = 7.16
    lm, rm, gap = 0.30, 0.03, 0.04
    pw = (W - lm - rm - 2 * gap) / 3
    hs = [pw * d["rgb"].shape[0] / d["rgb"].shape[1] for d in rows]
    top, rg, leg = 0.20, 0.06, 0.30
    H = top + hs[0] + rg + hs[1] + leg
    fig = plt.figure(figsize=(W, H))
    fs = 7.5
    halo = [pe.withStroke(linewidth=1.6, foreground="black")]
    lab = dict(fontsize=6.3, color="white", ha="center", va="center", path_effects=halo)
    titles = ["Input", "Class-level masking (Y-Cls)", "SAVIOR-PM"]
    row_labels = ["(a) VIODE\nparking lot, high", "(b) SAVIOR-Warehouse\nhall L3, $t$ = 61.45 s"]
    y = H - top
    axes = []
    for r, d in enumerate(rows):
        y -= hs[r]
        ra = []
        for c in range(3):
            a = fig.add_axes([(lm + c * (pw + gap)) / W, y / H, pw / W, hs[r] / H])
            a.set_xticks([])
            a.set_yticks([])
            for s in a.spines.values():
                s.set_linewidth(0.6)
            if c == 0:
                a.imshow(d["rgb"], interpolation="lanczos")
            else:
                ml = d["ml_cls"] if c == 1 else d["ml_pm"]
                a.imshow(overlay(d["rgb"], ml, d["static_pot"]), interpolation="lanczos")
                pts = d["pts"]
                rem = ml[pts[:, 1].astype(int), pts[:, 0].astype(int)] >= 128
                a.plot(pts[~rem, 0], pts[~rem, 1], "o", ms=2.0, mfc=GREEN, mec="black", mew=0.3, ls="none")
                a.plot(pts[rem, 0], pts[rem, 1], "x", ms=2.6, color=RED, mew=0.9, ls="none",
                       path_effects=[pe.withStroke(linewidth=1.7, foreground="white")])
            for cnt in contours(d["moving"]):
                cc = np.vstack([cnt, cnt[:1]])
                a.plot(cc[:, 0], cc[:, 1], color="white", lw=0.8, ls=(0, (2.5, 1.5)))
            a.set_xlim(-0.5, d["rgb"].shape[1] - 0.5)
            a.set_ylim(d["rgb"].shape[0] - 0.5, -0.5)
            if r == 0:
                a.set_title(titles[c], fontsize=fs, pad=3)
            if c == 0:
                a.set_ylabel(row_labels[r], fontsize=fs, labelpad=3)
            ra.append(a)
        axes.append(ra)
        y -= rg

    # minimal in-image labels (positions in pixel coordinates of each image)
    a0, a1, a2 = axes[0]
    a0.text(640, 330, "moving", **lab)
    a0.text(120, 375, "parked", **lab)
    a1.text(120, 385, "parked:\nmasked", **lab)
    a2.text(120, 385, "parked:\nkept", **lab)
    b0, b1, b2 = axes[1]
    b0.text(125, 62, "moving\n(lead forklift)", **lab)
    b0.text(585, 120, "parked", **lab)
    b1.text(470, 335, "parked forklift, pallets,\nboxes: masked", **lab)
    b2.annotate("co-moving forklift\nmissed", xy=(120, 260), xytext=(300, 330), fontsize=6.3, color="white",
                ha="center", va="center", path_effects=halo,
                arrowprops=dict(arrowstyle="-|>", color="white", lw=0.8, shrinkA=0, shrinkB=0,
                                path_effects=[pe.withStroke(linewidth=1.8, foreground="black")]))

    hdl = [Patch(fc=RED, ec="none", label="dynamic outlier (core)"),
           Patch(fc=LRED, ec="none", label="extension band"),
           Patch(fc=GREEN, ec="none", alpha=0.8, label="static potentially dynamic object: kept"),
           Line2D([], [], color="0.35", lw=0.9, ls=(0, (2.5, 1.5)), label="moving (ground truth)"),
           Line2D([], [], marker="o", ls="none", mfc=GREEN, mec="black", mew=0.3, ms=3.2, label="feature kept"),
           Line2D([], [], marker="x", ls="none", color=RED, mew=0.9, ms=3.6, label="feature removed")]
    fig.legend(handles=hdl, loc="lower center", ncol=6, fontsize=6.4, frameon=False, handlelength=1.4,
               handletextpad=0.4, columnspacing=1.0, bbox_to_anchor=(0.5 + (lm - rm) / 2 / W, 0.0))
    fig.savefig(f"{OUT}/fig_qual.pdf")
    fig.savefig(f"{OUT}/fig_qual.png", dpi=300)
    print("wrote fig_qual")


if __name__ == "__main__":
    main()
