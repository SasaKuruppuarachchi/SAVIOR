#!/usr/bin/env python3
"""Generate every data figure of the SAVIOR v2 paper draft from the stored result tables.

Run inside the SAVIOR image (matplotlib + numpy + yaml):
    src/savior/docker/exec.sh python3 paper/scripts/make_figures.py
Inputs are read-only: results/<phase>/tables/*, results/<phase>/<seq>/<method>/eval/samples.npz,
data/warehouse/preview/*.png, results/p6_warehouse/figures/qual_*.png.
Outputs: paper/figures/*.pdf and *.png (300 dpi). fig_timing is generated but not used in the v2 draft (Table XI instead).
No number is computed here that is not already in a result table, except (i) per-run success-rate curves
(empirical CDF of the stored per-run ATE values) and (ii) RPE box plots of the stored per-segment samples.
"""
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mpatches  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

WS = "/home/sasa/workspace/savior_ws"
RES = os.path.join(WS, "results")
OUT = os.path.join(WS, "paper", "figures")
STYLE = os.path.join(WS, "src/savior/savior_eval/savior_eval/paper.mplstyle")
plt.style.use(STYLE)

SINGLE = 3.5
DOUBLE = 7.16

# fixed colour per method (FIGURE_STYLE.md): OpenVINS blue, SAVIOR red, variants black/green/magenta/orange
C = {
    "openvins": "blue",
    "savior": "red",          # current SAVIOR = YOLO + promotion + motion evidence (P4); P7 later
    "oracle": "black",        # perfect selective (moving-object) masks
    "naive": "green",         # YOLO class masking
    "oracle_naive": "magenta",  # perfect class masks
    "p2": "orange",           # YOLO + promotion, no motion evidence
}
LABEL = {
    "openvins": "OpenVINS",
    "savior": "SAVIOR-PM",
    "oracle": "Oracle dyn.-outlier",
    "naive": "YOLO class-level",
    "oracle_naive": "Oracle class-level",
    "p2": "SAVIOR-P",
}


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"))
    plt.close(fig)
    print("wrote", name)


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def paired(path):
    with open(path) as f:
        return json.load(f)


def find(rows, group, method, ref):
    for r in rows:
        if r["group"] == group and r["method"] == method and r["ref"] == ref:
            return r
    raise KeyError((group, method, ref))


