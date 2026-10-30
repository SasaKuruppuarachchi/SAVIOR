#!/usr/bin/env python3
"""Fig. 4 analogue of the SAVIOR paper: step-by-step classification and post-processing of dynamic outliers.

Frame: SAVIOR-Warehouse aisles_t1_L2, frame FRAME (default 127, t = 6.35 s; tuning split t1 only, never t2/t3).
A driven forklift carries a pallet with four boxes (person -> forklift -> load), a walking person passes in
front, and static potentially dynamic objects (rack boxes, a box stack on the right) touch the chain in 2D
at a larger depth. One frame is used for all seven panels.
Frame choice: the original frame 125 (t = 6.25 s) was moved later so that the driver and the passer-by are
separated in the image. The passer-by (P1) leaves the image after frame 132 (t = 6.60 s), so a frame at 7.25-8.25 s
cannot show the scene. Among frames 126-132, 127 is the only one where the driver and passer-by masks are separated
(22.9 px gap; 125/126: touching), the box stack is refused by the depth gate (8.2 / 8.8 m), the
person -> forklift -> load chain is intact (load at 2-3 hops) and no static object of >= 200 px is promoted
(128, 129, 131, 132: false promotions of rack boxes or PF2; 130: no box-stack refusal). Checked with a per-frame
SAVIOR-P pass (driver/P1 mask gap, refused objects in contact, false promotions).

Detector: the GT instance segmentation (one instance per GT id) replaces YOLO26-seg, so that the figure shows
the classification logic rather than segmentation errors. Every later stage is savior_perception's own code,
run with the SAVIOR-P / SAVIOR-PM configurations of results/p6_warehouse/methods.yaml (contact depth gate with
0.5 m noise cap, depth-guided extension, no tracker):
  * SAVIOR-P pass (no motion evidence) on the frame: panels (2)-(4), the interaction cues alone;
  * SAVIOR-PM pass over the preceding 2 s (HISTORY = 40 frames; gyro of imu_noisy.csv + stereo): panel (5) motion
    evidence and the final masks of panels (6)-(7). At this frame no potentially dynamic object has a static
    decision (panel 5 shows moving vs undecided): the windowed test confirms "static" only when
    |v_rad| + 2 sigma_rad < 0.6 m/s, i.e. for objects within about 4 m on this rig (fb = 56.4 px m, 0.6 px anchor
    disparity jitter, 0.8 s window; derived from the motion.* defaults); the first static decisions of aisles_t1_L2
    occur at frames 340-400. find_promotion_frame.py (stage 3) found no t1 L2/L3 frame with both the full promotion
    story and a correct static decision on a potentially dynamic object.
Panel (2) and the per-link depth tests of panel (3) are re-evaluated with the pipeline's own PromotionGate
predicates (overlap_px, depth_compatible) on the instances of the SAVIOR-P pass.
Features in panel (7): FAST corners selected on a 5x5 grid (150 per image, threshold 20, 10 px spacing), as
configured for OpenVINS on this dataset; "removed" = on a mask pixel >= 128 (core or band).

Usage (inside the savior image):  python3 paper/scripts/make_promotion_figure.py
Outputs: paper/figures/fig_promotion.pdf/.png and thumb_left/thumb_right/thumb_depth.png (used by fig_system).
Frame: FRAME environment variable (default 127).
"""
import json
import math
import os
import sys

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promotion_common import WS, gt_instances, gyro, make_pipeline, read_moving  # noqa: E402
from savior_perception.core.types import MASK_CORE, MASK_EXTENSION  # noqa: E402

SEQ = "aisles_t1_L2"
FRAME = int(os.environ.get("FRAME", 127))   # t = 6.35 s, all seven panels
HISTORY = 40          # SAVIOR-PM pass: frames before FRAME (2 s at 20 Hz)
RAW = f"{WS}/data/warehouse/raw/{SEQ}"
OUT = f"{WS}/paper/figures"
plt.style.use(f"{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle")

RED = np.array([230, 25, 25])
ORANGE = np.array([255, 140, 0])
CYAN = np.array([0, 190, 230])
GREEN = np.array([40, 175, 60])
YELLOW = np.array([255, 225, 0])
BLUE = np.array([40, 80, 230])


