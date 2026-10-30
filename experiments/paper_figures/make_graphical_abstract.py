#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Graphical abstract / overview figure for the SAVIOR paper.

One glance, little text, built from real data: SAVIOR-Warehouse hall_t1_L3 at t = 61.45 s.
  1) stereo + IMU input   2) moving (masked) vs static movable (kept)   3) gated features
  4) unchanged MSCKF -> top-down trajectory: GT, OpenVINS (fails) and SAVIOR.
Masks in panel 2 are the dataset's GT moving flags (illustrative). The trajectories are representative
runs of the tuning split t1 with the OpenVINS back-end v1 (illustrative only), same start offset 0.0 s: OpenVINS run_01
(results/p6_warehouse; the typical stand-still failure, 5.2 m ATE) and the final SAVIOR (sens_fix1, results/p7) run_01
(0.132 m; median of 10 offsets 0.130 m). The back-end v2 pair was not used: under v2, 8/10 OpenVINS offsets diverge without
a plottable trajectory, and the two bounded ones (1.25 / 1.49 m) show the failure less clearly.

Usage (inside the savior image):  python3 paper/scripts/make_graphical_abstract.py
"""
import json
import os

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

WS = "/home/sasa/workspace/savior_ws"
SEQ = "hall_t1_L3"
STAMP = "1700000061450000000"
RAW = f"{WS}/data/warehouse/raw/{SEQ}"
OUT = f"{WS}/paper/figures/fig_overview"
EST_OV = f"{WS}/results/p6_warehouse/{SEQ}/openvins/run_01/stamped_traj_estimate.txt"
EST_SV = f"{WS}/results/p7/{SEQ}/sens_fix1/run_01/stamped_traj_estimate.txt"
GT = f"{WS}/data/warehouse/gt/{SEQ}.txt"

plt.style.use(f"{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle")
RED = np.array([230, 30, 30])
GREEN = np.array([30, 170, 60])


def load_tum(p):
    a = np.loadtxt(p, comments="#")
    return a[:, 0], a[:, 1:4]


def align_posyaw(t_e, p_e, t_g, p_g):
    """Associate by nearest stamp, then fit yaw + translation (as in rpg posyaw)."""
    idx = np.clip(np.searchsorted(t_g, t_e), 1, len(t_g) - 1)
    idx -= (t_e - t_g[idx - 1]) < (t_g[idx] - t_e)
    g = p_g[idx]
    me, mg = p_e.mean(0), g.mean(0)
    H = (p_e[:, :2] - me[:2]).T @ (g[:, :2] - mg[:2])
    U, _, Vt = np.linalg.svd(H)
    R2 = Vt.T @ U.T
    if np.linalg.det(R2) < 0:
        Vt[1] *= -1
        R2 = Vt.T @ U.T
    R = np.eye(3)
    R[:2, :2] = R2
    return (p_e - me) @ R.T + mg


def main():
    img = cv2.cvtColor(cv2.imread(f"{RAW}/cam0/{STAMP}.png"), cv2.COLOR_BGR2RGB)
    seg = cv2.imread(f"{RAW}/seg0/{STAMP}.png", cv2.IMREAD_UNCHANGED)
    inst = {i["id"]: i for i in json.load(open(f"{RAW}/instances.json"))["instances"]}
    moving_ids = set()
    for line in open(f"{RAW}/moving.csv"):
        if line.startswith("#"):
            continue
        f, ts, *rest = line.strip().split(",")
        if ts == STAMP:
            moving_ids = {int(x) for x in rest[0].split()} if rest and rest[0] else set()
            break
    ids = np.unique(seg)
    mov = np.isin(seg, list(moving_ids))
    static_pot = np.isin(seg, [i for i in ids if i in inst and inst[i]["role"] in ("potential", "dynamic")
                               and i not in moving_ids])

    # Panel 2: dynamic outliers (GT moving) = red (removed), static potentially dynamic = green (kept)
    p2 = img.astype(float)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2).astype(float)
    p2 = 0.55 * gray + 0.45 * p2
    p2[mov] = 0.45 * p2[mov] + 0.55 * RED
    p2[static_pot] = 0.5 * p2[static_pot] + 0.5 * GREEN
    for m, c in ((mov, RED), (static_pot, GREEN)):
        cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(p2, cnts, -1, tuple(int(v) for v in c), 2)
    p2 = np.clip(p2, 0, 255).astype(np.uint8)

    # Panel 3: FAST features on a grid; rejected inside the (dilated) moving mask
    g8 = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    kps = cv2.FastFeatureDetector_create(threshold=20).detect(g8)
    kps = sorted(kps, key=lambda k: -k.response)
    cell, taken, pts = 48, set(), []
    for k in kps:
        c = (int(k.pt[0] // cell), int(k.pt[1] // cell))
        if c not in taken:
            taken.add(c)
            pts.append(k.pt)
    movd = cv2.dilate(mov.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    p3 = (0.6 * gray + 0.4 * img).astype(np.uint8).copy()

    # Trajectories
    tg, pg = load_tum(GT)
    to, po = load_tum(EST_OV)
    ts, ps = load_tum(EST_SV)
    po_a, ps_a = align_posyaw(to, po, tg, pg), align_posyaw(ts, ps, tg, pg)

    fig = plt.figure(figsize=(7.2, 4.1))
    H, W = img.shape[:2]
    ax_w, ax_h = 0.305, 0.305 * (H / W) * 7.2 / 4.1
    y_top = 0.53
    xs = [0.01, 0.345, 0.68]
    titles = ["Stereo + IMU", "Moving or static?", "Gate features"]
    panels = [img, p2, p3]
    axes = []
    for x, t, im in zip(xs, titles, panels):
        ax = fig.add_axes([x, y_top, ax_w, ax_h])
        ax.imshow(im)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(t, fontsize=17, pad=4)
        axes.append(ax)
    for (x, y) in pts:
        bad = movd[int(y), int(x)]
        axes[2].plot(x, y, "x" if bad else "o", ms=5 if bad else 4, mew=1.5,
                     color="red" if bad else "lime", mec="red" if bad else "darkgreen")
    # legend chips for panel 2 (two words each)
    axes[1].text(0.02, 0.96, "dynamic outlier: removed", color="white", fontsize=11, va="top", transform=axes[1].transAxes,
                 bbox=dict(boxstyle="round,pad=0.2", fc="red", ec="none", alpha=0.85))
    axes[1].text(0.98, 0.04, "static: kept", color="white", fontsize=11, ha="right",
                 transform=axes[1].transAxes,
                 bbox=dict(boxstyle="round,pad=0.2", fc=tuple(GREEN / 255), ec="none", alpha=0.9))
    # arrows between image panels
    for x0 in (xs[0] + ax_w, xs[1] + ax_w):
        fig.patches.append(FancyArrowPatch((x0 + 0.004, y_top + ax_h / 2), (x0 + 0.027, y_top + ax_h / 2),
                                           transform=fig.transFigure, arrowstyle="-|>", mutation_scale=12,
                                           lw=1.4, color="black"))

    # bottom row (right to left): features -> MSCKF box (under panel 3) -> trajectory
    bx, by, bw, bh = xs[2] + 0.02, 0.17, ax_w - 0.04, 0.17
    fig.patches.append(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.01,rounding_size=0.02",
                                      transform=fig.transFigure, fc="#eef3ff", ec="blue", lw=1.2))
    fig.text(bx + bw / 2, by + bh * 0.5, "MSCKF", ha="center", va="center", fontsize=20,
             color="blue")
    cx = bx + bw / 2
    fig.patches.append(FancyArrowPatch((cx, y_top - 0.015), (cx, by + bh + 0.012), transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=12, lw=1.4, color="black"))
    fig.patches.append(FancyArrowPatch((bx - 0.012, by + bh / 2), (0.635, by + bh / 2),
                                       transform=fig.transFigure, arrowstyle="-|>", mutation_scale=12,
                                       lw=1.4, color="black"))
    fig.text(cx, 0.03, "IMU", ha="center", fontsize=14)
    fig.patches.append(FancyArrowPatch((cx, 0.085), (cx, by - 0.012), transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=10, lw=1.1, color="black"))

    axt = fig.add_axes([0.03, 0.04, 0.40, 0.43])
    axt.plot(pg[:, 0], pg[:, 1], color="black", lw=1.6, label="Ground truth")
    axt.plot(po_a[:, 0], po_a[:, 1], color="blue", lw=2.0, label="OpenVINS")
    axt.plot(ps_a[:, 0], ps_a[:, 1], color="red", lw=2.6, label="SAVIOR")
    axt.set_aspect("equal", adjustable="datalim")
    axt.set_xticks([]); axt.set_yticks([])
    axt.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=12, frameon=False, handlelength=1.6)
    fig.savefig(OUT + ".pdf")
    fig.savefig(OUT + ".png", dpi=300)
    print("wrote", OUT + ".pdf/.png", "| moving ids:", len(moving_ids), "| features:", len(pts),
          "rejected:", int(sum(movd[int(y), int(x)] for x, y in pts)))


if __name__ == "__main__":
    main()