# ---------------------------------------------------------------------------------------------------- trend
def fig_trend():
    p3a = paired(f"{RES}/p3a/tables/paired_ate.json")
    p5 = paired(f"{RES}/p5_viode/tables/paired_ate.json")
    p6 = paired(f"{RES}/p6_warehouse/tables/paired_ate.json")
    fig, axs = plt.subplots(1, 3, figsize=(DOUBLE, 1.85), sharey=True,
                            gridspec_kw=dict(width_ratios=[3, 4, 4], wspace=0.08))

    def plot(ax, xs, vals, key, dx, marker):
        y = [v[0] for v in vals]
        lo = [v[0] - v[1] for v in vals]
        hi = [v[2] - v[0] for v in vals]
        ax.errorbar(np.array(xs) + dx, y, yerr=[lo, hi], color=C[key], marker=marker, ms=3.5, lw=1.0,
                    capsize=2, label=LABEL[key])

    # (a) uHumans2: P3a reports method-minus-reference in % of the reference mean (negative = better)
    ax = axs[0]
    xs = [0, 1, 2]
    vals = []
    for g in ("00h", "06h", "12h"):
        r = find(p3a, g, "oracle_person", "savior_none")
        mref = r["mean"] / (r["pct"] / 100.0) if r["pct"] != 0 else 1.0
        vals.append((r["pct"], 100 * r["ci"][0] / mref, 100 * r["ci"][1] / mref))
    plot(ax, xs, vals, "oracle", 0.0, "o")
    ax.set_xticks(xs)
    ax.set_xticklabels(["0", "6", "12"])
    ax.set_xlabel("humans in scene")
    ax.set_title("uHumans2", fontsize=9)
    ax.set_ylabel("ATE change (%)")
    # (b) VIODE pooled over 3 environments per level
    ax = axs[1]
    lv = ["none", "low", "mid", "high"]
    for key, m, dx, mk in (("oracle", "oracle_dynamic", -0.15, "o"), ("naive", "yolo_naive", 0.0, "^"),
                           ("savior", "yolo_p4_pot", 0.15, "s")):
        vals = []
        for l in lv:
            r = find(p5, f"all_{l}", m, "openvins")
            vals.append((r["gm_ratio_pct"], r["ci_pct"][0], r["ci_pct"][1]))
        plot(ax, range(4), vals, key, dx, mk)
    ax.set_xticks(range(4))
    ax.set_xticklabels(lv)
    ax.set_xlabel("VIODE dynamic level")
    ax.set_title("VIODE (3 env.)", fontsize=9)
    # (c) warehouse pooled over aisles + hall per level
    ax = axs[2]
    for key, m, dx, mk in (("oracle", "oracle_moving_ext", -0.2, "o"), ("oracle_naive", "oracle_class_naive", -0.07, "D"),
                           ("naive", "yolo_naive", 0.07, "^"), ("savior", "yolo_p4", 0.2, "s")):
        vals = []
        for l in ("L0", "L1", "L2", "L3"):
            r = find(p6, f"all_{l}", m, "openvins")
            vals.append((r["gm_ratio_pct"], r["ci_pct"][0], r["ci_pct"][1]))
        plot(ax, range(4), vals, key, dx, mk)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["L0", "L1", "L2", "L3"])
    ax.set_xlabel("SAVIOR-Warehouse level")
    ax.set_title("SAVIOR-Warehouse (2 scenes)", fontsize=9)
    for a in axs:
        a.axhline(0, color=C["openvins"], lw=1.0, ls="--")
        a.set_ylim(-100, 110)
    h, l = axs[2].get_legend_handles_labels()
    h0, l0 = axs[1].get_legend_handles_labels()
    order = {}
    for hh, ll in list(zip(h0, l0)) + list(zip(h, l)):
        order.setdefault(ll, hh)
    axs[0].legend(list(order.values()), list(order.keys()), loc="lower left", fontsize=6.3)
    save(fig, "fig_trend")


# ---------------------------------------------------------------------------------------------------- share vs gain
def fig_share_gain():
    v = read_csv(f"{RES}/p5_viode/tables/share_vs_gain.csv")
    w = read_csv(f"{RES}/p6_warehouse/tables/share_vs_gain.csv")
    with open(f"{RES}/p6_warehouse/tables/share_vs_gain_corr.yaml") as f:
        corr = yaml.safe_load(f)
    fig, axs = plt.subplots(1, 2, figsize=(DOUBLE * 0.72, 1.85), sharey=True, gridspec_kw=dict(wspace=0.08))
    for ax, col, key, xl in ((axs[0], "px_dyn", "px_dyn", "moving pixel share (%)"),
                             (axs[1], "msckf_used_meas_dyn", "msckf_used_meas_dyn", "MSCKF-used share, movers (%)")):
        xv = [100 * float(r[col]) for r in v]
        yv = [float(r["gain_oracle_dynamic_pct"]) for r in v]
        xw = [100 * float(r[col]) for r in w]
        yw = [float(r["gain_oracle_moving_pct"]) for r in w]
        ax.scatter(np.maximum(xv, 0.01), yv, s=14, marker="o", facecolors="none", edgecolors="black", label="VIODE")
        ax.scatter(np.maximum(xw, 0.01), yw, s=14, marker="s", color="black", label="SAVIOR-Warehouse")
        ax.set_xscale("log")
        ax.axhline(0, color=C["openvins"], lw=0.8, ls="--")
        c = corr[f"combined: gain_oracle_moving_pct ~ {key}"]
        ax.text(0.04, 0.95, f"Spearman $\\rho$ = {c['spearman_rho']:.2f}\n$p$ = {c['p']:.1e}, n = {c['n']}",
                transform=ax.transAxes, va="top", fontsize=6.5)
        ax.set_xlabel(xl)
    axs[0].set_ylabel("oracle ATE reduction (%)")
    axs[1].legend(loc="lower right", fontsize=6.3)
    save(fig, "fig_share_gain")