def frame_list():
    rows = [l.strip().split(",") for l in open(f"{RAW}/frames.csv") if not l.startswith("#")]
    return [(int(f), ts) for f, ts in rows]


def run_pass(meta, motion):
    pipe = make_pipeline(RAW, motion=motion)
    frames = frame_list()
    seq = frames[FRAME - HISTORY:FRAME + 1] if motion else frames[FRAME:FRAME + 1]
    g = gyro(RAW) if motion else None
    prev = None
    for f, ts in seq:
        left = cv2.imread(f"{RAW}/cam0/{ts}.png", cv2.IMREAD_GRAYSCALE)
        right = cv2.imread(f"{RAW}/cam1/{ts}.png", cv2.IMREAD_GRAYSCALE)
        insts = gt_instances(RAW, ts, meta, pipe.roles)
        t = int(ts) * 1e-9
        R = g.rotation(prev, t) if (g is not None and prev is not None) else None
        prev = t
        ml, _, st = pipe.process(left, right, t, insts, R_imu=R)
    return pipe, insts, ml, st, ts


def tint(base, mask, color, a=0.55):
    out = base.copy()
    out[mask] = (1 - a) * out[mask] + a * color
    return out


def outline(img, mask, color, th=1):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, tuple(float(c) for c in color), th)


def centroid(m):
    ys, xs = np.nonzero(m)
    return float(xs.mean()), float(ys.mean())


def features(gray):
    """FAST corners on a 5x5 grid, 150 per image (OpenVINS front-end settings of this dataset)."""
    h, w = gray.shape
    fast = cv2.FastFeatureDetector_create(threshold=20)
    pts = []
    per = int(math.ceil(150 / 25))
    for gy in range(5):
        for gx in range(5):
            x0, x1, y0, y1 = gx * w // 5, (gx + 1) * w // 5, gy * h // 5, (gy + 1) * h // 5
            kps = sorted(fast.detect(gray[y0:y1, x0:x1]), key=lambda k: -k.response)
            sel = []
            for k in kps:
                p = (k.pt[0] + x0, k.pt[1] + y0)
                if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= 100 for q in sel):
                    sel.append(p)
                if len(sel) >= per:
                    break
            pts += sel
    return np.array(pts)


