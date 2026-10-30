#!/usr/bin/env python3
"""Fig. 1 of the SAVIOR paper: system overview in the style of the original paper (figures/3_1_1_sys.png).

Vector redraw: stereo images + IMU on the left, the OpenVINS front-end (feature extraction -> dynamic outlier
removal -> feature tracking) and back-end (MSCKF propagation / augmentation / update), and the SAVIOR modules in
blue boxes (detection of potentially dynamic objects; classification of dynamic outliers; post-processing).
Thumbnails: SAVIOR-Warehouse aisles_t1_L2, t = 6.35 s (frame 127; left / right image and ROI stereo depth), written by
make_promotion_figure.py (run it first). Data flow: the stereo pair feeds feature extraction and the ROI stereo
depth; the depth feeds the depth gate and the mask extension; the left image feeds the segmentation; the gyro is a
labelled input of the motion evidence; temporal tracking (IMU-predicted) is part of the frozen SAVIOR configuration.
The front-end and back-end rows are back-end-agnostic: the same masks gate OpenVINS (MSCKF) or VINS-Fusion
(sliding-window bundle adjustment). No arrow crosses.

Usage (inside the savior image):  python3 paper/scripts/make_system_figure.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

WS = "/home/sasa/workspace/savior_ws"
OUT = f"{WS}/paper/figures"
plt.style.use(f"{WS}/src/savior/savior_eval/savior_eval/paper.mplstyle")
BLUE = "#0a5fb4"
FS = 6.0


def main():
    W, H, Y0 = 100.0, 74.0, 3.0          # drawing units; the strip below Y0 is cropped
    fig = plt.figure(figsize=(3.5, 3.5 * (H - Y0) / W))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(Y0, H)
    ax.axis("off")

    def box(x, y, w, h, text="", ec="black", lw=0.7, fs=FS, title=None, bold=False, rs=1.6, fc="white", tdy=0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rs}", fc=fc, ec=ec, lw=lw))
        if text:
            ax.text(x + w / 2, y + h / 2 + tdy, text, ha="center", va="center", fontsize=fs, linespacing=1.05,
                    fontweight="bold" if bold else "normal")
        if title:
            ax.text(x + w / 2, y + h - 1.0, title, ha="center", va="top", fontsize=FS, fontweight="bold",
                    linespacing=1.0)

    def arrow(p0, p1, c="black", lw=0.8, ls="-"):
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=c, lw=lw, ls=ls,
                                                          mutation_scale=6, shrinkA=0, shrinkB=0))

    def line(pts, c="black", lw=0.8):
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, lw=lw, solid_capstyle="butt")

    def thumb(path, x, y, w, h):
        im = plt.imread(path)
        a = fig.add_axes([x / W, (y - Y0) / (H - Y0), w / W, h / (H - Y0)])
        a.imshow(im, aspect="auto")
        a.set_xticks([]); a.set_yticks([])
        for s in a.spines.values():
            s.set_linewidth(0.5)

    # ---------------- SAVIOR modules (blue)
    yT, hT = 50.0, 23.0
    xD, yD, wD, hD = 31.0, 39.6, 14.0, 8.4                     # ROI stereo depth thumbnail
    box(1.0, yT, 21.0, hT, ec=BLUE, lw=1.4, title="Detection of\npotentially\ndynamic\nobjects")
    box(2.8, yT + 2.0, 17.4, 8.0, "Instance\nsegmentation", ec=BLUE, lw=1.0, fs=FS - 0.6)
    box(25.0, yT, 52.0, hT, ec=BLUE, lw=1.4, title="Classification of dynamic outliers")
    inner = [("Overlap", 25.0 + 1.6), ("Depth\ngate", 25.0 + 14.2), ("Associa-\ntion tree", 25.0 + 26.8),
             ("Motion\nevidence", 25.0 + 39.4)]
    for t, x in inner:
        box(x, yT + 2.0, 11.0, 13.0, t, ec=BLUE, lw=1.0, rs=1.2, fs=FS - 0.6)
    for (_, x0), (_, x1) in zip(inner[:-1], inner[1:]):
        arrow((x0 + 11.0, yT + 8.5), (x1, yT + 8.5), lw=0.6)
    box(80.0, 29.0, 19.0, 44.0, ec=BLUE, lw=1.4, title="Post-\nprocessing")
    box(81.6, 51.0, 15.8, 13.0, "Mask\nextension", ec=BLUE, lw=1.0, rs=1.2)
    box(81.6, 31.0, 15.8, 13.0, "Temporal\ntracking", ec=BLUE, lw=1.0, rs=1.2)
    arrow((89.5, 51.0), (89.5, 44.0), lw=0.6)
    arrow((22.0, yT + 6.0), (25.0, yT + 6.0))
    arrow((77.0, yT + 6.0), (80.0, yT + 6.0))

    # ---------------- inputs: stereo pair (bus to feature extraction and ROI stereo depth), left image -> segmentation
    thumb(f"{OUT}/thumb_left.png", 1.0, 34.5, 17.0, 9.5)
    thumb(f"{OUT}/thumb_right.png", 1.0, 23.5, 17.0, 9.5)
    ax.text(9.5, 21.8, "stereo images", ha="center", va="top", fontsize=FS - 0.5)
    box(1.0, 4.0, 17.0, 9.0, "IMU", fs=FS + 0.5, rs=1.0)
    arrow((9.5, 44.0), (9.5, yT), lw=0.7)                       # left image -> instance segmentation
    xb = 20.5                                                   # stereo bus
    line([(18.0, 39.25), (xb, 39.25)], lw=0.7)
    line([(18.0, 28.25), (xb, 28.25)], lw=0.7)
    line([(xb, 28.25), (xb, yD + hD / 2)], lw=0.7)
    arrow((xb, 30.0), (24.0, 30.0))                             # stereo pair -> feature extraction
    arrow((xb, yD + hD / 2), (xD, yD + hD / 2), lw=0.7)          # stereo pair -> ROI stereo depth

    # ---------------- ROI stereo depth (from the stereo pair) -> depth gate and mask extension
    thumb(f"{OUT}/thumb_depth.png", xD, yD, wD, hD)
    ax.text(xD + wD / 2, yD - 0.4, "ROI stereo depth", ha="center", va="top", fontsize=FS - 1.0)
    xg = 25.0 + 14.2 + 3.0                                      # into the depth-gate box
    arrow((xg, yD + hD), (xg, yT + 2.0), lw=0.7)
    yE = yD + hD / 2 + 1.0
    line([(xD + wD, yE), (85.0, yE)], lw=0.7)
    arrow((85.0, yE), (85.0, 51.0), lw=0.7)

    # ---------------- OpenVINS front-end
    yF, hF = 24.0, 12.0
    box(24.0, yF, 16.0, hF, "Feature\nextraction")
    box(44.0, yF, 17.0, hF, "Dynamic\noutlier\nremoval", ec=BLUE, lw=1.4)
    box(65.0, yF, 13.0, hF, "Feature\ntracking")
    arrow((40.0, yF + hF / 2), (44.0, yF + hF / 2))
    arrow((61.0, yF + hF / 2), (65.0, yF + hF / 2))
    # post-processing -> dynamic outlier removal (blue, as in the original)
    yM = 39.0
    line([(81.6, yM), (52.5, yM)], c=BLUE, lw=1.1)
    arrow((52.5, yM), (52.5, yF + hF), c=BLUE, lw=1.1)
    ax.text(54.0, yM + 0.6, "dynamic-outlier masks", fontsize=FS - 1.0, color=BLUE, va="bottom")
    ax.text(51.0, yF - 1.2, "VIO front-end (OpenVINS or VINS-Fusion)", ha="center", va="top", fontsize=FS - 0.8,
            style="italic")
    # gyro -> motion evidence (IMU-compensated); drawn as a labelled input to keep the arrows free of crossings
    xm = 25.0 + 39.4 + 5.5
    arrow((xm, 48.6), (xm, yT + 2.0), c="0.3", lw=0.6)
    ax.text(xm, 48.4, "gyro (IMU)", ha="center", va="top", fontsize=FS - 1.2, color="0.3", style="italic")

    # ---------------- OpenVINS back-end (unchanged MSCKF)
    yB, hB = 4.0, 9.0
    box(24.0, yB, 16.0, hB, "IMU\npropagation", fs=FS - 0.6)
    box(44.0, yB, 34.0, hB, "Visual-inertial\nupdate", fs=FS - 0.6)
    arrow((18.0, yB + hB / 2), (24.0, yB + hB / 2))
    arrow((40.0, yB + hB / 2), (44.0, yB + hB / 2))
    arrow((71.5, yF), (71.5, yB + hB))
    arrow((78.0, yB + hB / 2), (84.0, yB + hB / 2))
    ax.text(85.0, yB + hB / 2, "pose", va="center", fontsize=FS)
    ax.text(51.0, yB + hB + 1.0, "estimator back-end (unchanged)", ha="center", va="bottom", fontsize=FS - 0.8,
            style="italic")
    fig.savefig(f"{OUT}/fig_system.pdf")
    fig.savefig(f"{OUT}/fig_system.png", dpi=300)
    print("wrote fig_system")


if __name__ == "__main__":
    main()