# ---------------------------------------------------------------------------------------------------- feature fates
def fig_fates():
    fig, axs = plt.subplots(1, 2, figsize=(DOUBLE, 1.9), gridspec_kw=dict(width_ratios=[1.0, 1.25], wspace=0.25))
    # (a) fate of dynamic tracks: uHumans2 (P3a feature_fates.md, mean of the two 06h / three 12h logged
    #     baseline-equivalent runs, transcribed below with the run names) and VIODE (feature_fates.txt)
    p3a_rows = {  # used / chi2 / trifail / few [%] from results/p3a/tables/feature_fates.md
        "06h": [(9, 29, 41, 20), (12, 28, 36, 20)],               # 06h_observe_run01, run03
        "12h": [(9, 26, 42, 20), (8, 29, 36, 23), (11, 27, 40, 20)],  # 12h_observe_run01, run03, 12h_openvins_run01
    }
    labels, fates = [], []
    for k, rows in p3a_rows.items():
        labels.append(f"uH2 {k}")
        fates.append(np.mean(np.array(rows, float), axis=0) / 100.0)
    with open(f"{RES}/p5_viode/tables/feature_fates.txt") as f:
        lines = [l for l in f.read().splitlines()[1:] if l.strip()]
    short = {"parking_lot": "PL", "city_day": "CD", "city_night": "CN"}
    for l in lines:
        c = [x.strip() for x in l.split("|")]
        seq = c[0]
        if not seq.endswith("high") and not seq.endswith("mid"):
            continue
        env, lvl = seq.rsplit("_", 1)
        labels.append(f"{short[env]} {lvl}")
        fates.append(np.array([float(x) for x in c[8].split("/")]))
    fates = np.array(fates)
    ax = axs[0]
    names = ["used in update", "$\\chi^2$-rejected", "triangulation failed", "< 2 measurements"]
    cols = ["red", "0.25", "0.55", "0.85"]
    bottom = np.zeros(len(labels))
    for j in range(4):
        ax.bar(range(len(labels)), fates[:, j], bottom=bottom, color=cols[j], edgecolor="black", lw=0.4,
               label=names[j], width=0.7)
        bottom += fates[:, j]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("share of dynamic tracks")
    ax.set_ylim(0, 1.25)
    ax.set_title("Fate of Dynamic Feature Tracks", fontsize=9)
    ax.legend(loc="upper center", ncol=2, fontsize=6.0)
    # (b) warehouse, stock OpenVINS: kept vs MSCKF-used share on moving and on static potential objects
    rows = [r for r in read_csv(f"{RES}/p6_warehouse/tables/feature_fates.csv") if r["method"] == "openvins"]
    seqs = [r["seq"].replace("_t1_", " ") for r in rows]
    x = np.arange(len(rows))
    wdt = 0.2
    sets = [("kept_moving", "kept, moving", "white", "black", ""),
            ("used_moving", "MSCKF-used, moving", "black", "black", ""),
            ("kept_static_pot", "kept, static pot. dyn.", "white", "black", "////"),
            ("used_static_pot", "MSCKF-used, static pot. dyn.", "0.6", "black", "////")]
    ax = axs[1]
    for i, (k, lab, fc, ec, hatch) in enumerate(sets):
        ax.bar(x + (i - 1.5) * wdt, [100 * float(r[k]) for r in rows], width=wdt, color=fc, edgecolor=ec,
               hatch=hatch, lw=0.5, label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels(seqs, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("share (%)")
    ax.set_ylim(0, 62)
    ax.set_title("Where Measurements Come From (OpenVINS)", fontsize=9)
    ax.legend(loc="upper left", fontsize=6.0, ncol=2)
    save(fig, "fig_fates")


# ---------------------------------------------------------------------------------------------------- dynamic-outlier vs class-level
def fig_selective():
    p6 = paired(f"{RES}/p6_warehouse/tables/paired_ate.json")
    groups = ["all_L0", "all_L1", "all_L2", "all_L3", "all_L2+L3"]
    glab = ["L0", "L1", "L2", "L3", "L2+L3"]
    meths = [("oracle", "oracle_moving_ext", "o"), ("oracle_naive", "oracle_class_naive", "D"),
             ("naive", "yolo_naive", "^"), ("p2", "yolo_p2", "v"), ("savior", "yolo_p4", "s")]
    fig, axs = plt.subplots(1, 2, figsize=(DOUBLE, 2.0), gridspec_kw=dict(width_ratios=[1.35, 1.0], wspace=0.28))
    ax = axs[0]
    nm = len(meths)
    for gi, g in enumerate(groups):
        for mi, (key, m, mk) in enumerate(meths):
            r = find(p6, g, m, "openvins")
            y = gi + (mi - (nm - 1) / 2) * 0.15
            ratio = 1 + r["gm_ratio_pct"] / 100
            lo, hi = 1 + r["ci_pct"][0] / 100, 1 + r["ci_pct"][1] / 100
            ax.plot([lo, hi], [y, y], color=C[key], lw=1.0)
            ax.plot(ratio, y, marker=mk, color=C[key], ms=3.5, ls="none", label=LABEL[key] if gi == 0 else None)
    ax.axvline(1.0, color=C["openvins"], ls="--", lw=1.0)
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2])
    ax.set_xticklabels(["0.1", "0.2", "0.5", "1", "2"])
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(glab)
    ax.invert_yaxis()
    ax.set_xlabel("ATE ratio to OpenVINS (geom. mean, 95 % CI)")
    ax.set_title("Paired Effect per Dynamic Level", fontsize=9)
    ax.set_xlim(0.04, 2.6)
    # (b) feature budget (kept features vs OpenVINS), mean of the two scenes per level
    fb = read_csv(f"{RES}/p6_warehouse/tables/feature_budget.csv")
    ax = axs[1]
    for key, m, mk in meths:
        ys = []
        for l in ("L0", "L1", "L2", "L3"):
            vals = [float(r["kept_vs_openvins_pct"]) for r in fb if r["method"] == m and r["seq"].endswith(l)]
            ys.append(np.mean(vals))
        ax.plot(range(4), ys, marker=mk, color=C[key], ms=3.5, label=LABEL[key])
    ax.axhline(0, color=C["openvins"], ls="--", lw=1.0)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["L0", "L1", "L2", "L3"])
    ax.set_ylabel("kept-feature change (%)")
    ax.set_xlabel("dynamic level (mean of 2 scenes)")
    ax.set_title("Feature Budget", fontsize=9)
    ax.legend(loc="lower left", fontsize=6.0)
    save(fig, "fig_selective")