def main():
    meta = {i["id"]: i for i in json.load(open(f"{RAW}/instances.json"))["instances"]}
    name = lambda x: meta[x.gt_id]["name"]  # noqa: E731
    mov_ids = read_moving(RAW)[FRAME][1]

    # ---------------- SAVIOR-P pass (interaction cues only)
    pP, iP, mlP, stP, ts = run_pass(meta, motion=False)
    assert "_t1_" in SEQ
    gate = pP.gate
    dil = {k: gate._dilated(x) for k, x in enumerate(iP) if x.role in ("dynamic", "potential")}
    roots = [k for k, x in enumerate(iP) if x.status == "root"]
    dyn = [k for k, x in enumerate(iP) if x.is_dynamic]
    pot = [k for k, x in enumerate(iP) if x.role == "potential"]

    def touches(k, group):
        return any(gate.overlap_px(dil[k], dil[q]) >= gate.cfg.min_overlap_px for q in group if q != k)
    overlap_root = [k for k in pot if touches(k, roots)]
    contact_chain = [k for k in pot if touches(k, dyn)]
    refused = [k for k in contact_chain if not iP[k].is_dynamic]
    promoted = [k for k in pot if iP[k].status == "promoted"]

    def hop(k):
        return 0 if iP[k].parent < 0 else 1 + hop(iP[k].parent)

    img = cv2.cvtColor(cv2.imread(f"{RAW}/cam0/{ts}.png"), cv2.COLOR_BGR2RGB).astype(float)
    gray = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g3 = np.repeat(gray[..., None], 3, 2).astype(float)
    base = 0.6 * g3 + 0.4 * img
    H, W = gray.shape
    fb = pP.rect.fb

    print("frame", SEQ, FRAME, ts, "| roots:", [name(iP[k]) for k in roots])
    print("overlap with always-dynamic:", [name(iP[k]) for k in overlap_root])
    print("promoted:", [(name(iP[k]), hop(k), name(iP[iP[k].parent])) for k in promoted])
    print("refused in contact:", [(name(iP[k]), round(iP[k].depth, 1)) for k in refused])
    print("false promotions (static GT):", [(name(iP[k]), iP[k].area) for k in promoted if iP[k].gt_id not in mov_ids])

    # ---------------- SAVIOR-PM pass (motion evidence over 2 s)
    pM, iM, mlM, stM, tsM = run_pass(meta, motion=True)
    assert tsM == ts
    mstate = {x.gt_id: (x.motion or {}).get("state", "none") for x in iM}
    print("motion states:", {name(x): mstate[x.gt_id] for x in iM if x.area > 1500})
    import collections
    print("motion state counts:", collections.Counter(mstate.values()),
          "static:", [(name(x), x.area) for x in iM if mstate.get(x.gt_id) == "static"][:12])
    print("depths of false promotions:", [(name(iP[k]), iP[k].depth) for k in promoted if iP[k].gt_id not in mov_ids])
    print("PM statuses:", {name(x): x.status for x in iM if x.area > 1500})

    # ---------------- panels
    P = []
    # (1) detection
    p = base.copy()
    for x in iP:
        p = tint(p, x.mask, RED if x.role == "dynamic" else CYAN)
    p = np.clip(p, 0, 255)
    for x in iP:
        outline(p, x.mask, RED if x.role == "dynamic" else CYAN)
    P.append(("(1) Detection", p, []))
    # (2) overlap with always-dynamic outliers
    p = base.copy()
    for k in roots:
        p = tint(p, iP[k].mask, RED)
    for k in overlap_root:
        p = tint(p, iP[k].mask, YELLOW, 0.6)
    p = np.clip(p, 0, 255)
    for k in overlap_root:
        outline(p, iP[k].mask, ORANGE)
    P.append(("(2) Overlap", p, []))
    # (3) depth gate: ROI stereo depth of the chain and of the objects in contact with it
    p = 0.85 * g3
    show = sorted(set(dyn) | set(contact_chain))
    cmap = plt.get_cmap("turbo_r")
    zmin, zmax = 1.5, 15.0
    for k in show:
        x = iP[k]
        if x.disp_crop is None or x.work_box is None:
            continue
        x0, y0, x1, y1 = x.work_box
        d = x.disp_crop
        m = x.mask[y0:y1, x0:x1] & (d > 0)
        z = fb / np.where(d > 0, d, np.nan)
        col = cmap(np.clip((z - zmin) / (zmax - zmin), 0, 1))[..., :3] * 255
        sub = p[y0:y1, x0:x1]
        sub[m] = 0.25 * sub[m] + 0.75 * col[m]
    p = np.clip(p, 0, 255)
    for k in refused:
        outline(p, iP[k].mask, GREEN, 2)
    for k in dyn:
        outline(p, iP[k].mask, RED, 1)
    labels3 = []
    # labelled: the forklift (1 hop) and a carried box (2 hops) accepted; two objects in contact refused
    stack = sorted((k for k in refused if name(iP[k]).startswith("stackC.") and math.isfinite(iP[k].depth)),
                   key=lambda k: -iP[k].area)
    stack_nm = name(iP[stack[0]]) if stack else "stackC.box2"     # largest refused box-stack instance
    for nm, dx, dy in (("F1", 470, 345), ("F1.box3", 150, 130), (stack_nm, 560, 120)):
        ks = [k for k in (dyn + refused) if name(iP[k]) == nm]
        if not ks or not math.isfinite(iP[ks[0]].depth):
            continue
        x = iP[ks[0]]
        labels3.append((x, f"{x.depth:.1f}$\\pm${x.sigma_z:.1f} m", "ok" if x.is_dynamic else "no", dx, dy))
        print("label", nm, "centroid", [round(v) for v in centroid(x.mask)], "bbox", x.bbox)
    P.append(("(3) Depth gate", p, labels3))
    # (4) association tree (SAVIOR-P): roots red, promoted orange; BFS tree edges between centroids
    p = base.copy()
    for k in dyn:
        p = tint(p, iP[k].mask, RED if iP[k].status == "root" else ORANGE, 0.6)
    for k in refused:
        p = tint(p, iP[k].mask, GREEN, 0.45)
    p = np.clip(p, 0, 255)
    edges = [(centroid(iP[iP[k].parent].mask), centroid(iP[k].mask)) for k in promoted
             if iP[k].area >= 1500 and iP[iP[k].parent].area >= 1500]
    P.append(("(4) Association tree", p, edges))
    # (5) motion evidence (SAVIOR-PM)
    p = base.copy()
    col_state = {"moving": RED, "static": BLUE}
    for x in iM:
        if x.role not in ("dynamic", "potential"):
            continue
        st = mstate.get(x.gt_id, "none")
        if st in col_state:
            p = tint(p, x.mask, col_state[st], 0.6)
    p = np.clip(p, 0, 255)
    P.append(("(5) Motion evidence", p, []))
    # (6) mask extension band (SAVIOR-PM)
    p = base.copy()
    p = tint(p, mlM == MASK_CORE, RED, 0.6)
    p = tint(p, mlM == MASK_EXTENSION, YELLOW, 0.8)
    P.append(("(6) Mask extension", np.clip(p, 0, 255), []))
    # (7) final dynamic-outlier mask + features
    p = base.copy()
    p = tint(p, mlM >= 128, RED, 0.35)
    p = np.clip(p, 0, 255)
    outline(p, mlM >= 128, RED, 1)
    pts = features(gray)
    rem = np.array([mlM[int(round(y)), int(round(x))] >= 128 for x, y in pts]) if len(pts) else np.zeros(0, bool)
    P.append(("(7) Dynamic-outlier mask", p, pts))
    print("features:", len(pts), "removed:", int(rem.sum()), "| core px", int((mlM == MASK_CORE).sum()),
          "band px", int((mlM == MASK_EXTENSION).sum()))

    # ---------------- figure (double column, two rows)
    fig = plt.figure(figsize=(7.16, 2.92))
    aw = 0.243
    ah = aw * (H / W) * 7.16 / 2.92
    xs = [0.005, 0.254, 0.503, 0.752]
    y1, y2 = 0.535, 0.045
    pos = [(xs[0], y1), (xs[1], y1), (xs[2], y1), (xs[3], y1), (xs[0], y2), (xs[1], y2), (xs[2], y2)]
    axes = []
    for (title, im, extra), (x, y) in zip(P, pos):
        ax = fig.add_axes([x, y, aw, ah])
        ax.imshow(im.astype(np.uint8))
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(0, W); ax.set_ylim(H, 0)
        ax.set_title(title, fontsize=8, pad=2)
        axes.append(ax)
    fs = 6.2
    bb = dict(boxstyle="round,pad=0.15", ec="none", alpha=0.85)
    # (1) tags
    a = axes[0]
    drv = [x for x in iP if name(x) == "F1.driver"][0]
    fk = [x for x in iP if name(x) == "F1"][0]
    cx, cy = centroid(drv.mask)
    a.annotate("always-dynamic", (cx, cy), (cx - 40, 30), fontsize=fs, color="white", ha="right",
               bbox=dict(bb, fc="red"), arrowprops=dict(arrowstyle="-", color="red", lw=0.6))
    a.text(8, H - 12, "potentially dynamic", fontsize=fs, color="black", va="bottom",
           bbox=dict(bb, fc=tuple(CYAN / 255)))
    # (2)
    axes[1].text(8, H - 12, "touches always-dynamic", fontsize=fs, color="black", va="bottom",
                 bbox=dict(bb, fc=tuple(YELLOW / 255)))
    # (3) depth labels
    a = axes[2]
    for x, txt, ok, tx, ty in P[2][2]:
        cx, cy = centroid(x.mask)
        fc = "red" if ok == "ok" else tuple(GREEN / 255)
        far = abs(tx - cx) + abs(ty - cy) > 60
        a.annotate(txt + ("  ✓" if ok == "ok" else "  ✗"), (cx, cy), (tx, ty), fontsize=fs, ha="center",
                   va="center", color="white", bbox=dict(bb, fc=fc),
                   arrowprops=dict(arrowstyle="-", color="white", lw=0.7) if far else None)
    a.text(8, 10, "contact: $|\\Delta z_c| < 0.3\\,\\mathrm{m} + \\min(3\\sigma_c, c)$", fontsize=fs, va="top",
           bbox=dict(bb, fc="white"))
    # (4) tree edges
    a = axes[3]
    for (p0, p1) in P[3][2]:
        a.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color="navy", lw=1.0,
                                                          mutation_scale=7, shrinkA=0, shrinkB=0))
        a.plot(*p0, "o", color="navy", ms=2.5)
    a.text(8, H - 12, "root $\\rightarrow$ promoted", fontsize=fs, va="bottom", color="white",
           bbox=dict(bb, fc=tuple(ORANGE / 255)))
    # (5)
    axes[4].text(8, H - 12, "moving", fontsize=fs, va="bottom", color="white", bbox=dict(bb, fc="red"))
    axes[4].text(165, H - 12, "undecided (prior)", fontsize=fs, va="bottom", color="black", bbox=dict(bb, fc="0.85"))
    if any(v == "static" for v in mstate.values()):
        axes[4].text(400, H - 12, "static", fontsize=fs, va="bottom", color="white", bbox=dict(bb, fc=tuple(BLUE / 255)))
    # (6)
    axes[5].text(8, H - 12, "core (255)", fontsize=fs, va="bottom", color="white", bbox=dict(bb, fc="red"))
    axes[5].text(215, H - 12, "band (192)", fontsize=fs, va="bottom", color="black",
                 bbox=dict(bb, fc=tuple(YELLOW / 255)))
    # (7) features
    a = axes[6]
    if len(pts):
        a.plot(pts[~rem, 0], pts[~rem, 1], "o", ms=2.2, mfc="lime", mec="darkgreen", mew=0.4, ls="none")
        a.plot(pts[rem, 0], pts[rem, 1], "x", ms=2.6, color="red", mew=0.8, ls="none")
    # legend panel
    la = fig.add_axes([xs[3] + 0.01, y2, aw - 0.01, ah])
    la.axis("off")
    hs = [Patch(fc=tuple(RED / 255), ec="none", label="always-dynamic / dynamic outlier"),
          Patch(fc=tuple(ORANGE / 255), ec="none", label="promoted (dynamic outlier)"),
          Patch(fc=tuple(CYAN / 255), ec="none", label="potentially dynamic"),
          Patch(fc=tuple(GREEN / 255), ec="none", label="classified static (kept)"),
          Patch(fc=tuple(YELLOW / 255), ec="none", label="extension band"),
          Line2D([], [], marker="o", ls="none", mfc="lime", mec="darkgreen", ms=3, label="inlier feature: kept"),
          Line2D([], [], marker="x", ls="none", color="red", ms=3.5, label="dynamic-outlier feature: removed")]
    la.legend(handles=hs, loc="center left", fontsize=6.2, frameon=True, handlelength=1.2, borderpad=0.5,
              labelspacing=0.45)
    cb = fig.add_axes([xs[2] + 0.02, y1 - 0.035, aw - 0.04, 0.018])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(zmin, zmax))
    c = fig.colorbar(sm, cax=cb, orientation="horizontal")
    c.ax.tick_params(labelsize=5, length=1.5, pad=1)
    c.set_label("ROI stereo depth (m)", fontsize=5.2, labelpad=1)
    fig.savefig(f"{OUT}/fig_promotion.pdf")
    fig.savefig(f"{OUT}/fig_promotion.png", dpi=300)
    print("wrote fig_promotion")

    # thumbnails for the system overview (fig_system): stereo pair and the ROI stereo depth of panel (3)
    cv2.imwrite(f"{OUT}/thumb_left.png", cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR))
    cv2.imwrite(f"{OUT}/thumb_right.png", cv2.imread(f"{RAW}/cam1/{ts}.png"))
    cv2.imwrite(f"{OUT}/thumb_depth.png", cv2.cvtColor(P[2][1].astype(np.uint8), cv2.COLOR_RGB2BGR))

if __name__ == "__main__":
    main()
