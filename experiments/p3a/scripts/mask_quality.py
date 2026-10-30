"""Summarise mask_study.py output: human coverage, YOLO-vs-oracle mask quality, right-mask warp sanity.
python3 mask_quality.py <masks dir> -> results/p3a/tables/mask_quality.{md,json}, figures/mask_*.png"""
import csv
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

P3 = '/home/sasa/workspace/savior_ws/results/p3a'
NPX = 720 * 480.0
D = sys.argv[1]
BINS = [30, 100, 300, 1000, 3000, 10000, 1e9]
res = {}
lines = ['# P3a mask quality (offline, every stereo frame; oracle = GT seg colour (35,213,234))\n']
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
for seq, col in [('office_s1_00h', '#2a78d6'), ('office_s1_06h', '#eb6834'), ('office_s1_12h', '#1baf7a')]:
    try:
        rows = list(csv.DictReader(open(f'{D}/{seq}_frames.csv')))
    except FileNotFoundError:
        continue
    g = lambda k: np.array([float(r[k]) if r[k] != '' else np.nan for r in rows])  # noqa: E731
    hp, yp, yi = g('human_px'), g('y_px'), g('y_inter')
    fc, fci, fb, fbi = g('f_core'), g('f_core_inter'), g('f_band'), g('f_band_inter')
    lc, rc, small = g('orc_left_core'), g('orc_right_core'), g('human_px_small')
    hum = hp > 0
    union = hp + yp - yi
    iou = np.where(union > 0, yi / np.maximum(union, 1), np.nan)
    areas, recs = [], []
    for r in rows:
        if r['comp_areas']:
            areas += [int(x) for x in r['comp_areas'].split()]
            recs += [float(x) for x in r['comp_recall'].split()]
    areas, recs = np.array(areas), np.array(recs)
    inst = {}
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        m = (areas >= lo) & (areas < hi)
        inst[f'{lo}-{int(hi) if hi < 1e8 else "inf"}'] = dict(n=int(m.sum()), recall_at_50pct=round(float((recs[m] >= 0.5).mean()), 3)
                                                             if m.any() else None)
    ratio = np.where(lc > 0, rc / np.maximum(lc, 1), np.nan)
    s = dict(frames=len(rows), frames_with_human=round(float(hum.mean()), 4),
             human_cov_mean_all=round(float(hp.mean() / NPX * 100), 4),
             human_cov_mean_when_present=round(float(hp[hum].mean() / NPX * 100), 4) if hum.any() else 0,
             human_cov_p90_when_present=round(float(np.percentile(hp[hum], 90) / NPX * 100), 3) if hum.any() else 0,
             human_cov_max=round(float(hp.max() / NPX * 100), 3),
             frames_cov_gt_1pct=round(float((hp / NPX > 0.01).mean()), 4),
             frames_cov_gt_5pct=round(float((hp / NPX > 0.05).mean()), 4),
             human_px_in_components_lt30=round(float(small.sum() / max(1, hp.sum())), 4),
             oracle_core_vs_human_px=round(float(lc.sum() / max(1, hp.sum())), 4),
             right_vs_left_core_px=round(float(rc.sum() / max(1, lc.sum())), 4),
             frames_right_core_lt_half_left=round(float(np.nanmean(ratio[lc > 0] < 0.5)), 4) if (lc > 0).any() else None)
    if np.isfinite(yp).any():
        s.update(yolo_person=dict(
            pixel_recall=round(float(yi.sum() / max(1, hp.sum())), 4),
            pixel_precision=round(float(yi.sum() / max(1, yp.sum())), 4),
            micro_iou=round(float(yi.sum() / max(1, union.sum())), 4),
            mean_frame_iou_human_frames=round(float(np.nanmean(iou[hum])), 4) if hum.any() else None,
            median_frame_iou_human_frames=round(float(np.nanmedian(iou[hum])), 4) if hum.any() else None,
            frames_detected_any=round(float(((yi > 0)[hum]).mean()), 4) if hum.any() else None,
            frames_with_yolo_mask=round(float((yp > 0).mean()), 4),
            false_positive_frames=round(float(((yp > 0) & ~hum).mean()), 4),
            fp_instances=int(np.nansum(g('y_fp_inst'))),
            mask_px_vs_oracle=round(float(yp.sum() / max(1, hp.sum())), 3),
            instance_recall_by_area_px=inst),
            yolo_full=dict(core_recall=round(float(fci.sum() / max(1, hp.sum())), 4),
                           core_precision=round(float(fci.sum() / max(1, fc.sum())), 4),
                           core_plus_band_recall=round(float((fci + fbi).sum() / max(1, hp.sum())), 4),
                           core_cov_mean=round(float(fc.mean() / NPX * 100), 4),
                           band_cov_mean=round(float(fb.mean() / NPX * 100), 4),
                           masked_px_vs_oracle=round(float((fc + fb).sum() / max(1, hp.sum())), 3)))
        if hum.any():
            axs[1].hist(iou[hum], bins=40, range=(0, 1), color=col, alpha=0.55, label=seq[-3:])
    res[seq] = s
    t = np.arange(len(hp))
    axs[0].plot(t / 16.4, hp / NPX * 100, color=col, lw=0.6, alpha=0.8, label=seq[-3:])
axs[0].set_xlabel('frame index / 16.4 Hz [s]')
axs[0].set_ylabel('oracle human mask [% of image]')
axs[0].legend(frameon=False)
axs[1].set_xlabel('per-frame IoU, YOLO26s-seg person vs oracle (frames with humans)')
axs[1].set_ylabel('frames')
axs[1].legend(frameon=False)
for a in axs:
    a.grid(alpha=0.25, lw=0.5)
    a.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(f'{P3}/figures/mask_coverage_and_yolo_iou.png', dpi=130)
json.dump(res, open(f'{P3}/tables/mask_quality.json', 'w'), indent=1)
import yaml  # noqa: E402
lines.append(yaml.safe_dump(res, sort_keys=False))
open(f'{P3}/tables/mask_quality.md', 'w').write('\n'.join(lines))
print('\n'.join(lines))