# ---------------------------------------------------------------------------------------------------- success CDF
def per_run(path, seqs, method, fail_thr):
    out = []
    for r in read_csv(path):
        if r["seq"] in seqs and r["method"] == method:
            for i in range(1, 11):
                v = r.get(f"ate_run{i:02d}", "")
                try:
                    x = float(v)
                except ValueError:
                    x = math.inf
                if not math.isfinite(x):
                    x = math.inf
                out.append(x)
    return np.array(out)


def fig_success():
    fig, axs = plt.subplots(2, 1, figsize=(SINGLE, 3.1), gridspec_kw=dict(hspace=0.55))
    thr = np.logspace(np.log10(0.03), np.log10(3.0), 300)
    wh = f"{RES}/p6_warehouse/tables/methods.csv"
    seqs = {"aisles_t1_L2", "aisles_t1_L3", "hall_t1_L2", "hall_t1_L3"}
    for key, m in (("openvins", "openvins"), ("oracle", "oracle_moving_ext"), ("oracle_naive", "oracle_class_naive"),
                   ("naive", "yolo_naive"), ("p2", "yolo_p2"), ("savior", "yolo_p4")):
        a = per_run(wh, seqs, m, 2.0)
        axs[0].plot(thr, [(a <= t).mean() for t in thr], color=C[key], label=f"{LABEL[key]} (n={len(a)})")
    vi = f"{RES}/p5_viode/tables/methods.csv"
    vseqs = {"parking_lot_high", "city_day_high", "city_night_high"}
    for key, m in (("openvins", "openvins"), ("oracle", "oracle_dynamic"), ("naive", "yolo_naive"),
                   ("savior", "yolo_p4_pot")):
        a = per_run(vi, vseqs, m, 1.0)
        axs[1].plot(thr, [(a <= t).mean() for t in thr], color=C[key], label=f"{LABEL[key]} (n={len(a)})")
    for ax, t, ft in ((axs[0], "SAVIOR-Warehouse L2+L3", 2.0), (axs[1], "VIODE high", 1.0)):
        ax.set_xscale("log")
        ax.set_xlabel("ATE threshold (m)")
        ax.set_title(t, fontsize=9)
        ax.axvline(ft, color="0.5", ls=":", lw=0.8)
        ax.set_ylim(0, 1.02)
        ax.legend(loc="lower right", fontsize=5.6)
    axs[0].set_ylabel("success rate (ATE $\\leq$ thr.)")
    save(fig, "fig_success")


# ---------------------------------------------------------------------------------------------------- RPE boxes
def fig_rpe():
    seqs = [("hall_t1_L2", "(a) hall L2"), ("aisles_t1_L3", "(b) aisles L3")]
    meths = [("openvins", "openvins"), ("oracle", "oracle_moving_ext"), ("naive", "yolo_naive"), ("savior", "yolo_p4")]
    fig, axs = plt.subplots(2, 2, figsize=(DOUBLE, 2.3), sharex="col", gridspec_kw=dict(hspace=0.12, wspace=0.2))
    for ci, (seq, title) in enumerate(seqs):
        lens = None
        for mi, (key, m) in enumerate(meths):
            s = np.load(f"{RES}/p6_warehouse/{seq}/{m}/eval/samples.npz")
            ls = sorted({k.split("_")[-1] for k in s.files if k.startswith("rpe_trans_m_")}, key=float)
            lens = ls if lens is None else lens
            for row, metric in ((0, "rpe_rot_deg_"), (1, "rpe_trans_m_")):   # orientation on top (FIGURE_STYLE)
                data = [s[metric + L] for L in lens]
                pos = np.arange(len(lens)) + (mi - 1.5) * 0.19
                b = axs[row, ci].boxplot(data, positions=pos, widths=0.15, notch=True, showfliers=False,
                                         patch_artist=False)
                for part in ("boxes", "whiskers", "caps", "medians"):
                    for it in b[part]:
                        it.set_color(C[key])
                        it.set_linewidth(0.9)
                if row == 0 and ci == 0:
                    axs[row, ci].plot([], [], color=C[key], label=LABEL[key])
        for row in (0, 1):
            axs[row, ci].set_xticks(range(len(lens)))
            axs[row, ci].set_xticklabels([f"{float(L):.0f}" for L in lens])
        axs[0, ci].set_title(f"Relative Pose Error, {title[4:]}", fontsize=9)
        axs[1, ci].set_xlabel("sub-trajectory length (m)")
    axs[0, 0].set_ylabel("orientation (deg)", fontsize=8)
    axs[1, 0].set_ylabel("position (m)", fontsize=8)
    fig.align_ylabels(axs[:, 0])
    axs[0, 0].legend(loc="upper left", fontsize=6.0, ncol=2)
    save(fig, "fig_rpe")


# ---------------------------------------------------------------------------------------------------- timing
def fig_timing():
    rows = {(r["method"], r["group"]): r for r in read_csv(f"{RES}/p6_warehouse/tables/timing.csv")}
    meths = [("oracle_moving_ext", "Oracle dyn.-outlier"), ("yolo_naive", "YOLO class-level"), ("yolo_p2", "SAVIOR-P"),
             ("yolo_p4", "SAVIOR-PM")]
    stages = [("segment", "segment", "0.15"), ("depth", "ROI depth", "0.45"), ("motion", "motion", "red"),
              ("gating", "promotion", "orange"), ("extension", "extension", "green"), ("compose", "compose", "0.75")]
    fig, ax = plt.subplots(figsize=(SINGLE, 2.2))
    labels = []
    y = 0
    for m, lab in meths:
        r = rows[(m, "L2+L3")]
        left = 0.0
        for k, sl, col in stages:
            v = r[f"{k}_med"]
            v = 0.0 if v in ("", "nan") or math.isnan(float(v)) else float(v)
            ax.barh(y, v, left=left, color=col, edgecolor="black", lw=0.3, height=0.6,
                    label=sl if y == 0 else None)
            left += v
        ax.plot(float(r["node_total_p90"]), y, marker="|", color="black", ms=8)
        labels.append(lab + " (desktop)")
        y += 1
    ax.barh(y, 0, height=0.6)
    ax.text(1, y, "Jetson Orin NX: pending", va="center", fontsize=6.5, color="red")
    labels.append("SAVIOR (Orin NX)")
    ax.axvline(50, color="0.4", ls="--", lw=0.8)
    ax.text(51, -0.6, "50 ms budget", fontsize=6.0, color="0.3")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("median per-frame time (ms); | = node p90")
    ax.set_title("Per-Stage Timing (warehouse L2+L3)", fontsize=9)
    ax.legend(loc="lower right", fontsize=5.6, ncol=2)
    save(fig, "fig_timing")


# ---------------------------------------------------------------------------------------------------- dataset + qualitative
def fig_dataset():
    prev = f"{WS}/data/warehouse/preview"
    picks = [("aisles_t1_L3_f01392.png", "aisles L3"), ("hall_t1_L3_f00812.png", "hall L3")]
    cols = ["cam0 (left)", "GT instance classes", "GT moving instances"]
    fig, axs = plt.subplots(2, 3, figsize=(DOUBLE, 2.55), gridspec_kw=dict(wspace=0.03, hspace=0.05))
    for i, (fn, lab) in enumerate(picks):
        im = plt.imread(os.path.join(prev, fn))
        h, w = im.shape[0] // 2, im.shape[1] // 2
        pad = 22  # skip the text banner of the preview
        axs[i, 0].imshow(im[pad:h, :w])
        axs[i, 1].imshow(im[h + pad:, :w])
        axs[i, 2].imshow(im[h + pad:, w:])
        axs[i, 0].set_ylabel(lab, fontsize=8)
    for j, c in enumerate(cols):
        axs[0, j].set_title(c, fontsize=8)
    for a in axs.ravel():
        a.set_xticks([])
        a.set_yticks([])
    save(fig, "fig_dataset")


QUAL_LABELS = ["input", "GT: dyn. outlier (red) / static pot. dyn. (blue)", "Oracle class-level",
               "YOLO class-level", "SAVIOR-PM", "SAVIOR-PM + revocation, H=2 (post-hoc)"]


def relabel(src, dst):
    """Copy a 3x2 qualitative overlay grid and replace the run names burnt into each tile by the paper names."""
    import cv2
    im = cv2.imread(src)
    th, tw = im.shape[0] // 2, im.shape[1] // 3
    for k, lab in enumerate(QUAL_LABELS):
        y0, x0 = (k // 3) * th, (k % 3) * tw
        im[y0:y0 + 26, x0:x0 + tw] = (0.05 * im[y0:y0 + 26, x0:x0 + tw]).astype(im.dtype)
        cv2.putText(im, lab, (x0 + 6, y0 + 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(dst, im)


def copy_static():
    q = f"{RES}/p6_warehouse/figures"
    relabel(f"{q}/qual_hall_t1_L3_1700000061450000000.png", f"{OUT}/qual_hall_L3.png")
    relabel(f"{q}/qual_aisles_t1_L2_1700000077450000000.png", f"{OUT}/qual_aisles_L2.png")
    print("copied qualitative overlays (relabelled)")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    todo = sys.argv[1:] or ["trend", "share_gain", "fates", "selective", "success", "rpe", "timing",
                            "dataset", "static"]
    for t in todo:
        {"trend": fig_trend, "share_gain": fig_share_gain, "fates": fig_fates,
         "selective": fig_selective, "success": fig_success, "rpe": fig_rpe, "timing": fig_timing,
         "dataset": fig_dataset, "static": copy_static}[t]()
